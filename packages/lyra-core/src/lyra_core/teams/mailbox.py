"""L311-3 — Per-teammate mailbox with idle notifications.

A :class:`Mailbox` is a directory of per-recipient inboxes. Every
message is one Markdown file (sortable filename: timestamp + sender +
nonce); ``read(name)`` lists all messages addressed to ``name`` in
chronological order.

The mailbox is intentionally **append-only from the sender side** —
nothing ever rewrites an existing message in place. ``mark_read`` only
moves a message into a per-recipient ``_read/`` subdirectory; ``purge``
deletes read messages older than a TTL.

This stays stdlib-only and human-inspectable — a developer can
``ls ~/.lyra/teams/{team}/mailbox/security/`` to read what messages
the security teammate has received, including the lead's idle
notifications.
"""
from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


MessageKind = Literal["info", "task", "idle", "alert"]


_FILENAME_RE = re.compile(
    r"^(?P<ts>\d{13})-(?P<sender>[a-z0-9-]+)-(?P<nonce>[0-9a-f]{6})\.md$"
)


@dataclass(frozen=True)
class MailboxMessage:
    """One message in a recipient's inbox."""

    sender: str
    recipient: str
    kind: MessageKind
    body: str
    created_at: float
    path: Path

    @property
    def is_idle(self) -> bool:
        return self.kind == "idle"


class Mailbox:
    """Directory-backed per-recipient mailbox.

    Layout::

        {root}/
        ├── lead/
        │   ├── 1715266020000-security-1f3a4c.md
        │   └── _read/
        ├── security/
        │   └── 1715266045000-lead-9b1c2e.md
        └── performance/
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- registration ---------------------------------------------

    def ensure(self, name: str) -> Path:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "_read").mkdir(parents=True, exist_ok=True)
        return d

    # ---- send / read / mark / purge --------------------------------

    def send(
        self,
        *,
        sender: str,
        recipient: str,
        body: str,
        kind: MessageKind = "info",
    ) -> Path:
        if not _is_safe_name(sender) or not _is_safe_name(recipient):
            raise ValueError(
                f"sender/recipient must be lowercase id, got {sender!r} -> {recipient!r}"
            )
        if kind not in ("info", "task", "idle", "alert"):
            raise ValueError(f"unknown message kind {kind!r}")
        target_dir = self.ensure(recipient)
        ts = int(time.time() * 1000)
        nonce = secrets.token_hex(3)
        path = target_dir / f"{ts:013d}-{sender}-{nonce}.md"
        head = (
            "---\n"
            f"from: {sender}\n"
            f"to: {recipient}\n"
            f"kind: {kind}\n"
            f"created_at: {ts}\n"
            "---\n"
        )
        path.write_text(head + (body or ""), encoding="utf-8")
        return path

    def read(self, recipient: str, *, include_read: bool = False) -> list[MailboxMessage]:
        """Return all messages addressed to ``recipient`` in chronological order."""
        d = self.root / recipient
        if not d.exists():
            return []
        out: list[MailboxMessage] = []
        targets = [d]
        if include_read:
            targets.append(d / "_read")
        for tgt in targets:
            if not tgt.exists():
                continue
            for p in sorted(tgt.glob("*.md")):
                m = _FILENAME_RE.match(p.name)
                if m is None:
                    continue
                msg = _load(p, recipient=recipient)
                if msg is not None:
                    out.append(msg)
        return out

    def mark_read(self, message: MailboxMessage) -> None:
        target = message.path.parent / "_read" / message.path.name
        if message.path.exists():
            message.path.replace(target)

    def purge_older_than(self, *, recipient: str, ttl_s: float) -> int:
        """Remove read messages whose ``created_at`` is older than ``ttl_s`` seconds.
        Returns the count removed."""
        cutoff = time.time() - ttl_s
        d = self.root / recipient / "_read"
        if not d.exists():
            return 0
        removed = 0
        for p in d.glob("*.md"):
            m = _FILENAME_RE.match(p.name)
            if m is None:
                continue
            ts_ms = int(m.group("ts"))
            if ts_ms / 1000 < cutoff:
                p.unlink()
                removed += 1
        return removed

    def message_count(self) -> int:
        """Total messages across all inboxes (read + unread). For reporting."""
        total = 0
        for p in self.root.rglob("*.md"):
            if _FILENAME_RE.match(p.name):
                total += 1
        return total


# ---- internal helpers -------------------------------------------------


def _is_safe_name(name: str) -> bool:
    return bool(name) and bool(re.match(r"^[a-z0-9][a-z0-9-]*$", name))


def _load(path: Path, *, recipient: str) -> MailboxMessage | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    head = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, str] = {}
    for line in head.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    sender = meta.get("from", "?")
    kind = meta.get("kind", "info")
    if kind not in ("info", "task", "idle", "alert"):
        kind = "info"
    try:
        ts_ms = int(meta.get("created_at", "0"))
    except ValueError:
        ts_ms = 0
    return MailboxMessage(
        sender=sender,
        recipient=recipient,
        kind=kind,  # type: ignore[arg-type]
        body=body.rstrip(),
        created_at=ts_ms / 1000.0,
        path=path,
    )


__all__ = [
    "Mailbox",
    "MailboxMessage",
    "MessageKind",
]
