"""Text processing tools for transformation, formatting, and analysis."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from enum import StrEnum


class TextOperation(StrEnum):
    TRIM = "trim"
    UPPER = "upper"
    LOWER = "lower"
    CAPITALIZE = "capitalize"
    WRAP = "wrap"
    INDENT = "indent"
    DEDENT = "dedent"


@dataclass(frozen=True)
class TextDiff:
    """Unified diff between two text blocks."""

    added_lines: int
    removed_lines: int
    unchanged_lines: int
    unified_diff: str


@dataclass(frozen=True)
class TextStats:
    char_count: int
    word_count: int
    line_count: int
    byte_count: int
    avg_word_length: float
    unique_word_count: int


class TextTool:
    """Text manipulation, diffing, and statistical analysis.

    Usage::

        tool = TextTool()
        diff = tool.diff(old_text, new_text)
        stats = tool.analyze("Hello world")
        wrapped = tool.transform(text, TextOperation.WRAP, width=72)
    """

    def diff(self, original: str, modified: str, context_lines: int = 3) -> TextDiff:
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                lineterm="",
                n=context_lines,
            )
        )
        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
        unchanged = sum(1 for l in diff_lines if l.startswith(" "))
        return TextDiff(
            added_lines=added,
            removed_lines=removed,
            unchanged_lines=unchanged,
            unified_diff="\n".join(diff_lines),
        )

    def analyze(self, text: str) -> TextStats:
        words = text.split()
        unique = set(w.lower() for w in words)
        return TextStats(
            char_count=len(text),
            word_count=len(words),
            line_count=text.count("\n") + 1,
            byte_count=len(text.encode("utf-8")),
            avg_word_length=sum(len(w) for w in words) / len(words) if words else 0.0,
            unique_word_count=len(unique),
        )

    def transform(self, text: str, operation: TextOperation, **kwargs: int | str) -> str:
        if operation == TextOperation.TRIM:
            return text.strip()
        if operation == TextOperation.UPPER:
            return text.upper()
        if operation == TextOperation.LOWER:
            return text.lower()
        if operation == TextOperation.CAPITALIZE:
            return text.capitalize()
        if operation == TextOperation.WRAP:
            import textwrap

            width = int(kwargs.get("width", 80))
            return textwrap.fill(text, width=width)
        if operation == TextOperation.INDENT:
            prefix = str(kwargs.get("prefix", "    "))
            return prefix + text.replace("\n", f"\n{prefix}")
        if operation == TextOperation.DEDENT:
            import textwrap

            return textwrap.dedent(text)
        raise ValueError(f"Unknown operation: {operation}")

    @staticmethod
    def extract_pattern(text: str, pattern: str, group: int = 0) -> list[str]:
        return [m.group(group) for m in re.finditer(pattern, text)]

    @staticmethod
    def replace_pattern(text: str, pattern: str, replacement: str) -> str:
        return re.sub(pattern, replacement, text)
