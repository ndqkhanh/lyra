"""harness_core.multi_hop.operators — externalised-chain primitives.

Per [docs/199-multi-hop-reasoning-techniques-arc.md](../../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md)
Phase 1 (prompted retrieval-reasoning) and [docs/201-compositionality-gap-canon.md]
(../../../../../../../research/harness-engineering/docs/201-compositionality-gap-canon.md)
(why externalising the chain is the architectural fix for the compositionality gap).

Two canonical operators:
    - Self-Ask (Press et al. 2022, arXiv:2210.03350) — explicit follow-up
      sub-questions until the final answer.
    - IRCoT (Trivedi et al. 2023, arXiv:2212.10509) — interleave CoT generation
      with per-sentence retrieval; +21 retrieval / +15 QA points over single-shot.

Both operators are Protocol-typed (LLM, Retriever) so they're testable against
deterministic stubs and swappable in production with any LLM/retriever wire.
"""
from __future__ import annotations

from .ircot import IRCoTOperator, IRCoTResult, IRCoTStep
from .protocols import (
    LLMTextGenerator,
    Retriever,
    RetrievedDoc,
    StubLLM,
    StubRetriever,
)
from .self_ask import (
    SelfAskOperator,
    SelfAskResult,
    SelfAskStep,
    parse_self_ask_response,
)

__all__ = [
    "IRCoTOperator",
    "IRCoTResult",
    "IRCoTStep",
    "LLMTextGenerator",
    "Retriever",
    "RetrievedDoc",
    "SelfAskOperator",
    "SelfAskResult",
    "SelfAskStep",
    "StubLLM",
    "StubRetriever",
    "parse_self_ask_response",
]
