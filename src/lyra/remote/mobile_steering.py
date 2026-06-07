"""
Mobile Steering Surface — high-level API for mobile control of Lyra sessions.

Provides a ``MobileSteeringSurface`` class that wraps
:class:`lyra.remote.zero_trust_relay.ZeroTrustRelay` with convenient methods
for checking session status, approving/denying tool calls, sending messages,
subscribing to real-time session events, and managing push notifications.

This version adds comprehensive push notification support:
- APNs (iOS) and FCM (Android) integration
- Rich notifications with action buttons (Approve/Deny)
- Customizable NotificationTemplates
- Completion, error, approval_request, and cost_alert notification types

Usage
-----

.. code-block:: python

    from lyra.remote import (
        MobileSteeringSurface, RelayConfig, SessionEvent,
    )

    surface = MobileSteeringSurface(
        relay_url="wss://relay.lyra.example.com/ws",
        device_id="my-phone",
    )

    # At-a-glance session summary
    summary = await surface.status("lyra-abc123")
    print(summary.pending_approvals)

    # Approve a tool call
    await surface.approve("tool_call_001")

    # Deny a tool call
    await surface.deny("tool_call_001")

    # Send a message to the agent
    await surface.message("lyra-abc123", "Please summarize the results")

    # Subscribe to real-time events
    await surface.subscribe("lyra-abc123", SessionEvent.NEEDS_APPROVAL,
                            lambda s, p: print("Approval needed!"))
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from lyra.remote.zero_trust_relay import (
    MobileAction,
    PushNotification,
    RelayConfig,
    SessionEvent,
    SessionSummary,
    SignedCommand,
    ZeroTrustRelay,
    build_notification,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Notification types
# ---------------------------------------------------------------------------


class NotificationType(str, Enum):
    """Extended notification types beyond basic session events."""

    COMPLETION = "completion"
    ERROR = "error"
    APPROVAL_REQUEST = "approval_request"
    COST_ALERT = "cost_alert"
    DISCONNECTED = "disconnected"
    SESSION_STARTED = "session_started"
    TOOL_COMPLETED = "tool_completed"
    MILESTONE = "milestone"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Push notification service abstraction
# ---------------------------------------------------------------------------


@dataclass
class NotificationTemplate:
    """A configurable template for push notification messages.

    Attributes:
        notification_type: The type of notification.
        title_template: Template string for the title (may contain ``{var}`` placeholders).
        body_template: Template string for the body.
        priority: Push notification priority (``"default"``, ``"high"``, ``"normal"``).
        category: iOS notification category for action buttons.
        sound: Notification sound name.
        badge: Badge count (``+1`` to increment, or an integer).
        ttl: Time-to-live in seconds before the notification is dropped.
    """

    notification_type: NotificationType | str
    title_template: str
    body_template: str
    priority: str = "default"
    category: str = ""
    sound: str = "default"
    badge: int = 0
    ttl: int = 86400  # 24 hours

    def render_title(self, **kwargs: Any) -> str:
        """Render the title template with *kwargs* variables."""
        try:
            return self.title_template.format(**kwargs)
        except KeyError:
            return self.title_template

    def render_body(self, **kwargs: Any) -> str:
        """Render the body template with *kwargs* variables."""
        try:
            return self.body_template.format(**kwargs)
        except KeyError:
            return self.body_template


# Default notification templates
_DEFAULT_TEMPLATES: dict[NotificationType, NotificationTemplate] = {
    NotificationType.COMPLETION: NotificationTemplate(
        notification_type=NotificationType.COMPLETION,
        title_template="Session Complete",
        body_template="Your Lyra session {session_id} has finished its work.",
        priority="normal",
        category="session_complete",
    ),
    NotificationType.ERROR: NotificationTemplate(
        notification_type=NotificationType.ERROR,
        title_template="Session Error",
        body_template="Your Lyra session {session_id} encountered an error: {error_message}.",
        priority="high",
        category="session_error",
        sound="alert",
    ),
    NotificationType.APPROVAL_REQUEST: NotificationTemplate(
        notification_type=NotificationType.APPROVAL_REQUEST,
        title_template="Approval Required",
        body_template="Session {session_id}: {tool_name} needs your approval to proceed.",
        priority="high",
        category="approval_request",
    ),
    NotificationType.COST_ALERT: NotificationTemplate(
        notification_type=NotificationType.COST_ALERT,
        title_template="Cost Alert",
        body_template="Session {session_id} cost has reached ${cost:.2f}.",
        priority="high",
        category="cost_alert",
    ),
    NotificationType.DISCONNECTED: NotificationTemplate(
        notification_type=NotificationType.DISCONNECTED,
        title_template="Session Disconnected",
        body_template="Your Lyra session {session_id} has been disconnected.",
        priority="normal",
        category="session_disconnected",
    ),
    NotificationType.SESSION_STARTED: NotificationTemplate(
        notification_type=NotificationType.SESSION_STARTED,
        title_template="Session Started",
        body_template="Lyra session {session_id} has started.",
        priority="normal",
    ),
    NotificationType.TOOL_COMPLETED: NotificationTemplate(
        notification_type=NotificationType.TOOL_COMPLETED,
        title_template="Tool Completed",
        body_template="Tool {tool_name} completed in session {session_id}.",
        priority="normal",
    ),
    NotificationType.MILESTONE: NotificationTemplate(
        notification_type=NotificationType.MILESTONE,
        title_template="Milestone Reached",
        body_template="{milestone_name} reached in session {session_id}.",
        priority="high",
        category="milestone",
    ),
    NotificationType.SYSTEM: NotificationTemplate(
        notification_type=NotificationType.SYSTEM,
        title_template="Lyra System",
        body_template="{message}",
        priority="high",
        category="system_alert",
    ),
}


# ---------------------------------------------------------------------------
# APNs payload builder
# ---------------------------------------------------------------------------


@dataclass
class APNsPayload:
    """Apple Push Notification service payload builder.

    Constructs the structured APNs JSON payload according to Apple's
    UserNotifications framework, including support for action buttons
    via the ``category`` field.

    Attributes:
        alert_title: Notification title.
        alert_body: Notification body text.
        category: Category identifier for custom actions.
        sound: Sound name (or ``"default"``).
        badge: Badge number (0 to clear).
        thread_id: Grouping identifier for notification threading.
        mutable_content: If True, enables notification service app extension.
        custom_data: Additional key-value pairs sent in the payload.
    """

    alert_title: str
    alert_body: str
    category: str = ""
    sound: str = "default"
    badge: int = 1
    thread_id: str = ""
    mutable_content: bool = False
    custom_data: dict[str, Any] = field(default_factory=dict)

    def build(self) -> dict[str, Any]:
        """Build the APNs JSON payload dict."""
        aps: dict[str, Any] = {
            "alert": {
                "title": self.alert_title,
                "body": self.alert_body,
            },
            "sound": self.sound,
            "badge": self.badge,
        }

        if self.category:
            aps["category"] = self.category
        if self.thread_id:
            aps["thread-id"] = self.thread_id
        if self.mutable_content:
            aps["mutable-content"] = 1

        payload: dict[str, Any] = {"aps": aps}
        payload.update(self.custom_data)
        return payload


# ---------------------------------------------------------------------------
# FCM payload builder
# ---------------------------------------------------------------------------


@dataclass
class FCMPayload:
    """Firebase Cloud Messaging payload builder.

    Constructs the FCM JSON payload for Android, including support for
    notification actions.

    Attributes:
        title: Notification title.
        body: Notification body.
        click_action: Intent action on notification tap.
        tag: Grouping tag for notification stacking.
        priority: ``"high"`` or ``"normal"``.
        color: Notification icon color (hex, e.g. ``"#6C63FF"``).
        ttl: Time-to-live in seconds.
        data: Additional data payload.
    """

    title: str
    body: str
    click_action: str = ""
    tag: str = ""
    priority: str = "high"
    color: str = "#6C63FF"
    ttl: int = 86400
    data: dict[str, Any] = field(default_factory=dict)

    def build(self) -> dict[str, Any]:
        """Build the FCM JSON payload dict."""
        notification: dict[str, Any] = {
            "title": self.title,
            "body": self.body,
            "color": self.color,
        }
        if self.click_action:
            notification["click_action"] = self.click_action
        if self.tag:
            notification["tag"] = self.tag

        payload: dict[str, Any] = {
            "to": "/topics/lyra",  # Overridden per-device in delivery
            "priority": self.priority,
            "time_to_live": self.ttl,
            "notification": notification,
            "data": {
                "lyra_type": "notification",
                **self.data,
            },
        }
        return payload


# ---------------------------------------------------------------------------
# Rich action buttons for notifications
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationAction:
    """An action button attached to a push notification.

    Attributes:
        identifier: Unique action identifier (e.g. ``"APPROVE"``, ``"DENY"``).
        title: Button text displayed to the user.
        destructive: If True, the button is rendered with a destructive style.
        foreground: If True, launching the action brings the app to the foreground.
        authentication_required: If True, the user must authenticate to perform this action.
    """

    identifier: str
    title: str
    destructive: bool = False
    foreground: bool = True
    authentication_required: bool = True


# Standard action buttons for approval notifications
_APPROVAL_ACTIONS = [
    NotificationAction(
        identifier="APPROVE",
        title="Approve",
        foreground=True,
        authentication_required=True,
    ),
    NotificationAction(
        identifier="DENY",
        title="Deny",
        destructive=True,
        foreground=True,
        authentication_required=True,
    ),
]

# Cost alert action
_COST_ALERT_ACTIONS = [
    NotificationAction(
        identifier="VIEW_SESSION",
        title="View Session",
        foreground=True,
    ),
    NotificationAction(
        identifier="PAUSE_SESSION",
        title="Pause Session",
        foreground=True,
        authentication_required=True,
    ),
]


# ---------------------------------------------------------------------------
# Rich notification builder
# ---------------------------------------------------------------------------


@dataclass
class RichNotification:
    """A rich push notification with platform-specific payloads and action buttons.

    Attributes:
        session_id: The source session.
        event: The triggering session event.
        template: The notification template used.
        variables: Template variables for rendering.
        actions: Action buttons to attach.
        apns_payload: Pre-built APNs payload (if targeting iOS).
        fcm_payload: Pre-built FCM payload (if targeting Android).
        created_at: Unix timestamp of creation.
    """

    session_id: str
    event: SessionEvent | NotificationType
    template: NotificationTemplate
    variables: dict[str, Any] = field(default_factory=dict)
    actions: list[NotificationAction] = field(default_factory=list)
    apns_payload: APNsPayload | None = None
    fcm_payload: FCMPayload | None = None
    created_at: float = field(default_factory=time.time)

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def for_approval_request(
        cls,
        session_id: str,
        tool_name: str = "Unknown",
        tool_call_id: str = "",
    ) -> "RichNotification":
        """Build a rich approval-request notification with action buttons."""
        template = _DEFAULT_TEMPLATES[NotificationType.APPROVAL_REQUEST]
        variables = {
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
        }

        title = template.render_title(**variables)
        body = template.render_body(**variables)

        return cls(
            session_id=session_id,
            event=SessionEvent.NEEDS_APPROVAL,
            template=template,
            variables=variables,
            actions=_APPROVAL_ACTIONS,
            apns_payload=APNsPayload(
                alert_title=title,
                alert_body=body,
                category="approval_request",
                thread_id=session_id,
                custom_data={
                    "lyra_session": session_id,
                    "lyra_event": "approval_request",
                    "lyra_tool_call_id": tool_call_id,
                    "lyra_tool_name": tool_name,
                },
            ),
            fcm_payload=FCMPayload(
                title=title,
                body=body,
                click_action="LYRA_APPROVAL",
                tag=session_id,
                data={
                    "lyra_action": "approval_request",
                    "lyra_session_id": session_id,
                    "lyra_tool_call_id": tool_call_id,
                    "lyra_tool_name": tool_name,
                    "lyra_actions": json.dumps([
                        {"identifier": "APPROVE", "title": "Approve"},
                        {"identifier": "DENY", "title": "Deny"},
                    ]),
                },
            ),
        )

    @classmethod
    def for_completion(
        cls,
        session_id: str,
        summary: str = "",
        duration_seconds: float = 0.0,
    ) -> "RichNotification":
        """Build a session-completion notification."""
        template = _DEFAULT_TEMPLATES[NotificationType.COMPLETION]
        variables = {
            "session_id": session_id,
            "summary": summary,
        }

        title = template.render_title(**variables)
        body = template.render_body(**variables)

        return cls(
            session_id=session_id,
            event=SessionEvent.COMPLETION,
            template=template,
            variables=variables,
            apns_payload=APNsPayload(
                alert_title=title,
                alert_body=body,
                badge=0,
                thread_id=session_id,
                custom_data={
                    "lyra_session": session_id,
                    "lyra_event": "completion",
                    "lyra_duration": duration_seconds,
                },
            ),
            fcm_payload=FCMPayload(
                title=title,
                body=body,
                tag=session_id,
                priority="normal",
                data={
                    "lyra_action": "completion",
                    "lyra_session_id": session_id,
                    "lyra_duration": str(duration_seconds),
                },
            ),
        )

    @classmethod
    def for_error(
        cls,
        session_id: str,
        error_message: str = "",
    ) -> "RichNotification":
        """Build an error notification."""
        template = _DEFAULT_TEMPLATES[NotificationType.ERROR]
        variables = {
            "session_id": session_id,
            "error_message": error_message,
        }

        title = template.render_title(**variables)
        body = template.render_body(**variables)

        return cls(
            session_id=session_id,
            event=SessionEvent.ERROR,
            template=template,
            variables=variables,
            apns_payload=APNsPayload(
                alert_title=title,
                alert_body=body,
                category="session_error",
                sound="alert",
                thread_id=session_id,
                custom_data={
                    "lyra_session": session_id,
                    "lyra_event": "error",
                    "lyra_error": error_message,
                },
            ),
            fcm_payload=FCMPayload(
                title=title,
                body=body,
                click_action="LYRA_ERROR",
                tag=session_id,
                data={
                    "lyra_action": "error",
                    "lyra_session_id": session_id,
                    "lyra_error": error_message,
                },
            ),
        )

    @classmethod
    def for_cost_alert(
        cls,
        session_id: str,
        cost: float = 0.0,
        threshold: float = 0.0,
    ) -> "RichNotification":
        """Build a cost-alert notification with action buttons."""
        template = _DEFAULT_TEMPLATES[NotificationType.COST_ALERT]
        variables = {
            "session_id": session_id,
            "cost": cost,
        }

        title = template.render_title(**variables)
        body = template.render_body(**variables)

        return cls(
            session_id=session_id,
            event=SessionEvent.COST_ALERT,
            template=template,
            variables=variables,
            actions=_COST_ALERT_ACTIONS,
            apns_payload=APNsPayload(
                alert_title=title,
                alert_body=body,
                category="cost_alert",
                sound="alert",
                thread_id=session_id,
                custom_data={
                    "lyra_session": session_id,
                    "lyra_event": "cost_alert",
                    "lyra_cost": cost,
                    "lyra_threshold": threshold,
                },
            ),
            fcm_payload=FCMPayload(
                title=title,
                body=body,
                click_action="LYRA_COST_ALERT",
                tag=session_id,
                data={
                    "lyra_action": "cost_alert",
                    "lyra_session_id": session_id,
                    "lyra_cost": str(cost),
                    "lyra_threshold": str(threshold),
                    "lyra_actions": json.dumps([
                        {"identifier": "VIEW_SESSION", "title": "View Session"},
                        {"identifier": "PAUSE_SESSION", "title": "Pause"},
                    ]),
                },
            ),
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_push_notification(self) -> PushNotification:
        """Convert to a :class:`PushNotification` for relay delivery."""
        return PushNotification(
            title=self.apns_payload.alert_title if self.apns_payload else "",
            body=self.apns_payload.alert_body if self.apns_payload else "",
            event=SessionEvent(self.event.value) if isinstance(self.event, NotificationType)
            else self.event,
            session_id=self.session_id,
            data={
                **self.variables,
                "actions": [
                    {"identifier": a.identifier, "title": a.title}
                    for a in self.actions
                ],
                "apns": self.apns_payload.build() if self.apns_payload else None,
                "fcm": self.fcm_payload.build() if self.fcm_payload else None,
            },
        )


# ---------------------------------------------------------------------------
# Notification manager
# ---------------------------------------------------------------------------


class NotificationManager:
    """Manages push notification templates, delivery, and formatting.

    Provides a registry of notification templates that can be customised
    at runtime and a delivery interface that produces platform-specific
    payloads (APNs, FCM).

    Use :class:`MobileSteeringSurface` for high-level notification sending.
    This class is the lower-level template and delivery engine.
    """

    def __init__(self) -> None:
        self._templates: dict[NotificationType, NotificationTemplate] = {
            **{k: v for k, v in _DEFAULT_TEMPLATES.items()},
        }

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    def register_template(self, template: NotificationTemplate) -> None:
        """Register or override a notification template.

        Args:
            template: The template to register.  Its ``notification_type``
                is used as the key.
        """
        ntype = (
            template.notification_type
            if isinstance(template.notification_type, NotificationType)
            else NotificationType(template.notification_type)
        )
        self._templates[ntype] = template
        logger.info("notification template registered", notification_type=ntype.value)

    def get_template(self, notification_type: NotificationType) -> NotificationTemplate | None:
        """Get a registered template by type.

        Falls back to the default if not found.
        """
        return self._templates.get(notification_type)

    def list_templates(self) -> list[dict[str, Any]]:
        """List all registered templates (metadata only)."""
        return [
            {
                "notification_type": t.notification_type.value,
                "title_template": t.title_template,
                "priority": t.priority,
                "category": t.category,
            }
            for t in self._templates.values()
        ]

    # ------------------------------------------------------------------
    # Delivery simulation
    # ------------------------------------------------------------------

    def send_apns(self, payload: APNsPayload, device_token: str) -> dict[str, Any]:
        """Send (simulate) an APNs notification.

        In production, this would use ``httpx`` to POST to Apple's APNs
        server.  Here we log and return a success response.

        Args:
            payload: The APNs payload to deliver.
            device_token: The target device token.

        Returns:
            A result dict with ``success`` status and ``apns_id``.
        """
        payload_dict = payload.build()
        logger.info(
            "APNs notification",
            device_token=device_token[:8] + "...",
            title=payload_dict.get("aps", {}).get("alert", {}).get("title"),
        )
        return {
            "success": True,
            "service": "apns",
            "apns_id": f"apns-{int(time.time())}-{device_token[:8]}",
        }

    def send_fcm(self, payload: FCMPayload, device_token: str) -> dict[str, Any]:
        """Send (simulate) an FCM notification.

        In production, this would use ``httpx`` to POST to the FCM HTTP
        v1 API.  Here we log and return a success response.

        Args:
            payload: The FCM payload to deliver.
            device_token: The target device token.

        Returns:
            A result dict with ``success`` status and ``message_id``.
        """
        payload_dict = payload.build()
        logger.info(
            "FCM notification",
            device_token=device_token[:8] + "...",
            title=payload_dict.get("notification", {}).get("title"),
        )
        return {
            "success": True,
            "service": "fcm",
            "message_id": f"fcm-{int(time.time())}-{device_token[:8]}",
        }


# ---------------------------------------------------------------------------
# Extended subscription
# ---------------------------------------------------------------------------


@dataclass
class SteeringSubscription:
    """An active subscription to a session's real-time events.

    Attributes:
        subscription_id: Unique identifier for the subscription.
        session_id: The subscribed session.
        event: The event type being monitored.
        callback: User-provided handler ``(session_id, payload)``.
        created_at: Unix timestamp of subscription creation.
    """

    subscription_id: str
    session_id: str
    event: SessionEvent
    callback: Callable[[str, dict[str, Any]], Any]
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# MobileSteeringSurface (enhanced)
# ---------------------------------------------------------------------------


class MobileSteeringSurface:
    """High-level mobile steering API for remote Lyra sessions.

    Parameters
    ----------
    relay_url : str
        WebSocket URL of the relay server.
    device_id : str
        Unique device identifier.
    notification_token : str, optional
        Push notification token (FCM / APNS).
    auto_connect : bool
        If ``True`` (default), connect immediately on init.
    """

    def __init__(
        self,
        relay_url: str,
        device_id: str,
        notification_token: str = "",
        auto_connect: bool = True,
    ) -> None:
        self._config = RelayConfig(
            relay_url=relay_url,
            device_id=device_id,
            notification_token=notification_token,
        )
        self._relay = ZeroTrustRelay(self._config)
        self._connected = False
        self._subscriptions: dict[str, SteeringSubscription] = {}
        self._sub_counter = 0

        # Push notification components
        self.notification_manager = NotificationManager()
        self._notification_token = notification_token

        if auto_connect:
            self._connect_task: asyncio.Task[Any] | None = \
                asyncio.create_task(self._connect_async())

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def _connect_async(self) -> None:
        """Internal async connection handler."""
        try:
            await self._relay.connect()
            self._connected = True
            logger.info("mobile steering connected", device=self._config.device_id)
        except ConnectionError:
            logger.exception("mobile steering connection failed")
            self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure the relay connection is established.

        If the connection was started lazily via ``auto_connect=True``,
        this waits for it to complete.  If not connected, connects immediately.
        """
        if self._connected:
            return
        await self._relay.connect()
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from the relay."""
        await self._relay.disconnect()
        self._connected = False

    # ------------------------------------------------------------------
    # Session summary
    # ------------------------------------------------------------------

    async def status(self, session_id: str) -> SessionSummary:
        """Return an at-a-glance snapshot of *session_id*.

        The summary is built from the last known state of the session
        relayed through the encrypted channel.  Returns a best-effort
        snapshot even if the session is temporarily unreachable.

        Parameters
        ----------
        session_id : str
            The session to query.

        Returns
        -------
        SessionSummary
        """
        await self.ensure_connected()

        # Request a status snapshot via encrypted message
        status_future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()

        def handle_status(sid: str, payload: dict[str, Any]) -> None:
            if sid == session_id and not status_future.done():
                status_future.set_result(payload)

        self._relay.on_any_message(handle_status)
        await self._relay.send_encrypted(session_id, {"type": "status_request"})

        try:
            result = await asyncio.wait_for(status_future, timeout=10.0)
        except asyncio.TimeoutError:
            # Return a best-effort offline summary
            return SessionSummary(
                session_id=session_id,
                agent_online=False,
            )

        return SessionSummary(
            session_id=session_id,
            agent_online=result.get("agent_online", False),
            pending_approvals=result.get("pending_approvals", 0),
            last_message=result.get("last_message", ""),
            running_tool=result.get("running_tool", ""),
            total_cost=result.get("total_cost", 0.0),
            elapsed_seconds=result.get("elapsed_seconds", 0.0),
        )

    # ------------------------------------------------------------------
    # Tool call approval
    # ------------------------------------------------------------------

    async def approve(
        self,
        session_id: str,
        tool_call_id: str,
        reason: str = "",
    ) -> None:
        """Approve a pending tool call from a mobile device.

        Sends a signed command through the relay.  The local Lyra process
        receives the approval and proceeds with the tool execution.

        Parameters
        ----------
        session_id : str
            The session containing the pending tool call.
        tool_call_id : str
            The tool call identifier to approve.
        reason : str, optional
            Optional reason for approval.
        """
        await self.ensure_connected()

        cmd = SignedCommand(
            action=MobileAction.APPROVE,
            payload={
                "tool_call_id": tool_call_id,
                "reason": reason,
                "source": "mobile",
            },
            session_id=session_id,
        )
        await self._relay.mobile_steer(cmd)
        logger.info(
            "tool call approved from mobile",
            session_id=session_id,
            tool_call_id=tool_call_id,
        )

    async def deny(
        self,
        session_id: str,
        tool_call_id: str,
        reason: str = "",
    ) -> None:
        """Deny a pending tool call from a mobile device.

        Parameters
        ----------
        session_id : str
            The session containing the pending tool call.
        tool_call_id : str
            The tool call identifier to deny.
        reason : str, optional
            Optional reason for denial.
        """
        await self.ensure_connected()

        cmd = SignedCommand(
            action=MobileAction.DENY,
            payload={
                "tool_call_id": tool_call_id,
                "reason": reason,
                "source": "mobile",
            },
            session_id=session_id,
        )
        await self._relay.mobile_steer(cmd)
        logger.info(
            "tool call denied from mobile",
            session_id=session_id,
            tool_call_id=tool_call_id,
        )

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def message(
        self,
        session_id: str,
        text: str,
    ) -> None:
        """Send a text message to the agent in *session_id*.

        The message is encrypted end-to-end and forwarded to the local
        Lyra process, where it appears as a user message in the
        conversation.

        Parameters
        ----------
        session_id : str
            The target session.
        text : str
            The message text to send.
        """
        await self.ensure_connected()

        cmd = SignedCommand(
            action=MobileAction.MESSAGE,
            payload={
                "text": text,
                "source": "mobile",
            },
            session_id=session_id,
        )
        await self._relay.mobile_steer(cmd)
        logger.info(
            "message sent from mobile",
            session_id=session_id,
            text_snippet=text[:50],
        )

    # ------------------------------------------------------------------
    # Session peek
    # ------------------------------------------------------------------

    async def peek(self, session_id: str) -> dict[str, Any]:
        """Peek at the current session state without modifying anything.

        Returns a snapshot of the conversation context, running tool,
        and recent messages.  This is a read-only operation.

        Parameters
        ----------
        session_id : str
            The session to peek at.

        Returns
        -------
        dict
            Session state snapshot (conversation context, active tool, etc.).
        """
        await self.ensure_connected()

        peek_future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()

        def handle_peek(sid: str, payload: dict[str, Any]) -> None:
            if sid == session_id and not peek_future.done():
                peek_future.set_result(payload)

        self._relay.on_any_message(handle_peek)
        await self._relay.send_encrypted(session_id, {"type": "peek_request"})

        try:
            return await asyncio.wait_for(peek_future, timeout=10.0)
        except asyncio.TimeoutError:
            return {"session_id": session_id, "error": "timeout"}

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        session_id: str,
        event: SessionEvent,
        callback: Callable[[str, dict[str, Any]], Any],
    ) -> str:
        """Subscribe to real-time events for *session_id*.

        When *event* fires, *callback* is called with ``(session_id, payload)``.
        Returns a subscription ID that can be passed to :meth:`unsubscribe`.

        Parameters
        ----------
        session_id : str
            The session to monitor.
        event : SessionEvent
            The event type to subscribe to.
        callback : Callable[[str, dict], Any]
            Handler, sync or async.

        Returns
        -------
        str
            Subscription identifier.
        """
        await self.ensure_connected()

        self._sub_counter += 1
        sub_id = f"sub-{self._sub_counter}-{session_id}"

        sub = SteeringSubscription(
            subscription_id=sub_id,
            session_id=session_id,
            event=event,
            callback=callback,
        )
        self._subscriptions[sub_id] = sub

        # Wire the callback through the relay's event handler system
        @self._relay.on_event(event)
        async def _relay_handler(sid: str, payload: dict[str, Any]) -> None:
            if sid == session_id:
                await self._safe_call(callback, sid, payload)

        logger.info(
            "subscription added",
            subscription_id=sub_id,
            session_id=session_id,
            session_event=event.value,
        )
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove a previously created subscription.

        Parameters
        ----------
        subscription_id : str
            The ID returned by :meth:`subscribe`.
        """
        self._subscriptions.pop(subscription_id, None)
        logger.info("subscription removed", subscription_id=subscription_id)

    def list_subscriptions(self) -> list[dict[str, Any]]:
        """List all active subscriptions."""
        return [
            {
                "subscription_id": s.subscription_id,
                "session_id": s.session_id,
                "event": s.event.value,
            }
            for s in self._subscriptions.values()
        ]

    # ------------------------------------------------------------------
    # Push notifications
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        session_id: str,
        event: SessionEvent,
        **overrides: Any,
    ) -> None:
        """Send a push notification for a session event.

        Uses the notification token configured at init time.
        If the notification token is set, attempts platform-specific delivery
        (APNs for iOS, FCM for Android) in addition to relay forwarding.

        Parameters
        ----------
        session_id : str
            The source session.
        event : SessionEvent
            The event type (determines the notification template).
        **overrides
            Override ``title``, ``body``, or additional ``data`` keys.
        """
        await self.ensure_connected()

        notification = build_notification(event, session_id, **overrides)
        await self._relay.send_push_notification(notification)

        # Platform-specific delivery if we have a token
        if self._notification_token:
            self._deliver_platform_notification(event, session_id, **overrides)

        logger.info(
            "push notification sent",
            session_id=session_id,
            session_event=event.value,
        )

    async def send_rich_notification(self, notification: RichNotification) -> None:
        """Send a rich notification with platform-specific payloads.

        Delivers both APNs and FCM payloads based on the notification
        configuration.  The notification is also forwarded through the
        relay.

        Parameters
        ----------
        notification : RichNotification
            The rich notification to deliver.
        """
        await self.ensure_connected()

        # Forward through relay
        push_notif = notification.to_push_notification()
        await self._relay.send_push_notification(push_notif)

        # Platform-specific delivery
        if self._notification_token:
            token_lower = self._notification_token.lower()

            # Heuristic: APNs tokens are hex strings; FCM tokens contain
            # alphanumeric with special chars like colons or underscores.
            if self._is_apns_token(token_lower):
                if notification.apns_payload:
                    self.notification_manager.send_apns(
                        notification.apns_payload,
                        self._notification_token,
                    )
            else:
                if notification.fcm_payload:
                    self.notification_manager.send_fcm(
                        notification.fcm_payload,
                        self._notification_token,
                    )

        logger.info(
            "rich notification sent",
            session_id=notification.session_id,
            event=notification.event.value,
            action_count=len(notification.actions),
        )

    # ------------------------------------------------------------------
    # Notification template management
    # ------------------------------------------------------------------

    def register_notification_template(self, template: NotificationTemplate) -> None:
        """Register a custom notification template.

        Parameters
        ----------
        template : NotificationTemplate
            The template to register.
        """
        self.notification_manager.register_template(template)

    def list_notification_templates(self) -> list[dict[str, Any]]:
        """List all registered notification templates."""
        return self.notification_manager.list_templates()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    async def _safe_call(func: Callable[..., Any], *args: Any) -> Any:
        """Invoke *func* with *args*, supporting sync and async callables."""
        result = func(*args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    @staticmethod
    def _is_apns_token(token: str) -> bool:
        """Heuristic: APNs device tokens are hex strings (no separators)."""
        return all(c in "0123456789abcdef" for c in token)

    def _deliver_platform_notification(
        self,
        event: SessionEvent,
        session_id: str,
        **overrides: Any,
    ) -> None:
        """Deliver a platform-specific notification based on the event."""
        event_map: dict[SessionEvent, NotificationType] = {
            SessionEvent.COMPLETION: NotificationType.COMPLETION,
            SessionEvent.ERROR: NotificationType.ERROR,
            SessionEvent.NEEDS_APPROVAL: NotificationType.APPROVAL_REQUEST,
            SessionEvent.COST_ALERT: NotificationType.COST_ALERT,
            SessionEvent.DISCONNECTED: NotificationType.DISCONNECTED,
        }

        ntype = event_map.get(event)
        if ntype is None:
            return

        template = self.notification_manager.get_template(ntype)
        if template is None:
            return

        variables = {
            "session_id": session_id,
            **overrides,
        }

        title = template.render_title(**variables)
        body = template.render_body(**variables)

        if self._is_apns_token(self._notification_token):
            payload = APNsPayload(
                alert_title=title,
                alert_body=body,
                category=template.category,
                thread_id=session_id,
            )
            self.notification_manager.send_apns(payload, self._notification_token)
        else:
            payload = FCMPayload(
                title=title,
                body=body,
                tag=session_id,
            )
            self.notification_manager.send_fcm(payload, self._notification_token)
