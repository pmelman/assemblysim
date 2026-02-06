"""
Moderator Agent Module

Defines the ModeratorAgent class that facilitates deliberation,
guides discussion, and ensures productive dialogue.
"""

import logging
from typing import Optional

from app.llm_client import get_llm_client
from app.prompt_loader import get_moderator_prompt

logger = logging.getLogger(__name__)


class ModeratorAgent:
    """
    An AI agent that moderates the deliberation process.

    Responsibilities:
    - Opening and closing rounds
    - Prompting specific citizens to speak
    - Asking follow-up questions
    - Synthesizing discussion points
    - Managing time and focus
    """

    # System prompt now loaded from prompts.yaml via get_moderator_prompt()

    def __init__(self, assembly_topic: str):
        """
        Initialize the moderator agent.

        Args:
            assembly_topic: The policy topic being deliberated
        """
        self.topic = assembly_topic
        self.system_prompt = get_moderator_prompt()
        self.llm = get_llm_client(purpose="moderator")

    async def open_assembly(self, citizen_names: list[str]) -> str:
        """
        Generate the opening statement for the assembly.

        Args:
            citizen_names: Names of participating citizens

        Returns:
            Opening statement text
        """
        prompt = f"""You are opening a citizens' deliberative assembly on the topic:

"{self.topic}"

There are {len(citizen_names)} citizens participating. Welcome them warmly, explain the purpose of deliberation, and set expectations for respectful dialogue.

Keep your opening to 2-3 paragraphs. End by introducing the topic and inviting initial thoughts."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=400
            )
            return response

        except Exception as e:
            logger.error(f"Error generating opening: {e}")
            return f"""Welcome, everyone, to today's Citizens' Assembly.

We're here to deliberate on an important topic: {self.topic}

Over the course of our discussion, you'll have the opportunity to share your perspectives, listen to others, and work together toward understanding this complex issue. Remember, the goal isn't necessarily to reach consensus, but to engage thoughtfully with different viewpoints.

Let's begin. Who would like to share their initial thoughts?"""

    async def open_round(
        self,
        round_number: int,
        citizen_names: list[str],
        previous_summary: Optional[str] = None
    ) -> str:
        """
        Generate the opening for a new deliberation round.

        Args:
            round_number: Current round number (1-indexed)
            citizen_names: Names of citizens in this group
            previous_summary: Summary of previous round if applicable

        Returns:
            Round opening statement
        """
        prompt = f"""You are opening Round {round_number} of deliberation on:

"{self.topic}"

Citizens in this group: {', '.join(citizen_names)}
"""

        if previous_summary:
            prompt += f"""
Summary of previous discussion:
{previous_summary}

Acknowledge the progress made and introduce the focus for this round.
"""
        else:
            prompt += "\nThis is the first round. Introduce the topic and invite initial perspectives.\n"

        prompt += "\nKeep your opening to 1-2 paragraphs."

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=300
            )
            return response

        except Exception as e:
            logger.error(f"Error generating round opening: {e}")
            return f"Let's begin Round {round_number} of our deliberation. Who would like to start?"

    async def prompt_citizen(
        self,
        citizen_name: str,
        context: Optional[str] = None,
        focus_area: Optional[str] = None
    ) -> str:
        """
        Generate a prompt to invite a specific citizen to speak.

        Args:
            citizen_name: Name of the citizen to prompt
            context: Recent discussion context
            focus_area: Specific area to focus on (optional)

        Returns:
            Prompt for the citizen
        """
        prompt = f"""You need to invite {citizen_name} to share their thoughts.

Topic: {self.topic}
"""

        if context:
            prompt += f"""
Recent discussion:
{context}
"""

        if focus_area:
            prompt += f"\nFocus area: {focus_area}\n"

        prompt += """
Generate a brief, natural prompt inviting this citizen to contribute.
Keep it to 1-2 sentences. You might:
- Ask them to share their perspective
- Follow up on something said earlier
- Invite them to respond to a specific point
- Ask about their experience or values related to the topic"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=100
            )
            return response

        except Exception as e:
            logger.error(f"Error generating citizen prompt: {e}")
            return f"{citizen_name}, we'd love to hear your thoughts. What's your perspective?"

    async def ask_followup(
        self,
        last_speaker: str,
        last_statement: str,
        discussion_context: Optional[str] = None
    ) -> str:
        """
        Generate a follow-up question to deepen discussion.

        Args:
            last_speaker: Name of the last speaker
            last_statement: What they said
            discussion_context: Broader discussion context

        Returns:
            Follow-up question
        """
        prompt = f"""{last_speaker} just said:
"{last_statement}"

Topic: {self.topic}
"""

        if discussion_context:
            prompt += f"""
Discussion context:
{discussion_context}
"""

        prompt += """
Generate a thoughtful follow-up question to deepen the discussion.
This could:
- Ask for clarification or examples
- Explore underlying values or reasoning
- Connect to something said earlier
- Invite others to respond

Keep it to 1-2 sentences."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=100
            )
            return response

        except Exception as e:
            logger.error(f"Error generating followup: {e}")
            return "That's an interesting point. Would anyone like to respond or add to that?"

    async def present_plenary_synthesis(
        self,
        group_summaries: list[dict],
        topic: str
    ) -> str:
        """
        Present a synthesis of all group discussions in the plenary phase.

        Args:
            group_summaries: List of dicts with group name and summary
            topic: The assembly topic

        Returns:
            Plenary synthesis statement
        """
        # Format group summaries
        summaries_text = ""
        for gs in group_summaries:
            group_name = gs.get("group", "Unknown")
            summary = gs.get("summary", {})
            consensus = summary.get("consensus", "No consensus recorded")
            disagreements = summary.get("disagreements", "No disagreements recorded")

            summaries_text += f"""
GROUP {group_name}:
Consensus: {consensus[:300]}...
Key Disagreements: {disagreements[:200]}...
"""

        prompt = f"""Present a plenary synthesis to the full assembly.

Topic: {topic}

GROUP SUMMARIES:
{summaries_text}

Generate a synthesis (2-3 paragraphs) that:
1. Welcomes everyone to the plenary session
2. Highlights themes that emerged across multiple groups
3. Notes interesting differences between groups
4. Identifies potential areas of assembly-wide consensus
5. Prepares participants to hear from group representatives

Be neutral and inclusive of all perspectives."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=500
            )
            return response

        except Exception as e:
            logger.error(f"Error generating plenary synthesis: {e}")
            return f"""Welcome to the plenary session. We've heard thoughtful discussions from all groups on {topic}.

Now we'll hear from representatives of each group before moving to the voting phase. Let's explore what emerged from our small group deliberations."""

    async def synthesize_discussion(
        self,
        discussion_transcript: str,
        round_number: Optional[int] = None
    ) -> str:
        """
        Synthesize the key points from a discussion segment.

        Args:
            discussion_transcript: The discussion to synthesize
            round_number: Current round number if applicable

        Returns:
            Synthesis of key points
        """
        prompt = f"""Synthesize the following deliberation discussion:

{discussion_transcript}

Provide a brief summary (2-3 paragraphs) that:
1. Identifies the main points raised
2. Notes areas of agreement
3. Acknowledges areas of disagreement or tension
4. Does NOT take sides or express preference

Be neutral and comprehensive."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=400
            )
            return response

        except Exception as e:
            logger.error(f"Error generating synthesis: {e}")
            return "The discussion covered multiple perspectives on this topic."

    async def transition_to_voting(
        self,
        discussion_summary: str,
        recommendations: list[dict]
    ) -> str:
        """
        Generate the transition statement to the voting phase.

        Args:
            discussion_summary: Summary of the full deliberation
            recommendations: List of recommendation dicts

        Returns:
            Transition statement
        """
        rec_text = "\n".join([
            f"- {rec.get('title', 'Recommendation')}: {rec.get('description', '')}"
            for rec in recommendations
        ])

        prompt = f"""The deliberation is complete. Transition to the voting phase.

Topic: {self.topic}

Discussion Summary:
{discussion_summary}

Recommendations to vote on:
{rec_text}

Generate a brief transition statement (2 paragraphs) that:
1. Thanks participants for their thoughtful contributions
2. Summarizes the key insights from deliberation
3. Introduces the voting process
4. Reminds participants to vote based on their values and what they learned"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=400
            )
            return response

        except Exception as e:
            logger.error(f"Error generating voting transition: {e}")
            return f"""Thank you all for this thoughtful deliberation on {self.topic}.

We've heard many perspectives and explored the issue deeply. Now it's time to cast your votes on the recommendations. Please vote based on your values and what you've learned during our discussion."""

    async def close_assembly(
        self,
        vote_results: dict,
        key_themes: list[str]
    ) -> str:
        """
        Generate the closing statement for the assembly.

        Args:
            vote_results: Dict with vote tallies
            key_themes: Key themes from the deliberation

        Returns:
            Closing statement
        """
        themes_text = ", ".join(key_themes) if key_themes else "various important considerations"

        prompt = f"""Close the citizens' assembly with final remarks.

Topic: {self.topic}

Vote Results:
- Support: {vote_results.get('support', 0)}
- Oppose: {vote_results.get('oppose', 0)}
- Abstain: {vote_results.get('abstain', 0)}

Key Themes Discussed: {themes_text}

Generate a brief closing (2 paragraphs) that:
1. Thanks participants for their engagement
2. Acknowledges the range of perspectives shared
3. Notes the value of deliberation regardless of outcome
4. Expresses hope for continued civic engagement"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=300
            )
            return response

        except Exception as e:
            logger.error(f"Error generating closing: {e}")
            return f"""Thank you all for participating in this Citizens' Assembly on {self.topic}.

Your thoughtful engagement with this important issue demonstrates the value of deliberative democracy. Regardless of the vote outcome, the perspectives shared here contribute to our collective understanding."""

    def __repr__(self):
        return f"<ModeratorAgent(topic='{self.topic[:30]}...')>"
