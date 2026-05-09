"""Contamination guard for public benchmarks.

The landscape study (``docs/roadmap-v1.5-v2.md`` §0.1) documents the
drop from 80.9% (SWE-bench Verified) to 45.9% (SWE-bench Pro) for the
same Claude Opus 4.5 checkpoint — Verified pre-dates the model's training
cutoff and is contaminated. Lyra refuses to evaluate on a corpus
whose cutoff is on or before the model's training cutoff unless the
operator explicitly opts in via ``--allow-contaminated``.

Policy in one sentence: **fail-closed**. If we don't know the model's
training cutoff, we assume contamination. If the dates tie, we assume
contamination. Operators can always override; we just force them to
acknowledge the trade-off in writing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


class ContaminationError(RuntimeError):
    """Raised when the guard refuses a run."""


@dataclass
class ContaminationGuard:
    """Refuse-by-default gate between a model and a corpus.

    ``check()`` either returns silently (clean run), returns with a warning
    attached (opt-in contaminated run), or raises ``ContaminationError``
    (refusal). Warnings flow back into the ``Report`` so ``lyra retro``
    can surface them for the operator and reviewers.
    """

    corpus_name: str
    corpus_cutoff: date
    model_name: str
    model_training_cutoff: date | None
    allow_contaminated: bool = False
    warnings: list[str] = field(default_factory=list)

    def check(self) -> None:
        if self.model_training_cutoff is None:
            self._handle_unknown_cutoff()
            return

        if self.corpus_cutoff <= self.model_training_cutoff:
            self._handle_contaminated()
            return

    def _handle_unknown_cutoff(self) -> None:
        message = (
            f"unknown training cutoff for model {self.model_name!r}; "
            f"refusing to attest a clean run on corpus {self.corpus_name!r}"
        )
        if not self.allow_contaminated:
            raise ContaminationError(message)
        self.warnings.append(
            f"allow_contaminated=True: {message}; record surfaced in retro"
        )

    def _handle_contaminated(self) -> None:
        message = (
            f"corpus {self.corpus_name!r} (cutoff {self.corpus_cutoff.isoformat()}) "
            f"is on or before model {self.model_name!r} training cutoff "
            f"({self.model_training_cutoff.isoformat() if self.model_training_cutoff else 'unknown'}); "
            f"contaminated"
        )
        if not self.allow_contaminated:
            raise ContaminationError(message)
        self.warnings.append(
            f"allow_contaminated=True: {message}; record surfaced in retro"
        )
