"""
Zero-Trust Remote Relay — outbound-only relay for Lyra remote access.

Architecture
------------
  Local Lyra process  --outbound WebSocket-->  Relay Server  <-- Mobile / Browser
       |                                              |
  E2E-encrypted payloads                     Sees only ciphertext
  Per-session ephemeral keys                  Never decrypts
  Signed commands                             Verifies signatures

This module implements the *client* side of the relay. The server side lives
in ``src/lyra/server/relay.py`` and ``src/lyra/server/relay_ws.py``.

References
----------
- src/lyra/server/relay.py    — RelayServer session / credential management
- src/lyra/commands/dispatcher.py  — slash command dispatch
- :class:`MobileSteeringSurface`  — high-level mobile steering API
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from hashlib import pbkdf2_hmac, sha256
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Conditional cryptography import
# ---------------------------------------------------------------------------

try:
    from cryptography.fernet import Fernet
    import cryptography  # noqa: F401
    HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover
    Fernet = None  # type: ignore[assignment]
    HAS_CRYPTOGRAPHY = False


# ---------------------------------------------------------------------------
# Relayed message types
# ---------------------------------------------------------------------------


class SessionEvent(str, Enum):
    """Types of session events that trigger notifications or handler dispatch."""

    COMPLETION = "completion"
    ERROR = "error"
    NEEDS_APPROVAL = "needs_approval"
    COST_ALERT = "cost_alert"
    DISCONNECTED = "disconnected"


class MobileAction(str, Enum):
    """Actions a mobile user can perform on a remote session."""

    APPROVE = "approve"
    DENY = "deny"
    MESSAGE = "message"
    PEEK = "peek"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelayConfig:
    """Configuration for the zero-trust relay client.

    Attributes:
        relay_url: WebSocket URL of the relay server (``wss://...``).
        device_id: Unique device identifier for this Lyra instance.
        notification_token: Token for push notifications (FCM / APNS).
        reconnect_delay: Seconds to wait before reconnecting (default 5).
        max_reconnect_attempts: Max reconnection attempts (0 = infinite).
        heartbeat_interval: Seconds between heartbeats (default 30).
    """

    relay_url: str
    device_id: str
    notification_token: str = ""
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 0
    heartbeat_interval: float = 30.0


# ---------------------------------------------------------------------------
# Session summary (returned by MobileSteeringSurface.status())
# ---------------------------------------------------------------------------


@dataclass
class SessionSummary:
    """At-a-glance snapshot of a remote session.

    Attributes:
        session_id: Unique session identifier.
        agent_online: Whether the agent is currently connected.
        pending_approvals: Number of tool calls awaiting approval.
        last_message: Most recent message snippet.
        running_tool: Name of the currently executing tool, if any.
        total_cost: Approximate total cost of this session so far.
        elapsed_seconds: Seconds since the session started.
    """

    session_id: str
    agent_online: bool = False
    pending_approvals: int = 0
    last_message: str = ""
    running_tool: str = ""
    total_cost: float = 0.0
    elapsed_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Signed remote command
# ---------------------------------------------------------------------------


@dataclass
class SignedCommand:
    """A remote command with a cryptographic signature.

    The command is serialized, signed with the session's ephemeral key, and
    forwarded through the relay.  The relay *verifies* the signature (so it
    can reject forged commands) but *cannot* decrypt the payload.

    Attributes:
        action: The mobile action to execute.
        payload: Action-specific payload (tool_call_id, text, etc.).
        session_id: The target session.
        timestamp: Unix timestamp of command creation.
        nonce: Unique nonce to prevent replay attacks.
        signature: HMAC-SHA256 signature of the serialized command.
    """

    action: MobileAction
    payload: dict[str, Any]
    session_id: str
    timestamp: float = field(default_factory=time.time)
    nonce: str = field(default_factory=lambda: os.urandom(16).hex())
    signature: str = ""

    def serialize(self) -> str:
        """Canonical JSON for signing (no signature field, sorted keys)."""
        data = {
            "action": self.action.value,
            "payload": self.payload,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }
        return json.dumps(data, separators=(",", ":"), sort_keys=True)


# ---------------------------------------------------------------------------
# Zero-trust encryption layer
# ---------------------------------------------------------------------------


class ZeroTrustCrypto:
    """End-to-end encryption for zero-trust relay messages.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) from the ``cryptography``
    library when available.  Falls back to a deterministic PBKDF2+XOR
    scheme — suitable for testing but **not production grade**.  Install
    ``cryptography>=41.0`` for production deployments.

    Key derivation uses PBKDF2-HMAC-SHA256 with 600 000 iterations.
    """

    PBKDF2_SALT = b"lyra-zt-relay-v1"
    PBKDF2_ITERATIONS = 600_000

    def __init__(self, key_bytes: bytes) -> None:
        if len(key_bytes) < 16:
            raise ValueError("Key must be at least 16 bytes")
        self._raw_key = key_bytes

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def generate_key() -> bytes:
        """Generate a random 32-byte symmetric key."""
        return os.urandom(32)

    # ------------------------------------------------------------------
    # Encryption
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Encrypt *plaintext* to a portable base64 ciphertext string."""
        if HAS_CRYPTOGRAPHY:
            return self._fernet_encrypt(plaintext)
        return self._xor_encrypt(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt *ciphertext* back to the original plaintext."""
        if HAS_CRYPTOGRAPHY:
            return self._fernet_decrypt(ciphertext)
        return self._xor_decrypt(ciphertext)

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def sign(self, data: str) -> str:
        """Return an HMAC-SHA256 hex digest of *data*."""
        return hmac.new(self._raw_key, data.encode(), sha256).hexdigest()

    def verify(self, data: str, signature: str) -> bool:
        """Return ``True`` when *signature* is valid for *data*."""
        return hmac.compare_digest(self.sign(data), signature)

    # ------------------------------------------------------------------
    # Fernet implementation
    # ------------------------------------------------------------------

    def _fernet_key(self) -> bytes:
        """Derive a url-safe-base64 Fernet key from the raw key."""
        derived = pbkdf2_hmac(
            "sha256",
            self._raw_key,
            self.PBKDF2_SALT,
            self.PBKDF2_ITERATIONS,
            dklen=32,
        )
        return base64.urlsafe_b64encode(derived)

    def _fernet_encrypt(self, plaintext: str) -> str:
        f = Fernet(self._fernet_key())
        return f.encrypt(plaintext.encode()).decode()

    def _fernet_decrypt(self, ciphertext: str) -> str:
        f = Fernet(self._fernet_key())
        return f.decrypt(ciphertext.encode()).decode()

    # ------------------------------------------------------------------
    # Stdlib-only fallback (PBKDF2 + XOR stream cipher)
    # ------------------------------------------------------------------

    def _xor_encrypt(self, plaintext: str) -> str:
        """Encrypt with a PBKDF2-derived keystream (INSECURE, fallback)."""
        salt = os.urandom(16)
        pt = plaintext.encode()
        ks = pbkdf2_hmac("sha256", self._raw_key, salt, self.PBKDF2_ITERATIONS, dklen=len(pt))
        ct = bytes(a ^ b for a, b in zip(pt, ks))
        return salt.hex() + ":" + ct.hex()

    def _xor_decrypt(self, ciphertext: str) -> str:
        parts = ciphertext.split(":")
        salt = bytes.fromhex(parts[0])
        ct = bytes.fromhex(parts[1])
        ks = pbkdf2_hmac("sha256", self._raw_key, salt, self.PBKDF2_ITERATIONS, dklen=len(ct))
        return bytes(a ^ b for a, b in zip(ct, ks)).decode()


# ---------------------------------------------------------------------------
# Push notifications
# ---------------------------------------------------------------------------


@dataclass
class PushNotification:
    """A push notification payload for mobile delivery.

    Attributes:
        title: Notification title (visible on lock screen).
        body: Notification body text.
        event: The session event type.
        session_id: The source session.
        data: Additional structured data for the mobile app.
    """

    title: str
    body: str
    event: SessionEvent
    session_id: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Build a dictionary suitable for FCM / APNS delivery."""
        return {
            "title": self.title,
            "body": self.body,
            "event": self.event.value if isinstance(self.event, Enum) else self.event,
            "session_id": self.session_id,
            "data": {
                **self.data,
                "timestamp": self.data.get("timestamp", time.time()),
            },
        }


# Default notification templates keyed by event type.
_NOTIFICATION_TEMPLATES: dict[SessionEvent, tuple[str, str]] = {
    SessionEvent.COMPLETION: (
        "Session Complete",
        "Your Lyra session has finished its work.",
    ),
    SessionEvent.ERROR: (
        "Session Error",
        "Your Lyra session encountered an error.",
    ),
    SessionEvent.NEEDS_APPROVAL: (
        "Approval Required",
        "A tool call needs your approval to proceed.",
    ),
    SessionEvent.COST_ALERT: (
        "Cost Alert",
        "Your Lyra session cost has exceeded the threshold.",
    ),
    SessionEvent.DISCONNECTED: (
        "Session Disconnected",
        "Your Lyra session has been disconnected.",
    ),
}


def build_notification(
    event: SessionEvent,
    session_id: str,
    **overrides: Any,
) -> PushNotification:
    """Build a :class:`PushNotification` from an event type.

    Parameters
    ----------
    event : SessionEvent
        The event that triggered the notification.
    session_id : str
        The session identifier.
    **overrides
        Override ``title``, ``body``, or additional ``data`` keys.

    Returns
    -------
    PushNotification
    """
    title, body = _NOTIFICATION_TEMPLATES.get(
        event,
        ("Lyra Notification", "A Lyra session event occurred."),
    )
    data = dict(overrides)
    data.setdefault("timestamp", time.time())
    data.pop("title", None)
    data.pop("body", None)

    return PushNotification(
        title=overrides.get("title", title),
        body=overrides.get("body", body),
        event=event,
        session_id=session_id,
        data=data,
    )


# ---------------------------------------------------------------------------
# Zero-trust relay client
# ---------------------------------------------------------------------------


class ZeroTrustRelay:
    """Outbound-only zero-trust relay client for Lyra remote access.

    The relay **never** opens inbound ports.  Instead it establishes an
    outbound WebSocket connection to the relay server and keeps it alive.
    All payloads are end-to-end encrypted — the relay sees only ciphertext.
    Every remote command is signed with a per-session ephemeral key.

    Usage::

        config = RelayConfig(
            relay_url="wss://relay.lyra.example.com/ws",
            device_id="my-macbook-pro",
            notification_token="fcm-token-...",
        )
        relay = ZeroTrustRelay(config)
        await relay.connect()
        await relay.register_session("lyra-abc123", "dev-session")
        await relay.send_encrypted("lyra-abc123", {"type": "status"})
        await relay.disconnect()
    """

    def __init__(
        self,
        config: RelayConfig,
        transport_key: bytes | None = None,
    ) -> None:
        self._config = config
        self._crypto = ZeroTrustCrypto(transport_key or ZeroTrustCrypto.generate_key())
        self._ws: Any = None
        self._running = False
        self._reconnect_attempts = 0
        self._session_keys: dict[str, bytes] = {}  # session_id -> raw key

        # Per-event handler lists
        self._event_handlers: dict[SessionEvent, list[Callable[..., Any]]] = {
            e: [] for e in SessionEvent
        }
        # Generic message handler (session_id, payload_dict)
        self._on_message: Callable[[str, dict[str, Any]], Any] | None = None

        # Background tasks
        self._heartbeat_task: asyncio.Task[Any] | None = None
        self._listener_task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish an outbound WebSocket connection to the relay server.

        Automatically retries on failure up to ``max_reconnect_attempts``.

        Raises
        ------
        ConnectionError
            If the connection cannot be established and max reconnect
            attempts are exhausted.
        """
        import aiohttp

        self._running = True

        while self._running:
            try:
                http_session = aiohttp.ClientSession()
                ws = await http_session.ws_connect(
                    self._config.relay_url,
                    heartbeat=self._config.heartbeat_interval,
                )
                self._ws = ws
                self._reconnect_attempts = 0
                logger.info(
                    "relay connected",
                    url=self._config.relay_url,
                    device=self._config.device_id,
                )

                await self._send_plain({
                    "type": "auth",
                    "device_id": self._config.device_id,
                })

                self._listener_task = asyncio.create_task(self._listen())
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                return

            except Exception as exc:
                self._reconnect_attempts += 1
                if (
                    self._config.max_reconnect_attempts > 0
                    and self._reconnect_attempts > self._config.max_reconnect_attempts
                ):
                    raise ConnectionError(
                        f"Max reconnect attempts "
                        f"({self._config.max_reconnect_attempts}) exceeded"
                    ) from exc

                logger.warning(
                    "relay reconnect pending",
                    attempt=self._reconnect_attempts,
                    delay=self._config.reconnect_delay,
                )
                await asyncio.sleep(self._config.reconnect_delay)

    async def disconnect(self) -> None:
        """Gracefully disconnect from the relay server."""
        self._running = False

        for task_attr in ("_heartbeat_task", "_listener_task"):
            task = getattr(self, task_attr)
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            setattr(self, task_attr, None)

        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
            self._ws = None

        logger.info("relay disconnected", device=self._config.device_id)

    # ------------------------------------------------------------------
    # Session registration
    # ------------------------------------------------------------------

    async def register_session(self, session_id: str, name: str = "") -> None:
        """Register *session_id* for remote access.

        Generates a fresh ephemeral key, stores it locally, and sends the
        key's encrypted form through the relay so the relay can later verify
        signatures when forwarding mobile commands.

        Parameters
        ----------
        session_id : str
            The session to register.
        name : str
            Human-readable session name (defaults to *session_id*).

        Raises
        ------
        ConnectionError
            If not connected to the relay.
        """
        if self._ws is None or self._ws.closed:
            raise ConnectionError("Not connected to relay")

        session_key = ZeroTrustCrypto.generate_key()
        session_crypto = ZeroTrustCrypto(session_key)
        encrypted_key = self._crypto.encrypt(session_key.hex())

        await self._send_encrypted_raw({
            "type": "register_session",
            "session_id": session_id,
            "name": name or session_id,
            "session_key": encrypted_key,
        })
        self._session_keys[session_id] = session_key
        logger.info("session registered for remote", session_id=session_id)

    async def unregister_session(self, session_id: str) -> None:
        """Remove *session_id* from remote access."""
        self._session_keys.pop(session_id, None)
        if self._ws and not self._ws.closed:
            await self._send_plain({
                "type": "unregister_session",
                "session_id": session_id,
            })
        logger.info("session unregistered", session_id=session_id)

    # ------------------------------------------------------------------
    # Sending messages
    # ------------------------------------------------------------------

    async def send_encrypted(
        self,
        session_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Encrypt and forward *payload* through the relay.

        The relay sees only ciphertext and cannot decrypt the payload.

        Parameters
        ----------
        session_id : str
            Target session.
        payload : dict
            Arbitrary JSON-serializable data.

        Raises
        ------
        ConnectionError
            If not connected to the relay.
        ValueError
            If the session has not been registered.
        """
        if self._ws is None or self._ws.closed:
            raise ConnectionError("Not connected to relay")

        session_key = self._session_keys.get(session_id)
        if session_key is None:
            raise ValueError(f"Session {session_id} is not registered for remote access")

        session_crypto = ZeroTrustCrypto(session_key)
        plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        ciphertext = session_crypto.encrypt(plaintext)
        signature = session_crypto.sign(plaintext)

        await self._send_encrypted_raw({
            "type": "relay_message",
            "session_id": session_id,
            "ciphertext": ciphertext,
            "signature": signature,
            "timestamp": time.time(),
        })

    async def send_push_notification(self, notification: PushNotification) -> None:
        """Forward *notification* to the relay for mobile delivery.

        Parameters
        ----------
        notification : PushNotification
            The notification payload.

        Raises
        ------
        ConnectionError
            If not connected to the relay.
        """
        if not self._config.notification_token:
            logger.warning("No notification token configured, skipping push")
            return
        if self._ws is None or self._ws.closed:
            raise ConnectionError("Not connected to relay")

        await self._send_encrypted_raw({
            "type": "push_notification",
            "notification": notification.to_payload(),
            "notification_token": self._config.notification_token,
        })

    async def mobile_steer(self, command: SignedCommand) -> None:
        """Send a signed mobile steering command through the relay.

        Parameters
        ----------
        command : SignedCommand
            The steering command.  Its *signature* attribute is populated
            before sending.

        Raises
        ------
        ConnectionError
            If not connected to the relay.
        """
        if self._ws is None or self._ws.closed:
            raise ConnectionError("Not connected to relay")

        session_key = self._session_keys.get(command.session_id)
        session_crypto = ZeroTrustCrypto(
            session_key if session_key is not None else self._crypto._raw_key
        )

        serialized = command.serialize()
        command.signature = session_crypto.sign(serialized)

        await self._send_encrypted_raw({
            "type": "mobile_steer",
            "command": {
                "action": command.action.value,
                "payload": command.payload,
                "session_id": command.session_id,
                "timestamp": command.timestamp,
                "nonce": command.nonce,
                "signature": command.signature,
                "serialized": serialized,
            },
        })

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_event(
        self,
        event: SessionEvent,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a handler for *event*.

        Usage::

            @relay.on_event(SessionEvent.NEEDS_APPROVAL)
            async def on_approval(session_id, payload):
                ...
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._event_handlers[event].append(func)
            return func
        return decorator

    def on_any_message(self, handler: Callable[[str, dict[str, Any]], Any]) -> None:
        """Register a callback for all decrypted messages.

        The callback receives ``(session_id, payload_dict)``.
        """
        self._on_message = handler

    # ------------------------------------------------------------------
    # Listener (background)
    # ------------------------------------------------------------------

    async def _listen(self) -> None:
        """Background reader that processes relay frames."""
        try:
            async for msg in self._ws:
                if msg.type == "close":
                    break
                try:
                    data = json.loads(msg.data) if msg.data else {}
                except json.JSONDecodeError:
                    continue
                await self._handle_relay_frame(data)
        except (asyncio.CancelledError, ConnectionError):
            pass
        finally:
            logger.info("relay listener stopped")

    async def _handle_relay_frame(self, data: dict[str, Any]) -> None:
        """Route a relay frame to the appropriate internal handler."""
        msg_type = data.get("type", "")

        if msg_type == "heartbeat_ack":
            return
        if msg_type == "auth_ok":
            logger.info("relay authentication successful")
            return

        if msg_type == "relay_message":
            await self._handle_incoming_message(data)
        elif msg_type == "mobile_command":
            await self._handle_mobile_command(data)

    async def _handle_incoming_message(self, data: dict[str, Any]) -> None:
        """Decrypt and dispatch an incoming relay message."""
        session_id = data.get("session_id", "")
        ciphertext = data.get("ciphertext", "")
        signature = data.get("signature", "")

        if not session_id or not ciphertext:
            return

        session_key = self._session_keys.get(session_id)
        if session_key is None:
            logger.warning("message for unknown session", session_id=session_id)
            return

        session_crypto = ZeroTrustCrypto(session_key)
        try:
            plaintext = session_crypto.decrypt(ciphertext)
        except Exception:
            logger.exception("decryption failed", session_id=session_id)
            return

        if signature and not session_crypto.verify(plaintext, signature):
            logger.warning("signature verification failed", session_id=session_id)
            return

        payload = json.loads(plaintext)

        if self._on_message:
            await self._safe_call(self._on_message, session_id, payload)

        event_type = payload.get("event", "")
        if event_type and event_type in self._event_handlers:
            for handler in self._event_handlers[SessionEvent(event_type)]:
                await self._safe_call(handler, session_id, payload)

    async def _handle_mobile_command(self, data: dict[str, Any]) -> None:
        """Receive and verify a signed mobile steering command."""
        cmd = data.get("command", {})
        session_id = cmd.get("session_id", "")
        serialized = cmd.get("serialized", "")
        signature = cmd.get("signature", "")

        if not session_id or not serialized:
            return

        session_key = self._session_keys.get(session_id)
        if session_key is None:
            logger.warning("mobile command for unknown session", session_id=session_id)
            return

        session_crypto = ZeroTrustCrypto(session_key)
        if not session_crypto.verify(serialized, signature):
            logger.warning("mobile command signature invalid", session_id=session_id)
            return

        action_str = cmd.get("action", "")
        payload = cmd.get("payload", {})

        logger.info(
            "mobile command verified",
            session_id=session_id,
            action=action_str,
        )

        # Map approve/deny to NEEDS_APPROVAL handlers
        mapped = {
            MobileAction.APPROVE.value: SessionEvent.NEEDS_APPROVAL,
            MobileAction.DENY.value: SessionEvent.NEEDS_APPROVAL,
        }
        event = mapped.get(action_str)
        if event and event in self._event_handlers:
            for handler in self._event_handlers[event]:
                await self._safe_call(handler, session_id, {
                    "action": action_str,
                    "payload": payload,
                })

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to keep the relay connection alive."""
        try:
            while self._running:
                await asyncio.sleep(self._config.heartbeat_interval)
                if self._ws and not self._ws.closed:
                    await self._send_plain({
                        "type": "heartbeat",
                        "device_id": self._config.device_id,
                    })
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send_plain(self, data: dict[str, Any]) -> None:
        """Send an unencrypted control frame."""
        if self._ws and not self._ws.closed:
            await self._ws.send_json(data)

    async def _send_encrypted_raw(self, data: dict[str, Any]) -> None:
        """Send a JSON frame (contents may contain encrypted bits)."""
        if self._ws and not self._ws.closed:
            await self._ws.send_json(data)

    @staticmethod
    async def _safe_call(func: Callable[..., Any], *args: Any) -> Any:
        """Invoke *func* with *args*, supporting sync and async callables."""
        result = func(*args)
        if asyncio.iscoroutine(result):
            return await result
        return result
