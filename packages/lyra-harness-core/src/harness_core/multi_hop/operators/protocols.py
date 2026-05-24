"""LLMTextGenerator + Retriever Protocols + deterministic stubs.

Both operators (Self-Ask, IRCoT) accept a caller-injected LLM + Retriever via
these Protocols. Production wires :class:`harness_core.models.LLMProvider`
through a thin adapter; tests use the stubs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol


@dataclass(frozen=True)
class RetrievedDoc:
    """Minimal retrieved-document shape consumed by operators."""

    doc_id: str
    text: str
    score: float = 0.0
    source: str = ""


class LLMTextGenerator(Protocol):
    """Minimal text-generation Protocol.

    Production wires :class:`harness_core.models.LLMProvider`.complete or any
    provider that takes a prompt + returns a string. Stubs match this shape.
    """

    name: str

    def generate(self, prompt: str, *, max_tokens: int = 512, stop: Optional[list[str]] = None) -> str: ...


class Retriever(Protocol):
    """Minimal retrieval Protocol.

    Returns up to ``top_k`` :class:`RetrievedDoc`s for a query. Production
    wires :class:`HippoRAGRetriever`, BM25, vector, or MCP retrievers.
    """

    name: str

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievedDoc]: ...


# --- Deterministic stubs for tests ---------------------------------------


@dataclass
class StubLLM:
    """Scripted LLM: returns the next response from a queue per call.

    Use for testing operator control flow without a real LM. Each ``generate``
    call pops the next response from ``responses``; runs out → raises.
    """

    responses: list[str] = field(default_factory=list)
    name: str = "stub-llm-v1"
    _call_count: int = 0

    def generate(self, prompt: str, *, max_tokens: int = 512, stop: Optional[list[str]] = None) -> str:
        if self._call_count >= len(self.responses):
            raise RuntimeError(
                f"StubLLM exhausted: {self._call_count} calls made, only "
                f"{len(self.responses)} responses scripted"
            )
        out = self.responses[self._call_count]
        self._call_count += 1
        return out

    @property
    def call_count(self) -> int:
        return self._call_count


@dataclass
class StubRetriever:
    """Scripted retriever: returns docs by lookup or a fallback callable."""

    fixtures: dict[str, list[RetrievedDoc]] = field(default_factory=dict)
    fallback: Optional[Callable[[str, int], list[RetrievedDoc]]] = None
    name: str = "stub-retriever-v1"
    _calls: list[tuple[str, int]] = field(default_factory=list)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievedDoc]:
        self._calls.append((query, top_k))
        if query in self.fixtures:
            return self.fixtures[query][:top_k]
        if self.fallback is not None:
            return self.fallback(query, top_k)
        return []

    @property
    def calls(self) -> list[tuple[str, int]]:
        return list(self._calls)


__all__ = [
    "LLMTextGenerator",
    "Retriever",
    "RetrievedDoc",
    "StubLLM",
    "StubRetriever",
]
