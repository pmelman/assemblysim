"""
Citizen Forge Module

The Citizen Forge transforms GSS survey data into rich LLM personas
for the Silicon Citizens' Assembly.

Components:
- sampler: Stratified sampling to ensure demographic representation
- persona_generator: Writer LLM that creates natural language personas
- validator: Quality checks on generated personas
"""

from .sampler import StratifiedSampler, sample_citizens
from .persona_generator import (
    PersonaGenerator,
    generate_personas_from_sample,
    generate_personas_sync
)
from .validator import PersonaValidator, validate_personas

__all__ = [
    'StratifiedSampler',
    'sample_citizens',
    'PersonaGenerator',
    'generate_personas_from_sample',
    'generate_personas_sync',
    'PersonaValidator',
    'validate_personas'
]
