"""
Assembly API Router

REST API endpoints for managing assemblies, citizens, briefing books,
messages, and reports.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.models import (
    Assembly, Citizen, DeliberationGroup, Message, BriefingBook, Report,
    RoundResearch, AssemblyStatus
)
from app.models.schemas import (
    AssemblyCreateRequest, AssemblyResponse, AssemblyDetailResponse,
    AssemblyListResponse, CitizenResponse, CitizenDetailResponse,
    BriefingBookResponse, BriefingGenerateRequest, MessageResponse,
    ReportResponse, GroupResponse, RoundResearchResponse
)
from app.api.services import (
    create_assembly_with_citizens,
    generate_briefing_for_assembly,
    get_assembly_with_details
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assemblies", tags=["assemblies"])


# =============================================================================
# ASSEMBLY ENDPOINTS
# =============================================================================

@router.post("", response_model=AssemblyResponse, status_code=201)
async def create_assembly(
    request: AssemblyCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new assembly (without generating citizens).

    Citizens must be generated separately using POST /assemblies/{id}/citizens.
    """
    logger.info(f"Creating assembly for topic: {request.topic[:50]}...")

    # Create assembly record
    round_prompts_data = None
    if request.round_prompts:
        round_prompts_data = [rp.model_dump() for rp in request.round_prompts]

    assembly = Assembly(
        topic=request.topic,
        num_citizens=request.num_citizens,
        num_groups=request.num_groups,
        num_rounds=request.num_rounds,
        sampling_strategy=request.sampling_strategy,
        round_prompts=round_prompts_data,
        max_research_calls_per_round=request.max_research_calls_per_round,
        max_research_tokens_per_call=request.max_research_tokens_per_call,
        custom_citizen_ids=request.custom_citizen_ids,
        status=AssemblyStatus.PENDING
    )
    db.add(assembly)
    db.commit()
    db.refresh(assembly)

    logger.info(f"Created assembly {assembly.id} (citizens not generated yet)")

    return assembly


@router.get("", response_model=AssemblyListResponse)
def list_assemblies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all assemblies with optional filtering.
    """
    query = db.query(Assembly)

    if status:
        try:
            status_enum = AssemblyStatus(status)
            query = query.filter(Assembly.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    total = query.count()
    assemblies = query.order_by(Assembly.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return AssemblyListResponse(
        assemblies=assemblies,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{assembly_id}", response_model=AssemblyDetailResponse)
def get_assembly(
    assembly_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about an assembly.
    """
    assembly = get_assembly_with_details(db, assembly_id)

    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")

    # Load round research
    round_research_records = db.query(RoundResearch).filter(
        RoundResearch.assembly_id == assembly_id
    ).order_by(RoundResearch.round_number).all()

    # Build response with nested data
    response = AssemblyDetailResponse(
        id=assembly.id,
        topic=assembly.topic,
        status=assembly.status.value,
        num_citizens=assembly.num_citizens,
        num_groups=assembly.num_groups,
        num_rounds=assembly.num_rounds,
        sampling_strategy=assembly.sampling_strategy,
        round_prompts=assembly.round_prompts,
        max_research_calls_per_round=assembly.max_research_calls_per_round,
        max_research_tokens_per_call=assembly.max_research_tokens_per_call,
        error_message=assembly.error_message,
        created_at=assembly.created_at,
        updated_at=assembly.updated_at,
        completed_at=assembly.completed_at,
        citizens=[CitizenResponse(
            id=c.id,
            name=c.name,
            background_summary=c.background_summary,
            key_values=c.key_values,
            demographic_tags=c.demographic_tags,
            group_id=c.group_id,
            final_vote=c.final_vote,
            vote_reasoning=c.vote_reasoning,
            created_at=c.created_at
        ) for c in assembly.citizens],
        groups=[GroupResponse(
            id=g.id,
            name=g.name,
            round_summaries=g.round_summaries,
            consensus_summary=g.consensus_summary,
            disagreements_summary=g.disagreements_summary,
            citizen_count=len([c for c in assembly.citizens if c.group_id == g.id]),
            created_at=g.created_at
        ) for g in assembly.groups],
        briefing_book=BriefingBookResponse(
            id=assembly.briefing_book.id,
            assembly_id=assembly.briefing_book.assembly_id,
            topic_query=assembly.briefing_book.topic_query,
            content_markdown=assembly.briefing_book.content_markdown,
            sections=assembly.briefing_book.sections,
            sources=assembly.briefing_book.sources,
            generated_at=assembly.briefing_book.generated_at
        ) if assembly.briefing_book else None,
        report=ReportResponse(
            id=assembly.report.id,
            assembly_id=assembly.report.assembly_id,
            executive_summary=assembly.report.executive_summary,
            recommendations=assembly.report.recommendations,
            vote_tally=assembly.report.vote_tally,
            minority_report=assembly.report.minority_report,
            key_themes=assembly.report.key_themes,
            generated_at=assembly.report.generated_at
        ) if assembly.report else None,
        round_research=[RoundResearchResponse(
            id=rr.id,
            assembly_id=rr.assembly_id,
            round_number=rr.round_number,
            queries=rr.queries,
            results=rr.results,
            summary_markdown=rr.summary_markdown,
            created_at=rr.created_at
        ) for rr in round_research_records]
    )

    return response


@router.delete("/{assembly_id}", status_code=204)
def delete_assembly(
    assembly_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an assembly and all related data.
    """
    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()

    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")

    db.delete(assembly)
    db.commit()

    logger.info(f"Deleted assembly {assembly_id}")


# =============================================================================
# CITIZEN ENDPOINTS
# =============================================================================

@router.get("/{assembly_id}/citizens", response_model=list[CitizenResponse])
def list_citizens(
    assembly_id: int,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List all citizens in an assembly.
    """
    query = db.query(Citizen).filter(Citizen.assembly_id == assembly_id)

    if group_id:
        query = query.filter(Citizen.group_id == group_id)

    citizens = query.all()

    if not citizens:
        # Check if assembly exists
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise HTTPException(status_code=404, detail="Assembly not found")

    return citizens


@router.get("/{assembly_id}/citizens/{citizen_id}", response_model=CitizenDetailResponse)
def get_citizen(
    assembly_id: int,
    citizen_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a citizen including system prompt.
    """
    citizen = db.query(Citizen).filter(
        Citizen.id == citizen_id,
        Citizen.assembly_id == assembly_id
    ).first()

    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    return citizen


@router.post("/{assembly_id}/citizens", status_code=202)
async def generate_citizens(
    assembly_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate citizens for the assembly.

    The assembly must be in PENDING status. Citizen generation
    runs in the background - poll the assembly status to track progress.
    """
    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()

    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")

    if assembly.status != AssemblyStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Assembly not in PENDING status (current: {assembly.status.value})"
        )

    # Check if citizens already exist
    existing_count = db.query(Citizen).filter(
        Citizen.assembly_id == assembly_id
    ).count()

    if existing_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Citizens already exist ({existing_count} found)"
        )

    # Check if assembly has custom citizen IDs stored
    custom_citizen_ids = assembly.custom_citizen_ids

    # Start background citizen generation
    background_tasks.add_task(
        create_assembly_with_citizens,
        assembly.id,
        assembly.num_citizens,
        assembly.num_groups,
        assembly.sampling_strategy,
        custom_citizen_ids=custom_citizen_ids
    )

    return {
        "message": "Citizen generation started",
        "assembly_id": assembly_id,
        "num_citizens": assembly.num_citizens,
        "num_groups": assembly.num_groups
    }


# =============================================================================
# BRIEFING ENDPOINTS
# =============================================================================

@router.post("/{assembly_id}/briefing", response_model=BriefingBookResponse)
async def generate_briefing(
    assembly_id: int,
    request: BriefingGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate a briefing book for the assembly.

    If a briefing already exists, it will be replaced.
    """
    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()

    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")

    if assembly.status == AssemblyStatus.GENERATING_BRIEFING:
        raise HTTPException(
            status_code=409,
            detail="Briefing generation already in progress"
        )

    # Start background briefing generation
    background_tasks.add_task(
        generate_briefing_for_assembly,
        assembly_id,
        request.depth
    )

    # Return current briefing if exists, or placeholder
    existing_briefing = db.query(BriefingBook).filter(
        BriefingBook.assembly_id == assembly_id
    ).first()

    if existing_briefing:
        return existing_briefing

    # Return placeholder response
    from datetime import datetime
    return BriefingBookResponse(
        id=0,
        assembly_id=assembly_id,
        topic_query=assembly.topic,
        content_markdown="Briefing generation in progress...",
        sections=None,
        sources=None,
        generated_at=datetime.utcnow()
    )


@router.get("/{assembly_id}/briefing", response_model=BriefingBookResponse)
def get_briefing(
    assembly_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the briefing book for an assembly.
    """
    briefing = db.query(BriefingBook).filter(
        BriefingBook.assembly_id == assembly_id
    ).first()

    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing book not found")

    return briefing


@router.delete("/{assembly_id}/briefing", status_code=204)
def delete_briefing(
    assembly_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete the briefing book for an assembly.
    """
    briefing = db.query(BriefingBook).filter(
        BriefingBook.assembly_id == assembly_id
    ).first()

    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing book not found")

    # Update assembly status if it was READY (go back to CITIZENS_READY)
    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
    if assembly and assembly.status == AssemblyStatus.READY:
        assembly.status = AssemblyStatus.CITIZENS_READY

    db.delete(briefing)
    db.commit()

    logger.info(f"Deleted briefing for assembly {assembly_id}")

    return briefing


# =============================================================================
# DELIBERATION ENDPOINTS
# =============================================================================

@router.post("/{assembly_id}/start", status_code=202)
async def start_deliberation(
    assembly_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start the deliberation process for an assembly.

    The assembly must have citizens and optionally a briefing book.
    Deliberation runs in the background - poll the assembly status
    or connect via WebSocket for real-time updates.
    """
    from app.api.services import run_deliberation_for_assembly

    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()

    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")

    # Check status
    if assembly.status not in [AssemblyStatus.READY, AssemblyStatus.CITIZENS_READY]:
        raise HTTPException(
            status_code=400,
            detail=f"Assembly not ready for deliberation (status: {assembly.status.value})"
        )

    # Check for citizens
    citizen_count = db.query(Citizen).filter(
        Citizen.assembly_id == assembly_id
    ).count()

    if citizen_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Assembly has no citizens"
        )

    # Start background deliberation
    background_tasks.add_task(
        run_deliberation_for_assembly,
        assembly_id
    )

    return {
        "message": "Deliberation started",
        "assembly_id": assembly_id,
        "status": "deliberating",
        "citizens": citizen_count
    }


# =============================================================================
# MESSAGE ENDPOINTS
# =============================================================================

@router.get("/{assembly_id}/messages", response_model=list[MessageResponse])
def list_messages(
    assembly_id: int,
    group_id: Optional[int] = None,
    phase: Optional[str] = None,
    round_number: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List messages from the deliberation.
    """
    query = db.query(Message).filter(Message.assembly_id == assembly_id)

    if group_id:
        query = query.filter(Message.group_id == group_id)
    if phase:
        query = query.filter(Message.phase == phase)
    if round_number:
        query = query.filter(Message.round_number == round_number)

    messages = query.order_by(Message.created_at).offset(offset).limit(limit).all()

    # Add citizen names to response
    result = []
    for msg in messages:
        response = MessageResponse(
            id=msg.id,
            assembly_id=msg.assembly_id,
            group_id=msg.group_id,
            citizen_id=msg.citizen_id,
            citizen_name=msg.citizen.name if msg.citizen else None,
            phase=msg.phase,
            round_number=msg.round_number,
            role=msg.role,
            content=msg.content,
            citations=msg.citations,
            fact_check_status=msg.fact_check_status,
            created_at=msg.created_at
        )
        result.append(response)

    return result


# =============================================================================
# GROUP ENDPOINTS
# =============================================================================

@router.get("/{assembly_id}/groups", response_model=list[GroupResponse])
def list_groups(
    assembly_id: int,
    db: Session = Depends(get_db)
):
    """
    List all deliberation groups in an assembly.
    """
    groups = db.query(DeliberationGroup).filter(
        DeliberationGroup.assembly_id == assembly_id
    ).order_by(DeliberationGroup.name).all()

    if not groups:
        assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
        if not assembly:
            raise HTTPException(status_code=404, detail="Assembly not found")

    # Count citizens per group
    result = []
    for group in groups:
        citizen_count = db.query(Citizen).filter(
            Citizen.group_id == group.id
        ).count()

        result.append(GroupResponse(
            id=group.id,
            name=group.name,
            round_summaries=group.round_summaries,
            consensus_summary=group.consensus_summary,
            disagreements_summary=group.disagreements_summary,
            citizen_count=citizen_count,
            created_at=group.created_at
        ))

    return result


# =============================================================================
# REPORT ENDPOINTS
# =============================================================================

@router.get("/{assembly_id}/report", response_model=ReportResponse)
def get_report(
    assembly_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the final report for an assembly.
    """
    report = db.query(Report).filter(Report.assembly_id == assembly_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


# =============================================================================
# RESEARCH ENDPOINTS
# =============================================================================

@router.get("/{assembly_id}/research", response_model=list[RoundResearchResponse])
def list_research(
    assembly_id: int,
    round_number: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List follow-up research results for an assembly, optionally filtered by round.
    """
    # Verify assembly exists
    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")

    query = db.query(RoundResearch).filter(RoundResearch.assembly_id == assembly_id)

    if round_number is not None:
        query = query.filter(RoundResearch.round_number == round_number)

    return query.order_by(RoundResearch.round_number).all()
