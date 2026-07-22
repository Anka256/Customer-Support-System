import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["refund", "technical_issue", "billing", "general_question", "complaint"]
Priority = Literal["urgent", "normal"]
Status = Literal["auto_ready", "manual_review"]


class TicketCreate(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=20_000)


class TicketCreateResponse(BaseModel):
    """Returned immediately after POST /tickets — pipeline runs synchronously."""

    id: uuid.UUID | None
    accepted: bool
    status: Status | None = None
    message: str | None = None


class LogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    step_name: str
    duration_ms: int
    success: bool
    error_message: str | None
    created_at: datetime


class RejectedLogItem(BaseModel):
    """A log entry for a ticket that was rejected (validation failure or
    confirmed prompt injection) and therefore never made it into `tickets`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    step_name: str
    error_message: str | None
    created_at: datetime


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str | None
    priority: str | None
    status: str
    detected_language: str | None
    confidence_score: int | None
    created_at: datetime


class TicketDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_text: str
    detected_language: str | None
    category: str | None
    priority: str | None
    summary: str | None
    draft_reply: str | None
    confidence_score: int | None
    status: str
    retry_count: int
    created_at: datetime
    logs: list[LogEntry] = []
