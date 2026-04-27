"""Retrospective artifact builder (Markdown)."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def build_retro_artifact(
    *,
    session_id: str,
    events: Iterable[Mapping[str, Any]],
    plan: Mapping[str, Any] | None,
    verdict: str,
    artifact_index: dict[str, str],
) -> str:
    lines = [f"# Retro for {session_id}", ""]

    # Plan section
    lines.append("## Plan")
    if plan:
        title = plan.get("title", "(untitled)")
        lines.append(f"- Title: {title}")
        feats = plan.get("feature_items") or []
        if feats:
            lines.append("- Features:")
            for f in feats:
                skill = f.get("skill", "?")
                desc = f.get("description", "")
                lines.append(f"  - `{skill}`: {desc}")
        tests = plan.get("acceptance_tests") or []
        if tests:
            lines.append("- Acceptance tests:")
            for t in tests:
                lines.append(f"  - `{t}`")
    else:
        lines.append("(no plan recorded)")
    lines.append("")

    # Timeline
    lines.append("## Timeline")
    for ev in events:
        kind = ev.get("kind", "?")
        payload = ev.get("payload") or {}
        if kind == "tool.call":
            name = payload.get("name", "?")
            args = payload.get("args", {})
            lines.append(f"- `tool.call` **{name}** args={args!r}")
        elif kind == "tool.result":
            ok = payload.get("ok", None)
            lines.append(f"- `tool.result` ok={ok}")
        else:
            lines.append(f"- `{kind}`")
    lines.append("")

    # Verdict
    lines.append("## Verdict")
    lines.append(f"- Final: **{verdict}**")
    lines.append("")

    # Artifacts
    lines.append("## Artifacts")
    if artifact_index:
        for name, digest in artifact_index.items():
            lines.append(f"- `{name}`: {digest}")
    else:
        lines.append("(no artifact hashes recorded)")
    lines.append("")

    return "\n".join(lines)
