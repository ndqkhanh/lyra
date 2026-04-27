"""``pdf_extract`` tool — best-effort text extraction from a PDF.

The tool looks at the file header to confirm it's a PDF, then delegates
to any installed backend in this order:

1. ``pypdf`` (``pypdf.PdfReader``)
2. ``pdfminer`` (``pdfminer.high_level.extract_text``)

If neither is installed, returns a structured error rather than
raising — the agent stays on the happy path.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

__all__ = ["PdfExtractError", "extract_text_from_pdf", "make_pdf_extract_tool"]


class PdfExtractError(Exception):
    pass


@dataclass(frozen=True)
class _Backend:
    name: str
    is_available: Callable[[], bool]
    extract: Callable[[Path], str]


def _try_pypdf(path: Path) -> str:
    import pypdf  # type: ignore  # noqa: PLC0415

    reader = pypdf.PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _has_pypdf() -> bool:
    try:
        import pypdf  # type: ignore  # noqa: F401,PLC0415

        return True
    except ImportError:
        return False


def _try_pdfminer(path: Path) -> str:
    from pdfminer.high_level import extract_text  # type: ignore  # noqa: PLC0415

    return extract_text(str(path)) or ""


def _has_pdfminer() -> bool:
    try:
        from pdfminer.high_level import extract_text  # type: ignore  # noqa: F401,PLC0415

        return True
    except ImportError:
        return False


_BACKENDS: tuple[_Backend, ...] = (
    _Backend("pypdf", _has_pypdf, _try_pypdf),
    _Backend("pdfminer", _has_pdfminer, _try_pdfminer),
)


def extract_text_from_pdf(path: Path | str) -> str:
    """Extract text using the first available backend.

    Raises :class:`PdfExtractError` if the file is not a PDF, does not
    exist, or no backend is installed.
    """
    p = Path(path)
    if not p.exists():
        raise PdfExtractError(f"pdf not found: {p}")
    with p.open("rb") as fh:
        magic = fh.read(5)
    if magic != b"%PDF-":
        raise PdfExtractError(f"not a PDF (bad magic): {p}")
    for backend in _BACKENDS:
        if backend.is_available():
            return backend.extract(p)
    raise PdfExtractError(
        "no pdf backend installed (install pypdf or pdfminer.six)"
    )


def make_pdf_extract_tool(*, repo_root: Path | str) -> Callable[..., dict]:
    root = Path(repo_root).resolve()

    def pdf_extract(*, path: str, max_chars: int | None = None) -> dict:
        try:
            target = (root / path).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise PdfExtractError(
                    f"refusing pdf_extract outside repo_root: {path}"
                ) from exc
            text = extract_text_from_pdf(target)
        except PdfExtractError as exc:
            return {"ok": False, "error": str(exc)}

        if max_chars is not None and len(text) > max_chars:
            return {
                "ok": True,
                "text": text[:max_chars],
                "truncated": True,
                "length": len(text),
            }
        return {"ok": True, "text": text, "truncated": False, "length": len(text)}

    pdf_extract.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "pdf_extract",
        "description": "Extract text from a PDF under repo_root.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
        },
    }
    return pdf_extract
