"""Tests for ``paste-as-image`` (Wave-C Task 15).

Contract:

1. ``detect_image_paste(text)`` returns ``(mime, b64payload, residual)``
   when ``text`` is (or contains) a base64-encoded PNG/JPEG; otherwise
   returns ``None``.
2. ``write_attachment(session, mime, b64payload)`` decodes the bytes,
   chooses the next ordinal under
   ``<sessions_root>/<session_id>/attachments/``, writes ``<n>.<ext>``,
   and returns the on-disk :class:`pathlib.Path`.
3. The pasted prompt is rewritten so the LLM sees ``[Image #N]``
   instead of the raw payload — ``substitute_image_tokens`` handles
   the in-place rewrite.
4. The whole pipeline is a no-op when the input has no image — text
   passes through untouched (so we never break plain pasting).
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from lyra_cli.interactive.paste import (
    detect_image_paste,
    substitute_image_tokens,
    write_attachment,
)
from lyra_cli.interactive.session import InteractiveSession


# A 1x1 transparent PNG. Smallest valid payload we can paste.
_PNG_BYTES = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9p7yMA8AAAAASUVORK5CYII="
)
_PNG_B64 = base64.b64encode(_PNG_BYTES).decode("ascii")
_PNG_DATA_URI = f"data:image/png;base64,{_PNG_B64}"

_JPEG_HEADER = bytes.fromhex("FFD8FFE000104A464946000101")  # SOI + JFIF
_JPEG_BYTES = _JPEG_HEADER + b"\x00" * 32 + bytes.fromhex("FFD9")  # EOI
_JPEG_B64 = base64.b64encode(_JPEG_BYTES).decode("ascii")


# ---------------------------------------------------------------------------
# detect_image_paste
# ---------------------------------------------------------------------------


def test_detect_data_uri_png() -> None:
    found = detect_image_paste(_PNG_DATA_URI)
    assert found is not None
    mime, payload, residual = found
    assert mime == "image/png"
    assert base64.b64decode(payload) == _PNG_BYTES
    # The residual prompt is empty when the entire paste was the data URI.
    assert residual.strip() == ""


def test_detect_inline_with_text() -> None:
    text = f"can you describe this? {_PNG_DATA_URI}"
    found = detect_image_paste(text)
    assert found is not None
    mime, _payload, residual = found
    assert mime == "image/png"
    # Surrounding text is preserved so we don't lose the user's prompt.
    assert "can you describe this?" in residual


def test_detect_raw_b64_jpeg_with_magic_bytes() -> None:
    """Raw base64 (no data: URI) must still be detectable when the
    decoded bytes start with a known image magic number."""
    found = detect_image_paste(_JPEG_B64)
    assert found is not None
    mime, payload, _residual = found
    assert mime == "image/jpeg"
    assert base64.b64decode(payload).startswith(b"\xff\xd8")


def test_detect_returns_none_for_plain_text() -> None:
    assert detect_image_paste("Hi! Just a normal message.") is None


# ---------------------------------------------------------------------------
# write_attachment + substitute_image_tokens
# ---------------------------------------------------------------------------


def test_write_attachment_picks_next_ordinal(tmp_path: Path) -> None:
    session = InteractiveSession(repo_root=tmp_path, sessions_root=tmp_path / "sessions")
    p1 = write_attachment(session, "image/png", _PNG_B64)
    p2 = write_attachment(session, "image/png", _PNG_B64)
    assert p1.name == "1.png"
    assert p2.name == "2.png"
    assert p1.read_bytes() == _PNG_BYTES
    assert p1.parent.name == "attachments"


def test_write_attachment_uses_session_dir(tmp_path: Path) -> None:
    sessions_root = tmp_path / "sessions"
    session = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="sess-test-0001",
    )
    p = write_attachment(session, "image/jpeg", _JPEG_B64)
    assert p.parent == sessions_root / "sess-test-0001" / "attachments"


def test_write_attachment_requires_sessions_root(tmp_path: Path) -> None:
    """Without ``sessions_root`` we have nowhere to write — the helper
    should raise rather than silently lose the upload."""
    session = InteractiveSession(repo_root=tmp_path)
    with pytest.raises(RuntimeError):
        write_attachment(session, "image/png", _PNG_B64)


def test_substitute_image_tokens_rewrites_prompt(tmp_path: Path) -> None:
    session = InteractiveSession(
        repo_root=tmp_path, sessions_root=tmp_path / "sessions"
    )
    text = f"please review {_PNG_DATA_URI}"
    rewritten, attachments = substitute_image_tokens(session, text)
    assert "[Image #1]" in rewritten
    assert _PNG_B64 not in rewritten  # the giant payload must be gone
    assert len(attachments) == 1


def test_substitute_image_tokens_passthrough(tmp_path: Path) -> None:
    session = InteractiveSession(
        repo_root=tmp_path, sessions_root=tmp_path / "sessions"
    )
    text = "no image here, just words."
    rewritten, attachments = substitute_image_tokens(session, text)
    assert rewritten == text
    assert attachments == []
