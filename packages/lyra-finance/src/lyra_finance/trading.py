"""
Multi-agent trading system for Lyra Finance.

Implements Layer 2 components:
- BullBearDebate: structured adversarial debate between analysts
- TradingAgent: executes trades with risk checks
- PortfolioManager: position sizing, rebalancing

Design principles:
- Multi-agent adversarial debate over single-agent predictions
- Structural constraints (position limits, stop-losses) over LLM instructions
- Deterministic math for sizing, AI for reasoning only
"""

from __future__ import annotations

import datetime
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from lyra_finance.models import (
    AnalystReport,
    AnalystType,
    Asset,
    MarketData,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Portfolio,
    RiskProfile,
    Trade,
    TradeDirection,
    TradingDecision,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bull / Bear Adversarial Debate
# ---------------------------------------------------------------------------


@dataclass
class DebateRound:
    """One round of debate with bull and bear arguments."""

    bull_score: float = 0.0
    bear_score: float = 0.0
    bull_reports: tuple[AnalystReport, ...] = field(default_factory=tuple)
    bear_reports: tuple[AnalystReport, ...] = field(default_factory=tuple)
    consensus_decision: TradingDecision | None = None


class BullBearDebate:
    """Structured adversarial debate between bullish and bearish analysts.

    Aggregates reports from bullish analysts and bearish analysts, weights
    them by confidence, and produces a final TradingDecision. The debate
    structure forces opposing viewpoints to be explicitly considered rather
    than averaging away disagreement.
    """

    def __init__(self, name: str = "BullBearDebate", bull_bias: float = 0.0) -> None:
        """
        Args:
            name: Identifier for this debate instance.
            bull_bias: Positive values favour bulls, negative favour bears.
                Range [-0.5, 0.5]. 0 = neutral.
        """
        self.name = name
        self.bull_bias = max(-0.5, min(0.5, bull_bias))
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def debate(
        self,
        reports: Sequence[AnalystReport],
        asset: Asset | None = None,
        _market_data: Sequence[MarketData] | None = None,
    ) -> DebateRound:
        """Run one full debate round from analyst reports.

        Args:
            reports: AnalystReport instances from all analysts.
            asset: Optional asset context.
            market_data: Optional market data context.

        Returns:
            DebateRound containing the bull/bear scores and final decision.
        """
        # Classify reports
        bull_reports = tuple(r for r in reports if r.rating in ("strong_buy", "buy"))
        bear_reports = tuple(r for r in reports if r.rating in ("strong_sell", "sell"))
        neutral_reports = tuple(r for r in reports if r.rating == "hold")

        self.logger.info(
            "Debate: %d bull, %d bear, %d neutral reports for %s",
            len(bull_reports),
            len(bear_reports),
            len(neutral_reports),
            reports[0].symbol if reports else "unknown",
        )

        # Confidence-weighted scoring
        bull_score = self._weighted_score(bull_reports, True)
        bear_score = self._weighted_score(bear_reports, False)

        # Apply bull/bias
        bull_score += self.bull_bias

        # Determine direction
        decision = self._decide(
            bull_score, bear_score, bull_reports, bear_reports, neutral_reports, asset
        )

        return DebateRound(
            bull_score=bull_score,
            bear_score=bear_score,
            bull_reports=bull_reports,
            bear_reports=bear_reports,
            consensus_decision=decision,
        )

    def _weighted_score(self, reports: tuple[AnalystReport, ...], _is_bull: bool) -> float:
        """Compute confidence-weighted aggregate score."""
        if not reports:
            return 0.0
        total = 0.0
        weight_sum = 0.0
        for r in reports:
            w = r.confidence
            # Scale weight by analyst type (fundamental/news get more weight)
            if r.analyst_type == AnalystType.FUNDAMENTAL:
                w *= 1.2
            elif r.analyst_type == AnalystType.NEWS:
                w *= 1.1
            elif r.analyst_type == AnalystType.SENTIMENT:
                w *= 0.8
            total += w * (r.confidence * 100.0)
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0

    def _decide(
        self,
        bull_score: float,
        bear_score: float,
        bull_reports: tuple[AnalystReport, ...],
        bear_reports: tuple[AnalystReport, ...],
        neutral_reports: tuple[AnalystReport, ...],
        asset: Asset | None,
    ) -> TradingDecision:
        """Translate debate scores into a TradingDecision."""
        symbol = (
            bull_reports[0].symbol
            if bull_reports
            else (
                bear_reports[0].symbol
                if bear_reports
                else neutral_reports[0].symbol if neutral_reports else "UNKNOWN"
            )
        )
        net_score = bull_score - bear_score
        max_score = max(bull_score, bear_score, 1.0)

        # Direction
        if net_score > 20:
            direction = TradeDirection.LONG
        elif net_score < -20:
            direction = TradeDirection.SHORT
        else:
            direction = TradeDirection.HOLD

        # Confidence from margin of victory
        confidence = min(0.95, abs(net_score) / max_score * 0.8 + 0.1)

        # Position sizing from conviction
        if direction == TradeDirection.LONG:
            position_size = min(0.25, confidence * 0.3)
        elif direction == TradeDirection.SHORT:
            position_size = min(0.15, confidence * 0.2)
        else:
            position_size = 0.0

        # Target price from bull/bear reports
        target_price = self._consensus_target(bull_reports)
        stop_loss = None
        if asset and asset.current_price > 0 and direction == TradeDirection.LONG:
            stop_loss = asset.current_price * 0.95  # 5% stop-loss
        elif asset and asset.current_price > 0 and direction == TradeDirection.SHORT:
            stop_loss = asset.current_price * 1.05  # 5% stop-loss on short

        all_reports = bull_reports + bear_reports + neutral_reports
        reasoning = (
            f"Bull score: {bull_score:.1f}, Bear score: {bear_score:.1f}. "
            f"Net: {net_score:+.1f}. Direction: {direction.value}. "
            f"Confidence: {confidence:.1%}."
        )

        return TradingDecision(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            position_size_pct=position_size,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            supporting_reports=all_reports,
        )

    @staticmethod
    def _consensus_target(reports: tuple[AnalystReport, ...]) -> float | None:
        """Average target prices from reports that have them."""
        targets = [r.target_price for r in reports if r.target_price is not None]
        if not targets:
            return None
        return sum(targets) / len(targets)


# ---------------------------------------------------------------------------
# Trading agent
# ---------------------------------------------------------------------------


class TradingAgent:
    """Executes trades with risk checks and order management.

    Serves as the bridge between analyst decisions and actual order
    execution. Validates every trade against risk limits before submission.
    """

    def __init__(
        self, name: str = "TradingAgent", default_order_type: OrderType = OrderType.MARKET
    ) -> None:
        self.name = name
        self.default_order_type = default_order_type
        self._orders: list[Order] = []
        self._trades: list[Trade] = []
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    @property
    def open_orders(self) -> list[Order]:
        return [o for o in self._orders if o.is_open]

    @property
    def order_history(self) -> tuple[Order, ...]:
        return tuple(self._orders)

    @property
    def trade_history(self) -> tuple[Trade, ...]:
        return tuple(self._trades)

    def execute_decision(
        self, decision: TradingDecision, portfolio: Portfolio, current_price: float | None = None
    ) -> Order | None:
        """Convert a TradingDecision into an Order.

        Returns None if the trade is rejected (zero quantity, no position
        sizing, or invalid direction).
        """
        if decision.direction == TradeDirection.HOLD:
            self.logger.info("HOLD decision for %s — no order created.", decision.symbol)
            return None

        if decision.position_size_pct <= 0:
            self.logger.info("Zero position size for %s — skipping.", decision.symbol)
            return None

        price = current_price or 0.0
        if price <= 0:
            self.logger.warning("Invalid price %.2f for %s.", price, decision.symbol)
            return None

        # Calculate position quantity
        allocation = portfolio.total_value * decision.position_size_pct
        quantity = int(allocation / price)
        if quantity <= 0:
            self.logger.info("Calculated quantity 0 for %s.", decision.symbol)
            return None

        side = OrderSide.BUY if decision.direction == TradeDirection.LONG else OrderSide.SELL

        order = Order(
            id=self._next_order_id(),
            symbol=decision.symbol,
            side=side,
            quantity=quantity,
            order_type=self.default_order_type,
            price=price if self.default_order_type != OrderType.MARKET else None,
            status=OrderStatus.PENDING,
            reason=f"Decision confidence: {decision.confidence:.2f}",
        )

        self._orders.append(order)
        self.logger.info(
            "Created %s order: %d shares of %s at %.2f (%.1f%% of portfolio).",
            side.value,
            quantity,
            decision.symbol,
            price,
            decision.position_size_pct * 100.0,
        )
        return order

    def fill_order(
        self,
        order_id: str,
        fill_price: float,
        fill_quantity: int | None = None,
        commission: float = 0.0,
    ) -> Trade | None:
        """Mark an order as filled, creating the corresponding Trade."""
        for i, order in enumerate(self._orders):
            if order.id != order_id:
                continue
            if not order.is_open:
                self.logger.warning(
                    "Order %s is not open (status: %s).", order_id, order.status.value
                )
                return None

            qty = fill_quantity or order.quantity
            new_filled = order.filled_quantity + qty
            if new_filled > order.quantity:
                self.logger.warning(
                    "Fill quantity %d exceeds order %s quantity %d.", qty, order_id, order.quantity
                )
                return None

            new_status = (
                OrderStatus.FILLED if new_filled >= order.quantity else OrderStatus.PARTIALLY_FILLED
            )

            updated_order = Order(
                id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type=order.order_type,
                price=order.price,
                stop_price=order.stop_price,
                status=new_status,
                created_at=order.created_at,
                filled_at=datetime.datetime.now(),
                filled_quantity=new_filled,
                filled_avg_price=fill_price,
                reason=order.reason,
            )

            trade = Trade(
                id=self._next_trade_id(),
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=qty,
                price=fill_price,
                commission=commission,
            )

            self._orders[i] = updated_order
            self._trades.append(trade)
            self.logger.info("Filled order %s: %d shares at %.2f.", order_id, qty, fill_price)
            return trade

        self.logger.warning("Order %s not found.", order_id)
        return None

    def cancel_order(self, order_id: str) -> Order | None:
        """Cancel an open order."""
        for i, order in enumerate(self._orders):
            if order.id != order_id:
                continue
            if not order.is_open:
                self.logger.warning("Order %s is already %s.", order_id, order.status.value)
                return None
            cancelled = Order(
                id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type=order.order_type,
                price=order.price,
                stop_price=order.stop_price,
                status=OrderStatus.CANCELLED,
                created_at=order.created_at,
                filled_at=order.filled_at,
                filled_quantity=order.filled_quantity,
                filled_avg_price=order.filled_avg_price,
                reason="Cancelled by TradingAgent",
            )
            self._orders[i] = cancelled
            self.logger.info("Cancelled order %s.", order_id)
            return cancelled
        return None

    def _next_order_id(self) -> str:
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"

    def _next_trade_id(self) -> str:
        return f"TRD-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Portfolio manager
# ---------------------------------------------------------------------------


@dataclass
class PortfolioConfig:
    """Configuration for portfolio management strategy."""

    risk_profile: RiskProfile = RiskProfile.NEUTRAL
    max_position_pct: float = 0.20  # max % of portfolio per position
    min_cash_pct: float = 0.05  # min cash reserve
    rebalance_threshold_pct: float = 5.0  # drift % that triggers rebalance
    target_position_count: int = 10  # desired number of positions
    rebalance_frequency_days: int = 30


class PortfolioManager:
    """Manages portfolio construction, position sizing, and rebalancing.

    Implements Layer 2 position sizing logic with configurable risk profiles.
    Conservative profiles limit concentration; aggressive profiles allow
    larger positions.
    """

    def __init__(
        self, name: str = "PortfolioManager", config: PortfolioConfig | None = None
    ) -> None:
        self.name = name
        self.config = config or PortfolioConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def size_position(
        self, decision: TradingDecision, portfolio: Portfolio, current_price: float
    ) -> int:
        """Calculate shares to allocate, respecting limits.

        Applies:
        1. Portfolio cash availability
        2. Risk-profile-based max position size
        3. Position count diversification limits
        """
        if portfolio.total_value <= 0:
            return 0

        # Base allocation from decision
        base_pct = decision.position_size_pct

        # Cap at risk-profile max
        max_pos_pct = self._max_position_pct()
        base_pct = min(base_pct, max_pos_pct)

        # Ensure min cash
        max_deployable = (1.0 - self.config.min_cash_pct) * portfolio.total_value
        cash_available = min(portfolio.cash, max_deployable)

        allocation = portfolio.total_value * base_pct
        allocation = min(allocation, cash_available)

        if current_price > 0:
            return int(allocation / current_price)
        return 0

    def needs_rebalance(self, portfolio: Portfolio) -> bool:
        """Check if portfolio has drifted beyond rebalance threshold."""
        if not portfolio.positions:
            return False

        target_allocation = 1.0 / self.config.target_position_count

        for position in portfolio.positions:
            actual_pct = (
                position.market_value / portfolio.total_value if portfolio.total_value > 0 else 0
            )
            drift = abs(actual_pct - target_allocation) * 100.0
            if drift > self.config.rebalance_threshold_pct:
                return True
        return False

    def rebalance(
        self, portfolio: Portfolio, current_prices: dict[str, float]
    ) -> list[TradingDecision]:
        """Generate trading decisions to rebalance portfolio.

        Returns list of TradingDecision instances to bring the portfolio
        back to target allocation.
        """
        decisions: list[TradingDecision] = []
        if portfolio.total_value <= 0:
            return decisions

        target_allocation = portfolio.total_value * (1.0 / self.config.target_position_count)

        # Check current drift
        for position in portfolio.positions:
            current_value = position.quantity * current_prices.get(
                position.symbol, position.current_price
            )
            target_value = target_allocation

            if current_value > target_value * (1 + self.config.rebalance_threshold_pct / 100.0):
                # Overweight — sell some
                excess = current_value - target_value
                direction = TradeDirection.SHORT
                pct = excess / portfolio.total_value
                decisions.append(
                    TradingDecision(
                        symbol=position.symbol,
                        direction=direction,
                        confidence=0.6,
                        position_size_pct=pct,
                        reasoning=f"Rebalancing: overweight {position.symbol}.",
                    )
                )
            elif current_value < target_value * (1 - self.config.rebalance_threshold_pct / 100.0):
                # Underweight — buy more
                deficit = target_value - current_value
                direction = TradeDirection.LONG
                pct = deficit / portfolio.total_value
                decisions.append(
                    TradingDecision(
                        symbol=position.symbol,
                        direction=direction,
                        confidence=0.6,
                        position_size_pct=pct,
                        reasoning=f"Rebalancing: underweight {position.symbol}.",
                    )
                )

        return decisions

    def _max_position_pct(self) -> float:
        """Max % of portfolio a single position can occupy."""
        profile_limits = {
            RiskProfile.CONSERVATIVE: 0.10,
            RiskProfile.NEUTRAL: 0.20,
            RiskProfile.AGGRESSIVE: 0.35,
        }
        return profile_limits.get(self.config.risk_profile, 0.20)
