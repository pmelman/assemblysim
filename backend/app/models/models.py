"""
SQLAlchemy Models for Silicon Citizens' Assembly

Defines the database schema for assemblies, citizens, deliberation groups,
messages, briefing books, and reports.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, JSON, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship

from app.models.database import Base


class User(Base):
    """User account for authentication and access control."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    invite_codes_created = relationship("InviteCode", foreign_keys="InviteCode.created_by_user_id", back_populates="created_by")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', is_admin={self.is_admin})>"


class InviteCode(Base):
    """Invite codes for user registration."""
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="invite_codes_created")
    used_by = relationship("User", foreign_keys=[used_by_user_id])

    def __repr__(self):
        return f"<InviteCode(id={self.id}, code='{self.code[:8]}...', used={'yes' if self.used_by_user_id else 'no'})>"


class AssemblyStatus(str, enum.Enum):
    """Status of an assembly through its lifecycle."""
    PENDING = "pending"              # Created, awaiting citizen generation
    GENERATING_CITIZENS = "generating_citizens"  # Citizens being generated
    CITIZENS_READY = "citizens_ready"    # Citizens generated, awaiting briefing
    GENERATING_BRIEFING = "generating_briefing"  # Briefing book being created
    READY = "ready"                  # Ready for deliberation
    DELIBERATING = "deliberating"    # Deliberation in progress
    VOTING = "voting"                # Voting phase
    COMPLETED = "completed"          # Assembly finished
    FAILED = "failed"                # Error occurred


class Assembly(Base):
    """
    A Citizens' Assembly deliberation session.

    Represents a complete assembly including its topic, participants,
    deliberation content, and final report.
    """
    __tablename__ = "assemblies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    topic = Column(String(500), nullable=False)
    status = Column(Enum(AssemblyStatus), default=AssemblyStatus.PENDING, nullable=False)

    # Configuration
    num_citizens = Column(Integer, default=40, nullable=False)
    num_groups = Column(Integer, default=5, nullable=False)
    num_rounds = Column(Integer, default=3, nullable=False)
    sampling_strategy = Column(String(50), default="stratified")

    # Per-round prompts: [{"theme": "...", "prompt": "..."}]
    round_prompts = Column(JSON, nullable=True)

    # Follow-up research configuration
    max_research_calls_per_round = Column(Integer, default=2, nullable=False)
    max_research_tokens_per_call = Column(Integer, default=2000, nullable=False)

    # Custom citizens (list of CustomCitizenTemplate IDs to include)
    custom_citizen_ids = Column(JSON, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    citizens = relationship("Citizen", back_populates="assembly", cascade="all, delete-orphan")
    groups = relationship("DeliberationGroup", back_populates="assembly", cascade="all, delete-orphan")
    briefing_book = relationship("BriefingBook", back_populates="assembly", uselist=False, cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="assembly", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="assembly", uselist=False, cascade="all, delete-orphan")
    round_research = relationship("RoundResearch", back_populates="assembly", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Assembly(id={self.id}, topic='{self.topic[:30]}...', status={self.status})>"


class Citizen(Base):
    """
    A citizen participant in an assembly.

    Stores the GSS source data, generated persona, and voting information.
    """
    __tablename__ = "citizens"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("deliberation_groups.id"), nullable=True)

    # GSS source data
    gss_row_id = Column(Integer, nullable=True)
    gss_year = Column(Integer, nullable=True)
    gss_data = Column(JSON, nullable=True)  # Full GSS variables as JSON

    # Generated persona
    name = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    background_summary = Column(Text, nullable=True)
    key_values = Column(JSON, nullable=True)  # List of value strings
    demographic_tags = Column(JSON, nullable=True)  # List of tag strings

    # Voting
    final_vote = Column(String(50), nullable=True)  # "support", "oppose", "abstain"
    vote_reasoning = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assembly = relationship("Assembly", back_populates="citizens")
    group = relationship("DeliberationGroup", back_populates="citizens")
    messages = relationship("Message", back_populates="citizen", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Citizen(id={self.id}, name='{self.name}', assembly_id={self.assembly_id})>"


class DeliberationGroup(Base):
    """
    A small group for deliberation discussions.

    Assemblies are divided into groups (typically 5) of 8 citizens each
    for more focused discussion.
    """
    __tablename__ = "deliberation_groups"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    name = Column(String(10), nullable=False)  # 'A', 'B', 'C', 'D', 'E'

    # Round summaries (list of summaries per round)
    round_summaries = Column(JSON, nullable=True)

    # Final summaries
    consensus_summary = Column(Text, nullable=True)
    disagreements_summary = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assembly = relationship("Assembly", back_populates="groups")
    citizens = relationship("Citizen", back_populates="group")
    messages = relationship("Message", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DeliberationGroup(id={self.id}, name='{self.name}', assembly_id={self.assembly_id})>"


class Message(Base):
    """
    A message in the deliberation process.

    Captures all dialogue including moderator prompts, citizen responses,
    and recorder summaries.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("deliberation_groups.id"), nullable=True)
    citizen_id = Column(Integer, ForeignKey("citizens.id"), nullable=True)

    # Message context
    phase = Column(String(50), nullable=False)  # "introduction", "deliberation", "voting"
    round_number = Column(Integer, nullable=True)
    role = Column(String(50), nullable=False)  # "moderator", "citizen", "recorder", "system"

    # Content
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)  # List of source citations

    # Fact-checking (future use)
    fact_check_status = Column(String(50), nullable=True)  # "verified", "disputed", "unchecked"

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assembly = relationship("Assembly", back_populates="messages")
    group = relationship("DeliberationGroup", back_populates="messages")
    citizen = relationship("Citizen", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', phase='{self.phase}')>"


class BriefingBook(Base):
    """
    Research briefing materials for an assembly.

    Contains Perplexity-generated research on the assembly topic,
    including arguments for and against, policy options, and sources.
    """
    __tablename__ = "briefing_books"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False, unique=True)

    # Query and content
    topic_query = Column(Text, nullable=False)
    content_markdown = Column(Text, nullable=False)

    # Structured sections
    sections = Column(JSON, nullable=True)
    # Expected structure:
    # {
    #     "overview": "...",
    #     "arguments_for": ["...", "..."],
    #     "arguments_against": ["...", "..."],
    #     "policy_options": ["...", "..."],
    #     "key_facts": ["...", "..."]
    # }

    # Sources
    sources = Column(JSON, nullable=True)  # List of {title, url, snippet}

    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assembly = relationship("Assembly", back_populates="briefing_book")

    def __repr__(self):
        return f"<BriefingBook(id={self.id}, assembly_id={self.assembly_id})>"


class Report(Base):
    """
    Final report from a completed assembly.

    Contains the executive summary, recommendations, vote tally,
    and analysis of themes and minority viewpoints.
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False, unique=True)

    # Summary
    executive_summary = Column(Text, nullable=True)

    # Recommendations (list of recommendation objects)
    recommendations = Column(JSON, nullable=True)
    # Expected structure:
    # [
    #     {"title": "...", "description": "...", "support_level": "strong/moderate/weak"},
    #     ...
    # ]

    # Voting
    vote_tally = Column(JSON, nullable=True)
    # Expected structure:
    # {
    #     "support": 25,
    #     "oppose": 10,
    #     "abstain": 5,
    #     "total": 40
    # }

    # Proposal scores (all proposals with avg scores and pass/fail)
    proposal_scores = Column(JSON, nullable=True)
    # Expected structure:
    # [
    #     {"title": "...", "description": "...", "avg_score": 3.8, "num_votes": 40, "passed": true},
    #     ...
    # ]

    # Analysis
    minority_report = Column(Text, nullable=True)
    key_themes = Column(JSON, nullable=True)  # List of theme strings

    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assembly = relationship("Assembly", back_populates="report")

    def __repr__(self):
        return f"<Report(id={self.id}, assembly_id={self.assembly_id})>"


class RoundResearch(Base):
    """
    Follow-up research results generated between deliberation rounds.

    Stores Perplexity research queries and results triggered by
    analysis of the round's discussion.
    """
    __tablename__ = "round_research"

    id = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    queries = Column(JSON, nullable=False)        # ["query1", "query2"]
    results = Column(JSON, nullable=False)         # [{"query": "...", "content": "...", "sources": [...]}]
    summary_markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assembly = relationship("Assembly", back_populates="round_research")

    def __repr__(self):
        return f"<RoundResearch(id={self.id}, assembly_id={self.assembly_id}, round={self.round_number})>"


class CustomCitizenTemplate(Base):
    """
    A reusable custom citizen template.

    Saved independently of assemblies and can be selected when creating
    a new assembly to pre-seed specific citizens before GSS generation
    fills the remaining slots.
    """
    __tablename__ = "custom_citizen_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    mode = Column(String(20), nullable=False, default="traits")  # "traits" or "full"

    # Traits (used in "traits" mode, optional in "full" mode)
    background_summary = Column(Text, nullable=True)
    key_values = Column(JSON, nullable=True)  # List of value strings
    demographic_tags = Column(JSON, nullable=True)  # List of tag strings
    political_leaning = Column(String(50), nullable=True)  # e.g. "liberal", "moderate", "conservative"

    # Generated or user-provided persona
    system_prompt = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<CustomCitizenTemplate(id={self.id}, name='{self.name}', mode='{self.mode}')>"


class AssemblyProfile(Base):
    """
    A saved assembly settings profile.

    Stores a named bundle of assembly creation settings (prompts, sizes,
    preset delegates, etc.) that the user can load when creating new
    assemblies.
    """
    __tablename__ = "assembly_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False)  # Bundle of assembly creation settings

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<AssemblyProfile(id={self.id}, name='{self.name}')>"


class AppSettings(Base):
    """
    Singleton table for persistent application defaults.

    Only one row (id=1) should exist. Stores default values
    for assembly creation parameters.
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    default_num_citizens = Column(Integer, default=40)
    default_num_groups = Column(Integer, default=5)
    default_num_rounds = Column(Integer, default=3)
    default_sampling_strategy = Column(String(50), default="stratified")
    default_round_prompts = Column(JSON, nullable=True)
    default_max_research_calls_per_round = Column(Integer, default=2)
    default_max_research_tokens_per_call = Column(Integer, default=2000)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSettings(id={self.id})>"
