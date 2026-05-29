"""
Valuation models for Lyra Finance.

Implements Layer 3 (Financial Analysis Pipeline) components:
- DCFValuation: discounted cash flow analysis
- EVEbitdaValuation: comparable company analysis
- HybridValuation: weighted combination of multiple methods

Design principles:
- Deterministic math, AI reasoning — LLMs do not calculate
- Structural constraints ensure sensible valuation bounds
- Multiple methods with configurable weights reduce model risk
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lyra_finance.models import ValuationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DCF valuation
# ---------------------------------------------------------------------------


@dataclass
class DCFAssumptions:
    """Assumptions for Discounted Cash Flow valuation."""
    free_cash_flow: float = 100_000_000.0       # TTM FCF in dollars
    growth_rate_pct: float = 5.0                 # Annual FCF growth rate %
    terminal_growth_pct: float = 2.0             # Perpetuity growth rate %
    discount_rate_pct: float = 10.0              # WACC or required return %
    projection_years: int = 5                    # Explicit projection period
    shares_outstanding: int = 100_000_000        # Diluted shares
    cash_and_equivalents: float = 0.0            # Excess cash
    total_debt: float = 0.0                      # Total debt
    margin_of_safety_pct: float = 15.0           # Margin of safety %


class DCFValuation:
    """Discounted Cash Flow valuation model.

    Computes intrinsic value by projecting free cash flows and discounting
    them to present value, plus terminal value.
    """

    def __init__(self, name: str = "DCFValuation",
                 assumptions: DCFAssumptions | None = None) -> None:
        self.name = name
        self.assumptions = assumptions or DCFAssumptions()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def value(self, symbol: str, current_price: float,
              assumptions: DCFAssumptions | None = None) -> ValuationResult:
        """Run DCF valuation for the given symbol.

        Args:
            symbol: Ticker symbol.
            current_price: Current market price.
            assumptions: Optional override assumptions.

        Returns:
            ValuationResult with fair value.
        """
        a = assumptions or self.assumptions
        growth_rate = a.growth_rate_pct / 100.0
        terminal_growth = a.terminal_growth_pct / 100.0
        discount_rate = a.discount_rate_pct / 100.0

        # Project FCFs
        pv_fcfs = 0.0
        fcf = a.free_cash_flow
        for year in range(1, a.projection_years + 1):
            fcf = fcf * (1.0 + growth_rate)
            pv_fcf = fcf / ((1.0 + discount_rate) ** year)
            pv_fcfs += pv_fcf

        # Terminal value (Gordon Growth Model)
        terminal_fcf = fcf * (1.0 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1.0 + discount_rate) ** a.projection_years)

        # Enterprise value
        enterprise_value = pv_fcfs + pv_terminal

        # Equity value
        equity_value = (enterprise_value
                        + a.cash_and_equivalents
                        - a.total_debt)

        # Per share value
        if a.shares_outstanding > 0:
            fair_value = equity_value / a.shares_outstanding
        else:
            fair_value = 0.0

        confidence = self._confidence_score(a, fair_value > 0)

        self.logger.info(
            "DCF %s: EV=$%.2fB, FV=$%.2f, price=$%.2f",
            symbol, enterprise_value / 1e9, fair_value, current_price,
        )

        return ValuationResult(
            symbol=symbol,
            fair_value=round(fair_value, 2),
            current_price=current_price,
            method="dcf",
            confidence=confidence,
            assumptions={
                "free_cash_flow": a.free_cash_flow,
                "growth_rate_pct": a.growth_rate_pct,
                "terminal_growth_pct": a.terminal_growth_pct,
                "discount_rate_pct": a.discount_rate_pct,
                "projection_years": a.projection_years,
                "enterprise_value": round(enterprise_value, 2),
                "equity_value": round(equity_value, 2),
                "pv_fcfs": round(pv_fcfs, 2),
                "pv_terminal": round(pv_terminal, 2),
                "terminal_value": round(terminal_value, 2),
                "cash_and_equivalents": a.cash_and_equivalents,
                "total_debt": a.total_debt,
            },
        )

    @staticmethod
    def _confidence_score(assumptions: DCFAssumptions,
                          positive_fv: bool) -> float:
        """Estimate confidence based on assumption reasonableness."""
        score = 0.5  # baseline

        # Terminal growth should be < discount rate
        if assumptions.terminal_growth_pct < assumptions.discount_rate_pct:
            score += 0.15
        else:
            score -= 0.2

        # Growth should be reasonable
        if 0 < assumptions.growth_rate_pct < 30:
            score += 0.1
        else:
            score -= 0.1

        # Positive FCF
        if assumptions.free_cash_flow > 0:
            score += 0.1
        else:
            score -= 0.2

        # Reasonable discount rate
        if 5 <= assumptions.discount_rate_pct <= 15:
            score += 0.05

        # Positive fair value
        if positive_fv:
            score += 0.1

        return max(0.1, min(0.95, score))


# ---------------------------------------------------------------------------
# EV/EBITDA valuation
# ---------------------------------------------------------------------------


@dataclass
class EVEbitdaAssumptions:
    """Assumptions for EV/EBITDA comparable company analysis."""
    ebitda: float = 50_000_000.0           # TTM EBITDA
    target_ev_ebitda_multiple: float = 12.0  # Target EV/EBITDA multiple
    cash_and_equivalents: float = 0.0
    total_debt: float = 0.0
    shares_outstanding: int = 100_000_000
    comparable_multiple_high: float = 15.0  # Sector high
    comparable_multiple_low: float = 8.0    # Sector low


class EVEbitdaValuation:
    """EV/EBITDA valuation model based on comparable company analysis.

    Computes fair value by applying a target EV/EBITDA multiple to the
    company's EBITDA, adjusting for net debt.
    """

    def __init__(self, name: str = "EVEbitdaValuation",
                 assumptions: EVEbitdaAssumptions | None = None) -> None:
        self.name = name
        self.assumptions = assumptions or EVEbitdaAssumptions()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def value(self, symbol: str, current_price: float,
              assumptions: EVEbitdaAssumptions | None = None) -> ValuationResult:
        """Run EV/EBITDA valuation for the given symbol.

        Args:
            symbol: Ticker symbol.
            current_price: Current market price.
            assumptions: Optional override assumptions.

        Returns:
            ValuationResult with fair value.
        """
        a = assumptions or self.assumptions

        # Enterprise value from EBITDA multiple
        enterprise_value = a.ebitda * a.target_ev_ebitda_multiple

        # Equity value
        equity_value = (enterprise_value
                        + a.cash_and_equivalents
                        - a.total_debt)

        # Per share value
        fair_value = (equity_value / a.shares_outstanding
                      if a.shares_outstanding > 0 else 0.0)

        confidence = self._confidence_score(a, a.target_ev_ebitda_multiple)

        # Compute range
        ev_low = a.ebitda * a.comparable_multiple_low
        ev_high = a.ebitda * a.comparable_multiple_high
        equity_low = ev_low + a.cash_and_equivalents - a.total_debt
        equity_high = ev_high + a.cash_and_equivalents - a.total_debt
        fair_low = (equity_low / a.shares_outstanding
                    if a.shares_outstanding > 0 else 0.0)
        fair_high = (equity_high / a.shares_outstanding
                     if a.shares_outstanding > 0 else 0.0)

        self.logger.info(
            "EV/EBITDA %s: EV=$%.2fB, FV=$%.2f (range: $%.2f–$%.2f)",
            symbol, enterprise_value / 1e9, fair_value, fair_low, fair_high,
        )

        return ValuationResult(
            symbol=symbol,
            fair_value=round(fair_value, 2),
            current_price=current_price,
            method="ev_ebitda",
            confidence=confidence,
            assumptions={
                "ebitda": a.ebitda,
                "target_ev_ebitda_multiple": a.target_ev_ebitda_multiple,
                "comparable_multiple_low": a.comparable_multiple_low,
                "comparable_multiple_high": a.comparable_multiple_high,
                "enterprise_value": round(enterprise_value, 2),
                "equity_value": round(equity_value, 2),
                "fair_value_range_low": round(fair_low, 2),
                "fair_value_range_high": round(fair_high, 2),
            },
        )

    @staticmethod
    def _confidence_score(assumptions: EVEbitdaAssumptions,
                          multiple: float) -> float:
        """Estimate confidence in EV/EBITDA valuation."""
        score = 0.5  # baseline

        # Multiple should be within comparable range
        if assumptions.comparable_multiple_low <= multiple <= assumptions.comparable_multiple_high:
            score += 0.15
        else:
            score -= 0.15

        # Positive EBITDA
        if assumptions.ebitda > 0:
            score += 0.15
        else:
            score -= 0.25

        # Reasonable multiple range width
        range_width = assumptions.comparable_multiple_high - assumptions.comparable_multiple_low
        if 3 <= range_width <= 10:
            score += 0.1

        # Sufficient shares outstanding
        if assumptions.shares_outstanding > 1_000_000:
            score += 0.05

        return max(0.1, min(0.95, score))


# ---------------------------------------------------------------------------
# Hybrid valuation
# ---------------------------------------------------------------------------


@dataclass
class HybridAssumptions:
    """Weights for hybrid valuation combination."""
    dcf_weight: float = 0.5
    ev_ebitda_weight: float = 0.5


class HybridValuation:
    """Weighted combination of multiple valuation methods.

    Reduces model risk by averaging across methodologies. The hybrid
    approach is the primary output of Layer 3 for final fair value
    estimates.
    """

    def __init__(self, name: str = "HybridValuation",
                 dcf: DCFValuation | None = None,
                 ev_ebitda: EVEbitdaValuation | None = None,
                 assumptions: HybridAssumptions | None = None) -> None:
        self.name = name
        self.dcf = dcf or DCFValuation()
        self.ev_ebitda = ev_ebitda or EVEbitdaValuation()
        self.assumptions = assumptions or HybridAssumptions()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def value(self, symbol: str, current_price: float,
              dcf_assumptions: DCFAssumptions | None = None,
              ev_ebitda_assumptions: EVEbitdaAssumptions | None = None,
              weights: tuple[float, float] | None = None) -> ValuationResult:
        """Compute hybrid valuation from DCF and EV/EBITDA.

        Args:
            symbol: Ticker symbol.
            current_price: Current market price.
            dcf_assumptions: Assumptions for DCF model.
            ev_ebitda_assumptions: Assumptions for EV/EBITDA model.
            weights: Override weights as (dcf_weight, ev_ebitda_weight).

        Returns:
            ValuationResult with blended fair value.
        """
        dcf_result = self.dcf.value(symbol, current_price, dcf_assumptions)
        ev_result = self.ev_ebitda.value(symbol, current_price, ev_ebitda_assumptions)

        if weights:
            dcf_w, ev_w = weights
        else:
            dcf_w, ev_w = self.assumptions.dcf_weight, self.assumptions.ev_ebitda_weight

        total_w = dcf_w + ev_w
        if total_w <= 0:
            dcf_w = ev_w = 0.5
            total_w = 1.0

        # Weighted fair value
        blended_fv = (dcf_result.fair_value * dcf_w + ev_result.fair_value * ev_w) / total_w

        # Confidence: weighted average adjusted for agreement
        agreement = 1.0 - abs(dcf_result.fair_value - ev_result.fair_value) / max(
            abs(dcf_result.fair_value), abs(ev_result.fair_value), 1.0,
        )
        blended_confidence = ((dcf_result.confidence * dcf_w
                               + ev_result.confidence * ev_w) / total_w
                              * (0.7 + 0.3 * agreement))

        self.logger.info(
            "Hybrid %s: FV=$%.2f (DCF=$%.2f, EV/EBITDA=$%.2f, agreement=%.1f%%)",
            symbol, blended_fv, dcf_result.fair_value, ev_result.fair_value,
            agreement * 100.0,
        )

        return ValuationResult(
            symbol=symbol,
            fair_value=round(blended_fv, 2),
            current_price=current_price,
            method="hybrid",
            confidence=min(0.95, blended_confidence),
            assumptions={
                "dcf_fair_value": dcf_result.fair_value,
                "ev_ebitda_fair_value": ev_result.fair_value,
                "dcf_weight": dcf_w,
                "ev_ebitda_weight": ev_w,
                "agreement_pct": round(agreement * 100.0, 2),
                "dcf_assumptions": dcf_result.assumptions,
                "ev_ebitda_assumptions": ev_result.assumptions,
            },
        )
