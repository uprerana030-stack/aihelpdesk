"""Duplicate Agent (design doc Section 9.1 step 6 / FR-4).

Vector-similarity check against existing OPEN tickets, with two tiers:
  * at/above the MERGE threshold  -> flagged as a duplicate; the orchestrator
    auto-resolves the new ticket from the original's recorded resolution.
  * between SUGGEST and MERGE      -> surfaced as "possible duplicate"
    suggestions only; the pipeline continues to RAG.
Only matches at/above the SUGGEST threshold are shown at all, so weak
hashing-fallback noise doesn't pollute the suggestion banner.
"""
from __future__ import annotations

from app.agents.base import AgentResult
from app.core.config import get_settings
from app.core.embeddings import is_semantic_backend
from app.core.vectorstore import find_similar_tickets

settings = get_settings()


class DuplicateAgent:
    name = "DuplicateAgent"

    def run(self, text: str, exclude_ticket_id: int | None = None) -> AgentResult:
        # Safety: if only the hashing fallback is available, similarity is not
        # semantic, so DO NOT flag duplicates (this is what caused the earlier
        # false 74-88% matches). Skip cleanly and let RAG/routing handle it.
        if not is_semantic_backend():
            return AgentResult(
                self.name, "duplicate_checked",
                {"is_duplicate": False, "duplicate_of_id": None, "suggestions": [],
                 "merge_threshold": settings.duplicate_similarity_threshold,
                 "suggest_threshold": settings.duplicate_suggest_threshold},
                confidence=0.0, model_version="vector-cosine-1.0",
                detail="Duplicate check skipped: semantic embeddings unavailable.",
            )

        matches = find_similar_tickets(text, top_k=5, exclude_ticket_id=exclude_ticket_id)
        merge_threshold = settings.duplicate_similarity_threshold
        suggest_threshold = settings.duplicate_suggest_threshold
        suggestions = [
            {
                "ticket_id": m["metadata"].get("ticket_id"),
                "title": (m["document"] or "")[:80],
                "similarity": round(m["score"], 3),
            }
            for m in matches
            if m["score"] >= suggest_threshold
        ]
        top = suggestions[0] if suggestions else None
        is_duplicate = bool(top and top["similarity"] >= merge_threshold)
        return AgentResult(
            self.name,
            "duplicate_checked",
            {
                "is_duplicate": is_duplicate,
                "duplicate_of_id": top["ticket_id"] if is_duplicate else None,
                "suggestions": suggestions,
                "merge_threshold": merge_threshold,
                "suggest_threshold": suggest_threshold,
            },
            confidence=top["similarity"] if top else 0.0,
            model_version="vector-cosine-1.0",
            detail=(
                f"Duplicate of #{top['ticket_id']} (sim={top['similarity']:.2f}) — merging."
                if is_duplicate
                else (
                    f"{len(suggestions)} possible duplicate(s) above {suggest_threshold:.2f}; continuing to RAG."
                    if suggestions else f"No similar ticket above {suggest_threshold:.2f}."
                )
            ),
        )
