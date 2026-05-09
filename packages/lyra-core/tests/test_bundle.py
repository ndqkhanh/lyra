"""Tests for L311-4 / L311-5 / L311-6 — Software 3.0 SourceBundle,
agent-installer, and verifier-coverage index."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.bundle import (
    AgentInstaller,
    Attestation,
    AttestationError,
    BundleValidationError,
    InstallError,
    SmokeEvalReport,
    SourceBundle,
    VerifierCoverageIndex,
    sign_attestation,
    verify_attestation,
)


# ---- helpers ----------------------------------------------------------


def _write_min_bundle(
    root: Path,
    *,
    name: str = "test-bundle",
    version: str = "0.1.0",
    eval_lines: list[dict] | None = None,
    dual_use: bool = False,
    threshold: float = 0.95,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if eval_lines is None:
        eval_lines = [{"id": 1, "expected_pass": True}, {"id": 2, "expected_pass": True}]
    (root / "persona.md").write_text("You are a test agent.\n", encoding="utf-8")
    (root / "MEMORY.md").write_text("Initial memory seed.\n", encoding="utf-8")
    skills = root / "skills"
    skills.mkdir(exist_ok=True)
    (skills / "01-greeting.md").write_text(
        "---\nname: greeting\ndescription: say hi\n---\n# Greeting skill\n",
        encoding="utf-8",
    )
    (skills / "02-farewell.md").write_text(
        "---\nname: farewell\ndescription: say bye\n---\n# Farewell skill\n",
        encoding="utf-8",
    )
    evals = root / "evals"
    evals.mkdir(exist_ok=True)
    (evals / "golden.jsonl").write_text(
        "\n".join(json.dumps(x) for x in eval_lines) + "\n", encoding="utf-8"
    )
    (evals / "rubric.md").write_text("# Rubric\nPass means right.\n", encoding="utf-8")
    manifest = f"""apiVersion: lyra.dev/v3
kind: SourceBundle
name: {name}
version: {version}
description: a test bundle
dual_use: {'true' if dual_use else 'false'}
smoke_eval_threshold: {threshold}
persona: persona.md
skills: skills/
tools:
  - kind: native
    name: read
  - kind: mcp
    name: code_search
    server: stdio:./mcp/code_search.py
memory:
  seed: MEMORY.md
evals:
  golden: evals/golden.jsonl
  rubric: evals/rubric.md
verifier:
  domain: code
  command: pytest -q
  budget_seconds: 600
"""
    (root / "bundle.yaml").write_text(manifest, encoding="utf-8")
    return root


# ---- SourceBundle.load + validate ------------------------------------


def test_bundle_loads_six_parts(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    b = SourceBundle.load(root)
    b.validate()
    assert b.manifest.name == "test-bundle"
    assert b.manifest.version == "0.1.0"
    assert b.persona.text.startswith("You are")
    assert len(b.skills) == 2
    assert len(b.tools) == 2
    assert b.tools[0].kind == "native"
    assert b.tools[1].kind == "mcp"
    assert b.tools[1].server.startswith("stdio:")
    assert b.memory.seed_text.startswith("Initial")
    assert b.evals.eval_count == 2
    assert b.verifier.domain == "code"


def test_bundle_skills_carry_name_and_description(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    b = SourceBundle.load(root)
    names = [s.name for s in b.skills]
    descs = [s.description for s in b.skills]
    assert "greeting" in names and "farewell" in names
    assert all(d for d in descs)


def test_bundle_summary_includes_hash(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    b = SourceBundle.load(root)
    s = b.summary()
    assert s["name"] == "test-bundle"
    assert len(s["hash"]) == 16


def test_bundle_validate_rejects_missing_persona(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    (root / "persona.md").write_text("", encoding="utf-8")
    b = SourceBundle.load(root)
    with pytest.raises(BundleValidationError, match="persona"):
        b.validate()


def test_bundle_validate_rejects_empty_evals(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    (root / "evals" / "golden.jsonl").write_text("", encoding="utf-8")
    b = SourceBundle.load(root)
    with pytest.raises(BundleValidationError, match="evals"):
        b.validate()


def test_bundle_load_missing_manifest_raises(tmp_path):
    (tmp_path / "b").mkdir()
    with pytest.raises(BundleValidationError, match="bundle.yaml"):
        SourceBundle.load(tmp_path / "b")


def test_bundle_hash_is_stable(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    b1 = SourceBundle.load(root)
    b2 = SourceBundle.load(root)
    assert b1.hash() == b2.hash()


def test_bundle_hash_changes_with_persona(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    b1 = SourceBundle.load(root)
    (root / "persona.md").write_text("Different persona.\n", encoding="utf-8")
    b2 = SourceBundle.load(root)
    assert b1.hash() != b2.hash()


# ---- attestation ------------------------------------------------------


def _stub_attestation() -> Attestation:
    return Attestation(
        bundle_name="x",
        bundle_version="0.1.0",
        bundle_hash="abc123",
        target_dir="/tmp/x",
        installed_at=1715260000.0,
        smoke_eval_pass=10,
        smoke_eval_fail=0,
        smoke_eval_pass_rate=1.0,
        registered_skills=("a", "b"),
        wired_tools=("native:read",),
        verifier_domain="code",
        dual_use=False,
        signature=None,
    )


def test_attestation_sign_and_verify():
    a = _stub_attestation()
    signed = sign_attestation(a)
    assert signed.signature is not None
    assert verify_attestation(signed) is True


def test_attestation_verify_rejects_tampered():
    a = _stub_attestation()
    signed = sign_attestation(a)
    tampered = Attestation(
        bundle_name=signed.bundle_name,
        bundle_version=signed.bundle_version,
        bundle_hash=signed.bundle_hash,
        target_dir="/tmp/tampered",  # changed
        installed_at=signed.installed_at,
        smoke_eval_pass=signed.smoke_eval_pass,
        smoke_eval_fail=signed.smoke_eval_fail,
        smoke_eval_pass_rate=signed.smoke_eval_pass_rate,
        registered_skills=signed.registered_skills,
        wired_tools=signed.wired_tools,
        verifier_domain=signed.verifier_domain,
        dual_use=signed.dual_use,
        signature=signed.signature,
    )
    assert verify_attestation(tampered) is False


def test_attestation_verify_unsigned_raises():
    a = _stub_attestation()
    with pytest.raises(AttestationError):
        verify_attestation(a)


def test_attestation_round_trip(tmp_path):
    a = sign_attestation(_stub_attestation())
    p = tmp_path / "att.json"
    a.dump(p)
    b = Attestation.load(p)
    assert b.bundle_hash == a.bundle_hash
    assert verify_attestation(b) is True


# ---- AgentInstaller ---------------------------------------------------


def test_installer_happy_path(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    bundle = SourceBundle.load(root)
    target = tmp_path / "installed"
    inst = AgentInstaller(bundle=bundle)
    att = inst.install(target_dir=target)
    assert att.smoke_eval_pass_rate == 1.0
    assert (target / "persona.md").exists()
    assert (target / "memory_seed.md").exists()
    assert (target / "skills" / "01-greeting.md").exists()
    assert (target / "tools.json").exists()
    assert (target / "attestation.json").exists()
    assert verify_attestation(att) is True


def test_installer_idempotent(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    bundle = SourceBundle.load(root)
    target = tmp_path / "installed"
    inst = AgentInstaller(bundle=bundle)
    att1 = inst.install(target_dir=target)
    att2 = inst.install(target_dir=target)
    assert att1.bundle_hash == att2.bundle_hash
    assert att1.installed_at == att2.installed_at  # same record returned


def test_installer_blocks_low_smoke_eval(tmp_path):
    # Bundle with all expected_pass=false → 0% pass rate, threshold 0.95
    eval_lines = [{"id": 1, "expected_pass": False}, {"id": 2, "expected_pass": False}]
    root = _write_min_bundle(tmp_path / "b", eval_lines=eval_lines)
    bundle = SourceBundle.load(root)
    inst = AgentInstaller(bundle=bundle)
    with pytest.raises(InstallError, match="LBL-AI-EVAL"):
        inst.install(target_dir=tmp_path / "installed")


def test_installer_calls_on_step(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    bundle = SourceBundle.load(root)
    seen: list[str] = []

    def cb(step, payload):
        seen.append(step)

    inst = AgentInstaller(bundle=bundle, on_step=cb)
    inst.install(target_dir=tmp_path / "installed")
    assert seen[:5] == ["provision", "register_skills", "wire_tools", "smoke_eval", "attest"]


def test_installer_custom_smoke_runner(tmp_path):
    root = _write_min_bundle(tmp_path / "b")
    bundle = SourceBundle.load(root)
    calls = []

    def runner(b):
        calls.append(b.manifest.name)
        return SmokeEvalReport(pass_count=10, fail_count=0)

    inst = AgentInstaller(bundle=bundle, smoke_eval_runner=runner)
    att = inst.install(target_dir=tmp_path / "installed")
    assert calls == ["test-bundle"]
    assert att.smoke_eval_pass_rate == 1.0


def test_installer_dual_use_propagates_to_attestation(tmp_path):
    root = _write_min_bundle(tmp_path / "b", dual_use=True)
    bundle = SourceBundle.load(root)
    inst = AgentInstaller(bundle=bundle)
    # v3.11: dual-use bundles require explicit authorization
    # (LBL-BUNDLE-DUAL-USE). Verified separately in test_dual_use_install.py.
    att = inst.install(
        target_dir=tmp_path / "installed",
        allow_dual_use=True,
        authorized_by="test:propagation",
    )
    assert att.dual_use is True
    assert att.authorized_by == "test:propagation"


# ---- SmokeEvalReport --------------------------------------------------


def test_smoke_eval_report_pass_rate():
    r = SmokeEvalReport(pass_count=4, fail_count=1)
    assert abs(r.pass_rate - 0.8) < 1e-9
    assert r.total == 5


def test_smoke_eval_report_zero_attempted():
    r = SmokeEvalReport(pass_count=0, fail_count=0, skipped=2)
    assert r.pass_rate == 0.0


# ---- VerifierCoverageIndex --------------------------------------------


def test_coverage_index_basic():
    idx = VerifierCoverageIndex()
    idx.record_verifier(domain="code", verifier_id="pytest")
    idx.record_verifier(domain="code", verifier_id="mypy")
    idx.record_evals(domain="code", count=120)
    idx.record_pass_rate(domain="code", rate=0.9)
    cov = idx.get("code")
    assert cov.verifier_count == 2
    assert cov.eval_count == 120
    assert cov.pass_rate_30d == 0.9
    # score ≈ 0.4*(2/5) + 0.4*0.9 + 0.2*1.0 = 0.16 + 0.36 + 0.2 = 0.72
    assert abs(cov.coverage_score - 0.72) < 1e-3
    assert cov.admit_recommendation == "edit_automatically"


def test_coverage_index_low_score_recommends_plan_mode():
    idx = VerifierCoverageIndex()
    idx.record_pass_rate(domain="voice", rate=0.5)
    cov = idx.get("voice")
    assert cov.admit_recommendation == "plan_mode"


def test_coverage_index_rejects_invalid_pass_rate():
    idx = VerifierCoverageIndex()
    with pytest.raises(ValueError):
        idx.record_pass_rate(domain="x", rate=1.5)


def test_coverage_index_all_returns_sorted_domains():
    idx = VerifierCoverageIndex()
    idx.record_verifier(domain="research", verifier_id="judge")
    idx.record_verifier(domain="code", verifier_id="pytest")
    domains = [c.domain for c in idx.all()]
    assert domains == ["code", "research"]
