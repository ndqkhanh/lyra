"""Tests for L311-6 bundle → coverage auto-populate.

Every successful install contributes to the process-wide
:class:`VerifierCoverageIndex`. The CLI `/coverage` slash reads
the same singleton, so users see installed bundles surface
automatically.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.bundle import (
    AgentInstaller,
    SourceBundle,
    global_index,
    reset_global_index,
)


@pytest.fixture(autouse=True)
def _isolated_index():
    """Each test gets a fresh global index."""
    reset_global_index()
    yield
    reset_global_index()


def _make_bundle(root: Path, *, name: str, domain: str = "code") -> SourceBundle:
    root.mkdir(parents=True, exist_ok=True)
    (root / "persona.md").write_text(f"persona for {name}\n", encoding="utf-8")
    (root / "MEMORY.md").write_text("seed\n", encoding="utf-8")
    skills = root / "skills"
    skills.mkdir(exist_ok=True)
    (skills / "01-x.md").write_text(
        "---\nname: x\ndescription: x\n---\n", encoding="utf-8"
    )
    (skills / "02-y.md").write_text(
        "---\nname: y\ndescription: y\n---\n", encoding="utf-8"
    )
    evals = root / "evals"
    evals.mkdir(exist_ok=True)
    eval_lines = [{"id": i, "expected_pass": True} for i in range(5)]
    (evals / "golden.jsonl").write_text(
        "\n".join(json.dumps(x) for x in eval_lines) + "\n", encoding="utf-8"
    )
    (evals / "rubric.md").write_text("# Rubric\n", encoding="utf-8")
    manifest = f"""apiVersion: lyra.dev/v3
kind: SourceBundle
name: {name}
version: 0.1.0
description: A test bundle.
dual_use: false
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
  domain: {domain}
  command: pytest -q
  budget_seconds: 30
"""
    (root / "bundle.yaml").write_text(manifest, encoding="utf-8")
    return SourceBundle.load(root)


def test_install_populates_global_index(tmp_path):
    bundle = _make_bundle(tmp_path / "b", name="bundle-a", domain="code")
    inst = AgentInstaller(bundle=bundle)
    inst.install(target_dir=tmp_path / "out")
    cov = global_index().get("code")
    assert cov.verifier_count == 1
    assert cov.eval_count == 5
    assert cov.pass_rate_30d == 1.0


def test_two_bundles_same_domain_aggregate(tmp_path):
    bundle_a = _make_bundle(tmp_path / "a", name="bundle-a", domain="code")
    bundle_b = _make_bundle(tmp_path / "b", name="bundle-b", domain="code")
    AgentInstaller(bundle=bundle_a).install(target_dir=tmp_path / "out_a")
    AgentInstaller(bundle=bundle_b).install(target_dir=tmp_path / "out_b")
    cov = global_index().get("code")
    assert cov.verifier_count == 2
    assert cov.eval_count == 10  # 5 + 5


def test_two_bundles_different_domains(tmp_path):
    bundle_a = _make_bundle(tmp_path / "a", name="bundle-a", domain="code")
    bundle_b = _make_bundle(tmp_path / "b", name="bundle-b", domain="research")
    AgentInstaller(bundle=bundle_a).install(target_dir=tmp_path / "out_a")
    AgentInstaller(bundle=bundle_b).install(target_dir=tmp_path / "out_b")
    domains = set(global_index().domains())
    assert {"code", "research"} <= domains


def test_auto_populate_disabled_per_installer(tmp_path):
    bundle = _make_bundle(tmp_path / "b", name="bundle-a", domain="code")
    inst = AgentInstaller(bundle=bundle)
    inst.auto_populate_coverage = False
    inst.install(target_dir=tmp_path / "out")
    # No domains in the index.
    assert global_index().domains() == ()


def test_idempotent_install_does_not_double_count(tmp_path):
    bundle = _make_bundle(tmp_path / "b", name="bundle-a", domain="code")
    inst = AgentInstaller(bundle=bundle)
    inst.install(target_dir=tmp_path / "out")
    # Second install short-circuits via LBL-AI-IDEMPOTENT and should
    # not re-populate the index.
    inst.install(target_dir=tmp_path / "out")
    cov = global_index().get("code")
    # verifier_id is a set under the hood so duplicate adds are safe.
    assert cov.verifier_count == 1


def test_global_index_singleton_persists():
    a = global_index()
    b = global_index()
    assert a is b


def test_reset_clears_singleton():
    a = global_index()
    a.record_pass_rate(domain="x", rate=0.5)
    reset_global_index()
    assert global_index() is not a
    assert global_index().domains() == ()
