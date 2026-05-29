"""Semantic and syntactic diff generation."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DiffConfig:
    """Configuration governing diff generation."""

    context_lines: int = 3
    ignore_whitespace: bool = True
    semantic_mode: bool = True


@dataclass(frozen=True)
class DiffHunk:
    """A single contiguous changed region in a diff."""

    start_line_old: int
    end_line_old: int
    start_line_new: int
    end_line_new: int
    content: str
    change_type: str


@dataclass(frozen=True)
class DiffResult:
    """Complete diff result for a file pair."""

    file_path: str
    hunks: tuple[DiffHunk, ...]
    lines_added: int
    lines_removed: int
    semantic_summary: str


class DiffGenerator:
    """Semantic and syntactic diff generation."""

    @staticmethod
    async def compute_diff(
        original: str,
        modified: str,
        config: DiffConfig = DiffConfig(),
    ) -> DiffResult:
        """Compute a structured diff between two strings."""
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)

        if config.ignore_whitespace:
            orig_compare = [re.sub(r"\s+", "", l) for l in orig_lines]
            mod_compare = [re.sub(r"\s+", "", l) for l in mod_lines]
        else:
            orig_compare = orig_lines
            mod_compare = mod_lines

        differ = difflib.SequenceMatcher(a=orig_compare, b=mod_compare)
        opcodes = differ.get_opcodes()

        hunks: list[DiffHunk] = []
        lines_added = 0
        lines_removed = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                continue
            if tag == "replace":
                lines_removed += i2 - i1
                lines_added += j2 - j1
            elif tag == "delete":
                lines_removed += i2 - i1
            elif tag == "insert":
                lines_added += j2 - j1

            context_start = max(0, i1 - config.context_lines)
            context_end = min(len(mod_lines), j2 + config.context_lines)

            hunk_lines: list[str] = []
            if context_start < i1:
                hunk_lines.extend(
                    f" {l}" if not l.endswith("\n") else f" {l}"
                    for l in orig_lines[context_start:i1]
                )
            for l in orig_lines[i1:i2]:
                hunk_lines.append(
                    f"-{l}" if l.endswith("\n") else f"-{l}\n"
                )
            for l in mod_lines[j1:j2]:
                hunk_lines.append(
                    f"+{l}" if l.endswith("\n") else f"+{l}\n"
                )
            if j2 < context_end:
                hunk_lines.extend(
                    f" {l}" if not l.endswith("\n") else f" {l}"
                    for l in mod_lines[j2:context_end]
                )

            change_type = tag
            hunk = DiffHunk(
                start_line_old=i1 + 1,
                end_line_old=i2,
                start_line_new=j1 + 1,
                end_line_new=j2,
                content="".join(hunk_lines),
                change_type=change_type,
            )
            hunks.append(hunk)

        semantic_summary = (
            f"{lines_added} additions, {lines_removed} deletions "
            f"across {len(hunks)} hunk(s)"
        )

        return DiffResult(
            file_path="",
            hunks=tuple(hunks),
            lines_added=lines_added,
            lines_removed=lines_removed,
            semantic_summary=semantic_summary,
        )

    @staticmethod
    async def batch_diff(
        file_pairs: tuple[tuple[str, str, str], ...],
    ) -> tuple[DiffResult, ...]:
        """Compute diffs for multiple file pairs in batch."""
        results: list[DiffResult] = []
        for file_path, original, modified in file_pairs:
            result = await DiffGenerator.compute_diff(original, modified)
            result = DiffResult(
                file_path=file_path,
                hunks=result.hunks,
                lines_added=result.lines_added,
                lines_removed=result.lines_removed,
                semantic_summary=result.semantic_summary,
            )
            results.append(result)
        return tuple(results)

    @staticmethod
    def summarize_changes(diff: DiffResult) -> str:
        """Produce a human-readable summary of changes."""
        parts: list[str] = []
        if diff.lines_added > 0:
            parts.append(f"{diff.lines_added} line(s) added")
        if diff.lines_removed > 0:
            parts.append(f"{diff.lines_removed} line(s) removed")
        if diff.hunks:
            change_types = sorted({h.change_type for h in diff.hunks})
            parts.append(f"changes: {', '.join(change_types)}")
        return "; ".join(parts) if parts else "No changes"
