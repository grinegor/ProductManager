from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from pm_agent.config import Settings
from pm_agent.rag import RAGStore, batched, chunk_text, load_documents


class FakeEmbeddingClient:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            t = text.lower()
            vectors.append(
                [
                    float(t.count("growth") + 1),
                    float(t.count("retention") + 1),
                    float((len(text) % 10) + 1),
                ]
            )
        return vectors


class RagHelpersTests(unittest.TestCase):
    def test_chunk_text_handles_overlap_larger_than_chunk(self) -> None:
        text = " ".join([f"w{i}" for i in range(20)])
        chunks = chunk_text(text, chunk_words=8, overlap_words=20)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(len(c.split()) <= 8 for c in chunks))

    def test_batched(self) -> None:
        items = ["a", "b", "c", "d", "e"]
        out = list(batched(items, 2))
        self.assertEqual(out, [["a", "b"], ["c", "d"], ["e"]])

    def test_load_documents_filters_extensions_and_empty_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "ok.md").write_text("hello", encoding="utf-8")
            (root / "ok.txt").write_text("world", encoding="utf-8")
            (root / "skip.json").write_text("{}", encoding="utf-8")
            (root / "empty.md").write_text("   ", encoding="utf-8")

            docs = load_documents(root)
            sources = sorted([Path(s).name for s, _ in docs])
            self.assertEqual(sources, ["ok.md", "ok.txt"])


class RagStoreTests(unittest.TestCase):
    def test_build_and_retrieve(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs = root / "docs"
            data = root / "data"
            docs.mkdir(parents=True, exist_ok=True)
            data.mkdir(parents=True, exist_ok=True)

            (docs / "growth.md").write_text("growth funnel optimization growth", encoding="utf-8")
            (docs / "retention.md").write_text("retention churn retention", encoding="utf-8")

            settings = Settings(
                openai_api_key="test-key",
                openai_model="test-model",
                fallback_openai_model="",
                openai_reasoning_effort="high",
                embedding_model="test-embed",
                docs_dir=docs,
                data_dir=data,
                top_k=2,
                max_history_messages=8,
            )

            store = RAGStore(settings=settings, llm_client=FakeEmbeddingClient())
            stats = store.build_from_docs(chunk_words=20, overlap_words=5)
            self.assertEqual(stats["documents"], 2)
            self.assertEqual(stats["chunks"], 2)
            self.assertTrue(store.has_index())

            hits = store.retrieve("growth", top_k=2)
            self.assertGreaterEqual(len(hits), 1)
            self.assertTrue(any("growth" in hit.text.lower() for hit in hits))


if __name__ == "__main__":
    unittest.main()
