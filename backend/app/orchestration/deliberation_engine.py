"""
Deliberation Engine

Orchestrates the complete deliberation flow for a Citizens' Assembly.
Manages agents, turn-taking, message storage, and report generation.

Phase 3 Features:
- Group-based deliberation (parallel small groups)
- Citation tracking
- Fact-checking
- Anti-consensus bias (stubbornness)
- Plenary synthesis phase
"""

import logging
import re
from typing import Optional, Callable, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import (
    Assembly, Citizen, DeliberationGroup, Message, Report, AssemblyStatus
)
from app.agents import CitizenAgent, ModeratorAgent, RecorderAgent, FactCheckerAgent
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DeliberationEngine:
    """
    Orchestrates a complete Citizens' Assembly deliberation.

    Phase 3 Flow:
    1. Load assembly, citizens, briefing from database
    2. Initialize agent instances (including fact-checker if enabled)
    3. Run group-based deliberation rounds (or all-together if groups disabled)
    4. Run plenary synthesis phase (if enabled)
    5. Conduct voting
    6. Generate final report
    7. Save everything to database
    """

    def __init__(
        self,
        assembly_id: int,
        db: Session,
        broadcast_callback: Optional[Callable] = None
    ):
        """
        Initialize the deliberation engine.

        Args:
            assembly_id: ID of the assembly to run
            db: Database session
            broadcast_callback: Optional async function to broadcast updates
        """
        self.assembly_id = assembly_id
        self.db = db
        self.broadcast = broadcast_callback

        # Will be loaded
        self.assembly: Optional[Assembly] = None
        self.citizens: list[Citizen] = []
        self.groups: list[DeliberationGroup] = []
        self.briefing_content: Optional[str] = None

        # Agent instances
        self.moderator: Optional[ModeratorAgent] = None
        self.citizen_agents: dict[int, CitizenAgent] = {}
        self.recorder: Optional[RecorderAgent] = None
        self.fact_checker: Optional[FactCheckerAgent] = None

        # State tracking
        self.all_messages: list[dict] = []  # For final transcript

    async def run(self):
        """
        Run the complete deliberation process.

        This is the main entry point that orchestrates everything.
        """
        try:
            logger.info(f"Starting deliberation for assembly {self.assembly_id}")

            # 1. Load data and initialize
            await self._load_assembly()
            await self._initialize_agents()
            await self._update_status(AssemblyStatus.DELIBERATING, "Deliberation started")

            # 2. Opening
            await self._run_opening()

            # 3. Deliberation rounds
            if settings.ENABLE_GROUP_DELIBERATION and len(self.groups) > 0:
                # Group-based deliberation
                for round_num in range(1, self.assembly.num_rounds + 1):
                    await self._run_group_deliberation_round(round_num)
            else:
                # Legacy: all citizens together
                for round_num in range(1, self.assembly.num_rounds + 1):
                    await self._run_round(round_num)

            # 4. Plenary synthesis (if enabled and groups exist)
            if settings.ENABLE_PLENARY_PHASE and len(self.groups) > 0:
                await self._run_plenary()

            # 5. Voting
            await self._run_voting()

            # 6. Final report
            await self._generate_report()

            # 7. Complete
            await self._update_status(AssemblyStatus.COMPLETED, "Deliberation completed")
            self.assembly.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Deliberation completed for assembly {self.assembly_id}")

        except Exception as e:
            logger.error(f"Deliberation failed for assembly {self.assembly_id}: {e}", exc_info=True)
            await self._update_status(
                AssemblyStatus.FAILED,
                f"Deliberation failed: {str(e)}"
            )
            raise

    async def _load_assembly(self):
        """Load assembly data from database."""
        self.assembly = self.db.query(Assembly).filter(
            Assembly.id == self.assembly_id
        ).first()

        if not self.assembly:
            raise ValueError(f"Assembly {self.assembly_id} not found")

        # Load citizens
        self.citizens = self.db.query(Citizen).filter(
            Citizen.assembly_id == self.assembly_id
        ).order_by(Citizen.id).all()

        if not self.citizens:
            raise ValueError(f"No citizens found for assembly {self.assembly_id}")

        # Load groups
        self.groups = self.db.query(DeliberationGroup).filter(
            DeliberationGroup.assembly_id == self.assembly_id
        ).order_by(DeliberationGroup.name).all()

        # Load briefing content
        if self.assembly.briefing_book:
            self.briefing_content = self.assembly.briefing_book.content_markdown

        logger.info(
            f"Loaded assembly: {len(self.citizens)} citizens, "
            f"{len(self.groups)} groups, "
            f"briefing: {'yes' if self.briefing_content else 'no'}"
        )

    async def _initialize_agents(self):
        """Initialize all agent instances."""
        # Moderator
        self.moderator = ModeratorAgent(self.assembly.topic)

        # Recorder
        self.recorder = RecorderAgent(self.assembly.topic)

        # Fact-checker (if enabled and briefing exists)
        if settings.ENABLE_FACT_CHECKING and self.briefing_content:
            self.fact_checker = FactCheckerAgent(self.briefing_content)
            logger.info("Fact-checker agent initialized")

        # Citizens
        for citizen in self.citizens:
            agent = CitizenAgent(
                citizen_id=citizen.id,
                name=citizen.name,
                system_prompt=citizen.system_prompt,
                background_summary=citizen.background_summary,
                key_values=citizen.key_values,
                briefing_content=self.briefing_content
            )
            self.citizen_agents[citizen.id] = agent

        logger.info(f"Initialized {len(self.citizen_agents)} citizen agents")

    async def _run_opening(self):
        """Run the assembly opening."""
        citizen_names = [c.name for c in self.citizens]
        opening_msg = await self.moderator.open_assembly(citizen_names)

        await self._save_message(
            role="moderator",
            content=opening_msg,
            phase="opening"
        )

        logger.info("Opening complete")

    async def _run_group_deliberation_round(self, round_num: int):
        """
        Run a deliberation round across all groups.

        Each group deliberates separately, then the recorder summarizes.
        """
        logger.info(f"Starting group deliberation round {round_num}/{self.assembly.num_rounds}")

        # Run each group's round
        for group in self.groups:
            await self._run_group_round(group, round_num)

        logger.info(f"Round {round_num} complete for all groups")

        # Broadcast round completion
        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "round_complete",
                "round": round_num,
                "total_rounds": self.assembly.num_rounds
            })

    async def _run_group_round(self, group: DeliberationGroup, round_num: int):
        """
        Run a single round for one group.

        Args:
            group: The deliberation group
            round_num: The round number (1-indexed)
        """
        # Get citizens in this group
        group_citizens = [c for c in self.citizens if c.group_id == group.id]

        if not group_citizens:
            logger.warning(f"No citizens in group {group.name}")
            return

        logger.info(f"Running round {round_num} for Group {group.name} ({len(group_citizens)} citizens)")

        # Moderator opens round for this group
        citizen_names = [c.name for c in group_citizens]
        opening = await self.moderator.open_round(
            round_number=round_num,
            citizen_names=citizen_names
        )

        await self._save_message(
            role="moderator",
            content=f"[Group {group.name}] {opening}",
            phase="deliberation",
            round_number=round_num,
            group_id=group.id
        )

        # Get group-specific context
        context = self._get_group_context(group.id, limit=10)

        # Each citizen in this group responds
        for i, citizen in enumerate(group_citizens):
            agent = self.citizen_agents[citizen.id]

            # Get a specific prompt from moderator occasionally
            prompt = None
            if i % 3 == 0 and i > 0:
                prompt = await self.moderator.prompt_citizen(
                    citizen.name,
                    context=context
                )

            # Citizen responds with round context for stubbornness
            response = await agent.respond(
                discussion_context=context,
                prompt=prompt,
                round_number=round_num,
                total_rounds=self.assembly.num_rounds
            )

            # Extract citations (if enabled)
            citations = None
            if settings.ENABLE_CITATIONS:
                citations = self._extract_citations(response)

            # Fact check (if enabled)
            fact_check_status = None
            if self.fact_checker:
                result = await self.fact_checker.check_message(response)
                fact_check_status = result["status"]

            await self._save_message(
                role="citizen",
                content=response,
                phase="deliberation",
                round_number=round_num,
                citizen_id=citizen.id,
                group_id=group.id,
                citations=citations,
                fact_check_status=fact_check_status
            )

            # Update context for next citizen
            context = self._get_group_context(group.id, limit=10)

            # Broadcast progress
            if self.broadcast:
                await self.broadcast(self.assembly_id, {
                    "type": "new_message",
                    "round": round_num,
                    "group": group.name,
                    "citizen": citizen.name,
                    "progress": f"{i+1}/{len(group_citizens)}"
                })

        # Recorder summarizes this group's round
        round_transcript = self._get_group_round_transcript(group.id, round_num)
        summary = await self.recorder.summarize_round(
            transcript=round_transcript,
            round_number=round_num,
            group_name=group.name
        )

        await self._save_message(
            role="recorder",
            content=f"[Group {group.name} Summary] {summary}",
            phase="deliberation",
            round_number=round_num,
            group_id=group.id
        )

        # Save group round summary
        if not group.round_summaries:
            group.round_summaries = []
        group.round_summaries.append({
            "round": round_num,
            "summary": summary
        })
        self.db.commit()

        logger.info(f"Group {group.name} round {round_num} complete")

    async def _run_round(self, round_num: int):
        """
        Run a single deliberation round (legacy: all citizens together).

        For simplicity, we'll run all citizens in sequence rather than
        dividing into groups.

        Args:
            round_num: The round number (1-indexed)
        """
        logger.info(f"Starting round {round_num}/{self.assembly.num_rounds}")

        # Moderator opens the round
        citizen_names = [c.name for c in self.citizens]
        opening = await self.moderator.open_round(
            round_number=round_num,
            citizen_names=citizen_names
        )

        await self._save_message(
            role="moderator",
            content=opening,
            phase="deliberation",
            round_number=round_num
        )

        # Get recent discussion context (last 10 messages)
        context = self._get_recent_context(limit=10)

        # Each citizen responds
        for i, citizen in enumerate(self.citizens):
            agent = self.citizen_agents[citizen.id]

            # Get a specific prompt from moderator occasionally
            prompt = None
            if i % 3 == 0 and i > 0:  # Every 3rd citizen after first
                prompt = await self.moderator.prompt_citizen(
                    citizen.name,
                    context=context
                )

            # Citizen responds with round context
            response = await agent.respond(
                discussion_context=context,
                prompt=prompt,
                round_number=round_num,
                total_rounds=self.assembly.num_rounds
            )

            # Extract citations (if enabled)
            citations = None
            if settings.ENABLE_CITATIONS:
                citations = self._extract_citations(response)

            # Fact check (if enabled)
            fact_check_status = None
            if self.fact_checker:
                result = await self.fact_checker.check_message(response)
                fact_check_status = result["status"]

            await self._save_message(
                role="citizen",
                content=response,
                phase="deliberation",
                round_number=round_num,
                citizen_id=citizen.id,
                citations=citations,
                fact_check_status=fact_check_status
            )

            # Update context for next citizen
            context = self._get_recent_context(limit=10)

            # Broadcast progress
            if self.broadcast:
                await self.broadcast(self.assembly_id, {
                    "type": "new_message",
                    "round": round_num,
                    "citizen": citizen.name,
                    "progress": f"{i+1}/{len(self.citizens)}"
                })

        # Recorder summarizes the round
        round_transcript = self._get_round_transcript(round_num)
        summary = await self.recorder.summarize_round(
            transcript=round_transcript,
            round_number=round_num
        )

        await self._save_message(
            role="recorder",
            content=summary,
            phase="deliberation",
            round_number=round_num
        )

        logger.info(f"Round {round_num} complete")

        # Broadcast round completion
        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "round_complete",
                "round": round_num,
                "total_rounds": self.assembly.num_rounds
            })

    async def _run_plenary(self):
        """Run plenary synthesis after group deliberation."""
        logger.info("Starting plenary synthesis")

        # Generate group summaries
        group_summaries = []
        for group in self.groups:
            # Generate overall group summary from round summaries
            summary = await self.recorder.generate_group_summary(
                group_name=group.name,
                round_summaries=group.round_summaries or []
            )

            group.consensus_summary = summary.get("consensus", "")
            group.disagreements_summary = summary.get("disagreements", "")

            group_summaries.append({
                "group": group.name,
                "summary": summary
            })

        self.db.commit()

        # Moderator presents cross-group synthesis
        synthesis = await self.moderator.present_plenary_synthesis(
            group_summaries=group_summaries,
            topic=self.assembly.topic
        )

        await self._save_message(
            role="moderator",
            content=synthesis,
            phase="plenary"
        )

        # Brief cross-group discussion (one representative from each group)
        for group in self.groups:
            rep = self._select_group_representative(group)
            if rep is None:
                continue

            agent = self.citizen_agents[rep.id]

            response = await agent.respond_to_plenary(
                group_summaries=group_summaries,
                own_group=group.name
            )

            await self._save_message(
                role="citizen",
                content=f"[Group {group.name} Representative] {response}",
                phase="plenary",
                citizen_id=rep.id,
                group_id=group.id
            )

        logger.info("Plenary synthesis complete")

        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "plenary_complete"
            })

    def _select_group_representative(self, group: DeliberationGroup) -> Optional[Citizen]:
        """
        Select a representative from a group for plenary discussion.

        Selects the citizen who spoke most (or first citizen as fallback).
        """
        group_citizens = [c for c in self.citizens if c.group_id == group.id]

        if not group_citizens:
            return None

        # Count messages per citizen in this group
        citizen_msg_counts = {}
        for msg in self.all_messages:
            if msg.get("group_id") == group.id and msg.get("citizen_id"):
                cid = msg["citizen_id"]
                citizen_msg_counts[cid] = citizen_msg_counts.get(cid, 0) + 1

        # Find most active citizen
        if citizen_msg_counts:
            most_active_id = max(citizen_msg_counts, key=citizen_msg_counts.get)
            for c in group_citizens:
                if c.id == most_active_id:
                    return c

        # Fallback to first citizen
        return group_citizens[0]

    async def _run_voting(self):
        """Run the voting phase."""
        logger.info("Starting voting phase")

        await self._update_status(AssemblyStatus.VOTING, "Voting in progress")

        # Create recommendations from discussion
        recommendations = [
            {
                "title": f"Recommendation on {self.assembly.topic}",
                "description": "Based on the deliberation, participants will vote on this policy proposal."
            }
        ]

        # Moderator transitions to voting
        full_transcript = self._get_full_transcript()
        discussion_summary = await self.recorder.generate_consensus_summary(
            transcript=full_transcript
        )

        transition = await self.moderator.transition_to_voting(
            discussion_summary=discussion_summary,
            recommendations=recommendations
        )

        await self._save_message(
            role="moderator",
            content=transition,
            phase="voting"
        )

        # Each citizen votes
        vote_tally = {"support": 0, "oppose": 0, "abstain": 0}

        for citizen in self.citizens:
            agent = self.citizen_agents[citizen.id]

            vote_result = await agent.cast_vote(
                recommendations=recommendations,
                discussion_summary=discussion_summary
            )

            # Save vote to database
            citizen.final_vote = vote_result["vote"]
            citizen.vote_reasoning = vote_result["reasoning"]

            # Update tally
            vote_tally[vote_result["vote"]] = vote_tally.get(vote_result["vote"], 0) + 1

            # Save voting message
            await self._save_message(
                role="citizen",
                content=f"Vote: {vote_result['vote'].upper()}\n\nReasoning: {vote_result['reasoning']}",
                phase="voting",
                citizen_id=citizen.id
            )

        self.db.commit()

        vote_tally["total"] = len(self.citizens)
        logger.info(f"Voting complete: {vote_tally}")

        # Moderator closes
        themes = await self.recorder.identify_themes(full_transcript)
        closing = await self.moderator.close_assembly(
            vote_results=vote_tally,
            key_themes=themes
        )

        await self._save_message(
            role="moderator",
            content=closing,
            phase="closing"
        )

        # Store vote tally for report
        self.vote_tally = vote_tally

        logger.info("Voting complete")

    async def _generate_report(self):
        """Generate the final assembly report."""
        logger.info("Generating final report")

        full_transcript = self._get_full_transcript()

        recommendations = [
            {
                "title": f"Policy Recommendation: {self.assembly.topic}",
                "description": "The assembly deliberated on this topic and reached the following conclusion.",
                "support_level": "strong" if self.vote_tally["support"] > len(self.citizens) * 0.6 else "moderate"
            }
        ]

        # Generate all report components
        report_data = await self.recorder.generate_final_summary(
            full_transcript=full_transcript,
            vote_results=self.vote_tally,
            recommendations=recommendations
        )

        # Save to database
        report = Report(
            assembly_id=self.assembly_id,
            executive_summary=report_data["executive_summary"],
            recommendations=recommendations,
            vote_tally=self.vote_tally,
            minority_report=report_data["minority_report"],
            key_themes=report_data["key_themes"]
        )

        self.db.add(report)
        self.db.commit()

        logger.info("Report generated and saved")

        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "report_ready",
                "vote_tally": self.vote_tally,
                "themes": report_data["key_themes"]
            })

    def _extract_citations(self, response: str) -> Optional[list[dict]]:
        """
        Extract citations from citizen response.

        Looks for [Source: ...] patterns in the response.

        Args:
            response: The citizen's response text

        Returns:
            List of citation dicts or None if no citations found
        """
        citations = []

        # Match [Source: ...] patterns
        pattern = r'\[Source:\s*([^\]]+)\]'
        matches = re.findall(pattern, response)

        for match in matches:
            citation = {
                "text": match.strip(),
                "source": self._match_to_briefing_source(match),
                "url": None  # Could link to Perplexity sources in future
            }
            citations.append(citation)

        return citations if citations else None

    def _match_to_briefing_source(self, source_text: str) -> str:
        """
        Match citation text to briefing book section.

        Args:
            source_text: The source text from the citation

        Returns:
            Normalized section name
        """
        source_lower = source_text.lower()

        if "overview" in source_lower:
            return "Briefing Overview"
        elif "fact" in source_lower or "statistic" in source_lower:
            return "Key Facts"
        elif "for" in source_lower or "support" in source_lower or "proponent" in source_lower:
            return "Arguments For"
        elif "against" in source_lower or "oppose" in source_lower or "opponent" in source_lower:
            return "Arguments Against"
        elif "option" in source_lower or "policy" in source_lower:
            return "Policy Options"
        else:
            return source_text

    async def _save_message(
        self,
        role: str,
        content: str,
        phase: str,
        round_number: Optional[int] = None,
        citizen_id: Optional[int] = None,
        group_id: Optional[int] = None,
        citations: Optional[list[dict]] = None,
        fact_check_status: Optional[str] = None
    ):
        """Save a message to the database and track for transcript."""
        message = Message(
            assembly_id=self.assembly_id,
            role=role,
            content=content,
            phase=phase,
            round_number=round_number,
            citizen_id=citizen_id,
            group_id=group_id,
            citations=citations,
            fact_check_status=fact_check_status
        )

        self.db.add(message)
        self.db.commit()

        # Track for transcript
        self.all_messages.append({
            "role": role,
            "content": content,
            "phase": phase,
            "round": round_number,
            "citizen_id": citizen_id,
            "group_id": group_id
        })

        # Broadcast new message
        if self.broadcast:
            citizen_name = None
            if citizen_id:
                citizen = next((c for c in self.citizens if c.id == citizen_id), None)
                if citizen:
                    citizen_name = citizen.name

            await self.broadcast(self.assembly_id, {
                "type": "new_message",
                "message": {
                    "role": role,
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "phase": phase,
                    "round": round_number,
                    "citizen_name": citizen_name,
                    "citations": citations,
                    "fact_check_status": fact_check_status
                }
            })

    def _get_group_context(self, group_id: int, limit: int = 10) -> str:
        """
        Get recent messages for a specific group.

        Args:
            group_id: The group's database ID
            limit: Maximum number of messages to include

        Returns:
            Formatted context string
        """
        group_msgs = [m for m in self.all_messages if m.get("group_id") == group_id]
        return self._format_context(group_msgs[-limit:])

    def _get_group_round_transcript(self, group_id: int, round_num: int) -> str:
        """
        Get all messages from a specific group and round.

        Args:
            group_id: The group's database ID
            round_num: The round number

        Returns:
            Formatted transcript string
        """
        msgs = [m for m in self.all_messages
                if m.get("group_id") == group_id and m.get("round") == round_num]
        return self._format_context(msgs)

    def _format_context(self, messages: list[dict]) -> str:
        """
        Format a list of messages into a context string.

        Args:
            messages: List of message dicts

        Returns:
            Formatted context string
        """
        lines = []

        for msg in messages:
            speaker = msg["role"].upper()
            if msg.get("citizen_id"):
                citizen = next((c for c in self.citizens if c.id == msg["citizen_id"]), None)
                if citizen:
                    speaker = citizen.name

            lines.append(f"{speaker}: {msg['content']}")

        return "\n\n".join(lines)

    def _get_recent_context(self, limit: int = 10) -> str:
        """Get recent messages as context string."""
        recent = self.all_messages[-limit:]
        return self._format_context(recent)

    def _get_round_transcript(self, round_num: int) -> str:
        """Get all messages from a specific round."""
        round_msgs = [m for m in self.all_messages if m.get("round") == round_num]
        return self._format_context(round_msgs)

    def _get_full_transcript(self) -> str:
        """Get the complete deliberation transcript."""
        lines = []

        for msg in self.all_messages:
            speaker = msg["role"].upper()
            if msg.get("citizen_id"):
                citizen = next((c for c in self.citizens if c.id == msg["citizen_id"]), None)
                if citizen:
                    speaker = citizen.name

            phase_label = f"[{msg['phase'].upper()}"
            if msg.get("round"):
                phase_label += f" - Round {msg['round']}"
            if msg.get("group_id"):
                group = next((g for g in self.groups if g.id == msg["group_id"]), None)
                if group:
                    phase_label += f" - Group {group.name}"
            phase_label += "]"

            lines.append(f"{phase_label} {speaker}: {msg['content']}")

        return "\n\n".join(lines)

    async def _update_status(self, status: AssemblyStatus, message: Optional[str] = None):
        """Update assembly status and optionally broadcast."""
        self.assembly.status = status
        if message and not self.assembly.error_message:
            # Only update error message if it's an actual error
            if status == AssemblyStatus.FAILED:
                self.assembly.error_message = message

        self.db.commit()

        logger.info(f"Status updated to: {status.value}")

        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "status_update",
                "status": status.value,
                "message": message or f"Status: {status.value}"
            })


async def run_deliberation(
    assembly_id: int,
    db: Session,
    broadcast_callback: Optional[Callable] = None
):
    """
    Convenience function to run a complete deliberation.

    Args:
        assembly_id: ID of the assembly
        db: Database session
        broadcast_callback: Optional async callback for broadcasts
    """
    engine = DeliberationEngine(assembly_id, db, broadcast_callback)
    await engine.run()
