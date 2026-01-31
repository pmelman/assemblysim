"""
Run the demo with verbose logging enabled.

This shows all LLM prompts, responses, and Perplexity queries.
"""

import logging
import sys
import asyncio

# Set up verbose logging BEFORE importing anything else
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('deliberation_verbose.log', mode='w')
    ]
)

# Now import and run the demo
from demo_deliberation import quick_demo, full_demo

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run demo with verbose LLM logging")
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="Demo mode"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("VERBOSE LOGGING ENABLED")
    print("=" * 80)
    print("All LLM interactions will be logged to:")
    print("  - Console (below)")
    print("  - File: deliberation_verbose.log")
    print()
    print("Look for lines marked with:")
    print("  - 'LLM REQUEST' - what we're sending to the model")
    print("  - 'RESPONSE' - what the model returned")
    print("  - 'PERPLEXITY REQUEST' - research queries")
    print("=" * 80)
    print()

    if args.mode == "full":
        asyncio.run(full_demo())
    else:
        asyncio.run(quick_demo())

    print()
    print("=" * 80)
    print("Full verbose log saved to: deliberation_verbose.log")
    print("=" * 80)
