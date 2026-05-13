"""Differential tool-output retention policy.

Decides which tool outputs to keep, summarise, or drop based on type
and recency — then deduplicates and cleans the retained outputs.

Research grounding: §9 (forgetting mechanisms — type-based: tool outputs
are reproducible, user intent is not; relevance-based: drop unreferenced
content), §3.4 AgentDiet waste taxonomy (three reducible waste classes),
§11 step 3 (strip ANSI from logs, dedupe stack frames).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Retention levels
# ---------------------------------------------------------------------------


class RetentionLevel(str, Enum):
    KEEP = "keep"
    SUMMARISE = "summarise"
    DROP = "drop"


class ReproducibilityClass(str, Enum):
    REPRODUCIBLE = "reproducible"      # file reads, bash outputs — can be re-fetched
    IRREPRODUCIBLE = "irreproducible"  # user confirmations, external API responses


# ---------------------------------------------------------------------------
# Tool-output type registry
# ---------------------------------------------------------------------------

_REPRODUCIBLE_TOOLS = frozenset(
    {
        "read_file",
        "read",
        "bash",
        "execute_bash",
        "shell",
        "run_command",
        "list_files",
        "ls",
        "grep",
        "search_files",
        "codesearch",
        "web_search",   # can be re-run
    }
)

_IRREPRODUCIBLE_TOOLS = frozenset(
    {
        "ask_user",
        "ask_user_question",
        "confirm",
        "approve",
        "reject",
        "send_message",
        "create_pull_request",
        "git_push",
        "deploy",
    }
)


class ReproducibilityClassifier:
    """Classify a tool call by whether its output can be reproduced.

    Reproducible outputs (bash, file reads) can be dropped and re-fetched.
    Irreproducible outputs (user input, external side effects) must be kept.
    """

    def classify(
        self,
        tool_name: str,
        *,
        output_text: str = "",
    ) -> ReproducibilityClass:
        name = tool_name.lower().strip()
        if name in _IRREPRODUCIBLE_TOOLS:
            return ReproducibilityClass.IRREPRODUCIBLE
        if name in _REPRODUCIBLE_TOOLS:
            return ReproducibilityClass.REPRODUCIBLE
        # Heuristic: if the output looks like user-provided text (question
        # marks, short sentences) treat it as irreproducible.
        if output_text and len(output_text) < 200 and "?" in output_text:
            return ReproducibilityClass.IRREPRODUCIBLE
        return ReproducibilityClass.REPRODUCIBLE


# ---------------------------------------------------------------------------
# Retention decider
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetentionDecision:
    level: RetentionLevel
    reason: str
    tool_name: str
    turn_age: int  # turns since this output was produced


class RetentionDecider:
    """Decide the retention level for a tool output.

    Rules (in priority order):
      1. Irreproducible → always KEEP
      2. Referenced in last ``recent_turns`` → KEEP
      3. Age <= ``keep_turns`` → KEEP
      4. Age <= ``summarise_turns`` → SUMMARISE (keep first+last lines)
      5. Otherwise → DROP
    """

    def __init__(
        self,
        *,
        keep_turns: int = 3,
        summarise_turns: int = 8,
        recent_turns: int = 3,
    ) -> None:
        self.keep_turns = keep_turns
        self.summarise_turns = summarise_turns
        self.recent_turns = recent_turns

    def decide(
        self,
        tool_name: str,
        *,
        turn_age: int,
        referenced: bool = False,
        reproducibility: ReproducibilityClass = ReproducibilityClass.REPRODUCIBLE,
    ) -> RetentionDecision:
        if reproducibility == ReproducibilityClass.IRREPRODUCIBLE:
            return RetentionDecision(
                level=RetentionLevel.KEEP,
                reason="irreproducible output (user input or external side effect)",
                tool_name=tool_name,
                turn_age=turn_age,
            )
        if referenced:
            return RetentionDecision(
                level=RetentionLevel.KEEP,
                reason=f"referenced in last {self.recent_turns} turns",
                tool_name=tool_name,
                turn_age=turn_age,
            )
        if turn_age <= self.keep_turns:
            return RetentionDecision(
                level=RetentionLevel.KEEP,
                reason=f"recent output (age={turn_age} <= keep_turns={self.keep_turns})",
                tool_name=tool_name,
                turn_age=turn_age,
            )
        if turn_age <= self.summarise_turns:
            return RetentionDecision(
                level=RetentionLevel.SUMMARISE,
                reason=f"older output (age={turn_age}), summarise to head+tail",
                tool_name=tool_name,
                turn_age=turn_age,
            )
        return RetentionDecision(
            level=RetentionLevel.DROP,
            reason=f"stale unreferenced reproducible output (age={turn_age})",
            tool_name=tool_name,
            turn_age=turn_age,
        )


# ---------------------------------------------------------------------------
# OutputDeduplicator
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


class OutputDeduplicator:
    """Clean tool output text: strip noise and collapse repetition.

    Operations (in order):
    1. Strip ANSI escape sequences
    2. Collapse 3+ consecutive blank lines → 1 blank line
    3. Collapse consecutively repeated lines → single line + count
    4. Truncate stack traces: keep first N + last N frames
    5. Truncate very long outputs: keep head + tail lines

    The output is always shorter than or equal in length to the input.
    """

    def __init__(
        self,
        *,
        stack_head: int = 3,
        stack_tail: int = 3,
        max_lines: int = 50,
        head_lines: int = 20,
        tail_lines: int = 20,
    ) -> None:
        self.stack_head = stack_head
        self.stack_tail = stack_tail
        self.max_lines = max_lines
        self.head_lines = head_lines
        self.tail_lines = tail_lines

    def clean(self, text: str) -> str:
        text = self._strip_ansi(text)
        text = self._collapse_blank_lines(text)
        text = self._collapse_repeated_lines(text)
        text = self._truncate_stack_trace(text)
        text = self._truncate_long_output(text)
        return text

    def _strip_ansi(self, text: str) -> str:
        return _ANSI_RE.sub("", text)

    def _collapse_blank_lines(self, text: str) -> str:
        return _BLANK_LINES_RE.sub("\n\n", text)

    def _collapse_repeated_lines(self, text: str) -> str:
        lines = text.splitlines()
        if not lines:
            return text
        result: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            count = 1
            while i + count < len(lines) and lines[i + count] == line:
                count += 1
            if count > 1:
                result.append(f"{line}  [repeated {count}×]")
            else:
                result.append(line)
            i += count
        return "\n".join(result)

    def _truncate_stack_trace(self, text: str) -> str:
        lines = text.splitlines()
        # Detect stack-trace-like blocks (lines starting with spaces/tabs
        # containing "at ", "File ", or "line " patterns)
        stack_markers = sum(
            1 for ln in lines
            if re.match(r"^\s+(?:at |File |in |\w+\.py)", ln)
        )
        if stack_markers <= (self.stack_head + self.stack_tail):
            return text
        head = lines[: self.stack_head]
        tail = lines[-self.stack_tail :]
        omitted = len(lines) - self.stack_head - self.stack_tail
        return "\n".join(
            [*head, f"  ... [{omitted} frames omitted] ...", *tail]
        )

    def _truncate_long_output(self, text: str) -> str:
        lines = text.splitlines()
        if len(lines) <= self.max_lines:
            return text
        head = lines[: self.head_lines]
        tail = lines[-self.tail_lines :]
        omitted = len(lines) - self.head_lines - self.tail_lines
        return "\n".join(
            [*head, f"... [{omitted} lines omitted] ...", *tail]
        )


# ---------------------------------------------------------------------------
# ToolOutputPolicy — high-level coordinator
# ---------------------------------------------------------------------------


class ToolOutputPolicy:
    """Apply retention + deduplication policy to a list of messages.

    Returns a new message list with tool outputs classified and cleaned.
    Tool outputs marked DROP are removed; SUMMARISE outputs are truncated;
    KEEP outputs are cleaned (ANSI stripped etc.) but otherwise unchanged.

    Usage::
        policy = ToolOutputPolicy()
        cleaned = policy.apply(messages)
    """

    def __init__(
        self,
        *,
        decider: RetentionDecider | None = None,
        deduplicator: OutputDeduplicator | None = None,
        classifier: ReproducibilityClassifier | None = None,
    ) -> None:
        self._decider = decider or RetentionDecider()
        self._deduplicator = deduplicator or OutputDeduplicator()
        self._classifier = classifier or ReproducibilityClassifier()

    def apply(
        self,
        messages: list[dict[str, Any]],
        *,
        recent_turns: int = 3,
    ) -> list[dict[str, Any]]:
        """Return cleaned messages. Does not mutate the original list."""
        result: list[dict[str, Any]] = []
        total = len(messages)
        recent_text = self._extract_recent_text(messages, recent_turns)

        for i, msg in enumerate(messages):
            if msg.get("role") != "tool":
                result.append(msg)
                continue

            tool_name = msg.get("name", "") or ""
            content = msg.get("content", "")
            output_text = content if isinstance(content, str) else str(content)
            turn_age = total - i

            repro = self._classifier.classify(tool_name, output_text=output_text)
            referenced = output_text[:80] in recent_text if output_text else False

            decision = self._decider.decide(
                tool_name,
                turn_age=turn_age,
                referenced=referenced,
                reproducibility=repro,
            )

            if decision.level == RetentionLevel.DROP:
                continue
            elif decision.level == RetentionLevel.SUMMARISE:
                cleaned = self._deduplicator.clean(output_text)
                result.append({**msg, "content": cleaned})
            else:  # KEEP
                cleaned = self._deduplicator.clean(output_text)
                result.append({**msg, "content": cleaned})

        return result

    def _extract_recent_text(
        self, messages: list[dict[str, Any]], n: int
    ) -> str:
        recent = messages[-n:] if n < len(messages) else messages
        parts: list[str] = []
        for msg in recent:
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
        return " ".join(parts)


__all__ = [
    "RetentionLevel",
    "ReproducibilityClass",
    "ReproducibilityClassifier",
    "RetentionDecision",
    "RetentionDecider",
    "OutputDeduplicator",
    "ToolOutputPolicy",
]
