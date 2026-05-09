"""Wave-C Task 15: detect & extract images pasted into the REPL prompt.

Paste-as-image is the small-but-mighty UX that turns the CLI into a
real multimodal interface — paste a screenshot of a stack-trace, the
agent sees it on the next turn. The full multimodal pipeline (OCR,
vision-tower routing) lands in Wave F; this module ships the
*plumbing*: detect base64 PNG/JPEG payloads in the prompt buffer,
write them to ``<sessions_root>/<session_id>/attachments/<n>.<ext>``,
and substitute ``[Image #N]`` so the LLM stream stays clean text.

Why this design?

- **Pure function detection.** ``detect_image_paste`` returns a tuple
  rather than mutating anything; the input/output is trivially
  testable without prompt_toolkit installed.
- **Magic-byte sniff fallback.** Some terminals strip the
  ``data:image/png;base64,`` prefix during clipboard transit; we still
  match on raw base64 when the decoded bytes start with PNG (\\x89PNG)
  or JPEG (\\xff\\xd8) magic numbers.
- **Per-session attachment dirs.** All attachments live under the
  session's on-disk root so ``/export`` (Task 2) can bundle them with
  the transcript without us tracking a separate registry.
- **No dependency on PIL.** Decoding is via ``base64.b64decode``; we
  don't open or re-encode the image. OCR / preview render is Wave F.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .session import InteractiveSession


# Greedy match for ``data:image/<ext>;base64,<payload>`` data URIs.
# The payload class is wide on purpose — base64 alphabet plus padding,
# but no whitespace; we trim trailing whitespace separately so a paste
# ending in a newline still detects.
_DATA_URI_RE = re.compile(
    r"data:image/(?P<ext>png|jpe?g|webp|gif);base64,(?P<payload>[A-Za-z0-9+/=]+)"
)

# Magic-byte sniffing for raw base64 (no data: URI). Order matters —
# match the most specific signatures first.
_MAGIC_NUMBERS: tuple[tuple[bytes, str, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
    (b"RIFF", "image/webp", "webp"),  # WEBP RIFF container
)


@dataclass(frozen=True)
class _Detected:
    """Internal: parsed bits of one detected image paste."""

    mime: str
    ext: str
    payload: str
    residual: str


def detect_image_paste(text: str) -> tuple[str, str, str] | None:
    """Find the first image payload in ``text``.

    Returns ``(mime, base64_payload, residual_text)``. ``residual_text``
    is the user prompt with the payload removed, so callers can keep the
    surrounding question intact when substituting ``[Image #N]``.

    Returns ``None`` when no image is present, leaving plain pastes
    fully untouched.
    """
    found = _detect(text)
    if found is None:
        return None
    return found.mime, found.payload, found.residual


def _detect(text: str) -> _Detected | None:
    if not text:
        return None
    # Pass 1: data URI (the well-formed case most terminals produce).
    match = _DATA_URI_RE.search(text)
    if match:
        ext = match.group("ext")
        if ext == "jpg":
            ext = "jpeg"
        residual = (text[: match.start()] + text[match.end():]).strip()
        return _Detected(
            mime=f"image/{ext}",
            ext=_normalise_ext(ext),
            payload=match.group("payload"),
            residual=residual,
        )

    # Pass 2: raw base64 — try decoding the whole input and sniffing
    # magic bytes. This is intentionally narrow (only when the entire
    # paste is one base64 blob) so we don't false-positive on prose
    # that happens to contain base64-shaped substrings.
    candidate = text.strip()
    if not candidate or any(ch in candidate for ch in (" ", "\n")):
        return None
    try:
        raw = base64.b64decode(candidate, validate=True)
    except (ValueError, base64.binascii.Error):
        return None
    for magic, mime, ext in _MAGIC_NUMBERS:
        if raw.startswith(magic):
            return _Detected(mime=mime, ext=ext, payload=candidate, residual="")
    return None


def _normalise_ext(ext: str) -> str:
    return {
        "png": "png",
        "jpeg": "jpg",
        "jpg": "jpg",
        "gif": "gif",
        "webp": "webp",
    }.get(ext, "bin")


# ---------------------------------------------------------------------------
# Attachment writer + prompt rewriter
# ---------------------------------------------------------------------------


def write_attachment(
    session: "InteractiveSession", mime: str, b64_payload: str
) -> Path:
    """Write the decoded bytes under the session's attachment dir.

    Raises ``RuntimeError`` when the session has no on-disk home
    (``sessions_root`` is None) — silently dropping a paste would be
    surprising and hide the user's data.
    """
    sessions_root = getattr(session, "sessions_root", None)
    if sessions_root is None:
        raise RuntimeError(
            "session has no sessions_root; can't persist image paste. "
            "Construct the session with sessions_root=... or use "
            "InteractiveSession.from_config(...)."
        )
    session_id = getattr(session, "session_id", None)
    if not session_id:
        raise RuntimeError("session_id is required to write an attachment")
    folder = Path(sessions_root) / session_id / "attachments"
    folder.mkdir(parents=True, exist_ok=True)

    ext = _ext_from_mime(mime)
    next_n = _next_ordinal(folder, ext)
    out = folder / f"{next_n}.{ext}"
    out.write_bytes(base64.b64decode(b64_payload))
    return out


def _ext_from_mime(mime: str) -> str:
    return {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/gif": "gif",
        "image/webp": "webp",
    }.get(mime, "bin")


def _next_ordinal(folder: Path, ext: str) -> int:
    """Return ``max(existing_ordinal) + 1`` so attachments are 1-indexed
    in user-visible order regardless of paste order or restarts."""
    existing = [
        int(p.stem)
        for p in folder.glob(f"*.{ext}")
        if p.stem.isdigit()
    ]
    # Be conservative across extensions: if the folder already contains
    # `1.png` and we're adding a `.jpg`, we want to start at 2.
    cross_ext = [
        int(p.stem)
        for p in folder.iterdir()
        if p.is_file() and p.stem.isdigit()
    ]
    return max(existing + cross_ext + [0]) + 1


def substitute_image_tokens(
    session: "InteractiveSession", text: str
) -> tuple[str, list[Path]]:
    """Replace every detected image paste with ``[Image #N]`` tokens.

    Returns the rewritten prompt and the list of on-disk paths so the
    caller can attach them to the next LLM call (Wave F).
    """
    attachments: list[Path] = []
    rewritten = text
    while True:
        found = _detect(rewritten)
        if found is None:
            return rewritten, attachments
        path = write_attachment(session, found.mime, found.payload)
        attachments.append(path)
        token = f"[Image #{len(attachments)}]"
        # Substitute exactly the run we matched so adjacent text wins.
        if found.residual:
            rewritten = (
                found.residual
                + (" " if not found.residual.endswith(" ") else "")
                + token
            )
        else:
            rewritten = token


__all__ = ["detect_image_paste", "write_attachment", "substitute_image_tokens"]
