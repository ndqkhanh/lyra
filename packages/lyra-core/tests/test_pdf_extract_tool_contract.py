"""Contract tests for the ``pdf_extract`` tool."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.tools.pdf_extract import (
    PdfExtractError,
    extract_text_from_pdf,
    make_pdf_extract_tool,
)


def test_tool_schema_is_present(tmp_path: Path) -> None:
    tool = make_pdf_extract_tool(repo_root=tmp_path)
    assert tool.__tool_schema__["name"] == "pdf_extract"
    assert "path" in tool.__tool_schema__["parameters"]["required"]


def test_missing_file_returns_error(tmp_path: Path) -> None:
    tool = make_pdf_extract_tool(repo_root=tmp_path)
    r = tool(path="missing.pdf")
    assert r["ok"] is False
    assert "not found" in r["error"]


def test_non_pdf_returns_error(tmp_path: Path) -> None:
    (tmp_path / "not-really.pdf").write_bytes(b"hello world")
    tool = make_pdf_extract_tool(repo_root=tmp_path)
    r = tool(path="not-really.pdf")
    assert r["ok"] is False
    assert "not a PDF" in r["error"]


def test_outside_repo_root_is_refused(tmp_path: Path) -> None:
    sibling = tmp_path.parent / "escaped.pdf"
    sibling.write_bytes(b"%PDF-1.4\n%EOF\n")
    tool = make_pdf_extract_tool(repo_root=tmp_path)
    r = tool(path="../escaped.pdf")
    assert r["ok"] is False
    assert "outside repo_root" in r["error"]


def test_direct_helper_raises_for_bad_magic(tmp_path: Path) -> None:
    p = tmp_path / "bogus.pdf"
    p.write_bytes(b"not a pdf at all")
    with pytest.raises(PdfExtractError, match="bad magic"):
        extract_text_from_pdf(p)


def test_no_backend_installed_returns_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "empty.pdf"
    p.write_bytes(b"%PDF-1.4\n%EOF\n")

    import lyra_core.tools.pdf_extract as pe

    monkeypatch.setattr(pe, "_BACKENDS", ())
    tool = make_pdf_extract_tool(repo_root=tmp_path)
    r = tool(path="empty.pdf")
    assert r["ok"] is False
    assert "no pdf backend installed" in r["error"]


def test_uses_backend_when_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "good.pdf"
    p.write_bytes(b"%PDF-1.4\n%EOF\n")

    import lyra_core.tools.pdf_extract as pe
    from lyra_core.tools.pdf_extract import _Backend

    fake = _Backend(
        name="fake",
        is_available=lambda: True,
        extract=lambda path: "hello PDF world",
    )
    monkeypatch.setattr(pe, "_BACKENDS", (fake,))
    tool = make_pdf_extract_tool(repo_root=tmp_path)
    r = tool(path="good.pdf")
    assert r["ok"] is True
    assert r["text"] == "hello PDF world"
    assert r["length"] == len("hello PDF world")


def test_max_chars_truncates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "big.pdf"
    p.write_bytes(b"%PDF-1.4\n%EOF\n")

    import lyra_core.tools.pdf_extract as pe
    from lyra_core.tools.pdf_extract import _Backend

    fake = _Backend(
        name="fake",
        is_available=lambda: True,
        extract=lambda _: "x" * 500,
    )
    monkeypatch.setattr(pe, "_BACKENDS", (fake,))
    tool = make_pdf_extract_tool(repo_root=tmp_path)
    r = tool(path="big.pdf", max_chars=100)
    assert r["truncated"] is True
    assert len(r["text"]) == 100
    assert r["length"] == 500
