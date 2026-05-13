"""Proactive compaction controller.

Three components:

1. :class:`CompactionController` — decides *when* to compact. Triggers at
   60 % utilisation by default, well before the 70 % threshold where
   reasoning quality degrades (§13 #3, MindStudio analysis).

2. :class:`DecisionPreservingPrompt` — builds a compaction instruction
   that explicitly preserves decisions, rationale, and project conventions.
   The Anthropic default only captures "what to do next"; community
   consensus is that decision context is the first casualty (okhlopkov.com).

3. :class:`EssentialsInjector` — maintains a short "Context Essentials"
   block (10–50 lines) and injects it as a system message after compaction
   fires. Implements the Nick Porter post-compaction hook pattern (§7).

Research grounding: §13 #3, §6.1 (Claude Code auto-compaction),
§7 (okhlopkov.com, MindStudio, Nick Porter Medium post).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# CompactionController
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactionDecision:
    """Result of :meth:`CompactionController.should_compact`."""

    should_compact: bool
    utilisation: float
    trigger_pct: float
    reason: str


class CompactionController:
    """Decide when to compact based on context utilisation.

    ``utilisation`` is a float in [0.0, 1.0] representing what fraction
    of the model's context window is currently used. The controller fires
    when utilisation reaches ``trigger_pct`` (default 0.60).

    Usage::
        ctrl = CompactionController(trigger_pct=0.60)
        if ctrl.should_compact(utilisation=0.65).should_compact:
            summary = run_compaction(messages, prompt=ctrl.compaction_prompt())
    """

    def __init__(
        self,
        *,
        trigger_pct: float = 0.60,
        ralph_pct: float = 0.85,
    ) -> None:
        if not 0.0 < trigger_pct < 1.0:
            raise ValueError(f"trigger_pct must be in (0, 1); got {trigger_pct}")
        if not trigger_pct < ralph_pct <= 1.0:
            raise ValueError(
                f"ralph_pct must be > trigger_pct and <= 1.0; "
                f"got ralph_pct={ralph_pct}, trigger_pct={trigger_pct}"
            )
        self.trigger_pct = trigger_pct
        self.ralph_pct = ralph_pct

    def check(self, utilisation: float) -> CompactionDecision:
        """Return a decision for the given utilisation level."""
        if utilisation >= self.ralph_pct:
            return CompactionDecision(
                should_compact=True,
                utilisation=utilisation,
                trigger_pct=self.trigger_pct,
                reason=(
                    f"utilisation {utilisation:.1%} >= ralph threshold "
                    f"{self.ralph_pct:.1%} — urgent compaction required"
                ),
            )
        if utilisation >= self.trigger_pct:
            return CompactionDecision(
                should_compact=True,
                utilisation=utilisation,
                trigger_pct=self.trigger_pct,
                reason=(
                    f"utilisation {utilisation:.1%} >= trigger "
                    f"{self.trigger_pct:.1%} — proactive compaction"
                ),
            )
        return CompactionDecision(
            should_compact=False,
            utilisation=utilisation,
            trigger_pct=self.trigger_pct,
            reason=(
                f"utilisation {utilisation:.1%} < trigger "
                f"{self.trigger_pct:.1%} — no compaction needed"
            ),
        )

    def select_summariser_model(
        self,
        fast_model: str,
        smart_model: str,
        *,
        invariant_count: int = 0,
        invariant_threshold: int = 6,
    ) -> str:
        """Pick the cheaper model unless the window has many invariants.

        Research: "doing your own compaction with Haiku for a Sonnet session
        can be 5–10× cheaper for the same summary quality" (§11 design
        choices). Use the smart model only when there are many invariants
        that require careful judgment.
        """
        if invariant_count >= invariant_threshold:
            return smart_model
        return fast_model


# ---------------------------------------------------------------------------
# DecisionPreservingPrompt
# ---------------------------------------------------------------------------

_DEFAULT_DECISION_PROMPT = """\
You are summarising a coding-agent conversation for context compaction.
Your summary will replace all earlier turns; the raw history will not be
accessible afterward.

CRITICAL — preserve ALL of the following (verbatim where possible):
1. DECISIONS made and their rationale ("we chose X because Y")
2. PROJECT CONVENTIONS established ("always use snake_case", "never mock the DB")
3. SECURITY / ACCESS CONTROL rules from earlier instructions
4. REJECTED approaches and WHY they were rejected (prevents re-exploration)
5. Current task state: what is done, what is in progress, what is next
6. File paths, function names, and module boundaries that were pinned
7. Known bugs or constraints that must be worked around

OMIT: raw tool output, verbose stack traces, repeated file content,
intermediate reasoning that reached a dead end.

Keep the summary under {max_tokens} tokens. Use concise bullet points.
Structure: ## Decisions | ## Conventions | ## Task State | ## Next Steps
"""


@dataclass
class DecisionPreservingPrompt:
    """Build a compaction instruction that retains decisions and rationale.

    Usage::
        prompt = DecisionPreservingPrompt(max_tokens=800)
        system_msg = prompt.as_system_message()
    """

    max_tokens: int = 800
    extra_instructions: list[str] = field(default_factory=list)
    _template: str = field(default=_DEFAULT_DECISION_PROMPT, init=False)

    def render(self) -> str:
        """Return the rendered prompt string."""
        base = self._template.format(max_tokens=self.max_tokens)
        if self.extra_instructions:
            additions = "\n".join(
                f"- {instr}" for instr in self.extra_instructions
            )
            base += f"\nADDITIONAL INSTRUCTIONS:\n{additions}\n"
        return base

    def as_system_message(self) -> dict[str, Any]:
        """Return a ``{"role": "system", "content": "..."}`` dict."""
        return {"role": "system", "content": self.render()}

    def with_extra(self, instruction: str) -> "DecisionPreservingPrompt":
        """Return a new prompt with an additional instruction appended."""
        return DecisionPreservingPrompt(
            max_tokens=self.max_tokens,
            extra_instructions=[*self.extra_instructions, instruction],
        )


# ---------------------------------------------------------------------------
# EssentialsInjector
# ---------------------------------------------------------------------------


@dataclass
class EssentialsInjector:
    """Maintain a "Context Essentials" block for post-compaction re-injection.

    The essentials block is a short list of critical rules and conventions
    (10–50 lines) that are injected as a system message after compaction fires.
    This implements the Nick Porter post-compaction hook pattern (§7):
    "treat CLAUDE.md as the employee handbook; the injected block is the
    before-you-ship checklist."

    Usage::
        injector = EssentialsInjector()
        injector.add("Never mock the database in tests.")
        injector.add("All API responses use the envelope format.")
        messages = injector.inject(messages_after_compaction)
    """

    _essentials: list[str] = field(default_factory=list)
    store_path: Path | None = None

    def __post_init__(self) -> None:
        if self.store_path and self.store_path.exists():
            self._load(self.store_path)

    def add(self, rule: str) -> None:
        """Append a rule to the essentials block."""
        rule = rule.strip()
        if rule and rule not in self._essentials:
            self._essentials.append(rule)
            if self.store_path:
                self._save(self.store_path)

    def remove(self, index: int) -> str:
        """Remove and return the rule at *index*."""
        removed = self._essentials.pop(index)
        if self.store_path:
            self._save(self.store_path)
        return removed

    def rules(self) -> list[str]:
        return list(self._essentials)

    def render(self) -> str:
        """Render the essentials block as a formatted string."""
        if not self._essentials:
            return ""
        lines = ["## Context Essentials (re-injected after compaction)\n"]
        for i, rule in enumerate(self._essentials, 1):
            lines.append(f"{i}. {rule}")
        return "\n".join(lines)

    def inject(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return a new message list with the essentials block prepended.

        Inserts as the first message so it lands in the stable prefix.
        No-op if the essentials block is empty.
        """
        if not self._essentials:
            return list(messages)
        essentials_msg = {
            "role": "system",
            "content": self.render(),
        }
        return [essentials_msg, *messages]

    def load_from_file(self, path: Path) -> None:
        """Load rules from a plain-text file (one rule per line)."""
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                self.add(line)

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._essentials, indent=2))

    def _load(self, path: Path) -> None:
        try:
            self._essentials = json.loads(path.read_text())
        except (json.JSONDecodeError, TypeError):
            self._essentials = []


__all__ = [
    "CompactionController",
    "CompactionDecision",
    "DecisionPreservingPrompt",
    "EssentialsInjector",
]
