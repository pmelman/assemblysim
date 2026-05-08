"""
API Services Module

Business logic for assembly operations, including background tasks
for citizen generation and briefing book creation.
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.database import get_db_session
from app.models.models import (
    Assembly, Citizen, DeliberationGroup, BriefingBook, AssemblyStatus,
    CustomCitizenTemplate, AppSettings
)
from app.citizen_forge.sampler import StratifiedSampler
from app.citizen_forge.persona_generator import PersonaGenerator
from app.knowledge.perplexity_client import get_perplexity_client

logger = logging.getLogger(__name__)


async def create_assembly_with_citizens(
    assembly_id: int,
    num_citizens: int,
    num_groups: int,
    sampling_strategy: str = "stratified",
    broadcast_callback=None,
    custom_citizen_ids: Optional[list] = None
):
    """
    Background task to generate citizens for an assembly.

    Args:
        assembly_id: ID of the assembly to populate
        num_citizens: Number of citizens to generate
        num_groups: Number of deliberation groups
        sampling_strategy: Sampling strategy for GSS data
        broadcast_callback: Optional callback to broadcast status updates
    """
    logger.info(f"Starting citizen generation for assembly {assembly_id}")

    try:
        with get_db_session() as db:
            # Update status to generating
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if not assembly:
                logger.error(f"Assembly {assembly_id} not found")
                return

            assembly.status = AssemblyStatus.GENERATING_CITIZENS
            db.commit()

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "status_update",
                    "status": "generating_citizens",
                    "message": "Starting citizen generation..."
                })

        # Resolve the assembly-wide default citizen model (admin setting)
        with get_db_session() as db:
            app_settings = db.query(AppSettings).filter(AppSettings.id == 1).first()
            default_citizen_model = (
                app_settings.default_citizen_model if app_settings else None
            )

        # Load custom citizen templates if provided
        custom_templates = []
        if custom_citizen_ids:
            with get_db_session() as db:
                custom_templates = db.query(CustomCitizenTemplate).filter(
                    CustomCitizenTemplate.id.in_(custom_citizen_ids)
                ).all()
                # Detach from session so we can use them later
                custom_templates = [{
                    "name": t.name,
                    "system_prompt": t.system_prompt or "",
                    "background_summary": t.background_summary,
                    "key_values": t.key_values or [],
                    "demographic_tags": t.demographic_tags or [],
                    "model": t.model,
                } for t in custom_templates]

            logger.info(f"Loaded {len(custom_templates)} custom citizen templates")

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "status_update",
                    "status": "generating_citizens",
                    "message": f"Loaded {len(custom_templates)} custom citizens, sampling remaining..."
                })

        # Calculate how many GSS citizens to generate
        gss_count = num_citizens - len(custom_templates)

        personas = []
        if gss_count > 0:
            # Sample from GSS data
            logger.info(f"Sampling {gss_count} citizens using {sampling_strategy} strategy")
            sampler = StratifiedSampler(target_n=gss_count)
            sampler.load_data(years=[2022])
            sample_df = sampler.sample(strategy=sampling_strategy)

            logger.info(f"Sampled {len(sample_df)} rows from GSS data")

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "status_update",
                    "status": "generating_citizens",
                    "message": f"Sampled {len(sample_df)} respondents, generating personas..."
                })

            # Generate personas
            generator = PersonaGenerator()
            personas = await generator.generate_batch(sample_df, max_concurrent=3)

        # Combine custom and generated citizens, then shuffle for random group assignment
        import random
        all_personas = custom_templates + personas
        random.shuffle(all_personas)

        logger.info(f"Total citizens: {len(all_personas)} ({len(custom_templates)} custom + {len(personas)} generated)")

        # Save to database
        with get_db_session() as db:
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if not assembly:
                logger.error(f"Assembly {assembly_id} not found after generation")
                return

            # Create deliberation groups
            group_names = [chr(65 + i) for i in range(num_groups)]  # A, B, C, D, E
            groups = []
            for name in group_names:
                group = DeliberationGroup(
                    assembly_id=assembly_id,
                    name=name
                )
                db.add(group)
                groups.append(group)
            db.flush()  # Get group IDs

            # Create citizens and assign to groups
            citizens_per_group = len(all_personas) // num_groups
            for i, persona in enumerate(all_personas):
                group_index = min(i // citizens_per_group, num_groups - 1)
                group = groups[group_index]

                citizen = Citizen(
                    assembly_id=assembly_id,
                    group_id=group.id,
                    name=persona.get("name", f"Citizen {i+1}"),
                    system_prompt=persona.get("system_prompt", ""),
                    background_summary=persona.get("background_summary"),
                    key_values=persona.get("key_values", []),
                    demographic_tags=persona.get("demographic_tags", []),
                    gss_data=persona.get("gss_data"),
                    gss_row_id=persona.get("gss_data", {}).get("id"),
                    gss_year=persona.get("gss_data", {}).get("year"),
                    model=persona.get("model") or default_citizen_model,
                )
                db.add(citizen)

            # Update assembly status - READY if briefing exists, otherwise CITIZENS_READY
            briefing_exists = db.query(BriefingBook).filter(
                BriefingBook.assembly_id == assembly_id
            ).first() is not None

            if briefing_exists:
                assembly.status = AssemblyStatus.READY
                status_message = f"Generated {len(all_personas)} citizens in {num_groups} groups, assembly ready for deliberation"
            else:
                assembly.status = AssemblyStatus.CITIZENS_READY
                status_message = f"Generated {len(all_personas)} citizens in {num_groups} groups"

            assembly.num_citizens = len(all_personas)
            assembly.num_groups = num_groups
            db.commit()

            logger.info(f"Saved {len(all_personas)} citizens and {num_groups} groups for assembly {assembly_id}")

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "status_update",
                    "status": assembly.status.value,
                    "message": status_message,
                    "num_citizens": len(all_personas),
                    "num_groups": num_groups
                })

    except Exception as e:
        logger.error(f"Error generating citizens for assembly {assembly_id}: {e}")

        with get_db_session() as db:
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if assembly:
                assembly.status = AssemblyStatus.FAILED
                assembly.error_message = str(e)
                db.commit()

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "error",
                    "status": "failed",
                    "message": f"Failed to generate citizens: {str(e)}"
                })


async def generate_briefing_for_assembly(
    assembly_id: int,
    depth: str = "standard",
    broadcast_callback=None
):
    """
    Background task to generate a briefing book for an assembly.

    Args:
        assembly_id: ID of the assembly
        depth: Research depth (quick, standard, detailed)
        broadcast_callback: Optional callback to broadcast status updates
    """
    logger.info(f"Starting briefing generation for assembly {assembly_id}")

    try:
        with get_db_session() as db:
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if not assembly:
                logger.error(f"Assembly {assembly_id} not found")
                return

            topic = assembly.topic

            assembly.status = AssemblyStatus.GENERATING_BRIEFING
            db.commit()

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "status_update",
                    "status": "generating_briefing",
                    "message": "Researching topic..."
                })

        # Generate briefing
        client = get_perplexity_client()
        briefing_data = await client.generate_briefing_book(topic, depth=depth)

        logger.info(f"Generated briefing for topic: {topic[:50]}...")

        # Save to database
        with get_db_session() as db:
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if not assembly:
                logger.error(f"Assembly {assembly_id} not found after briefing generation")
                return

            # Check if briefing already exists
            existing_briefing = db.query(BriefingBook).filter(
                BriefingBook.assembly_id == assembly_id
            ).first()

            if existing_briefing:
                # Update existing
                existing_briefing.topic_query = topic
                existing_briefing.content_markdown = briefing_data.get("content_markdown", "")
                existing_briefing.sections = briefing_data.get("sections")
                existing_briefing.sources = briefing_data.get("sources", [])
                existing_briefing.generated_at = datetime.utcnow()
            else:
                # Create new
                briefing = BriefingBook(
                    assembly_id=assembly_id,
                    topic_query=topic,
                    content_markdown=briefing_data.get("content_markdown", ""),
                    sections=briefing_data.get("sections"),
                    sources=briefing_data.get("sources", [])
                )
                db.add(briefing)

            # Update assembly status - only READY if citizens exist
            citizen_count = db.query(Citizen).filter(
                Citizen.assembly_id == assembly_id
            ).count()

            if citizen_count > 0:
                assembly.status = AssemblyStatus.READY
                status_message = "Briefing book generated, assembly ready for deliberation"
            else:
                # Keep status as PENDING if no citizens yet
                # (briefing can be generated independently)
                if assembly.status == AssemblyStatus.GENERATING_BRIEFING:
                    assembly.status = AssemblyStatus.PENDING
                status_message = "Briefing book generated (citizens not yet generated)"

            db.commit()

            logger.info(f"Saved briefing book for assembly {assembly_id}")

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "status_update",
                    "status": assembly.status.value,
                    "message": status_message,
                    "is_fallback": briefing_data.get("is_fallback", False)
                })

    except Exception as e:
        logger.error(f"Error generating briefing for assembly {assembly_id}: {e}")

        with get_db_session() as db:
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if assembly:
                assembly.status = AssemblyStatus.FAILED
                assembly.error_message = f"Briefing generation failed: {str(e)}"
                db.commit()

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "error",
                    "status": "failed",
                    "message": f"Failed to generate briefing: {str(e)}"
                })


def get_assembly_with_details(db: Session, assembly_id: int) -> Optional[Assembly]:
    """
    Get an assembly with all related data loaded.

    Args:
        db: Database session
        assembly_id: Assembly ID

    Returns:
        Assembly with citizens, groups, briefing, etc. or None
    """
    from sqlalchemy.orm import joinedload

    return db.query(Assembly).options(
        joinedload(Assembly.citizens),
        joinedload(Assembly.groups),
        joinedload(Assembly.briefing_book),
        joinedload(Assembly.report),
        joinedload(Assembly.round_research)
    ).filter(Assembly.id == assembly_id).first()


def assign_citizens_to_groups(db: Session, assembly_id: int) -> dict:
    """
    Assign or reassign citizens to deliberation groups.

    Args:
        db: Database session
        assembly_id: Assembly ID

    Returns:
        Dict with group assignments
    """
    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
    if not assembly:
        return {"error": "Assembly not found"}

    citizens = db.query(Citizen).filter(Citizen.assembly_id == assembly_id).all()
    groups = db.query(DeliberationGroup).filter(
        DeliberationGroup.assembly_id == assembly_id
    ).order_by(DeliberationGroup.name).all()

    if not groups:
        return {"error": "No groups found"}

    # Distribute citizens evenly
    citizens_per_group = len(citizens) // len(groups)
    remainder = len(citizens) % len(groups)

    assignments = {}
    citizen_index = 0

    for i, group in enumerate(groups):
        group_size = citizens_per_group + (1 if i < remainder else 0)
        group_citizens = citizens[citizen_index:citizen_index + group_size]

        for citizen in group_citizens:
            citizen.group_id = group.id

        assignments[group.name] = [c.name for c in group_citizens]
        citizen_index += group_size

    db.commit()

    return assignments


async def run_deliberation_for_assembly(
    assembly_id: int,
    broadcast_callback=None
):
    """
    Background task to run the complete deliberation process.

    Args:
        assembly_id: ID of the assembly
        broadcast_callback: Optional callback to broadcast status updates
    """
    from app.orchestration import run_deliberation

    logger.info(f"Starting deliberation for assembly {assembly_id}")

    try:
        with get_db_session() as db:
            # Verify assembly is ready
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if not assembly:
                logger.error(f"Assembly {assembly_id} not found")
                return

            if assembly.status not in [AssemblyStatus.READY, AssemblyStatus.CITIZENS_READY]:
                logger.error(f"Assembly {assembly_id} not ready (status: {assembly.status})")
                if broadcast_callback:
                    await broadcast_callback(assembly_id, {
                        "type": "error",
                        "message": f"Assembly not ready for deliberation (status: {assembly.status.value})"
                    })
                return

        # Run deliberation (uses its own db session)
        with get_db_session() as db:
            await run_deliberation(
                assembly_id=assembly_id,
                db=db,
                broadcast_callback=broadcast_callback
            )

    except Exception as e:
        logger.error(f"Error running deliberation for assembly {assembly_id}: {e}")

        with get_db_session() as db:
            assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
            if assembly:
                assembly.status = AssemblyStatus.FAILED
                assembly.error_message = f"Deliberation failed: {str(e)}"
                db.commit()

            if broadcast_callback:
                await broadcast_callback(assembly_id, {
                    "type": "error",
                    "status": "failed",
                    "message": f"Deliberation failed: {str(e)}"
                })
