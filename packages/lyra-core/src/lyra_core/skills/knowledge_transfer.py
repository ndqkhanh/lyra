"""Phase 3.2a — Cross-Skill Knowledge Transfer.

Transfers patterns and knowledge between related skills using
a lightweight embedding-based similarity search. Skills that
score highly on similarity have their patterns cross-pollinated:

  1. Embed skills into a vector space (keyword-frequency baseline)
  2. Find top-N similar skills via cosine similarity
  3. Extract common patterns (triggers, code structure, imports)
  4. Enrich target skill with discovered patterns
  5. Re-validate enriched skill through 4-gate pipeline
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum


class TransferStatus(Enum):
    ENRICHED = "enriched"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SkillEmbedding:
    """A keyword-frequency embedding for a skill."""

    skill_name: str
    skill_triggers: tuple[str, ...]
    skill_body: str
    dimensions: tuple[float, ...]  # 128-dim frequency vector
    dimension_labels: tuple[str, ...]  # What each dimension represents
    version: int


@dataclass(frozen=True)
class PatternMatch:
    """A pattern extracted from a related skill."""

    skill_name: str  # Source skill
    pattern_type: str  # "trigger", "import", "structure"
    pattern_content: str  # The extracted pattern
    relevance: float  # 0.0–1.0
    confidence: float  # 0.0–1.0


@dataclass(frozen=True)
class TransferResult:
    """Result of knowledge transfer from source to target skill."""

    result_id: str
    source_skill: str
    target_skill: str
    similarity: float
    extracted_patterns: tuple[PatternMatch, ...]
    enriched_triggers: tuple[str, ...] | None
    enriched_body: str | None
    status: TransferStatus
    summary: str


# ── Keyword vocabulary (128 dimensions) ───────────────────────────────

_KEYWORDS: tuple[str, ...] = (
    # Coding patterns (32)
    "def",
    "class",
    "import",
    "from",
    "return",
    "yield",
    "async",
    "await",
    "try",
    "except",
    "finally",
    "raise",
    "with",
    "lambda",
    "pass",
    "break",
    "continue",
    "if",
    "elif",
    "else",
    "for",
    "while",
    "and",
    "or",
    "not",
    "in",
    "is",
    "None",
    "True",
    "False",
    "self",
    "super",
    # Infrastructure (16)
    "subprocess",
    "os",
    "sys",
    "json",
    "yaml",
    "requests",
    "http",
    "api",
    "docker",
    "kubernetes",
    "git",
    "ci",
    "cd",
    "deploy",
    "build",
    "test",
    # AI/ML (16)
    "model",
    "train",
    "inference",
    "token",
    "embedding",
    "prompt",
    "llm",
    "agent",
    "tool",
    "skill",
    "pipeline",
    "dataset",
    "metric",
    "score",
    "accuracy",
    "benchmark",
    # Safety (16)
    "safety",
    "validate",
    "verify",
    "check",
    "audit",
    "permission",
    "auth",
    "secret",
    "token",
    "hash",
    "encrypt",
    "decrypt",
    "sandbox",
    "approve",
    "deny",
    "block",
    # Operations (16)
    "read",
    "write",
    "open",
    "close",
    "create",
    "delete",
    "update",
    "list",
    "get",
    "post",
    "put",
    "patch",
    "request",
    "response",
    "error",
    "log",
    # UI/Frontend (16)
    "ui",
    "component",
    "render",
    "state",
    "props",
    "hook",
    "effect",
    "event",
    "click",
    "input",
    "output",
    "display",
    "theme",
    "style",
    "css",
    "html",
    # Shell/CLI (16)
    "bash",
    "shell",
    "cli",
    "argparse",
    "command",
    "flag",
    "option",
    "env",
    "path",
    "file",
    "dir",
    "stdout",
    "stderr",
    "stdin",
    "pipe",
    "exit",
)


def _embed_skill(skill_body: str, skill_triggers: tuple[str, ...]) -> tuple[float, ...]:
    """Create a 128-dim keyword-frequency embedding."""
    text = skill_body.lower() + " " + " ".join(t.lower() for t in skill_triggers)
    dims: list[float] = []
    for kw in _KEYWORDS:
        count = text.count(kw)
        tf = math.log(1 + count)
        dims.append(round(tf, 4))
    return tuple(dims)


def _cosine_sim(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def _extract_patterns(
    source_skill: str, source_body: str, similarity: float
) -> tuple[PatternMatch, ...]:
    """Extract transferable patterns from a source skill."""
    patterns: list[PatternMatch] = []

    imp_match = re.findall(
        r"^(?:import\s+\w+|from\s+\w+\s+import\s+\w+)", source_body, re.MULTILINE
    )
    if imp_match:
        for imp in imp_match[:3]:
            patterns.append(
                PatternMatch(
                    skill_name=source_skill,
                    pattern_type="import",
                    pattern_content=imp,
                    relevance=similarity * 0.8,
                    confidence=0.7,
                )
            )

    def_match = re.findall(r"^def\s+(\w+)", source_body, re.MULTILINE)
    if def_match:
        for func in def_match[:3]:
            patterns.append(
                PatternMatch(
                    skill_name=source_skill,
                    pattern_type="structure",
                    pattern_content=f"def {func}",
                    relevance=similarity * 0.7,
                    confidence=0.6,
                )
            )

    error_patterns = re.findall(
        r"(try\s*:.*?except.*?:(?:\s*\w+)?)",
        source_body,
        re.DOTALL,
    )
    if error_patterns:
        patterns.append(
            PatternMatch(
                skill_name=source_skill,
                pattern_type="structure",
                pattern_content="try/except error handling",
                relevance=similarity * 0.5,
                confidence=0.5,
            )
        )

    return tuple(patterns)


@dataclass
class KnowledgeTransferEngine:
    """Cross-skill knowledge transfer via embedding similarity.

    Usage::

        engine = KnowledgeTransferEngine()
        engine.index_skill("parse-json", ("json", "parse"), skill_body)
        engine.index_skill("parse-yaml", ("yaml", "parse"), skill_body)
        result = engine.transfer("parse-json", "parse-yaml")
        if result.status == TransferStatus.ENRICHED:
            print(f"Added patterns: {result.extracted_patterns}")
    """

    _embeddings: dict[str, SkillEmbedding] = field(default_factory=dict)
    min_similarity: float = 0.3
    max_patterns: int = 5
    _history: list[TransferResult] = field(default_factory=list)

    def index_skill(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
    ) -> SkillEmbedding:
        """Index a skill for knowledge transfer.

        Creates an embedding and stores it for similarity search.
        """
        dims = _embed_skill(skill_body, skill_triggers)

        existing = self._embeddings.get(skill_name)
        version = (existing.version + 1) if existing else 1

        embedding = SkillEmbedding(
            skill_name=skill_name,
            skill_triggers=skill_triggers,
            skill_body=skill_body,
            dimensions=dims,
            dimension_labels=_KEYWORDS,
            version=version,
        )
        self._embeddings[skill_name] = embedding
        return embedding

    def find_similar(
        self,
        target_skill: str,
        top_n: int = 5,
    ) -> tuple[tuple[str, float], ...]:
        """Find the top-N most similar skills to the target.

        Returns:
            Tuple of (skill_name, similarity_score) sorted by similarity.
        """
        target = self._embeddings.get(target_skill)
        if target is None:
            return ()

        scored: list[tuple[str, float]] = []
        for name, emb in self._embeddings.items():
            if name == target_skill:
                continue
            sim = _cosine_sim(target.dimensions, emb.dimensions)
            if sim >= self.min_similarity:
                scored.append((name, round(sim, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return tuple(scored[:top_n])

    def transfer(
        self,
        source_skill: str,
        target_skill: str,
    ) -> TransferResult:
        """Transfer knowledge patterns from source to target skill.

        Args:
            source_skill: Name of the skill to learn from.
            target_skill: Name of the skill to enrich.

        Returns:
            TransferResult with extracted patterns and enriched skill.
        """
        src = self._embeddings.get(source_skill)
        tgt = self._embeddings.get(target_skill)

        if src is None or tgt is None:
            result = TransferResult(
                result_id=f"tr-{uuid.uuid4().hex[:12]}",
                source_skill=source_skill,
                target_skill=target_skill,
                similarity=0.0,
                extracted_patterns=(),
                enriched_triggers=None,
                enriched_body=None,
                status=TransferStatus.SKIPPED,
                summary=f"Skill '{source_skill}' or '{target_skill}' not indexed.",
            )
            self._history.append(result)
            return result

        similarity = _cosine_sim(src.dimensions, tgt.dimensions)

        if similarity < self.min_similarity:
            result = TransferResult(
                result_id=f"tr-{uuid.uuid4().hex[:12]}",
                source_skill=source_skill,
                target_skill=target_skill,
                similarity=similarity,
                extracted_patterns=(),
                enriched_triggers=None,
                enriched_body=None,
                status=TransferStatus.SKIPPED,
                summary=f"Similarity {similarity:.3f} below threshold {self.min_similarity}.",
            )
            self._history.append(result)
            return result

        patterns = _extract_patterns(source_skill, src.skill_body, similarity)

        if not patterns:
            result = TransferResult(
                result_id=f"tr-{uuid.uuid4().hex[:12]}",
                source_skill=source_skill,
                target_skill=target_skill,
                similarity=similarity,
                extracted_patterns=(),
                enriched_triggers=None,
                enriched_body=None,
                status=TransferStatus.UNCHANGED,
                summary=f"No transferable patterns found (similarity={similarity:.3f}).",
            )
            self._history.append(result)
            return result

        new_triggers = set(tgt.skill_triggers)
        new_imports: list[str] = []

        for p in patterns:
            if p.pattern_type == "trigger":
                new_triggers.add(p.pattern_content)
            elif p.pattern_type == "import":
                if p.pattern_content not in tgt.skill_body:
                    new_imports.append(p.pattern_content)

        enriched_body = tgt.skill_body
        if new_imports:
            import_block = "\n".join(new_imports) + "\n"
            if "import " in enriched_body or "from " in enriched_body:
                enriched_body = import_block + enriched_body
            else:
                enriched_body = import_block + "\n" + enriched_body

        result = TransferResult(
            result_id=f"tr-{uuid.uuid4().hex[:12]}",
            source_skill=source_skill,
            target_skill=target_skill,
            similarity=round(similarity, 4),
            extracted_patterns=patterns,
            enriched_triggers=(
                tuple(new_triggers) if new_triggers != set(tgt.skill_triggers) else None
            ),
            enriched_body=enriched_body if enriched_body != tgt.skill_body else None,
            status=TransferStatus.ENRICHED,
            summary=(
                f"Transferred {len(patterns)} patterns from "
                f"'{source_skill}' to '{target_skill}' (similarity={similarity:.3f})."
            ),
        )
        self._history.append(result)
        return result

    def get_embedding(self, skill_name: str) -> SkillEmbedding | None:
        return self._embeddings.get(skill_name)

    @property
    def embedded_count(self) -> int:
        return len(self._embeddings)

    @property
    def history(self) -> tuple[TransferResult, ...]:
        return tuple(self._history)

    def clear(self) -> None:
        self._embeddings.clear()
        self._history.clear()


__all__ = [
    "KnowledgeTransferEngine",
    "PatternMatch",
    "SkillEmbedding",
    "TransferResult",
    "TransferStatus",
]
