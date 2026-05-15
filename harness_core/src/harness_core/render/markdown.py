"""Markdown renderers — Trace, WitnessLattice, EvalRun → Markdown text.

Output is suitable for Pages-style co-authored documents, post-mortems,
GitHub PR descriptions, and any context where a human reads the report.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Optional

from ..eval_runner import EvalRun
from ..provenance import Witness, WitnessKind, WitnessLattice
from ..replay import ReplayEvent, ReplayEventKind, Trace


def trace_to_markdown(
    trace: Trace,
    *,
    title: Optional[str] = None,
    show_payloads: bool = True,
    max_payload_chars: int = 200,
) -> str:
    """Render a :class:`Trace` as a Markdown event log."""
    lines: list[str] = []
    title = title or f"Trace: {trace.trace_id}"
    lines.append(f"# {title}")
    lines.append("")

    stats = trace.stats()
    lines.append(f"**{stats['total']}** events, "
                 f"**{stats['issuers']}** issuers, "
                 f"**{stats['namespaces']}** namespaces.")
    lines.append("")

    if not trace.events:
        lines.append("_No events._")
        return "\n".join(lines)

    lines.append("## Events")
    lines.append("")
    for i, event in enumerate(trace.events, 1):
        ts_human = _dt.datetime.utcfromtimestamp(event.timestamp).isoformat()
        bullet = (
            f"{i}. **[{event.kind.value}]** "
            f"`{event.event_id[:12]}` "
            f"by `{event.issued_by}` at {ts_human}"
        )
        if event.namespace_id:
            bullet += f" (ns: `{event.namespace_id}`)"
        lines.append(bullet)
        if show_payloads and event.payload:
            payload_str = _format_payload(event.payload, max_chars=max_payload_chars)
            lines.append(f"   - {payload_str}")
        if event.parent_event_ids:
            parents = ", ".join(p[:8] for p in event.parent_event_ids[:3])
            lines.append(f"   - parents: `{parents}`")

    return "\n".join(lines)


def witness_lattice_to_markdown(
    lattice: WitnessLattice,
    *,
    title: Optional[str] = None,
    focus_witness_id: Optional[str] = None,
) -> str:
    """Render a :class:`WitnessLattice` (or one witness's chain) as Markdown."""
    lines: list[str] = []
    title = title or "Provenance Lattice"
    lines.append(f"# {title}")
    lines.append("")

    if focus_witness_id is not None:
        chain = lattice.ledger.trace_provenance(focus_witness_id)
        if not chain:
            lines.append(f"_Witness `{focus_witness_id[:12]}` not found._")
            return "\n".join(lines)
        lines.append(f"Provenance chain for `{focus_witness_id[:12]}`:")
        lines.append("")
        for w in chain:
            lines.append(_witness_bullet(w))
        return "\n".join(lines)

    # Full lattice summary.
    stats = lattice.ledger.stats()
    lines.append(f"**{stats['total']}** witnesses, "
                 f"**{stats['issuers']}** issuers.")
    lines.append("")
    by_kind = {k: v for k, v in stats.items() if k not in ("total", "issuers")}
    if by_kind:
        lines.append("## By Kind")
        lines.append("")
        for kind, count in sorted(by_kind.items(), key=lambda kv: -kv[1]):
            if count:
                lines.append(f"- **{kind}**: {count}")
        lines.append("")

    lines.append("## Witnesses")
    lines.append("")
    witnesses = lattice.ledger.witnesses_for()
    if not witnesses:
        lines.append("_No witnesses._")
        return "\n".join(lines)
    for w in witnesses:
        lines.append(_witness_bullet(w))

    return "\n".join(lines)


def eval_run_to_markdown(
    run: EvalRun,
    *,
    title: Optional[str] = None,
    show_failed_only: bool = False,
) -> str:
    """Render an :class:`EvalRun` as a Markdown report."""
    lines: list[str] = []
    title = title or f"Eval Run: {run.suite_id}"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- **Run ID**: `{run.run_id[:12]}`")
    lines.append(f"- **Timestamp**: "
                 f"{_dt.datetime.utcfromtimestamp(run.timestamp).isoformat()}")
    lines.append(f"- **Pass rate**: **{run.pass_rate:.1%}** "
                 f"({run.n_passed}/{len(run.results)} passed)")
    lines.append(f"- **Mean score**: **{run.mean_score:.3f}**")
    if run.total_cost_usd > 0:
        lines.append(f"- **Total cost**: ${run.total_cost_usd:.4f}")
    if run.total_duration_ms > 0:
        lines.append(f"- **Total duration**: {run.total_duration_ms:.1f} ms")
    if run.n_errors > 0:
        lines.append(f"- **⚠️  Errors**: {run.n_errors}")
    lines.append("")

    results = run.failed_cases() if show_failed_only else list(run.results)
    if show_failed_only and not results:
        lines.append("_All cases passed._ ✅")
        return "\n".join(lines)

    section_title = "Failed Cases" if show_failed_only else "Results"
    lines.append(f"## {section_title}")
    lines.append("")
    for r in results:
        icon = "✅" if r.passed else "❌"
        bullet = (
            f"- {icon} `{r.case_id}` — score **{r.score:.3f}** "
            f"({r.duration_ms:.0f}ms"
        )
        if r.cost_usd > 0:
            bullet += f", ${r.cost_usd:.4f}"
        bullet += ")"
        lines.append(bullet)
        if r.error:
            lines.append(f"  - **error**: `{r.error}`")

    return "\n".join(lines)


# --- Helpers ----------------------------------------------------------


def _witness_bullet(w: Witness) -> str:
    ts = _dt.datetime.utcfromtimestamp(w.issued_at).isoformat()
    summary = _witness_summary(w)
    base = f"- **[{w.kind.value}]** `{w.short_id()}` by `{w.issued_by}` at {ts}: {summary}"
    if w.parent_witnesses:
        parents = ", ".join(p[:8] for p in w.parent_witnesses[:3])
        base += f" (parents: `{parents}`)"
    return base


def _witness_summary(w: Witness) -> str:
    c = w.content
    if w.kind == WitnessKind.AGENT_DECISION:
        return f"action={c.get('action', '?')!r}"
    if w.kind == WitnessKind.TOOL_RESULT:
        return f"tool={c.get('tool_name', '?')!r}"
    if w.kind == WitnessKind.VERIFIER_VERDICT:
        return f"passed={c.get('passed')} severity={c.get('severity', '?')}"
    if w.kind == WitnessKind.HUMAN_APPROVAL:
        return f"approved={c.get('approved')} scope={c.get('scope', '?')!r}"
    if w.kind == WitnessKind.RETRIEVAL:
        n = len(c.get("doc_ids", []))
        q = c.get("query", "")
        return f"query={q!r} ({n} docs)"
    if w.kind == WitnessKind.INFERENCE:
        return f"claim={c.get('claim', '')!r}"
    return ""


def _format_payload(payload: dict, *, max_chars: int) -> str:
    """Render a payload dict as a compact key=value string, truncated."""
    parts: list[str] = []
    for k, v in payload.items():
        if isinstance(v, (list, tuple)) and len(v) > 5:
            v_repr = f"[{len(v)} items]"
        elif isinstance(v, dict) and len(v) > 5:
            v_repr = f"{{{len(v)} fields}}"
        else:
            v_repr = repr(v)
        if len(v_repr) > 50:
            v_repr = v_repr[:47] + "..."
        parts.append(f"{k}={v_repr}")
    rendered = "; ".join(parts)
    if len(rendered) > max_chars:
        rendered = rendered[: max_chars - 3] + "..."
    return rendered


__all__ = [
    "eval_run_to_markdown",
    "trace_to_markdown",
    "witness_lattice_to_markdown",
]
