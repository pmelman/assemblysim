# Silicon Citizens' Assembly 🏛️

A multi-agent LLM system that simulates deliberative democracy using real survey data from the General Social Survey (GSS).

## What Is This?

The Silicon Citizens' Assembly creates AI personas based on real American survey respondents, then brings them together for structured policy deliberation. Each "citizen" is an LLM agent with:

- **Authentic demographics** from GSS data (age, race, region, education, income)
- **Real political views** derived from actual survey responses
- **Nuanced values** that go beyond simple left/right ideology
- **Bot-themed names** like "Marcus Shannon" and "Patricia Berners-Lee" to celebrate our AI heritage

The goal: Explore what happens when diverse perspectives engage in good-faith deliberation, free from the constraints of human time, attention, and social pressure.


### Start the Server

Backend:
```bash
cd backend
uvicorn app.main:app --reload
```
Frontend:
```bash
cd frontend
npm run dev
```

Then visit http://localhost:3000


## Bot-Themed Names 🤖

Each persona gets a sci-fi/tech themed last name to acknowledge their AI nature:

- **Computing Pioneers**: Turing, Lovelace, Hopper, Dijkstra, Shannon
- **Sci-Fi Authors**: Asimov, Gibson, Dick, Stephenson, Clarke
- **Sci-Fi Characters**: Deckard, Ripley, Trinity, Connor, Skywalker
- **Tech Terms**: Protocol, Neural, Matrix, Quantum, Circuit

This creates names like "Marcus Shannon" and "Dorothy Dijkstra" - memorable, fun, and honest about what these agents are.

## Architecture

### Complete System (Phase 1 + 2)

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐  │
│  │ GSS Sampling │───▶│ Persona Gen  │───▶│  Citizens   │  │
│  └──────────────┘    └──────────────┘    └─────────────┘  │
│         │                    │                    │        │
│         ▼                    ▼                    ▼        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              SQLite Database                         │  │
│  │  • Assemblies  • Citizens  • Messages  • Reports     │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                           │       │
│         ▼                                           ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐  │
│  │ Perplexity   │───▶│ Deliberation │───▶│   Report    │  │
│  │ Briefing     │    │ Engine       │    │ Generation  │  │
│  └──────────────┘    └──────────────┘    └─────────────┘  │
│                              │                             │
│                              ▼                             │
│                     ┌────────────────┐                     │
│                     │   WebSocket    │                     │
│                     │  (Real-time)   │                     │
│                     └────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**Data & Personas:**
- **`gss_loader.py`**: Loads GSS Stata files (72k respondents)
- **`sampler.py`**: Stratified sampling for demographic representation
- **`persona_generator.py`**: LLM converts GSS rows → personas
- **`validator.py`**: Quality checks for stereotypes, diversity

**Backend API:**
- **`main.py`**: FastAPI app with CORS, routers, health checks
- **`models/`**: SQLAlchemy database models and Pydantic schemas
- **`api/`**: REST endpoints and WebSocket for real-time updates

**Agents:**
- **`CitizenAgent`**: Persona + briefing → deliberation responses
- **`ModeratorAgent`**: Facilitates discussion, manages flow
- **`RecorderAgent`**: Summarizes rounds, generates reports

**Orchestration:**
- **`deliberation_engine.py`**: Coordinates full assembly workflow
- **`perplexity_client.py`**: Generates research briefings

**Configuration:**
- **`prompts.yaml`**: All system prompts (easy to customize!)
- **`config.py`**: Settings, model selection, API keys

## Model Configuration

The system uses different models for different tasks:

```yaml
# Edit .env to customize
WRITER_MODEL=anthropic/claude-sonnet-4.5      # Persona generation
CITIZEN_MODEL=qwen/qwen3-235b-a22b-2507        # Deliberation
MODERATOR_MODEL=anthropic/claude-sonnet-4.5    # Facilitation
UTILITY_MODEL=openai/gpt-4o-mini               # Summaries
```

**Customize prompts** without touching code:
```bash
nano backend/app/prompts.yaml
```

See `backend/PROMPTS_GUIDE.md` for details.

## Project Structure

```
assemblysim/
├── backend/
│   ├── app/
│   │   ├── config.py                  # Settings & environment
│   │   ├── llm_client.py              # Unified LLM client
│   │   ├── prompt_loader.py           # Loads prompts from YAML
│   │   ├── prompts.yaml               # All system prompts
│   │   ├── main.py                    # FastAPI application
│   │   ├── data/
│   │   │   ├── gss_loader.py          # GSS data loading
│   │   │   └── gss_labels.py          # Variable mappings
│   │   ├── citizen_forge/
│   │   │   ├── sampler.py             # Stratified sampling
│   │   │   ├── persona_generator.py   # LLM generation
│   │   │   └── validator.py           # Quality checks
│   │   ├── models/
│   │   │   ├── database.py            # SQLAlchemy setup
│   │   │   ├── models.py              # DB models
│   │   │   └── schemas.py             # Pydantic schemas
│   │   ├── api/
│   │   │   ├── assemblies.py          # REST endpoints
│   │   │   ├── websocket.py           # Real-time updates
│   │   │   └── services.py            # Business logic
│   │   ├── agents/
│   │   │   ├── citizen_agent.py       # Citizen behavior
│   │   │   ├── moderator_agent.py     # Facilitation
│   │   │   └── recorder_agent.py      # Analysis
│   │   ├── knowledge/
│   │   │   └── perplexity_client.py   # Research briefings
│   │   └── orchestration/
│   │       └── deliberation_engine.py # Main workflow
│   ├── demo_deliberation.py           # Full demo script
│   ├── demo_verbose.py                # With LLM logging
│   ├── requirements.txt
│   ├── DELIBERATION_GUIDE.md          # API usage guide
│   └── PROMPTS_GUIDE.md               # Prompt customization
├── .env                               # API keys (gitignored)
├── .env.example                       # Template
└── README.md                          # This file
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| POST | `/assemblies` | Create assembly (starts citizen generation) |
| GET | `/assemblies` | List all assemblies |
| GET | `/assemblies/{id}` | Get assembly details |
| GET | `/assemblies/{id}/citizens` | List citizens |
| POST | `/assemblies/{id}/briefing` | Generate briefing book |
| POST | `/assemblies/{id}/start` | Start deliberation |
| GET | `/assemblies/{id}/messages` | Get deliberation transcript |
| GET | `/assemblies/{id}/report` | Get final report |
| GET | `/assemblies/{id}/research` | List follow-up research |
| GET | `/settings` | Get persistent assembly defaults |
| PUT | `/settings` | Update assembly defaults |
| WS | `/ws/assemblies/{id}` | Real-time updates |

See `backend/DELIBERATION_GUIDE.md` for detailed API usage.

## Configuration

Create a `.env` file in the `assemblysim/` directory:

```bash
# Required: API keys
OPENROUTER_API_KEY=sk-or-v1-...
PERPLEXITY_API_KEY=pplx-...  # Optional, for briefing books

# Optional: Direct provider keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# LLM Configuration (OpenRouter model IDs)
LLM_PROVIDER=openrouter
WRITER_MODEL=anthropic/claude-sonnet-4.5
CITIZEN_MODEL=qwen/qwen3-235b-a22b-2507
MODERATOR_MODEL=anthropic/claude-sonnet-4.5
UTILITY_MODEL=openai/gpt-4o-mini

# Generation Parameters
TEMPERATURE=0.7
WRITER_MAX_TOKENS=1000

# Assembly Parameters
DEFAULT_NUM_CITIZENS=40
DEFAULT_NUM_GROUPS=5
DEFAULT_NUM_ROUNDS=3

# Follow-up Research (Perplexity between rounds)
DEFAULT_MAX_RESEARCH_CALLS_PER_ROUND=2
DEFAULT_MAX_RESEARCH_TOKENS_PER_CALL=2000

# Features
ENABLE_FACT_CHECKING=False  # Currently disabled

# Database
DATABASE_URL=sqlite:///./assemblysim.db
```

## Data Source

**General Social Survey (GSS) 1972-2024**
- **Source**: NORC at the University of Chicago
- **Size**: 567 MB Stata file, 72k+ respondents, 6,904 variables
- **Location**: `../data/GSS_stata/gss7224_r2.dta`

We use ~45 core variables covering:
- Demographics (age, sex, race, region, education, income)
- Political views (polviews, partyid)
- Religion (relig, attend)
- Issue attitudes (spending priorities, social issues, economic policy)

See `../data/GSS_stata/claude_summary.txt` for detailed documentation.

## Demo Scripts

**Full deliberation:**
```bash
# Quick demo (6 citizens, 2 rounds, ~5 min)
python demo_deliberation.py --mode quick

# Full demo (8 citizens, 3 rounds, with briefing, ~10 min)
python demo_deliberation.py --mode full

# Custom topic
python demo_deliberation.py --topic "Should cities ban single-use plastics?" --citizens 10
```

**With verbose LLM logging:**
```bash
python demo_verbose.py --mode quick
# Shows all prompts and responses
# Logs saved to deliberation_verbose.log
```

**Just test persona generation:**
```bash
python demo_citizen_forge.py --num-citizens 8
```

## Requirements

- **Python 3.9+**
- **OpenRouter API key** (provides access to many models)
- **Perplexity API key** (optional, for research briefings)
- **GSS data file** at `../data/GSS_stata/gss7224_r2.dta`

Python packages (see `requirements.txt`):
- FastAPI, Uvicorn - Web framework
- SQLAlchemy - Database ORM
- Pydantic - Data validation
- Pandas - Data manipulation
- PyYAML - Prompt configuration
- httpx - Async HTTP for LLM APIs


## Resources

- **Design Document**: `../Silicon Assembly - Design Document.md`
- **Development Plan**: `../DEVELOPMENT_PLAN.md`
- **Deliberation Guide**: `backend/DELIBERATION_GUIDE.md`
- **Prompts Guide**: `backend/PROMPTS_GUIDE.md`
- **GSS Documentation**: `../data/GSS_stata/claude_summary.txt`
- **GSS Codebook**: `../data/GSS_stata/GSS 2024 Codebook R2.pdf`
- **Claude.md**: `CLAUDE.md` (AI assistant guide)

## Contributing

This is currently a personal research project. Stay tuned for contribution guidelines!

## License

TBD

## Acknowledgments

- **General Social Survey**: NORC at the University of Chicago
- **OpenRouter**: Unified LLM API access
- **Anthropic, OpenAI, Alibaba**: Claude, GPT, and Qwen models
- **Perplexity**: Research and citations
- **Computing pioneers and sci-fi authors**: For inspiring our bot names! 🤖
