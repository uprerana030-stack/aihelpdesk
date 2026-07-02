"""Ticket service — submission and lifecycle management.

Owns idempotency (NFR: Reliability), persistence, invocation of the multi-agent
orchestrator, and post-pipeline notifications. Keeps the API thin.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.agents.orchestrator import AgentOrchestrator
from app.core.security import Role
from app.models import Feedback, Ticket, User
from app.models.ticket import TicketStatus
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.log_repo import LogRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.user_repo import UserRepository
from app.schemas import TicketOut
from app.services.notification_service import NotificationService


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ticket_to_out(ticket: Ticket) -> TicketOut:
    sources = None
    if ticket.kb_sources:
        try:
            sources = json.loads(ticket.kb_sources)
        except json.JSONDecodeError:
            sources = None
    return TicketOut(
        id=ticket.id, employee_id=ticket.employee_id, title=ticket.title,
        description=ticket.description, ocr_text=ticket.ocr_text, intent=ticket.intent,
        category=ticket.category, priority=ticket.priority, priority_score=ticket.priority_score,
        confidence=ticket.confidence, status=ticket.status, resolution=ticket.resolution,
        resolution_source=ticket.resolution_source, kb_sources=sources, department=ticket.department,
        assigned_agent_id=ticket.assigned_agent_id, duplicate_of_id=ticket.duplicate_of_id,
        escalation_target=ticket.escalation_target, routing_reason=ticket.routing_reason,
        created_at=ticket.created_at, first_response_at=ticket.first_response_at,
        resolved_at=ticket.resolved_at, closed_at=ticket.closed_at,
    )


class TicketService:
    def __init__(self, db) -> None:
        self.db = db
        self.tickets = TicketRepository(db)
        self.users = UserRepository(db)
        self.feedback = FeedbackRepository(db)
        self.logs = LogRepository(db)
        self.notifier = NotificationService(db)

    # --- Submission (workflow steps 1-12) ---
    def submit(self, employee: User, title: str, description: str,
               attachment_path: str | None, idempotency_key: str | None):
        # Idempotency: an identical retried submission returns the same ticket
        # rather than re-running the AI pipeline (NFR: Reliability).
        if idempotency_key:
            existing = self.tickets.get_by_idempotency_key(idempotency_key)
            if existing:
                logs = self.logs.list_for_ticket(existing.id)
                steps = [
                    {"agent": l.agent_name or l.actor, "event": l.event, "detail": "(replayed)",
                     "confidence": l.confidence}
                    for l in logs if l.agent_name
                ]
                return existing, steps, []

        ticket = Ticket(
            employee_id=employee.id, title=title or description[:60],
            description=description, attachment_path=attachment_path,
            status=TicketStatus.OPEN, idempotency_key=idempotency_key,
        )
        ticket = self.tickets.add(ticket)
        self.logs.record(event="ticket_submitted", ticket_id=ticket.id, actor=employee.email)

        orchestrator = AgentOrchestrator(self.db)
        steps, suggestions = orchestrator.process(ticket)
        ticket = self.tickets.save(ticket)

        # Notify per outcome (FR-15): auto-resolved -> employee; routed -> managers.
        if ticket.status == TicketStatus.RESOLVED:
            self.notifier.notify_ticket_resolved(ticket, employee.email)
        elif ticket.status != TicketStatus.DUPLICATE:
            self.notifier.notify_managers_new_ticket(ticket)
        return ticket, steps, suggestions

    # --- Tracking / access control ---
    def get_for_user(self, ticket_id: int, user: User) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found.")
        self._authorize_view(ticket, user)
        return ticket

    def _authorize_view(self, ticket: Ticket, user: User) -> None:
        if user.role_name in Role.MANAGER_ROLES or user.role_name == Role.SYSTEM_ADMIN:
            return
        if ticket.employee_id == user.id:
            return
        if user.role_name in Role.AGENT_ROLES and (
            ticket.assigned_agent_id == user.id or ticket.department == user.department
        ):
            return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view this ticket.")

    def list_for_user(self, user: User) -> list[Ticket]:
        if user.role_name in Role.MANAGER_ROLES:
            return self.tickets.list_all()
        if user.role_name in Role.AGENT_ROLES:
            dept = self.tickets.list_for_department(user.department) if user.department else []
            mine = self.tickets.list_for_agent(user.id)
            merged = {t.id: t for t in (dept + mine)}
            return sorted(merged.values(), key=lambda t: t.created_at, reverse=True)
        return self.tickets.list_for_employee(user.id)

    # --- Escalation (FR-9, Section 3.6) ---
    def escalate(self, ticket_id: int, user: User, target: str, note: str) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found.")
        if user.role_name not in Role.AGENT_ROLES and user.role_name not in Role.MANAGER_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only agents/managers can escalate.")
        ticket.status = TicketStatus.ESCALATED
        ticket.escalation_target = target
        ticket.routing_reason = (ticket.routing_reason or "") + f"\nEscalated to {target}: {note}"
        ticket = self.tickets.save(ticket)
        self.logs.record(event="escalated", ticket_id=ticket.id, actor=user.email,
                         output_data={"target": target, "note": note})
        employee = self.users.get(ticket.employee_id)
        self.notifier.notify_ticket_escalated(ticket, employee.email if employee else None)
        return ticket

    # --- Agent/manual resolution (Section 3.6) ---
    def resolve(self, ticket_id: int, user: User, resolution: str) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found.")
        if user.role_name not in Role.AGENT_ROLES and user.role_name not in Role.MANAGER_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only agents/managers can resolve.")
        ticket.status = TicketStatus.RESOLVED
        ticket.resolution = resolution
        ticket.resolution_source = "agent"
        ticket.resolved_at = _now()
        if ticket.first_response_at is None:
            ticket.first_response_at = _now()
        ticket = self.tickets.save(ticket)
        self.logs.record(event="agent_resolved", ticket_id=ticket.id, actor=user.email)
        employee = self.users.get(ticket.employee_id)
        self.notifier.notify_ticket_resolved_by_agent(ticket, employee.email if employee else None)
        return ticket

    def close(self, ticket_id: int, user: User) -> Ticket:
        ticket = self.get_for_user(ticket_id, user)
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = _now()
        ticket = self.tickets.save(ticket)
        self.logs.record(event="closed", ticket_id=ticket.id, actor=user.email)
        return ticket

    # --- Feedback (FR-14, Section 3.8) ---
    def add_feedback(self, ticket_id: int, user: User, rating: int, comment: str) -> Feedback:
        ticket = self.get_for_user(ticket_id, user)
        if ticket.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "Feedback allowed only on resolved/closed tickets.")
        fb = self.feedback.add(Feedback(ticket_id=ticket.id, user_id=user.id, rating=rating, comment=comment))
        self.logs.record(event="feedback_received", ticket_id=ticket.id, actor=user.email,
                         output_data={"rating": rating})
        # If the employee says an AI-generated resolution did NOT work (thumbs
        # down), the automated fix failed -> escalate to the human team so an
        # agent can pick it up and contact the employee.
        if rating == 0 and ticket.resolution_source in ("auto", "duplicate_match"):
            self._escalate_from_feedback(ticket, user, comment)
        return fb

    def _escalate_from_feedback(self, ticket: Ticket, user: User, comment: str) -> None:
        """Re-open an auto-resolved ticket that the employee reports unresolved,
        route it to the right human team, and assign an available agent."""
        from app.agents.routing_agent import RoutingAgent

        dept = ticket.department
        if not dept:
            dept = RoutingAgent().run(ticket.category, 0.0).output.get("department")
        ticket.department = dept
        ticket.status = TicketStatus.ESCALATED
        ticket.escalation_target = "human_team"
        ticket.resolved_at = None  # no longer considered resolved
        reason = ("The automated solution did not resolve the issue (employee feedback), "
                  f"so it was escalated to the {dept} team for manual handling.")
        if comment:
            reason += f' Employee note: "{comment}"'
        ticket.routing_reason = reason

        agent = self.users.pick_available_agent(dept)
        if agent:
            ticket.assigned_agent_id = agent.id
        self.tickets.save(ticket)
        self.logs.record(event="escalated_from_feedback", ticket_id=ticket.id, actor=user.email,
                         output_data={"department": dept, "comment": comment})
        employee = self.users.get(ticket.employee_id)
        self.notifier.notify_ticket_escalated(ticket, employee.email if employee else None)

    def list_escalations(self, user: User) -> list[dict]:
        """Escalated tickets for the manual team, enriched with the employee's
        contact details and their feedback comment (why the auto-fix failed)."""
        if user.role_name not in Role.AGENT_ROLES and user.role_name not in Role.MANAGER_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only agents/managers can view escalations.")
        escalated = [t for t in self.list_for_user(user) if t.status == TicketStatus.ESCALATED]
        out = []
        for t in escalated:
            emp = self.users.get(t.employee_id)
            comments = [f.comment for f in self.feedback.list_for_ticket(t.id) if f.comment]
            out.append({
                "ticket": ticket_to_out(t),
                "employee_name": emp.full_name if emp else "",
                "employee_email": emp.email if emp else "",
                "employee_department": emp.department if emp else None,
                "feedback_comment": comments[-1] if comments else None,
            })
        return out

    def audit_trail(self, ticket_id: int, user: User):
        ticket = self.get_for_user(ticket_id, user)
        return self.logs.list_for_ticket(ticket.id)
