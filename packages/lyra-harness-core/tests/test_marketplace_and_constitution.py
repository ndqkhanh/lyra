"""Tests for marketplace adapter + per-user constitution."""
from __future__ import annotations

import time

import pytest

from harness_core.constitution import (
    Constitution,
    ConstitutionRegistry,
    Principle,
    suggest_principle_from_edit,
)
from harness_core.marketplace import (
    InMemoryCuratorHost,
    InMemoryMarketplaceHost,
    InstallResult,
    MCPServer,
    PromotedSkill,
    TrajectoryRecord,
    TrustTier,
    TrustVerdict,
)


# --- Marketplace types --------------------------------------------------


class TestTrustVerdict:
    def test_invalid_score(self):
        with pytest.raises(ValueError):
            TrustVerdict(server_name="x", tier=TrustTier.TRUSTED, score=1.5)

    def test_installable(self):
        v = TrustVerdict(server_name="x", tier=TrustTier.TRUSTED, score=0.9)
        assert v.installable is True
        v2 = TrustVerdict(server_name="x", tier=TrustTier.SUSPICIOUS, score=0.5)
        assert v2.installable is False

    def test_expiry(self):
        past = time.time() - 100
        v = TrustVerdict(server_name="x", tier=TrustTier.TRUSTED, score=0.9, expires_at=past)
        assert v.is_expired is True
        assert v.installable is False


class TestInMemoryMarketplaceHost:
    def _host_with_servers(self):
        host = InMemoryMarketplaceHost()
        host.add_server(MCPServer(
            name="github", description="GitHub MCP server",
            upstream_marketplace="lobehub", download_count=1000,
        ))
        host.add_server(MCPServer(
            name="filesystem", description="Local filesystem MCP",
            upstream_marketplace="modelcontextprotocol", download_count=500,
        ))
        host.add_server(MCPServer(
            name="postgres", description="Postgres MCP",
            upstream_marketplace="lobehub", download_count=2000,
        ))
        return host

    def test_list_marketplace_basic(self):
        host = self._host_with_servers()
        results = host.list_marketplace()
        # Sorted by download_count desc.
        assert [r.name for r in results] == ["postgres", "github", "filesystem"]

    def test_list_with_filter(self):
        host = self._host_with_servers()
        results = host.list_marketplace(filter="github")
        assert [r.name for r in results] == ["github"]

    def test_list_with_upstream(self):
        host = self._host_with_servers()
        results = host.list_marketplace(upstream="lobehub")
        assert {r.name for r in results} == {"github", "postgres"}

    def test_list_top_k(self):
        host = self._host_with_servers()
        assert len(host.list_marketplace(top_k=2)) == 2

    def test_install_trusted(self):
        host = self._host_with_servers()
        host.set_verdict(TrustVerdict(server_name="github", tier=TrustTier.TRUSTED, score=0.9))
        result = host.install_mcp(server_name="github", user_context={"user_id": "u1"})
        assert result.installed is True
        assert result.verdict.tier == TrustTier.TRUSTED
        assert result.config["server_name"] == "github"

    def test_install_suspicious_without_force_blocked(self):
        host = self._host_with_servers()
        host.set_verdict(TrustVerdict(
            server_name="github", tier=TrustTier.SUSPICIOUS, score=0.4,
            reasons=("low download count",),
        ))
        result = host.install_mcp(server_name="github", user_context={})
        assert result.installed is False
        assert "force=True" in result.note

    def test_install_suspicious_with_force(self):
        host = self._host_with_servers()
        host.set_verdict(TrustVerdict(
            server_name="github", tier=TrustTier.SUSPICIOUS, score=0.4,
        ))
        result = host.install_mcp(server_name="github", user_context={}, force=True)
        assert result.installed is True
        assert "force" in result.note.lower()

    def test_install_rejected_blocked_even_with_force(self):
        host = self._host_with_servers()
        host.set_verdict(TrustVerdict(
            server_name="github", tier=TrustTier.REJECTED, score=0.0,
            reasons=("CVE-2025-9999",),
        ))
        result = host.install_mcp(server_name="github", user_context={}, force=True)
        assert result.installed is False
        assert "REJECTED" in result.note

    def test_install_unknown_server(self):
        host = self._host_with_servers()
        result = host.install_mcp(server_name="nonexistent", user_context={})
        assert result.installed is False
        assert result.verdict.tier == TrustTier.REJECTED

    def test_install_default_tier_is_suspicious(self):
        host = InMemoryMarketplaceHost(default_tier=TrustTier.SUSPICIOUS)
        host.add_server(MCPServer(name="unknown", description=""))
        # No verdict set → default_tier = SUSPICIOUS → blocked without force.
        result = host.install_mcp(server_name="unknown", user_context={})
        assert result.installed is False

    def test_install_log(self):
        host = self._host_with_servers()
        host.set_verdict(TrustVerdict(server_name="github", tier=TrustTier.TRUSTED, score=0.9))
        host.install_mcp(server_name="github", user_context={})
        host.install_mcp(server_name="postgres", user_context={})
        assert len(host.install_log) == 2

    def test_get_trust_verdict(self):
        host = self._host_with_servers()
        host.set_verdict(TrustVerdict(server_name="github", tier=TrustTier.TRUSTED, score=0.9))
        v = host.get_trust_verdict("github")
        assert v is not None
        assert v.tier == TrustTier.TRUSTED
        assert host.get_trust_verdict("nonexistent") is None


class TestInMemoryCuratorHost:
    def _traj(self, project="lyra", outcome="success"):
        return TrajectoryRecord(
            project=project,
            trajectory_id="t-1",
            task_signature="refactor-task",
            actions=("read", "edit", "test"),
            outcome=outcome,
        )

    def test_submit_accepted(self):
        host = InMemoryCuratorHost()
        result = host.submit_trajectory(self._traj())
        assert result.accepted is True
        assert result.submission_id

    def test_submit_with_auto_accept_off(self):
        host = InMemoryCuratorHost(auto_accept=False)
        result = host.submit_trajectory(self._traj())
        assert result.accepted is False

    def test_submit_failure_outcome_queued_for_review(self):
        host = InMemoryCuratorHost()
        result = host.submit_trajectory(self._traj(outcome="failure"))
        assert result.queued_for_review is True

    def test_promote_and_list(self):
        host = InMemoryCuratorHost()
        host.promote(PromotedSkill(name="refactor-pytest", source_project="lyra", eval_score=0.8))
        host.promote(PromotedSkill(name="biomed-query", source_project="helix-bio", eval_score=0.9))
        skills = host.list_promoted_skills(user_context={})
        # Sorted by eval_score desc.
        assert skills[0].name == "biomed-query"

    def test_list_filtered_by_source_project(self):
        host = InMemoryCuratorHost()
        host.promote(PromotedSkill(name="A", source_project="lyra", eval_score=0.8))
        host.promote(PromotedSkill(name="B", source_project="helix-bio", eval_score=0.9))
        lyra_skills = host.list_promoted_skills(user_context={}, source_project="lyra")
        assert {s.name for s in lyra_skills} == {"A"}

    def test_submissions_for_project(self):
        host = InMemoryCuratorHost()
        host.submit_trajectory(self._traj(project="lyra"))
        host.submit_trajectory(self._traj(project="mentat"))
        assert len(host.submissions_for_project("lyra")) == 1
        assert len(host.submissions_for_project("mentat")) == 1


# --- Constitution -------------------------------------------------------


class TestPrinciple:
    def test_valid(self):
        p = Principle(text="Be terse.", weight=1.0)
        assert p.text == "Be terse."

    def test_empty_text_rejected(self):
        with pytest.raises(ValueError):
            Principle(text="")
        with pytest.raises(ValueError):
            Principle(text="   ")

    def test_weight_bounds(self):
        with pytest.raises(ValueError):
            Principle(text="x", weight=-1)
        with pytest.raises(ValueError):
            Principle(text="x", weight=10)


class TestConstitution:
    def test_render_empty(self):
        c = Constitution(user_id="u1")
        assert "(none specified)" in c.render()

    def test_render_orders_by_weight_desc(self):
        c = Constitution(user_id="u1", principles=(
            Principle(text="A", weight=0.5),
            Principle(text="B", weight=2.0),
            Principle(text="C", weight=1.0),
        ))
        rendered = c.render()
        # B should come first.
        b_idx = rendered.index("B")
        a_idx = rendered.index("A")
        c_idx = rendered.index("C")
        assert b_idx < c_idx < a_idx

    def test_with_principle_immutable(self):
        c = Constitution(user_id="u1", principles=(Principle(text="A"),))
        c2 = c.with_principle(Principle(text="B"))
        assert c.version == 1
        assert c2.version == 2
        assert len(c.principles) == 1
        assert len(c2.principles) == 2

    def test_with_principle_replace(self):
        c = Constitution(user_id="u1", principles=(Principle(text="A"),))
        c2 = c.with_principle(Principle(text="A2"), replace_text="A")
        assert c2.principles == (Principle(text="A2"),)

    def test_without_principle(self):
        c = Constitution(user_id="u1", principles=(Principle(text="A"), Principle(text="B")))
        c2 = c.without_principle(text="A")
        assert c2.principles == (Principle(text="B"),)

    def test_without_principle_no_match(self):
        c = Constitution(user_id="u1", principles=(Principle(text="A"),))
        c2 = c.without_principle(text="X")
        assert c is c2  # unchanged → same instance

    def test_bumped(self):
        c = Constitution(user_id="u1", principles=(Principle(text="A", weight=1.0),))
        c2 = c.bumped(text="A", delta=0.5)
        assert c2.principles[0].weight == pytest.approx(1.5)

    def test_bumped_clamps(self):
        c = Constitution(user_id="u1", principles=(Principle(text="A", weight=4.9),))
        c2 = c.bumped(text="A", delta=2.0)
        assert c2.principles[0].weight == 5.0  # clamped

    def test_caps_at_5_principles(self):
        with pytest.raises(ValueError):
            Constitution(user_id="u1", principles=tuple(
                Principle(text=f"P{i}") for i in range(6)
            ))

    def test_user_id_required(self):
        with pytest.raises(ValueError):
            Constitution(user_id="")

    def test_to_dict(self):
        c = Constitution(user_id="u1", principles=(Principle(text="A", weight=1.5),))
        d = c.to_dict()
        assert d["user_id"] == "u1"
        assert d["principles"][0]["text"] == "A"


class TestSuggestPrincipleFromEdit:
    def test_small_edit_returns_none(self):
        assert suggest_principle_from_edit(original="hello", edited="hello!") is None

    def test_lengthening_suggests_verbose(self):
        original = "x" * 100
        edited = "x" * 200
        p = suggest_principle_from_edit(original=original, edited=edited)
        assert p is not None
        assert "verbose" in p.text.lower()

    def test_shortening_suggests_terse(self):
        original = "x" * 200
        edited = "x" * 100
        p = suggest_principle_from_edit(original=original, edited=edited)
        assert p is not None
        assert "terse" in p.text.lower()

    def test_empty_inputs_return_none(self):
        assert suggest_principle_from_edit(original="", edited="") is None


class TestConstitutionRegistry:
    def test_get_or_create(self):
        reg = ConstitutionRegistry()
        c = reg.get_or_create("u1", default_principles=[Principle(text="A")])
        assert c.user_id == "u1"
        # Subsequent get returns the same.
        assert reg.get("u1") is c

    def test_put_get(self):
        reg = ConstitutionRegistry()
        c = Constitution(user_id="u1", principles=(Principle(text="A"),))
        reg.put(c)
        assert reg.get("u1") is c

    def test_update_for_edit_no_change_returns_none(self):
        reg = ConstitutionRegistry()
        result = reg.update_for_edit(user_id="u1", original="x", edited="x.")
        assert result is None

    def test_update_for_edit_appends_principle(self):
        reg = ConstitutionRegistry()
        result = reg.update_for_edit(
            user_id="u1",
            original="x" * 100,
            edited="x" * 200,
        )
        assert result is not None
        assert len(result.principles) == 1

    def test_update_for_edit_bumps_existing(self):
        reg = ConstitutionRegistry()
        # First edit: appends.
        first = reg.update_for_edit(user_id="u1", original="x"*100, edited="x"*200)
        # Second identical edit: bumps weight.
        second = reg.update_for_edit(user_id="u1", original="x"*100, edited="x"*200)
        assert first is not None and second is not None
        # Same number of principles (no duplicate).
        assert len(second.principles) == len(first.principles) == 1
        assert second.principles[0].weight > first.principles[0].weight

    def test_update_for_edit_drops_lowest_at_cap(self):
        reg = ConstitutionRegistry()
        # Pre-load 5 principles with a clear lowest.
        c = Constitution(user_id="u1", principles=(
            Principle(text="P1", weight=0.1),  # lowest
            Principle(text="P2", weight=2.0),
            Principle(text="P3", weight=3.0),
            Principle(text="P4", weight=4.0),
            Principle(text="P5", weight=5.0),
        ))
        reg.put(c)
        result = reg.update_for_edit(user_id="u1", original="x"*100, edited="x"*200)
        assert result is not None
        # P1 (lowest weight) should be dropped to make room.
        texts = {p.text for p in result.principles}
        assert "P1" not in texts
        # New principle added.
        assert len(result.principles) == 5

    def test_remove(self):
        reg = ConstitutionRegistry()
        reg.put(Constitution(user_id="u1"))
        assert reg.remove("u1") is True
        assert reg.remove("u1") is False  # already gone

    def test_len(self):
        reg = ConstitutionRegistry()
        reg.put(Constitution(user_id="u1"))
        reg.put(Constitution(user_id="u2"))
        assert len(reg) == 2
