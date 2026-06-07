"""
Lyra Relay Server — self-hostable outbound-only relay for remote access.

Implements §4.29 Remote Access: an outbound-only WebSocket relay that lets
users drive their local Lyra sessions from phone, browser, or any device
without opening inbound ports.

Architecture (from Claude Code Remote Control, §3.1):
  1. Local Lyra process makes outbound WebSocket to the relay
  2. Relay registers the session and polls/stays connected
  3. Remote client connects to relay (browser/phone)
  4. Relay routes messages between remote client and local session
  5. Short-lived scoped credentials, TLS end-to-end

Key advantage over Claude Code: Lyra sessions survive terminal close
because they're hosted by the §4.13 supervisor/daemon.

References
----------
- Claude Code Remote Control: https://code.claude.com/docs/en/remote-control
- Lyra §4.29 Remote Access Plan: plans/4.29-remote-access.md
- Lyra §4.13 Swarm Plan: plans/4.13-swarm-fleet.md
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class SessionStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    TIMEOUT = "timeout"


class ClientType(str, Enum):
    LOCAL = "local"     # The Lyra process on the user's machine
    REMOTE = "remote"   # Browser, phone, or external client


@dataclass
class RelaySession:
    """A session registered with the relay.

    Attributes:
        session_id: Unique session identifier.
        name: Human-readable session name.
        local_ws: WebSocket connection to the local Lyra process.
        status: Current connection status.
        created_at: Unix timestamp of session creation.
        last_heartbeat: Unix timestamp of last heartbeat from local.
        credential_hash: HMAC of the credential used to register.
        metadata: Arbitrary session metadata (working dir, model, etc.).
    """

    session_id: str
    name: str
    status: SessionStatus = SessionStatus.ONLINE
    created_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    credential_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # Transport — set after init
    local_ws: Any = None
    remote_clients: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelayCredential:
    """A short-lived scoped credential for relay access.

    Each credential is scoped to a single purpose (register, attach, admin)
    and expires independently. Multiple short-lived credentials per session
    means compromise of one doesn't compromise all.

    Attributes:
        token: The credential token (sent to client).
        purpose: What this credential can do.
        session_id: Which session it's scoped to (None = all).
        expires_at: Unix timestamp of expiry.
    """

    token: str
    purpose: str
    session_id: Optional[str]
    expires_at: float

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


# ---------------------------------------------------------------------------
# Relay server
# ---------------------------------------------------------------------------


class RelayServer:
    """Self-hostable WebSocket relay for Lyra remote access.

    Usage (standalone)::

        relay = RelayServer(host="0.0.0.0", port=9090, secret_key="...")
        await relay.start()

    Usage (embedded in Lyra server)::

        from lyra.server.app import app
        relay = RelayServer(secret_key=os.environ["LYRA_RELAY_KEY"])
        app.mount("/relay", relay.as_asgi_app())
    """

    # Session timeout: if no heartbeat for this long, mark as offline
    SESSION_TIMEOUT_SECONDS = 600  # 10 minutes (matches Claude Code)

    # Credential lifetimes
    CREDENTIAL_REGISTER_TTL = 3600    # 1 hour to register a session
    CREDENTIAL_ATTACH_TTL = 7200      # 2 hours to attach to a session
    CREDENTIAL_ADMIN_TTL = 300        # 5 minutes for admin operations

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9090,
        secret_key: Optional[str] = None,
    ) -> None:
        self._host = host
        self._port = port
        self._secret_key = secret_key or secrets.token_hex(32)

        self._sessions: dict[str, RelaySession] = {}
        self._credentials: dict[str, RelayCredential] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def register_session(
        self,
        name: str,
        credential: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Register a new session with the relay.

        Args:
            name: Human-readable session name.
            credential: Registration credential (from local Lyra process).
            metadata: Optional session metadata.

        Returns:
            (session_id, attach_credential) tuple.

        Raises:
            ValueError: If the registration credential is invalid or expired.
        """
        self._verify_credential(credential, "register")

        session_id = f"lyra-{secrets.token_hex(6)}"
        attach_cred = self._issue_credential(
            purpose="attach",
            session_id=session_id,
            ttl=self.CREDENTIAL_ATTACH_TTL,
        )

        session = RelaySession(
            session_id=session_id,
            name=name,
            credential_hash=self._hash(credential),
            metadata=metadata or {},
        )
        self._sessions[session_id] = session

        logger.info("session registered", session_id=session_id, name=name)
        return session_id, attach_cred

    def get_session(self, session_id: str) -> Optional[RelaySession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions with their status."""
        return [
            {
                "session_id": s.session_id,
                "name": s.name,
                "status": s.status.value,
                "remote_clients": len(s.remote_clients),
                "created_at": s.created_at,
                "metadata": s.metadata,
            }
            for s in self._sessions.values()
        ]

    def remove_session(self, session_id: str, admin_credential: str) -> None:
        """Remove a session (admin operation).

        Args:
            session_id: Session to remove.
            admin_credential: Admin credential for authorization.

        Raises:
            ValueError: If credential is invalid.
            KeyError: If session doesn't exist.
        """
        self._verify_credential(admin_credential, "admin")
        session = self._sessions.pop(session_id, None)
        if session is None:
            raise KeyError(f"Session {session_id} not found")
        logger.info("session removed", session_id=session_id)

    # ------------------------------------------------------------------
    # Heartbeat and timeout
    # ------------------------------------------------------------------

    def heartbeat(self, session_id: str) -> None:
        """Record a heartbeat from the local Lyra process."""
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.last_heartbeat = time.time()
        if session.status == SessionStatus.OFFLINE:
            session.status = SessionStatus.ONLINE
            logger.info("session reconnected", session_id=session_id)

    async def cleanup_timeouts(self) -> list[str]:
        """Mark timed-out sessions as offline. Run periodically.

        Returns:
            List of session IDs that were marked offline.
        """
        now = time.time()
        timed_out = []
        for sid, session in self._sessions.items():
            if (
                session.status == SessionStatus.ONLINE
                and now - session.last_heartbeat > self.SESSION_TIMEOUT_SECONDS
            ):
                session.status = SessionStatus.TIMEOUT
                timed_out.append(sid)
                logger.warning("session timed out", session_id=sid)

        return timed_out

    # ------------------------------------------------------------------
    # Credential management
    # ------------------------------------------------------------------

    def issue_registration_credential(self) -> str:
        """Issue a credential that allows registering a new session."""
        return self._issue_credential("register", None, self.CREDENTIAL_REGISTER_TTL)

    def issue_admin_credential(self) -> str:
        """Issue a short-lived admin credential."""
        return self._issue_credential("admin", None, self.CREDENTIAL_ADMIN_TTL)

    def verify_attach(self, session_id: str, credential: str) -> bool:
        """Verify that a credential allows attaching to a session.

        Args:
            session_id: The session to attach to.
            credential: The attach credential.

        Returns:
            True if the credential is valid for this session.
        """
        try:
            self._verify_credential(credential, "attach", session_id)
            return True
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the relay server (placeholder for actual WebSocket server).

        In production, this would start an aiohttp or uvicorn WebSocket
        server. The integration point is:

        .. code-block:: python

            from aiohttp import web

            app = web.Application()
            app.router.add_get("/ws/{session_id}", self._handle_ws)
            web.run_app(app, host=self._host, port=self._port)
        """
        self._running = True
        logger.info(
            "relay server started",
            host=self._host,
            port=self._port,
        )

        # Background cleanup task
        while self._running:
            await asyncio.sleep(30)
            await self.cleanup_timeouts()

    async def stop(self) -> None:
        """Stop the relay server."""
        self._running = False
        logger.info("relay server stopped")

    # ------------------------------------------------------------------
    # QR code generation helper
    # ------------------------------------------------------------------

    @staticmethod
    def generate_session_url(relay_host: str, session_id: str, credential: str) -> str:
        """Generate a session URL that can be encoded as a QR code.

        Args:
            relay_host: The relay server's public hostname.
            session_id: The session to connect to.
            credential: The attach credential.

        Returns:
            A URL that opens the Lyra web client.
        """
        return (
            f"https://{relay_host}/lyra/attach"
            f"?session={session_id}"
            f"&credential={credential}"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _issue_credential(
        self,
        purpose: str,
        session_id: Optional[str],
        ttl: int,
    ) -> str:
        """Issue a short-lived credential."""
        token = secrets.token_urlsafe(32)
        cred = RelayCredential(
            token=token,
            purpose=purpose,
            session_id=session_id,
            expires_at=time.time() + ttl,
        )
        self._credentials[token] = cred
        return token

    def _verify_credential(
        self,
        token: str,
        purpose: str,
        session_id: Optional[str] = None,
    ) -> None:
        """Verify a credential is valid. Raises ValueError if not."""
        cred = self._credentials.get(token)
        if cred is None:
            raise ValueError("Unknown credential")
        if cred.is_expired:
            self._credentials.pop(token, None)
            raise ValueError("Credential expired")
        if cred.purpose != purpose:
            raise ValueError(
                f"Credential purpose mismatch: {cred.purpose} != {purpose}"
            )
        if session_id is not None and cred.session_id != session_id:
            raise ValueError(
                f"Credential session mismatch: {cred.session_id} != {session_id}"
            )

    @staticmethod
    def _hash(data: str) -> str:
        """Compute a non-reversible hash for credential storage."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
