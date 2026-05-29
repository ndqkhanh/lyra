"""Tests for ResearchMemoryController."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lyra_research.memory import ResearchNote
from lyra_research.memory_controller import ResearchMemoryController


class _FakeNoteStore:
    def __init__(self) -> None:
        self._notes: dict[str, ResearchNote] = {}

    def add(self, note: ResearchNote) -> None:
        self._notes[note.id] = note

    def all(self) -> list[ResearchNote]:
        return list(self._notes.values())


def test_write_note_no_store() -> None:
    controller = ResearchMemoryController()
    note = ResearchNote(
        id="n1",
        topic="test",
        content="test content",
        tags=["tag1"],
        confidence=0.9,
    )
    decisions = controller.write_note(note)
    assert len(decisions) == 1
    assert decisions[0].action == "REJECT"
    assert decisions[0].reason == "no note store configured"


def test_write_note_new() -> None:
    store = _FakeNoteStore()
    controller = ResearchMemoryController(note_store=store)
    note = ResearchNote(
        id="n1",
        topic="test",
        content="test content",
        tags=["tag1"],
        confidence=0.9,
    )
    decisions = controller.write_note(note)
    assert len(decisions) == 1
    assert decisions[0].action == "WRITE"
    assert decisions[0].target == "note"
    assert decisions[0].target_id == "n1"
    assert "n1" in store._notes


def test_write_note_duplicate_detection() -> None:
    store = _FakeNoteStore()
    controller = ResearchMemoryController(note_store=store)

    # Add first note
    note1 = ResearchNote(
        id="n1",
        topic="test",
        content="first note",
        tags=["tag1", "tag2", "tag3"],
        confidence=0.8,
    )
    controller.write_note(note1)

    # Add duplicate with 3 shared tags
    note2 = ResearchNote(
        id="n2",
        topic="test",
        content="second note",
        tags=["tag1", "tag2", "tag3", "tag4"],
        confidence=0.9,
    )
    decisions = controller.write_note(note2)

    # Should detect merge
    assert any(d.action == "MERGE" for d in decisions)
    merge_decision = next(d for d in decisions if d.action == "MERGE")
    assert merge_decision.target_id == "n1"

    # Higher confidence note should be kept and link to the duplicate
    assert "n2" in store._notes
    assert "n1" in store._notes["n2"].links


def test_write_note_contradiction_detection() -> None:
    store = _FakeNoteStore()
    controller = ResearchMemoryController(note_store=store)

    # Add first note without negation
    note1 = ResearchNote(
        id="n1",
        topic="test",
        content="The system works well",
        tags=["tag1", "tag2"],
        confidence=0.8,
    )
    controller.write_note(note1)

    # Add contradicting note with negation
    note2 = ResearchNote(
        id="n2",
        topic="test",
        content="The system does not work",
        tags=["tag1", "tag2"],
        confidence=0.9,
    )
    decisions = controller.write_note(note2)

    # Should flag contradiction
    write_decision = next(d for d in decisions if d.action == "WRITE" and d.metadata)
    assert "contradictions" in write_decision.metadata
    assert "n1" in write_decision.metadata["contradictions"]


def test_write_note_promotion_to_kg() -> None:
    store = _FakeNoteStore()

    class _FakeKG:
        def __init__(self) -> None:
            self.nodes: list = []

        def add_node(self, node: object) -> None:
            self.nodes.append(node)

    kg = _FakeKG()
    controller = ResearchMemoryController(
        note_store=store,
        kg=kg,
        promote_confidence=0.85,
    )

    # Add high-confidence note with sources
    note = ResearchNote(
        id="n1",
        topic="test",
        title="Test Finding",
        content="important finding",
        tags=["tag1"],
        confidence=0.9,
        source_ids=["src1", "src2"],
    )
    decisions = controller.write_note(note)

    # Should promote to KG
    assert any(d.action == "PROMOTE" and d.target == "kg" for d in decisions)
    assert len(kg.nodes) == 1


def test_expire_stale_notes() -> None:
    store = _FakeNoteStore()
    controller = ResearchMemoryController(note_store=store)

    # Add old note
    old_note = ResearchNote(
        id="n1",
        topic="test",
        content="old note",
        tags=["tag1"],
        confidence=0.7,
        updated_at=datetime.now(timezone.utc) - timedelta(days=200),
    )
    store.add(old_note)

    # Add recent note
    recent_note = ResearchNote(
        id="n2",
        topic="test",
        content="recent note",
        tags=["tag2"],
        confidence=0.7,
        updated_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    store.add(recent_note)

    # Add promoted note (should not expire)
    promoted_note = ResearchNote(
        id="n3",
        topic="test",
        content="promoted note",
        tags=["tag3"],
        confidence=0.9,
        updated_at=datetime.now(timezone.utc) - timedelta(days=200),
    )
    store.add(promoted_note)

    decisions = controller.expire_stale(older_than_days=180)

    # Should only expire old, non-promoted note
    assert len(decisions) == 1
    assert decisions[0].action == "EXPIRE"
    assert decisions[0].target_id == "n1"


def test_write_case() -> None:
    from lyra_research.memory import ResearchCase

    class _FakeCaseBank:
        def __init__(self) -> None:
            self.cases: list = []

        def save_case(self, case: ResearchCase) -> None:
            self.cases.append(case)

    case_bank = _FakeCaseBank()
    controller = ResearchMemoryController(case_bank=case_bank)

    case = ResearchCase(
        id="c1",
        topic="test topic",
        domain="test",
        report_summary="test summary",
        quality_score=0.8,
    )
    decision = controller.write_case(case)

    assert decision.action == "WRITE"
    assert decision.target == "case"
    assert decision.target_id == "c1"
    assert len(case_bank.cases) == 1


def test_write_strategy() -> None:
    from lyra_research.memory import ResearchStrategy

    class _FakeStrategyMemory:
        def __init__(self) -> None:
            self.strategies: list = []

        def add(self, strategy: ResearchStrategy) -> None:
            self.strategies.append(strategy)

    strategy_memory = _FakeStrategyMemory()
    controller = ResearchMemoryController(strategy_memory=strategy_memory)

    strategy = ResearchStrategy(
        id="s1",
        topic_type="test",
        domain="test",
        outcome_score=0.8,
        use_count=5,
    )
    decision = controller.write_strategy(strategy)

    assert decision.action == "WRITE"
    assert decision.target == "strategy"
    assert len(strategy_memory.strategies) == 1
