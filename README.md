# Silicon Citizens' Assembly 🏛️

A multi-agent LLM system that simulates deliberative democracy using real survey data from the General Social Survey (GSS).

## What Is This?

The Silicon Citizens' Assembly creates AI personas based on real American survey respondents, then brings them together for structured policy deliberation. Each "citizen" is an LLM agent with:

- **Authentic demographics** from GSS data (age, race, region, education, income)
- **Real political views** derived from actual survey responses
- **Nuanced values** that go beyond simple left/right ideology
- **Bot-themed names** like "Marcus Shannon" and "Patricia Berners-Lee" to celebrate our AI heritage

The goal: Explore what happens when diverse perspectives engage in good-faith deliberation, free from the constraints of human time, attention, and social pressure.

## Project Status

**Phase 1: The Citizen Forge** ✅ **COMPLETE**

The core persona generation pipeline is fully functional:

- ✅ Stratified sampling from GSS 2022 data
- ✅ LLM-powered persona generation via OpenRouter
- ✅ Anti-stereotype validation
- ✅ Bot-themed naming system
- ✅ Quality metrics and diversity checks

**Next Phase:** Phase 2 - Backend Infrastructure (FastAPI, database, agent framework)

## Quick Start

### Try the Demo (5 minutes)

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Set up your API key (one level up from backend/)
cd ..
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Run the demo
cd backend
python demo_citizen_forge.py --num-citizens 8

# Or just test the sampling (no API calls)
python demo_citizen_forge.py --dry-run
```

You'll see:
1. **Sampling**: 8 citizens selected using stratified sampling
2. **Generation**: LLM creates rich personas from GSS data
3. **Validation**: Quality checks ensure nuanced, stereotype-free personas
4. **Output**: `demo_personas.json` with complete agent definitions

### Example Output

```
[1] Harold Muad'Dib
    A retired manufacturing supervisor from the Midwest who values
    traditional morality, personal responsibility, and pragmatic
    problem-solving. Active in his Protestant church and community.
    Values: Traditional morality, Personal responsibility,
            Free market principles, Community stability

[2] Shanice Gibson
    A pragmatic, independent-minded working woman who combines
    progressive economic views with support for law and order.
    Values: Economic justice, Practical problem-solving,
            Community safety, Self-reliance
```

## Bot-Themed Names 🤖

Each persona gets a sci-fi/tech themed last name to acknowledge their AI nature:

- **Computing Pioneers**: Turing, Lovelace, Hopper, Dijkstra, Shannon
- **Sci-Fi Authors**: Asimov, Gibson, Dick, Stephenson, Clarke
- **Sci-Fi Characters**: Deckard, Ripley, Trinity, Connor, Skywalker
- **Tech Terms**: Protocol, Neural, Matrix, Quantum, Circuit

This creates names like "Marcus Shannon" and "Dorothy Dijkstra" - memorable, fun, and honest about what these agents are.

## Architecture

### Phase 1: The Citizen Forge (Current)

```
GSS Data (72k respondents)
    ↓
Stratified Sampling
    ↓
LLM Persona Generation (Writer LLM)
    ↓
Validation & Quality Checks
    ↓
AI Citizen Agents
```

**Key Components:**

- **`gss_loader.py`**: Loads and validates GSS Stata files
- **`sampler.py`**: Stratified sampling ensuring demographic representation
- **`persona_generator.py`**: Writer LLM converts GSS rows → rich personas
- **`validator.py`**: Quality checks for stereotypes, completeness, diversity
- **`llm_client.py`**: Unified client for OpenRouter/OpenAI/Anthropic

### Future Phases

**Phase 2**: Backend API (FastAPI, PostgreSQL, LangGraph)
**Phase 3**: Assembly Protocol (5-phase deliberation workflow)
**Phase 4**: Frontend (Next.js real-time deliberation viewer)
**Phase 5**: Polish & Deploy

## Project Structure

```
assemblysim/
├── backend/
│   ├── app/
│   │   ├── config.py              # Settings & environment
│   │   ├── llm_client.py          # Unified LLM client
│   │   ├── data/
│   │   │   ├── gss_loader.py      # GSS data loading
│   │   │   └── gss_labels.py      # Variable mappings
│   │   └── citizen_forge/
│   │       ├── sampler.py         # Stratified sampling
│   │       ├── persona_generator.py  # LLM generation
│   │       └── validator.py       # Quality checks
│   ├── demo_citizen_forge.py      # Phase 1 demo script
│   └── requirements.txt
├── .env                           # API keys (gitignored)
├── .env.example                   # Template
└── README.md                      # This file
```

## Configuration

Create a `.env` file in the `assemblysim/` directory:

```bash
# Required: OpenRouter API key (provides access to many models)
OPENROUTER_API_KEY=sk-or-v1-...

# Optional: Direct provider keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# LLM Configuration
LLM_PROVIDER=openrouter
WRITER_MODEL=anthropic/claude-3.5-sonnet
CITIZEN_MODEL=anthropic/claude-3.5-sonnet
UTILITY_MODEL=openai/gpt-4o-mini

# Generation Parameters
TEMPERATURE=0.7
WRITER_MAX_TOKENS=1000

# Assembly Parameters
DEFAULT_NUM_CITIZENS=40
DEFAULT_NUM_GROUPS=5
DEFAULT_NUM_ROUNDS=3
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

## How It Works

### 1. Stratified Sampling

The `StratifiedSampler` ensures demographic representation:

```python
DEFAULT_QUOTAS = {
    'polviews_group': {
        'Liberal': 0.30,      # 30% liberal
        'Moderate': 0.35,     # 35% moderate
        'Conservative': 0.35  # 35% conservative
    },
    'race': {1: 0.60, 2: 0.13, 3: 0.27},  # Matches US census
    'age_group': {'18-29': 0.20, '30-44': 0.25, '45-64': 0.30, '65+': 0.25}
}
```

### 2. Persona Generation

The Writer LLM converts GSS data into natural language personas:

**Input** (from GSS):
```
Age: 34, Sex: Female, Race: Black, Region: East North Central
Political Views: Slightly Conservative
Education: High school graduate
Employment: Working full time
...
```

**Output** (LLM-generated):
```json
{
  "name": "Jasmine",
  "system_prompt": "You are Jasmine, a 34-year-old Black woman...",
  "background_summary": "A pragmatic working professional...",
  "key_values": ["Practical problem-solving", "Economic justice", ...]
}
```

Then assigned bot-themed last name: **Jasmine Circuit**

### 3. Validation

Quality checks ensure:
- ✅ No stereotypical language (accents, dialects, caricatures)
- ✅ System prompts 100-500 words
- ✅ References to deliberation context
- ✅ Unique names (no duplicates)
- ✅ Diverse values across cohort

## Demo Script Options

```bash
# Generate 8 personas (default)
python demo_citizen_forge.py

# Generate 40 personas (full assembly)
python demo_citizen_forge.py --num-citizens 40

# Test sampling only (no LLM calls, fast)
python demo_citizen_forge.py --dry-run

# Set random seed for reproducibility
python demo_citizen_forge.py --seed 42

# Show full system prompts
python demo_citizen_forge.py --verbose
```

## Requirements

- **Python 3.11+**
- **OpenRouter API key** (or OpenAI/Anthropic)
- **GSS data file** at `../data/GSS_stata/gss7224_r2.dta`

Python packages (see `requirements.txt`):
- `pydantic-settings` - Configuration
- `pandas` - Data manipulation
- `pyreadstat` - Stata file reading
- `httpx` - Async HTTP for LLM APIs

## Development Roadmap

### ✅ Phase 0: Foundation (Complete)
- Project structure
- Configuration system
- GSS data loading pipeline

### ✅ Phase 1: The Citizen Forge (Complete)
- Stratified sampling
- LLM persona generation
- Bot-themed naming
- Validation system

### 🚧 Phase 2: Core Backend (Next)
- FastAPI application
- PostgreSQL database
- LangGraph agent framework
- Perplexity integration for research

### 📋 Phase 3: Assembly Protocol
- 5-phase deliberation workflow
- Small group deliberation
- Plenary synthesis
- Voting and reporting

### 📋 Phase 4: Frontend
- Next.js application
- Assembly creation UI
- Real-time deliberation viewer
- Report generation and display

### 📋 Phase 5: Integration & Polish
- End-to-end testing
- Performance optimization
- Deployment setup
- Documentation

## Resources

- **Design Document**: `../Silicon Assembly - Design Document.md`
- **Development Plan**: `../DEVELOPMENT_PLAN.md`
- **GSS Documentation**: `../data/GSS_stata/claude_summary.txt`
- **GSS Codebook**: `../data/GSS_stata/GSS 2024 Codebook R2.pdf`

## Contributing

This is currently a personal research project. Stay tuned for contribution guidelines!

## License

TBD

## Acknowledgments

- **General Social Survey**: NORC at the University of Chicago
- **OpenRouter**: Unified LLM API access
- **Anthropic & OpenAI**: Claude and GPT-4 models
- **Computing pioneers and sci-fi authors**: For inspiring our bot names! 🤖
