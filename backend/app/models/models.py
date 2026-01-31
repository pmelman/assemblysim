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
    topic = Column(String(500), nullable=False)
    status = Column(Enum(AssemblyStatus), default=AssemblyStatus.PENDING, nullable=False)

    # Configuration
    num_citizens = Column(Integer, default=40, nullable=False)
    num_groups = Column(Integer, default=5, nullable=False)
    num_rounds = Column(Integer, default=3, nullable=False)
    sampling_strategy = Column(String(50), default="stratified")

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    citizens = relationship("Citizen", back_populates="assembly", cascade="all, delete-orphan")
    groups = relationship("DeliberationGroup", back_populates="assembly", cascade="all, delete-orphan")
    briefing_book = relationship("BriefingBook", back_populates="assembly", uselist=False, cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="assembly", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="assembly", uselist=False, cascade="all, delete-orphan")

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

    # Analysis
    minority_report = Column(Text, nullable=True)
    key_themes = Column(JSON, nullable=True)  # List of theme strings

    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assembly = relationship("Assembly", back_populates="report")

    def __repr__(self):
        return f"<Report(id={self.id}, assembly_id={self.assembly_id})>"
