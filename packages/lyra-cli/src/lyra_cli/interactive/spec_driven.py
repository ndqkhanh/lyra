"""Spec-Driven Development commands (Wave E).

Three top-level REPL commands based on BMAD / Spec-Driven Development
(doc 321):

* :func:`cmd_specify`  — generate a structured spec with hidden-question
  detection.
* :func:`cmd_bmad`     — invoke a BMAD agent persona (analyst / pm /
  architect / dev / qa / writer).
* :func:`cmd_tasks`    — split a plan or spec into independently testable
  task chunks.

Every handler matches the ``SlashHandler`` contract
``(InteractiveSession, args: str) -> CommandResult`` so they slot into
``COMMAND_REGISTRY`` next to ``/skills``, ``/cron``, etc.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # InteractiveSession imported lazily

# ---------------------------------------------------------------------------
# Result factory (lazy import — mirrors v311_commands.py)
# ---------------------------------------------------------------------------


def _result_class() -> type:
    try:
        from .session import CommandResult  # type: ignore[attr-defined]
        return CommandResult
    except Exception:
        from dataclasses import dataclass

        @dataclass
        class _Stub:
            output: str = ""
            renderable: Any | None = None
            should_exit: bool = False
            clear_screen: bool = False
            new_mode: str | None = None

        return _Stub


def _ok(text: str, renderable: Any | None = None) -> Any:
    cls = _result_class()
    return cls(output=text, renderable=renderable)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert *text* to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unnamed"


def _specs_dir(session: Any) -> Path:
    """Return the directory where spec files are written."""
    try:
        if session.repo_root:
            return Path(session.repo_root) / ".lyra" / "specs"
    except AttributeError:
        pass
    return Path.home() / ".lyra" / "specs"


def _tasks_dir(session: Any) -> Path:
    """Return the directory where task files are written."""
    try:
        if session.repo_root:
            return Path(session.repo_root) / ".lyra"
    except AttributeError:
        pass
    return Path.home() / ".lyra"


def _session_model(session: Any) -> str:
    try:
        return str(session.model)
    except AttributeError:
        return "lyra"


# ---------------------------------------------------------------------------
# cmd_specify
# ---------------------------------------------------------------------------

_SPEC_TEMPLATE = """\
# Feature Spec: {feature}

**Date:** {date}
**Author:** {author}

---

## Background

> Describe the context and motivation for this feature.

<background goes here>

---

## Hidden Questions

The following ambiguities must be resolved before implementation begins:

- **Who can {feature}?**  Which user roles / permissions are involved?
- **What happens when the operation fails mid-way?**  Partial state, rollback?
- **What state transitions are valid?**  What states can this feature transition from/to?
- **What are the failure modes?**  Network errors, timeouts, invalid input?
- **What are the edge cases?**  Empty inputs, concurrent access, large data sets?
- **Is there an existing system this replaces or integrates with?**

---

## Acceptance Criteria

- [ ] AC-1: <describe criterion>
- [ ] AC-2: <describe criterion>
- [ ] AC-3: <describe criterion>

---

## Out of Scope

The following are explicitly excluded from this spec:

- <item not in scope>

---

## Implementation Notes

- Preferred language/framework: <fill in>
- Key data models: <fill in>
- External dependencies: <fill in>
- Performance targets: <fill in>
"""


def cmd_specify(session: Any, args: str) -> Any:
    """Generate a structured spec with hidden-question detection.

    Parameters
    ----------
    session:
        Active :class:`~lyra_cli.interactive.session.InteractiveSession`.
    args:
        Topic or feature name for the spec.

    Returns
    -------
    CommandResult
        Always returns a result; never raises.
    """
    topic = (args or "").strip()
    if not topic:
        return _ok("usage: /specify <feature-name>")

    slug = _slugify(topic)
    today = datetime.date.today().isoformat()
    author = _session_model(session)

    content = _SPEC_TEMPLATE.format(feature=topic, date=today, author=author)

    out_dir = _specs_dir(session)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"spec-{slug}.md"

    if dest.exists():
        return _ok(
            f"spec already exists: {dest}\n"
            f"delete or rename it before creating a new one."
        )

    dest.write_text(content)

    try:
        from rich.panel import Panel

        renderable = Panel(
            f"[bold cyan]{dest}[/bold cyan]\n\n"
            f"Edit the spec, fill in the Hidden Questions section, then\n"
            f"run [bold]/tasks --from-spec {dest.name}[/bold] to split into tasks.",
            title="[bold]Spec created[/bold]",
            border_style="green",
        )
    except Exception:
        renderable = None

    return _ok(
        f"spec written to: {dest}\n"
        f"next: edit the spec, answer the hidden questions, then run "
        f"`/tasks --from-spec {dest.name}`.",
        renderable=renderable,
    )


# ---------------------------------------------------------------------------
# cmd_bmad
# ---------------------------------------------------------------------------

_BMAD_ROLES: dict[str, str] = {
    "analyst": "Research Brief",
    "pm": "Product Requirements Document",
    "architect": "Architecture Decision Record",
    "dev": "Implementation Checklist",
    "qa": "Acceptance Criteria & Test Matrix",
    "writer": "Documentation Outline",
}

_BMAD_TEMPLATES: dict[str, str] = {
    "analyst": """\
## Research Brief: {task}

### Background
> What is the current state of things? Why does this matter?

<background>

### Key Findings
1. Finding one
2. Finding two

### Open Questions
- Question A
- Question B

### Recommended Next Steps
1. Step one
2. Step two
""",
    "pm": """\
## PRD: {task}

### Overview
> One-paragraph description of the feature and its value.

<overview>

### User Stories
- As a **<user>**, I want **<capability>** so that **<benefit>**.
- As a **<user>**, I want **<capability>** so that **<benefit>**.

### Epics
1. **Epic 1:** <title> — <description>
2. **Epic 2:** <title> — <description>

### Success Metrics
- Metric 1: <target>
- Metric 2: <target>
""",
    "architect": """\
## ADR: {task}

### Status
Proposed

### Context
> What is the problem that needs to be solved?

<context>

### Decision
> What was decided?

<decision>

### Consequences
**Positive:**
- Consequence A

**Negative:**
- Consequence B

### Alternatives Considered
1. **Alternative A** — rejected because <reason>
2. **Alternative B** — rejected because <reason>
""",
    "dev": """\
## Implementation Checklist: {task}

### Files to Change
- [ ] `<path/to/file.py>` — <what to change>
- [ ] `<path/to/test.py>` — <what to add>

### Test Plan
- [ ] Unit test: <scenario>
- [ ] Integration test: <scenario>

### Done Criteria
- [ ] All tests pass
- [ ] No regressions in adjacent functionality
- [ ] PR approved and merged
""",
    "qa": """\
## Acceptance Criteria & Test Matrix: {task}

### Acceptance Criteria
- [ ] AC-1: <criterion>
- [ ] AC-2: <criterion>

### Test Matrix

| Scenario | Input | Expected Output | Type |
|----------|-------|-----------------|------|
| Happy path | <input> | <output> | positive |
| Edge case | <input> | <output> | boundary |
| Error case | <input> | <error message> | negative |

### Out of Scope
- <scenario not tested here>
""",
    "writer": """\
## Documentation Outline: {task}

### Sections
1. Introduction / Overview
2. Prerequisites
3. Quick Start
4. Detailed Usage
5. Configuration Reference
6. Troubleshooting
7. FAQ

### Code Examples Needed
- Example 1: <scenario>
- Example 2: <scenario>

### Glossary Terms
- **Term A**: definition
- **Term B**: definition
""",
}

_BMAD_USAGE = """\
/bmad — BMAD agent personas.

  /bmad analyst  <task>     Research brief: background, findings, open questions
  /bmad pm       <feature>  PRD: overview, user stories, epics
  /bmad architect <comp>    ADR: context, decision, consequences, alternatives
  /bmad dev      <task>     Implementation checklist: files, test plan, done criteria
  /bmad qa       <feature>  Acceptance criteria + test matrix
  /bmad writer   <topic>    Documentation outline: sections, examples, glossary

Example: /bmad pm "user authentication with OAuth"
"""


def cmd_bmad(session: Any, args: str) -> Any:
    """Invoke a BMAD agent persona.

    Parameters
    ----------
    session:
        Active :class:`~lyra_cli.interactive.session.InteractiveSession`.
    args:
        ``<role> <task>``  e.g. ``analyst "OAuth refresh flow"``.

    Returns
    -------
    CommandResult
        Always returns a result; never raises.
    """
    raw = (args or "").strip()
    if not raw:
        return _ok(_BMAD_USAGE)

    parts = raw.split(maxsplit=1)
    role = parts[0].lower()
    task = parts[1].strip() if len(parts) > 1 else ""

    if role not in _BMAD_ROLES:
        known = ", ".join(_BMAD_ROLES.keys())
        return _ok(
            f"unknown role {role!r}.  known roles: {known}\n\n{_BMAD_USAGE}"
        )

    if not task:
        return _ok(f"usage: /bmad {role} <task-description>")

    doc_title = _BMAD_ROLES[role]
    body = _BMAD_TEMPLATES[role].format(task=task)

    try:
        from rich.panel import Panel

        renderable = Panel(
            body,
            title=f"[bold cyan]{doc_title}[/bold cyan]",
            subtitle=f"[dim]role={role}  task={task!r}[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    except Exception:
        renderable = None

    output = f"=== {doc_title}: {task} ===\n\n{body}"
    return _ok(output, renderable=renderable)


# ---------------------------------------------------------------------------
# cmd_tasks
# ---------------------------------------------------------------------------

_TASK_SIZES = ("S", "M", "L")


def _estimate_size(description: str) -> str:
    """Heuristic size estimate based on description length."""
    words = len(description.split())
    if words < 12:
        return "S"
    if words < 30:
        return "M"
    return "L"


def _parse_spec_tasks(content: str) -> list[dict[str, str]]:
    """Extract task candidates from a spec file."""
    tasks: list[dict[str, str]] = []
    task_id = 1

    # Pull from Acceptance Criteria checkboxes
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            desc = stripped[len("- [ ]"):].strip()
            if not desc:
                continue
            tasks.append(
                {
                    "id": f"T{task_id:03d}",
                    "description": desc,
                    "acceptance": f"Criterion satisfied: {desc}",
                    "size": _estimate_size(desc),
                    "deps": "—",
                }
            )
            task_id += 1

    # Also pull numbered list items from Implementation Notes
    in_impl = False
    for line in content.splitlines():
        if line.strip().startswith("## Implementation"):
            in_impl = True
            continue
        if in_impl and line.startswith("## "):
            in_impl = False
        if in_impl:
            m = re.match(r"^\s*\d+\.\s+(.+)", line)
            if m:
                desc = m.group(1).strip()
                tasks.append(
                    {
                        "id": f"T{task_id:03d}",
                        "description": desc,
                        "acceptance": f"Implemented: {desc}",
                        "size": _estimate_size(desc),
                        "deps": f"T{task_id - 1:03d}" if task_id > 1 else "—",
                    }
                )
                task_id += 1

    return tasks


def _parse_free_text_tasks(text: str) -> list[dict[str, str]]:
    """Split a blob of text into task chunks by numbered or bulleted items."""
    tasks: list[dict[str, str]] = []
    task_id = 1
    for line in text.splitlines():
        stripped = line.strip()
        m = re.match(r"^(\d+\.|-|\*|•)\s+(.+)", stripped)
        if m:
            desc = m.group(2).strip()
            tasks.append(
                {
                    "id": f"T{task_id:03d}",
                    "description": desc,
                    "acceptance": f"Done: {desc}",
                    "size": _estimate_size(desc),
                    "deps": f"T{task_id - 1:03d}" if task_id > 1 else "—",
                }
            )
            task_id += 1
    return tasks


def cmd_tasks(session: Any, args: str) -> Any:
    """Split a plan or spec into independently testable task chunks.

    Parameters
    ----------
    session:
        Active :class:`~lyra_cli.interactive.session.InteractiveSession`.
    args:
        ``--from-spec <file>`` or bare text / empty (uses pending task).

    Returns
    -------
    CommandResult
        Always returns a result; never raises.
    """
    raw = (args or "").strip()

    tasks: list[dict[str, str]] = []
    source_label = "input"

    if raw.startswith("--from-spec"):
        rest = raw[len("--from-spec"):].strip()
        if not rest:
            return _ok("usage: /tasks --from-spec <filename>")

        # Try repo/.lyra/specs/ then ~/.lyra/specs/ then as absolute path
        candidate_dirs = [_specs_dir(session), Path.home() / ".lyra" / "specs"]
        spec_path: Path | None = None
        for d in candidate_dirs:
            p = d / rest
            if p.exists():
                spec_path = p
                break
        if spec_path is None:
            p = Path(rest)
            if p.exists():
                spec_path = p
        if spec_path is None:
            return _ok(f"spec file not found: {rest!r}")

        content = spec_path.read_text(errors="replace")
        tasks = _parse_spec_tasks(content)
        source_label = spec_path.name
    else:
        # Use provided text, or fall back to pending_task / last message
        text = raw
        if not text:
            try:
                text = session.pending_task or ""
            except AttributeError:
                text = ""
        if not text:
            try:
                history = session.history
                last = next(
                    (m["content"] for m in reversed(history) if m.get("role") == "assistant"),
                    None,
                )
                text = str(last) if last else ""
            except Exception:
                text = ""
        if not text:
            return _ok(
                "usage: /tasks [--from-spec <file>]\n\n"
                "no pending task or last message found.  provide text or a spec file."
            )
        tasks = _parse_free_text_tasks(text)
        source_label = "text input"

    if not tasks:
        return _ok(
            f"no tasks extracted from {source_label}.\n"
            "ensure the source contains numbered items or `- [ ]` checkboxes."
        )

    # Write tasks file
    today = datetime.date.today().isoformat()
    out_dir = _tasks_dir(session)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"tasks-{today}.md"

    lines = [f"# Tasks — {today}", f"Source: {source_label}", ""]
    for t in tasks:
        lines += [
            f"## {t['id']}: {t['description']}",
            "",
            f"- **Acceptance:** {t['acceptance']}",
            f"- **Size:** {t['size']}",
            f"- **Deps:** {t['deps']}",
            "",
        ]
    dest.write_text("\n".join(lines))

    try:
        from rich.table import Table

        table = Table(title=f"Tasks ({source_label})", show_lines=False)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Description")
        table.add_column("Size", justify="center")
        table.add_column("Deps", style="dim")
        for t in tasks:
            size_color = {"S": "green", "M": "yellow", "L": "red"}.get(t["size"], "white")
            table.add_row(
                t["id"],
                t["description"],
                f"[{size_color}]{t['size']}[/{size_color}]",
                t["deps"],
            )
        renderable = table
    except Exception:
        renderable = None

    summary_lines = [f"extracted {len(tasks)} task(s) from {source_label}:"]
    for t in tasks:
        summary_lines.append(f"  {t['id']} [{t['size']}] {t['description']}")
    summary_lines.append(f"\nwritten to: {dest}")

    return _ok("\n".join(summary_lines), renderable=renderable)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["cmd_bmad", "cmd_specify", "cmd_tasks"]
