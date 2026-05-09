"""Wave-C Task 3: ``/map`` — render a stdlib-only ASCII dependency tree.

The v1 stub printed a placeholder. Wave-C teaches the slash to walk
``repo_root`` and emit an indented tree of every ``*.py`` file, with
a depth cap so a deep monorepo doesn't flood the REPL. No graphviz
dep, no AST analysis — that's Wave F. The point here is to ship a
real, useful read-only view that exists *today*.

Three contract tests:

1. Renders an indented tree containing the seeded files.
2. Outside-a-real-repo path (root has no Python at all): friendly
   "no python sources found" without crashing.
3. Depth-cap honoured: files ≥ ``max_depth`` levels deep are not
   listed individually (the parent dir is shown with a `…` marker).
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def _seed_repo(tmp: Path) -> Path:
    """Create a tiny package layout so /map has something interesting."""
    pkg = tmp / "pkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "deep" / "deeper" / "deepest").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "module_a.py").write_text("import os\n", encoding="utf-8")
    (pkg / "sub" / "module_b.py").write_text("import sys\n", encoding="utf-8")
    (pkg / "deep" / "deeper" / "deepest" / "buried.py").write_text("", encoding="utf-8")
    return tmp


def test_map_renders_indented_tree_of_python_files(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    s = InteractiveSession(repo_root=tmp_path)
    out = s._cmd_map_text("")
    # Every seeded module shows up by name (basename suffices — the
    # tree adds whitespace between markers and names).
    assert "module_a.py" in out
    assert "module_b.py" in out
    # Tree structure cues — at least one branch glyph and the heading:
    assert "pkg" in out
    assert "/map:" in out or "Repository map" in out


def test_map_handles_repo_with_no_python(tmp_path: Path) -> None:
    """An empty / non-python tree gets a friendly message, not a crash."""
    (tmp_path / "README.md").write_text("# nothing python here\n", encoding="utf-8")
    s = InteractiveSession(repo_root=tmp_path)
    out = s._cmd_map_text("")
    assert "no python" in out.lower() or "no .py" in out.lower()


def test_map_caps_depth(tmp_path: Path) -> None:
    """Files buried below ``max_depth`` collapse to ``…`` markers."""
    _seed_repo(tmp_path)
    s = InteractiveSession(repo_root=tmp_path)
    out = s._cmd_map_text("--max-depth=2")
    # ``buried.py`` is 4 dirs deep (pkg/deep/deeper/deepest) —
    # max-depth=2 must hide it.
    assert "buried.py" not in out
    # But the depth-cap marker should appear so the user knows there's
    # more to see.
    assert "…" in out or "..." in out
