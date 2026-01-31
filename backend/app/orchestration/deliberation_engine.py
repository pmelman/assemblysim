"""
Deliberation Engine

Orchestrates the complete deliberation flow for a Citizens' Assembly.
Manages agents, turn-taking, message storage, and report generation.
"""

import logging
from typing import Optional, Callable, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import (
    Assembly, Citizen, DeliberationGroup, Message, Report, AssemblyStatus
)
from app.agents import CitizenAgent, ModeratorAgent, RecorderAgent

logger = logging.getLogger(__name__)


class DeliberationEngine:
    """
    Orchestrates a complete Citizens' Assembly deliberation.

    Flow:
    1. Load assembly, citizens, briefing from database
    2. Initialize agent instances
    3. Run deliberation rounds
    4. Conduct voting
    5. Generate final report
    6. Save everything to database
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
            for round_num in range(1, self.assembly.num_rounds + 1):
                await self._run_round(round_num)

            # 4. Voting
            await self._run_voting()

            # 5. Final report
            await self._generate_report()

            # 6. Complete
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

    async def _run_round(self, round_num: int):
        """
        Run a single deliberation round.

        For simplicity, we'll run all citizens in sequence rather than
        dividing into groups. Groups can be added later.

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

            # Citizen responds
            response = await agent.respond(
                discussion_context=context,
                prompt=prompt
            )

            await self._save_message(
                role="citizen",
                content=response,
                phase="deliberation",
                round_number=round_num,
                citizen_id=citizen.id
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

    async def _save_message(
        self,
        role: str,
        content: str,
        phase: str,
        round_number: Optional[int] = None,
        citizen_id: Optional[int] = None,
        group_id: Optional[int] = None
    ):
        """Save a message to the database and track for transcript."""
        message = Message(
            assembly_id=self.assembly_id,
            role=role,
            content=content,
            phase=phase,
            round_number=round_number,
            citizen_id=citizen_id,
            group_id=group_id
        )

        self.db.add(message)
        self.db.commit()

        # Track for transcript
        self.all_messages.append({
            "role": role,
            "content": content,
            "phase": phase,
            "round": round_number,
            "citizen_id": citizen_id
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
                    "citizen_name": citizen_name
                }
            })

    def _get_recent_context(self, limit: int = 10) -> str:
        """Get recent messages as context string."""
        recent = self.all_messages[-limit:]
        lines = []

        for msg in recent:
            speaker = msg["role"].upper()
            if msg["citizen_id"]:
                citizen = next((c for c in self.citizens if c.id == msg["citizen_id"]), None)
                if citizen:
                    speaker = citizen.name

            lines.append(f"{speaker}: {msg['content']}")

        return "\n\n".join(lines)

    def _get_round_transcript(self, round_num: int) -> str:
        """Get all messages from a specific round."""
        round_msgs = [m for m in self.all_messages if m.get("round") == round_num]
        lines = []

        for msg in round_msgs:
            speaker = msg["role"].upper()
            if msg["citizen_id"]:
                citizen = next((c for c in self.citizens if c.id == msg["citizen_id"]), None)
                if citizen:
                    speaker = citizen.name

            lines.append(f"{speaker}: {msg['content']}")

        return "\n\n".join(lines)

    def _get_full_transcript(self) -> str:
        """Get the complete deliberation transcript."""
        lines = []

        for msg in self.all_messages:
            speaker = msg["role"].upper()
            if msg["citizen_id"]:
                citizen = next((c for c in self.citizens if c.id == msg["citizen_id"]), None)
                if citizen:
                    speaker = citizen.name

            phase_label = f"[{msg['phase'].upper()}"
            if msg.get("round"):
                phase_label += f" - Round {msg['round']}"
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
