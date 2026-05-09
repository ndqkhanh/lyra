"""Embedded :class:`LyraClient` — Python-native entry point to Lyra.

The CLI's chat handler runs inside a Typer Click app and a
``rich`` console; that's the wrong shape when a notebook or eval
script wants to drive Lyra programmatically. This module exposes
the *same* primitives (provider routing, alias resolution, session
JSONL persistence, skill / model / session listing) behind a small,
pure-Python facade so embedders don't have to spawn ``lyra chat``
per turn.

Design constraints (Phase N):

* **No global state.** Multiple :class:`LyraClient` instances must
  coexist (e.g. one per repo in a monorepo eval harness).
* **Lazy session creation.** Callers passing ``session_id=None``
  get a fresh session id minted on the first turn — symmetrical
  with the REPL, which only writes ``turns.jsonl`` once it has a
  message to record.
* **Fail-soft.** Provider exceptions land in
  :attr:`ChatResponse.error` instead of propagating, so an embedded
  loop survives a single bad turn.
* **Provider injection seam.** Tests and N.5 (sandbox provider)
  pass a ``provider_factory`` callable that returns a stand-in
  ``LLMProvider``; production code falls through to
  :func:`lyra_cli.llm_factory.build_llm`.

The HTTP layer added in N.6 (``lyra serve``) will wrap an instance
of this class — no copy-paste of the chat path.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional

from lyra_core.paths import RepoLayout
from lyra_core.providers.aliases import DEFAULT_ALIASES, resolve_alias

from ..tracing import TracingHub
from .types import ChatRequest, ChatResponse, StreamEvent


# A provider factory returns an object exposing ``generate(messages)`` —
# mirroring :class:`harness_core.models.LLMProvider`. We accept a
# callable rather than a fixed class so tests can inject ``MockLLM``
# directly without faking out :func:`build_llm`'s env-var cascade.
ProviderFactory = Callable[[Optional[str]], Any]


def _new_session_id() -> str:
    """Mint a session id of the form ``YYYYMMDDTHHMMSS-<6 hex>``.

    Same shape as the REPL's :func:`_default_session_id` (timestamp
    prefix means lexicographic sort = chronological sort). The hex
    suffix avoids collisions when two clients spawn within the
    same second.
    """
    return time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]


class LyraClient:
    """In-process client for Lyra's chat pipeline.

    Construct once per repo, reuse across turns. ``close()`` is a
    no-op today but reserved so future provider pools (HTTP keep-alive
    connections, sandbox containers) can release resources without
    breaking the API.

    Args:
        repo_root: The repo whose ``.lyra/`` directory holds sessions
            and skills. Defaults to the current working directory.
        model: Default model slug or alias used when a
            :class:`ChatRequest` doesn't specify one. ``None`` means
            "let the provider cascade pick one".
        provider_factory: Optional callable ``slug -> provider``. Tests
            and N.5 use this to bypass :func:`build_llm`. ``None`` means
            "use the production factory".
        tracing: Optional :class:`TracingHub` to fan turn events out
            to LangSmith / Langfuse / custom observers. ``None`` is
            equivalent to a hub with zero callbacks (the default).
    """

    def __init__(
        self,
        repo_root: Path | str | None = None,
        *,
        model: str | None = None,
        provider_factory: ProviderFactory | None = None,
        tracing: TracingHub | None = None,
    ) -> None:
        self.repo_root = Path(repo_root or Path.cwd()).resolve()
        self.layout = RepoLayout(self.repo_root)
        # Make the sessions dir eagerly so list_sessions on a fresh
        # repo doesn't trip on a missing directory; ensure() is
        # idempotent.
        self.layout.ensure()
        self._default_model = model
        self._provider_factory = provider_factory
        self.tracing: TracingHub = tracing or TracingHub()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, request: ChatRequest | str) -> ChatResponse:
        """Send a single turn and return the assistant reply.

        Accepts either a :class:`ChatRequest` or a raw prompt string
        (sugar for ``ChatRequest(prompt=...)``). Always returns a
        :class:`ChatResponse` — even on provider failure ``error`` is
        set instead of an exception bubbling up.
        """
        req = self._normalize(request)
        sid = req.session_id or _new_session_id()
        provider, slug = self._resolve_provider(req.model)

        trace = self.tracing.start_turn(
            session_id=sid,
            model=slug,
            prompt=req.prompt,
            system_prompt=req.system_prompt,
            metadata=req.metadata,
        )

        text = ""
        error: str | None = None
        usage: Mapping[str, Any] | None = None
        try:
            messages = self._build_messages(sid, req)
            reply = provider.generate(messages)
            text = getattr(reply, "content", "") or ""
            usage = self._extract_usage(reply)
        except Exception as exc:  # noqa: BLE001 — explicit fail-soft
            error = f"{exc.__class__.__name__}: {exc}".strip()

        self.tracing.end_turn(trace, text=text, usage=usage, error=error)
        self._persist_turn(sid, req, text=text, model=slug, error=error, usage=usage)
        return ChatResponse(
            text=text,
            session_id=sid,
            model=slug,
            usage=usage,
            error=error,
        )

    def stream(self, request: ChatRequest | str) -> Iterator[StreamEvent]:
        """Yield :class:`StreamEvent` objects for a single turn.

        Most providers in the cascade (Anthropic SDK, Gemini SDK, etc.)
        only expose a single-shot ``generate`` today, so the MVP
        wraps :meth:`chat` and emits exactly two events: a ``delta``
        carrying the full reply, then a ``complete``. Errors collapse
        into a single ``error`` event. N.6 (HTTP/SSE) and N.5
        (sandbox provider) will upgrade this to genuine token-by-token
        streaming.
        """
        resp = self.chat(request)
        if resp.error:
            yield StreamEvent(kind="error", payload=resp.error)
            return
        yield StreamEvent(kind="delta", payload=resp.text)
        yield StreamEvent(kind="complete", payload=resp.text)

    def list_models(self) -> list[str]:
        """Every canonical model slug Lyra knows about, sorted.

        Backed by :class:`AliasRegistry.canonical_slugs`. The list
        is deduplicated so ``opus``/``claude-opus-4.5`` collapse
        into one entry — embedded callers usually want the
        provider-callable slug, not every alias the REPL accepts.
        """
        return DEFAULT_ALIASES.canonical_slugs()

    def list_skills(self) -> list[dict[str, Any]]:
        """All ``SKILL.md`` packs discoverable from this repo.

        Walks the same precedence chain the REPL uses (packaged →
        user-global → project-local). Returns dicts rather than the
        in-package ``Skill`` dataclass so the result survives a
        JSON / HTTP round trip — N.6 will serve this verbatim.

        Returns:
            One entry per skill with keys ``id``, ``description``,
            ``path``. Unknown fields default to empty strings, and
            duplicates resolve later-wins (same as the loader's
            chat-mode injection).
        """
        # Imported lazily so a fresh install without ``lyra_skills``
        # doesn't fail at module import — the helper already
        # degrades to ``[]`` in that case.
        from ..interactive.skills_inject import (
            _load_skills_safely,
            discover_skill_roots,
        )

        skills = _load_skills_safely(discover_skill_roots(self.repo_root))
        out: list[dict[str, Any]] = []
        for s in skills:
            path = getattr(s, "path", None)
            out.append(
                {
                    "id": getattr(s, "id", "") or "",
                    "description": (getattr(s, "description", "") or "").strip(),
                    "path": str(path) if path else "",
                }
            )
        # Stable order so callers (and tests) can compare lists by index.
        out.sort(key=lambda r: r["id"])
        return out

    def list_sessions(self) -> list[dict[str, Any]]:
        """Every on-disk session under this repo's ``.lyra/sessions``.

        Returns dicts with the same fields as
        :class:`SessionMeta` so the result is JSON-friendly.
        Order is ``session_id`` ascending, matching
        :meth:`SessionsStore.list`.
        """
        from ..interactive.sessions_store import SessionsStore

        store = SessionsStore(self.layout.sessions_dir)
        return [
            {
                "session_id": m.session_id,
                "name": m.name,
                "turn_count": m.turn_count,
                "created_at": m.created_at,
            }
            for m in store.list()
        ]

    def close(self) -> None:
        """Release client-held resources.

        No-op today. Reserved so future provider pools / sandbox
        handles can register cleanup without forcing callers to
        switch to a different API.
        """
        return None

    # Context manager sugar so ``with LyraClient() as c:`` Just Works.
    def __enter__(self) -> "LyraClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _normalize(self, request: ChatRequest | str) -> ChatRequest:
        """Coerce a raw string prompt into a :class:`ChatRequest`."""
        if isinstance(request, ChatRequest):
            return request
        if isinstance(request, str):
            return ChatRequest(prompt=request)
        raise TypeError(
            f"chat() expected ChatRequest or str, got {type(request).__name__}"
        )

    def _resolve_provider(self, model: str | None) -> tuple[Any, str]:
        """Build a provider for *model*, returning ``(provider, canonical_slug)``.

        The canonical slug is what we record in ``turns.jsonl`` so the
        Phase M dashboard / aggregator see the resolved name rather
        than whichever alias the caller typed (``opus`` vs
        ``claude-opus-4.5``).
        """
        requested = model or self._default_model
        slug = resolve_alias(requested) if requested else "auto"
        if self._provider_factory is not None:
            provider = self._provider_factory(slug)
        else:
            from ..llm_factory import build_llm

            provider = build_llm(slug or "auto")
        return provider, slug or "auto"

    def _build_messages(self, sid: str, req: ChatRequest) -> list[Any]:
        """Reconstruct the Message list the provider expects.

        Replays prior turns from ``turns.jsonl`` so a follow-up
        ``chat()`` call carries conversational context without the
        caller having to re-send history. ``harness_core.messages``
        is imported lazily so an embedded user who just wants
        :meth:`list_models` doesn't pay the import cost.
        """
        from harness_core.messages import Message

        msgs: list[Any] = []
        if req.system_prompt:
            msgs.append(Message.system(req.system_prompt))
        for row in self._read_turns(sid):
            role = row.get("role")
            content = row.get("content") or ""
            if role == "user":
                msgs.append(Message.user(content))
            elif role == "assistant" and not row.get("error"):
                msgs.append(Message.assistant(content=content))
        msgs.append(Message.user(req.prompt))
        return msgs

    def _read_turns(self, sid: str) -> list[dict[str, Any]]:
        """Best-effort JSONL reader. Skips malformed lines."""
        log = self.layout.sessions_dir / sid / "turns.jsonl"
        if not log.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
        return out

    def _persist_turn(
        self,
        sid: str,
        req: ChatRequest,
        *,
        text: str,
        model: str,
        error: str | None,
        usage: Mapping[str, Any] | None,
    ) -> None:
        """Append one user + one assistant row to ``turns.jsonl``.

        Two rows (not one combined) so the Phase M aggregator and
        observatory dashboard — which already groups by ``role`` —
        consume the same event shape the REPL writes. ``ts`` is
        identical for the pair so both rows fall in the same
        time bucket.
        """
        sess_dir = self.layout.sessions_dir / sid
        sess_dir.mkdir(parents=True, exist_ok=True)
        log = sess_dir / "turns.jsonl"
        ts = time.time()

        rows: list[dict[str, Any]] = [
            {
                "ts": ts,
                "role": "user",
                "content": req.prompt,
                "model": model,
                "session_id": sid,
                "metadata": dict(req.metadata or {}),
            },
            {
                "ts": ts,
                "role": "assistant",
                "content": text,
                "model": model,
                "session_id": sid,
                "error": error,
                "usage": dict(usage) if usage else None,
            },
        ]
        with log.open("a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _extract_usage(self, reply: Any) -> Mapping[str, Any] | None:
        """Pull a provider-agnostic usage dict off an assistant message.

        ``harness_core.messages.Message`` has no usage field today;
        provider adapters set it ad-hoc. We poke a few common
        attribute / key shapes and return ``None`` when nothing is
        recognisable so callers can branch on truthiness.
        """
        if reply is None:
            return None
        usage = getattr(reply, "usage", None)
        if usage is None and isinstance(reply, dict):
            usage = reply.get("usage")
        if usage is None:
            return None
        if isinstance(usage, Mapping):
            return dict(usage)
        if hasattr(usage, "__dict__"):
            return {k: v for k, v in vars(usage).items() if not k.startswith("_")}
        return None


__all__ = ["LyraClient"]
