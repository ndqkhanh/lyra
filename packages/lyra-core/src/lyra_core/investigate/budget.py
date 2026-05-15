"""Investigation budget — turn / bash / bytes / wall-clock caps.

DCI-Agent-Lite caps a run at 300 turns. The wider DCI paper notes
that long-tail trajectories blow past simple turn caps (RQ4 — corpus
scale), so we add three finer guards Lyra's permissions grammar can
enforce: bash-call count, total bytes read, and wall-clock seconds.

The budget is a pure value object — it does not enforce itself.
The investigation runner is the single writer; it calls
:meth:`InvestigationBudget.check` between tool calls and raises
:class:`BudgetExceeded` on the first breach. Tests can fast-forward
a budget by passing an injected ``clock``.

Cite: arXiv:2605.05242 §3.5; DCI-Agent-Lite README "Turn budget (max 300)".
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    """Raised when an investigation exceeds any one budget axis.

    The attribute :attr:`axis` names which axis tripped (``"turns"``,
    ``"bash_calls"``, ``"bytes_read"``, or ``"wall_clock_s"``) so the
    runner can record a clean stop reason in the trajectory ledger.
    """

    def __init__(self, axis: str, used: float, cap: float) -> None:
        super().__init__(
            f"investigation budget exceeded on {axis}: used {used} > cap {cap}"
        )
        self.axis = axis
        self.used = used
        self.cap = cap


Clock = Callable[[], float]


@dataclass
class InvestigationBudget:
    """Per-axis caps for one investigation.

    Defaults mirror DCI-Agent-Lite's 300-turn ceiling plus three
    safety nets the paper does not impose but Lyra's permissions
    grammar already supports.

    Attributes:
        max_turns: Hard cap on agent turns (one LLM call + tool call
            = one turn). Matches DCI-Agent-Lite's default.
        max_bash_calls: Independent cap on the bash tool specifically;
            useful when the agent is iterating on a noisy pattern.
        max_bytes_read: Sum of bytes returned by all read / cat / head
            calls. Bounds the context budget regardless of the level0-4
            compactor setting.
        wall_clock_s: Hard real-time ceiling. The 30-minute default is
            DCI's typical BrowseComp-Plus run.
        clock: Source of "now" — defaults to :func:`time.monotonic` so
            tests can inject a fake.
    """

    max_turns: int = 300
    max_bash_calls: int = 200
    max_bytes_read: int = 100_000_000
    wall_clock_s: float = 1800.0
    clock: Clock = field(default=time.monotonic)

    _turns: int = field(default=0, init=False)
    _bash_calls: int = field(default=0, init=False)
    _bytes_read: int = field(default=0, init=False)
    _started_at: float | None = field(default=None, init=False)

    def start(self) -> None:
        """Mark the investigation as started. Idempotent."""
        if self._started_at is None:
            self._started_at = self.clock()

    def record_turn(self) -> None:
        """Tick one turn. Raises :class:`BudgetExceeded` on cap breach."""
        self.start()
        self._turns += 1
        if self._turns > self.max_turns:
            raise BudgetExceeded("turns", self._turns, self.max_turns)

    def record_bash_call(self) -> None:
        """Tick one bash invocation."""
        self.start()
        self._bash_calls += 1
        if self._bash_calls > self.max_bash_calls:
            raise BudgetExceeded("bash_calls", self._bash_calls, self.max_bash_calls)

    def record_bytes(self, n: int) -> None:
        """Account *n* bytes read by a read/cat/head call."""
        self.start()
        if n < 0:
            raise ValueError(f"bytes read must be non-negative, got {n}")
        self._bytes_read += n
        if self._bytes_read > self.max_bytes_read:
            raise BudgetExceeded("bytes_read", self._bytes_read, self.max_bytes_read)

    def check_wall_clock(self) -> None:
        """Raise if the wall-clock budget is exhausted. Cheap; call often."""
        if self._started_at is None:
            return
        elapsed = self.clock() - self._started_at
        if elapsed > self.wall_clock_s:
            raise BudgetExceeded("wall_clock_s", elapsed, self.wall_clock_s)

    @property
    def turns_used(self) -> int:
        return self._turns

    @property
    def bash_calls_used(self) -> int:
        return self._bash_calls

    @property
    def bytes_read_used(self) -> int:
        return self._bytes_read

    @property
    def wall_clock_used(self) -> float:
        if self._started_at is None:
            return 0.0
        return self.clock() - self._started_at


__all__ = ["BudgetExceeded", "Clock", "InvestigationBudget"]
