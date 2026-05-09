"""Wave-E Task 10a: ``image_describe`` tool.

Calls the active LLM with an image attachment and returns a short
caption / description. The LLM client is injectable so unit tests
never hit the network; production callers wire the project-wide
provider.

Resolves Wave-C "paste-as-image" stubs: when the user pastes an
image the REPL stores it as an attachment and substitutes
``[Image #N]``. The agent can later call ``image_describe(path=...)``
on the attachment path to get a description back.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable


__all__ = [
    "ImageDescribeError",
    "VisionLLM",
    "describe_image",
    "make_image_describe_tool",
]


class ImageDescribeError(Exception):
    pass


@runtime_checkable
class VisionLLM(Protocol):
    """Tiny LLM surface the tool needs."""

    def describe(self, *, image_path: Path, prompt: str | None = None) -> str: ...


def _validate_image(path: Path) -> None:
    if not path.exists():
        raise ImageDescribeError(f"image not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        raise ImageDescribeError(
            f"unsupported image format {suffix!r}; expected png/jpg/jpeg/gif/webp/bmp"
        )


def describe_image(
    path: Path | str,
    *,
    llm: VisionLLM,
    prompt: str | None = None,
) -> str:
    p = Path(path)
    _validate_image(p)
    return llm.describe(image_path=p, prompt=prompt)


def make_image_describe_tool(
    *,
    repo_root: Path | str,
    llm: VisionLLM,
) -> Callable[..., dict[str, Any]]:
    root = Path(repo_root).resolve()

    def image_describe(*, path: str, prompt: str | None = None) -> dict[str, Any]:
        try:
            target = (root / path).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ImageDescribeError(
                    f"refusing image_describe outside repo_root: {path}"
                ) from exc
            text = describe_image(target, llm=llm, prompt=prompt)
        except ImageDescribeError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "description": text, "path": str(target)}

    image_describe.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "image_describe",
        "description": "Describe a local image via the active vision LLM.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prompt": {"type": "string"},
            },
            "required": ["path"],
        },
    }
    return image_describe
