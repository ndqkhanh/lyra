"""Tests for harness_core.render — Markdown / JSON / structured-log output."""
from __future__ import annotations

import json

import pytest

from harness_core.eval_runner import (
    EvalCase,
    EvalResult,
    EvalRun,
    EvalRunner,
    EvalSuite,
)
from harness_core.provenance import WitnessLattice
from harness_core.render import (
    eval_run_to_json,
    eval_run_to_markdown,
    structured_log_lines,
    trace_to_json,
    trace_to_markdown,
    witness_lattice_to_json,
    witness_lattice_to_markdown,
)
from harness_core.replay import ReplayEventKind, TraceBuilder


# --- Trace renderers ---------------------------------------------------


def _build_demo_trace():
    builder = TraceBuilder(trace_id="incident-2026-05-09")
    builder.add_event(
        kind=ReplayEventKind.RETRIEVAL,
        issued_by="hipporag", timestamp=1.0,
        payload={"query": "X", "doc_ids": ["d1", "d2"]},
        event_id="evt-1",
    )
    builder.add_event(
        kind=ReplayEventKind.AGENT_DECISION,
        issued_by="research-agent", timestamp=2.0,
        payload={"action": "answer"},
        event_id="evt-2",
        namespace_id="proj-A",
    )
    builder.add_event(
        kind=ReplayEventKind.HUMAN_APPROVAL,
        issued_by="user:alice", timestamp=3.0,
        payload={"approved": True},
        event_id="evt-3",
    )
    return builder.build()


class TestTraceToMarkdown:
    def test_basic(self):
        trace = _build_demo_trace()
        md = trace_to_markdown(trace)
        assert "# Trace: incident-2026-05-09" in md
        assert "**3** events" in md
        assert "[retrieval]" in md
        assert "[agent_decision]" in md
        assert "[human_approval]" in md

    def test_custom_title(self):
        trace = _build_demo_trace()
        md = trace_to_markdown(trace, title="Custom Title")
        assert "# Custom Title" in md

    def test_empty_trace(self):
        from harness_core.replay import Trace
        empty = Trace(trace_id="empty")
        md = trace_to_markdown(empty)
        assert "_No events._" in md

    def test_show_payloads(self):
        trace = _build_demo_trace()
        md = trace_to_markdown(trace, show_payloads=True)
        assert "query=" in md or "action=" in md

    def test_hide_payloads(self):
        trace = _build_demo_trace()
        md = trace_to_markdown(trace, show_payloads=False)
        # Payload preview shouldn't appear.
        assert "query='X'" not in md

    def test_namespace_shown(self):
        trace = _build_demo_trace()
        md = trace_to_markdown(trace)
        assert "ns: `proj-A`" in md

    def test_truncates_long_payload(self):
        builder = TraceBuilder(trace_id="t")
        long_text = "x" * 1000
        builder.add_event(
            kind=ReplayEventKind.RETRIEVAL, issued_by="r",
            timestamp=1.0, payload={"data": long_text},
        )
        md = trace_to_markdown(builder.build(), max_payload_chars=100)
        assert "..." in md
        # Total payload section should be under (100 chars + small overhead).
        # We just confirm it didn't render the full 1000-char string.
        assert long_text not in md


class TestTraceToJson:
    def test_basic_structure(self):
        trace = _build_demo_trace()
        out = trace_to_json(trace)
        assert out["trace_id"] == "incident-2026-05-09"
        assert "stats" in out
        assert len(out["events"]) == 3

    def test_event_fields(self):
        trace = _build_demo_trace()
        out = trace_to_json(trace)
        first = out["events"][0]
        assert first["event_id"] == "evt-1"
        assert first["kind"] == "retrieval"
        assert first["issued_by"] == "hipporag"

    def test_json_serialisable(self):
        trace = _build_demo_trace()
        out = trace_to_json(trace)
        # Must be json.dumps-able.
        s = json.dumps(out)
        round_trip = json.loads(s)
        assert round_trip["trace_id"] == trace.trace_id


class TestStructuredLogLines:
    def test_one_line_per_event(self):
        trace = _build_demo_trace()
        lines = structured_log_lines(trace)
        assert len(lines) == 3

    def test_each_line_is_json(self):
        trace = _build_demo_trace()
        for line in structured_log_lines(trace):
            obj = json.loads(line)
            assert "trace_id" in obj
            assert "event_id" in obj
            assert "kind" in obj

    def test_extra_fields_merged(self):
        trace = _build_demo_trace()
        lines = structured_log_lines(
            trace, extra_fields={"service": "polaris", "env": "prod"},
        )
        for line in lines:
            obj = json.loads(line)
            assert obj["service"] == "polaris"
            assert obj["env"] == "prod"


# --- WitnessLattice renderers ----------------------------------------


def _build_demo_lattice():
    lattice = WitnessLattice()
    retrieval = lattice.record_retrieval(
        retriever_name="hipporag",
        query="who directed Casablanca",
        doc_ids=["d1"],
    )
    inference = lattice.record_inference(
        agent_id="research-agent",
        claim="Bob Curtiz directed Casablanca",
        supporting=[retrieval.witness_id],
    )
    return lattice, retrieval, inference


class TestWitnessLatticeToMarkdown:
    def test_full_lattice(self):
        lattice, _, _ = _build_demo_lattice()
        md = witness_lattice_to_markdown(lattice)
        assert "# Provenance Lattice" in md
        assert "**2** witnesses" in md
        assert "retrieval" in md
        assert "inference" in md

    def test_focused_witness(self):
        lattice, _, inference = _build_demo_lattice()
        md = witness_lattice_to_markdown(
            lattice, focus_witness_id=inference.witness_id,
        )
        assert "Provenance chain for" in md
        # Both inference + parent retrieval should appear.
        assert "[inference]" in md
        assert "[retrieval]" in md

    def test_unknown_focus_witness(self):
        lattice, _, _ = _build_demo_lattice()
        md = witness_lattice_to_markdown(lattice, focus_witness_id="missing")
        assert "not found" in md

    def test_empty_lattice(self):
        empty = WitnessLattice()
        md = witness_lattice_to_markdown(empty)
        assert "_No witnesses._" in md


class TestWitnessLatticeToJson:
    def test_basic(self):
        lattice, _, _ = _build_demo_lattice()
        out = witness_lattice_to_json(lattice)
        assert out["stats"]["total"] == 2
        assert len(out["witnesses"]) == 2

    def test_witness_fields(self):
        lattice, _, _ = _build_demo_lattice()
        out = witness_lattice_to_json(lattice)
        for w in out["witnesses"]:
            assert "witness_id" in w
            assert "kind" in w
            assert "parent_witnesses" in w

    def test_json_serialisable(self):
        lattice, _, _ = _build_demo_lattice()
        out = witness_lattice_to_json(lattice)
        json.dumps(out)


# --- EvalRun renderers ------------------------------------------------


def _build_demo_eval_run():
    suite = EvalSuite(
        suite_id="multi-hop-bench",
        cases=(
            EvalCase(case_id="q1", inputs={"q": "easy"}, expected_output="A"),
            EvalCase(case_id="q2", inputs={"q": "hard"}, expected_output="B"),
        ),
    )

    def program(inputs):
        return {"easy": "A", "hard": "WRONG"}[inputs["q"]]

    runner = EvalRunner(
        program=program,
        eval_fn=lambda c, o: 1.0 if o == c.expected_output else 0.0,
    )
    return runner.run(suite)


class TestEvalRunToMarkdown:
    def test_basic(self):
        run = _build_demo_eval_run()
        md = eval_run_to_markdown(run)
        assert "# Eval Run: multi-hop-bench" in md
        assert "**Pass rate**" in md
        assert "50.0%" in md  # 1/2 passed
        assert "✅" in md
        assert "❌" in md

    def test_show_failed_only(self):
        run = _build_demo_eval_run()
        md = eval_run_to_markdown(run, show_failed_only=True)
        # Only the failed case (q2) shown.
        assert "q2" in md
        assert "Failed Cases" in md

    def test_all_passed_message(self):
        suite = EvalSuite(
            suite_id="x",
            cases=(EvalCase(case_id="c1", inputs={"q": "x"}, expected_output="x"),),
        )
        runner = EvalRunner(
            program=lambda i: "x",
            eval_fn=lambda c, o: 1.0,
        )
        run = runner.run(suite)
        md = eval_run_to_markdown(run, show_failed_only=True)
        assert "All cases passed" in md


class TestEvalRunToJson:
    def test_basic_structure(self):
        run = _build_demo_eval_run()
        out = eval_run_to_json(run)
        assert out["suite_id"] == "multi-hop-bench"
        assert "summary" in out
        assert out["summary"]["pass_rate"] == 0.5
        assert len(out["results"]) == 2

    def test_result_fields(self):
        run = _build_demo_eval_run()
        out = eval_run_to_json(run)
        for r in out["results"]:
            assert "case_id" in r
            assert "score" in r
            assert "passed" in r

    def test_json_serialisable(self):
        run = _build_demo_eval_run()
        out = eval_run_to_json(run)
        json.dumps(out)


# --- Composability tests -----------------------------------------------


class TestComposability:
    """Renderers should compose: a project can build a complete report by
    concatenating Trace + Lattice + EvalRun markdown sections."""

    def test_combined_markdown_report(self):
        trace = _build_demo_trace()
        lattice, _, _ = _build_demo_lattice()
        run = _build_demo_eval_run()

        report = "\n\n".join([
            "# Daily Report\n",
            trace_to_markdown(trace, title="Today's Trace"),
            witness_lattice_to_markdown(lattice, title="Provenance"),
            eval_run_to_markdown(run, title="Eval Results"),
        ])

        assert "# Daily Report" in report
        assert "# Today's Trace" in report
        assert "# Provenance" in report
        assert "# Eval Results" in report

    def test_combined_json_export(self):
        trace = _build_demo_trace()
        lattice, _, _ = _build_demo_lattice()
        run = _build_demo_eval_run()

        combined = {
            "trace": trace_to_json(trace),
            "provenance": witness_lattice_to_json(lattice),
            "eval_run": eval_run_to_json(run),
        }
        # Single round-trippable JSON document.
        s = json.dumps(combined)
        loaded = json.loads(s)
        assert loaded["trace"]["trace_id"] == trace.trace_id
        assert loaded["eval_run"]["suite_id"] == "multi-hop-bench"
