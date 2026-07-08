"""RAG / Resolution Agent (design doc Section 8.2.1 / FR-6, FR-7, FR-8).

Pipeline: Vector Search (ChromaDB) -> LLM -> grounded Response. Returns a
candidate answer, the KB citations it used, and a confidence score that the
orchestrator compares against AI_CONFIDENCE_THRESHOLD (Section 9.1 step 8).

If no LLM is configured/available, confidence is forced low so the ticket is
routed to a human team rather than auto-resolved (graceful degradation).
"""
from __future__ import annotations

from app.agents.base import AgentResult, extract_json
from app.core.config import get_settings
from app.core.llm import llm_complete
from app.core.vectorstore import search_kb

settings = get_settings()

_SYSTEM = (
    "You are an IT/Admin helpdesk resolution assistant. Answer ONLY from the provided "
    "knowledge base context. If the context is insufficient, say so and set a low confidence. "
    "Respond with JSON only."
)


class RAGAgent:
    name = "RAGAgent"

    def run(self, query: str) -> AgentResult:
        chunks = search_kb(query, top_k=settings.rag_top_k)
        sources = [
            {
                "article_id": c["metadata"].get("article_id"),
                "title": c["metadata"].get("title", "Untitled"),
                "snippet": (c["document"] or "")[:240],
                "score": round(c["score"], 3),
            }
            for c in chunks
        ]
        retrieval_strength = max((c["score"] for c in chunks), default=0.0)

        if not chunks:
            return AgentResult(
                self.name, "rag_generated",
                {"answer": "", "sources": [], "retrieval_strength": 0.0},
                confidence=0.0, model_version="rag-1.0",
                detail="No KB chunks retrieved; routing to a human team.",
            )

        context = "\n\n".join(
            f"[{i+1}] {c['metadata'].get('title','')}\n{c['document']}" for i, c in enumerate(chunks)
        )
        prompt = (
            f"Knowledge base context:\n{context}\n\n"
            f"Employee request:\n{query}\n\n"
            "Return JSON: {\"answer\": <grounded answer citing [n]>, "
            "\"confidence\": <0..1 how well the KB answers this>}"
        )
        result = llm_complete(prompt, system=_SYSTEM)

        if not result.available:
            # Graceful degradation: when LLM is unavailable, use KB retrieval strength as confidence
            # if require_gemini is False. This allows auto-resolution from strong KB matches
            # even without an LLM. Otherwise, force low confidence so the ticket routes to humans.
            confidence = retrieval_strength if not settings.require_gemini else 0.0
            detail = (
                f"Using KB retrieval strength as confidence ({confidence:.0%}) — LLM unavailable."
                if not settings.require_gemini
                else "LLM unavailable; degrading to manual routing."
            )
            return AgentResult(
                self.name, "rag_generated",
                {"answer": "", "sources": sources, "retrieval_strength": round(retrieval_strength, 3)},
                confidence=confidence, model_version="none",
                detail=detail,
            )

        data = extract_json(result.text) or {}
        answer = data.get("answer") or result.text.strip()
        llm_conf = float(data.get("confidence", 0.5) or 0.5)
        # Blend LLM self-assessed confidence with retrieval strength.
        confidence = max(0.0, min(1.0, 0.6 * llm_conf + 0.4 * retrieval_strength))
        return AgentResult(
            self.name, "rag_generated",
            {"answer": answer, "sources": sources, "retrieval_strength": round(retrieval_strength, 3)},
            confidence=confidence,
            model_version=f"{result.provider}:{result.model}",
            detail=f"Generated grounded answer (conf={confidence:.2f}).",
        )
