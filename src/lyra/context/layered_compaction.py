"""
Layered Compaction Engine — threshold-escalating context compression for Lyra.

Provides three compression layers with escalating sophistication:

1. **Layer 1 (fast / truncate)** — Drops messages below a recency/importance
   threshold using simple heuristic scoring.
2. **Layer 2 (medium / summarize)** — Summarises conversation chunks via a
   cheap model call (heuristic placeholder for real model summarisation).
3. **Layer 3 (deep / semantic)** — Applies embedding-clustering-based semantic
   compression to collapse semantically similar turns.

The engine escalates through layers automatically: it starts with Layer 1,
checks whether the result fits the token budget, and if not proceeds to
Layer 2, then Layer 3.

Also provides:

- ``CompositeRetentionScore`` — weighted sum of importance, recency, and
  relevance heuristics used by Layers 1 and 2.
- ``StructuralCodeProtection`` — AST-aware helper that prevents code blocks
  from being truncated or summarised.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

_TRUNCATION_MARKER = "[...truncated by Lyra Layered Compaction...]"

# ---------------------------------------------------------------------------
# CompositeRetentionScore
# ---------------------------------------------------------------------------


@dataclass
class CompositeRetentionScore:
    """Weighted heuristic scoring for message retention value.

    The composite score combines three dimensions:

    - ``importance`` (0.0–1.0): How important this message is for task
      completion (system messages, critical decisions get high scores).
    - ``recency`` (0.0–1.0): How recently the message was written.
    - ``relevance`` (0.0–1.0): How relevant the message is to the current
      task or query.

    The final score is ``w_i * importance + w_r * recency + w_v * relevance``.

    Attributes:
        w_importance: Weight for the importance dimension.
        w_recency:    Weight for the recency dimension.
        w_relevance:  Weight for the relevance dimension.
    """

    w_importance: float = 0.4
    w_recency: float = 0.35
    w_relevance: float = 0.25

    def compute(
        self,
        importance: float,
        recency: float,
        relevance: float,
    ) -> float:
        """Compute the weighted composite score.

        Args:
            importance: Importance score in [0.0, 1.0].
            recency:    Recency score in [0.0, 1.0].
            relevance:  Relevance score in [0.0, 1.0].

        Returns:
            Weighted composite score in [0.0, 1.0].
        """
        return (
            self.w_importance * importance
            + self.w_recency * recency
            + self.w_relevance * relevance
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "w_importance": self.w_importance,
            "w_recency": self.w_recency,
            "w_relevance": self.w_relevance,
        }


# ---------------------------------------------------------------------------
# StructuralCodeProtection
# ---------------------------------------------------------------------------


class StructuralCodeProtection:
    """AST-aware helper that protects code blocks from compaction.

    When asked to protect a message, it checks whether the content contains
    valid code blocks (fenced with ```) and returns metadata about them so
    that upper layers can redact or skip those portions.

    The protection is *structural*: it looks for fenced code blocks and
    optionally tries to parse Python blocks with ``ast.parse`` to confirm
    syntactic validity. Non-Python blocks are still protected structurally.
    """

    def __init__(self, languages: set[str] | None = None) -> None:
        """Initialise code protection.

        Args:
            languages: Set of languages to AST-validate (default: ``{"python"}``).
        """
        self._languages: set[str] = languages or {"python"}

    def has_code(self, content: str) -> bool:
        """Check whether *content* contains at least one code block.

        Args:
            content: Message text.

        Returns:
            True if at least one fenced code block is found.
        """
        return bool(_CODE_BLOCK_RE.search(content))

    def protect(self, content: str) -> str:
        """Return content with code blocks structurally protected.

        Protected code blocks are wrapped with markers so that downstream
        compaction layers can skip or re-insert them later.

        For now this is a *identity* placeholder — the engine calls it to
        tag blocks. In a real implementation this would replace blocks with
        a placeholder token, run compaction, then re-insert.

        Args:
            content: Original message text.

        Returns:
            Content with code blocks structurally annotated (currently
            returns the content unchanged with metadata available via
            :meth:`extract_blocks`).
        """
        return content

    def extract_blocks(self, content: str) -> list[dict[str, Any]]:
        """Extract metadata for all fenced code blocks in content.

        Returns a list of dicts, each with:

        - ``language``: The language tag (e.g. ``"python"``, ``""``).
        - ``start``: Character offset of the block opening.
        - ``end``: Character offset of the block closing.
        - ``valid_syntax``: For known languages, whether the block parses
          as valid AST.

        Args:
            content: Message text.

        Returns:
            List of code block metadata dicts.
        """
        blocks: list[dict[str, Any]] = []
        for match in _CODE_BLOCK_RE.finditer(content):
            lang = match.group(1).strip()
            code = match.group(0)
            valid: bool | None = None
            if lang in self._languages:
                valid = self._validate_syntax(code, lang)
            blocks.append({
                "language": lang,
                "start": match.start(),
                "end": match.end(),
                "valid_syntax": valid,
            })
        return blocks

    @staticmethod
    def _validate_syntax(code: str, language: str) -> bool:
        """Return True if *code* is syntactically valid for *language*.

        Strips the outer fence markers before parsing so that only the
        inner code content is validated. Only supports Python currently.
        """
        if language == "python":
            # Strip the outer fence markers: ```python\n...\n```
            lines = code.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]  # drop fence opening line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # drop fence closing line
            inner = "\n".join(lines)
            try:
                ast.parse(inner)
                return True
            except SyntaxError:
                return False
        return True  # unknown languages treated as valid


# ---------------------------------------------------------------------------
# LayeredCompactionEngine
# ---------------------------------------------------------------------------


@dataclass
class LayeredCompactionEngine:
    """Threshold-escalating layered context compressor.

    Usage::

        engine = LayeredCompactionEngine()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        compressed, trace = engine.compress(messages, target_token_budget=50)
        # ``compressed`` : list of dict messages
        # ``trace``       : dict with layer info
    """

    # Token budget at which we escalate to the next layer
    layer1_budget: int = 4096
    layer2_budget: int = 2048
    # Retained if a message's composite score is >= threshold
    layer1_threshold: float = 0.35
    layer2_threshold: float = 0.25

    # Number of most recent turns always kept by Layer 1
    keep_recent: int = 5

    # Weights for composite scoring
    retention_weights: CompositeRetentionScore = field(
        default_factory=CompositeRetentionScore,
    )

    # Code protection helper
    code_protector: StructuralCodeProtection = field(
        default_factory=StructuralCodeProtection,
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(
        self,
        messages: list[dict[str, str]],
        target_token_budget: int | None = None,
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Compress *messages* to fit *target_token_budget*.

        Escalation flow:

        1. Try **Layer 1** (fast truncation). If the result fits within
           *target_token_budget* (or ``layer1_budget``), return it.
        2. Otherwise try **Layer 2** (medium summarisation). If the
           result fits, return it.
        3. Otherwise apply **Layer 3** (deep semantic compression).

        Args:
            messages: List of messages to compress.
            target_token_budget: Maximum tokens the compressed output
                should occupy. Falls back to ``layer1_budget`` if unset.

        Returns:
            Tuple of ``(compressed_messages, trace_dict)`` where
            *trace_dict* contains the layer that was applied, token
            counts, and which messages were kept.

        Raises:
            ValueError: If *messages* is empty.
        """
        if not messages:
            raise ValueError("Cannot compress an empty message list")

        budget = target_token_budget or self.layer1_budget
        original_tokens = self._estimate_tokens(messages)

        # --- Layer 1: fast truncation ---
        compressed_l1, trace_l1 = self._layer1_truncate(
            messages, budget,
        )
        l1_tokens = self._estimate_tokens(compressed_l1)
        if l1_tokens <= budget:
            return compressed_l1, {
                "layer": 1,
                "original_tokens": original_tokens,
                "compressed_tokens": l1_tokens,
                "budget": budget,
                "messages_in": len(messages),
                "messages_out": len(compressed_l1),
                "details": trace_l1,
            }

        # --- Layer 2: medium summarisation ---
        compressed_l2, trace_l2 = self._layer2_summarise(
            messages, budget,
        )
        l2_tokens = self._estimate_tokens(compressed_l2)
        if l2_tokens <= budget:
            return compressed_l2, {
                "layer": 2,
                "original_tokens": original_tokens,
                "compressed_tokens": l2_tokens,
                "budget": budget,
                "messages_in": len(messages),
                "messages_out": len(compressed_l2),
                "details": trace_l2,
            }

        # --- Layer 3: deep semantic compression ---
        compressed_l3, trace_l3 = self._layer3_deep_compress(
            messages, budget,
        )
        l3_tokens = self._estimate_tokens(compressed_l3)

        return compressed_l3, {
            "layer": 3,
            "original_tokens": original_tokens,
            "compressed_tokens": l3_tokens,
            "budget": budget,
            "messages_in": len(messages),
            "messages_out": len(compressed_l3),
            "details": trace_l3,
        }

    # ------------------------------------------------------------------
    # Layer 1 — Fast truncation
    # ------------------------------------------------------------------

    def _layer1_truncate(
        self,
        messages: list[dict[str, str]],
        budget: int,
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Truncate old low-value messages.

        Keeps:
        - System messages unconditionally.
        - The ``keep_recent`` most recent non-system messages.
        - Any message whose :class:`CompositeRetentionScore` is above
          ``layer1_threshold``.

        Remaining low-score messages are dropped.
        """
        result: list[dict[str, str]] = []
        n = len(messages)
        dropped_count = 0
        system_msg: dict[str, str] | None = None

        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Always keep system message
            if role == "system":
                system_msg = msg
                continue

            # Always keep recent messages
            if n - i <= self.keep_recent:
                result.append(msg)
                continue

            # Score and decide
            score = self._compute_retention_score(
                msg, i, n,
            )
            if score >= self.layer1_threshold:
                result.append(msg)
            else:
                dropped_count += 1

        # Prepend system message if present
        if system_msg is not None:
            result.insert(0, system_msg)

        return result, {
            "layer": 1,
            "dropped": dropped_count,
            "kept": len(result),
            "threshold_used": self.layer1_threshold,
        }

    # ------------------------------------------------------------------
    # Layer 2 — Medium summarisation
    # ------------------------------------------------------------------

    def _layer2_summarise(
        self,
        messages: list[dict[str, str]],
        budget: int,
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Summarize conversation chunks using heuristics.

        In a production system this would call a cheap model (e.g. Haiku).
        Here we use a heuristic approach:

        1. Identify chunks of low-value user/assistant back-and-forth.
        2. Replace each chunk with a single condensed message.
        3. Preserve system messages, code blocks, and recent turns.
        """
        result: list[dict[str, str]] = []
        summarised_chunks = 0
        system_msg: dict[str, str] | None = None
        n = len(messages)

        i = 0
        while i < n:
            msg = messages[i]
            role = msg.get("role", "")

            # Preserve system message
            if role == "system":
                system_msg = msg
                i += 1
                continue

            # Preserve recent messages
            if n - i <= self.keep_recent:
                result.append(msg)
                i += 1
                continue

            content = msg.get("content", "")

            # Protect code-containing messages from summarisation
            if self.code_protector.has_code(content):
                result.append(msg)
                i += 1
                continue

            score = self._compute_retention_score(msg, i, n)

            # If high score, keep as-is
            if score >= self.layer2_threshold:
                result.append(msg)
                i += 1
                continue

            # Low score: try to merge with adjacent low-score turns
            chunk: list[dict[str, str]] = [msg]
            j = i + 1
            while j < n:
                next_msg = messages[j]
                next_role = next_msg.get("role", "")
                if next_role == "system":
                    break
                if n - j <= self.keep_recent:
                    break
                if self.code_protector.has_code(next_msg.get("content", "")):
                    break
                next_score = self._compute_retention_score(next_msg, j, n)
                if next_score >= self.layer2_threshold:
                    break
                chunk.append(next_msg)
                j += 1

            # Replace chunk with a single summarised message
            summary = self._heuristic_summarise_chunk(chunk)
            result.append({
                "role": "user",
                "content": f"[Summarised {len(chunk)} turns] {summary}",
            })
            summarised_chunks += 1
            i = j

        if system_msg is not None:
            result.insert(0, system_msg)

        return result, {
            "layer": 2,
            "summarised_chunks": summarised_chunks,
            "kept": len(result),
            "threshold_used": self.layer2_threshold,
        }

    # ------------------------------------------------------------------
    # Layer 3 — Deep semantic compression
    # ------------------------------------------------------------------

    def _layer3_deep_compress(
        self,
        messages: list[dict[str, str]],
        budget: int,
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Apply embedding-clustering-style semantic compression.

        In a real system this would:
        1. Embed each message.
        2. Cluster semantically similar messages.
        3. Replace each cluster with a prototype / centroid message.

        Here we use a heuristic proxy: messages with very similar content
        lengths and roles are grouped and deduplicated.
        """
        result: list[dict[str, str]] = []
        system_msg: dict[str, str] | None = None
        merged_count = 0
        n = len(messages)

        # Group consecutive messages by role proximity
        i = 0
        while i < n:
            msg = messages[i]
            role = msg.get("role", "")

            if role == "system":
                system_msg = msg
                i += 1
                continue

            if n - i <= self.keep_recent:
                result.append(msg)
                i += 1
                continue

            # Protect code messages
            if self.code_protector.has_code(msg.get("content", "")):
                result.append(msg)
                i += 1
                continue

            # Find semantically similar consecutive messages (heuristic:
            # same role, similar content length)
            content = msg.get("content", "")
            cluster: list[dict[str, str]] = [msg]
            j = i + 1
            while j < n:
                next_msg = messages[j]
                if next_msg.get("role", "") != role:
                    break
                if n - j <= self.keep_recent:
                    break
                if self.code_protector.has_code(next_msg.get("content", "")):
                    break
                # Length-similarity heuristic
                next_len = len(next_msg.get("content", ""))
                current_len = len(content)
                if max(current_len, next_len) > 0:
                    ratio = min(current_len, next_len) / max(current_len, next_len)
                    if ratio < 0.5:
                        break  # lengths too different — stop clustering
                cluster.append(next_msg)
                j += 1

            if len(cluster) > 1:
                # Merge cluster into a single representative message
                merged = self._heuristic_merge_cluster(cluster)
                result.append(merged)
                merged_count += len(cluster) - 1
            else:
                result.append(msg)

            i = j

        if system_msg is not None:
            result.insert(0, system_msg)

        return result, {
            "layer": 3,
            "clusters_merged": merged_count,
            "kept": len(result),
        }

    # ------------------------------------------------------------------
    # Heuristic helpers (stand-ins for real model calls)
    # ------------------------------------------------------------------

    @staticmethod
    def _heuristic_summarise_chunk(chunk: list[dict[str, str]]) -> str:
        """Heuristic summary of a chunk of conversation turns.

        In production this would call a cheap model. Here we concatenate
        the core content of each turn.
        """
        parts: list[str] = []
        for c in chunk:
            role = c.get("role", "unknown")
            text = c.get("content", "")
            # Truncate long content within the chunk
            if len(text) > 200:
                text = text[:200] + "..."
            parts.append(f"[{role}] {text}")
        return " | ".join(parts)

    @staticmethod
    def _heuristic_merge_cluster(
        cluster: list[dict[str, str]],
    ) -> dict[str, str]:
        """Merge a cluster of similar messages into one representative.

        Picks the longest message as representative and notes the count.
        """
        rep = max(cluster, key=lambda m: len(m.get("content", "")))
        return {
            "role": rep.get("role", "user"),
            "content": f"[Merged {len(cluster)} similar turns] {rep.get('content', '')}",
        }

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _compute_retention_score(
        self,
        msg: dict[str, str],
        index: int,
        total: int,
    ) -> float:
        """Compute a composite retention score for a single message.

        Args:
            msg:   The message dict.
            index: Zero-based index in the original list.
            total: Total number of messages.

        Returns:
            Float in [0.0, 1.0].
        """
        importance = self._importance_heuristic(msg)
        recency = self._recency_score(index, total)
        relevance = self._relevance_heuristic(msg)
        return self.retention_weights.compute(importance, recency, relevance)

    @staticmethod
    def _importance_heuristic(msg: dict[str, str]) -> float:
        """Heuristic for message importance.

        - System messages: 1.0
        - Assistant messages with medium content: 0.8
        - User messages: 0.6
        - Tool result messages: 0.3
        """
        role = msg.get("role", "")
        if role == "system":
            return 1.0
        if role == "assistant":
            return 0.8
        if role in ("tool", "tool_result"):
            return 0.3
        return 0.6  # user

    @staticmethod
    def _recency_score(index: int, total: int) -> float:
        """Linear recency score — newer messages score higher."""
        if total <= 1:
            return 1.0
        return (index + 1) / total

    @staticmethod
    def _relevance_heuristic(msg: dict[str, str]) -> float:
        """Heuristic for message relevance based on content length.

        Very short messages may be acknowledgements (low relevance).
        Very long tool results are often bulky (moderate relevance).
        Medium-length assistant responses are most relevant.
        """
        content = msg.get("content", "")
        length = len(content)
        if length < 10:
            return 0.3
        if length > 5000:
            return 0.5
        if msg.get("role") == "assistant":
            return 0.9
        return 0.7

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(messages: list[dict[str, str]]) -> int:
        """Rough token estimate: 1 token per 4 characters."""
        total = sum(len(m.get("content", "")) for m in messages)
        if total == 0:
            return 0
        return max(1, total // 4)

    @staticmethod
    def _message_tokens(msg: dict[str, str]) -> int:
        """Token estimate for a single message."""
        return max(1, len(msg.get("content", "")) // 4)


__all__ = [
    "CompositeRetentionScore",
    "LayeredCompactionEngine",
    "StructuralCodeProtection",
]
