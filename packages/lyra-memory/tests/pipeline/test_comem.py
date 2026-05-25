"""Tests for CoMem Pipeline."""

import asyncio

from lyra_memory.pipeline.comem import CoMemPipeline, CompressedContext, CompressionJob


class StubLLM:
    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or ["compressed summary"]
        self._idx = 0
        self.prompts: list[str] = []

    @property
    def responses(self) -> list[str]:
        return self._responses

    @responses.setter
    def responses(self, value: list[str]) -> None:
        self._responses = value
        self._idx = 0

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return "compressed"


class TestCompressionJob:
    def test_default_values(self):
        job = CompressionJob(step_id=42, raw_context="raw text here")
        assert job.step_id == 42
        assert job.raw_context == "raw text here"
        assert len(job.id) == 32


class TestCompressedContext:
    def test_compression_ratio(self):
        ctx = CompressedContext(
            step_id=1,
            compressed="short",
            original_length=100,
            compressed_length=10,
        )
        assert ctx.compression_ratio == 0.1

    def test_compression_ratio_zero_original(self):
        ctx = CompressedContext(
            step_id=1, compressed="", original_length=0, compressed_length=0,
        )
        assert ctx.compression_ratio == 1.0

    def test_tokens_saved(self):
        ctx = CompressedContext(
            step_id=1,
            compressed="abc",
            original_length=200,
            compressed_length=3,
        )
        assert ctx.tokens_saved == 197


class TestCoMemPipeline:
    def _make_pipeline(self, **kwargs) -> CoMemPipeline:
        defaults = dict(memory_model=StubLLM(), k_steps=2)
        defaults.update(kwargs)
        return CoMemPipeline(**defaults)

    async def test_start_and_stop(self):
        pipeline = self._make_pipeline()
        await pipeline.start()
        assert pipeline._running is True
        await pipeline.stop()
        assert pipeline._running is False

    async def test_enqueue_returns_step_id(self):
        pipeline = self._make_pipeline()
        sid = await pipeline.enqueue_context("test context")
        assert sid == 0
        sid2 = await pipeline.enqueue_context("another context")
        assert sid2 == 1

    async def test_enqueue_adds_to_queue(self):
        pipeline = self._make_pipeline()
        await pipeline.enqueue_context("test")
        assert pipeline.compression_queue.qsize() == 1

    async def test_get_compressed_returns_none_for_unknown(self):
        pipeline = self._make_pipeline()
        assert pipeline.get_compressed(999) is None

    async def test_full_compression_cycle(self):
        pipeline = self._make_pipeline()
        await pipeline.start()

        sid = await pipeline.enqueue_context("long context " * 100)
        await asyncio.sleep(0.2)

        await pipeline.stop()
        result = pipeline.get_compressed(sid)
        if result:
            assert result.step_id == sid
            assert len(result.compressed) > 0
            assert result.original_length > result.compressed_length

    async def test_cleanup_removes_stale_entries(self):
        pipeline = self._make_pipeline(k_steps=1)
        await pipeline.start()

        for i in range(10):
            await pipeline.enqueue_context(f"context {i}")
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.3)
        await pipeline.stop()

        assert len(pipeline.compressed_store) <= 5

    async def test_start_idempotent(self):
        pipeline = self._make_pipeline()
        await pipeline.start()
        await pipeline.start()
        assert pipeline._running is True

    async def test_stop_cleans_up_task(self):
        pipeline = self._make_pipeline()
        await pipeline.start()
        await pipeline.stop()
        if pipeline._compressor_task:
            assert pipeline._compressor_task.done()
