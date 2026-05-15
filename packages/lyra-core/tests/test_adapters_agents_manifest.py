"""Tests for cross-harness AGENTS.md exporter (Phase CE.3, P2-3)."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.adapters.agents_manifest import (
    AgentsManifest,
    CatalogEntry,
    manifest_from_lyra_registries,
    render_manifest,
    write_manifest,
)


# ────────────────────────────────────────────────────────────────
# CatalogEntry validation
# ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_kind", ["", "tool", "service", "Skill"])
def test_entry_rejects_invalid_kind(bad_kind: str):
    with pytest.raises(ValueError):
        CatalogEntry(name="x", kind=bad_kind, summary="y")


def test_entry_rejects_empty_name():
    with pytest.raises(ValueError):
        CatalogEntry(name="", kind="skill", summary="y")


def test_entry_rejects_empty_summary():
    with pytest.raises(ValueError):
        CatalogEntry(name="x", kind="skill", summary="")


# ────────────────────────────────────────────────────────────────
# AgentsManifest
# ────────────────────────────────────────────────────────────────


def test_by_kind_filters_correctly():
    m = AgentsManifest(project_name="lyra")
    m.add(CatalogEntry(name="a", kind="skill", summary="s1"))
    m.add(CatalogEntry(name="b", kind="agent", summary="s2"))
    m.add(CatalogEntry(name="c", kind="skill", summary="s3"))
    assert [e.name for e in m.by_kind("skill")] == ["a", "c"]
    assert [e.name for e in m.by_kind("agent")] == ["b"]


# ────────────────────────────────────────────────────────────────
# render_manifest
# ────────────────────────────────────────────────────────────────


def test_render_header_uses_project_name_uppercase():
    m = AgentsManifest(project_name="lyra")
    body = render_manifest(m)
    assert body.startswith("# LYRA — agents catalog")


def test_render_description_included_when_present():
    m = AgentsManifest(project_name="lyra", description="local-first agent kernel")
    body = render_manifest(m)
    assert "local-first agent kernel" in body


def test_render_universal_marker_present():
    m = AgentsManifest()
    body = render_manifest(m)
    assert "Claude Code, Codex, Cursor, OpenCode" in body


def test_render_sections_ordered_skills_agents_commands_rules():
    m = AgentsManifest()
    m.add(CatalogEntry(name="rule-x", kind="rule", summary="a"))
    m.add(CatalogEntry(name="cmd-y", kind="command", summary="b"))
    m.add(CatalogEntry(name="agent-z", kind="agent", summary="c"))
    m.add(CatalogEntry(name="skill-q", kind="skill", summary="d"))
    body = render_manifest(m)
    pos_skill = body.index("## Skills")
    pos_agent = body.index("## Agents")
    pos_cmd = body.index("## Commands")
    pos_rule = body.index("## Rules")
    assert pos_skill < pos_agent < pos_cmd < pos_rule


def test_render_within_section_sorts_by_name():
    m = AgentsManifest()
    m.add(CatalogEntry(name="zeta", kind="skill", summary="z"))
    m.add(CatalogEntry(name="alpha", kind="skill", summary="a"))
    body = render_manifest(m)
    assert body.index("alpha") < body.index("zeta")


def test_render_omits_empty_sections():
    m = AgentsManifest()
    m.add(CatalogEntry(name="only-skill", kind="skill", summary="x"))
    body = render_manifest(m)
    assert "## Skills" in body
    assert "## Agents" not in body
    assert "## Commands" not in body
    assert "## Rules" not in body


def test_render_includes_source_path_when_present():
    m = AgentsManifest()
    m.add(
        CatalogEntry(
            name="x",
            kind="skill",
            summary="does the thing",
            path="packages/lyra-skills/skills/x/SKILL.md",
        )
    )
    body = render_manifest(m)
    assert "[source](packages/lyra-skills/skills/x/SKILL.md)" in body


def test_render_includes_tags_when_present():
    m = AgentsManifest()
    m.add(
        CatalogEntry(
            name="x",
            kind="skill",
            summary="does the thing",
            tags=("tdd", "python"),
        )
    )
    body = render_manifest(m)
    assert "tags: tdd, python" in body


def test_render_ends_with_single_newline():
    m = AgentsManifest()
    body = render_manifest(m)
    assert body.endswith("\n")
    assert not body.endswith("\n\n")


# ────────────────────────────────────────────────────────────────
# manifest_from_lyra_registries
# ────────────────────────────────────────────────────────────────


def test_factory_builds_manifest_from_tuples():
    m = manifest_from_lyra_registries(
        skills=[("tdd-discipline", "test-first workflow", "skills/tdd/SKILL.md")],
        agents=[("explore", "codebase search", "agents/explore.md")],
        commands=[("compact", "manual compaction")],
        rules=[("style", "PEP 8", "rules/python/coding-style.md")],
        project_name="lyra",
        description="kernel",
    )
    assert m.project_name == "lyra"
    assert len(m.entries) == 4
    assert {e.kind for e in m.entries} == {"skill", "agent", "command", "rule"}


def test_factory_empty_inputs_yields_empty_manifest():
    m = manifest_from_lyra_registries()
    body = render_manifest(m)
    # No sections, just header + universal marker.
    assert "## Skills" not in body
    assert "## Agents" not in body


# ────────────────────────────────────────────────────────────────
# write_manifest
# ────────────────────────────────────────────────────────────────


def test_write_manifest_persists_to_disk(tmp_path: Path):
    m = AgentsManifest(project_name="lyra")
    m.add(CatalogEntry(name="x", kind="skill", summary="y"))
    target = tmp_path / "subdir" / "AGENTS.md"
    body = write_manifest(m, target_path=str(target))
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == body


def test_write_manifest_creates_parent_directories(tmp_path: Path):
    m = AgentsManifest()
    target = tmp_path / "nested" / "deep" / "AGENTS.md"
    write_manifest(m, target_path=str(target))
    assert target.is_file()
