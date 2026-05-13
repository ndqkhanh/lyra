"""Unit tests for agent_tree."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.transparency.event_store import EventStore, make_event
from lyra_core.transparency.agent_tree import build_agent_tree, render_tree_text


@pytest.fixture
def store(tmp_path: Path) -> EventStore:
    return EventStore(tmp_path / "test.db")


@pytest.mark.unit
def test_empty_store_returns_no_roots(store: EventStore) -> None:
    assert build_agent_tree(store) == []


@pytest.mark.unit
def test_session_start_creates_root(store: EventStore) -> None:
    store.append(make_event("SessionStart", session_id="root"))
    roots = build_agent_tree(store)
    assert len(roots) == 1
    assert roots[0].session_id == "root"


@pytest.mark.unit
def test_subagent_start_creates_child(store: EventStore) -> None:
    store.append(make_event("SessionStart", session_id="root"))
    store.append(make_event(
        "SubagentStart", session_id="child",
        payload={"parent_session_id": "root"},
    ))
    roots = build_agent_tree(store)
    assert len(roots) == 1
    assert len(roots[0].children) == 1
    assert roots[0].children[0].session_id == "child"


@pytest.mark.unit
def test_subagent_stop_marks_done(store: EventStore) -> None:
    store.append(make_event("SubagentStart", session_id="child", payload={"parent_session_id": ""}))
    store.append(make_event("SubagentStop", session_id="child"))
    roots = build_agent_tree(store)
    assert roots[0].state == "done"


@pytest.mark.unit
def test_render_tree_empty() -> None:
    text = render_tree_text([])
    assert "no subagent" in text


@pytest.mark.unit
def test_render_tree_shows_session_id(store: EventStore) -> None:
    store.append(make_event("SessionStart", session_id="mysession-abc"))
    roots = build_agent_tree(store)
    text = render_tree_text(roots)
    assert "mysession" in text
