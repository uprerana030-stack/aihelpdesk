"""Pydantic request/response schemas (FastAPI validation — design doc Section 8.1)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.security import Role


# --- Auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = ""
    # Optional: self-service employee registration only needs name/email/dept.
    # When omitted, a default demo password is used (identity is the email header).
    password: str | None = Field(default=None, min_length=6)
    role_name: str = Role.EMPLOYEE
    department: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    email: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role_name: str
    department: str | None = None
    is_available: bool = True

    model_config = {"from_attributes": True}


# --- Tickets ---
class TicketCreate(BaseModel):
    title: str = ""
    description: str = Field(min_length=1)
    # Optional client-provided idempotency key (NFR: Reliability).
    idempotency_key: str | None = None


class DuplicateSuggestion(BaseModel):
    ticket_id: int
    title: str
    similarity: float


class PipelineStep(BaseModel):
    agent: str
    event: str
    detail: str
    confidence: float | None = None


class TicketOut(BaseModel):
    id: int
    employee_id: int
    title: str
    description: str
    ocr_text: str = ""
    intent: str | None = None
    category: str | None = None
    priority: str | None = None
    priority_score: float = 0.0
    confidence: float = 0.0
    status: str
    resolution: str | None = None
    resolution_source: str | None = None
    kb_sources: list[dict] | None = None
    department: str | None = None
    assigned_agent_id: int | None = None
    duplicate_of_id: int | None = None
    escalation_target: str | None = None
    routing_reason: str | None = None
    created_at: datetime
    first_response_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class TicketSubmitResult(BaseModel):
    """Returned by the submission endpoint: the ticket + a trace of pipeline steps."""
    ticket: TicketOut
    pipeline: list[PipelineStep]
    duplicate_suggestions: list[DuplicateSuggestion] = []


class EscalatedTicketOut(BaseModel):
    """An escalated ticket for the manual-team dashboard, with employee contact."""
    ticket: TicketOut
    employee_name: str = ""
    employee_email: str = ""
    employee_department: str | None = None
    feedback_comment: str | None = None


class EscalateRequest(BaseModel):
    target: str = "L2"          # L2 / L3 / vendor
    note: str = ""


class ResolveRequest(BaseModel):
    resolution: str = Field(min_length=1)


# --- Knowledge base ---
class ArticleCreate(BaseModel):
    title: str
    content: str = Field(min_length=1)
    category: str = "General"


class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None


class ArticleOut(BaseModel):
    id: int
    title: str
    content: str
    category: str
    retrieval_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KBSearchResult(BaseModel):
    article_id: int | None = None
    title: str
    snippet: str
    score: float


# --- Feedback ---
class FeedbackCreate(BaseModel):
    rating: int = Field(ge=0, le=1)
    comment: str = ""


# --- Analytics ---
class AnalyticsOut(BaseModel):
    total_tickets: int
    auto_resolved: int
    agent_resolved: int
    auto_resolution_rate: float
    routing_accuracy: float
    avg_resolution_minutes: float | None
    avg_first_response_minutes: float | None
    escalation_rate: float
    by_department: dict[str, int]
    by_status: dict[str, int]
    csat: float | None
