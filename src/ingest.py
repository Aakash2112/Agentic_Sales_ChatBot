"""
Ingest 2026.pdf into a vectorized format:
  - vector_store/index.faiss  — FAISS index of chunk embeddings
  - vector_store/chunks.json  — chunk text + metadata
"""

import json
import os
import re
from pathlib import Path

import faiss
import numpy as np
import pdfplumber
from sentence_transformers import SentenceTransformer

PDF_PATH = "data/2026.pdf"
OUT_DIR = "data/vector_store"
EMBED_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE = 1600       # target characters, roughly ~400 tokens
CHUNK_OVERLAP = 300     # overlapping characters for context


def extract_pages(pdf_path: str) -> list[dict]:
    """Extract cleaned text from each PDF page."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = re.sub(r"\s+", " ", text).strip()

            if text:
                pages.append({
                    "page": i,
                    "text": text,
                })

    if not pages:
        raise ValueError(
            "No text extracted. This PDF may be scanned/image-based and may require OCR."
        )

    return pages


def split_into_sentences(text: str) -> list[str]:
    """Basic sentence splitting."""
    return re.split(r"(?<=[.!?])\s+", text)


def chunk_pages(pages: list[dict], size: int, overlap: int) -> list[dict]:
    """Create sentence-aware overlapping chunks per page."""
    if overlap >= size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")

    chunks = []
    chunk_id = 0

    for p in pages:
        sentences = split_into_sentences(p["text"])
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current) + len(sentence) + 1 <= size:
                current = f"{current} {sentence}".strip()
            else:
                if current:
                    chunks.append({
                        "chunk_id": chunk_id,
                        "page": p["page"],
                        "text": current,
                    })
                    chunk_id += 1

                # Carry over the last part of previous chunk for context
                overlap_text = current[-overlap:] if current else ""
                current = f"{overlap_text} {sentence}".strip()

        if current:
            chunks.append({
                "chunk_id": chunk_id,
                "page": p["page"],
                "text": current,
            })
            chunk_id += 1

    if not chunks:
        raise ValueError("No chunks created from extracted text.")

    return chunks


def embed_chunks(chunks: list[dict], model_name: str) -> np.ndarray:
    """Embed text chunks using SentenceTransformer."""
    model = SentenceTransformer(model_name)
    texts = [c["text"] for c in chunks]

    print(f"Embedding {len(texts)} chunks with {model_name}...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True,
    )

    return np.asarray(embeddings, dtype="float32")


def build_index(embeddings: np.ndarray) -> faiss.Index:
    """Build FAISS cosine-similarity index using normalized vectors."""
    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        raise ValueError("Invalid embeddings array.")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    return index


def save(index: faiss.Index, chunks: list[dict], out_dir: str) -> None:
    """Save FAISS index and chunk metadata."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, os.path.join(out_dir, "index.faiss"))

    with open(os.path.join(out_dir, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(chunks)} chunks → {out_dir}/")


if __name__ == "__main__":
    pages = extract_pages(PDF_PATH)
    print(f"Extracted text from {len(pages)} pages.")

    chunks = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"Created {len(chunks)} chunks.")

    embeddings = embed_chunks(chunks, EMBED_MODEL)

    index = build_index(embeddings)
    save(index, chunks, OUT_DIR)

    print("Done. Vector store ready in ./data/vector_store/")