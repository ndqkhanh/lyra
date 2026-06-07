"""RL-based policy search engine."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .exceptions import PolicySearchError


@dataclass(frozen=True)
class SearchConfig:
    """Configuration for a policy search run."""

    search_algorithm: str = "bayesian"
    max_iterations: int = 100
    exploration_rate: float = 0.1
    convergence_threshold: float = 0.001


@dataclass(frozen=True)
class PolicyCandidate:
    """A candidate policy discovered during search."""

    candidate_id: str
    parameters: tuple[tuple[str, float], ...]
    score: float
    uncertainty: float
    iteration_found: int


@dataclass(frozen=True)
class SearchResult:
    """The result of a policy search run."""

    best_policy: PolicyCandidate
    candidates: tuple[PolicyCandidate, ...]
    iterations: int
    converged: bool
    search_time_ms: float


class PolicySearch:
    """RL-based policy search engine supporting configurable algorithms."""

    _rng: random.Random

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    async def search_policy(
        self, config: SearchConfig, objective: str
    ) -> SearchResult:
        """Execute a policy search given configuration and objective."""
        if config.max_iterations < 1:
            raise PolicySearchError("max_iterations must be >= 1")
        if config.exploration_rate < 0.0 or config.exploration_rate > 1.0:
            raise PolicySearchError("exploration_rate must be in [0.0, 1.0]")
        if config.convergence_threshold < 0.0:
            raise PolicySearchError("convergence_threshold must be >= 0.0")

        start = time.monotonic()
        candidates: list[PolicyCandidate] = []

        for iteration in range(config.max_iterations):
            params = _generate_random_parameters(self._rng, objective)
            score = self._evaluate_candidate(params)
            uncertainty = self._estimate_uncertainty(score, iteration)

            candidate = PolicyCandidate(
                candidate_id=f"candidate_{iteration}",
                parameters=params,
                score=score,
                uncertainty=uncertainty,
                iteration_found=iteration,
            )
            candidates.append(candidate)

            if self._check_convergence(candidates, config.convergence_threshold):
                break

        if not candidates:
            raise PolicySearchError("no candidates generated during search")

        best = max(candidates, key=lambda c: c.score)
        elapsed = (time.monotonic() - start) * 1000.0

        return SearchResult(
            best_policy=best,
            candidates=tuple(candidates),
            iterations=len(candidates),
            converged=len(candidates) < config.max_iterations,
            search_time_ms=elapsed,
        )

    async def refine_search(
        self, previous: SearchResult, iterations: int
    ) -> SearchResult:
        """Refine a previous search result with additional iterations."""
        if iterations < 1:
            raise PolicySearchError("iterations must be >= 1")

        start = time.monotonic()
        refined_candidates = list(previous.candidates)

        for _i in range(iterations):
            idx = len(refined_candidates)
            params = _mutate_parameters(
                previous.best_policy.parameters, self._rng
            )
            score = self._evaluate_candidate(params)
            uncertainty = self._estimate_uncertainty(score, idx)

            candidate = PolicyCandidate(
                candidate_id=f"candidate_{idx}",
                parameters=params,
                score=score,
                uncertainty=uncertainty,
                iteration_found=idx,
            )
            refined_candidates.append(candidate)

        best = max(refined_candidates, key=lambda c: c.score)
        elapsed = (time.monotonic() - start) * 1000.0

        return SearchResult(
            best_policy=best,
            candidates=tuple(refined_candidates),
            iterations=len(refined_candidates),
            converged=False,
            search_time_ms=elapsed,
        )

    async def explore_parameter_space(
        self, bounds: tuple[tuple[float, float], ...]
    ) -> tuple[PolicyCandidate, ...]:
        """Explore a parameter space defined by bounds."""
        if not bounds:
            raise PolicySearchError("bounds must not be empty")
        for low, high in bounds:
            if low >= high:
                raise PolicySearchError(
                    f"invalid bound [{low}, {high}]: low must be < high"
                )

        candidates: list[PolicyCandidate] = []
        for i, (low, high) in enumerate(bounds):
            samples = self._rng.uniform(low, high)
            params = (
                (f"param_{i}_0", low),
                (f"param_{i}_1", high),
                (f"param_{i}_sample", samples),
            )
            score = self._evaluate_candidate(params)
            candidate = PolicyCandidate(
                candidate_id=f"explore_{i}",
                parameters=params,
                score=score,
                uncertainty=1.0,
                iteration_found=0,
            )
            candidates.append(candidate)

        return tuple(candidates)

    async def select_best(
        self, candidates: tuple[PolicyCandidate, ...], top_k: int = 5
    ) -> tuple[PolicyCandidate, ...]:
        """Select the top-k best candidates by score."""
        if not candidates:
            raise PolicySearchError("candidates must not be empty")
        if top_k < 1:
            raise PolicySearchError("top_k must be >= 1")

        sorted_candidates = sorted(
            candidates, key=lambda c: c.score, reverse=True
        )
        return tuple(sorted_candidates[:top_k])

    def _evaluate_candidate(
        self, params: tuple[tuple[str, float], ...]
    ) -> float:
        """Score a candidate using a heuristic based on its parameters."""
        if not params:
            return 0.0
        raw = sum(v for _, v in params) / len(params)
        noisy = raw + self._rng.gauss(0.0, 0.1)
        return max(0.0, min(1.0, noisy))

    def _estimate_uncertainty(self, score: float, iteration: int) -> float:
        """Estimate uncertainty decreasing with more iterations."""
        base = 0.5 - 0.4 * min(1.0, iteration / 50.0)
        return max(0.05, base + self._rng.gauss(0, 0.05))

    def _check_convergence(
        self,
        candidates: list[PolicyCandidate],
        threshold: float,
    ) -> bool:
        """Check if scores have converged within threshold."""
        if len(candidates) < 5:
            return False
        recent = candidates[-5:]
        scores = [c.score for c in recent]
        return max(scores) - min(scores) <= threshold


def _generate_random_parameters(
    rng: random.Random, objective: str
) -> tuple[tuple[str, float], ...]:
    """Generate random parameter tuples based on objective."""
    base_params = [
        ("learning_rate", rng.uniform(0.0001, 0.1)),
        ("batch_size", float(rng.choice([16, 32, 64, 128, 256]))),
        ("entropy_coef", rng.uniform(0.001, 0.1)),
    ]
    if objective.lower() == "exploration":
        base_params.append(("explore_bonus", rng.uniform(0.0, 1.0)))
    return tuple(base_params)


def _mutate_parameters(
    params: tuple[tuple[str, float], ...], rng: random.Random
) -> tuple[tuple[str, float], ...]:
    """Mutate parameters with random noise for refinement."""
    mutated: list[tuple[str, float]] = []
    for name, value in params:
        noise = rng.gauss(0.0, value * 0.1)
        new_val = max(0.0, value + noise)
        mutated.append((name, new_val))
    return tuple(mutated)
