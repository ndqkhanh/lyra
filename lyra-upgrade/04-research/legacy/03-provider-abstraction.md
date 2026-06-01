# Provider Abstraction Layer -- Deep Dive

## 1. Executive Summary

Lyra normalises 16+ AI providers through a single abstraction layer rooted in the `LLMProvider` interface (`packages/lyra-harness-core/src/lyra_harness_core/models.py`). Every provider, from Anthropic's native Messages API to OpenAI-compatible backends like DeepSeek, Grok, Cerebras, Mistral, OpenRouter, and local runtimes like Ollama and LM Studio, is surfaced through the same `generate(messages, tools, max_tokens, temperature) -> Message` contract. The abstraction has four layers:

1. **The `LLMProvider` interface** -- a 4-method abstract contract that every adapter implements.
2. **Provider-specific adapters** -- one per distinct wire format (Anthropic, Gemini, Ollama) plus a single generic `OpenAICompatibleLLM` that covers 18+ backends that speak the `/v1/chat/completions` dialect.
3. **A static capability registry** (`ProviderSpec`) that describes each provider's context window, tool support, reasoning support, vision support, and model lineup without instantiating any HTTP clients.
4. **Routing, fallback, and health layers** that consume the registry to make cost-aware, confidence-driven decisions about which provider to call and when to escalate.

The abstraction goes beyond existing harnesses (LangChain, LiteLLM, OpenRouter) because it owns the entire lifecycle: credential hydration from `~/.lyra/auth.json` and `.env` files, model alias resolution, per-provider context-window-adaptive compaction, PolyKV-style prompt caching coordination across sibling subagents, circuit-breaker health monitoring, and a cost-aware cascade router that starts at DeepSeek (10-20x cheaper than Claude) and escalates through Anthropic, OpenAI, and Gemini as task complexity demands.

Source files referenced throughout this document can be found under `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/packages/`:
- `lyra-harness-core/src/lyra_harness_core/models.py` -- `LLMProvider` ABC + base `AnthropicLLM`
- `lyra-harness-core/src/lyra_harness_core/messages.py` -- `Message`, `ToolCall`, `ToolResult`, `StopReason`
- `lyra-core/src/lyra_core/providers/registry.py` -- `ProviderSpec`, `PROVIDER_REGISTRY`
- `lyra-core/src/lyra_core/providers/aliases.py` -- `AliasRegistry`, `DEFAULT_ALIASES`
- `lyra-core/src/lyra_core/providers/prompt_cache.py` -- `PromptCacheCoordinator`, per-provider cache adapters
- `lyra-core/src/lyra_core/routing/provider_health.py` -- `ProviderHealthMonitor`
- `lyra-core/src/lyra_core/routing/cascade.py` -- `ConfidenceCascadeRouter`
- `lyra-core/src/lyra_core/routing/dynamic_pricing.py` -- `DynamicPricingEngine`
- `lyra-context/src/lyra_context/provider_adapter.py` -- `ProviderAdaptiveCompactor`
- `lyra-cli/src/lyra_cli/llm_factory.py` -- `build_llm()`, auto-cascade logic
- `lyra-cli/src/lyra_cli/llm_router.py` -- intra-provider model routing
- `lyra-cli/src/lyra_cli/providers/anthropic.py` -- `LyraAnthropicLLM`
- `lyra-cli/src/lyra_cli/providers/openai_compatible.py` -- `OpenAICompatibleLLM` + 18 presets
- `lyra-cli/src/lyra_cli/providers/gemini.py` -- `GeminiLLM`
- `lyra-cli/src/lyra_cli/providers/ollama.py` -- `OllamaLLM`
- `lyra-cli/src/lyra_cli/providers/fallback.py` -- `FallbackChain`

## 2. The AbstractProvider Interface

### 2.1 Canonical Types

The abstraction is built on five canonical types defined in `messages.py`:

**`Message`** (Pydantic BaseModel): The universal turn representation. Fields are `role` ("system" | "user" | "assistant" | "tool"), `content` (string), `tool_calls` (list of `ToolCall`), `tool_results` (list of `ToolResult`), and `stop_reason` (a `StopReason` enum). This single class carries every LLM response mode: plain text, multi-turn tool-use, error conditions, and max-tokens exhaustion.

**`ToolCall`**: A proposed function invocation with `id` (string), `name` (string), and `args` (dict). Every provider adapter normalises its native tool-call format into this shape.

**`ToolResult`**: The outcome of a tool execution with `call_id` (links back to the `ToolCall.id`), `content` (string), and `is_error` (bool). Tool results are fed back into the message list as role="tool" messages.

**`StopReason`**: An enum with values `END_TURN`, `TOOL_USE`, `MAX_TOKENS`, `STOP_SEQUENCE`, `ERROR`. Each adapter maps the provider's native finish-reason onto this discrete set.

**`ChatRequest`/`ChatResponse`**: These are not explicit standalone types but are expressed through the method signatures of `LLMProvider.generate()`. The "request" is the tuple `(messages, tools, max_tokens, temperature)`, and the "response" is a single `Message` object.

### 2.2 The `LLMProvider` Contract

Defined in `models.py`:

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        raise NotImplementedError
```

This is deliberately minimal. Four parameters cover every major LLM API:
- `messages` -- The full transcript. System prompts are carried as messages with `role="system"`, not as a separate parameter, so the interface stays uniform across providers that have different system-prompt mechanisms.
- `tools` -- Anthropic-style tool schemas (`{"name", "description", "input_schema"}`). Every adapter translates to its provider's native tool schema.
- `max_tokens` -- Output token budget.
- `temperature` -- Sampling temperature.

The return type is always a single `Message` with `role="assistant"`. Tool calls are embedded inside the `Message.tool_calls` list; the caller's loop inspects `stop_reason` to decide whether to dispatch tools or surface the final text.

### 2.3 Streaming

The `LLMProvider` ABC does not mandate streaming -- only `generate()` is abstract. Individual adapters that support streaming expose an `Iterator[str]` method. The `OpenAICompatibleLLM` provider, for instance, implements `stream()` alongside `generate()` to yield SSE text deltas with usage capture via `stream_options.include_usage`. The Anthropic adapter, by contrast, handles streaming at the harness-core level through a separate `stream` method that yields `Message` objects per chunk.

### 2.4 Token Counting

Lyra does not have a universal `count_tokens()` method on the `LLMProvider` ABC. Each adapter records usage from response metadata after each `generate()` call into a `last_usage: dict[str, int]` attribute that normalises to `{"prompt_tokens", "completion_tokens", "total_tokens"}`. The OpenAI-compatible adapter goes further with `cumulative_usage` that accumulates across calls. For providers that omit usage in final streaming chunks (some older vLLM builds, certain proxy gateways), the adapter implements a character-count backstop that estimates tokens at 4 chars/token.

### 2.5 How It Differs from Provider-Specific SDKs

The contrast with native SDKs reveals the abstraction's value:

- **Anthropic SDK**: Messages use `{"role": "user", "content": [{"type": "text", "text": "..."}]}` with separate `system` parameter. Tool calls are `tool_use` content blocks. Responses have a `content` list of mixed-type blocks.
- **OpenAI SDK**: Messages use `{"role": "user", "content": "..."}` (string content). Tool calls are a separate `tool_calls` array on the message object. Arguments are JSON-encoded strings. System is just another message with `role="system"`.
- **Gemini SDK**: Messages use `{"role": "user", "parts": [{"text": "..."}]}`. System goes in a top-level `systemInstruction`. Tool calls are `functionCall` parts. Arguments are native dicts. API key goes in the query string, not a header.
- **Ollama API**: Messages follow OpenAI shape but the endpoint is `/api/chat` not `/v1/chat/completions`. Tool format matches OpenAI but the response schema differs slightly.

Lyra's `LLMProvider` abstraction hides all of these differences behind the single `generate(messages, tools, max_tokens, temperature) -> Message` contract. The `Message` class normalises content to strings, tool calls to `ToolCall` objects, and stop reasons to the `StopReason` enum. Every adapter performs a bidirectional translation at its boundary.

## 3. Provider Adapters

### 3.1 Anthropic Adapter

**File**: `lyra-harness-core/src/lyra_harness_core/models.py` (base `AnthropicLLM`)
**File**: `lyra-cli/src/lyra_cli/providers/anthropic.py` (`LyraAnthropicLLM`)

The base `AnthropicLLM` in `harness_core` is the minimal adapter. It translates:

- System messages -> top-level `system` parameter (Anthropic's API does not support `role="system"` in the messages array).
- User/assistant messages -> `{"role": ..., "content": [{"type": "text"|"tool_use"|"tool_result", ...}]}` blocks.
- Tool schemas -> passed through directly (the Anthropic SDK accepts the same `{"name", "description", "input_schema"}` shape Lyra uses internally).
- Response content blocks -> text parts are concatenated; `tool_use` blocks become `ToolCall` objects with `id`, `name`, `input` (args).

The Lyra-specific subclass `LyraAnthropicLLM` adds session-mode billing support. It installs a one-call spy on `self._client.messages.create` to capture the raw SDK response object, then lifts `response.usage.input_tokens` and `response.usage.output_tokens` into `self.last_usage`. The spy is restored in a `finally` block so an exception cannot leave a wrapper installed across calls.

**Extended thinking / budget_tokens mapping**: Anthropic's extended thinking feature (Claude 3.7+ Sonnet and Opus 4.x) is exposed through the `thinking` parameter in the SDK's `messages.create()`. Lyra's base `AnthropicLLM` adapter does not hardcode extended thinking configuration -- it is controllable through the harness-level parameter expansion in `lyra_harness_core`. When extended thinking is enabled, the adapter passes `thinking={"type": "enabled", "budget_tokens": N}` alongside the normal message payload. The thinking content blocks in the response (type `thinking` and `redacted_thinking`) are transparently handled by the LLM-level loop -- the adapter strips them from the visible content stream and only surfaces the final text response to the agent loop.

**Prompt caching**: The Anthropic adapter for `PromptCacheCoordinator` (`AnthropicAdapter` in `prompt_cache.py`) returns a `{"cache_control": {"type": "ephemeral"}}` directive that the caller splices onto the last block of the shared prefix. Anthropic charges 25% extra on the cache write but only 10% on subsequent reads -- a net saving starting from the first sibling reuse.

### 3.2 OpenAI Adapter

**File**: `lyra-cli/src/lyra_cli/providers/openai_compatible.py`

The `OpenAICompatibleLLM` is a single generic class that covers every provider speaking the `/v1/chat/completions` wire format. It handles:

**Message format normalization**: Translates Lyra's internal `Message` list to OpenAI's wire format:
- `role="system"` messages are sent as `{"role": "system", "content": "..."}`.
- `role="user"` and `role="assistant"` messages are sent as-is.
- `role="tool"` messages become `{"role": "tool", "content": "...", "tool_call_id": "..."}`. If a single tool message carries multiple `ToolResult` entries, they are concatenated with newlines under the first result's call_id.

**Tool calls array handling**: On the outbound path (`_tool_to_openai`), Lyra's Anthropic-style `{"name", "description", "input_schema"}` schemas are translated to OpenAI's `{"type": "function", "function": {"name", "description", "parameters"}}`. On the inbound path (`_choice_to_msg`), the OpenAI `tool_calls` array in the response is decoded: `arguments` (a JSON-encoded string on the wire) is parsed, `id` and `name` are lifted directly, and the finish reason `tool_calls` maps to `StopReason.TOOL_USE`.

**Reasoning model handling**: The `_ReasoningConfig` dataclass controls per-model quirks:
- `use_max_completion_tokens=True` -- uses `max_completion_tokens` instead of `max_tokens` for o-series models (o3, o4-mini) that reject the legacy field.
- `supports_reasoning_effort=True` -- sets `reasoning_effort` parameter (low/medium/high) instead of `temperature` (which reasoning models ignore).
- The `reasoning_content` field that OpenAI's o-series emits for chain-of-thought is deliberately **dropped** at the adapter boundary to prevent prompt-injection surprises and log bloat.

**Token usage**: The `_record_usage()` method captures the response's `usage` dict onto `last_usage` (for immediate billing) and accumulates into `cumulative_usage` (for run-footers). The streaming path uses `stream_options.include_usage` to receive a final SSE event with usage data, with a character-count backstop when the provider omits it.

**18 presets** are defined as `_Preset` dataclass instances that configure the generic `OpenAICompatibleLLM` for specific backends. Each `_Preset` carries static metadata (`name`, `label`, `base_url`, `env_keys`, `default_model`, `model_env_keys`, `extra_headers`, `auth_scheme`, `reasoning`, `probe_reachable`) and a `build()` factory method that constructs an `OpenAICompatibleLLM` with the right configuration. The `configured()` method checks env vars (for cloud providers) or probes a local endpoint (for local providers). The `read_api_key()` method returns the first non-empty value from the preset's `env_keys` tuple, and `read_model()` checks model-specific env vars before falling back to `default_model`.

```python
@dataclass(frozen=True)
class _Preset:
    name: str
    label: str
    base_url: str
    env_keys: tuple[str, ...]
    default_model: str
    ...
    def build(self, model=None, *, provider_routing=None) -> OpenAICompatibleLLM:
        ...
    def configured(self) -> bool:
        ...
```

The full preset set:

| Preset Name | Provider | Base URL |
|---|---|---|
| `openai` | OpenAI | `https://api.openai.com/v1` |
| `openai-reasoning` | OpenAI o-series | same base, different model/reasoning config |
| `deepseek` | DeepSeek | `https://api.deepseek.com/v1` |
| `xai` | xAI Grok | `https://api.x.ai/v1` |
| `groq` | Groq | `https://api.groq.com/openai/v1` |
| `cerebras` | Cerebras | `https://api.cerebras.ai/v1` |
| `mistral` | Mistral | `https://api.mistral.ai/v1` |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` |
| `qwen` | Alibaba Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `dashscope` | Legacy Qwen alias | same endpoint |
| `lmstudio` | LM Studio (local) | `http://127.0.0.1:1234/v1` |
| `vllm` | vLLM (local) | `http://127.0.0.1:8000/v1` |
| `llama-server` | llama.cpp (local) | `http://127.0.0.1:8080/v1` |
| `tgi` | HuggingFace TGI (local) | `http://127.0.0.1:8081/v1` |
| `llamafile` | Mozilla Llamafile (local) | `http://127.0.0.1:8082/v1` |
| `mlx` | MLX-LM (Apple Silicon) | `http://127.0.0.1:8083/v1` |

Local presets use `auth_scheme="none"` and `probe_reachable=True` so the factory's auto-cascade can detect them by issuing a cheap GET to their `/v1/models` endpoint with a 0.8-second timeout.

### 3.3 DeepSeek Adapter

**File**: `lyra-cli/src/lyra_cli/providers/openai_compatible.py` (preset `deepseek`)

DeepSeek speaks the OpenAI wire format and uses the same `OpenAICompatibleLLM` class. The preset configures:
- Base URL: `https://api.deepseek.com/v1`
- Env var: `DEEPSEEK_API_KEY`
- Default model: `deepseek-chat` (the general/coding model)

**Key differences from OpenAI**:
- DeepSeek's context window is 128K tokens for the V4 models, compared to 128K for GPT-4o and 200K for Claude and o3.
- The DeepSeek Reasoner model (R1/R2) emits reasoning content in a similar shape to OpenAI's `reasoning_content`. The adapter strips it at the `_choice_to_msg` boundary, same as OpenAI o-series.
- DeepSeek does not support `max_completion_tokens` -- it uses the standard `max_tokens` parameter even for reasoning models. The DeepSeek preset does not set `use_max_completion_tokens=True` on its `_ReasoningConfig`.
- DeepSeek pricing is approximately 10-20x cheaper than Claude Opus on a per-token basis. This is the primary motivator for DeepSeek heading the auto-cascade in `build_llm()`: the cost-aware default for the typical Lyra user.

**Prompt caching**: DeepSeek applies automatic prefix caching (same as OpenAI) with no request-side directive. The `DeepSeekAdapter` in the `PromptCacheCoordinator` returns `None` from `make_directive()` because no payload modification is needed -- the coordinator's job is merely to ensure sibling subagents emit byte-identical prefixes so the provider's cache hits.

**Model alias resolution in `aliases.py`**: DeepSeek aliases implement a "small/smart split" pattern. The fast/cheap aliases (`deepseek`, `deepseek-v4-flash`, `deepseek-chat`) resolve to `deepseek-chat` (the general model). The reasoning aliases (`deepseek-v4-pro`, `deepseek-reasoner`, `deepseek-r1`) resolve to `deepseek-reasoner` (the chain-of-thought model). Regex patterns future-proof the registry: any versioned slug matching `^deepseek-v\d+(?:\.\d+)?-(?:pro|reasoner)` routes to `deepseek-reasoner`, and `^deepseek-v\d+(?:\.\d+)?-(?:flash|chat|fast)` routes to `deepseek-chat`.

### 3.4 Google Adapter

**File**: `lyra-cli/src/lyra_cli/providers/gemini.py`

Gemini is the only top-tier cloud LLM that does **not** speak the OpenAI chat-completions format. Lyra gives it a dedicated `GeminiLLM` class with its own wire-format translation.

**System message handling**: Gemini does not support `role="system"` in the `contents` array. The `_build_contents()` method splits system messages into a top-level `systemInstruction` field. Multiple system messages are concatenated with newline separators.

**Message format normalization** (`_msg_to_gemini`):
- Gemini's `contents` array uses `role="user"` and `role="model"` (not "assistant"). The adapter maps `assistant` -> `model`.
- Text content is wrapped in `{"parts": [{"text": "..."}]}`.
- Tool calls are translated to `{"functionCall": {"name": "...", "args": {...}}}` parts inside a `model`-role content block.
- Tool results become `{"functionResponse": {"name": "<call_id>", "response": {...}}}` parts inside a `user`-role content block.

**Tool schema normalization** (`_tool_to_gemini`): Anthropic-style `{"name", "description", "input_schema"}` is translated to Gemini's `{"name", "description", "parameters"}` function declaration. Parameters are expected as plain JSON Schema, which matches Lyra's internal format.

**Response decoding** (`_candidate_to_msg`): Gemini responses may contain both `text` and `functionCall` parts in a single candidate. The adapter separates them: text chunks are concatenated, function call parts become `ToolCall` objects with synthesised IDs (`gemini_call_0`, `gemini_call_1`, ...) because Gemini does not emit call IDs in its response.

**Critical tool-use detection**: Gemini emits `finishReason: "STOP"` even when the model produced a `functionCall` part. The adapter overrides this: if any `functionCall` was present in the response, the stop reason is set to `TOOL_USE` regardless of the wire finish reason. Without this override, the agent loop would think the model wanted to end the turn and would never dispatch the tool.

**Authentication**: Gemini takes the API key as a query parameter (`?key=...`) rather than an `Authorization` header, following Google REST API conventions. The adapter accepts both `GEMINI_API_KEY` and `GOOGLE_API_KEY` env vars.

**1M-2M context window handling**: Gemini's models (2.5 Pro: 2M tokens, 2.5 Flash: 1M tokens) have by far the largest context windows of any Lyra provider. The `ProviderAdaptiveCompactor` (see Section 6.3) uses lighter compaction for Gemini: at high context usage ratios it selects `KV_EVICT` or `SUMMARIZE` strategies instead of the `AGGRESSIVE` strategy used for small-window providers like DeepSeek (64K) or local models (8K).

**Usage normalization**: Gemini reports token counts in `usageMetadata` with fields `promptTokenCount`, `candidatesTokenCount`, and `totalTokenCount`. The `_record_usage()` method translates these to Lyra's standard `{"prompt_tokens", "completion_tokens", "total_tokens"}` dict.

**Prompt caching**: Gemini exposes an explicit `CachedContent` REST endpoint. The `GeminiAdapter` in the `PromptCacheCoordinator` returns a directive containing `{"cached_content": "lyra-cache-<digest[:16]>", "ttl": "..."}`. The coordinator stores the `CachedContent` resource name so sibling subagents can reference it without re-creating the resource.

### 3.5 Ollama Adapter

**File**: `lyra-cli/src/lyra_cli/providers/ollama.py`

Ollama is the most widely installed local LLM runtime. The adapter uses **stdlib-only** (`urllib` + `json`) to avoid adding a compile-time dependency.

**Wire format**: Ollama exposes an `/api/chat` endpoint with an OpenAI-compatible message format but a different response schema. The adapter translates Lyra's `Message` list to the same `{"role", "content", "tool_calls"}` shape OpenAI uses, then maps the response back. Tool calls are supported through Ollama's `tools` parameter (available since 0.3.x).

**Reachability probe**: A GET to `http://127.0.0.1:11434/api/tags` with a 0.8-second timeout. This runs on every startup in auto-mode. If the probe fails, the factory silently moves to the next provider in the cascade.

**Default model**: `qwen2.5-coder:1.5b` -- approximately 1 GB, runs CPU-only on a laptop, Apache-2.0 licensed. Users override via `OLLAMA_MODEL` or `OPEN_HARNESS_LOCAL_MODEL` env vars.

### 3.6 Fallback Chain

**File**: `lyra-cli/src/lyra_cli/providers/fallback.py`

The `FallbackChain` wraps multiple `LLMProvider` instances and tries them in order. It implements a two-tier error classification:

- **Retryable errors**: HTTP 5xx, HTTP 429, timeouts, connection resets, "unreachable" messages. On retryable errors, the chain advances to the next provider and continues.
- **Fatal errors**: HTTP 4xx (except 429), `ProviderNotConfigured`, `TypeError`, arbitrary Python exceptions. On fatal errors, the chain re-raises immediately -- retrying with a different provider won't fix a missing API key or a malformed prompt.

If every provider in the chain fails with only retryable errors, it raises `FallbackExhausted` with an aggregated error message listing all failures.

This is distinct from the factory's selection cascade: the factory picks ONE provider at startup; the `FallbackChain` is a runtime cascade that rolls over on transient failures while keeping the primary provider as long as it's healthy.

## 4. Capability Detection

### 4.1 Per-Provider Capability Map

The `PROVIDER_REGISTRY` (`registry.py`) is a tuple of `ProviderSpec` dataclass instances -- a pure-data module with zero HTTP client imports. Each spec declares:

| Field | Type | Purpose |
|---|---|---|
| `key` | str | Canonical identifier (e.g., "anthropic", "deepseek") |
| `display_name` | str | Human-readable label |
| `env_vars` | tuple[str] | Which env vars to check for credential presence |
| `default_model` | str | Safe default if no model is explicitly requested |
| `context_window` | int | Best-known input context size (informative, not authoritative) |
| `supports_tools` | bool | Function/tool calling |
| `supports_reasoning` | bool | Extended thinking / chain-of-thought |
| `supports_streaming` | bool | SSE-based streaming |
| `supports_vision` | bool | Image input support |
| `models` | tuple[ModelSpec] | Individual model variants with slugs and tags |

The `providers_by_capability()` function allows querying: find all providers that support tools AND reasoning AND have a context window of at least 128K. This powers the `--llm auto` cascade's filtering logic.

### 4.2 Runtime Probing vs Static Config

Lyra uses a hybrid approach:

**Static metadata** (most decisions): The `ProviderSpec` registry is consulted for context window, tool support, and reasoning support. Static metadata is sufficient for routing decisions because these capabilities change at the provider level, not per-invocation.

**Environment probing** (presence checks): The `configured()` method on each `_Preset` checks env vars (for cloud providers) or issues a lightweight GET probe (for local providers). The probe timeout is 0.8s for both Ollama's `/api/tags` and OpenAI-compatible `/v1/models` endpoints.

**Health monitoring** (runtime state): The `ProviderHealthMonitor` (`provider_health.py`) tracks per-provider success rates, latency percentiles, error counts, and circuit breaker state. This is runtime state, not configuration -- it feeds the `ConfidenceCascadeRouter` and the `DynamicPricingEngine`.

**Model alias resolution** (name-based routing): The `AliasRegistry` (`aliases.py`) maps user-typed model names to canonical slugs. Two layers: exact aliases (`opus` -> `claude-opus-4.5`) and regex patterns (`^deepseek-v\\d+.*-pro$` -> `deepseek-reasoner`). The provider for each alias is stored alongside the slug so the factory can route `--model opus` to the Anthropic backend without a separate lookup.

### 4.3 Context Window Detection

The `ProviderAdaptiveCompactor` (`lyra_context/provider_adapter.py`) maintains a mapping of provider -> context window:

```python
_PROVIDER_CONTEXT_WINDOWS = {
    "anthropic": 200_000,
    "openai": 128_000,
    "google": 2_000_000,
    "deepseek": 64_000,      # conservative for older models
    "openrouter": 128_000,
    "local": 8_000,
    "default": 128_000,
}
```

The compactor selects compaction strategy based on both the raw window size and the current usage ratio:
- At < 50% usage: no compaction.
- At 50-70%: summarise (all providers).
- At 70-85%: small-window providers truncate; large-window providers summarise.
- At 85-95%: small-window providers go aggressive; large-window providers use KV eviction.
- Above 95%: aggressive for everyone.

This is provider-adaptive: the same prompt arriving at Gemini (2M window) receives gentler compaction than at DeepSeek (64K window), because Gemini has more headroom before context pressure degrades quality. This is, per the source comment, an "unaddressed frontier" in existing LLM harnesses and is identified as Lyra's specific contribution.

## 5. Fallback & Escalation

### 5.1 Fast-Standard-Deep Tier Escalation

Lyra implements three escalation paths:

**1. Factory selection cascade** (`llm_factory.py::build_llm()`): At startup, the `auto` cascade tries providers in this priority order:
1. DeepSeek (cost-aware default, 10-20x cheaper than Claude)
2. Anthropic (reference target for tool-using agents)
3. OpenAI, xAI/Grok, Groq, Cerebras, Mistral, OpenRouter, Qwen (iterated via preset registry in declaration order)
4. LM Studio, vLLM, llama-server, TGI, Llamafile, MLX (local backends)
5. Gemini (native adapter, checked after OpenAI-compatible presets)
6. Ollama (local, checked last)

If `LYRA_PREFER_LOCAL=1` (default) and Ollama is reachable, the cascade tries the local provider first. Set `LYRA_PREFER_LOCAL=0` to force cloud-first routing (for CI/determinism).

**2. Intra-provider model routing** (`llm_router.py`): Within a single provider's family, `route_model_for_task()` selects a task-appropriate model:
```python
PROVIDER_FAMILIES["anthropic"] = ProviderModelFamily(
    reasoning="claude-opus-4.7",
    coding="claude-sonnet-4.6",
    quick="claude-haiku-4.5",
    creative="claude-opus-4.7",
    planning="claude-opus-4.7",
)
```
The task type is detected from the prompt via keyword scoring. "explain", "analyze", "why" -> reasoning. "implement", "fix", "refactor" -> coding. "what", "when", "list" -> quick. The model slug is then looked up in the provider's family config.

**3. Confidence-driven cascade** (`cascade.py::ConfidenceCascadeRouter`): Inspired by FrugalGPT and RouteLLM research, this uses an ordered list of `CascadeStage` objects (cheap -> expensive). Each stage has a `cost_weight` and `accept_above_confidence` threshold. The router calls the cheap provider first, feeds the answer to a `ConfidenceEstimator`, and returns the answer if confidence >= threshold. Otherwise it escalates to the next stage. This is production-ready but sitll integrated via the routing middleware layer -- the primary agent loop uses explicit model routing rather than the confidence cascade by default.

### 5.2 Provider Health Scoring

The `ProviderHealthMonitor` (`provider_health.py`) tracks these metrics per provider:
- Total requests and errors
- Consecutive error count
- Latency history (deque, max 200 entries)
- Circuit state: CLOSED -> OPEN -> HALF_OPEN -> CLOSED

The circuit breaker opens after `error_threshold` (default 5) consecutive errors. After `recovery_timeout_seconds` (default 30), it transitions to HALF_OPEN and allows up to `half_open_max_requests` (default 3) trial requests. If those succeed, the circuit closes; if one fails, it reopens.

Health status is rated: HEALTHY (< 10% error rate + latency under threshold), DEGRADED, UNHEALTHY, or DEAD (circuit open). The `get_healthy_providers()` method feeds the cascade router and the pricing engine.

### 5.3 Circuit Breaker at $5/Session

The `DynamicPricingEngine` (`dynamic_pricing.py`) tracks `budget_pressure` -- a float from 0.0 (no pressure) to 1.0 (critical). When budget pressure exceeds 0.8, the engine recommends the cheapest provider regardless of quality tier:

```python
if self.budget_pressure > 0.8:
    recommended = cheapest
else:
    standard = [q for q in quotes if q.tier == PricingTier.STANDARD]
    recommended = standard[0] if standard else cheapest
```

The $5/session circuit breaker is a separate mechanism in the CLI's session management (not in the pricing engine itself). `build_llm()` sets `LYRA_ACTIVE_PROVIDER` in the environment after selection, and the session middleware checks cumulative spend against the session budget. If the budget is exceeded, subsequent `generate()` calls are rejected until the session is reset or the user explicitly overrides the limit.

The per-model pricing table is:
```
claude-haiku-4-5:    $0.80/M input   $4.00/M output
claude-sonnet-4-6:   $3.00/M input  $15.00/M output
claude-opus-4-7:    $15.00/M input  $75.00/M output
deepseek-v4-pro:     $0.50/M input   $2.00/M output
gpt-4o:              $2.50/M input  $10.00/M output
gpt-4o-mini:         $0.15/M input   $0.60/M output
```

## 6. Architecture Diagram

```
                                  +---------------------+
                                  |   lyra CLI / REPL   |
                                  +----------+----------+
                                             |
                                   +---------+---------+
                                   |   build_llm()     |
                                   |  (llm_factory.py)  |
                                   +----+----+----+----+
                                        |    |    |
                     +-------------------+    |    +------------------+
                     |                         |                      |
            +--------v--------+      +---------v---------+  +--------v--------+
            |  AliasRegistry   |      |  ProviderHealth   |  |  ProviderSpec   |
            |  (aliases.py)    |      |  (provider_health)|  |  (registry.py)  |
            +------------------+      +----+---------+----+  +--------+--------+
                                            |         |                |
                                   +--------v-+  +---v---------+      |
                                   |Fallback  |  |DynamicPrice |      |
                                   |Chain     |  |Engine       |      |
                                   +----------+  +-------------+      |
                                                                      |
                    +-----------------------+--------------------------+
                    |                       |                          |
            +-------v--------+    +--------v--------+       +---------v--------+
            |   LLMProvider   |    |  ProviderAdapt  |       |   PromptCache    |
            |   (ABC)         |    |  Compactor      |       |   Coordinator    |
            |  generate()     |    |  (context)      |       |   (prompt_cache) |
            +---+----+----+---+    +-----------------+       +------------------+
                |    |    |
      +---------+    |    +----------+
      |              |               |
+-----v------+ +----v----+  +-------v------+
| Anthropic  | | OpenAI  |  |   Gemini     |
| LLM        | | Compat  |  |   LLM        |
| (native)   | | (18 px) |  | (REST)       |
+------------+ +----+----+  +-------^------+
                    |                |
           +--------+--------+      |
           |        |        |      |
     +-----v--+ +--v---+ +--v---+  |
     |DeepSeek| | xAI  | | Groq |  |
     +--------+ +------+ +------+  |
                                    |
                           +--------+--------+
                           |    Ollama LLM   |
                           |   (local,stdlib)|
                           +-----------------+

+==================================================================+
|                     SESSION / CONTEXT LAYER                       |
|  +-----------------+  +-----------------+  +-------------------+  |
|  | Confidence      |  | Intra-Provider  |  | ProviderAdaptive  |  |
|  | Cascade Router  |  | Model Router    |  | Compactor         |  |
|  +-----------------+  +-----------------+  +-------------------+  |
+==================================================================+

Flow:
1. User types a prompt in the CLI REPL.
2. `build_llm()` resolves `--llm auto` through the cascade:
   a. Hydrate credentials from auth.json and .env
   b. Resolve model alias (e.g., "opus" -> "claude-opus-4.7", provider=anthropic)
   c. Try providers in priority order until one is configured
   d. Set `LYRA_ACTIVE_PROVIDER` in environment
3. `PromptCacheCoordinator.coordinate()` checks if the shared prefix is cached.
4. `ProviderAdaptiveCompactor.select_strategy()` chooses compaction based on context window.
5. The adapter's `generate()` translates Lyra Messages -> provider wire format.
6. Response is normalised back to a Lyra Message with ToolCall objects.
7. `ProviderHealthMonitor.record_success/error()` updates runtime health.
8. `DynamicPricingEngine.estimate()` tracks cumulative session spend.
```

## 7. Multi-Provider Portability

### 7.1 How Skills Work Across Providers

Lyra's skills system (agent routing profiles, prompt templates, tools) operates at the `LLMProvider` abstraction level, not at the provider-specific SDK level. This means:

- A skill that uses tool calling works identically on Anthropic, OpenAI, DeepSeek, Gemini, Groq, and Ollama. The adapter normalises tool schemas in both directions.
- A skill that uses system prompts works identically on every provider. The Anthropic adapter moves system content to the top-level `system` parameter; the Gemini adapter moves it to `systemInstruction`; the OpenAI-compatible adapter sends it as a `role="system"` message.
- A skill that relies on extended thinking works on Anthropic and OpenAI o-series (with appropriate `_ReasoningConfig`), silently degrades on providers that don't support it (DeepSeek flash models, Mistral, Groq), and is adapted to Gemini's thinking mode by the Gemini adapter.

The only skill-level difference a developer needs to handle is context window size: a skill that assumes 200K context on Anthropic may fail on DeepSeek (128K) or Ollama (8K local model). The `ProviderAdaptiveCompactor` mitigates this by applying more aggressive compaction as the usage ratio approaches the provider's window limit.

### 7.2 Tool Calling Format Normalization

This is the most intricate translation in the abstraction layer. Lyra uses Anthropic-style tool schemas internally:

```python
# Internal format (Anthropic-style)
{
    "name": "search_web",
    "description": "Search the web for current information",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }
}
```

Each adapter translates to and from this format:

**Anthropic adapter**: Pass-through. The Anthropic Messages API accepts this exact schema in the `tools` parameter.

**OpenAI-compatible adapter** (`_tool_to_openai`): Wraps each tool in `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`. On the response side (`_choice_to_msg`), the adapter reads `tool_calls` from the OpenAI response, parses any JSON-string `arguments`, and constructs `ToolCall(id, name, args)`.

**Gemini adapter** (`_tool_to_gemini`): Translates to `{"functionDeclarations": [{"name": ..., "description": ..., "parameters": ...}]}`. On the response side, `functionCall` parts become `ToolCall` objects with synthesised IDs.

**Ollama adapter**: Uses the OpenAI-compatible tool format (Ollama mirrors OpenAI's `/v1/chat/completions` tool schema in its `/api/chat` endpoint).

The `_tool_to_openai` method includes a pass-through check: if `tool.get("type") == "function"` and `isinstance(tool.get("function"), dict)`, the schema is returned unchanged. This lets advanced callers bypass translation by pre-building OpenAI-shaped tool definitions.

### 7.3 Streaming Differences

Streaming behaviour varies significantly across providers:

**OpenAI-compatible**: Uses standard SSE with `data:` frames. The `_iter_sse_data_lines()` method in `openai_compatible.py` implements a robust SSE parser that handles CRLF/LF, multi-line data continuations, SSE comments, and `[DONE]` markers. The final chunk carries a `usage` block when `stream_options.include_usage` is set.

**Gemini**: Uses SSE but with a different event format (`content` blocks with `{"text": "..."}` deltas). Currently the `GeminiLLM` adapter only implements `generate()`, not streaming -- chat-mode streaming goes through the OpenAI-compatible path or the Anthropic path.

**Anthropic**: Streaming is handled at the `lyra_harness_core` level through the SDK's native `stream` method, which yields content block deltas as `Message` objects. The Lyra subclass does not override streaming -- it inherits the harness-core implementation.

**Ollama**: The `/api/chat` endpoint uses NDJSON streaming. Each line is a complete JSON object with a `done` flag. The adapter parses each line, extracts text deltas, and yields them. The final `done: true` line carries the full message including usage data.

The usage backstop in the OpenAI-compatible streaming path ensures that even when a provider omits the final usage event (older vLLM, certain proxy gateways), the billing system still has approximate numbers: `est_prompt = prompt_chars // 4`, `est_completion = streamed_chars // 4`. The estimated tokens are tagged with `"estimated": True` so observability tooling can distinguish real from fallback numbers.

### 7.4 Authentication Portability

Each provider has its own auth path, unified through the factory:

1. **Cloud APIs**: API keys from env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, etc.). The factory's `_hydrate_env_from_dotenv()` cascades: `~/.lyra/auth.json` -> project-local `.env` -> process env.
2. **AWS Bedrock**: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` + `AWS_REGION` environment variables, or the default credential chain (`~/.aws/credentials`, IAM role).
3. **Google Vertex AI**: `GOOGLE_CLOUD_PROJECT` + Application Default Credentials (`gcloud auth application-default login`).
4. **GitHub Copilot**: `GITHUB_TOKEN` (a `gho_*` token from GitHub OAuth), exchanged for a 30-minute `ghs_*` session token by the `CopilotTokenStore`.
5. **Local providers**: No credentials. Reachability is probed via lightweight GET requests with 0.8s timeouts.

The `ProviderNotConfigured` exception is defined separately from `ProviderHTTPError` so the factory can distinguish "not configured" (a caller-fixable setup issue) from "transient HTTP error" (a runtime problem). In `auto` mode, `ProviderNotConfigured` causes a silent skip to the next provider. In explicit `--llm <name>` mode, it raises immediately with an actionable error message.

## 8. Trade-Off Analysis

### 8.1 Single `LLMProvider` ABC vs Per-Provider Interfaces

**Advantage**: Extreme simplicity. A skill writer only needs to learn one `generate()` signature. Adding a new provider requires implementing exactly one method. The `FallbackChain`, `ConfidenceCascadeRouter`, and `ProviderHealthMonitor` all operate generically.

**Disadvantage**: The ABC cannot express provider-specific capabilities. Extended thinking, vision, streaming, and prompt caching are invisible at the interface level. Skills must either check the `ProviderSpec` registry at runtime or accept silent degradation on providers that lack the capability.

**Mitigation**: The `ProviderSpec` capability map and the `providers_by_capability()` filter handle the most common queries. The `_ReasoningConfig` dataclass in the OpenAI-compatible adapter is a pragmatic workaround for the reasoning-model quirks (different parameter names, different token limit fields). For rare provider-specific features, the fallback chain allows an explicit configuration path.

### 8.2 Stdlib-Only HTTP vs SDK Dependencies

**Choice**: Every provider adapter except Anthropic (which wraps the `anthropic` SDK) and Bedrock/Vertex (which use `boto3`/`google-cloud-aiplatform`) uses only `urllib` + `json` from the stdlib.

**Advantage**: Zero compile-time dependencies for 90%+ of provider configurations. `pip install lyra` stays lean. No version conflicts between provider SDKs. No SDK bugs to wait for fixes. All HTTP client behaviour is under Lyra's control.

**Disadvantage**: No connection pooling, no automatic retries, no HTTP/2 support, no built-in backoff. The `urllib`-based adapters must implement their own retry logic (which lives in the `FallbackChain`, not the adapters themselves). Streaming via `urllib` requires manual SSE parsing.

**Mitigation**: The `_urlopen` injection seam in `OpenAICompatibleLLM` lets test code or advanced deployments inject a pooled `urllib3.PoolManager` or a mock. The streaming SSE parser (`_iter_sse_data_lines`) has been battle-tested against OpenAI, DeepSeek, Groq, Cerebras, Mistral, xAI, and OpenRouter. The `_urllib_http.py` module provides a `StdlibHTTP` class for providers (like Copilot) that need more HTTP control than a single `urlopen` call.

### 8.3 One Generic OpenAI-Compatible Adapter vs Individual Classes

**Choice**: 18 providers share a single `OpenAICompatibleLLM` class configured by `_Preset` dataclasses.

**Advantage**: Adding a new OpenAI-compatible provider is a 5-line preset definition -- no new class, no new test file, no new import in the factory. The auto-cascade automatically picks up the new preset. All bug fixes and improvements to the adapter benefit every provider simultaneously.

**Disadvantage**: Provider-specific quirks (like Groq's slightly different response envelope or OpenRouter's provider routing headers) must be handled through the `_Preset` configuration knobs (`extra_headers`, `auth_scheme`, `reasoning`, `probe_reachable`). If a quirk is complex enough, the preset becomes a leaky abstraction.

**Mitigation**: The `_Preset` dataclass has grown just enough knobs to cover all observed quirks: `extra_headers` for OpenRouter attribution headers, `auth_scheme` for Azure-style api-key auth, `reasoning` for o-series / R1 reasoning models, `probe_reachable` for local servers, and `ProviderRouting` for OpenRouter's provider-selection fields. No provider has yet required a full subclass override.

### 8.4 Auto Cascade with Hardcoded Priority vs User Choice

**Choice**: The auto cascade has a hardcoded priority (DeepSeek -> Anthropic -> OpenAI-compatible -> Gemini -> Ollama).

**Advantage**: 90% of users never need to think about provider selection. The cascade reflects the 2026 cost/quality landscape: DeepSeek is good and cheap; Anthropic is better and more expensive; local is free and offline. Users with explicit requirements use `--llm <name>`.

**Disadvantage**: The hardcoded priority reflects the maintainer's estimate of the cost/quality landscape, not the user's. A user who prefers Claude but has both `DEEPSEEK_API_KEY` and `ANTHROPIC_API_KEY` set will get DeepSeek unless they pass `--llm anthropic`. This priority hardcoding could also become stale as model capabilities shift.

**Mitigation**: `LYRA_PREFER_LOCAL` gives users control over local-first behaviour. The `--llm <name>` flag is always the unambiguous override. The `describe_selection()` function makes the active provider transparent in the startup banner and status line. And the auto-cascade priority can be updated as the competitive landscape evolves (it already moved DeepSeek to the front in the 2026 update cycle).

### 8.6 Custom Provider Import-String Registry vs Hardcoded Adapter Set**

**Choice**: In addition to the 18 built-in presets and 4 native adapters, Lyra provides a registry for custom providers defined in `settings.json` via import strings. The `provider_registry.py` module reads `settings.json:providers` and constructs `LLMProvider` instances from dotted import paths.

**Advantage**: Enterprise users and plugin authors can add proprietary or internal providers without forking Lyra's source code. The custom provider is loaded at runtime and participates in the same `--llm <name>` resolution path as built-in providers.

**Disadvantage**: Import-string-based registration is fragile. A wrong module path, an import error, or a type mismatch produces an error at construction time rather than at declaration time. Runtime type checking is limited because the registry sees the provider through the `LLMProvider` Protocol, not a concrete class.

**Mitigation**: The `CustomProviderError` exception encapsulates import and construction failures with an actionable message pointing to the config file and line. The custom registry is consulted *before* the built-in preset table in `build_llm()`, so users can override a built-in provider with a custom implementation if needed.

### 8.7 One `Message` Format vs Per-Provider Message Types

**Choice**: Lyra uses a single `Message` class (Pydantic BaseModel) for all providers, with the Anthopic-style `role` convention as the canonical form.

**Advantage**: The agent loop, tool dispatcher, skill executor, and context compactor all operate on the same data type. No per-provider message mappers or discriminators are needed at the application layer. The `Message` class is serialisable to JSON for persistence and debugging.

**Disadvantage**: Some provider-specific metadata is lost during normalisation. Gemini's `role="model"` (vs "assistant"), Ollama's per-response model name, and OpenAI's `system_fingerprint` are all discarded at the adapter boundary. Extended thinking content blocks (Anthropic's `thinking` and `redacted_thinking`, OpenAI's `reasoning_content`) are deliberately stripped to prevent prompt-injection surfaces.

**Mitigation**: The `last_usage` dict carries per-turn metadata that is provider-informative but not critical to the agent loop. The `cumulative_usage` dict on the OpenAI-compatible adapter accumulates token counts across calls for run-level observability. For metadata that must survive the adapter boundary, provider-specific fields can be added to the `Message` model as optional extras without breaking existing consumers.

**Choice**: The `PromptCacheCoordinator` manages one shared anchor per `(provider, document_digest)` across all sibling subagents.

**Advantage**: When N agents read the same shared document (SOUL.md, plan artifact, system prompt), the first write pays the cache-set cost and all subsequent reads pay the cache-hit rate. This is the PolyKV insight applied to hosted APIs: O(1) shared prefix cost regardless of agent count.

**Disadvantage**: The cache floor of 4000 characters means short shared prefixes are never cached. The 300-second TTL means long-running sessions beyond 5 minutes see the anchor expire and pay the write cost again. The coordinator adds a lock acquisition to every subagent dispatch.

**Mitigation**: The floor is tuned to avoid caching micro-prompts where the write overhead beats the saving. The TTL matches most providers' ephemeral cache TTLs (Anthropic's default is also 5 minutes). The coordinator is lock-granular on `(provider, digest)` pairs, so concurrent subagents on different documents don't contend.

## 9. (B) Breakthrough: Universal Provider Interface

Lyra's provider abstraction goes beyond existing harnesses in five specific ways:

### 9.1 PolyKV-Style Subagent Cache Coordination

Existing harnesses (LangChain, LiteLLM, Semantic Kernel) treat prompt caching as a per-request optimisation: if a single request has a repeated prefix, the provider's automatic caching may apply. Lyra extends this to the multi-agent case through the `PromptCacheCoordinator`. When N sibling subagents read the same shared document across multiple `generate()` calls, the coordinator ensures they share a single cache anchor. The coordinator adapts per provider: `cache_control` blocks for Anthropic, automatic prefix-alignment for OpenAI/DeepSeek, `CachedContent` resources for Gemini. No other harness coordinates prompt caching across subagents from a single orchestrator.

### 9.2 Provider-Adaptive Context Compaction

The `ProviderAdaptiveCompactor` is Lyra's specific contribution to what the source identifies as "an unaddressed frontier." Compaction strategy varies by provider context window: a 2M-token Gemini prompt gets summarisation; a 64K-token DeepSeek prompt at the same usage ratio gets truncation or aggressive compaction. The thresholds are based on both the absolute window size and the current usage ratio, producing a graduated response that no other LLM harness implements. Existing harnesses apply the same compaction strategy regardless of which provider will ultimately process the prompt.

### 9.3 Cost-Aware Provider Cascade with Local-First Preference

Lyra's auto-cascade is the only harness that (a) ranks DeepSeek first by default because of its cost/quality ratio, (b) falls back to local providers (Ollama, LM Studio) when no cloud key is configured, and (c) respects the `LYRA_PREFER_LOCAL` environment variable for offline-first routing. The `DynamicPricingEngine` and `ProviderHealthMonitor` feed runtime signals into the selection decision, making it a closed-loop routing system rather than a static priority list. Existing harnesses either require manual provider configuration or use simple round-robin/fallback strategies.

### 9.4 Unified Credential Hydration with Three-Layer Resolution

Lyra's `_hydrate_env_from_dotenv()` resolves credentials through three cascading sources: `~/.lyra/auth.json` (written by `lyra connect`), project-local `.env` (walked from CWD up), and process environment variables. The resolution is idempotent and cumulative -- each layer only fills in slots that are still empty. This means a user can have API keys in their `.env` for shared CI, override individual keys with environment variables, and store non-sensitive defaults in `auth.json`. No existing harness provides this three-layer credential resolution with Lyra's priority semantics. Additionally, the `_route_kind_via_alias()` function ensures that when a user types `--model deepseek-chat`, the alias registry resolves it to the DeepSeek provider and sets `DEEPSEEK_MODEL` in the environment, so the downstream factory doesn't accidentally route to OpenAI.

### 9.5 Zero-Dependency Provider Adaptation for 90% of Backends

By building the `OpenAICompatibleLLM` adapter on stdlib-only `urllib` + `json`, Lyra supports 18+ provider backends without importing a single provider SDK. The same approach applies to the Gemini adapter (stdlib-only REST) and the Ollama adapter (stdlib-only). Only Anthropic (the `anthropic` package), Bedrock (`boto3`), and Vertex AI (`google-cloud-aiplatform`) require optional dependencies -- and these are isolated to the `lyra[anthropic]`, `lyra[bedrock]`, and `lyra[vertex]` extras. This means `pip install lyra` gives the user 18+ providers with zero compile-time dependencies. Existing harnesses typically require the provider's SDK as a hard dependency, meaning users who want to switch from Anthropic to DeepSeek must `pip install openai`, and DeepSeek users must `pip install openai` (because DeepSeek uses the OpenAI wire format).

The combination of these five breakthroughs -- subagent cache coordination, provider-adaptive compaction, cost-aware cascade with local-first preference, three-layer credential resolution, and zero-dependency provider coverage -- makes Lyra's provider abstraction layer qualitatively different from existing LLM harnesses. It is not merely an adapter pattern applied to LLMs; it is a unified execution substrate that treats provider selection, credential management, context budgeting, prompt caching, and health monitoring as a single optimization problem.

## 10. Key Sources

- `LLMProvider` abstract base class: `packages/lyra-harness-core/src/lyra_harness_core/models.py` (lines 16-28)
- `Message`, `ToolCall`, `ToolResult`, `StopReason`: `packages/lyra-harness-core/src/lyra_harness_core/messages.py`
- `ProviderSpec` registry and `PROVIDER_REGISTRY`: `packages/lyra-core/src/lyra_core/providers/registry.py` (lines 40-586)
- `AliasRegistry` with 4-layer alias resolution: `packages/lyra-core/src/lyra_core/providers/aliases.py`
- `PromptCacheCoordinator` and per-provider cache adapters: `packages/lyra-core/src/lyra_core/providers/prompt_cache.py`
- `ProviderHealthMonitor` with circuit breaker: `packages/lyra-core/src/lyra_core/routing/provider_health.py`
- `ConfidenceCascadeRouter` (FrugalGPT/RouteLLM inspired): `packages/lyra-core/src/lyra_core/routing/cascade.py`
- `DynamicPricingEngine`: `packages/lyra-core/src/lyra_core/routing/dynamic_pricing.py`
- `ProviderAdaptiveCompactor` (provider-adaptive context strategy): `packages/lyra-context/src/lyra_context/provider_adapter.py`
- `build_llm()` auto-cascade and `describe_selection()`: `packages/lyra-cli/src/lyra_cli/llm_factory.py`
- Intra-provider model routing: `packages/lyra-cli/src/lyra_cli/llm_router.py`
- `LyraAnthropicLLM` (Anthropic wrapper with usage capture): `packages/lyra-cli/src/lyra_cli/providers/anthropic.py`
- `OpenAICompatibleLLM` and 18 presets: `packages/lyra-cli/src/lyra_cli/providers/openai_compatible.py`
- `GeminiLLM` (native REST adapter): `packages/lyra-cli/src/lyra_cli/providers/gemini.py`
- `OllamaLLM` (stdlib-only local adapter): `packages/lyra-cli/src/lyra_cli/providers/ollama.py`
- `FallbackChain` (runtime retryable-error cascade): `packages/lyra-cli/src/lyra_cli/providers/fallback.py`
- `AnthropicBedrockLLM` and `GeminiVertexLLM`: `packages/lyra-cli/src/lyra_cli/providers/bedrock.py` and `packages/lyra-cli/src/lyra_cli/providers/vertex.py`
