"""LangSmith tracing observer.

LangSmith is the tracing/eval backend most teams using LangChain
already have set up; routing Lyra turns there gives them a single
pane of glass without standing up another platform. The wire format
is "create a run, update it on completion" via the public
``langsmith.Client`` SDK.

This adapter is *soft-dependent*: when ``langsmith`` isn't
installed (or ``LANGSMITH_API_KEY`` isn't set) the callback no-ops
instead of raising. Embedded users who never opt in pay zero cost.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from .base import TurnTrace

logger = logging.getLogger(__name__)


class LangSmithCallback:
    """Forward Lyra turn lifecycle events to LangSmith.

    Args:
        project: LangSmith project / dataset name. ``None`` falls
            back to ``$LANGSMITH_PROJECT`` and finally ``"lyra"``.
        api_key: Override for ``$LANGSMITH_API_KEY``. Pass ``None``
            to read the env var (the typical case).
        client: Pre-built ``langsmith.Client`` instance. Tests pass
            a mock here; production code leaves it ``None`` so the
            callback constructs one lazily on the first turn.

    Attributes:
        enabled: ``False`` when the SDK isn't importable / no key is
            present. Read by tests asserting the callback degraded
            cleanly.
    """

    def __init__(
        self,
        project: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        client: Any = None,
    ) -> None:
        self.project = project or os.environ.get("LANGSMITH_PROJECT") or "lyra"
        self._explicit_client = client
        self._api_key = api_key or os.environ.get("LANGSMITH_API_KEY")
        self._client: Any = client
        self._run_ids: dict[str, str] = {}
        # Resolve eagerly so users can read ``enabled`` to check setup.
        self.enabled: bool = self._resolve_client() is not None

    # ---------------- protocol methods ---------------- #

    def on_turn_start(self, trace: TurnTrace) -> None:
        """Open a LangSmith run for *trace*; cache its id by ``trace_id``.

        Errors are logged at debug level — see :meth:`TracingHub._safe_call`
        — so a flaky control plane never breaks the chat loop.
        """
        client = self._resolve_client()
        if client is None:
            return
        try:
            run = client.create_run(
                name=f"lyra:{trace.model}",
                run_type="llm",
                inputs={
                    "prompt": trace.prompt,
                    "system_prompt": trace.system_prompt,
                    "session_id": trace.session_id,
                    "metadata": dict(trace.metadata or {}),
                },
                project_name=self.project,
                extra={"lyra_trace_id": trace.trace_id},
            )
        except Exception:  # noqa: BLE001 — observer is fail-soft
            logger.debug("langsmith create_run failed", exc_info=True)
            return
        run_id = self._extract_run_id(run)
        if run_id:
            self._run_ids[trace.trace_id] = run_id

    def on_turn_end(self, trace: TurnTrace) -> None:
        """Patch the open run with the assistant reply / error."""
        client = self._resolve_client()
        if client is None:
            return
        run_id = self._run_ids.pop(trace.trace_id, None)
        if not run_id:
            return
        try:
            client.update_run(
                run_id,
                outputs={"text": trace.text, "usage": dict(trace.usage or {})},
                error=trace.error,
                end_time=trace.ended_at,
            )
        except Exception:  # noqa: BLE001
            logger.debug("langsmith update_run failed", exc_info=True)

    # ---------------- internals ---------------- #

    def _resolve_client(self) -> Any:
        """Lazy-build the LangSmith ``Client``. Cached after first call.

        Returning ``None`` means "this turn is not traced"; callers
        treat the result as opaque and just gate calls on it.
        """
        if self._client is not None:
            return self._client
        if not self._api_key:
            return None
        try:
            from langsmith import Client  # type: ignore
        except ImportError:
            return None
        try:
            self._client = Client(api_key=self._api_key)
        except Exception:  # noqa: BLE001
            logger.debug("langsmith Client init failed", exc_info=True)
            return None
        return self._client

    @staticmethod
    def _extract_run_id(run: Any) -> Optional[str]:
        """Pull the run id off whatever shape ``create_run`` returned.

        Older SDKs return a dataclass with ``.id``; newer ones return
        a dict. Production tests pin one shape, but real users hit
        both — peek at the common attributes/keys and fall back to
        ``str(run)`` so the trace is at least correlatable in logs.
        """
        if run is None:
            return None
        rid = getattr(run, "id", None)
        if rid is not None:
            return str(rid)
        if isinstance(run, dict):
            rid = run.get("id") or run.get("run_id")
            if rid is not None:
                return str(rid)
        return None


__all__ = ["LangSmithCallback"]
