"""
Prompt Loader

Loads system prompts from prompts.yaml for all agents.
Provides a centralized way to manage and customize prompts.
"""

import yaml
from pathlib import Path
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """Loads and caches prompts from YAML configuration."""

    def __init__(self, prompts_file: str = "prompts.yaml"):
        """
        Initialize the prompt loader.

        Args:
            prompts_file: Path to the prompts YAML file (relative to app/)
        """
        self.prompts_file = Path(__file__).parent / prompts_file
        self._prompts = None

    def load(self) -> dict:
        """
        Load prompts from YAML file.

        Returns:
            Dictionary with all prompts
        """
        if self._prompts is None:
            try:
                with open(self.prompts_file, 'r') as f:
                    self._prompts = yaml.safe_load(f)
                logger.info(f"Loaded prompts from {self.prompts_file}")
            except FileNotFoundError:
                logger.error(f"Prompts file not found: {self.prompts_file}")
                raise
            except yaml.YAMLError as e:
                logger.error(f"Error parsing prompts YAML: {e}")
                raise

        return self._prompts

    def get(self, agent: str, prompt_type: str = "system") -> str:
        """
        Get a specific prompt.

        Args:
            agent: Agent name ("writer", "moderator", "recorder", "citizen", "perplexity")
            prompt_type: Type of prompt ("system", "deliberation_instructions", etc.)

        Returns:
            The prompt text

        Raises:
            KeyError: If prompt not found
        """
        prompts = self.load()

        if agent not in prompts:
            raise KeyError(f"Agent '{agent}' not found in prompts.yaml")

        if prompt_type not in prompts[agent]:
            raise KeyError(f"Prompt type '{prompt_type}' not found for agent '{agent}'")

        return prompts[agent][prompt_type]

    def reload(self):
        """Reload prompts from file (useful for hot-reloading)."""
        self._prompts = None
        return self.load()


@lru_cache()
def get_prompt_loader() -> PromptLoader:
    """
    Get the singleton prompt loader instance.

    Returns:
        Cached PromptLoader instance
    """
    return PromptLoader()


def get_prompt(agent: str, prompt_type: str = "system") -> str:
    """
    Convenience function to get a prompt.

    Args:
        agent: Agent name
        prompt_type: Type of prompt

    Returns:
        The prompt text
    """
    loader = get_prompt_loader()
    return loader.get(agent, prompt_type)


# Convenience functions for each agent
def get_writer_prompt() -> str:
    """Get the writer (persona generation) system prompt."""
    return get_prompt("writer", "system")


def get_moderator_prompt() -> str:
    """Get the moderator system prompt."""
    return get_prompt("moderator", "system")


def get_recorder_prompt() -> str:
    """Get the recorder system prompt."""
    return get_prompt("recorder", "system")


def get_citizen_instructions() -> str:
    """Get the citizen deliberation instructions."""
    return get_prompt("citizen", "deliberation_instructions")


def get_citizen_citation_instructions() -> str:
    """Get the citizen citation instructions."""
    return get_prompt("citizen", "citation_instructions")


def get_fact_checker_prompt() -> str:
    """Get the fact-checker system prompt."""
    return get_prompt("fact_checker", "system")


def get_perplexity_prompt() -> str:
    """Get the Perplexity research system prompt."""
    return get_prompt("perplexity", "system")


def get_perplexity_research_query_prompt() -> str:
    """Get the Perplexity follow-up research query prompt."""
    return get_prompt("perplexity", "research_query")


def get_citizen_proposal_instructions() -> str:
    """Get the citizen proposal generation instructions."""
    return get_prompt("citizen", "proposal_instructions")


def get_citizen_score_vote_instructions() -> str:
    """Get the citizen score voting instructions."""
    return get_prompt("citizen", "score_vote_instructions")


def get_moderator_proposal_prompt() -> str:
    """Get the moderator proposal generation opening prompt."""
    return get_prompt("moderator", "prompt_proposals")


def get_moderator_deduplicate_prompt() -> str:
    """Get the moderator deduplication instructions."""
    return get_prompt("moderator", "deduplicate_proposals")


def get_moderator_score_voting_transition() -> str:
    """Get the moderator score voting transition statement."""
    return get_prompt("moderator", "transition_to_score_voting")
