"""Tests for lyra-finance."""
from lyra_finance import FinanceAgent

class TestFinanceAgent:
    def test_buy(self):
        f = FinanceAgent()
        assert f.buy("AAPL", 10, 150.0)
        assert "AAPL" in f.portfolio.holdings

    def test_insufficient_funds(self):
        f = FinanceAgent()
        assert not f.buy("TSLA", 1000, 500.0)
