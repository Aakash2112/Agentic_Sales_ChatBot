import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import FAISS_INDEX_PATH, EMBEDDING_MODEL, TOP_K_RESULTS

_index = None
_chunks = None
_model = None


def _load():
    global _index, _chunks, _model
    if _index is None:
        index_file = os.path.join(FAISS_INDEX_PATH, "index.faiss")
        chunks_file = os.path.join(FAISS_INDEX_PATH, "chunks.json")
        if not os.path.exists(index_file):
            raise FileNotFoundError(
                f"FAISS index not found at {index_file}"
            )
        _index = faiss.read_index(index_file)
        with open(chunks_file, "r") as f:
            _chunks = json.load(f)
        _model = SentenceTransformer(EMBEDDING_MODEL)


def search(query: str, top_k: int = TOP_K_RESULTS) -> list[dict]:
    """Return top_k most relevant chunks for the query."""
    _load()
    query_embedding = _model.encode([query], convert_to_numpy=True).astype(np.float32)
    distances, indices = _index.search(query_embedding, top_k)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        chunk = _chunks[idx]
        results.append({
            "text": chunk["text"],
            "source": chunk.get("source", f"chunk-{chunk.get('chunk_id', idx)}"),
            "page": chunk.get("page", "?"),
            "score": float(dist),
        })
    return results


def get_context(query: str) -> str:
    """Return a formatted context string for injection into the LLM prompt."""
    results = search(query)
    if not results:
        return "No relevant information found."
    parts = []
    for r in results:
        parts.append(f"[{r['source']} - Page {r['page']}]\n{r['text']}")
    return "\n\n---\n\n".join(parts)
