# Claude Code Guide: Silicon Citizens' Assembly

This document helps AI assistants (like you!) understand and work on this codebase effectively.

## Project Overview

**Silicon Citizens' Assembly** is a multi-agent LLM deliberative democracy simulation system. It creates AI personas from real General Social Survey (GSS) data and orchestrates structured policy deliberation.

**Current Status**: Phase 2 complete (Full backend with deliberation engine working)
**Working Directory**: `/Users/paulmelman/Claude/Assembly Sim/assemblysim`

## Quick Context

### What We've Built (Phase 0-2)

**Phase 1 - Citizen Forge:**
1. **GSS Data Pipeline**: Load and parse 567MB Stata file with 72k respondents
2. **Stratified Sampling**: Select representative citizens matching US demographics
3. **Persona Generation**: LLM converts GSS rows → rich, nuanced character profiles
4. **Bot Naming**: Assigns tech/sci-fi themed last names (Turing, Gibson, Trinity, etc.)
5. **Validation**: Anti-stereotype checks, quality metrics, diversity analysis

**Phase 2 - Core Backend:**
1. **FastAPI Application**: REST API with WebSocket support
2. **SQLite Database**: SQLAlchemy models for assemblies, citizens, messages, reports
3. **Deliberation Engine**: Multi-agent orchestration without LangGraph
4. **Agent System**: Citizen, Moderator, and Recorder agents
5. **Perplexity Integration**: Research briefing books + follow-up research between rounds
6. **Prompt Configuration**: YAML-based prompt management
7. **Per-Round Prompts**: Custom themes and moderator instructions for each round
8. **Settings Management**: Persistent defaults for assembly configuration

### What's Next (Phase 3+)

- LangGraph integration (optional enhancement)
- Group-based deliberation (currently all citizens together)
- Next.js frontend for real-time viewing
- Enhanced fact-checking and citations

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
│   │   ├── prompt_loader.py           # Loads prompts from prompts.yaml
│   │   ├── prompts.yaml               # All system prompts (YAML config)
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── data/
│   │   │   ├── gss_loader.py          # GSSLoader: loads Stata files
│   │   │   └── gss_labels.py          # Label mappings for GSS variables
│   │   ├── citizen_forge/
│   │   │   ├── sampler.py             # StratifiedSampler: quota-based sampling
│   │   │   ├── persona_generator.py   # PersonaGenerator: LLM generation
│   │   │   └── validator.py           # PersonaValidator: quality checks
│   │   ├── models/
│   │   │   ├── database.py            # SQLAlchemy engine, session management
│   │   │   ├── models.py              # DB models (Assembly, Citizen, Message, etc.)
│   │   │   └── schemas.py             # Pydantic schemas for API
│   │   ├── api/
│   │   │   ├── assemblies.py          # REST API endpoints
│   │   │   ├── websocket.py           # WebSocket for real-time updates
│   │   │   └── services.py            # Background tasks, business logic
│   │   ├── agents/
│   │   │   ├── citizen_agent.py       # CitizenAgent: deliberation behavior
│   │   │   ├── moderator_agent.py     # ModeratorAgent: facilitation
│   │   │   └── recorder_agent.py      # RecorderAgent: summarization
│   │   ├── knowledge/
│   │   │   └── perplexity_client.py   # Perplexity API for briefings
│   │   └── orchestration/
│   │       └── deliberation_engine.py # Main deliberation workflow
│   ├── demo_citizen_forge.py          # Phase 1 demo (persona generation only)
│   ├── demo_deliberation.py           # Phase 2 demo (full deliberation)
│   ├── demo_verbose.py                # Demo with LLM logging
│   ├── assemblysim.db                 # SQLite database (gitignored)
│   ├── DELIBERATION_GUIDE.md          # API usage guide
│   ├── PROMPTS_GUIDE.md               # Prompt customization guide
│   └── requirements.txt               # Python dependencies
└── README.md                          # Main documentation
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

### Phase 1 Files (Persona Generation)

#### `config.py` - Configuration System
- Uses pydantic-settings with `.env` file at `assemblysim/.env`
- Model selection: WRITER_MODEL, CITIZEN_MODEL, MODERATOR_MODEL, UTILITY_MODEL
- Database URL, API keys, LLM parameters
- Research defaults: DEFAULT_MAX_RESEARCH_CALLS_PER_ROUND, DEFAULT_MAX_RESEARCH_TOKENS_PER_CALL
- ENABLE_FACT_CHECKING=False (currently disabled)

#### `gss_loader.py` - Data Loading
- `GSSLoader.load(years=None)` returns pandas DataFrame
- Only loads ~45 CORE_VARIABLES to save memory
- Always check for NaN values with `pd.notna()`

#### `sampler.py` - Stratified Sampling
- `StratifiedSampler(target_n=40).sample(strategy='stratified')`
- DEFAULT_QUOTAS for political/race/age balance
- Returns representative sample from GSS

#### `persona_generator.py` - LLM Persona Creation
- Uses `get_writer_prompt()` from prompt_loader
- `generate_batch(df)` creates personas from GSS rows
- Assigns bot-themed last names
- Returns list of persona dicts with name, system_prompt, key_values, etc.

### Phase 2 Files (Backend & Deliberation)

#### `main.py` - FastAPI Application
- FastAPI app with CORS middleware
- Includes assemblies_router and websocket_router
- Health check at `/health`
- Lifespan events for database initialization

#### `models/database.py` - Database Layer
- SQLAlchemy engine with SQLite
- `get_db()` dependency for FastAPI routes
- `get_db_session()` context manager for background tasks
- `init_db()` creates all tables

#### `models/models.py` - Database Models
- **Assembly**: topic, status, num_citizens, round_prompts, research config
- **Citizen**: name, system_prompt, gss_data, final_vote
- **DeliberationGroup**: group assignments, summaries
- **Message**: deliberation transcript (role, content, phase, round)
- **BriefingBook**: Perplexity research content
- **RoundResearch**: follow-up research queries, results, sources (new)
- **AppSettings**: persistent defaults singleton (new)
- **Report**: executive summary, vote tally, themes
- **AssemblyStatus** enum: PENDING → GENERATING_CITIZENS → CITIZENS_READY → READY → DELIBERATING → VOTING → COMPLETED

#### `models/schemas.py` - Pydantic Schemas
- Request schemas: AssemblyCreateRequest (with round_prompts, research config), BriefingGenerateRequest, AppSettingsUpdateRequest
- Response schemas: AssemblyResponse, CitizenResponse, ReportResponse, RoundResearchResponse, AppSettingsResponse
- RoundPromptConfig for per-round themes/prompts
- WSMessage for WebSocket communication (includes research_complete type)

#### `api/assemblies.py` - REST Endpoints
- POST /assemblies - Create assembly, start citizen generation
- GET /assemblies/{id} - Get assembly details (includes round_research)
- POST /assemblies/{id}/briefing - Generate briefing book
- POST /assemblies/{id}/start - Start deliberation
- GET /assemblies/{id}/messages - Get transcript
- GET /assemblies/{id}/report - Get final report
- GET /assemblies/{id}/research - List follow-up research

#### `api/settings.py` - Settings Endpoints (new)
- GET /settings - Get persistent assembly defaults
- PUT /settings - Update defaults (partial updates supported)

#### `api/websocket.py` - Real-time Updates
- `ConnectionManager` class manages WebSocket connections
- `/ws/assemblies/{id}` endpoint for real-time updates
- `broadcast_to_assembly()` function for status updates

#### `api/services.py` - Background Tasks
- `create_assembly_with_citizens()` - Generate personas in background
- `generate_briefing_for_assembly()` - Perplexity research
- `run_deliberation_for_assembly()` - Full deliberation workflow

#### `orchestration/deliberation_engine.py` - Main Workflow
- `DeliberationEngine` class orchestrates complete assembly
- Flow: Opening → Rounds (with research between) → Voting → Report
- Each round: Moderator opens (with custom theme/prompt) → Citizens respond → Recorder summarizes
- Between rounds: Generates research queries from transcript, calls Perplexity, injects results
- Saves all messages to database
- Broadcasts updates via WebSocket

#### `agents/citizen_agent.py` - Citizen Behavior
- `CitizenAgent(citizen_id, name, system_prompt, briefing_content)`
- `respond(discussion_context)` - Generate deliberation response
- `cast_vote(recommendations)` - Vote with reasoning
- Uses `get_citizen_instructions()` from prompt_loader

#### `agents/moderator_agent.py` - Facilitation
- `ModeratorAgent(assembly_topic)`
- `open_assembly()`, `open_round()`, `prompt_citizen()`
- `transition_to_voting()`, `close_assembly()`
- Uses `get_moderator_prompt()` from prompt_loader

#### `agents/recorder_agent.py` - Analysis
- `RecorderAgent(assembly_topic)`
- `summarize_round()` - Round summaries
- `identify_themes()`, `generate_consensus_summary()`
- `generate_final_summary()` - Complete report
- Uses `get_recorder_prompt()` from prompt_loader

#### `knowledge/perplexity_client.py` - Research
- `PerplexityClient().generate_briefing_book(topic, depth)`
- `research_query(query, max_tokens)` - focused follow-up research between rounds
- Generalized markdown builder handles any JSON structure from Perplexity
- Returns structured briefing with sources and citations
- Fallback mode when API unavailable
- Uses `get_perplexity_prompt()` from prompt_loader

#### `prompt_loader.py` - Prompt Management
- Loads all system prompts from `prompts.yaml`
- `get_writer_prompt()`, `get_moderator_prompt()`, etc.
- Cached with @lru_cache for performance

#### `prompts.yaml` - Prompt Configuration
- All static system prompts in one YAML file
- Sections: writer, moderator, recorder, citizen, perplexity
- Edit without touching code!

## Model Configuration

The system uses different models for different tasks (configured in `.env`):

```bash
WRITER_MODEL=anthropic/claude-sonnet-4.5      # Persona generation (needs good JSON)
CITIZEN_MODEL=qwen/qwen3-235b-a22b-2507        # Deliberation (thinking/reasoning)
MODERATOR_MODEL=anthropic/claude-sonnet-4.5    # Facilitation (neutral, clear)
UTILITY_MODEL=openai/gpt-4o-mini               # Summaries (fast, cheap)
```

Use `get_llm_client(purpose="writer")` to get the right model for each task.

## Common Workflows

### Creating an Assembly

```python
# 1. Create assembly record
assembly = Assembly(topic="Topic", num_citizens=8, status=AssemblyStatus.PENDING)
db.add(assembly)
db.commit()

# 2. Generate citizens in background
background_tasks.add_task(create_assembly_with_citizens, assembly.id, 8, 2, "stratified")

# 3. Status transitions:
# PENDING → GENERATING_CITIZENS → CITIZENS_READY

# 4. Optionally generate briefing
await generate_briefing_for_assembly(assembly.id)
# CITIZENS_READY → GENERATING_BRIEFING → READY

# 5. Start deliberation
await run_deliberation_for_assembly(assembly.id)
# READY → DELIBERATING → VOTING → COMPLETED
```

### Running Deliberation

```python
engine = DeliberationEngine(assembly_id, db, broadcast_callback)
await engine.run()

# Flow:
# 1. Load assembly, citizens, briefing
# 2. Initialize agents (moderator, citizens, recorder)
# 3. Opening (moderator welcomes)
# 4. For each round:
#    - Moderator opens round
#    - Each citizen responds (with context)
#    - Recorder summarizes
# 5. Voting:
#    - Moderator transitions
#    - Each citizen casts vote
# 6. Report generation:
#    - Recorder generates final summary
# 7. Complete
```

### Customizing Prompts

```yaml
# Edit backend/app/prompts.yaml
moderator:
  system: |
    You are a skilled facilitator...
    [Your custom instructions]
```

Changes take effect on next restart. See `PROMPTS_GUIDE.md` for details.

## Development Patterns

### Database Sessions

**In API routes:**
```python
@router.get("/assemblies/{id}")
def get_assembly(id: int, db: Session = Depends(get_db)):
    assembly = db.query(Assembly).filter(Assembly.id == id).first()
    return assembly
```

**In background tasks:**
```python
async def background_task():
    with get_db_session() as db:
        # Auto-commits on success, rollbacks on error
        assembly = db.query(Assembly).filter(...).first()
```

### NaN Handling

GSS data has many NaN values:

```python
# ❌ BAD
age = int(row['age'])

# ✅ GOOD
age = int(row['age']) if pd.notna(row.get('age')) else None
```

### Async/Await

All LLM calls and deliberation are async:

```python
# Agent responses
response = await citizen.respond(context)

# Deliberation
await run_deliberation(assembly_id, db)

# From sync context
import asyncio
asyncio.run(some_async_function())
```

### WebSocket Broadcasting

```python
from app.api.websocket import broadcast_to_assembly

await broadcast_to_assembly(assembly_id, {
    "type": "status_update",
    "status": "deliberating",
    "message": "Round 1 starting..."
})
```

## Testing & Debugging

### Quick Tests

```bash
# Test imports
python -c "from app.main import app; print('OK')"

# Test prompts
python -c "from app.prompt_loader import get_moderator_prompt; print(get_moderator_prompt()[:100])"

# Test database
python -c "from app.models.database import init_db; init_db(); print('OK')"
```

### Run Full Demo

```bash
# Quick (6 citizens, 2 rounds, ~5 min)
python demo_deliberation.py --mode quick

# Full (8 citizens, 3 rounds, with briefing, ~10 min)
python demo_deliberation.py --mode full

# With verbose LLM logging
python demo_verbose.py --mode quick
```

### API Testing

```bash
# Start server
uvicorn app.main:app --reload

# Create assembly
curl -X POST http://localhost:8000/assemblies \
  -H "Content-Type: application/json" \
  -d '{"topic": "Test", "num_citizens": 6}'

# Check status
curl http://localhost:8000/assemblies/1

# Start deliberation (after status is READY)
curl -X POST http://localhost:8000/assemblies/1/start
```

## Important Gotchas

### 1. .env Location
`.env` is at `assemblysim/.env`, **NOT** `assemblysim/backend/.env`

### 2. Working Directory
Always run from `assemblysim/backend/`:
```bash
cd /Users/paulmelman/Claude/Assembly\ Sim/assemblysim/backend
```

### 3. Model Names
OpenRouter uses format: `provider/model-name`
```bash
CITIZEN_MODEL=qwen/qwen3-235b-a22b-2507  # ✅
CITIZEN_MODEL=qwen3-235b  # ❌
```

### 4. Database File
SQLite DB is at `backend/assemblysim.db` (gitignored)

### 5. Prompt Caching
Prompts are cached with `@lru_cache()`. To reload, restart the app.

### 6. Background Tasks
Background tasks use their own database sessions via `get_db_session()`, not `get_db()`

### 7. Empty LLM Responses
Some models (especially thinking models) may return content in different fields. Check the LLM client logging if responses seem empty.

## Success Metrics

Phase 2 is successful when:
- ✅ API server starts without errors
- ✅ Demo runs complete deliberation
- ✅ Citizens generated from GSS data
- ✅ Deliberation produces transcript and report
- ✅ Database saves all data correctly
- ✅ WebSocket broadcasts status updates
- ✅ Prompts load from YAML

All metrics currently met! 🎉

## Resources

- **Main README**: `../README.md`
- **Design Doc**: `../Silicon Assembly - Design Document.md`
- **Development Plan**: `../DEVELOPMENT_PLAN.md`
- **Deliberation Guide**: `DELIBERATION_GUIDE.md`
- **Prompts Guide**: `PROMPTS_GUIDE.md`
- **GSS Docs**: `../data/GSS_stata/claude_summary.txt`

## Questions to Ask User

When unclear, ask about:

1. **Models**: Which model for which task?
2. **Prompts**: Should we adjust agent behavior?
3. **Features**: Add groups, fact-checking, etc.?
4. **Performance**: Fewer citizens for speed?
5. **Next Steps**: Frontend, LangGraph, or enhancements?

---

**TL;DR for Claude**: Phase 2 complete! Full FastAPI backend with deliberation engine. Citizens deliberate, vote, generate reports. Prompts in YAML. Run `python demo_deliberation.py --mode quick` to see it in action. Next: frontend or advanced features.
