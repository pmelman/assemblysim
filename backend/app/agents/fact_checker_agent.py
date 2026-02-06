"""
Fact-Checker Agent Module

Validates factual claims in citizen messages against the briefing book.
"""

import json
import logging
from typing import Optional

from app.llm_client import get_llm_client
from app.config import get_settings

logger = logging.getLogger(__name__)


class FactCheckerAgent:
    """
    Validates claims against the briefing book.

    Returns one of:
    - "verified": Claim aligns with briefing
    - "disputed": Claim contradicts briefing
    - "unchecked": Cannot determine from briefing
    """

    SYSTEM_PROMPT = """You are a fact-checker for a citizens' deliberative assembly.
Your task is to verify whether claims in citizen statements are supported by the briefing materials.

GUIDELINES:
1. Only verify factual claims, not opinions or values
2. If a claim matches information in the briefing, mark as "verified"
3. If a claim contradicts the briefing, mark as "disputed"
4. If the briefing doesn't address the claim, mark as "unchecked"
5. Be conservative - when uncertain, use "unchecked"

OUTPUT FORMAT (JSON):
{
    "status": "verified" | "disputed" | "unchecked",
    "explanation": "Brief explanation of your determination",
    "relevant_briefing_section": "Section name if applicable"
}"""

    # Indicators that suggest a statement contains factual claims
    FACTUAL_INDICATORS = [
        "percent", "%", "study", "research", "according to",
        "data shows", "statistics", "evidence", "fact",
        "increase", "decrease", "million", "billion",
        "report", "survey", "analysis", "found that",
        "experts", "scientists", "economists"
    ]

    def __init__(self, briefing_content: str):
        """
        Initialize the fact-checker agent.

        Args:
            briefing_content: The briefing book content to check against
        """
        self.briefing_content = briefing_content
        self.llm = get_llm_client(purpose="utility")

    async def check_message(self, content: str) -> dict:
        """
        Check a citizen message for factual accuracy.

        Args:
            content: The citizen's message content

        Returns:
            Dict with status, explanation, and relevant_briefing_section
        """
        # Skip short messages or pure opinions
        if len(content) < 100 or not self._has_factual_claims(content):
            return {
                "status": "unchecked",
                "explanation": "No verifiable factual claims detected",
                "relevant_briefing_section": None
            }

        prompt = f"""BRIEFING MATERIALS:
{self.briefing_content[:3000]}

CITIZEN STATEMENT TO VERIFY:
{content}

Check this statement against the briefing. Are there any factual claims that can be verified or disputed?
Respond with a JSON object containing status, explanation, and relevant_briefing_section."""

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=300
            )
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Fact check error: {e}")
            return {
                "status": "unchecked",
                "explanation": "Fact check unavailable",
                "relevant_briefing_section": None
            }

    def _has_factual_claims(self, content: str) -> bool:
        """
        Quick heuristic to detect if content has factual claims.

        Args:
            content: The message content to analyze

        Returns:
            True if the content appears to contain factual claims
        """
        content_lower = content.lower()
        return any(ind in content_lower for ind in self.FACTUAL_INDICATORS)

    def _parse_response(self, response: str) -> dict:
        """
        Parse LLM response into structured format.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed dict with status, explanation, relevant_briefing_section
        """
        try:
            # Try to extract JSON from the response
            json_str = response

            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            result = json.loads(json_str.strip())

            # Validate and normalize status
            valid_statuses = ["verified", "disputed", "unchecked"]
            if result.get("status") not in valid_statuses:
                result["status"] = "unchecked"

            # Ensure required fields exist
            if "explanation" not in result:
                result["explanation"] = ""
            if "relevant_briefing_section" not in result:
                result["relevant_briefing_section"] = None

            return result

        except (json.JSONDecodeError, IndexError, KeyError):
            # Fallback parsing based on keywords
            response_lower = response.lower()

            if "verified" in response_lower and "disputed" not in response_lower:
                status = "verified"
            elif "disputed" in response_lower or "contradict" in response_lower:
                status = "disputed"
            else:
                status = "unchecked"

            return {
                "status": status,
                "explanation": response[:200] if response else "",
                "relevant_briefing_section": None
            }

    def __repr__(self):
        return f"<FactCheckerAgent(briefing_length={len(self.briefing_content)})>"
