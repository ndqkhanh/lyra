"""Tests for the installed-bundles registry + uninstall lifecycle."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.bundle import (
    AgentInstaller,
    InstalledRecord,
    InstalledRegistry,
    SourceBundle,
    UninstallError,
    reset_global_installed_registry,
    uninstall_bundle,
)


@pytest.fixture
def isolated_registry(tmp_path):
    """Pin the global registry to an isolated path for each test."""
    path = tmp_path / "installed.json"
    reg = reset_global_installed_registry(path=path)
    yield reg
    reset_global_installed_registry()


def _make_bundle(tmp_path: Path, *, name: str = "iri-test", dual_use: bool = False) -> SourceBundle:
    root = tmp_path / "src"
    root.mkdir(parents=True, exist_ok=True)
    (root / "persona.md").write_text("p\n", encoding="utf-8")
    (root / "MEMORY.md").write_text("seed\n", encoding="utf-8")
    skills = root / "skills"
    skills.mkdir(exist_ok=True)
    (skills / "01-x.md").write_text("---\nname: x\ndescription: x\n---\n", encoding="utf-8")
    (skills / "02-y.md").write_text("---\nname: y\ndescription: y\n---\n", encoding="utf-8")
    evals = root / "evals"
    evals.mkdir(exist_ok=True)
    (evals / "golden.jsonl").write_text(json.dumps({"id": 1, "expected_pass": True}) + "\n", encoding="utf-8")
    (evals / "rubric.md").write_text("# r\n", encoding="utf-8")
    (root / "bundle.yaml").write_text(f"""apiVersion: lyra.dev/v3
kind: SourceBundle
name: {name}
version: 0.1.0
description: irt
dual_use: {'true' if dual_use else 'false'}
smoke_eval_threshold: 0.95
persona: persona.md
skills: skills/
tools:
  - kind: native
    name: x
memory:
  seed: MEMORY.md
evals:
  golden: evals/golden.jsonl
  rubric: evals/rubric.md
verifier:
  domain: irt
  command: pytest -q
  budget_seconds: 30
""", encoding="utf-8")
    return SourceBundle.load(root)


# ---- record / registry basics ---------------------------------------


def test_record_round_trip_json():
    r = InstalledRecord(
        bundle_name="x", bundle_version="0.1.0", bundle_hash="abc",
        target_dir="/tmp/x", attestation_path="/tmp/x/attestation.json",
        installed_at=1.0, last_verified_at=2.0,
        dual_use=True, authorized_by="ops:k", verifier_domain="code",
    )
    r2 = InstalledRecord.from_json(r.to_json())
    assert r2 == r


def test_registry_upsert_and_query(tmp_path):
    reg = InstalledRegistry(path=tmp_path / "i.json")
    rec = InstalledRecord(
        bundle_name="x", bundle_version="0.1.0", bundle_hash="abc",
        target_dir="/tmp/x", attestation_path="/tmp/x/att.json",
        installed_at=1.0, last_verified_at=2.0,
    )
    reg.upsert(rec)
    assert len(reg) == 1
    assert reg.find_by_name("x") == (rec,)
    assert reg.find_by_hash("abc") == (rec,)
    assert reg.find(bundle_hash="abc", target_dir="/tmp/x") is not None


def test_registry_persistence_across_instances(tmp_path):
    path = tmp_path / "i.json"
    reg = InstalledRegistry(path=path)
    rec = InstalledRecord(
        bundle_name="x", bundle_version="0.1.0", bundle_hash="abc",
        target_dir="/tmp/x", attestation_path="/tmp/x/att.json",
        installed_at=1.0, last_verified_at=2.0,
    )
    reg.upsert(rec)
    # Reopen — state must survive.
    reg2 = InstalledRegistry(path=path)
    assert len(reg2) == 1
    assert reg2.find_by_name("x")[0].bundle_hash == "abc"


def test_registry_remove(tmp_path):
    reg = InstalledRegistry(path=tmp_path / "i.json")
    rec = InstalledRecord(
        bundle_name="x", bundle_version="0.1.0", bundle_hash="abc",
        target_dir="/tmp/x", attestation_path="/tmp/x/att.json",
        installed_at=1.0, last_verified_at=2.0,
    )
    reg.upsert(rec)
    removed = reg.remove("abc", "/tmp/x")
    assert removed is not None
    assert len(reg) == 0


def test_registry_distinct_target_dirs_are_distinct_entries(tmp_path):
    reg = InstalledRegistry(path=tmp_path / "i.json")
    rec1 = InstalledRecord(
        bundle_name="x", bundle_version="0.1.0", bundle_hash="abc",
        target_dir="/tmp/a", attestation_path="/tmp/a/att.json",
        installed_at=1.0, last_verified_at=2.0,
    )
    rec2 = InstalledRecord(
        bundle_name="x", bundle_version="0.1.0", bundle_hash="abc",
        target_dir="/tmp/b", attestation_path="/tmp/b/att.json",
        installed_at=1.0, last_verified_at=2.0,
    )
    reg.upsert(rec1)
    reg.upsert(rec2)
    assert len(reg) == 2


# ---- installer auto-register ----------------------------------------


def test_installer_populates_registry(tmp_path, isolated_registry):
    bundle = _make_bundle(tmp_path)
    target = tmp_path / "out"
    AgentInstaller(bundle=bundle).install(target_dir=target)
    rows = isolated_registry.find_by_name(bundle.manifest.name)
    assert len(rows) == 1
    assert rows[0].target_dir == str(target.resolve())
    assert rows[0].verifier_domain == bundle.verifier.domain


def test_installer_dual_use_record_includes_authorized_by(tmp_path, isolated_registry):
    bundle = _make_bundle(tmp_path, name="dual-iri", dual_use=True)
    AgentInstaller(bundle=bundle).install(
        target_dir=tmp_path / "out",
        allow_dual_use=True,
        authorized_by="ops:khanh",
    )
    rows = isolated_registry.find_by_name("dual-iri")
    assert rows[0].dual_use is True
    assert rows[0].authorized_by == "ops:khanh"


def test_installer_idempotent_install_updates_last_verified(
    tmp_path, isolated_registry
):
    bundle = _make_bundle(tmp_path)
    target = tmp_path / "out"
    AgentInstaller(bundle=bundle).install(target_dir=target)
    first_install_at = isolated_registry.all()[0].installed_at

    # Sleep negligibly then re-install.
    import time as _t
    _t.sleep(0.01)
    AgentInstaller(bundle=bundle).install(target_dir=target)
    rec = isolated_registry.all()[0]
    # installed_at preserved (idempotent), last_verified_at advanced.
    assert rec.installed_at == first_install_at
    assert rec.last_verified_at >= first_install_at


def test_installer_can_disable_auto_register(tmp_path, isolated_registry):
    bundle = _make_bundle(tmp_path)
    inst = AgentInstaller(bundle=bundle)
    inst.auto_register_install = False
    inst.install(target_dir=tmp_path / "out")
    assert len(isolated_registry) == 0


# ---- uninstall lifecycle --------------------------------------------


def test_uninstall_removes_target_and_record(tmp_path, isolated_registry):
    bundle = _make_bundle(tmp_path)
    target = tmp_path / "out"
    att = AgentInstaller(bundle=bundle).install(target_dir=target)
    assert target.exists()
    assert len(isolated_registry) == 1

    removed = uninstall_bundle(
        bundle_hash=att.bundle_hash,
        target_dir=target,
    )
    assert removed.bundle_name == bundle.manifest.name
    assert not target.exists()
    assert len(isolated_registry) == 0


def test_uninstall_unknown_raises(tmp_path, isolated_registry):
    with pytest.raises(UninstallError, match="no installed record"):
        uninstall_bundle(bundle_hash="0" * 64, target_dir=tmp_path / "out")


def test_uninstall_refuses_when_attestation_tampered(tmp_path, isolated_registry):
    bundle = _make_bundle(tmp_path)
    target = tmp_path / "out"
    att = AgentInstaller(bundle=bundle).install(target_dir=target)

    # Tamper with the attestation file.
    att_path = target / "attestation.json"
    raw = json.loads(att_path.read_text(encoding="utf-8"))
    raw["target_dir"] = "/somewhere/else"
    att_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(UninstallError, match="signature invalid"):
        uninstall_bundle(bundle_hash=att.bundle_hash, target_dir=target)


def test_uninstall_override_skips_verify(tmp_path, isolated_registry):
    bundle = _make_bundle(tmp_path)
    target = tmp_path / "out"
    att = AgentInstaller(bundle=bundle).install(target_dir=target)

    # Tamper.
    att_path = target / "attestation.json"
    raw = json.loads(att_path.read_text(encoding="utf-8"))
    raw["target_dir"] = "/somewhere/else"
    att_path.write_text(json.dumps(raw), encoding="utf-8")

    # Override allows it through.
    removed = uninstall_bundle(
        bundle_hash=att.bundle_hash,
        target_dir=target,
        verify_attestation_first=False,
    )
    assert removed.bundle_name == bundle.manifest.name
    assert not target.exists()


def test_uninstall_refuses_when_attestation_missing(tmp_path, isolated_registry):
    bundle = _make_bundle(tmp_path)
    target = tmp_path / "out"
    att = AgentInstaller(bundle=bundle).install(target_dir=target)

    # Delete attestation.
    (target / "attestation.json").unlink()

    with pytest.raises(UninstallError, match="LBL-UNINSTALL-VERIFY"):
        uninstall_bundle(bundle_hash=att.bundle_hash, target_dir=target)


def test_uninstall_emits_lifecycle_event(tmp_path, isolated_registry, monkeypatch):
    captured: list = []

    def fake_emit(name: str, /, **attrs):
        captured.append((name, attrs))

    from lyra_core.hir import events
    monkeypatch.setattr(events, "emit", fake_emit)

    bundle = _make_bundle(tmp_path)
    target = tmp_path / "out"
    att = AgentInstaller(bundle=bundle).install(target_dir=target)
    uninstall_bundle(bundle_hash=att.bundle_hash, target_dir=target)

    names = [n for n, _ in captured]
    assert "bundle.uninstalled" in names
