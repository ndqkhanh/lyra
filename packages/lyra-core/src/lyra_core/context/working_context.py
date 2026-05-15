"""``WORKING-CONTEXT.md`` — auto-maintained session-spanning state file
(Phase CE.2, P1-4).

Borrowed from ECC: a tiny plain-text file at the repo's
``.lyra/WORKING-CONTEXT.md`` capturing *what's in flight* — current
task, plan summary, todo state, blocking questions, last commit /
branch. Separate from:

* ``SOUL.md``   — persona (rarely changes).
* ``CLAUDE.md`` — durable config / coding rules.
* ``MEMORY.md`` — durable facts about the project.

The working-context file is loud and short-lived. Surfaced as L2
cached mid in the context engine so the model always knows what we're
in the middle of, without having to re-derive it from the recent
transcript every turn.

Hard byte cap (``DEFAULT_CAP_BYTES``) keeps it from sprawling. Render
trims oldest sections first so the most-recent state survives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CAP_BYTES = 2048
DEFAULT_RELATIVE_PATH = Path(".lyra") / "WORKING-CONTEXT.md"


_HEADER = "# WORKING CONTEXT"


@dataclass
class WorkingContext:
    """Structured form of the file. Roundtrips through markdown."""

    current_task: str = ""
    plan_summary: str = ""
    todo_lines: list[str] = field(default_factory=list)
    blocking_questions: list[str] = field(default_factory=list)
    last_commit: str = ""
    branch: str = ""

    # ------------------------------------------------------------------ I/O
    def to_markdown(self) -> str:
        sections: list[str] = [_HEADER, ""]
        if self.current_task:
            sections += ["## Current task", self.current_task.strip(), ""]
        if self.plan_summary:
            sections += ["## Plan summary", self.plan_summary.strip(), ""]
        if self.todo_lines:
            sections += ["## TODO"]
            sections += [f"- {line.strip()}" for line in self.todo_lines if line.strip()]
            sections.append("")
        if self.blocking_questions:
            sections += ["## Blocking questions"]
            sections += [
                f"- {q.strip()}" for q in self.blocking_questions if q.strip()
            ]
            sections.append("")
        if self.last_commit or self.branch:
            sections += ["## Repo"]
            if self.branch:
                sections.append(f"- branch: {self.branch}")
            if self.last_commit:
                sections.append(f"- last_commit: {self.last_commit}")
            sections.append("")
        return "\n".join(sections).rstrip() + "\n"

    @classmethod
    def from_markdown(cls, text: str) -> "WorkingContext":
        wc = cls()
        if not text:
            return wc
        current_section: str | None = None
        buffer: list[str] = []

        def flush() -> None:
            if current_section is None:
                return
            cleaned = [line for line in buffer if line.strip()]
            if current_section == "Current task":
                wc.current_task = "\n".join(buffer).strip()
            elif current_section == "Plan summary":
                wc.plan_summary = "\n".join(buffer).strip()
            elif current_section == "TODO":
                wc.todo_lines = [
                    line[2:].strip() if line.startswith("- ") else line.strip()
                    for line in cleaned
                ]
            elif current_section == "Blocking questions":
                wc.blocking_questions = [
                    line[2:].strip() if line.startswith("- ") else line.strip()
                    for line in cleaned
                ]
            elif current_section == "Repo":
                for line in cleaned:
                    if line.startswith("- branch:"):
                        wc.branch = line.split(":", 1)[1].strip()
                    elif line.startswith("- last_commit:"):
                        wc.last_commit = line.split(":", 1)[1].strip()

        for raw in text.splitlines():
            line = raw.rstrip()
            if line.startswith("## "):
                flush()
                current_section = line[3:].strip()
                buffer = []
                continue
            if line.startswith("# "):
                continue
            buffer.append(line)
        flush()
        return wc


# ────────────────────────────────────────────────────────────────
# Disk I/O
# ────────────────────────────────────────────────────────────────


def resolve_path(repo_root: Path) -> Path:
    """Where the file lives for ``repo_root``."""
    return repo_root / DEFAULT_RELATIVE_PATH


def read_working_context(repo_root: Path) -> WorkingContext:
    path = resolve_path(repo_root)
    if not path.is_file():
        return WorkingContext()
    return WorkingContext.from_markdown(path.read_text(encoding="utf-8"))


def write_working_context(
    repo_root: Path, wc: WorkingContext, *, cap_bytes: int = DEFAULT_CAP_BYTES
) -> Path:
    """Render and atomically write the file. Returns the path written."""
    body = render(wc, cap_bytes=cap_bytes)
    path = resolve_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)
    return path


def reset_working_context(repo_root: Path) -> bool:
    """Delete the file. Returns True if a file was removed."""
    path = resolve_path(repo_root)
    if path.is_file():
        path.unlink()
        return True
    return False


# ────────────────────────────────────────────────────────────────
# Rendering with cap-driven trimming
# ────────────────────────────────────────────────────────────────


def render(wc: WorkingContext, *, cap_bytes: int = DEFAULT_CAP_BYTES) -> str:
    """Render and trim to fit ``cap_bytes``.

    Trimming order (oldest / least-load-bearing first):
      1. Drop blocking_questions tail entries.
      2. Drop todo_lines tail entries.
      3. Truncate plan_summary.
      4. Truncate current_task.
    """
    if cap_bytes <= 0:
        raise ValueError(f"cap_bytes must be > 0, got {cap_bytes}")
    candidate = wc
    body = candidate.to_markdown()
    if len(body.encode("utf-8")) <= cap_bytes:
        return body

    # Strategy: copy + pare back fields.
    todo = list(candidate.todo_lines)
    blocking = list(candidate.blocking_questions)
    plan = candidate.plan_summary
    task = candidate.current_task

    def rebuild() -> str:
        return WorkingContext(
            current_task=task,
            plan_summary=plan,
            todo_lines=todo,
            blocking_questions=blocking,
            last_commit=candidate.last_commit,
            branch=candidate.branch,
        ).to_markdown()

    # 1. shrink blocking from the tail.
    while blocking and len(rebuild().encode("utf-8")) > cap_bytes:
        blocking.pop()
    if len(rebuild().encode("utf-8")) <= cap_bytes:
        return rebuild()

    # 2. shrink todo from the tail.
    while todo and len(rebuild().encode("utf-8")) > cap_bytes:
        todo.pop()
    if len(rebuild().encode("utf-8")) <= cap_bytes:
        return rebuild()

    # 3. truncate plan summary.
    while plan and len(rebuild().encode("utf-8")) > cap_bytes:
        plan = plan[: max(0, len(plan) - 32)].rstrip()
    if len(rebuild().encode("utf-8")) <= cap_bytes:
        return rebuild()

    # 4. truncate current task as a last resort.
    while task and len(rebuild().encode("utf-8")) > cap_bytes:
        task = task[: max(0, len(task) - 32)].rstrip()
    return rebuild()


def render_for_context_layer(
    wc: WorkingContext, *, cap_bytes: int = DEFAULT_CAP_BYTES
) -> str:
    """Render for injection as an L2 cached-mid system message.

    Adds the wrapper marker so the model knows what the block is.
    """
    return f"<working-context>\n{render(wc, cap_bytes=cap_bytes)}</working-context>"


__all__ = [
    "DEFAULT_CAP_BYTES",
    "DEFAULT_RELATIVE_PATH",
    "WorkingContext",
    "read_working_context",
    "render",
    "render_for_context_layer",
    "reset_working_context",
    "resolve_path",
    "write_working_context",
]
