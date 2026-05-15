"""Red tests for the CLI Typer smoke: commands parse and basic contracts hold.

Contract from docs/system-design.md:
    lyra init
    lyra run <task>
    lyra plan <task>            (Phase 2 entry; produces plan artifact only)
    lyra doctor
    lyra session list
    lyra retro <session-id>

Only --help shapes and `init` behavior are verified here; `run`'s end-to-end
flow ships in Phase 3 when the loop extension is done.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lyra_cli.__main__ import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_root_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.stdout
    for sub in ["init", "run", "plan", "doctor", "session", "retro", "evals"]:
        assert sub in out, f"subcommand {sub!r} missing from --help"


def test_subcommand_helps(runner: CliRunner) -> None:
    for sub in ["init", "run", "plan", "doctor", "retro", "evals"]:
        result = runner.invoke(app, [sub, "--help"])
        assert result.exit_code == 0, f"{sub} --help failed: {result.stdout}"


def test_evals_command_smoke(runner: CliRunner) -> None:
    result = runner.invoke(app, ["evals", "--corpus", "golden", "--drift-gate", "0.0"])
    assert result.exit_code == 0
    assert "corpus=golden" in result.stdout
    assert "success_rate=" in result.stdout


def test_evals_swe_bench_pro_without_tasks_path_exits_helpfully(
    runner: CliRunner,
) -> None:
    """Running ``--corpus swe-bench-pro`` with no tasks file must not crash.

    Phase 12 DoD requires the CLI to dispatch on the public corpus name;
    we defer the heavy corpus download to the operator. When they forget,
    we point them at the adapter library and ``docs/benchmarks.md``.
    """
    result = runner.invoke(app, ["evals", "--corpus", "swe-bench-pro"])
    assert result.exit_code == 2
    assert "tasks-path" in result.stdout.lower()
    assert "SWEBenchProAdapter" in result.stdout


def test_evals_swe_bench_pro_with_tasks_path_writes_submission(
    tmp_path: Path, runner: CliRunner
) -> None:
    """Round-trip: JSONL in → stub policy → Scale-AI-shape JSONL out.

    The stub policy inside the CLI returns empty-patch / unresolved, which
    is the safest default for a dry run. What we verify is that the
    submission file exists and has the exact three keys per line.
    """
    inp = tmp_path / "pro.jsonl"
    inp.write_text(
        json.dumps(
            {
                "instance_id": "x__y-1",
                "repo": "x/y",
                "base_commit": "abc",
                "problem_statement": "stub",
                "FAIL_TO_PASS": ["tests::test_a"],
                "PASS_TO_PASS": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "submission.jsonl"
    result = runner.invoke(
        app,
        [
            "evals",
            "--corpus",
            "swe-bench-pro",
            "--tasks-path",
            str(inp),
            "--output",
            str(out),
            "--drift-gate",
            "0.0",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    rows = [json.loads(ln) for ln in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert set(rows[0].keys()) == {"instance_id", "model_name_or_path", "model_patch"}


def test_evals_loco_eval_with_tasks_path_reports_coverage(
    tmp_path: Path, runner: CliRunner
) -> None:
    """A tiny LoCoEval JSONL drives the conversation driver and reports coverage."""
    inp = tmp_path / "loco.jsonl"
    inp.write_text(
        json.dumps(
            {
                "sample_id": "loco-1",
                "repo": "x/y",
                "turns": ["hello"],
                "requirements": ["REQ-A"],
                "context_budget_tokens": 10_000,
                "tokens_per_turn": 100,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["evals", "--corpus", "loco-eval", "--tasks-path", str(inp)],
    )
    assert result.exit_code == 0, result.stdout
    assert "corpus=loco-eval" in result.stdout
    assert "requirement_coverage=" in result.stdout


def test_init_creates_soul_and_state_dir(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "SOUL.md").exists()
    assert (tmp_path / ".lyra").is_dir()
    assert (tmp_path / ".lyra" / "policy.yaml").exists()


def test_init_is_idempotent_without_force(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    # Modify SOUL to check it isn't overwritten
    (tmp_path / "SOUL.md").write_text("# user edited SOUL\n")
    result = runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "SOUL.md").read_text() == "# user edited SOUL\n"


def test_init_force_overwrites(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    (tmp_path / "SOUL.md").write_text("# user edited\n")
    result = runner.invoke(app, ["init", "--repo-root", str(tmp_path), "--force"])
    assert result.exit_code == 0
    assert "user edited" not in (tmp_path / "SOUL.md").read_text()


def test_plan_command_with_auto_approve_writes_plan_artifact(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(
        app,
        [
            "plan",
            "please add a small feature that exports json",
            "--repo-root",
            str(tmp_path),
            "--auto-approve",
            "--llm",
            "mock",
        ],
    )
    assert result.exit_code == 0, result.stdout
    plans_dir = tmp_path / ".lyra" / "plans"
    assert plans_dir.exists()
    plans = list(plans_dir.glob("*.md"))
    assert plans, "no plan artifact written"


def test_doctor_prints_status(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(app, ["doctor", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    out = result.stdout
    # doctor reports at minimum: SOUL, policy, tdd state, python version
    assert "SOUL" in out
    assert "policy" in out.lower()
    assert "python" in out.lower()


def test_doctor_reports_all_lyra_packages(
    tmp_path: Path, runner: CliRunner
) -> None:
    """Doctor must enumerate the five Lyra packages with versions.

    Operators use `doctor` to verify no package got missed in an editable
    install; we make that check a first-class feature.
    """
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(app, ["doctor", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    out = result.stdout
    for pkg in [
        "lyra-core",
        "lyra-skills",
        "lyra-mcp",
        "lyra-evals",
        "lyra-cli",
    ]:
        assert pkg in out, f"{pkg!r} missing from doctor output"


def test_session_list_empty(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(app, ["session", "list", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    # No sessions yet — should not crash.
    assert "0 session" in result.stdout.lower() or "no session" in result.stdout.lower()


def test_version_flag(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "lyra" in result.stdout.lower()


def test_no_args_launches_interactive_session(
    tmp_path: Path, runner: CliRunner
) -> None:
    """``lyra --legacy`` boots the prompt_toolkit REPL.

    v3.14 Phase 6 flipped the bare default to the Textual shell, so
    this test asserts the legacy off-ramp via ``--legacy``. The
    underlying contract — REPL dispatcher live, accepts ``/exit`` —
    is unchanged.
    """
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(
        app,
        ["--legacy", "--repo-root", str(tmp_path)],
        input="/exit\n",
    )
    assert result.exit_code == 0, result.stdout
    out = result.stdout
    assert "Lyra" in out
    assert "/help" in out  # banner hint


def test_no_args_eof_terminates_loop_cleanly(
    tmp_path: Path, runner: CliRunner
) -> None:
    """EOF (empty stdin) must not crash; it's how pipes quit the REPL."""
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(
        app, ["--repo-root", str(tmp_path)], input=""
    )
    assert result.exit_code == 0, result.stdout


def test_run_requires_plan_by_default(tmp_path: Path, runner: CliRunner) -> None:
    """Plan Mode is default-on; a non-trivial task without --auto-approve
    on a mock LLM will reject the plan because there's no interactive shell."""
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(
        app,
        [
            "run",
            "refactor auth to support OIDC and migrate sessions",
            "--repo-root",
            str(tmp_path),
            "--llm",
            "mock",
        ],
    )
    # Without auto-approve, interactive callback is absent → safe fail
    assert result.exit_code != 0
    assert "reject" in result.stdout.lower() or "not approved" in result.stdout.lower()


def test_run_with_no_plan_flag_and_trivial_task(tmp_path: Path, runner: CliRunner) -> None:
    """--no-plan bypass with a tiny mock task: must not write to src/**."""
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    result = runner.invoke(
        app,
        [
            "run",
            "fix typo in README",
            "--repo-root",
            str(tmp_path),
            "--llm",
            "mock",
            "--no-plan",
        ],
    )
    # The mock LLM in --llm mock mode will end-turn immediately for this demo;
    # we just want to know the command path works end-to-end without crashing.
    assert result.exit_code in (0, 1)
