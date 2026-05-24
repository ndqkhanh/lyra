"""
Financial data models for Lyra Finance Agent.

Frozen dataclasses representing all core domain entities across the
5-layer finance architecture: market data, orders & trades, analyst
outputs, risk profiles, and portfolio state.
"""

from __future__ import annotations

import datetime
import enum
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AssetClass(enum.Enum):
    """Broad asset classification."""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    FOREX = "forex"
    DERIVATIVE = "derivative"
    CASH = "cash"


class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TradeDirection(enum.Enum):
    LONG = "long"
    SHORT = "short"
    HOLD = "hold"


class RiskProfile(enum.Enum):
    """Aggressiveness of portfolio management."""
    AGGRESSIVE = "aggressive"
    NEUTRAL = "neutral"
    CONSERVATIVE = "conservative"


class AnalystType(enum.Enum):
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    NEWS = "news"


class SignalSource(enum.Enum):
    """Origin of a sentiment signal."""
    NEWS_ARTICLE = "news_article"
    SOCIAL_MEDIA = "social_media"
    EARNINGS_CALL = "earnings_call"
    SEC_FILING = "sec_filing"
    MACRO_DATA = "macro_data"
    ANALYST_RATING = "analyst_rating"
    INSIDER_TRADING = "insider_trading"


# ---------------------------------------------------------------------------
# Market data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Asset:
    """A tradeable financial instrument."""
    symbol: str
    name: str = ""
    asset_class: AssetClass = AssetClass.STOCK
    sector: str = ""
    current_price: float = 0.0
    previous_close: float = 0.0
    market_cap: float = 0.0
    volume: int = 0
    beta: float = 1.0
    dividend_yield: float = 0.0
    pe_ratio: float | None = None
    eps: float | None = None
    fifty_two_week_high: float = 0.0
    fifty_two_week_low: float = 0.0

    @property
    def day_change_pct(self) -> float:
        if self.previous_close > 0:
            return ((self.current_price - self.previous_close) / self.previous_close) * 100.0
        return 0.0

    @property
    def ytd_return_pct(self) -> float:
        """Placeholder: would require Jan 1 price to compute."""
        return 0.0


@dataclass(frozen=True)
class MarketData:
    """OHLCV-style snapshot for a given timestamp."""
    symbol: str
    timestamp: datetime.datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    vwap: float | None = None

    @property
    def range_pct(self) -> float:
        if self.open > 0:
            return ((self.high - self.low) / self.open) * 100.0
        return 0.0


# ---------------------------------------------------------------------------
# Portfolio & order models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Position:
    """A holding in a particular asset."""
    symbol: str
    quantity: int
    average_cost: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.average_cost

    @property
    def unrealized_pl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pl_pct(self) -> float:
        if self.cost_basis > 0:
            return (self.unrealized_pl / self.cost_basis) * 100.0
        return 0.0


@dataclass(frozen=True)
class Portfolio:
    """Complete portfolio snapshot."""
    positions: tuple[Position, ...] = field(default_factory=tuple)
    cash: float = 0.0
    risk_profile: RiskProfile = RiskProfile.NEUTRAL
    last_rebalanced: datetime.datetime | None = None
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0

    @property
    def total_market_value(self) -> float:
        return sum(p.market_value for p in self.positions)

    @property
    def total_value(self) -> float:
        return self.total_market_value + self.cash

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def cash_pct(self) -> float:
        tv = self.total_value
        if tv > 0:
            return (self.cash / tv) * 100.0
        return 100.0

    @property
    def total_pl(self) -> float:
        return self.total_market_value - self.total_deposits + self.total_withdrawals

    def get_position(self, symbol: str) -> Position | None:
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None


@dataclass(frozen=True)
class Order:
    """A request to buy or sell an asset."""
    id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    filled_at: datetime.datetime | None = None
    filled_quantity: int = 0
    filled_avg_price: float | None = None
    reason: str = ""

    @property
    def is_open(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)

    @property
    def notional_value(self) -> float:
        p = self.filled_avg_price if self.filled_avg_price is not None else (self.price or 0.0)
        return self.filled_quantity * p

    @property
    def value_at_submission(self) -> float:
        p = self.price or 0.0
        return self.quantity * p


@dataclass(frozen=True)
class Trade:
    """A completed trade (filled order)."""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float = 0.0
    executed_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    pnl: float = 0.0
    notes: str = ""

    @property
    def notional_value(self) -> float:
        return self.quantity * self.price


# ---------------------------------------------------------------------------
# Analyst output models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SentimentSignal:
    """A sentiment observation for an asset."""
    symbol: str
    score: float  # -1.0 (very bearish) to +1.0 (very bullish)
    source: SignalSource = SignalSource.NEWS_ARTICLE
    confidence: float = 0.5  # 0.0 to 1.0
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    headline: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        if not -1.0 <= self.score <= 1.0:
            raise ValueError(f"Sentiment score must be in [-1, 1], got {self.score}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass(frozen=True)
class AnalystReport:
    """Output produced by any analyst type."""
    analyst_type: AnalystType
    symbol: str
    rating: str  # strong_buy, buy, hold, sell, strong_sell
    target_price: float | None = None
    confidence: float = 0.5
    reasoning: str = ""
    signals: tuple[SentimentSignal, ...] = field(default_factory=tuple)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass(frozen=True)
class TradingDecision:
    """Aggregated decision from the trading pipeline."""
    symbol: str
    direction: TradeDirection
    confidence: float = 0.0
    position_size_pct: float = 0.0  # % of portfolio to allocate
    time_horizon_days: int = 1
    target_price: float | None = None
    stop_loss: float | None = None
    reasoning: str = ""
    supporting_reports: tuple[AnalystReport, ...] = field(default_factory=tuple)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
        if not 0.0 <= self.position_size_pct <= 1.0:
            raise ValueError(f"Position size must be in [0, 1], got {self.position_size_pct}")


# ---------------------------------------------------------------------------
# Risk models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskMetrics:
    """Aggregate risk measurements for a portfolio."""
    var_95: float = 0.0           # 95% Value at Risk (daily)
    var_99: float = 0.0           # 99% Value at Risk (daily)
    cvar_95: float = 0.0          # Conditional VaR (expected shortfall)
    max_drawdown: float = 0.0     # Maximum drawdown %
    volatility: float = 0.0       # Daily volatility (annualized)
    sharpe_ratio: float = 0.0     # Rolling Sharpe
    beta: float = 1.0             # Portfolio beta
    correlation_matrix: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class CircuitBreakerEvent:
    """Record of a circuit breaker trigger."""
    symbol: str
    reason: str
    threshold: float
    current_value: float
    action_taken: str  # "liquidate", "halt_trading", "reduce_position"
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


# ---------------------------------------------------------------------------
# Valuation models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValuationResult:
    """Output from any valuation method."""
    symbol: str
    fair_value: float
    current_price: float
    method: str
    upside_pct: float = 0.0
    confidence: float = 0.5
    assumptions: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "upside_pct",
                           ((self.fair_value - self.current_price) / self.current_price * 100.0)
                           if self.current_price > 0 else 0.0)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


# ---------------------------------------------------------------------------
# Performance tracking
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Periodic portfolio performance record."""
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    total_value: float = 0.0
    daily_return_pct: float = 0.0
    cumulative_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
