"""Wave-D Task 3: user-defined subagent presets.

Users drop a YAML/JSON file under ``~/.lyra/agents/<name>.yaml`` (or
``.json``). The :func:`load_presets` function returns a dict of
:class:`SubagentPreset` keyed by name; ``"explore"``, ``"general"``,
and ``"plan"`` are always present (built-ins, leaf vs orchestrator
classified by their ``role`` field).

Five RED tests:

1. Built-ins are loaded when the directory is empty.
2. A user file overrides a built-in by name.
3. ``role`` defaults to ``leaf`` and is normalised against the
   accepted set ``{"leaf", "orchestrator"}``.
4. Malformed YAML returns the built-ins + a clearly-named entry in
   ``errors`` (never raises — a bad file should not break boot).
5. ``aliases`` lets a preset be looked up by a short name.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_load_presets_returns_builtins_when_dir_missing(tmp_path: Path) -> None:
    from lyra_core.subagent.presets import load_presets

    bundle = load_presets(user_dir=tmp_path / "does-not-exist")
    assert "explore" in bundle.presets
    assert "general" in bundle.presets
    assert "plan" in bundle.presets


def test_load_presets_user_file_overrides_builtin(tmp_path: Path) -> None:
    from lyra_core.subagent.presets import load_presets

    user_dir = tmp_path / "agents"
    user_dir.mkdir()
    (user_dir / "explore.yaml").write_text(
        "name: explore\n"
        "description: my custom explore\n"
        "model: gpt-mini\n"
        "tools: [Read, Glob, Grep]\n",
        encoding="utf-8",
    )
    bundle = load_presets(user_dir=user_dir)
    assert bundle.presets["explore"].description == "my custom explore"
    assert bundle.presets["explore"].model == "gpt-mini"


def test_load_presets_role_defaults_to_leaf(tmp_path: Path) -> None:
    from lyra_core.subagent.presets import load_presets

    user_dir = tmp_path / "agents"
    user_dir.mkdir()
    (user_dir / "researcher.yaml").write_text(
        "name: researcher\n"
        "description: gathers context for the planner\n",
        encoding="utf-8",
    )
    bundle = load_presets(user_dir=user_dir)
    assert bundle.presets["researcher"].role == "leaf"


def test_load_presets_invalid_role_falls_back_to_leaf(tmp_path: Path) -> None:
    from lyra_core.subagent.presets import load_presets

    user_dir = tmp_path / "agents"
    user_dir.mkdir()
    (user_dir / "weird.yaml").write_text(
        "name: weird\n"
        "description: an agent\n"
        "role: chaos-engineer\n",
        encoding="utf-8",
    )
    bundle = load_presets(user_dir=user_dir)
    assert bundle.presets["weird"].role == "leaf"


def test_load_presets_malformed_yaml_is_recovered(tmp_path: Path) -> None:
    from lyra_core.subagent.presets import load_presets

    user_dir = tmp_path / "agents"
    user_dir.mkdir()
    (user_dir / "bad.yaml").write_text("name: bad\n  : :\n  this is not yaml\n", encoding="utf-8")
    bundle = load_presets(user_dir=user_dir)
    assert "explore" in bundle.presets  # built-ins still made it
    assert any("bad" in e for e in bundle.errors)


def test_load_presets_aliases_resolve_to_preset(tmp_path: Path) -> None:
    from lyra_core.subagent.presets import load_presets

    user_dir = tmp_path / "agents"
    user_dir.mkdir()
    (user_dir / "deep-research.yaml").write_text(
        "name: deep-research\n"
        "description: long-horizon research\n"
        "aliases: [dr, research]\n"
        "role: orchestrator\n",
        encoding="utf-8",
    )
    bundle = load_presets(user_dir=user_dir)
    assert bundle.resolve("dr").name == "deep-research"
    assert bundle.resolve("research").name == "deep-research"
    assert bundle.resolve("deep-research").role == "orchestrator"
