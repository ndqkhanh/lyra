"""
Tests for OutboundRelayServer, ScopedCredentialMinter, SyncProtocol, and
MultiSurfaceSync.
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.remote.relay_server import (
    AllowedAction,
    CredentialScope,
    DiffEntry,
    MultiSurfaceSync,
    OutboundRelayServer,
    ScopedCredentialMinter,
    SurfaceInfo,
    SyncPatch,
    SyncProtocol,
)


# =========================================================================
# Helpers
# =========================================================================


class _AsyncMsgIter:
    def __init__(self, messages: list[dict] | None = None):
        self._messages = list(messages or [])

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        msg = self._messages.pop(0)
        return _Frame(msg)


class _Frame:
    type = "text"

    def __init__(self, data: dict) -> None:
        self.data = json.dumps(data)


def _make_mock_ws(messages=None):
    ws = MagicMock()
    ws.closed = False
    ws.__aiter__ = lambda *args: _AsyncMsgIter(messages or [])
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


def _patch_aiohttp(ws):
    patcher = patch("aiohttp.ClientSession")
    cls = patcher.start()
    sess = MagicMock()
    sess.ws_connect = AsyncMock(return_value=ws)
    cls.return_value = sess
    return patcher


# =========================================================================
# ScopedCredentialMinter
# =========================================================================


class TestScopedCredentialMinter:
    """Credential minting, verification, and revocation."""

    def setup_method(self):
        self.minter = ScopedCredentialMinter()

    def test_mint_returns_token_and_scope(self):
        token, scope = self.minter.mint("session-1")
        assert len(token) > 20
        assert scope.session_id == "session-1"
        assert scope.expiry is not None
        assert AllowedAction.ADMIN in scope.allowed_actions

    def test_mint_with_limited_actions(self):
        token, scope = self.minter.mint(
            "session-1",
            allowed_actions={AllowedAction.PEEK},
            max_uses=3,
        )
        assert scope.allowed_actions == frozenset({AllowedAction.PEEK})
        assert scope.max_uses == 3

    def test_verify_valid_token(self):
        token, _ = self.minter.mint("session-1")
        assert self.minter.verify(token, AllowedAction.ADMIN, "session-1") is True

    def test_verify_wrong_session(self):
        token, _ = self.minter.mint("session-1")
        assert self.minter.verify(token, AllowedAction.ADMIN, "session-2") is False

    def test_verify_wrong_action(self):
        token, _ = self.minter.mint(
            "session-1",
            allowed_actions={AllowedAction.PEEK},
        )
        assert self.minter.verify(token, AllowedAction.ADMIN, "session-1") is False

    def test_verify_unknown_token(self):
        assert self.minter.verify("fake-token", AllowedAction.PEEK, "session-1") is False

    def test_verify_revoked_token(self):
        token, _ = self.minter.mint("session-1")
        self.minter.revoke(token)
        assert self.minter.verify(token, AllowedAction.ADMIN, "session-1") is False

    def test_verify_use_limit_enforced(self):
        token, _ = self.minter.mint(
            "session-1",
            allowed_actions={AllowedAction.PEEK},
            max_uses=2,
        )
        assert self.minter.verify(token, AllowedAction.PEEK, "session-1") is True
        assert self.minter.verify(token, AllowedAction.PEEK, "session-1") is True
        assert self.minter.verify(token, AllowedAction.PEEK, "session-1") is False

    def test_revoke_returns_true_for_existing(self):
        token, _ = self.minter.mint("session-1")
        assert self.minter.revoke(token) is True

    def test_revoke_returns_false_for_unknown(self):
        assert self.minter.revoke("fake-token") is False

    def test_revoke_all_for_session(self):
        t1, _ = self.minter.mint("session-a")
        t2, _ = self.minter.mint("session-a")
        t3, _ = self.minter.mint("session-b")
        assert self.minter.revoke_all_for_session("session-a") == 2
        assert self.minter.verify(t1, AllowedAction.ADMIN, "session-a") is False
        assert self.minter.verify(t3, AllowedAction.ADMIN, "session-b") is True

    def test_list_active_returns_metadata(self):
        self.minter.mint("s1")
        self.minter.mint("s2", allowed_actions={AllowedAction.PEEK})
        active = self.minter.list_active()
        assert len(active) == 2
        for entry in active:
            assert "session_id" in entry
            assert "expires_at" in entry
            assert "allowed_actions" in entry
            assert "max_uses" in entry
            assert "use_count" in entry

    def test_list_active_excludes_expired(self):
        # Mint with a very short TTL and then advance
        import datetime

        token, scope = self.minter.mint("s1", ttl_seconds=-1)  # Already expired
        token2, _ = self.minter.mint("s2")
        active = self.minter.list_active()
        # The expired credential should be excluded
        ids = [a["session_id"] for a in active]
        assert "s1" not in ids
        assert "s2" in ids

    def test_verify_expired_token(self):
        import datetime

        token, scope = self.minter.mint("s1", ttl_seconds=-1)
        assert self.minter.verify(token, AllowedAction.ADMIN, "s1") is False

    def test_hash_consistency(self):
        h1 = ScopedCredentialMinter._hash("test-token")
        h2 = ScopedCredentialMinter._hash("test-token")
        assert h1 == h2

    def test_hash_different(self):
        h1 = ScopedCredentialMinter._hash("token-a")
        h2 = ScopedCredentialMinter._hash("token-b")
        assert h1 != h2


# =========================================================================
# SyncProtocol
# =========================================================================


class TestSyncProtocol:
    """Diff-based state synchronisation with LWW conflict resolution."""

    def setup_method(self):
        self.protocol = SyncProtocol()

    def test_get_default(self):
        assert self.protocol.get("nonexistent") is None
        assert self.protocol.get("nonexistent", "fallback") == "fallback"

    def test_set_and_get(self):
        self.protocol.set("tools.pending.0.status", "waiting")
        assert self.protocol.get("tools.pending.0.status") == "waiting"

    def test_snapshot_returns_copy(self):
        self.protocol.set("key", "value")
        snap = self.protocol.snapshot()
        assert snap == {"key": "value"}
        snap["key"] = "modified"
        assert self.protocol.get("key") == "value"  # Original unchanged

    def test_version_starts_at_zero(self):
        assert self.protocol.version == 0

    def test_version_increments_on_set(self):
        self.protocol.set("k", "v")
        assert self.protocol.version == 1
        self.protocol.set("k2", "v2")
        assert self.protocol.version == 2

    def test_delete(self):
        self.protocol.set("key", "value")
        assert self.protocol.get("key") == "value"
        self.protocol.delete("key")
        assert self.protocol.get("key") is None

    def test_delete_nonexistent(self):
        self.protocol.delete("nonexistent")  # Should not raise

    def test_apply_patch_new_values(self):
        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="a.b", value=42, timestamp=100.0)],
            base_version=0,
            source="mobile",
        )
        applied = self.protocol.apply_patch(patch)
        assert "a.b" in applied
        assert self.protocol.get("a.b") == 42
        assert self.protocol.version == 1

    def test_apply_patch_lww_newer_wins(self):
        self.protocol.set("key", "old", source="local")
        old_ts = time.time() - 10
        newer_ts = time.time()

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="key", value="new", timestamp=newer_ts)],
            base_version=0,
            source="remote",
        )
        applied = self.protocol.apply_patch(patch)
        assert "key" in applied
        assert self.protocol.get("key") == "new"

    def test_apply_patch_lww_older_loses(self):
        self.protocol.set("key", "new", source="local")
        newer_ts = time.time()
        older_ts = time.time() - 10

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="key", value="old", timestamp=older_ts)],
            base_version=0,
            source="remote",
        )
        applied = self.protocol.apply_patch(patch)
        assert "key" not in applied
        assert self.protocol.get("key") == "new"

    def test_apply_patch_deletion(self):
        self.protocol.set("key", "value")
        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="key", value=None, timestamp=time.time())],
            base_version=0,
            source="remote",
        )
        self.protocol.apply_patch(patch)
        assert self.protocol.get("key") is None

    def test_apply_patch_notifies_listeners(self):
        listener = MagicMock()
        self.protocol.on_sync(listener)

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="k", value="v", timestamp=1.0)],
            base_version=0,
            source="mobile",
        )
        self.protocol.apply_patch(patch)
        listener.assert_called_once_with(patch)

    def test_listener_exception_does_not_crash(self):
        def failing_listener(patch):
            raise RuntimeError("listener failed")

        self.protocol.on_sync(failing_listener)
        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="k", value="v", timestamp=1.0)],
            base_version=0,
            source="mobile",
        )
        # Should not raise
        self.protocol.apply_patch(patch)

    def test_on_sync_decorator(self):
        @self.protocol.on_sync
        def handler(patch):
            pass

        assert handler in self.protocol._listeners

    def test_conflicts_detects_close_timestamps(self):
        self.protocol.set("key", "original", source="local")
        original_ts = time.time()

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="key", value="remote", timestamp=original_ts + 0.5)],
            base_version=0,
            source="remote",
        )
        conflicts = self.protocol.conflicts(patch)
        assert len(conflicts) == 1
        assert conflicts[0].path == "key"

    def test_conflicts_no_conflict_wide_gap(self):
        self.protocol.set("key", "original", source="local")
        old_ts = time.time() - 10

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="key", value="remote", timestamp=old_ts)],
            base_version=0,
            source="remote",
        )
        conflicts = self.protocol.conflicts(patch)
        # The existing timestamp is much newer than the patch's timestamp,
        # so the gap is > 1 second and should not be a conflict
        assert len(conflicts) == 0

    def test_compute_patch_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            self.protocol.compute_patch("s1", "mobile")


# =========================================================================
# MultiSurfaceSync
# =========================================================================


class TestMultiSurfaceSync:
    """Multi-surface state synchronisation orchestration."""

    def setup_method(self):
        self.sync = MultiSurfaceSync()

    def test_bind_session(self):
        self.sync.bind_session("lyra-abc")
        assert self.sync._session_id == "lyra-abc"

    def test_register_surface(self):
        info = self.sync.register_surface("phone-1", "mobile")
        assert info.surface_id == "phone-1"
        assert info.surface_type == "mobile"
        assert info.connected_at > 0
        assert info.protocol_version == 1

    def test_register_duplicate_surface(self):
        self.sync.register_surface("phone-1", "mobile")
        # Second registration overwrites the first
        info = self.sync.register_surface("phone-1", "desktop")
        assert info.surface_type == "desktop"

    def test_unregister_surface(self):
        self.sync.register_surface("phone-1", "mobile")
        self.sync.unregister_surface("phone-1")
        assert self.sync.get_surface("phone-1") is None

    def test_unregister_unknown(self):
        self.sync.unregister_surface("unknown")  # Should not raise

    def test_get_surface_returns_none(self):
        assert self.sync.get_surface("nonexistent") is None

    def test_list_surfaces(self):
        self.sync.register_surface("a", "mobile")
        self.sync.register_surface("b", "desktop")
        assert len(self.sync.list_surfaces()) == 2

    def test_apply_remote_patch(self):
        self.sync.bind_session("s1")
        self.sync.register_surface("phone-1", "mobile")

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="status", value="running")],
            base_version=0,
            source="phone-1",
        )
        applied = self.sync.apply_remote_patch(patch, "phone-1")
        assert "status" in applied
        # last_sync_at should be updated
        surface = self.sync.get_surface("phone-1")
        assert surface is not None
        assert surface.last_sync_at > 0

    def test_apply_remote_patch_unknown_surface(self):
        """Applying a patch from an unregistered surface is still applied."""
        self.sync.bind_session("s1")
        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="k", value="v")],
            base_version=0,
            source="unknown",
        )
        applied = self.sync.apply_remote_patch(patch, "unknown")
        assert "k" in applied

    def test_compute_patch_for_uptodate_returns_none(self):
        """compute_patch_for returns None when surface is current."""
        self.sync.bind_session("s1")
        self.sync.register_surface("phone-1", "mobile")
        result = self.sync.compute_patch_for("phone-1")
        assert result is None

    def test_compute_patch_for_stale_returns_full_snapshot(self):
        self.sync.bind_session("s1")
        self.sync.register_surface("phone-1", "mobile")

        # Apply some changes from a different surface
        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="status", value="done")],
            base_version=0,
            source="desktop",
        )
        self.sync.apply_remote_patch(patch, "desktop")

        result = self.sync.compute_patch_for("phone-1")
        assert result is not None
        assert len(result.diffs) == 1
        assert result.diffs[0].path == "status"
        assert result.diffs[0].value == "done"

    def test_detect_conflicts(self):
        self.sync.bind_session("s1")
        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="k", value="v", timestamp=time.time())],
            base_version=0,
            source="mobile",
        )
        conflicts = self.sync.detect_conflicts(patch)
        assert isinstance(conflicts, list)

    def test_surface_info_dataclass(self):
        info = SurfaceInfo(
            surface_id="test",
            surface_type="mobile",
            connected_at=100.0,
            last_sync_at=200.0,
            protocol_version=2,
        )
        assert info.surface_id == "test"
        assert info.protocol_version == 2


# =========================================================================
# OutboundRelayServer
# =========================================================================


class TestOutboundRelayServer:
    """Outbound relay server lifecycle and message handling."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_start_connects_and_authenticates(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub.example.com/relay",
                instance_id="my-laptop",
            )
            await relay.start()
            assert relay._ws is ws
            assert relay._running is True
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_stop_closes_ws(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub.example.com/relay",
                instance_id="my-laptop",
            )
            await relay.start()
            await relay.stop()
            ws.close.assert_called_once()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_start_reconnect_exhausted(self):
        """Reconnect attempts exhaust with max_reconnect_attempts set."""
        patcher = patch("aiohttp.ClientSession")
        cls = patcher.start()
        sess = MagicMock()
        sess.ws_connect = AsyncMock(side_effect=ConnectionError("no route to host"))
        cls.return_value = sess
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub.example.com/relay",
                instance_id="laptop",
                max_reconnect_attempts=1,
            )
            with pytest.raises(ConnectionError, match="Max reconnect attempts"):
                await relay.start()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_start_sends_auth_frame(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub.example.com/relay",
                instance_id="my-laptop",
            )
            await relay.start()
            auth_sent = False
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and isinstance(args[0], dict) and args[0].get("type") == "relay_auth":
                    assert args[0]["instance_id"] == "my-laptop"
                    auth_sent = True
            assert auth_sent
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_background_tasks(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub.example.com/relay",
                instance_id="my-laptop",
            )
            await relay.start()
            assert len(relay._background_tasks) == 2
            await relay.stop()
            assert len(relay._background_tasks) == 0
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_stop_twice_no_error(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            await relay.stop()
            await relay.stop()  # Should not raise
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # Session registration
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_session_unconnected_raises(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        with pytest.raises(ConnectionError, match="Outbound relay not connected"):
            await relay.register_session("lyra-test")

    @pytest.mark.asyncio
    async def test_register_session_success(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            result = await relay.register_session("lyra-abc")
            assert result["session_id"] == "lyra-abc"
            assert "admin_token" in result
            assert len(result["admin_token"]) > 20
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_unregister_session(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            await relay.register_session("lyra-abc")
            ws.send_json.reset_mock()
            await relay.unregister_session("lyra-abc")
            # Should have sent unregister message
            unreg_sent = False
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and args[0].get("type") == "unregister_relay_session":
                    unreg_sent = True
            assert unreg_sent
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_unregister_session_no_ws(self):
        """unregister_session works when relay is not connected."""
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        await relay.unregister_session("lyra-test")  # Should not raise

    # ------------------------------------------------------------------
    # Credential minting helpers
    # ------------------------------------------------------------------

    def test_mint_attach_credential(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        token, scope = relay.mint_attach_credential("session-1")
        assert AllowedAction.ATTACH in scope.allowed_actions
        assert AllowedAction.STEER in scope.allowed_actions
        assert AllowedAction.PEEK in scope.allowed_actions

    def test_mint_steer_credential(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        token, scope = relay.mint_steer_credential("session-1", max_uses=5)
        assert scope.allowed_actions == frozenset({AllowedAction.STEER})
        assert scope.max_uses == 5

    # ------------------------------------------------------------------
    # State sync proxy
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_sync_state(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            await relay.register_session("lyra-abc")

            updated = await relay.sync_state(
                "phone-1",
                {"tools.status": "running", "tools.output": "ok"},
            )
            assert "tools.status" in updated
            assert "tools.output" in updated
            await relay.stop()
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # Frame handling
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_handle_heartbeat_ack(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        await relay._handle_frame({"type": "heartbeat_ack"})
        # Should not raise or do anything

    @pytest.mark.asyncio
    async def test_handle_auth_ok(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        await relay._handle_frame({"type": "relay_auth_ok"})
        # Should not raise

    @pytest.mark.asyncio
    async def test_handle_surface_attach_invalid_credential(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            ws.send_json.reset_mock()

            await relay._handle_surface_attach({
                "surface_id": "phone-1",
                "surface_type": "mobile",
                "credential": "invalid",
                "session_id": "s1",
            })

            # Should have sent failure response
            attach_result = None
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and args[0].get("type") == "surface_attach_result":
                    attach_result = args[0]
            assert attach_result is not None
            assert attach_result["success"] is False
            assert attach_result["error"] == "invalid_credential"
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_handle_surface_attach_valid(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            await relay.register_session("lyra-s1")

            # Mint an attach credential
            token, _ = relay.mint_attach_credential("lyra-s1")
            ws.send_json.reset_mock()

            await relay._handle_surface_attach({
                "surface_id": "phone-1",
                "surface_type": "mobile",
                "credential": token,
                "session_id": "lyra-s1",
            })

            attach_result = None
            for call in ws.send_json.call_args_list:
                args, _ = call
                if args and args[0].get("type") == "surface_attach_result":
                    attach_result = args[0]
            assert attach_result is not None
            assert attach_result["success"] is True
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_handle_surface_sync_unknown_ignored(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        # Unknown surface should be ignored
        await relay._handle_surface_sync({
            "surface_id": "unknown",
            "state_updates": {"k": "v"},
        })

    @pytest.mark.asyncio
    async def test_handle_surface_detach(self):
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            relay.sync.register_surface("phone-1", "mobile")
            assert relay.sync.get_surface("phone-1") is not None

            await relay._handle_surface_detach({"surface_id": "phone-1"})
            assert relay.sync.get_surface("phone-1") is None
            await relay.stop()
        finally:
            patcher.stop()

    # ------------------------------------------------------------------
    # Listen loop
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_listen_loop_processes_messages(self):
        ws = _make_mock_ws([{"type": "heartbeat_ack"}, {"type": "relay_auth_ok"}])
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            await asyncio.sleep(0.02)
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_listen_loop_handles_close_frame(self):
        ws_messages = [{"type": "heartbeat_ack"}]
        ws = _make_mock_ws(ws_messages)
        # After the messages, the iteration will hit StopAsyncIteration
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            await asyncio.sleep(0.02)
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_listen_loop_handles_json_error(self):
        ws = _make_mock_ws()
        ws.data = "not-json"
        ws.type = "text"
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            await asyncio.sleep(0.02)
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_heartbeat_loop(self):
        """Heartbeat loop runs as a background task during start()."""
        ws = _make_mock_ws()
        patcher = _patch_aiohttp(ws)
        try:
            relay = OutboundRelayServer(
                hub_url="wss://hub/relay",
                instance_id="laptop",
            )
            await relay.start()
            # Background tasks are started, including heartbeat loop
            ws.send_json.reset_mock()
            await relay.stop()
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_cancelled(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        # Create task with _running=False so loop exits immediately
        task = asyncio.create_task(relay._heartbeat_loop())
        await task  # Should not raise

    # ------------------------------------------------------------------
    # _send helper
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_no_ws(self):
        relay = OutboundRelayServer(
            hub_url="wss://hub/relay",
            instance_id="laptop",
        )
        await relay._send({"type": "test"})  # Should not raise

    # ------------------------------------------------------------------
    # AllowedAction enum
    # ------------------------------------------------------------------

    def test_allowed_action_values(self):
        assert AllowedAction.REGISTER.value == "register"
        assert AllowedAction.ATTACH.value == "attach"
        assert AllowedAction.STEER.value == "steer"
        assert AllowedAction.PEEK.value == "peek"
        assert AllowedAction.ADMIN.value == "admin"

    # ------------------------------------------------------------------
    # CredentialScope
    # ------------------------------------------------------------------

    def test_credential_scope_frozen(self):
        scope = CredentialScope(
            session_id="s1",
            expiry=time.time(),
            allowed_actions=frozenset({AllowedAction.PEEK}),
            max_uses=5,
        )
        assert scope.session_id == "s1"
        assert AllowedAction.PEEK in scope.allowed_actions

    # ------------------------------------------------------------------
    # DiffEntry / SyncPatch
    # ------------------------------------------------------------------

    def test_diff_entry_defaults(self):
        d = DiffEntry(path="a.b", value=1)
        assert d.timestamp == 0.0
        assert d.source == "unknown"

    def test_sync_patch_defaults(self):
        p = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="k", value="v")],
            base_version=0,
            source="mobile",
        )
        assert p.session_id == "s1"

    def test_surface_info_defaults(self):
        info = SurfaceInfo(surface_id="test", surface_type="mobile")
        assert info.connected_at == 0.0
        assert info.protocol_version == 1
