"""Stagnation-Stop Detection (Plan 33.1.2 / CheetahClaws).

Detect when the agent emits the same summary N consecutive times
(whitespace-normalized). Prevents infinite loops and wasted compute.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class StagnationResult:
    stagnated: bool
    reason: str = ""
    repeated_output: str = ""
    consecutive_count: int = 0


class StagnationDetector:
    """Detect agent loop stagnation via consecutive identical outputs.

    When the model emits the same normalized output for `max_repeats`
    consecutive iterations, the loop is considered stagnated.
    """

    def __init__(self, max_repeats: int = 3) -> None:
        if max_repeats < 2:
            raise ValueError("max_repeats must be >= 2")
        self.max_repeats = max_repeats
        self._history: deque[str] = deque(maxlen=max_repeats)
        self._total_checks: int = 0
        self._stagnation_count: int = 0

    def check(self, output: str) -> StagnationResult:
        normalized = self._normalize(output)
        self._history.append(normalized)
        self._total_checks += 1

        if len(self._history) < self.max_repeats:
            return StagnationResult(stagnated=False)

        if len(set(self._history)) == 1:
            self._stagnation_count += 1
            return StagnationResult(
                stagnated=True,
                reason=f"Same output repeated {self.max_repeats} consecutive times",
                repeated_output=output[:200],
                consecutive_count=self.max_repeats,
            )

        return StagnationResult(stagnated=False)

    def reset(self) -> None:
        self._history.clear()

    def record_different_output(self, output: str) -> None:
        """Feed a non-identical output to break a potential chain without
        triggering a full stagnation check."""
        self._history.append(self._normalize(output))

    @property
    def stagnation_rate(self) -> float:
        if self._total_checks == 0:
            return 0.0
        return self._stagnation_count / self._total_checks

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.split())
