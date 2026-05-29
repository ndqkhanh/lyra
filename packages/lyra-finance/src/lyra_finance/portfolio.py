"""
Portfolio optimization engine for Lyra Finance.

Implements Layer 5 components:
- PortfolioOptimizer: mean-variance optimization, risk parity
- SharpeTracker: rolling Sharpe ratio tracking
- AllocationStrategy: configurable allocation methods

Design principles:
- Deterministic math for all optimizations
- Structural constraints (no negative weights, budget = 1.0)
- Hybrid speed+reasoning: fast allocation + validation checks
"""

from __future__ import annotations

import datetime
import logging
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from lyra_finance.models import (
    Asset,
    PerformanceSnapshot,
    Portfolio,
    RiskProfile,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Allocation strategy
# ---------------------------------------------------------------------------


class AllocationMethod(Enum):
    """Available portfolio allocation methods."""

    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP = "market_cap"
    MINIMUM_VARIANCE = "minimum_variance"
    RISK_PARITY = "risk_parity"
    MAX_SHARPE = "max_sharpe"
    CONSTANT_PROPORTION = "constant_proportion"


@dataclass
class AllocationResult:
    """Output of an allocation optimization."""

    method: AllocationMethod
    weights: dict[str, float]  # symbol -> weight
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    risk_contribution: dict[str, float] = field(default_factory=dict)
    details: str = ""


class AllocationStrategy:
    """Configurable allocation strategy with multiple methods.

    Provides fast, deterministic allocation calculations that can be
    used standalone or as inputs to PortfolioOptimizer.
    """

    def __init__(
        self,
        name: str = "AllocationStrategy",
        default_method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT,
    ) -> None:
        self.name = name
        self.default_method = default_method
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def allocate(
        self,
        symbols: Sequence[str],
        method: AllocationMethod | None = None,
        expected_returns: dict[str, float] | None = None,
        covariances: dict[tuple[str, str], float] | None = None,
        risk_profile: RiskProfile = RiskProfile.NEUTRAL,
    ) -> AllocationResult:
        """Compute allocation weights for a set of symbols.

        Args:
            symbols: Asset symbols to allocate across.
            method: Allocation method (default: EQUAL_WEIGHT).
            expected_returns: Expected annual returns by symbol.
            covariances: Pairwise return covariances.
            risk_profile: Risk profile for risk-based methods.

        Returns:
            AllocationResult with weights and expected statistics.
        """
        method = method or self.default_method
        n = len(symbols)
        if n == 0:
            return AllocationResult(method=method, weights={})

        if method == AllocationMethod.EQUAL_WEIGHT:
            return self._equal_weight(symbols, expected_returns)
        elif method == AllocationMethod.RISK_PARITY:
            return self._risk_parity(symbols, expected_returns, covariances, risk_profile)
        elif method == AllocationMethod.MINIMUM_VARIANCE:
            return self._minimum_variance(symbols, expected_returns, covariances)
        elif method == AllocationMethod.MAX_SHARPE:
            return self._max_sharpe(symbols, expected_returns, covariances)
        elif method == AllocationMethod.CONSTANT_PROPORTION:
            return self._constant_proportion(symbols, expected_returns, risk_profile)
        else:
            return self._market_cap(symbols, expected_returns)

    # ------------------------------------------------------------------
    # Allocation methods
    # ------------------------------------------------------------------

    def _equal_weight(
        self, symbols: Sequence[str], expected_returns: dict[str, float] | None = None
    ) -> AllocationResult:
        """Equal-weight allocation across all symbols."""
        weight = 1.0 / len(symbols)
        weights = dict.fromkeys(symbols, weight)
        exp_ret = (
            statistics.mean(expected_returns.values())
            if expected_returns and len(expected_returns) > 0
            else 0.0
        )
        return AllocationResult(
            method=AllocationMethod.EQUAL_WEIGHT,
            weights=weights,
            expected_return=exp_ret,
            details=f"Equal weight ({weight:.1%} each) across {len(symbols)} assets.",
        )

    def _risk_parity(
        self,
        symbols: Sequence[str],
        expected_returns: dict[str, float] | None = None,
        covariances: dict[tuple[str, str], float] | None = None,
        risk_profile: RiskProfile = RiskProfile.NEUTRAL,
    ) -> AllocationResult:
        """Risk parity: each asset contributes equal risk.

        Uses simple inverse-volatility heuristic when full covariance
        matrix is not available.
        """
        if covariances is None or len(covariances) == 0:
            # Fall back to inverse-volatility weighting
            vols: dict[str, float] = {}
            if expected_returns:
                for s in symbols:
                    vols[s] = abs(expected_returns.get(s, 0.0)) or 1.0
            if not vols:
                return self._equal_weight(symbols, expected_returns)

            inv_vol = {s: 1.0 / vols[s] for s in symbols}
            total = sum(inv_vol.values())
            weights = {s: v / total for s, v in inv_vol.items()}
        else:
            # Compute risk contributions from covariance matrix
            weights = self._solve_risk_parity(symbols, covariances)

        exp_ret = (
            statistics.mean(expected_returns.values())
            if expected_returns and len(expected_returns) > 0
            else 0.0
        )

        risk_contrib = dict(weights.items())
        return AllocationResult(
            method=AllocationMethod.RISK_PARITY,
            weights=weights,
            expected_return=exp_ret,
            risk_contribution=risk_contrib,
            details=f"Risk parity allocation across {len(symbols)} assets.",
        )

    def _minimum_variance(
        self,
        symbols: Sequence[str],
        expected_returns: dict[str, float] | None = None,
        covariances: dict[tuple[str, str], float] | None = None,
    ) -> AllocationResult:
        """Minimum variance portfolio."""
        if covariances is None or len(covariances) == 0:
            # Equal weight when no covariance data
            return self._equal_weight(symbols, expected_returns)

        len(symbols)
        weights = self._solve_min_variance(symbols, covariances)

        # Compute portfolio variance
        pvar = self._portfolio_variance(weights, covariances)
        pvol = math.sqrt(pvar) if pvar > 0 else 0.0

        return AllocationResult(
            method=AllocationMethod.MINIMUM_VARIANCE,
            weights=weights,
            expected_volatility=pvol,
            details=f"Minimum variance portfolio (σ={pvol:.2%}).",
        )

    def _max_sharpe(
        self,
        symbols: Sequence[str],
        expected_returns: dict[str, float] | None = None,
        covariances: dict[tuple[str, str], float] | None = None,
    ) -> AllocationResult:
        """Maximum Sharpe ratio portfolio."""
        if not expected_returns or not covariances:
            return self._equal_weight(symbols, expected_returns)

        len(symbols)
        weights = self._solve_max_sharpe(symbols, expected_returns, covariances)

        exp_ret = sum(weights[s] * expected_returns.get(s, 0.0) for s in symbols)
        pvar = self._portfolio_variance(weights, covariances)
        pvol = math.sqrt(pvar) if pvar > 0 else 0.0
        sharpe = (exp_ret / pvol) if pvol > 0 else 0.0

        return AllocationResult(
            method=AllocationMethod.MAX_SHARPE,
            weights=weights,
            expected_return=exp_ret,
            expected_volatility=pvol,
            sharpe_ratio=sharpe,
            details=f"Maximum Sharpe portfolio (SR={sharpe:.2f}).",
        )

    def _constant_proportion(
        self,
        symbols: Sequence[str],
        expected_returns: dict[str, float] | None = None,
        risk_profile: RiskProfile = RiskProfile.NEUTRAL,
    ) -> AllocationResult:
        """Constant proportion portfolio insurance-style allocation."""
        n = len(symbols)
        base_weight = 1.0 / n

        # Adjust for risk profile
        risk_mult = {
            RiskProfile.CONSERVATIVE: 0.5,
            RiskProfile.NEUTRAL: 1.0,
            RiskProfile.AGGRESSIVE: 1.5,
        }.get(risk_profile, 1.0)

        weights = {}
        for s in symbols:
            ret = expected_returns.get(s, 0.0) if expected_returns else 0.0
            # Higher expected return -> higher weight
            ret_factor = 1.0 + ret * risk_mult
            weights[s] = base_weight * max(0.5, min(2.0, ret_factor))

        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {s: w / total for s, w in weights.items()}

        return AllocationResult(
            method=AllocationMethod.CONSTANT_PROPORTION,
            weights=weights,
            details=f"Constant proportion allocation (profile={risk_profile.value}).",
        )

    def _market_cap(
        self, symbols: Sequence[str], expected_returns: dict[str, float] | None = None
    ) -> AllocationResult:
        """Market-cap-weighted allocation (equal weight if no cap data)."""
        if not expected_returns:
            return self._equal_weight(symbols, expected_returns)
        # Use expected returns as proxy for market cap influence
        total_ret = sum(abs(v) for v in expected_returns.values()) or 1.0
        weights = {s: abs(expected_returns.get(s, 0.0)) / total_ret for s in symbols}
        return AllocationResult(
            method=AllocationMethod.MARKET_CAP,
            weights=weights,
            expected_return=statistics.mean(expected_returns.values()),
            details=f"Market-cap proxy allocation across {len(symbols)} assets.",
        )

    # ------------------------------------------------------------------
    # Numerical solvers (simplified — production would use cvxopt/scipy)
    # ------------------------------------------------------------------

    @staticmethod
    def _solve_risk_parity(
        symbols: Sequence[str], covariances: dict[tuple[str, str], float]
    ) -> dict[str, float]:
        """Solve for equal risk contribution weights using iterative method."""
        n = len(symbols)
        if n == 0:
            return {}

        # Start with equal weights, iterate
        weights = dict.fromkeys(symbols, 1.0 / n)
        for _ in range(100):
            # Compute risk contributions
            portfolio_var = 0.0
            for i in symbols:
                for j in symbols:
                    cov = covariances.get((i, j), covariances.get((j, i), 0.0))
                    portfolio_var += weights[i] * weights[j] * cov

            if portfolio_var <= 0:
                break

            total_risk = math.sqrt(portfolio_var)

            # Marginal risk contributions
            mrc = {}
            for i in symbols:
                sum_cov = sum(
                    weights[j] * covariances.get((i, j), covariances.get((j, i), 0.0))
                    for j in symbols
                )
                mrc[i] = sum_cov / total_risk if total_risk > 0 else 0.0

            # Risk contributions
            rc = {s: weights[s] * mrc[s] for s in symbols}
            total_rc = sum(rc.values())

            # Adjust weights toward equal risk contribution
            target_rc = total_rc / n
            new_weights = {}
            for s in symbols:
                if rc.get(s, 0) > 0:
                    new_weights[s] = weights[s] * (target_rc / rc[s])
                else:
                    new_weights[s] = weights[s]

            # Normalize
            total_w = sum(new_weights.values())
            if total_w > 0:
                weights = {s: w / total_w for s, w in new_weights.items()}

        return weights

    @staticmethod
    def _solve_min_variance(
        symbols: Sequence[str], covariances: dict[tuple[str, str], float]
    ) -> dict[str, float]:
        """Solve for minimum variance portfolio using inverse-variance heuristic."""
        n = len(symbols)
        if n == 0:
            return {}

        # Extract variances (diagonal of covariance matrix)
        variances: dict[str, float] = {}
        for s in symbols:
            v = covariances.get((s, s), 0.0)
            variances[s] = v if v > 0 else 1.0

        # Inverse-variance weighting
        inv_var = {s: 1.0 / variances[s] for s in symbols}
        total = sum(inv_var.values())
        return {s: v / total for s, v in inv_var.items()}

    @staticmethod
    def _solve_max_sharpe(
        symbols: Sequence[str],
        expected_returns: dict[str, float],
        covariances: dict[tuple[str, str], float],
    ) -> dict[str, float]:
        """Solve for maximum Sharpe portfolio using simplified approach."""
        n = len(symbols)
        if n == 0:
            return {}

        # Minimum variance weights as baseline
        min_var = AllocationStrategy._solve_min_variance(symbols, covariances)

        # Tilt toward higher expected returns
        if expected_returns:
            total_ret = sum(max(0.0, expected_returns.get(s, 0.0)) for s in symbols)
            if total_ret > 0:
                ret_weights = {
                    s: max(0.0, expected_returns.get(s, 0.0)) / total_ret for s in symbols
                }
                # Blend min-var and return-based
                weights = {s: 0.5 * min_var[s] + 0.5 * ret_weights[s] for s in symbols}
                total_w = sum(weights.values())
                if total_w > 0:
                    return {s: w / total_w for s, w in weights.items()}

        return min_var

    @staticmethod
    def _portfolio_variance(
        weights: dict[str, float], covariances: dict[tuple[str, str], float]
    ) -> float:
        """Compute portfolio variance given weights and covariance matrix."""
        pvar = 0.0
        symbols = list(weights.keys())
        for i in symbols:
            for j in symbols:
                cov = covariances.get((i, j), covariances.get((j, i), 0.0))
                pvar += weights[i] * weights[j] * cov
        return max(0.0, pvar)


# ---------------------------------------------------------------------------
# Sharpe tracker
# ---------------------------------------------------------------------------


@dataclass
class SharpeSnapshot:
    """Rolling Sharpe ratio at a point in time."""

    timestamp: datetime.datetime
    sharpe_ratio: float
    periods_used: int
    annualized_return: float
    annualized_volatility: float


class SharpeTracker:
    """Tracks rolling Sharpe ratio over configurable lookback windows.

    Maintains a running history of portfolio returns and computes
    rolling annualized Sharpe ratio on demand.
    """

    def __init__(
        self, name: str = "SharpeTracker", window_days: int = 252, risk_free_rate: float = 0.0
    ) -> None:
        self.name = name
        self.window_days = window_days
        self.risk_free_rate = risk_free_rate
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._daily_returns: list[tuple[datetime.datetime, float]] = []

    def record_return(self, return_pct: float, timestamp: datetime.datetime | None = None) -> None:
        """Record a daily portfolio return."""
        self._daily_returns.append(
            (timestamp or datetime.datetime.now(), return_pct / 100.0),
        )
        # Prune old entries beyond window
        if len(self._daily_returns) > self.window_days * 2:
            _cutoff = len(self._daily_returns) - self.window_days * 2
            self._daily_returns = self._daily_returns[-self.window_days * 2 :]

    def compute(self) -> SharpeSnapshot:
        """Compute the current rolling Sharpe ratio."""
        recent = (
            self._daily_returns[-self.window_days :]
            if len(self._daily_returns) > self.window_days
            else self._daily_returns
        )

        if len(recent) < 5:
            return SharpeSnapshot(
                timestamp=datetime.datetime.now(),
                sharpe_ratio=0.0,
                periods_used=len(recent),
                annualized_return=0.0,
                annualized_volatility=0.0,
            )

        returns = [r[1] for r in recent]
        avg_return = statistics.mean(returns)
        vol = statistics.stdev(returns) if len(returns) > 1 else 0.0

        # Annualize
        ann_return = avg_return * 252
        ann_vol = vol * math.sqrt(252)

        excess_return = ann_return - self.risk_free_rate
        sharpe = excess_return / ann_vol if ann_vol > 0 else 0.0

        return SharpeSnapshot(
            timestamp=datetime.datetime.now(),
            sharpe_ratio=sharpe,
            periods_used=len(recent),
            annualized_return=ann_return * 100.0,
            annualized_volatility=ann_vol * 100.0,
        )

    @property
    def return_count(self) -> int:
        return len(self._daily_returns)

    def clear(self) -> None:
        """Clear all recorded returns."""
        self._daily_returns.clear()


# ---------------------------------------------------------------------------
# Portfolio optimizer
# ---------------------------------------------------------------------------


class PortfolioOptimizer:
    """Full portfolio optimization engine.

    Combines allocation strategies, Sharpe tracking, and performance
    monitoring into a single optimisation interface.
    """

    def __init__(
        self,
        name: str = "PortfolioOptimizer",
        strategy: AllocationStrategy | None = None,
        sharpe_tracker: SharpeTracker | None = None,
    ) -> None:
        self.name = name
        self.strategy = strategy or AllocationStrategy()
        self.sharpe_tracker = sharpe_tracker or SharpeTracker()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._snapshots: list[PerformanceSnapshot] = []

    def optimize(
        self,
        portfolio: Portfolio,
        assets: Sequence[Asset],
        expected_returns: dict[str, float] | None = None,
        covariances: dict[tuple[str, str], float] | None = None,
        method: AllocationMethod | None = None,
    ) -> AllocationResult:
        """Run full portfolio optimisation.

        Args:
            portfolio: Current portfolio state.
            assets: Available assets to allocate across.
            expected_returns: Expected returns per asset.
            covariances: Return covariance matrix.
            method: Allocation method override.

        Returns:
            AllocationResult with optimal weights.
        """
        symbols = [a.symbol for a in assets]
        if not symbols:
            return AllocationResult(method=method or AllocationMethod.EQUAL_WEIGHT, weights={})

        result = self.strategy.allocate(
            symbols=symbols,
            method=method,
            expected_returns=expected_returns,
            covariances=covariances,
            risk_profile=portfolio.risk_profile,
        )

        self.logger.info(
            "Optimized portfolio (%s): %d assets, σ=%.2f%%, SR=%.2f",
            result.method.value,
            len(symbols),
            result.expected_volatility * 100.0 if result.expected_volatility > 0 else 0.0,
            result.sharpe_ratio,
        )

        return result

    def snapshot(self, portfolio: Portfolio) -> PerformanceSnapshot:
        """Record a performance snapshot."""
        sharpe = self.sharpe_tracker.compute()
        snapshot = PerformanceSnapshot(
            total_value=portfolio.total_value,
            sharpe_ratio=sharpe.sharpe_ratio,
            total_trades=sum(p.quantity for p in portfolio.positions),
        )
        self._snapshots.append(snapshot)
        return snapshot

    @property
    def snapshots(self) -> tuple[PerformanceSnapshot, ...]:
        return tuple(self._snapshots)
