"""Wave-F Task 2 — trace-vs-reality verifier contract."""
from __future__ import annotations

from pathlib import Path

from lyra_core.verifier import (
    TraceClaim,
    extract_claims,
    verify_trace,
)


# ---- seed a tiny repo ----------------------------------------------


def _seed(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "parser.py").write_text(
        "def parse(x):\n"
        "    return x.strip()\n"
        "def load(path):\n"
        "    return open(path, encoding='utf-8').read()\n",
        encoding="utf-8",
    )


# ---- extraction -----------------------------------------------------


def test_extract_claims_picks_up_file_line_citations() -> None:
    narration = (
        "I edited `pkg/parser.py:2` and fixed the bug in "
        "`pkg/parser.py:4`. No other file was touched."
    )
    claims = extract_claims(narration)
    paths = [(c.path, c.line) for c in claims]
    assert ("pkg/parser.py", 2) in paths
    assert ("pkg/parser.py", 4) in paths


def test_extract_claims_tolerates_no_line_number() -> None:
    claims = extract_claims("See README.md for details.")
    assert [(c.path, c.line) for c in claims] == [("README.md", None)]


def test_extract_claims_ignores_non_code_words() -> None:
    claims = extract_claims("this sentence has no citations whatsoever.")
    assert claims == []


# ---- trace-vs-FS ----------------------------------------------------


def test_accurate_citation_passes(tmp_path: Path) -> None:
    _seed(tmp_path)
    verd = verify_trace(
        narration="I fixed `pkg/parser.py:2`.",
        repo_root=tmp_path,
    )
    assert verd.passed
    assert verd.claims[0].line == 2


def test_wrong_line_number_fails(tmp_path: Path) -> None:
    _seed(tmp_path)
    verd = verify_trace(
        narration="I fixed `pkg/parser.py:999`.",
        repo_root=tmp_path,
    )
    assert not verd.passed
    assert "out of range" in verd.miscited[0].reason


def test_missing_file_fails(tmp_path: Path) -> None:
    _seed(tmp_path)
    verd = verify_trace(
        narration="I edited `pkg/nonexistent.py:1`.",
        repo_root=tmp_path,
    )
    assert not verd.passed
    assert "does not exist" in verd.miscited[0].reason


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    _seed(tmp_path)
    verd = verify_trace(
        narration="Peek `../../../../etc/shadow.yaml:1`.",
        repo_root=tmp_path,
    )
    assert not verd.passed
    assert (
        "escapes" in verd.miscited[0].reason
        or "does not exist" in verd.miscited[0].reason
    )


def test_snippet_must_match_disk(tmp_path: Path) -> None:
    _seed(tmp_path)
    good = verify_trace(
        narration="",
        repo_root=tmp_path,
        extra_claims=[
            TraceClaim(
                path="pkg/parser.py",
                line=2,
                snippet="return x.strip()",
            )
        ],
    )
    assert good.passed
    bad = verify_trace(
        narration="",
        repo_root=tmp_path,
        extra_claims=[
            TraceClaim(
                path="pkg/parser.py",
                line=2,
                snippet="totally different code",
            )
        ],
    )
    assert not bad.passed
    assert "snippet not found" in bad.miscited[0].reason


# ---- trace-vs-diff --------------------------------------------------


def test_diff_channel_is_optional(tmp_path: Path) -> None:
    _seed(tmp_path)
    verd = verify_trace(
        narration="I edited `pkg/parser.py:2`.",
        repo_root=tmp_path,
    )
    assert verd.checked_diff is False


def test_diff_channel_detects_missing_diff_entry(tmp_path: Path) -> None:
    _seed(tmp_path)
    diff = "diff --git a/docs/README.md b/docs/README.md\n+hello\n"
    verd = verify_trace(
        narration="I edited `pkg/parser.py:2`.",
        repo_root=tmp_path,
        diff=diff,
    )
    assert verd.checked_diff is True
    assert not verd.passed
    assert "does not mention" in verd.miscited[0].reason


def test_diff_channel_accepts_matching_entry(tmp_path: Path) -> None:
    _seed(tmp_path)
    diff = (
        "diff --git a/pkg/parser.py b/pkg/parser.py\n"
        "+    return x.strip()\n"
    )
    verd = verify_trace(
        narration="I edited `pkg/parser.py:2`.",
        repo_root=tmp_path,
        diff=diff,
    )
    assert verd.passed
    assert verd.checked_diff is True


def test_to_dict_is_json_shaped(tmp_path: Path) -> None:
    _seed(tmp_path)
    verd = verify_trace(
        narration="I edited `pkg/parser.py:999`.",
        repo_root=tmp_path,
    )
    data = verd.to_dict()
    assert data["passed"] is False
    assert data["checked_diff"] is False
    assert "miscited" in data and len(data["miscited"]) == 1
