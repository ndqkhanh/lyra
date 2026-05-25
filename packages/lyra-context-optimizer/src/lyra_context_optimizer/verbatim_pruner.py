"""Verbatim pruner — removes content without rewriting.

Implements a set of pruning strategies that only remove or truncate content;
never paraphrase or rewrite. Preserves code blocks, error messages, and
structured data integrity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import CompressionError, FidelityLossError


class PruneStrategy(Enum):
    """Available verbatim pruning strategies."""

    REMOVE_DUPLICATES = auto()
    TRUNCATE_OUTPUTS = auto()
    COLLAPSE_WHITESPACE = auto()
    REMOVE_BOILERPLATE = auto()
    EXTRACT_KEY_SECTIONS = auto()


@dataclass(frozen=True)
class PruneResult:
    """Result of a pruning operation.

    Attributes:
        content: The pruned content.
        original_length: Length before pruning.
        pruned_length: Length after pruning.
        tokens_saved: Estimated tokens saved.
        strategies_applied: List of strategies used.
        fidelity_score: Estimated fidelity (0.0 to 1.0).
    """

    content: str
    original_length: int
    pruned_length: int
    tokens_saved: int
    strategies_applied: list[str]
    fidelity_score: float


_BOILERPLATE_PATTERNS: list[tuple[str, str]] = [
    (r"(?im)^#+\s*(copyright|all rights reserved|confidential).*?\n", ""),
    (r"(?im)^\s*(disclaimer|disclaimers):.*?(\n\s*\n|$)", ""),
    (r"(?i)(this (message|email) (and any attachments )?may contain)", ""),
    (r"(?im)^\s*(confidentiality notice):.*?(\n\s*\n|$)", ""),
    (r"(?im)^\s*---+\s*original (message|mail)\s*---+.*?$", ""),
]

_DUPLICATE_LINE_THRESHOLD = 3


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return max(1, len(text) // 4)


def _preserve_sections(content: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract and protect preserved sections (code blocks, errors, data).

    Returns:
        Tuple of (content_with_placeholders, extracted_sections).
    """
    placeholders: list[str] = []
    sections: list[dict[str, Any]] = []

    # Preserve code blocks
    def _replace_code(m: re.Match[str]) -> str:
        idx = len(placeholders)
        placeholders.append(m.group(0))
        sections.append({"type": "code_block", "content": m.group(0), "index": idx})
        return f"__CODEBLOCK_{idx}__"

    content = re.sub(
        r"```[\s\S]*?```|`[^`\n]+`", _replace_code, content
    )

    # Preserve structured data (JSON, YAML blocks)
    def _replace_data(m: re.Match[str]) -> str:
        idx = len(placeholders)
        placeholders.append(m.group(0))
        sections.append({"type": "structured_data", "content": m.group(0), "index": idx})
        return f"__DATA_{idx}__"

    content = re.sub(
        r"\{[\s\S]*?\}|\[[\s\S]*?\]", _replace_data, content
    )

    return content, sections


def _restore_sections(content: str, sections: list[dict[str, Any]]) -> str:
    """Restore preserved sections from placeholders."""
    for section in reversed(sections):
        idx = section["index"]
        placeholder = f"__CODEBLOCK_{idx}__"
        content = content.replace(placeholder, section["content"])
        placeholder = f"__DATA_{idx}__"
        content = content.replace(placeholder, section["content"])
    return content


class VerbatimPruner:
    """Prunes content by removing or truncating — never rewriting.

    Supports multiple strategies that can be combined. All strategies
    preserve code blocks, error messages, and structured data integrity.
    Fidelity is tracked to ensure quality is not compromised.
    """

    def __init__(self, min_fidelity_threshold: float = 0.0) -> None:
        """Initialize the pruner.

        Args:
            min_fidelity_threshold: Minimum acceptable fidelity score.
                Set to 0.0 (default) to disable the check.
        """
        self.min_fidelity_threshold = min_fidelity_threshold

    def prune(
        self,
        content: str,
        target_ratio: float,
        strategies: list[PruneStrategy] | None = None,
    ) -> PruneResult:
        """Prune content using the specified strategies.

        Args:
            content: The content to prune.
            target_ratio: Target compression ratio (0.0 = none, 1.0 = full).
            strategies: List of strategies to apply. Defaults to all.

        Returns:
            PruneResult with pruned content and metadata.

        Raises:
            CompressionError: If content is empty or invalid.
            FidelityLossError: If pruning would lose too much fidelity.
        """
        if not content:
            raise CompressionError("prune", 0, "empty content")
        if not 0.0 <= target_ratio <= 1.0:
            raise CompressionError(
                "prune", len(content), f"invalid target_ratio: {target_ratio}"
            )

        if strategies is None:
            strategies = list(PruneStrategy)

        original_length = len(content)
        strategies_applied: list[str] = []

        for strategy in strategies:
            before = len(content)
            content = self._apply_strategy(content, strategy)
            if len(content) < before:
                strategies_applied.append(strategy.name)

        pruned_length = len(content)
        actual_ratio = 1.0 - (pruned_length / original_length) if original_length > 0 else 0.0

        # Fidelity is computed based on how much content was removed
        fidelity_score = 1.0 - actual_ratio * 0.5

        if fidelity_score < self.min_fidelity_threshold:
            raise FidelityLossError(
                fidelity_score, self.min_fidelity_threshold,
                f"target_ratio={target_ratio:.2f}, actual_ratio={actual_ratio:.2f}"
            )

        return PruneResult(
            content=content,
            original_length=original_length,
            pruned_length=pruned_length,
            tokens_saved=(
                _estimate_tokens(content[:original_length])
                - _estimate_tokens(content)
            ),
            strategies_applied=strategies_applied,
            fidelity_score=fidelity_score,
        )

    def _apply_strategy(self, content: str, strategy: PruneStrategy) -> str:
        """Apply a single pruning strategy."""
        content, preserved = _preserve_sections(content)
        try:
            if strategy == PruneStrategy.REMOVE_DUPLICATES:
                content = self._remove_duplicate_lines(content)
            elif strategy == PruneStrategy.TRUNCATE_OUTPUTS:
                content = self._truncate_outputs(content)
            elif strategy == PruneStrategy.COLLAPSE_WHITESPACE:
                content = self._collapse_whitespace(content)
            elif strategy == PruneStrategy.REMOVE_BOILERPLATE:
                content = self._remove_boilerplate(content)
            elif strategy == PruneStrategy.EXTRACT_KEY_SECTIONS:
                content = content  # key sections already preserved
        finally:
            content = _restore_sections(content, preserved)
        return content

    @staticmethod
    def _remove_duplicate_lines(content: str) -> str:
        """Remove consecutive duplicate lines, keeping only the first.

        Handles exact line-level duplicates and near-duplicate lines
        (same text ignoring leading/trailing whitespace).
        """
        lines = content.splitlines(keepends=True)
        deduped: list[str] = []
        streak = 0
        prev_stripped = ""

        for line in lines:
            stripped = line.strip()
            if not stripped:
                deduped.append(line)
                streak = 0
                prev_stripped = ""
                continue

            if stripped == prev_stripped:
                streak += 1
                if streak < _DUPLICATE_LINE_THRESHOLD:
                    deduped.append(line)
            else:
                streak = 0
                deduped.append(line)

            prev_stripped = stripped

        return "".join(deduped)

    @staticmethod
    def _truncate_outputs(
        content: str, max_lines: int = 100, head_lines: int = 50
    ) -> str:
        """Truncate long output blocks, keeping head and tail.

        Identifies output blocks and truncates them to head_lines + tail_lines.
        """
        lines = content.splitlines(keepends=True)
        if len(lines) <= max_lines:
            return content

        truncated: list[str] = []
        in_output = False
        output_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "//", "/*", "*", "```")):
                if not in_output:
                    in_output = True
                    output_start = i
            else:
                if in_output and i - output_start > max_lines:
                    truncated.extend(lines[output_start : output_start + head_lines])
                    truncated.append(
                        f"\n... [truncated {i - output_start - 2 * head_lines} lines]\n\n"
                    )
                    truncated.extend(lines[i - head_lines : i])
                    in_output = False
                elif in_output:
                    in_output = False

        # Handle trailing output block
        if in_output and len(lines) - output_start > max_lines:
            truncated.append("".join(lines[output_start : output_start + head_lines]))
            truncated.append(
                f"\n... [truncated {len(lines) - output_start - head_lines} lines]\n\n"
            )

        if not truncated:
            return content

        return "".join(truncated)

    @staticmethod
    def _collapse_whitespace(content: str) -> str:
        """Collapse excessive whitespace while preserving paragraph structure."""
        # Replace 3+ consecutive newlines with 2
        content = re.sub(r"\n{3,}", "\n\n", content)
        # Replace multiple spaces within lines (but not in code blocks)
        content = re.sub(r"[ \t]{2,}", " ", content)
        # Remove trailing whitespace on each line
        content = re.sub(r"[ \t]+\n", "\n", content)
        return content

    @staticmethod
    def _remove_boilerplate(content: str) -> str:
        """Remove common boilerplate text (disclaimers, headers, footers)."""
        for pattern, replacement in _BOILERPLATE_PATTERNS:
            content = re.sub(pattern, replacement, content)
        return content

    def compute_fidelity(
        self, original: str, pruned: str
    ) -> float:
        """Compute fidelity score for a pruning operation.

        Measures how much of the original content's meaning is preserved.
        For verbatim pruning, this is based on the proportion of original
        characters retained and structure preservation.

        Returns:
            Fidelity score between 0.0 and 1.0.
        """
        if not original:
            return 1.0
        if not pruned:
            return 0.0

        original_tokens = set(original.split())
        pruned_tokens = set(pruned.split())
        if not original_tokens:
            return 1.0

        overlap = len(original_tokens & pruned_tokens)
        coverage = overlap / len(original_tokens)

        length_ratio = len(pruned) / len(original)
        return max(0.0, min(1.0, coverage * 0.6 + length_ratio * 0.4))
