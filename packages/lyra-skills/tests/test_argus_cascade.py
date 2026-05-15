"""Tests for the V3.8 Theme A Argus integration.

Exercises every Lyra-shaped surface that the Argus library is wired
into: the bridge, the cascade orchestrator, the SkillRouter opt-in
seam, the telemetry mirror, and the governance ledgers.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_skill_router import SkillSource, TrustTier

from lyra_skills.argus_bridge import (
    argus_skill_to_manifest,
    manifest_to_argus_skill,
)
from lyra_skills.argus_cascade import LyraArgusCascade
from lyra_skills.argus_telemetry_bridge import mirror_registry_into_cascade
from lyra_skills.loader import SkillManifest
from lyra_skills.router import SkillRouter


def _manifest(
    id_: str,
    description: str,
    *,
    keywords: list[str] | None = None,
    body: str = "",
    progressive: bool = False,
) -> SkillManifest:
    return SkillManifest(
        id=id_,
        name=id_.replace("-", " ").title(),
        description=description,
        body=body,
        path=f"/skills/{id_}/SKILL.md",
        version="1.0.0",
        keywords=keywords or [],
        applies_to=[],
        requires=[],
        progressive=progressive,
        extras={},
    )


# ---------------------------------------------------------------------------
# bridge round-trip
# ---------------------------------------------------------------------------


class TestBridge:
    def test_manifest_to_argus_preserves_core_fields(self) -> None:
        m = _manifest("edit", "make code edits", keywords=["edit", "change"])
        s = manifest_to_argus_skill(m)
        assert s.name == "edit"
        assert s.description == "make code edits"
        assert "edit" in s.when_to_use and "change" in s.when_to_use
        assert s.source is SkillSource.LOCAL_AUTHORED
        assert s.trust_tier is TrustTier.T_REVIEWED
        assert s.extra["display_name"] == "Edit"
        assert s.extra["progressive"] is False

    def test_round_trip_preserves_all_fields(self) -> None:
        m = SkillManifest(
            id="demo",
            name="Display Name",
            description="one-liner",
            body="full body",
            path="/x/SKILL.md",
            version="2.3.4",
            keywords=["foo", "bar"],
            applies_to=["**/*.py"],
            requires=["rich", "pydantic"],
            progressive=True,
            extras={"author": "alice", "tags": ["t1"]},
        )
        s = manifest_to_argus_skill(m)
        m2 = argus_skill_to_manifest(s)
        assert m == m2

    def test_explicit_source_drives_trust_tier(self) -> None:
        m = _manifest("noisy", "from a marketplace")
        s = manifest_to_argus_skill(
            m, source=SkillSource.MARKETPLACE_GLAMA,
        )
        assert s.source is SkillSource.MARKETPLACE_GLAMA
        assert s.trust_tier is TrustTier.T_UNTRUSTED


# ---------------------------------------------------------------------------
# cascade orchestrator
# ---------------------------------------------------------------------------


class TestCascade:
    def test_index_manifests_populates_catalog(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        added = cascade.index_manifests([
            _manifest("a", "alpha"),
            _manifest("b", "beta"),
        ])
        assert added == 2
        assert len(cascade) == 2
        assert cascade.loadable_count() == 2

    def test_route_keyword_mode_uses_bm25(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        cascade.index_manifests([
            _manifest("edit", "edit source files", keywords=["edit", "change"]),
            _manifest("test-gen", "generate tests", keywords=["tests", "tdd"]),
            _manifest("localize", "find code", keywords=["find", "locate"]),
        ])
        result = cascade.route("write tests for the parser", mode="keyword", top_k=2)
        assert not result.is_empty
        assert result.top is not None
        assert result.top.manifest.id == "test-gen"
        assert "tier_1_keyword" in result.tier_names

    def test_route_returns_lyra_manifests(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        manifests = [_manifest("edit", "edits", keywords=["edit"])]
        cascade.index_manifests(manifests)
        result = cascade.route("edit", mode="keyword")
        assert isinstance(result.top.manifest, SkillManifest)
        assert result.top.manifest is manifests[0]

    def test_route_emits_telemetry_to_disk(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        cascade.index_manifests([_manifest("edit", "edit", keywords=["edit"])])
        cascade.route("edit something", mode="keyword")
        rows = list(cascade.telemetry_path.read_text().splitlines())
        events = [json.loads(r) for r in rows if r.strip()]
        kinds = [e["kind"] for e in events]
        assert "router.decision" in kinds

    def test_record_outcome_emits_skill_executed(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        cascade.index_manifests([_manifest("edit", "edit", keywords=["edit"])])
        cascade.record_outcome("edit", success=True, query="edit something")
        cascade.record_outcome("edit", success=False, query="edit broken")
        events = [
            json.loads(line)
            for line in cascade.telemetry_path.read_text().splitlines()
            if line.strip()
        ]
        assert any(e["kind"] == "skill.executed" for e in events)
        assert any(e["kind"] == "skill.rejected" for e in events)

    def test_retract_tombstones_skill(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        cascade.index_manifests([_manifest("edit", "edit")])
        cascade.retract("edit", reason="superseded")
        assert cascade.host.catalog.get("edit") is None
        tombstone_lines = (tmp_path / "tombstones.jsonl").read_text().splitlines()
        assert tombstone_lines  # at least one line written

    def test_quality_score_reports_per_skill(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        cascade.index_manifests([
            _manifest("edit", "make code edits", keywords=["edit"]),
            _manifest("test-gen", "generate tests", keywords=["tests"]),
        ])
        report = cascade.quality_score()
        assert report  # tuple of per-skill DescriptionQualityReport rows
        names = {r.skill_name for r in report}
        assert names == {"edit", "test-gen"}

    def test_heartbeat_runs_without_telemetry(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        cascade.index_manifests([_manifest("edit", "edit")])
        result = cascade.heartbeat()
        assert result is not None  # RefinementResult


# ---------------------------------------------------------------------------
# SkillRouter opt-in seam
# ---------------------------------------------------------------------------


class TestRouterOptIn:
    def test_default_router_uses_overlap_path(self) -> None:
        r = SkillRouter([_manifest("edit", "edit source files")])
        hits = r.route("edit a file")
        assert hits and hits[0].id == "edit"
        assert r.argus_cascade is None

    def test_with_argus_delegates_to_cascade(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        manifests = [
            _manifest("edit", "make code edits", keywords=["edit"]),
            _manifest("test-gen", "generate tests", keywords=["tests"]),
        ]
        r = SkillRouter.with_argus(manifests, cascade=cascade)
        # `route()` routes via the cascade in default (auto) mode; the
        # results are SkillManifest instances projected back from
        # Argus's RankedSkill rows.
        hits = r.route("write tests")
        assert hits, "cascade should return at least one pick"
        assert all(isinstance(m, SkillManifest) for m in hits)
        assert {m.id for m in hits} <= {"edit", "test-gen"}
        assert r.argus_cascade is cascade

    def test_with_argus_keyword_mode_disambiguates(self, tmp_path: Path) -> None:
        cascade = LyraArgusCascade(state_dir=tmp_path)
        manifests = [
            _manifest("edit", "make code edits", keywords=["edit"]),
            _manifest("test-gen", "generate tests", keywords=["tests", "tdd"]),
        ]
        r = SkillRouter.with_argus(manifests, cascade=cascade)
        result = r.route_with_trace(
            "write tests for the parser", top_k=1, mode="keyword",
        )
        # Keyword mode forces Tier 1 BM25 even on small catalogs, so
        # discriminating tokens like "tests" pick the test-gen skill.
        assert result.top is not None
        assert result.top.manifest.id == "test-gen"
        assert "tier_1_keyword" in result.tier_names

    def test_route_with_trace_requires_cascade(self) -> None:
        r = SkillRouter([_manifest("edit", "edit")])
        with pytest.raises(RuntimeError):
            r.route_with_trace("anything")

    def test_route_with_trace_returns_full_decision(self, tmp_path: Path) -> None:
        r = SkillRouter.with_argus(
            [_manifest("edit", "edit", keywords=["edit"])],
            cascade=LyraArgusCascade(state_dir=tmp_path),
        )
        result = r.route_with_trace("edit", top_k=1)
        assert result.top is not None
        assert result.tier_names  # at least one tier ran


# ---------------------------------------------------------------------------
# registry telemetry bridge
# ---------------------------------------------------------------------------


class TestTelemetryBridge:
    def test_mirror_registry_writes_to_argus(self, tmp_path: Path) -> None:
        from lyra_core.skills.registry import (
            Skill as LyraSkill,
            SkillRegistry,
        )

        cascade = LyraArgusCascade(state_dir=tmp_path)
        registry = SkillRegistry()
        registry.register(LyraSkill(id="edit", description="d", triggers=("edit",)))

        restore = mirror_registry_into_cascade(registry, cascade)
        try:
            registry.record_success("edit")
            registry.record_miss("edit")
        finally:
            restore()

        assert registry.get("edit").success_count == 1
        assert registry.get("edit").miss_count == 1
        events = [
            json.loads(line)
            for line in cascade.telemetry_path.read_text().splitlines()
            if line.strip()
        ]
        kinds = [e["kind"] for e in events if e["skill_name"] == "edit"]
        assert "skill.executed" in kinds
        assert "skill.rejected" in kinds

    def test_restore_detaches_bridge(self, tmp_path: Path) -> None:
        from lyra_core.skills.registry import (
            Skill as LyraSkill,
            SkillRegistry,
        )

        cascade = LyraArgusCascade(state_dir=tmp_path)
        registry = SkillRegistry()
        registry.register(LyraSkill(id="edit", description="d", triggers=("edit",)))

        restore = mirror_registry_into_cascade(registry, cascade)
        registry.record_success("edit")
        restore()

        # After restore, registry counts still increment, but Argus
        # ledger does not receive new events.
        before = (
            cascade.telemetry_path.read_text() if cascade.telemetry_path.exists() else ""
        )
        registry.record_success("edit")
        after = (
            cascade.telemetry_path.read_text() if cascade.telemetry_path.exists() else ""
        )
        assert after == before
        assert registry.get("edit").success_count == 2
