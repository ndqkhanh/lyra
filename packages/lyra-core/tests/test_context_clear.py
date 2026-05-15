"""Tests for tool-result clearing (Phase CE.1, P0-2)."""
from __future__ import annotations

from lyra_core.context.clear import (
    FORGET_TOOL_NAME,
    clear_stale_tool_results,
    clear_tool_result,
    collect_cited_span_ids,
    forget_tool_handler,
)


def _tool(sid: str, name: str = "read_file", body: str = "the body") -> dict:
    return {"role": "tool", "tool_call_id": sid, "name": name, "content": body}


def _user(text: str) -> dict:
    return {"role": "user", "content": text}


def _asst(text: str) -> dict:
    return {"role": "assistant", "content": text}


# ────────────────────────────────────────────────────────────────
# clear_tool_result
# ────────────────────────────────────────────────────────────────


def test_clear_replaces_matching_tool_message_with_stub():
    msgs = [_user("hi"), _tool("t-1", body="big body 12345"), _asst("ok")]
    new, ok = clear_tool_result(msgs, "t-1")
    assert ok is True
    assert new[0] == msgs[0]
    assert new[2] == msgs[2]
    assert new[1]["content"].startswith("[cleared: read_file @ t-1")
    assert "view artifact" in new[1]["content"]


def test_clear_does_not_mutate_input():
    msgs = [_tool("t-1", body="original")]
    clear_tool_result(msgs, "t-1")
    assert msgs[0]["content"] == "original"


def test_clear_returns_false_when_span_id_absent():
    msgs = [_tool("t-1"), _tool("t-2")]
    new, ok = clear_tool_result(msgs, "t-missing")
    assert ok is False
    assert new == msgs


def test_clear_is_idempotent():
    msgs = [_tool("t-1", body="x")]
    first, ok1 = clear_tool_result(msgs, "t-1")
    assert ok1 is True
    second, ok2 = clear_tool_result(first, "t-1")
    assert ok2 is False  # already cleared
    assert second == first


def test_clear_ignores_non_tool_messages_with_same_id():
    """A user message that happens to share an id must not be cleared."""
    msgs = [
        {"role": "user", "content": "I have an id", "id": "t-1"},
        _tool("t-1", body="real tool body"),
    ]
    new, ok = clear_tool_result(msgs, "t-1")
    assert ok is True
    assert new[0] == msgs[0]  # user untouched
    assert new[1]["content"].startswith("[cleared:")


def test_clear_only_clears_first_match():
    msgs = [_tool("t-1", body="A"), _tool("t-1", body="B")]
    new, ok = clear_tool_result(msgs, "t-1")
    assert ok is True
    assert new[0]["content"].startswith("[cleared:")
    assert new[1]["content"] == "B"  # second copy preserved


def test_clear_accepts_id_field_too():
    msgs = [{"role": "tool", "id": "abc", "name": "x", "content": "body"}]
    _new, ok = clear_tool_result(msgs, "abc")
    assert ok is True


# ────────────────────────────────────────────────────────────────
# clear_stale_tool_results
# ────────────────────────────────────────────────────────────────


def test_stale_clear_keeps_recent_tool_results():
    """The freshest `older_than` tool messages are preserved."""
    msgs = [_tool(f"t-{i}", body=f"body-{i}") for i in range(6)]
    new, cleared = clear_stale_tool_results(msgs, older_than=3)
    # Last 3 stay raw; first 3 get cleared.
    assert cleared == ["t-0", "t-1", "t-2"]
    for i in range(3):
        assert new[i]["content"].startswith("[cleared:")
    for i in range(3, 6):
        assert new[i]["content"] == f"body-{i}"


def test_stale_clear_respects_citation_set():
    msgs = [_tool(f"t-{i}", body=f"body-{i}") for i in range(6)]
    new, cleared = clear_stale_tool_results(
        msgs, older_than=3, cited_span_ids={"t-1"}
    )
    assert "t-1" not in cleared  # protected by citation
    assert new[1]["content"] == "body-1"


def test_stale_clear_with_no_old_messages_is_noop():
    msgs = [_tool(f"t-{i}") for i in range(2)]
    new, cleared = clear_stale_tool_results(msgs, older_than=8)
    assert cleared == []
    assert new == msgs


def test_stale_clear_with_match_predicate_filters_by_tool_name():
    msgs = [
        _tool("t-0", name="read_file", body="big"),
        _tool("t-1", name="bash", body="log"),
        _tool("t-2", name="read_file", body="another"),
        _tool("t-3", name="bash", body="recent"),  # protected by older_than
    ]
    new, cleared = clear_stale_tool_results(
        msgs,
        older_than=1,
        match=lambda m: m.get("name") == "read_file",
    )
    assert cleared == ["t-0", "t-2"]
    assert new[1]["content"] == "log"  # bash not matched
    assert new[3]["content"] == "recent"


def test_stale_clear_skips_already_cleared():
    msgs = [
        {
            "role": "tool",
            "tool_call_id": "t-0",
            "name": "x",
            "content": "[cleared: x @ t-0; old; view artifact to restore]",
        },
        _tool("t-1"),
    ]
    _new, cleared = clear_stale_tool_results(msgs, older_than=0)
    assert cleared == ["t-1"]


def test_stale_clear_negative_older_than_raises():
    import pytest

    with pytest.raises(ValueError):
        clear_stale_tool_results([_tool("t-0")], older_than=-1)


# ────────────────────────────────────────────────────────────────
# collect_cited_span_ids
# ────────────────────────────────────────────────────────────────


def test_collect_cited_finds_later_mentions():
    msgs = [
        _tool("t-1", body="some content"),
        _asst("I'm going to use the result from t-1 to decide"),
        _tool("t-2", body="other"),
    ]
    cited = collect_cited_span_ids(msgs)
    assert cited == {"t-1"}


def test_collect_cited_ignores_self_reference_inside_tool_body():
    """The tool body of t-1 mentioning t-1 doesn't count as citation."""
    msgs = [
        _tool("t-1", body="my id is t-1 you know"),
        _asst("ok"),
    ]
    cited = collect_cited_span_ids(msgs)
    assert cited == set()


def test_collect_cited_handles_empty_transcript():
    assert collect_cited_span_ids([]) == set()


# ────────────────────────────────────────────────────────────────
# Forget(span_id) tool adapter
# ────────────────────────────────────────────────────────────────


def test_forget_tool_handler_returns_status_dict():
    msgs = [_tool("t-1", body="body")]
    out = forget_tool_handler(msgs, span_id="t-1")
    assert out["span_id"] == "t-1"
    assert out["cleared"] is True
    assert isinstance(out["messages"], list)
    new_msgs: list[dict] = out["messages"]  # type: ignore[assignment]
    assert new_msgs[0]["content"].startswith("[cleared:")


def test_forget_tool_handler_when_span_missing():
    msgs = [_tool("t-1")]
    out = forget_tool_handler(msgs, span_id="t-missing")
    assert out["cleared"] is False
    assert out["messages"] == msgs


def test_forget_tool_name_is_exposed():
    assert FORGET_TOOL_NAME == "Forget"
