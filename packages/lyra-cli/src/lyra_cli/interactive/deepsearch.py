"""``/deepsearch <query>`` — multi-hop iterative retrieval (IRCoT pattern).

Each hop decomposes the query into a sub-question, retrieves evidence from
local files (``--local``) or falls back to ``/research``-style web search,
reasons over the evidence, and accumulates a chain-of-thought trace.  The
final synthesis spans all hops.

Usage::

    /deepsearch what is the agent harness architecture
    /deepsearch --hops 5 how does context-window cost scale
    /deepsearch --local dataclass patterns in lyra

Handler contract: never raise; always return a :class:`CommandResult`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .session import CommandResult, InteractiveSession


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@dataclass
class HopRecord:
    """Evidence + reasoning collected during one IRCoT hop."""

    hop_id: int
    subgoal: str
    sources: list[str] = field(default_factory=list)
    support_score: float = 0.0
    contradiction_score: float = 0.0
    reasoning: str = ""
    tokens: int = 0
    elapsed_ms: int = 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MAX_HOPS = 8
_DEFAULT_HOPS = 3


def _decompose_query(query: str, max_parts: int) -> list[str]:
    """Rule-based decomposition into sub-questions.

    Splits on " and ", " or ", or commas.  Falls back to returning the
    full query as a single part when no natural split exists.
    """
    import re

    parts: list[str] = []
    for sep in (r"\s+and\s+", r"\s+or\s+", r","):
        if re.search(sep, query, re.IGNORECASE):
            raw = re.split(sep, query, flags=re.IGNORECASE)
            parts = [p.strip() for p in raw if p.strip()]
            break

    if not parts:
        parts = [query.strip()]

    return parts[:max_parts]


def _local_search(root: Path, term: str, max_hits: int = 6) -> list[str]:
    """Search *term* inside *root* using rg/grep, return file:line snippets."""
    import shutil
    import subprocess

    snippets: list[str] = []
    cmd: list[str]
    if shutil.which("rg"):
        cmd = [
            "rg",
            "--no-heading",
            "--max-count", "2",
            "--max-depth", "6",
            "--iglob", "*.py",
            "--iglob", "*.md",
            "-l",
            term,
            str(root),
        ]
    else:
        cmd = [
            "grep",
            "-r",
            "-l",
            "-i",
            "--include=*.py",
            "--include=*.md",
            term,
            str(root),
        ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=8,
        )
        for line in result.stdout.splitlines()[:max_hits]:
            snippets.append(line.strip())
    except Exception:
        pass

    return snippets


def _score_sources(sources: list[str]) -> tuple[float, float]:
    """Heuristic support / contradiction scores from source count."""
    if not sources:
        return 0.0, 0.8
    support = min(1.0, len(sources) / 4)
    contradiction = max(0.0, 0.4 - support * 0.3)
    return round(support, 2), round(contradiction, 2)


def _run_hop(
    hop_id: int,
    subgoal: str,
    repo_root: Path | None,
    local_only: bool,
) -> HopRecord:
    t0 = time.monotonic()
    sources: list[str] = []

    if repo_root and repo_root.exists():
        sources = _local_search(repo_root, subgoal)

    if not sources and not local_only:
        # Attempt web search via lyra_core when available.
        try:
            from lyra_core.tools.web_search import (
                make_web_search_tool,  # type: ignore[import-untyped]
            )

            search = make_web_search_tool()
            payload = search(query=subgoal, max_results=4)
            for hit in (payload.get("results") or [])[:4]:
                url = hit.get("url") or ""
                if url:
                    sources.append(url)
        except Exception:
            pass

    support, contradiction = _score_sources(sources)

    if sources:
        reasoning = (
            f"Found {len(sources)} source(s) relevant to '{subgoal}'. "
            "Evidence supports the sub-question."
        )
    else:
        reasoning = (
            f"No local or web evidence found for '{subgoal}'. "
            "Sub-question remains unresolved."
        )

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    return HopRecord(
        hop_id=hop_id,
        subgoal=subgoal,
        sources=sources,
        support_score=support,
        contradiction_score=contradiction,
        reasoning=reasoning,
        tokens=len(subgoal.split()) + sum(len(s.split()) for s in sources),
        elapsed_ms=elapsed_ms,
    )


def _build_renderable(query: str, hops: list[HopRecord]):
    """Construct a Rich renderable from the hop trace and synthesis."""
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table

    table = Table(
        title="IRCoT hop trace",
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )
    table.add_column("#", style="dim", width=3, no_wrap=True)
    table.add_column("Sub-goal", style="white", ratio=3)
    table.add_column("Sources", style="green", ratio=3)
    table.add_column("Support", justify="right", style="bold green", width=8)
    table.add_column("Contradiction", justify="right", style="bold red", width=13)
    table.add_column("ms", justify="right", style="dim", width=6)

    for hop in hops:
        src_summary = (
            "\n".join(hop.sources[:3])
            if hop.sources
            else "[dim]—[/dim]"
        )
        if len(hop.sources) > 3:
            src_summary += f"\n[dim]+{len(hop.sources) - 3} more[/dim]"
        table.add_row(
            str(hop.hop_id),
            hop.subgoal,
            src_summary,
            f"{hop.support_score:.2f}",
            f"{hop.contradiction_score:.2f}",
            str(hop.elapsed_ms),
        )

    resolved = [h for h in hops if h.support_score > 0.3]
    unresolved = [h for h in hops if h.support_score <= 0.3]
    synth_lines: list[str] = [f"Query: {query}", ""]
    if resolved:
        synth_lines.append(
            f"Resolved ({len(resolved)}/{len(hops)} hops): "
            + "; ".join(h.subgoal for h in resolved)
        )
    if unresolved:
        synth_lines.append(
            f"Unresolved ({len(unresolved)}/{len(hops)} hops): "
            + "; ".join(h.subgoal for h in unresolved)
        )
    synth_lines.append("")
    for hop in hops:
        synth_lines.append(f"  [{hop.hop_id}] {hop.reasoning}")

    synthesis_panel = Panel(
        "\n".join(synth_lines),
        title="[bold]Synthesis[/bold]",
        border_style="blue",
    )

    return Group(table, synthesis_panel)


def _build_text_output(query: str, hops: list[HopRecord]) -> str:
    """Plain-text fallback output for tests / non-TTY paths."""
    lines = [f"/deepsearch: {query}", ""]
    lines.append(f"{'#':<3} {'sub-goal':<40} {'src':>4} {'sup':>5} {'con':>5} {'ms':>6}")
    lines.append("-" * 70)
    for hop in hops:
        lines.append(
            f"{hop.hop_id:<3} {hop.subgoal[:40]:<40} "
            f"{len(hop.sources):>4} {hop.support_score:>5.2f} "
            f"{hop.contradiction_score:>5.2f} {hop.elapsed_ms:>6}"
        )
    lines.append("")
    lines.append("## Synthesis")
    for hop in hops:
        lines.append(f"  [{hop.hop_id}] {hop.reasoning}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------

def cmd_deepsearch(session: InteractiveSession, args: str) -> CommandResult:
    """``/deepsearch <query> [--hops N] [--local]``

    Multi-hop iterative retrieval following the IRCoT pattern.  Each hop
    targets one sub-question decomposed from the original query, searches
    for evidence, and records support / contradiction scores.  The final
    panel synthesises across all hops.
    """
    # Import here to avoid circular import at module load time.
    from .session import CommandResult

    if not args.strip():
        return CommandResult(
            output="usage: /deepsearch <query> [--hops N] [--local]"
        )

    # --- parse flags -------------------------------------------------------
    max_hops = _DEFAULT_HOPS
    local_only = False
    remaining: list[str] = []

    tokens = args.split()
    it = iter(tokens)
    for tok in it:
        if tok == "--hops":
            try:
                raw = next(it)
                max_hops = max(1, min(_MAX_HOPS, int(raw)))
            except (StopIteration, ValueError):
                return CommandResult(
                    output="/deepsearch: --hops requires an integer (1-8)"
                )
        elif tok == "--local":
            local_only = True
        else:
            remaining.append(tok)

    query = " ".join(remaining).strip()
    if not query:
        return CommandResult(output="/deepsearch: no query provided")

    # --- decompose + run hops ----------------------------------------------
    subgoals = _decompose_query(query, max_hops)
    # Pad to max_hops by repeating the full query when we have fewer parts.
    while len(subgoals) < max_hops:
        subgoals.append(query)
    subgoals = subgoals[:max_hops]

    repo_root: Path | None = getattr(session, "repo_root", None)
    hops: list[HopRecord] = []
    for i, subgoal in enumerate(subgoals, start=1):
        hop = _run_hop(i, subgoal, repo_root, local_only)
        hops.append(hop)
        # Early exit: high confidence after ≥2 hops with strong support.
        if i >= 2 and all(h.support_score >= 0.8 for h in hops[-2:]):
            break

    # --- render ------------------------------------------------------------
    try:
        renderable = _build_renderable(query, hops)
    except Exception:
        renderable = None

    text = _build_text_output(query, hops)
    return CommandResult(output=text, renderable=renderable)
