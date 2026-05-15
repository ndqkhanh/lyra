"""Tests for iterative-retrieval sub-agent handoff (Phase CE.2, P1-2)."""
from __future__ import annotations

import pytest

from lyra_core.subagent.handoff import (
    HANDOFF_SEED_CAP_BYTES,
    REQUEST_MORE_CONTEXT_TOOL_NAME,
    RESPONSE_CHUNK_CAP_BYTES,
    ContextRequest,
    ContextResponse,
    HandoffError,
    HandoffSeed,
    SubagentHandoff,
    make_seed_from_parent,
    request_more_context_tool_handler,
)


# ────────────────────────────────────────────────────────────────
# HandoffSeed validation
# ────────────────────────────────────────────────────────────────


def test_seed_renders_task_and_acceptance():
    seed = HandoffSeed(
        task="explore src/api.py",
        acceptance_test="every public function has a docstring",
        hints=("look at recent changes",),
    )
    body = seed.render()
    assert "# Task" in body
    assert "explore src/api.py" in body
    assert "# Acceptance test" in body
    assert "every public function" in body
    assert "# Hints" in body
    assert "- look at recent changes" in body


def test_seed_renders_without_hints_section():
    seed = HandoffSeed(task="x", acceptance_test="y")
    body = seed.render()
    assert "# Hints" not in body


def test_seed_rejects_empty_task():
    with pytest.raises(HandoffError, match="task"):
        HandoffSeed(task="", acceptance_test="y")


def test_seed_rejects_empty_acceptance():
    with pytest.raises(HandoffError, match="acceptance"):
        HandoffSeed(task="x", acceptance_test="")


def test_seed_rejects_oversize():
    # Build hints that together exceed the cap.
    big = "x" * 4096
    with pytest.raises(HandoffError, match="exceeds cap"):
        HandoffSeed(task="t", acceptance_test="a", hints=(big,))


def test_seed_under_cap_accepted():
    seed = HandoffSeed(
        task="t" * 100,
        acceptance_test="a" * 100,
        hints=tuple(f"hint {i}" for i in range(5)),
    )
    assert len(seed.render().encode("utf-8")) <= HANDOFF_SEED_CAP_BYTES


def test_seed_rejects_non_positive_cap():
    with pytest.raises(HandoffError, match="cap_bytes"):
        HandoffSeed(task="t", acceptance_test="a", cap_bytes=0)


# ────────────────────────────────────────────────────────────────
# ContextRequest / ContextResponse validation
# ────────────────────────────────────────────────────────────────


def test_request_rejects_empty_query():
    with pytest.raises(HandoffError):
        ContextRequest(query="", requested_by="sub-1")


def test_request_rejects_empty_requester():
    with pytest.raises(HandoffError):
        ContextRequest(query="q", requested_by="")


def test_response_under_cap_passes():
    r = ContextResponse(query="q", chunks=("a", "b"))
    assert r.truncated is False


def test_response_oversize_must_mark_truncated():
    big = "x" * (RESPONSE_CHUNK_CAP_BYTES + 8)
    with pytest.raises(HandoffError, match="truncated"):
        ContextResponse(query="q", chunks=(big,))


def test_response_oversize_with_truncated_flag_accepted():
    big = "x" * (RESPONSE_CHUNK_CAP_BYTES + 8)
    r = ContextResponse(query="q", chunks=(big,), truncated=True)
    assert r.truncated is True


# ────────────────────────────────────────────────────────────────
# SubagentHandoff lifecycle
# ────────────────────────────────────────────────────────────────


class _StaticProvider:
    """Stub provider that returns a fixed response for any request."""

    def __init__(self, response: ContextResponse) -> None:
        self.response = response
        self.served: list[ContextRequest] = []

    def serve(self, request: ContextRequest) -> ContextResponse:
        self.served.append(request)
        return ContextResponse(
            query=request.query,
            chunks=self.response.chunks,
            truncated=self.response.truncated,
        )


def test_handoff_records_each_request():
    seed = HandoffSeed(task="t", acceptance_test="a")
    provider = _StaticProvider(ContextResponse(query="x", chunks=("answer",)))
    h = SubagentHandoff(seed=seed, provider=provider, subagent_id="sub-1")
    h.request_more("first")
    h.request_more("second")
    assert [r.query for r in h.requests] == ["first", "second"]
    assert all(r.requested_by == "sub-1" for r in h.requests)


def test_handoff_returns_provider_chunks():
    seed = HandoffSeed(task="t", acceptance_test="a")
    provider = _StaticProvider(
        ContextResponse(query="x", chunks=("chunk-A", "chunk-B"))
    )
    h = SubagentHandoff(seed=seed, provider=provider, subagent_id="s")
    resp = h.request_more("q1")
    assert resp.chunks == ("chunk-A", "chunk-B")
    assert resp.query == "q1"


# ────────────────────────────────────────────────────────────────
# make_seed_from_parent
# ────────────────────────────────────────────────────────────────


def test_make_seed_does_not_embed_parent_context():
    """The 10k parent context must NOT slip into the seed body."""
    big_parent = "PARENT_BODY_PROBE " * 1000  # > 16 KB
    seed = make_seed_from_parent(
        task="do thing",
        acceptance_test="test passes",
        parent_context=big_parent,
        hints=("hint",),
    )
    assert "PARENT_BODY_PROBE" not in seed.render()
    assert len(seed.render().encode("utf-8")) <= HANDOFF_SEED_CAP_BYTES


def test_make_seed_propagates_cap_override():
    seed = make_seed_from_parent(
        task="t",
        acceptance_test="a",
        parent_context="",
        cap_bytes=512,
    )
    assert seed.cap_bytes == 512


# ────────────────────────────────────────────────────────────────
# Integration scenario from the doc: 10KB parent, ≤2KB seed, callbacks
# ────────────────────────────────────────────────────────────────


class _MemoryStubProvider:
    """Mimics the parent's L5 memory: lookup by substring in a 10KB blob."""

    def __init__(self, parent_blob: str) -> None:
        self.parent_blob = parent_blob

    def serve(self, request: ContextRequest) -> ContextResponse:
        q = request.query
        hits: list[str] = []
        for line in self.parent_blob.splitlines():
            if q in line:
                hits.append(line)
                if sum(len(h.encode("utf-8")) for h in hits) > 512:
                    return ContextResponse(
                        query=q,
                        chunks=tuple(hits),
                        truncated=True,
                    )
        return ContextResponse(query=q, chunks=tuple(hits))


def test_subagent_starts_under_2kb_and_can_pull_more():
    parent_blob = "\n".join(
        f"line {i}: about feature_{i % 5}" for i in range(500)
    )
    assert len(parent_blob.encode("utf-8")) > 10_000

    seed = make_seed_from_parent(
        task="audit feature_3 references",
        acceptance_test="every feature_3 line is accounted for",
        parent_context=parent_blob,
    )
    # Seed under cap — the sub-agent never sees the 10KB blob upfront.
    assert len(seed.render().encode("utf-8")) <= HANDOFF_SEED_CAP_BYTES

    provider = _MemoryStubProvider(parent_blob)
    h = SubagentHandoff(seed=seed, provider=provider, subagent_id="auditor")

    # Sub-agent decides it needs more — pulls feature_3 mentions.
    resp = h.request_more("feature_3")
    assert len(resp.chunks) > 0
    assert all("feature_3" in c for c in resp.chunks)

    # Audit trail captured the request.
    assert len(h.requests) == 1
    assert h.requests[0].query == "feature_3"


# ────────────────────────────────────────────────────────────────
# RequestMoreContext tool handler
# ────────────────────────────────────────────────────────────────


def test_request_more_context_tool_returns_json_shape():
    seed = HandoffSeed(task="t", acceptance_test="a")
    provider = _StaticProvider(
        ContextResponse(query="x", chunks=("payload",))
    )
    h = SubagentHandoff(seed=seed, provider=provider, subagent_id="s")
    out = request_more_context_tool_handler(h, query="anything")
    assert out["ok"] is True
    assert out["query"] == "anything"
    assert out["chunks"] == ["payload"]
    assert out["truncated"] is False


def test_request_more_context_tool_handles_handoff_error():
    seed = HandoffSeed(task="t", acceptance_test="a")
    provider = _StaticProvider(ContextResponse(query="x", chunks=()))
    h = SubagentHandoff(seed=seed, provider=provider, subagent_id="s")
    out = request_more_context_tool_handler(h, query="")  # empty query
    assert out["ok"] is False
    assert "query" in str(out["error"]).lower()


def test_request_more_context_tool_name_is_exposed():
    assert REQUEST_MORE_CONTEXT_TOOL_NAME == "RequestMoreContext"
