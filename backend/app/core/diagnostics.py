"""AI-stack self-diagnostics (surfaced, never silently swallowed).

Confirms the vector store is up, the embedding backend is a REAL one (not the
near-random hashing fallback), the KB index is populated, and a smoke retrieval
against a seeded topic actually returns a hit. Used both at startup (logged) and
via GET /admin/diagnostics so the 0%-auto-resolution failure mode is visible.
"""
from __future__ import annotations

import logging

from app.core.embeddings import embed, embedding_backend
from app.core.llm import llm_configured
from app.core.vectorstore import backend_name, kb_chunk_count, search_kb

logger = logging.getLogger("helpdesk.diagnostics")

# A query that should match a seeded KB article once the index is healthy.
_SMOKE_QUERY = "how do I reset my password"


def run_diagnostics() -> dict:
    warnings: list[str] = []

    emb_backend = embedding_backend()
    try:
        emb_dim = len(embed("diagnostic probe"))
    except Exception as exc:  # noqa: BLE001
        emb_dim = 0
        warnings.append(f"embedding call failed: {exc}")

    if emb_backend.startswith("hashing"):
        warnings.append(
            "Embedding backend is the HASHING FALLBACK (near-random vectors) — "
            "RAG similarity will be unreliable and auto-resolution will stay low. "
            "Ensure Gemini is reachable (GEMINI_API_KEY + network/TLS) or install "
            "sentence-transformers."
        )

    chunks = kb_chunk_count()
    if chunks == 0:
        warnings.append("KB index is EMPTY (0 chunks). Run: python backend/reindex.py")

    # Smoke retrieval — proves query dim matches stored dim and search returns hits.
    smoke: dict = {"query": _SMOKE_QUERY}
    try:
        hits = search_kb(_SMOKE_QUERY, top_k=1)
        if hits:
            top = hits[0]
            smoke.update(
                ok=True,
                top_title=(top.get("metadata") or {}).get("title"),
                top_score=round(float(top.get("score", 0.0)), 3),
            )
        else:
            smoke["ok"] = False
            warnings.append("Smoke retrieval returned no hits (empty index or dimension mismatch).")
    except Exception as exc:  # noqa: BLE001
        smoke.update(ok=False, error=str(exc))
        warnings.append(f"Smoke retrieval error: {exc}")

    result = {
        "healthy": not warnings,
        "llm_configured": llm_configured(),
        "embedding_backend": emb_backend,
        "embedding_dim": emb_dim,
        "vector_backend": backend_name(),
        "kb_chunks": chunks,
        "smoke_retrieval": smoke,
        "warnings": warnings,
    }
    return result


def log_diagnostics() -> dict:
    """Run diagnostics and log a clear one-line summary + any warnings."""
    d = run_diagnostics()
    logger.info(
        "AI stack: llm=%s embed=%s(dim=%s) vectors=%s kb_chunks=%s smoke=%s",
        d["llm_configured"], d["embedding_backend"], d["embedding_dim"],
        d["vector_backend"], d["kb_chunks"], d["smoke_retrieval"].get("ok"),
    )
    for w in d["warnings"]:
        logger.warning("DIAGNOSTIC: %s", w)
    if d["healthy"]:
        logger.info("AI stack healthy: RAG auto-resolution is expected to work.")
    return d
