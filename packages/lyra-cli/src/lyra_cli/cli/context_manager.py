"""Context Window Manager — Phase D (MemGPT/Wang et al. 2023 inspired).

Sliding window with rolling LLM-generated summary.
Keeps last N verbatim turns + a compressed summary of older turns.
O(1) context growth regardless of session length.

Evidence:
- MemGPT (arXiv:2310.08560): recursive summary keeps O(1) context overhead
- Wang et al. 2023 (Neurocomputing 2025): rolling summaries maintain consistency
- Production: 60-80% history token reduction, continuity preserved
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class ContextBudget:
    """Token budget configuration for the context window."""
    max_history_tokens: int = 8_000
    verbatim_turns: int = 4
    compression_trigger: float = 0.75


class ContextManager:
    """Manages conversation history to prevent context bloat.

    Architecture:
    - _verbatim: last N turns kept verbatim (always recent, always accurate)
    - _summary: LLM-generated prose summary of older turns (compact, searchable)
    - Compression fires when verbatim buffer exceeds compression_trigger * budget
    """

    def __init__(
        self,
        budget: ContextBudget,
        summarizer: Callable[[list[dict], str], Awaitable[str]],
    ) -> None:
        self._budget = budget
        self._summarizer = summarizer
        self._summary: str = ""
        self._verbatim: list[dict] = []
        self._total_turns: int = 0
        self._compressions: int = 0

    def add_messages(self, user_msg: str, assistant_msg: str) -> None:
        """Record a completed turn. Call after the assistant response finishes."""
        self._verbatim.append({"role": "user", "content": user_msg})
        self._verbatim.append({"role": "assistant", "content": assistant_msg})
        self._total_turns += 1

    async def maybe_compress(self) -> bool:
        """Compress history if over budget threshold. Returns True if ran."""
        if not self._should_compress():
            return False
        await self._compress()
        return True

    def build_messages(self, system: str = "") -> list[dict]:
        """Build the full message list to send to the provider.

        Order: system prompt → summary block (if any) → verbatim recent turns.
        The summary block uses role=system so Anthropic extracts it correctly.
        """
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        if self._summary:
            summarized_turns = self._total_turns - len(self._verbatim) // 2
            block = (
                f"[Summary of {summarized_turns} earlier turns in this session]\n"
                f"{self._summary}"
            )
            msgs.append({"role": "system", "content": block})
        msgs.extend(self._verbatim)
        return msgs

    def stats(self) -> dict:
        verbatim_turns = len(self._verbatim) // 2
        verbatim_tokens = sum(len(m["content"]) for m in self._verbatim) // 4
        summary_tokens = len(self._summary) // 4
        return {
            "total_turns": self._total_turns,
            "verbatim_turns": verbatim_turns,
            "summarized_turns": self._total_turns - verbatim_turns,
            "verbatim_tokens_est": verbatim_tokens,
            "summary_tokens_est": summary_tokens,
            "total_history_tokens_est": verbatim_tokens + summary_tokens,
            "compressions": self._compressions,
        }

    def clear(self) -> None:
        self._summary = ""
        self._verbatim.clear()
        self._total_turns = 0
        self._compressions = 0

    # ── Private ────────────────────────────────────────────────────────

    def _estimate_tokens(self) -> int:
        return sum(len(m["content"]) for m in self._verbatim) // 4

    def _should_compress(self) -> bool:
        threshold = int(self._budget.max_history_tokens * self._budget.compression_trigger)
        return self._estimate_tokens() > threshold

    async def _compress(self) -> None:
        keep_count = self._budget.verbatim_turns * 2  # N user+assistant pairs
        if len(self._verbatim) <= keep_count:
            return
        to_summarize = self._verbatim[:-keep_count]
        self._verbatim = self._verbatim[-keep_count:]
        self._summary = await self._summarizer(to_summarize, self._summary)
        self._compressions += 1
