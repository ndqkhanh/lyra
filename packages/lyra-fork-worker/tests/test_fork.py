"""Tests for Fork Worker package."""

import pytest
from lyra_fork_worker import ForkWorkerOrchestrator, PatchApplier, TestRunner, PatchResult


class TestPatchApplier:
    def test_apply(self):
        a = PatchApplier()
        result = a.apply("/tmp/test_repo", "patch content")
        assert result == True


class TestTestRunner:
    @pytest.mark.asyncio
    async def test_run_tests(self):
        r = TestRunner()
        results = await r.run_tests("/tmp/test_repo")
        assert results["total"] == 946
        assert results["passed"] > 0


class TestForkWorkerOrchestrator:
    @pytest.mark.asyncio
    async def test_spawn_worker(self):
        o = ForkWorkerOrchestrator(max_workers=2)
        w = await o.spawn_worker("/tmp/repo")
        assert w.worker_id == "w1"

    @pytest.mark.asyncio
    async def test_test_patch(self):
        o = ForkWorkerOrchestrator()
        r = await o.test_patch("patch content", "/tmp/repo")
        assert isinstance(r, PatchResult)
