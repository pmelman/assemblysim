"""
Recorder Agent Module

Defines the RecorderAgent class that captures, summarizes, and
analyzes deliberation content for the final report.
"""

import logging
from typing import Optional

from app.llm_client import get_llm_client
from app.prompt_loader import get_recorder_prompt

logger = logging.getLogger(__name__)


class RecorderAgent:
    """
    An AI agent that records and summarizes deliberation.

    Responsibilities:
    - Summarizing each round of discussion
    - Identifying key themes and arguments
    - Tracking areas of agreement and disagreement
    - Generating the final assembly report
    """

    # System prompt now loaded from prompts.yaml via get_recorder_prompt()

    def __init__(self, assembly_topic: str):
        """
        Initialize the recorder agent.

        Args:
            assembly_topic: The policy topic being deliberated
        """
        self.topic = assembly_topic
        self.system_prompt = get_recorder_prompt()
        self.llm = get_llm_client(purpose="utility")
        self._round_summaries: list[str] = []

    async def summarize_round(
        self,
        transcript: str,
        round_number: int,
        group_name: Optional[str] = None
    ) -> str:
        """
        Generate a summary of a deliberation round.

        Args:
            transcript: The full round transcript
            round_number: The round number (1-indexed)
            group_name: Name of the deliberation group if applicable

        Returns:
            Round summary text
        """
        group_context = f" (Group {group_name})" if group_name else ""

        prompt = f"""Summarize Round {round_number}{group_context} of deliberation on:

"{self.topic}"

TRANSCRIPT:
{transcript}

Provide a summary (2-3 paragraphs) that:
1. Captures the main points raised
2. Notes key arguments and evidence cited
3. Identifies areas of agreement and disagreement
4. Highlights particularly insightful contributions

Be concise but comprehensive. Do not include your own opinions."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=500
            )

            # Store for later use
            self._round_summaries.append({
                "round": round_number,
                "group": group_name,
                "summary": response
            })

            return response

        except Exception as e:
            logger.error(f"Error generating round summary: {e}")
            return f"Round {round_number} covered various perspectives on the topic."

    async def identify_themes(
        self,
        full_transcript: str
    ) -> list[str]:
        """
        Identify key themes from the deliberation.

        Args:
            full_transcript: Complete deliberation transcript

        Returns:
            List of key theme strings
        """
        prompt = f"""Analyze this deliberation and identify the key themes:

TOPIC: {self.topic}

TRANSCRIPT:
{full_transcript}

List 5-8 key themes that emerged during the discussion.
Format as a simple list, one theme per line.
Themes should be concise (3-7 words each)."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=300
            )

            # Parse the response into a list
            themes = []
            for line in response.strip().split("\n"):
                # Clean up the line
                theme = line.strip()
                # Remove list markers
                for prefix in ["- ", "• ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. "]:
                    if theme.startswith(prefix):
                        theme = theme[len(prefix):]
                if theme:
                    themes.append(theme)

            return themes[:8]  # Cap at 8 themes

        except Exception as e:
            logger.error(f"Error identifying themes: {e}")
            return ["Policy considerations", "Economic implications", "Social impact"]

    async def generate_consensus_summary(
        self,
        transcript: str,
        vote_results: Optional[dict] = None
    ) -> str:
        """
        Generate a summary of areas where consensus was reached.

        Args:
            transcript: The deliberation transcript
            vote_results: Optional vote tally

        Returns:
            Consensus summary text
        """
        vote_context = ""
        if vote_results:
            vote_context = f"""
Vote Results:
- Support: {vote_results.get('support', 0)}
- Oppose: {vote_results.get('oppose', 0)}
- Abstain: {vote_results.get('abstain', 0)}
"""

        prompt = f"""Identify areas of consensus from this deliberation:

TOPIC: {self.topic}
{vote_context}

TRANSCRIPT:
{transcript}

Write a summary (2-3 paragraphs) focusing on:
1. Points where most participants agreed
2. Shared values or concerns across different viewpoints
3. Common ground that emerged during discussion

Focus on genuine consensus, not just majority views."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=400
            )
            return response

        except Exception as e:
            logger.error(f"Error generating consensus summary: {e}")
            return "Areas of consensus were explored during the deliberation."

    async def generate_disagreements_summary(
        self,
        transcript: str
    ) -> str:
        """
        Generate a summary of areas of disagreement.

        Args:
            transcript: The deliberation transcript

        Returns:
            Disagreements summary text
        """
        prompt = f"""Identify areas of disagreement from this deliberation:

TOPIC: {self.topic}

TRANSCRIPT:
{transcript}

Write a summary (2-3 paragraphs) focusing on:
1. Key points of contention
2. Different values or priorities that led to disagreement
3. Specific proposals or aspects that divided participants

Present all sides fairly without taking a position."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=400
            )
            return response

        except Exception as e:
            logger.error(f"Error generating disagreements summary: {e}")
            return "Various points of disagreement were discussed during the deliberation."

    async def generate_minority_report(
        self,
        transcript: str,
        vote_results: dict
    ) -> str:
        """
        Generate a minority report capturing dissenting views.

        Args:
            transcript: The deliberation transcript
            vote_results: Vote tally dict

        Returns:
            Minority report text
        """
        # Build vote context for both old and new formats
        if 'total_proposals' in vote_results:
            # New score-voting format
            vote_text = (
                f"Proposals scored: {vote_results.get('total_proposals', 0)}, "
                f"Passed: {vote_results.get('passed', 0)}, "
                f"Did not pass: {vote_results.get('failed', 0)}"
            )
            minority_context = "proposals that did not pass or perspectives not fully represented in the passing proposals"
        else:
            # Legacy format
            support = vote_results.get("support", 0)
            oppose = vote_results.get("oppose", 0)
            vote_text = f"Support: {support}, Oppose: {oppose}, Abstain: {vote_results.get('abstain', 0)}"
            minority_context = "opposition" if support > oppose else "support"

        prompt = f"""Generate a minority report for this deliberation:

TOPIC: {self.topic}

Vote Results: {vote_text}

The minority perspective includes: {minority_context}

TRANSCRIPT:
{transcript}

Write a minority report (2-3 paragraphs) that:
1. Fairly represents perspectives that were not fully captured in the passing proposals
2. Captures minority arguments, concerns, and low-scoring proposals
3. Notes the values and reasoning behind dissenting positions
4. Respects these perspectives without dismissing them

This should give voice to those whose views were not fully represented in the final recommendations."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=500
            )
            return response

        except Exception as e:
            logger.error(f"Error generating minority report: {e}")
            return "The minority perspective was represented in the deliberation."

    async def generate_executive_summary(
        self,
        full_transcript: str,
        vote_results: dict,
        recommendations: list[dict],
        themes: list[str]
    ) -> str:
        """
        Generate the executive summary for the final report.

        Args:
            full_transcript: Complete deliberation transcript
            vote_results: Final vote tally
            recommendations: List of recommendations
            themes: Key themes identified

        Returns:
            Executive summary text
        """
        rec_text = "\n".join([
            f"- {rec.get('title', 'Recommendation')}"
            for rec in recommendations
        ])

        themes_text = ", ".join(themes) if themes else "various considerations"

        # Build vote results text for both old and new formats
        if 'total_proposals' in vote_results:
            # New score-voting format
            vote_text = (
                f"- Total proposals scored: {vote_results.get('total_proposals', 0)}\n"
                f"- Proposals that passed (avg score >3/5): {vote_results.get('passed', 0)}\n"
                f"- Proposals that did not pass: {vote_results.get('failed', 0)}\n"
                f"- Total voters: {vote_results.get('total_voters', 0)}"
            )
        else:
            # Legacy support/oppose/abstain format
            vote_text = (
                f"- Support: {vote_results.get('support', 0)}\n"
                f"- Oppose: {vote_results.get('oppose', 0)}\n"
                f"- Abstain: {vote_results.get('abstain', 0)}\n"
                f"- Total: {vote_results.get('total', 0)}"
            )

        # Include recommendation scores if available
        rec_detail_lines = []
        for rec in recommendations:
            line = f"- {rec.get('title', 'Recommendation')}"
            if 'avg_score' in rec:
                line += f" (avg score: {rec['avg_score']}/5)"
            rec_detail_lines.append(line)
        rec_detail_text = "\n".join(rec_detail_lines)

        prompt = f"""Generate an executive summary for this citizens' assembly:

TOPIC: {self.topic}

KEY THEMES: {themes_text}

RECOMMENDATIONS CONSIDERED:
{rec_detail_text}

SCORE VOTING RESULTS:
{vote_text}

TRANSCRIPT EXCERPT (for context):
{full_transcript[:2000]}

Write an executive summary (3-4 paragraphs) that:
1. Introduces the topic and purpose of the assembly
2. Summarizes the deliberation process and key discussions
3. Reports the score voting outcome — which proposals passed and their scores
4. Notes the significance of the findings

Be objective and comprehensive. This summary will be read by policymakers and the public."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=600
            )
            return response

        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return f"The Citizens' Assembly deliberated on {self.topic} and reached a conclusion through democratic discussion and voting."

    async def generate_group_summary(
        self,
        group_name: str,
        round_summaries: list[dict]
    ) -> dict:
        """
        Generate an overall summary for a deliberation group.

        Args:
            group_name: Name of the group (A, B, C, etc.)
            round_summaries: List of dicts with round number and summary text

        Returns:
            Dict with consensus and disagreements summaries
        """
        if not round_summaries:
            return {
                "consensus": "No discussion recorded for this group.",
                "disagreements": "No disagreements recorded."
            }

        # Format round summaries
        summaries_text = "\n\n".join([
            f"Round {rs.get('round', '?')}: {rs.get('summary', 'No summary')}"
            for rs in round_summaries
        ])

        prompt = f"""Analyze Group {group_name}'s deliberation and generate two summaries:

TOPIC: {self.topic}

ROUND SUMMARIES:
{summaries_text}

Generate:
1. CONSENSUS: What did this group generally agree on? What shared values or concerns emerged?
2. DISAGREEMENTS: What were the main points of contention? What issues divided the group?

Format your response as:
CONSENSUS:
[2-3 paragraphs about areas of agreement]

DISAGREEMENTS:
[2-3 paragraphs about areas of disagreement]"""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=600
            )

            # Parse response
            result = {"consensus": "", "disagreements": ""}

            if "CONSENSUS:" in response and "DISAGREEMENTS:" in response:
                parts = response.split("DISAGREEMENTS:")
                result["consensus"] = parts[0].replace("CONSENSUS:", "").strip()
                result["disagreements"] = parts[1].strip() if len(parts) > 1 else ""
            else:
                result["consensus"] = response

            return result

        except Exception as e:
            logger.error(f"Error generating group summary: {e}")
            return {
                "consensus": f"Group {group_name} discussed the topic.",
                "disagreements": "Various perspectives were shared."
            }

    async def generate_final_summary(
        self,
        full_transcript: str,
        vote_results: dict,
        recommendations: list[dict]
    ) -> dict:
        """
        Generate all components of the final report.

        Args:
            full_transcript: Complete deliberation transcript
            vote_results: Final vote tally
            recommendations: List of recommendations

        Returns:
            Dict with all report components
        """
        # Generate each component
        themes = await self.identify_themes(full_transcript)

        executive_summary = await self.generate_executive_summary(
            full_transcript, vote_results, recommendations, themes
        )

        consensus = await self.generate_consensus_summary(full_transcript, vote_results)
        disagreements = await self.generate_disagreements_summary(full_transcript)
        minority_report = await self.generate_minority_report(full_transcript, vote_results)

        return {
            "executive_summary": executive_summary,
            "key_themes": themes,
            "consensus_summary": consensus,
            "disagreements_summary": disagreements,
            "minority_report": minority_report,
            "vote_tally": vote_results,
            "recommendations": recommendations
        }

    def __repr__(self):
        return f"<RecorderAgent(topic='{self.topic[:30]}...')>"
