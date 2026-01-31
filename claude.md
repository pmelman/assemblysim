# Claude Code Guide: Silicon Citizens' Assembly

This document helps AI assistants (like you!) understand and work on this codebase effectively.

## Project Overview

**Silicon Citizens' Assembly** is a multi-agent LLM deliberative democracy simulation system. It creates AI personas from real General Social Survey (GSS) data and orchestrates structured policy deliberation.

**Current Status**: Phase 1 complete (Citizen Forge working)
**Working Directory**: `/Users/paulmelman/Claude/Assembly Sim/assemblysim`

## Quick Context

### What We've Built (Phase 0-1)

1. **GSS Data Pipeline**: Load and parse 567MB Stata file with 72k respondents
2. **Stratified Sampling**: Select representative citizens matching US demographics
3. **Persona Generation**: LLM converts GSS rows → rich, nuanced character profiles
4. **Bot Naming**: Assigns tech/sci-fi themed last names (Turing, Gibson, Trinity, etc.)
5. **Validation**: Anti-stereotype checks, quality metrics, diversity analysis

### What's Next (Phase 2+)

- FastAPI backend with PostgreSQL
- LangGraph multi-agent deliberation system
- Perplexity integration for research briefings
- Next.js frontend for real-time viewing

## Architecture Map

### Directory Structure

```
assemblysim/                           # Project root (working directory)
├── .env                               # API keys (CRITICAL: gitignored)
├── .env.example                       # Template for .env
├── backend/
│   ├── app/
│   │   ├── config.py                  # Pydantic settings, loads from ../.env
│   │   ├── llm_client.py              # Unified LLM client (OpenRouter/OpenAI/Anthropic)
│   │   ├── data/
│   │   │   ├── gss_loader.py          # GSSLoader: loads Stata files
│   │   │   └── gss_labels.py          # Label mappings for GSS variables
│   │   └── citizen_forge/
│   │       ├── __init__.py            # Module exports
│   │       ├── sampler.py             # StratifiedSampler: quota-based sampling
│   │       ├── persona_generator.py   # PersonaGenerator: LLM generation
│   │       └── validator.py           # PersonaValidator: quality checks
│   ├── demo_citizen_forge.py          # Main demo script (RUNNABLE)
│   └── requirements.txt               # Python dependencies
└── README.md                          # Human documentation
```

### Data Location (External)

```
../data/                               # One level up from assemblysim/
└── GSS_stata/
    ├── gss7224_r2.dta                 # 567MB Stata file (GSS 1972-2024)
    ├── claude_summary.txt             # GSS data documentation
    └── GSS 2024 Codebook R2.pdf       # Official codebook
```

## Key Files Deep Dive

### `config.py` - Configuration System

**Purpose**: Centralized settings using pydantic-settings

**Important Details**:
- `.env` file is at `assemblysim/.env` (one level up from backend/)
- Config class has `env_file = Path(__file__).parent.parent.parent / ".env"`
- Uses `@lru_cache()` for `get_settings()` singleton pattern
- GSS data path is relative: `DATA_DIR / "GSS_stata" / "gss7224_r2.dta"`

**Key Settings**:
```python
LLM_PROVIDER: str = "openrouter"  # or "openai", "anthropic"
OPENROUTER_API_KEY: str
WRITER_MODEL: str = "anthropic/claude-3.5-sonnet"
WRITER_MAX_TOKENS: int = 1000
DEFAULT_NUM_CITIZENS: int = 40
```

### `gss_loader.py` - Data Loading

**Purpose**: Load and validate GSS Stata files

**Key Class**: `GSSLoader`
- `CORE_VARIABLES`: List of ~45 GSS variables we use
- `load(years=None)`: Returns pandas DataFrame
- `validate_data()`: Checks for required columns

**Important**:
- GSS data is HUGE (72k rows, 6,904 vars)
- We only load CORE_VARIABLES to save memory
- Use `years=[2022]` to filter to recent data
- NaN values are common - always use `pd.notna()` checks

### `gss_labels.py` - Variable Mappings

**Purpose**: Human-readable labels for GSS coded values

**Key Functions**:
- `format_value(variable, code)`: Gets label for a code
- `get_age_group(age)`: Converts age → age group string
- `format_income_bracket(code)`: Income code → "$X - $Y"

**Key Dicts**:
- `POLVIEWS_LABELS`: 1=Extremely Liberal ... 7=Extremely Conservative
- `SEX_LABELS`, `RACE_LABELS`, `REGION_LABELS`, etc.

### `sampler.py` - Stratified Sampling

**Purpose**: Select representative citizens from GSS data

**Key Class**: `StratifiedSampler`
- `DEFAULT_QUOTAS`: Target distributions for political/race/age groups
- `prepare_data()`: Cleans and groups GSS data
- `sample(strategy='stratified')`: Returns sampled DataFrame

**Sampling Strategies**:
- `'stratified'`: Proportional to quotas (default)
- `'quota'`: Exact quota matching
- `'random'`: Pure random sampling

**Usage Pattern**:
```python
sampler = StratifiedSampler(gss_data=df, target_n=40)
sampler.prepare_data()
sample_df = sampler.sample(strategy='stratified', seed=42)
```

### `persona_generator.py` - LLM Persona Creation

**Purpose**: Convert GSS rows into rich LLM personas

**Key Class**: `PersonaGenerator`

**Main Methods**:
- `generate_persona(row)`: Single persona from GSS Series
- `generate_batch(df, max_concurrent=5)`: Batch generation with rate limiting
- `_assign_bot_last_names(personas)`: Add unique sci-fi/tech last names

**Bot Last Names**:
- List of ~60 tech/sci-fi themed surnames
- Computing pioneers: Turing, Lovelace, Hopper, Shannon, Dijkstra
- Sci-fi refs: Asimov, Gibson, Deckard, Trinity, Muad'Dib
- Tech terms: Protocol, Neural, Matrix, Quantum, Circuit
- Ensures no duplicate full names

**LLM Prompts**:
- `WRITER_SYSTEM_PROMPT`: Instructions for persona creation
  - Emphasizes values over stereotypes
  - Warns against accents, dialects, caricatures
  - Requests 200-400 word system prompts
- `WRITER_USER_TEMPLATE`: Formats GSS data for LLM

**Output Format**:
```python
{
    "name": "Marcus Shannon",  # First name from LLM + bot last name
    "system_prompt": "You are Marcus...",  # 200-400 words
    "background_summary": "Marcus is...",  # 2-3 sentences
    "key_values": ["Evidence-based", "Pragmatic", ...],  # 2-5 values
    "demographic_tags": ["Moderate", "Midwest", ...],
    "gss_data": {...}  # Original GSS variables
}
```

**Error Handling**:
- Falls back to `_create_fallback_persona()` if LLM fails
- Parses JSON from LLM response (handles markdown code blocks)
- Validates required fields

### `validator.py` - Quality Assurance

**Purpose**: Ensure personas are high-quality and non-stereotypical

**Key Class**: `PersonaValidator`

**Stereotype Detection**:
- `STEREOTYPE_PATTERNS`: Regex list for problematic language
- Catches: accents ("y'all", "ain't"), stereotypes ("gun-toting"), caricatures

**Validation Checks**:
- Required fields present (`name`, `system_prompt`, `background_summary`, `key_values`)
- System prompt length (50-600 words)
- Mentions deliberation context
- References persona's values
- No stereotype patterns
- Reasonable number of key values (2-5)

**Batch Validation**:
- `validate_batch(personas)`: Returns pass rate, issues list
- `check_diversity(personas)`: Checks name uniqueness, value diversity

**Usage**:
```python
result = validate_personas(personas)
# Returns: {'validation': {...}, 'diversity': {...}}
```

### `llm_client.py` - LLM API Client

**Purpose**: Unified interface for multiple LLM providers

**Key Class**: `LLMClient`

**Supported Providers**:
- OpenRouter (default): Proxy for many models
- OpenAI: Direct GPT-4, GPT-4o, etc.
- Anthropic: Direct Claude models

**Main Method**:
```python
async def complete(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> str
```

**Provider Detection**:
- Uses `settings.LLM_PROVIDER` ("openrouter", "openai", "anthropic")
- Falls back based on which API keys are set
- OpenRouter uses OpenAI-compatible format

**Factory Function**:
```python
get_llm_client(purpose="writer")
# Returns configured LLMClient instance
# Purpose can be: "writer", "citizen", "utility"
```

### `demo_citizen_forge.py` - Demo Script

**Purpose**: End-to-end demo of Phase 1 pipeline

**CLI Arguments**:
- `--num-citizens N`: Number to generate (default: 8)
- `--dry-run`: Skip LLM calls, show sampling only
- `--seed N`: Random seed for reproducibility
- `--verbose`: Show full system prompts

**Workflow**:
1. Load GSS 2022 data
2. Stratified sampling
3. Generate personas (LLM calls)
4. Display results
5. Validate quality
6. Save to `demo_personas.json`

**Usage**:
```bash
cd backend
python demo_citizen_forge.py --num-citizens 8
```

## Development Patterns

### NaN Handling in Pandas

**CRITICAL**: GSS data has many NaN values. Always check:

```python
# ❌ BAD - will crash on NaN
age = int(row['age'])

# ✅ GOOD - safe conversion
age = int(row['age']) if pd.notna(row.get('age')) else 'Unknown'

# ✅ BETTER - helper function
def safe_int(val):
    if pd.isna(val):
        return None
    return int(val)

age_val = safe_int(row.get('age'))
age = str(age_val) if age_val else 'Unknown'
```

### Async/Await for LLM Calls

All LLM operations are async:

```python
# Single call
persona = await generator.generate_persona(row)

# Batch with concurrency limit
personas = await generator.generate_batch(df, max_concurrent=3)

# From sync context
personas = asyncio.run(generate_personas_from_sample(df))
```

### Configuration Access

Always use the singleton pattern:

```python
from app.config import get_settings

settings = get_settings()  # Cached, loads .env once
api_key = settings.OPENROUTER_API_KEY
```

### Error Handling Philosophy

- **LLM failures**: Fallback to simple persona, don't crash
- **Data issues**: Log warnings, use "Unknown" for missing values
- **Validation failures**: Track warnings, only fail on critical errors

## Common Tasks

### Add a New GSS Variable

1. Add to `CORE_VARIABLES` in `gss_loader.py`
2. Add label mapping to `gss_labels.py` if coded
3. Update `_format_prompt()` in `persona_generator.py`
4. Test with `demo_citizen_forge.py --dry-run`

### Change Sampling Strategy

Edit `DEFAULT_QUOTAS` in `sampler.py`:

```python
DEFAULT_QUOTAS = {
    'polviews_group': {
        'Liberal': 0.40,      # Increase liberal representation
        'Moderate': 0.30,
        'Conservative': 0.30
    },
    # ...
}
```

### Add Bot Last Names

Add to `BOT_LAST_NAMES` list in `persona_generator.py`:

```python
BOT_LAST_NAMES = [
    # ... existing names ...
    'YourNewName',
    'AnotherName',
]
```

### Adjust LLM Temperature

In `.env`:
```bash
TEMPERATURE=0.9  # More creative
TEMPERATURE=0.3  # More consistent
```

Or per-call:
```python
response = await llm.complete(prompt, temperature=0.9)
```

## Testing & Validation

### Quick Test (No API Calls)

```bash
python demo_citizen_forge.py --dry-run
```

Shows sampling without LLM generation.

### Full Test (8 Personas)

```bash
python demo_citizen_forge.py --num-citizens 8
```

Generates 8 personas, saves to `demo_personas.json`.

### Check Output

```bash
cat demo_personas.json | jq '.[0]'  # View first persona
cat demo_personas.json | jq '.[].name'  # List all names
```

### Expected Validation Metrics

- Pass rate: ~95-100%
- Warnings: <5 total
- Unique names: 100%
- Unique values: 20-40
- Political distribution: Balanced

## Important Gotchas

### 1. .env Location

The `.env` file is at `assemblysim/.env`, **NOT** `assemblysim/backend/.env`.

Config file handles this with:
```python
env_file = Path(__file__).parent.parent.parent / ".env"
```

### 2. GSS Data Path

Data is **outside** the assemblysim directory:
```
Assembly Sim/
├── assemblysim/      # Code here
└── data/            # Data here
    └── GSS_stata/
```

Relative path: `../data/GSS_stata/gss7224_r2.dta`

### 3. Working Directory

Always run from `assemblysim/backend/`:
```bash
cd /Users/paulmelman/Claude/Assembly\ Sim/assemblysim/backend
python demo_citizen_forge.py
```

### 4. OpenRouter Model Names

OpenRouter uses format: `provider/model-name`
```python
WRITER_MODEL=anthropic/claude-3.5-sonnet  # ✅ Correct
WRITER_MODEL=claude-3.5-sonnet  # ❌ Wrong
```

### 5. Integer Conversion

GSS data is floats in pandas. Always convert:
```python
code = int(row['polviews']) if pd.notna(row.get('polviews')) else None
```

## Git & Secrets

### NEVER Commit

- `.env` file (has real API keys)
- `demo_personas.json` (output file)
- Any file with actual API keys

### Safe to Commit

- `.env.example` (template only)
- All `.py` files
- `requirements.txt`
- Documentation

## Next Phase Preview (Phase 2)

You'll be working on:

1. **FastAPI Backend**
   - REST API for assembly management
   - WebSocket for real-time updates
   - Database models (PostgreSQL + SQLAlchemy)

2. **LangGraph Integration**
   - Multi-agent orchestration
   - State management for deliberations
   - Agent-to-agent communication

3. **Perplexity Integration**
   - Research briefing generation
   - Fact-checking capabilities
   - Evidence synthesis

## Resources for AI Assistants

- **GSS Variable Docs**: `../data/GSS_stata/claude_summary.txt`
- **Design Doc**: `../Silicon Assembly - Design Document.md`
- **Development Plan**: `../DEVELOPMENT_PLAN.md`
- **Codebook**: `../data/GSS_stata/GSS 2024 Codebook R2.pdf` (large PDF)

## Questions to Ask User

When unclear, ask about:

1. **Sampling**: Should we adjust demographic quotas?
2. **Validation**: Are stereotype checks too strict/loose?
3. **LLM Config**: Which model to use for which purpose?
4. **Output**: What format for saving personas?
5. **Next Steps**: Ready for Phase 2 or refine Phase 1?

## Success Metrics

Phase 1 is successful when:
- ✅ Demo runs without errors
- ✅ 95%+ personas pass validation
- ✅ No duplicate names
- ✅ Diverse values across cohort
- ✅ No stereotypical language detected
- ✅ Output saved to JSON correctly

All metrics currently met! 🎉

---

**TL;DR for Claude**: This is a working LLM agent system. Phase 1 (persona generation) is complete. Demo script works. Key files: `persona_generator.py`, `sampler.py`, `validator.py`. Run `python demo_citizen_forge.py` from backend/ to see it in action. Next phase is backend API infrastructure.
