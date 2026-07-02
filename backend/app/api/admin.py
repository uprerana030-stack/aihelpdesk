"""Admin / diagnostics endpoints — database overview.

Powers the frontend "Database" view: row counts per table plus the most recent
records, so the SQLite store can be inspected from the browser. Public, in line
with the rest of the API.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.diagnostics import run_diagnostics
from app.models import AuditLog, Feedback, KnowledgeArticle, Role, Ticket, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/diagnostics")
async def diagnostics() -> dict:
    """AI-stack health: embedding backend, vector store, KB chunk count, and a
    smoke retrieval — so a broken RAG path (0% auto-resolution) is visible."""
    return run_diagnostics()

# Displayed in the same order in the UI.
_TABLES = {
    "users": User,
    "tickets": Ticket,
    "knowledge_articles": KnowledgeArticle,
    "feedback": Feedback,
    "audit_logs": AuditLog,
    "roles": Role,
}


@router.get("/db")
async def db_overview(db: Session = Depends(get_db)) -> dict:
    """Row counts + recent records — a live snapshot of the SQLite store."""
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "")

    counts = {
        name: db.scalar(select(func.count()).select_from(model))
        for name, model in _TABLES.items()
    }

    recent_tickets = [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "category": t.category,
            "department": t.department,
            "confidence": t.confidence,
            "created_at": t.created_at,
        }
        for t in db.scalars(select(Ticket).order_by(Ticket.id.desc()).limit(10))
    ]

    recent_users = [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role_name": u.role_name,
            "department": u.department,
        }
        for u in db.scalars(select(User).order_by(User.id.desc()).limit(10))
    ]

    recent_feedback = [
        {
            "id": f.id,
            "ticket_id": f.ticket_id,
            "rating": f.rating,
            "comment": f.comment,
            "created_at": f.created_at,
        }
        for f in db.scalars(select(Feedback).order_by(Feedback.id.desc()).limit(10))
    ]

    return {
        "db_file": db_path,
        "exists": os.path.exists(db_path),
        "size_bytes": os.path.getsize(db_path) if os.path.exists(db_path) else 0,
        "counts": counts,
        "recent_tickets": recent_tickets,
        "recent_users": recent_users,
        "recent_feedback": recent_feedback,
    }
