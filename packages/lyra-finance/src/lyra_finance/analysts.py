"""
Multi-agent analyst system for Lyra Finance.

Implements 4 specialised analyst types as part of Layer 2 (Multi-Agent Trading
System). Each analyst produces AnalystReport instances that feed into the
adversarial debate and trading pipeline.

Design principles:
- Deterministic calculations, LLM-free math
- Fast filters before deep analysis
- Structural constraints over LLM instructions
"""

from __future__ import annotations

import logging
import statistics
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from lyra_finance.models import (
    AnalystReport,
    AnalystType,
    Asset,
    MarketData,
    SentimentSignal,
    SignalSource,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base analyst
# ---------------------------------------------------------------------------


class BaseAnalyst(ABC):
    """Abstract base for all analyst types."""

    def __init__(self, name: str = "") -> None:
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    @abstractmethod
    def analyze(
        self,
        symbol: str,
        asset: Asset | None = None,
        market_data: Sequence[MarketData] | None = None,
        signals: Sequence[SentimentSignal] | None = None,
    ) -> AnalystReport:
        """Produce an AnalystReport for the given symbol."""
        ...


# ---------------------------------------------------------------------------
# Fundamental analyst
# ---------------------------------------------------------------------------


@dataclass
class FinancialStatement:
    """Simplified financial statement for fundamental analysis."""

    revenue: float = 0.0
    cost_of_goods_sold: float = 0.0
    operating_expenses: float = 0.0
    net_income: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    total_equity: float = 0.0
    shares_outstanding: int = 0
    free_cash_flow: float = 0.0
    ebitda: float = 0.0
    revenue_growth_pct: float = 0.0
    earnings_growth_pct: float = 0.0


class FundamentalAnalyst(BaseAnalyst):
    """Analyses financial statements, ratios, and fundamental metrics.

    Performs:
    - DCF-based intrinsic value estimate
    - Key financial ratio calculation (P/E, P/B, D/E, ROE, ROA)
    - Growth trajectory assessment
    """

    def __init__(
        self,
        name: str = "FundamentalAnalyst",
        statements: dict[str, FinancialStatement] | None = None,
    ) -> None:
        super().__init__(name)
        self._statements: dict[str, FinancialStatement] = statements or {}

    def register_statement(self, symbol: str, statement: FinancialStatement) -> None:
        """Register a financial statement for a symbol."""
        self._statements[symbol] = statement

    def analyze(
        self,
        symbol: str,
        asset: Asset | None = None,
        market_data: Sequence[MarketData] | None = None,
        signals: Sequence[SentimentSignal] | None = None,
    ) -> AnalystReport:
        statement = self._statements.get(symbol)
        if statement is None:
            return AnalystReport(
                analyst_type=AnalystType.FUNDAMENTAL,
                symbol=symbol,
                rating="hold",
                confidence=0.3,
                reasoning="No financial statement available for analysis.",
            )

        ratios = self._compute_ratios(statement, asset)
        score = self._compute_fundamental_score(ratios, statement)

        rating, confidence = self._rating_from_score(score)
        target_price = self._estimate_target_price(asset, statement, ratios)

        metadata = {
            "pe_ratio": ratios.get("pe_ratio"),
            "pb_ratio": ratios.get("pb_ratio"),
            "de_ratio": ratios.get("de_ratio"),
            "roe_pct": ratios.get("roe_pct"),
            "roa_pct": ratios.get("roa_pct"),
            "gross_margin_pct": ratios.get("gross_margin_pct"),
            "net_margin_pct": ratios.get("net_margin_pct"),
            "fundamental_score": score,
            "fcf_yield": ratios.get("fcf_yield"),
        }

        reasoning = (
            f"Fundamental score: {score:.2f}/100. "
            f"P/E: {ratios.get('pe_ratio', 'N/A')}, "
            f"P/B: {ratios.get('pb_ratio', 'N/A')}, "
            f"D/E: {ratios.get('de_ratio', 'N/A')}, "
            f"ROE: {ratios.get('roe_pct', 'N/A')}%, "
            f"Revenue growth: {statement.revenue_growth_pct:.1f}%."
        )

        return AnalystReport(
            analyst_type=AnalystType.FUNDAMENTAL,
            symbol=symbol,
            rating=rating,
            target_price=target_price,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata,
        )

    def _compute_ratios(
        self, statement: FinancialStatement, asset: Asset | None
    ) -> dict[str, float | None]:
        """Compute key financial ratios."""
        ratios: dict[str, float | None] = {}

        # P/E ratio
        if asset and statement.net_income > 0 and statement.shares_outstanding > 0:
            eps = statement.net_income / statement.shares_outstanding
            ratios["pe_ratio"] = asset.current_price / eps if eps > 0 else None
        else:
            ratios["pe_ratio"] = statement.eps if statement.eps else None

        # P/B ratio
        if asset and statement.total_equity > 0 and statement.shares_outstanding > 0:
            book_value_per_share = statement.total_equity / statement.shares_outstanding
            ratios["pb_ratio"] = (
                asset.current_price / book_value_per_share if book_value_per_share > 0 else None
            )
        else:
            ratios["pb_ratio"] = None

        # D/E ratio
        ratios["de_ratio"] = (
            statement.total_liabilities / statement.total_equity
            if statement.total_equity > 0
            else None
        )

        # ROE
        ratios["roe_pct"] = (
            (statement.net_income / statement.total_equity) * 100.0
            if statement.total_equity > 0
            else None
        )

        # ROA
        ratios["roa_pct"] = (
            (statement.net_income / statement.total_assets) * 100.0
            if statement.total_assets > 0
            else None
        )

        # Gross margin
        if statement.revenue > 0:
            gross_profit = statement.revenue - statement.cost_of_goods_sold
            ratios["gross_margin_pct"] = (gross_profit / statement.revenue) * 100.0
        else:
            ratios["gross_margin_pct"] = None

        # Net margin
        ratios["net_margin_pct"] = (
            (statement.net_income / statement.revenue) * 100.0 if statement.revenue > 0 else None
        )

        # FCF yield
        if (
            asset
            and statement.free_cash_flow > 0
            and asset.current_price > 0
            and statement.shares_outstanding > 0
        ):
            fcf_per_share = statement.free_cash_flow / statement.shares_outstanding
            ratios["fcf_yield"] = (fcf_per_share / asset.current_price) * 100.0
        else:
            ratios["fcf_yield"] = None

        return ratios

    def _compute_fundamental_score(
        self, ratios: dict[str, float | None], statement: FinancialStatement
    ) -> float:
        """Score from 0-100 based on fundamental health."""
        score = 50.0  # neutral baseline

        # Revenue growth
        if statement.revenue_growth_pct > 10:
            score += 10
        elif statement.revenue_growth_pct > 5:
            score += 5
        elif statement.revenue_growth_pct < 0:
            score -= 10

        # Profitability
        net_margin = ratios.get("net_margin_pct") or 0
        if net_margin > 20:
            score += 10
        elif net_margin > 10:
            score += 5
        elif net_margin < 0:
            score -= 10

        # Leverage
        de = ratios.get("de_ratio") or 0
        if de < 0.3:
            score += 10
        elif de < 1.0:
            score += 5
        elif de > 3.0:
            score -= 10

        # ROE
        roe = ratios.get("roe_pct") or 0
        if roe > 20:
            score += 10
        elif roe > 10:
            score += 5
        elif roe < 0:
            score -= 5

        # FCF yield
        fcf_yield = ratios.get("fcf_yield") or 0
        if fcf_yield > 8:
            score += 10
        elif fcf_yield > 4:
            score += 5

        return max(0.0, min(100.0, score))

    def _estimate_target_price(
        self, asset: Asset | None, statement: FinancialStatement, ratios: dict[str, float | None]
    ) -> float | None:
        """Estimate target price from P/E multiple approach."""
        if not asset or asset.current_price <= 0:
            return None
        pe = ratios.get("pe_ratio")
        if pe is not None and pe > 0:
            # Apply industry-average P/E expansion/contraction
            target_pe = pe * 1.1  # 10% expansion for quality
            eps = (
                statement.net_income / statement.shares_outstanding
                if statement.shares_outstanding > 0
                else 0
            )
            if eps > 0:
                return target_pe * eps
        return None

    def _rating_from_score(self, score: float) -> tuple[str, float]:
        """Map fundamental score to rating string and confidence."""
        if score >= 80:
            return ("strong_buy", 0.85)
        if score >= 65:
            return ("buy", 0.70)
        if score >= 45:
            return ("hold", 0.55)
        if score >= 30:
            return ("sell", 0.65)
        return ("strong_sell", 0.80)


# ---------------------------------------------------------------------------
# Sentiment analyst
# ---------------------------------------------------------------------------


class SentimentAnalyst(BaseAnalyst):
    """Analyses market sentiment from news and social signals.

    Aggregates sentiment signals and produces a consensus view using
    confidence-weighted averaging.
    """

    def __init__(
        self, name: str = "SentimentAnalyst", weights: dict[str, float] | None = None
    ) -> None:
        super().__init__(name)
        self._weights = weights or {
            SignalSource.NEWS_ARTICLE.value: 1.0,
            SignalSource.SOCIAL_MEDIA.value: 0.5,
            SignalSource.EARNINGS_CALL.value: 1.5,
            SignalSource.SEC_FILING.value: 1.2,
            SignalSource.MACRO_DATA.value: 0.8,
            SignalSource.ANALYST_RATING.value: 1.0,
            SignalSource.INSIDER_TRADING.value: 1.3,
        }

    def analyze(
        self,
        symbol: str,
        asset: Asset | None = None,
        market_data: Sequence[MarketData] | None = None,
        signals: Sequence[SentimentSignal] | None = None,
    ) -> AnalystReport:
        if not signals:
            return AnalystReport(
                analyst_type=AnalystType.SENTIMENT,
                symbol=symbol,
                rating="hold",
                confidence=0.2,
                reasoning="No sentiment signals available.",
            )

        symbol_signals = [s for s in signals if s.symbol == symbol]
        if not symbol_signals:
            return AnalystReport(
                analyst_type=AnalystType.SENTIMENT,
                symbol=symbol,
                rating="hold",
                confidence=0.2,
                reasoning=f"No sentiment signals found for {symbol}.",
            )

        weighted_score, total_confidence = self._aggregate_sentiment(symbol_signals)
        avg_confidence = total_confidence / len(symbol_signals) if symbol_signals else 0.0

        rating = self._rating_from_score(weighted_score)
        confidence = min(0.9, avg_confidence * 0.8 + 0.1)

        positive_count = sum(1 for s in symbol_signals if s.score > 0)
        negative_count = sum(1 for s in symbol_signals if s.score < 0)
        neutral_count = len(symbol_signals) - positive_count - negative_count

        reasoning = (
            f"Sentiment score: {weighted_score:+.3f} "
            f"(+{positive_count}/-{negative_count}/{neutral_count} signals). "
            f"Confidence: {confidence:.1%}."
        )

        return AnalystReport(
            analyst_type=AnalystType.SENTIMENT,
            symbol=symbol,
            rating=rating,
            confidence=confidence,
            reasoning=reasoning,
            signals=tuple(symbol_signals),
            metadata={
                "weighted_score": weighted_score,
                "signal_count": len(symbol_signals),
                "positive_signals": positive_count,
                "negative_signals": negative_count,
                "neutral_signals": neutral_count,
            },
        )

    def _aggregate_sentiment(self, signals: Sequence[SentimentSignal]) -> tuple[float, float]:
        """Confidence-weighted average of sentiment signals."""
        total_weighted = 0.0
        total_confidence = 0.0

        for signal in signals:
            w = self._weights.get(signal.source.value, 1.0) * signal.confidence
            total_weighted += signal.score * w
            total_confidence += w

        if total_confidence > 0:
            return (total_weighted / total_confidence, total_confidence)
        return (0.0, 0.0)

    def _rating_from_score(self, score: float) -> str:
        if score >= 0.5:
            return "strong_buy"
        if score >= 0.2:
            return "buy"
        if score > -0.2:
            return "hold"
        if score > -0.5:
            return "sell"
        return "strong_sell"


# ---------------------------------------------------------------------------
# Technical analyst
# ---------------------------------------------------------------------------


class TechnicalAnalyst(BaseAnalyst):
    """Performs technical analysis using price/volume indicators.

    Computes:
    - Simple Moving Averages (SMA-20, SMA-50, SMA-200)
    - Relative Strength Index (RSI)
    - MACD line, signal line, histogram
    - Support/resistance level detection
    """

    def analyze(
        self,
        symbol: str,
        asset: Asset | None = None,
        market_data: Sequence[MarketData] | None = None,
        signals: Sequence[SentimentSignal] | None = None,
    ) -> AnalystReport:
        if not market_data:
            return AnalystReport(
                analyst_type=AnalystType.TECHNICAL,
                symbol=symbol,
                rating="hold",
                confidence=0.2,
                reasoning="No market data available for technical analysis.",
            )

        closes = [md.close for md in market_data if md.close > 0]
        if len(closes) < 20:
            return AnalystReport(
                analyst_type=AnalystType.TECHNICAL,
                symbol=symbol,
                rating="hold",
                confidence=0.3,
                reasoning=f"Insufficient data points ({len(closes)}). Need at least 20.",
            )

        signals_list: list[SentimentSignal] = []
        scores = 0.0
        checks = 0

        # SMA trend
        sma_20 = self._sma(closes, 20)
        sma_50 = self._sma(closes, 50) if len(closes) >= 50 else None
        sma_200 = self._sma(closes, 200) if len(closes) >= 200 else None

        current_price = closes[-1]
        sma_bullish = 0
        sma_bearish = 0

        if sma_50 is not None and current_price > sma_50:
            sma_bullish += 1
        elif sma_50 is not None:
            sma_bearish += 1

        if sma_200 is not None and current_price > sma_200:
            sma_bullish += 1
        elif sma_200 is not None:
            sma_bearish += 1

        # Golden cross / death cross
        if sma_50 is not None and sma_200 is not None:
            prev_sma_50 = self._sma(closes[:-1], 50) if len(closes) > 50 else sma_50
            prev_sma_200 = self._sma(closes[:-1], 200) if len(closes) > 200 else sma_200
            if sma_50 > sma_200 and prev_sma_50 <= prev_sma_200:
                scores += 15  # golden cross
                checks += 1
            elif sma_50 < sma_200 and prev_sma_50 >= prev_sma_200:
                scores -= 15  # death cross
                checks += 1

        scores += (sma_bullish - sma_bearish) * 5
        checks += 1

        # RSI
        rsi = self._rsi(closes, 14)
        rsi_signal = SentimentSignal(
            symbol=symbol,
            score=0.0,
            source=SignalSource.NEWS_ARTICLE,
            headline=f"RSI-14: {rsi:.1f}",
        )
        if rsi < 30:
            scores += 10  # oversold — bullish
            rsi_signal = SentimentSignal(
                symbol=symbol,
                score=0.7,
                source=SignalSource.NEWS_ARTICLE,
                confidence=0.6,
                headline=f"RSI oversold ({rsi:.1f})",
            )
        elif rsi > 70:
            scores -= 10  # overbought — bearish
            rsi_signal = SentimentSignal(
                symbol=symbol,
                score=-0.7,
                source=SignalSource.NEWS_ARTICLE,
                confidence=0.6,
                headline=f"RSI overbought ({rsi:.1f})",
            )
        signals_list.append(rsi_signal)

        # MACD
        macd_line, signal_line = self._macd(closes)
        macd_histogram = macd_line[-1] - signal_line[-1]
        macd_signal = SentimentSignal(
            symbol=symbol,
            score=0.0,
            source=SignalSource.NEWS_ARTICLE,
            headline=f"MACD histogram: {macd_histogram:.3f}",
        )
        if macd_histogram > 0 and len(macd_line) > 1:
            prev_histogram = macd_line[-2] - signal_line[-2]
            if macd_histogram > prev_histogram:
                scores += 8  # bullish MACD momentum
                macd_signal = SentimentSignal(
                    symbol=symbol,
                    score=0.6,
                    source=SignalSource.NEWS_ARTICLE,
                    confidence=0.55,
                    headline=f"MACD bullish ({macd_histogram:+.3f})",
                )
        elif macd_histogram < 0:
            prev_histogram = macd_line[-2] - signal_line[-2] if len(macd_line) > 1 else 0
            if macd_histogram < prev_histogram:
                scores -= 8  # bearish MACD momentum
                macd_signal = SentimentSignal(
                    symbol=symbol,
                    score=-0.6,
                    source=SignalSource.NEWS_ARTICLE,
                    confidence=0.55,
                    headline=f"MACD bearish ({macd_histogram:+.3f})",
                )
        signals_list.append(macd_signal)

        # Volume confirmation
        if len(market_data) >= 2:
            recent_volumes = [md.volume for md in market_data[-5:] if md.volume > 0]
            older_volumes = [md.volume for md in market_data[-10:-5] if md.volume > 0]
            if recent_volumes and older_volumes:
                avg_recent = statistics.mean(recent_volumes)
                avg_older = statistics.mean(older_volumes)
                if avg_older > 0 and avg_recent > avg_older * 1.5:
                    scores += 5  # rising volume confirms trend

        # Normalize score
        max_possible = 10 + 15 + 10 + 8 + 5  # from RSI + cross + SMA + MACD + volume
        normalized = max(-1.0, min(1.0, scores / max_possible))

        rating = self._rating_from_score(normalized)
        confidence = min(0.8, 0.3 + abs(normalized) * 0.5)

        reasoning = (
            f"Technical score: {normalized:+.3f}. "
            f"SMA-20: {sma_20:.2f}, RSI-14: {rsi:.1f}, "
            f"MACD hist: {macd_histogram:.3f}. "
            f"Price: ${current_price:.2f}."
        )

        return AnalystReport(
            analyst_type=AnalystType.TECHNICAL,
            symbol=symbol,
            rating=rating,
            target_price=self._estimate_target(closes),
            confidence=confidence,
            reasoning=reasoning,
            signals=tuple(signals_list),
            metadata={
                "sma_20": sma_20,
                "sma_50": sma_50,
                "sma_200": sma_200,
                "rsi_14": rsi,
                "macd_histogram": macd_histogram,
                "technical_score": normalized,
                "data_points": len(closes),
            },
        )

    # ------------------------------------------------------------------
    # Technical indicator implementations (deterministic, no LLM)
    # ------------------------------------------------------------------

    @staticmethod
    def _sma(values: Sequence[float], period: int) -> float:
        if len(values) < period:
            return 0.0
        return sum(values[-period:]) / period

    @staticmethod
    def _ema(values: Sequence[float], period: int) -> float:
        if len(values) < period:
            return values[-1] if values else 0.0
        multiplier = 2.0 / (period + 1)
        ema = sum(values[:period]) / period
        for v in values[period:]:
            ema = (v - ema) * multiplier + ema
        return ema

    def _rsi(self, closes: Sequence[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains, losses = 0.0, 0.0
        for i in range(len(closes) - period, len(closes)):
            change = closes[i] - closes[i - 1]
            if change > 0:
                gains += change
            else:
                losses -= change
        avg_gain = gains / period
        avg_loss = losses / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _macd(
        self, closes: Sequence[float], fast: int = 12, slow: int = 26, signal_period: int = 9
    ) -> tuple[list[float], list[float]]:
        """Compute MACD line and signal line from closing prices.

        Proper forward computation: MACD line = EMA(fast) - EMA(slow),
        signal line = EMA(MACD, signal_period).
        """
        n = len(closes)
        if n < slow + signal_period:
            return [0.0], [0.0]

        # Compute EMA(fast) and EMA(slow) for each position
        fast_mult = 2.0 / (fast + 1)
        slow_mult = 2.0 / (slow + 1)

        fast_ema = sum(closes[:fast]) / fast
        slow_ema = sum(closes[:slow]) / slow

        # Catch up fast_ema from index `fast` to `slow - 1`
        for i in range(fast, slow):
            fast_ema = (closes[i] - fast_ema) * fast_mult + fast_ema

        macd_values: list[float] = []
        for i in range(slow, n):
            # Update both EMAs in sync
            fast_ema = (closes[i] - fast_ema) * fast_mult + fast_ema
            slow_ema = (closes[i] - slow_ema) * slow_mult + slow_ema
            macd_values.append(fast_ema - slow_ema)

        if not macd_values:
            return [0.0], [0.0]

        # Signal line: EMA of MACD values
        sig_mult = 2.0 / (signal_period + 1)
        signal_ema = sum(macd_values[:signal_period]) / signal_period
        signal_values = [signal_ema]

        for v in macd_values[signal_period:]:
            signal_ema = (v - signal_ema) * sig_mult + signal_ema
            signal_values.append(signal_ema)

        # Return last few values for recent analysis
        recent_macd = macd_values[-signal_period - 1 :]
        recent_signal = signal_values[-signal_period - 1 :]
        return recent_macd, recent_signal

    @staticmethod
    def _estimate_target(closes: Sequence[float]) -> float | None:
        """Simple resistance-based target price estimate."""
        if len(closes) < 20:
            return None
        recent = closes[-20:]
        resistance = max(recent)
        current = closes[-1]
        if current > 0:
            # Target ~1.05x of recent resistance
            return resistance * 1.05
        return None

    def _rating_from_score(self, score: float) -> str:
        if score >= 0.5:
            return "strong_buy"
        if score >= 0.2:
            return "buy"
        if score > -0.2:
            return "hold"
        if score > -0.5:
            return "sell"
        return "strong_sell"


# ---------------------------------------------------------------------------
# News analyst
# ---------------------------------------------------------------------------


class NewsAnalyst(BaseAnalyst):
    """Analyses event-driven news and macro factors.

    Evaluates:
    - Earnings surprise magnitude
    - Macroeconomic indicator impact
    - Geopolitical event classification
    - Sector-wide catalyst identification
    """

    def __init__(self, name: str = "NewsAnalyst") -> None:
        super().__init__(name)
        self._event_weights: dict[str, float] = {
            "earnings_beat": 15.0,
            "earnings_miss": -15.0,
            "guidance_up": 10.0,
            "guidance_down": -10.0,
            "merger_acquired": 20.0,
            "merger_acquirer": -5.0,
            "regulatory_approval": 12.0,
            "regulatory_penalty": -18.0,
            "product_launch": 8.0,
            "product_failure": -12.0,
            "management_change": 5.0,
            "dividend_increase": 5.0,
            "dividend_cut": -8.0,
            "buyback_announced": 7.0,
            "insider_buying": 6.0,
            "insider_selling": -6.0,
            "macro_positive": 8.0,
            "macro_negative": -8.0,
            "geopolitical_risk": -12.0,
            "legal_settlement": -5.0,
        }

    def analyze(
        self,
        symbol: str,
        asset: Asset | None = None,
        market_data: Sequence[MarketData] | None = None,
        signals: Sequence[SentimentSignal] | None = None,
    ) -> AnalystReport:
        if not signals:
            return AnalystReport(
                analyst_type=AnalystType.NEWS,
                symbol=symbol,
                rating="hold",
                confidence=0.2,
                reasoning="No news signals available for analysis.",
            )

        # Score events
        total_score = 0.0
        event_details: list[str] = []
        significant_events = 0

        for signal in signals:
            if signal.symbol != symbol:
                continue
            event_type = signal.detail if signal.detail in self._event_weights else ""
            weight = self._event_weights.get(event_type, signal.score * 10)
            contribution = weight * signal.confidence
            total_score += contribution

            if abs(contribution) >= 5:
                significant_events += 1
                event_details.append(f"{event_type} ({contribution:+.1f})")

        # Normalize
        max_abs_score = max(1.0, sum(abs(w) for w in self._event_weights.values()) / 5)
        normalized = max(-1.0, min(1.0, total_score / max_abs_score))

        rating = self._rating_from_score(normalized)
        confidence = min(0.85, 0.2 + min(1.0, significant_events * 0.2))

        event_summary = "; ".join(event_details) if event_details else "No significant events"
        reasoning = (
            f"News score: {normalized:+.3f} across {significant_events} significant events. "
            f"{event_summary}."
        )

        return AnalystReport(
            analyst_type=AnalystType.NEWS,
            symbol=symbol,
            rating=rating,
            confidence=confidence,
            reasoning=reasoning,
            signals=tuple(signals),
            metadata={
                "event_score": normalized,
                "significant_events": significant_events,
                "total_score": total_score,
            },
        )

    def _rating_from_score(self, score: float) -> str:
        if score >= 0.5:
            return "strong_buy"
        if score >= 0.2:
            return "buy"
        if score > -0.2:
            return "hold"
        if score > -0.5:
            return "sell"
        return "strong_sell"
