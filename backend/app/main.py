"""FastAPI application entry point — the gateway (design doc Section 8.2.1).

Single entry point handling auth, routing of requests to internal services, and
response assembly. Async endpoints throughout (NFR: Scalability).
"""
from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.api import admin, analytics, auth, knowledge, notifications, tickets
from app.core.config import get_settings
from app.core.database import init_db
from app.core.llm import llm_configured
from app.core.tls import apply_tls_settings
from app.core.vectorstore import backend_name, kb_chunk_count

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

# Apply outbound TLS policy (CA bundle / disable-verify) before any HTTPS call
# to an external API (e.g. Gemini). See app/core/tls.py.
apply_tls_settings()

app = FastAPI(
    title="AI-Powered IT/Admin Helpdesk Router",
    version="1.0.0",
    description="Multi-agent ticket triage, RAG resolution, routing & escalation.",
)

# Streamlit frontend calls this API; allow cross-origin in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    init_db()
    # Resolve LLM/embedding availability off the request path so the first real
    # request isn't penalized (and so a blocked network degrades quietly).
    import threading

    def _prewarm() -> None:
        try:
            from app.core.diagnostics import log_diagnostics
            from app.core.llm import llm_complete

            llm_complete("ping")
            # Logs a clear AI-stack summary + warnings (empty index, hashing
            # fallback, dimension mismatch) so RAG problems are visible at boot.
            log_diagnostics()
        except Exception:  # noqa: BLE001
            pass

    threading.Thread(target=_prewarm, name="prewarm", daemon=True).start()



app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/status", tags=["system"])
async def status() -> dict:
    """System health & AI-governance visibility (System Administrator persona)."""
    return {
        "status": "ok",
        "llm_configured": llm_configured(),
        "vector_backend": backend_name(),
        "kb_chunks_indexed": kb_chunk_count(),
        "confidence_threshold": settings.ai_confidence_threshold,
        "duplicate_threshold": settings.duplicate_similarity_threshold,
    }
