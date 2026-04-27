"""Langfuse tracing observer.

Langfuse is the open-source alternative most self-hosted shops
prefer; it has the same ``trace -> span`` shape as LangSmith but a
slightly different SDK surface (one ``trace`` per top-level
operation, ``generation`` spans inside).

Like :mod:`.langsmith_cb` this adapter is soft-dependent: missing
``langfuse`` package or env vars => no-op (`enabled=False`). The
hub catches exceptions, but we still log at debug level so a
misconfigured key surfaces in ``LYRA_LOG=DEBUG`` runs.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from .base import TurnTrace

logger = logging.getLogger(__name__)


class LangfuseCallback:
    """Forward Lyra turn lifecycle events to Langfuse.

    Args:
        public_key: Langfuse public key. ``None`` falls back to
            ``$LANGFUSE_PUBLIC_KEY``.
        secret_key: Langfuse secret key. ``None`` falls back to
            ``$LANGFUSE_SECRET_KEY``.
        host: Langfuse host URL. ``None`` falls back to
            ``$LANGFUSE_HOST`` and finally Langfuse's default
            cloud endpoint.
        client: Pre-built ``langfuse.Langfuse`` instance for tests.
            Production code leaves it ``None``.

    Attributes:
        enabled: ``False`` when the SDK isn't importable or no
            credentials are present.
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
        *,
        client: Any = None,
    ) -> None:
        self._public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
        self._secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
        self._host = host or os.environ.get("LANGFUSE_HOST")
        self._explicit_client = client
        self._client: Any = client
        # Each open turn keeps its trace handle here so ``end`` can
        # close it. We stash the *handle* rather than the trace_id
        # because Langfuse's SDK works through stateful objects.
        self._open: dict[str, Any] = {}
        self.enabled: bool = self._resolve_client() is not None

    # ---------------- protocol methods ---------------- #

    def on_turn_start(self, trace: TurnTrace) -> None:
        """Open a Langfuse trace + generation span for the turn."""
        client = self._resolve_client()
        if client is None:
            return
        try:
            handle = client.trace(
                name=f"lyra:{trace.model}",
                id=trace.trace_id,
                session_id=trace.session_id,
                input={"prompt": trace.prompt, "system_prompt": trace.system_prompt},
                metadata=dict(trace.metadata or {}),
            )
        except Exception:  # noqa: BLE001
            logger.debug("langfuse trace() failed", exc_info=True)
            return
        if handle is not None:
            self._open[trace.trace_id] = handle

    def on_turn_end(self, trace: TurnTrace) -> None:
        """Update the trace with the assistant reply and finalise it."""
        client = self._resolve_client()
        if client is None:
            return
        handle = self._open.pop(trace.trace_id, None)
        if handle is None:
            return
        try:
            handle.update(
                output={"text": trace.text, "usage": dict(trace.usage or {})},
                level="ERROR" if trace.error else "DEFAULT",
                status_message=trace.error,
                end_time=trace.ended_at,
            )
        except Exception:  # noqa: BLE001
            logger.debug("langfuse trace.update() failed", exc_info=True)
        # Best-effort flush so embedded scripts that exit immediately
        # after a turn don't lose the event.
        flush = getattr(client, "flush", None)
        if callable(flush):
            try:
                flush()
            except Exception:  # noqa: BLE001
                logger.debug("langfuse flush() failed", exc_info=True)

    # ---------------- internals ---------------- #

    def _resolve_client(self) -> Any:
        """Lazy-build the Langfuse SDK client; cached after first success."""
        if self._client is not None:
            return self._client
        if not self._public_key or not self._secret_key:
            return None
        try:
            from langfuse import Langfuse  # type: ignore
        except ImportError:
            return None
        try:
            kwargs: dict[str, Any] = {
                "public_key": self._public_key,
                "secret_key": self._secret_key,
            }
            if self._host:
                kwargs["host"] = self._host
            self._client = Langfuse(**kwargs)
        except Exception:  # noqa: BLE001
            logger.debug("langfuse Langfuse() init failed", exc_info=True)
            return None
        return self._client


__all__ = ["LangfuseCallback"]
