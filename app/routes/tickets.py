import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.db_models import Ticket
from app.models.schemas import TicketCreate, TicketCreateResponse, TicketDetail, TicketListItem
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
