"""Post-edit impact map: given an edited file, return the test files that
should be re-run.

v1 heuristics (keep it dumb, observable, and reviewable):

    1. If the file is itself a test (``tests/**/test_*.py``), return itself.
    2. If the edit is outside ``repo_root``, return empty list.
    3. Convention match: ``src/<a>/<b>.py`` → ``tests/<a>/test_<b>.py``
       (and the ``tests/test_<b>.py`` fallback).
    4. Symbol match: for every ``def foo`` / class in the edited file,
       search ``tests/**/*.py`` for ``from ... import foo`` / ``<module>.foo``.
"""
from __future__ import annotations

import re
from pathlib import Path

_DEF_RE = re.compile(r"^\s*(?:def|class)\s+(\w+)", re.MULTILINE)
_IMPORT_FROM_RE_TMPL = r"from\s+[\w\.]+\s+import\s+[^\n]*\b{name}\b"


def _safe_relative(p: Path, root: Path) -> Path | None:
    try:
        return p.resolve().relative_to(root.resolve())
    except ValueError:
        return None


def _convention_matches(rel: Path, repo_root: Path) -> list[Path]:
    """Map src/<a>/<b>.py → tests/<a>/test_<b>.py (+ common fallbacks)."""
    if rel.suffix != ".py":
        return []
    parts = rel.parts
    if not parts:
        return []

    candidates: list[Path] = []

    if parts[0] == "src":
        sub = parts[1:]
        if sub:
            stem = Path(sub[-1]).stem
            test_dir = Path("tests") / Path(*sub[:-1]) if len(sub) > 1 else Path("tests")
            candidates.append(repo_root / test_dir / f"test_{stem}.py")
            candidates.append(repo_root / "tests" / f"test_{stem}.py")

    stem = rel.stem
    candidates.append(repo_root / "tests" / f"test_{stem}.py")

    return [c for c in candidates if c.exists()]


def _symbol_matches(edited: Path, repo_root: Path) -> list[Path]:
    if not edited.exists() or edited.suffix != ".py":
        return []
    try:
        text = edited.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    names = set(_DEF_RE.findall(text))
    if not names:
        return []

    tests_dir = repo_root / "tests"
    if not tests_dir.exists():
        return []

    hits: set[Path] = set()
    for name in names:
        pat = re.compile(_IMPORT_FROM_RE_TMPL.format(name=re.escape(name)))
        for t in tests_dir.rglob("*.py"):
            try:
                body = t.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            if pat.search(body):
                hits.add(t)
    return sorted(hits)


def tests_for_edit(path: Path, *, repo_root: Path) -> list[Path]:
    rel = _safe_relative(Path(path), Path(repo_root))
    if rel is None:
        return []

    # Rule 1: edited file itself is a test.
    if rel.parts and rel.parts[0] == "tests" and Path(path).exists():
        return [Path(path)]

    results: set[Path] = set()
    for p in _convention_matches(rel, Path(repo_root)):
        results.add(p)
    for p in _symbol_matches(Path(path), Path(repo_root)):
        results.add(p)
    return sorted(results)
