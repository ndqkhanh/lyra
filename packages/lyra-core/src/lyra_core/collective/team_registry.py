"""Per-team dead-end registry with noise estimation.

Extends DeadEndRegistry to provide per-team isolation and noise-level
estimation. Each team gets its own registry instance, preventing
cross-team contamination of dead-end knowledge. Noise estimation
tracks confirmation quality using the NoiseGate primitive.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from lyra_core.collective import DeadEndEntry, DeadEndRegistry


@dataclass
class NoiseEstimate:
    """Estimated noise level for a team's dead-end confirmation."""

    team_id: str
    signal_count: int = 0       # Number of independent confirmations
    noise_count: int = 0        # Number of contradictory findings
    confidence: float = 0.0     # signal / (signal + noise), clamped to [0, 1]
    last_updated: float = field(default_factory=time.time)

    @property
    def is_reliable(self) -> bool:
        """A dead-end is reliable when confidence > 0.5 with sufficient signal."""
        return self.confidence > 0.5 and self.signal_count >= 2

    @property
    def needs_more_data(self) -> bool:
        return self.signal_count + self.noise_count < 3


@dataclass
class TeamDeadEndRecord:
    """Dead-end entry scoped to a specific team."""

    entry: DeadEndEntry
    team_id: str
    noise: NoiseEstimate
    recorded_at: float = field(default_factory=time.time)


class TeamDeadEndRegistry:
    """Per-team dead-end registries with noise estimation.

    Each team gets its own DeadEndRegistry. A noise estimator
    tracks confirmation quality and can flag unreliable dead-ends.

    Usage::

        reg = TeamDeadEndRegistry()
        team_reg = reg.for_team("team-1")
        team_reg.register(DeadEndEntry(...))
        est = reg.get_noise("team-1")
    """

    def __init__(self) -> None:
        self._registries: dict[str, DeadEndRegistry] = {}
        self._noise: dict[str, NoiseEstimate] = {}
        self._records: list[TeamDeadEndRecord] = []

    def for_team(self, team_id: str) -> DeadEndRegistry:
        """Get or create the dead-end registry for a team."""
        if team_id not in self._registries:
            self._registries[team_id] = DeadEndRegistry()
            self._noise[team_id] = NoiseEstimate(team_id=team_id)
        return self._registries[team_id]

    def record_dead_end(self, team_id: str, entry: DeadEndEntry) -> TeamDeadEndRecord:
        """Record a dead-end for a team, updating noise estimates."""
        registry = self.for_team(team_id)
        registry.register(entry)

        record = TeamDeadEndRecord(
            entry=entry,
            team_id=team_id,
            noise=self._noise.get(team_id, NoiseEstimate(team_id=team_id)),
        )
        self._records.append(record)
        return record

    def confirm_signal(self, team_id: str) -> NoiseEstimate:
        """Register a confirming signal (strengthens dead-end confidence)."""
        est = self._noise.get(team_id)
        if est is None:
            est = NoiseEstimate(team_id=team_id)
            self._noise[team_id] = est
        est.signal_count += 1
        est.confidence = self._compute_confidence(est)
        est.last_updated = time.time()
        return est

    def record_noise(self, team_id: str) -> NoiseEstimate:
        """Register contradictory noise (weakens dead-end confidence)."""
        est = self._noise.get(team_id)
        if est is None:
            est = NoiseEstimate(team_id=team_id)
            self._noise[team_id] = est
        est.noise_count += 1
        est.confidence = self._compute_confidence(est)
        est.last_updated = time.time()
        return est

    def get_noise(self, team_id: str) -> NoiseEstimate | None:
        return self._noise.get(team_id)

    def is_reliable_dead_end(self, team_id: str, hypothesis: str,
                             approach: str = "") -> bool:
        """Check if a dead-end is both known AND reliably confirmed."""
        registry = self._registries.get(team_id)
        if registry is None:
            return False
        is_dead, _ = registry.is_known_dead_end(hypothesis, approach)
        if not is_dead:
            return False
        est = self._noise.get(team_id)
        if est is None:
            return False
        return est.is_reliable

    def unreliable_teams(self) -> list[str]:
        """List teams whose dead-end registries have unreliable noise estimates."""
        return [
            tid for tid, est in self._noise.items()
            if not est.is_reliable and not est.needs_more_data
        ]

    def team_count(self) -> int:
        return len(self._registries)

    def total_records(self) -> int:
        return len(self._records)

    @staticmethod
    def _compute_confidence(est: NoiseEstimate) -> float:
        total = est.signal_count + est.noise_count
        if total == 0:
            return 0.0
        return max(0.0, min(1.0, est.signal_count / total))
