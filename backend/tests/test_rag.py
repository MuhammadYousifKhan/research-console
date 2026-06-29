"""Tests for the RAG retrieval service.

A deterministic stub embedding function is injected so the tests never download
the ONNX model or touch the network — embeddings are a tiny keyword-count vector,
which is enough to make the relevant chunk rank first.
"""

import pytest
from chromadb.api.types import EmbeddingFunction

from app.schemas.research import Observation, Source
from app.services.rag import RAGError, RAGRetriever, TextChunker


class StubEmbeddingFunction(EmbeddingFunction):
    """Embeds text as keyword-presence counts over a fixed vocabulary."""

    VOCAB = ["solar", "wind", "battery", "nuclear", "cost"]

    def __call__(self, input):  # noqa: A002 - chromadb's parameter name is `input`
        vectors = []
        for document in input:
            lowered = document.lower()
            # Trailing constant keeps vectors non-zero so cosine distance is defined.
            vectors.append([float(lowered.count(word)) for word in self.VOCAB] + [0.1])
        return vectors

    def name(self) -> str:
        return "stub"


# -- TextChunker ------------------------------------------------------------


def test_chunker_splits_with_overlap():
    chunker = TextChunker(chunk_size=20, chunk_overlap=8)
    text = " ".join(f"word{i}" for i in range(40))
    chunks = chunker.chunk(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= 20 for chunk in chunks)
    # Consecutive chunks share at least one word (overlap preserved).
    first_words = set(chunks[0].split())
    second_words = set(chunks[1].split())
    assert first_words & second_words


def test_chunker_handles_empty_and_blank():
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    assert chunker.chunk("") == []
    assert chunker.chunk("   ") == []


# -- RAGRetriever -----------------------------------------------------------


def _observations() -> tuple[list[Observation], list[Source]]:
    sources = [
        Source(citation_id=1, title="Solar power", url="https://example.com/solar", snippet="solar"),
        Source(citation_id=2, title="Nuclear power", url="https://example.com/nuclear", snippet="nuclear"),
    ]
    observations = [
        Observation(
            task_id=1,
            task="solar",
            tool="search_web",
            result="Solar panels keep dropping in cost and pair well with battery storage.",
            sources=[sources[0]],
        ),
        Observation(
            task_id=2,
            task="nuclear",
            tool="search_web",
            result="Nuclear reactors provide steady baseload but have high upfront cost.",
            sources=[sources[1]],
        ),
    ]
    return observations, sources


def test_retrieve_ranks_relevant_chunk_first_and_keeps_citation():
    observations, sources = _observations()
    retriever = RAGRetriever(top_k=2, embedding_function=StubEmbeddingFunction())

    chunks = retriever.build_and_retrieve("solar battery", observations, sources)

    assert chunks
    # The solar/battery chunk should rank ahead of the nuclear one.
    assert "solar" in chunks[0].text.lower()
    assert 1 in chunks[0].citation_ids


def test_format_evidence_prefixes_citation_tags():
    observations, sources = _observations()
    retriever = RAGRetriever(top_k=4, embedding_function=StubEmbeddingFunction())

    chunks = retriever.build_and_retrieve("nuclear cost", observations, sources)
    evidence = RAGRetriever.format_evidence(chunks)

    assert "[" in evidence and "]" in evidence
    assert "nuclear" in evidence.lower()


def test_empty_evidence_raises_rag_error():
    retriever = RAGRetriever(embedding_function=StubEmbeddingFunction())
    with pytest.raises(RAGError):
        retriever.build_and_retrieve("anything", [], [])
