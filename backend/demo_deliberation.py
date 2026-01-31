"""
Demo script to run a complete assembly deliberation.

This demonstrates the full Phase 2 functionality:
1. Create assembly
2. Generate citizens
3. Generate briefing book (optional)
4. Run deliberation
5. View results
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.database import get_db_session, init_db
from app.models.models import Assembly, Citizen, BriefingBook, Report, AssemblyStatus
from app.citizen_forge.sampler import StratifiedSampler
from app.citizen_forge.persona_generator import PersonaGenerator
from app.knowledge.perplexity_client import get_perplexity_client
from app.orchestration import run_deliberation


async def create_demo_assembly(
    topic: str = "Should the United States implement a Universal Basic Income?",
    num_citizens: int = 8,
    skip_briefing: bool = False
):
    """
    Create a complete assembly and run deliberation.

    Args:
        topic: The policy topic
        num_citizens: Number of citizens (keep small for demo, e.g., 8)
        skip_briefing: Skip briefing generation (faster for testing)
    """
    print("=" * 80)
    print("Silicon Citizens' Assembly - Full Demo")
    print("=" * 80)
    print(f"\nTopic: {topic}")
    print(f"Citizens: {num_citizens}")
    print()

    # Initialize database
    init_db()

    # Step 1: Create assembly
    print("Step 1: Creating assembly...")
    with get_db_session() as db:
        assembly = Assembly(
            topic=topic,
            num_citizens=num_citizens,
            num_groups=2,  # Simplified: 2 groups for demo
            num_rounds=2,  # Shorter for demo
            status=AssemblyStatus.PENDING
        )
        db.add(assembly)
        db.flush()
        assembly_id = assembly.id
        print(f"✓ Created assembly ID: {assembly_id}")

    # Step 2: Generate citizens
    print("\nStep 2: Generating citizens from GSS data...")
    sampler = StratifiedSampler(target_n=num_citizens)
    sampler.load_data(years=[2022])
    sample_df = sampler.sample(strategy='stratified')
    print(f"✓ Sampled {len(sample_df)} respondents")

    print("Generating personas (this may take a minute)...")
    generator = PersonaGenerator()
    personas = await generator.generate_batch(sample_df, max_concurrent=3)
    print(f"✓ Generated {len(personas)} personas")

    # Save citizens to database
    with get_db_session() as db:
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()

        # Create groups
        from app.models.models import DeliberationGroup
        group_a = DeliberationGroup(assembly_id=assembly_id, name='A')
        group_b = DeliberationGroup(assembly_id=assembly_id, name='B')
        db.add(group_a)
        db.add(group_b)
        db.flush()

        # Add citizens
        for i, persona in enumerate(personas):
            group = group_a if i < len(personas) // 2 else group_b
            citizen = Citizen(
                assembly_id=assembly_id,
                group_id=group.id,
                name=persona["name"],
                system_prompt=persona["system_prompt"],
                background_summary=persona.get("background_summary"),
                key_values=persona.get("key_values", []),
                demographic_tags=persona.get("demographic_tags", []),
                gss_data=persona.get("gss_data")
            )
            db.add(citizen)

        assembly.status = AssemblyStatus.CITIZENS_READY
        db.commit()

    print(f"✓ Saved {len(personas)} citizens to database")
    print("\nCitizen Roster:")
    for i, p in enumerate(personas, 1):
        values = ", ".join(p.get("key_values", [])[:3])
        print(f"  {i}. {p['name']}: {values}")

    # Step 3: Generate briefing book (optional)
    if not skip_briefing:
        print("\nStep 3: Generating briefing book...")
        print("(Using Perplexity to research the topic)")
        try:
            perplexity = get_perplexity_client()
            briefing_data = await perplexity.generate_briefing_book(
                topic=topic,
                depth="standard"
            )

            with get_db_session() as db:
                briefing = BriefingBook(
                    assembly_id=assembly_id,
                    topic_query=topic,
                    content_markdown=briefing_data["content_markdown"],
                    sections=briefing_data.get("sections"),
                    sources=briefing_data.get("sources", [])
                )
                db.add(briefing)

                assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
                assembly.status = AssemblyStatus.READY
                db.commit()

            is_fallback = briefing_data.get("is_fallback", False)
            print(f"✓ Briefing book generated {'(fallback mode)' if is_fallback else ''}")
            print(f"  Sections: {list(briefing_data.get('sections', {}).keys())}")
            print(f"  Sources: {len(briefing_data.get('sources', []))}")

        except Exception as e:
            print(f"⚠ Briefing generation failed: {e}")
            print("  Continuing without briefing...")
    else:
        print("\nStep 3: Skipping briefing generation (as requested)")
        with get_db_session() as db:
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            assembly.status = AssemblyStatus.READY
            db.commit()

    # Step 4: Run deliberation
    print("\n" + "=" * 80)
    print("Step 4: Running Deliberation")
    print("=" * 80)
    print("\nThis will take several minutes as agents discuss the topic...")
    print()

    with get_db_session() as db:
        await run_deliberation(
            assembly_id=assembly_id,
            db=db
        )

    print("\n✓ Deliberation complete!")

    # Step 5: Display results
    print("\n" + "=" * 80)
    print("Step 5: Results")
    print("=" * 80)

    with get_db_session() as db:
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        citizens = db.query(Citizen).filter(Citizen.assembly_id == assembly_id).all()
        report = db.query(Report).filter(Report.assembly_id == assembly_id).first()

        print(f"\nAssembly Status: {assembly.status.value}")
        print(f"Completed: {assembly.completed_at}")

        # Vote tally
        if report:
            print("\n--- VOTE TALLY ---")
            for vote_type, count in report.vote_tally.items():
                print(f"  {vote_type.capitalize()}: {count}")

            print("\n--- KEY THEMES ---")
            for theme in report.key_themes or []:
                print(f"  • {theme}")

            print("\n--- EXECUTIVE SUMMARY ---")
            print(report.executive_summary)

            if report.minority_report:
                print("\n--- MINORITY REPORT ---")
                print(report.minority_report)

        # Individual votes
        print("\n--- INDIVIDUAL VOTES ---")
        for citizen in citizens:
            vote = citizen.final_vote or "no vote"
            print(f"\n{citizen.name}: {vote.upper()}")
            if citizen.vote_reasoning:
                print(f"  Reasoning: {citizen.vote_reasoning[:200]}...")

    print("\n" + "=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print(f"\nAssembly ID: {assembly_id}")
    print("You can now:")
    print("  - Start the API server: uvicorn app.main:app --reload")
    print(f"  - View assembly: http://localhost:8000/assemblies/{assembly_id}")
    print(f"  - View messages: http://localhost:8000/assemblies/{assembly_id}/messages")
    print(f"  - View report: http://localhost:8000/assemblies/{assembly_id}/report")


async def quick_demo():
    """Run a quick demo with minimal citizens and no briefing."""
    await create_demo_assembly(
        topic="Should the United States implement a Universal Basic Income?",
        num_citizens=6,  # Small number for speed
        skip_briefing=True  # Skip for speed
    )


async def full_demo():
    """Run a full demo with briefing book."""
    await create_demo_assembly(
        topic="Should the United States implement a Universal Basic Income?",
        num_citizens=8,
        skip_briefing=False
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Demo the Silicon Citizens' Assembly")
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="Demo mode: quick (no briefing, 6 citizens) or full (with briefing, 8 citizens)"
    )
    parser.add_argument(
        "--topic",
        help="Custom topic for deliberation"
    )
    parser.add_argument(
        "--citizens",
        type=int,
        help="Number of citizens (default varies by mode)"
    )

    args = parser.parse_args()

    if args.topic or args.citizens:
        # Custom configuration
        asyncio.run(create_demo_assembly(
            topic=args.topic or "Should the United States implement a Universal Basic Income?",
            num_citizens=args.citizens or 8,
            skip_briefing=(args.mode == "quick")
        ))
    elif args.mode == "full":
        asyncio.run(full_demo())
    else:
        asyncio.run(quick_demo())
