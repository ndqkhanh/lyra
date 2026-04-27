"""Wave-E Task 10: contract tests for ``image_describe`` + ``image_ocr``.

Both tools are LLM/OCR-injectable, so the unit tier never reaches a
real provider. A tiny PNG is produced on the fly for the path checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from lyra_core.tools.image_describe import (
    ImageDescribeError,
    describe_image,
    make_image_describe_tool,
)
from lyra_core.tools.image_ocr import (
    ImageOCRError,
    OCRBackend,
    make_image_ocr_tool,
    ocr_image,
)


# Tiny 1x1 PNG (red pixel) — base64 decoded to bytes.
_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
    b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc"
    b"\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01R\xfb\xb1\xc7\x00\x00\x00\x00"
    b"IEND\xaeB`\x82"
)


@pytest.fixture()
def tiny_png(tmp_path: Path) -> Path:
    p = tmp_path / "img.png"
    p.write_bytes(_PNG_BYTES)
    return p


# ---------------------------------------------------------------------------
# image_describe
# ---------------------------------------------------------------------------


@dataclass
class _StubVisionLLM:
    response: str = "a tiny red square"
    last_call: dict[str, Any] | None = None

    def describe(self, *, image_path: Path, prompt: str | None = None) -> str:
        self.last_call = {"image_path": image_path, "prompt": prompt}
        return self.response


def test_describe_image_returns_llm_text(tiny_png: Path) -> None:
    llm = _StubVisionLLM()
    text = describe_image(tiny_png, llm=llm, prompt="caption this")
    assert text == "a tiny red square"
    assert llm.last_call is not None
    assert llm.last_call["image_path"] == tiny_png
    assert llm.last_call["prompt"] == "caption this"


def test_describe_image_rejects_missing_file(tmp_path: Path) -> None:
    llm = _StubVisionLLM()
    with pytest.raises(ImageDescribeError):
        describe_image(tmp_path / "nope.png", llm=llm)


def test_describe_image_rejects_unsupported_format(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("not an image")
    llm = _StubVisionLLM()
    with pytest.raises(ImageDescribeError):
        describe_image(p, llm=llm)


def test_image_describe_tool_blocks_path_traversal(tmp_path: Path) -> None:
    llm = _StubVisionLLM()
    tool = make_image_describe_tool(repo_root=tmp_path, llm=llm)
    result = tool(path="../etc/passwd")
    assert result["ok"] is False
    assert "outside" in result["error"].lower() or "not found" in result["error"].lower()


# ---------------------------------------------------------------------------
# image_ocr
# ---------------------------------------------------------------------------


def test_ocr_image_uses_first_available_backend(tiny_png: Path) -> None:
    backend = OCRBackend(
        name="stub",
        is_available=lambda: True,
        extract=lambda path: f"OCR<{path.name}>",
    )
    text = ocr_image(tiny_png, backends=[backend])
    assert text == "OCR<img.png>"


def test_ocr_image_skips_unavailable_backends(tiny_png: Path) -> None:
    skipped = OCRBackend(
        name="missing",
        is_available=lambda: False,
        extract=lambda _: "",
    )
    used = OCRBackend(
        name="real",
        is_available=lambda: True,
        extract=lambda path: "ocr-text",
    )
    text = ocr_image(tiny_png, backends=[skipped, used])
    assert text == "ocr-text"


def test_ocr_image_no_backend_raises(tiny_png: Path) -> None:
    with pytest.raises(ImageOCRError):
        ocr_image(tiny_png, backends=[])


def test_image_ocr_tool_blocks_path_traversal(tmp_path: Path) -> None:
    tool = make_image_ocr_tool(repo_root=tmp_path)
    result = tool(path="../etc/passwd")
    assert result["ok"] is False
