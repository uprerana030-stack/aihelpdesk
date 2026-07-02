"""Rebuild the vector store from the SQLite database.

Run this whenever the embedding model (GEMINI_EMBEDDING_MODEL) changes — vectors
of different dimensions cannot be compared, so a stale index must be rebuilt:

    python backend/reindex.py

It clears both vector collections (KB chunks + ticket embeddings) and re-embeds
every knowledge article and ticket with the CURRENT embedding backend, so all
stored vectors share one dimension and RAG / duplicate detection work correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a standalone script: add backend/ to the path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.tls import apply_tls_settings  # noqa: E402

apply_tls_settings()  # so Gemini embeddings can be reached through the proxy

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.embeddings import embedding_backend  # noqa: E402
from app.core.vectorstore import (  # noqa: E402
    KB_COLLECTION,
    TICKET_COLLECTION,
    reset_collection,
    upsert_ticket_embedding,
)
from app.models import KnowledgeArticle, Ticket  # noqa: E402
from app.services.kb_service import KBService  # noqa: E402


def _clear_collections() -> None:
    """Wipe both collections so no stale-dimension vectors survive."""
    for name in (KB_COLLECTION, TICKET_COLLECTION):
        reset_collection(name)
        print(f"  cleared {name}")
    # Remove any leftover numpy-fallback JSON files so a switch to ChromaDB
    # doesn't leave stale data behind.
    settings = get_settings()
    for name in (KB_COLLECTION, TICKET_COLLECTION):
        f = Path(settings.chroma_persist_dir) / f"{name}.json"
        if f.exists():
            f.unlink()


def run() -> None:
    print("Embedding backend:", embedding_backend())
    _clear_collections()

    db = SessionLocal()
    try:
        kb = KBService(db)
        articles = db.query(KnowledgeArticle).all()
        for article in articles:
            kb._index(article)  # delete + re-embed this article's chunks
        print(f"Re-indexed KB articles: {len(articles)}")

        tickets = db.query(Ticket).all()
        for t in tickets:
            text = f"{t.title}\n{t.description}\n{t.ocr_text or ''}".strip()
            upsert_ticket_embedding(t.id, text, t.status)
        print(f"Re-indexed tickets: {len(tickets)}")

        print("Reindex complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
