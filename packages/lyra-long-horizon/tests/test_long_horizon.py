import asyncio
from lyra_long_horizon import LongHorizonExecutor
class TestLongHorizonExecutor:
    def test_execute(self):
        e = LongHorizonExecutor()
        r = asyncio.run(e.execute(100))
        assert r.steps_completed == 100
        assert len(e.checkpoints) == 10
    def test_replan(self):
        e = LongHorizonExecutor()
        r = asyncio.run(e.execute(50))
        restore = asyncio.run(e.replan(25))
        assert restore >= 10
