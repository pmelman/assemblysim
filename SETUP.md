# Phase 0 Setup Guide

Complete these steps to finish Phase 0 setup.

## Step 1: Create Python Virtual Environment

```bash
cd assemblysim/backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

You should see `(venv)` appear in your terminal prompt.

## Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- FastAPI and Uvicorn (web framework)
- Pandas and Pyreadstat (data processing, Stata files)
- LangChain, LangGraph, OpenAI, Anthropic (LLM framework)
- SQLAlchemy (database)
- And other dependencies

Expected install time: 2-3 minutes

## Step 3: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your preferred editor
nano .env  # or vim, code, etc.
```

Add your API keys:
```bash
# At minimum, add ONE of these:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# For Phase 2+ (research functionality):
PERPLEXITY_API_KEY=pplx-...
```

**Don't have API keys yet?** That's OK - you can continue with Phase 0 validation and add them before Phase 1.

## Step 4: Validate Setup

```bash
python validate_phase0.py
```

You should see:

```
======================================================================
PHASE 0 VALIDATION SUMMARY
======================================================================
✓ PASSED     Dependencies
✓ PASSED     Configuration
✓ PASSED     GSS Data Loader
✓ PASSED     Label Mappings
✓ PASSED     Sampling Prep
======================================================================

🎉 Phase 0 setup complete! All checks passed.
```

## Troubleshooting

### "GSS data file not found"

The system expects the GSS data at:
```
/Users/paulmelman/Claude/Assembly Sim/data/GSS_stata/gss7224_r2.dta
```

If your data is elsewhere, update `DATA_DIR` in `.env`:
```bash
DATA_DIR=/path/to/your/data/folder
```

### "ModuleNotFoundError"

Make sure:
1. Virtual environment is activated: `source venv/bin/activate`
2. Dependencies installed: `pip install -r requirements.txt`
3. You're in the `backend/` directory

### "Validation failed with warnings"

Some warnings are OK, especially:
- Missing API keys (you can add them later)
- High missingness in some GSS variables (expected)

As long as the critical checks pass, you're good to proceed.

## What's Next?

Once Phase 0 validation passes:

1. **Review the Development Plan:**
   ```bash
   cat ../DEVELOPMENT_PLAN.md
   ```

2. **Read about Phase 1:**
   Phase 1 focuses on the "Citizen Forge" - converting GSS data into LLM personas.

3. **Explore the data:**
   ```python
   # In Python REPL
   from app.data.gss_loader import load_gss_for_sampling
   from app.data.gss_labels import get_label

   df = load_gss_for_sampling(years=[2022])
   print(df.head())
   print(df['polviews'].value_counts())
   ```

4. **Start Phase 1 development** when ready!

## Quick Reference

```bash
# Activate virtual environment
source venv/bin/activate

# Run validation
python validate_phase0.py

# Run tests (when pytest is set up)
pytest tests/test_phase0.py -v

# Deactivate virtual environment
deactivate
```
