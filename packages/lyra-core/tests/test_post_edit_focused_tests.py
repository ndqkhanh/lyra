"""Red tests for post-edit impact map → focused test runner."""
from __future__ import annotations

from pathlib import Path

from lyra_core.tdd.impact_map import tests_for_edit


def _mk(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_same_name_testfile_path_mapping(tmp_path: Path) -> None:
    _mk(tmp_path / "src" / "foo" / "bar.py", "x = 1\n")
    t = tmp_path / "tests" / "foo" / "test_bar.py"
    _mk(t, "from src.foo.bar import x\n")
    out = tests_for_edit(tmp_path / "src" / "foo" / "bar.py", repo_root=tmp_path)
    assert t in out


def test_symbol_reference_mapping(tmp_path: Path) -> None:
    _mk(tmp_path / "src" / "util.py", "def add(a, b): return a+b\n")
    t = tmp_path / "tests" / "test_math.py"
    _mk(t, "from src.util import add\n\ndef test_add():\n    assert add(1, 2) == 3\n")
    out = tests_for_edit(tmp_path / "src" / "util.py", repo_root=tmp_path)
    assert t in out


def test_unrelated_test_not_returned(tmp_path: Path) -> None:
    _mk(tmp_path / "src" / "a.py", "x = 1\n")
    _mk(tmp_path / "src" / "b.py", "y = 2\n")
    ta = tmp_path / "tests" / "test_a.py"
    _mk(ta, "from src.a import x\n")
    tb = tmp_path / "tests" / "test_b.py"
    _mk(tb, "from src.b import y\n")
    out = tests_for_edit(tmp_path / "src" / "a.py", repo_root=tmp_path)
    assert ta in out
    assert tb not in out


def test_edit_of_testfile_returns_itself(tmp_path: Path) -> None:
    t = tmp_path / "tests" / "test_x.py"
    _mk(t, "def test_x(): pass\n")
    out = tests_for_edit(t, repo_root=tmp_path)
    assert t in out


def test_edit_outside_repo_root_returns_empty(tmp_path: Path) -> None:
    other = tmp_path / "outside.py"
    _mk(other, "x = 1\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tests_for_edit(other, repo_root=repo)
    assert out == []
