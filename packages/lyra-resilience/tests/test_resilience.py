"""Tests for lyra-resilience."""
import asyncio

from lyra_resilience import CircuitBreaker, RecoveryLadder


def test_circuit_breaker_closed():
    cb = CircuitBreaker("test", threshold=3)
    async def ok_fn(): return "ok"
    result = asyncio.run(cb.call(ok_fn))
    assert result == "ok"


class TestRecoveryLadder:
    def test_recovery_steps(self):
        ladder = RecoveryLadder()
        result = asyncio.run(ladder.recover(Exception("test"), {}))
        assert result.step == "rule_patch"
        assert result.success
