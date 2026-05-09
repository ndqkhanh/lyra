"""Phase 12 — Red tests for the SWE-bench Pro adapter.

We do NOT depend on Scale AI's harness being installed. Instead we prove
that our adapter:

1. Loads Pro tasks from a canonical JSONL into a stable ``PublicBenchmarkTask``
   dataclass.
2. Drives those tasks through our existing ``EvalRunner`` contract.
3. Emits a *submission file* whose shape is byte-for-byte what Scale AI's
   evaluator ingests: one JSON object per line, exactly three keys
   (``instance_id``, ``model_name_or_path``, ``model_patch``), no extras.
4. Surfaces a ``resolved`` verdict compatible with Scale AI's
   ``{resolved, unresolved, error}`` bucketing when an oracle is supplied.

Why this matters: SWE-bench Verified is contaminated (45.9% vs 80.9% for
the same model, see ``docs/roadmap-v1.5-v2.md`` §0.1). Pro is the public
scoreboard Lyra must score on. The adapter is the bridge between
our generic runner and the public harness.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_evals.adapters.swe_bench_pro import (
    PublicBenchmarkTask,
    SWEBenchProAdapter,
    load_swe_bench_pro,
    write_submission,
)
from lyra_evals.runner import EvalRunner, TaskResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SAMPLE_TASK = {
    "instance_id": "pytest-dev__pytest-1234",
    "repo": "pytest-dev/pytest",
    "base_commit": "abc1234",
    "problem_statement": "AssertionRewriter crashes on walrus in comprehension",
    "hints_text": "",
    "created_at": "2026-01-15T12:00:00Z",
    "version": "8.3",
    "FAIL_TO_PASS": ["testing/test_assertrewrite.py::test_walrus_comp"],
    "PASS_TO_PASS": [],
    "environment_setup_commit": "def5678",
}

_SAMPLE_PATCH = (
    "diff --git a/src/_pytest/assertion/rewrite.py "
    "b/src/_pytest/assertion/rewrite.py\n"
    "--- a/src/_pytest/assertion/rewrite.py\n"
    "+++ b/src/_pytest/assertion/rewrite.py\n"
    "@@ -1,1 +1,2 @@\n"
    "-# placeholder\n"
    "+# fixed\n"
    "+# patched\n"
)


@pytest.fixture
def pro_jsonl(tmp_path: Path) -> Path:
    """One-line Pro JSONL on disk."""
    target = tmp_path / "swe_bench_pro_mini.jsonl"
    target.write_text(json.dumps(_SAMPLE_TASK) + "\n", encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# 1. PublicBenchmarkTask shape
# ---------------------------------------------------------------------------


def test_public_benchmark_task_preserves_canonical_keys(pro_jsonl: Path) -> None:
    """The dataclass must round-trip the canonical Pro fields, unchanged.

    Scale AI's harness keys on ``instance_id``; ``FAIL_TO_PASS`` and
    ``PASS_TO_PASS`` drive verdict evaluation. Losing any of these in
    translation breaks byte-level compatibility.
    """
    tasks = load_swe_bench_pro(pro_jsonl)
    assert len(tasks) == 1
    task = tasks[0]
    assert isinstance(task, PublicBenchmarkTask)
    assert task.instance_id == _SAMPLE_TASK["instance_id"]
    assert task.repo == _SAMPLE_TASK["repo"]
    assert task.base_commit == _SAMPLE_TASK["base_commit"]
    assert task.fail_to_pass == tuple(_SAMPLE_TASK["FAIL_TO_PASS"])
    assert task.pass_to_pass == tuple(_SAMPLE_TASK["PASS_TO_PASS"])


def test_public_benchmark_task_limit_honors_budget(tmp_path: Path) -> None:
    """``--budget 50`` must stop loading at 50 lines even if the file is bigger."""
    huge = tmp_path / "huge.jsonl"
    with huge.open("w", encoding="utf-8") as fh:
        for i in range(200):
            row = dict(_SAMPLE_TASK)
            row["instance_id"] = f"repo__issue-{i}"
            fh.write(json.dumps(row) + "\n")
    tasks = load_swe_bench_pro(huge, limit=50)
    assert len(tasks) == 50
    assert tasks[0].instance_id == "repo__issue-0"
    assert tasks[-1].instance_id == "repo__issue-49"


# ---------------------------------------------------------------------------
# 2. Adapter runs under EvalRunner
# ---------------------------------------------------------------------------


def test_adapter_wraps_eval_runner_and_produces_predictions(
    pro_jsonl: Path,
) -> None:
    """A Pro task must run under our ``EvalRunner`` and produce a patch + verdict.

    The adapter gives our existing ``Policy`` contract a ``PublicBenchmarkTask``
    via the ``Task`` bridge; the inner policy returns a ``(patch, resolved)``
    pair which the adapter stores on the result for later submission.
    """
    tasks = load_swe_bench_pro(pro_jsonl)
    adapter = SWEBenchProAdapter(model_name_or_path="lyra/mock-0.2.0")

    def stub_policy(task: PublicBenchmarkTask) -> tuple[str, bool]:
        assert task.instance_id == _SAMPLE_TASK["instance_id"]
        return (_SAMPLE_PATCH, True)

    runner = EvalRunner(policy=adapter.policy(stub_policy), drift_gate=None)
    report = runner.run([adapter.as_generic_task(t) for t in tasks])

    assert report.total == 1
    assert report.passed == 1
    predictions = adapter.predictions()
    assert len(predictions) == 1
    assert predictions[0]["instance_id"] == _SAMPLE_TASK["instance_id"]
    assert predictions[0]["model_name_or_path"] == "lyra/mock-0.2.0"
    assert predictions[0]["model_patch"] == _SAMPLE_PATCH


# ---------------------------------------------------------------------------
# 3. Submission file is byte-level compatible with Scale AI's harness
# ---------------------------------------------------------------------------


def test_submission_file_has_exactly_scale_ai_keys(tmp_path: Path) -> None:
    """Each line MUST have exactly {instance_id, model_name_or_path, model_patch}.

    Extra keys break Scale AI's strict ingestion; missing keys crash the
    verdict pass. We hardcode the key set here so drift across a Pro
    schema change surfaces as a red test, not as a silently-failing run.
    """
    out = tmp_path / "preds.jsonl"
    write_submission(
        out,
        predictions=[
            {
                "instance_id": "a__b-1",
                "model_name_or_path": "lyra",
                "model_patch": _SAMPLE_PATCH,
            },
            {
                "instance_id": "c__d-2",
                "model_name_or_path": "lyra",
                "model_patch": "",
            },
        ],
    )
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        row = json.loads(line)
        assert set(row.keys()) == {
            "instance_id",
            "model_name_or_path",
            "model_patch",
        }, f"unexpected keys in {row!r}"
        assert isinstance(row["instance_id"], str) and row["instance_id"]
        assert isinstance(row["model_name_or_path"], str)
        assert isinstance(row["model_patch"], str)


def test_submission_rejects_extra_keys(tmp_path: Path) -> None:
    """Defensive: if a caller passes a prediction with extra keys we must raise.

    This is the sharp end of 'byte-for-byte compatible': silently stripping
    fields would hide adapter bugs, and silently passing them would poison
    the submission.
    """
    out = tmp_path / "preds.jsonl"
    with pytest.raises(ValueError, match="unexpected keys"):
        write_submission(
            out,
            predictions=[
                {
                    "instance_id": "a__b-1",
                    "model_name_or_path": "lyra",
                    "model_patch": _SAMPLE_PATCH,
                    "confidence": 0.7,  # extra key — must be rejected
                },
            ],
        )


# ---------------------------------------------------------------------------
# 4. End-to-end: EvalRunner result → submission file round-trip
# ---------------------------------------------------------------------------


def test_adapter_submission_round_trip(pro_jsonl: Path, tmp_path: Path) -> None:
    """``write_submission(adapter.predictions())`` produces a valid Pro file.

    This is the full chain: load Pro JSONL → run via EvalRunner → emit
    submission JSONL. Any Pro-submission run in CI must traverse this
    path, so we pin it as a test.
    """
    tasks = load_swe_bench_pro(pro_jsonl)
    adapter = SWEBenchProAdapter(model_name_or_path="lyra/mock")

    def stub_policy(_t: PublicBenchmarkTask) -> tuple[str, bool]:
        return (_SAMPLE_PATCH, True)

    runner = EvalRunner(policy=adapter.policy(stub_policy), drift_gate=None)
    runner.run([adapter.as_generic_task(t) for t in tasks])

    out = tmp_path / "submission.jsonl"
    write_submission(out, adapter.predictions())

    reloaded = [
        json.loads(line)
        for line in out.read_text(encoding="utf-8").splitlines()
    ]
    assert len(reloaded) == 1
    assert reloaded[0]["instance_id"] == _SAMPLE_TASK["instance_id"]


def test_unresolved_task_result_flows_through_to_report() -> None:
    """A failing task must register as ``passed=False`` with reason captured.

    The runner's drift-gate semantics (``success_rate < gate``) depend on
    this; a broken adapter that silently coerces unresolved → resolved
    would hide regressions on the Pro corpus.
    """
    task = PublicBenchmarkTask(
        instance_id="x__y-1",
        repo="x/y",
        base_commit="deadbee",
        problem_statement="stub",
        fail_to_pass=("tests/test_x.py::test_y",),
        pass_to_pass=(),
    )
    adapter = SWEBenchProAdapter(model_name_or_path="lyra")

    def policy(_t: PublicBenchmarkTask) -> tuple[str, bool]:
        return ("", False)

    result: TaskResult = adapter.policy(policy)(adapter.as_generic_task(task))
    assert result.passed is False
    assert result.task_id == "x__y-1"
    assert "unresolved" in result.reason.lower()
