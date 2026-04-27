"""LLM selection for the CLI.

The ``--llm`` flag accepts one of:

* ``auto`` (default) — pick the best configured backend in this
  order and silently fall through on the rest:

    1.  **DeepSeek**            — ``DEEPSEEK_API_KEY``
    2.  **Anthropic**           — ``ANTHROPIC_API_KEY``
    3.  **OpenAI**              — ``OPENAI_API_KEY``
    4.  **Gemini**              — ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY``
    5.  **xAI** (Grok)          — ``XAI_API_KEY`` / ``GROK_API_KEY``
    6.  **Groq**                — ``GROQ_API_KEY``
    7.  **Cerebras**            — ``CEREBRAS_API_KEY``
    8.  **Mistral**             — ``MISTRAL_API_KEY``
    9.  **Qwen / DashScope**    — ``DASHSCOPE_API_KEY`` / ``QWEN_API_KEY``
    10. **OpenRouter**          — ``OPENROUTER_API_KEY``
    11. **LM Studio** (local)   — reachable ``:1234/v1/models``
    12. **Ollama** (local)      — reachable ``:11434/api/tags``

  DeepSeek heads the cascade because in 2026 its coder models match
  Claude Sonnet / GPT-5 on agentic-coding benchmarks at roughly
  10-20× lower per-token cost; for the typical Lyra user the
  cost-aware default is the right one. Users who want a different
  primary still get it via ``--llm anthropic`` / ``--llm openai`` /
  etc., or by simply not setting ``DEEPSEEK_API_KEY``.

  If none of the above can be built, raise
  :class:`NoProviderConfigured`. This is the **production** behaviour
  added in v2.1; the previous silent downgrade to the mock provider
  hid setup bugs and made unconfigured installs feel "alive when they
  weren't" (the operator saw canned plan text and thought their
  agent was working). Tests can keep using ``--llm mock`` explicitly.

* ``mock`` — always the mock provider with a canned plan artifact.
  Used by tests and docs that must be deterministic. NEVER picked by
  the auto cascade; you must ask for it by name.
* ``anthropic`` / ``openai`` / ``openai-reasoning`` / ``gemini`` /
  ``deepseek`` / ``xai`` / ``groq`` / ``cerebras`` / ``mistral`` /
  ``qwen`` / ``openrouter`` / ``lmstudio`` / ``ollama`` — *require*
  the named provider. Raises if the key / daemon is missing.
  Fail-loud variant for CI where a silent downgrade to the mock
  would hide bugs.

The cascade is intentionally silent in ``auto`` mode: each path
decides by itself and hands back a working provider. Callers that
want to *tell* the user which backend was picked (status line,
``lyra doctor``) use :func:`describe_selection` — same
reachability checks, no provider construction.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

from harness_core.models import LLMProvider, MockLLM

from lyra_core.providers.aliases import resolve_alias
from lyra_core.providers.auth_hints import missing_credential_hint
from lyra_core.providers.dotenv import dotenv_value

from .providers.anthropic import LyraAnthropicLLM as AnthropicLLM
from .providers.bedrock import (
    AnthropicBedrockLLM,
    BedrockUnavailable,
    bedrock_available,
)
from .providers.gemini import (
    GEMINI_DEFAULT_MODEL,
    GeminiLLM,
    gemini_configured,
)
from .providers.ollama import (
    OLLAMA_DEFAULT_MODEL,
    OllamaConnectionError,
    OllamaLLM,
    ollama_reachable,
)
from .providers.openai_compatible import (
    ProviderNotConfigured,
    configured_presets,
    iter_presets,
    preset_by_name,
)
from .providers.vertex import (
    GeminiVertexLLM,
    VertexUnavailable,
    vertex_available,
)


_DOTENV_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "DASHSCOPE_API_KEY",
    "QWEN_API_KEY",
    # v2.3.0: cloud-routed Anthropic (Bedrock) and cloud-routed
    # Gemini (Vertex AI) — both bring their own auth conventions
    # (AWS_REGION + boto3 credential chain; GOOGLE_CLOUD_PROJECT +
    # ADC). We hydrate these from dotenv too so a project-local
    # ``.env`` can drive the whole config without setting them
    # globally.
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "BEDROCK_MODEL",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "VERTEX_MODEL",
    "GITHUB_TOKEN",
    "COPILOT_MODEL",
    "OLLAMA_HOST",
    "OPEN_HARNESS_LOCAL_MODEL",
    "OPEN_HARNESS_GEMINI_MODEL",
    "GEMINI_MODEL",
    "OLLAMA_MODEL",
    "HARNESS_LLM_MODEL",
)


class NoProviderConfigured(RuntimeError):
    """Raised by :func:`build_llm` when ``auto`` finds nothing usable.

    The error message must be actionable: it lists the env vars the
    cascade scanned and points the operator at ``lyra connect`` (the
    Phase 3 picker) so the fix is a single command away. Production
    code paths should catch this exception and render the hint via
    Rich rather than letting Python print the bare traceback.
    """

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or (
                "no provider configured for --llm auto.\n\n"
                "Lyra scanned ANTHROPIC_API_KEY, OPENAI_API_KEY, "
                "GEMINI_API_KEY, DEEPSEEK_API_KEY, XAI_API_KEY, "
                "GROQ_API_KEY, CEREBRAS_API_KEY, MISTRAL_API_KEY, "
                "DASHSCOPE_API_KEY (Qwen), OPENROUTER_API_KEY, plus "
                "the local LM Studio (:1234) and Ollama (:11434) "
                "daemons, and found no working backend.\n\n"
                "Fix it by either:\n"
                "  • setting one of the keys above (export "
                "ANTHROPIC_API_KEY=... etc.), or\n"
                "  • running `lyra connect` to pick a provider and "
                "paste a key interactively, or\n"
                "  • passing --llm mock explicitly for offline / "
                "deterministic tests."
            )
        )


# Map a provider name (as saved in ``~/.lyra/auth.json``) to the env
# var the cascade reads. Kept in this module so adding a new provider
# preset in ``openai_compatible.py`` only requires updating this map +
# the preset table — no surgery in build_llm itself.
_AUTHJSON_PROVIDER_TO_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    # v2.3.0: GitHub OAuth → Copilot session token. Saved as a long-
    # lived ``gho_*`` token in auth.json under provider key
    # ``copilot``; the CLI exchanges it for a 30-min ``ghs_*`` token
    # on first call.
    "copilot": "GITHUB_TOKEN",
}


def _hydrate_env_from_authjson() -> None:
    """Source any missing provider keys from ``~/.lyra/auth.json``.

    Resolution priority (low → high) when a key is needed:

    1. ``~/.lyra/auth.json`` (this function) — long-lived store
       written by ``lyra connect``.
    2. Project-local ``.env`` (see :func:`_hydrate_env_from_dotenv`).
    3. Process env (``os.environ``) — wins, so ``ANTHROPIC_API_KEY=…
       lyra`` continues to override.

    We stamp env vars in this order from lowest to highest, only
    filling in slots that are still empty, so the env-var the user
    passed always beats a stale auth.json entry.
    """
    try:
        from lyra_core.auth.store import load as _load_auth
    except Exception:
        return
    try:
        data = _load_auth()
    except Exception:
        return
    providers = data.get("providers", {}) if isinstance(data, dict) else {}
    if not isinstance(providers, dict):
        return
    for provider, entry in providers.items():
        if not isinstance(entry, dict):
            continue
        env_name = _AUTHJSON_PROVIDER_TO_ENV.get(provider)
        if not env_name or os.environ.get(env_name):
            continue
        api_key = entry.get("api_key")
        if isinstance(api_key, str) and api_key:
            os.environ[env_name] = api_key


def _hydrate_env_from_dotenv() -> None:
    """Source any missing provider keys from auth.json or a local ``.env``.

    Idempotent: env vars that are already set in :data:`os.environ`
    always win — we only fill in *unset* keys. Resolution layers:

    1. ``~/.lyra/auth.json`` (long-lived store, written by ``lyra
       connect``) — checked first so a saved key resurfaces even when
       no ``.env`` is around.
    2. Project-local ``.env`` (claw-code semantics: walk from CWD up).

    Silently no-ops when neither source provides a value.
    """
    _hydrate_env_from_authjson()
    for key in _DOTENV_KEYS:
        if os.environ.get(key):
            continue
        value = dotenv_value(key)
        if value:
            os.environ[key] = value


def _resolve_model_alias_from_env() -> None:
    """Replace ``HARNESS_LLM_MODEL`` with its canonical slug if it's an alias.

    Lets users type ``HARNESS_LLM_MODEL=opus`` (or ``--model opus``)
    and have the canonical ``claude-opus-4.5`` slug propagate to every
    downstream consumer (registry lookup, preflight, OTel attributes).
    """
    requested = os.environ.get("HARNESS_LLM_MODEL", "").strip()
    if not requested:
        return
    resolved = resolve_alias(requested)
    if resolved and resolved != requested:
        os.environ["HARNESS_LLM_MODEL"] = resolved


def _emit_provider_selected(provider: str, model: str, *, is_local: bool) -> None:
    """Fire a ``provider_selected`` HIR event. Best-effort."""
    try:
        from lyra_core.hir import events as hir_events

        hir_events.emit(
            "provider_selected",
            provider=provider,
            model=model,
            local=is_local,
        )
    except Exception:
        # Telemetry must never break the cascade.
        pass


def _provider_routing_for_preset(name: str):
    """Return a :class:`ProviderRouting` populated from ``settings.json`` or ``None``.

    Best-effort: any failure (missing file, malformed JSON, unknown
    keys) returns ``None`` so the caller silently skips the routing
    payload. Lets users dial OpenRouter knobs (``sort`` / ``only`` /
    ``ignore`` / ``order`` / ``require_parameters`` /
    ``data_collection``) via ``~/.lyra/settings.json`` without env
    vars or CLI flags.
    """
    try:
        from lyra_core.providers.registry import provider_routing_for

        from .providers.openai_compatible import ProviderRouting

        cfg = provider_routing_for(name)
        if not cfg:
            return None
        # Filter to known fields so a typo doesn't break the build.
        # Coerce JSON arrays (lists) to the tuples the dataclass wants
        # for hashability; other field types pass through unchanged.
        tuple_fields = {"only", "ignore", "order"}
        allowed = {
            "sort",
            "require_parameters",
            "data_collection",
        } | tuple_fields
        kwargs: dict = {}
        for k, v in cfg.items():
            if k not in allowed:
                continue
            if k in tuple_fields and isinstance(v, list):
                kwargs[k] = tuple(v)
            else:
                kwargs[k] = v
        if not kwargs:
            return None
        return ProviderRouting(**kwargs)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Canned mock plan (for --llm mock and as the ultimate fallback)
# ---------------------------------------------------------------------------


def _canned_plan_text(task: str, *, session_id: str) -> str:
    """Deterministic Plan-Mode artifact for the mock provider.

    Kept inline (rather than in a separate provider file) so changes
    to the plan schema touch one place.
    """
    goal_hash = "sha256:" + hashlib.sha256(task.encode("utf-8")).hexdigest()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    return (
        "---\n"
        f"session_id: {session_id}\n"
        f"created_at: {created_at}\n"
        "planner_model: mock\n"
        "estimated_cost_usd: 0.0\n"
        f"goal_hash: {goal_hash}\n"
        "---\n\n"
        "# Plan: " + (task[:80] or "untitled") + "\n\n"
        "## Acceptance tests\n"
        "- tests/test_generated.py::test_placeholder\n\n"
        "## Expected files\n"
        "- src/generated.py\n\n"
        "## Forbidden files\n\n"
        "## Feature items\n"
        "1. **(test_gen)** Write a failing test for the requested behaviour\n"
        "2. **(edit)** Implement the smallest diff that passes the test\n\n"
        "## Open questions\n\n"
        "## Notes\n"
        "Produced by mock LLM in canned Plan Mode\n"
    )


# ---------------------------------------------------------------------------
# Individual backend availability checks
# ---------------------------------------------------------------------------


def _anthropic_available() -> bool:
    """True iff an Anthropic run would be viable without crashing.

    Checks both the key *and* the import — having the key but no
    ``anthropic`` package on ``PYTHONPATH`` is a user-configuration
    error we don't want to hit during ``auto`` selection (it would
    raise at construction time and abort the whole run).
    """
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _build_mock(task_hint: Optional[str], session_id: Optional[str]) -> MockLLM:
    sid = session_id or "01HMOCK0000000000000000000"
    task = task_hint or ""
    return MockLLM(scripted_outputs=[_canned_plan_text(task, session_id=sid)])


# ---------------------------------------------------------------------------
# Known --llm names (for the CLI flag's help text and validation)
# ---------------------------------------------------------------------------


_ALWAYS_KNOWN = (
    "auto",
    "mock",
    "anthropic",
    "gemini",
    "ollama",
    "qwen",
    # v2.3.0: cloud-routed and Copilot — explicitly named so CI can
    # ``--llm bedrock`` / ``--llm vertex`` / ``--llm copilot`` and
    # fail loud if their auth isn't configured.
    "bedrock",
    "vertex",
    "copilot",
)


def known_llm_names() -> list[str]:
    """Every backend slug the ``--llm`` flag accepts.

    Used by the CLI's ``--help`` text (``lyra run --help`` lists
    them) and by future shell-completion integration. We compute this
    dynamically so adding a new OpenAI-compatible preset automatically
    shows up everywhere without touching the CLI commands.

    Phase N.8: also surface custom providers from
    ``settings.json:providers`` so user-defined slugs appear in
    ``--help`` alongside the built-ins.
    """
    preset_names = [p.name for p in iter_presets()]
    try:
        from .provider_registry import known_custom_slugs

        custom = known_custom_slugs()
    except Exception:
        # Bad settings.json must never break the CLI's help text.
        custom = []
    return list(_ALWAYS_KNOWN) + preset_names + list(custom)


def _maybe_build_custom_provider(kind: str) -> Optional[LLMProvider]:
    """Try to satisfy ``--llm <kind>`` from the custom-provider registry.

    Returns ``None`` when *kind* isn't a registered slug; the cascade
    in :func:`build_llm` then falls through to the built-in branches.
    Failures *during* construction (bad import string, unimportable
    module, factory TypeError) re-raise as
    :class:`~.provider_registry.CustomProviderError` so the user
    gets a clear "your settings.json is wrong" message instead of a
    silent fall-through to the auto cascade.
    """
    if not kind or kind == "auto":
        return None
    try:
        from .provider_registry import (
            build_provider,
            load_registered_providers,
        )
    except Exception:
        return None
    registered = load_registered_providers()
    entry = registered.get(kind)
    if entry is None:
        return None
    llm = build_provider(entry)
    _emit_provider_selected(entry.slug, entry.import_string, is_local=False)
    return llm


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_llm(
    kind: str,
    *,
    task_hint: Optional[str] = None,
    session_id: Optional[str] = None,
) -> LLMProvider:
    """Resolve the CLI's ``--llm`` choice into an :class:`LLMProvider`.

    See the module docstring for the ``auto`` cascade order and the
    fail-loud semantics of explicit names.
    """
    kind = (kind or "auto").lower().strip()
    _hydrate_env_from_dotenv()
    _resolve_model_alias_from_env()

    # -- mock: always works ---------------------------------------------
    if kind == "mock":
        llm = _build_mock(task_hint, session_id)
        _emit_provider_selected("mock", "canned", is_local=True)
        return llm

    # -- explicit Anthropic ---------------------------------------------
    if kind == "anthropic":
        if not _anthropic_available():
            hint = missing_credential_hint(asking="anthropic")
            msg = "anthropic: ANTHROPIC_API_KEY not set"
            if hint:
                msg = f"{msg} - {hint}"
            raise RuntimeError(msg)
        llm = AnthropicLLM()
        model = os.environ.get("HARNESS_LLM_MODEL", "claude-3-5-sonnet-latest")
        _emit_provider_selected("anthropic", model, is_local=False)
        return llm

    # -- explicit Gemini ------------------------------------------------
    if kind == "gemini":
        llm = GeminiLLM()
        model = (
            os.environ.get("OPEN_HARNESS_GEMINI_MODEL", "").strip()
            or os.environ.get("GEMINI_MODEL", "").strip()
            or GEMINI_DEFAULT_MODEL
        )
        _emit_provider_selected("gemini", model, is_local=False)
        return llm

    # -- explicit Bedrock (Anthropic via AWS) ---------------------------
    if kind == "bedrock":
        if not bedrock_available():
            raise BedrockUnavailable(
                "bedrock: boto3 not installed. "
                "Install with `pip install 'lyra[bedrock]'` and ensure "
                "AWS credentials are configured (env vars, ~/.aws/credentials, "
                "or an IAM role)."
            )
        model = (
            os.environ.get("BEDROCK_MODEL", "").strip()
            or os.environ.get("HARNESS_LLM_MODEL", "").strip()
            or "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        region = (
            os.environ.get("AWS_REGION", "").strip()
            or os.environ.get("AWS_DEFAULT_REGION", "").strip()
            or None
        )
        llm = AnthropicBedrockLLM(model=model, region=region)
        _emit_provider_selected("bedrock", model, is_local=False)
        return llm

    # -- explicit Vertex AI (Gemini via Google Cloud) -------------------
    if kind == "vertex":
        if not vertex_available():
            raise VertexUnavailable(
                "vertex: google-cloud-aiplatform not installed. "
                "Install with `pip install 'lyra[vertex]'` and ensure "
                "GOOGLE_CLOUD_PROJECT plus Application Default Credentials "
                "are configured (`gcloud auth application-default login`)."
            )
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
        if not project:
            raise VertexUnavailable(
                "vertex: GOOGLE_CLOUD_PROJECT not set. "
                "Run `gcloud config set project <project-id>` or export "
                "GOOGLE_CLOUD_PROJECT before retrying."
            )
        location = (
            os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip()
            or "us-central1"
        )
        model = (
            os.environ.get("VERTEX_MODEL", "").strip()
            or os.environ.get("HARNESS_LLM_MODEL", "").strip()
            or "gemini-2.5-pro"
        )
        llm = GeminiVertexLLM(model=model, project=project, location=location)
        _emit_provider_selected("vertex", model, is_local=False)
        return llm

    # -- explicit Copilot (GitHub OAuth → Copilot chat) -----------------
    if kind == "copilot":
        from .providers._urllib_http import StdlibHTTP
        from .providers.copilot import (
            CopilotLLM,
            CopilotTokenStore,
            CopilotUnavailable,
        )

        github_token = os.environ.get("GITHUB_TOKEN", "").strip()
        if not github_token:
            raise CopilotUnavailable(
                "copilot: GITHUB_TOKEN not set. "
                "Run `lyra connect copilot --key <gho_token>` to save one, "
                "or export GITHUB_TOKEN with a Copilot-eligible token."
            )
        # Stdlib-only HTTP keeps Lyra's footprint small. Anyone
        # hammering Copilot at production volume can subclass and
        # pass a real ``requests.Session`` / ``urllib3.PoolManager``
        # via :class:`CopilotLLM` directly.
        model = (
            os.environ.get("COPILOT_MODEL", "").strip()
            or os.environ.get("HARNESS_LLM_MODEL", "").strip()
            or "gpt-4o"
        )
        llm = CopilotLLM(
            github_token=github_token,
            http=StdlibHTTP(),
            model=model,
            token_store=CopilotTokenStore(),
        )
        _emit_provider_selected("copilot", model, is_local=False)
        return llm

    # -- explicit Ollama ------------------------------------------------
    if kind == "ollama":
        if not ollama_reachable():
            raise OllamaConnectionError(
                "ollama daemon not reachable. "
                "Start it with `ollama serve` (or launch the Ollama "
                "app), then retry."
            )
        llm = OllamaLLM()
        model = (
            os.environ.get("OPEN_HARNESS_LOCAL_MODEL", "").strip()
            or os.environ.get("OLLAMA_MODEL", "").strip()
            or OLLAMA_DEFAULT_MODEL
        )
        _emit_provider_selected("ollama", model, is_local=True)
        return llm

    # -- custom provider (N.8 import-string registry) -------------------
    # Looked up *before* the OpenAI-compatible preset table so users
    # can override a built-in slug with their own implementation if
    # they really want to (e.g. monkey-patched DeepSeek with custom
    # auth). The lookup is cheap — a single JSON read — and it
    # returns ``None`` when the slug isn't registered.
    custom = _maybe_build_custom_provider(kind)
    if custom is not None:
        return custom

    # -- explicit OpenAI-compatible preset ------------------------------
    # Phase 2: ``qwen`` is a real preset peer of ``dashscope`` (same
    # endpoint, same key fallbacks); no alias substitution needed.
    preset = preset_by_name(kind) if kind != "auto" else None
    if preset is not None:
        # Fail-loud: if the user *asked* for this preset and the key
        # is missing, surface that rather than silently downgrading.
        llm = preset.build(provider_routing=_provider_routing_for_preset(preset.name))
        _emit_provider_selected(
            preset.name,
            preset.read_model(),
            is_local=preset.auth_scheme == "none",
        )
        return llm

    if kind != "auto":
        # Unknown name → treat as auto. The CLI validates against
        # ``known_llm_names`` before we get here in normal flows; this
        # branch is the belt-and-braces for programmatic callers.
        kind = "auto"

    # ------------------------- auto cascade ----------------------------
    #
    # Priority order in 2026:
    #
    #   1. DeepSeek — cost-aware default. Coder models match Claude /
    #      GPT-5 on agentic benchmarks at ~10-20× lower per-token cost;
    #      the typical Lyra user's bill is dominated by tool loops, so
    #      DeepSeek-first saves money without sacrificing quality.
    #   2. Anthropic — reference target for tool-using agents; users
    #      who care about Claude specifically usually have the key.
    #   3. OpenAI / Gemini / xAI / Groq / Cerebras / Mistral / Qwen /
    #      OpenRouter — iterated via the preset registry in declaration
    #      order, "roughly cheapest per token that's still good at
    #      code".
    #   4. LM Studio + Ollama — local fallbacks last so users who
    #      accidentally left a key in their env don't suddenly route
    #      to their laptop.
    #
    # Users who want Anthropic-first still get it via ``--llm
    # anthropic`` (explicit), or by simply not setting
    # ``DEEPSEEK_API_KEY``.

    deepseek_preset = preset_by_name("deepseek")
    if deepseek_preset is not None and deepseek_preset.configured():
        try:
            llm = deepseek_preset.build(
                provider_routing=_provider_routing_for_preset("deepseek")
            )
            _emit_provider_selected(
                "deepseek", deepseek_preset.read_model(), is_local=False
            )
            return llm
        except ProviderNotConfigured:
            # Defensive: env var was scrubbed between configured()
            # and build(). Fall through to the rest of the cascade.
            pass

    if _anthropic_available():
        try:
            llm = AnthropicLLM()
            model = os.environ.get("HARNESS_LLM_MODEL", "claude-3-5-sonnet-latest")
            _emit_provider_selected("anthropic", model, is_local=False)
            return llm
        except ImportError:
            pass  # ``anthropic`` disappeared between check and build

    # OpenAI / OpenAI-reasoning / xAI / Groq / Cerebras / Mistral /
    # OpenRouter / LM Studio — all iterated via the preset registry so
    # adding a new preset automatically slots into auto. DeepSeek is
    # already handled above and is skipped here to avoid double-trying.
    for p in configured_presets():
        if p.name == "deepseek":
            continue
        try:
            llm = p.build(provider_routing=_provider_routing_for_preset(p.name))
            _emit_provider_selected(
                p.name, p.read_model(), is_local=p.auth_scheme == "none"
            )
            return llm
        except ProviderNotConfigured:
            # Should not happen after ``configured()`` said True, but
            # defensive just in case an env var disappeared between
            # the check and the build.
            continue

    if gemini_configured():
        try:
            llm = GeminiLLM()
            model = (
                os.environ.get("OPEN_HARNESS_GEMINI_MODEL", "").strip()
                or os.environ.get("GEMINI_MODEL", "").strip()
                or GEMINI_DEFAULT_MODEL
            )
            _emit_provider_selected("gemini", model, is_local=False)
            return llm
        except ProviderNotConfigured:
            pass

    if ollama_reachable():
        # If Ollama is up but the target model isn't pulled yet, we
        # still return the provider — the first ``generate`` call will
        # raise ``OllamaConnectionError`` with the exact ``ollama pull
        # <model>`` command to run. Better than silently dropping to
        # the mock and leaving the user confused.
        llm = OllamaLLM()
        model = (
            os.environ.get("OPEN_HARNESS_LOCAL_MODEL", "").strip()
            or os.environ.get("OLLAMA_MODEL", "").strip()
            or OLLAMA_DEFAULT_MODEL
        )
        _emit_provider_selected("ollama", model, is_local=True)
        return llm

    # No backend matched. Fail-loud per the v2.1 contract — the silent
    # downgrade to MockLLM is gone. This is the path the user sees when
    # they ran `lyra` without any API key set; the exception message
    # tells them how to fix it.
    raise NoProviderConfigured()


def describe_selection(kind: str = "auto") -> str:
    """Short human label for the backend ``build_llm(kind)`` would return.

    Examples::

        "anthropic · claude-3-5-sonnet-latest"
        "openai · gpt-5"
        "gemini · gemini-2.5-pro"
        "ollama · qwen2.5-coder:1.5b (local)"
        "mock · canned outputs (no API key, no local model)"

    Used by the status line, ``lyra doctor``, and the REPL
    startup banner so the user can see which backend they're actually
    talking to. Runs the same availability checks as :func:`build_llm`
    but does not construct the provider — cheap enough to call on
    every status refresh.
    """
    kind = (kind or "auto").lower().strip()
    _hydrate_env_from_dotenv()
    _resolve_model_alias_from_env()

    if kind == "mock":
        return "mock · canned outputs"

    if kind == "anthropic":
        model = os.environ.get("HARNESS_LLM_MODEL", "claude-3-5-sonnet-latest")
        return f"anthropic · {model}"

    if kind == "gemini":
        model = (
            os.environ.get("OPEN_HARNESS_GEMINI_MODEL", "").strip()
            or os.environ.get("GEMINI_MODEL", "").strip()
            or GEMINI_DEFAULT_MODEL
        )
        return f"gemini · {model}"

    if kind == "ollama":
        model = (
            os.environ.get("OPEN_HARNESS_LOCAL_MODEL", "").strip()
            or os.environ.get("OLLAMA_MODEL", "").strip()
            or OLLAMA_DEFAULT_MODEL
        )
        return f"ollama · {model} (local)"

    if kind == "bedrock":
        model = (
            os.environ.get("BEDROCK_MODEL", "").strip()
            or os.environ.get("HARNESS_LLM_MODEL", "").strip()
            or "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        return f"bedrock · {model}"

    if kind == "vertex":
        model = (
            os.environ.get("VERTEX_MODEL", "").strip()
            or os.environ.get("HARNESS_LLM_MODEL", "").strip()
            or "gemini-2.5-pro"
        )
        return f"vertex · {model}"

    if kind == "copilot":
        model = (
            os.environ.get("COPILOT_MODEL", "").strip()
            or os.environ.get("HARNESS_LLM_MODEL", "").strip()
            or "gpt-4o"
        )
        return f"copilot · {model}"

    # ``qwen`` resolves directly via :func:`preset_by_name` now (Phase 2
    # promoted it from string-alias to a real preset).
    preset = preset_by_name(kind) if kind != "auto" else None
    if preset is not None:
        model = preset.read_model()
        suffix = " (local)" if preset.auth_scheme == "none" else ""
        return f"{preset.name} · {model}{suffix}"

    # auto: same cascade as build_llm, but string-only — DeepSeek
    # first, then Anthropic, then the rest of the preset registry.
    deepseek_preset = preset_by_name("deepseek")
    if deepseek_preset is not None and deepseek_preset.configured():
        return f"deepseek · {deepseek_preset.read_model()}"

    if _anthropic_available():
        model = os.environ.get("HARNESS_LLM_MODEL", "claude-3-5-sonnet-latest")
        return f"anthropic · {model}"

    for p in configured_presets():
        if p.name == "deepseek":
            continue
        suffix = " (local)" if p.auth_scheme == "none" else ""
        return f"{p.name} · {p.read_model()}{suffix}"

    if gemini_configured():
        model = (
            os.environ.get("OPEN_HARNESS_GEMINI_MODEL", "").strip()
            or os.environ.get("GEMINI_MODEL", "").strip()
            or GEMINI_DEFAULT_MODEL
        )
        return f"gemini · {model}"

    if ollama_reachable():
        model = (
            os.environ.get("OPEN_HARNESS_LOCAL_MODEL", "").strip()
            or os.environ.get("OLLAMA_MODEL", "").strip()
            or OLLAMA_DEFAULT_MODEL
        )
        return f"ollama · {model} (local)"

    # No backend matches — be honest about it instead of advertising
    # "mock canned outputs". Status bars / `lyra doctor` use this string
    # verbatim, so the wording is consciously short.
    return "unconfigured · run `lyra connect` or set an API key"


__all__ = [
    "build_llm",
    "describe_selection",
    "known_llm_names",
    "NoProviderConfigured",
]
