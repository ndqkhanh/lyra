"""Tests for bundle routines parsing + auto-registration into Lyra v3.7 cron."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.bundle import (
    AgentInstaller,
    RoutineSpec,
    SourceBundle,
)
from lyra_core.cron.routines import (
    CronTrigger,
    GitHubWebhookTrigger,
    HttpApiTrigger,
    RoutineRegistry,
)


# ---- helpers ----------------------------------------------------------


def _write_bundle(
    root: Path,
    *,
    name: str = "rt-test",
    routines_yaml: str = "",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "persona.md").write_text("persona\n", encoding="utf-8")
    (root / "MEMORY.md").write_text("seed\n", encoding="utf-8")
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
name: {name}
version: 0.1.0
description: routines test
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
  domain: rt
  command: pytest -q
  budget_seconds: 30
{routines_yaml}
"""
    (root / "bundle.yaml").write_text(manifest, encoding="utf-8")
    return root


# ---- bundle.routines parsing ----------------------------------------


def test_bundle_without_routines_section(tmp_path):
    root = _write_bundle(tmp_path / "b")
    b = SourceBundle.load(root)
    assert b.routines == ()


def test_bundle_loads_cron_routine(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        routines_yaml="""routines:
  - kind: cron
    name: weekly
    schedule: "0 9 * * MON"
    handler: skills/01-x.md
""",
    )
    b = SourceBundle.load(root)
    assert len(b.routines) == 1
    r = b.routines[0]
    assert r.kind == "cron"
    assert r.name == "weekly"
    assert r.schedule == "0 9 * * MON"
    assert r.handler == "skills/01-x.md"


def test_bundle_loads_webhook_routine(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        routines_yaml="""routines:
  - kind: webhook
    name: on-push
    handler: skills/02-y.md
    repo: lyra-org/lyra
    events: push
""",
    )
    b = SourceBundle.load(root)
    assert len(b.routines) == 1
    assert b.routines[0].kind == "webhook"
    assert b.routines[0].repo == "lyra-org/lyra"
    assert b.routines[0].events == ("push",)


def test_bundle_loads_api_routine(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        routines_yaml="""routines:
  - kind: api
    name: manual
    handler: skills/01-x.md
    path: /trigger
""",
    )
    b = SourceBundle.load(root)
    assert len(b.routines) == 1
    assert b.routines[0].kind == "api"
    assert b.routines[0].path == "/trigger"


def test_bundle_skips_invalid_routine_entries(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        routines_yaml="""routines:
  - kind: cron
    name: ok
    schedule: "0 0 * * *"
    handler: skills/01-x.md
  - kind: explode
    name: bad-kind
    handler: skills/01-x.md
  - kind: cron
    handler: skills/01-x.md
""",
    )
    b = SourceBundle.load(root)
    # Only the valid cron entry is kept.
    assert len(b.routines) == 1
    assert b.routines[0].name == "ok"


# ---- AgentInstaller routine registration ---------------------------


def test_installer_no_registry_skips_routines(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        routines_yaml="""routines:
  - kind: cron
    name: weekly
    schedule: "0 9 * * MON"
    handler: skills/01-x.md
""",
    )
    bundle = SourceBundle.load(root)
    inst = AgentInstaller(bundle=bundle)
    inst.install(target_dir=tmp_path / "out")
    assert inst.last_registered_routines == ()


def test_installer_registers_cron_routine(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        name="open-fang-test",
        routines_yaml="""routines:
  - kind: cron
    name: weekly-feed
    schedule: "0 9 * * MON"
    handler: skills/01-x.md
""",
    )
    bundle = SourceBundle.load(root)
    reg = RoutineRegistry()
    inst = AgentInstaller(bundle=bundle, routine_registry=reg)
    inst.install(target_dir=tmp_path / "out")
    assert "open-fang-test.weekly-feed" in reg.routines
    routine = reg.routines["open-fang-test.weekly-feed"]
    assert isinstance(routine.trigger, CronTrigger)
    assert routine.trigger.expression == "0 9 * * MON"


def test_installer_registers_multiple_routines(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        name="polaris-test",
        routines_yaml="""routines:
  - kind: cron
    name: tick
    schedule: "*/15 * * * *"
    handler: skills/01-x.md
  - kind: webhook
    name: on-push
    handler: skills/02-y.md
    repo: org/repo
    events: push
""",
    )
    bundle = SourceBundle.load(root)
    reg = RoutineRegistry()
    inst = AgentInstaller(bundle=bundle, routine_registry=reg)
    inst.install(target_dir=tmp_path / "out")
    assert "polaris-test.tick" in reg.routines
    assert "polaris-test.on-push" in reg.routines
    assert isinstance(reg.routines["polaris-test.on-push"].trigger, GitHubWebhookTrigger)


def test_installer_registers_api_routine(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        name="aegis",
        routines_yaml="""routines:
  - kind: api
    name: manual-trigger
    handler: skills/01-x.md
    path: /aegis/trigger
""",
    )
    bundle = SourceBundle.load(root)
    reg = RoutineRegistry()
    inst = AgentInstaller(bundle=bundle, routine_registry=reg)
    inst.install(target_dir=tmp_path / "out")
    assert "aegis.manual-trigger" in reg.routines
    assert isinstance(reg.routines["aegis.manual-trigger"].trigger, HttpApiTrigger)
    assert reg.routines["aegis.manual-trigger"].trigger.path == "/aegis/trigger"


def test_installer_workflow_callable_dispatches(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        name="tw",
        routines_yaml="""routines:
  - kind: cron
    name: feed
    schedule: "0 0 * * *"
    handler: skills/01-x.md
""",
    )
    bundle = SourceBundle.load(root)
    reg = RoutineRegistry()
    inst = AgentInstaller(bundle=bundle, routine_registry=reg)
    inst.install(target_dir=tmp_path / "out")
    invocation = reg.fire_cron("tw.feed", payload={"trigger": "manual"})
    assert invocation.routine_name == "tw.feed"
    # Workflow returned the stub envelope.
    # (RoutineRegistry doesn't return the workflow result on
    # invocation; we verify the workflow id is in the registry.)
    assert "tw.feed" in reg.workflows


def test_installer_idempotent_routine_registration(tmp_path):
    root = _write_bundle(
        tmp_path / "b",
        name="idem",
        routines_yaml="""routines:
  - kind: cron
    name: x
    schedule: "0 0 * * *"
    handler: skills/01-x.md
""",
    )
    bundle = SourceBundle.load(root)
    reg = RoutineRegistry()
    inst = AgentInstaller(bundle=bundle, routine_registry=reg)
    inst.install(target_dir=tmp_path / "out")
    # Second install (different target dir to avoid attestation
    # short-circuit) should not raise on duplicate-routine.
    inst2 = AgentInstaller(bundle=bundle, routine_registry=reg)
    inst2.install(target_dir=tmp_path / "out2")
    assert "idem.x" in reg.routines
    assert len([r for r in reg.routines if r.endswith(".x")]) == 1


def test_installer_user_workflow_overrides_stub(tmp_path):
    """When the caller pre-registers a workflow at the canonical
    id, the installer leaves it alone."""
    root = _write_bundle(
        tmp_path / "b",
        name="user-wf",
        routines_yaml="""routines:
  - kind: cron
    name: feed
    schedule: "0 0 * * *"
    handler: skills/01-x.md
""",
    )
    bundle = SourceBundle.load(root)
    reg = RoutineRegistry()
    user_called = []

    def user_workflow(routine_name: str, payload):
        user_called.append((routine_name, payload))
        return {"from": "user"}

    reg.register_workflow("user-wf.feed", user_workflow)
    AgentInstaller(bundle=bundle, routine_registry=reg).install(target_dir=tmp_path / "out")
    assert reg.workflows["user-wf.feed"] is user_workflow
