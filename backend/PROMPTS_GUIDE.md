# Prompts Configuration Guide

All system prompts are now centralized in `app/prompts.yaml` for easy editing.

## Quick Start

**Edit prompts:**
```bash
nano app/prompts.yaml
# or use your favorite editor
```

**Changes take effect immediately** - just restart your demo or server.

## Prompt Structure

The YAML file contains prompts for five agents:

```yaml
writer:           # Persona generation (Kimi-K2)
  system: |
    [Full system prompt...]

moderator:        # Facilitation (Claude Sonnet 4.5)
  system: |
    [Full system prompt...]

recorder:         # Summarization (GPT-4o-mini)
  system: |
    [Full system prompt...]

citizen:          # Deliberation behavior
  deliberation_instructions: |
    [Guidelines for citizens...]

perplexity:       # Research queries
  system: |
    [Research assistant prompt...]
```

## What's Where

### Static Prompts (in YAML)
- **System prompts** - Core instructions for each agent
- **Guidelines** - Behavioral rules and principles
- **Output formats** - JSON structures, response styles

### Dynamic Templates (in code)
- Prompts with variables (topic, round number, citizen names)
- Contextual prompts (discussion summaries, voting instructions)
- F-string formatted prompts

**Example:**
```python
# Static prompt (YAML)
"You are a skilled facilitator..."

# Dynamic template (code)
f"You are opening Round {round_number} on the topic: {topic}..."
```

## Editing Prompts

### Change Moderator Style

Make the moderator more casual:
```yaml
moderator:
  system: |
    You're facilitating a casual, friendly citizens' assembly...

    COMMUNICATION STYLE:
    - Conversational and warm
    - Use contractions and casual language
    - Keep energy upbeat
```

### Adjust Persona Generation

Make personas more policy-focused:
```yaml
writer:
  system: |
    ...
    5. POLICY EXPERTISE
       - Emphasize policy knowledge and issue familiarity
       - Include relevant professional experience
       - Reference specific policy examples
```

### Modify Deliberation Guidelines

Encourage shorter responses:
```yaml
citizen:
  deliberation_instructions: |
    DELIBERATION GUIDELINES:
    - Keep responses brief (1-2 paragraphs max)
    - Make one clear point per response
    - Be concise and direct
```

## Testing Changes

After editing prompts:

```bash
# Quick test
python -c "from app.prompt_loader import get_moderator_prompt; print(get_moderator_prompt()[:200])"

# Run demo with new prompts
python demo_deliberation.py --mode quick

# Check verbose logs to see prompts in action
python demo_verbose.py --mode quick
```

## Prompt Versions

To A/B test prompts, you can:

**1. Create multiple YAML files:**
```bash
cp app/prompts.yaml app/prompts_formal.yaml
cp app/prompts.yaml app/prompts_casual.yaml
# Edit each version differently
```

**2. Switch between them:**
```python
# In your code
loader = PromptLoader('prompts_casual.yaml')
```

**3. Or use git branches:**
```bash
git checkout -b experiment-casual-moderator
# Edit prompts.yaml
git commit -m "Test casual moderator style"
```

## Prompt Best Practices

### 1. Be Specific
❌ "Be helpful and respectful"
✅ "Acknowledge each speaker by name, summarize their point in 1 sentence, then transition to the next speaker"

### 2. Include Examples
```yaml
moderator:
  system: |
    ...
    When opening a round, say something like:
    "Welcome to Round 2. In Round 1, we explored [theme]. Now let's dive deeper into [aspect]..."
```

### 3. Set Constraints
```yaml
citizen:
  deliberation_instructions: |
    - Keep responses to 2-4 paragraphs (200-400 words)
    - Reference at most 1-2 points from previous speakers
    - Focus on your unique perspective, not repeating others
```

### 4. Specify Tone
```yaml
recorder:
  system: |
    OUTPUT TONE:
    - Professional but accessible
    - Neutral, never judgmental
    - Clear, avoiding jargon
```

## Common Customizations

### Make Citizens More Opinionated
```yaml
citizen:
  deliberation_instructions: |
    - Take clear positions based on your values
    - Don't hedge or equivocate unnecessarily
    - Defend your perspective when challenged
```

### Make Moderator More Active
```yaml
moderator:
  system: |
    ACTIVE FACILITATION:
    - Interject to clarify unclear points
    - Call out logical fallacies gently
    - Summarize frequently (every 3-4 speakers)
    - Redirect tangents immediately
```

### Add Fact-Checking Instructions
```yaml
recorder:
  system: |
    FACT VERIFICATION:
    - Flag claims that need verification
    - Note when statistics are cited without sources
    - Track consistency of arguments across speakers
```

## Troubleshooting

**Problem:** Agent behavior doesn't change after editing YAML

**Solutions:**
1. Restart the demo/server (changes aren't hot-reloaded)
2. Check YAML syntax: `python -c "import yaml; yaml.safe_load(open('app/prompts.yaml'))"`
3. Verify the right file is being used: `python -c "from app.prompt_loader import get_prompt_loader; print(get_prompt_loader().prompts_file)"`

**Problem:** YAML parse error

**Common issues:**
- Indentation (use spaces, not tabs)
- Missing pipe `|` for multi-line strings
- Unescaped special characters

**Fix:**
```bash
# Validate YAML
python -c "import yaml; yaml.safe_load(open('app/prompts.yaml'))"
```

## Advanced: Hot-Reloading

To reload prompts without restarting:

```python
from app.prompt_loader import get_prompt_loader

# Reload all prompts
loader = get_prompt_loader()
loader.reload()

# Agents created after this will use new prompts
```

## File Locations

- **Prompts:** `backend/app/prompts.yaml`
- **Loader:** `backend/app/prompt_loader.py`
- **Usage:**
  - `backend/app/citizen_forge/persona_generator.py`
  - `backend/app/agents/moderator_agent.py`
  - `backend/app/agents/recorder_agent.py`
  - `backend/app/agents/citizen_agent.py`
  - `backend/app/knowledge/perplexity_client.py`

---

**Pro Tip:** Keep your custom prompts in version control, and use descriptive commit messages so you can track what worked!
