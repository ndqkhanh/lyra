"""Phase J.4 (v3.1.0): Reflexion retrospective loop.

Locked surface (every test pins one part of the public contract):

1. ``Reflection`` is frozen, dict-roundtrips, and validates verdict.
2. ``naive_lesson`` returns a non-empty string for any input.
3. ``ReflectionMemory`` is in-memory by default and persists when given
   a path; load / round-trip is lossless.
4. ``recent(k)`` returns the K newest entries chronologically.
5. ``for_tags`` filters entries that share at least one tag.
6. ``inject_reflections`` returns ``""`` for empty memory and
   ``header + bullet-per-lesson`` for non-empty memory.
7. ``make_reflection`` truncates lessons longer than 1500 chars.
"""
from __future__ import annotations

from pathlib import Path

from lyra_core.loop import (
    Reflection,
    ReflectionMemory,
    inject_reflections,
    make_reflection,
    naive_lesson,
)


def test_reflection_is_dict_roundtrippable() -> None:
    r = Reflection(
        task="write tests",
        verdict="fail",
        lesson="forgot the fixture",
        tags=("python", "pytest"),
    )
    payload = r.to_dict()
    assert payload["task"] == "write tests"
    assert payload["verdict"] == "fail"
    assert payload["tags"] == ["python", "pytest"]
    revived = Reflection.from_dict(payload)
    assert revived.task == r.task
    assert revived.verdict == r.verdict
    assert revived.lesson == r.lesson
    assert revived.tags == r.tags


def test_naive_lesson_is_non_empty_for_any_input() -> None:
    assert naive_lesson("", "", "fail").strip() != ""
    assert "fail" in naive_lesson("foo", "bar", "fail")


def test_make_reflection_truncates_long_lessons() -> None:
    def _verbose(_t: str, _a: str, _v: str) -> str:
        return "x" * 5000
    r = make_reflection("t", "a", "fail", lesson_generator=_verbose)
    assert len(r.lesson) <= 1500
    assert r.lesson.endswith("...")


def test_reflection_memory_in_memory_only() -> None:
    mem = ReflectionMemory()
    assert len(mem) == 0
    mem.add(Reflection(task="t1", verdict="pass", lesson="l1"))
    mem.add(Reflection(task="t2", verdict="fail", lesson="l2"))
    assert len(mem) == 2
    assert tuple(r.task for r in mem.all()) == ("t1", "t2")


def test_reflection_memory_persists_to_disk(tmp_path: Path) -> None:
    snap = tmp_path / "reflexion.json"
    mem = ReflectionMemory(path=snap)
    mem.add(Reflection(task="t1", verdict="pass", lesson="l1"))
    mem.add(Reflection(task="t2", verdict="fail", lesson="l2", tags=("rust",)))
    assert snap.exists()
    revived = ReflectionMemory(path=snap)
    assert len(revived) == 2
    assert revived.all()[1].tags == ("rust",)


def test_recent_returns_newest_k_in_order() -> None:
    mem = ReflectionMemory()
    for i in range(5):
        mem.add(Reflection(task=f"t{i}", verdict="pass", lesson=f"l{i}"))
    recent = mem.recent(3)
    assert tuple(r.task for r in recent) == ("t2", "t3", "t4")


def test_recent_zero_returns_empty() -> None:
    mem = ReflectionMemory()
    mem.add(Reflection(task="t1", verdict="pass", lesson="l1"))
    assert mem.recent(0) == ()


def test_for_tags_filters_by_tag_overlap() -> None:
    mem = ReflectionMemory()
    mem.add(Reflection(task="t1", verdict="fail", lesson="l1", tags=("rust",)))
    mem.add(Reflection(task="t2", verdict="fail", lesson="l2", tags=("python",)))
    mem.add(Reflection(task="t3", verdict="fail", lesson="l3", tags=("rust", "tdd")))
    rust_only = mem.for_tags(["rust"])
    assert tuple(r.task for r in rust_only) == ("t1", "t3")
    assert mem.for_tags([]) == mem.all()


def test_inject_reflections_empty_returns_empty_string() -> None:
    mem = ReflectionMemory()
    assert inject_reflections(mem) == ""


def test_inject_reflections_renders_bullets_with_verdict() -> None:
    mem = ReflectionMemory()
    mem.add(Reflection(task="t1", verdict="fail", lesson="missed precondition"))
    mem.add(Reflection(task="t2", verdict="pass", lesson="iterate again"))
    out = inject_reflections(mem, k=10)
    assert "Lessons from previous attempts:" in out
    assert "- [fail] missed precondition" in out
    assert "- [pass] iterate again" in out


def test_inject_reflections_respects_tag_filter() -> None:
    mem = ReflectionMemory()
    mem.add(Reflection(task="t1", verdict="fail", lesson="l1", tags=("python",)))
    mem.add(Reflection(task="t2", verdict="fail", lesson="l2", tags=("rust",)))
    out = inject_reflections(mem, k=10, tags=["python"])
    assert "l1" in out
    assert "l2" not in out


def test_inject_reflections_collapses_lesson_whitespace() -> None:
    mem = ReflectionMemory()
    mem.add(Reflection(task="t1", verdict="fail", lesson="line one\nline two\n"))
    out = inject_reflections(mem, k=10)
    assert "line one line two" in out
    assert "\n  " not in out


def test_clear_empties_memory_and_persists(tmp_path: Path) -> None:
    snap = tmp_path / "reflexion.json"
    mem = ReflectionMemory(path=snap)
    mem.add(Reflection(task="t1", verdict="pass", lesson="l1"))
    mem.clear()
    assert len(mem) == 0
    revived = ReflectionMemory(path=snap)
    assert len(revived) == 0
