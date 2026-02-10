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

    async def _call_api(self, prompt: str, max_tokens: int = 4000, system_prompt: Optional[str] = None) -> dict:
        """Make the API call to Perplexity.

        Args:
            prompt: The user prompt to send
            max_tokens: Maximum tokens in response (default 4000)
            system_prompt: Optional override for system prompt
        """
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
            "model": "sonar-pro",  # Updated to current Perplexity model
            "messages": [
                {"role": "system", "content": system_prompt or self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens,
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
                    # Handle both string URLs and dict citations
                    if isinstance(cite, str):
                        logger.debug(f"  {i}. {cite}")
                    elif isinstance(cite, dict):
                        logger.debug(f"  {i}. {cite.get('title', 'Unknown')}: {cite.get('url', 'No URL')}")
                    else:
                        logger.debug(f"  {i}. {cite}")
            logger.debug("=" * 80)

            return result

    def _parse_response(self, response: dict, topic: str) -> dict:
        """Parse the Perplexity API response into structured format."""
        try:
            content = response["choices"][0]["message"]["content"]

            # Log raw content for debugging
            logger.debug(f"Raw Perplexity content (first 500 chars): {content[:500]}")

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            sections = json.loads(content.strip())

            # Validate that sections is a dict
            if not isinstance(sections, dict):
                logger.warning(f"Parsed JSON is not a dict, got {type(sections).__name__}")
                raise ValueError(f"Expected dict, got {type(sections).__name__}")

            # Extract citations if available
            sources = []
            if "citations" in response:
                for citation in response["citations"]:
                    # Handle both string URLs and dict citations
                    if isinstance(citation, str):
                        # Citation is just a URL string
                        sources.append({
                            "title": citation,
                            "url": citation,
                            "snippet": ""
                        })
                    elif isinstance(citation, dict):
                        # Citation is a full dict with metadata
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

        except (json.JSONDecodeError, KeyError, ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to parse Perplexity response: {type(e).__name__}: {e}")
            # Try to use raw content as markdown
            try:
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            except (AttributeError, TypeError):
                content = ""
            return {
                "content_markdown": content or f"# {topic}\n\nBriefing content unavailable.",
                "sections": None,
                "sources": []
            }

    def _build_markdown(self, sections: dict, topic: str) -> str:
        """Build markdown content from any structured JSON sections.

        Handles arbitrary JSON structures by converting keys to readable
        headings and rendering values based on their type (string, list, dict, etc.).
        """
        md = f"# Briefing Book: {topic}\n\n"

        # Safety check - ensure sections is a dict
        if not isinstance(sections, dict):
            logger.warning(f"_build_markdown received non-dict: {type(sections).__name__}")
            return md + str(sections) if sections else md

        for key, value in sections.items():
            if value is None:
                continue
            heading = self._key_to_heading(key)
            md += self._render_section(heading, value, level=2)

        return md

    def _key_to_heading(self, key: str) -> str:
        """Convert a JSON key like 'problem_landscape' to 'Problem Landscape'."""
        return key.replace("_", " ").replace("-", " ").title()

    def _render_section(self, heading: str, value, level: int = 2) -> str:
        """Recursively render a section value into markdown.

        Handles: str, list[str], list[dict], dict[str, str], dict[str, Any].
        """
        prefix = "#" * level
        md = ""

        if isinstance(value, str):
            md += f"{prefix} {heading}\n\n{value}\n\n"

        elif isinstance(value, list):
            md += f"{prefix} {heading}\n\n"
            for i, item in enumerate(value, 1):
                if isinstance(item, str):
                    md += f"- {item}\n"
                elif isinstance(item, dict):
                    # Render each dict item as a sub-section
                    # Use a summary field if available, else the first string value
                    sub_label = (
                        item.get("issue")
                        or item.get("approach")
                        or item.get("title")
                        or item.get("name")
                        or f"Item {i}"
                    )
                    md += f"\n{'#' * (level + 1)} {sub_label}\n\n"
                    for k, v in item.items():
                        if k in ("issue", "approach", "title", "name"):
                            continue  # Already used as heading
                        label = self._key_to_heading(k)
                        if isinstance(v, str):
                            md += f"**{label}:** {v}\n\n"
                        elif isinstance(v, list):
                            md += f"**{label}:**\n"
                            for sub_item in v:
                                md += f"- {sub_item}\n"
                            md += "\n"
                        else:
                            md += f"**{label}:** {v}\n\n"
                else:
                    md += f"- {item}\n"
            md += "\n"

        elif isinstance(value, dict):
            md += f"{prefix} {heading}\n\n"
            for k, v in value.items():
                label = self._key_to_heading(k)
                if isinstance(v, str):
                    md += f"**{label}:** {v}\n\n"
                elif isinstance(v, list):
                    md += f"**{label}:**\n"
                    for item in v:
                        md += f"- {item}\n"
                    md += "\n"
                elif isinstance(v, dict):
                    md += self._render_section(label, v, level=level + 1)
                else:
                    md += f"**{label}:** {v}\n\n"

        else:
            # Fallback for other types (int, bool, etc.)
            md += f"{prefix} {heading}\n\n{value}\n\n"

        return md

    async def research_query(self, query: str, max_tokens: int = 2000) -> dict:
        """
        Perform a focused follow-up research query.

        Used between deliberation rounds to answer specific questions
        that emerged from the discussion.

        Args:
            query: The specific research question to answer
            max_tokens: Maximum tokens for the response

        Returns:
            Dict with query, content, and sources
        """
        if not self.is_available:
            logger.warning("Perplexity API not available for research query")
            return {
                "query": query,
                "content": f"Research unavailable for: {query}",
                "sources": []
            }

        system_prompt = (
            "You are a research assistant. Answer the following question with accurate, "
            "well-sourced information. Be concise and factual. Include specific data, "
            "statistics, and expert opinions where available. Cite your sources."
        )

        try:
            response = await self._call_api(
                prompt=query,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )

            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            sources = []
            if "citations" in response:
                for citation in response["citations"]:
                    if isinstance(citation, str):
                        sources.append({"title": citation, "url": citation})
                    elif isinstance(citation, dict):
                        sources.append({
                            "title": citation.get("title", ""),
                            "url": citation.get("url", "")
                        })

            return {
                "query": query,
                "content": content,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Research query failed: {e}")
            return {
                "query": query,
                "content": f"Research query failed: {str(e)}",
                "sources": []
            }

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
