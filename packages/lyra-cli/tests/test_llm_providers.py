"""Hermetic tests for every provider we ship.

Covers:

* the OpenAI-compatible base class (message encode/decode, tool
  schema translation, reasoning-model token-param flip, OpenRouter
  extra headers, error surfacing),
* the Gemini adapter (system-instruction split, tool-call / tool-
  result mapping, safety-filter error surfacing),
* the Ollama adapter (already shipped, now tested properly),
* the :func:`build_llm` cascade priority with every combination of
  env vars / local probes mocked,
* :func:`describe_selection` label formatting for every backend,
* the ``known_llm_names()`` output so ``--help`` stays in sync.

All HTTP is mocked via :func:`unittest.mock.patch` on
``urllib.request.urlopen`` — **no network** reaches out even if the
test machine has a real Ollama daemon running.
"""
from __future__ import annotations

import io
import json
from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import MagicMock, patch

import pytest
from harness_core.messages import Message, StopReason, ToolCall, ToolResult

from lyra_cli.llm_factory import (
    build_llm,
    describe_selection,
    known_llm_names,
)
from lyra_cli.providers.gemini import GeminiLLM
from lyra_cli.providers.ollama import OllamaConnectionError, OllamaLLM
from lyra_cli.providers.openai_compatible import (
    OpenAICompatibleLLM,
    ProviderHTTPError,
    ProviderNotConfigured,
    preset_by_name,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    """Minimal ``urlopen`` response stand-in with context-manager support."""

    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        return None


@contextmanager
def mock_urlopen(
    body: dict[str, Any] | bytes,
    *,
    status: int = 200,
) -> Iterator[MagicMock]:
    """Patch ``urllib.request.urlopen`` to return a canned JSON body.

    Yielded MagicMock has ``.call_args_list`` so tests can assert on
    what we actually sent to the wire.
    """
    payload = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    with patch("urllib.request.urlopen") as m:
        m.return_value = _FakeHTTPResponse(payload, status=status)
        yield m


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scrub every env var a provider might read so tests are hermetic."""
    for k in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "DEEPSEEK_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "OPEN_HARNESS_OPENAI_MODEL",
        "OPENAI_MODEL",
        "OPEN_HARNESS_GEMINI_MODEL",
        "GEMINI_MODEL",
        "OPEN_HARNESS_LOCAL_MODEL",
        "OLLAMA_MODEL",
        "OLLAMA_HOST",
        "OPEN_HARNESS_GROQ_MODEL",
        "GROQ_MODEL",
        "HARNESS_LLM_MODEL",
    ):
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------------------
# OpenAI-compatible base
# ---------------------------------------------------------------------------


def _sample_openai_response(
    *,
    text: str = "hi",
    tool_calls: list[dict[str, Any]] | None = None,
    finish_reason: str = "stop",
) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": text}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "choices": [
            {
                "index": 0,
                "message": msg,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
    }


def test_openai_basic_text_generation() -> None:
    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-5",
        provider_name="openai",
    )
    with mock_urlopen(_sample_openai_response(text="Hello world.")) as m:
        out = llm.generate([Message.user("Hi")])
    assert isinstance(out, Message)
    assert out.role == "assistant"
    assert out.content == "Hello world."
    assert out.stop_reason is StopReason.END_TURN
    # Verify the request that went out.
    req = m.call_args.args[0]
    assert req.full_url == "https://api.openai.com/v1/chat/completions"
    assert req.headers["Authorization"] == "Bearer sk-test"
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["model"] == "gpt-5"
    assert payload["messages"] == [{"role": "user", "content": "Hi"}]
    assert payload["max_tokens"] == 2048
    assert payload["temperature"] == 0.0


def test_openai_tool_call_round_trip() -> None:
    """Anthropic tool schema → OpenAI → response → ToolCall list."""
    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-5",
        provider_name="openai",
    )
    anthropic_tool = {
        "name": "read_file",
        "description": "Read a file from disk",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    }
    response = _sample_openai_response(
        text="",
        tool_calls=[
            {
                "id": "call_abc",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "README.md"}),
                },
            }
        ],
        finish_reason="tool_calls",
    )
    with mock_urlopen(response) as m:
        out = llm.generate([Message.user("read the readme")], tools=[anthropic_tool])
    assert out.stop_reason is StopReason.TOOL_USE
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].name == "read_file"
    assert out.tool_calls[0].args == {"path": "README.md"}
    # And on the wire: the tool schema was translated to OpenAI shape.
    sent = json.loads(m.call_args.args[0].data.decode("utf-8"))
    assert sent["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from disk",
                "parameters": anthropic_tool["input_schema"],
            },
        }
    ]


def test_openai_tool_result_encoding() -> None:
    """tool-role Message serialises as role=tool with tool_call_id."""
    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-5",
        provider_name="openai",
    )
    tool_msg = Message.tool(
        [ToolResult(call_id="call_abc", content="file contents", is_error=False)]
    )
    with mock_urlopen(_sample_openai_response(text="ok")) as m:
        llm.generate([Message.user("x"), tool_msg])
    sent = json.loads(m.call_args.args[0].data.decode("utf-8"))
    tool_wire = sent["messages"][-1]
    assert tool_wire["role"] == "tool"
    assert tool_wire["tool_call_id"] == "call_abc"
    assert "file contents" in tool_wire["content"]


def test_openai_reasoning_model_uses_max_completion_tokens() -> None:
    """o-series preset sends ``max_completion_tokens`` and ``reasoning_effort``."""
    preset = preset_by_name("openai-reasoning")
    assert preset is not None
    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url=preset.base_url,
        model=preset.default_model,
        provider_name=preset.name,
        reasoning=preset.reasoning,
    )
    with mock_urlopen(_sample_openai_response()) as m:
        llm.generate([Message.user("solve p=np")], max_tokens=1024, temperature=0.3)
    sent = json.loads(m.call_args.args[0].data.decode("utf-8"))
    assert "max_tokens" not in sent
    assert sent["max_completion_tokens"] == 1024
    assert "temperature" not in sent, "reasoning models must not send temperature"
    assert sent["reasoning_effort"] == "medium"


def test_openrouter_sends_attribution_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    preset = preset_by_name("openrouter")
    assert preset is not None
    llm = preset.build()
    with mock_urlopen(_sample_openai_response()) as m:
        llm.generate([Message.user("hi")])
    req = m.call_args.args[0]
    # capfirst-style header keys (urllib normalises them).
    hdrs = {k.lower(): v for k, v in req.header_items()}
    assert hdrs["http-referer"].startswith("https://github.com/")
    assert hdrs["x-title"] == "Lyra"
    assert hdrs["authorization"] == "Bearer or-test"


def test_openai_http_error_wraps_as_provider_http_error() -> None:
    """HTTP 401 → :class:`ProviderHTTPError` with the server body in the msg."""
    import urllib.error

    llm = OpenAICompatibleLLM(
        api_key="sk-bad",
        base_url="https://api.openai.com/v1",
        model="gpt-5",
        provider_name="openai",
    )
    err = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b'{"error":{"message":"invalid key"}}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(ProviderHTTPError) as ei:
            llm.generate([Message.user("hi")])
    assert "HTTP 401" in str(ei.value)
    assert "invalid key" in str(ei.value)


def test_openai_missing_key_raises_not_configured() -> None:
    with pytest.raises(ProviderNotConfigured):
        OpenAICompatibleLLM(
            api_key=None,
            base_url="https://api.openai.com/v1",
            model="gpt-5",
            provider_name="openai",
        )


def test_openai_model_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    preset = preset_by_name("openai")
    assert preset is not None
    llm = preset.build()
    assert llm.model == "gpt-4o"


def test_lyra_namespaced_override_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``OPEN_HARNESS_<PROVIDER>_MODEL`` beats the vendor-default env var."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("OPEN_HARNESS_OPENAI_MODEL", "gpt-5-turbo")
    preset = preset_by_name("openai")
    assert preset is not None
    llm = preset.build()
    assert llm.model == "gpt-5-turbo"


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


def _sample_gemini_response(
    *,
    text: str = "hi",
    function_calls: list[dict[str, Any]] | None = None,
    finish_reason: str = "STOP",
) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    if text:
        parts.append({"text": text})
    for fc in function_calls or []:
        parts.append({"functionCall": fc})
    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": parts},
                "finishReason": finish_reason,
            }
        ]
    }


def test_gemini_system_prompt_goes_to_system_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    llm = GeminiLLM()
    with mock_urlopen(_sample_gemini_response(text="ok")) as m:
        llm.generate(
            [
                Message.system("you are concise"),
                Message.user("hi"),
            ]
        )
    payload = json.loads(m.call_args.args[0].data.decode("utf-8"))
    assert payload["systemInstruction"] == {"parts": [{"text": "you are concise"}]}
    # Only the user turn ends up in contents.
    assert len(payload["contents"]) == 1
    assert payload["contents"][0]["role"] == "user"


def test_gemini_assistant_role_relabels_to_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    llm = GeminiLLM()
    with mock_urlopen(_sample_gemini_response(text="ok")) as m:
        llm.generate(
            [
                Message.user("hi"),
                Message.assistant("hello back"),
                Message.user("again"),
            ]
        )
    payload = json.loads(m.call_args.args[0].data.decode("utf-8"))
    roles = [c["role"] for c in payload["contents"]]
    assert roles == ["user", "model", "user"]


def test_gemini_tool_schema_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    llm = GeminiLLM()
    tool = {
        "name": "read_file",
        "description": "Read a file",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    }
    with mock_urlopen(_sample_gemini_response(text="ok")) as m:
        llm.generate([Message.user("hi")], tools=[tool])
    sent = json.loads(m.call_args.args[0].data.decode("utf-8"))
    assert sent["tools"] == [
        {
            "functionDeclarations": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": tool["input_schema"],
                }
            ]
        }
    ]


def test_gemini_function_call_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    llm = GeminiLLM()
    response = _sample_gemini_response(
        text="",
        function_calls=[{"name": "read_file", "args": {"path": "README.md"}}],
    )
    with mock_urlopen(response):
        out = llm.generate([Message.user("read readme")])
    assert out.stop_reason is StopReason.TOOL_USE
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].name == "read_file"
    assert out.tool_calls[0].args == {"path": "README.md"}
    # Gemini doesn't return call ids; we synthesise deterministic ones.
    assert out.tool_calls[0].id.startswith("gemini_call_")


def test_gemini_safety_block_surfaces_as_provider_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    llm = GeminiLLM()
    blocked = {"promptFeedback": {"blockReason": "SAFETY"}}
    with mock_urlopen(blocked):
        with pytest.raises(ProviderHTTPError) as ei:
            llm.generate([Message.user("something")])
    assert "SAFETY" in str(ei.value)


def test_gemini_missing_key_raises_not_configured() -> None:
    with pytest.raises(ProviderNotConfigured):
        GeminiLLM()


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


def _sample_ollama_response(
    *,
    text: str = "hi",
    tool_calls: list[dict[str, Any]] | None = None,
    done_reason: str = "stop",
) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": text}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "model": "qwen2.5-coder:1.5b",
        "message": msg,
        "done_reason": done_reason,
        "done": True,
    }


def test_ollama_generate_uses_host_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "gpu01:9000")
    llm = OllamaLLM()
    with mock_urlopen(_sample_ollama_response(text="hi")) as m:
        llm.generate([Message.user("hi")])
    url = m.call_args.args[0].full_url
    assert url == "http://gpu01:9000/api/chat"


def test_ollama_404_gives_install_hint() -> None:
    import urllib.error

    llm = OllamaLLM()
    err = urllib.error.HTTPError(
        url="http://127.0.0.1:11434/api/chat",
        code=404,
        msg="Not Found",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b'{"error":"model not found"}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(OllamaConnectionError) as ei:
            llm.generate([Message.user("hi")])
    assert "ollama pull" in str(ei.value)


def test_ollama_tool_call_decoding() -> None:
    llm = OllamaLLM()
    response = _sample_ollama_response(
        text="",
        tool_calls=[
            {
                "id": "call_1",
                "function": {
                    "name": "read_file",
                    "arguments": {"path": "README.md"},
                },
            }
        ],
        done_reason="tool_calls",
    )
    with mock_urlopen(response):
        out = llm.generate([Message.user("read readme")])
    assert out.stop_reason is StopReason.TOOL_USE
    assert out.tool_calls[0].name == "read_file"
    assert out.tool_calls[0].args == {"path": "README.md"}


# ---------------------------------------------------------------------------
# Factory cascade
# ---------------------------------------------------------------------------


def test_known_llm_names_includes_every_backend() -> None:
    names = known_llm_names()
    # Alphabet soup that the --llm flag must accept.
    for required in (
        "auto",
        "mock",
        "anthropic",
        "gemini",
        "ollama",
        "openai",
        "openai-reasoning",
        "deepseek",
        "xai",
        "groq",
        "cerebras",
        "mistral",
        "openrouter",
        "lmstudio",
    ):
        assert required in names, f"{required!r} missing from known_llm_names()"


def test_build_llm_auto_raises_no_provider_configured_when_nothing_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """v2.1 behaviour: ``auto`` no longer silently downgrades to MockLLM.

    Pre-2.1 a missing API key returned a canned-output mock that *felt*
    like a working agent and made setup bugs invisible. The contract
    now is fail-loud: callers must catch :class:`NoProviderConfigured`
    and either prompt the user (``lyra connect``) or surface the
    actionable error message.
    """
    from lyra_cli.llm_factory import NoProviderConfigured

    # Tight isolation: a real user's ``~/.lyra/auth.json`` and a project-local
    # ``.env`` would otherwise resurrect a key and make the auto cascade pick a
    # provider, hiding the fail-loud contract behind environment leakage.
    for k in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "CEREBRAS_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "OLLAMA_HOST",
        "HARNESS_LLM_MODEL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_PROFILE",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "VERTEX_PROJECT",
        "GITHUB_TOKEN",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    with (
        patch("lyra_cli.llm_factory.ollama_reachable", return_value=False),
        patch(
            "lyra_cli.providers.openai_compatible._endpoint_reachable",
            return_value=False,
        ),
        pytest.raises(NoProviderConfigured),
    ):
        build_llm("auto")


def test_build_llm_auto_prefers_openai_when_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    with (
        patch("lyra_cli.llm_factory.ollama_reachable", return_value=True),
        patch(
            "lyra_cli.providers.openai_compatible._endpoint_reachable",
            return_value=True,
        ),
        # No Anthropic => stays in the OpenAI slot at the top of the
        # cascade.
        patch(
            "lyra_cli.llm_factory._anthropic_available", return_value=False
        ),
    ):
        llm = build_llm("auto")
    assert isinstance(llm, OpenAICompatibleLLM)
    assert llm.provider_name == "openai"


def test_build_llm_auto_prefers_anthropic_over_openai_when_deepseek_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anthropic still beats OpenAI in the auto cascade.

    DeepSeek now sits at slot 1 of the cascade (cost-aware default),
    but the *original* intent of this test — "Anthropic outranks
    OpenAI" — still holds when DeepSeek is unconfigured. We omit
    ``DEEPSEEK_API_KEY`` from the env to exercise that sub-cascade.
    See ``test_deepseek_default_priority`` for the DeepSeek-first
    contract that supersedes the previous "Anthropic-first" default.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    # No DEEPSEEK_API_KEY → cascade falls through to slot 2 (Anthropic).
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with patch(
        "lyra_cli.llm_factory._anthropic_available", return_value=True
    ):
        with patch("lyra_cli.llm_factory.AnthropicLLM") as klass:
            klass.return_value = "ANTHROPIC_INSTANCE"
            out = build_llm("auto")
    assert out == "ANTHROPIC_INSTANCE"


def test_build_llm_auto_prefers_deepseek_over_anthropic_when_both_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The new v2.1.x default: DeepSeek beats Anthropic in the auto cascade.

    Cost-aware default — paired with the user-facing change tracked
    in :file:`test_deepseek_default_priority.py`. Tested here too so
    a future cascade refactor that *moves Anthropic back to the
    head* trips both files at once.
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-ds")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    with patch(
        "lyra_cli.llm_factory._anthropic_available", return_value=True
    ):
        with patch("lyra_cli.llm_factory.AnthropicLLM") as klass:
            klass.return_value = "ANTHROPIC_INSTANCE"
            out = build_llm("auto")
    # DeepSeek wins → real OpenAICompatibleLLM, not the Anthropic mock.
    assert out != "ANTHROPIC_INSTANCE"
    assert getattr(out, "provider_name", None) == "deepseek"


def test_build_llm_explicit_groq_fails_loud_when_key_missing() -> None:
    # No GROQ_API_KEY in env (via _clean_env).
    with pytest.raises(ProviderNotConfigured):
        build_llm("groq")


def test_build_llm_explicit_ollama_fails_loud_when_daemon_down() -> None:
    with patch(
        "lyra_cli.llm_factory.ollama_reachable", return_value=False
    ):
        with pytest.raises(OllamaConnectionError):
            build_llm("ollama")


def test_build_llm_unknown_name_degrades_to_auto_then_raises() -> None:
    """Programmatic callers may pass garbage; we treat it as ``auto``.

    Under v2.1 ``auto`` raises :class:`NoProviderConfigured` when
    nothing is reachable, so the unknown-name path inherits that
    behaviour. Callers that want the old "always returns SOMETHING"
    semantics must pass ``"mock"`` explicitly.
    """
    from lyra_cli.llm_factory import NoProviderConfigured

    with (
        patch("lyra_cli.llm_factory.ollama_reachable", return_value=False),
        patch(
            "lyra_cli.providers.openai_compatible._endpoint_reachable",
            return_value=False,
        ),
        pytest.raises(NoProviderConfigured),
    ):
        build_llm("completely-made-up")


# ---------------------------------------------------------------------------
# describe_selection
# ---------------------------------------------------------------------------


def test_describe_selection_auto_with_nothing_configured() -> None:
    """v2.1: an unconfigured cascade describes itself honestly.

    Pre-2.1 the label leaked the word ``mock`` here, which the status
    bar happily showed to operators who'd just forgotten to set a key.
    The new label is short and points at the fix.
    """
    with (
        patch("lyra_cli.llm_factory.ollama_reachable", return_value=False),
        patch(
            "lyra_cli.providers.openai_compatible._endpoint_reachable",
            return_value=False,
        ),
    ):
        label = describe_selection("auto")
    assert label.startswith("unconfigured")
    assert "lyra connect" in label or "API key" in label


def test_describe_selection_auto_with_groq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    with patch(
        "lyra_cli.llm_factory._anthropic_available", return_value=False
    ):
        label = describe_selection("auto")
    assert label.startswith("groq · ")
    assert "llama-3.3-70b" in label


def test_describe_selection_gemini_with_custom_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("OPEN_HARNESS_GEMINI_MODEL", "gemini-2.5-flash")
    assert describe_selection("gemini") == "gemini · gemini-2.5-flash"


def test_describe_selection_ollama_shows_local_tag() -> None:
    label = describe_selection("ollama")
    assert label.startswith("ollama · ")
    assert "(local)" in label


def test_describe_selection_lmstudio_shows_local_tag() -> None:
    label = describe_selection("lmstudio")
    assert label.startswith("lmstudio · ")
    assert "(local)" in label
