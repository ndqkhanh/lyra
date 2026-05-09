"""Tests for v3.11 slash commands — /team, /scaling, /coverage, /bundle."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from lyra_cli.interactive.v311_commands import (
    cmd_bundle,
    cmd_coverage,
    cmd_scaling,
    cmd_team,
)


# ---- helpers ----------------------------------------------------------


def _session() -> SimpleNamespace:
    """Stub session — handlers store their per-command state on it."""
    return SimpleNamespace()


def _bundle_dir() -> Path:
    """Return the path to one of the W1 sample bundles."""
    here = Path(__file__).resolve().parents[5]
    bundle = here / "projects" / "argus" / "bundle"
    assert bundle.is_dir(), f"missing argus bundle at {bundle}"
    return bundle


# ---- /team ------------------------------------------------------------


def test_team_help_renders():
    r = cmd_team(_session(), "help")
    assert "Agent Teams" in r.output


def test_team_list_empty():
    r = cmd_team(_session(), "list")
    assert "No team" in r.output


def test_team_spawn_and_status():
    s = _session()
    r1 = cmd_team(s, "spawn alice smart")
    assert "spawned" in r1.output
    assert "alice" in r1.output
    r2 = cmd_team(s, "status")
    assert "team=session" in r2.output
    assert "alice" in r2.output


def test_team_add_task_and_mailbox(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    s = _session()
    cmd_team(s, "spawn alice")
    r = cmd_team(s, "add-task review the auth module")
    assert "task added" in r.output
    r2 = cmd_team(s, "mailbox alice")
    assert "alice" in r2.output


def test_team_unknown_subcommand():
    r = cmd_team(_session(), "explode")
    assert "unknown" in r.output.lower()


def test_team_uses_real_executor_when_llm_present():
    """When the session has an llm + tools + store wired, /team spawn
    uses an AgentLoopExecutor over them instead of the stub."""

    class _StubLLM:
        def chat(self, *args, **kwargs):
            return {"content": "real-llm-reply", "tool_calls": [], "stop_reason": "end_turn"}

    class _StubStore:
        def append_user_message(self, *args, **kwargs): pass
        def append_assistant_message(self, *args, **kwargs): pass
        def session_started(self, *args, **kwargs): pass

    s = _session()
    s.llm = _StubLLM()
    s.tools = {}
    s.store = _StubStore()

    r = cmd_team(s, "spawn alice")
    assert "spawned" in r.output
    assert s._v311_lead is not None
    from lyra_core.teams import AgentLoopExecutor
    assert isinstance(s._v311_lead.executor, AgentLoopExecutor)


def test_team_falls_back_to_stub_when_no_llm():
    """No llm on session → fall back to deterministic stub executor."""
    s = _session()
    cmd_team(s, "spawn alice")
    assert s._v311_lead is not None
    from lyra_core.teams import AgentLoopExecutor
    # Stub executor is a plain function, not AgentLoopExecutor.
    assert not isinstance(s._v311_lead.executor, AgentLoopExecutor)


# ---- /scaling ---------------------------------------------------------


def test_scaling_default_renders_table():
    r = cmd_scaling(_session(), "")
    assert "axis" in r.output
    assert "pretrain" in r.output
    assert "best lever" in r.output


def test_scaling_help():
    r = cmd_scaling(_session(), "help")
    assert "Scaling" in r.output or "scaling" in r.output


def test_scaling_axis_detail():
    r = cmd_scaling(_session(), "axis pretrain")
    assert "axis=pretrain" in r.output


def test_scaling_axis_unknown():
    r = cmd_scaling(_session(), "axis explode")
    assert "unknown" in r.output.lower()


# ---- /coverage --------------------------------------------------------


def test_coverage_default_uses_global_singleton():
    """The default coverage index is the process-wide singleton, so
    bundles installed elsewhere in the process surface here."""
    from lyra_core.bundle import global_index, reset_global_index
    reset_global_index()
    try:
        global_index().record_verifier(domain="seeded", verifier_id="seeded-v")
        global_index().record_pass_rate(domain="seeded", rate=0.9)
        r = cmd_coverage(_session(), "")
        assert "seeded" in r.output
    finally:
        reset_global_index()


def test_coverage_isolated_when_explicitly_overridden():
    """Tests can pin a fresh index by setting session._v311_coverage."""
    from lyra_core.bundle import VerifierCoverageIndex
    s = _session()
    s._v311_coverage = VerifierCoverageIndex()
    r = cmd_coverage(s, "")
    assert "empty" in r.output.lower()


def test_coverage_help():
    r = cmd_coverage(_session(), "help")
    assert "coverage" in r.output.lower()


def test_coverage_after_record():
    s = _session()
    # Trigger lazy creation of the index
    cmd_coverage(s, "")
    # Score >= 0.7 requires >= 4 verifiers (verifier_norm=0.8) + high pass rate.
    # 0.4*(4/5) + 0.4*0.92 + 0.2*1.0 = 0.32 + 0.368 + 0.2 = 0.888
    for vid in ("pytest", "mypy", "ruff", "black"):
        s._v311_coverage.record_verifier(domain="code", verifier_id=vid)
    s._v311_coverage.record_evals(domain="code", count=120)
    s._v311_coverage.record_pass_rate(domain="code", rate=0.92)
    r = cmd_coverage(s, "")
    assert "code" in r.output
    assert "edit_automatically" in r.output


def test_coverage_per_domain():
    s = _session()
    cmd_coverage(s, "")
    s._v311_coverage.record_pass_rate(domain="research", rate=0.5)
    r = cmd_coverage(s, "research")
    assert "domain=research" in r.output


# ---- /bundle ----------------------------------------------------------


def test_bundle_help():
    r = cmd_bundle(_session(), "help")
    assert "Bundle" in r.output or "bundle" in r.output.lower()


def test_bundle_info_real_bundle():
    r = cmd_bundle(_session(), f"info {_bundle_dir()}")
    out = json.loads(r.output)
    assert out["name"] == "argus-skill-router"


def test_bundle_install_smokes(tmp_path):
    target = tmp_path / "installed"
    r = cmd_bundle(_session(), f"install {_bundle_dir()} {target}")
    assert "installed" in r.output
    assert (target / "attestation.json").exists()


def test_bundle_export_to_claude_code(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    r = cmd_bundle(_session(), f"export {_bundle_dir()} claude-code")
    assert "exported" in r.output
    # Default target dir is $HOME/.lyra-export-claude-code
    assert (tmp_path / ".lyra-export-claude-code").is_dir()


def test_bundle_export_unknown_target():
    r = cmd_bundle(_session(), f"export {_bundle_dir()} explode")
    assert "failed" in r.output.lower()


def test_bundle_unknown_subcommand():
    r = cmd_bundle(_session(), "explode")
    assert "unknown" in r.output.lower()


def test_bundle_list_empty(tmp_path, monkeypatch):
    """/bundle list with no installs prints a hint."""
    from lyra_core.bundle import reset_global_installed_registry

    monkeypatch.setenv("HOME", str(tmp_path))
    reset_global_installed_registry(path=tmp_path / "installed.json")
    r = cmd_bundle(_session(), "list")
    assert "No bundles" in r.output


def test_bundle_list_after_install(tmp_path, monkeypatch):
    """/bundle list shows installed bundles."""
    from lyra_core.bundle import reset_global_installed_registry

    monkeypatch.setenv("HOME", str(tmp_path))
    reset_global_installed_registry(path=tmp_path / "installed.json")
    cmd_bundle(_session(), f"install {_bundle_dir()} {tmp_path / 'installed'}")
    r = cmd_bundle(_session(), "list")
    assert "argus-skill-router" in r.output


def test_bundle_uninstall_round_trip(tmp_path, monkeypatch):
    from lyra_core.bundle import reset_global_installed_registry, global_installed_registry

    monkeypatch.setenv("HOME", str(tmp_path))
    reset_global_installed_registry(path=tmp_path / "installed.json")
    cmd_bundle(_session(), f"install {_bundle_dir()} {tmp_path / 'installed'}")
    rows = global_installed_registry().all()
    assert len(rows) == 1
    full_hash = rows[0].bundle_hash
    r = cmd_bundle(_session(), f"uninstall {full_hash[:8]} {tmp_path / 'installed'}")
    assert "uninstalled" in r.output
    assert len(global_installed_registry().all()) == 0


def test_bundle_uninstall_unknown_hash(tmp_path, monkeypatch):
    from lyra_core.bundle import reset_global_installed_registry

    monkeypatch.setenv("HOME", str(tmp_path))
    reset_global_installed_registry(path=tmp_path / "installed.json")
    r = cmd_bundle(_session(), f"uninstall 0000000000 {tmp_path / 'nope'}")
    assert "no installed bundle" in r.output.lower()


def test_bundle_fetch_help_when_short(tmp_path):
    s = _session()
    r = cmd_bundle(s, "fetch")
    assert "Usage" in r.output


def test_bundle_trust_help_when_short(tmp_path):
    s = _session()
    r = cmd_bundle(s, "trust")
    assert "Usage" in r.output


def test_bundle_trust_records_into_session_registry(tmp_path):
    s = _session()
    r = cmd_bundle(s, "trust acp-mkt acp-fp 6162636465")  # 'abcde' hex
    assert "trusted" in r.output
    # Verify session has the registry with the marketplace.
    reg = s._v311_marketplace
    assert reg.is_trusted("acp-mkt")


def test_bundle_fetch_round_trip(tmp_path, monkeypatch):
    """Round-trip: trust → fetch → install → verify hash."""
    import io
    import tarfile
    from lyra_core.bundle import sign_archive, MarketplaceKey

    payload_files = {
        "persona.md": "p\n",
        "MEMORY.md": "seed\n",
        "skills/01-x.md": "---\nname: x\ndescription: x\n---\n",
        "skills/02-y.md": "---\nname: y\ndescription: y\n---\n",
        "evals/golden.jsonl": json.dumps({"id": 1, "expected_pass": True}) + "\n",
        "evals/rubric.md": "# r\n",
        "bundle.yaml": (
            "apiVersion: lyra.dev/v3\n"
            "kind: SourceBundle\n"
            "name: cli-fetch-test\n"
            "version: 0.1.0\n"
            "description: x\n"
            "dual_use: false\n"
            "smoke_eval_threshold: 0.95\n"
            "persona: persona.md\n"
            "skills: skills/\n"
            "tools:\n  - kind: native\n    name: x\n"
            "memory:\n  seed: MEMORY.md\n"
            "evals:\n  golden: evals/golden.jsonl\n  rubric: evals/rubric.md\n"
            "verifier:\n  domain: cli\n  command: pytest -q\n  budget_seconds: 30\n"
        ),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path_, content in payload_files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=path_)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    archive = buf.getvalue()
    secret = b"cli-secret"
    sig = sign_archive(archive, MarketplaceKey(fingerprint="cli-fp", secret=secret))

    monkeypatch.setattr(
        "lyra_core.bundle.marketplace._default_fetch_url", lambda url: archive
    )
    s = _session()
    cmd_bundle(s, f"trust cli-mkt cli-fp {secret.hex()}")
    r = cmd_bundle(s, f"fetch https://x.example.com/b.tar.gz {sig} cli-mkt")
    assert "fetched" in r.output
    assert "cli-fetch-test" in r.output


def test_bundle_fetch_signature_mismatch_surfaces(tmp_path, monkeypatch):
    import io, tarfile
    from lyra_core.bundle import MarketplaceKey

    # Build any archive.
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="x")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"y"))
    archive = buf.getvalue()
    monkeypatch.setattr(
        "lyra_core.bundle.marketplace._default_fetch_url", lambda url: archive
    )
    s = _session()
    cmd_bundle(s, f"trust m1 fp1 {(b'k').hex()}")
    r = cmd_bundle(s, "fetch https://x.example.com/b.tar.gz 0000 m1")
    assert "fetch failed" in r.output
