"""Seed script — demo users, roles, KB articles, and a few tickets.

Run once after install so the app is immediately demoable:
    python backend/seed.py

Idempotent-ish: skips users/articles that already exist by email/title.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a standalone script: add backend/ to the path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.security import Role, hash_password  # noqa: E402
from app.models import User  # noqa: E402
from app.repositories.user_repo import RoleRepository  # noqa: E402
from app.services.kb_service import KBService, format_article_content  # noqa: E402
from app.services.ticket_service import TicketService  # noqa: E402
from kb_articles import KB_ARTICLES  # noqa: E402  (backend/kb_articles.py)

DEMO_PASSWORD = "Password123"

DEMO_USERS = [
    ("employee@demo.com", "Eva Employee", Role.EMPLOYEE, None),
    ("it.agent@demo.com", "Ian ITAgent", Role.IT_AGENT, "IT"),
    ("hr.agent@demo.com", "Hana HRAgent", Role.ADMIN_AGENT, "HR"),
    ("finance.agent@demo.com", "Femi Finance", Role.ADMIN_AGENT, "Finance"),
    ("manager@demo.com", "Maya Manager", Role.HELPDESK_MANAGER, None),
    ("kbadmin@demo.com", "Karl KBAdmin", Role.KB_ADMIN, None),
    ("sysadmin@demo.com", "Sam SysAdmin", Role.SYSTEM_ADMIN, None),
]

ROLE_DESCRIPTIONS = {
    Role.EMPLOYEE: "End user submitting support requests.",
    Role.IT_AGENT: "Technical staff resolving IT tickets.",
    Role.ADMIN_AGENT: "Handles non-technical admin requests (HR/Finance/Facilities).",
    Role.HELPDESK_MANAGER: "Oversees volume, SLA, team performance; sees analytics.",
    Role.KB_ADMIN: "Curates knowledge base articles for RAG.",
    Role.SYSTEM_ADMIN: "Platform configuration, roles, audit, governance.",
}

DEMO_TICKETS = [
    ("I forgot my password and I'm locked out", "I tried logging in several times this morning and now "
     "my account is locked. I need to reset my corporate password to get back into my email."),
    ("VPN keeps disconnecting every few minutes", "Since yesterday the VPN drops every couple of minutes "
     "while I work from home. It reconnects but it's making it impossible to work."),
    ("Need to claim travel expenses", "I traveled for a client meeting last week and want to submit my "
     "taxi and hotel receipts for reimbursement. How do I do this?"),
]


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        role_repo = RoleRepository(db)
        for name, desc in ROLE_DESCRIPTIONS.items():
            role_repo.upsert(name, desc)

        email_to_user: dict[str, User] = {}
        for email, name, role, dept in DEMO_USERS:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                email_to_user[email] = existing
                continue
            user = User(email=email, full_name=name, hashed_password=hash_password(DEMO_PASSWORD),
                        role_name=role, department=dept)
            db.add(user)
            db.commit()
            db.refresh(user)
            email_to_user[email] = user
        print(f"Users ready: {len(email_to_user)} (password for all demo users: {DEMO_PASSWORD})")

        kb = KBService(db)
        existing_titles = {a.title for a in kb.list()}
        created = 0
        from app.schemas import ArticleCreate
        admin = email_to_user["kbadmin@demo.com"]
        for art in KB_ARTICLES:
            if art["title"] in existing_titles:
                continue
            content = format_article_content(art["issue"], art["solution"])
            kb.create(
                ArticleCreate(title=art["title"], content=content, category=art["category"]),
                author_id=admin.id,
            )
            created += 1
        print(f"KB articles created: {created} (total {len(kb.list())})")

        ticket_service = TicketService(db)
        employee = email_to_user["employee@demo.com"]
        if not ticket_service.tickets.list_for_employee(employee.id):
            for title, desc in DEMO_TICKETS:
                ticket, _, _ = ticket_service.submit(employee, title, desc, None, None)
                print(f"  Ticket #{ticket.id}: status={ticket.status}, "
                      f"category={ticket.category}, conf={ticket.confidence:.2f}")
        else:
            print("Demo tickets already present; skipping.")

        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
