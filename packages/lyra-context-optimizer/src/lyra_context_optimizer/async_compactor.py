"""Parallel compactor + judge for async compaction (Slipstream pattern).

Runs compaction in parallel with agent operations and validates quality
via a judge that checks information preservation, key fact retention,
and instruction clarity. Rollback on judge rejection.

Targets +8.8pp accuracy improvement and -39.7% latency reduction.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .agent_driven_compaction import CompactionAction, CompactionStrategy
from .exceptions import CompactionError, FidelityLossError


class JudgeVerdict(Enum):
    """Verdict from the compaction judge."""

    PASS = auto()
    FAIL = auto()
    NEEDS_REVIEW = auto()


@dataclass(frozen=True)
class JudgeCriteria:
    """Criteria used by the compaction judge.

    Attributes:
        information_preservation: Score for how well information is preserved
            (0.0 to 1.0).
        key_fact_retention: Score for how many key facts are retained
            (0.0 to 1.0).
        instruction_clarity: Score for how clear instructions remain
            (0.0 to 1.0).
        structure_preservation: Score for structure integrity
            (0.0 to 1.0).
    """

    information_preservation: float
    key_fact_retention: float
    instruction_clarity: float
    structure_preservation: float = 1.0

    @property
    def overall_score(self) -> float:
        """Weighted overall quality score."""
        return (
            self.information_preservation * 0.35
            + self.key_fact_retention * 0.35
            + self.instruction_clarity * 0.20
            + self.structure_preservation * 0.10
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "information_preservation": self.information_preservation,
            "key_fact_retention": self.key_fact_retention,
            "instruction_clarity": self.instruction_clarity,
            "structure_preservation": self.structure_preservation,
            "overall_score": self.overall_score,
        }


class CompactionJudge:
    """Validates compaction quality against the original content.

    Evaluates compaction results on four criteria and decides whether
    the compaction is acceptable or should be rolled back.
    """

    def __init__(self, pass_threshold: float = 0.8) -> None:
        self.pass_threshold = pass_threshold
        self._history: list[dict[str, Any]] = []

    async def evaluate(
        self,
        original: str,
        compacted: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[JudgeVerdict, JudgeCriteria]:
        """Evaluate compaction quality.

        Analyzes information preservation, key fact retention, and
        instruction clarity by comparing original and compacted content.

        Args:
            original: Original content before compaction.
            compacted: Compacted content to evaluate.
            metadata: Optional metadata about the compaction.

        Returns:
            Tuple of (verdict, criteria_scores).
        """
        if not compacted:
            return JudgeVerdict.FAIL, JudgeCriteria(
                information_preservation=0.0,
                key_fact_retention=0.0,
                instruction_clarity=0.0,
                structure_preservation=0.0,
            )
        if compacted == original:
            return JudgeVerdict.PASS, JudgeCriteria(
                information_preservation=1.0,
                key_fact_retention=1.0,
                instruction_clarity=1.0,
                structure_preservation=1.0,
            )

        # Simulate evaluation with async-friendly computation
        info_score, key_score, clarity_score, struct_score = await asyncio.gather(
            self._evaluate_information_preservation(original, compacted),
            self._evaluate_key_fact_retention(original, compacted),
            self._evaluate_instruction_clarity(compacted),
            self._evaluate_structure_preservation(original, compacted),
        )

        criteria = JudgeCriteria(
            information_preservation=info_score,
            key_fact_retention=key_score,
            instruction_clarity=clarity_score,
            structure_preservation=struct_score,
        )

        overall = criteria.overall_score
        if overall >= self.pass_threshold:
            verdict = JudgeVerdict.PASS
        elif overall >= self.pass_threshold * 0.8:
            verdict = JudgeVerdict.NEEDS_REVIEW
        else:
            verdict = JudgeVerdict.FAIL

        self._history.append({
            "timestamp": time.time(),
            "original_length": len(original),
            "compacted_length": len(compacted),
            "verdict": verdict.name,
            "overall_score": overall,
            "criteria": criteria.to_dict(),
            "metadata": metadata or {},
        })

        return verdict, criteria

    async def _evaluate_information_preservation(
        self, original: str, compacted: str
    ) -> float:
        """Evaluate how well information content is preserved.

        Compares token overlap between original and compacted content.
        """
        original_tokens = set(original.split())
        compacted_tokens = set(compacted.split())

        if not original_tokens:
            return 1.0
        if not compacted_tokens:
            return 0.0

        overlap = len(original_tokens & compacted_tokens)
        coverage = overlap / len(original_tokens)
        # Penalize if compacted is much smaller
        length_penalty = max(0.0, 1.0 - len(compacted) / max(len(original), 1) * 3)
        return max(0.0, min(1.0, coverage * 0.8 + (1.0 - length_penalty) * 0.2))

    async def _evaluate_key_fact_retention(
        self, original: str, compacted: str
    ) -> float:
        """Evaluate retention of key facts.

        Extracts key terms (capitalized words, numbers, technical terms)
        and checks what fraction is retained.
        """
        import re

        key_pattern = re.compile(
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b\d+(?:\.\d+)?\b|`[^`]+`"
        )
        original_keys = set(key_pattern.findall(original))
        compacted_keys = set(key_pattern.findall(compacted))

        if not original_keys:
            return 1.0
        retained = len(original_keys & compacted_keys)
        return retained / len(original_keys)

    async def _evaluate_instruction_clarity(self, compacted: str) -> float:
        """Evaluate instruction clarity in compacted content.

        Measures readability: sentence length, structure markers,
        command presence.
        """
        import re

        sentences = re.split(r"[.!?]+", compacted)
        if not sentences:
            return 0.5

        # Penalize very long or very short sentences
        clarity_by_length = 0.0
        for s in sentences:
            word_count = len(s.split())
            if 5 <= word_count <= 30:
                clarity_by_length += 1.0
            elif word_count < 5:
                clarity_by_length += 0.5
            else:
                clarity_by_length += max(0.0, 1.0 - (word_count - 30) / 50)

        avg_clarity = clarity_by_length / len(sentences) if sentences else 0.5

        # Bonus for well-structured content
        has_bullets = " - " in compacted or " * " in compacted
        has_numbers = any(c.isdigit() for c in compacted)
        structure_bonus = (0.1 if has_bullets else 0.0) + (0.05 if has_numbers else 0.0)

        return min(1.0, avg_clarity + structure_bonus)

    async def _evaluate_structure_preservation(
        self, original: str, compacted: str
    ) -> float:
        """Evaluate whether structural elements are preserved.

        Checks for preserved code blocks, headers, lists, etc.
        """
        import re

        # Count structural elements in original and compacted
        struct_patterns = [
            r"```[\s\S]*?```",  # code blocks
            r"^#{1,6}\s",  # headers
            r"^\s*[-*]\s",  # list items
            r"^\s*\d+\.\s",  # numbered lists
        ]

        original_count = 0
        preserved_count = 0
        for pattern in struct_patterns:
            orig_matches = set(re.findall(pattern, original, re.MULTILINE))
            comp_matches = set(re.findall(pattern, compacted, re.MULTILINE))
            original_count += len(orig_matches)
            preserved_count += len(orig_matches & comp_matches)

        if original_count == 0:
            return 1.0
        return preserved_count / original_count

    @property
    def history(self) -> list[dict[str, Any]]:
        """Get judge evaluation history."""
        return list(self._history)

    @property
    def pass_rate(self) -> float:
        """Get overall pass rate across all evaluations."""
        if not self._history:
            return 1.0
        passes = sum(1 for h in self._history if h["verdict"] == "PASS")
        return passes / len(self._history)


class AsyncCompactor:
    """Async compactor that runs compaction in parallel with agent operations.

    The compactor creates a concurrent task that applies compaction while
    the agent continues its primary work (Slipstream pattern). Once both
    complete, a judge validates the result and rolls back if needed.

    Targets +8.8pp accuracy improvement and -39.7% latency vs. synchronous
    compaction.
    """

    def __init__(
        self,
        judge: CompactionJudge | None = None,
        pass_threshold: float = 0.8,
    ) -> None:
        self.judge = judge or CompactionJudge(pass_threshold=pass_threshold)
        self._history: list[dict[str, Any]] = []

    async def compact_async(
        self,
        context: str,
        *,
        target_ratio: float = 0.3,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, CompactionAction | None]:
        """Run compaction asynchronously with judge validation.

        Compacts the context in a concurrent task, evaluates the result,
        and rolls back if quality is insufficient.

        Args:
            context: The context to compact.
            target_ratio: Target compression ratio (0.0 to 1.0).
            metadata: Optional metadata.

        Returns:
            Tuple of (compacted_context, compaction_action or None on rollback).

        Raises:
            CompactionError: If context is empty.
        """
        if not context:
            raise CompactionError("empty context provided")

        start_time = time.time()
        original_length = len(context)
        target_tokens = max(1, int(len(context) * (1.0 - target_ratio)))

        # Run compaction as a concurrent task
        compactor_task = asyncio.create_task(
            self._compact_internal(context, target_tokens)
        )

        # Simulate parallel agent work (in production, the agent runs here)
        await asyncio.sleep(0.001)

        # Await the compaction result
        compacted, action = await compactor_task

        if action is None:
            elapsed = (time.time() - start_time) * 1000
            return context, CompactionAction(
                strategy=CompactionStrategy.DEFER,
                tokens_before=original_length,
                tokens_after=original_length,
                tokens_saved=0,
                fidelity_score=1.0,
                time_taken_ms=elapsed,
                reason="Compactor produced no output",
            )

        # Judge the compaction quality
        verdict, criteria = await self.judge.evaluate(
            context, compacted, metadata
        )

        elapsed = (time.time() - start_time) * 1000
        action = CompactionAction(
            strategy=action.strategy,
            tokens_before=action.tokens_before,
            tokens_after=action.tokens_after,
            tokens_saved=action.tokens_saved,
            blocks_removed=action.blocks_removed,
            blocks_summarized=action.blocks_summarized,
            fidelity_score=criteria.overall_score,
            time_taken_ms=elapsed,
            reason=f"Judge verdict: {verdict.name} | {action.reason}",
        )

        if verdict == JudgeVerdict.FAIL:
            # Rollback: return original context
            self._history.append({
                "timestamp": time.time(),
                "original_length": original_length,
                "compacted_length": len(compacted),
                "verdict": "ROLLBACK",
                "elapsed_ms": elapsed,
                "criteria": criteria.to_dict(),
            })
            return context, None

        if verdict == JudgeVerdict.NEEDS_REVIEW:
            # Partial compaction: return somewhat compacted
            intermediate = self._partial_rollback(context, compacted)
            self._history.append({
                "timestamp": time.time(),
                "original_length": original_length,
                "compacted_length": len(intermediate),
                "verdict": "PARTIAL",
                "elapsed_ms": elapsed,
                "criteria": criteria.to_dict(),
            })
            return intermediate, action

        # PASS
        self._history.append({
            "timestamp": time.time(),
            "original_length": original_length,
            "compacted_length": len(compacted),
            "verdict": "PASS",
            "elapsed_ms": elapsed,
            "criteria": criteria.to_dict(),
        })
        return compacted, action

    async def _compact_internal(
        self, context: str, target_tokens: int
    ) -> tuple[str, CompactionAction | None]:
        """Internal compaction logic.

        Applies compression to reduce the context to the target size.
        """
        if len(context) <= target_tokens:
            return context, CompactionAction(
                strategy=CompactionStrategy.DEFER,
                tokens_before=len(context),
                tokens_after=len(context),
                tokens_saved=0,
                fidelity_score=1.0,
                reason="Context already within target size",
            )

        # Simple compression: token-aware truncation from middle
        lines = context.splitlines(keepends=True)
        keep_lines = max(int(len(lines) * (target_tokens / max(len(context), 1)) * 4), 10)

        if len(lines) <= keep_lines:
            return context, None

        head_count = keep_lines // 2
        tail_count = keep_lines - head_count

        compacted_lines = lines[:head_count] + lines[-tail_count:]

        compacted = "".join(compacted_lines)
        tokens_saved = len(context) - len(compacted)

        action = CompactionAction(
            strategy=CompactionStrategy.PRUNE,
            tokens_before=len(context),
            tokens_after=len(compacted),
            tokens_saved=tokens_saved,
            fidelity_score=0.9,
            reason=f"Async truncated from {len(lines)} to {keep_lines} lines",
        )

        return compacted, action

    @staticmethod
    def _partial_rollback(original: str, compacted: str) -> str:
        """Partially restore content from compaction.

        Returns a blend of original and compacted content weighted
        toward the original.
        """
        # Restore first section of original to give more context
        lines_original = original.splitlines()
        lines_compacted = compacted.splitlines()

        if len(lines_compacted) >= len(lines_original):
            return original

        # Blend: first 60% from compacted, last 40% expand
        split_point = int(len(lines_compacted) * 0.6)
        restored = lines_compacted[:split_point]

        # Add back some lines from the original that were removed
        removed = lines_original[len(lines_compacted) :]
        restored.extend(removed[: int(len(removed) * 0.3)])

        return "\n".join(restored)

    @property
    def summary(self) -> dict[str, Any]:
        """Get compactor summary."""
        total_ops = len(self._history)
        passes = sum(1 for h in self._history if h["verdict"] == "PASS")
        rollbacks = sum(1 for h in self._history if h["verdict"] == "ROLLBACK")
        avg_time = (
            sum(h["elapsed_ms"] for h in self._history) / total_ops
            if total_ops > 0
            else 0.0
        )

        return {
            "total_operations": total_ops,
            "pass_count": passes,
            "rollback_count": rollbacks,
            "judge_pass_rate": self.judge.pass_rate,
            "avg_elapsed_ms": avg_time,
        }
