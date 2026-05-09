"""End-to-end v3.11 lifecycle test.

Exercises every v3.11 surface in one trace:

1. **Fetch** a remote bundle from a (mocked) marketplace, signature-
   verified.
2. **Install** the fetched bundle through ``AgentInstaller`` with the
   smoke-eval gate, dual-use authorization, and routine registration.
3. **List** installed bundles via the registry.
4. **Spawn** an Agent Teams runtime, add tasks, run to idle.
5. **Score** verifier coverage and read the scaling axes.
6. **Export** the bundle to all four cross-harness targets.
7. **Uninstall** with attestation re-verify.

Stdlib-only — no live LLM, no network, no real cron daemon thread.
The test is deliberately one long function so the lifecycle reads as
a story.
"""
from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest


def _build_dual_use_bundle_tar(*, name: str = "e2e-bundle") -> bytes:
    files = {
        "persona.md": "E2E persona\n",
        "MEMORY.md": "seed\n",
        "skills/01-x.md": "---\nname: x\ndescription: x\n---\n# X\n",
        "skills/02-y.md": "---\nname: y\ndescription: y\n---\n# Y\n",
        "skills/03-z.md": "---\nname: z\ndescription: z\n---\n# Z\n",
        "skills/04-w.md": "---\nname: w\ndescription: w\n---\n# W\n",
        "evals/golden.jsonl": "\n".join(
            json.dumps({"id": i, "expected_pass": True}) for i in range(12)
        ) + "\n",
        "evals/rubric.md": "# Rubric\n",
        "bundle.yaml": (
            "apiVersion: lyra.dev/v3\n"
            "kind: SourceBundle\n"
            f"name: {name}\n"
            "version: 0.1.0\n"
            "description: e2e dual-use bundle\n"
            "dual_use: true\n"
            "smoke_eval_threshold: 0.95\n"
            "persona: persona.md\n"
            "skills: skills/\n"
            "tools:\n"
            "  - kind: native\n    name: e2e_tool\n"
            "  - kind: mcp\n    name: e2e_mcp\n    server: stdio:./tools/e2e.py\n"
            "memory:\n  seed: MEMORY.md\n"
            "evals:\n  golden: evals/golden.jsonl\n  rubric: evals/rubric.md\n"
            "verifier:\n  domain: e2e\n  command: pytest -q\n  budget_seconds: 30\n"
            "routines:\n"
            "  - kind: cron\n    name: tick\n    schedule: every 1m\n    handler: skills/01-x.md\n"
        ),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path_, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=path_)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_v311_full_lifecycle(tmp_path, monkeypatch):
    """One end-to-end run touching every v3.11 surface."""
    from lyra_core.bundle import (
        AgentInstaller,
        DualUseAuthorizationError,
        FetchSpec,
        MarketplaceFetcher,
        MarketplaceKey,
        MarketplaceRegistry,
        SourceBundle,
        global_index,
        global_installed_registry,
        list_exporters,
        reset_global_index,
        reset_global_installed_registry,
        resolve_exporter,
        sign_archive,
        uninstall_bundle,
        verify_attestation,
    )
    from lyra_core.cron import RoutineDaemon
    from lyra_core.cron.routines import RoutineRegistry
    from lyra_core.meta import ScalingAxes
    from lyra_core.teams import LeadSession, TeammateSpec

    # Reset global singletons.
    reset_global_index()
    reset_global_installed_registry(path=tmp_path / "installed.json")

    try:
        # --- 1. Build + publish a dual-use bundle ---------------------
        archive = _build_dual_use_bundle_tar()
        secret = b"e2e-marketplace-secret"
        key = MarketplaceKey(fingerprint="e2e-key-v1", secret=secret)
        sig = sign_archive(archive, key)
        marketplace = MarketplaceRegistry()
        marketplace.trust("e2e-mkt", key)

        # --- 2. Fetch with mocked URL fetcher -------------------------
        fetcher = MarketplaceFetcher(
            registry=marketplace,
            cache_root=tmp_path / "cache",
            fetch_url=lambda url: archive,
        )
        fetched = fetcher.fetch(FetchSpec(
            url="https://e2e.example.com/bundle.tar.gz",
            expected_signature=sig,
            marketplace="e2e-mkt",
        ))
        assert fetched.bundle.manifest.name == "e2e-bundle"
        assert fetched.bundle.manifest.dual_use is True
        assert len(fetched.bundle.routines) == 1
        assert len(marketplace.sbom_log) == 1

        # --- 3. Install — dual-use blocks without auth ----------------
        installer = AgentInstaller(bundle=fetched.bundle)
        with pytest.raises(DualUseAuthorizationError):
            installer.install(target_dir=tmp_path / "installed")

        # --- 4. Install with authorization + routine registry ---------
        routine_reg = RoutineRegistry()
        installer = AgentInstaller(
            bundle=fetched.bundle,
            routine_registry=routine_reg,
        )
        target = tmp_path / "installed"
        attestation = installer.install(
            target_dir=target,
            allow_dual_use=True,
            authorized_by="e2e-test",
        )
        assert attestation.dual_use is True
        assert attestation.authorized_by == "e2e-test"
        assert attestation.smoke_eval_pass_rate >= 0.95
        assert verify_attestation(attestation) is True
        # Routine registered.
        assert "e2e-bundle.tick" in routine_reg.routines
        # Coverage auto-populated.
        cov = global_index().get("e2e")
        assert cov.eval_count >= 12

        # --- 5. List from the installed-registry ----------------------
        installed = global_installed_registry().all()
        assert any(r.bundle_name == "e2e-bundle" for r in installed)

        # --- 6. Drive the routine daemon for one tick -----------------
        from datetime import datetime, timedelta, timezone

        class _Clock:
            def __init__(self):
                self.now = datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc)

            def __call__(self):
                return self.now

            def advance(self, **kwargs):
                self.now += timedelta(**kwargs)

        clock = _Clock()
        daemon = RoutineDaemon(registry=routine_reg, clock=clock)
        daemon.tick_once()  # seeds schedule
        clock.advance(minutes=2)
        fired = daemon.tick_once()
        assert fired == 1

        # --- 7. Spawn an Agent Teams runtime + run a task -------------
        team_dir = tmp_path / "teams"
        executor_calls: list = []

        def stub_exec(spec, body):
            executor_calls.append((spec.name, body))
            return f"<{spec.name}>{body[:60]}</{spec.name}>"

        lead = LeadSession.create(
            team_name="e2e-team",
            team_dir=team_dir,
            executor=stub_exec,
        )
        lead.spawn(TeammateSpec(name="alice"))
        lead.spawn(TeammateSpec(name="bob"))
        a_id = lead.add_task("review module A", assign="alice")
        b_id = lead.add_task(
            "review module B after A", assign="bob", depends_on=[a_id]
        )
        completed = lead.run_until_idle(timeout_s=2.0)
        assert completed == 2
        assert lead.tasks.summary().completed == 2
        report = lead.shutdown()
        assert report.completed == 2

        # --- 8. Read scaling-axes recommendation ----------------------
        axes = ScalingAxes()
        axes.record_pretrain(model="claude-opus", param_b=200.0, quality=0.9)
        axes.record_ttc(max_samples=4, verifier_count=cov.verifier_count, avg_pass_rate=cov.pass_rate_30d)
        axes.record_memory(context_tokens=200_000, tier_count=3, retrieval_score=0.9)
        axes.record_tool_use(native_count=12, mcp_server_count=8, avg_success_rate=0.95)
        positions = axes.snapshot()
        assert len(positions) == 4
        best = axes.best_lever()
        assert best.axis in {"pretrain", "ttc", "memory", "tool_use"}

        # --- 9. Export to every cross-harness target ------------------
        for export_target in list_exporters():
            out = tmp_path / f"export-{export_target}"
            manifest = resolve_exporter(export_target).export(
                fetched.bundle, target=out
            )
            assert manifest.files, f"{export_target} produced no files"

        # --- 10. Uninstall — re-verify attestation, drop registry -----
        removed = uninstall_bundle(
            bundle_hash=attestation.bundle_hash,
            target_dir=target,
        )
        assert removed.bundle_name == "e2e-bundle"
        assert not target.exists()
        assert (
            global_installed_registry().find(
                bundle_hash=attestation.bundle_hash, target_dir=str(target)
            )
            is None
        )
    finally:
        reset_global_index()
        reset_global_installed_registry()
