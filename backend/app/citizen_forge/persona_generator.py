"""
Persona Generator Module

Converts GSS survey rows into rich, natural language persona prompts
for LLM agents. Uses a "Writer LLM" to create nuanced, non-stereotypical
character descriptions.
"""

import json
import pandas as pd
from typing import Optional
import logging
import asyncio
import random

from app.llm_client import get_llm_client
from app.prompt_loader import get_writer_prompt
from app.data.gss_labels import (
    get_label,
    format_value,
    get_age_group,
    format_income_bracket,
    REGION_LABELS,
    DEGREE_LABELS,
    WRKSTAT_LABELS,
    MARITAL_LABELS,
    RELIG_LABELS,
    SPENDING_LABELS
)

logger = logging.getLogger(__name__)


# =============================================================================
# BOT LAST NAMES (tech/sci-fi themed)
# =============================================================================

BOT_LAST_NAMES = [
    # Computing pioneers
    'Turing', 'Lovelace', 'Hopper', 'Babbage', 'Shannon', 'Dijkstra', 'Knuth',
    'Torvalds', 'Ritchie', 'Thompson', 'Wozniak', 'Berners-Lee',

    # Sci-fi authors
    'Asimov', 'Gibson', 'Dick', 'Stephenson', 'Clarke', 'Bradbury',
    'Herbert', 'Butler', 'Heinlein', 'Wells',

    # Sci-fi characters/references
    'Deckard', 'Ripley', 'Trinity', 'Connor', 'Skywalker', 'Solo',
    'Leia', 'Muad\'Dib', 'Montag', 'HAL',

    # Tech/bot terms
    'Protocol', 'Circuit', 'Neural', 'Vector', 'Matrix', 'Tensor',
    'Quantum', 'Binary', 'Logic', 'Cipher', 'Nexus', 'Cortex',
    'Synapse', 'Algorithm', 'Chrome', 'Byte', 'Node', 'Daemon',

    # Additional sci-fi refs
    'Replicant', 'Hologram', 'Android', 'Cypher', 'Morpheus', 'Oracle',
    'Archer', 'Data', 'Seven', 'Spock', 'Sulu', 'Uhura'
]


# =============================================================================
# WRITER LLM PROMPTS
# =============================================================================
# System prompt now loaded from prompts.yaml via get_writer_prompt()


WRITER_USER_TEMPLATE = """Create a persona from this General Social Survey respondent data:

=== DEMOGRAPHICS ===
- Age: {age} ({age_group})
- Sex: {sex}
- Race: {race}
- Region: {region}
- Education: {education}
- Employment: {employment}
- Marital Status: {marital}
- Household Income: {income}

=== POLITICAL & RELIGIOUS ===
- Political Views: {polviews} (on a scale from Extremely Liberal to Extremely Conservative)
- Party Identification: {partyid}
- Religious Affiliation: {religion}
- Religious Service Attendance: {attend}

=== ATTITUDES ON KEY ISSUES ===
{issue_attitudes}

=== INSTRUCTIONS ===
Create a nuanced persona that could authentically hold these views. Focus on their values, life experiences, and worldview. The persona will participate in a deliberative assembly on policy issues, so include guidance for respectful engagement with different perspectives.

Remember: Return ONLY valid JSON, no other text."""


# =============================================================================
# PERSONA GENERATOR CLASS
# =============================================================================

class PersonaGenerator:
    """
    Generates LLM personas from GSS survey data.

    Uses a "Writer LLM" to convert raw survey variables into
    natural language system prompts for citizen agents.
    """

    def __init__(self):
        """Initialize the persona generator with an LLM client."""
        self.llm = get_llm_client(purpose="writer")

    async def generate_persona(self, row: pd.Series) -> dict:
        """
        Generate a single persona from a GSS row.

        Args:
            row: A pandas Series containing GSS variables for one respondent

        Returns:
            Dictionary with persona data (name, system_prompt, etc.)
        """
        # Format the prompt with survey data
        prompt = self._format_prompt(row)

        try:
            # Call the Writer LLM
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=get_writer_prompt(),
                temperature=0.7,
                max_tokens=1500
            )

            # Check if response is empty
            if not response or not response.strip():
                logger.error("Empty response from Writer LLM")
                return self._create_fallback_persona(row)

            # Parse the JSON response
            persona = self._parse_response(response, row)

            # Add GSS source data
            persona['gss_data'] = self._extract_gss_data(row)

            return persona

        except Exception as e:
            logger.error(f"Error generating persona: {e}", exc_info=True)
            # Return a fallback persona
            return self._create_fallback_persona(row)

    async def generate_batch(
        self,
        df: pd.DataFrame,
        max_concurrent: int = 5
    ) -> list[dict]:
        """
        Generate personas for multiple GSS rows.

        Args:
            df: DataFrame with GSS respondents
            max_concurrent: Maximum concurrent API calls

        Returns:
            List of persona dictionaries
        """
        personas = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_limit(row):
            async with semaphore:
                return await self.generate_persona(row)

        # Create tasks for all rows
        tasks = [generate_with_limit(row) for _, row in df.iterrows()]

        # Run with progress logging
        total = len(tasks)
        for i, task in enumerate(asyncio.as_completed(tasks)):
            persona = await task
            personas.append(persona)
            if (i + 1) % 10 == 0:
                logger.info(f"Generated {i + 1}/{total} personas")

        logger.info(f"Generated {len(personas)} personas total")

        # Assign unique bot-themed last names
        personas = self._assign_bot_last_names(personas)

        return personas

    def _format_prompt(self, row: pd.Series) -> str:
        """Format the user prompt with GSS data."""

        # Format demographics
        age = int(row.get('age', 0)) if pd.notna(row.get('age')) else 'Unknown'
        age_group = get_age_group(age) if isinstance(age, int) else 'Unknown'

        sex = format_value('sex', int(row['sex'])) if pd.notna(row.get('sex')) else 'Unknown'
        race = format_value('race', int(row['race'])) if pd.notna(row.get('race')) else 'Unknown'

        region_code = int(row['region']) if pd.notna(row.get('region')) else None
        region = REGION_LABELS.get(region_code, 'Unknown') if region_code else 'Unknown'

        degree_code = int(row.get('degree', -1)) if pd.notna(row.get('degree')) else None
        education = DEGREE_LABELS.get(degree_code, 'Unknown') if degree_code is not None else 'Unknown'

        wrkstat_code = int(row.get('wrkstat', -1)) if pd.notna(row.get('wrkstat')) else None
        employment = WRKSTAT_LABELS.get(wrkstat_code, 'Unknown') if wrkstat_code is not None else 'Unknown'

        marital_code = int(row.get('marital', -1)) if pd.notna(row.get('marital')) else None
        marital = MARITAL_LABELS.get(marital_code, 'Unknown') if marital_code is not None else 'Unknown'

        income_code = int(row.get('income16', -1)) if pd.notna(row.get('income16')) else None
        income = format_income_bracket(income_code) if income_code and income_code > 0 else 'Unknown'

        # Format political/religious
        polviews = format_value('polviews', int(row['polviews'])) if pd.notna(row.get('polviews')) else 'Unknown'
        partyid = format_value('partyid', int(row['partyid'])) if pd.notna(row.get('partyid')) else 'Unknown'

        relig_code = int(row.get('relig', -1)) if pd.notna(row.get('relig')) else None
        religion = RELIG_LABELS.get(relig_code, 'Unknown') if relig_code is not None else 'Unknown'

        attend = format_value('attend', int(row['attend'])) if pd.notna(row.get('attend')) else 'Unknown'

        # Format issue attitudes
        issue_attitudes = self._format_issue_attitudes(row)

        return WRITER_USER_TEMPLATE.format(
            age=age,
            age_group=age_group,
            sex=sex,
            race=race,
            region=region,
            education=education,
            employment=employment,
            marital=marital,
            income=income,
            polviews=polviews,
            partyid=partyid,
            religion=religion,
            attend=attend,
            issue_attitudes=issue_attitudes
        )

    def _format_issue_attitudes(self, row: pd.Series) -> str:
        """Format issue attitude variables into readable text."""
        attitudes = []

        # National spending priorities
        spending_vars = {
            'natenvir': 'Environment protection',
            'natheal': 'Healthcare',
            'natfare': 'Welfare programs',
            'nateduc': 'Education',
            'natrace': 'Improving conditions for Black Americans',
            'natcity': 'Solving big city problems'
        }

        for var, label in spending_vars.items():
            if pd.notna(row.get(var)):
                code = int(row[var])
                value = SPENDING_LABELS.get(code, 'Unknown')
                attitudes.append(f"- {label} spending: {value}")

        # Binary issues
        binary_issues = {
            'cappun': ('Death penalty', {1: 'Favor', 2: 'Oppose'}),
            'gunlaw': ('Gun permits required', {1: 'Favor', 2: 'Oppose'}),
            'abany': ('Abortion for any reason', {1: 'Yes', 2: 'No'}),
            'grass': ('Marijuana legalization', {1: 'Legal', 2: 'Not legal'})
        }

        for var, (label, mapping) in binary_issues.items():
            if pd.notna(row.get(var)):
                code = int(row[var])
                value = mapping.get(code, 'Unknown')
                attitudes.append(f"- {label}: {value}")

        # Scale issues
        if pd.notna(row.get('homosex')):
            homosex_map = {1: 'Always wrong', 2: 'Almost always wrong',
                          3: 'Sometimes wrong', 4: 'Not wrong at all'}
            attitudes.append(f"- Same-sex relations: {homosex_map.get(int(row['homosex']), 'Unknown')}")

        if pd.notna(row.get('eqwlth')):
            # 1=Govt reduce inequality, 7=No govt action
            eqwlth = int(row['eqwlth'])
            if eqwlth <= 3:
                attitudes.append("- Income inequality: Government should reduce differences")
            elif eqwlth >= 5:
                attitudes.append("- Income inequality: Government should not interfere")
            else:
                attitudes.append("- Income inequality: Moderate position")

        if not attitudes:
            return "No specific issue positions recorded."

        return "\n".join(attitudes)

    def _parse_response(self, response: str, row: pd.Series) -> dict:
        """Parse the LLM response into a persona dictionary."""
        # Try to extract JSON from the response
        try:
            original_response = response  # Keep for debugging

            # Handle potential markdown code blocks
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]

            # Try to find JSON object in the response
            # Look for { and } to extract just the JSON part
            if '{' in response and '}' in response:
                start = response.find('{')
                # Find matching closing brace
                end = response.rfind('}') + 1
                response = response[start:end]

            persona = json.loads(response.strip())

            # Validate required fields
            required = ['name', 'system_prompt', 'background_summary', 'key_values']
            for field in required:
                if field not in persona:
                    raise ValueError(f"Missing required field: {field}")

            return persona

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response preview (first 500 chars): {original_response[:500]}")
            logger.error(f"Response preview (last 200 chars): {original_response[-200:]}")
            return self._create_fallback_persona(row)

    def _create_fallback_persona(self, row: pd.Series) -> dict:
        """Create a basic fallback persona if LLM generation fails."""
        age = int(row.get('age', 40)) if pd.notna(row.get('age')) else 40
        sex = format_value('sex', int(row['sex'])) if pd.notna(row.get('sex')) else 'Person'
        polviews = format_value('polviews', int(row['polviews']), simplified=True) if pd.notna(row.get('polviews')) else 'Moderate'
        region = REGION_LABELS.get(int(row.get('region', 5)), 'the United States') if pd.notna(row.get('region')) else 'the United States'

        # Generate a simple name
        names_by_sex = {
            'Male': ['James', 'Michael', 'Robert', 'David', 'William', 'John'],
            'Female': ['Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Susan']
        }
        import random
        name = random.choice(names_by_sex.get(sex, ['Alex', 'Jordan', 'Taylor']))

        return {
            'name': name,
            'system_prompt': f"""You are {name}, a {age}-year-old from {region}. Your political outlook is generally {polviews.lower()}.

During this assembly, you will share your perspective on policy issues based on your values and life experiences. Listen carefully to others, engage respectfully with different viewpoints, and remain open to evidence while staying true to your core beliefs.

Keep your responses concise and natural. You are a thoughtful citizen, not a political expert.""",
            'background_summary': f"{name} is a {age}-year-old from {region} with {polviews.lower()} political views.",
            'key_values': ['community', 'fairness', 'common sense'],
            'demographic_tags': [polviews, region]
        }

    def _extract_gss_data(self, row: pd.Series) -> dict:
        """Extract relevant GSS variables for storage."""
        gss_vars = [
            'year', 'id', 'age', 'sex', 'race', 'region', 'educ', 'degree',
            'marital', 'wrkstat', 'income16', 'polviews', 'partyid',
            'relig', 'attend'
        ]

        data = {}
        for var in gss_vars:
            if var in row.index and pd.notna(row[var]):
                data[var] = int(row[var]) if isinstance(row[var], (float, int)) else str(row[var])

        return data

    def _assign_bot_last_names(self, personas: list[dict]) -> list[dict]:
        """
        Assign unique bot/tech/sci-fi themed last names to personas.
        Ensures no duplicate full names.

        Args:
            personas: List of persona dicts with 'name' field (first name only)

        Returns:
            Updated personas with "FirstName LastName" format
        """
        # Shuffle last names for variety
        available_last_names = BOT_LAST_NAMES.copy()
        random.shuffle(available_last_names)

        used_full_names = set()
        last_name_index = 0

        for persona in personas:
            first_name = persona['name']

            # Find a last name that creates a unique full name
            attempts = 0
            max_attempts = len(BOT_LAST_NAMES)

            while attempts < max_attempts:
                last_name = available_last_names[last_name_index % len(available_last_names)]
                full_name = f"{first_name} {last_name}"

                if full_name not in used_full_names:
                    persona['name'] = full_name
                    used_full_names.add(full_name)
                    last_name_index += 1
                    break

                last_name_index += 1
                attempts += 1

            # If we somehow exhaust all options (very unlikely), add a number
            if attempts >= max_attempts:
                full_name = f"{first_name} {available_last_names[0]}-{len(used_full_names)}"
                persona['name'] = full_name
                used_full_names.add(full_name)

        return personas


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def generate_personas_from_sample(
    df: pd.DataFrame,
    max_concurrent: int = 5
) -> list[dict]:
    """
    Generate personas from a sampled DataFrame.

    Args:
        df: DataFrame with GSS respondents (from sampler)
        max_concurrent: Max concurrent LLM calls

    Returns:
        List of persona dictionaries ready for use as agents
    """
    generator = PersonaGenerator()
    return await generator.generate_batch(df, max_concurrent=max_concurrent)


def generate_personas_sync(df: pd.DataFrame) -> list[dict]:
    """Synchronous wrapper for persona generation."""
    return asyncio.run(generate_personas_from_sample(df))
