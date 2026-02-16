"""
Perplexity API Client for Briefing Book Generation

Generates comprehensive research briefings on policy topics using
Perplexity's search-augmented AI for accurate, sourced information.
"""

import httpx
import json
import logging
import re
from typing import Optional
from datetime import datetime

from app.config import get_settings
from app.prompt_loader import get_perplexity_prompt, get_perplexity_research_query_prompt

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

    async def _call_api(self, prompt: str, max_tokens: Optional[int] = None, system_prompt: Optional[str] = None) -> dict:
        """Make the API call to Perplexity.

        Args:
            prompt: The user prompt to send
            max_tokens: Maximum tokens in response (uses config default if not specified)
            system_prompt: Optional override for system prompt
        """
        logger.debug("=" * 80)
        logger.debug("PERPLEXITY REQUEST")
        logger.debug("-" * 80)
        logger.debug(f"PROMPT: {prompt[:500]}..." if len(prompt) > 500 else f"PROMPT: {prompt}")
        logger.debug("-" * 80)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Origin": "https://www.perplexity.ai",
            "Referer": "https://www.perplexity.ai/"
        }

        # Use config defaults if not specified
        if max_tokens is None:
            max_tokens = self.settings.PERPLEXITY_BRIEFING_MAX_TOKENS

        payload = {
            "model": self.settings.PERPLEXITY_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt or self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.settings.PERPLEXITY_TEMPERATURE,
            "max_tokens": max_tokens,
            "return_citations": True,
            "stream": True,
            "reasoning_effort": self.settings.PERPLEXITY_REASONING_EFFORT,
            "web_search_options": {
                "search_context_size": self.settings.PERPLEXITY_SEARCH_CONTEXT_SIZE
            }
        }

        async with httpx.AsyncClient(timeout=float(self.settings.PERPLEXITY_TIMEOUT)) as client:
            # Use streaming — sonar-deep-research returns empty content without it
            full_content = ""
            citations = []
            search_results = []
            last_chunk = {}

            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error(f"Perplexity API error: {response.status_code} - {body.decode()}")
                    response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        last_chunk = chunk
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_content += content
                        # Capture citations/search_results from final chunks
                        if "citations" in chunk:
                            citations = chunk["citations"]
                        if "search_results" in chunk:
                            search_results = chunk["search_results"]
                    except json.JSONDecodeError:
                        continue

            # Strip <think>...</think> reasoning blocks from deep-research models
            full_content = re.sub(r"<think>.*?</think>\s*", "", full_content, flags=re.DOTALL)
            # Handle truncated thinking (no closing tag)
            if "<think>" in full_content:
                full_content = full_content.split("<think>")[0].strip()

            # Build a response dict matching the non-streaming format
            result = {
                "id": last_chunk.get("id", ""),
                "model": last_chunk.get("model", self.settings.PERPLEXITY_MODEL),
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": full_content
                        }
                    }
                ],
                "citations": citations,
                "search_results": search_results,
                "usage": last_chunk.get("usage", {})
            }

            # Log response
            logger.debug(f"RESPONSE: {full_content[:1000]}..." if len(full_content) > 1000 else f"RESPONSE: {full_content}")

            if citations:
                logger.debug(f"CITATIONS: {len(citations)} sources")
                for i, cite in enumerate(citations[:3], 1):
                    if isinstance(cite, str):
                        logger.debug(f"  {i}. {cite}")
                    elif isinstance(cite, dict):
                        logger.debug(f"  {i}. {cite.get('title', 'Unknown')}: {cite.get('url', 'No URL')}")
                    else:
                        logger.debug(f"  {i}. {cite}")
            logger.debug("=" * 80)

            return result

    def _extract_json(self, content: str) -> dict:
        """Extract a JSON object from content that may contain surrounding text.

        Handles code fences, surrounding text, and truncated JSON
        (common with deep-research models that exceed the token limit).
        """
        # Strip code fences first
        raw = content
        if "```json" in raw:
            raw = raw.split("```json", 1)[1]
            if "```" in raw:
                raw = raw.split("```", 1)[0]
        elif "```" in raw:
            raw = raw.split("```", 1)[1]
            if "```" in raw:
                raw = raw.split("```", 1)[0]

        # Trim to the JSON object boundaries
        start = raw.find("{")
        if start != -1:
            raw = raw[start:]

        # Try parsing as-is
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass

        # Repair truncated JSON: close unclosed brackets/braces
        repaired = self._repair_truncated_json(raw)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

        raise ValueError("No valid JSON object found in content")

    def _repair_truncated_json(self, text: str) -> Optional[str]:
        """Attempt to repair JSON truncated by a token limit.

        Truncates at the last complete value, then closes any
        open brackets/braces.
        """
        # Trim trailing incomplete value — cut back to last comma, ], or }
        trimmed = text.rstrip()
        # Remove trailing partial string or number
        for end_char in (",", "}", "]", '"'):
            pos = trimmed.rfind(end_char)
            if pos != -1:
                trimmed = trimmed[:pos + 1]
                break
        else:
            return None

        # Remove any trailing comma before we close structures
        trimmed = trimmed.rstrip().rstrip(",")

        # Count unclosed openers
        stack = []
        in_string = False
        escape = False
        for ch in trimmed:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ("{", "["):
                stack.append(ch)
            elif ch == "}":
                if stack and stack[-1] == "{":
                    stack.pop()
            elif ch == "]":
                if stack and stack[-1] == "[":
                    stack.pop()

        # Close in reverse order
        closers = {"[": "]", "{": "}"}
        for opener in reversed(stack):
            trimmed += closers[opener]

        return trimmed

    def _parse_response(self, response: dict, topic: str) -> dict:
        """Parse the Perplexity API response into structured format."""
        try:
            content = response["choices"][0]["message"]["content"]

            # Log raw content for debugging
            logger.debug(f"Raw Perplexity content (first 500 chars): {content[:500]}")

            sections = self._extract_json(content)

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

    async def research_query(self, query: str, max_tokens: Optional[int] = None) -> dict:
        """
        Perform a focused follow-up research query.

        Used between deliberation rounds to answer specific questions
        that emerged from the discussion.

        Args:
            query: The specific research question to answer
            max_tokens: Maximum tokens for the response (uses config default if not specified)

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

        # Use config default if not specified
        if max_tokens is None:
            max_tokens = self.settings.PERPLEXITY_RESEARCH_MAX_TOKENS

        # Load system prompt from prompts.yaml
        system_prompt = get_perplexity_research_query_prompt()

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
