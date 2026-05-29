"""Tests for Auto-Fanout Context Compression (Plan 33.1.1)."""

import asyncio

import pytest
from lyra_core.auto_fanout import AutoFanoutCompressor, FanoutResult, _count_tokens


class TestAutoFanoutCompressor:
    async def _fake_summarize(self, chunk: str, idx: int) -> str:
        return f"[Summary of chunk {idx}]: {chunk[:50]}..."

    @pytest.mark.asyncio
    async def test_no_compression_below_threshold(self):
        comp = AutoFanoutCompressor()
        output = "Short output"
        result = await comp.compress(
            output, context_window=10000, subagent_summarize=self._fake_summarize
        )

        assert not result.was_compressed
        assert result.compressed_text == output

    @pytest.mark.asyncio
    async def test_compresses_large_output(self):
        comp = AutoFanoutCompressor(chunk_tokens=100)
        large_output = "\n\n".join([f"Paragraph {i}. " * 30 for i in range(10)])

        result = await comp.compress(
            large_output, context_window=1000, subagent_summarize=self._fake_summarize
        )

        assert result.was_compressed
        assert result.chunks_processed > 1
        assert result.compressed_tokens < result.original_tokens

    @pytest.mark.asyncio
    async def test_single_chunk_no_compression(self):
        comp = AutoFanoutCompressor(chunk_tokens=5000)
        output = "One paragraph.\n\nAnother paragraph."

        result = await comp.compress(
            output, context_window=1000, subagent_summarize=self._fake_summarize
        )

        assert not result.was_compressed

    def test_savings_pct_calculation(self):
        r = FanoutResult(
            compressed_text="short",
            original_tokens=1000,
            compressed_tokens=300,
            chunks_processed=5,
            was_compressed=True,
        )
        assert r.savings_pct == 70.0

    def test_zero_tokens_savings_pct(self):
        r = FanoutResult(
            compressed_text="",
            original_tokens=0,
            compressed_tokens=0,
            chunks_processed=0,
            was_compressed=False,
        )
        assert r.savings_pct == 0.0

    def test_code_blocks_preserved(self):
        comp = AutoFanoutCompressor(chunk_tokens=100)
        text = "Para 1.\n\n```python\nprint('hello world')\n```\n\nPara 2.\n\nPara 3."

        chunks = comp._split_at_boundaries(text)
        full = "\n\n".join(chunks)
        assert "```python" in full
        assert "print('hello world')" in full

    def test_overlap_added_between_chunks(self):
        comp = AutoFanoutCompressor(overlap_tokens=3)
        chunks = ["one two three four", "five six seven eight"]
        result = comp._add_overlap(chunks)
        assert len(result) == 2
        assert "four" in result[1]

    def test_merge_summaries_single(self):
        assert "hello" in AutoFanoutCompressor._merge_summaries(["hello"])

    def test_merge_summaries_multiple(self):
        merged = AutoFanoutCompressor._merge_summaries(["A", "B", "C"])
        assert "[Chunk 1/3]" in merged
        assert "[Chunk 3/3]" in merged

    @pytest.mark.asyncio
    async def test_fanout_semaphore_limits_concurrency(self):
        comp = AutoFanoutCompressor(max_fanout=2, chunk_tokens=50)
        large_output = "\n\n".join([f"Paragraph {i}. " * 30 for i in range(10)])
        running = 0
        max_running = 0

        async def tracking_summarize(_chunk: str, idx: int) -> str:
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            await asyncio.sleep(0.01)
            running -= 1
            return f"[Summary {idx}]"

        await comp.compress(large_output, context_window=500, subagent_summarize=tracking_summarize)
        assert max_running <= 2

    @pytest.mark.asyncio
    async def test_compression_returns_fanout_result_type(self):
        comp = AutoFanoutCompressor(chunk_tokens=50)
        large_output = "\n\n".join([f"Para {i}. " * 30 for i in range(10)])

        result = await comp.compress(
            large_output, context_window=500, subagent_summarize=self._fake_summarize
        )
        assert isinstance(result, FanoutResult)
        assert result.original_tokens > 0


def test_count_tokens():
    assert _count_tokens("") == 1
    assert _count_tokens("hello world") == 2
    assert _count_tokens("a" * 40) == 10
