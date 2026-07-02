"""Vector store abstraction (design doc Section 10: ChromaDB).

Two collections: `kb_chunks` (knowledge base document chunks for RAG) and
`ticket_embeddings` (open tickets, for duplicate detection).

Backend selection is automatic:
  * Preferred: ChromaDB (persistent client).
  * Fallback: a pure-numpy cosine store persisted to JSON — used when ChromaDB
    has no wheel for the running interpreter (e.g. brand-new Python). This keeps
    FR-4 (duplicate detection) and FR-6/FR-7 (RAG retrieval) working anywhere.

Embeddings are computed by app.core.embeddings (the Embedding Agent), so both
backends store identical vectors and behave the same.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.embeddings import (
    TASK_DOCUMENT,
    TASK_QUERY,
    TASK_SIMILARITY,
    embed,
    embed_many,
)

logger = logging.getLogger("helpdesk.vectorstore")
settings = get_settings()

KB_COLLECTION = "kb_chunks"
TICKET_COLLECTION = "ticket_embeddings"


class _NumpyStore:
    """Minimal cosine-similarity store persisted as JSON per collection."""

    backend = "numpy-cosine"

    def __init__(self, persist_dir: str) -> None:
        self._dir = Path(persist_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, collection: str) -> Path:
        return self._dir / f"{collection}.json"

    def _load(self, collection: str) -> dict[str, Any]:
        p = self._path(collection)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"ids": [], "embeddings": [], "documents": [], "metadatas": []}

    def _save(self, collection: str, data: dict[str, Any]) -> None:
        self._path(collection).write_text(json.dumps(data), encoding="utf-8")

    def upsert(self, collection, ids, documents, metadatas, embeddings) -> None:
        data = self._load(collection)
        index = {existing: i for i, existing in enumerate(data["ids"])}
        for _id, doc, meta, emb in zip(ids, documents, metadatas, embeddings):
            if _id in index:
                i = index[_id]
                data["documents"][i], data["metadatas"][i], data["embeddings"][i] = doc, meta, emb
            else:
                data["ids"].append(_id)
                data["documents"].append(doc)
                data["metadatas"].append(meta)
                data["embeddings"].append(emb)
        self._save(collection, data)

    def delete(self, collection, ids) -> None:
        data = self._load(collection)
        keep = [i for i, _id in enumerate(data["ids"]) if _id not in set(ids)]
        for key in ("ids", "documents", "metadatas", "embeddings"):
            data[key] = [data[key][i] for i in keep]
        self._save(collection, data)

    def query(self, collection, query_embedding, top_k, where=None):
        data = self._load(collection)
        if not data["ids"]:
            return []
        mat = np.asarray(data["embeddings"], dtype=np.float32)
        q = np.asarray(query_embedding, dtype=np.float32)
        # vectors are L2-normalized at embed time, so dot product == cosine sim.
        sims = mat @ q
        order = np.argsort(-sims)
        results = []
        for i in order:
            meta = data["metadatas"][i] or {}
            if where and any(meta.get(k) != v for k, v in where.items()):
                continue
            results.append({
                "id": data["ids"][i],
                "document": data["documents"][i],
                "metadata": meta,
                "score": float(sims[i]),
            })
            if len(results) >= top_k:
                break
        return results

    def count(self, collection) -> int:
        return len(self._load(collection)["ids"])


class _ChromaStore:
    backend = "chromadb"

    def __init__(self, persist_dir: str) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=persist_dir)

    def _col(self, collection):
        return self._client.get_or_create_collection(collection)

    def upsert(self, collection, ids, documents, metadatas, embeddings) -> None:
        self._col(collection).upsert(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
        )

    def delete(self, collection, ids) -> None:
        self._col(collection).delete(ids=ids)

    def query(self, collection, query_embedding, top_k, where=None):
        col = self._col(collection)
        if col.count() == 0:
            return []
        res = col.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, col.count()),
            where=where or None,
        )
        out = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for _id, doc, meta, dist in zip(ids, docs, metas, dists):
            # Chroma returns squared L2 distance for normalized vectors;
            # convert to a cosine-like similarity in [0, 1].
            out.append({
                "id": _id,
                "document": doc,
                "metadata": meta or {},
                "score": max(0.0, 1.0 - float(dist) / 2.0),
            })
        return out

    def count(self, collection) -> int:
        return self._col(collection).count()


def _build_store():
    try:
        store = _ChromaStore(settings.chroma_persist_dir)
        logger.info("Vector store backend: chromadb")
        return store
    except Exception as exc:  # noqa: BLE001
        logger.warning("ChromaDB unavailable (%s); using numpy-cosine fallback.", exc)
        return _NumpyStore(settings.chroma_persist_dir)


_store = None


def _get_store():
    global _store
    if _store is None:
        _store = _build_store()
    return _store


def backend_name() -> str:
    return _get_store().backend


# ---- High-level helpers used by repositories / agents ----------------------

def add_kb_chunk(chunk_id: str, text: str, metadata: dict[str, Any]) -> None:
    _get_store().upsert(KB_COLLECTION, [chunk_id], [text], [metadata], [embed(text, TASK_DOCUMENT)])


def add_kb_chunks(items: list[tuple[str, str, dict[str, Any]]]) -> None:
    if not items:
        return
    ids = [i[0] for i in items]
    docs = [i[1] for i in items]
    metas = [i[2] for i in items]
    _get_store().upsert(KB_COLLECTION, ids, docs, metas, embed_many(docs, TASK_DOCUMENT))


def delete_kb_article(article_id: int) -> None:
    """Remove all chunks belonging to an article (numpy backend filters by metadata)."""
    store = _get_store()
    if isinstance(store, _NumpyStore):
        data = store._load(KB_COLLECTION)
        ids = [data["ids"][i] for i, m in enumerate(data["metadatas"]) if (m or {}).get("article_id") == article_id]
        if ids:
            store.delete(KB_COLLECTION, ids)
    else:
        store._col(KB_COLLECTION).delete(where={"article_id": article_id})


def search_kb(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    k = top_k or settings.rag_top_k
    try:
        return _get_store().query(KB_COLLECTION, embed(query, TASK_QUERY), k)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "KB vector search failed (%s). If the embedding model/dimension "
            "changed, rebuild the index: python backend/reindex.py", exc,
        )
        return []


def upsert_ticket_embedding(ticket_id: int, text: str, status: str) -> None:
    _get_store().upsert(
        TICKET_COLLECTION, [f"ticket-{ticket_id}"], [text],
        [{"ticket_id": ticket_id, "status": status}], [embed(text, TASK_SIMILARITY)],
    )


def find_similar_tickets(text: str, top_k: int = 5, exclude_ticket_id: int | None = None) -> list[dict[str, Any]]:
    try:
        results = _get_store().query(TICKET_COLLECTION, embed(text, TASK_SIMILARITY), top_k)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Ticket similarity search failed (%s). If the embedding model/"
            "dimension changed, rebuild the index: python backend/reindex.py", exc,
        )
        return []
    if exclude_ticket_id is not None:
        results = [r for r in results if r["metadata"].get("ticket_id") != exclude_ticket_id]
    return results


def kb_chunk_count() -> int:
    return _get_store().count(KB_COLLECTION)


def reset_collection(collection: str) -> None:
    """Drop all vectors in a collection. Used by reindex.py when the embedding
    model (and thus vector dimension) changes. Backend-agnostic."""
    store = _get_store()
    if isinstance(store, _NumpyStore):
        path = store._path(collection)
        if path.exists():
            path.unlink()
    else:  # chromadb
        try:
            store._client.delete_collection(collection)
        except Exception:  # noqa: BLE001 — collection may not exist yet
            pass
