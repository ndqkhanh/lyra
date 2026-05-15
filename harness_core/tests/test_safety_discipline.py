"""Tests for safety/discipline modules — forensic, isolation, retraction."""
from __future__ import annotations

import pytest

from harness_core.forensic import (
    ReplayComparator,
    Trajectory,
    TrajectoryOutcome,
    TrajectorySimilarity,
    action_jaccard,
    fingerprint_jaccard,
)
from harness_core.gates import (
    RetractionGate,
    RetractionRecord,
    RetractionVerdict,
    StaticRetractionIndex,
)
from harness_core.isolation import (
    ContextNamespace,
    IsolatedContext,
    NamespacePermission,
    PermissionGrant,
    register_grant,
)
from harness_core.isolation.context_namespace import _clear_grants_for_test
from harness_core.orchestration import AgentDecision, SideEffectRecord


# --- Forensic / replay comparator ---------------------------------------


def _make_traj(
    *,
    tid: str,
    task: str,
    actions: list[str],
    fingerprints: list[str] | None = None,
    tools: list[tuple[str, bool]] | None = None,
    outcome: TrajectoryOutcome = TrajectoryOutcome.SUCCESS,
) -> Trajectory:
    fingerprints = fingerprints or [f"fp-{a}-{i}" for i, a in enumerate(actions)]
    decisions = tuple(
        AgentDecision(action=a, fingerprint=fp)
        for a, fp in zip(actions, fingerprints)
    )
    side_effects = tuple(
        SideEffectRecord(call_id=f"c{i}", tool_name=name, args={}, result=None, is_replayable=rep)
        for i, (name, rep) in enumerate(tools or [])
    )
    return Trajectory(
        trajectory_id=tid,
        task_signature=task,
        decisions=decisions,
        side_effects=side_effects,
        outcome=outcome,
    )


class TestActionJaccard:
    def test_identical(self):
        assert action_jaccard(["a", "b", "c"], ["a", "b", "c"]) == 1.0

    def test_disjoint(self):
        assert action_jaccard(["a", "b"], ["x", "y"]) == 0.0

    def test_partial_overlap(self):
        # bigrams of [a,b,c] = {(a,b), (b,c)}; of [a,b,d] = {(a,b), (b,d)}
        # Jaccard = 1 / 3.
        score = action_jaccard(["a", "b", "c"], ["a", "b", "d"])
        assert score == pytest.approx(1 / 3, abs=1e-3)

    def test_both_empty(self):
        assert action_jaccard([], []) == 1.0

    def test_length_one_uses_unigram(self):
        assert action_jaccard(["a"], ["a"]) == 1.0
        assert action_jaccard(["a"], ["b"]) == 0.0


class TestFingerprintJaccard:
    def test_identical(self):
        assert fingerprint_jaccard(frozenset({"a", "b"}), frozenset({"a", "b"})) == 1.0

    def test_disjoint(self):
        assert fingerprint_jaccard(frozenset({"a"}), frozenset({"b"})) == 0.0

    def test_both_empty(self):
        assert fingerprint_jaccard(frozenset(), frozenset()) == 1.0


class TestReplayComparator:
    def test_compare_same_task_only(self):
        comp = ReplayComparator(corpus=[
            _make_traj(tid="t1", task="task-A", actions=["search", "answer"]),
            _make_traj(tid="t2", task="task-B", actions=["search", "answer"]),  # different task
        ])
        current = _make_traj(tid="cur", task="task-A", actions=["search", "answer"])
        sims = comp.compare(current)
        # Only t1 (same task) appears.
        assert {s.pair_id[1] for s in sims} == {"t1"}

    def test_outlier_when_no_match(self):
        comp = ReplayComparator(corpus=[
            _make_traj(tid="t1", task="task-A", actions=["search", "search", "answer"]),
            _make_traj(tid="t2", task="task-A", actions=["search", "search", "answer"]),
        ])
        # Current trajectory does completely different actions.
        current = _make_traj(tid="cur", task="task-A", actions=["delete", "format", "destroy"])
        assert comp.is_outlier(current, threshold=0.3) is True

    def test_not_outlier_when_similar(self):
        comp = ReplayComparator(corpus=[
            _make_traj(tid="t1", task="task-A", actions=["search", "answer"]),
        ])
        current = _make_traj(tid="cur", task="task-A", actions=["search", "answer"])
        assert comp.is_outlier(current, threshold=0.5) is False

    def test_no_baseline_not_flagged(self):
        # No peers on the same task → don't accuse.
        comp = ReplayComparator(corpus=[])
        current = _make_traj(tid="cur", task="task-A", actions=["destroy"])
        assert comp.is_outlier(current) is False

    def test_stats(self):
        comp = ReplayComparator(corpus=[
            _make_traj(tid="t1", task="A", actions=["x"], outcome=TrajectoryOutcome.SUCCESS),
            _make_traj(tid="t2", task="A", actions=["x"], outcome=TrajectoryOutcome.FAILURE),
            _make_traj(tid="t3", task="B", actions=["x"], outcome=TrajectoryOutcome.ROLLED_BACK),
        ])
        stats = comp.stats()
        assert stats["trajectories"] == 3
        assert stats["tasks"] == 2
        assert stats["outcomes_success"] == 1
        assert stats["outcomes_failure"] == 1
        assert stats["outcomes_rolled_back"] == 1

    def test_similarity_ordering(self):
        comp = ReplayComparator(corpus=[
            _make_traj(tid="dissimilar", task="A", actions=["w", "x", "y"],
                       fingerprints=["f1", "f2", "f3"]),
            _make_traj(tid="similar", task="A", actions=["a", "b", "c"],
                       fingerprints=["fa", "fb", "fc"]),
        ])
        current = _make_traj(tid="cur", task="A", actions=["a", "b", "c"],
                             fingerprints=["fa", "fb", "fc"])
        sims = comp.compare(current)
        assert sims[0].pair_id[1] == "similar"
        assert sims[0].composite > sims[1].composite

    def test_tool_overlap_signal(self):
        comp = ReplayComparator(corpus=[
            _make_traj(tid="t1", task="A", actions=["call"],
                       tools=[("write_file", True), ("run_tests", True)]),
        ])
        # Same actions but a *non-replayable network call* → tool_overlap differs.
        current = _make_traj(tid="cur", task="A", actions=["call"],
                             tools=[("write_file", True), ("net_post", False)])
        sims = comp.compare(current)
        assert sims[0].tool_overlap < 1.0


# --- Isolation / context namespace --------------------------------------


@pytest.fixture(autouse=True)
def _reset_grants():
    _clear_grants_for_test()
    yield
    _clear_grants_for_test()


class TestIsolatedContextSameNamespace:
    def test_put_get(self):
        ns = ContextNamespace(namespace_id="run-1")
        ctx = IsolatedContext(namespace=ns)
        ctx.put("k", "v")
        assert ctx.get("k") == "v"

    def test_default_on_miss(self):
        ctx = IsolatedContext(namespace=ContextNamespace(namespace_id="run-1"))
        assert ctx.get("missing", default="dflt") == "dflt"

    def test_has_and_keys(self):
        ctx = IsolatedContext(namespace=ContextNamespace(namespace_id="run-1"))
        ctx.put("a", 1)
        ctx.put("b", 2)
        assert ctx.has("a") is True
        assert ctx.has("missing") is False
        assert set(ctx.keys()) == {"a", "b"}

    def test_empty_key_rejected(self):
        ctx = IsolatedContext(namespace=ContextNamespace(namespace_id="run-1"))
        with pytest.raises(ValueError):
            ctx.put("", "v")

    def test_namespace_id_must_be_nonempty(self):
        with pytest.raises(ValueError):
            ContextNamespace(namespace_id="")
        with pytest.raises(ValueError):
            ContextNamespace(namespace_id="   ")


class TestCrossNamespace:
    def test_default_blocks_cross_read(self):
        ns_a = ContextNamespace(namespace_id="A")
        ns_b = ContextNamespace(namespace_id="B")
        ctx_a = IsolatedContext(namespace=ns_a)
        ctx_b = IsolatedContext(namespace=ns_b)
        ctx_b.put("secret", "42")
        with pytest.raises(PermissionError):
            ctx_a.cross_read(other=ctx_b, key="secret")

    def test_grant_allows_cross_read(self):
        register_grant(PermissionGrant(
            source_namespace="B",
            target_namespace="A",
            permissions=frozenset({NamespacePermission.READ}),
            reason="approved by ops",
        ))
        ctx_a = IsolatedContext(namespace=ContextNamespace(namespace_id="A"))
        ctx_b = IsolatedContext(namespace=ContextNamespace(namespace_id="B"))
        ctx_b.put("k", "v")
        assert ctx_a.cross_read(other=ctx_b, key="k") == "v"

    def test_grant_is_one_way(self):
        # Grant B → A; B cannot read from A.
        register_grant(PermissionGrant(
            source_namespace="B",
            target_namespace="A",
            permissions=frozenset({NamespacePermission.READ}),
        ))
        ctx_a = IsolatedContext(namespace=ContextNamespace(namespace_id="A"))
        ctx_b = IsolatedContext(namespace=ContextNamespace(namespace_id="B"))
        ctx_a.put("k", "v")
        with pytest.raises(PermissionError):
            ctx_b.cross_read(other=ctx_a, key="k")

    def test_self_read_always_works(self):
        ctx = IsolatedContext(namespace=ContextNamespace(namespace_id="A"))
        ctx.put("k", "v")
        # Cross_read with self should work even with no grants.
        assert ctx.cross_read(other=ctx, key="k") == "v"

    def test_cross_list_requires_LIST_grant(self):
        ctx_a = IsolatedContext(namespace=ContextNamespace(namespace_id="A"))
        ctx_b = IsolatedContext(namespace=ContextNamespace(namespace_id="B"))
        ctx_b.put("k1", 1)
        with pytest.raises(PermissionError):
            ctx_a.cross_list(other=ctx_b)
        register_grant(PermissionGrant(
            source_namespace="B", target_namespace="A",
            permissions=frozenset({NamespacePermission.LIST}),
        ))
        assert ctx_a.cross_list(other=ctx_b) == ["k1"]

    def test_inherit_grants_from_parent(self):
        parent = IsolatedContext(namespace=ContextNamespace(namespace_id="parent"))
        parent.put("shared_fact", "x")
        child = IsolatedContext(namespace=ContextNamespace(
            namespace_id="child",
            parent="parent",
            inherit_grants=True,
        ))
        # Child inherits parent's data without an explicit grant.
        assert child.cross_read(other=parent, key="shared_fact") == "x"

    def test_no_inherit_when_flag_off(self):
        parent = IsolatedContext(namespace=ContextNamespace(namespace_id="parent"))
        parent.put("k", "v")
        child = IsolatedContext(namespace=ContextNamespace(
            namespace_id="child",
            parent="parent",
            inherit_grants=False,  # explicit opt-out
        ))
        with pytest.raises(PermissionError):
            child.cross_read(other=parent, key="k")


# --- Retraction gate ----------------------------------------------------


class TestRetractionGate:
    def _index(self):
        idx = StaticRetractionIndex()
        idx.add(RetractionRecord(
            paper_id="10.1038/nature.2020.fake",
            reason="data fabrication",
            source="RetractionWatch",
        ))
        return idx

    def test_retracted_doc_dropped(self):
        gate = RetractionGate(index=self._index())
        docs = [
            {"id": "d1", "paper_id": "10.1038/nature.2020.fake", "text": "..."},
            {"id": "d2", "paper_id": "10.1038/nature.2024.real", "text": "..."},
        ]
        kept, verdicts = gate.filter(docs)
        assert {d["id"] for d in kept} == {"d2"}
        retracted = [v for v in verdicts if v.is_retracted]
        assert len(retracted) == 1
        assert retracted[0].record.reason == "data fabrication"

    def test_no_paper_id_kept(self):
        gate = RetractionGate(index=self._index())
        docs = [{"id": "d1", "text": "doc with no paper_id"}]
        kept, verdicts = gate.filter(docs)
        assert len(kept) == 1
        assert verdicts[0].is_retracted is False
        assert "no paper_id" in verdicts[0].note

    def test_index_error_fail_closed(self):
        class BrokenIndex:
            name = "broken"
            def is_retracted(self, paper_id):
                raise RuntimeError("network down")

        gate = RetractionGate(index=BrokenIndex(), fail_closed=True)
        kept, verdicts = gate.filter([{"id": "d1", "paper_id": "x"}])
        # Fail-closed: dropped.
        assert kept == []
        assert verdicts[0].is_retracted is True
        assert "fail_closed" in verdicts[0].note

    def test_index_error_fail_open(self):
        class BrokenIndex:
            name = "broken"
            def is_retracted(self, paper_id):
                raise RuntimeError("down")

        gate = RetractionGate(index=BrokenIndex(), fail_closed=False)
        kept, verdicts = gate.filter([{"id": "d1", "paper_id": "x"}])
        # Fail-open: kept, flagged in note.
        assert len(kept) == 1
        assert verdicts[0].is_retracted is False
        assert "fail_open" in verdicts[0].note

    def test_stats(self):
        gate = RetractionGate(index=self._index())
        docs = [
            {"id": "d1", "paper_id": "10.1038/nature.2020.fake"},  # retracted
            {"id": "d2", "paper_id": "10.1038/clean"},  # ok
            {"id": "d3"},  # no paper_id
        ]
        _, verdicts = gate.filter(docs)
        s = gate.stats(verdicts)
        assert s["total"] == 3
        assert s["retracted"] == 1
        assert s["kept"] == 2
        assert s["no_paper_id"] == 1


class TestStaticRetractionIndex:
    def test_add_and_lookup(self):
        idx = StaticRetractionIndex()
        idx.add(RetractionRecord(paper_id="x", reason="r"))
        assert idx.is_retracted("x") is not None
        assert idx.is_retracted("y") is None
