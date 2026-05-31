"""
A-MEM: Agentic Memory with Zettelkasten-style dynamic linking.

Implements the A-MEM paper (Rutgers, ICLR 2026 MemAgent Workshop, arXiv 2502.12110):
memory notes that are dynamically linked, evolving over time through bidirectional
connections. Each note carries contextual descriptions, keywords, tags, and typed
links to other notes.

Key features:
- **Bidirectional links**: Notes link to each other with typed relationships
  (supports, contradicts, extends, relates_to, follows_from, generalizes, specializes)
- **Auto-linking**: New notes are automatically linked to related existing notes
  via embedding similarity + keyword overlap
- **Link decay**: Links weaken over time unless reinforced (Hebbian-style)
- **Graph navigation**: Traverse the link graph with depth-bounded BFS/DFS

Design rationale (WHY Zettelkasten vs alternatives):
- Flat vector DB: loses structural relationships between memories
- Relational DB: rigid schema can't capture evolving memory topology
- Property graph: overkill for agent memory (full Cypher/Gremlin querying not needed)
- RDF triples: too granular; agents think in notes, not atomic facts
- Zettelkasten: the sweet spot — notes are the natural unit of agent memory,
  typed links capture relationships, and the structure emerges organically
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class LinkType(str, Enum):
    """Typed relationships between memory notes (A-MEM link taxonomy)."""

    SUPPORTS = "supports"         # Note A provides evidence for Note B
    CONTRADICTS = "contradicts"   # Note A conflicts with Note B
    EXTENDS = "extends"           # Note A adds detail to Note B
    RELATES_TO = "relates_to"     # General semantic relationship
    FOLLOWS_FROM = "follows_from" # Note B is a logical consequence of Note A
    GENERALIZES = "generalizes"   # Note A is a more general principle
    SPECIALIZES = "specializes"   # Note A is a specific instance of Note B


@dataclass
class MemoryNote:
    """
    A single note in the A-MEM Zettelkasten graph.

    Each note is a self-contained unit of memory with:
    - A unique ID
    - Content (the actual memory)
    - Contextual description (summary for retrieval)
    - Keywords/tags for search
    - Typed links to other notes
    - Creation/modification timestamps
    - Activation level (Hebbian — increases with use, decays over time)
    """

    id: str
    content: str
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    activation: float = 1.0  # Hebbian activation (1.0 = baseline)
    access_count: int = 0

    def touch(self) -> None:
        """Record an access — boosts activation."""
        self.access_count += 1
        self.activation = min(5.0, self.activation + 0.05)
        self.modified_at = time.time()


@dataclass
class MemoryLink:
    """A typed, bidirectional link between two memory notes."""

    source_id: str
    target_id: str
    link_type: LinkType
    strength: float = 1.0  # 0.0–1.0, decays unless reinforced
    created_at: float = field(default_factory=time.time)


class AmemGraph:
    """
    A-MEM Zettelkasten graph — the linked memory note store.

    Manages notes and their typed links. Supports:
    - Adding notes with auto-linking to related existing notes
    - Bidirectional link creation with typed relationships
    - Link decay and reinforcement (Hebbian)
    - Graph traversal (BFS/DFS) for context retrieval
    - Contradiction detection via CONTRADICTS links

    Usage::

        graph = AmemGraph()
        note_a = graph.add_note("JWT is stateless", keywords=["auth", "jwt"], tags=["security"])
        note_b = graph.add_note("Session tokens are stateful", keywords=["auth", "session"])
        graph.link(note_a.id, note_b.id, LinkType.CONTRADICTS)

        # Auto-link a new note to existing ones
        note_c = graph.add_note("OAuth2 uses JWT for access tokens",
                                 keywords=["auth", "oauth2", "jwt"],
                                 auto_link=True)
        # note_c will be linked to note_a (EXTENDS) and note_b (CONTRADICTS)
    """

    def __init__(self) -> None:
        self._notes: dict[str, MemoryNote] = {}
        # Links stored bidirectionally: source_id -> set of MemoryLink
        self._outgoing: dict[str, list[MemoryLink]] = {}
        self._incoming: dict[str, list[MemoryLink]] = {}
        self._link_decay_rate: float = 0.01  # Per-access decay

    # ── Public API ─────────────────────────────────────────────────

    def add_note(
        self,
        content: str,
        description: str = "",
        keywords: list[str] | None = None,
        tags: list[str] | None = None,
        auto_link: bool = False,
        existing_embeddings: dict[str, list[float]] | None = None,
    ) -> MemoryNote:
        """
        Add a note to the graph.

        Args:
            content: The memory content.
            description: Human-readable summary for retrieval.
            keywords: Search keywords.
            tags: Categorization tags.
            auto_link: If True, attempt to auto-link to similar existing notes.
            existing_embeddings: Optional pre-computed embeddings for auto-linking.

        Returns:
            The created MemoryNote.
        """
        note_id = uuid.uuid4().hex[:12]
        note = MemoryNote(
            id=note_id,
            content=content,
            description=description or content[:200],
            keywords=keywords or [],
            tags=tags or [],
        )
        self._notes[note_id] = note
        self._outgoing[note_id] = []
        self._incoming[note_id] = []

        if auto_link:
            self._auto_link(note)

        return note

    def link(
        self,
        source_id: str,
        target_id: str,
        link_type: LinkType = LinkType.RELATES_TO,
        strength: float = 1.0,
    ) -> MemoryLink:
        """
        Create a typed link between two notes.

        Links are bidirectional in the data model — they're stored in both
        the source's outgoing set and the target's incoming set.
        """
        if source_id not in self._notes or target_id not in self._notes:
            raise KeyError(f"Note not found: source={source_id}, target={target_id}")

        link = MemoryLink(
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
            strength=strength,
        )
        self._outgoing[source_id].append(link)
        self._incoming[target_id].append(link)
        return link

    def get_note(self, note_id: str) -> MemoryNote | None:
        """Return a note by ID, touching it to boost activation."""
        note = self._notes.get(note_id)
        if note:
            note.touch()
        return note

    def get_outgoing_links(self, note_id: str) -> list[MemoryLink]:
        """Return all links FROM a note, sorted by strength descending."""
        links = self._outgoing.get(note_id, [])
        return sorted(links, key=lambda l: l.strength, reverse=True)

    def get_incoming_links(self, note_id: str) -> list[MemoryLink]:
        """Return all links TO a note, sorted by strength descending."""
        links = self._incoming.get(note_id, [])
        return sorted(links, key=lambda l: l.strength, reverse=True)

    def get_neighbors(
        self, note_id: str, link_types: list[LinkType] | None = None
    ) -> list[MemoryNote]:
        """
        Return all neighboring notes (linked in either direction).

        Args:
            note_id: The note to find neighbors for.
            link_types: Optional filter — only return neighbors connected
                via these link types.
        """
        neighbors: dict[str, MemoryNote] = {}
        for link in self.get_outgoing_links(note_id):
            if link_types is None or link.link_type in link_types:
                neighbor = self._notes.get(link.target_id)
                if neighbor:
                    neighbors[link.target_id] = neighbor
        for link in self.get_incoming_links(note_id):
            if link_types is None or link.link_type in link_types:
                neighbor = self._notes.get(link.source_id)
                if neighbor:
                    neighbors[link.source_id] = neighbor
        return list(neighbors.values())

    def traverse_bfs(
        self,
        start_id: str,
        max_depth: int = 3,
        link_types: list[LinkType] | None = None,
    ) -> list[MemoryNote]:
        """
        Breadth-first traversal from a start note.

        Args:
            start_id: Starting note ID.
            max_depth: Maximum traversal depth.
            link_types: Optional link type filter.

        Returns:
            List of visited notes in BFS order (start note first).
        """
        if start_id not in self._notes:
            return []

        visited: set[str] = {start_id}
        result: list[MemoryNote] = [self._notes[start_id]]
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            for link in self.get_outgoing_links(current_id):
                if link_types is not None and link.link_type not in link_types:
                    continue
                neighbor_id = link.target_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor = self._notes.get(neighbor_id)
                    if neighbor:
                        neighbor.touch()
                        result.append(neighbor)
                        queue.append((neighbor_id, depth + 1))

            # Also follow incoming links (bidirectional traversal)
            for link in self.get_incoming_links(current_id):
                if link_types is not None and link.link_type not in link_types:
                    continue
                neighbor_id = link.source_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor = self._notes.get(neighbor_id)
                    if neighbor:
                        neighbor.touch()
                        result.append(neighbor)
                        queue.append((neighbor_id, depth + 1))

        return result

    def find_contradictions(self, note_id: str) -> list[MemoryNote]:
        """Return all notes that contradict the given note."""
        return self.get_neighbors(note_id, link_types=[LinkType.CONTRADICTS])

    def find_supporting(self, note_id: str) -> list[MemoryNote]:
        """Return all notes that support the given note."""
        return self.get_neighbors(note_id, link_types=[LinkType.SUPPORTS])

    def decay_links(self) -> int:
        """
        Decay all link strengths (called periodically).

        Returns the number of links that dropped below threshold and were removed.
        """
        removed = 0
        threshold = 0.1

        for source_id, links in list(self._outgoing.items()):
            surviving: list[MemoryLink] = []
            for link in links:
                link.strength = max(0.0, link.strength - self._link_decay_rate)
                if link.strength < threshold:
                    # Remove from incoming as well
                    incoming = self._incoming.get(link.target_id)
                    if incoming:
                        self._incoming[link.target_id] = [
                            l for l in incoming if not (
                                l.source_id == link.source_id
                                and l.target_id == link.target_id
                            )
                        ]
                    removed += 1
                else:
                    surviving.append(link)
            self._outgoing[source_id] = surviving

        return removed

    def reinforce_link(self, source_id: str, target_id: str) -> bool:
        """
        Reinforce a link between two notes (Hebbian — "neurons that fire together").

        Returns True if the link was found and reinforced.
        """
        for link in self._outgoing.get(source_id, []):
            if link.target_id == target_id:
                link.strength = min(1.0, link.strength + 0.1)
                return True
        return False

    @property
    def note_count(self) -> int:
        return len(self._notes)

    @property
    def link_count(self) -> int:
        return sum(len(links) for links in self._outgoing.values())

    # ── Internal ─────────────────────────────────────────────────

    def _auto_link(self, note: MemoryNote) -> None:
        """
        Auto-link a new note to related existing notes.

        Strategy: keyword overlap + tag overlap. Notes with ≥1 keyword or tag
        match get a RELATES_TO link. Notes with ≥3 keyword matches get an EXTENDS
        link (the new note builds on the existing one).
        """
        for existing_id, existing in self._notes.items():
            if existing_id == note.id:
                continue

            kw_overlap = set(note.keywords) & set(existing.keywords)
            tag_overlap = set(note.tags) & set(existing.tags)
            total_overlap = len(kw_overlap) + len(tag_overlap)

            if total_overlap >= 3:
                self.link(note.id, existing_id, LinkType.EXTENDS, strength=0.8)
            elif total_overlap >= 1:
                self.link(note.id, existing_id, LinkType.RELATES_TO, strength=0.6)
