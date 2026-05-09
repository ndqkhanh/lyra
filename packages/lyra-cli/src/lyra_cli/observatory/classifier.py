"""Deterministic 13-category activity classifier.

Ported from CodeBurn ``classifier.ts``
(https://github.com/getagentseal/codeburn) with Lyra-specific
extensions: our 4-mode taxonomy biases ties, and pure slash-command
turns short-circuit to ``general`` so they don't pollute coding/debug
metrics.

Signal precedence (highest -> lowest):
1. Tool name in assistant text (``Edit(``, ``Write(``, ``Read(``...)
2. Strong keyword regex on user_input (``fix bug``, ``add feature``...)
3. Lyra mode (``debug`` -> debugging, ``plan`` -> plan, etc.)
4. Weak keyword regex
5. Fallback: ``general``

Determinism: every classifier call produces the same result for the
same row + prev. No timestamps, randomness, or external state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping


TaskCategory = Literal[
    "coding", "debugging", "feature", "refactor", "test",
    "explore", "plan", "delegation", "git", "build",
    "brainstorm", "conversation", "general",
]


@dataclass(frozen=True)
class Classification:
    category: TaskCategory
    confidence: float
    was_retry: bool
    retry_streak: int
    signals: tuple[str, ...]


# ---- regex tables (compiled once) -----------------------------------------

_RX = {
    "debugging": re.compile(
        r"\b(fix|debug|broken|fails?|failing|error|exception|"
        r"trace ?back|crash(?:es|ed)?|stack(?:trace)?|"
        r"why does .* (?:fail|error|crash))\b", re.I),
    "feature":   re.compile(
        r"\b(add|build|implement|create|introduce|ship|new "
        r"(?:feature|page|endpoint|route))\b", re.I),
    "refactor":  re.compile(
        r"\b(refactor|rename|extract|inline|move|split|consolidate|"
        r"deduplicate|clean ?up)\b", re.I),
    "test":      re.compile(
        r"\b(write|add|fix) (?:unit|integration|e2e)? ?tests?\b|"
        r"\btest coverage\b|\bpytest\b", re.I),
    "explore":   re.compile(
        r"\b(explain|how (?:does|do)|where (?:is|does)|what (?:is|does)|"
        r"walk me through|show me)\b", re.I),
    "plan":      re.compile(
        r"\b(plan|design|outline|spec(?:ify)?|approach|strategy)\b", re.I),
    "delegation": re.compile(
        r"\b(delegate|hand ?off|sub ?agent|spawn|fork .* agent)\b", re.I),
    "git":       re.compile(
        r"^(?:/?git\b|commit|push|pull|merge|rebase|branch|stash|cherry-?pick)\b",
        re.I),
    "build":     re.compile(
        r"\b(npm|pnpm|yarn|cargo|make|build|compile|bundle|webpack|"
        r"vite|rollup|tsc)\b", re.I),
    "brainstorm": re.compile(
        r"\b(brainstorm|ideas?|name (?:ideas|suggestions?)|propose)\b", re.I),
    "conversation": re.compile(
        r"^(?:hi|hello|hey|yo|thanks?|thank you|cool|nice|ok(?:ay)?)\b", re.I),
}

_TOOL_RX = re.compile(
    r"\b(Edit|Write|Read|Glob|Grep|Bash|Task|TodoWrite|"
    r"WebFetch|WebSearch)\(", re.I)

_CODING_TOOLS = {"Edit", "Write"}

# Coding-family categories share a workstream: a sequence of
# implement -> "still broken, try again" -> "fix the cache key" all
# count as one continued attempt for retry_streak / one_shot_rate
# purposes. Pure conversation/git/build/plan/explore/brainstorm/
# delegation each form their own workstream.
_CODING_FAMILY: frozenset[str] = frozenset({
    "coding", "debugging", "feature", "refactor", "test",
})


def _is_retry_continuation(prev_cat: str, cur_cat: str) -> bool:
    """Is the current turn a retry of the previous?

    Two patterns count as continuation:
    1. Exact same category (debugging->debugging, feature->feature).
    2. Coding-family work followed by a debugging turn ("implement X"
       then "still broken, try again" - the second turn is fixing what
       the first one set up).

    A fresh `feature`/`coding`/`refactor`/`test` turn after any prior
    work signals a new attempt and resets the streak.
    """
    if prev_cat == cur_cat:
        return True
    if cur_cat == "debugging" and prev_cat in _CODING_FAMILY:
        return True
    return False


# ---- public API -----------------------------------------------------------

def classify_turn(
    row: Mapping[str, Any],
    *,
    prev: Classification | None = None,
) -> Classification:
    signals: list[str] = []

    if row.get("command") and not row.get("model"):
        return _finalize("general", 1.0, prev, signals + ["slash-only"])

    user_text = (row.get("user_input") or row.get("user") or "").strip()
    asst_text = (row.get("assistant") or "").strip()
    mode = (row.get("mode") or "").lower()

    tool_hits = _TOOL_RX.findall(asst_text)
    code_tool = any(t in _CODING_TOOLS for t in tool_hits)
    if code_tool:
        signals.append("tool:Edit")
        if user_text and _RX["refactor"].search(user_text):
            signals.append("kw:refactor")
            return _finalize("refactor", 0.92, prev, signals)
        if user_text and _RX["test"].search(user_text):
            signals.append("kw:test")
            return _finalize("test", 0.9, prev, signals)
        return _finalize("coding", 0.9, prev, signals)

    if user_text:
        # `build` (e.g. "npm run build") must beat `feature` (e.g. "build a
        # foo") because the latter regex would also match "build" as a verb.
        for cat in (
            "debugging", "test", "refactor", "build", "feature",
            "delegation", "git", "plan",
            "brainstorm", "explore", "conversation",
        ):
            if _RX[cat].search(user_text):
                signals.append(f"kw:{cat}")
                conf = 0.8 if cat in ("debugging", "feature", "test", "refactor") else 0.7
                return _finalize(cat, conf, prev, signals)

    if mode == "debug":
        return _finalize("debugging", 0.5, prev, signals + ["mode:debug"])
    if mode == "plan":
        return _finalize("plan", 0.5, prev, signals + ["mode:plan"])
    if mode == "ask":
        return _finalize("conversation", 0.4, prev, signals + ["mode:ask"])

    return _finalize("general", 0.3, prev, signals + ["fallback"])


def one_shot_rate(rows: Iterable[Mapping[str, Any]]) -> float:
    """Fraction of coding-family turns where retry_streak == 1.

    Coding-family covers {coding, debugging, feature, refactor, test} -
    they share a workstream so a sequence like "implement X" then
    "still broken, try again" counts as one task with one retry.

    Convention: when no coding-family turns are present, returns 1.0
    (no failures observed). Callers that want to distinguish "no data"
    from "perfect" should also surface the count.
    """
    prev: Classification | None = None
    n_first_try = 0
    n_total = 0
    for row in rows:
        if row.get("kind") not in (None, "turn"):
            continue
        cls = classify_turn(row, prev=prev)
        if cls.category in _CODING_FAMILY:
            n_total += 1
            if cls.retry_streak == 1:
                n_first_try += 1
        prev = cls
    if n_total == 0:
        return 1.0
    return n_first_try / n_total


# ---- helpers --------------------------------------------------------------

def _finalize(
    category: TaskCategory, confidence: float,
    prev: Classification | None, signals: list[str],
) -> Classification:
    if prev is not None and _is_retry_continuation(prev.category, category):
        streak = prev.retry_streak + 1
        was_retry = True
    else:
        streak = 1
        was_retry = False
    return Classification(
        category=category, confidence=confidence,
        was_retry=was_retry, retry_streak=streak,
        signals=tuple(signals),
    )
