"""Analytics service (FR-13; Success Metrics, Section 7).

Aggregates ticket/feedback data into the KPIs described in the design doc:
auto-resolution rate, routing accuracy, resolution & first-response times,
escalation rate, CSAT, and breakdowns by department/status.
"""
from __future__ import annotations

from app.models.ticket import TicketStatus
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas import AnalyticsOut


def _minutes(start, end) -> float | None:
    if start and end:
        return round((end - start).total_seconds() / 60.0, 2)
    return None


class AnalyticsService:
    def __init__(self, db) -> None:
        self.tickets = TicketRepository(db)
        self.feedback = FeedbackRepository(db)

    def compute(self) -> AnalyticsOut:
        tickets = self.tickets.list_all()
        total = len(tickets)

        resolved = [t for t in tickets if t.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)]
        # Automated = resolved by AI with no human: RAG auto-resolve OR duplicate-match.
        auto = [t for t in resolved if t.resolution_source in ("auto", "duplicate_match")]
        agent = [t for t in resolved if t.resolution_source == "agent"]
        escalated = [t for t in tickets if t.status == TicketStatus.ESCALATED or t.escalation_target]

        res_times = [m for t in resolved if (m := _minutes(t.created_at, t.resolved_at)) is not None]
        fr_times = [m for t in tickets if (m := _minutes(t.created_at, t.first_response_at)) is not None]

        # Routing accuracy proxy: routed tickets that were NOT later escalated
        # (i.e. reached the right team first time, no re-routing).
        routed = [t for t in tickets if t.department and t.resolution_source not in ("auto", "duplicate_match")]
        correctly_routed = [t for t in routed if not t.escalation_target]

        by_department: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for t in tickets:
            if t.department:
                by_department[t.department] = by_department.get(t.department, 0) + 1
            by_status[t.status] = by_status.get(t.status, 0) + 1

        fbs = self.feedback.all()
        csat = round(sum(f.rating for f in fbs) / len(fbs), 3) if fbs else None

        return AnalyticsOut(
            total_tickets=total,
            auto_resolved=len(auto),
            agent_resolved=len(agent),
            auto_resolution_rate=round(len(auto) / total, 3) if total else 0.0,
            routing_accuracy=round(len(correctly_routed) / len(routed), 3) if routed else 0.0,
            avg_resolution_minutes=round(sum(res_times) / len(res_times), 2) if res_times else None,
            avg_first_response_minutes=round(sum(fr_times) / len(fr_times), 2) if fr_times else None,
            escalation_rate=round(len(escalated) / total, 3) if total else 0.0,
            by_department=by_department,
            by_status=by_status,
            csat=csat,
        )
