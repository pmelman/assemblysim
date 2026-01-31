"""
Perplexity API Client for Briefing Book Generation

Generates comprehensive research briefings on policy topics using
Perplexity's search-augmented AI for accurate, sourced information.
"""

import httpx
import json
import logging
from typing import Optional
from datetime import datetime

from app.config import get_settings
from app.prompt_loader import get_perplexity_prompt

logger = logging.getLogger(__name__)


class PerplexityClient:
    """
    Client for Perplexity API to generate research briefings.

    Produces structured briefing books with:
    - Topic overview
    - Arguments for and against
    - Policy options
    - Key facts and statistics
    - Cited sources
    """

    # System prompt now loaded from prompts.yaml via get_perplexity_prompt()

    def __init__(self):
        """Initialize the Perplexity client."""
        self.settings = get_settings()
        self.api_key = self.settings.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai"
        self.system_prompt = get_perplexity_prompt()

    @property
    def is_available(self) -> bool:
        """Check if Perplexity API is configured."""
        return bool(self.api_key)

    async def generate_briefing_book(
        self,
        topic: str,
        depth: str = "standard"
    ) -> dict:
        """
        Generate a comprehensive briefing book for a policy topic.

        Args:
            topic: The policy topic to research
            depth: Research depth - "quick", "standard", or "detailed"

        Returns:
            Dictionary with structured briefing content and sources
        """
        if not self.is_available:
            logger.warning("Perplexity API key not configured, using fallback")
            return self._generate_fallback_briefing(topic)

        # Adjust prompt based on depth
        detail_instruction = {
            "quick": "Provide a concise overview with key points only.",
            "standard": "Provide comprehensive coverage of main arguments and evidence.",
            "detailed": "Provide in-depth analysis with extensive evidence, historical context, and implementation details."
        }.get(depth, "Provide comprehensive coverage of main arguments and evidence.")

        user_prompt = f"""Research and analyze this policy topic for a citizens' deliberative assembly:

TOPIC: {topic}

{detail_instruction}

Include:
1. Clear overview of the issue
2. Main arguments on both sides
3. Specific policy options or variations
4. Key facts, statistics, and evidence
5. Important considerations and tradeoffs

Format your response as the JSON structure specified in your instructions."""

        try:
            response = await self._call_api(user_prompt)
            result = self._parse_response(response, topic)

            # Add metadata
            result["topic_query"] = topic
            result["depth"] = depth
            result["generated_at"] = datetime.utcnow().isoformat()

            return result

        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return self._generate_fallback_briefing(topic)

    async def _call_api(self, prompt: str) -> dict:
        """Make the API call to Perplexity."""
        logger.debug("=" * 80)
        logger.debug("PERPLEXITY REQUEST")
        logger.debug("-" * 80)
        logger.debug(f"PROMPT: {prompt[:500]}..." if len(prompt) > 500 else f"PROMPT: {prompt}")
        logger.debug("-" * 80)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000,
            "return_citations": True
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                response.raise_for_status()

            result = response.json()

            # Log response
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.debug(f"RESPONSE: {content[:1000]}..." if len(content) > 1000 else f"RESPONSE: {content}")

            citations = result.get("citations", [])
            if citations:
                logger.debug(f"CITATIONS: {len(citations)} sources")
                for i, cite in enumerate(citations[:3], 1):  # Show first 3
                    logger.debug(f"  {i}. {cite.get('title', 'Unknown')}: {cite.get('url', 'No URL')}")
            logger.debug("=" * 80)

            return result

    def _parse_response(self, response: dict, topic: str) -> dict:
        """Parse the Perplexity API response into structured format."""
        try:
            content = response["choices"][0]["message"]["content"]

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            sections = json.loads(content.strip())

            # Extract citations if available
            sources = []
            if "citations" in response:
                for citation in response["citations"]:
                    sources.append({
                        "title": citation.get("title", ""),
                        "url": citation.get("url", ""),
                        "snippet": citation.get("snippet", "")
                    })

            # Build markdown content
            content_markdown = self._build_markdown(sections, topic)

            return {
                "content_markdown": content_markdown,
                "sections": sections,
                "sources": sources
            }

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse Perplexity response: {e}")
            # Try to use raw content as markdown
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "content_markdown": content or f"# {topic}\n\nBriefing content unavailable.",
                "sections": None,
                "sources": []
            }

    def _build_markdown(self, sections: dict, topic: str) -> str:
        """Build markdown content from structured sections."""
        md = f"# Briefing Book: {topic}\n\n"

        if overview := sections.get("overview"):
            md += f"## Overview\n\n{overview}\n\n"

        if args_for := sections.get("arguments_for"):
            md += "## Arguments in Favor\n\n"
            for arg in args_for:
                md += f"- {arg}\n"
            md += "\n"

        if args_against := sections.get("arguments_against"):
            md += "## Arguments Against\n\n"
            for arg in args_against:
                md += f"- {arg}\n"
            md += "\n"

        if options := sections.get("policy_options"):
            md += "## Policy Options\n\n"
            for i, option in enumerate(options, 1):
                md += f"{i}. {option}\n"
            md += "\n"

        if facts := sections.get("key_facts"):
            md += "## Key Facts and Statistics\n\n"
            for fact in facts:
                md += f"- {fact}\n"
            md += "\n"

        if considerations := sections.get("considerations"):
            md += f"## Additional Considerations\n\n{considerations}\n\n"

        return md

    def _generate_fallback_briefing(self, topic: str) -> dict:
        """
        Generate a placeholder briefing when API is unavailable.

        This ensures the system can function without Perplexity,
        though with reduced research quality.
        """
        sections = {
            "overview": f"This briefing covers the topic: {topic}. A comprehensive research briefing was not available. Citizens should rely on their own knowledge and the deliberation process to explore this topic.",
            "arguments_for": [
                "Arguments supporting this policy will be explored during deliberation",
                "Proponents typically cite benefits such as [to be discussed]",
                "Historical precedents may offer supporting evidence"
            ],
            "arguments_against": [
                "Arguments opposing this policy will be explored during deliberation",
                "Critics typically cite concerns such as [to be discussed]",
                "Implementation challenges may be raised"
            ],
            "policy_options": [
                "Full implementation as proposed",
                "Phased or limited implementation",
                "Modified version with specific amendments",
                "No change to current policy"
            ],
            "key_facts": [
                "Factual information will be gathered during deliberation",
                "Citizens are encouraged to share relevant knowledge",
                "The moderator will help verify claims as needed"
            ],
            "considerations": "This is a placeholder briefing. For a full research briefing, please configure the Perplexity API key."
        }

        content_markdown = self._build_markdown(sections, topic)

        return {
            "topic_query": topic,
            "content_markdown": content_markdown,
            "sections": sections,
            "sources": [],
            "depth": "fallback",
            "generated_at": datetime.utcnow().isoformat(),
            "is_fallback": True
        }


def get_perplexity_client() -> PerplexityClient:
    """Factory function to get a Perplexity client instance."""
    return PerplexityClient()
