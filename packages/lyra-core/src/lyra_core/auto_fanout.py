"""Auto-Fanout Context Compression (Plan 33.1.1 / CheetahClaws).

When tool output exceeds 40% of context window, split at paragraph boundaries,
dispatch parallel sub-agent summaries (bounded semaphore), and merge.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass


@dataclass
class FanoutResult:
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    chunks_processed: int
    was_compressed: bool

    @property
    def savings_pct(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return (1 - self.compressed_tokens / self.original_tokens) * 100


class AutoFanoutCompressor:
    """Split large tool outputs, summarize in parallel, merge results.

    When `count_tokens(output) > 0.4 * context_window`:
    1. Split at paragraph boundaries respecting code blocks
    2. Dispatch N parallel sub-agent summarization calls (capped by max_fanout)
    3. Merge summaries into single compressed output
    """

    _CODE_BLOCK_RE: re.Pattern = re.compile(r"```[\s\S]*?```", re.MULTILINE)

    def __init__(
        self, max_fanout: int = 5, chunk_tokens: int = 3000, overlap_tokens: int = 200
    ) -> None:
        self.max_fanout = max_fanout
        self.chunk_tokens = chunk_tokens
        self.overlap = overlap_tokens

    async def compress(
        self,
        output: str,
        context_window: int,
        subagent_summarize,  # async callable(str, int) -> str
    ) -> FanoutResult:
        original_tokens = _count_tokens(output)
        threshold = int(0.4 * context_window)

        if original_tokens <= threshold:
            return FanoutResult(
                compressed_text=output,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                chunks_processed=0,
                was_compressed=False,
            )

        chunks = self._split_at_boundaries(output)
        if len(chunks) <= 1:
            return FanoutResult(
                compressed_text=output,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                chunks_processed=1,
                was_compressed=False,
            )

        chunks = self._add_overlap(chunks)

        sem = asyncio.Semaphore(self.max_fanout)

        async def _summarize_one(chunk: str, idx: int) -> str:
            async with sem:
                return await subagent_summarize(chunk, idx)

        summaries = await asyncio.gather(*[_summarize_one(c, i) for i, c in enumerate(chunks)])
        merged = self._merge_summaries(summaries)
        compressed_tokens = _count_tokens(merged)

        return FanoutResult(
            compressed_text=merged,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            chunks_processed=len(chunks),
            was_compressed=True,
        )

    def _split_at_boundaries(self, text: str) -> list[str]:
        """Split at paragraph boundaries, preserving code blocks."""
        placeholders: dict[str, str] = {}
        placeholder_idx = 0

        def _protect(m: re.Match) -> str:
            nonlocal placeholder_idx
            key = f"__CODE_BLOCK_{placeholder_idx}__"
            placeholders[key] = m.group(0)
            placeholder_idx += 1
            return key

        protected = self._CODE_BLOCK_RE.sub(_protect, text)

        blocks = re.split(r"\n\n(?=[^\n])", protected)
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for block in blocks:
            block_tokens = _count_tokens(block)
            if current_tokens + block_tokens > self.chunk_tokens and current:
                chunks.append("\n\n".join(current))
                current = [block]
                current_tokens = block_tokens
            else:
                current.append(block)
                current_tokens += block_tokens

        if current:
            chunks.append("\n\n".join(current))

        for key, code in placeholders.items():
            chunks = [c.replace(key, code) for c in chunks]

        return chunks

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        if len(chunks) <= 1:
            return chunks
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_words = chunks[i - 1].split()[-self.overlap :]
            if prev_words:
                result.append(" ".join(prev_words) + "\n\n" + chunks[i])
            else:
                result.append(chunks[i])
        return result

    @staticmethod
    def _merge_summaries(summaries: list[str]) -> str:
        """Merge summaries, deduplicating overlapping content."""
        if len(summaries) == 1:
            return summaries[0]
        return "\n\n---\n\n".join(
            f"[Chunk {i + 1}/{len(summaries)}]\n{s}" for i, s in enumerate(summaries)
        )


def _count_tokens(text: str) -> int:
    """Simple token estimator: ~4 chars = 1 token."""
    return max(1, len(text) // 4)
