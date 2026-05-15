"""Skills lifecycle sub-commands for ``/skills`` (Wave D).

Implements the create / admit / audit / distill / compose / merge / prune
workflow described in the Voyager/SkillsBench pattern.  Every public entry
point returns a ``CommandResult`` from the session module (lazy-imported so
this file can be tested in isolation).

Public API
----------
``cmd_skills_lifecycle(session, args: str) -> CommandResult``

Sub-commands
------------
* ``create <name> [--from-last-session]`` — scaffold a new SKILL.md
* ``admit <name>``                        — admission gate (required sections)
* ``audit``                               — walk all roots, report table
* ``distill <name>``                      — condense a verbose skill
* ``compose <a> <b> [...]``               — chain skills into a workflow skill
* ``merge <a> <b>``                       — merge two skills into one
* ``prune [--stale] [--unsafe]``          — list candidates for removal
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # InteractiveSession imported lazily below

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS: tuple[str, ...] = (
    "## Applicability",
    "## Procedure",
    "## Verifier",
)

_SKILL_TEMPLATE = """\
# {name}

## Applicability
When to use this skill: <trigger condition>

## Procedure
1. Step one
2. Step two

## Verifier
```bash
# test command that verifies this skill works
```

## Lineage
- Created: {date}
- Source: {source}
"""

_STALE_DAYS = 30

# ---------------------------------------------------------------------------
# Result factory (lazy import mirrors v311_commands.py pattern)
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
# Skill root helpers
# ---------------------------------------------------------------------------


def _skill_roots(session: Any) -> list[Path]:
    roots: list[Path] = [Path.home() / ".lyra" / "skills"]
    try:
        if session.repo_root:
            roots.append(Path(session.repo_root) / ".lyra" / "skills")
    except AttributeError:
        pass
    return roots


def _find_skill_file(session: Any, name: str) -> Path | None:
    """Return the first SKILL.md matching *name* across all roots."""
    for root in _skill_roots(session):
        candidate = root / f"{name}.md"
        if candidate.exists():
            return candidate
        # Also allow name/SKILL.md layout
        candidate2 = root / name / "SKILL.md"
        if candidate2.exists():
            return candidate2
    return None


def _all_skill_files(session: Any) -> list[Path]:
    """Walk all roots and return every .md file found."""
    files: list[Path] = []
    for root in _skill_roots(session):
        if root.is_dir():
            files.extend(sorted(root.rglob("*.md")))
    return files


def _check_sections(text: str) -> list[str]:
    """Return the list of *missing* required sections."""
    return [s for s in _REQUIRED_SECTIONS if s not in text]


def _skill_name_from_path(path: Path) -> str:
    if path.name == "SKILL.md":
        return path.parent.name
    return path.stem


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------


def _cmd_create(session: Any, rest: str) -> Any:
    parts = rest.split()
    if not parts:
        return _ok("usage: /skills create <name> [--from-last-session]")
    name = parts[0]
    from_last = "--from-last-session" in parts

    dest = Path.home() / ".lyra" / "skills" / f"{name}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        return _ok(f"skill already exists: {dest}")

    source = "trajectory" if from_last else "manual"
    content = _SKILL_TEMPLATE.format(
        name=name,
        date=datetime.date.today().isoformat(),
        source=source,
    )

    if from_last:
        # Try to pull the last assistant message as a seed for the procedure
        try:
            history = session.history  # list of dicts with role/content
            last_assistant = next(
                (m["content"] for m in reversed(history) if m.get("role") == "assistant"),
                None,
            )
            if last_assistant:
                snippet = str(last_assistant)[:400].strip()
                content = content.replace(
                    "1. Step one\n2. Step two",
                    f"<!-- seeded from last session turn -->\n{snippet}",
                )
        except Exception:
            pass

    dest.write_text(content)
    return _ok(
        f"created skill: {dest}\n"
        f"edit the template then run `/skills admit {name}` to validate."
    )


def _cmd_admit(session: Any, rest: str) -> Any:
    name = rest.strip()
    if not name:
        return _ok("usage: /skills admit <name>")

    path = _find_skill_file(session, name)
    if path is None:
        return _ok(f"skill not found: {name!r}  (searched ~/.lyra/skills/ and repo/.lyra/skills/)")

    text = path.read_text(errors="replace")
    missing = _check_sections(text)

    if missing:
        return _ok(
            f"FAIL  {name!r} is missing required sections:\n"
            + "\n".join(f"  - {s}" for s in missing)
            + f"\n\nfix {path} then re-run `/skills admit {name}`."
        )

    return _ok(f"PASS  {name!r} admitted.  All required sections present.")


def _cmd_audit(session: Any) -> Any:
    files = _all_skill_files(session)
    if not files:
        return _ok(
            "no skill files found under ~/.lyra/skills/ or <repo>/.lyra/skills/.\n"
            "create one with `/skills create <name>`."
        )

    rows: list[tuple[str, str, str, str]] = []
    for path in files:
        sname = _skill_name_from_path(path)
        text = path.read_text(errors="replace")
        present = [s for s in _REQUIRED_SECTIONS if s in text]
        missing = [s for s in _REQUIRED_SECTIONS if s not in text]
        sections_str = ", ".join(s.lstrip("#").strip() for s in present)
        admitted = "yes" if not missing else f"no (missing: {', '.join(s.lstrip('#').strip() for s in missing)})"
        try:
            mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        except OSError:
            mtime = "unknown"
        rows.append((sname, sections_str or "—", admitted, mtime))

    try:
        from rich.table import Table

        table = Table(title="Skills Audit", show_lines=False, highlight=True)
        table.add_column("name", style="cyan", no_wrap=True)
        table.add_column("sections present", style="dim")
        table.add_column("admitted")
        table.add_column("last modified", style="dim")
        for name, sects, adm, mtime in rows:
            style = "green" if adm == "yes" else "red"
            table.add_row(name, sects, f"[{style}]{adm}[/{style}]", mtime)
        renderable = table
    except Exception:
        renderable = None

    lines = [f"{'name':<30} {'sections':<40} {'admitted':<12} {'modified'}"]
    lines.append("-" * 90)
    for name, sects, adm, mtime in rows:
        lines.append(f"{name:<30} {sects:<40} {adm:<12} {mtime}")

    return _ok("\n".join(lines), renderable=renderable)


def _cmd_distill(session: Any, rest: str) -> Any:
    name = rest.strip()
    if not name:
        return _ok("usage: /skills distill <name>")

    path = _find_skill_file(session, name)
    if path is None:
        return _ok(f"skill not found: {name!r}")

    text = path.read_text(errors="replace")
    lines = text.splitlines()

    # Build condensed version: keep headings, trim prose to first sentence/line
    condensed: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            condensed.append(line)
        elif stripped.startswith("```") or stripped.startswith("-") or stripped.startswith("*"):
            condensed.append(line)
        elif stripped and not condensed[-1:] == [""]:
            # Keep first non-empty content line per section, skip the rest
            # (heuristic: if previous line was a heading, keep this one)
            prev = condensed[-1] if condensed else ""
            if prev.strip().startswith("#"):
                condensed.append(line)
            else:
                condensed.append("")  # collapse prose

    condensed_text = "\n".join(condensed).strip()

    try:
        from rich.columns import Columns
        from rich.panel import Panel

        original_panel = Panel(
            text[:1200] + ("…" if len(text) > 1200 else ""),
            title=f"[bold]{name} — original[/bold]",
            border_style="dim",
        )
        condensed_panel = Panel(
            condensed_text,
            title=f"[bold]{name} — condensed[/bold]",
            border_style="cyan",
        )
        renderable = Columns([original_panel, condensed_panel])
    except Exception:
        renderable = None

    output = (
        f"=== {name} — original ({len(lines)} lines) ===\n"
        f"{text[:800]}{'…' if len(text) > 800 else ''}\n\n"
        f"=== {name} — condensed ({len(condensed)} lines) ===\n"
        f"{condensed_text}"
    )
    return _ok(output, renderable=renderable)


def _cmd_compose(session: Any, rest: str) -> Any:
    parts = rest.split()
    if len(parts) < 2:
        return _ok("usage: /skills compose <skill-a> <skill-b> [...]")

    combined_name = "-".join(parts) + "-workflow"
    dest = Path.home() / ".lyra" / "skills" / f"{combined_name}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)

    procedure_blocks: list[str] = []
    not_found: list[str] = []

    for sname in parts:
        path = _find_skill_file(session, sname)
        if path is None:
            not_found.append(sname)
            continue
        text = path.read_text(errors="replace")
        # Extract the Procedure section
        in_proc = False
        proc_lines: list[str] = []
        for line in text.splitlines():
            if line.strip() == "## Procedure":
                in_proc = True
                continue
            if in_proc and line.startswith("## "):
                break
            if in_proc:
                proc_lines.append(line)
        if proc_lines:
            procedure_blocks.append(
                f"### Phase: {sname}\n" + "\n".join(proc_lines).strip()
            )

    if not_found:
        return _ok(f"skills not found: {', '.join(not_found)}")

    skill_refs = "\n".join(f"- {s}" for s in parts)
    procedure = "\n\n".join(procedure_blocks) or "1. (compose phases here)"

    content = f"""\
# {combined_name}

## Applicability
Workflow composed from: {', '.join(parts)}.

## Procedure

{procedure}

## Verifier
```bash
# verify each constituent skill in order
```

## Lineage
- Created: {datetime.date.today().isoformat()}
- Source: compose({', '.join(parts)})
- Skills:
{skill_refs}
"""
    dest.write_text(content)
    return _ok(
        f"composed workflow skill written to: {dest}\n"
        f"review and run `/skills admit {combined_name}` to validate."
    )


def _cmd_merge(session: Any, rest: str) -> Any:
    parts = rest.split()
    if len(parts) != 2:
        return _ok("usage: /skills merge <skill-a> <skill-b>")

    name_a, name_b = parts
    path_a = _find_skill_file(session, name_a)
    path_b = _find_skill_file(session, name_b)

    missing = [n for n, p in [(name_a, path_a), (name_b, path_b)] if p is None]
    if missing:
        return _ok(f"skills not found: {', '.join(missing)}")

    assert path_a is not None and path_b is not None  # satisfied above

    def _extract_section(text: str, heading: str) -> str:
        lines = text.splitlines()
        in_section = False
        result: list[str] = []
        for line in lines:
            if line.strip() == heading:
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                result.append(line)
        return "\n".join(result).strip()

    text_a = path_a.read_text(errors="replace")
    text_b = path_b.read_text(errors="replace")

    # Merge: union applicability, combine procedure (deduplicate identical lines)
    app_a = _extract_section(text_a, "## Applicability")
    app_b = _extract_section(text_b, "## Applicability")
    proc_a = _extract_section(text_a, "## Procedure")
    proc_b = _extract_section(text_b, "## Procedure")
    ver_a = _extract_section(text_a, "## Verifier")
    ver_b = _extract_section(text_b, "## Verifier")

    seen: set[str] = set()
    merged_proc_lines: list[str] = []
    for line in (proc_a + "\n" + proc_b).splitlines():
        key = line.strip()
        if key and key not in seen:
            seen.add(key)
            merged_proc_lines.append(line)
        elif not key:
            merged_proc_lines.append(line)

    merged_name = f"{name_a}-{name_b}-merged"
    dest = Path.home() / ".lyra" / "skills" / f"{merged_name}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)

    content = f"""\
# {merged_name}

## Applicability
{app_a}

{app_b}

## Procedure
{chr(10).join(merged_proc_lines)}

## Verifier
{ver_a}

{ver_b}

## Lineage
- Created: {datetime.date.today().isoformat()}
- Source: merge({name_a}, {name_b})
"""
    dest.write_text(content)
    return _ok(
        f"merged skill written to: {dest}\n"
        f"review duplicates then run `/skills admit {merged_name}` to validate."
    )


def _cmd_prune(session: Any, rest: str) -> Any:
    flags = rest.split()
    stale_mode = "--stale" in flags
    unsafe_mode = "--unsafe" in flags

    if not stale_mode and not unsafe_mode:
        return _ok(
            "usage: /skills prune [--stale] [--unsafe]\n"
            "  --stale   list skills not modified in the last 30 days\n"
            "  --unsafe  list skills missing a ## Verifier section"
        )

    files = _all_skill_files(session)
    if not files:
        return _ok("no skill files found.")

    now = datetime.datetime.now()
    candidates: list[tuple[str, str]] = []  # (name, reason)

    for path in files:
        sname = _skill_name_from_path(path)
        text = path.read_text(errors="replace")

        if stale_mode:
            try:
                mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
                age = (now - mtime).days
                if age > _STALE_DAYS:
                    candidates.append((sname, f"stale ({age} days)"))
                    continue
            except OSError:
                pass

        if unsafe_mode:
            if "## Verifier" not in text:
                candidates.append((sname, "no ## Verifier section"))

    if not candidates:
        return _ok("no skills matched the prune criteria.")

    lines = [f"skills flagged for removal ({len(candidates)}):"]
    for sname, reason in candidates:
        lines.append(f"  - {sname}  [{reason}]")
    lines.append("")
    lines.append("run `/skills prune --confirm` to delete these skills.")

    return _ok("\n".join(lines))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_LIFECYCLE_HELP = """\
/skills lifecycle sub-commands (Wave D):

  /skills create <name> [--from-last-session]  scaffold a new SKILL.md
  /skills admit <name>                         validate required sections
  /skills audit                                table of all skills + status
  /skills distill <name>                       condensed view of a skill
  /skills compose <a> <b> [...]                chain skills into a workflow
  /skills merge <a> <b>                        merge two skills into one
  /skills prune [--stale] [--unsafe]           list removal candidates
"""


def cmd_skills_lifecycle(session: Any, args: str) -> Any:
    """Dispatch Wave-D lifecycle sub-commands for ``/skills``.

    Parameters
    ----------
    session:
        The active :class:`~lyra_cli.interactive.session.InteractiveSession`.
    args:
        Everything after ``/skills`` on the REPL line.

    Returns
    -------
    CommandResult
        Always returns a result; never raises.
    """
    raw = (args or "").strip()
    parts = raw.split(maxsplit=1)
    sub = parts[0] if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if sub == "create":
        return _cmd_create(session, rest)
    if sub == "admit":
        return _cmd_admit(session, rest)
    if sub == "audit":
        return _cmd_audit(session)
    if sub == "distill":
        return _cmd_distill(session, rest)
    if sub == "compose":
        return _cmd_compose(session, rest)
    if sub == "merge":
        return _cmd_merge(session, rest)
    if sub == "prune":
        return _cmd_prune(session, rest)

    return _ok(_LIFECYCLE_HELP)


__all__ = ["cmd_skills_lifecycle"]
