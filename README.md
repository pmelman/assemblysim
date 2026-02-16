# Silicon Citizens' Assembly

A multi-agent LLM system that simulates deliberative democracy using real survey data from the General Social Survey (GSS).

## What Is This?

The Silicon Citizens' Assembly creates AI personas based on real American survey respondents, then brings them together for structured policy deliberation. Each "citizen" is an LLM agent with:

- **Authentic demographics** from GSS data (age, race, region, education, income)
- **Real political views** derived from actual survey responses
- **Nuanced values** that go beyond simple left/right ideology
- **Bot-themed names** like "Marcus Shannon" and "Patricia Berners-Lee"

The goal: Explore what happens when diverse perspectives engage in good-faith deliberation, free from the constraints of human time, attention, and social pressure.

## Getting Started

### Backend

```bash
cd backend
source ../venv/bin/activate  # or your virtual environment
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On first startup, the admin user is created automatically from `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then visit http://localhost:3000, log in with your admin credentials, and start creating assemblies.

### New User Registration

The app uses invite-code registration. As an admin:
1. Log in and go to **Invite Codes** in the header
2. Generate a code and share it
3. New users register at `/register` with the code

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐  │
│  │ GSS Sampling │───>│ Persona Gen  │───>│  Citizens   │  │
│  └──────────────┘    └──────────────┘    └─────────────┘  │
│         │                    │                    │        │
│         v                    v                    v        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              SQLite Database                         │  │
│  │  Users, Assemblies, Citizens, Messages, Reports      │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                           │      │
│         v                                           v      │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐  │
│  │ Perplexity   │───>│ Deliberation │───>│   Report    │  │
│  │ Briefing     │    │ Engine       │    │ Generation  │  │
│  └──────────────┘    └──────────────┘    └─────────────┘  │
│                              │                             │
│                              v                             │
│                     ┌────────────────┐                     │
│                     │   WebSocket    │                     │
│                     │  (Real-time)   │                     │
│                     └────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────────┐
│                   Next.js Frontend                          │
├─────────────────────────────────────────────────────────────┤
│  Auth (JWT + invite codes) │ Dashboard │ Assembly Detail    │
│  Account Management        │ Settings  │ Custom Citizens    │
│  Real-time WebSocket updates │ Admin: Invite Codes          │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
assemblysim/
├── .env                               # API keys + auth config (gitignored)
├── backend/
│   ├── app/
│   │   ├── config.py                  # Settings & environment
│   │   ├── llm_client.py              # Unified LLM client
│   │   ├── prompt_loader.py           # Loads prompts from YAML
│   │   ├── prompts.yaml               # All system prompts
│   │   ├── main.py                    # FastAPI app, auth wiring, admin seed
│   │   ├── data/                      # GSS data loading & labels
│   │   ├── citizen_forge/             # Sampling, persona generation, validation
│   │   ├── models/
│   │   │   ├── database.py            # SQLAlchemy setup
│   │   │   ├── models.py             # ORM models (User, InviteCode, Assembly, etc.)
│   │   │   └── schemas.py            # Pydantic schemas
│   │   ├── api/
│   │   │   ├── auth.py               # Auth: register, login, JWT, invite codes, password change
│   │   │   ├── assemblies.py         # Assembly CRUD + deliberation endpoints
│   │   │   ├── settings.py           # App defaults
│   │   │   ├── custom_citizens.py    # Custom citizen templates
│   │   │   ├── websocket.py          # Real-time updates
│   │   │   └── services.py           # Background tasks
│   │   ├── agents/                    # Citizen, Moderator, Recorder agents
│   │   ├── knowledge/                 # Perplexity research client
│   │   └── orchestration/             # Deliberation engine
│   └── requirements.txt
├── frontend/
│   ├── app/                           # Next.js pages (login, register, account, dashboard, etc.)
│   ├── components/                    # React components (auth, assembly, citizen, deliberation, ui)
│   ├── hooks/                         # Data fetching hooks
│   ├── lib/                           # Types, API client, WebSocket client
│   ├── store/                         # Zustand stores (auth, deliberation)
│   ├── middleware.ts                  # Next.js middleware
│   └── package.json
└── data/
    └── GSS_stata/                     # GSS survey data
```

## Deliberation Flow

After citizens are generated and a briefing book is researched, the deliberation engine runs this sequence:

1. **Group Discussion Rounds** — Citizens discuss the topic in small deliberation groups across multiple rounds, with a moderator facilitating
2. **Plenary Round** — Cross-group discussion bringing all citizens together
3. **Proposal Generation** — Each citizen proposes 1-2 concrete policy ideas within their group
4. **Intra-Group Score Voting** — Citizens score all proposals in their group (1-5). Top 2 per group advance
5. **Moderator Deduplication** — The moderator reviews all advancing proposals and merges similar ones
6. **Assembly-Wide Score Voting** — Every citizen scores each deduplicated proposal (1-5). Proposals averaging >3.0 pass
7. **Report Generation** — Passing proposals become the assembly's recommendations. A recorder agent generates an executive summary, key themes, consensus/disagreement analysis, and a minority report

## API Endpoints

### Authentication (unauthenticated)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register with invite code |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Get current user (requires token) |
| POST | `/auth/change-password` | Change password (requires token) |
| POST | `/auth/invite-codes` | Generate invite code (admin only) |
| GET | `/auth/invite-codes` | List invite codes (admin only) |

### Health (unauthenticated)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |

### Assemblies (authenticated)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/assemblies` | Create assembly |
| GET | `/assemblies` | List assemblies |
| GET | `/assemblies/{id}` | Get assembly details |
| DELETE | `/assemblies/{id}` | Delete assembly |
| POST | `/assemblies/{id}/citizens` | Generate citizens |
| GET | `/assemblies/{id}/citizens` | List citizens |
| POST | `/assemblies/{id}/briefing` | Generate briefing |
| POST | `/assemblies/{id}/start` | Start deliberation |
| GET | `/assemblies/{id}/messages` | Get transcript |
| GET | `/assemblies/{id}/report` | Get final report |
| GET | `/assemblies/{id}/research` | List follow-up research |
| GET | `/settings` | Get app defaults |
| PUT | `/settings` | Update app defaults |
| WS | `/ws/assemblies/{id}` | Real-time updates |

## Configuration

Create a `.env` file in the `assemblysim/` directory:

```bash
# Required: API keys
OPENROUTER_API_KEY=sk-or-v1-...
PERPLEXITY_API_KEY=pplx-...

# LLM Configuration (OpenRouter model IDs)
LLM_PROVIDER=openrouter
WRITER_MODEL=anthropic/claude-sonnet-4.5
CITIZEN_MODEL=qwen/qwen3-235b-a22b-2507
MODERATOR_MODEL=anthropic/claude-sonnet-4.5
UTILITY_MODEL=openai/gpt-4o-mini

# Authentication
SECRET_KEY=your-secret-key-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-admin-password

# Database
DATABASE_URL=sqlite:///./assemblysim.db
```

## Model Configuration

The system uses different models for different tasks:

```bash
WRITER_MODEL=anthropic/claude-sonnet-4.5    # Persona generation
CITIZEN_MODEL=qwen/qwen3-235b-a22b-2507    # Deliberation
MODERATOR_MODEL=anthropic/claude-sonnet-4.5  # Facilitation
UTILITY_MODEL=openai/gpt-4o-mini            # Summaries
```

Customize prompts without touching code by editing `backend/app/prompts.yaml`.

## Data Source

**General Social Survey (GSS) 1972-2024**
- **Source**: NORC at the University of Chicago
- **Size**: 567 MB Stata file, 72k+ respondents
- **Location**: `../data/GSS_stata/gss7224_r2.dta`

## Requirements

- **Python 3.9+** with virtual environment
- **Node.js 18+** for the frontend
- **OpenRouter API key**
- **Perplexity API key** (optional, for research briefings)
- **GSS data file** at `../data/GSS_stata/gss7224_r2.dta`

## Resources

- **Deliberation Guide**: `backend/DELIBERATION_GUIDE.md`
- **Prompts Guide**: `backend/PROMPTS_GUIDE.md`
- **GSS Documentation**: `../data/GSS_stata/claude_summary.txt`
- **Claude.md**: `CLAUDE.md` (AI assistant guide)
