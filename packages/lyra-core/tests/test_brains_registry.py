"""Contract tests for ``lyra_core.brains`` (Phase J.1).

The four built-ins must always be present, every bundle must validate
its own name/description/SOUL body, and the installer must respect
``force`` while still keeping the marker file truthful.
"""
from __future__ import annotations

import pytest
from lyra_core.brains import (
    BrainBundle,
    BrainCommand,
    BrainRegistry,
    default_registry,
    install_brain,
)
from lyra_core.paths import RepoLayout


def test_default_registry_ships_four_builtins() -> None:
    reg = BrainRegistry(builtins=True)
    names = set(reg.names())
    assert {"default", "tdd-strict", "research", "ship-fast"} <= names


def test_default_registry_singleton_is_idempotent() -> None:
    a = default_registry()
    b = default_registry()
    assert a is b
    assert "default" in a.names()


def test_tdd_strict_bundle_enables_gate_by_default() -> None:
    reg = default_registry()
    bundle = reg.get("tdd-strict")
    assert bundle is not None
    assert bundle.tdd_gate_default is True
    assert "TDD" in bundle.soul_md
    assert bundle.policy_yaml is not None
    assert "tdd_gate: on" in bundle.policy_yaml


def test_research_bundle_uses_safe_toolset_and_denies_writes() -> None:
    reg = default_registry()
    bundle = reg.get("research")
    assert bundle is not None
    assert bundle.toolset == "safe"
    assert bundle.policy_yaml is not None
    assert "Bash" in bundle.policy_yaml
    assert "Edit" in bundle.policy_yaml
    assert "send_message" in bundle.policy_yaml


def test_ship_fast_bundle_keeps_tdd_off() -> None:
    reg = default_registry()
    bundle = reg.get("ship-fast")
    assert bundle is not None
    assert bundle.tdd_gate_default is False
    assert bundle.toolset == "coding"


def test_register_then_get_roundtrip() -> None:
    reg = BrainRegistry(builtins=False)
    bundle = BrainBundle(
        name="my-brain",
        description="custom",
        soul_md="# custom soul\n",
        toolset="default",
    )
    reg.register(bundle)
    assert reg.get("my-brain") is bundle
    assert "my-brain" in reg.names()


def test_register_duplicate_raises() -> None:
    reg = BrainRegistry()
    with pytest.raises(ValueError):
        reg.register(reg.get("default"))  # type: ignore[arg-type]


def test_replace_overwrites_existing() -> None:
    reg = BrainRegistry()
    new = BrainBundle(
        name="default",
        description="overwritten",
        soul_md="# new\n",
    )
    reg.replace(new)
    assert reg.get("default") is new


def test_invalid_brain_name_rejected() -> None:
    with pytest.raises(ValueError):
        BrainBundle(name="UPPER", description="x", soul_md="# x\n")
    with pytest.raises(ValueError):
        BrainBundle(name="-leading-dash", description="x", soul_md="# x\n")


def test_empty_description_rejected() -> None:
    with pytest.raises(ValueError):
        BrainBundle(name="ok", description="", soul_md="# x\n")


def test_empty_soul_rejected() -> None:
    with pytest.raises(ValueError):
        BrainBundle(name="ok", description="ok", soul_md="")


def test_install_writes_soul_and_marker(tmp_path) -> None:
    reg = default_registry()
    bundle = reg.get("default")
    layout = RepoLayout(repo_root=tmp_path)
    report = install_brain(bundle, layout)  # type: ignore[arg-type]
    soul = tmp_path / "SOUL.md"
    marker = tmp_path / ".lyra" / "brain.txt"
    assert soul.exists()
    assert "default brain" in soul.read_text()
    assert marker.exists()
    assert marker.read_text().strip() == "default"
    assert report.changed
    assert "SOUL.md" in report.written


def test_install_skips_existing_files_without_force(tmp_path) -> None:
    reg = default_registry()
    bundle = reg.get("default")
    layout = RepoLayout(repo_root=tmp_path)
    soul = tmp_path / "SOUL.md"
    soul.write_text("# user-written soul\n")
    report = install_brain(bundle, layout)  # type: ignore[arg-type]
    assert "SOUL.md" in report.skipped
    assert soul.read_text() == "# user-written soul\n"


def test_install_force_overwrites(tmp_path) -> None:
    reg = default_registry()
    bundle = reg.get("default")
    layout = RepoLayout(repo_root=tmp_path)
    soul = tmp_path / "SOUL.md"
    soul.write_text("# stale\n")
    report = install_brain(bundle, layout, force=True)  # type: ignore[arg-type]
    assert "SOUL.md" in report.written
    assert "default brain" in soul.read_text()


def test_install_writes_policy_yaml_when_present(tmp_path) -> None:
    reg = default_registry()
    bundle = reg.get("tdd-strict")
    layout = RepoLayout(repo_root=tmp_path)
    install_brain(bundle, layout)  # type: ignore[arg-type]
    policy = tmp_path / ".lyra" / "policy.yaml"
    assert policy.exists()
    assert "tdd_gate: on" in policy.read_text()


def test_install_skips_policy_when_bundle_ships_none(tmp_path) -> None:
    reg = default_registry()
    bundle = reg.get("default")
    layout = RepoLayout(repo_root=tmp_path)
    install_brain(bundle, layout)  # type: ignore[arg-type]
    policy = tmp_path / ".lyra" / "policy.yaml"
    assert not policy.exists()


def test_install_writes_user_commands(tmp_path) -> None:
    bundle = BrainBundle(
        name="custom-cmds",
        description="ships commands",
        soul_md="# soul\n",
        commands=(
            BrainCommand(name="ship", body="---\nname: ship\n---\nDeploy now."),
            BrainCommand(name="ack", body="ACK"),
        ),
    )
    layout = RepoLayout(repo_root=tmp_path)
    install_brain(bundle, layout)
    ship = tmp_path / ".lyra" / "commands" / "ship.md"
    ack = tmp_path / ".lyra" / "commands" / "ack.md"
    assert ship.exists() and "Deploy now" in ship.read_text()
    assert ack.exists() and ack.read_text() == "ACK"


def test_install_marker_records_active_brain(tmp_path) -> None:
    reg = default_registry()
    layout = RepoLayout(repo_root=tmp_path)
    install_brain(reg.get("research"), layout)  # type: ignore[arg-type]
    marker = tmp_path / ".lyra" / "brain.txt"
    assert marker.read_text().strip() == "research"


def test_invalid_command_name_rejected() -> None:
    with pytest.raises(ValueError):
        BrainCommand(name="WITH/SLASH", body="# bad")
