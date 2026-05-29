"""
AG-UI Protocol encoder / decoder.

Provides serialization (encode) and deserialization (decode) for all 16
AG-UI event types, plus lightweight validation and event-type peeking.
"""

from __future__ import annotations

import json
import logging

from lyra_streaming.models import (
    _EVENT_CLASS_BY_TYPE,
    AGEvent,
    EventType,
)

logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    """Raised when encoding or decoding fails at the protocol level."""


class ValidationError(Exception):
    """Raised when an event fails structural validation."""


class AGUIProtocol:
    """Bidirectional serializer / deserializer for the AG-UI event protocol.

    Usage::

        proto = AGUIProtocol()
        raw = proto.encode(my_event)       # AGEvent -> bytes
        event = proto.decode(raw)          # bytes -> AGEvent
        proto.validate(event)              # raises ValidationError or returns True
    """

    # Default content type sent over the wire.
    CONTENT_TYPE = "application/x-agui+json"

    @staticmethod
    def encode(event: AGEvent) -> bytes:
        """Serialize an `AGEvent` to JSON bytes for transport.

        Args:
            event: Any concrete subclass of `AGEvent`.

        Returns:
            UTF-8 encoded JSON bytes ready to send over a WebSocket or
            HTTP stream.

        Raises:
            ProtocolError: If serialization fails.
        """
        try:
            payload = event.to_dict()
            return json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        except Exception as exc:
            logger.error(
                "Failed to encode event type=%s run_id=%s: %s", event.type.name, event.run_id, exc
            )
            raise ProtocolError(f"Encode failed for event type {event.type.name}: {exc}") from exc

    @staticmethod
    def decode(raw: bytes) -> AGEvent:
        """Deserialize raw bytes back into a concrete `AGEvent` subclass.

        Args:
            raw: JSON bytes received over the transport.

        Returns:
            The appropriate `AGEvent` subclass instance.

        Raises:
            ProtocolError: If the raw data is not valid JSON or the
                ``type`` field is missing / unknown.
        """
        try:
            data = json.loads(raw if isinstance(raw, (str, bytes)) else raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("Failed to parse AG-UI event JSON: %s", exc)
            raise ProtocolError(f"Invalid JSON in event payload: {exc}") from exc

        if not isinstance(data, dict):
            raise ProtocolError("Event payload must be a JSON object")

        event_type_name = data.get("type")
        if not event_type_name:
            raise ProtocolError("Event payload missing required 'type' field")

        try:
            event_type = EventType[event_type_name]
        except KeyError:
            raise ProtocolError(f"Unknown event type: {event_type_name!r}") from None

        event_class = _EVENT_CLASS_BY_TYPE.get(event_type)
        if event_class is None:
            raise ProtocolError(f"No handler registered for event type: {event_type.name}")

        try:
            return event_class.from_dict(data)
        except Exception as exc:
            logger.error("Failed to construct event type=%s: %s", event_type.name, exc)
            raise ProtocolError(f"Failed to decode {event_type.name}: {exc}") from exc

    @staticmethod
    def validate(event: AGEvent) -> bool:
        """Validate the structure of an event.

        Checks that all required fields are present and have appropriate
        types.  Returns ``True`` on success or raises `ValidationError`.

        Args:
            event: An `AGEvent` instance to validate.

        Returns:
            ``True`` if the event passes validation.

        Raises:
            ValidationError: With a descriptive message explaining why
                validation failed.
        """
        if event.type is None:
            raise ValidationError("Event 'type' field is required")

        if not isinstance(event.type, EventType):
            raise ValidationError(f"Expected EventType, got {type(event.type).__name__}")

        if not event.run_id or not isinstance(event.run_id, str):
            raise ValidationError("Event 'run_id' must be a non-empty string")

        if event.sequence_number < 0:
            raise ValidationError(f"Invalid sequence_number: {event.sequence_number}")

        # Per-type validation
        event_type = event.type

        if event_type == EventType.RUN_ERROR:
            if not event.error_message:  # type: ignore[attr-defined]
                raise ValidationError("RUN_ERROR event requires 'error_message'")

        if event_type == EventType.TEXT_MESSAGE_CONTENT:
            if not event.message_id:  # type: ignore[attr-defined]
                raise ValidationError("TEXT_MESSAGE_CONTENT event requires 'message_id'")

        if event_type == EventType.STATE_DELTA:
            ops = event.operations  # type: ignore[attr-defined]
            if not isinstance(ops, list):
                raise ValidationError("STATE_DELTA 'operations' must be a list")

        return True

    @staticmethod
    def get_event_type(raw: bytes) -> EventType:
        """Peek at the event type without fully decoding the payload.

        Useful for routing / filtering decisions before committing to
        full deserialization.

        Args:
            raw: JSON bytes received over the transport.

        Returns:
            The `EventType` encoded in the payload.

        Raises:
            ProtocolError: If the data cannot be parsed or the ``type``
                field is missing / unknown.
        """
        try:
            data = json.loads(raw if isinstance(raw, (str, bytes)) else raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProtocolError(f"Invalid JSON when peeking event type: {exc}") from exc

        if not isinstance(data, dict):
            raise ProtocolError("Payload must be a JSON object")

        event_type_name = data.get("type")
        if not event_type_name:
            raise ProtocolError("Payload missing 'type' field")

        try:
            return EventType[event_type_name]
        except KeyError:
            raise ProtocolError(f"Unknown event type: {event_type_name!r}") from None

    @classmethod
    def encode_string(cls, event: AGEvent) -> str:
        """Encode an event to a JSON string (instead of bytes)."""
        raw = cls.encode(event)
        return raw.decode("utf-8")
