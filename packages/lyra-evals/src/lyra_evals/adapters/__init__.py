"""Public benchmark adapters — SWE-bench Pro and LoCoEval.

Each adapter bridges a canonical public corpus to our generic
``EvalRunner`` contract so that:

- Loading the corpus never requires installing the upstream harness.
- Running a corpus fits our drift-gate / snapshot pipeline unchanged.
- The emitted submission artefact is byte-compatible with the upstream
  evaluator (Scale AI for Pro, the LoCoEval oracle for conversations).
"""
from __future__ import annotations

from .loco_eval import (
    ConversationDriver,
    LoCoEvalResult,
    LoCoEvalTask,
    score_requirement_coverage,
)
from .swe_bench_pro import (
    PublicBenchmarkTask,
    SWEBenchProAdapter,
    load_swe_bench_pro,
    write_submission,
)
from .tau_bench import (
    TauBenchAdapter,
    TauBenchTask,
    TauBenchVerdict,
    load_tau_bench,
    write_tau_bench_submission,
)
from .terminal_bench_v2 import (
    TerminalBenchTaskV2,
    TerminalBenchV2Adapter,
    TerminalBenchVerdict,
    load_terminal_bench_v2,
    write_terminal_bench_v2_submission,
)

__all__ = [
    "ConversationDriver",
    "LoCoEvalResult",
    "LoCoEvalTask",
    "PublicBenchmarkTask",
    "SWEBenchProAdapter",
    "TauBenchAdapter",
    "TauBenchTask",
    "TauBenchVerdict",
    "TerminalBenchTaskV2",
    "TerminalBenchV2Adapter",
    "TerminalBenchVerdict",
    "load_swe_bench_pro",
    "load_tau_bench",
    "load_terminal_bench_v2",
    "score_requirement_coverage",
    "write_submission",
    "write_tau_bench_submission",
    "write_terminal_bench_v2_submission",
]
