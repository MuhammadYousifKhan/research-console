"""Retrieval-augmented generation for the synthesis stage.

Instead of feeding every gathered observation into the synthesis prompt, this
module chunks the evidence, embeds the chunks into a per-run in-memory Chroma
index, and returns only the top-k chunks most relevant to the research query.
Each chunk keeps the citation ids of the sources it came from, so the synthesizer
can still cite with ``[n]`` markers ("citation-aware retrieval").

The index is ephemeral: it is built, queried, and discarded within a single run.
Any failure raises :class:`RAGError`; the pipeline catches it and falls back to
the original full-evidence synthesis, preserving the honest-state principle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from app.core.config import settings
from app.schemas.research import Observation, Source


class RAGError(Exception):
    """Raised when retrieval cannot produce a usable result.

    Carries the real cause so the pipeline can report it on the (failed)
    retrieval step rather than silently degrading.
    """


@dataclass
class RetrievedChunk:
    text: str
    citation_ids: list[int] = field(default_factory=list)


class TextChunker:
    """Splits text into overlapping, word-aligned windows. Pure / dependency-free."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        # Overlap must leave forward progress, otherwise chunking never advances.
        self.chunk_size = chunk_size
        self.chunk_overlap = max(0, min(chunk_overlap, chunk_size - 1))

    def chunk(self, text: str) -> list[str]:
        words = (text or "").split()
        if not words:
            return []

        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for word in words:
            # +1 for the space that will join this word to the previous one.
            addition = len(word) + (1 if current else 0)
            if current and current_len + addition > self.chunk_size:
                chunks.append(" ".join(current))
                # Re-seed the next window with a tail of the current one for overlap.
                current, current_len = self._overlap_tail(current)
                addition = len(word) + (1 if current else 0)
            current.append(word)
            current_len += addition

        if current:
            chunks.append(" ".join(current))
        return chunks

    def _overlap_tail(self, words: list[str]) -> tuple[list[str], int]:
        if self.chunk_overlap == 0:
            return [], 0
        tail: list[str] = []
        length = 0
        for word in reversed(words):
            addition = len(word) + (1 if tail else 0)
            if length + addition > self.chunk_overlap:
                break
            tail.insert(0, word)
            length += addition
        return tail, length


class RAGRetriever:
    """Builds a per-run Chroma index and retrieves the most relevant chunks."""

    def __init__(
        self,
        *,
        top_k: int | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        embedding_function=None,
    ) -> None:
        self.top_k = top_k if top_k is not None else settings.rag_top_k
        self.chunker = TextChunker(
            chunk_size=chunk_size if chunk_size is not None else settings.rag_chunk_size,
            chunk_overlap=chunk_overlap if chunk_overlap is not None else settings.rag_chunk_overlap,
        )
        # Tests inject a deterministic stub so no model download/network is needed.
        self._embedding_function = embedding_function

    def build_and_retrieve(
        self,
        query: str,
        observations: list[Observation],
        sources: list[Source],
    ) -> list[RetrievedChunk]:
        documents, metadatas = self._build_documents(observations, sources)
        if not documents:
            raise RAGError("No evidence available to index for retrieval.")

        try:
            import chromadb
        except ImportError as error:  # pragma: no cover - dependency missing
            raise RAGError(f"chromadb is not installed: {error}") from error

        try:
            client = chromadb.EphemeralClient()
            collection = client.create_collection(
                name=f"run_{uuid4().hex}",
                embedding_function=self._resolve_embedding_function(),
            )
            collection.add(
                ids=[str(index) for index in range(len(documents))],
                documents=documents,
                metadatas=metadatas,
            )
            result = collection.query(
                query_texts=[query],
                n_results=min(self.top_k, len(documents)),
            )
        except Exception as error:  # chromadb raises a variety of internal errors
            raise RAGError(f"Vector retrieval failed: {error}") from error

        return self._parse_result(result)

    @staticmethod
    def format_evidence(chunks: list[RetrievedChunk]) -> str:
        """Render retrieved chunks as a synthesis evidence block, citation tags first."""
        lines = []
        for chunk in chunks:
            tags = "".join(f"[{cid}]" for cid in chunk.citation_ids)
            prefix = f"{tags} " if tags else ""
            lines.append(f"{prefix}{chunk.text}")
        return "\n\n".join(lines)

    # -- internals ----------------------------------------------------------

    def _resolve_embedding_function(self):
        if self._embedding_function is not None:
            return self._embedding_function
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        return DefaultEmbeddingFunction()

    def _build_documents(
        self,
        observations: list[Observation],
        sources: list[Source],
    ) -> tuple[list[str], list[dict]]:
        """Turn evidence into deduplicated (document, metadata) pairs.

        Chunks come from the fuller observation results (tagged with the citation
        ids of that observation's sources) plus each numbered source's snippet, so
        every source is guaranteed to be representable even if its result is thin.
        """
        url_to_citation = {
            source.url: source.citation_id
            for source in sources
            if source.url and source.citation_id is not None
        }

        documents: list[str] = []
        metadatas: list[dict] = []
        seen: set[str] = set()

        def add(text: str, citation_ids: list[int]) -> None:
            normalized = (text or "").strip()
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            documents.append(normalized)
            metadatas.append({"citation_ids": ",".join(str(cid) for cid in citation_ids)})

        for observation in observations:
            citation_ids = sorted(
                {
                    url_to_citation[src.url]
                    for src in observation.sources
                    if src.url in url_to_citation
                }
            )
            for piece in self.chunker.chunk(observation.result):
                add(piece, citation_ids)

        for source in sources:
            if source.citation_id is None:
                continue
            snippet = source.snippet or source.title
            for piece in self.chunker.chunk(f"{source.title}. {snippet}"):
                add(piece, [source.citation_id])

        return documents, metadatas

    @staticmethod
    def _parse_result(result: dict) -> list[RetrievedChunk]:
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        chunks: list[RetrievedChunk] = []
        for index, text in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            raw_ids = (metadata or {}).get("citation_ids", "")
            citation_ids = [int(part) for part in raw_ids.split(",") if part]
            chunks.append(RetrievedChunk(text=text, citation_ids=citation_ids))
        return chunks
