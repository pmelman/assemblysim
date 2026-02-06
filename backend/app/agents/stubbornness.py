"""
Stubbornness Mechanism

Prevents premature consensus by encouraging citizens to maintain
their authentic positions, especially in later rounds.
"""

from typing import Optional


def calculate_stubbornness(
    citizen_values: list[str],
    political_leaning: Optional[str],
    round_number: int,
    total_rounds: int
) -> float:
    """
    Calculate stubbornness modifier (0.0 to 1.0).

    Higher values = more resistant to changing position.
    Increases in later rounds to prevent bandwagon effects.

    Args:
        citizen_values: List of the citizen's core values
        political_leaning: Optional political leaning (not currently used)
        round_number: Current round number (1-indexed)
        total_rounds: Total number of rounds in deliberation

    Returns:
        Stubbornness value between 0.0 and 1.0
    """
    base = 0.3  # Base stubbornness

    # Increase stubbornness in later rounds
    round_factor = round_number / total_rounds if total_rounds > 0 else 0
    round_boost = round_factor * 0.3  # Up to +0.3 in final round

    # Strong values increase stubbornness
    value_boost = 0.0
    strong_value_keywords = [
        "faith", "family", "freedom", "tradition", "justice", "equality",
        "liberty", "security", "community", "independence", "fairness",
        "loyalty", "honor", "integrity", "morality", "patriotism"
    ]

    if citizen_values:
        for value in citizen_values:
            value_lower = value.lower() if value else ""
            if any(kw in value_lower for kw in strong_value_keywords):
                value_boost += 0.05
        value_boost = min(value_boost, 0.2)  # Cap at 0.2

    return min(base + round_boost + value_boost, 1.0)


def get_stubbornness_instruction(stubbornness: float, round_number: int) -> str:
    """
    Generate prompt instruction based on stubbornness level.

    Args:
        stubbornness: Calculated stubbornness value (0.0-1.0)
        round_number: Current round number (for context)

    Returns:
        Instruction string to append to citizen prompts
    """
    if stubbornness > 0.7:
        return """
IMPORTANT: You have strong convictions on this issue. While you should listen
respectfully to others, don't abandon your core values just to reach agreement.
It's okay to maintain your position if you genuinely believe it. Changing your
mind should require compelling new evidence or arguments, not just social pressure."""

    elif stubbornness > 0.4:
        return """
Remember to stay true to your values while engaging with other perspectives.
You may adjust your views based on compelling evidence, but don't feel
pressured to agree just for the sake of consensus. Your authentic voice matters."""

    else:
        return """
Keep an open mind and engage thoughtfully with different perspectives.
Consider new evidence while staying grounded in your core values."""
