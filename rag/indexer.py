"""
Builds a FAISS index from PDF files in the data/ directory.
Run this once (or whenever data changes): python -m rag.indexer
"""

import os
import json
import pickle
import numpy as np
import faiss
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from config import DATA_DIR, FAISS_INDEX_PATH, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP


def load_pdfs(data_dir: str) -> list[dict]:
    """Extract text from all PDFs in data_dir, return list of {text, source}."""
    documents = []
    for filename in os.listdir(data_dir):
        if not filename.lower().endswith(".pdf"):
            continue
        path = os.path.join(data_dir, filename)
        reader = PdfReader(path)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                documents.append({
                    "text": text.strip(),
                    "source": filename,
                    "page": page_num + 1,
                })
    return documents


def chunk_documents(documents: list[dict], chunk_size: int, overlap: int) -> list[dict]:
    """Split documents into overlapping chunks."""
    chunks = []
    for doc in documents:
        text = doc["text"]
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append({
                "text": chunk_text,
                "source": doc["source"],
                "page": doc["page"],
            })
            start += chunk_size - overlap
    return chunks


def build_index():
    print("Loading PDFs...")
    documents = load_pdfs(DATA_DIR)
    if not documents:
        print(f"No PDFs found in {DATA_DIR}. Add your Kia car data PDFs there.")
        return

    print(f"Loaded {len(documents)} pages. Chunking...")
    chunks = chunk_documents(documents, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"Created {len(chunks)} chunks. Embedding...")

    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype(np.float32)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
    faiss.write_index(index, os.path.join(FAISS_INDEX_PATH, "index.faiss"))
    with open(os.path.join(FAISS_INDEX_PATH, "chunks.pkl"), "wb") as f:
        pickle.dump(chunks, f)

    print(f"Index saved to {FAISS_INDEX_PATH} ({len(chunks)} chunks, dim={dimension})")


if __name__ == "__main__":
    build_index()
