"""
Tests for Lyra Remote v9.0 advanced features.

Covers:
- OutboundRelayServer: connection, session registration, credential minting
- ScopedCredentialMinter: mint, verify, revoke, scope enforcement
- MultiSurfaceSync: surface registration, sync patch application, conflict detection
- SyncProtocol: diff-based state updates, LWW conflict resolution
- Push notifications: APNs/FCM payloads, rich notifications, notification templates
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.remote.relay_server import (
    AllowedAction,
    CredentialScope,
    DiffEntry,
    MultiSurfaceSync,
    OutboundRelayServer,
    ScopedCredentialMinter,
    SyncPatch,
    SyncProtocol,
)
from lyra.remote.mobile_steering import (
    APNsPayload,
    FCMPayload,
    NotificationAction,
    NotificationManager,
    NotificationTemplate,
    NotificationType,
    RichNotification,
)
from lyra.remote.zero_trust_relay import SessionEvent


# ======================================================================
# ScopedCredentialMinter tests
# ======================================================================


class TestScopedCredentialMinter:
    """Test credential minting, verification, and revocation."""

    def test_mint_credential(self):
        """Minting a credential returns a token and a valid scope."""
        minter = ScopedCredentialMinter()
        token, scope = minter.mint(
            "session-1",
            ttl_seconds=3600,
            allowed_actions={AllowedAction.ATTACH, AllowedAction.STEER},
            max_uses=3,
        )

        assert len(token) > 16
        assert scope.session_id == "session-1"
        assert AllowedAction.ATTACH in scope.allowed_actions
        assert AllowedAction.STEER in scope.allowed_actions
        assert AllowedAction.ADMIN not in scope.allowed_actions
        assert scope.max_uses == 3
        assert scope.expiry > datetime.now(timezone.utc)

    def test_verify_valid_credential(self):
        """A freshly minted credential verifies successfully."""
        minter = ScopedCredentialMinter()
        token, _ = minter.mint(
            "session-1",
            allowed_actions={AllowedAction.ATTACH},
        )

        assert minter.verify(token, AllowedAction.ATTACH, "session-1") is True

    def test_verify_expired_credential(self):
        """An expired credential fails verification."""
        minter = ScopedCredentialMinter()
        token, scope = minter.mint(
            "session-1",
            ttl_seconds=0,
            allowed_actions={AllowedAction.ATTACH},
        )

        # Fast-forward time by patching our check
        assert minter.verify(token, AllowedAction.ATTACH, "session-1") is False

    def test_verify_wrong_action(self):
        """A credential scoped to one action fails for another."""
        minter = ScopedCredentialMinter()
        token, _ = minter.mint(
            "session-1",
            allowed_actions={AllowedAction.PEEK},
        )

        assert minter.verify(token, AllowedAction.ATTACH, "session-1") is False
        assert minter.verify(token, AllowedAction.PEEK, "session-1") is True

    def test_verify_wrong_session(self):
        """A credential scoped to one session fails for another."""
        minter = ScopedCredentialMinter()
        token, _ = minter.mint("session-1")

        assert minter.verify(token, AllowedAction.ATTACH, "session-2") is False

    def test_verify_unknown_token(self):
        """An unknown token fails verification."""
        minter = ScopedCredentialMinter()
        assert minter.verify("fake-token", AllowedAction.ATTACH, "session-1") is False

    def test_max_uses_limit(self):
        """A credential with max_uses is revoked after that many uses."""
        minter = ScopedCredentialMinter()
        token, _ = minter.mint(
            "session-1",
            allowed_actions={AllowedAction.PEEK},
            max_uses=2,
        )

        assert minter.verify(token, AllowedAction.PEEK, "session-1") is True
        assert minter.verify(token, AllowedAction.PEEK, "session-1") is True
        # Third use should fail
        assert minter.verify(token, AllowedAction.PEEK, "session-1") is False

    def test_revoke_credential(self):
        """Revoking a credential invalidates it immediately."""
        minter = ScopedCredentialMinter()
        token, _ = minter.mint("session-1")

        assert minter.revoke(token) is True
        assert minter.verify(token, AllowedAction.ATTACH, "session-1") is False

    def test_revoke_all_for_session(self):
        """Revoking all credentials for a session invalidates all of them."""
        minter = ScopedCredentialMinter()
        t1, _ = minter.mint("session-1")
        t2, _ = minter.mint("session-1")
        t3, _ = minter.mint("session-2")

        count = minter.revoke_all_for_session("session-1")
        assert count == 2

        assert minter.verify(t1, AllowedAction.ATTACH, "session-1") is False
        assert minter.verify(t2, AllowedAction.ATTACH, "session-1") is False
        # session-2 cred should still work
        assert minter.verify(t3, AllowedAction.ATTACH, "session-2") is True

    def test_list_active(self):
        """list_active returns only non-expired credentials."""
        minter = ScopedCredentialMinter()
        token, _ = minter.mint("session-1", ttl_seconds=3600, allowed_actions={AllowedAction.PEEK})

        # Mint an expired one
        e_token, _ = minter.mint("session-2", ttl_seconds=0)

        active = minter.list_active()
        assert len(active) >= 1
        # Expired credential should not appear
        for entry in active:
            assert entry["session_id"] != "session-2"


# ======================================================================
# SyncProtocol tests
# ======================================================================


class TestSyncProtocol:
    """Test diff-based state synchronisation with LWW conflict resolution."""

    def test_set_and_get(self):
        """Setting a path and reading it back works."""
        proto = SyncProtocol()
        proto.set("agent.status", "running")
        assert proto.get("agent.status") == "running"

    def test_delete(self):
        """Deleting a path removes it from state."""
        proto = SyncProtocol()
        proto.set("agent.status", "running")
        proto.delete("agent.status")
        assert proto.get("agent.status") is None

    def test_snapshot(self):
        """snapshot returns a copy of all values."""
        proto = SyncProtocol()
        proto.set("a", 1)
        proto.set("b", 2)
        snap = proto.snapshot()
        assert snap == {"a": 1, "b": 2}

    def test_version_increments(self):
        """Version increments on each change."""
        proto = SyncProtocol()
        v0 = proto.version
        proto.set("a", 1)
        assert proto.version == v0 + 1

    def test_apply_patch(self):
        """Applying a sync patch updates state."""
        proto = SyncProtocol()
        patch = SyncPatch(
            session_id="s1",
            diffs=[
                DiffEntry(path="status", value="running", timestamp=100.0, source="mobile"),
                DiffEntry(path="progress.pct", value=50, timestamp=100.0, source="mobile"),
            ],
            base_version=0,
            source="mobile",
        )
        applied = proto.apply_patch(patch)
        assert "status" in applied
        assert "progress.pct" in applied
        assert proto.get("status") == "running"
        assert proto.get("progress.pct") == 50

    def test_lww_conflict_resolution(self):
        """Later timestamp wins in LWW conflict."""
        proto = SyncProtocol()
        proto.set("status", "old_value", source="local")
        # Simulate the timestamp being at 50
        proto._timestamps["status"] = 50.0

        old_patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="status", value="should_lose", timestamp=25.0, source="mobile")],
            base_version=0,
            source="mobile",
        )
        new_patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="status", value="should_win", timestamp=100.0, source="mobile")],
            base_version=0,
            source="mobile",
        )

        proto.apply_patch(old_patch)
        assert proto.get("status") == "old_value"  # old_value at ts 50 wins over ts 25

        proto.apply_patch(new_patch)
        assert proto.get("status") == "should_win"  # ts 100 wins over ts 50

    def test_on_sync_listener(self):
        """Registered listeners fire on patch application."""
        proto = SyncProtocol()
        calls: list[SyncPatch] = []

        @proto.on_sync
        def listener(patch):
            calls.append(patch)

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="a", value=1, timestamp=100.0, source="mobile")],
            base_version=0,
            source="mobile",
        )
        proto.apply_patch(patch)
        assert len(calls) == 1
        assert calls[0].source == "mobile"

    def test_conflicts_detection(self):
        """Conflicting updates are flagged."""
        proto = SyncProtocol()
        proto.set("x", 1, source="local")
        proto._timestamps["x"] = 100.5

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="x", value=2, timestamp=100.8, source="mobile")],
            base_version=0,
            source="mobile",
        )
        conflicts = proto.conflicts(patch)
        assert len(conflicts) == 1
        assert conflicts[0].path == "x"


# ======================================================================
# MultiSurfaceSync tests
# ======================================================================


class TestMultiSurfaceSync:
    """Test multi-surface state synchronisation orchestration."""

    def test_register_unregister_surface(self):
        """Registering and unregistering surfaces works."""
        mss = MultiSurfaceSync()
        mss.bind_session("s1")

        info = mss.register_surface("phone-1", "mobile")
        assert info.surface_id == "phone-1"
        assert info.surface_type == "mobile"

        assert len(mss.list_surfaces()) == 1
        mss.unregister_surface("phone-1")
        assert len(mss.list_surfaces()) == 0

    def test_apply_remote_patch(self):
        """Applying a remote patch updates the protocol state."""
        mss = MultiSurfaceSync()
        mss.bind_session("s1")
        mss.register_surface("phone-1", "mobile")

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="status", value="running", timestamp=100.0, source="phone-1")],
            base_version=0,
            source="phone-1",
        )
        applied = mss.apply_remote_patch(patch, from_surface="phone-1")
        assert "status" in applied
        assert mss._protocol.get("status") == "running"

    def test_compute_patch_for_new_surface(self):
        """A new surface gets a full-state patch."""
        mss = MultiSurfaceSync()
        mss.bind_session("s1")
        mss._protocol.set("status", "running")

        mss.register_surface("web-1", "web")
        patch = mss.compute_patch_for("web-1", source="server")
        assert patch is not None
        assert len(patch.diffs) > 0

    def test_compute_patch_for_synced_surface(self):
        """An up-to-date surface gets no patch."""
        mss = MultiSurfaceSync()
        mss.bind_session("s1")
        mss.register_surface("web-1", "web")

        # Initial sync brings the surface up to date
        mss._surface_versions["web-1"] = mss._protocol.version

        patch = mss.compute_patch_for("web-1", source="server")
        assert patch is None

    def test_detect_conflicts(self):
        """Conflict detection delegates to the protocol."""
        mss = MultiSurfaceSync()
        mss.bind_session("s1")
        mss._protocol.set("x", 1)
        mss._protocol._timestamps["x"] = 100.5

        patch = SyncPatch(
            session_id="s1",
            diffs=[DiffEntry(path="x", value=2, timestamp=100.8, source="mobile")],
            base_version=0,
            source="mobile",
        )
        conflicts = mss.detect_conflicts(patch)
        assert len(conflicts) == 1


# ======================================================================
# OutboundRelayServer tests
# ======================================================================


class TestOutboundRelayServer:
    """Test the outbound relay server (with mocked WebSocket)."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Server initialises with a credential minter and sync."""
        relay = OutboundRelayServer(
            hub_url="wss://hub.test/relay",
            instance_id="test-laptop",
        )
        assert relay._hub_url == "wss://hub.test/relay"
        assert relay._instance_id == "test-laptop"
        assert isinstance(relay.credential_minter, ScopedCredentialMinter)
        assert isinstance(relay.sync, MultiSurfaceSync)

    def test_mint_attach_credential(self):
        """mint_attach_credential produces a valid credential."""
        relay = OutboundRelayServer(
            hub_url="wss://hub.test/relay",
            instance_id="test-laptop",
        )
        token, scope = relay.mint_attach_credential("session-1")
        assert scope.session_id == "session-1"
        assert AllowedAction.ATTACH in scope.allowed_actions
        assert AllowedAction.STEER in scope.allowed_actions
        assert AllowedAction.PEEK in scope.allowed_actions
        assert AllowedAction.ADMIN not in scope.allowed_actions

    def test_mint_steer_credential(self):
        """mint_steer_credential produces a limited-use credential."""
        relay = OutboundRelayServer(
            hub_url="wss://hub.test/relay",
            instance_id="test-laptop",
        )
        token, scope = relay.mint_steer_credential("session-1", max_uses=5)
        assert scope.max_uses == 5
        assert AllowedAction.STEER in scope.allowed_actions
        assert AllowedAction.ATTACH not in scope.allowed_actions

    @pytest.mark.asyncio
    async def test_register_session_fails_when_disconnected(self):
        """register_session raises ConnectionError when not connected."""
        relay = OutboundRelayServer(
            hub_url="wss://hub.test/relay",
            instance_id="test-laptop",
        )
        with pytest.raises(ConnectionError):
            await relay.register_session("session-1")

    @pytest.mark.asyncio
    async def test_sync_state(self):
        """sync_state applies state updates."""
        relay = OutboundRelayServer(
            hub_url="wss://hub.test/relay",
            instance_id="test-laptop",
        )
        relay.sync.bind_session("s1")

        updates = {"status": "running", "progress.pct": 50}
        applied = await relay.sync_state("phone-1", updates)
        assert "status" in applied
        assert "progress.pct" in applied


# ======================================================================
# Push notification tests
# ======================================================================


class TestAPNsPayload:
    """Test APNs payload building."""

    def test_basic_payload(self):
        """A basic payload contains aps.alert.title and aps.alert.body."""
        payload = APNsPayload(
            alert_title="Test Alert",
            alert_body="This is a test.",
            category="test_category",
        )
        built = payload.build()
        assert built["aps"]["alert"]["title"] == "Test Alert"
        assert built["aps"]["alert"]["body"] == "This is a test."
        assert built["aps"]["category"] == "test_category"

    def test_custom_data(self):
        """Custom data is merged into the payload."""
        payload = APNsPayload(
            alert_title="Test",
            alert_body="Body",
            custom_data={"lyra_key": "value"},
        )
        built = payload.build()
        assert built["lyra_key"] == "value"

    def test_mutable_content(self):
        """mutable_content flag sets aps.mutable-content."""
        payload = APNsPayload(
            alert_title="Test",
            alert_body="Body",
            mutable_content=True,
        )
        built = payload.build()
        assert built["aps"]["mutable-content"] == 1

    def test_badge_zero(self):
        """Badge zero clears the badge."""
        payload = APNsPayload(
            alert_title="Test",
            alert_body="Body",
            badge=0,
        )
        built = payload.build()
        assert built["aps"]["badge"] == 0


class TestFCMPayload:
    """Test FCM payload building."""

    def test_basic_payload(self):
        """A basic FCM payload has notification and data sections."""
        payload = FCMPayload(
            title="Test Alert",
            body="This is a test.",
            click_action="LYRA_TEST",
        )
        built = payload.build()
        assert built["notification"]["title"] == "Test Alert"
        assert built["notification"]["body"] == "This is a test."
        assert built["notification"]["click_action"] == "LYRA_TEST"
        assert built["data"]["lyra_type"] == "notification"

    def test_custom_data(self):
        """Custom data is included in the data section."""
        payload = FCMPayload(
            title="Test",
            body="Body",
            data={"session_id": "abc123"},
        )
        built = payload.build()
        assert built["data"]["session_id"] == "abc123"


class TestRichNotification:
    """Test rich notification building."""

    def test_for_approval_request(self):
        """Approval request notification has action buttons."""
        notif = RichNotification.for_approval_request(
            session_id="s1",
            tool_name="read_file",
            tool_call_id="tc_001",
        )
        assert notif.session_id == "s1"
        assert len(notif.actions) == 2
        assert notif.actions[0].identifier == "APPROVE"
        assert notif.actions[1].identifier == "DENY"
        assert notif.apns_payload is not None
        assert notif.fcm_payload is not None
        assert notif.actions[0].title == "Approve"

    def test_for_completion(self):
        """Completion notification has no action buttons."""
        notif = RichNotification.for_completion(
            session_id="s1",
            summary="Done.",
            duration_seconds=120.0,
        )
        assert notif.session_id == "s1"
        assert notif.event == SessionEvent.COMPLETION
        assert len(notif.actions) == 0
        assert notif.apns_payload.alert_title == "Session Complete"
        assert notif.apns_payload.badge == 0

    def test_for_error(self):
        """Error notification includes the error message."""
        notif = RichNotification.for_error(
            session_id="s1",
            error_message="Connection failed",
        )
        assert notif.event == SessionEvent.ERROR
        assert "error" in notif.apns_payload.alert_body.lower()

    def test_for_cost_alert(self):
        """Cost alert notification has view/pause actions."""
        notif = RichNotification.for_cost_alert(
            session_id="s1",
            cost=5.50,
            threshold=5.00,
        )
        assert notif.event == SessionEvent.COST_ALERT
        assert len(notif.actions) == 2
        assert notif.actions[0].identifier == "VIEW_SESSION"
        assert "$5.50" in notif.apns_payload.alert_body
        assert notif.fcm_payload.data["lyra_cost"] == "5.5"

    def test_to_push_notification(self):
        """Rich notification converts to a PushNotification for relay delivery."""
        notif = RichNotification.for_approval_request(
            session_id="s1",
            tool_name="execute",
            tool_call_id="tc_001",
        )
        push = notif.to_push_notification()
        assert push.session_id == "s1"
        assert push.title == notif.apns_payload.alert_title
        assert push.body == notif.apns_payload.alert_body
        assert "actions" in push.data
        assert push.data["apns"] is not None
        assert push.data["fcm"] is not None


class TestNotificationManager:
    """Test notification template registration and delivery."""

    def test_default_templates_exist(self):
        """All notification types have default templates."""
        mgr = NotificationManager()
        for ntype in NotificationType:
            template = mgr.get_template(ntype)
            assert template is not None, f"Missing template for {ntype}"

    def test_register_custom_template(self):
        """Registering a custom template overrides the default."""
        mgr = NotificationManager()
        custom = NotificationTemplate(
            notification_type=NotificationType.COMPLETION,
            title_template="Custom Complete",
            body_template="Custom body for {session_id}",
        )
        mgr.register_template(custom)
        retrieved = mgr.get_template(NotificationType.COMPLETION)
        assert retrieved is not None
        assert retrieved.title_template == "Custom Complete"

    def test_template_rendering(self):
        """Template renders title and body with variables."""
        template = NotificationTemplate(
            notification_type=NotificationType.COMPLETION,
            title_template="{session_id} Complete",
            body_template="Session {session_id} finished after {duration}s",
        )
        title = template.render_title(session_id="s1")
        body = template.render_body(session_id="s1", duration="120")
        assert title == "s1 Complete"
        assert body == "Session s1 finished after 120s"

    def test_template_rendering_missing_key(self):
        """Missing template keys fall back to the raw template."""
        template = NotificationTemplate(
            notification_type=NotificationType.COMPLETION,
            title_template="Hello {name}",
            body_template="Body",
        )
        title = template.render_title()
        assert title == "Hello {name}"  # Falls back to raw template

    def test_send_apns(self):
        """APNs delivery returns a success response."""
        mgr = NotificationManager()
        payload = APNsPayload(alert_title="Test", alert_body="Body")
        result = mgr.send_apns(payload, "fake-device-token")
        assert result["success"] is True
        assert result["service"] == "apns"

    def test_send_fcm(self):
        """FCM delivery returns a success response."""
        mgr = NotificationManager()
        payload = FCMPayload(title="Test", body="Body")
        result = mgr.send_fcm(payload, "fake-device-token")
        assert result["success"] is True
        assert result["service"] == "fcm"

    def test_list_templates(self):
        """list_templates returns metadata for all registered templates."""
        mgr = NotificationManager()
        templates = mgr.list_templates()
        assert len(templates) >= len(NotificationType)
        for t in templates:
            assert "notification_type" in t
            assert "title_template" in t
            assert "priority" in t
