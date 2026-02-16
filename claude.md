# Claude Code Guide: Silicon Citizens' Assembly

Guide for AI assistants working on this codebase.

## Project Overview

Multi-agent LLM deliberative democracy simulation. Creates AI personas from real GSS survey data and orchestrates structured policy deliberation.

**Working Directory**: `/Users/paulmelman/Claude/Assembly Sim/assemblysim`

## Directory Structure

```
assemblysim/                           # Project root (working directory)
├── .env                               # API keys + auth config (gitignored)
├── backend/
│   ├── app/
│   │   ├── config.py                  # Pydantic settings, loads from ../.env
│   │   ├── llm_client.py              # Unified LLM client (OpenRouter/OpenAI/Anthropic)
│   │   ├── prompt_loader.py           # Loads prompts from prompts.yaml
│   │   ├── prompts.yaml               # All system prompts (YAML config)
│   │   ├── main.py                    # FastAPI app, lifespan, router wiring, admin seed
│   │   ├── data/
│   │   │   ├── gss_loader.py          # GSSLoader: loads Stata files
│   │   │   └── gss_labels.py          # Label mappings for GSS variables
│   │   ├── citizen_forge/
│   │   │   ├── sampler.py             # StratifiedSampler: quota-based sampling
│   │   │   ├── persona_generator.py   # PersonaGenerator: LLM generation
│   │   │   └── validator.py           # PersonaValidator: quality checks
│   │   ├── models/
│   │   │   ├── database.py            # SQLAlchemy engine, session management
│   │   │   ├── models.py              # ORM models (User, InviteCode, Assembly, Citizen, etc.)
│   │   │   └── schemas.py             # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── auth.py                # Auth endpoints, JWT, password hashing, get_current_user
│   │   │   ├── assemblies.py          # Assembly CRUD + citizen/briefing/deliberation endpoints
│   │   │   ├── settings.py            # App defaults endpoints
│   │   │   ├── custom_citizens.py     # Custom citizen template CRUD
│   │   │   ├── websocket.py           # WebSocket real-time updates
│   │   │   └── services.py            # Background tasks (citizen gen, briefing, deliberation)
│   │   ├── agents/
│   │   │   ├── citizen_agent.py       # CitizenAgent: deliberation behavior
│   │   │   ├── moderator_agent.py     # ModeratorAgent: facilitation
│   │   │   ├── recorder_agent.py      # RecorderAgent: summarization
│   │   │   └── stubbornness.py        # Personality traits
│   │   ├── knowledge/
│   │   │   └── perplexity_client.py   # Perplexity API for briefings + follow-up research
│   │   └── orchestration/
│   │       └── deliberation_engine.py # Main deliberation workflow
│   ├── requirements.txt
│   └── assemblysim.db                 # SQLite database (gitignored)
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout with AuthGuard, header nav, UserMenu
│   │   ├── page.tsx                   # Dashboard (assembly list)
│   │   ├── login/page.tsx             # Login page
│   │   ├── register/page.tsx          # Registration with invite code
│   │   ├── account/page.tsx           # Account management, change password
│   │   ├── admin/invite-codes/page.tsx # Admin invite code management
│   │   ├── assemblies/
│   │   │   ├── new/page.tsx           # Create assembly form
│   │   │   └── [id]/page.tsx          # Assembly detail view
│   │   ├── citizens/custom/page.tsx   # Custom citizen templates
│   │   └── settings/page.tsx          # App settings
│   ├── components/
│   │   ├── auth/
│   │   │   ├── AuthGuard.tsx          # Redirects to /login if not authenticated
│   │   │   └── UserMenu.tsx           # Username link + sign out + admin links
│   │   ├── assembly/                  # AssemblyCard, CreateForm, Header, Actions, StatusBadge
│   │   ├── citizen/                   # CitizenCard, Grid, Avatar, DetailModal, VoteIndicator
│   │   ├── deliberation/             # MessageBubble, Thread, RoundDivider, GroupSelector
│   │   ├── briefing/                  # BriefingViewer, SourceList
│   │   ├── report/                    # ReportViewer, RecommendationCard, VoteChart
│   │   └── ui/                        # shadcn/ui base components
│   ├── hooks/                         # useAssemblies, useAssembly, useMessages, useSettings, useWebSocket
│   ├── lib/
│   │   ├── types.ts                   # TypeScript interfaces (mirrors backend schemas)
│   │   ├── api.ts                     # API client with auth headers on all requests
│   │   ├── utils.ts                   # Utility functions
│   │   └── websocket.ts              # WebSocket client with auto-reconnect
│   ├── store/
│   │   ├── authStore.ts               # Zustand: user, token, login/logout, loadFromStorage
│   │   └── deliberationStore.ts       # Zustand: live messages, assembly statuses
│   ├── middleware.ts                  # Next.js middleware
│   └── package.json
└── data/                              # External: GSS data files
    └── GSS_stata/
        └── gss7224_r2.dta             # 567MB Stata file (GSS 1972-2024)
```

## Authentication

JWT-based auth with invite-code registration. Implemented in `api/auth.py`.

- **Admin seed**: On startup, if no users exist, creates admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars
- **get_current_user**: FastAPI dependency injected via `Depends()`. All routers except auth, health, and websocket require it (set in `main.py` via router-level dependencies)
- **Invite codes**: Admin generates codes, new users redeem them during registration
- **Frontend**: `AuthGuard` wraps the app in `layout.tsx`, checks token via `/auth/me` on mount, redirects to `/login` if invalid. Token stored in `localStorage` as `auth_token`
- **API client**: `getAuthHeaders()` in `lib/api.ts` reads token from localStorage and adds `Authorization: Bearer` header to all requests

## Development Patterns

### Database Sessions

**In API routes** — use `get_db()` dependency:
```python
def get_assembly(id: int, db: Session = Depends(get_db)):
```

**In background tasks** — use `get_db_session()` context manager:
```python
with get_db_session() as db:
    # Auto-commits on success, rollbacks on error
```

### LLM Client

Use `get_llm_client(purpose="writer"|"citizen"|"moderator"|"utility")` to get the right model. Models configured in `.env` with OpenRouter format: `provider/model-name`.

### WebSocket Broadcasting

```python
from app.api.websocket import broadcast_to_assembly
await broadcast_to_assembly(assembly_id, {"type": "status_update", ...})
```

### Assembly Status Flow

`PENDING` → `GENERATING_CITIZENS` → `CITIZENS_READY` → `GENERATING_BRIEFING` → `READY` → `DELIBERATING` → `VOTING` → `COMPLETED`

### Deliberation Flow

After citizens and briefing are ready, the deliberation engine runs:

1. **Group Rounds** — Citizens discuss the topic in small groups across multiple rounds
2. **Plenary Round** — Cross-group discussion with all citizens
3. **Proposal Generation** — Each citizen in each group proposes 1-2 policy ideas
4. **Intra-Group Score Voting** — Citizens score all group proposals (1-5), top 2 per group advance
5. **Moderator Deduplication** — Moderator LLM merges similar proposals across groups
6. **Assembly-Wide Score Voting** — Every citizen scores each deduplicated proposal (1-5), proposals averaging >3 pass
7. **Report Generation** — Passing proposals become recommendations; recorder agent generates executive summary, themes, consensus/disagreement summaries, minority report

Key files: `orchestration/deliberation_engine.py` (flow), `agents/citizen_agent.py` (propose_policies, score_vote), `agents/moderator_agent.py` (deduplicate_proposals), `agents/recorder_agent.py` (report generation)

## Important Gotchas

1. **`.env` location**: `assemblysim/.env`, NOT `assemblysim/backend/.env`
2. **Working directory**: Always run backend from `assemblysim/backend/`
3. **Virtual environment**: Install Python packages to the venv at `../venv/`, not system Python. Use `source "/Users/paulmelman/Claude/Assembly Sim/venv/bin/activate"` or `python -m uvicorn` to ensure correct interpreter.
4. **Model names**: OpenRouter format `provider/model-name` (e.g. `qwen/qwen3-235b-a22b-2507`)
5. **SQLite DB**: `backend/assemblysim.db` (gitignored)
6. **Prompt caching**: `@lru_cache()` — restart app to reload prompts
7. **Background tasks**: Use `get_db_session()`, not `get_db()`
8. **GSS NaN values**: Always check `pd.notna()` before casting GSS data
9. **Update DB**: Don't forget to update the DB when you make updates that add new columns
