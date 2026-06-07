"""Tests for zero-trust relay and mobile steering."""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.remote.mobile_steering import MobileSteeringSurface
from lyra.remote.zero_trust_relay import (
    MobileAction,
    PushNotification,
    RelayConfig,
    SessionEvent,
    SessionSummary,
    SignedCommand,
    ZeroTrustCrypto,
    ZeroTrustRelay,
    build_notification,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _AsyncMessageIter:
    """An async iterator that yields WebSocket message frames.

    Each item is a simple namespace with a ``type`` attribute (always
    ``"text"``) and a ``data`` attribute containing the JSON string.
    """

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self._messages = list(messages)

    def __aiter__(self) -> _AsyncMessageIter:
        return self

    async def __anext__(self) -> Any:
        if not self._messages:
            raise StopAsyncIteration
        msg = self._messages.pop(0)
        # Simulate aiohttp WSMessage shape
        return _Frame(msg)


class _Frame:
    """Minimal stand-in for an aiohttp WSMessage."""

    type = "text"  # Class-level default

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = json.dumps(data)
        self.type = "text"


def _make_mock_ws(messages: list[dict[str, Any]] | None = None) -> MagicMock:
    """Build a mocked aiohttp WebSocket that yields *messages*."""
    ws = MagicMock()
    ws.closed = False
    ws.__aiter__.return_value = _AsyncMessageIter(messages or [])
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws


def _patch_client_session(ws: MagicMock) -> MagicMock:
    """Patch ``aiohttp.ClientSession`` so ``ws_connect`` returns *ws*.

    Note: ``connect()`` uses ``ClientSession()`` (no ``async with``), so we
    mock the return value of direct construction, not ``__aenter__``.
    """
    patcher = patch("aiohttp.ClientSession")
    mock_session_cls = patcher.start()
    session_instance = MagicMock()
    session_instance.ws_connect = AsyncMock(return_value=ws)
    mock_session_cls.return_value = session_instance
    return patcher


# =========================================================================
# ZeroTrustCrypto
# =========================================================================


class TestZeroTrustCrypto:
    """E2E encryption tests."""

    def test_generate_key(self) -> None:
        key = ZeroTrustCrypto.generate_key()
        assert len(key) == 32  # 256 bits

    def test_generate_key_unique(self) -> None:
        keys = {ZeroTrustCrypto.generate_key() for _ in range(10)}
        assert len(keys) == 10

    def test_encrypt_decrypt_roundtrip(self) -> None:
        key = ZeroTrustCrypto.generate_key()
        crypto = ZeroTrustCrypto(key)
        plaintext = "hello, zero-trust relay"
        ciphertext = crypto.encrypt(plaintext)
        assert ciphertext != plaintext
        decrypted = crypto.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_decrypt_empty_string(self) -> None:
        crypto = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        assert crypto.decrypt(crypto.encrypt("")) == ""

    def test_encrypt_decrypt_unicode(self) -> None:
        crypto = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        text = "Lyra remote access -- zero trust relay"
        assert crypto.decrypt(crypto.encrypt(text)) == text

    def test_different_keys_produce_different_ciphertext(self) -> None:
        crypto_a = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        crypto_b = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        plaintext = "secret payload"
        assert crypto_a.encrypt(plaintext) != crypto_b.encrypt(plaintext)

    def test_decrypt_with_wrong_key_raises(self) -> None:
        crypto_a = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        crypto_b = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        ciphertext = crypto_a.encrypt("test")
        with pytest.raises(Exception):
            crypto_b.decrypt(ciphertext)

    def test_key_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 16 bytes"):
            ZeroTrustCrypto(b"short")

    def test_sign_and_verify(self) -> None:
        crypto = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        data = "command:approve:tool_123"
        sig = crypto.sign(data)
        assert crypto.verify(data, sig)
        assert not crypto.verify(data + "tampered", sig)

    def test_sign_empty_data(self) -> None:
        crypto = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        sig = crypto.sign("")
        assert crypto.verify("", sig)
        assert not crypto.verify("x", sig)

    def test_sign_different_keys(self) -> None:
        a = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        b = ZeroTrustCrypto(ZeroTrustCrypto.generate_key())
        sig = a.sign("data")
        assert not b.verify("data", sig)

    def test_ciphertext_is_not_deterministic(self) -> None:
        """Encryption produces different output each call (random IV/salt)."""
        key = ZeroTrustCrypto.generate_key()
        crypto = ZeroTrustCrypto(key)
        ct1 = crypto.encrypt("same text")
        ct2 = crypto.encrypt("same text")
        assert ct1 != ct2


# =========================================================================
# SignedCommand
# =========================================================================


class TestSignedCommand:
    """Signed command serialization and signing."""

    def test_serialize_does_not_include_signature(self) -> None:
        cmd = SignedCommand(
            action=MobileAction.APPROVE,
            payload={"tool_call_id": "tc_001"},
            session_id="lyra-abc123",
        )
        serialized = cmd.serialize()
        parsed = json.loads(serialized)
        assert "signature" not in parsed

    def test_serialize_sorted_keys(self) -> None:
        cmd = SignedCommand(
            action=MobileAction.MESSAGE,
            payload={"text": "hello"},
            session_id="lyra-xyz",
        )
        s = cmd.serialize()
        keys = list(json.loads(s).keys())
        assert keys == sorted(keys)

    def test_nonce_randomness(self) -> None:
        cmd1 = SignedCommand(MobileAction.APPROVE, {}, "s1")
        cmd2 = SignedCommand(MobileAction.APPROVE, {}, "s1")
        assert cmd1.nonce != cmd2.nonce

    def test_timestamp_is_set(self) -> None:
        cmd = SignedCommand(MobileAction.APPROVE, {}, "s1")
        assert cmd.timestamp > 0
        assert abs(cmd.timestamp - time.time()) < 5


# =========================================================================
# PushNotification
# =========================================================================


class TestPushNotification:
    """Notification building and template selection."""

    def test_template_completion(self) -> None:
        n = build_notification(SessionEvent.COMPLETION, "lyra-abc")
        assert "Complete" in n.title
        assert n.event == SessionEvent.COMPLETION
        assert n.session_id == "lyra-abc"

    def test_template_error(self) -> None:
        n = build_notification(SessionEvent.ERROR, "lyra-abc")
        assert "Error" in n.title

    def test_template_approval(self) -> None:
        n = build_notification(SessionEvent.NEEDS_APPROVAL, "lyra-abc")
        assert "Approval" in n.title

    def test_template_cost_alert(self) -> None:
        n = build_notification(SessionEvent.COST_ALERT, "lyra-abc")
        assert "Cost" in n.title

    def test_template_disconnected(self) -> None:
        n = build_notification(SessionEvent.DISCONNECTED, "lyra-abc")
        assert "Disconnected" in n.title

    def test_custom_title_body(self) -> None:
        n = build_notification(
            SessionEvent.COMPLETION,
            "lyra-abc",
            title="Custom Title",
            body="Custom body text",
        )
        assert n.title == "Custom Title"
        assert n.body == "Custom body text"

    def test_custom_data(self) -> None:
        n = build_notification(
            SessionEvent.COMPLETION,
            "lyra-abc",
            extra_key="extra_value",
        )
        assert n.data["extra_key"] == "extra_value"
        assert "timestamp" in n.data

    def test_to_payload(self) -> None:
        n = build_notification(SessionEvent.COMPLETION, "lyra-abc")
        payload = n.to_payload()
        assert "title" in payload
        assert "body" in payload
        assert "event" in payload
        assert "session_id" in payload
        assert payload["session_id"] == "lyra-abc"

    def test_unknown_event_fallback(self) -> None:
        n = build_notification("unknown_event", "lyra-abc")  # type: ignore[arg-type]
        assert n.title == "Lyra Notification"

    def test_default_timestamp(self) -> None:
        n = build_notification(SessionEvent.COMPLETION, "lyra-abc")
        assert n.data["timestamp"] > 0
        assert abs(n.data["timestamp"] - time.time()) < 5

    def test_push_notification_dataclass(self) -> None:
        n = PushNotification(
            title="Test",
            body="test body",
            event=SessionEvent.ERROR,
            session_id="lyra-abc",
        )
        assert n.title == "Test"
        assert n.body == "test body"

    def test_push_notification_with_data(self) -> None:
        n = PushNotification(
            title="Test",
            body="test",
            event=SessionEvent.COMPLETION,
            session_id="lyra-abc",
            data={"cost": 0.05},
        )
        assert n.data["cost"] == 0.05


# =========================================================================
# ZeroTrustRelay
# =========================================================================


class TestZeroTrustRelay:
    """Relay connection, encryption, and mobile steering tests."""

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def test_config_defaults(self) -> None:
        config = RelayConfig(
            relay_url="wss://relay.example.com/ws",
            device_id="test-device",
        )
        assert config.relay_url == "wss://relay.example.com/ws"
        assert config.device_id == "test-device"
        assert config.notification_token == ""
        assert config.reconnect_delay == 5.0
        assert config.heartbeat_interval == 30.0

    def test_config_custom(self) -> None:
        config = RelayConfig(
            relay_url="wss://custom.relay/ws",
            device_id="custom-device",
            notification_token="fcm-token-xyz",
            reconnect_delay=1.0,
            heartbeat_interval=15.0,
        )
        assert config.notification_token == "fcm-token-xyz"
        assert config.reconnect_delay == 1.0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(
                relay_url="wss://relay.example.com/ws",
                device_id="test-device",
            )
            relay = ZeroTrustRelay(config)
            await relay.connect()
            assert relay._ws is ws
            await relay.disconnect()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_disconnect_closes_ws(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(
                relay_url="wss://relay.example.com/ws",
                device_id="test-device",
            )
            relay = ZeroTrustRelay(config)
            await relay.connect()
            ws.close.assert_not_called()
            await relay.disconnect()
            ws.close.assert_called_once()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_disconnect_twice_no_error(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
            relay = ZeroTrustRelay(config)
            await relay.connect()
            await relay.disconnect()
            await relay.disconnect()  # second call should not raise
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # Session registration
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_session(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
            relay = ZeroTrustRelay(config)
            await relay.connect()

            await relay.register_session("lyra-abc123", "test-session")
            assert "lyra-abc123" in relay._session_keys
            assert ws.send_json.called
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_unregister_session(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
            relay = ZeroTrustRelay(config)
            await relay.connect()
            await relay.register_session("lyra-abc123")
            assert "lyra-abc123" in relay._session_keys

            await relay.unregister_session("lyra-abc123")
            assert "lyra-abc123" not in relay._session_keys
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_send_encrypted_no_session_raises(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
            relay = ZeroTrustRelay(config)
            await relay.connect()

            with pytest.raises(ValueError, match="not registered"):
                await relay.send_encrypted("unknown-session", {"type": "test"})
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # E2E encryption
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_e2e_encryption_end_to_end(self) -> None:
        """Verify messages are encrypted and signed end-to-end."""
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
            relay = ZeroTrustRelay(config)
            await relay.connect()
            await relay.register_session("lyra-abc123")

            ws.send_json.reset_mock()
            await relay.send_encrypted(
                "lyra-abc123",
                {"type": "status", "data": "secret"},
            )

            # Find the relay_message call
            relay_msg = None
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and isinstance(args[0], dict) and args[0].get("type") == "relay_message":
                    relay_msg = args[0]
                    break

            assert relay_msg is not None, "No relay_message sent"
            assert "ciphertext" in relay_msg
            assert "signature" in relay_msg
            assert "secret" not in relay_msg["ciphertext"]
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # Command signing
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_mobile_steer_sends_signed_command(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
            relay = ZeroTrustRelay(config)
            await relay.connect()
            await relay.register_session("lyra-abc123")

            ws.send_json.reset_mock()
            cmd = SignedCommand(
                action=MobileAction.APPROVE,
                payload={"tool_call_id": "tc_001"},
                session_id="lyra-abc123",
            )
            await relay.mobile_steer(cmd)

            steer_call = None
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and isinstance(args[0], dict) and args[0].get("type") == "mobile_steer":
                    steer_call = args[0]
                    break

            assert steer_call is not None, "No mobile_steer sent"
            command_frame = steer_call["command"]
            assert command_frame["action"] == "approve"
            assert command_frame["signature"] != ""
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # Push notifications
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_push_notification(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(
                relay_url="wss://relay/ws",
                device_id="d1",
                notification_token="fcm-token",
            )
            relay = ZeroTrustRelay(config)
            await relay.connect()

            ws.send_json.reset_mock()
            notification = build_notification(SessionEvent.COMPLETION, "lyra-abc")
            await relay.send_push_notification(notification)

            push_call = None
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and isinstance(args[0], dict) and args[0].get("type") == "push_notification":
                    push_call = args[0]
                    break

            assert push_call is not None, "No push_notification sent"
            assert push_call["notification_token"] == "fcm-token"
            assert push_call["notification"]["event"] == "completion"
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_push_notification_without_token_skipped(self) -> None:
        ws = _make_mock_ws()
        patcher = _patch_client_session(ws)
        try:
            config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
            relay = ZeroTrustRelay(config)
            await relay.connect()

            ws.send_json.reset_mock()
            notification = build_notification(SessionEvent.COMPLETION, "lyra-abc")
            await relay.send_push_notification(notification)

            # Should NOT have sent a push_notification frame
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and isinstance(args[0], dict):
                    assert args[0].get("type") != "push_notification"
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def test_on_event_decorator(self) -> None:
        config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
        relay = ZeroTrustRelay(config)

        @relay.on_event(SessionEvent.COMPLETION)
        async def handler(sid: str, payload: dict) -> None:
            pass

        assert len(relay._event_handlers[SessionEvent.COMPLETION]) == 1

    def test_on_any_message(self) -> None:
        config = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
        relay = ZeroTrustRelay(config)

        def handler(sid: str, payload: dict) -> None:
            pass

        relay.on_any_message(handler)
        assert relay._on_message is handler


# =========================================================================
# MobileSteeringSurface
# =========================================================================


class TestMobileSteeringSurface:
    """High-level mobile steering API tests."""

    def test_init_without_connect(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        assert not surface._connected

    @pytest.mark.asyncio
    async def test_init_with_auto_connect(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
        )
        assert surface._connect_task is not None

    @pytest.mark.asyncio
    async def test_status_offline_timeout(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.send_encrypted = AsyncMock()
        mock_relay.on_any_message = MagicMock()
        mock_relay.connect = AsyncMock()
        surface._relay = mock_relay

        result = await surface.status("lyra-abc")
        assert isinstance(result, SessionSummary)
        assert result.session_id == "lyra-abc"

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.disconnect = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.disconnect()
        mock_relay.disconnect.assert_called_once()
        assert not surface._connected

    @pytest.mark.asyncio
    async def test_approve(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        mock_relay.mobile_steer = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.approve("lyra-abc", "tc_001")
        mock_relay.mobile_steer.assert_called_once()
        cmd = mock_relay.mobile_steer.call_args[0][0]
        assert cmd.action == MobileAction.APPROVE
        assert cmd.payload["tool_call_id"] == "tc_001"

    @pytest.mark.asyncio
    async def test_deny(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        mock_relay.mobile_steer = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.deny("lyra-abc", "tc_001")
        mock_relay.mobile_steer.assert_called_once()
        cmd = mock_relay.mobile_steer.call_args[0][0]
        assert cmd.action == MobileAction.DENY

    @pytest.mark.asyncio
    async def test_deny_with_reason(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        mock_relay.mobile_steer = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.deny("lyra-abc", "tc_001", reason="Not needed")
        cmd = mock_relay.mobile_steer.call_args[0][0]
        assert cmd.payload["reason"] == "Not needed"

    @pytest.mark.asyncio
    async def test_message(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        mock_relay.mobile_steer = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.message("lyra-abc", "Hello, Lyra!")
        mock_relay.mobile_steer.assert_called_once()
        cmd = mock_relay.mobile_steer.call_args[0][0]
        assert cmd.action == MobileAction.MESSAGE
        assert cmd.payload["text"] == "Hello, Lyra!"

    @pytest.mark.asyncio
    async def test_peek(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        mock_relay.send_encrypted = AsyncMock()
        mock_relay.on_any_message = MagicMock()
        surface._relay = mock_relay
        surface._connected = True

        result = await surface.peek("lyra-abc")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_subscribe(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        sub_id = await surface.subscribe(
            "lyra-abc",
            SessionEvent.NEEDS_APPROVAL,
            lambda s, p: None,
        )
        assert sub_id in surface._subscriptions
        assert sub_id.startswith("sub-")

    @pytest.mark.asyncio
    async def test_unsubscribe(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        sub_id = await surface.subscribe(
            "lyra-abc", SessionEvent.COMPLETION, lambda s, p: None
        )
        assert len(surface._subscriptions) == 1
        await surface.unsubscribe(sub_id)
        assert len(surface._subscriptions) == 0

    @pytest.mark.asyncio
    async def test_list_subscriptions(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.subscribe("s1", SessionEvent.COMPLETION, lambda s, p: None)
        await surface.subscribe("s2", SessionEvent.ERROR, lambda s, p: None)
        subs = surface.list_subscriptions()
        assert len(subs) == 2
        events = {s["event"] for s in subs}
        assert events == {"completion", "error"}

    @pytest.mark.asyncio
    async def test_send_notification(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        mock_relay.send_push_notification = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.send_notification("lyra-abc", SessionEvent.COMPLETION)
        mock_relay.send_push_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_with_overrides(self) -> None:
        surface = MobileSteeringSurface(
            relay_url="wss://relay.example.com/ws",
            device_id="phone-1",
            auto_connect=False,
        )
        mock_relay = AsyncMock(spec=ZeroTrustRelay)
        mock_relay.connect = AsyncMock()
        mock_relay.send_push_notification = AsyncMock()
        surface._relay = mock_relay
        surface._connected = True

        await surface.send_notification(
            "lyra-abc",
            SessionEvent.COST_ALERT,
            title="Over Budget!",
            body="Session cost exceeded $5",
            cost=5.50,
        )
        notification = mock_relay.send_push_notification.call_args[0][0]
        assert notification.title == "Over Budget!"
        assert notification.data["cost"] == 5.50


# =========================================================================
# SessionSummary
# =========================================================================


class TestSessionSummary:
    """Session summary dataclass."""

    def test_defaults(self) -> None:
        s = SessionSummary(session_id="lyra-abc")
        assert not s.agent_online
        assert s.pending_approvals == 0
        assert s.last_message == ""

    def test_full(self) -> None:
        s = SessionSummary(
            session_id="lyra-abc",
            agent_online=True,
            pending_approvals=3,
            last_message="Processing data...",
            running_tool="web_search",
            total_cost=0.42,
            elapsed_seconds=300.0,
        )
        assert s.agent_online
        assert s.pending_approvals == 3


# =========================================================================
# RelayConfig
# =========================================================================


class TestRelayConfig:
    """Relay configuration dataclass."""

    def test_minimal(self) -> None:
        c = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
        assert c.max_reconnect_attempts == 0  # infinite

    def test_repr(self) -> None:
        c = RelayConfig(relay_url="wss://relay/ws", device_id="d1")
        r = repr(c)
        assert "relay_url" in r or "RelayConfig" in r
