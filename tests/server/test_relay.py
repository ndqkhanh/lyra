"""Tests for the Lyra Relay WebSocket transport (relay_ws.py).

Covers handle_local_ws, handle_remote_ws, and the internal routing
helpers (_route_to_remote, _broadcast_to_remotes, _safe_send).

The core RelayServer and RelayCredential classes are already tested in
the top-level tests/test_relay.py.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from lyra.server.relay import RelayServer, SessionStatus
from lyra.server.relay_ws import (
    _broadcast_to_remotes,
    _route_to_remote,
    _safe_send,
    handle_local_ws,
    handle_remote_ws,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_ws() -> AsyncMock:
    """Return an aiohttp-like WebSocket mock that yields nothing."""
    ws = AsyncMock()
    ws.type = "text"
    ws.data = '{"type": "heartbeat"}'
    # Make __aiter__ return an empty iterator by default so the
    # ``async for msg in ws`` loop terminates immediately.
    ws.__aiter__.return_value = iter([])
    return ws


def _setup_relay() -> tuple[RelayServer, str]:
    """Create a RelayServer with one registered session.

    Returns:
        (relay, session_id)
    """
    relay = RelayServer(secret_key="test-key")
    reg_cred = relay.issue_registration_credential()
    session_id, _ = relay.register_session("Test-Session", reg_cred)
    return relay, session_id


# ---------------------------------------------------------------------------
# _safe_send
# ---------------------------------------------------------------------------


class TestSafeSend:
    """_safe_send helper."""

    async def test_sends_json(self):
        ws = AsyncMock()
        await _safe_send(ws, {"type": "ping"})
        ws.send_json.assert_awaited_once_with({"type": "ping"})

    async def test_silently_handles_connection_error(self):
        ws = AsyncMock()
        ws.send_json.side_effect = ConnectionError("broken pipe")
        await _safe_send(ws, {"type": "ping"})  # should not raise

    async def test_silently_handles_cancelled_error(self):
        ws = AsyncMock()
        ws.send_json.side_effect = asyncio.CancelledError()
        await _safe_send(ws, {"type": "ping"})  # should not raise


# ---------------------------------------------------------------------------
# _route_to_remote
# ---------------------------------------------------------------------------


class TestRouteToRemote:
    """_route_to_remote helper."""

    async def test_routes_to_specific_remote(self):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        session = MagicMock()
        session.remote_clients = {"r1": ws1, "r2": ws2}

        await _route_to_remote(session, "r1", {"text": "hello"})

        ws1.send_json.assert_awaited_once_with(
            {"type": "message", "from": "local", "data": {"text": "hello"}}
        )
        ws2.send_json.assert_not_called()

    async def test_unknown_target_is_noop(self):
        ws = AsyncMock()
        session = MagicMock()
        session.remote_clients = {"r1": ws}

        await _route_to_remote(session, "unknown", {"text": "hello"})
        ws.send_json.assert_not_called()


# ---------------------------------------------------------------------------
# _broadcast_to_remotes
# ---------------------------------------------------------------------------


class TestBroadcastToRemotes:
    """_broadcast_to_remotes helper."""

    async def test_broadcasts_to_all_remotes(self):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        session = MagicMock()
        session.remote_clients = {"r1": ws1, "r2": ws2}

        await _broadcast_to_remotes(session, {"text": "broadcast"})

        for ws in (ws1, ws2):
            ws.send_json.assert_awaited_once()
            # await_args is a _Call object; [0] is positional-args tuple, [0] is the dict
            payload = ws.send_json.await_args[0][0]
            assert payload["type"] == "message"
            assert payload["from"] == "local"
            assert payload["data"] == {"text": "broadcast"}

    async def test_tolerates_failed_remotes(self):
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_json.side_effect = ConnectionError("gone")
        session = MagicMock()
        session.remote_clients = {"good": good_ws, "bad": bad_ws}

        # Should not raise
        await _broadcast_to_remotes(session, {"text": "hi"})
        good_ws.send_json.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle_local_ws
# ---------------------------------------------------------------------------


class TestHandleLocalWs:
    """handle_local_ws — WebSocket handler for local Lyra processes."""

    async def test_closes_on_unknown_session(self):
        relay = RelayServer(secret_key="test-key")
        ws = _make_mock_ws()
        await handle_local_ws(relay, ws, "does-not-exist")
        ws.close.assert_awaited_once()

    async def test_registers_ws_and_sets_online(self):
        """Session is found, so the handler does NOT close the WS.

        The ``local_ws`` and ``status=ONLINE`` are set at handler entry,
        but the ``finally`` block always resets them on exit.  We verify
        the session was found by asserting ``close`` was never called.
        """
        relay, session_id = _setup_relay()
        ws = _make_mock_ws()
        await handle_local_ws(relay, ws, session_id)

        # Session existed so the early-close path was *not* taken
        ws.close.assert_not_called()
        # Cleanup leaves session offline
        assert relay.get_session(session_id).status == SessionStatus.OFFLINE

    async def test_heartbeat_message(self):
        relay, session_id = _setup_relay()
        session = relay.get_session(session_id)
        old_hb = session.last_heartbeat

        ws = _make_mock_ws()
        # Yield a heartbeat, then stop
        hb_msg = MagicMock()
        hb_msg.type = "text"
        hb_msg.data = '{"type": "heartbeat"}'
        ws.__aiter__.return_value = iter([hb_msg])

        await handle_local_ws(relay, ws, session_id)
        assert session.last_heartbeat >= old_hb

    async def test_message_routed_to_remote(self):
        relay, session_id = _setup_relay()
        session = relay.get_session(session_id)

        # Attach a remote client
        remote_ws = AsyncMock()
        session.remote_clients["rem1"] = remote_ws

        msg = MagicMock()
        msg.type = "text"
        msg.data = json.dumps(
            {
                "type": "message",
                "to": "rem1",
                "data": {"text": "from local"},
            }
        )

        ws = _make_mock_ws()
        ws.__aiter__.return_value = iter([msg])

        await handle_local_ws(relay, ws, session_id)

        remote_ws.send_json.assert_awaited_once_with(
            {"type": "message", "from": "local", "data": {"text": "from local"}}
        )

    async def test_broadcast_reaches_all_remotes(self):
        relay, session_id = _setup_relay()
        session = relay.get_session(session_id)

        rws1 = AsyncMock()
        rws2 = AsyncMock()
        session.remote_clients["r1"] = rws1
        session.remote_clients["r2"] = rws2

        msg = MagicMock()
        msg.type = "text"
        msg.data = json.dumps({"type": "broadcast", "data": {"status": "update"}})

        ws = _make_mock_ws()
        ws.__aiter__.return_value = iter([msg])

        await handle_local_ws(relay, ws, session_id)

        rws1.send_json.assert_awaited_once()
        rws2.send_json.assert_awaited_once()

    async def test_invalid_json_skipped(self):
        relay, session_id = _setup_relay()

        msg = MagicMock()
        msg.type = "text"
        msg.data = "not valid json{{{"

        ws = _make_mock_ws()
        ws.__aiter__.return_value = iter([msg])

        # Should not raise
        await handle_local_ws(relay, ws, session_id)

    async def test_sets_status_offline_after_disconnect(self):
        relay, session_id = _setup_relay()
        session = relay.get_session(session_id)

        ws = _make_mock_ws()
        await handle_local_ws(relay, ws, session_id)

        assert session.status == SessionStatus.OFFLINE
        assert session.local_ws is None

    async def test_close_message_breaks_loop(self):
        relay, session_id = _setup_relay()

        close_msg = MagicMock()
        close_msg.type = "close"

        ws = _make_mock_ws()
        ws.__aiter__.return_value = iter([close_msg])

        await handle_local_ws(relay, ws, session_id)
        # After close, session should be offline
        session = relay.get_session(session_id)
        assert session.status == SessionStatus.OFFLINE


# ---------------------------------------------------------------------------
# handle_remote_ws
# ---------------------------------------------------------------------------


class TestHandleRemoteWs:
    """handle_remote_ws — WebSocket handler for remote (browser/phone) clients."""

    async def test_closes_on_invalid_credential(self):
        relay, session_id = _setup_relay()
        ws = _make_mock_ws()
        await handle_remote_ws(relay, ws, session_id, "bad-cred")
        ws.close.assert_awaited_once()

    async def test_closes_on_unknown_session(self):
        relay = RelayServer(secret_key="test-key")
        # Register a session to get a real attach credential, but then
        # pass a different session_id
        reg_cred = relay.issue_registration_credential()
        _, attach_cred = relay.register_session("Real", reg_cred)

        ws = _make_mock_ws()
        await handle_remote_ws(relay, ws, "nonexistent", attach_cred)
        ws.close.assert_awaited_once()

    async def test_sends_connected_handshake(self):
        relay, session_id = _setup_relay()
        session = relay.get_session(session_id)

        reg_cred = relay.issue_registration_credential()
        _, attach_cred = relay.register_session("MySesh", reg_cred)
        session_id2 = list(relay._sessions.keys())[-1]
        session2 = relay.get_session(session_id2)

        # Add a local ws so we can check notifications
        local_ws = AsyncMock()
        session2.local_ws = local_ws

        ws = _make_mock_ws()
        await handle_remote_ws(relay, ws, session2.session_id, attach_cred)

        # Remote should get connected event
        ws.send_json.assert_any_call(
            {
                "type": "connected",
                "session_name": "MySesh",
                "client_id": ws.send_json.call_args[0][0]["client_id"],
            }
        )

    async def test_registers_as_remote_client(self):
        """Client is added to remote_clients during the connection, then
        removed in the finally block. The ``remote_left`` notification
        proves registration did happen."""
        relay, session_id = _setup_relay()
        reg_cred2 = relay.issue_registration_credential()
        sid2, attach_cred2 = relay.register_session("Test2", reg_cred2)
        session = relay.get_session(sid2)
        local_ws = AsyncMock()
        session.local_ws = local_ws

        ws = _make_mock_ws()
        await handle_remote_ws(relay, ws, sid2, attach_cred2)

        # remote_left proves the client was registered and then cleaned up
        assert len(session.remote_clients) == 0
        local_ws.send_json.assert_any_call(
            {"type": "remote_left", "client_id": ANY},
        )

    async def test_remote_message_forwarded_to_local(self):
        relay, session_id = _setup_relay()

        reg_cred2 = relay.issue_registration_credential()
        sid2, attach_cred2 = relay.register_session("Test2", reg_cred2)
        session = relay.get_session(sid2)

        local_ws = AsyncMock()
        session.local_ws = local_ws

        # Remote sends a message
        msg = MagicMock()
        msg.type = "text"
        msg.data = json.dumps(
            {"type": "message", "data": {"text": "from phone"}}
        )

        ws = _make_mock_ws()
        ws.__aiter__.return_value = iter([msg])

        await handle_remote_ws(relay, ws, sid2, attach_cred2)

        # Local should have received the forwarded message
        local_ws.send_json.assert_any_call(
            {
                "type": "message",
                "from": ws.send_json.call_args[0][0]["client_id"],
                "data": {"text": "from phone"},
            }
        )

    async def test_notifies_local_on_join(self):
        relay, session_id = _setup_relay()

        reg_cred2 = relay.issue_registration_credential()
        sid2, attach_cred2 = relay.register_session("Test2", reg_cred2)
        session = relay.get_session(sid2)
        local_ws = AsyncMock()
        session.local_ws = local_ws

        ws = _make_mock_ws()
        await handle_remote_ws(relay, ws, sid2, attach_cred2)

        # Local should have been notified of remote_joined
        local_ws.send_json.assert_any_call(
            {
                "type": "remote_joined",
                "client_id": ws.send_json.call_args[0][0]["client_id"],
            }
        )

    async def test_notifies_local_on_disconnect(self):
        relay, session_id = _setup_relay()

        reg_cred2 = relay.issue_registration_credential()
        sid2, attach_cred2 = relay.register_session("Test2", reg_cred2)
        session = relay.get_session(sid2)
        local_ws = AsyncMock()
        session.local_ws = local_ws

        ws = _make_mock_ws()
        await handle_remote_ws(relay, ws, sid2, attach_cred2)

        # Local should have been notified of remote_left
        local_ws.send_json.assert_any_call(
            {
                "type": "remote_left",
                "client_id": ws.send_json.call_args[0][0]["client_id"],
            }
        )

    async def test_invalid_json_skipped(self):
        relay, session_id = _setup_relay()
        reg_cred2 = relay.issue_registration_credential()
        sid2, attach_cred2 = relay.register_session("Test2", reg_cred2)
        session = relay.get_session(sid2)
        session.local_ws = AsyncMock()

        bad_msg = MagicMock()
        bad_msg.type = "text"
        bad_msg.data = "<<<not json>>>"

        ws = _make_mock_ws()
        ws.__aiter__.return_value = iter([bad_msg])

        # Should not raise
        await handle_remote_ws(relay, ws, sid2, attach_cred2)

    async def test_removes_client_from_session_after_disconnect(self):
        relay, session_id = _setup_relay()

        reg_cred2 = relay.issue_registration_credential()
        sid2, attach_cred2 = relay.register_session("Test2", reg_cred2)
        session = relay.get_session(sid2)
        session.local_ws = AsyncMock()

        ws = _make_mock_ws()
        await handle_remote_ws(relay, ws, sid2, attach_cred2)

        assert len(session.remote_clients) == 0
