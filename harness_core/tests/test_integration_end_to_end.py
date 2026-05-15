"""End-to-end integration test — one workflow exercises every major module.

Narrative:

    A user asks a multi-hop research question. The router classifies it,
    a sub-agent dispatches a tool through the guarded tool runtime, the
    cost is tracked, every step is witnessed, the trace is rendered as a
    Markdown report + JSON export, an eval suite scores the run, the
    user's edit to the report is captured for continuous learning,
    a memory consolidation pass compacts old session memory, and a
    skill drift monitor confirms baseline performance.

The test is the one place we assert *composability* — every isolated
unit test confirms its own contract; this confirms they fit together.
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from harness_core.continuous_learning import (
    ContinuousLearner,
    EditRecorder,
)
from harness_core.cost import CostTracker, PricingTable
from harness_core.distributed import Bus
from harness_core.eval_runner import EvalCase, EvalRunner, EvalSuite
from harness_core.evals import BudgetController
from harness_core.memory_consolidation import (
    ConsolidationPolicy,
    MemoryConsolidator,
)
from harness_core.memory_store import MemoryItem, MemoryKind, MemoryStore
from harness_core.messages import ToolCall
from harness_core.provenance import WitnessLattice
from harness_core.render import (
    eval_run_to_json,
    eval_run_to_markdown,
    structured_log_lines,
    trace_to_json,
    trace_to_markdown,
    witness_lattice_to_markdown,
)
from harness_core.replay import TraceBuilder
from harness_core.routing import BELLERouter, QueryType
from harness_core.skill_drift import DriftPolicy, SkillDriftMonitor
from harness_core.tool_runtime import ExponentialBackoff, ToolEngine
from harness_core.tools import Tool, ToolRegistry
from harness_core.verifier import StubPolicyVerifier, VerifierComposer


class _ResearchTool(Tool):
    """Stub research tool — accepts a query, returns a stable answer."""

    name = "research"
    description = "Answer a research question"

    class ArgsModel(BaseModel):
        query: str

    def run(self, args: Any) -> str:
        return f"answer for: {args.query}"


def test_full_stack_workflow():
    # --- Layer 1: shared infrastructure -------------------------------
    lattice = WitnessLattice()
    trace_builder = TraceBuilder(trace_id="incident-2026-05-09")
    cost_tracker = CostTracker(pricing=PricingTable(prices={
        "tool:research": {"input_per_M": 1.0, "output_per_M": 0.0},
    }))
    budget = BudgetController(budget_tokens=1_000_000)
    bus = Bus(namespace="orion-code", lattice=lattice)
    memory = MemoryStore()

    # --- Layer 2: routing --------------------------------------------
    router = BELLERouter()
    decision = router.route(
        "who directed Casablanca and where were they born",
    )
    # Bridge questions are the canonical multi-hop case.
    assert decision.query_type in (
        QueryType.MULTI_HOP_BRIDGE,
        QueryType.FAN_OUT,
        QueryType.SINGLE_HOP,
    )

    # --- Layer 3: tool runtime with all gates ------------------------
    registry = ToolRegistry()
    registry.register(_ResearchTool())
    composer = VerifierComposer(verifiers=[StubPolicyVerifier()])

    engine = ToolEngine(
        registry=registry,
        verifier=composer,
        budget=budget,
        cost_tracker=cost_tracker,
        lattice=lattice,
        trace=trace_builder,
        retry_policy=ExponentialBackoff(max_attempts=3, base_delay=0.0),
        sleep_fn=lambda _: None,
        project="orion-code",
        user_id="alice",
        agent_id="research-agent",
    )

    # Run the tool 3 times — model 3 sub-agent calls during multi-hop.
    executions = []
    for i, hop in enumerate(["who directed Casablanca",
                              "Michael Curtiz birthplace",
                              "Budapest geography"]):
        # Cross-agent broadcast: announce the hop on the bus.
        bus.publish(
            topic="agent.research.hop",
            payload={"hop_index": i, "query": hop},
            issued_by="research-agent",
        )
        ex = engine.execute(
            ToolCall(id=f"call-{i}", name="research", args={"query": hop}),
            estimated_tokens=1000,
        )
        assert ex.succeeded
        executions.append(ex)

    # --- Layer 4: assertions on the audit trail ----------------------
    # Each call: 1 verdict + 1 tool_result witness = 6 total.
    assert lattice.ledger.stats()["total"] >= 6
    # Trace has at least 6 events from the engine + 3 from the bus = 9.
    trace = trace_builder.build()
    assert len(trace.events) >= 6
    # Cost tracker recorded all 3 calls.
    assert len(cost_tracker.all_entries()) == 3
    assert cost_tracker.total(project="orion-code") > 0

    # --- Layer 5: rendering ------------------------------------------
    md_trace = trace_to_markdown(trace, title="Research Trace")
    assert "Research Trace" in md_trace
    md_lattice = witness_lattice_to_markdown(lattice, title="Provenance")
    assert "Provenance" in md_lattice
    json_trace = trace_to_json(trace)
    assert json_trace["trace_id"] == "incident-2026-05-09"
    log_lines = structured_log_lines(
        trace, extra_fields={"service": "orion-code", "env": "test"},
    )
    assert all('"service": "orion-code"' in line for line in log_lines)

    # --- Layer 6: evaluation ----------------------------------------
    suite = EvalSuite(
        suite_id="research-bench",
        cases=(
            EvalCase(
                case_id="q1",
                inputs={"q": "who directed Casablanca"},
                expected_output="answer for: who directed Casablanca",
            ),
            EvalCase(
                case_id="q2",
                inputs={"q": "where was Michael Curtiz born"},
                expected_output="answer for: Michael Curtiz birthplace",
            ),
        ),
    )

    def program(inputs):
        return f"answer for: {inputs['q']}"

    runner = EvalRunner(
        program=program,
        eval_fn=lambda case, output: 1.0 if output == case.expected_output else 0.0,
    )
    run = runner.run(suite)
    # First case matches; second doesn't.
    assert run.n_passed == 1
    md_run = eval_run_to_markdown(run, title="Eval Results")
    assert "research-bench" in md_run or "Eval Results" in md_run
    json_run = eval_run_to_json(run)
    assert json_run["summary"]["pass_rate"] == 0.5

    # --- Layer 7: continuous learning -------------------------------
    edit_recorder = EditRecorder()
    # User edited a few report drafts; learner notices the pattern.
    for i in range(5):
        edit_recorder.record(
            agent_output=f"Result of hop {i} indicates that the answer to the "
                         "user's query is, in fact, the value returned by the tool.",
            user_edit=f"Hop {i}: see tool answer.",
            user_id="alice",
        )
    learner = ContinuousLearner(recorder=edit_recorder, memory=memory)
    learning_report = learner.learn(user_id="alice")
    # At least the length-shortening preference should be detected.
    assert learning_report.n_preferences_learned >= 1
    # Preference is now stored in alice's memory namespace.
    alice_items = [
        it for it in memory._items.values()  # noqa: SLF001
        if it.namespace == "alice"
    ]
    assert len(alice_items) >= 1

    # --- Layer 8: memory consolidation ------------------------------
    # Seed some old EPISODIC memory representing past sessions.
    for i in range(6):
        memory.insert(MemoryItem.create(
            kind=MemoryKind.EPISODIC,
            content=f"session log entry {i}: agent ran research hop {i}",
            namespace="alice",
            tags=("session-2026-05-08",),
            importance=0.3,
            timestamp=1_000_000.0,  # very old
        ))
    consolidator = MemoryConsolidator(
        store=memory,
        policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=3),
        lattice=lattice,
        agent_id="orion-consolidator",
    )
    cons_report = consolidator.consolidate(namespace="alice")
    assert cons_report.n_summaries_created >= 1

    # --- Layer 9: skill drift monitor -------------------------------
    drift = SkillDriftMonitor(
        policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        lattice=lattice,
    )
    # Baseline: 5 successful research calls.
    for _ in range(5):
        drift.record(skill_id="research-skill", succeeded=True)
    # Recent: 3 more successes → no drift.
    for _ in range(3):
        drift.record(skill_id="research-skill", succeeded=True)
    assert drift.check("research-skill") is None

    # Inject a regression: 3 failures in a row.
    for _ in range(3):
        drift.record(skill_id="research-skill", succeeded=False)
    alert = drift.check("research-skill")
    assert alert is not None
    assert alert.severity == "critical"

    # --- Layer 10: distributed audit summary ------------------------
    # Bus history captures every cross-agent message.
    pub_history = bus.history(topic_pattern="agent.research.hop")
    assert len(pub_history) == 3

    # Final invariant: every layer produced at least one witness on the
    # shared lattice — proves all modules use the same provenance ledger.
    final_witnesses = lattice.ledger.witnesses_for()
    issuers = {w.issued_by for w in final_witnesses}
    # research-agent (tool runtime), agent-research-hop (bus),
    # orion-consolidator, skill-drift-monitor, plus composer.
    assert "skill-drift-monitor" in issuers
    assert "orion-consolidator" in issuers
    # Total witnesses: tool runtime (6+) + bus publishes (3) +
    # consolidation (1+) + drift (1) ≥ 11.
    assert len(final_witnesses) >= 11
