import time

from harness_core.memory import Memory


def test_add_and_all_roundtrip(tmp_path):
    m = Memory(root=tmp_path, scope="test")
    m.add("user prefers Python", kind="preference", actor="agent")
    m.add("deadline Friday", kind="fact")
    entries = m.all()
    assert {e.kind for e in entries} == {"preference", "fact"}


def test_expires_at_drops_entry(tmp_path):
    m = Memory(root=tmp_path, scope="test")
    m.add("stale", kind="fact", expires_at=time.time() - 1)
    m.add("fresh", kind="fact")
    assert [e.content for e in m.all()] == ["fresh"]


def test_search_matches_keywords(tmp_path):
    m = Memory(root=tmp_path, scope="test")
    m.add("prefers pytest for tests", kind="preference")
    m.add("unrelated note about coffee", kind="fact")
    hits = m.search("pytest tests")
    assert len(hits) == 1
    assert "pytest" in hits[0].content


def test_clear_empties_scope(tmp_path):
    m = Memory(root=tmp_path, scope="test")
    m.add("x")
    assert len(m.all()) == 1
    m.clear()
    assert m.all() == []


def test_scope_isolation(tmp_path):
    a = Memory(root=tmp_path, scope="a")
    b = Memory(root=tmp_path, scope="b")
    a.add("only in a")
    assert [e.content for e in a.all()] == ["only in a"]
    assert b.all() == []
