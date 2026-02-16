"""
Citizen Agent Module

Defines the CitizenAgent class that represents a citizen participant
in the deliberative assembly. Each agent has a persona derived from
GSS data and can respond to deliberation prompts.
"""

import logging
from typing import Optional

from app.llm_client import get_llm_client
from app.config import get_settings
from app.prompt_loader import (
    get_citizen_instructions, get_citizen_citation_instructions,
    get_citizen_proposal_instructions, get_citizen_score_vote_instructions
)
from app.agents.stubbornness import calculate_stubbornness, get_stubbornness_instruction

logger = logging.getLogger(__name__)
settings = get_settings()


class CitizenAgent:
    """
    An AI agent representing a citizen in the assembly.

    Combines a persona (from GSS data) with deliberation context
    (briefing book, discussion history) to generate authentic responses.
    """

    # Deliberation instructions now loaded from prompts.yaml via get_citizen_instructions()

    def __init__(
        self,
        citizen_id: int,
        name: str,
        system_prompt: str,
        background_summary: Optional[str] = None,
        key_values: Optional[list[str]] = None,
        briefing_content: Optional[str] = None
    ):
        """
        Initialize a citizen agent.

        Args:
            citizen_id: Database ID of the citizen
            name: The citizen's name
            system_prompt: The persona system prompt from generation
            background_summary: Brief background for display
            key_values: List of core values
            briefing_content: Briefing book content for this assembly
        """
        self.citizen_id = citizen_id
        self.name = name
        self.background_summary = background_summary
        self.key_values = key_values or []

        # Build the full system prompt
        self._base_system_prompt = system_prompt
        self._briefing_content = briefing_content
        self._full_system_prompt = self._build_full_system_prompt()

        # Get LLM client configured for citizen responses
        self.llm = get_llm_client(purpose="citizen")

    def _build_full_system_prompt(self) -> str:
        """Build the complete system prompt including briefing and instructions."""
        prompt = self._base_system_prompt

        # Add briefing context if available
        if self._briefing_content:
            prompt += f"""

BRIEFING MATERIALS:
The following research has been provided to inform your deliberation:

{self._briefing_content[:4000]}

You may reference these materials in your responses."""

            # Add citation instructions if enabled
            if settings.ENABLE_CITATIONS:
                prompt += get_citizen_citation_instructions()

        # Add deliberation instructions
        prompt += get_citizen_instructions()

        return prompt

    def update_briefing(self, briefing_content: str):
        """Update the briefing content and rebuild system prompt."""
        self._briefing_content = briefing_content
        self._full_system_prompt = self._build_full_system_prompt()

    async def respond(
        self,
        discussion_context: str,
        prompt: Optional[str] = None,
        round_number: int = 1,
        total_rounds: int = 3
    ) -> str:
        """
        Generate a response in the deliberation.

        Args:
            discussion_context: Recent discussion messages for context
            prompt: Optional specific prompt (e.g., from moderator)
            round_number: Current round number (1-indexed)
            total_rounds: Total number of rounds in deliberation

        Returns:
            The citizen's response text
        """
        # Build the user message
        user_message = f"""DISCUSSION SO FAR:
{discussion_context}

"""
        # Add stubbornness instruction if enabled
        if settings.ENABLE_STUBBORNNESS:
            stubbornness = calculate_stubbornness(
                citizen_values=self.key_values,
                political_leaning=None,
                round_number=round_number,
                total_rounds=total_rounds
            )
            stubbornness_instruction = get_stubbornness_instruction(
                stubbornness, round_number
            )
            user_message += f"{stubbornness_instruction}\n\n"

        if prompt:
            user_message += f"""THE MODERATOR ASKS: {prompt}

Please share your thoughts."""
        else:
            user_message += "Please share your perspective on the current discussion."

        try:
            response = await self.llm.complete(
                prompt=user_message,
                system_prompt=self._full_system_prompt,
                max_tokens=500
            )
            return response

        except Exception as e:
            logger.error(f"Error generating citizen response: {e}")
            return f"[{self.name} is gathering their thoughts...]"

    async def respond_to_plenary(
        self,
        group_summaries: list[dict],
        own_group: str
    ) -> str:
        """
        Respond during the plenary phase as a group representative.

        Args:
            group_summaries: List of dicts with group name and summary
            own_group: Name of this citizen's group

        Returns:
            The citizen's plenary response
        """
        # Format group summaries
        summaries_text = "\n\n".join([
            f"GROUP {gs['group']}:\n{gs.get('summary', {}).get('consensus', 'No summary available')}"
            for gs in group_summaries
        ])

        user_message = f"""You are representing Group {own_group} in the plenary session.

SUMMARIES FROM ALL GROUPS:
{summaries_text}

As a representative of your group, share:
1. The key insights or positions from your group's discussion
2. How your group's perspective relates to or differs from other groups
3. Any points of potential common ground you see across groups

Keep your response focused (2-3 paragraphs)."""

        try:
            response = await self.llm.complete(
                prompt=user_message,
                system_prompt=self._full_system_prompt,
                max_tokens=400
            )
            return response

        except Exception as e:
            logger.error(f"Error generating plenary response: {e}")
            return f"[{self.name} shares their group's perspective...]"

    async def respond_to_question(
        self,
        question: str,
        discussion_context: Optional[str] = None
    ) -> str:
        """
        Respond to a direct question from another citizen or moderator.

        Args:
            question: The question being asked
            discussion_context: Optional recent discussion for context

        Returns:
            The citizen's response
        """
        user_message = f"""Someone has asked you directly: "{question}"

"""
        if discussion_context:
            user_message = f"""RECENT DISCUSSION:
{discussion_context}

{user_message}"""

        user_message += "Please respond to this question based on your values and perspective."

        try:
            response = await self.llm.complete(
                prompt=user_message,
                system_prompt=self._full_system_prompt,
                max_tokens=400
            )
            return response

        except Exception as e:
            logger.error(f"Error generating question response: {e}")
            return f"[{self.name} considers the question...]"

    async def cast_vote(
        self,
        recommendations: list[dict],
        discussion_summary: Optional[str] = None
    ) -> dict:
        """
        Cast a vote on the assembly's recommendations.

        Args:
            recommendations: List of recommendation dicts with title and description
            discussion_summary: Summary of the full deliberation

        Returns:
            Dict with vote, reasoning, and confidence
        """
        # Format recommendations
        rec_text = "\n".join([
            f"{i+1}. {rec.get('title', 'Recommendation')}: {rec.get('description', '')}"
            for i, rec in enumerate(recommendations)
        ])

        user_message = f"""The deliberation is complete. Based on your values, the discussion, and the evidence presented, please cast your vote.

RECOMMENDATIONS TO VOTE ON:
{rec_text}

"""
        if discussion_summary:
            user_message += f"""SUMMARY OF DELIBERATION:
{discussion_summary}

"""

        user_message += """Please provide your vote in this format:
VOTE: [support / oppose / abstain]
REASONING: [2-3 sentences explaining your decision]
CONFIDENCE: [high / medium / low]

Base your vote on your authentic values and what you learned during deliberation."""

        try:
            response = await self.llm.complete(
                prompt=user_message,
                system_prompt=self._full_system_prompt,
                max_tokens=300
            )

            # Parse the response
            return self._parse_vote_response(response)

        except Exception as e:
            logger.error(f"Error casting vote: {e}")
            return {
                "vote": "abstain",
                "reasoning": "Unable to reach a decision at this time.",
                "confidence": "low"
            }

    async def propose_policies(
        self,
        discussion_context: str,
        group_context: str
    ) -> str:
        """
        Generate 1-2 policy proposals based on the deliberation.

        Args:
            discussion_context: Full deliberation context
            group_context: Recent group discussion context

        Returns:
            Raw response text containing proposals in structured format
        """
        instructions = get_citizen_proposal_instructions()

        user_message = f"""DELIBERATION CONTEXT:
{discussion_context}

RECENT GROUP DISCUSSION:
{group_context}

{instructions}

Based on your values and what you've learned during this deliberation, propose 1-2 specific policy proposals."""

        try:
            response = await self.llm.complete(
                prompt=user_message,
                system_prompt=self._full_system_prompt,
                max_tokens=500
            )
            return response

        except Exception as e:
            logger.error(f"Error generating proposals: {e}")
            return f"PROPOSAL 1: {self.name}'s Recommendation\nBased on the deliberation, I recommend further study and balanced policy action on this topic."

    async def score_vote(
        self,
        proposals: list[dict],
        discussion_summary: str
    ) -> dict:
        """
        Score each proposal on a scale of 1-5.

        Args:
            proposals: List of proposal dicts with 'title' and 'description'
            discussion_summary: Summary of the full deliberation

        Returns:
            Dict mapping proposal index to score (1-5)
        """
        instructions = get_citizen_score_vote_instructions()

        # Format proposals
        proposals_text = "\n".join([
            f"{i+1}. {p['title']}: {p['description']}"
            for i, p in enumerate(proposals)
        ])

        user_message = f"""DELIBERATION SUMMARY:
{discussion_summary}

PROPOSALS TO SCORE:
{proposals_text}

{instructions}

Score each proposal based on your values and what you learned during deliberation."""

        try:
            response = await self.llm.complete(
                prompt=user_message,
                system_prompt=self._full_system_prompt,
                max_tokens=400
            )
            return self._parse_score_response(response, len(proposals))

        except Exception as e:
            logger.error(f"Error scoring proposals: {e}")
            # Default to neutral scores
            return {i: 3 for i in range(len(proposals))}

    def _parse_score_response(self, response: str, num_proposals: int) -> dict:
        """Parse score voting response into {index: score} dict."""
        import re
        scores = {}

        # Look for patterns like "1. title: 4" or "1. 4" or "title: 4/5"
        lines = response.split("\n")
        for line in lines:
            # Match numbered lines with scores
            match = re.match(r'\s*(\d+)\.\s*.*?:\s*(\d)', line)
            if match:
                idx = int(match.group(1)) - 1  # Convert to 0-indexed
                score = int(match.group(2))
                if 0 <= idx < num_proposals and 1 <= score <= 5:
                    scores[idx] = score

        # Fill in missing scores with neutral (3)
        for i in range(num_proposals):
            if i not in scores:
                scores[i] = 3

        return scores

    def _parse_vote_response(self, response: str) -> dict:
        """Parse the vote response into structured format."""
        result = {
            "vote": "abstain",
            "reasoning": "",
            "confidence": "medium"
        }

        response_lower = response.lower()

        # Extract vote
        if "vote:" in response_lower:
            vote_line = response_lower.split("vote:")[1].split("\n")[0].strip()
            if "support" in vote_line:
                result["vote"] = "support"
            elif "oppose" in vote_line:
                result["vote"] = "oppose"
            elif "abstain" in vote_line:
                result["vote"] = "abstain"

        # Extract reasoning
        if "reasoning:" in response_lower:
            parts = response.split("REASONING:")
            if len(parts) > 1:
                reasoning = parts[1]
                if "CONFIDENCE:" in reasoning:
                    reasoning = reasoning.split("CONFIDENCE:")[0]
                result["reasoning"] = reasoning.strip()

        # Extract confidence
        if "confidence:" in response_lower:
            conf_line = response_lower.split("confidence:")[1].split("\n")[0].strip()
            if "high" in conf_line:
                result["confidence"] = "high"
            elif "low" in conf_line:
                result["confidence"] = "low"
            else:
                result["confidence"] = "medium"

        # If parsing failed, use full response as reasoning
        if not result["reasoning"]:
            result["reasoning"] = response[:500]

        return result

    def __repr__(self):
        return f"<CitizenAgent(id={self.citizen_id}, name='{self.name}')>"


def create_citizen_agent_from_db(citizen, briefing_content: Optional[str] = None) -> CitizenAgent:
    """
    Factory function to create a CitizenAgent from a database Citizen model.

    Args:
        citizen: Database Citizen model instance
        briefing_content: Optional briefing book content

    Returns:
        Configured CitizenAgent instance
    """
    return CitizenAgent(
        citizen_id=citizen.id,
        name=citizen.name,
        system_prompt=citizen.system_prompt,
        background_summary=citizen.background_summary,
        key_values=citizen.key_values,
        briefing_content=briefing_content
    )
