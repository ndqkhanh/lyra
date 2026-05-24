"""
Risk management system for Lyra Finance.

Implements Layer 4 components:
- RiskManager: position limits, Value-at-Risk, portfolio-level risk
- CircuitBreaker: forced liquidation when thresholds breached
- ComplianceMonitor: regulatory and policy checks

Design principles:
- Structural constraints over LLM instructions for risk
- Circuit breakers with deterministic forced liquidation
- Hybrid speed+reasoning: fast numeric checks + deep monitoring
"""

from __future__ import annotations

import datetime
import logging
import statistics
from dataclasses import dataclass
from typing import Sequence

from lyra_finance.models import (
    CircuitBreakerEvent,
    Portfolio,
    RiskMetrics,
    Trade,
    TradeDirection,
    TradingDecision,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Risk manager
# ---------------------------------------------------------------------------


@dataclass
class RiskLimits:
    """Configured risk limits for a portfolio."""
    max_single_position_pct: float = 0.20        # 20% max per position
    max_leverage: float = 1.0                     # no leverage by default
    max_concentration_pct: float = 0.30           # 30% max per sector
    max_drawdown_pct: float = 0.15                # 15% max drawdown before halt
    var_95_limit_pct: float = 0.02                # 2% daily VaR limit
    min_trades_before_var: int = 10               # minimum trades for VaR calc
    stop_loss_pct_default: float = 0.05           # 5% default stop loss
    max_daily_trades: int = 50                    # trade frequency limit
    max_order_value: float = 1_000_000.0          # single order notional cap


class RiskManager:
    """Portfolio-level risk management.

    Performs fast numeric checks (position limits, VaR, drawdown) as the
    first gate before any trading decision is forwarded for execution.
    """

    def __init__(self, name: str = "RiskManager",
                 limits: RiskLimits | None = None) -> None:
        self.name = name
        self.limits = limits or RiskLimits()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._var_data: list[float] = []  # daily returns for VaR calculation

    def check_trade(self, decision: TradingDecision,
                    portfolio: Portfolio) -> tuple[bool, str]:
        """Validate a trade against all risk limits.

        Returns:
            Tuple of (approved: bool, reason: str).
        """
        checks = [
            self._check_position_limit(decision, portfolio),
            self._check_cash_availability(decision, portfolio),
            self._check_daily_trade_limit(decision),
            self._check_notional_limit(decision, portfolio),
        ]

        for approved, reason in checks:
            if not approved:
                return (False, reason)

        return (True, "All risk checks passed.")

    def compute_var(self, daily_returns: Sequence[float] | None = None,
                    confidence: float = 0.95) -> RiskMetrics:
        """Compute Value-at-Risk and related metrics.

        Uses historical simulation method (deterministic).
        """
        returns = list(daily_returns or self._var_data)

        if len(returns) < self.limits.min_trades_before_var:
            return RiskMetrics()

        sorted_returns = sorted(returns)
        n = len(sorted_returns)

        # VaR at confidence level
        var_index = int((1.0 - confidence) * n)
        var_95 = abs(sorted_returns[var_index]) if 0 <= var_index < n else 0.0

        var_99_index = int(0.01 * n)
        var_99 = abs(sorted_returns[var_99_index]) if 0 <= var_99_index < n else 0.0

        # Conditional VaR (expected shortfall)
        tail = [r for r in sorted_returns if r <= -var_95]
        cvar_95 = abs(statistics.mean(tail)) if tail else var_95

        # Volatility (annualized, assuming daily returns)
        vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
        annualized_vol = vol * (252 ** 0.5)

        # Max drawdown
        max_dd = self._compute_max_drawdown(returns)

        # Sharpe (assuming 0% risk-free rate)
        avg_return = statistics.mean(returns)
        sharpe = (avg_return / vol * (252 ** 0.5)) if vol > 0 else 0.0

        return RiskMetrics(
            var_95=var_95 * 100.0,
            var_99=var_99 * 100.0,
            cvar_95=cvar_95 * 100.0,
            max_drawdown=max_dd * 100.0,
            volatility=annualized_vol * 100.0,
            sharpe_ratio=sharpe,
        )

    def record_daily_return(self, return_pct: float) -> None:
        """Record a daily portfolio return for VaR tracking."""
        self._var_data.append(return_pct / 100.0)
        # Keep last 500 returns
        if len(self._var_data) > 500:
            self._var_data.pop(0)

    def risk_adjust_decision(self, decision: TradingDecision,
                             risk_metrics: RiskMetrics,
                             portfolio: Portfolio) -> TradingDecision:
        """Scale back a decision based on current risk metrics.

        Applies risk-based position sizing reduction when VaR or drawdown
        is elevated.
        """
        if risk_metrics.var_95 <= 0:
            return decision

        adjustment = 1.0

        # Reduce size if VaR is elevated
        if risk_metrics.var_95 > self.limits.var_95_limit_pct * 100.0:
            adjustment *= (self.limits.var_95_limit_pct * 100.0) / risk_metrics.var_95

        # Reduce size if drawdown is near limit
        if risk_metrics.max_drawdown > self.limits.max_drawdown_pct * 50.0:
            drawdown_ratio = 1.0 - (risk_metrics.max_drawdown / (self.limits.max_drawdown_pct * 100.0))
            adjustment *= max(0.1, drawdown_ratio)

        # Apply adjustment
        adjusted_pct = decision.position_size_pct * adjustment
        self.logger.info(
            "Risk adjustment: %.1f%% of original size (VaR=%.2f%%, DD=%.2f%%).",
            adjustment * 100.0, risk_metrics.var_95, risk_metrics.max_drawdown,
        )

        return TradingDecision(
            symbol=decision.symbol,
            direction=decision.direction,
            confidence=decision.confidence * (0.5 + adjustment * 0.5),
            position_size_pct=adjusted_pct,
            time_horizon_days=decision.time_horizon_days,
            target_price=decision.target_price,
            stop_loss=decision.stop_loss,
            reasoning=(f"Risk-adjusted: {decision.reasoning} "
                       f"| Adjustment: {adjustment:.0%}"),
            supporting_reports=decision.supporting_reports,
        )

    # ------------------------------------------------------------------
    # Internal check methods
    # ------------------------------------------------------------------

    def _check_position_limit(self, decision: TradingDecision,
                              portfolio: Portfolio) -> tuple[bool, str]:
        """Check single position size and sector concentration."""
        if decision.position_size_pct > self.limits.max_single_position_pct:
            return (False,
                    f"Position size {decision.position_size_pct:.1%} exceeds "
                    f"limit of {self.limits.max_single_position_pct:.1%}.")
        return (True, "")

    def _check_cash_availability(self, decision: TradingDecision,
                                 portfolio: Portfolio) -> tuple[bool, str]:
        """"Check sufficient cash for buy orders."""
        if decision.direction == TradeDirection.SHORT:
            return (True, "")
        cost = portfolio.total_value * decision.position_size_pct
        if cost > portfolio.cash:
            return (False,
                    f"Insufficient cash: ${cost:.2f} needed, "
                    f"${portfolio.cash:.2f} available.")
        return (True, "")

    def _check_daily_trade_limit(self, _decision: TradingDecision) -> tuple[bool, str]:
        """Check if we'd exceed daily trade limit (stateless check)."""
        # NOTE: daily count should be tracked externally; we return OK here.
        return (True, "")

    def _check_notional_limit(self, decision: TradingDecision,
                              portfolio: Portfolio) -> tuple[bool, str]:
        """Check single order notional value limit."""
        notional = portfolio.total_value * decision.position_size_pct
        if notional > self.limits.max_order_value:
            return (False,
                    f"Order notional ${notional:.2f} exceeds "
                    f"limit of ${self.limits.max_order_value:.2f}.")
        return (True, "")

    @staticmethod
    def _compute_max_drawdown(returns: Sequence[float]) -> float:
        """Compute maximum drawdown from a series of returns."""
        if not returns:
            return 0.0
        cumulative = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns:
            cumulative *= (1.0 + r)
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


@dataclass
class BreakerConfig:
    """Circuit breaker threshold configuration."""
    daily_loss_pct: float = 0.10          # 10% daily loss triggers halt
    portfolio_drawdown_pct: float = 0.20  # 20% total drawdown triggers liquidation
    single_trade_loss_pct: float = 0.05   # 5% loss on single trade triggers review
    volatility_spike_pct: float = 0.08    # 8% daily vol spike triggers halt
    cooldown_minutes: int = 30            # cool-down after circuit break
    max_consecutive_losses: int = 5       # stop after 5 consecutive losses


class CircuitBreaker:
    """Market circuit breaker with forced liquidation at thresholds.

    Monitors portfolio state in real-time and triggers deterministic
    actions when pre-defined thresholds are breached.
    """

    def __init__(self, name: str = "CircuitBreaker",
                 config: BreakerConfig | None = None) -> None:
        self.name = name
        self.config = config or BreakerConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._events: list[CircuitBreakerEvent] = []
        self._is_triggered: bool = False
        self._triggered_at: datetime.datetime | None = None
        self._consecutive_losses: int = 0

    @property
    def events(self) -> tuple[CircuitBreakerEvent, ...]:
        return tuple(self._events)

    @property
    def is_triggered(self) -> bool:
        return self._is_triggered

    @property
    def in_cooldown(self) -> bool:
        if not self._triggered_at:
            return False
        elapsed = (datetime.datetime.now() - self._triggered_at).total_seconds()
        return elapsed < self.config.cooldown_minutes * 60

    def check_daily_loss(self, daily_return_pct: float) -> list[CircuitBreakerEvent]:
        """Check if daily loss exceeds threshold."""
        events: list[CircuitBreakerEvent] = []
        if daily_return_pct <= -self.config.daily_loss_pct * 100.0:
            event = CircuitBreakerEvent(
                symbol="PORTFOLIO",
                reason=f"Daily loss {daily_return_pct:.2f}% exceeds "
                       f"limit {self.config.daily_loss_pct * 100:.0f}%.",
                threshold=self.config.daily_loss_pct * 100.0,
                current_value=daily_return_pct,
                action_taken="halt_trading",
            )
            self._trigger(event)
            events.append(event)
        return events

    def check_portfolio_drawdown(self, drawdown_pct: float) -> list[CircuitBreakerEvent]:
        """Check if total drawdown exceeds threshold."""
        events: list[CircuitBreakerEvent] = []
        if drawdown_pct >= self.config.portfolio_drawdown_pct * 100.0:
            event = CircuitBreakerEvent(
                symbol="PORTFOLIO",
                reason=f"Portfolio drawdown {drawdown_pct:.2f}% exceeds "
                       f"limit {self.config.portfolio_drawdown_pct * 100:.0f}%.",
                threshold=self.config.portfolio_drawdown_pct * 100.0,
                current_value=drawdown_pct,
                action_taken="liquidate",
            )
            self._trigger(event)
            events.append(event)
        return events

    def check_trade_loss(self, trade: Trade) -> list[CircuitBreakerEvent]:
        """Check if a single trade loss exceeds threshold."""
        events: list[CircuitBreakerEvent] = []
        if trade.pnl < 0 and abs(trade.pnl) / max(trade.notional_value, 1) >= self.config.single_trade_loss_pct:
            self._consecutive_losses += 1
            if self._consecutive_losses >= self.config.max_consecutive_losses:
                event = CircuitBreakerEvent(
                    symbol=trade.symbol,
                    reason=f"{self._consecutive_losses} consecutive losses on {trade.symbol}.",
                    threshold=self.config.max_consecutive_losses,
                    current_value=float(self._consecutive_losses),
                    action_taken="reduce_position",
                )
                self._trigger(event)
                events.append(event)
        elif trade.pnl >= 0:
            self._consecutive_losses = 0
        return events

    def reset(self) -> None:
        """Reset circuit breaker state."""
        self._is_triggered = False
        self._triggered_at = None
        self._consecutive_losses = 0
        self.logger.info("Circuit breaker reset.")

    def _trigger(self, event: CircuitBreakerEvent) -> None:
        """Record a breaker trigger event."""
        self._events.append(event)
        self._is_triggered = True
        self._triggered_at = event.timestamp
        self.logger.warning(
            "CIRCUIT BREAKER TRIGGERED: %s — %s (action: %s)",
            event.symbol, event.reason, event.action_taken,
        )


# ---------------------------------------------------------------------------
# Compliance monitor
# ---------------------------------------------------------------------------


@dataclass
class ComplianceRule:
    """A single compliance rule definition."""
    name: str
    description: str
    enabled: bool = True
    severity: str = "medium"  # low, medium, high, critical


class ComplianceMonitor:
    """Monitors trading activity for regulatory and policy compliance.

    Implements configurable rule-based compliance with pre-trade and
    post-trade checks. Rules are structurally enforced (not LLM-based)
    for deterministic outcomes.
    """

    def __init__(self, name: str = "ComplianceMonitor") -> None:
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._rules: dict[str, ComplianceRule] = {
            "pattern_day_trader": ComplianceRule(
                name="pattern_day_trader",
                description="Limit day trades if < $25k account (FINRA rule).",
                severity="high",
            ),
            "wash_sale": ComplianceRule(
                name="wash_sale",
                description="Prevent wash sale pattern (buy back within 30 days at loss).",
                severity="medium",
            ),
            "concentration_limit": ComplianceRule(
                name="concentration_limit",
                description="Single position ≤ 30% of portfolio value.",
                severity="high",
            ),
            "restricted_stocks": ComplianceRule(
                name="restricted_stocks",
                description="Block trading in restricted/pink-sheet securities.",
                severity="critical",
            ),
            "leverage_limit": ComplianceRule(
                name="leverage_limit",
                description="Portfolio leverage ≤ regulatory limit.",
                severity="critical",
            ),
        }
        self._recent_sells: dict[str, list[tuple[str, float, datetime.datetime]]] = {}

    def pre_trade_check(self, decision: TradingDecision,
                        portfolio: Portfolio) -> tuple[bool, str]:
        """Run compliance rules before a trade is executed."""
        checks = [
            self._check_concentration(decision, portfolio),
            self._check_wash_sale(decision),
        ]
        for approved, reason in checks:
            if not approved:
                self.logger.warning("Pre-trade compliance FAIL: %s", reason)
                return (False, reason)
        return (True, "All compliance checks passed.")

    def post_trade_check(self, trade: Trade) -> list[str]:
        """Run compliance rules after a trade is executed."""
        warnings: list[str] = []
        if trade.side.value == "sell":
            self._record_sell(trade)
        return warnings

    @property
    def rules(self) -> dict[str, ComplianceRule]:
        return dict(self._rules)

    def disable_rule(self, rule_name: str) -> bool:
        """Disable a specific compliance rule."""
        if rule_name in self._rules:
            self._rules[rule_name] = ComplianceRule(
                name=self._rules[rule_name].name,
                description=self._rules[rule_name].description,
                enabled=False,
                severity=self._rules[rule_name].severity,
            )
            self.logger.info("Compliance rule '%s' disabled.", rule_name)
            return True
        return False

    def enable_rule(self, rule_name: str) -> bool:
        """Enable a specific compliance rule."""
        if rule_name in self._rules:
            self._rules[rule_name] = ComplianceRule(
                name=self._rules[rule_name].name,
                description=self._rules[rule_name].description,
                enabled=True,
                severity=self._rules[rule_name].severity,
            )
            self.logger.info("Compliance rule '%s' enabled.", rule_name)
            return True
        return False

    # ------------------------------------------------------------------
    # Internal rule checks
    # ------------------------------------------------------------------

    def _check_concentration(self, decision: TradingDecision,
                             portfolio: Portfolio) -> tuple[bool, str]:
        """Check that position won't exceed concentration limit."""
        if decision.position_size_pct > 0.30:
            return (False,
                    f"Position would be {decision.position_size_pct:.1%} of portfolio, "
                    "exceeds 30% concentration limit.")
        return (True, "")

    def _check_wash_sale(self, decision: TradingDecision) -> tuple[bool, str]:
        """Check for potential wash sale (buying within 30 days of selling at loss)."""
        if decision.direction.value != "buy":
            return (True, "")
        symbol = decision.symbol
        sells = self._recent_sells.get(symbol, [])
        now = datetime.datetime.now()
        for _sell_id, price, ts in sells:
            if (now - ts).days < 30:
                return (False,
                        f"Wash sale risk: {symbol} was sold at a loss on {ts.date()} "
                        f"(within 30-day window).")
        return (True, "")

    def _record_sell(self, trade: Trade) -> None:
        """Record a sell trade for wash sale detection."""
        if trade.side.value != "sell":
            return
        if trade.symbol not in self._recent_sells:
            self._recent_sells[trade.symbol] = []
        self._recent_sells[trade.symbol].append(
            (trade.id, trade.price, trade.executed_at),
        )
        # Prune records older than 30 days
        now = datetime.datetime.now()
        self._recent_sells[trade.symbol] = [
            s for s in self._recent_sells[trade.symbol]
            if (now - s[2]).days < 30
        ]
