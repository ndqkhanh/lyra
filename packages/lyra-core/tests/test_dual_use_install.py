"""Tests for the v3.11 LBL-BUNDLE-DUAL-USE install gate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.bundle import (
    AgentInstaller,
    DualUseAuthorizationError,
    SourceBundle,
    verify_attestation,
)


def _make_dual_use_bundle(root: Path, *, dual_use: bool = True) -> SourceBundle:
    root.mkdir(parents=True, exist_ok=True)
    (root / "persona.md").write_text("Dual-use bundle persona.\n", encoding="utf-8")
    (root / "MEMORY.md").write_text("seed.\n", encoding="utf-8")
    skills = root / "skills"
    skills.mkdir(exist_ok=True)
    (skills / "01-x.md").write_text("---\nname: x\ndescription: x\n---\n", encoding="utf-8")
    (skills / "02-y.md").write_text("---\nname: y\ndescription: y\n---\n", encoding="utf-8")
    evals = root / "evals"
    evals.mkdir(exist_ok=True)
    (evals / "golden.jsonl").write_text(
        json.dumps({"id": 1, "expected_pass": True}) + "\n", encoding="utf-8"
    )
    (evals / "rubric.md").write_text("# Rubric\n", encoding="utf-8")
    manifest = f"""apiVersion: lyra.dev/v3
kind: SourceBundle
name: dual-use-test
version: 0.1.0
description: A dual-use test bundle.
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
  domain: dual-use-test
  command: pytest -q
  budget_seconds: 10
"""
    (root / "bundle.yaml").write_text(manifest, encoding="utf-8")
    return SourceBundle.load(root)


def test_dual_use_blocks_default_install(tmp_path):
    bundle = _make_dual_use_bundle(tmp_path / "b")
    inst = AgentInstaller(bundle=bundle)
    with pytest.raises(DualUseAuthorizationError, match="LBL-BUNDLE-DUAL-USE"):
        inst.install(target_dir=tmp_path / "out")


def test_dual_use_requires_authorized_by(tmp_path):
    bundle = _make_dual_use_bundle(tmp_path / "b")
    inst = AgentInstaller(bundle=bundle)
    # allow_dual_use alone is not enough — authorized_by must be non-empty.
    with pytest.raises(DualUseAuthorizationError):
        inst.install(target_dir=tmp_path / "out", allow_dual_use=True)
    with pytest.raises(DualUseAuthorizationError):
        inst.install(target_dir=tmp_path / "out", allow_dual_use=True, authorized_by="")
    with pytest.raises(DualUseAuthorizationError):
        inst.install(target_dir=tmp_path / "out", allow_dual_use=True, authorized_by="   ")


def test_dual_use_passes_with_authorization(tmp_path):
    bundle = _make_dual_use_bundle(tmp_path / "b")
    inst = AgentInstaller(bundle=bundle)
    att = inst.install(
        target_dir=tmp_path / "out",
        allow_dual_use=True,
        authorized_by="ops:khanh@2026-05-09",
    )
    assert att.dual_use is True
    assert att.authorized_by == "ops:khanh@2026-05-09"
    assert verify_attestation(att) is True


def test_non_dual_use_ignores_flags(tmp_path):
    bundle = _make_dual_use_bundle(tmp_path / "b", dual_use=False)
    inst = AgentInstaller(bundle=bundle)
    att = inst.install(target_dir=tmp_path / "out")  # no flags needed
    assert att.dual_use is False
    assert att.authorized_by is None


def test_authorized_by_survives_attestation_round_trip(tmp_path):
    bundle = _make_dual_use_bundle(tmp_path / "b")
    inst = AgentInstaller(bundle=bundle)
    att = inst.install(
        target_dir=tmp_path / "out",
        allow_dual_use=True,
        authorized_by="security-review-2026-05-09",
    )
    # Re-load and verify.
    from lyra_core.bundle import Attestation
    reloaded = Attestation.load(Path(att.target_dir) / "attestation.json")
    assert reloaded.authorized_by == "security-review-2026-05-09"
    assert verify_attestation(reloaded) is True


def test_dual_use_authorization_in_attestation_json(tmp_path):
    bundle = _make_dual_use_bundle(tmp_path / "b")
    inst = AgentInstaller(bundle=bundle)
    inst.install(
        target_dir=tmp_path / "out",
        allow_dual_use=True,
        authorized_by="incident-7421",
    )
    raw = json.loads((tmp_path / "out" / "attestation.json").read_text(encoding="utf-8"))
    assert raw["authorized_by"] == "incident-7421"
    assert raw["dual_use"] is True
