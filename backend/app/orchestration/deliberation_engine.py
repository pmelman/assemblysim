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

import json
import logging
import re
from typing import Optional, Callable, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.models import (
    Assembly, Citizen, DeliberationGroup, Message, Report, RoundResearch,
    AssemblyStatus
)
from app.agents import CitizenAgent, ModeratorAgent, RecorderAgent, FactCheckerAgent
from app.config import get_settings
from app.knowledge.perplexity_client import get_perplexity_client
from app.llm_client import get_llm_client
from app.prompt_loader import get_moderator_proposal_prompt, get_moderator_score_voting_transition

logger = logging.getLogger(__name__)
settings = get_settings()

# Default round prompts used when none are configured on the assembly
DEFAULT_ROUND_PROMPTS = [
    {
        "theme": "Initial Reactions",
        "prompt": "Focus on first impressions and personal connections to the topic. "
                  "Encourage citizens to share how this issue affects them personally "
                  "and what their initial stance is."
    },
    {
        "theme": "Trade-offs & Evidence",
        "prompt": "Push citizens to engage with the briefing evidence and consider "
                  "trade-offs. Challenge assumptions and encourage them to respond "
                  "to points raised by others, especially those they disagree with."
    },
    {
        "theme": "Synthesis & Recommendations",
        "prompt": "Guide the discussion toward actionable recommendations. Ask citizens "
                  "to identify areas of agreement, propose specific policy options, and "
                  "articulate what an ideal outcome would look like."
    },
]


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
                    # Follow-up research between rounds (not after the last one)
                    if round_num < self.assembly.num_rounds:
                        await self._run_follow_up_research(round_num)
            else:
                # Legacy: all citizens together
                for round_num in range(1, self.assembly.num_rounds + 1):
                    await self._run_round(round_num)
                    # Follow-up research between rounds (not after the last one)
                    if round_num < self.assembly.num_rounds:
                        await self._run_follow_up_research(round_num)

            # 4. Plenary synthesis (if enabled and groups exist)
            if settings.ENABLE_PLENARY_PHASE and len(self.groups) > 0:
                await self._run_plenary()

            # 5. Proposal generation & score voting
            await self._run_proposal_round()
            await self._run_assembly_score_voting()

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

    def _get_round_prompt(self, round_num: int) -> dict:
        """
        Get the theme and prompt for a given round number.

        Checks the assembly's configured round_prompts first, then falls back
        to DEFAULT_ROUND_PROMPTS, then to a generic fallback.

        Args:
            round_num: 1-indexed round number

        Returns:
            Dict with 'theme' and 'prompt' keys
        """
        idx = round_num - 1

        # Check assembly-configured prompts
        if self.assembly.round_prompts and idx < len(self.assembly.round_prompts):
            return self.assembly.round_prompts[idx]

        # Fall back to defaults
        if idx < len(DEFAULT_ROUND_PROMPTS):
            return DEFAULT_ROUND_PROMPTS[idx]

        # Generic fallback for rounds beyond configured count
        return {
            "theme": f"Round {round_num} Discussion",
            "prompt": "Continue the deliberation, building on previous rounds. "
                      "Encourage deeper engagement and new perspectives."
        }

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

        # Get round prompt configuration
        round_config = self._get_round_prompt(round_num)
        round_theme = round_config.get("theme")
        round_prompt_text = round_config.get("prompt")

        # Moderator opens round for this group
        citizen_names = [c.name for c in group_citizens]
        opening = await self.moderator.open_round(
            round_number=round_num,
            citizen_names=citizen_names,
            round_theme=round_theme,
            round_prompt=round_prompt_text
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

        # Save group round summary (reassign to trigger SQLAlchemy change detection)
        current_summaries = group.round_summaries or []
        group.round_summaries = current_summaries + [{
            "round": round_num,
            "summary": summary
        }]
        flag_modified(group, "round_summaries")
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

        # Get round prompt configuration
        round_config = self._get_round_prompt(round_num)
        round_theme = round_config.get("theme")
        round_prompt_text = round_config.get("prompt")

        # Moderator opens the round
        citizen_names = [c.name for c in self.citizens]
        opening = await self.moderator.open_round(
            round_number=round_num,
            citizen_names=citizen_names,
            round_theme=round_theme,
            round_prompt=round_prompt_text
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

    async def _run_follow_up_research(self, round_num: int):
        """
        Run follow-up research between rounds using Perplexity.

        Analyzes the round transcript to generate research queries,
        calls Perplexity for each, and saves results.

        Args:
            round_num: The round that just completed
        """
        max_calls = self.assembly.max_research_calls_per_round
        if max_calls <= 0:
            logger.info(f"Follow-up research disabled (max_calls=0)")
            return

        max_tokens = self.assembly.max_research_tokens_per_call

        logger.info(f"Running follow-up research after round {round_num}")

        # Get the round transcript
        transcript = self._get_round_transcript(round_num)
        if not transcript:
            logger.warning(f"No transcript for round {round_num}, skipping research")
            return

        # Generate research queries from transcript
        queries = await self._generate_research_queries(transcript, round_num)
        if not queries:
            logger.info(f"No research queries generated for round {round_num}")
            return

        # Limit to max calls
        queries = queries[:max_calls]
        logger.info(f"Researching {len(queries)} queries for round {round_num}")

        # Call Perplexity for each query
        perplexity = get_perplexity_client()
        results = []
        for query in queries:
            result = await perplexity.research_query(query, max_tokens=max_tokens)
            results.append(result)

        # Build summary markdown
        summary_md = self._build_research_summary(results, round_num)

        # Save RoundResearch record
        research_record = RoundResearch(
            assembly_id=self.assembly_id,
            round_number=round_num,
            queries=queries,
            results=results,
            summary_markdown=summary_md
        )
        self.db.add(research_record)
        self.db.commit()

        # Save as a system message so it appears in context for the next round
        await self._save_message(
            role="system",
            content=summary_md,
            phase="research",
            round_number=round_num
        )

        logger.info(f"Follow-up research complete for round {round_num}")

        # Broadcast research complete event
        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "research_complete",
                "round": round_num,
                "num_queries": len(queries)
            })

    async def _generate_research_queries(self, transcript: str, round_num: int) -> list[str]:
        """
        Use utility LLM to analyze the round transcript and generate
        focused research queries targeting unresolved factual questions.

        Args:
            transcript: The round's discussion transcript
            round_num: The round number

        Returns:
            List of research query strings
        """
        llm = get_llm_client(purpose="utility")

        prompt = f"""Analyze this deliberation transcript from Round {round_num} and identify 1-3 specific,
factual research questions that emerged from the discussion. Focus on:
- Unresolved factual disputes or claims that need verification
- Specific data or statistics that were referenced but not confirmed
- Policy implementation details that citizens asked about
- Comparisons to other jurisdictions or precedents mentioned

Transcript:
{transcript[:3000]}

Return ONLY a JSON array of query strings. Example:
["What is the current cost estimate for implementing UBI in the US?", "How did Finland's UBI pilot program perform?"]

Return between 1 and 3 queries. If no factual questions need researching, return an empty array: []"""

        try:
            response = await llm.complete(
                prompt=prompt,
                system_prompt="You analyze deliberation transcripts and generate research queries. Return only valid JSON.",
                max_tokens=300,
                temperature=0.3
            )

            # Parse JSON from response
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            queries = json.loads(response.strip())
            if isinstance(queries, list):
                return [q for q in queries if isinstance(q, str) and q.strip()]
            return []

        except Exception as e:
            logger.error(f"Failed to generate research queries: {e}")
            return []

    def _build_research_summary(self, results: list[dict], round_num: int) -> str:
        """
        Format research results into readable markdown for context injection.

        Args:
            results: List of research result dicts from Perplexity
            round_num: The round number these results follow

        Returns:
            Formatted markdown string
        """
        lines = [f"## Follow-Up Research (After Round {round_num})\n"]

        for i, result in enumerate(results, 1):
            query = result.get("query", "Unknown query")
            content = result.get("content", "No results available.")
            sources = result.get("sources", [])

            lines.append(f"### Q{i}: {query}\n")
            lines.append(f"{content}\n")

            if sources:
                lines.append("**Sources:**")
                for source in sources[:3]:
                    title = source.get("title", source.get("url", ""))
                    url = source.get("url", "")
                    if url:
                        lines.append(f"- [{title}]({url})")
                    else:
                        lines.append(f"- {title}")
                lines.append("")

        return "\n".join(lines)

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

    def _parse_proposals(self, response: str, citizen_id: int, group_name: str) -> list[dict]:
        """
        Parse policy proposals from a citizen's response.

        Args:
            response: Raw citizen response text
            citizen_id: ID of the citizen who proposed
            group_name: Name of the citizen's group

        Returns:
            List of proposal dicts
        """
        proposals = []
        # Split on PROPOSAL N: pattern
        parts = re.split(r'PROPOSAL\s+\d+\s*:', response)

        for part in parts[1:]:  # Skip text before first PROPOSAL
            lines = part.strip().split('\n', 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else title

            if title:
                proposals.append({
                    "title": title,
                    "description": description,
                    "citizen_id": citizen_id,
                    "group": group_name
                })

        # Fallback: if no proposals were parsed, treat entire response as one
        if not proposals and response.strip():
            proposals.append({
                "title": f"Proposal from citizen {citizen_id}",
                "description": response.strip()[:500],
                "citizen_id": citizen_id,
                "group": group_name
            })

        return proposals

    async def _run_proposal_round(self):
        """
        Run proposal generation and intra-group score voting.

        1. Each group generates proposals (one round of citizen responses)
        2. Intra-group score voting selects top 2 per group
        3. Moderator deduplicates similar proposals across groups
        """
        logger.info("Starting proposal generation round")
        await self._update_status(AssemblyStatus.VOTING, "Proposal generation in progress")

        # Get discussion summary for context
        full_transcript = self._get_full_transcript()
        discussion_summary = await self.recorder.generate_consensus_summary(
            transcript=full_transcript
        )

        all_advancing_proposals = []

        if settings.ENABLE_GROUP_DELIBERATION and len(self.groups) > 0:
            for group in self.groups:
                group_citizens = [c for c in self.citizens if c.group_id == group.id]
                if not group_citizens:
                    continue

                # Moderator opens proposal round for this group
                proposal_prompt = get_moderator_proposal_prompt()
                await self._save_message(
                    role="moderator",
                    content=f"[Group {group.name}] {proposal_prompt}",
                    phase="proposals",
                    group_id=group.id
                )

                # Each citizen proposes 1-2 ideas
                group_proposals = []
                group_context = self._get_group_context(group.id, limit=10)

                for citizen in group_citizens:
                    agent = self.citizen_agents[citizen.id]
                    response = await agent.propose_policies(
                        discussion_context=discussion_summary,
                        group_context=group_context
                    )

                    await self._save_message(
                        role="citizen",
                        content=response,
                        phase="proposals",
                        citizen_id=citizen.id,
                        group_id=group.id
                    )

                    # Parse proposals
                    parsed = self._parse_proposals(response, citizen.id, group.name)
                    group_proposals.extend(parsed)

                # Intra-group score voting — top 2 advance
                if len(group_proposals) > 2:
                    top_proposals = await self._run_group_score_voting(
                        group, group_proposals, discussion_summary
                    )
                else:
                    top_proposals = group_proposals

                all_advancing_proposals.extend(top_proposals)

                if self.broadcast:
                    await self.broadcast(self.assembly_id, {
                        "type": "group_proposals_complete",
                        "group": group.name,
                        "num_proposals": len(top_proposals)
                    })
        else:
            # No groups: all citizens propose together
            proposal_prompt = get_moderator_proposal_prompt()
            await self._save_message(
                role="moderator",
                content=proposal_prompt,
                phase="proposals"
            )

            context = self._get_recent_context(limit=10)
            for citizen in self.citizens:
                agent = self.citizen_agents[citizen.id]
                response = await agent.propose_policies(
                    discussion_context=discussion_summary,
                    group_context=context
                )

                await self._save_message(
                    role="citizen",
                    content=response,
                    phase="proposals",
                    citizen_id=citizen.id
                )

                parsed = self._parse_proposals(response, citizen.id, "All")
                all_advancing_proposals.extend(parsed)

            # If many proposals, do intra-assembly score voting to trim
            if len(all_advancing_proposals) > 6:
                all_advancing_proposals = await self._run_group_score_voting(
                    None, all_advancing_proposals, discussion_summary, top_n=6
                )

        logger.info(f"Total advancing proposals: {len(all_advancing_proposals)}")

        # Moderator deduplication
        if len(all_advancing_proposals) > 1:
            self.deduplicated_proposals = await self._run_moderator_deduplication(
                all_advancing_proposals
            )
        else:
            self.deduplicated_proposals = all_advancing_proposals

        self.discussion_summary = discussion_summary

        logger.info(f"Deduplicated to {len(self.deduplicated_proposals)} proposals")

        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "proposals_ready",
                "num_proposals": len(self.deduplicated_proposals)
            })

    async def _run_group_score_voting(
        self,
        group: Optional[DeliberationGroup],
        proposals: list[dict],
        discussion_summary: str,
        top_n: int = 2
    ) -> list[dict]:
        """
        Run intra-group score voting to select top proposals.

        Args:
            group: The group (or None for all citizens)
            proposals: List of proposal dicts to vote on
            discussion_summary: Discussion summary for context
            top_n: Number of top proposals to advance

        Returns:
            Top-scoring proposals
        """
        if group:
            voters = [c for c in self.citizens if c.group_id == group.id]
            group_label = f"Group {group.name}"
        else:
            voters = list(self.citizens)
            group_label = "Assembly"

        # Collect scores from each voter
        all_scores = {i: [] for i in range(len(proposals))}

        for citizen in voters:
            agent = self.citizen_agents[citizen.id]
            scores = await agent.score_vote(proposals, discussion_summary)

            # Build score message for the chat
            score_lines = []
            for idx in range(len(proposals)):
                score = scores.get(idx, 3)
                all_scores[idx].append(score)
                score_lines.append(f"{idx+1}. {proposals[idx]['title']}: {score}/5")

            await self._save_message(
                role="citizen",
                content=f"[{group_label} Intra-Group Vote]\nSCORES:\n" + "\n".join(score_lines),
                phase="proposals",
                citizen_id=citizen.id,
                group_id=group.id if group else None
            )

        # Calculate averages
        avg_scores = {}
        for idx, score_list in all_scores.items():
            if score_list:
                avg_scores[idx] = sum(score_list) / len(score_list)
            else:
                avg_scores[idx] = 0

        # Sort by average score, take top N
        sorted_indices = sorted(avg_scores, key=avg_scores.get, reverse=True)
        top_indices = sorted_indices[:top_n]

        top_proposals = []
        for idx in top_indices:
            proposal = proposals[idx].copy()
            proposal["group_avg_score"] = round(avg_scores[idx], 2)
            top_proposals.append(proposal)

        logger.info(f"{group_label} top {top_n} proposals selected (scores: {[p['group_avg_score'] for p in top_proposals]})")
        return top_proposals

    async def _run_moderator_deduplication(self, proposals: list[dict]) -> list[dict]:
        """
        Have the moderator deduplicate similar proposals.

        Args:
            proposals: All advancing proposals from groups

        Returns:
            Deduplicated proposal list
        """
        logger.info(f"Moderator deduplicating {len(proposals)} proposals")

        deduplicated = await self.moderator.deduplicate_proposals(
            proposals=proposals,
            topic=self.assembly.topic
        )

        # Save deduplication message
        original_titles = [p["title"] for p in proposals]
        dedup_titles = [p["title"] for p in deduplicated]

        dedup_msg = f"After reviewing all {len(proposals)} advancing proposals, "
        if len(deduplicated) < len(proposals):
            dedup_msg += f"I've consolidated them into {len(deduplicated)} distinct proposals by merging similar ideas:\n\n"
        else:
            dedup_msg += f"all {len(deduplicated)} proposals are sufficiently distinct:\n\n"

        for i, p in enumerate(deduplicated, 1):
            dedup_msg += f"{i}. **{p['title']}**: {p['description']}\n"

        await self._save_message(
            role="moderator",
            content=dedup_msg,
            phase="proposals"
        )

        return deduplicated

    async def _run_assembly_score_voting(self):
        """
        Run assembly-wide score voting on deduplicated proposals.

        Every citizen scores each proposal 1-5. Proposals averaging >3 pass.
        Results stored in self.proposal_scores for report generation.
        """
        logger.info("Starting assembly-wide score voting")

        proposals = self.deduplicated_proposals
        discussion_summary = self.discussion_summary

        # Moderator transition
        transition_text = get_moderator_score_voting_transition()
        proposals_text = "\n".join([
            f"{i+1}. **{p['title']}**: {p['description']}"
            for i, p in enumerate(proposals)
        ])
        await self._save_message(
            role="moderator",
            content=f"{transition_text}\n\nProposals to score:\n{proposals_text}",
            phase="voting"
        )

        # Collect scores from ALL citizens
        all_scores = {i: [] for i in range(len(proposals))}

        for citizen in self.citizens:
            agent = self.citizen_agents[citizen.id]
            scores = await agent.score_vote(proposals, discussion_summary)

            # Build score message
            score_lines = []
            for idx in range(len(proposals)):
                score = scores.get(idx, 3)
                all_scores[idx].append(score)
                score_lines.append(f"{idx+1}. {proposals[idx]['title']}: {score}/5")

            await self._save_message(
                role="citizen",
                content=f"SCORES:\n" + "\n".join(score_lines),
                phase="voting",
                citizen_id=citizen.id
            )

            if self.broadcast:
                await self.broadcast(self.assembly_id, {
                    "type": "vote_cast",
                    "citizen": citizen.name,
                    "progress": f"{self.citizens.index(citizen)+1}/{len(self.citizens)}"
                })

        self.db.commit()

        # Calculate results
        self.proposal_scores = []
        passing_proposals = []

        for idx in range(len(proposals)):
            scores_list = all_scores[idx]
            avg = sum(scores_list) / len(scores_list) if scores_list else 0
            passed = avg > 3

            score_entry = {
                "title": proposals[idx]["title"],
                "description": proposals[idx]["description"],
                "avg_score": round(avg, 2),
                "num_votes": len(scores_list),
                "passed": passed
            }
            self.proposal_scores.append(score_entry)

            if passed:
                passing_proposals.append(score_entry)

        self.passing_proposals = passing_proposals

        logger.info(
            f"Score voting complete: {len(passing_proposals)}/{len(proposals)} proposals passed (>3.0 avg)"
        )

        # Moderator closing with results
        full_transcript = self._get_full_transcript()
        themes = await self.recorder.identify_themes(full_transcript)

        results_text = "Score voting results:\n\n"
        for ps in self.proposal_scores:
            status = "PASSED" if ps["passed"] else "did not pass"
            results_text += f"- **{ps['title']}**: avg score {ps['avg_score']}/5 ({status})\n"

        closing = await self.moderator.close_assembly(
            vote_results={
                "total_proposals": len(proposals),
                "passed": len(passing_proposals),
                "failed": len(proposals) - len(passing_proposals)
            },
            key_themes=themes
        )

        await self._save_message(
            role="moderator",
            content=f"{results_text}\n\n{closing}",
            phase="closing"
        )

        logger.info("Assembly-wide score voting complete")

    async def _generate_report(self):
        """Generate the final assembly report using scored proposals."""
        logger.info("Generating final report")

        full_transcript = self._get_full_transcript()

        # Build recommendations from passing proposals
        recommendations = []
        for ps in self.passing_proposals:
            recommendations.append({
                "title": ps["title"],
                "description": ps["description"],
                "avg_score": ps["avg_score"],
                "support_level": "strong" if ps["avg_score"] >= 4.0 else "moderate"
            })

        # Build vote tally summary for backward compat
        vote_tally = {
            "total_proposals": len(self.proposal_scores),
            "passed": len(self.passing_proposals),
            "failed": len(self.proposal_scores) - len(self.passing_proposals),
            "total_voters": len(self.citizens)
        }

        # Generate all report components
        report_data = await self.recorder.generate_final_summary(
            full_transcript=full_transcript,
            vote_results=vote_tally,
            recommendations=recommendations
        )

        # Save to database
        report = Report(
            assembly_id=self.assembly_id,
            executive_summary=report_data["executive_summary"],
            recommendations=recommendations,
            vote_tally=vote_tally,
            proposal_scores=self.proposal_scores,
            minority_report=report_data["minority_report"],
            key_themes=report_data["key_themes"]
        )

        self.db.add(report)
        self.db.commit()

        logger.info("Report generated and saved")

        if self.broadcast:
            await self.broadcast(self.assembly_id, {
                "type": "report_ready",
                "vote_tally": vote_tally,
                "proposal_scores": self.proposal_scores,
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

    def _get_full_transcript(self, max_chars: int = 80000) -> str:
        """Get the deliberation transcript, truncated to fit model context windows.

        With 40 citizens x 3 rounds the full transcript can easily exceed
        100k+ characters.  We keep the first and last portions (most useful
        for report generation) and replace the middle with a marker.

        Args:
            max_chars: Maximum character length for the returned transcript.
                       Defaults to 80 000 (~20k tokens), safely within most
                       model context windows when combined with other prompt text.
        """
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

        full = "\n\n".join(lines)

        if len(full) <= max_chars:
            return full

        # Keep first 60% and last 40% of the budget (opening rounds + final voting
        # are most important for report generation)
        head_budget = int(max_chars * 0.6)
        tail_budget = max_chars - head_budget - 200  # 200 chars for the marker
        omitted = len(full) - head_budget - tail_budget

        logger.warning(
            f"Transcript truncated: {len(full)} chars -> {max_chars} chars "
            f"({omitted} chars omitted from middle)"
        )

        return (
            full[:head_budget]
            + f"\n\n[... {omitted:,} characters omitted for brevity ...]\n\n"
            + full[-tail_budget:]
        )

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
