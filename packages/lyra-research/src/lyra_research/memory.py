"""
Research Memory System.

Provides persistent storage for research notes (Zettelkasten), local paper corpus,
research strategies, and session case history.
"""

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# ResearchNote (Zettelkasten / A-Mem style)
# ---------------------------------------------------------------------------

@dataclass
class ResearchNote:
    """A single Zettelkasten-style research note with links."""
    id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    title: str = ""
    content: str = ""
    source_ids: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    note_type: str = "finding"  # "finding", "gap", "strategy", "contradiction", "question"
    confidence: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _note_to_dict(note: ResearchNote) -> Dict[str, Any]:
    d = asdict(note)
    d["created_at"] = note.created_at.isoformat()
    d["updated_at"] = note.updated_at.isoformat()
    return d


def _dict_to_note(d: Dict[str, Any]) -> ResearchNote:
    d = dict(d)
    d["created_at"] = datetime.fromisoformat(d["created_at"])
    d["updated_at"] = datetime.fromisoformat(d["updated_at"])
    return ResearchNote(**d)


# ---------------------------------------------------------------------------
# ResearchNoteStore
# ---------------------------------------------------------------------------

class ResearchNoteStore:
    """Stores ResearchNotes in a JSON file with link traversal.

    Persistence: stores as JSON at self.store_path (default: ~/.lyra/research_notes.json)
    """

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or Path.home() / ".lyra" / "research_notes.json"
        self._notes: Dict[str, ResearchNote] = {}
        self._load()

    def add(self, note: ResearchNote) -> ResearchNote:
        """Add a note, auto-link to existing notes with overlapping tags/topics."""
        auto_links = self._auto_link(note)
        linked_ids = list(set(note.links + auto_links))
        note = ResearchNote(
            id=note.id,
            topic=note.topic,
            title=note.title,
            content=note.content,
            source_ids=note.source_ids,
            links=linked_ids,
            tags=note.tags,
            note_type=note.note_type,
            confidence=note.confidence,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        # Back-link existing notes to this new note
        for existing_id in auto_links:
            existing = self._notes.get(existing_id)
            if existing and note.id not in existing.links:
                self._notes[existing_id] = ResearchNote(
                    id=existing.id,
                    topic=existing.topic,
                    title=existing.title,
                    content=existing.content,
                    source_ids=existing.source_ids,
                    links=existing.links + [note.id],
                    tags=existing.tags,
                    note_type=existing.note_type,
                    confidence=existing.confidence,
                    created_at=existing.created_at,
                    updated_at=datetime.now(timezone.utc),
                )
        self._notes[note.id] = note
        self._save()
        return note

    def get(self, note_id: str) -> Optional[ResearchNote]:
        return self._notes.get(note_id)

    def search(self, query: str, top_k: int = 10) -> List[ResearchNote]:
        """Keyword search over title + content + tags."""
        query_lower = query.lower()
        results = []
        for note in self._notes.values():
            searchable = f"{note.title} {note.content} {' '.join(note.tags)}".lower()
            if query_lower in searchable:
                results.append(note)
        return results[:top_k]

    def get_linked(self, note_id: str) -> List[ResearchNote]:
        """Get all notes linked to this note."""
        note = self._notes.get(note_id)
        if not note:
            return []
        return [self._notes[lid] for lid in note.links if lid in self._notes]

    def find_by_topic(self, topic: str) -> List[ResearchNote]:
        """Get all notes for a given topic (substring match)."""
        topic_lower = topic.lower()
        return [n for n in self._notes.values() if topic_lower in n.topic.lower()]

    def update(self, note_id: str, **kwargs) -> Optional[ResearchNote]:
        """Update a note's fields and set updated_at."""
        note = self._notes.get(note_id)
        if not note:
            return None
        d = _note_to_dict(note)
        d.update(kwargs)
        d["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = _dict_to_note(d)
        self._notes[note_id] = updated
        self._save()
        return updated

    def delete(self, note_id: str) -> bool:
        if note_id not in self._notes:
            return False
        del self._notes[note_id]
        self._save()
        return True

    def _auto_link(self, note: ResearchNote) -> List[str]:
        """Find existing notes with >=2 overlapping tags or same topic."""
        linked = []
        note_tags = set(note.tags)
        for existing_id, existing in self._notes.items():
            if existing_id == note.id:
                continue
            overlap = note_tags & set(existing.tags)
            same_topic = (
                note.topic
                and existing.topic
                and note.topic.lower() == existing.topic.lower()
            )
            if len(overlap) >= 2 or same_topic:
                linked.append(existing_id)
        return linked

    def _save(self) -> None:
        """Persist all notes to JSON."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {nid: _note_to_dict(n) for nid, n in self._notes.items()}
        self.store_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        """Load notes from JSON if file exists."""
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            self._notes = {nid: _dict_to_note(d) for nid, d in data.items()}
        except (json.JSONDecodeError, KeyError, TypeError):
            self._notes = {}


# ---------------------------------------------------------------------------
# LocalCorpus (DCI-style local paper storage with SQLite)
# ---------------------------------------------------------------------------

@dataclass
class CorpusEntry:
    """A downloaded paper/source stored locally."""
    id: str
    source_id: str
    title: str
    url: str
    abstract: str
    full_text: str
    source_type: str
    stored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class LocalCorpus:
    """Local corpus of downloaded papers with SQLite search.

    Stores parsed content locally. Supports full-text search via LIKE.
    DB path default: ~/.lyra/research_corpus.db
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".lyra" / "research_corpus.db"
        self._init_db()

    def store(self, entry: CorpusEntry) -> bool:
        """Store a corpus entry. Returns False if already stored (by source_id)."""
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM corpus_entries WHERE source_id = ?", (entry.source_id,)
            ).fetchone()
            if existing:
                return False
            conn.execute(
                """
                INSERT INTO corpus_entries
                  (id, source_id, title, url, abstract, full_text, source_type, stored_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.source_id,
                    entry.title,
                    entry.url,
                    entry.abstract,
                    entry.full_text,
                    entry.source_type,
                    entry.stored_at.isoformat(),
                    json.dumps(entry.metadata),
                ),
            )
        return True

    def get(self, source_id: str) -> Optional[CorpusEntry]:
        """Retrieve by original source_id."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM corpus_entries WHERE source_id = ?", (source_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def search(self, query: str, top_k: int = 10) -> List[CorpusEntry]:
        """Full-text search over title + abstract + full_text using LIKE."""
        pattern = f"%{query}%"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM corpus_entries
                WHERE title LIKE ? OR abstract LIKE ? OR full_text LIKE ?
                LIMIT ?
                """,
                (pattern, pattern, pattern, top_k),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def list_all(self, source_type: Optional[str] = None) -> List[CorpusEntry]:
        """List all stored entries, optionally filtered by source_type."""
        with sqlite3.connect(self.db_path) as conn:
            if source_type:
                rows = conn.execute(
                    "SELECT * FROM corpus_entries WHERE source_type = ?", (source_type,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM corpus_entries").fetchall()
        return [self._row_to_entry(r) for r in rows]

    def delete(self, source_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM corpus_entries WHERE source_id = ?", (source_id,)
            )
        return cursor.rowcount > 0

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM corpus_entries").fetchone()
        return row[0] if row else 0

    def _init_db(self) -> None:
        """Create SQLite tables if not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS corpus_entries (
                    id TEXT NOT NULL,
                    source_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    full_text TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    stored_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )

    def _row_to_entry(self, row: tuple) -> CorpusEntry:
        id_, source_id, title, url, abstract, full_text, source_type, stored_at, metadata_json = row
        return CorpusEntry(
            id=id_,
            source_id=source_id,
            title=title,
            url=url,
            abstract=abstract,
            full_text=full_text,
            source_type=source_type,
            stored_at=datetime.fromisoformat(stored_at),
            metadata=json.loads(metadata_json),
        )


# ---------------------------------------------------------------------------
# ResearchStrategyMemory (ReasoningBank-style)
# ---------------------------------------------------------------------------

@dataclass
class ResearchStrategy:
    """A learned research strategy from a past session."""
    id: str = field(default_factory=lambda: str(uuid4()))
    topic_type: str = ""
    domain: str = ""
    strategy_steps: List[str] = field(default_factory=list)
    outcome_score: float = 0.0
    lessons_learned: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0


def _strategy_to_dict(s: ResearchStrategy) -> Dict[str, Any]:
    d = asdict(s)
    d["created_at"] = s.created_at.isoformat()
    return d


def _dict_to_strategy(d: Dict[str, Any]) -> ResearchStrategy:
    d = dict(d)
    d["created_at"] = datetime.fromisoformat(d["created_at"])
    return ResearchStrategy(**d)


class ResearchStrategyMemory:
    """Stores and retrieves research strategies by domain/topic_type.

    Persistence: JSON at ~/.lyra/research_strategies.json
    """

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or Path.home() / ".lyra" / "research_strategies.json"
        self._strategies: Dict[str, ResearchStrategy] = {}
        self._load()

    def save_strategy(self, strategy: ResearchStrategy) -> ResearchStrategy:
        self._strategies[strategy.id] = strategy
        self._save()
        return strategy

    def get_best_for_domain(self, domain: str, top_k: int = 3) -> List[ResearchStrategy]:
        """Get top-k strategies for a domain, sorted by outcome_score desc."""
        matching = [
            s for s in self._strategies.values()
            if s.domain.lower() == domain.lower()
        ]
        matching.sort(key=lambda s: s.outcome_score, reverse=True)
        return matching[:top_k]

    def get_for_topic_type(self, topic_type: str) -> List[ResearchStrategy]:
        return [
            s for s in self._strategies.values()
            if s.topic_type.lower() == topic_type.lower()
        ]

    def record_outcome(self, strategy_id: str, score: float, lesson: str) -> None:
        """Update a strategy's outcome score and increment use_count."""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return
        self._strategies[strategy_id] = ResearchStrategy(
            id=strategy.id,
            topic_type=strategy.topic_type,
            domain=strategy.domain,
            strategy_steps=strategy.strategy_steps,
            outcome_score=score,
            lessons_learned=lesson,
            created_at=strategy.created_at,
            use_count=strategy.use_count + 1,
        )
        self._save()

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {sid: _strategy_to_dict(s) for sid, s in self._strategies.items()}
        self.store_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            self._strategies = {sid: _dict_to_strategy(d) for sid, d in data.items()}
        except (json.JSONDecodeError, KeyError, TypeError):
            self._strategies = {}


# ---------------------------------------------------------------------------
# SessionCaseBank (Memento-style episodic case storage)
# ---------------------------------------------------------------------------

@dataclass
class ResearchCase:
    """A completed research session stored as a reusable case."""
    id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    domain: str = ""
    report_path: str = ""
    report_summary: str = ""
    sources_found: int = 0
    quality_score: float = 0.0
    duration_seconds: float = 0.0
    top_sources: List[str] = field(default_factory=list)
    key_findings: List[str] = field(default_factory=list)
    gaps_found: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _case_to_dict(c: ResearchCase) -> Dict[str, Any]:
    d = asdict(c)
    d["created_at"] = c.created_at.isoformat()
    return d


def _dict_to_case(d: Dict[str, Any]) -> ResearchCase:
    d = dict(d)
    d["created_at"] = datetime.fromisoformat(d["created_at"])
    return ResearchCase(**d)


class SessionCaseBank:
    """Stores completed research sessions for future reuse.

    Persistence: JSON at ~/.lyra/research_cases.json
    """

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or Path.home() / ".lyra" / "research_cases.json"
        self._cases: Dict[str, ResearchCase] = {}
        self._load()

    def save_case(self, case: ResearchCase) -> ResearchCase:
        self._cases[case.id] = case
        self._save()
        return case

    def find_related(self, topic: str, top_k: int = 3) -> List[ResearchCase]:
        """Find cases with overlapping topic keywords, sorted by quality_score desc."""
        topic_words = set(w.lower() for w in topic.split() if len(w) > 3)
        scored = []
        for case in self._cases.values():
            case_words = set(w.lower() for w in case.topic.split() if len(w) > 3)
            overlap = len(topic_words & case_words)
            if overlap > 0:
                scored.append((overlap, case))
        scored.sort(key=lambda x: (x[0], x[1].quality_score), reverse=True)
        return [c for _, c in scored[:top_k]]

    def get_all(self, domain: Optional[str] = None) -> List[ResearchCase]:
        """List all cases, optionally filtered by domain."""
        if domain:
            return [c for c in self._cases.values() if c.domain.lower() == domain.lower()]
        return list(self._cases.values())

    def get_best(self, n: int = 5) -> List[ResearchCase]:
        """Get top-n cases by quality_score."""
        sorted_cases = sorted(self._cases.values(), key=lambda c: c.quality_score, reverse=True)
        return sorted_cases[:n]

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {cid: _case_to_dict(c) for cid, c in self._cases.items()}
        self.store_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            self._cases = {cid: _dict_to_case(d) for cid, d in data.items()}
        except (json.JSONDecodeError, KeyError, TypeError):
            self._cases = {}
