"""harness_core.render — Markdown / JSON / structured-log output renderers.

Composes :mod:`harness_core.replay`, :mod:`harness_core.provenance`,
:mod:`harness_core.eval_runner`, and :mod:`harness_core.cost` into
human-consumable reports + audit logs.

Three target formats:

    1. **Markdown** — for Pages-style co-authored documents, post-mortems,
       research reports.
    2. **JSON** — for downstream tools (dashboards, CI artefacts, log
       aggregators).
    3. **Structured log** — line-per-event, parseable by log search engines
       (Datadog / Splunk / journalctl).

Used by Polaris (research reports), Atlas-Research (synthesis writeups),
Helix-Bio (protocol + audit), Aegis-Ops (post-mortems), Orion-Code (PR
descriptions + audit), Lyra (architecture docs).
"""
from __future__ import annotations

from .json_export import (
    eval_run_to_json,
    trace_to_json,
    witness_lattice_to_json,
)
from .log_export import structured_log_lines
from .markdown import (
    eval_run_to_markdown,
    trace_to_markdown,
    witness_lattice_to_markdown,
)

__all__ = [
    "eval_run_to_json",
    "eval_run_to_markdown",
    "structured_log_lines",
    "trace_to_json",
    "trace_to_markdown",
    "witness_lattice_to_json",
    "witness_lattice_to_markdown",
]
