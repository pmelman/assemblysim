"""
LLM Client Module

Provides a unified interface to various LLM providers including:
- OpenRouter (proxy to multiple providers)
- OpenAI (direct)
- Anthropic (direct)
"""

import httpx
import json
from typing import Optional
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client supporting multiple providers.

    Primary support is for OpenRouter which provides access to
    Claude, GPT-4, and other models through a single API.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        self.settings = get_settings()
        self.model = model or self.settings.WRITER_MODEL
        self.temperature = temperature if temperature is not None else self.settings.TEMPERATURE
        self.max_tokens = max_tokens or self.settings.MAX_TOKENS

        # Determine provider and set up client
        self.provider = self.settings.LLM_PROVIDER
        self._setup_client()

    def _setup_client(self):
        """Configure the HTTP client based on provider."""
        if self.provider == "openrouter":
            self.base_url = self.settings.OPENROUTER_BASE_URL
            self.api_key = self.settings.OPENROUTER_API_KEY
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://silicon-citizens-assembly.local",
                "X-Title": "Silicon Citizens' Assembly",
                "Content-Type": "application/json"
            }
        elif self.provider == "openai":
            self.base_url = "https://api.openai.com/v1"
            self.api_key = self.settings.OPENAI_API_KEY
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        elif self.provider == "anthropic":
            self.base_url = "https://api.anthropic.com/v1"
            self.api_key = self.settings.ANTHROPIC_API_KEY
            self.headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        if not self.api_key:
            raise ValueError(f"API key not configured for provider: {self.provider}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a completion from the LLM.

        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The generated text response
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        # Log the request (truncated for readability)
        logger.debug("=" * 80)
        logger.debug(f"LLM REQUEST ({self.model})")
        logger.debug("-" * 80)
        if system_prompt:
            logger.debug(f"SYSTEM: {system_prompt[:200]}..." if len(system_prompt) > 200 else f"SYSTEM: {system_prompt}")
        logger.debug(f"USER: {prompt[:500]}..." if len(prompt) > 500 else f"USER: {prompt}")
        logger.debug(f"Params: temp={temp}, max_tokens={tokens}")
        logger.debug("-" * 80)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if self.provider in ["openrouter", "openai"]:
            response = await self._complete_openai_format(messages, temp, tokens)
        elif self.provider == "anthropic":
            response = await self._complete_anthropic_format(prompt, system_prompt, temp, tokens)
        else:
            response = ""

        # Log the response
        logger.debug(f"RESPONSE: {response[:500]}..." if len(response) > 500 else f"RESPONSE: {response}")
        logger.debug("=" * 80)

        return response

    async def _complete_openai_format(
        self,
        messages: list,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Complete using OpenAI-compatible API format (OpenRouter, OpenAI)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )

            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                response.raise_for_status()

            result = response.json()

            # Debug logging for response structure
            logger.debug(f"API Response keys: {result.keys()}")
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                logger.debug(f"Choice keys: {choice.keys()}")
                if "message" in choice:
                    message = choice["message"]
                    logger.debug(f"Message keys: {message.keys()}")

                    # Get content
                    content = message.get("content", "") or ""
                    logger.debug(f"Content length: {len(content)}")

                    # For thinking models (like Kimi-K2), check reasoning field
                    reasoning = message.get("reasoning", "") or ""
                    if reasoning:
                        logger.debug(f"Reasoning length: {len(reasoning)}")
                        logger.debug(f"Reasoning preview: {reasoning[:200]}")

                    # If content is empty but reasoning exists, the model might have
                    # put the actual response in reasoning instead
                    if not content and reasoning:
                        logger.info("Content empty, using reasoning field instead")
                        return reasoning

                    return content
                else:
                    logger.warning(f"No 'message' in choice. Choice: {choice}")
                    return ""
            else:
                logger.warning(f"No choices in result. Result: {result}")
                return ""

    async def _complete_anthropic_format(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Complete using Anthropic's native API format."""
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload
            )

            if response.status_code != 200:
                logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                response.raise_for_status()

            result = response.json()
            return result["content"][0]["text"]

    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Synchronous version of complete() for non-async contexts.
        """
        import asyncio

        # Handle running in existing event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, need to use run_in_executor or similar
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    self.complete(prompt, system_prompt, temperature, max_tokens)
                )
                return future.result()
        except RuntimeError:
            # No event loop running, we can use asyncio.run
            return asyncio.run(
                self.complete(prompt, system_prompt, temperature, max_tokens)
            )


def get_llm_client(
    model: Optional[str] = None,
    purpose: str = "default"
) -> LLMClient:
    """
    Factory function to get an LLM client configured for a specific purpose.

    Args:
        model: Specific model to use (overrides defaults)
        purpose: "writer" for persona generation, "citizen" for agents,
                "moderator" for moderator agent, "utility" for helper tasks

    Returns:
        Configured LLMClient instance
    """
    settings = get_settings()

    if model:
        return LLMClient(model=model)

    if purpose == "writer":
        return LLMClient(
            model=settings.WRITER_MODEL,
            max_tokens=settings.WRITER_MAX_TOKENS
        )
    elif purpose == "citizen":
        return LLMClient(
            model=settings.CITIZEN_MODEL,
            temperature=settings.TEMPERATURE
        )
    elif purpose == "moderator":
        return LLMClient(
            model=settings.MODERATOR_MODEL,
            temperature=0.5  # Moderate temp for facilitation
        )
    elif purpose == "utility":
        return LLMClient(
            model=settings.UTILITY_MODEL,
            temperature=0.3  # Lower temp for utility tasks
        )
    else:
        return LLMClient()
