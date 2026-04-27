"""Red tests for procedural (skill) memory + progressive disclosure.

Contract:
    - ``ProceduralMemory`` stores skills as (id, name, description, body)
    - Writable via ``put``; readable via ``get`` and ``search``
    - SQLite FTS5 backed so search is keyword-based (no embeddings in v1 MVP)
    - ``list_topics``, ``get_topic``, ``search_topic`` compose the
      progressive-disclosure surface (umbrella MCP-friendly)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory.procedural import ProceduralMemory, SkillRecord
from lyra_core.memory.progressive import (
    get_topic,
    list_topics,
    search_topic,
)


@pytest.fixture
def mem(tmp_path: Path) -> ProceduralMemory:
    return ProceduralMemory(db_path=tmp_path / "skills.sqlite")


def test_put_then_get(mem: ProceduralMemory) -> None:
    mem.put(
        SkillRecord(
            id="edit",
            name="Edit",
            description="minimum-viable edit to make tests pass",
            body="Use the `Edit` tool; keep changes small.",
        )
    )
    got = mem.get("edit")
    assert got is not None
    assert got.name == "Edit"
    assert "Edit" in got.body


def test_search_finds_by_keyword(mem: ProceduralMemory) -> None:
    mem.put(
        SkillRecord(
            id="edit",
            name="Edit",
            description="fast file edits",
            body="apply diffs",
        )
    )
    mem.put(
        SkillRecord(
            id="test_gen",
            name="Test Gen",
            description="produce failing tests (red)",
            body="write one assertion first",
        )
    )
    hits = [r.id for r in mem.search("red")]
    assert "test_gen" in hits


def test_search_results_are_tokenizer_bounded(mem: ProceduralMemory) -> None:
    for i in range(20):
        mem.put(
            SkillRecord(
                id=f"skill_{i}",
                name=f"Skill {i}",
                description=f"description {i}",
                body=("body " + str(i)) * 200,
            )
        )
    hits = mem.search("body", max_tokens=80)
    assert hits
    total = sum(len(r.body.split()) for r in hits)
    assert total <= 80 * 2, f"search results exceed token budget: {total}"


def test_list_topics_from_memory(mem: ProceduralMemory) -> None:
    mem.put(SkillRecord("a", "A", "alpha", "body"))
    mem.put(SkillRecord("b", "B", "beta", "body"))
    topics = list_topics(mem)
    assert {"a", "b"} <= {t.id for t in topics}


def test_get_topic_fetches_one(mem: ProceduralMemory) -> None:
    mem.put(SkillRecord("x", "X", "xray", "content"))
    got = get_topic(mem, "x")
    assert got is not None
    assert got.name == "X"


def test_search_topic_returns_matches(mem: ProceduralMemory) -> None:
    mem.put(SkillRecord("n1", "N1", "note one", "apple banana"))
    mem.put(SkillRecord("n2", "N2", "note two", "cherry date"))
    hits = [r.id for r in search_topic(mem, "banana")]
    assert "n1" in hits
    assert "n2" not in hits
