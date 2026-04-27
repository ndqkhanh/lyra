"""Wave-E Task 10b: ``image_ocr`` tool.

Tries every OCR backend in order: ``pytesseract`` (most common) →
``easyocr`` (better for non-Latin scripts). Both are opt-in via
``pip install lyra[vision]``. If no backend is installed the tool
returns a structured error rather than raising — the agent stays on
the happy path.

Backends are injectable through ``ocr_backends=`` so unit tests
exercise the chain without installing anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


__all__ = [
    "ImageOCRError",
    "OCRBackend",
    "ocr_image",
    "make_image_ocr_tool",
]


class ImageOCRError(Exception):
    pass


@dataclass(frozen=True)
class OCRBackend:
    name: str
    is_available: Callable[[], bool]
    extract: Callable[[Path], str]


def _try_pytesseract(path: Path) -> str:  # pragma: no cover — smoke
    import pytesseract  # type: ignore  # noqa: PLC0415
    from PIL import Image  # type: ignore  # noqa: PLC0415

    return pytesseract.image_to_string(Image.open(str(path))) or ""


def _has_pytesseract() -> bool:  # pragma: no cover — smoke
    try:
        import pytesseract  # type: ignore  # noqa: F401,PLC0415
        from PIL import Image  # type: ignore  # noqa: F401,PLC0415

        return True
    except ImportError:
        return False


def _try_easyocr(path: Path) -> str:  # pragma: no cover — smoke
    import easyocr  # type: ignore  # noqa: PLC0415

    reader = easyocr.Reader(["en"], gpu=False)
    return "\n".join(line[1] for line in reader.readtext(str(path)))


def _has_easyocr() -> bool:  # pragma: no cover — smoke
    try:
        import easyocr  # type: ignore  # noqa: F401,PLC0415

        return True
    except ImportError:
        return False


_DEFAULT_BACKENDS: tuple[OCRBackend, ...] = (
    OCRBackend("pytesseract", _has_pytesseract, _try_pytesseract),
    OCRBackend("easyocr", _has_easyocr, _try_easyocr),
)


def _validate_image(path: Path) -> None:
    if not path.exists():
        raise ImageOCRError(f"image not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}:
        raise ImageOCRError(
            f"unsupported image format {suffix!r}; expected common raster"
        )


def ocr_image(
    path: Path | str,
    *,
    backends: Sequence[OCRBackend] | None = None,
) -> str:
    p = Path(path)
    _validate_image(p)
    chain = backends if backends is not None else _DEFAULT_BACKENDS
    for backend in chain:
        if backend.is_available():
            return backend.extract(p)
    raise ImageOCRError(
        "no OCR backend installed (install pytesseract or easyocr)"
    )


def make_image_ocr_tool(
    *,
    repo_root: Path | str,
    backends: Sequence[OCRBackend] | None = None,
) -> Callable[..., dict[str, Any]]:
    root = Path(repo_root).resolve()

    def image_ocr(*, path: str) -> dict[str, Any]:
        try:
            target = (root / path).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ImageOCRError(
                    f"refusing image_ocr outside repo_root: {path}"
                ) from exc
            text = ocr_image(target, backends=backends)
        except ImageOCRError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "text": text, "path": str(target)}

    image_ocr.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "image_ocr",
        "description": "Extract text from a local image via OCR.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    }
    return image_ocr
