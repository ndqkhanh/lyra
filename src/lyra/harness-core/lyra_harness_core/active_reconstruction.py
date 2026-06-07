"""Active Reconstruction Memory — Cue→Tag→Content dynamic graph (P2-B2 CRITICAL).

Memory is NOT static retrieval — it's a dynamic reconstruction from partial cues
via spreading activation across a tag network. When confidence is below threshold,
falls back to vector retrieval.

Implements the MRAgent paper pattern (OpenReview: AIJsjIqfsp).
See: plan-phase2-memory.md §Breakthrough 2
"""
from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Tag Network
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TagNode:
    """A node in the tag activation network."""

    tag: str
    weight: float = 1.0  # base importance
    activation: float = 0.0  # current activation level
    threshold: float = 0.1  # minimum activation to fire
    decay: float = 0.85  # per-hop decay factor


@dataclass(frozen=True)
class TagEdge:
    """Weighted, directed edge between two tag nodes."""

    source: str
    target: str
    weight: float = 0.5  # association strength [0, 1]
    co_occurrence_count: int = 0


@dataclass(frozen=True)
class MemoryFragment:
    """A fragment of memory content keyed by tags."""

    fragment_id: str
    content: str
    tags: frozenset[str]
    importance: float = 0.5
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0
    source: str = ""


# ---------------------------------------------------------------------------
# Reconstruction Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cue:
    """A partial cue that triggers memory reconstruction."""

    query: str
    tags: frozenset[str] = frozenset()
    context_hints: frozenset[str] = frozenset()
    min_confidence: float = 0.5


@dataclass(frozen=True)
class ActivatedTag:
    """A tag with its activation level after spreading."""

    tag: str
    activation: float
    hop_distance: int
    source_tags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ReconstructedMemory:
    """Output of the active reconstruction process."""

    fragments: tuple[MemoryFragment, ...]
    activated_tags: tuple[ActivatedTag, ...]
    confidence: float
    reconstruction_path: tuple[str, ...]  # tag path taken
    elapsed_ms: float
    from_fallback: bool = False

    @property
    def combined_content(self) -> str:
        return "\n---\n".join(f.content for f in self.fragments)

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.5


@dataclass(frozen=True)
class ReconstructionVerdict:
    """Self-verification gate output."""

    passed: bool
    confidence: float
    reason: str
    fallback_triggered: bool = False
    fallback_fragments: tuple[MemoryFragment, ...] = ()


# ---------------------------------------------------------------------------
# Tag Network Engine
# ---------------------------------------------------------------------------


@dataclass
class TagNetwork:
    """Spreading-activation tag network for content reconstruction."""

    nodes: dict[str, TagNode] = field(default_factory=dict)
    edges: dict[str, dict[str, TagEdge]] = field(default_factory=dict)
    _fragment_index: dict[str, list[str]] = field(default_factory=dict)  # tag -> fragment_ids

    # --- Node management ---

    def add_node(
        self, tag: str, weight: float = 1.0, threshold: float = 0.1, decay: float = 0.85
    ) -> None:
        self.nodes[tag] = TagNode(tag=tag, weight=weight, threshold=threshold, decay=decay)

    def has_node(self, tag: str) -> bool:
        return tag in self.nodes

    # --- Edge management ---

    def add_edge(self, source: str, target: str, weight: float = 0.5) -> None:
        if source not in self.edges:
            self.edges[source] = {}
        existing = self.edges[source].get(target)
        co_occurrence = (existing.co_occurrence_count + 1) if existing else 0
        self.edges[source][target] = TagEdge(
            source=source,
            target=target,
            weight=weight,
            co_occurrence_count=co_occurrence,
        )

    def get_edge(self, source: str, target: str) -> TagEdge | None:
        return self.edges.get(source, {}).get(target)

    def get_neighbors(self, tag: str) -> list[TagEdge]:
        return list(self.edges.get(tag, {}).values())

    # --- Fragment indexing ---

    def index_fragment(self, fragment: MemoryFragment) -> None:
        for tag in fragment.tags:
            if tag not in self._fragment_index:
                self._fragment_index[tag] = []
            if fragment.fragment_id not in self._fragment_index[tag]:
                self._fragment_index[tag].append(fragment.fragment_id)

    def remove_fragment(self, fragment_id: str) -> None:
        for tag_frags in self._fragment_index.values():
            if fragment_id in tag_frags:
                tag_frags.remove(fragment_id)

    def fragments_for_tag(self, tag: str) -> list[str]:
        return list(self._fragment_index.get(tag, []))

    def fragments_for_tags(self, tags: frozenset[str]) -> set[str]:
        result: set[str] = set()
        for tag in tags:
            result.update(self._fragment_index.get(tag, []))
        return result

    # --- Spreading activation ---

    def activate(
        self,
        seed_tags: frozenset[str],
        max_hops: int = 3,
        activation_threshold: float = 0.05,
    ) -> dict[str, ActivatedTag]:
        """Spread activation from seed tags through the network.

        Uses a BFS-like algorithm with decay per hop.
        """
        activated: dict[str, ActivatedTag] = {}
        current_wave: dict[str, tuple[float, int, frozenset[str]]] = {}

        # Seed initial activation
        for tag in seed_tags:
            node = self.nodes.get(tag)
            if node is None:
                continue
            initial = node.weight
            current_wave[tag] = (initial, 0, frozenset([tag]))
            activated[tag] = ActivatedTag(
                tag=tag,
                activation=initial,
                hop_distance=0,
                source_tags=frozenset([tag]),
            )

        # Spread through hops
        for _ in range(max_hops):
            if not current_wave:
                break
            next_wave: dict[str, tuple[float, int, frozenset[str]]] = {}

            for source_tag, (source_act, dist, sources) in current_wave.items():
                source_node = self.nodes.get(source_tag)
                if source_node is None:
                    continue
                decay = source_node.decay

                for edge in self.get_neighbors(source_tag):
                    target_tag = edge.target
                    if target_tag in activated:
                        continue

                    target_node = self.nodes.get(target_tag)
                    if target_node is None:
                        continue

                    propagated = source_act * decay * edge.weight
                    if propagated < activation_threshold:
                        continue

                    new_sources = sources | frozenset([target_tag])
                    next_wave[target_tag] = (propagated, dist + 1, new_sources)
                    activated[target_tag] = ActivatedTag(
                        tag=target_tag,
                        activation=propagated,
                        hop_distance=dist + 1,
                        source_tags=new_sources,
                    )

            current_wave = next_wave

        return activated

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return sum(len(targets) for targets in self.edges.values())

    def fragment_index_size(self) -> int:
        return sum(len(ids) for ids in self._fragment_index.values())


# ---------------------------------------------------------------------------
# Self-Verification Gate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelfVerificationGate:
    """Confidence-based gate that decides whether reconstructed memory is trustworthy.

    When confidence is below threshold, triggers fallback to vector retrieval.
    """

    confidence_threshold: float = 0.5
    min_fragments: int = 1
    min_activated_tags: int = 2

    def verify(
        self,
        reconstructed: ReconstructedMemory,
        fallback_fragments: tuple[MemoryFragment, ...] = (),
    ) -> ReconstructionVerdict:
        """Check if reconstructed memory meets confidence requirements."""
        if len(reconstructed.fragments) < self.min_fragments:
            return ReconstructionVerdict(
                passed=False,
                confidence=reconstructed.confidence,
                reason=f"Too few fragments ({len(reconstructed.fragments)} < {self.min_fragments})",
                fallback_triggered=True,
                fallback_fragments=fallback_fragments,
            )

        if len(reconstructed.activated_tags) < self.min_activated_tags:
            return ReconstructionVerdict(
                passed=False,
                confidence=reconstructed.confidence,
                reason=f"Too few activated tags ({len(reconstructed.activated_tags)} < {self.min_activated_tags})",
                fallback_triggered=True,
                fallback_fragments=fallback_fragments,
            )

        if reconstructed.confidence < self.confidence_threshold:
            return ReconstructionVerdict(
                passed=False,
                confidence=reconstructed.confidence,
                reason=f"Confidence below threshold ({reconstructed.confidence:.3f} < {self.confidence_threshold})",
                fallback_triggered=True,
                fallback_fragments=fallback_fragments,
            )

        return ReconstructionVerdict(
            passed=True,
            confidence=reconstructed.confidence,
            reason="Confidence threshold met",
        )


# ---------------------------------------------------------------------------
# Active Reconstruction Engine
# ---------------------------------------------------------------------------


def _make_fragment_id(content: str, tags: frozenset[str]) -> str:
    h = hashlib.sha256(f"{content}|{sorted(tags)}".encode()).hexdigest()[:16]
    return f"frag-{h}"


@dataclass
class ActiveReconstructionEngine:
    """Main engine: Cue → Tag Activation → Content Reconstruction → Verify → Fallback."""

    network: TagNetwork = field(default_factory=TagNetwork)
    fragments: dict[str, MemoryFragment] = field(default_factory=dict)
    gate: SelfVerificationGate = field(default_factory=SelfVerificationGate)
    max_hops: int = 3
    activation_threshold: float = 0.05

    # --- Fragment management ---

    def add_fragment(
        self,
        content: str,
        tags: frozenset[str],
        importance: float = 0.5,
        source: str = "",
    ) -> MemoryFragment:
        """Add a memory fragment to the engine, indexing its tags."""
        fragment_id = _make_fragment_id(content, tags)
        if fragment_id in self.fragments:
            return self.fragments[fragment_id]

        frag = MemoryFragment(
            fragment_id=fragment_id,
            content=content,
            tags=tags,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
            source=source,
        )
        self.fragments[fragment_id] = frag

        # Ensure tag nodes exist
        for tag in tags:
            if not self.network.has_node(tag):
                self.network.add_node(tag)

        # Build tag co-occurrence edges
        tag_list = sorted(tags)
        for i in range(len(tag_list)):
            for j in range(i + 1, len(tag_list)):
                self.network.add_edge(tag_list[i], tag_list[j])
                self.network.add_edge(tag_list[j], tag_list[i])

        self.network.index_fragment(frag)
        return frag

    def remove_fragment(self, fragment_id: str) -> bool:
        frag = self.fragments.pop(fragment_id, None)
        if frag is None:
            return False
        self.network.remove_fragment(fragment_id)
        return True

    def get_fragment(self, fragment_id: str) -> MemoryFragment | None:
        frag = self.fragments.get(fragment_id)
        if frag is not None:
            object.__setattr__(frag, "last_accessed", time.time())
            object.__setattr__(frag, "access_count", frag.access_count + 1)
        return frag

    # --- Tag extraction ---

    @staticmethod
    def extract_tags(text: str) -> frozenset[str]:
        """Extract tags from text using simple keyword extraction."""
        words = text.lower().split()
        # Filter: keep words >3 chars, deduplicate
        return frozenset(w.strip(".,;:!?()[]{}'\"") for w in words if len(w) > 3)

    # --- Reconstruction ---

    def reconstruct(self, cue: Cue) -> ReconstructedMemory:
        """Reconstruct memory from a partial cue.

        1. Extract/expand seed tags from cue
        2. Spread activation through tag network
        3. Collect fragments keyed by activated tags
        4. Score confidence based on activation levels + fragment count
        """
        t0 = time.time()

        # 1. Determine seed tags — from explicit tags or extracted from query
        seed_tags = set(cue.tags) if cue.tags else set(self.extract_tags(cue.query))
        seed_tags |= set(cue.context_hints)

        # Filter to tags that exist in the network
        existing_seeds = frozenset(t for t in seed_tags if self.network.has_node(t))

        # 2. Spread activation
        if existing_seeds:
            activated = self.network.activate(
                existing_seeds,
                max_hops=self.max_hops,
                activation_threshold=self.activation_threshold,
            )
        else:
            activated = {}

        # 3. Collect fragments from activated tags (ordered by activation)
        sorted_tags = sorted(activated.values(), key=lambda a: a.activation, reverse=True)
        seen_fragments: dict[str, MemoryFragment] = {}
        for at in sorted_tags:
            for fid in self.network.fragments_for_tag(at.tag):
                if fid not in seen_fragments and fid in self.fragments:
                    seen_fragments[fid] = self.fragments[fid]

        # Sort by activation × importance
        def _score(frag: MemoryFragment) -> float:
            tag_acts = [
                activated[t].activation for t in frag.tags if t in activated
            ]
            avg_act = sum(tag_acts) / len(tag_acts) if tag_acts else 0.0
            return avg_act * frag.importance

        ordered = sorted(seen_fragments.values(), key=_score, reverse=True)

        # 4. Compute confidence
        confidence = self._compute_confidence(activated, ordered)

        path = tuple(at.tag for at in sorted_tags)

        result = ReconstructedMemory(
            fragments=tuple(ordered),
            activated_tags=tuple(sorted_tags),
            confidence=confidence,
            reconstruction_path=path,
            elapsed_ms=(time.time() - t0) * 1000,
        )

        # Mark fragments as accessed
        for f in ordered:
            object.__setattr__(f, "last_accessed", time.time())
            object.__setattr__(f, "access_count", f.access_count + 1)

        return result

    def reconstruct_with_fallback(
        self,
        cue: Cue,
        fallback_fn=None,
    ) -> ReconstructionVerdict:
        """Reconstruct and pass through the self-verification gate.

        If the gate rejects, fallback is triggered with results from fallback_fn.
        """
        result = self.reconstruct(cue)

        fallback_frags: tuple[MemoryFragment, ...] = ()
        if fallback_fn is not None:
            fallback_frags = tuple(fallback_fn(cue.query))

        verdict = self.gate.verify(result, fallback_frags)

        if not verdict.passed and verdict.fallback_triggered and fallback_frags:
            return ReconstructionVerdict(
                passed=False,
                confidence=0.0,
                reason=verdict.reason + " — fallback returned",
                fallback_triggered=True,
                fallback_fragments=fallback_frags,
            )

        return verdict

    # --- Confidence scoring ---

    @staticmethod
    def _compute_confidence(
        activated: dict[str, ActivatedTag],
        fragments: list[MemoryFragment],
    ) -> float:
        """Compute reconstruction confidence from activation + fragment signals."""
        if not fragments:
            return 0.0

        # Activation score: mean activation of tags that matched fragments
        matched_tags: set[str] = set()
        for f in fragments:
            matched_tags.update(f.tags)
        matched_tags &= set(activated.keys())

        if matched_tags:
            act_scores = [activated[t].activation for t in matched_tags]
            activation_score = sum(act_scores) / len(act_scores)
        else:
            activation_score = 0.0

        # Fragment score: normalized by count and importance
        fragment_score = sum(f.importance for f in fragments) / max(len(fragments), 1)

        # Coverage score: proportion of activated tags that yielded fragments
        coverage = len(matched_tags) / max(len(activated), 1)

        # Combined: weighted blend
        # Weights favor activation (the spreading signal) over raw count
        confidence = 0.5 * activation_score + 0.3 * fragment_score + 0.2 * coverage

        # Clamp to [0, 1] and apply sigmoid-like scaling for sensitivity
        return 1.0 / (1.0 + math.exp(-5 * (confidence - 0.5)))

    # --- Stats ---

    @property
    def fragment_count(self) -> int:
        return len(self.fragments)

    @property
    def tag_count(self) -> int:
        return self.network.node_count()

    @property
    def edge_count(self) -> int:
        return self.network.edge_count()


__all__ = [
    "ActivatedTag",
    "ActiveReconstructionEngine",
    "Cue",
    "MemoryFragment",
    "ReconstructedMemory",
    "ReconstructionVerdict",
    "SelfVerificationGate",
    "TagEdge",
    "TagNetwork",
    "TagNode",
]
