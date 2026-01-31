"""
Enable verbose logging for LLM interactions.

Run this before the demo to see all LLM prompts and responses.
"""

import logging
import sys

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('deliberation_verbose.log')
    ]
)

# Set specific loggers
logging.getLogger('app.llm_client').setLevel(logging.DEBUG)
logging.getLogger('app.agents').setLevel(logging.DEBUG)
logging.getLogger('app.knowledge').setLevel(logging.DEBUG)
logging.getLogger('app.orchestration').setLevel(logging.DEBUG)

print("✓ Verbose logging enabled")
print("  - Console output: DEBUG level")
print("  - File output: deliberation_verbose.log")
print("\nNow run: python demo_deliberation.py --mode quick")
