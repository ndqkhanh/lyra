"""
Durable session management with multi-device fan-out and presence awareness.

Sessions survive client disconnects so that an in-flight run continues
and late-joining devices receive the full event stream.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from lyra_streaming.models import AGEvent, DeviceInfo, Session

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Raised when a session operation cannot be completed."""


class PresenceTracker:
    """Tracks which devices are currently connected to each session.

    Provides eventual-consistency presence that the `SessionManager` can
    consult during broadcast fan-out.
    """

    def __init__(self) -> None:
        # session_id -> set of connected device_ids
        self._presence: dict[str, set[str]] = {}

    def mark_connected(self, session_id: str, device_id: str) -> None:
        """Record that *device_id* is now online for *session_id*."""
        if session_id not in self._presence:
            self._presence[session_id] = set()
        self._presence[session_id].add(device_id)
        logger.debug("Presence: device %s connected to session %s", device_id, session_id)

    def mark_disconnected(self, session_id: str, device_id: str) -> None:
        """Record that *device_id* has gone offline for *session_id*."""
        if session_id in self._presence:
            self._presence[session_id].discard(device_id)
            if not self._presence[session_id]:
                del self._presence[session_id]
        logger.debug("Presence: device %s disconnected from session %s", device_id, session_id)

    def get_presence(self, session_id: str) -> list[str]:
        """Return the list of device IDs currently online for *session_id*."""
        return sorted(self._presence.get(session_id, set()))

    def is_connected(self, session_id: str, device_id: str) -> bool:
        """Return ``True`` if *device_id* is currently present."""
        return device_id in self._presence.get(session_id, set())

    @property
    def active_sessions(self) -> list[str]:
        """Return session IDs that have at least one connected device."""
        return sorted(self._presence.keys())


class SessionManager:
    """Manages durable agent sessions.

    Sessions are keyed by ``session_id`` and can be created, resumed,
    closed, and fanned-out across multiple devices.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._resume_tokens: dict[str, str] = {}  # session_id -> resume_token
        self.presence = PresenceTracker()

    # ── CRUD ───────────────────────────────────────────────────────

    def create_session(self, user_id: str, metadata: dict[str, Any] | None = None) -> Session:
        """Create a new durable session for *user_id*.

        Args:
            user_id: The owning user identifier.
            metadata: Optional initial state to seed ``session.state``.

        Returns:
            A new `Session` instance.
        """
        session_id = str(uuid.uuid4())
        resume_token = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_active=now,
            state=metadata or {},
        )
        self._sessions[session_id] = session
        self._resume_tokens[session_id] = resume_token
        logger.info("Session %s created for user %s", session_id, user_id)
        return session

    def resume_session(self, session_id: str, resume_token: str) -> Session:
        """Resume a previously created session after a disconnect.

        Args:
            session_id: The session to resume.
            resume_token: Token issued at session creation (or last resume).

        Returns:
            The `Session` with ``last_active`` updated.

        Raises:
            SessionError: If the session does not exist, the token is
                invalid, or the session was explicitly closed.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError(f"Session {session_id} not found")

        expected_token = self._resume_tokens.get(session_id)
        if expected_token is None or resume_token != expected_token:
            raise SessionError(f"Invalid resume token for session {session_id}")

        # Rotate resume token on each successful resume
        new_token = str(uuid.uuid4())
        self._resume_tokens[session_id] = new_token

        session = Session(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            last_active=datetime.now(timezone.utc),
            state=session.state,
            devices=session.devices,
            run_id=session.run_id,
            sequence_number=session.sequence_number,
        )
        self._sessions[session_id] = session
        logger.info("Session %s resumed", session_id)
        return session

    def close_session(self, session_id: str) -> None:
        """Gracefully close a session.

        The session and its resume token are removed; any subsequent
        ``resume_session`` call will fail.

        Args:
            session_id: The session to close.

        Raises:
            SessionError: If the session does not exist.
        """
        if session_id not in self._sessions:
            raise SessionError(f"Session {session_id} not found")

        del self._sessions[session_id]
        self._resume_tokens.pop(session_id, None)
        logger.info("Session %s closed", session_id)

    def get_session(self, session_id: str) -> Session | None:
        """Return a session by ID, or ``None``."""
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[Session]:
        """Return all currently active (not closed) sessions."""
        return list(self._sessions.values())

    # ── Multi-device ───────────────────────────────────────────────

    def add_device(self, session_id: str, device_info: DeviceInfo) -> Session:
        """Register a device with a session.

        Args:
            session_id: Target session.
            device_info: Descriptor for the connecting device.

        Returns:
            Updated `Session`.

        Raises:
            SessionError: If the session does not exist.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError(f"Session {session_id} not found")

        new_devices = dict(session.devices)
        new_devices[device_info.device_id] = device_info

        session = Session(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            last_active=datetime.now(timezone.utc),
            state=session.state,
            devices=new_devices,
            run_id=session.run_id,
            sequence_number=session.sequence_number,
        )
        self._sessions[session_id] = session
        logger.info("Device %s added to session %s", device_info.device_id, session_id)
        return session

    def remove_device(self, session_id: str, device_id: str) -> Session:
        """Remove a device from a session.

        Args:
            session_id: Target session.
            device_id: Device to remove.

        Returns:
            Updated `Session`.

        Raises:
            SessionError: If the session does not exist.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError(f"Session {session_id} not found")

        new_devices = dict(session.devices)
        new_devices.pop(device_id, None)

        session = Session(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            last_active=datetime.now(timezone.utc),
            state=session.state,
            devices=new_devices,
            run_id=session.run_id,
            sequence_number=session.sequence_number,
        )
        self._sessions[session_id] = session
        self.presence.mark_disconnected(session_id, device_id)
        logger.info("Device %s removed from session %s", device_id, session_id)
        return session

    def broadcast(self, session_id: str, event: AGEvent) -> list[str]:
        """Return the device IDs that should receive *event*.

        The actual transport-level send is handled by the WebSocket
        server; this method returns the list of online device IDs for
        the session so the server can fan-out.

        Args:
            session_id: Target session.
            event: The event to broadcast.

        Returns:
            List of online device IDs for *session_id*.

        Raises:
            SessionError: If the session does not exist.
        """
        if session_id not in self._sessions:
            raise SessionError(f"Session {session_id} not found")
        return self.presence.get_presence(session_id)

    # ── State helpers ──────────────────────────────────────────────

    def update_state(self, session_id: str, state: dict[str, Any]) -> Session:
        """Replace the session state snapshot.

        Args:
            session_id: Target session.
            state: New full state dictionary.

        Returns:
            Updated `Session`.

        Raises:
            SessionError: If the session does not exist.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError(f"Session {session_id} not found")

        session = Session(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            last_active=datetime.now(timezone.utc),
            state=state,
            devices=session.devices,
            run_id=session.run_id,
            sequence_number=session.sequence_number,
        )
        self._sessions[session_id] = session
        return session
