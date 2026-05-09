"""``lyra burn optimize`` runner + renderer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table

from .optimize_rules import Finding, RULES


def optimize(sessions_root: Path) -> list[Finding]:
    if not sessions_root.exists():
        return []
    rows: list[Mapping] = []
    for sess_dir in sorted(sessions_root.iterdir()):
        if not sess_dir.is_dir():
            continue
        path = sess_dir / "turns.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("kind") != "turn":
                continue
            rows.append(row)

    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule(rows))
    return findings


def render_optimize(findings: list[Finding]) -> RenderableType:
    if not findings:
        return Panel("[green]Looking good - no waste patterns detected.[/]",
                     title="lyra burn optimize")
    t = Table(title="findings", expand=True, show_header=True,
              header_style="bold cyan")
    t.add_column("id")
    t.add_column("severity")
    t.add_column("title")
    t.add_column("detail")
    for f in findings:
        t.add_row(f.rule_id, f.severity, f.title, f.detail)
    return Panel(t, title="lyra burn optimize")
