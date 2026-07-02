"""Ticket endpoints — submission, tracking, listing, escalation, resolution,
feedback, and audit trail (design doc Sections 3.1, 3.5, 3.6, 3.8, FR-12)."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models import User
from app.schemas import (
    DuplicateSuggestion,
    EscalatedTicketOut,
    EscalateRequest,
    FeedbackCreate,
    PipelineStep,
    ResolveRequest,
    TicketOut,
    TicketSubmitResult,
)
from app.services.ticket_service import TicketService, ticket_to_out
from app.core.database import get_db

router = APIRouter(prefix="/tickets", tags=["tickets"])
settings = get_settings()


def _save_upload(file: UploadFile | None) -> str | None:
    if not file:
        return None
    suffix = Path(file.filename or "").suffix
    dest = Path(settings.upload_dir) / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(file.file.read())
    return str(dest)


@router.post("", response_model=TicketSubmitResult, status_code=201)
async def submit_ticket(
    description: str = Form(...),
    title: str = Form(""),
    idempotency_key: str | None = Form(None),
    attachment: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketSubmitResult:
    path = _save_upload(attachment)
    service = TicketService(db)
    ticket, steps, suggestions = service.submit(user, title, description, path, idempotency_key)
    return TicketSubmitResult(
        ticket=ticket_to_out(ticket),
        pipeline=[PipelineStep(**s) for s in steps],
        duplicate_suggestions=[DuplicateSuggestion(**s) for s in suggestions if s.get("ticket_id")],
    )


@router.get("", response_model=list[TicketOut])
async def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [ticket_to_out(t) for t in TicketService(db).list_for_user(user)]


@router.get("/escalations", response_model=list[EscalatedTicketOut])
async def list_escalations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manual-team dashboard: escalated tickets + employee contact details."""
    return TicketService(db).list_escalations(user)


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ticket_to_out(TicketService(db).get_for_user(ticket_id, user))


@router.get("/{ticket_id}/audit")
async def get_audit_trail(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = TicketService(db).audit_trail(ticket_id, user)
    return [
        {
            "event": l.event, "agent": l.agent_name, "actor": l.actor,
            "model_version": l.model_version, "confidence": l.confidence,
            "created_at": l.created_at, "output": l.output_json,
        }
        for l in logs
    ]


@router.post("/{ticket_id}/escalate", response_model=TicketOut)
async def escalate_ticket(ticket_id: int, payload: EscalateRequest,
                          user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ticket_to_out(TicketService(db).escalate(ticket_id, user, payload.target, payload.note))


@router.post("/{ticket_id}/resolve", response_model=TicketOut)
async def resolve_ticket(ticket_id: int, payload: ResolveRequest,
                         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ticket_to_out(TicketService(db).resolve(ticket_id, user, payload.resolution))


@router.post("/{ticket_id}/close", response_model=TicketOut)
async def close_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ticket_to_out(TicketService(db).close(ticket_id, user))


@router.post("/{ticket_id}/feedback", status_code=201)
async def submit_feedback(ticket_id: int, payload: FeedbackCreate,
                          user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = TicketService(db)
    fb = service.add_feedback(ticket_id, user, payload.rating, payload.comment)
    # Report whether negative feedback triggered escalation to the human team,
    # so the employee UI can say "an agent will contact you".
    ticket = service.tickets.get(ticket_id)
    escalated = bool(ticket and ticket.status == "escalated")
    return {"id": fb.id, "ticket_id": fb.ticket_id, "rating": fb.rating,
            "escalated": escalated, "status": ticket.status if ticket else None}
