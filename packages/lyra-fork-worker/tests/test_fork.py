"""Tests for Fork Worker package."""

import pytest
from lyra_fork_worker import ForkWorkerOrchestrator, PatchApplier


class TestPatchApplier:
    def test_apply(self):
        a = PatchApplier()
        result = a.apply("/tmp/test_repo", "patch content")
        assert result


class TestForkWorkerOrchestrator:
    @pytest.mark.skip(reason="Requires filesystem access")
    def test_spawn_worker(self):
        pass

    @pytest.mark.skip(reason="Requires filesystem access")
    def test_test_patch(self):
        pass

    def test_init(self):
        o = ForkWorkerOrchestrator()
        assert o.max_workers == 4
