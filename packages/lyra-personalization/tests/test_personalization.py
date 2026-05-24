"""
Comprehensive tests for the lyra-personalization package.

Covers all modules: models, profile, embeddings, memory, and autonomy.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from lyra_personalization.autonomy import (
    AutonomyController,
    AutonomyLevel,
    EscalationRecord,
)
from lyra_personalization.embeddings import (
    CompactEmbedding,
    EmbeddingManager,
    PrivacyBudget,
)
from lyra_personalization.memory import MemoryEntry, TripartiteMemory
from lyra_personalization.models import (
    CommunicationStyle,
    InteractionRecord,
    RichRepresentation,
    SkillLevel,
    UserProfile,
    WorkingMemory,
)
from lyra_personalization.profile import UserProfileManager

# =============================================================================
# Models Tests
# =============================================================================


class TestInteractionRecord:
    """Tests for InteractionRecord frozen dataclass."""

    def test_creation_defaults(self):
        """Test creation with default values."""
        record = InteractionRecord(content="Hello")
        assert record.content == "Hello"
        assert record.type == "query"
        assert 0.0 <= record.importance <= 1.0
        assert record.id is not None

    def test_frozen_immutability(self):
        """Test that frozen dataclass cannot be mutated."""
        record = InteractionRecord(content="Test")
        with pytest.raises(AttributeError):
            record.content = "New content"  # type: ignore[misc]

    def test_invalid_importance(self):
        """Test validation of importance field."""
        with pytest.raises(ValueError, match="Importance must be"):
            InteractionRecord(content="Test", importance=1.5)
        with pytest.raises(ValueError, match="Importance must be"):
            InteractionRecord(content="Test", importance=-0.1)

    def test_valid_importance(self):
        """Test valid importance values."""
        record = InteractionRecord(content="Test", importance=0.5)
        assert record.importance == 0.5

    def test_full_creation(self):
        """Test creation with all fields."""
        now = datetime.now()
        record = InteractionRecord(
            content="Show me the code",
            session_id="sess-1",
            type="query",
            outcome="success",
            importance=0.8,
            metadata={"duration_ms": 150},
        )
        assert record.session_id == "sess-1"
        assert record.type == "query"
        assert record.outcome == "success"
        assert record.importance == 0.8
        assert record.metadata["duration_ms"] == 150


class TestSkillLevel:
    """Tests for SkillLevel enum."""

    def test_all_levels(self):
        """Test all skill level values."""
        assert SkillLevel.NOVICE.value == "novice"
        assert SkillLevel.BEGINNER.value == "beginner"
        assert SkillLevel.INTERMEDIATE.value == "intermediate"
        assert SkillLevel.ADVANCED.value == "advanced"
        assert SkillLevel.EXPERT.value == "expert"

    def test_ordering(self):
        """Test skill level ordering by definition."""
        levels = list(SkillLevel)
        names = [l.value for l in levels]
        assert names == ["novice", "beginner", "intermediate", "advanced", "expert"]


class TestAutonomyLevel:
    """Tests for AutonomyLevel enum."""

    def test_all_levels(self):
        """Test all autonomy level values."""
        assert AutonomyLevel.FULLY_AUTONOMOUS.value == "fully_autonomous"
        assert AutonomyLevel.SUGGEST_ONLY.value == "suggest_only"
        assert AutonomyLevel.MANUAL.value == "manual"


class TestCommunicationStyle:
    """Tests for CommunicationStyle enum."""

    def test_all_styles(self):
        """Test all communication style values."""
        assert CommunicationStyle.CONCISE.value == "concise"
        assert CommunicationStyle.BALANCED.value == "balanced"
        assert CommunicationStyle.VERBOSE.value == "verbose"
        assert CommunicationStyle.TECHNICAL.value == "technical"
        assert CommunicationStyle.EDUCATIONAL.value == "educational"


class TestCompactEmbedding:
    """Tests for CompactEmbedding frozen dataclass."""

    def test_creation(self):
        """Test basic creation."""
        emb = CompactEmbedding(
            user_id="user-1",
            vector=[0.1, 0.2, 0.3],
        )
        assert emb.user_id == "user-1"
        assert emb.vector == [0.1, 0.2, 0.3]
        assert emb.version == 1

    def test_token_estimate(self):
        """Test token estimate calculation."""
        emb = CompactEmbedding(
            user_id="user-1",
            compressed_tokens="user concise python advanced",
        )
        assert emb.token_estimate == 30

    def test_default_token_estimate(self):
        """Test default token estimate when no compressed_tokens."""
        emb = CompactEmbedding(user_id="user-1")
        assert emb.token_estimate == 30

    def test_frozen(self):
        """Test immutability."""
        emb = CompactEmbedding(user_id="user-1")
        with pytest.raises(AttributeError):
            emb.user_id = "user-2"  # type: ignore[misc]


class TestRichRepresentation:
    """Tests for RichRepresentation frozen dataclass."""

    def test_creation(self):
        """Test basic creation."""
        repr_ = RichRepresentation(user_id="user-1")
        assert repr_.user_id == "user-1"
        assert repr_.total_interactions == 0
        assert repr_.communication_style == CommunicationStyle.BALANCED

    def test_with_interactions(self):
        """Test with interaction history."""
        interactions = [
            InteractionRecord(content="Hello", importance=0.5),
            InteractionRecord(content="World", importance=0.8),
        ]
        repr_ = RichRepresentation(
            user_id="user-1",
            interaction_history=interactions,
        )
        assert repr_.total_interactions == 2

    def test_with_preferences(self):
        """Test with preferences."""
        repr_ = RichRepresentation(
            user_id="user-1",
            preferences={"theme": "dark", "language": "python"},
        )
        assert repr_.preferences["theme"] == "dark"
        assert repr_.preferences["language"] == "python"


class TestWorkingMemory:
    """Tests for WorkingMemory frozen dataclass."""

    def test_creation(self):
        """Test basic creation."""
        wm = WorkingMemory()
        assert wm.session_id is not None
        assert wm.active_task is None
        assert not wm.is_expired()

    def test_expiry(self):
        """Test TTL expiry."""
        old = WorkingMemory(
            created_at=datetime.now() - timedelta(hours=2),
            ttl=timedelta(hours=1),
        )
        assert old.is_expired()

    def test_not_expired(self):
        """Test within TTL."""
        recent = WorkingMemory(
            created_at=datetime.now() - timedelta(minutes=30),
            ttl=timedelta(hours=1),
        )
        assert not recent.is_expired()

    def test_with_entries(self):
        """Test working memory with entries."""
        wm = WorkingMemory(
            entries={"task": "coding", "file": "main.py"},
            active_task="refactor module",
            recent_tool_calls=["read", "edit"],
        )
        assert wm.entries["task"] == "coding"
        assert wm.active_task == "refactor module"
        assert len(wm.recent_tool_calls) == 2


class TestUserProfile:
    """Tests for UserProfile frozen dataclass."""

    def test_creation(self):
        """Test basic creation."""
        profile = UserProfile(user_id="user-1")
        assert profile.user_id == "user-1"
        assert profile.autonomy_level == AutonomyLevel.SUGGEST_ONLY
        assert profile.trust_score == 0.5

    def test_frozen(self):
        """Test immutability."""
        profile = UserProfile(user_id="user-1")
        with pytest.raises(AttributeError):
            profile.user_id = "user-2"  # type: ignore[misc]

    def test_with_rich_repr(self):
        """Test profile with rich representation."""
        rich = RichRepresentation(
            user_id="user-1",
            preferences={"language": "python"},
        )
        profile = UserProfile(user_id="user-1", rich_repr=rich)
        assert profile.rich_repr.preferences["language"] == "python"


# =============================================================================
# Profile Manager Tests
# =============================================================================


class TestUserProfileManager:
    """Tests for UserProfileManager."""

    def test_create_profile(self):
        """Test creating a new profile."""
        manager = UserProfileManager()
        profile = manager.create_profile("user-1")
        assert profile.user_id == "user-1"
        assert profile.rich_repr.user_id == "user-1"

    def test_duplicate_profile(self):
        """Test duplicate profile creation raises error."""
        manager = UserProfileManager()
        manager.create_profile("user-1")
        with pytest.raises(ValueError, match="already exists"):
            manager.create_profile("user-1")

    def test_get_profile(self):
        """Test retrieving a profile."""
        manager = UserProfileManager()
        manager.create_profile("user-1")
        profile = manager.get_profile("user-1")
        assert profile is not None
        assert profile.user_id == "user-1"

    def test_get_nonexistent_profile(self):
        """Test retrieving a non-existent profile."""
        manager = UserProfileManager()
        profile = manager.get_profile("nonexistent")
        assert profile is None

    def test_update_from_interaction(self):
        """Test updating profile from an interaction."""
        manager = UserProfileManager()
        profile = manager.create_profile("user-1")
        interaction = InteractionRecord(
            content="Write a Python function",
            type="query",
            outcome="success",
            importance=0.7,
        )
        updated = manager.update_from_interaction(profile, interaction)
        assert len(updated.rich_repr.interaction_history) == 1
        assert updated.rich_repr.interaction_history[0].content == "Write a Python function"

    def test_update_from_interaction_internal_state(self):
        """Test that updated profile is stored internally."""
        manager = UserProfileManager()
        profile = manager.create_profile("user-1")
        interaction = InteractionRecord(content="Test", importance=0.6)
        manager.update_from_interaction(profile, interaction)
        retrieved = manager.get_profile("user-1")
        assert retrieved is not None
        assert len(retrieved.rich_repr.interaction_history) == 1

    def test_compute_skill_level_explicit(self):
        """Test skill level assessment with explicit skill."""
        manager = UserProfileManager()
        profile = manager.create_profile("user-1")
        rich = RichRepresentation(
            user_id="user-1",
            skill_levels={"python": SkillLevel.EXPERT},
        )
        profile = UserProfile(
            user_id="user-1",
            rich_repr=rich,
        )
        level = manager.compute_skill_level(profile, "python")
        assert level == SkillLevel.EXPERT

    def test_compute_skill_level_from_history(self):
        """Test skill level assessment from interaction history."""
        manager = UserProfileManager()
        profile = manager.create_profile("user-1")
        interactions = [
            InteractionRecord(
                content="Fix Python bug in parser",
                outcome="success",
                importance=0.8,
            ) for _ in range(20)
        ]
        rich = RichRepresentation(
            user_id="user-1",
            interaction_history=interactions,
        )
        profile = UserProfile(
            user_id="user-1",
            rich_repr=rich,
        )
        level = manager.compute_skill_level(profile, "python")
        assert level in (SkillLevel.ADVANCED, SkillLevel.EXPERT)

    def test_compute_skill_level_no_data(self):
        """Test skill level assessment with no data."""
        manager = UserProfileManager()
        profile = manager.create_profile("user-1")
        level = manager.compute_skill_level(profile, "rust")
        assert level == SkillLevel.NOVICE

    def test_extract_preferences_empty(self):
        """Test preference extraction with no interactions."""
        manager = UserProfileManager()
        prefs = manager.extract_preferences([])
        assert prefs == {}

    def test_extract_preferences_with_data(self):
        """Test preference extraction from interactions."""
        manager = UserProfileManager()
        interactions = [
            InteractionRecord(content="I prefer using the CLI", outcome="success", importance=0.5),
            InteractionRecord(content="CLI tools are fast", outcome="success", importance=0.6),
        ]
        prefs = manager.extract_preferences(interactions)
        assert "preferred_tool_category" in prefs
        assert prefs["preferred_tool_category"] == "cli"

    def test_detect_communication_style_concise(self):
        """Test detecting concise communication style."""
        manager = UserProfileManager()
        interactions = [
            InteractionRecord(content="run", importance=0.3),
            InteractionRecord(content="ok", importance=0.3),
            InteractionRecord(content="done", importance=0.3),
        ]
        style = manager.detect_communication_style(interactions)
        assert style == CommunicationStyle.CONCISE

    def test_detect_communication_style_technical(self):
        """Test detecting technical communication style."""
        manager = UserProfileManager()
        interactions = [
            InteractionRecord(
                content="Refactor the API endpoint to use async/await "
                        "with proper error handling and type checking",
                importance=0.5,
            ),
            InteractionRecord(
                content="The function signature needs a generic type parameter",
                importance=0.5,
            ),
        ]
        style = manager.detect_communication_style(interactions)
        assert style in (CommunicationStyle.TECHNICAL, CommunicationStyle.VERBOSE)

    def test_detect_communication_style_empty(self):
        """Test detecting style with no interactions."""
        manager = UserProfileManager()
        style = manager.detect_communication_style([])
        assert style == CommunicationStyle.BALANCED


# =============================================================================
# Embedding Manager Tests
# =============================================================================


class TestEmbeddingManager:
    """Tests for EmbeddingManager."""

    def test_compute_embedding(self):
        """Test computing embedding from rich representation."""
        manager = EmbeddingManager()
        rich = RichRepresentation(
            user_id="user-1",
            preferences={"language": "python"},
        )
        emb = manager.compute_embedding(rich)
        assert emb.user_id == "user-1"
        assert len(emb.vector) > 0
        assert emb.version == 1

    def test_update_embedding(self):
        """Test updating an embedding with new interaction."""
        manager = EmbeddingManager()
        rich = RichRepresentation(user_id="user-1")
        emb = manager.compute_embedding(rich)
        interaction = InteractionRecord(content="Test", importance=0.7)
        updated = manager.update_embedding(emb, interaction)
        assert updated.version == 2
        assert updated.user_id == "user-1"

    def test_inject_into_context(self):
        """Test injecting embedding into prompt."""
        manager = EmbeddingManager()
        emb = CompactEmbedding(
            user_id="user-1",
            compressed_tokens="user concise python",
        )
        augmented = manager.inject_into_context(emb, "Hello")
        assert "User Context" in augmented
        assert "Hello" in augmented

    def test_compute_similarity_same(self):
        """Test similarity between identical embeddings."""
        manager = EmbeddingManager()
        emb_a = CompactEmbedding(
            user_id="user-1",
            vector=[1.0, 0.0, 0.0],
        )
        emb_b = CompactEmbedding(
            user_id="user-2",
            vector=[1.0, 0.0, 0.0],
        )
        sim = manager.compute_similarity(emb_a, emb_b)
        assert abs(sim - 1.0) < 0.001

    def test_compute_similarity_orthogonal(self):
        """Test similarity between orthogonal embeddings."""
        manager = EmbeddingManager()
        emb_a = CompactEmbedding(
            user_id="user-1",
            vector=[1.0, 0.0],
        )
        emb_b = CompactEmbedding(
            user_id="user-2",
            vector=[0.0, 1.0],
        )
        sim = manager.compute_similarity(emb_a, emb_b)
        assert abs(sim - 0.0) < 0.001

    def test_compute_similarity_empty(self):
        """Test similarity with empty vectors."""
        manager = EmbeddingManager()
        emb_a = CompactEmbedding(user_id="user-1")
        emb_b = CompactEmbedding(user_id="user-2")
        sim = manager.compute_similarity(emb_a, emb_b)
        assert sim == 0.0

    def test_compress_for_transport(self):
        """Test transport compression."""
        manager = EmbeddingManager()
        emb = CompactEmbedding(
            user_id="user-1",
            vector=[0.5, -0.3, 0.8, 0.1, -0.6, 0.2, 0.9, -0.4, 0.7, 0.0] * 6,
            version=3,
        )
        compressed = manager.compress_for_transport(emb)
        assert compressed.startswith("v3:")

    def test_privacy_budget(self):
        """Test privacy budget tracking."""
        manager = EmbeddingManager()
        budget = manager.compute_privacy_budget()
        assert budget.epsilon_spent == 0.0
        assert budget.remaining == 10.0
        assert not budget.is_exhausted

        # Spending budget
        budget.spend(2.0)
        assert budget.epsilon_spent == 2.0
        assert abs(budget.remaining - 8.0) < 0.001


class TestPrivacyBudget:
    """Tests for PrivacyBudget dataclass."""

    def test_initial_state(self):
        """Test initial budget state."""
        budget = PrivacyBudget()
        assert budget.epsilon_spent == 0.0
        assert budget.epsilon_budget == 10.0
        assert not budget.is_exhausted

    def test_spend_valid(self):
        """Test spending within budget."""
        budget = PrivacyBudget()
        assert budget.spend(5.0) is True
        assert budget.epsilon_spent == 5.0

    def test_spend_exhausted(self):
        """Test spending when budget is exhausted."""
        budget = PrivacyBudget(epsilon_spent=9.9)
        assert budget.spend(0.5) is False
        assert budget.epsilon_spent == 9.9

    def test_remaining(self):
        """Test remaining budget calculation."""
        budget = PrivacyBudget(epsilon_spent=3.0)
        assert abs(budget.remaining - 7.0) < 0.001


# =============================================================================
# Tripartite Memory Tests
# =============================================================================


class TestTripartiteMemory:
    """Tests for TripartiteMemory."""

    def test_add_to_working(self):
        """Test adding to working memory."""
        memory = TripartiteMemory()
        entry = MemoryEntry(content="Current task: refactor", memory_type="working")
        memory.add_to_working(entry)
        assert memory.working_count == 1

    def test_promote_to_episodic(self):
        """Test promoting working memory to episodic."""
        memory = TripartiteMemory()
        entry = MemoryEntry(content="Important event", memory_type="working", importance=0.8)
        memory.add_to_working(entry)
        memory.promote_to_episodic(entry)
        assert memory.working_count == 0
        assert memory.episodic_count == 1

    def test_consolidate_to_semantic(self):
        """Test consolidating episodic to semantic."""
        memory = TripartiteMemory(semantic_cooldown=timedelta(seconds=0))
        entry = MemoryEntry(
            content="User prefers Python 3.12",
            memory_type="episodic",
            importance=0.9,
        )
        memory._episodic.append(entry)
        memory.consolidate_to_semantic([entry])
        assert memory.semantic_count == 1
        assert memory.episodic_count == 0

    def test_consolidate_low_importance_skipped(self):
        """Test that low-importance entries are not consolidated."""
        memory = TripartiteMemory(semantic_cooldown=timedelta(seconds=0))
        entry = MemoryEntry(
            content="Trivial detail",
            memory_type="episodic",
            importance=0.1,
        )
        memory._episodic.append(entry)
        memory.consolidate_to_semantic([entry])
        assert memory.semantic_count == 0
        assert memory.episodic_count == 1

    def test_search_memory(self):
        """Test searching across memory tiers."""
        memory = TripartiteMemory()
        memory.add_to_working(MemoryEntry(content="Python function", memory_type="working"))
        memory._episodic.append(MemoryEntry(content="Python bug fix", memory_type="episodic", importance=0.7))
        memory._semantic.append(MemoryEntry(content="Python expertise", memory_type="semantic", importance=0.9))
        results = memory.search_memory("python", memory_type="all")
        assert len(results) == 3

    def test_search_specific_type(self):
        """Test searching a specific memory type."""
        memory = TripartiteMemory()
        memory._episodic.append(MemoryEntry(content="Episodic python", memory_type="episodic", importance=0.6))
        memory._semantic.append(MemoryEntry(content="Semantic python", memory_type="semantic", importance=0.9))
        results = memory.search_memory("python", memory_type="semantic")
        assert len(results) == 1
        assert results[0].memory_type == "semantic"

    def test_forget_old_entries(self):
        """Test pruning old entries."""
        memory = TripartiteMemory()
        old = MemoryEntry(
            content="Old memory",
            memory_type="episodic",
            importance=0.1,
            timestamp=datetime.now() - timedelta(days=30),
        )
        recent = MemoryEntry(
            content="Recent memory",
            memory_type="episodic",
            importance=0.5,
            timestamp=datetime.now(),
        )
        memory._episodic = [old, recent]
        pruned = memory.forget_old_entries(timedelta(days=7))
        assert pruned == 1
        assert memory.episodic_count == 1

    def test_clear_working_memory(self):
        """Test clearing working memory."""
        memory = TripartiteMemory()
        memory.add_to_working(MemoryEntry(content="Entry 1", memory_type="working"))
        memory.add_to_working(MemoryEntry(content="Entry 2", memory_type="working"))
        cleared = memory.clear_working_memory()
        assert cleared == 2
        assert memory.working_count == 0

    def test_add_interaction(self):
        """Test adding an interaction record."""
        memory = TripartiteMemory()
        interaction = InteractionRecord(
            content="Test interaction",
            importance=0.7,
        )
        memory.add_interaction(interaction)
        assert memory.working_count > 0
        assert memory.episodic_count == 1

    def test_add_interaction_low_importance(self):
        """Test adding low-importance interaction."""
        memory = TripartiteMemory(importance_threshold=0.5)
        interaction = InteractionRecord(
            content="Low importance",
            importance=0.1,
        )
        memory.add_interaction(interaction)
        assert memory.working_count > 0
        assert memory.episodic_count == 0

    def test_get_episodic_highlights(self):
        """Test getting episodic highlights."""
        memory = TripartiteMemory()
        memory._episodic = [
            MemoryEntry(content="Low", memory_type="episodic", importance=0.3),
            MemoryEntry(content="High", memory_type="episodic", importance=0.9),
            MemoryEntry(content="Medium", memory_type="episodic", importance=0.6),
        ]
        highlights = memory.get_episodic_highlights(limit=2)
        assert len(highlights) == 2
        assert highlights[0].content == "High"
        assert highlights[1].content == "Medium"

    def test_get_all_working_entries(self):
        """Test retrieving all working entries."""
        memory = TripartiteMemory()
        memory.add_to_working(MemoryEntry(content="Entry 1", memory_type="working"))
        memory.add_to_working(MemoryEntry(content="Entry 2", memory_type="working"))
        entries = memory.get_all_working_entries()
        assert len(entries) == 2


# =============================================================================
# Autonomy Controller Tests
# =============================================================================


class TestAutonomyController:
    """Tests for AutonomyController."""

    def test_get_autonomy_level_high_trust(self):
        """Test high trust leads to full autonomy."""
        controller = AutonomyController()
        profile = UserProfile(
            user_id="user-1",
            trust_score=0.9,
        )
        level = controller.get_autonomy_level(profile, "Write code")
        assert level == AutonomyLevel.FULLY_AUTONOMOUS

    def test_get_autonomy_level_low_trust(self):
        """Test low trust leads to manual."""
        controller = AutonomyController()
        profile = UserProfile(
            user_id="user-1",
            trust_score=0.1,
        )
        level = controller.get_autonomy_level(profile, "Write code")
        assert level == AutonomyLevel.MANUAL

    def test_get_autonomy_level_critical_task(self):
        """Test critical task forces manual."""
        controller = AutonomyController()
        profile = UserProfile(
            user_id="user-1",
            trust_score=0.9,
        )
        level = controller.get_autonomy_level(
            profile,
            "Delete production database and reset permissions",
        )
        assert level == AutonomyLevel.MANUAL

    def test_should_escalate_low_confidence(self):
        """Test low confidence triggers escalation."""
        controller = AutonomyController()
        assert controller.should_escalate("Write code", 0.1)

    def test_should_not_escalate_high_confidence(self):
        """Test high confidence avoids escalation."""
        controller = AutonomyController()
        assert not controller.should_escalate("Write code", 0.9)

    def test_should_escalate_high_stakes(self):
        """Test high-stakes action triggers escalation."""
        controller = AutonomyController()
        assert controller.should_escalate("delete all files", 0.9)

    def test_should_escalate_recent_denials(self):
        """Test recent denials trigger escalation."""
        controller = AutonomyController()
        for _ in range(3):
            controller.record_escalation_outcome(
                EscalationRecord(action="test", confidence=0.5, approved=False),
            )
        assert controller.should_escalate("Write code", 0.5)

    def test_record_escalation_outcome(self):
        """Test recording escalation outcomes."""
        controller = AutonomyController()
        escalation = EscalationRecord(
            action="Delete file",
            confidence=0.4,
            approved=True,
        )
        controller.record_escalation_outcome(escalation)
        history = controller.get_escalation_history()
        assert len(history) == 1
        assert history[0].action == "Delete file"
        assert history[0].approved is True

    def test_compute_trust_score(self):
        """Test trust score computation."""
        controller = AutonomyController()
        profile = UserProfile(user_id="user-1", trust_score=0.5)
        score = controller.compute_trust_score(profile)
        assert 0.0 <= score <= 1.0

    def test_compute_trust_score_with_history(self):
        """Test trust score with interaction history."""
        controller = AutonomyController()
        interactions = [
            InteractionRecord(content="Task", outcome="success", importance=0.5)
            for _ in range(30)
        ]
        rich = RichRepresentation(
            user_id="user-1",
            interaction_history=interactions,
        )
        profile = UserProfile(user_id="user-1", rich_repr=rich, trust_score=0.5)
        score = controller.compute_trust_score(profile)
        assert 0.0 <= score <= 1.0
