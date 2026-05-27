"""Symbolic Short-Term Memory — Mermaid Canvas compression.

Converts verbose tool outputs into compact Mermaid graph representations,
offloading full text to refs/*.md for on-demand recall via node_id.

Achieves ~61% token reduction on tool outputs (TencentDB-Agent-Memory, 2026).

Architecture:
    Tool output → extract entities/relations → Mermaid graph (~200 tokens)
    Full text → refs/{node_id}.md (on-demand grep recall)
    Context injection: graph + 100-token NL summary
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar
from uuid import uuid4


@dataclass
class SymbolicRepresentation:
    """Compressed representation of a tool output."""

    node_id: str
    mermaid_graph: str
    summary: str
    token_savings: float  # percentage saved
    ref_path: str = ""

    @property
    def context_tokens(self) -> int:
        """Estimated tokens consumed in LLM context."""
        return _estimate_tokens(self.mermaid_graph) + _estimate_tokens(self.summary)


@dataclass
class EntityNode:
    """An entity extracted from tool output."""

    name: str
    kind: str  # file, function, class, error, result, concept
    attributes: dict = field(default_factory=dict)


@dataclass
class Relation:
    """A relation between two entities."""

    source: str
    target: str
    label: str  # calls, imports, returns, contains, causes


def _estimate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token."""
    return max(1, len(text) // 4)


def _slugify(name: str) -> str:
    """Normalize entity name to a Mermaid-safe node ID."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)[:40]


class SymbolicShortTermMemory:
    """Compress tool outputs into Mermaid graphs + ref files.

    Usage::

        sstm = SymbolicShortTermMemory(refs_dir=Path("refs"))
        rep = sstm.compress("bash", tool_output)
        # rep.mermaid_graph → inject into context (~200 tokens)
        # rep.summary → inject into context (~100 tokens)
        # rep.node_id → for on-demand full-text recall from refs/*.md
    """

    # Patterns for entity extraction
    _FILE_PAT: ClassVar[re.Pattern] = re.compile(
        r"(?:^|\s)([\w/\-.]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|yaml|yml|json|toml|md)(?:\:\d+)?)",
        re.MULTILINE,
    )
    _FUNC_PAT: ClassVar[re.Pattern] = re.compile(
        r"(?:def |function |class |fn |func )([\w_]+)",
        re.MULTILINE,
    )
    _ERROR_PAT: ClassVar[re.Pattern] = re.compile(
        r"(Error|Exception|Warning|Traceback|FAILED|FAILURE)[: ](.+?)(?:\n|$)",
        re.MULTILINE,
    )
    _RESULT_PAT: ClassVar[re.Pattern] = re.compile(
        r"(\d+)\s+(passed|failed|errors?|warnings?|tests?|items?)",
        re.IGNORECASE,
    )

    def __init__(self, refs_dir: Path = Path("refs")):
        self.refs_dir = Path(refs_dir)
        self.refs_dir.mkdir(parents=True, exist_ok=True)
        self._node_index: dict[str, Path] = {}

    def compress(self, tool_name: str, output: str) -> SymbolicRepresentation:
        """Compress tool output into symbolic graph + ref file."""
        node_id = f"{tool_name}-{uuid4().hex[:8]}"
        ref_path = self.refs_dir / f"{node_id}.md"
        original_tokens = _estimate_tokens(output)

        entities = self._extract_entities(output)
        relations = self._extract_relations(entities)
        graph = self._build_mermaid(entities, relations)
        summary = self._summarize(output, entities)

        ref_path.write_text(
            f"# {tool_name} Output ({node_id})\n\n"
            f"**Compressed**: {len(entities)} entities, {len(relations)} relations\n\n"
            f"{output}",
            encoding="utf-8",
        )
        self._node_index[node_id] = ref_path

        compressed_tokens = _estimate_tokens(graph) + _estimate_tokens(summary)
        savings = 1.0 - (compressed_tokens / max(1, original_tokens))

        return SymbolicRepresentation(
            node_id=node_id,
            mermaid_graph=graph,
            summary=summary,
            token_savings=savings,
            ref_path=str(ref_path),
        )

    def recall(self, node_id: str) -> str | None:
        """Retrieve full text from ref file by node_id."""
        ref_path = self._node_index.get(node_id)
        if ref_path is None:
            ref_path = self.refs_dir / f"{node_id}.md"
        try:
            return ref_path.read_text(encoding="utf-8")
        except (OSError, FileNotFoundError):
            return None

    def _extract_entities(self, output: str) -> list[EntityNode]:
        """Extract entities from tool output using regex patterns."""
        entities: list[EntityNode] = []
        seen: set[str] = set()

        for m in self._FILE_PAT.finditer(output):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                entities.append(EntityNode(name=name, kind="file"))

        for m in self._FUNC_PAT.finditer(output):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                entities.append(EntityNode(name=name, kind="function"))

        for m in self._ERROR_PAT.finditer(output):
            name = f"{m.group(1)}: {m.group(2)[:60]}"
            if name not in seen:
                seen.add(name)
                entities.append(EntityNode(name=name, kind="error"))

        for m in self._RESULT_PAT.finditer(output):
            name = f"{m.group(1)} {m.group(2)}"
            if name not in seen and len(entities) < 20:
                seen.add(name)
                entities.append(EntityNode(name=name, kind="result"))

        return entities

    def _extract_relations(self, entities: list[EntityNode]) -> list[Relation]:
        """Infer relations between entities (files→functions, errors→files)."""
        relations: list[Relation] = []
        files = [e for e in entities if e.kind == "file"]
        funcs = [e for e in entities if e.kind == "function"]
        errors = [e for e in entities if e.kind == "error"]

        for func in funcs[:10]:
            if files:
                relations.append(Relation(source=files[0].name, target=func.name, label="contains"))

        for err in errors[:5]:
            if files:
                relations.append(Relation(source=err.name, target=files[0].name, label="occurred_in"))

        return relations

    def _build_mermaid(self, entities: list[EntityNode], relations: list[Relation]) -> str:
        """Build Mermaid graph string."""
        lines = ["graph TD"]
        kind_styles = {"file": "fa:fa-file", "function": "fa:fa-code", "error": "fa:fa-exclamation-triangle", "result": "fa:fa-chart-bar"}

        for e in entities[:20]:
            sid = _slugify(e.name)
            label = e.name[:50].replace('"', "'")
            icon = kind_styles.get(e.kind, "")
            lines.append(f'    {sid}["{icon} {label}"]')

        for r in relations[:15]:
            src = _slugify(r.source)
            tgt = _slugify(r.target)
            lines.append(f"    {src} -->|{r.label}| {tgt}")

        return "\n".join(lines)

    def _summarize(self, output: str, entities: list[EntityNode]) -> str:
        """Create a concise NL summary of the output."""
        parts: list[str] = []
        kinds: dict[str, int] = {}
        for e in entities:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1

        kind_summary = ", ".join(f"{v} {k}s" for k, v in sorted(kinds.items()))
        if kind_summary:
            parts.append(f"Found: {kind_summary}")

        lines = output.strip().split("\n")
        if len(lines) <= 3:
            parts.append(output[:200])
        else:
            parts.append(f"{len(lines)} lines of output")
            first = lines[0][:100]
            if first:
                parts.append(f"First line: {first}")
            last = lines[-1][:100]
            if last:
                parts.append(f"Last line: {last}")

        return ". ".join(parts)


class CraniMemGate:
    """Goal-conditioned write gate for episodic buffer (L0).

    Filters incoming memories based on relevance to current active goals.
    Only memories aligned with at least one active goal pass through.
    """

    def __init__(self, min_goal_alignment: float = 0.3):
        self._active_goals: list[str] = []
        self.min_goal_alignment = min_goal_alignment

    @property
    def active_goals(self) -> list[str]:
        return list(self._active_goals)

    def set_goals(self, goals: list[str]) -> None:
        self._active_goals = list(goals)

    def add_goal(self, goal: str) -> None:
        if goal not in self._active_goals:
            self._active_goals.append(goal)

    def remove_goal(self, goal: str) -> None:
        try:
            self._active_goals.remove(goal)
        except ValueError:
            pass

    def should_admit(self, content: str) -> tuple[bool, float]:
        """Check if content aligns with any active goal.

        Returns (admitted, alignment_score).
        """
        if not self._active_goals:
            return True, 1.0

        content_lower = content.lower()
        best_score = 0.0

        for goal in self._active_goals:
            score = self._goal_alignment(content_lower, goal.lower())
            best_score = max(best_score, score)

        admitted = best_score >= self.min_goal_alignment
        return admitted, best_score

    def _goal_alignment(self, content: str, goal: str) -> float:
        """Simple keyword-overlap alignment scorer."""
        goal_words = set(goal.split())
        if not goal_words:
            return 0.0
        content_words = set(content.split())
        overlap = goal_words & content_words
        return len(overlap) / len(goal_words)
