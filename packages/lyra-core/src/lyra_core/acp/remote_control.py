"""Remote-control bridge over ACP (v3.7 L37-1).

Anthropic's Claude Code "Remote Control" lets a session that started
locally be driven from a second client (web / mobile). Lyra's
``acp/server.py`` ships the JSON-RPC handshake; this module adds the
session-attach + relay surface on top.

Two bright-lines apply (see plan §3):

* ``LBL-RC-AUTH`` — every attach requires a fresh, HMAC-signed token
  (default TTL 300 seconds); replay attempts raise ``RemoteAuthError``.
* ``LBL-RC-SCOPE`` — the relay refuses any tool call whose action
  kind is not in the session's pre-approved set; remote clients
  cannot upgrade their own scope.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional


_LBL_AUTH: str = "LBL-RC-AUTH"
_LBL_SCOPE: str = "LBL-RC-SCOPE"

DEFAULT_ATTACH_TTL_S: float = 300.0


class RemoteAuthError(RuntimeError):
    """Raised when an attach fails authentication."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"{_LBL_AUTH}: {reason}")
        self.bright_line = _LBL_AUTH


class RemoteScopeError(RuntimeError):
    """Raised when a relayed call falls outside the session's scope."""

    def __init__(self, action_kind: str) -> None:
        super().__init__(
            f"{_LBL_SCOPE}: action_kind={action_kind!r} is not in the "
            "session's pre-approved set"
        )
        self.bright_line = _LBL_SCOPE
        self.action_kind = action_kind


@dataclass(frozen=True)
class AttachToken:
    """One-shot HMAC-signed attach token."""

    session_id: str
    nonce: str
    issued_ts: float
    ttl_s: float
    signature: str

    def is_expired(self, *, now_ts: Optional[float] = None) -> bool:
        now = time.time() if now_ts is None else now_ts
        return (now - self.issued_ts) > self.ttl_s


def issue_token(
    *,
    session_id: str,
    secret: bytes,
    ttl_s: float = DEFAULT_ATTACH_TTL_S,
    now_ts: Optional[float] = None,
) -> AttachToken:
    issued = time.time() if now_ts is None else now_ts
    nonce = secrets.token_hex(16)
    payload = f"{session_id}|{nonce}|{issued:.6f}|{ttl_s:.6f}".encode("utf-8")
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return AttachToken(
        session_id=session_id, nonce=nonce, issued_ts=issued,
        ttl_s=ttl_s, signature=sig,
    )


def verify_token(token: AttachToken, *, secret: bytes,
                 now_ts: Optional[float] = None) -> None:
    """Raises ``RemoteAuthError`` if the token is invalid or expired."""
    if token.is_expired(now_ts=now_ts):
        raise RemoteAuthError(f"token expired (issued {token.issued_ts:.0f})")
    payload = (
        f"{token.session_id}|{token.nonce}|"
        f"{token.issued_ts:.6f}|{token.ttl_s:.6f}"
    ).encode("utf-8")
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, token.signature):
        raise RemoteAuthError("HMAC signature mismatch")


@dataclass
class RelayChannel:
    """One attached remote client."""

    channel_id: str
    session_id: str
    attached_ts: float
    history: list[dict[str, Any]] = field(default_factory=list)
    _open: bool = True

    @property
    def open(self) -> bool:
        return self._open

    def close(self) -> None:
        self._open = False

    def push(self, message: dict[str, Any]) -> None:
        self.history.append(message)


@dataclass
class RemoteSession:
    """One session that may host attached remote clients."""

    session_id: str
    secret: bytes
    pre_approved_kinds: frozenset[str]
    used_nonces: set[str] = field(default_factory=set)
    channels: dict[str, RelayChannel] = field(default_factory=dict)

    def issue_attach_token(self, *, ttl_s: float = DEFAULT_ATTACH_TTL_S) -> AttachToken:
        return issue_token(
            session_id=self.session_id, secret=self.secret, ttl_s=ttl_s,
        )

    def attach(self, token: AttachToken, *, now_ts: Optional[float] = None) -> RelayChannel:
        if token.session_id != self.session_id:
            raise RemoteAuthError("session_id mismatch")
        verify_token(token, secret=self.secret, now_ts=now_ts)
        if token.nonce in self.used_nonces:
            raise RemoteAuthError("nonce already used (replay refused)")
        self.used_nonces.add(token.nonce)
        channel_id = f"ch-{secrets.token_hex(6)}"
        ch = RelayChannel(
            channel_id=channel_id, session_id=self.session_id,
            attached_ts=time.time() if now_ts is None else now_ts,
        )
        self.channels[channel_id] = ch
        return ch

    def detach(self, channel_id: str) -> None:
        ch = self.channels.get(channel_id)
        if ch is None:
            return
        ch.close()
        # Keep the closed channel in the dict so audit can replay.

    def relay(self, channel_id: str, *, action_kind: str,
              message: dict[str, Any]) -> None:
        """Relay a message from a remote client. Enforces LBL-RC-SCOPE."""
        ch = self.channels.get(channel_id)
        if ch is None or not ch.open:
            raise RemoteScopeError(action_kind)
        if action_kind not in self.pre_approved_kinds:
            raise RemoteScopeError(action_kind)
        ch.push({"action_kind": action_kind, "message": message})


@dataclass
class RelayHub:
    """Registry of active RemoteSessions keyed by session_id."""

    sessions: dict[str, RemoteSession] = field(default_factory=dict)

    def register(self, session: RemoteSession) -> None:
        if session.session_id in self.sessions:
            raise ValueError(f"session {session.session_id!r} already registered")
        self.sessions[session.session_id] = session

    def get(self, session_id: str) -> RemoteSession:
        return self.sessions[session_id]

    def all_session_ids(self) -> tuple[str, ...]:
        return tuple(self.sessions.keys())


__all__ = [
    "AttachToken",
    "DEFAULT_ATTACH_TTL_S",
    "RelayChannel",
    "RelayHub",
    "RemoteAuthError",
    "RemoteScopeError",
    "RemoteSession",
    "issue_token",
    "verify_token",
]
