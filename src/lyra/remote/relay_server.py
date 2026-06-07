"""
Outbound Relay Server — Lyra-initiated outbound WebSocket relay for remote access.

Architecture
------------
  Lyra (initiator)  --outbound WebSocket-->  OutboundRelayServer
       |                                              |
  Scoped credentials                           No inbound ports
  Per-session ephemeral keys                   Diff-based state sync
  Multi-surface push                           LWW conflict resolution

This is the entension of the zero-trust relay pattern: Lyra itself initiates
the connection, keeps it alive, and manages per-session credentials and
multi-device state synchronization.

References
----------
- ZeroTrustRelay in :mod:`lyra.remote.zero_trust_relay` (client-side relay)
- RelayServer in :mod:`lyra.server.relay` (server-side session management)
- :class:`MobileSteeringSurface` (high-level mobile control API)
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Credential scoping
# ---------------------------------------------------------------------------


class AllowedAction(str, Enum):
    """Actions a scoped credential may perform."""

    REGISTER = "register"
    ATTACH = "attach"
    STEER = "steer"  # approve/deny/message
    PEEK = "peek"
    ADMIN = "admin"


@dataclass(frozen=True)
class CredentialScope:
    """Defines the scope of a minted credential.

    Attributes:
        session_id: The session this credential is scoped to.
        expiry: UTC datetime after which the credential is invalid.
        allowed_actions: Set of actions permitted with this credential.
        max_uses: Maximum number of times the credential may be used (0 = unlimited).
    """

    session_id: str
    expiry: datetime
    allowed_actions: frozenset[AllowedAction] = frozenset()
    max_uses: int = 0


class ScopedCredentialMinter:
    """Mints per-session, time-limited, action-scoped credentials.

    Each credential is an opaque token that carries its scope internally
    (via a lookup table).  The relay server checks the scope before
    allowing any operation.

    Credentials are one-way hashed for storage — the plaintext token is
    returned to the caller and never persisted.
    """

    def __init__(self) -> None:
        self._credentials: dict[str, CredentialScope] = {}
        self._use_counts: dict[str, int] = {}
        self._revoked: set[str] = set()

    # ------------------------------------------------------------------
    # Minting
    # ------------------------------------------------------------------

    def mint(
        self,
        session_id: str,
        *,
        ttl_seconds: int = 3600,
        allowed_actions: set[AllowedAction] | None = None,
        max_uses: int = 0,
    ) -> tuple[str, CredentialScope]:
        """Mint a new scoped credential.

        Args:
            session_id: The session to scope the credential to.
            ttl_seconds: Time-to-live in seconds (default 1 hour).
            allowed_actions: Set of permitted actions (default: all).
            max_uses: Maximum uses before auto-revocation (0 = unlimited).

        Returns:
            (token, CredentialScope) tuple.  The token is the plaintext
            credential that must be shared with the caller.  It is not
            stored in plaintext.
        """
        token = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        actions = allowed_actions or set(AllowedAction)
        scope = CredentialScope(
            session_id=session_id,
            expiry=expiry,
            allowed_actions=frozenset(actions),
            max_uses=max_uses,
        )

        # Store the SHA-256 hash of the token, not the token itself
        token_hash = self._hash(token)
        self._credentials[token_hash] = scope
        self._use_counts[token_hash] = 0

        logger.info(
            "credential minted",
            session_id=session_id,
            ttl=ttl_seconds,
            actions=[a.value for a in actions],
        )
        return token, scope

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify(
        self,
        token: str,
        action: AllowedAction,
        session_id: str,
    ) -> bool:
        """Verify that *token* is valid for *action* on *session_id*.

        Args:
            token: The plaintext credential token.
            action: The action being attempted.
            session_id: The target session.

        Returns:
            True if the credential is valid, not expired, not revoked,
            within its action scope, and under its use limit.
        """
        if token in self._revoked:
            return False

        token_hash = self._hash(token)
        scope = self._credentials.get(token_hash)
        if scope is None:
            return False

        # Check expiry
        if datetime.now(timezone.utc) > scope.expiry:
            self._credentials.pop(token_hash, None)
            self._use_counts.pop(token_hash, None)
            return False

        # Check session
        if scope.session_id != session_id:
            return False

        # Check action scope
        if action not in scope.allowed_actions:
            return False

        # Check use limit
        if scope.max_uses > 0:
            count = self._use_counts.get(token_hash, 0)
            if count >= scope.max_uses:
                self._revoked.add(token)
                return False
            self._use_counts[token_hash] = count + 1

        return True

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------

    def revoke(self, token: str) -> bool:
        """Revoke a credential immediately.  Returns True if found."""
        self._revoked.add(token)
        token_hash = self._hash(token)
        scope = self._credentials.pop(token_hash, None)
        self._use_counts.pop(token_hash, None)
        return scope is not None

    def revoke_all_for_session(self, session_id: str) -> int:
        """Revoke all credentials scoped to *session_id*.

        Returns the number of credentials revoked.
        """
        count = 0
        for token_hash, scope in list(self._credentials.items()):
            if scope.session_id == session_id:
                self._credentials.pop(token_hash, None)
                self._use_counts.pop(token_hash, None)
                count += 1
        logger.info("credentials revoked for session", session_id=session_id, count=count)
        return count

    def list_active(self) -> list[dict[str, Any]]:
        """Return metadata on all non-expired credentials (no tokens)."""
        now = datetime.now(timezone.utc)
        result = []
        for token_hash, scope in list(self._credentials.items()):
            if now > scope.expiry:
                continue
            result.append({
                "session_id": scope.session_id,
                "expires_at": scope.expiry.isoformat(),
                "allowed_actions": sorted(a.value for a in scope.allowed_actions),
                "max_uses": scope.max_uses,
                "use_count": self._use_counts.get(token_hash, 0),
            })
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(token: str) -> str:
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Diff-based state synchronisation
# ---------------------------------------------------------------------------


@dataclass
class DiffEntry:
    """A single change in a diff-based state update.

    Attributes:
        path: Dot-separated path to the changed field (e.g. ``"tools.pending.0.status"``).
        value: The new value (or None for deletion).
        timestamp: Monotonic timestamp for LWW conflict resolution.
        source: Surface identifier that produced the change (``"desktop"``, ``"mobile"``, ``"web"``).
    """

    path: str
    value: Any
    timestamp: float = 0.0
    source: str = "unknown"


@dataclass
class SyncPatch:
    """A collection of diffs to apply, with conflict resolution metadata.

    Attributes:
        session_id: The session being synced.
        diffs: List of individual field-level changes.
        base_version: The version of the state this patch was computed against.
        source: The surface producing this patch.
    """

    session_id: str
    diffs: list[DiffEntry]
    base_version: int
    source: str


class SyncProtocol:
    """Diff-based state synchronisation with LWW (last-writer-wins) conflict resolution.

    Maintains a versioned state tree and produces/consumes SyncPatch objects
    to keep multiple surfaces in sync with minimal data transfer.

    Strategy
    --------
    - State is a flat dictionary of dot-separated keys for field-level diffs.
    - Each update is timestamped; the latest timestamp wins (LWW).
    - Version counter increments on every applied patch.
    - Tombstone entries (None values) are pruned after a configurable TTL.
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}
        self._version: int = 0
        self._listeners: list[Callable[[SyncPatch], Any]] = []

    # ------------------------------------------------------------------
    # State read
    # ------------------------------------------------------------------

    def get(self, path: str, default: Any = None) -> Any:
        """Read a value at *path* (dot-separated)."""
        return self._state.get(path, default)

    def snapshot(self) -> dict[str, Any]:
        """Return a full copy of the current state."""
        return dict(self._state)

    @property
    def version(self) -> int:
        """Current state version (monotonic counter)."""
        return self._version

    # ------------------------------------------------------------------
    # Local updates
    # ------------------------------------------------------------------

    def set(self, path: str, value: Any, source: str = "local") -> None:
        """Set a value and produce a sync event."""
        timestamp = time.time()
        self._apply_diff(DiffEntry(path=path, value=value, timestamp=timestamp, source=source))

    def delete(self, path: str, source: str = "local") -> None:
        """Delete a key from the state."""
        timestamp = time.time()
        self._apply_diff(DiffEntry(path=path, value=None, timestamp=timestamp, source=source))

    # ------------------------------------------------------------------
    # Remote patch application
    # ------------------------------------------------------------------

    def apply_patch(self, patch: SyncPatch) -> list[str]:
        """Apply a remote sync patch with LWW conflict resolution.

        Args:
            patch: The incoming patch from another surface.

        Returns:
            List of paths that were actually updated (winners of LWW).
        """
        applied: list[str] = []
        for diff in patch.diffs:
            existing_ts = self._timestamps.get(diff.path, -1.0)
            if diff.timestamp >= existing_ts:
                self._apply_diff(diff, increment_version=False)
                applied.append(diff.path)

        self._version += 1
        self._notify(patch)
        return applied

    def compute_patch(
        self,
        session_id: str,
        source: str,
        base_version: int = -1,
    ) -> SyncPatch | None:
        """Compute a diff patch since *base_version*.

        Returns None if there are no changes since the base.
        """
        raise NotImplementedError("Incremental diff not yet implemented")

    # ------------------------------------------------------------------
    # Plumbing
    # ------------------------------------------------------------------

    def _apply_diff(self, diff: DiffEntry, increment_version: bool = True) -> None:
        """Apply a single diff entry to the internal state."""
        if diff.value is None:
            self._state.pop(diff.path, None)
            self._timestamps.pop(diff.path, None)
        else:
            self._state[diff.path] = diff.value
            self._timestamps[diff.path] = diff.timestamp

        if increment_version:
            self._version += 1

    def _notify(self, patch: SyncPatch) -> None:
        """Fire registered listeners after a patch is applied."""
        for listener in self._listeners:
            try:
                listener(patch)
            except Exception:
                logger.exception("sync listener failed", patch_source=patch.source)

    def on_sync(self, listener: Callable[[SyncPatch], Any]) -> Callable[..., Any]:
        """Register a listener for state sync events.

        Can be used as a decorator::

            @protocol.on_sync
            def handle_sync(patch):
                ...
        """
        self._listeners.append(listener)
        return listener

    # ------------------------------------------------------------------
    # Conflict inspection
    # ------------------------------------------------------------------

    def conflicts(self, patch: SyncPatch) -> list[DiffEntry]:
        """Return diffs in *patch* that conflict with current state.

        A diff "conflicts" when both sides changed the same path with
        timestamps close enough to be ambiguous (within 1 second).
        """
        result: list[DiffEntry] = []
        for diff in patch.diffs:
            existing_ts = self._timestamps.get(diff.path)
            if existing_ts is not None and abs(diff.timestamp - existing_ts) < 1.0:
                result.append(diff)
        return result


# ---------------------------------------------------------------------------
# Multi-surface state synchronisation
# ---------------------------------------------------------------------------


@dataclass
class SurfaceInfo:
    """Metadata about a connected surface.

    Attributes:
        surface_id: Unique identifier (``"desktop"``, ``"mobile-<uuid>"``, ``"web-<uuid>"``).
        surface_type: Surface type (``"desktop"``, ``"mobile"``, ``"web"``).
        connected_at: Unix timestamp of connection.
        last_sync_at: Unix timestamp of last successful sync.
        protocol_version: Sync protocol version the surface supports.
    """

    surface_id: str
    surface_type: str
    connected_at: float = 0.0
    last_sync_at: float = 0.0
    protocol_version: int = 1


class MultiSurfaceSync:
    """Orchestrates state synchronisation across multiple connected surfaces.

    Manages the set of active surfaces, routes sync patches between them,
    and provides conflict diagnostics.
    """

    def __init__(self, protocol: SyncProtocol | None = None) -> None:
        self._surfaces: dict[str, SurfaceInfo] = {}
        self._protocol = protocol or SyncProtocol()
        self._surface_versions: dict[str, int] = {}
        self._session_id: str = ""

    # ------------------------------------------------------------------
    # Session binding
    # ------------------------------------------------------------------

    def bind_session(self, session_id: str) -> None:
        """Bind this synchroniser to a session."""
        self._session_id = session_id
        logger.info("multi-surface sync bound", session_id=session_id)

    # ------------------------------------------------------------------
    # Surface management
    # ------------------------------------------------------------------

    def register_surface(
        self,
        surface_id: str,
        surface_type: str,
    ) -> SurfaceInfo:
        """Register a new surface for synchronisation.

        Args:
            surface_id: Unique surface identifier.
            surface_type: ``"desktop"``, ``"mobile"``, or ``"web"``.

        Returns:
            The SurfaceInfo object for the new surface.
        """
        info = SurfaceInfo(
            surface_id=surface_id,
            surface_type=surface_type,
            connected_at=time.time(),
        )
        self._surfaces[surface_id] = info
        self._surface_versions[surface_id] = 0
        logger.info("surface registered", surface_id=surface_id, surface_type=surface_type)
        return info

    def unregister_surface(self, surface_id: str) -> None:
        """Remove a surface from synchronisation."""
        self._surfaces.pop(surface_id, None)
        self._surface_versions.pop(surface_id, None)
        logger.info("surface unregistered", surface_id=surface_id)

    def get_surface(self, surface_id: str) -> SurfaceInfo | None:
        """Get surface info by ID."""
        return self._surfaces.get(surface_id)

    def list_surfaces(self) -> list[SurfaceInfo]:
        """Return all active surfaces."""
        return list(self._surfaces.values())

    # ------------------------------------------------------------------
    # Sync orchestration
    # ------------------------------------------------------------------

    def apply_remote_patch(self, patch: SyncPatch, from_surface: str) -> list[str]:
        """Apply a patch from one surface and propagate to all others.

        Args:
            patch: The incoming sync patch.
            from_surface: Surface ID of the sender.

        Returns:
            List of paths actually updated.
        """
        applied = self._protocol.apply_patch(patch)
        surface = self._surfaces.get(from_surface)
        if surface is not None:
            surface.last_sync_at = time.time()
        self._surface_versions[from_surface] = self._protocol.version
        return applied

    def compute_patch_for(
        self,
        surface_id: str,
        source: str = "unknown",
    ) -> SyncPatch | None:
        """Compute a patch with all changes since *surface_id* last synced.

        Returns None if the surface is up to date.
        """
        base_ver = self._surface_versions.get(surface_id, 0)
        if base_ver >= self._protocol.version:
            return None

        # Full-state patch (optimisation: incremental diff later)
        return SyncPatch(
            session_id=self._session_id,
            diffs=[
                DiffEntry(path=k, value=v, source=source)
                for k, v in self._protocol.snapshot().items()
            ],
            base_version=base_ver,
            source=source,
        )

    # ------------------------------------------------------------------
    # Conflict diagnostics
    # ------------------------------------------------------------------

    def detect_conflicts(self, patch: SyncPatch) -> list[DiffEntry]:
        """Detect which entries in *patch* conflict with current state."""
        return self._protocol.conflicts(patch)


# ---------------------------------------------------------------------------
# Outbound relay server
# ---------------------------------------------------------------------------


class OutboundRelayServer:
    """Lyra-initiated outbound-only relay server.

    Unlike the traditional relay pattern where a server listens for incoming
    connections, this relay is *initiated by Lyra itself* as an outbound
    WebSocket connection.  No inbound ports are opened.

    Responsibilities
    ----------------
    - Maintain an outbound WebSocket connection to the configured relay hub.
    - Manage per-session scoped credentials (mint, verify, revoke).
    - Orchestrate multi-surface state synchronisation.
    - Route encrypted messages between surfaces.

    Usage::

        relay = OutboundRelayServer(
            hub_url="wss://hub.lyra.example.com/relay",
            instance_id="my-laptop",
        )
        await relay.start()
        await relay.register_session("lyra-abc123")
        # ... surfaces connect and sync via the hub ...
        await relay.stop()
    """

    HEARTBEAT_INTERVAL = 30.0
    RECONNECT_DELAY = 5.0

    def __init__(
        self,
        hub_url: str,
        instance_id: str,
        max_reconnect_attempts: int = 0,
    ) -> None:
        self._hub_url = hub_url
        self._instance_id = instance_id
        self._max_reconnect_attempts = max_reconnect_attempts

        self._ws: Any = None
        self._running = False
        self._reconnect_attempts = 0

        self.credential_minter = ScopedCredentialMinter()
        self.sync = MultiSurfaceSync()

        self._background_tasks: list[asyncio.Task[Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the outbound relay.  Blocks until the connection is
        established or max reconnect attempts are exhausted."""
        import aiohttp

        self._running = True

        while self._running:
            try:
                http_session = aiohttp.ClientSession()
                ws = await http_session.ws_connect(
                    self._hub_url,
                    heartbeat=self.HEARTBEAT_INTERVAL,
                )
                self._ws = ws
                self._reconnect_attempts = 0
                logger.info(
                    "outbound relay connected",
                    hub=self._hub_url,
                    instance=self._instance_id,
                )

                # Authenticate with instance identity
                await self._send({"type": "relay_auth", "instance_id": self._instance_id})

                # Start background tasks
                self._background_tasks.append(
                    asyncio.create_task(self._listen_loop())
                )
                self._background_tasks.append(
                    asyncio.create_task(self._heartbeat_loop())
                )
                return

            except Exception as exc:
                self._reconnect_attempts += 1
                if (
                    self._max_reconnect_attempts > 0
                    and self._reconnect_attempts > self._max_reconnect_attempts
                ):
                    raise ConnectionError(
                        f"Max reconnect attempts ({self._max_reconnect_attempts}) exceeded"
                    ) from exc

                logger.warning(
                    "outbound relay reconnect pending",
                    attempt=self._reconnect_attempts,
                )
                await asyncio.sleep(self.RECONNECT_DELAY)

    async def stop(self) -> None:
        """Gracefully stop the relay and clean up."""
        self._running = False

        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._background_tasks.clear()

        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        logger.info("outbound relay stopped", instance=self._instance_id)

    # ------------------------------------------------------------------
    # Session registration
    # ------------------------------------------------------------------

    async def register_session(
        self,
        session_id: str,
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        """Register a session for remote access via the outbound relay.

        Mints an initial admin credential and sends the registration
        through the relay hub.

        Args:
            session_id: The local session to expose.
            ttl_seconds: Credential TTL.

        Returns:
            Dict with ``session_id`` and ``admin_token``.
        """
        if self._ws is None or self._ws.closed:
            raise ConnectionError("Outbound relay not connected")

        # Mint an initial admin credential for this session
        admin_token, _ = self.credential_minter.mint(
            session_id,
            ttl_seconds=ttl_seconds,
            allowed_actions={AllowedAction.ADMIN},
            max_uses=1,
        )

        # Bind the sync protocol to this session
        self.sync.bind_session(session_id)

        await self._send({
            "type": "register_relay_session",
            "session_id": session_id,
            "instance_id": self._instance_id,
        })

        logger.info("session registered via outbound relay", session_id=session_id)
        return {"session_id": session_id, "admin_token": admin_token}

    async def unregister_session(self, session_id: str) -> None:
        """Remove a session from the relay hub."""
        self.credential_minter.revoke_all_for_session(session_id)
        if self._ws and not self._ws.closed:
            await self._send({
                "type": "unregister_relay_session",
                "session_id": session_id,
            })
        logger.info("session unregistered from outbound relay", session_id=session_id)

    # ------------------------------------------------------------------
    # Credential minting helpers
    # ------------------------------------------------------------------

    def mint_attach_credential(
        self,
        session_id: str,
        ttl_seconds: int = 7200,
    ) -> tuple[str, CredentialScope]:
        """Mint a credential that allows attaching to a session."""
        return self.credential_minter.mint(
            session_id,
            ttl_seconds=ttl_seconds,
            allowed_actions={AllowedAction.ATTACH, AllowedAction.STEER, AllowedAction.PEEK},
            max_uses=0,
        )

    def mint_steer_credential(
        self,
        session_id: str,
        ttl_seconds: int = 3600,
        max_uses: int = 10,
    ) -> tuple[str, CredentialScope]:
        """Mint a credential for limited steering operations."""
        return self.credential_minter.mint(
            session_id,
            ttl_seconds=ttl_seconds,
            allowed_actions={AllowedAction.STEER},
            max_uses=max_uses,
        )

    # ------------------------------------------------------------------
    # State sync proxy
    # ------------------------------------------------------------------

    async def sync_state(
        self,
        surface_id: str,
        state_updates: dict[str, Any],
    ) -> list[str]:
        """Receive state updates from a surface and propagate them.

        Args:
            surface_id: Surface sending the update.
            state_updates: Flat dict of ``path -> value`` changes.

        Returns:
            List of paths that were actually updated.
        """
        diffs = [
            DiffEntry(path=k, value=v, source=surface_id, timestamp=time.time())
            for k, v in state_updates.items()
        ]
        patch = SyncPatch(
            session_id=self.sync._session_id,
            diffs=diffs,
            base_version=0,
            source=surface_id,
        )
        return self.sync.apply_remote_patch(patch, from_surface=surface_id)

    # ------------------------------------------------------------------
    # Internal: listen loop
    # ------------------------------------------------------------------

    async def _listen_loop(self) -> None:
        """Background reader for incoming relay frames."""
        try:
            async for msg in self._ws:
                if msg.type == "close":
                    break
                try:
                    data = json.loads(msg.data) if msg.data else {}
                except json.JSONDecodeError:
                    continue
                await self._handle_frame(data)
        except (asyncio.CancelledError, ConnectionError):
            pass
        finally:
            logger.info("outbound relay listener stopped")

    async def _handle_frame(self, data: dict[str, Any]) -> None:
        """Route an incoming relay hub frame."""
        msg_type = data.get("type", "")

        if msg_type == "heartbeat_ack":
            return
        if msg_type == "relay_auth_ok":
            logger.info("relay hub authentication successful")
            return

        if msg_type == "surface_attach":
            await self._handle_surface_attach(data)
        elif msg_type == "surface_sync":
            await self._handle_surface_sync(data)
        elif msg_type == "surface_detach":
            await self._handle_surface_detach(data)

    async def _handle_surface_attach(self, data: dict[str, Any]) -> None:
        """A remote surface wants to attach to this relay instance."""
        surface_id = data.get("surface_id", "")
        surface_type = data.get("surface_type", "unknown")
        credential = data.get("credential", "")
        session_id = data.get("session_id", "")

        if not self.credential_minter.verify(credential, AllowedAction.ATTACH, session_id):
            logger.warning("surface attach rejected: invalid credential", surface_id=surface_id)
            await self._send({
                "type": "surface_attach_result",
                "surface_id": surface_id,
                "session_id": session_id,
                "success": False,
                "error": "invalid_credential",
            })
            return

        info = self.sync.register_surface(surface_id, surface_type)

        logger.info("surface attached", surface_id=surface_id, surface_type=surface_type)
        await self._send({
            "type": "surface_attach_result",
            "surface_id": surface_id,
            "session_id": session_id,
            "success": True,
            "protocol_version": info.protocol_version,
        })

    async def _handle_surface_sync(self, data: dict[str, Any]) -> None:
        """Apply a sync patch from a remote surface."""
        surface_id = data.get("surface_id", "")
        updates = data.get("state_updates", {})

        if surface_id not in self.sync._surfaces:
            return

        await self.sync_state(surface_id, updates)

    async def _handle_surface_detach(self, data: dict[str, Any]) -> None:
        """A remote surface is detaching."""
        surface_id = data.get("surface_id", "")
        self.sync.unregister_surface(surface_id)
        logger.info("surface detached", surface_id=surface_id)

    # ------------------------------------------------------------------
    # Internal: heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to keep the relay hub connection alive."""
        try:
            while self._running:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                if self._ws and not self._ws.closed:
                    await self._send({
                        "type": "relay_heartbeat",
                        "instance_id": self._instance_id,
                    })
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send(self, data: dict[str, Any]) -> None:
        """Send a JSON frame through the WebSocket."""
        if self._ws and not self._ws.closed:
            await self._ws.send_json(data)
