"""Inject relevant memory snippets into the chat system prompt.

Lyra learns. Every successful or failed agent trajectory can be
distilled into a :class:`Lesson` (positive strategy or *anti-skill*)
inside a :class:`lyra_core.memory.reasoning_bank.ReasoningBank`, and
every onboarding pack can be promoted into a
:class:`lyra_core.memory.procedural.ProceduralMemory` SQLite store
keyed for FTS5 lookup.

Pre-v2.4 the chat handler ignored both: the bank stayed in memory
between turns but never leaked into the LLM's context, and the
procedural store was a glorified bookmark folder. Phase B.5 changes
that: every chat turn we

1. open (lazily) the procedural store at
   ``<repo>/.lyra/memory/procedural.sqlite``,
2. ``search()`` it with the user line,
3. recall the top-k lessons from the in-process
   :class:`ReasoningBank` (only if one's been attached to the
   session — a real production wiring),
4. render a compact "## Relevant memory" block, and
5. let
   :func:`lyra_cli.interactive.session._chat_with_llm` prepend it to
   the system prompt before the LLM sees the turn.

The block is bounded:

* up to ``max_skills`` procedural skill descriptions (default 4),
* up to ``max_lessons`` reasoning-bank lessons (default 4), and
* per-line truncated at ``line_limit`` chars (default 200).

Lessons surface their polarity (``[do]`` for SUCCESS strategies,
``[avoid]`` for FAILURE anti-skills) so the LLM can reason about
them differently. Procedural skills are rendered ``id: description``
- the model can ``Read`` the body via the chat tools when it
decides to apply one.

If neither store has anything to say about the turn, the function
returns the empty string and the system prompt is left untouched.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, List, Optional


_DEFAULT_MAX_SKILLS = 4
_DEFAULT_MAX_LESSONS = 4
_DEFAULT_LINE_LIMIT = 200
_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{3,}")


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------


def _extract_query_tokens(text: str, *, max_tokens: int = 8) -> List[str]:
    """Pull a small set of meaningful tokens out of the user line.

    Used to shape the FTS5 query for procedural memory and the
    task-signature for the reasoning bank. Trims out one-letter
    fillers and dedupes case-insensitively.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in _TOKEN_RE.findall(text or ""):
        norm = raw.lower()
        if norm in seen:
            continue
        seen.add(norm)
        out.append(raw)
        if len(out) >= max_tokens:
            break
    return out


# ---------------------------------------------------------------------------
# Procedural memory
# ---------------------------------------------------------------------------


def _default_procedural_db_path(repo_root: Path) -> Path:
    """Where the project-local procedural store lives.

    Mirrors the path convention used elsewhere in Lyra
    (``<repo>/.lyra/<feature>/<file>``).
    """
    return Path(repo_root) / ".lyra" / "memory" / "procedural.sqlite"


def _open_procedural_memory(db_path: Path) -> Any:
    """Best-effort load — return ``None`` when the file isn't there.

    We *do not* auto-create the SQLite file. Memory is opt-in: a
    user populates it via the agent loop or the ``lyra memory``
    subcommand. Auto-creating an empty store on first chat would
    confuse ``/skills list`` reports.
    """
    if not db_path.exists():
        return None
    try:
        from lyra_core.memory.procedural import ProceduralMemory
    except Exception:
        return None
    try:
        return ProceduralMemory(db_path=db_path)
    except Exception:
        return None


def _search_procedural(
    memory: Any,
    line: str,
    *,
    max_results: int,
) -> List[dict]:
    """Run a tokenised search and return ``[{id, description}, ...]``.

    Returns an empty list when the store is unavailable or the
    search raises. We never propagate the exception — a corrupted
    SQLite file should not abort a chat turn.
    """
    if memory is None:
        return []
    tokens = _extract_query_tokens(line)
    if not tokens:
        return []
    query = " OR ".join(tokens) if len(tokens) > 1 else tokens[0]
    try:
        records = memory.search(query)
    except Exception:
        return []
    out: list[dict] = []
    for rec in records[:max_results]:
        out.append(
            {
                "id": getattr(rec, "id", "?"),
                "description": getattr(rec, "description", "") or "",
            }
        )
    return out


# ---------------------------------------------------------------------------
# ReasoningBank
# ---------------------------------------------------------------------------


def _recall_bank_lessons(
    bank: Any,
    line: str,
    *,
    k: int,
) -> List[dict]:
    """Return ``[{title, body, polarity}, ...]`` from the bank.

    ``bank`` is duck-typed: anything with a ``recall(task_signature,
    k=...)`` returning iterable of objects with ``title``, ``body``,
    and ``polarity`` works. ``None`` means "no bank attached".
    """
    if bank is None:
        return []
    if k <= 0:
        return []
    tokens = _extract_query_tokens(line)
    # Pure-punctuation / one-letter input has no usable signature;
    # bail to keep the system prompt clean instead of bombing the bank
    # with empty-string queries.
    if not tokens:
        return []
    sig = " ".join(tokens)
    try:
        lessons = bank.recall(sig, k=k)
    except Exception:
        return []
    out: list[dict] = []
    for lesson in lessons:
        polarity = getattr(lesson, "polarity", None)
        polarity_label = "do"
        try:
            from lyra_core.memory.reasoning_bank import TrajectoryOutcome

            if polarity is TrajectoryOutcome.FAILURE:
                polarity_label = "avoid"
        except Exception:
            if str(polarity).lower().endswith("failure"):
                polarity_label = "avoid"
        out.append(
            {
                "title": getattr(lesson, "title", "") or "",
                "body": getattr(lesson, "body", "") or "",
                "polarity": polarity_label,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Public renderer
# ---------------------------------------------------------------------------


def render_memory_block(
    line: str,
    *,
    repo_root: Path,
    procedural_memory: Any = None,
    reasoning_bank: Any = None,
    max_skills: int = _DEFAULT_MAX_SKILLS,
    max_lessons: int = _DEFAULT_MAX_LESSONS,
    line_limit: int = _DEFAULT_LINE_LIMIT,
) -> str:
    """Build the "## Relevant memory" block for ``line``.

    Args:
        line: the user's chat input.
        repo_root: project root used when ``procedural_memory`` is
            not pre-supplied (we attempt to open the default
            ``<repo>/.lyra/memory/procedural.sqlite`` path).
        procedural_memory: optional pre-opened store. Tests pass a
            populated in-memory instance; the production path lets
            the function open the default store on demand.
        reasoning_bank: optional bank instance with a
            ``recall(task_signature, k=...)`` method.
        max_skills: cap on procedural-memory entries surfaced.
        max_lessons: cap on reasoning-bank lessons surfaced.
        line_limit: per-line char cap (truncates with ``…``).

    Returns ``""`` when neither store has anything relevant — the
    caller is expected to skip prepending so the system prompt
    doesn't carry a dangling header.
    """
    proc_mem = procedural_memory
    if proc_mem is None:
        proc_mem = _open_procedural_memory(_default_procedural_db_path(repo_root))

    skills = _search_procedural(proc_mem, line, max_results=max_skills)
    lessons = _recall_bank_lessons(reasoning_bank, line, k=max_lessons)

    if not skills and not lessons:
        return ""

    out_lines: list[str] = ["## Relevant memory", ""]

    if skills:
        out_lines.append("### Procedural skills")
        out_lines.append(
            "Past patterns the team has captured for similar work. "
            "Cite the id and read the body via the ``Read`` tool if "
            "you decide to apply one."
        )
        for s in skills:
            entry = f"- {s['id']}: {s['description'].strip()}"
            out_lines.append(_truncate(entry, line_limit))
        out_lines.append("")

    if lessons:
        out_lines.append("### Reasoning lessons")
        out_lines.append(
            "Distilled successes (``[do]``) and anti-skills "
            "(``[avoid]``) from prior trajectories. Treat ``[avoid]`` "
            "items as documented failure modes — explicitly check you "
            "are not repeating them."
        )
        for lesson in lessons:
            tag = lesson["polarity"]
            head = lesson["title"].strip() or "(untitled)"
            body = lesson["body"].strip().replace("\n", " ")
            entry = f"- [{tag}] {head}: {body}" if body else f"- [{tag}] {head}"
            out_lines.append(_truncate(entry, line_limit))
        out_lines.append("")

    return "\n".join(out_lines)


def _truncate(entry: str, limit: int) -> str:
    if len(entry) <= limit:
        return entry
    return entry[: limit - 1] + "…"


__all__ = [
    "render_memory_block",
    "_default_procedural_db_path",
    "_extract_query_tokens",
    "_open_procedural_memory",
]
