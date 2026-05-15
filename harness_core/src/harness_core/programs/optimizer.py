"""Bootstrap-few-shot optimizer for :class:`MultiHopProgram`.

DSPy's canonical compilation step. Walk the trainset, run the program on each
example, keep the top-k high-scoring trajectories as demonstrations, return
a new program with those demonstrations attached.

Future variants (MIPROv2-style joint optimisation, BootstrapFinetune for
parameter updates) plug in via the same compile interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .multi_hop_program import (
    Demonstration,
    Example,
    MultiHopProgram,
    ProgramOutput,
)


_EvalFn = Callable[[Example, ProgramOutput], float]


@dataclass
class BootstrapFewShot:
    """Few-shot demonstration optimizer.

    The compile step:

        1. For each example in the trainset, run the program (uncompiled).
        2. Score the (example, output) with ``eval_fn`` ∈ [0, 1].
        3. Keep examples scoring ≥ ``min_score`` as demonstration candidates.
        4. Sort by score descending; keep the top ``max_bootstrapped_demos``.
        5. Return a new program with those demonstrations attached.

    Stable + deterministic given the same trainset + program + eval_fn.

    >>> from harness_core.programs import MultiHopProgram, Signature
    >>> from harness_core.routing import BELLERouter
    >>> from harness_core.multi_hop import (
    ...     SelfAskOperator, IRCoTOperator, StubLLM, StubRetriever,
    ... )
    >>> from harness_core.pipeline import MultiHopPipeline
    """

    max_bootstrapped_demos: int = 4
    min_score: float = 0.5
    skip_failed_completions: bool = True

    def __post_init__(self) -> None:
        if self.max_bootstrapped_demos < 0:
            raise ValueError(
                f"max_bootstrapped_demos must be >= 0, got {self.max_bootstrapped_demos}"
            )
        if not 0.0 <= self.min_score <= 1.0:
            raise ValueError(
                f"min_score must be in [0, 1], got {self.min_score}"
            )

    def compile(
        self,
        *,
        program: MultiHopProgram,
        trainset: Iterable[Example],
        eval_fn: _EvalFn,
    ) -> MultiHopProgram:
        """Compile a program by bootstrapping demonstrations from the trainset."""
        candidates: list[Demonstration] = []
        for ex in trainset:
            try:
                out = program(**ex.inputs)
            except Exception:
                # If running the program raises, skip; production deployments
                # log this for debugging.
                continue

            if self.skip_failed_completions and not out.completed:
                continue

            score = eval_fn(ex, out)
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"eval_fn returned out-of-range score: {score}")
            if score < self.min_score:
                continue

            # Capture the operator's reasoning trace for the demonstration.
            trace = self._extract_trace(out)
            candidates.append(
                Demonstration(
                    example=ex,
                    trace=trace,
                    score=score,
                    operator_used=out.pipeline_result.operator_used,
                )
            )

        # Sort by score desc, then by trace length asc (prefer concise demos).
        candidates.sort(key=lambda d: (-d.score, len(d.trace)))
        kept = candidates[: self.max_bootstrapped_demos]
        return program.with_demonstrations(kept)

    @staticmethod
    def _extract_trace(output: ProgramOutput) -> tuple[str, ...]:
        """Extract a compact trace from the pipeline result."""
        steps = [s.value for s in output.pipeline_result.steps]
        return tuple(steps)


__all__ = ["BootstrapFewShot"]
