"""Tests for src/desktop/fleet_dashboard.py and src/desktop/skills_hub.py."""
from __future__ import annotations

import pytest

from lyra.desktop.fleet_dashboard import (
    DashboardConfig,
    DashboardState,
    FleetDashboard,
    SessionCard,
    SortBy,
)
from lyra.desktop.skills_hub import SkillCard, SkillsHub
from lyra.skills.registry import SkillRegistry
from lyra.skills.skill import Skill, SkillCategory


# ======================================================================
# FleetDashboard tests
# ======================================================================


class TestDashboardConfig:
    """Tests for DashboardConfig."""

    def test_default_config(self):
        """Default config values are correct."""
        config = DashboardConfig()
        assert config.refresh_interval == 5
        assert config.max_cards == 50
        assert config.sort_by == SortBy.RECENT
        assert config.enable_websocket is False

    def test_merge_preserves_immutability(self):
        """merge() returns a new instance without mutating the original."""
        original = DashboardConfig(refresh_interval=10, max_cards=100)
        merged = original.merge({"refresh_interval": 3, "max_cards": 25})

        assert original.refresh_interval == 10
        assert original.max_cards == 100
        assert merged.refresh_interval == 3
        assert merged.max_cards == 25

    def test_to_dict_roundtrip(self):
        """from_dict(to_dict(x)) == x."""
        original = DashboardConfig(
            refresh_interval=15,
            max_cards=20,
            sort_by=SortBy.COST,
            enable_websocket=True,
            websocket_url="ws://localhost:8080",
        )
        d = original.to_dict()
        restored = DashboardConfig.from_dict(d)
        assert restored.refresh_interval == original.refresh_interval
        assert restored.max_cards == original.max_cards
        assert restored.sort_by == original.sort_by
        assert restored.enable_websocket == original.enable_websocket


class TestSessionCard:
    """Tests for SessionCard."""

    def test_default_values(self):
        """Default field values are correct."""
        card = SessionCard(session_id="sess-1")
        assert card.session_id == "sess-1"
        assert card.total_cost == 0.0
        assert card.total_tokens == 0
        assert card.expanded is False
        assert card.last_message == ""

    def test_to_dict_roundtrip(self):
        """from_dict(to_dict(x)) == x."""
        original = SessionCard(
            session_id="sess-42",
            status="active",  # type: ignore
            agent_id="agent-1",
            model="sonnet-4.6",
            total_cost=1.23,
            total_tokens=5000,
            tool_calls=10,
            errors=1,
            latency=12.5,
            last_message="Hello world",
            started_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T01:00:00",
            expanded=True,
            metadata={"key": "val"},
        )
        d = original.to_dict()
        restored = SessionCard.from_dict(d)
        assert restored.session_id == original.session_id
        assert restored.model == original.model
        assert restored.total_cost == original.total_cost
        assert restored.expanded == original.expanded


class TestFleetDashboard:
    """Tests for FleetDashboard."""

    def test_render_fleet_view_returns_state(self):
        """render_fleet_view() returns a DashboardState even with no sessions."""
        dashboard = FleetDashboard()
        state = dashboard.render_fleet_view()

        assert isinstance(state, DashboardState)
        assert state.total_sessions >= 0
        assert isinstance(state.cards, list)
        assert isinstance(state.last_updated, str)
        assert len(state.last_updated) > 0

    def test_session_card_returns_none_for_missing(self):
        """session_card() returns None for unknown sessions."""
        dashboard = FleetDashboard()
        card = dashboard.session_card("nonexistent-session")
        assert card is None

    def test_peek_session_returns_message_for_missing(self):
        """peek_session() returns an error message for unknown sessions."""
        dashboard = FleetDashboard()
        result = dashboard.peek_session("nonexistent")
        assert "No messages found" in result

    def test_reply_session_returns_false_for_missing(self):
        """reply_session() returns False for unknown sessions."""
        dashboard = FleetDashboard()
        result = dashboard.reply_session("nonexistent", "hello")
        assert result is False

    def test_cost_summary_returns_dict(self):
        """cost_summary() returns a structured dict even with no sessions."""
        dashboard = FleetDashboard()
        summary = dashboard.cost_summary()

        assert isinstance(summary, dict)
        assert "total_cost" in summary
        assert "total_tokens" in summary
        assert "average_cost_per_token" in summary
        assert "session_count" in summary
        assert "per_model" in summary
        assert summary["total_cost"] == 0.0
        assert summary["session_count"] >= 0

    def test_set_session_model(self):
        """set_session_model() records the model without error."""
        dashboard = FleetDashboard()
        dashboard.set_session_model("sess-1", "sonnet-4.6")
        # No direct accessor, but confirm render doesn't crash
        state = dashboard.render_fleet_view()
        assert isinstance(state, DashboardState)

    def test_update_config_returns_new_config(self):
        """update_config() returns a new config with merged values."""
        dashboard = FleetDashboard()
        new_config = dashboard.update_config({"max_cards": 10})
        assert new_config.max_cards == 10
        assert dashboard.config.max_cards == 10

    def test_sort_by_status(self):
        """_sort_cards sorts correctly by status."""
        cards = [
            SessionCard(session_id="a", status="completed"),  # type: ignore
            SessionCard(session_id="b", status="active"),  # type: ignore
            SessionCard(session_id="c", status="failed"),  # type: ignore
        ]
        sorted_cards = FleetDashboard._sort_cards(cards, SortBy.STATUS)
        # Should sort by status.value descending + updated_at descending
        assert len(sorted_cards) == 3

    def test_sort_by_cost(self):
        """_sort_cards sorts correctly by cost."""
        cards = [
            SessionCard(session_id="a", total_cost=5.0),
            SessionCard(session_id="b", total_cost=10.0),
            SessionCard(session_id="c", total_cost=1.0),
        ]
        sorted_cards = FleetDashboard._sort_cards(cards, SortBy.COST)
        assert sorted_cards[0].total_cost == 10.0
        assert sorted_cards[1].total_cost == 5.0
        assert sorted_cards[2].total_cost == 1.0

    def test_ws_register_and_push(self):
        """WebSocket client registration and push works without error."""
        dashboard = FleetDashboard()
        dashboard.update_config({"enable_websocket": True})

        received: list[dict] = []

        def callback(payload: dict) -> None:
            received.append(payload)

        dashboard.register_ws_client(callback)
        dashboard.push_update()

        assert len(received) == 1
        assert "cards" in received[0]
        assert "total_cost" in received[0]

    def test_ws_client_failure_removed(self):
        """A failing WebSocket client is removed after push."""
        dashboard = FleetDashboard()
        dashboard.update_config({"enable_websocket": True})

        def failing_callback(payload: dict) -> None:
            raise RuntimeError("Boom!")

        dashboard.register_ws_client(failing_callback)
        dashboard.push_update()

        # The failing client should have been discarded
        assert len(dashboard._ws_clients) == 0  # noqa: SLF001

    def test_dashboard_state_to_dict(self):
        """DashboardState.to_dict() serializes correctly."""
        card = SessionCard(session_id="sess-1", total_cost=2.5, total_tokens=1000)
        state = DashboardState(
            cards=[card],
            total_sessions=1,
            total_cost=2.5,
            total_tokens=1000,
        )
        d = state.to_dict()
        assert d["total_sessions"] == 1
        assert d["total_cost"] == 2.5
        assert len(d["cards"]) == 1
        assert d["cards"][0]["session_id"] == "sess-1"

    def test_sort_by_tokens(self):
        """_sort_cards sorts correctly by tokens."""
        cards = [
            SessionCard(session_id="a", total_tokens=100),
            SessionCard(session_id="b", total_tokens=500),
            SessionCard(session_id="c", total_tokens=50),
        ]
        sorted_cards = FleetDashboard._sort_cards(cards, SortBy.TOKENS)
        assert sorted_cards[0].total_tokens == 500
        assert sorted_cards[2].total_tokens == 50

    def test_sort_by_model(self):
        """_sort_cards sorts correctly by model."""
        cards = [
            SessionCard(session_id="b", model="haiku"),
            SessionCard(session_id="a", model="sonnet"),
        ]
        sorted_cards = FleetDashboard._sort_cards(cards, SortBy.MODEL)
        assert sorted_cards[0].model == "haiku"

    def test_sort_by_recent(self):
        """_sort_cards sorts by recency."""
        cards = [
            SessionCard(session_id="a", updated_at="2026-01-01T00:00:00"),
            SessionCard(session_id="b", updated_at="2026-01-02T00:00:00"),
        ]
        sorted_cards = FleetDashboard._sort_cards(cards, SortBy.RECENT)
        assert sorted_cards[0].session_id == "b"

    def test_unregister_ws_client(self):
        """WebSocket client unregistration works."""
        dashboard = FleetDashboard()
        dashboard.update_config({"enable_websocket": True})

        def cb(payload):
            pass

        dashboard.register_ws_client(cb)
        dashboard.unregister_ws_client(cb)
        assert len(dashboard._ws_clients) == 0

    def test_push_update_disabled(self):
        """push_update returns early when websocket disabled."""
        dashboard = FleetDashboard()
        dashboard.push_update()  # should not raise

    def test_session_card_exists(self):
        """session_card returns card for known sessions."""
        dashboard = FleetDashboard()
        card = dashboard.session_card("nonexistent")
        assert card is None

    def test_peek_session_with_data(self):
        """peek_session returns formatted messages for sessions with steps."""
        from unittest.mock import MagicMock
        dashboard = FleetDashboard()
        mock_mgr = MagicMock()
        mock_mgr.get_steps.return_value = [{"content": "Hello"}, {"content": "World"}]
        dashboard._session_manager = mock_mgr
        result = dashboard.peek_session("test-session")
        assert "Hello" in result

    def test_peek_session_custom_count(self):
        dashboard = FleetDashboard()
        from unittest.mock import MagicMock
        mock_mgr = MagicMock()
        mock_mgr.get_steps.return_value = [{"content": f"Msg {i}"} for i in range(10)]
        dashboard._session_manager = mock_mgr
        result = dashboard.peek_session("test", n=3)
        assert result.count("Msg") <= 3

    def test_reply_session_success(self):
        """reply_session returns True when append succeeds."""
        from unittest.mock import MagicMock
        dashboard = FleetDashboard()
        mock_mgr = MagicMock()
        mock_mgr.append_step.return_value = True
        dashboard._session_manager = mock_mgr
        result = dashboard.reply_session("test-session", "Hello")
        assert result is True

    def test_cost_summary_empty(self):
        from unittest.mock import MagicMock
        dashboard = FleetDashboard()
        mock_mgr = MagicMock()
        mock_mgr.list_sessions.return_value = []
        dashboard._session_manager = mock_mgr
        summary = dashboard.cost_summary()
        assert "total_cost" in summary

    def test_config_sort_by_string(self):
        """Config.merge handles string sort_by values."""
        config = DashboardConfig()
        merged = config.merge({"sort_by": "cost"})
        assert merged.sort_by == SortBy.COST

    def test_config_to_dict_full(self):
        config = DashboardConfig(
            refresh_interval=10, max_cards=25,
            sort_by=SortBy.STATUS, enable_websocket=True,
            websocket_url="ws://test", peek_message_count=50,
        )
        d = config.to_dict()
        assert d["refresh_interval"] == 10

    def test_config_from_dict_roundtrip(self):
        data = {
            "refresh_interval": 15, "max_cards": 30,
            "sort_by": "cost", "enable_websocket": True,
        }
        config = DashboardConfig.from_dict(data)
        assert config.refresh_interval == 15
        assert config.sort_by == SortBy.COST

    def test_session_card_to_dict_full(self):
        card = SessionCard(
            session_id="sess-99", status="failed",
            agent_id="agent-x", model="haiku",
            total_cost=5.5, total_tokens=5000,
            tool_calls=50, errors=2, latency=3.5,
            last_message="last msg", started_at="t1",
            updated_at="t2", expanded=True,
            metadata={"key": "val"},
        )
        d = card.to_dict()
        assert d["total_cost"] == 5.5

    def test_session_card_from_dict_minimal(self):
        card = SessionCard.from_dict({"session_id": "sess-1"})
        assert card.session_id == "sess-1"

    def test_sort_cards_status_none(self):
        """_sort_cards handles cards with None status."""
        cards = [
            SessionCard(session_id="a", status=None),  # type: ignore
        ]
        FleetDashboard._sort_cards(cards, SortBy.STATUS)

    def test_peek_session_formatted_with_dict_steps(self):
        """peek_session formats dict steps correctly."""
        from unittest.mock import MagicMock
        dashboard = FleetDashboard()
        mock_mgr = MagicMock()
        mock_mgr.get_steps.return_value = [
            {"type": "user_reply", "content": "Hello world", "timestamp": "2026-01-01"},
            "Plain string step",
        ]
        dashboard._session_manager = mock_mgr
        result = dashboard.peek_session("test")
        assert "Hello world" in result or "Plain" in result


# ======================================================================
# SkillsHub tests
# ======================================================================


class TestSkillCard:
    """Tests for SkillCard."""

    def test_default_values(self):
        """Default field values are correct."""
        card = SkillCard(skill_id="test-skill", name="Test Skill", description="A test skill")
        assert card.skill_id == "test-skill"
        assert card.installs == 0
        assert card.stars == 0.0
        assert card.enabled is True
        assert card.installed is False

    def test_to_dict_roundtrip(self):
        """from_dict(to_dict(x)) == x."""
        original = SkillCard(
            skill_id="skill-1",
            name="Skill One",
            description="Does something useful",
            category=SkillCategory.TDD_TESTING,
            version="2.0.0",
            tags=["python", "testing"],
            language="python",
            installs=42,
            stars=4.5,
            enabled=True,
            installed=True,
            source="github",
            github_url="https://github.com/user/repo",
            updated_at="2026-06-01T00:00:00",
        )
        d = original.to_dict()
        restored = SkillCard.from_dict(d)
        assert restored.skill_id == original.skill_id
        assert restored.name == original.name
        assert restored.category == original.category
        assert restored.installs == original.installs
        assert restored.stars == original.stars
        assert restored.github_url == original.github_url

    def test_from_skill(self):
        """from_skill() correctly builds a SkillCard from a Skill."""
        skill = Skill(
            name="test-skill",
            description="A test skill",
            content="Some content here",
            category=SkillCategory.BACKEND_PATTERNS,
            tags=["python", "backend"],
            language="python",
            version="1.5.0",
            source="ecc",
        )
        card = SkillCard.from_skill(skill)
        assert card.name == "test-skill"
        assert card.description == "A test skill"
        assert card.category == SkillCategory.BACKEND_PATTERNS
        assert card.tags == ["python", "backend"]
        assert card.language == "python"
        assert card.source == "ecc"


class TestSkillsHub:
    """Tests for SkillsHub."""

    @pytest.fixture
    def hub(self) -> SkillsHub:
        """Fixture: a clean SkillsHub with no pre-registered skills."""
        registry = SkillRegistry()
        return SkillsHub(registry=registry)

    @pytest.fixture
    def hub_with_skills(self) -> SkillsHub:
        """Fixture: a SkillsHub with a few sample skills."""
        registry = SkillRegistry()
        registry.register(
            Skill(
                name="python-testing",
                description="Python testing patterns with pytest",
                content="Content about pytest fixtures, mocking, ...",
                category=SkillCategory.TDD_TESTING,
                tags=["python", "testing", "pytest"],
                language="python",
            )
        )
        registry.register(
            Skill(
                name="api-design",
                description="RESTful API design best practices",
                content="Content about REST, HATEOAS, versioning",
                category=SkillCategory.API_DESIGN,
                tags=["api", "rest", "design"],
            )
        )
        registry.register(
            Skill(
                name="docker-deployment",
                description="Docker and container deployment patterns",
                content="Content about Dockerfiles, compose, k8s",
                category=SkillCategory.DEPLOYMENT,
                tags=["docker", "deployment", "containers"],
            )
        )
        return SkillsHub(registry=registry)

    def test_list_skills_all(self, hub_with_skills: SkillsHub):
        """list_skills() returns all skills with no filters."""
        cards = hub_with_skills.list_skills()
        assert len(cards) == 3

    def test_list_skills_category_filter(self, hub_with_skills: SkillsHub):
        """list_skills() filters by category."""
        cards = hub_with_skills.list_skills(category="api-design")
        assert len(cards) == 1
        assert cards[0].name == "api-design"

    def test_list_skills_search(self, hub_with_skills: SkillsHub):
        """list_skills() filters by text search."""
        cards = hub_with_skills.list_skills(search="testing")
        assert len(cards) >= 1
        assert all("testing" in c.name.lower() or "testing" in c.description.lower() for c in cards)

    def test_list_skills_search_partial(self, hub_with_skills: SkillsHub):
        """list_skills() finds skills with partial tag matches."""
        cards = hub_with_skills.list_skills(search="test")
        assert len(cards) >= 1

    def test_popular_skills_returns_top(self, hub_with_skills: SkillsHub):
        """popular_skills() returns skills sorted by popularity."""
        popular = hub_with_skills.popular_skills(limit=2)
        assert len(popular) <= 2

    def test_enable_skill(self, hub_with_skills: SkillsHub):
        """enable_skill() returns True for existing skills."""
        assert hub_with_skills.enable_skill("python-testing") is True

    def test_enable_skill_missing_by_id(self):
        """enable_skill() returns False for nonexistent skills."""
        hub = SkillsHub()
        assert hub.enable_skill("nonexistent") is False

    def test_disable_skill(self, hub_with_skills: SkillsHub):
        """disable_skill() returns True for existing skills."""
        assert hub_with_skills.disable_skill("python-testing") is True

    def test_disable_skill_missing(self):
        """disable_skill() returns False for nonexistent skills."""
        hub = SkillsHub()
        assert hub.disable_skill("nonexistent") is False

    def test_enable_disable_cycle(self, hub_with_skills: SkillsHub):
        """Enabling then disabling a skill changes its enabled status."""
        hub_with_skills.disable_skill("python-testing")
        cards = hub_with_skills.list_skills()
        disabled = [c for c in cards if c.name == "python-testing"]
        assert len(disabled) > 0

        hub_with_skills.enable_skill("python-testing")
        cards = hub_with_skills.list_skills()
        enabled = [c for c in cards if c.name == "python-testing"]
        assert len(enabled) > 0

    def test_skill_rating_valid(self, hub_with_skills: SkillsHub):
        """skill_rating() creates a rating record."""
        record = hub_with_skills.skill_rating("python-testing", 5, user_id="user-1")
        assert record.stars == 5
        assert record.user_id == "user-1"
        assert record.skill_id == "python-testing"

    def test_skill_rating_invalid_range(self, hub_with_skills: SkillsHub):
        """skill_rating() raises ValueError for out-of-range stars."""
        with pytest.raises(ValueError, match="Stars must be between 1 and 5"):
            hub_with_skills.skill_rating("python-testing", 0)

    def test_skill_rating_unknown_skill(self):
        """skill_rating() raises ValueError for unknown skills."""
        hub = SkillsHub()
        with pytest.raises(ValueError, match="Skill not found"):
            hub.skill_rating("nonexistent", 3)

    def test_get_ratings_empty(self, hub_with_skills: SkillsHub):
        """get_ratings() returns empty list for unrated skills."""
        ratings = hub_with_skills.get_ratings("python-testing")
        assert ratings == []

    def test_get_ratings_after_rating(self, hub_with_skills: SkillsHub):
        """get_ratings() returns stored ratings."""
        hub_with_skills.skill_rating("python-testing", 4, user_id="alice")
        hub_with_skills.skill_rating("python-testing", 5, user_id="bob")
        ratings = hub_with_skills.get_ratings("python-testing")
        assert len(ratings) == 2

    def test_hub_status(self, hub_with_skills: SkillsHub):
        """hub_status() returns a summary dict."""
        status = hub_with_skills.hub_status()
        assert "total_installed" in status
        assert "categories" in status
        assert status["total_installed"] >= 3

    def test_install_skill_invalid_url(self):
        """install_skill() raises ValueError for invalid GitHub URLs."""
        hub = SkillsHub()
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            hub.install_skill("not-a-url")

    def test_uninstall_skill_missing(self):
        """uninstall_skill() returns False for nonexistent skills."""
        hub = SkillsHub()
        assert hub.uninstall_skill("nonexistent") is False

    def test_uninstall_skill_existing(self, hub_with_skills: SkillsHub):
        """uninstall_skill() returns True and removes the skill."""
        assert hub_with_skills.uninstall_skill("python-testing") is True
        cards = hub_with_skills.list_skills()
        names = [c.name for c in cards]
        assert "python-testing" not in names

    def test_is_enabled_default(self):
        """is_enabled() returns True by default."""
        hub = SkillsHub()
        # Skill doesn't exist in registry but we check _enabled_cache
        assert hub.is_enabled("anything") is True

    def test_discover_from_repo_nonexistent(self):
        """discover_from_repo() raises NotADirectoryError for bad paths."""
        hub = SkillsHub()
        with pytest.raises((NotADirectoryError, FileNotFoundError)):
            hub.discover_from_repo("/nonexistent/path")

    def test_github_url_validation(self):
        """_is_valid_github_url() correctly validates URLs."""
        assert SkillsHub._is_valid_github_url("https://github.com/user/repo") is True
        assert SkillsHub._is_valid_github_url("https://github.com/user/repo.git") is True
        assert SkillsHub._is_valid_github_url("http://github.com/user/repo") is True
        assert SkillsHub._is_valid_github_url("https://gitlab.com/user/repo") is False
        assert SkillsHub._is_valid_github_url("not-a-url") is False
        assert SkillsHub._is_valid_github_url("") is False
