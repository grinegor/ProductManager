from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import faiss
import numpy as np

from .config import Settings
from .llm import OpenAIClient


@dataclass
class RetrievedChunk:
    chunk_id: int
    source: str
    text: str
    score: float


def load_documents(docs_dir: Path) -> list[tuple[str, str]]:
    documents: list[tuple[str, str]] = []
    if not docs_dir.exists():
        return documents

    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        documents.append((str(path), text))
    return documents


def chunk_text(text: str, chunk_words: int = 700, overlap_words: int = 120) -> list[str]:
    words = text.split()
    if not words:
        return []

    if overlap_words >= chunk_words:
        overlap_words = max(0, chunk_words // 4)

    step = max(1, chunk_words - overlap_words)
    chunks: list[str] = []

    for start in range(0, len(words), step):
        end = start + chunk_words
        slice_words = words[start:end]
        if not slice_words:
            continue
        chunks.append(" ".join(slice_words))
        if end >= len(words):
            break

    return chunks


def batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


class RAGStore:
    def __init__(self, settings: Settings, llm_client: OpenAIClient) -> None:
        self.settings = settings
        self.llm_client = llm_client
        self.index: faiss.Index | None = None
        self.chunks: list[dict] = []
        self.load()

    def has_index(self) -> bool:
        return self.index is not None and bool(self.chunks)

    def load(self) -> None:
        index_path = self.settings.faiss_index_path
        chunks_path = self.settings.chunk_store_path

        if not index_path.exists() or not chunks_path.exists():
            self.index = None
            self.chunks = []
            return

        self.index = faiss.read_index(str(index_path))
        self.chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    def build_from_docs(
        self,
        docs_dir: Path | None = None,
        chunk_words: int = 700,
        overlap_words: int = 120,
    ) -> dict[str, int]:
        docs_dir = docs_dir or self.settings.docs_dir
        documents = load_documents(docs_dir)

        chunk_records: list[dict] = []
        for source, content in documents:
            for chunk in chunk_text(content, chunk_words=chunk_words, overlap_words=overlap_words):
                chunk_records.append(
                    {
                        "source": source,
                        "text": chunk,
                    }
                )

        if not chunk_records:
            self.index = None
            self.chunks = []
            return {"documents": len(documents), "chunks": 0}

        texts = [record["text"] for record in chunk_records]

        embeddings: list[list[float]] = []
        for chunk_batch in batched(texts, batch_size=64):
            batch_embeddings = self.llm_client.embed_texts(chunk_batch)
            embeddings.extend(batch_embeddings)

        vectors = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(vectors)

        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)

        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.settings.faiss_index_path))
        self.settings.chunk_store_path.write_text(
            json.dumps(chunk_records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.index = index
        self.chunks = chunk_records

        return {"documents": len(documents), "chunks": len(chunk_records)}

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if not query.strip() or self.index is None or not self.chunks:
            return []

        top_k = top_k or self.settings.top_k

        query_vec = np.array(self.llm_client.embed_texts([query]), dtype="float32")
        faiss.normalize_L2(query_vec)

        scores, ids = self.index.search(query_vec, top_k)

        retrieved: list[RetrievedChunk] = []
        for rank, chunk_id in enumerate(ids[0]):
            if chunk_id < 0 or chunk_id >= len(self.chunks):
                continue
            chunk = self.chunks[chunk_id]
            retrieved.append(
                RetrievedChunk(
                    chunk_id=int(chunk_id),
                    source=str(chunk.get("source", "unknown")),
                    text=str(chunk.get("text", "")),
                    score=float(scores[0][rank]),
                )
            )

        return retrieved
