"""Tests for lyra-resilience."""
import pytest
from lyra_resilience import CircuitBreaker, RecoveryLadder


@pytest.mark.asyncio
async def test_circuit_breaker_closed():
    cb = CircuitBreaker("test", threshold=3)
    result = await cb.call(lambda: "ok")
    assert result == "ok"


class TestRecoveryLadder:
    @pytest.mark.asyncio
    async def test_recovery_steps(self):
        ladder = RecoveryLadder()
        result = await ladder.recover(Exception("test"), {})
        assert result.step == "rule_patch"
        assert result.success
