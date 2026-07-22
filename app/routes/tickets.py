import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.db_models import Log, Ticket
from app.models.schemas import (
    RejectedLogItem,
    TicketCreate,
    TicketCreateResponse,
    TicketDetail,
    TicketListItem,
)
from app.pipeline.graph import run_pipeline
from app.rate_limit import limiter
from app.security import verify_api_key

settings = get_settings()

router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(verify_api_key)])


@router.post("", response_model=TicketCreateResponse)
@limiter.limit(settings.rate_limit)
async def create_ticket(request: Request, payload: TicketCreate) -> TicketCreateResponse:
    """Submit a new ticket. Runs the full LangGraph pipeline synchronously
    (in a worker thread, since the pipeline's LLM/DB calls are blocking) and
    returns the outcome. Rejected tickets (failed validation or a confirmed
    prompt injection attempt) are logged but never written to `tickets`."""
    state = await asyncio.to_thread(run_pipeline, payload.raw_text)

    if state.get("rejected"):
        return TicketCreateResponse(
            id=None,
            accepted=False,
            message=state.get("rejection_reason"),
        )

    return TicketCreateResponse(
        id=uuid.UUID(state["ticket_id"]),
        accepted=True,
        status=state.get("status"),
    )


@router.get("", response_model=list[TicketListItem])
@limiter.limit(settings.rate_limit)
async def list_tickets(
    request: Request, db: AsyncSession = Depends(get_db)
) -> list[Ticket]:
    result = await db.execute(select(Ticket).order_by(Ticket.created_at.desc()))
    return list(result.scalars().all())


@router.get("/rejected", response_model=list[RejectedLogItem])
@limiter.limit(settings.rate_limit)
async def list_rejected_tickets(
    request: Request, db: AsyncSession = Depends(get_db)
) -> list[Log]:
    """Lists tickets that never made it into `tickets` — rejected by
    validation or a confirmed prompt injection attempt. These only exist
    as orphan `logs` rows (ticket_id IS NULL), for audit visibility."""
    result = await db.execute(
        select(Log)
        .where(Log.ticket_id.is_(None), Log.success.is_(False))
        .order_by(Log.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{ticket_id}", response_model=TicketDetail)
@limiter.limit(settings.rate_limit)
async def get_ticket(
    request: Request, ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Ticket:
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.logs))
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.delete("/{ticket_id}", status_code=204)
@limiter.limit(settings.rate_limit)
async def delete_ticket(
    request: Request, ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    """Deletes a ticket and its logs (FK is ON DELETE CASCADE)."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await db.delete(ticket)
    await db.commit()
