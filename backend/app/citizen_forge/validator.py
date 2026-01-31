"""
Persona Validation Module

Validates generated personas for quality, avoiding stereotypes,
and ensuring consistency with source GSS data.
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Words/phrases that suggest stereotyping
STEREOTYPE_PATTERNS = [
    # Accents and dialects
    r"\by'all\b",
    r"\bain't\b",
    r"\bgonna\b",
    r"\bwanna\b",
    r"speaks with (a|an) .+ accent",
    r"thick .+ accent",
    r"drawl",

    # Cultural stereotypes
    r"typical .+ (conservative|liberal|southerner|northerner)",
    r"like most .+ people",
    r"as you'd expect from",
    r"stereotypical",

    # Caricatures
    r"gun-toting",
    r"tree-hugging",
    r"bleeding heart",
    r"bible-thumping",
    r"snowflake",
    r"redneck",
    r"elitist",
]


class PersonaValidator:
    """
    Validates generated personas for quality and appropriateness.
    """

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, fail on warnings. If False, only fail on errors.
        """
        self.strict = strict
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.stereotype_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in STEREOTYPE_PATTERNS
        ]

    def validate(self, persona: dict) -> dict:
        """
        Validate a single persona.

        Args:
            persona: Persona dictionary with 'name', 'system_prompt', etc.

        Returns:
            Validation result dictionary with 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []

        # Check required fields
        required_fields = ['name', 'system_prompt', 'background_summary', 'key_values']
        for field in required_fields:
            if field not in persona:
                errors.append(f"Missing required field: {field}")
            elif not persona[field]:
                errors.append(f"Empty required field: {field}")

        if errors:
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check system prompt quality
        system_prompt = persona.get('system_prompt', '')
        prompt_issues = self._check_system_prompt(system_prompt)
        errors.extend(prompt_issues['errors'])
        warnings.extend(prompt_issues['warnings'])

        # Check for stereotypes
        stereotype_issues = self._check_stereotypes(system_prompt)
        warnings.extend(stereotype_issues)

        # Check name
        name_issues = self._check_name(persona.get('name', ''))
        warnings.extend(name_issues)

        # Check key values
        key_values = persona.get('key_values', [])
        if len(key_values) < 2:
            warnings.append("Fewer than 2 key values defined")
        if len(key_values) > 5:
            warnings.append("More than 5 key values (may be too many)")

        # Determine validity
        valid = len(errors) == 0
        if self.strict and warnings:
            valid = False

        return {
            'valid': valid,
            'errors': errors,
            'warnings': warnings
        }

    def _check_system_prompt(self, prompt: str) -> dict:
        """Check system prompt for quality issues."""
        errors = []
        warnings = []

        # Length checks
        word_count = len(prompt.split())
        if word_count < 50:
            errors.append(f"System prompt too short ({word_count} words, minimum 50)")
        elif word_count < 100:
            warnings.append(f"System prompt may be too brief ({word_count} words)")
        elif word_count > 600:
            warnings.append(f"System prompt may be too long ({word_count} words)")

        # Must mention deliberation/assembly context
        deliberation_keywords = [
            'deliberat', 'assembly', 'discuss', 'listen', 'perspective',
            'respectful', 'engage', 'evidence', 'values'
        ]
        has_context = any(kw in prompt.lower() for kw in deliberation_keywords)
        if not has_context:
            warnings.append("System prompt doesn't mention deliberation context")

        # Should mention staying true to values
        value_keywords = ['value', 'belief', 'principle', 'conviction']
        has_values = any(kw in prompt.lower() for kw in value_keywords)
        if not has_values:
            warnings.append("System prompt doesn't reference persona's values")

        return {'errors': errors, 'warnings': warnings}

    def _check_stereotypes(self, text: str) -> list[str]:
        """Check for stereotypical language."""
        warnings = []

        for pattern in self.stereotype_regex:
            if pattern.search(text):
                warnings.append(f"Potential stereotype detected: matches pattern '{pattern.pattern}'")

        return warnings

    def _check_name(self, name: str) -> list[str]:
        """Check name for issues."""
        warnings = []

        if not name or len(name) < 2:
            warnings.append("Name is missing or too short")

        # Check for placeholder names
        placeholder_patterns = ['Citizen', 'Person', 'Respondent', 'User', 'Agent']
        if any(p.lower() in name.lower() for p in placeholder_patterns):
            warnings.append(f"Name appears to be a placeholder: {name}")

        return warnings

    def validate_batch(self, personas: list[dict]) -> dict:
        """
        Validate a batch of personas.

        Args:
            personas: List of persona dictionaries

        Returns:
            Batch validation results
        """
        results = []
        valid_count = 0
        error_count = 0
        warning_count = 0

        for i, persona in enumerate(personas):
            result = self.validate(persona)
            result['index'] = i
            result['name'] = persona.get('name', f'Persona {i}')
            results.append(result)

            if result['valid']:
                valid_count += 1
            else:
                error_count += 1

            warning_count += len(result['warnings'])

        return {
            'total': len(personas),
            'valid': valid_count,
            'invalid': error_count,
            'total_warnings': warning_count,
            'pass_rate': valid_count / len(personas) if personas else 0,
            'results': results
        }

    def check_diversity(self, personas: list[dict]) -> dict:
        """
        Check diversity across a batch of personas.

        Args:
            personas: List of persona dictionaries

        Returns:
            Diversity metrics
        """
        # Check for duplicate names
        names = [p.get('name', '') for p in personas]
        unique_names = set(names)
        duplicate_names = len(names) - len(unique_names)

        # Check key value diversity
        all_values = []
        for p in personas:
            all_values.extend(p.get('key_values', []))
        unique_values = set(all_values)

        # Check political diversity (from demographic_tags if available)
        political_tags = []
        for p in personas:
            tags = p.get('demographic_tags', [])
            for tag in tags:
                if any(pol in tag.lower() for pol in ['liberal', 'moderate', 'conservative']):
                    political_tags.append(tag.lower())

        return {
            'unique_names': len(unique_names),
            'duplicate_names': duplicate_names,
            'unique_values': len(unique_values),
            'value_variety': len(unique_values) / len(all_values) if all_values else 0,
            'political_distribution': {
                tag: political_tags.count(tag) for tag in set(political_tags)
            } if political_tags else {}
        }


def validate_personas(
    personas: list[dict],
    strict: bool = False
) -> dict:
    """
    Convenience function to validate a batch of personas.

    Args:
        personas: List of persona dictionaries
        strict: Whether to use strict validation

    Returns:
        Validation results including pass rate and issues
    """
    validator = PersonaValidator(strict=strict)

    batch_result = validator.validate_batch(personas)
    diversity_result = validator.check_diversity(personas)

    # Log summary
    logger.info(f"Validation complete: {batch_result['valid']}/{batch_result['total']} valid")
    logger.info(f"Pass rate: {batch_result['pass_rate']*100:.1f}%")
    logger.info(f"Total warnings: {batch_result['total_warnings']}")

    if diversity_result['duplicate_names'] > 0:
        logger.warning(f"Found {diversity_result['duplicate_names']} duplicate names")

    return {
        'validation': batch_result,
        'diversity': diversity_result
    }
