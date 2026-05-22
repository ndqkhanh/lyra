"""Finance Agent — trading analysis, portfolio management, market intelligence."""
from __future__ import annotations
import logging, random, time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["Portfolio", "MarketAsset", "FinanceAgent"]

@dataclass
class MarketAsset:
    symbol: str; price: float = 0.0; change_pct: float = 0.0; volume: int = 0

@dataclass
class Portfolio:
    cash: float = 10000.0; holdings: dict[str, int] = field(default_factory=dict)

class FinanceAgent:
    def __init__(self):
        self.portfolio = Portfolio()
        self.watchlist: list[str] = []
        self.trades: list[dict] = []

    def add_to_watchlist(self, symbol: str) -> None:
        self.watchlist.append(symbol)

    def get_quote(self, symbol: str) -> MarketAsset:
        return MarketAsset(symbol=symbol, price=random.uniform(10, 500), change_pct=random.uniform(-5, 5))

    def buy(self, symbol: str, shares: int, price: float) -> bool:
        cost = shares * price
        if cost > self.portfolio.cash: return False
        self.portfolio.cash -= cost
        self.portfolio.holdings[symbol] = self.portfolio.holdings.get(symbol, 0) + shares
        self.trades.append({"action": "buy", "symbol": symbol, "shares": shares, "price": price, "time": time.time()})
        return True

    def analyze_portfolio(self) -> dict[str, Any]:
        total = self.portfolio.cash + sum(self.get_quote(s).price * q for s, q in self.portfolio.holdings.items())
        return {"cash": self.portfolio.cash, "holdings": len(self.portfolio.holdings), "total_value": total, "trades": len(self.trades)}
