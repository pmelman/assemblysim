"""
Curated catalog of LLM models exposed in the admin UI.

These are OpenRouter model IDs. Users can also enter a custom OpenRouter
model ID via the UI, so this list is suggestive, not restrictive.
"""

AVAILABLE_MODELS: list[dict[str, str]] = [
    {"id": "anthropic/claude-sonnet-4.6", "label": "Claude Sonnet 4.6"},
    {"id": "anthropic/claude-opus-4.7", "label": "Claude Opus 4.7"},
    {"id": "qwen/qwen3.6-plus", "label": "Qwen3.6 Plus"},
    {"id": "x-ai/grok-4.3", "label": "Grok 4.3"},
    {"id": "deepseek/deepseek-v4-pro", "label": "DeepSeek V4 Pro"},
    {"id": "moonshotai/kimi-k2.6", "label": "Kimi K2.6"},
    {"id": "google/gemma-4-31b-it", "label": "Gemma 4 31B"},
    {"id": "google/gemini-3-flash-preview", "label": "Gemini 3 Flash"},
    {"id": "google/gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro"},
]

DEFAULT_CITIZEN_MODEL = "anthropic/claude-sonnet-4.6"
