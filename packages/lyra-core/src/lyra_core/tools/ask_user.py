"""``AskUserQuestion`` tool — Claude-Code-style multi-choice prompt.

Lets the agent pause mid-task to ask the user a structured question
with explicit choices, instead of free-form text. Picked up the
schema from ``code.claude.com/docs/en/tools-reference#askuserquestion``;
the contract here is the minimum needed to make agent-driven decision
points feel like a real CLI dialog rather than a "please type Y or N"
freeform escape hatch.

Two design choices worth flagging:

* **Output is a JSON line, not a paragraph.** The model needs a
  parseable answer it can branch on without prose-grokking, so we
  return ``{"selected": ["option text"], "index": [n]}``. ``index``
  uses 1-based offsets to match what the operator typed.
* **The prompter is injectable.** Tests pass a fake; the REPL passes
  a Rich-aware one. Keeps the tool itself fully unit-testable without
  spawning a subprocess or commandeering stdin.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence

from harness_core.tools import Tool, ToolError
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class AskUserPrompt:
    """The structured form passed to a prompter callback."""

    question: str
    options: tuple[str, ...]
    multi_select: bool


# Prompter contract: receives an AskUserPrompt, returns the *indices*
# (1-based) the operator picked. Returning an empty tuple cancels.
Prompter = Callable[[AskUserPrompt], Sequence[int]]


def _default_prompter(prompt: AskUserPrompt) -> Sequence[int]:
    """Plain-text fallback prompter for non-Rich callers (CI, tests).

    Reads a single line of input. Comma-separated indices for
    multi-select; a single index for single-select. Empty input
    cancels.
    """
    print(prompt.question)
    for i, option in enumerate(prompt.options, 1):
        print(f"  {i}. {option}")
    raw = input(
        "→ enter "
        + ("indices (comma-separated)" if prompt.multi_select else "index")
        + ": "
    ).strip()
    if not raw:
        return ()
    out: List[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk.isdigit():
            continue
        n = int(chunk)
        if 1 <= n <= len(prompt.options):
            out.append(n)
    return tuple(out)


class _AskUserArgs(BaseModel):
    question: str = Field(..., description="The question to display.")
    options: List[str] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Choices to present (2–10).",
    )
    multi_select: bool = Field(
        default=False, description="Allow more than one selection."
    )


class AskUserQuestionTool(Tool):
    """Pause the agent loop and present a structured choice to the user.

    The tool is **medium risk** — it doesn't write to disk, but it
    *blocks* on user input which is a UX side-effect worth gating
    behind the same approval cache as a Bash invocation. Risk = low
    would have it auto-approve in agent mode and surprise users by
    silently popping a dialog inside an "unattended" run.
    """

    name = "AskUserQuestion"
    description = (
        "Present the user with a multiple-choice question and wait "
        "for them to pick one (or several) options."
    )
    risk = "medium"
    writes = False
    ArgsModel = _AskUserArgs  # pyright: ignore[reportAssignmentType]

    def __init__(self, prompter: Optional[Prompter] = None) -> None:
        self._prompter: Prompter = prompter or _default_prompter

    def set_prompter(self, prompter: Prompter) -> None:
        """Swap the prompter at runtime (REPL injects a Rich-aware one)."""
        self._prompter = prompter

    def run(self, args: Any) -> str:
        a: _AskUserArgs = args  # type: ignore[assignment]
        if len(a.options) != len(set(a.options)):
            raise ToolError("AskUserQuestion: options must be unique")
        prompt = AskUserPrompt(
            question=a.question.strip(),
            options=tuple(a.options),
            multi_select=a.multi_select,
        )
        indices = list(self._prompter(prompt))
        if not indices:
            return json.dumps(
                {"cancelled": True, "selected": [], "index": []}
            )
        # Sanitize: keep only in-range, dedupe, preserve order. For
        # single-select, take the first valid pick.
        seen: set[int] = set()
        clean: List[int] = []
        for n in indices:
            if 1 <= n <= len(a.options) and n not in seen:
                seen.add(n)
                clean.append(n)
        if not clean:
            return json.dumps(
                {"cancelled": True, "selected": [], "index": []}
            )
        if not a.multi_select:
            clean = clean[:1]
        selected = [a.options[n - 1] for n in clean]
        return json.dumps({"cancelled": False, "selected": selected, "index": clean})


__all__ = [
    "AskUserPrompt",
    "AskUserQuestionTool",
    "Prompter",
]
