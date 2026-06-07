"""
Mutation Verifier — Stability testing via input mutation.

Mutates agent inputs (permutation, noise, boundary values, missing fields)
and measures output stability. Drops in regression when semantically similar
inputs produce divergent outputs.
"""

from __future__ import annotations

import copy
import hashlib
import math
import random
import string
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Mutation types
# ---------------------------------------------------------------------------


class MutationType(str, Enum):
    """Supported mutation types for stability testing."""

    INPUT_PERMUTATION = "input_permutation"
    NOISE_INJECTION = "noise_injection"
    BOUNDARY_VALUE = "boundary_value"
    MISSING_FIELD = "missing_field"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class MutationConfig:
    """Configuration for the mutation verifier.

    Attributes
    ----------
    mutation_types:
        Which mutation strategies to apply. Default: all four.
    count:
        Number of mutated variants to generate per input (default 5).
    stability_threshold:
        Minimum similarity score before a regression is flagged (0-1, default 0.8).
    noise_scale:
        Relative magnitude of numeric noise injection (default 0.05 = 5 %).
    seed:
        Random seed for reproducibility.
    """

    mutation_types: list[MutationType] = field(
        default_factory=lambda: list(MutationType)
    )
    count: int = 5
    stability_threshold: float = 0.8
    noise_scale: float = 0.05
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("count must be >= 1")
        if not 0.0 <= self.stability_threshold <= 1.0:
            raise ValueError("stability_threshold must be in [0, 1]")
        if not 0.0 <= self.noise_scale <= 1.0:
            raise ValueError("noise_scale must be in [0, 1]")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MutatedInput:
    """A single mutated variant of an agent input.

    Attributes
    ----------
    input_data:
        The mutated input dictionary.
    mutation_type:
        Which strategy was applied.
    description:
        Human-readable description of the mutation.
    mutation_id:
        Short unique hash derived from the mutation content.
    """

    input_data: dict[str, Any]
    mutation_type: MutationType
    description: str
    mutation_id: str = ""

    def __post_init__(self) -> None:
        if not self.mutation_id:
            raw = f"{self.mutation_type.value}:{str(self.input_data)[:100]}"
            self.mutation_id = hashlib.md5(raw.encode()).hexdigest()[:12]


@dataclass
class StabilityScore:
    """Result of a stability verification.

    Attributes
    ----------
    overall:
        Mean similarity across all mutation types (0-1, 1 = perfectly stable).
    per_mutation:
        Per-mutation-type average similarity scores.
    regressions:
        List of human-readable regression messages.
    n_mutations:
        Total number of mutated outputs evaluated.
    """

    overall: float
    per_mutation: dict[str, float]
    regressions: list[str]
    n_mutations: int = 0

    @property
    def is_stable(self) -> bool:
        """True when no regressions were detected."""
        return len(self.regressions) == 0


# ---------------------------------------------------------------------------
# Mutation Verifier
# ---------------------------------------------------------------------------


class MutationVerifier:
    """Mutate agent inputs and verify output stability.

    Usage::

        verifier = MutationVerifier()
        inputs = {"task": "write a poem", "style": "haiku"}

        mutants = verifier.apply_mutations(inputs, count=5)
        outputs = [(m, await agent.run(m.input_data)) for m in mutants]

        score = verifier.verify_stability(
            original_output=await agent.run(inputs),
            mutated_outputs=outputs,
        )
        print(score.is_stable, score.regressions)
    """

    def __init__(self, config: MutationConfig | None = None) -> None:
        self.config = config or MutationConfig()
        self._rng = random.Random(self.config.seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_mutations(
        self, input_data: dict[str, Any], count: int | None = None
    ) -> list[MutatedInput]:
        """Generate *count* mutated variants of *input_data*.

        Parameters
        ----------
        input_data:
            The original agent input dictionary.
        count:
            Number of variants (falls back to ``config.count``).

        Returns
        -------
        A list of :class:`MutatedInput` instances, one per variant.
        """
        n = count or self.config.count
        types = self.config.mutation_types
        if not types:
            return []

        results: list[MutatedInput] = []
        for i in range(n):
            mt = types[i % len(types)]
            mutated = self._apply_one(mt, input_data)
            results.append(
                MutatedInput(
                    input_data=mutated,
                    mutation_type=mt,
                    description=f"{mt.value}#{i}",
                )
            )
        return results

    def verify_stability(
        self,
        original_output: Any,
        mutated_outputs: list[tuple[MutatedInput, Any]],
    ) -> StabilityScore:
        """Compare mutated outputs to the original and compute stability.

        Parameters
        ----------
        original_output:
            The agent output produced from the unmodified input.
        mutated_outputs:
            Pairs of (MutatedInput, output) from each mutant.

        Returns
        -------
        A :class:`StabilityScore` with per-type averages and regression
        alerts.
        """
        per_type: dict[str, list[float]] = {}
        regressions: list[str] = []

        for mutated_input, output in mutated_outputs:
            sim = self._similarity(original_output, output)
            mt = mutated_input.mutation_type.value
            per_type.setdefault(mt, []).append(sim)
            if sim < self.config.stability_threshold:
                regressions.append(
                    f"{mt}: {mutated_input.description} "
                    f"similarity={sim:.3f} < "
                    f"threshold={self.config.stability_threshold}"
                )

        per_mutation = {
            mt: (sum(scores) / len(scores)) if scores else 1.0
            for mt, scores in per_type.items()
        }
        overall = (
            sum(per_mutation.values()) / len(per_mutation)
            if per_mutation
            else 1.0
        )

        return StabilityScore(
            overall=overall,
            per_mutation=per_mutation,
            regressions=regressions,
            n_mutations=len(mutated_outputs),
        )

    # ------------------------------------------------------------------
    # Mutation strategies
    # ------------------------------------------------------------------

    def _apply_one(
        self, mt: MutationType, data: dict[str, Any]
    ) -> dict[str, Any]:
        if mt == MutationType.INPUT_PERMUTATION:
            return self._permute(data)
        elif mt == MutationType.NOISE_INJECTION:
            return self._inject_noise(data)
        elif mt == MutationType.BOUNDARY_VALUE:
            return self._boundary(data)
        elif mt == MutationType.MISSING_FIELD:
            return self._missing(data)
        return copy.deepcopy(data)

    def _permute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Reorder list values and shuffle dict keys that contain ordered data."""
        result = copy.deepcopy(data)
        for key in list(result.keys()):
            val = result[key]
            if isinstance(val, list):
                shuffled = list(val)
                self._rng.shuffle(shuffled)
                result[key] = shuffled
            elif isinstance(val, str) and len(val) > 10:
                # Shuffle word order in longer strings
                words = val.split()
                if len(words) > 3:
                    self._rng.shuffle(words)
                    result[key] = " ".join(words)
        return result

    def _inject_noise(self, data: dict[str, Any]) -> dict[str, Any]:
        """Add small random perturbations to numeric fields."""
        result = copy.deepcopy(data)
        for key in list(result.keys()):
            val = result[key]
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                noise = val * self.config.noise_scale * (2 * self._rng.random() - 1)
                result[key] = val + noise
            elif isinstance(val, str):
                chars = list(val)
                n = max(1, int(len(chars) * self.config.noise_scale))
                for _ in range(n):
                    idx = self._rng.randint(0, len(chars) - 1)
                    chars[idx] = self._rng.choice(string.printable)
                result[key] = "".join(chars)
        return result

    def _boundary(self, data: dict[str, Any]) -> dict[str, Any]:
        """Replace numeric values with edge cases (0, large, negative)."""
        result = copy.deepcopy(data)
        boundary_choices = [0, 10**6, -(10**6), 1, -1]
        for key in list(result.keys()):
            val = result[key]
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                result[key] = self._rng.choice(boundary_choices)
            elif isinstance(val, str) and len(val) > 0:
                # Extremely long string
                if self._rng.random() < 0.5:
                    result[key] = val * 100
                else:
                    result[key] = val[:1]
        return result

    def _missing(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove a random subset of keys from the input."""
        if not data:
            return {}
        result = copy.deepcopy(data)
        keys = list(result.keys())
        n_remove = max(1, int(len(keys) * 0.3))
        to_remove = self._rng.sample(keys, min(n_remove, len(keys)))
        for k in to_remove:
            del result[k]
        return result

    # ------------------------------------------------------------------
    # Similarity
    # ------------------------------------------------------------------

    @staticmethod
    def _similarity(a: Any, b: Any) -> float:
        """Compute a similarity score between two outputs (0-1)."""
        if type(a) is not type(b):
            return 0.0
        if isinstance(a, dict) and isinstance(b, dict):
            return MutationVerifier._dict_similarity(a, b)
        if isinstance(a, str) and isinstance(b, str):
            return MutationVerifier._string_similarity(a, b)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return MutationVerifier._numeric_similarity(a, b)
        if isinstance(a, list) and isinstance(b, list):
            return MutationVerifier._list_similarity(a, b)
        return 1.0 if a == b else 0.0

    @staticmethod
    def _string_similarity(a: str, b: str) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        # Jaccard-like word overlap
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        intersection = a_words & b_words
        union = a_words | b_words
        return len(intersection) / len(union) if union else 1.0

    @staticmethod
    def _numeric_similarity(a: float, b: float) -> float:
        if a == b:
            return 1.0
        if a == 0.0 or b == 0.0:
            return 0.0
        ratio = min(a, b) / max(a, b)
        return max(0.0, min(1.0, ratio))

    @staticmethod
    def _dict_similarity(a: dict, b: dict) -> float:
        all_keys = set(a) | set(b)
        if not all_keys:
            return 1.0
        scores = []
        for k in all_keys:
            if k in a and k in b:
                scores.append(MutationVerifier._similarity(a[k], b[k]))
            else:
                scores.append(0.0)
        return sum(scores) / len(scores)

    @staticmethod
    def _list_similarity(a: list, b: list) -> float:
        if not a and not b:
            return 1.0
        max_len = max(len(a), len(b))
        if max_len == 0:
            return 1.0
        matches = 0
        for ai in a:
            for bj in b:
                if MutationVerifier._similarity(ai, bj) > 0.8:
                    matches += 1
                    break
        return matches / max_len
