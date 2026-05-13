"""
/research command — Deep Research AI Agent.

Usage:
  /research <topic>              Run full research pipeline
  /research list                 List past research sessions
  /research show <id>            Show a past report (by partial ID or topic)
  /research related <topic>      Find past sessions related to topic
"""
from __future__ import annotations


def handle_research_command(args: str, output_fn=print) -> int:
    """Handle /research subcommands. Returns exit code (0=ok, 1=error)."""
    parts = args.strip().split(None, 1)
    if not parts:
        output_fn("Usage: /research <topic> | list | show <id> | related <topic>")
        return 1

    subcommand = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if subcommand == "list":
        return _cmd_list(output_fn)
    elif subcommand == "show":
        return _cmd_show(rest, output_fn)
    elif subcommand == "related":
        return _cmd_related(rest, output_fn)
    else:
        # Treat entire args as topic
        topic = args.strip()
        return _cmd_research(topic, output_fn)


def _cmd_research(topic: str, output_fn=print) -> int:
    """Run the full research pipeline for a topic."""
    from lyra_research.orchestrator import ResearchOrchestrator, ResearchProgress

    def on_progress(p: ResearchProgress) -> None:
        bar = "█" * p.current_step + "░" * (10 - p.current_step)
        output_fn(f"[{bar}] Step {p.current_step}/10: {p.current_step_name}")

    output_fn(f"\n🔬 Starting deep research: {topic}\n")
    orchestrator = ResearchOrchestrator()
    progress = orchestrator.research(topic, progress_callback=on_progress)

    if progress.error:
        output_fn(f"\n❌ Research failed: {progress.error}")
        return 1

    output_fn(f"\n✅ Research complete in {progress.elapsed_seconds:.1f}s")
    output_fn(
        f"   Sources analyzed: {progress.papers_analyzed} papers, "
        f"{progress.repos_analyzed} repos"
    )
    output_fn(f"   Gaps found: {progress.gaps_found}")
    if progress.report:
        output_fn(f"   Quality score: {progress.report.quality_score:.0%}")
        output_fn(f"\n--- Report Preview ---\n")
        md = progress.report.to_markdown()
        output_fn(md[:2000] + ("\n... (truncated)" if len(md) > 2000 else ""))
    return 0


def _cmd_list(output_fn=print) -> int:
    """List past research sessions from the case bank."""
    from lyra_research.memory import SessionCaseBank

    bank = SessionCaseBank()
    cases = bank.get_all()
    if not cases:
        output_fn("No past research sessions found.")
        return 0
    output_fn(f"\n{'ID[:8]':<10} {'Topic':<40} {'Quality':>8} {'Sources':>8}")
    output_fn("-" * 70)
    for c in sorted(cases, key=lambda x: x.created_at, reverse=True)[:20]:
        output_fn(
            f"{c.id[:8]:<10} {c.topic[:38]:<40} "
            f"{c.quality_score:>7.0%} {c.sources_found:>8}"
        )
    return 0


def _cmd_show(query: str, output_fn=print) -> int:
    """Show a past research report by partial ID or topic keyword."""
    from pathlib import Path

    from lyra_research.memory import SessionCaseBank

    bank = SessionCaseBank()
    cases = bank.get_all()
    match = next(
        (
            c
            for c in cases
            if c.id.startswith(query) or query.lower() in c.topic.lower()
        ),
        None,
    )
    if not match:
        output_fn(f"No research session found matching: {query}")
        return 1
    output_fn(f"\nTopic: {match.topic}")
    output_fn(f"Quality: {match.quality_score:.0%} | Sources: {match.sources_found}")
    output_fn(f"Date: {match.created_at.strftime('%Y-%m-%d %H:%M')}")
    if match.report_path and Path(match.report_path).exists():
        output_fn(Path(match.report_path).read_text()[:3000])
    else:
        output_fn(f"\nSummary:\n{match.report_summary}")
    return 0


def _cmd_related(topic: str, output_fn=print) -> int:
    """Find past research sessions related to a topic."""
    from lyra_research.memory import SessionCaseBank

    bank = SessionCaseBank()
    related = bank.find_related(topic, top_k=5)
    if not related:
        output_fn(f"No related research found for: {topic}")
        return 0
    output_fn(f"\nRelated research sessions for '{topic}':")
    for c in related:
        output_fn(
            f"  [{c.id[:8]}] {c.topic} "
            f"(quality: {c.quality_score:.0%}, {c.sources_found} sources)"
        )
    return 0
