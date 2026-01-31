"""
Knowledge Package

Research and briefing book generation using external knowledge sources.
"""

from app.knowledge.perplexity_client import (
    PerplexityClient,
    get_perplexity_client
)

__all__ = [
    "PerplexityClient",
    "get_perplexity_client",
]
