"""
Agents Package

AI agents for the deliberative assembly: citizens, moderator, recorder,
fact-checker, and supporting mechanisms.
"""

from app.agents.citizen_agent import (
    CitizenAgent,
    create_citizen_agent_from_db
)

from app.agents.moderator_agent import ModeratorAgent

from app.agents.recorder_agent import RecorderAgent

from app.agents.fact_checker_agent import FactCheckerAgent

from app.agents.stubbornness import (
    calculate_stubbornness,
    get_stubbornness_instruction
)

__all__ = [
    "CitizenAgent",
    "create_citizen_agent_from_db",
    "ModeratorAgent",
    "RecorderAgent",
    "FactCheckerAgent",
    "calculate_stubbornness",
    "get_stubbornness_instruction",
]
