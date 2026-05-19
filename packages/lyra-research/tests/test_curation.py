"""Tests for knowledge curation system."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lyra_research.curation.curation_workflow import (
    CurationDecision,
    CurationWorkflow,
    DecisionType,
)
from lyra_research.curation.curator_metrics import CuratorMetrics
from lyra_research.curation.knowledge_entry import EntryStatus, KnowledgeEntry
from lyra_research.curation.knowledge_store import KnowledgeStore
from lyra_research.curation.knowledge_versioning import (
    KnowledgeVersion,
    VersionManager,
)


# ============================================================================
# Knowledge Entry Tests (3 tests)
# ============================================================================


def test_knowledge_entry_creation():
    """Test creating a knowledge entry."""
    entry = KnowledgeEntry(
        content="Test content",
        source="Test source",
        quality_score=0.85,
        category="research",
        tags=["test", "example"],
    )

    assert entry.content == "Test content"
    assert entry.source == "Test source"
    assert entry.quality_score == 0.85
    assert entry.category == "research"
    assert entry.tags == ["test", "example"]
    assert entry.status == EntryStatus.PENDING
    assert entry.version == 1
    assert entry.id  # UUID generated


def test_knowledge_entry_validation():
    """Test knowledge entry validation."""
    # Empty content
    with pytest.raises(ValueError, match="Content cannot be empty"):
        KnowledgeEntry(
            content="",
            source="Test",
            quality_score=0.8,
            category="test",
            tags=["tag"],
        )

    # Invalid quality score
    with pytest.raises(ValueError, match="Quality score must be between"):
        KnowledgeEntry(
            content="Test",
            source="Test",
            quality_score=1.5,
            category="test",
            tags=["tag"],
        )

    # Empty tags
    with pytest.raises(ValueError, match="Tags cannot be empty"):
        KnowledgeEntry(
            content="Test",
            source="Test",
            quality_score=0.8,
            category="test",
            tags=[],
        )


def test_knowledge_entry_state_transitions():
    """Test knowledge entry state transitions."""
    entry = KnowledgeEntry(
        content="Test",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    # Approve
    approved = entry.approve()
    assert approved.status == EntryStatus.APPROVED
    assert approved.id == entry.id
    assert approved.version == entry.version

    # Reject
    rejected = entry.reject()
    assert rejected.status == EntryStatus.REJECTED

    # Revise
    revised = entry.revise("New content", 0.9)
    assert revised.status == EntryStatus.REVISED
    assert revised.content == "New content"
    assert revised.quality_score == 0.9
    assert revised.version == entry.version + 1


# ============================================================================
# Curation Workflow Tests (8 tests)
# ============================================================================


def test_curation_workflow_initialization():
    """Test curation workflow initialization."""
    workflow = CurationWorkflow(quality_threshold=0.75)
    assert workflow.quality_threshold == 0.75

    # Invalid threshold
    with pytest.raises(ValueError, match="Quality threshold must be between"):
        CurationWorkflow(quality_threshold=1.5)


def test_curation_workflow_review_approve():
    """Test workflow review with approval."""
    workflow = CurationWorkflow(quality_threshold=0.7)
    entry = KnowledgeEntry(
        content="High quality content",
        source="Test",
        quality_score=0.85,
        category="test",
        tags=["tag"],
    )

    decision = workflow.review(entry)

    assert decision.decision_type == DecisionType.APPROVE
    assert decision.entry_id == entry.id
    assert "meets threshold" in decision.reason


def test_curation_workflow_review_reject():
    """Test workflow review with rejection."""
    workflow = CurationWorkflow(quality_threshold=0.7)
    entry = KnowledgeEntry(
        content="Low quality content",
        source="Test",
        quality_score=0.5,
        category="test",
        tags=["tag"],
    )

    decision = workflow.review(entry)

    assert decision.decision_type == DecisionType.REJECT
    assert decision.entry_id == entry.id
    assert "below threshold" in decision.reason


def test_curation_workflow_review_revision():
    """Test workflow review with revision request."""
    workflow = CurationWorkflow(quality_threshold=0.7)
    entry = KnowledgeEntry(
        content="Borderline content",
        source="Test",
        quality_score=0.65,
        category="test",
        tags=["tag"],
    )

    decision = workflow.review(entry)

    assert decision.decision_type == DecisionType.REQUEST_REVISION
    assert decision.entry_id == entry.id
    assert decision.feedback is not None


def test_curation_workflow_approve():
    """Test workflow approve method."""
    workflow = CurationWorkflow()
    entry = KnowledgeEntry(
        content="Test",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    approved = workflow.approve(entry)

    assert approved.status == EntryStatus.APPROVED
    assert approved.id == entry.id


def test_curation_workflow_reject():
    """Test workflow reject method."""
    workflow = CurationWorkflow()
    entry = KnowledgeEntry(
        content="Test",
        source="Test",
        quality_score=0.5,
        category="test",
        tags=["tag"],
    )

    rejected = workflow.reject(entry, "Quality too low")

    assert rejected.status == EntryStatus.REJECTED
    assert rejected.metadata["rejection_reason"] == "Quality too low"


def test_curation_workflow_request_revision():
    """Test workflow request revision method."""
    workflow = CurationWorkflow()
    entry = KnowledgeEntry(
        content="Test",
        source="Test",
        quality_score=0.65,
        category="test",
        tags=["tag"],
    )

    revised = workflow.request_revision(entry, "Please improve clarity")

    assert revised.status == EntryStatus.PENDING
    assert revised.metadata["revision_feedback"] == "Please improve clarity"
    assert revised.metadata["revision_requested"] is True


def test_curation_workflow_apply_decision():
    """Test applying curation decisions."""
    workflow = CurationWorkflow()
    entry = KnowledgeEntry(
        content="Test",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    # Apply approve decision
    approve_decision = CurationDecision(
        decision_type=DecisionType.APPROVE,
        entry_id=entry.id,
        reason="Good quality",
    )
    approved = workflow.apply_decision(entry, approve_decision)
    assert approved.status == EntryStatus.APPROVED

    # Apply reject decision
    reject_decision = CurationDecision(
        decision_type=DecisionType.REJECT,
        entry_id=entry.id,
        reason="Low quality",
    )
    rejected = workflow.apply_decision(entry, reject_decision)
    assert rejected.status == EntryStatus.REJECTED

    # Apply revision decision
    revision_decision = CurationDecision(
        decision_type=DecisionType.REQUEST_REVISION,
        entry_id=entry.id,
        reason="Needs work",
        feedback="Improve clarity",
    )
    revised = workflow.apply_decision(entry, revision_decision)
    assert revised.metadata["revision_requested"] is True


# ============================================================================
# Knowledge Versioning Tests (6 tests)
# ============================================================================


def test_version_manager_create_version():
    """Test creating a version."""
    manager = VersionManager()
    entry = KnowledgeEntry(
        content="Test content",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    version = manager.create_version(entry, "curator", "Initial version")

    assert version.entry_id == entry.id
    assert version.version == 1
    assert version.content == "Test content"
    assert version.changed_by == "curator"
    assert version.change_reason == "Initial version"


def test_version_manager_get_version_history():
    """Test getting version history."""
    manager = VersionManager()
    entry = KnowledgeEntry(
        content="Version 1",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    # Create multiple versions
    manager.create_version(entry, "curator", "Version 1")

    entry_v2 = entry.revise("Version 2", 0.85)
    manager.create_version(entry_v2, "curator", "Version 2")

    entry_v3 = entry_v2.revise("Version 3", 0.9)
    manager.create_version(entry_v3, "curator", "Version 3")

    history = manager.get_version_history(entry.id)

    assert len(history) == 3
    assert history[0].version == 1
    assert history[1].version == 2
    assert history[2].version == 3


def test_version_manager_get_version():
    """Test getting specific version."""
    manager = VersionManager()
    entry = KnowledgeEntry(
        content="Version 1",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    manager.create_version(entry, "curator", "Version 1")
    entry_v2 = entry.revise("Version 2", 0.85)
    manager.create_version(entry_v2, "curator", "Version 2")

    version = manager.get_version(entry.id, 1)

    assert version is not None
    assert version.version == 1
    assert version.content == "Version 1"


def test_version_manager_get_latest_version():
    """Test getting latest version."""
    manager = VersionManager()
    entry = KnowledgeEntry(
        content="Version 1",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    manager.create_version(entry, "curator", "Version 1")
    entry_v2 = entry.revise("Version 2", 0.85)
    manager.create_version(entry_v2, "curator", "Version 2")

    latest = manager.get_latest_version(entry.id)

    assert latest is not None
    assert latest.version == 2
    assert latest.content == "Version 2"


def test_version_manager_rollback():
    """Test rolling back to previous version."""
    manager = VersionManager()
    entry = KnowledgeEntry(
        content="Version 1",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    manager.create_version(entry, "curator", "Version 1")
    entry_v2 = entry.revise("Version 2", 0.85)
    manager.create_version(entry_v2, "curator", "Version 2")

    # Rollback to version 1
    rolled_back = manager.rollback_to_version(
        entry_v2, 1, "curator", "Reverting changes"
    )

    assert rolled_back.content == "Version 1"
    assert rolled_back.quality_score == 0.8
    assert rolled_back.version == 3  # New version created


def test_version_manager_version_count():
    """Test version count."""
    manager = VersionManager()
    entry = KnowledgeEntry(
        content="Test",
        source="Test",
        quality_score=0.8,
        category="test",
        tags=["tag"],
    )

    assert manager.get_version_count(entry.id) == 0

    manager.create_version(entry, "curator", "Version 1")
    assert manager.get_version_count(entry.id) == 1

    entry_v2 = entry.revise("Version 2", 0.85)
    manager.create_version(entry_v2, "curator", "Version 2")
    assert manager.get_version_count(entry.id) == 2


# ============================================================================
# Curator Metrics Tests (4 tests)
# ============================================================================


def test_curator_metrics_initialization():
    """Test curator metrics initialization."""
    metrics = CuratorMetrics()

    assert metrics.total_reviewed == 0
    assert metrics.approved == 0
    assert metrics.rejected == 0
    assert metrics.revised == 0
    assert metrics.avg_quality_score == 0.0
    assert metrics.acceptance_rate == 0.0


def test_curator_metrics_record_decision():
    """Test recording curation decisions."""
    metrics = CuratorMetrics()

    # Record approve decision
    approve_decision = CurationDecision(
        decision_type=DecisionType.APPROVE,
        entry_id="test-1",
        reason="Good quality",
    )
    metrics.record_decision(approve_decision, 0.85)

    assert metrics.total_reviewed == 1
    assert metrics.approved == 1
    assert metrics.avg_quality_score == 0.85
    assert metrics.acceptance_rate == 1.0

    # Record reject decision
    reject_decision = CurationDecision(
        decision_type=DecisionType.REJECT,
        entry_id="test-2",
        reason="Low quality",
    )
    metrics.record_decision(reject_decision, 0.5)

    assert metrics.total_reviewed == 2
    assert metrics.rejected == 1
    assert metrics.acceptance_rate == 0.5


def test_curator_metrics_get_metrics():
    """Test getting curator metrics."""
    metrics = CuratorMetrics()

    # Record multiple decisions
    metrics.record_decision(
        CurationDecision(DecisionType.APPROVE, "1", "Good"), 0.85
    )
    metrics.record_decision(
        CurationDecision(DecisionType.REJECT, "2", "Bad"), 0.5
    )
    metrics.record_decision(
        CurationDecision(
            DecisionType.REQUEST_REVISION, "3", "Needs work", "Improve"
        ),
        0.65,
    )

    result = metrics.get_metrics()

    assert result["total_reviewed"] == 3
    assert result["approved"] == 1
    assert result["rejected"] == 1
    assert result["revised"] == 1
    assert result["acceptance_rate"] == pytest.approx(0.333, abs=0.01)


def test_curator_metrics_quality_stats():
    """Test quality score statistics."""
    metrics = CuratorMetrics()

    # Record decisions with various quality scores
    metrics.record_decision(
        CurationDecision(DecisionType.APPROVE, "1", "Good"), 0.9
    )
    metrics.record_decision(
        CurationDecision(DecisionType.APPROVE, "2", "Good"), 0.8
    )
    metrics.record_decision(
        CurationDecision(DecisionType.REJECT, "3", "Bad"), 0.5
    )

    stats = metrics.get_quality_stats()

    assert stats["avg"] == pytest.approx(0.733, abs=0.01)
    assert stats["min"] == 0.5
    assert stats["max"] == 0.9
    assert stats["median"] == 0.8


# ============================================================================
# Knowledge Store Tests (4 tests)
# ============================================================================


def test_knowledge_store_initialization():
    """Test knowledge store initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = KnowledgeStore(Path(tmpdir))

        assert store.storage_path.exists()
        assert store.count() == 0


def test_knowledge_store_store_and_retrieve():
    """Test storing and retrieving entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = KnowledgeStore(Path(tmpdir))

        entry = KnowledgeEntry(
            content="Test content",
            source="Test",
            quality_score=0.85,
            category="research",
            tags=["test"],
        )
        approved = entry.approve()

        # Store
        store.store(approved)
        assert store.count() == 1

        # Retrieve
        retrieved = store.retrieve(approved.id)
        assert retrieved is not None
        assert retrieved.content == "Test content"
        assert retrieved.quality_score == 0.85


def test_knowledge_store_search():
    """Test searching entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = KnowledgeStore(Path(tmpdir))

        # Store multiple entries
        entry1 = KnowledgeEntry(
            content="Machine learning research",
            source="Paper 1",
            quality_score=0.9,
            category="research",
            tags=["ml", "ai"],
        ).approve()

        entry2 = KnowledgeEntry(
            content="Deep learning applications",
            source="Paper 2",
            quality_score=0.85,
            category="research",
            tags=["dl", "ai"],
        ).approve()

        entry3 = KnowledgeEntry(
            content="Natural language processing",
            source="Paper 3",
            quality_score=0.8,
            category="nlp",
            tags=["nlp", "ai"],
        ).approve()

        store.store(entry1)
        store.store(entry2)
        store.store(entry3)

        # Search by content
        results = store.search("learning")
        assert len(results) == 2

        # Search by category
        results = store.search("", category="nlp")
        assert len(results) == 1

        # Search by tag
        results = store.search("ai")
        assert len(results) == 3


def test_knowledge_store_get_by_category():
    """Test getting entries by category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = KnowledgeStore(Path(tmpdir))

        entry1 = KnowledgeEntry(
            content="Research 1",
            source="Test",
            quality_score=0.9,
            category="research",
            tags=["tag"],
        ).approve()

        entry2 = KnowledgeEntry(
            content="Research 2",
            source="Test",
            quality_score=0.85,
            category="research",
            tags=["tag"],
        ).approve()

        entry3 = KnowledgeEntry(
            content="Tutorial 1",
            source="Test",
            quality_score=0.8,
            category="tutorial",
            tags=["tag"],
        ).approve()

        store.store(entry1)
        store.store(entry2)
        store.store(entry3)

        research_entries = store.get_by_category("research")
        assert len(research_entries) == 2

        tutorial_entries = store.get_by_category("tutorial")
        assert len(tutorial_entries) == 1
