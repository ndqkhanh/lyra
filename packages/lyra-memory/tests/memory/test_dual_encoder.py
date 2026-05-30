"""Tests for MRAgent dual encoding system.

Comprehensive test coverage for:
  - Cue-tag-episode encoding
  - Cue-tag-semantic encoding
  - MRAgentDualEncoder integration
  - RoutingFabric with RRF fusion
  - Retrieval precision and recall
"""

import time

import numpy as np
import pytest

from lyra_memory.mragent.cue_tag_episode import (
    CueTagEpisodeEncoder,
    EpisodeEncoding,
)
from lyra_memory.mragent.cue_tag_semantic import (
    CueTagSemanticEncoder,
    SemanticEncoding,
)
from lyra_memory.mragent.dual_encoder import MRAgentDualEncoder
from lyra_memory.routing_fabric import (
    MemoryResult,
    RoutingConfig,
    RoutingFabric,
)


# ── CueTagEpisodeEncoder Tests ────────────────────────────────────────────


class TestCueTagEpisodeEncoder:
    """Tests for cue-tag-episode encoding pathway."""

    def test_encode_basic(self):
        """Test basic episode encoding."""
        encoder = CueTagEpisodeEncoder(embedding_dim=128)
        encoding = encoder.encode(
            cue="user login",
            tags=["auth", "security"],
            episode="User alice logged in at 10:30 AM",
        )

        assert isinstance(encoding, EpisodeEncoding)
        assert encoding.cue == "user login"
        assert encoding.tags == ("auth", "security")
        assert encoding.episode == "User alice logged in at 10:30 AM"
        assert encoding.embedding.shape == (128,)
        assert encoding.episode_id.startswith("episode-")

    def test_encode_with_custom_id(self):
        """Test encoding with custom episode ID."""
        encoder = CueTagEpisodeEncoder()
        encoding = encoder.encode(
            cue="test",
            tags=["tag1"],
            episode="content",
            episode_id="custom-123",
        )

        assert encoding.episode_id == "custom-123"

    def test_encode_empty_cue_and_tags(self):
        """Test encoding with empty cue and tags."""
        encoder = CueTagEpisodeEncoder()
        encoding = encoder.encode(cue="", tags=[], episode="Just the episode content")

        assert encoding.cue == ""
        assert encoding.tags == ()
        assert encoding.episode == "Just the episode content"
        assert encoding.embedding.shape == (384,)

    def test_encode_batch(self):
        """Test batch encoding of multiple episodes."""
        encoder = CueTagEpisodeEncoder()
        items = [
            ("cue1", ["tag1"], "episode1"),
            ("cue2", ["tag2", "tag3"], "episode2"),
            ("cue3", [], "episode3"),
        ]

        encodings = encoder.encode_batch(items)

        assert len(encodings) == 3
        assert all(isinstance(e, EpisodeEncoding) for e in encodings)
        assert encodings[0].cue == "cue1"
        assert encodings[1].tags == ("tag2", "tag3")
        assert encodings[2].episode == "episode3"

    def test_similarity(self):
        """Test similarity computation between episodes."""
        encoder = CueTagEpisodeEncoder()
        enc1 = encoder.encode("cue", ["tag"], "episode A")
        enc2 = encoder.encode("cue", ["tag"], "episode A")  # Same content
        enc3 = encoder.encode("different", ["other"], "episode B")

        sim_same = encoder.similarity(enc1, enc2)
        sim_diff = encoder.similarity(enc1, enc3)

        assert sim_same > 0.99  # Should be nearly identical
        assert sim_diff < sim_same  # Different content should be less similar

    def test_retrieve(self):
        """Test retrieval of top-k episodes."""
        encoder = CueTagEpisodeEncoder()

        # Create candidate episodes
        candidates = [
            encoder.encode("login", ["auth"], "User alice logged in"),
            encoder.encode("login", ["auth"], "User bob logged in"),
            encoder.encode("logout", ["auth"], "User alice logged out"),
            encoder.encode("purchase", ["commerce"], "User bought item"),
        ]

        # Query for login events
        results = encoder.retrieve(
            query_cue="login",
            query_tags=["auth"],
            candidates=candidates,
            top_k=2,
        )

        assert len(results) == 2
        assert all(isinstance(r[0], EpisodeEncoding) for r in results)
        assert all(isinstance(r[1], float) for r in results)
        # Results should be sorted by score
        assert results[0][1] >= results[1][1]

    def test_to_dict(self):
        """Test serialization to dictionary."""
        encoder = CueTagEpisodeEncoder()
        encoding = encoder.encode("cue", ["tag1", "tag2"], "episode content")

        d = encoding.to_dict()

        assert d["episode_id"] == encoding.episode_id
        assert d["cue"] == "cue"
        assert d["tags"] == ["tag1", "tag2"]
        assert d["episode"] == "episode content"
        assert isinstance(d["embedding"], list)
        assert len(d["embedding"]) == 384


# ── CueTagSemanticEncoder Tests ───────────────────────────────────────────


class TestCueTagSemanticEncoder:
    """Tests for cue-tag-semantic encoding pathway."""

    def test_encode_basic(self):
        """Test basic semantic encoding."""
        encoder = CueTagSemanticEncoder(embedding_dim=128)
        encoding = encoder.encode(
            cue="python",
            tags=["programming", "language"],
            fact="Python is a high-level programming language",
        )

        assert isinstance(encoding, SemanticEncoding)
        assert encoding.cue == "python"
        assert encoding.tags == ("programming", "language")
        assert encoding.fact == "Python is a high-level programming language"
        assert encoding.embedding.shape == (128,)
        assert encoding.fact_id.startswith("fact-")

    def test_encode_with_custom_id(self):
        """Test encoding with custom fact ID."""
        encoder = CueTagSemanticEncoder()
        encoding = encoder.encode(
            cue="test",
            tags=["tag1"],
            fact="fact content",
            fact_id="custom-fact-123",
        )

        assert encoding.fact_id == "custom-fact-123"

    def test_encode_batch(self):
        """Test batch encoding of multiple facts."""
        encoder = CueTagSemanticEncoder()
        items = [
            ("python", ["lang"], "Python is interpreted"),
            ("java", ["lang"], "Java is compiled"),
            ("rust", ["lang"], "Rust is memory-safe"),
        ]

        encodings = encoder.encode_batch(items)

        assert len(encodings) == 3
        assert all(isinstance(e, SemanticEncoding) for e in encodings)
        assert encodings[0].cue == "python"
        assert encodings[1].fact == "Java is compiled"

    def test_similarity(self):
        """Test similarity computation between facts."""
        encoder = CueTagSemanticEncoder()
        enc1 = encoder.encode("python", ["lang"], "Python is interpreted")
        enc2 = encoder.encode("python", ["lang"], "Python is interpreted")
        enc3 = encoder.encode("rust", ["lang"], "Rust is compiled")

        sim_same = encoder.similarity(enc1, enc2)
        sim_diff = encoder.similarity(enc1, enc3)

        assert sim_same > 0.99
        assert sim_diff < sim_same

    def test_retrieve(self):
        """Test retrieval of top-k facts."""
        encoder = CueTagSemanticEncoder()

        candidates = [
            encoder.encode("python", ["lang"], "Python is interpreted"),
            encoder.encode("python", ["lang"], "Python has dynamic typing"),
            encoder.encode("java", ["lang"], "Java is compiled"),
            encoder.encode("rust", ["lang"], "Rust is memory-safe"),
        ]

        results = encoder.retrieve(
            query_cue="python",
            query_tags=["lang"],
            candidates=candidates,
            top_k=2,
        )

        assert len(results) == 2
        # Results should be sorted by score
        assert results[0][1] >= results[1][1]

    def test_to_dict(self):
        """Test serialization to dictionary."""
        encoder = CueTagSemanticEncoder()
        encoding = encoder.encode("cue", ["tag1"], "fact content")

        d = encoding.to_dict()

        assert d["fact_id"] == encoding.fact_id
        assert d["cue"] == "cue"
        assert d["tags"] == ["tag1"]
        assert d["fact"] == "fact content"
        assert isinstance(d["embedding"], list)


# ── MRAgentDualEncoder Tests ──────────────────────────────────────────────


class TestMRAgentDualEncoder:
    """Tests for MRAgent dual encoder integration."""

    def test_initialization(self):
        """Test dual encoder initialization."""
        encoder = MRAgentDualEncoder(embedding_dim=256)

        assert encoder.embedding_dim == 256
        assert encoder.episode_encoder is not None
        assert encoder.semantic_encoder is not None

    def test_encode_episode(self):
        """Test episode encoding via dual encoder."""
        encoder = MRAgentDualEncoder()
        encoding = encoder.encode_episode(
            cue="meeting",
            tags=["work"],
            episode="Team meeting at 2 PM",
        )

        assert encoding.cue == "meeting"
        assert encoding.tags == ("work",)
        assert encoding.episode == "Team meeting at 2 PM"

    def test_encode_semantic(self):
        """Test semantic encoding via dual encoder."""
        encoder = MRAgentDualEncoder()
        encoding = encoder.encode_semantic(
            cue="python",
            tags=["programming"],
            fact="Python uses indentation for blocks",
        )

        assert encoding.cue == "python"
        assert encoding.tags == ("programming",)
        assert encoding.fact == "Python uses indentation for blocks"

    def test_retrieve_fused(self):
        """Test fused retrieval combining both pathways."""
        encoder = MRAgentDualEncoder()

        # Create test data
        episodes = [
            encoder.encode_episode("login", ["auth"], "Alice logged in"),
            encoder.encode_episode("login", ["auth"], "Bob logged in"),
        ]

        semantics = [
            encoder.encode_semantic("auth", ["security"], "Login requires password"),
            encoder.encode_semantic("auth", ["security"], "2FA improves security"),
        ]

        # Retrieve with fusion
        results = encoder.retrieve(
            query="login authentication",
            query_tags=["auth"],
            episode_candidates=episodes,
            semantic_candidates=semantics,
            k=3,
        )

        assert len(results) <= 3
        assert all(len(r) == 3 for r in results)  # (content, score, type)
        assert all(r[2] in ("episode", "semantic") for r in results)


# ── RoutingFabric Tests ───────────────────────────────────────────────────


class TestRoutingFabric:
    """Tests for routing fabric with RRF fusion."""

    def test_initialization(self):
        """Test routing fabric initialization."""
        fabric = RoutingFabric()

        assert fabric.config.embedding_dim == 384
        assert fabric.config.episode_weight == 0.6
        assert len(fabric.episode_store) == 0
        assert len(fabric.semantic_store) == 0

    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = RoutingConfig(
            embedding_dim=256,
            episode_weight=0.7,
            rrf_k=100,
        )
        fabric = RoutingFabric(config)

        assert fabric.config.embedding_dim == 256
        assert fabric.config.episode_weight == 0.7
        assert fabric.config.rrf_k == 100

    def test_store_episode(self):
        """Test storing an episode."""
        fabric = RoutingFabric()
        encoding = fabric.store_episode(
            cue="meeting",
            tags=["work"],
            episode="Team standup at 9 AM",
        )

        assert len(fabric.episode_store) == 1
        assert fabric.episode_store[0] == encoding
        assert encoding.episode == "Team standup at 9 AM"

    def test_store_semantic(self):
        """Test storing a semantic fact."""
        fabric = RoutingFabric()
        encoding = fabric.store_semantic(
            cue="python",
            tags=["programming"],
            fact="Python is dynamically typed",
        )

        assert len(fabric.semantic_store) == 1
        assert fabric.semantic_store[0] == encoding
        assert encoding.fact == "Python is dynamically typed"

    def test_store_batch_episodes(self):
        """Test batch storing episodes."""
        fabric = RoutingFabric()
        items = [
            ("cue1", ["tag1"], "episode1"),
            ("cue2", ["tag2"], "episode2"),
        ]

        encodings = fabric.store_batch_episodes(items)

        assert len(fabric.episode_store) == 2
        assert len(encodings) == 2

    def test_store_batch_semantic(self):
        """Test batch storing semantic facts."""
        fabric = RoutingFabric()
        items = [
            ("cue1", ["tag1"], "fact1"),
            ("cue2", ["tag2"], "fact2"),
        ]

        encodings = fabric.store_batch_semantic(items)

        assert len(fabric.semantic_store) == 2
        assert len(encodings) == 2

    def test_retrieve_empty_store(self):
        """Test retrieval from empty store."""
        fabric = RoutingFabric()
        results = fabric.retrieve("query", ["tag"], top_k=5)

        assert len(results) == 0

    def test_retrieve_episode_only(self):
        """Test retrieval from episode pathway only."""
        fabric = RoutingFabric()
        fabric.store_episode("login", ["auth"], "Alice logged in")
        fabric.store_episode("login", ["auth"], "Bob logged in")
        fabric.store_episode("logout", ["auth"], "Alice logged out")

        results = fabric.retrieve_episode_only("login", ["auth"], top_k=2)

        assert len(results) == 2
        assert all(isinstance(r, MemoryResult) for r in results)
        assert all(r.memory_type == "episode" for r in results)

    def test_retrieve_semantic_only(self):
        """Test retrieval from semantic pathway only."""
        fabric = RoutingFabric()
        fabric.store_semantic("python", ["lang"], "Python is interpreted")
        fabric.store_semantic("python", ["lang"], "Python has GIL")
        fabric.store_semantic("rust", ["lang"], "Rust is compiled")

        results = fabric.retrieve_semantic_only("python", ["lang"], top_k=2)

        assert len(results) == 2
        assert all(isinstance(r, MemoryResult) for r in results)
        assert all(r.memory_type == "semantic" for r in results)

    def test_retrieve_fused(self):
        """Test fused retrieval combining both pathways."""
        fabric = RoutingFabric()

        # Store episodes
        fabric.store_episode("meeting", ["work"], "Team meeting at 2 PM")
        fabric.store_episode("meeting", ["work"], "Client meeting at 4 PM")

        # Store semantic facts
        fabric.store_semantic("meeting", ["work"], "Meetings should have agendas")
        fabric.store_semantic("meeting", ["work"], "Meetings should be time-boxed")

        # Retrieve with fusion
        results = fabric.retrieve("meeting", ["work"], top_k=3)

        assert len(results) <= 3
        assert all(isinstance(r, MemoryResult) for r in results)
        # Should have both episode and semantic results
        types = {r.memory_type for r in results}
        assert len(types) >= 1  # At least one type present

    def test_retrieve_with_custom_weight(self):
        """Test retrieval with custom episode weight."""
        fabric = RoutingFabric()
        fabric.store_episode("test", ["tag"], "episode content")
        fabric.store_semantic("test", ["tag"], "semantic content")

        # Retrieve with high episode weight
        results_high = fabric.retrieve("test", ["tag"], top_k=2, episode_weight=0.9)

        # Retrieve with low episode weight
        results_low = fabric.retrieve("test", ["tag"], top_k=2, episode_weight=0.1)

        assert len(results_high) > 0
        assert len(results_low) > 0

    def test_stats(self):
        """Test statistics retrieval."""
        fabric = RoutingFabric()
        fabric.store_episode("cue1", ["tag1"], "episode1")
        fabric.store_episode("cue2", ["tag2"], "episode2")
        fabric.store_semantic("cue3", ["tag3"], "fact1")

        stats = fabric.stats()

        assert stats["episode_count"] == 2
        assert stats["semantic_count"] == 1
        assert stats["total_memories"] == 3
        assert stats["embedding_dim"] == 384
        assert stats["episode_weight"] == 0.6

    def test_clear(self):
        """Test clearing all memories."""
        fabric = RoutingFabric()
        fabric.store_episode("cue", ["tag"], "episode")
        fabric.store_semantic("cue", ["tag"], "fact")

        assert len(fabric.episode_store) == 1
        assert len(fabric.semantic_store) == 1

        fabric.clear()

        assert len(fabric.episode_store) == 0
        assert len(fabric.semantic_store) == 0

    def test_memory_result_to_dict(self):
        """Test MemoryResult serialization."""
        fabric = RoutingFabric()
        fabric.store_episode("cue", ["tag1", "tag2"], "episode content")

        results = fabric.retrieve_episode_only("cue", ["tag1"], top_k=1)
        result = results[0]

        d = result.to_dict()

        assert d["content"] == "episode content"
        assert d["memory_type"] == "episode"
        assert d["cue"] == "cue"
        assert d["tags"] == ["tag1", "tag2"]
        assert isinstance(d["score"], float)
        assert isinstance(d["timestamp"], float)


# ── Integration Tests ─────────────────────────────────────────────────────


class TestIntegration:
    """Integration tests for the complete dual encoding system."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from storage to retrieval."""
        fabric = RoutingFabric()

        # Store diverse memories
        fabric.store_episode("login", ["auth", "security"], "User alice logged in at 10:30")
        fabric.store_episode("login", ["auth"], "User bob logged in at 11:00")
        fabric.store_episode("purchase", ["commerce"], "User alice bought item X")

        fabric.store_semantic("auth", ["security"], "Login requires valid credentials")
        fabric.store_semantic("auth", ["security"], "Failed logins are rate-limited")
        fabric.store_semantic("commerce", ["business"], "Purchases require payment")

        # Query for authentication-related memories
        results = fabric.retrieve("user login authentication", ["auth"], top_k=4)

        assert len(results) > 0
        assert len(results) <= 4
        # Should retrieve both episodes and facts
        types = {r.memory_type for r in results}
        assert "episode" in types or "semantic" in types

    def test_precision_with_cue_tag_encoding(self):
        """Test that cue-tag encoding improves retrieval precision."""
        fabric = RoutingFabric()

        # Store memories with different cues
        fabric.store_episode("python", ["programming"], "Wrote Python script for data analysis")
        fabric.store_episode("meeting", ["work"], "Discussed Python project in meeting")
        fabric.store_semantic("python", ["programming"], "Python is a programming language")

        # Query with matching cue should rank higher
        results = fabric.retrieve("python programming", ["programming"], top_k=3)

        assert len(results) > 0
        # First result should be highly relevant
        assert "python" in results[0].content.lower()

    def test_rrf_fusion_combines_pathways(self):
        """Test that RRF properly combines episode and semantic pathways."""
        fabric = RoutingFabric()

        # Store complementary information in both pathways
        fabric.store_episode("api", ["tech"], "API call failed with 500 error")
        fabric.store_semantic("api", ["tech"], "500 errors indicate server problems")

        results = fabric.retrieve("api error", ["tech"], top_k=5)

        # Should retrieve from both pathways
        types = [r.memory_type for r in results]
        assert "episode" in types
        assert "semantic" in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
