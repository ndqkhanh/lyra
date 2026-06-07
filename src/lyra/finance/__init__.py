"""
Lyra Finance Agent — Multi-Layer Trading, Analysis & Portfolio Management.

5-Layer Architecture:
  Layer 1 — Financial Foundation Models (models.py)
  Layer 2 — Multi-Agent Trading System (analysts.py, trading.py)
  Layer 3 — Financial Analysis Pipeline (valuation.py)
  Layer 4 — Risk Management (risk.py)
  Layer 5 — Portfolio Optimization (portfolio.py)

Design principles:
  - Deterministic math, AI reasoning (LLMs do not calculate)
  - Structural constraints over LLM instructions for enforcement
  - Multi-agent adversarial debate over single-agent predictions
  - Frozen dataclasses, full type annotations, production-quality
"""

from lyra.finance.analysts import (
    FinancialStatement,
    FundamentalAnalyst,
    NewsAnalyst,
    SentimentAnalyst,
    TechnicalAnalyst,
)
from lyra.finance.models import (
    AnalystReport,
    AnalystType,
    Asset,
    AssetClass,
    CircuitBreakerEvent,
    MarketData,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PerformanceSnapshot,
    Portfolio,
    Position,
    RiskMetrics,
    RiskProfile,
    SentimentSignal,
    SignalSource,
    Trade,
    TradeDirection,
    TradingDecision,
    ValuationResult,
)
from lyra.finance.portfolio import (
    AllocationMethod,
    AllocationResult,
    AllocationStrategy,
    PortfolioOptimizer,
    SharpeSnapshot,
    SharpeTracker,
)
from lyra.finance.risk import (
    BreakerConfig,
    CircuitBreaker,
    ComplianceMonitor,
    ComplianceRule,
    RiskLimits,
    RiskManager,
)
from lyra.finance.trading import (
    BullBearDebate,
    DebateRound,
    PortfolioConfig,
    PortfolioManager,
    TradingAgent,
)
from lyra.finance.valuation import (
    DCFAssumptions,
    DCFValuation,
    EVEbitdaAssumptions,
    EVEbitdaValuation,
    HybridAssumptions,
    HybridValuation,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Layer 1 — Models
    "Asset",
    "AssetClass",
    "MarketData",
    "Position",
    "Portfolio",
    "Order",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "Trade",
    "TradeDirection",
    "RiskProfile",
    "AnalystType",
    "AnalystReport",
    "SentimentSignal",
    "SignalSource",
    "TradingDecision",
    "RiskMetrics",
    "CircuitBreakerEvent",
    "ValuationResult",
    "PerformanceSnapshot",
    # Layer 2 — Analysts
    "FundamentalAnalyst",
    "SentimentAnalyst",
    "TechnicalAnalyst",
    "NewsAnalyst",
    "FinancialStatement",
    # Layer 2 — Trading
    "BullBearDebate",
    "DebateRound",
    "TradingAgent",
    "PortfolioManager",
    "PortfolioConfig",
    # Layer 3 — Valuation
    "DCFValuation",
    "DCFAssumptions",
    "EVEbitdaValuation",
    "EVEbitdaAssumptions",
    "HybridValuation",
    "HybridAssumptions",
    # Layer 4 — Risk
    "RiskManager",
    "RiskLimits",
    "CircuitBreaker",
    "BreakerConfig",
    "ComplianceMonitor",
    "ComplianceRule",
    # Layer 5 — Portfolio
    "PortfolioOptimizer",
    "AllocationStrategy",
    "AllocationMethod",
    "AllocationResult",
    "SharpeTracker",
    "SharpeSnapshot",
]
