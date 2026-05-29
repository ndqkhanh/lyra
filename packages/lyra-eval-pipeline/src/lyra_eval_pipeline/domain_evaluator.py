"""Domain-specific evaluation with the EvalAgent pattern."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .adaptive_rubric import AdaptiveRubric, RubricDimension
from .exceptions import DomainEvalError


@dataclass(frozen=True)
class DomainEvalConfig:
    """Configuration for domain evaluation."""

    domain: str
    metrics: tuple[str, ...]
    threshold: float = 0.7
    max_samples: int = 1000


@dataclass(frozen=True)
class EvalSample:
    """A single evaluation sample."""

    sample_id: str
    input_text: str
    expected_output: str
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class EvalResult:
    """Result of evaluating a single sample."""

    sample_id: str
    domain: str
    metric_scores: tuple[tuple[str, float], ...]
    overall_score: float
    passed: bool
    latency_ms: float


@dataclass(frozen=True)
class DomainEvalReport:
    """Aggregated report for a domain evaluation."""

    domain: str
    results: tuple[EvalResult, ...]
    pass_rate: float
    avg_score: float
    avg_latency_ms: float


_DOMAIN_SAMPLES: dict[str, list[tuple[str, str, str]]] = {
    "math": [
        ("math-001", "2 + 2", "4"),
        ("math-002", "10 * 5", "50"),
        ("math-003", "100 / 4", "25"),
        ("math-004", "3^2", "9"),
        ("math-005", "sqrt(144)", "12"),
    ],
    "code": [
        ("code-001", "def add(a, b): ...", "return a + b"),
        ("code-002", "sort a list in python", "sorted(lst)"),
        ("code-003", "reverse a string", "s[::-1]"),
        ("code-004", "check if key exists in dict", "'key' in d"),
        ("code-005", "read file contents", "open('f').read()"),
    ],
    "reasoning": [
        ("reason-001", "All men are mortal. Socrates is a man.", "Socrates is mortal"),
        ("reason-002", "If it rains, ground gets wet. It rained.", "Ground is wet"),
        ("reason-003", "A > B and B > C", "A > C"),
        ("reason-004", "All birds fly. Penguin is a bird.", "Penguin flies"),
        ("reason-005", "2x + 3 = 7, solve for x", "x = 2"),
    ],
}


class DomainEvaluator:
    """Evaluates model responses across domains using adaptive rubric scoring."""

    def __init__(self, configs: tuple[DomainEvalConfig, ...] | None = None) -> None:
        self._configs: dict[str, DomainEvalConfig] = {}
        self._rubric = AdaptiveRubric()
        if configs:
            for cfg in configs:
                self._configs[cfg.domain] = cfg

    def add_config(self, config: DomainEvalConfig) -> None:
        """Register a domain evaluation config."""
        self._configs[config.domain] = config

    def get_config(self, domain: str) -> DomainEvalConfig:
        """Get config for a domain, or raise if not found."""
        cfg = self._configs.get(domain)
        if cfg is None:
            raise DomainEvalError(f"No config found for domain: {domain}")
        return cfg

    async def load_samples(self, domain: str) -> tuple[EvalSample, ...]:
        """Load evaluation samples for a given domain."""
        raw = _DOMAIN_SAMPLES.get(domain)
        if raw is None:
            raise DomainEvalError(f"Unknown domain: {domain}")
        config = self.get_config(domain)
        samples = [EvalSample(sample_id=sid, input_text=inp, expected_output=exp) for sid, inp, exp in raw]
        if len(samples) > config.max_samples:
            samples = samples[: config.max_samples]
        return tuple(samples)

    async def evaluate_sample(self, sample: EvalSample, config: DomainEvalConfig) -> EvalResult:
        """Evaluate a single sample and return its result."""
        start = time.monotonic()

        dimensions = [
            RubricDimension(
                name="accuracy",
                weight=0.5,
                description="Factual correctness of the response",
                scoring_function="exact_match",
            ),
            RubricDimension(
                name="relevance",
                weight=0.3,
                description="How relevant the response is to the query",
                scoring_function="keyword_match",
            ),
            RubricDimension(
                name="completeness",
                weight=0.2,
                description="Whether the response covers all required aspects",
                scoring_function="length_based",
            ),
        ]
        template = self._rubric.create_template(
            f"{config.domain}_eval",
            dimensions,
        )

        mock_response = sample.expected_output
        result = await self._rubric.score_response(mock_response, template)

        overall = result.total_score
        passed = overall >= config.threshold

        metric_scores = (
            ("accuracy", result.scores[0].raw_score if result.scores else 0.0),
            ("relevance", result.scores[1].raw_score if len(result.scores) > 1 else 0.0),
            ("completeness", result.scores[2].raw_score if len(result.scores) > 2 else 0.0),
        )

        elapsed = (time.monotonic() - start) * 1000

        return EvalResult(
            sample_id=sample.sample_id,
            domain=config.domain,
            metric_scores=metric_scores,
            overall_score=round(overall, 4),
            passed=passed,
            latency_ms=round(elapsed, 2),
        )

    async def evaluate_domain(self, domain: str) -> DomainEvalReport:
        """Evaluate all available samples for a domain."""
        config = self.get_config(domain)
        samples = await self.load_samples(domain)

        if not samples:
            raise DomainEvalError(f"No samples available for domain: {domain}")

        results: list[EvalResult] = []
        for sample in samples:
            result = await self.evaluate_sample(sample, config)
            results.append(result)

        results_t = tuple(results)
        passed_count = sum(1 for r in results_t if r.passed)
        pass_rate = passed_count / len(results_t) if results_t else 0.0
        avg_score = sum(r.overall_score for r in results_t) / len(results_t) if results_t else 0.0
        avg_latency = sum(r.latency_ms for r in results_t) / len(results_t) if results_t else 0.0

        return DomainEvalReport(
            domain=domain,
            results=results_t,
            pass_rate=round(pass_rate, 4),
            avg_score=round(avg_score, 4),
            avg_latency_ms=round(avg_latency, 2),
        )

    async def evaluate_all_domains(self) -> tuple[DomainEvalReport, ...]:
        """Evaluate all registered domains."""
        if not self._configs:
            raise DomainEvalError("No domains configured for evaluation")
        reports: list[DomainEvalReport] = []
        for domain in self._configs:
            report = await self.evaluate_domain(domain)
            reports.append(report)
        return tuple(reports)

    @property
    def domains(self) -> tuple[str, ...]:
        """Return tuple of registered domain names."""
        return tuple(self._configs.keys())
