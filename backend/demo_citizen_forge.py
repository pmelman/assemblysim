#!/usr/bin/env python3
"""
Citizen Forge Demo

This script demonstrates the Phase 1 Citizen Forge pipeline:
1. Load GSS data
2. Sample representative citizens using stratified sampling
3. Generate LLM personas from GSS data
4. Validate the generated personas

Usage:
    python demo_citizen_forge.py [--num-citizens N] [--dry-run]

Options:
    --num-citizens N    Number of citizens to generate (default: 8)
    --dry-run          Skip LLM calls, show sampling only
    --seed N           Random seed for reproducibility
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from app.data.gss_loader import GSSLoader
from app.data.gss_labels import format_value, REGION_LABELS
from app.citizen_forge import (
    StratifiedSampler,
    PersonaGenerator,
    validate_personas
)


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_subheader(text: str):
    """Print a formatted subheader."""
    print(f"\n--- {text} ---\n")


def print_sample_row(row, index: int):
    """Print a sampled GSS row in readable format."""
    import pandas as pd

    def safe_int(val):
        """Safely convert to int, returning None if NaN."""
        if pd.isna(val):
            return None
        return int(val)

    age_val = safe_int(row.get('age'))
    age = str(age_val) if age_val else 'Unknown'

    sex_val = safe_int(row.get('sex'))
    sex = format_value('sex', sex_val) if sex_val else 'Unknown'

    race_val = safe_int(row.get('race'))
    race = format_value('race', race_val) if race_val else 'Unknown'

    polviews_val = safe_int(row.get('polviews'))
    polviews = format_value('polviews', polviews_val) if polviews_val else 'Unknown'

    region_val = safe_int(row.get('region'))
    region = REGION_LABELS.get(region_val, 'Unknown') if region_val else 'Unknown'

    print(f"  [{index+1}] {age}yo {sex}, {race}, {region}")
    print(f"      Political views: {polviews}")


def print_persona(persona: dict, index: int, verbose: bool = False):
    """Print a generated persona."""
    print(f"\n  [{index+1}] {persona['name']}")
    print(f"      {persona['background_summary']}")
    print(f"      Values: {', '.join(persona['key_values'])}")

    if verbose:
        print(f"\n      System Prompt ({len(persona['system_prompt'].split())} words):")
        # Print first 200 chars
        prompt_preview = persona['system_prompt'][:300]
        if len(persona['system_prompt']) > 300:
            prompt_preview += "..."
        for line in prompt_preview.split('\n'):
            print(f"        {line}")


async def run_demo(
    num_citizens: int = 8,
    dry_run: bool = False,
    seed: int = None,
    verbose: bool = False
):
    """Run the Citizen Forge demo."""

    print_header("SILICON CITIZENS' ASSEMBLY - CITIZEN FORGE DEMO")

    settings = get_settings()
    print(f"\nConfiguration:")
    print(f"  LLM Provider: {settings.LLM_PROVIDER}")
    print(f"  Writer Model: {settings.WRITER_MODEL}")
    print(f"  GSS Data: {settings.GSS_DATA_PATH}")

    # Step 1: Load GSS Data
    print_subheader("Step 1: Loading GSS Data")

    try:
        loader = GSSLoader()
        df = loader.load(years=[2022])  # Use 2022 for demo
        print(f"  Loaded {len(df):,} respondents from GSS 2022")

        validation = loader.validate_data()
        print(f"  Validation: {'PASSED' if validation['valid'] else 'PASSED WITH WARNINGS'}")

    except FileNotFoundError as e:
        print(f"  ERROR: GSS data file not found")
        print(f"  {e}")
        return

    # Step 2: Stratified Sampling
    print_subheader("Step 2: Stratified Sampling")

    sampler = StratifiedSampler(gss_data=df, target_n=num_citizens)
    sampler.prepare_data()

    sample_df = sampler.sample(strategy='stratified', seed=seed)
    summary = sampler.get_sample_summary(sample_df)

    print(f"  Sampled {summary['total']} citizens")
    print(f"\n  Political distribution:")
    for group, count in summary['political'].items():
        pct = count / summary['total'] * 100
        print(f"    {group}: {count} ({pct:.0f}%)")

    print(f"\n  Sampled respondents:")
    for i, (_, row) in enumerate(sample_df.iterrows()):
        print_sample_row(row, i)

    if dry_run:
        print_header("DRY RUN COMPLETE")
        print("\nTo generate actual personas, run without --dry-run")
        print("This will make API calls to your LLM provider.\n")
        return

    # Step 3: Generate Personas
    print_subheader("Step 3: Generating Personas via LLM")

    print(f"  Generating {num_citizens} personas using {settings.WRITER_MODEL}...")
    print(f"  (This may take a minute...)\n")

    try:
        generator = PersonaGenerator()
        personas = await generator.generate_batch(sample_df, max_concurrent=3)
        print(f"  Generated {len(personas)} personas successfully!")

    except Exception as e:
        print(f"  ERROR generating personas: {e}")
        print(f"\n  Check your API keys in .env:")
        print(f"    OPENROUTER_API_KEY=...")
        return

    # Step 4: Display Personas
    print_subheader("Step 4: Generated Personas")

    for i, persona in enumerate(personas):
        print_persona(persona, i, verbose=verbose)

    # Step 5: Validate
    print_subheader("Step 5: Validation")

    validation_result = validate_personas(personas)

    batch = validation_result['validation']
    print(f"  Valid personas: {batch['valid']}/{batch['total']}")
    print(f"  Pass rate: {batch['pass_rate']*100:.0f}%")
    print(f"  Total warnings: {batch['total_warnings']}")

    diversity = validation_result['diversity']
    print(f"\n  Diversity metrics:")
    print(f"    Unique names: {diversity['unique_names']}/{len(personas)}")
    print(f"    Unique values: {diversity['unique_values']}")
    if diversity['political_distribution']:
        print(f"    Political spread: {diversity['political_distribution']}")

    # Any issues?
    issues = [r for r in batch['results'] if r['errors'] or r['warnings']]
    if issues:
        print(f"\n  Issues found:")
        for result in issues[:5]:  # Show max 5
            if result['errors']:
                print(f"    {result['name']}: ERRORS - {result['errors']}")
            if result['warnings']:
                print(f"    {result['name']}: warnings - {result['warnings'][:2]}")

    # Step 6: Save Output
    print_subheader("Step 6: Save Output")

    output_file = Path("demo_personas.json")
    with open(output_file, 'w') as f:
        json.dump(personas, f, indent=2)

    print(f"  Saved {len(personas)} personas to {output_file}")

    print_header("DEMO COMPLETE")
    print(f"""
Next steps:
1. Review the generated personas in demo_personas.json
2. Adjust prompts in persona_generator.py if needed
3. When satisfied, proceed to Phase 2 (backend infrastructure)

To generate more personas:
    python demo_citizen_forge.py --num-citizens 40

To test sampling only (no LLM calls):
    python demo_citizen_forge.py --dry-run
""")


def main():
    parser = argparse.ArgumentParser(
        description="Demo the Citizen Forge pipeline"
    )
    parser.add_argument(
        '--num-citizens', '-n',
        type=int,
        default=8,
        help='Number of citizens to generate (default: 8)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Skip LLM calls, show sampling only'
    )
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=None,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show full system prompts'
    )

    args = parser.parse_args()

    asyncio.run(run_demo(
        num_citizens=args.num_citizens,
        dry_run=args.dry_run,
        seed=args.seed,
        verbose=args.verbose
    ))


if __name__ == "__main__":
    main()
