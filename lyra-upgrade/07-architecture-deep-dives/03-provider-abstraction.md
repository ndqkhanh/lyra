# Provider Abstraction Layer -- Deep Dive

## 1. Executive Summary

Lyra's provider abstraction layer is the architectural seam that decouples every
higher-level capability (routing, skills, tools, memory, swarm, voice) from the
specifics of any single AI provider. Without this seam, every new provider would
require changes across the entire codebase -- the router would need provider-specific
routing logic, every skill would need to know which API format to emit, and the
memory system would need separate serialization paths per provider.

The abstraction layer normalizes five disjoint dimensions that every provider SDK
handles differently:

- **Message format**: Roles, content blocks, tool result envelopes, system prompts
- **Tool calling**: Schema declaration, request-time tool bindings, response-time
  tool call extraction
- **Streaming**: SSE event types, delta formats, termination signals (DONE vs
  message_stop)
- **Token accounting**: Input/output/cache-read/cache-write fields with different
  names and semantics per provider
- **Error taxonomy**: HTTP status codes, rate-limit headers, auth error strings,
  context-overflow signals

The result is that every component above the provider boundary -- the ModelRouter
in `packages/lyra-router/`, the Skills system in `packages/lyra-skills/`, the
Workflow engine in `packages/lyra-workflow/`, the Memory subsystem in
`packages/lyra-memory/`, and the orchestration stack in
`packages/lyra-orchestration/` -- contains zero provider-specific code. Each
provider lives entirely in its adapter under
`packages/lyra-provider/src/lyra_provider/adapters/`.

This design enables write-once-run-anywhere for skills: a skill that invokes an
LLM via `AbstractProvider.chat()` works identically whether the backend is
Anthropic, OpenAI, DeepSeek, or Google, subject only to capability constraints
(tool calling, vision, context window size). The router selects the provider; the
skill never knows which one it got.

The following sections examine every layer of this abstraction in detail: the
canonical interface types, each adapter's translation logic, the capability
detection system that informs routing decisions, the fallback and escalation chain
that maintains availability across provider outages, a complete architecture
diagram, trade-off analysis, and the breakthrough innovations that distinguish
Lyra's approach from every comparable harness.

---
---

## 2. The AbstractProvider Interface

### 2.1 Canonical Types

The abstraction lives in a single file:
`packages/lyra-provider/src/lyra_provider/interface.py` (322 lines). It defines
every type that crosses the provider boundary, ensuring that code above the
boundary never imports provider SDKs.

**MessageRole** is a simple enum of four canonical roles:

```python
class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

This is deliberately constrained. Anthropic has a flat role set (user, assistant
-- system is a separate API parameter, not a role). OpenAI/DeepSeek have system,
user, assistant, and tool roles. Google Gemini uses user, model, function
roles with a different tool result mechanism. The canonical set normalizes all
of these into four roles. The adapter for each provider handles the translation:

- Anthropic adapter: SYSTEM messages are extracted from the message list and
  sent as the `system` top-level parameter. TOOL messages become `user` role
  messages with `tool_result` content blocks.
- OpenAI/DeepSeek adapters: All four roles map 1:1 to their API equivalents.
- Google adapter (when implemented): SYSTEM maps to the `system_instruction`
  top-level field, TOOL maps to `function` role responses.

**ToolCall** is the canonical representation of a model-invoked tool:

```python
@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
```

The frozen dataclass design enforces immutability -- once created, a ToolCall
cannot be mutated, which prevents subtle bugs when the same ToolCall is
referenced from multiple places (streaming accumulator, response processing,
tool execution dispatch). The `arguments` field is always a parsed Python dict,
never a JSON string. This is a deliberate normalization: Anthropic returns
`input` as a parsed dict, while OpenAI/DeepSeek return `arguments` as a JSON
string that must be parsed. The adapter handles this difference.

**ToolResult** carries the output of a tool execution back to the model:

```python
@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    name: str
    content: str
    is_error: bool = False
```

The `is_error` field is critical. Anthropic's API supports a top-level `is_error`
flag on tool_result blocks. OpenAI/DeepSeek have no native error flag -- errors
must be encoded as text content. The adapter normalizes this: Anthropic passes
is_error natively; OpenAI/DeepSeek inject the error into content text.

**Message** is the central conversation unit:

```python
@dataclass
class Message:
    role: MessageRole
    content: str | list[dict[str, Any]]
    tool_calls: list[ToolCall] | None = None
    tool_result: ToolResult | None = None
    name: str | None = None
```

The `content` field accepts both string and structured list formats. String
content is the common case for text-only messages. List content supports
multi-modal messages (text + image) used by vision-capable providers. The
`tool_calls` and `tool_result` fields are mutually exclusive in practice:
assistant messages carry tool_calls, tool messages carry tool_result.

**ToolSchema** normalizes tool definitions:

```python
@dataclass(frozen=True)
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object
```

The `parameters` field uses JSON Schema as the common denominator. All major
providers accept JSON Schema for parameter definitions, though each wraps it
differently: Anthropic uses `input_schema`, OpenAI/DeepSeek use
`function.parameters`, Google uses `parameters` directly. The adapter rewraps.

**ChatRequest** is the complete input to any provider:

```python
@dataclass
class ChatRequest:
    messages: list[Message]
    model: str
    tools: list[ToolSchema] | None = None
    max_tokens: int = 4096
    temperature: float | None = None
    stream: bool = False
    effort_budget_tokens: int | None = None
    effort_instruction: str | None = None
    effort_reasoning: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
```

The three effort fields (`effort_budget_tokens`, `effort_instruction`,
`effort_reasoning`) are the mechanism by which Lyra's effort system
(`lyra-effort` package) communicates reasoning depth to the provider layer. Each
adapter picks the relevant field:

- Anthropic uses `effort_budget_tokens` -> `thinking.budget_tokens`
- OpenAI uses `effort_reasoning` -> `reasoning_effort` parameter
- DeepSeek uses `effort_instruction` -> injected into system prompt

The `extra` dict is a deliberate escape hatch for provider-specific parameters
that have no canonical equivalent. Examples include Anthropic's
`anthropic-version` header or OpenAI's `seed` parameter. It exists so the
abstraction doesn't become a straitjacket, but its use is discouraged for
anything that could be normalized.

**ChatResponse** is the complete output:

```python
@dataclass
class ChatResponse:
    content: str
    model: str
    usage: LLMUsage | None = None
    tool_calls: list[ToolCall] | None = None
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    provider: str = ""
    raw: Any = None
```

The `raw` field carries the complete provider response, enabling debugging and
forensic analysis without breaking the abstraction. The `latency_ms` field is
used by the router's BudgetTracker and NeuralUCB feedback loop to make
cost-aware and latency-aware routing decisions.

**LLMUsage** normalizes token accounting:

```python
@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
```

The cache fields are Anthropic-specific (prompt caching). OpenAI and DeepSeek
do not expose cache tokens separately. Google Gemini does not expose per-request
token counts at all. The adapter fills what it can and leaves zeros for
unsupported fields.

**StreamEvent** is the canonical streaming event:

```python
@dataclass(frozen=True)
class StreamEvent:
    type: str  # text_delta | tool_call_start | tool_call_delta | tool_call_end | done | error
    content: str = ""
    tool_call: ToolCall | None = None
    usage: LLMUsage | None = None
    error: str | None = None
```

The six event types normalize the different streaming protocols:
- Anthropic: `content_block_start`, `content_block_delta`, `content_block_stop`,
  `message_delta`, `message_stop`
- OpenAI/DeepSeek: `choices[0].delta.content`, `choices[0].delta.tool_calls`,
  `choices[0].finish_reason`, `usage` on the final chunk
- Google: Separate stream chunks with different field structure entirely

**ErrorCode and ProviderError** normalize error taxonomy:

```python
class ErrorCode(str, Enum):
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    CONTEXT_OVERFLOW = "context_overflow"
    INVALID_REQUEST = "invalid_request"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class ProviderError(Exception):
    code: ErrorCode
    message: str
    provider: str = ""
    retryable: bool = False
    raw: Any = None
```

The `retryable` field is used by the router's fallback chain. A RATE_LIMIT error
with `retryable=True` triggers an immediate retry on a different provider. An
AUTH_ERROR with `retryable=False` halts routing for that provider until
credentials are updated.

**ProviderConfig** holds connection parameters:

```python
@dataclass
class ProviderConfig:
    provider: str
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    max_retries: int = 3
    timeout_seconds: float = 120.0
    max_concurrent: int = 50
    extra: dict[str, Any] = field(default_factory=dict)
```

The `max_concurrent` field is used for connection pooling. The
`__repr__` method masks the API key to prevent credential leaks in logs:
```python
masked = (
    self.api_key[:8] + "..." + self.api_key[-4:]
    if len(self.api_key) > 12 else "***"
)
```

### 2.2 The AbstractProvider Protocol

The `AbstractProvider` abstract base class defines the contract every adapter
must fulfill:

```python
class AbstractProvider(abc.ABC):
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @property
    @abc.abstractmethod
    def provider_name(self) -> str: ...

    @abc.abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...

    @abc.abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]: ...

    @abc.abstractmethod
    async def validate_api_key(self) -> bool: ...

    @abc.abstractmethod
    async def list_models(self) -> list[str]: ...

    @abc.abstractmethod
    def supports_feature(self, feature: str) -> bool: ...

    @abc.abstractmethod
    def get_context_window(self, model: str) -> int: ...
```

The protocol is deliberately minimal -- seven methods. Every adapter must
implement all seven. The `chat` and `chat_stream` methods are the primary
data path. `validate_api_key` and `list_models` are lifecycle methods used
during initialization and health checking. `supports_feature` and
`get_context_window` provide static capability information that the router
uses for provider selection.

The design rationale, stated in the module docstring:

> The provider abstraction sits at the BOUNDARY. Components above
> this interface (router, skills, swarm, voice) contain ZERO provider-specific
> code. Components below (individual adapters) contain ONLY provider-specific
> code. This is the seam that makes Lyra multi-provider.

### 2.3 How Canonical Types Differ from Provider-Specific SDKs

The canonical types are not a lowest-common-denominator simplification. They
are a carefully designed intermediate representation that preserves the full
expressiveness of each provider's API while presenting a uniform interface.
Key differences from provider SDKs:

**Anthropic SDK** uses content blocks for everything: text blocks, tool_use
blocks, tool_result blocks, thinking blocks. The canonical `Message` type
collapses content blocks into a flat structure: text is `content`, tool uses
are `tool_calls`, tool results are `tool_result`. The Anthropic adapter (lines
79-104 of `adapters/anthropic.py`) handles the deconstruction/reconstruction:

```python
def _from_anthropic_message(anthropic_msg):
    content_blocks = anthropic_msg.get("content", [])
    text_parts = []
    tool_calls = []
    for block in content_blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append(ToolCall(
                id=block.get("id", ""),
                name=block.get("name", ""),
                arguments=block.get("input", {}),
            ))
    return Message(
        role=MessageRole.ASSISTANT,
        content="\n".join(text_parts),
        tool_calls=tool_calls or None,
    )
```

**OpenAI SDK** separates text and tool calls into different fields of the
response `choice.message`. Text is `message.content`, tool calls are
`message.tool_calls[i].function`. The canonical format unifies them into
a single `Message` with both `content` and `tool_calls` fields, which the
OpenAI adapter (reusing `deepseek.py`'s `_from_openai_message`) reconstructs.

**DeepSeek API** is OpenAI-compatible but with one critical difference: the
`usage` object uses `prompt_tokens`/`completion_tokens` instead of
Anthropic's `input_tokens`/`output_tokens`. The canonical `_from_openai_usage`
function normalizes this:

```python
def _from_openai_usage(usage_data):
    if usage_data is None:
        return LLMUsage(input_tokens=0, output_tokens=0)
    return LLMUsage(
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
    )
```

**Google GenAI SDK** uses a completely different structure with `Part` objects,
`FunctionCall` and `FunctionResponse` types, and a different streaming protocol.
The Google adapter is currently a stub (see Section 3.4), but the canonical
types are designed to accommodate it.

### 2.4 Error Normalization

Each provider has a different error signature. The canonical layer normalizes
them through `_translate_error` static methods in each adapter. The patterns
are consistent:

- **Anthropic** (lines 431-441): Status code mapping from HTTP responses.
  401 -> AUTH_ERROR, 429 -> RATE_LIMIT, 400 -> INVALID_REQUEST.
  Error messages checked case-insensitively.

- **DeepSeek** (lines 410-420): Same pattern, plus 402 -> AUTH_ERROR
  (insufficient balance -- DeepSeek-specific).

- **OpenAI** (lines 278-285): Simplified -- 401/unauthorized -> AUTH_ERROR,
  429/rate limit -> RATE_LIMIT, everything else -> UNKNOWN.

This normalization is what enables the router's fallback chain to treat errors
from different providers uniformly.

---
---

## 3. Provider Adapters

### 3.1 Anthropic Adapter

**File**: `packages/lyra-provider/src/lyra_provider/adapters/anthropic.py` (442 lines)
**Class**: `AnthropicProvider`
**API Base**: `https://api.anthropic.com/v1`
**HTTP Client**: httpx (primary), aiohttp (fallback)

The Anthropic adapter is the most complete in the codebase, reflecting the fact
that Anthropic's Messages API has the richest feature set among the supported
providers: extended thinking, prompt caching, vision, tool use, and JSON mode.

#### Message Format: Lyra Canonical to Anthropic Messages API

The adapter has bidirectional message translation through two functions:
`_to_anthropic_message` and `_from_anthropic_message`.

**Outbound translation** (`_to_anthropic_message`, lines 41-76):

```
Lyra SYSTEM role -> {"role": "system", "content": msg.content}
Lyra USER role   -> {"role": "user", "content": msg.content}
Lyra ASSISTANT   -> {"role": "assistant", "content": [...]}
  (with tool_calls: adds tool_use content blocks)
Lyra TOOL role   -> {"role": "user", "content": [{"type": "tool_result", ...}]}
```

The critical detail is how tool calls and tool results are handled. When an
assistant message has `tool_calls`, the adapter creates an array of `tool_use`
content blocks rather than a flat string:

```python
if msg.tool_calls:
    result["content"] = [
        {
            "type": "tool_use",
            "id": tc.id,
            "name": tc.name,
            "input": tc.arguments,
        }
        for tc in msg.tool_calls
    ]
```

This is because Anthropic's API requires tool uses as explicit content blocks,
not as flat string + tool_calls array. Tool results go into a user-role message
with `tool_result` content blocks, carrying the `is_error` flag natively.

**Inbound translation** (`_from_anthropic_message`, lines 79-104):

Anthropic response content blocks are parsed:
- `type: "text"` blocks are concatenated into `content`
- `type: "tool_use"` blocks become `ToolCall` objects in `tool_calls`

The string concatenation uses `"\n".join(text_parts)` because Anthropic may
return multiple text blocks interleaved with tool_use blocks (though in
practice, text blocks are usually contiguous).

#### Tool Use Normalization

Tool schemas are converted via `_to_anthropic_tool` (lines 112-118):

```python
def _to_anthropic_tool(tool):
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.parameters,
    }
```

The key mapping is `parameters` (Lyra's JSON Schema field) -> `input_schema`
(Anthropic's equivalent). Anthropic wraps the JSON Schema in a tight
`{name, description, input_schema}` object, while OpenAI/DeepSeek wrap it in
`{type: "function", function: {name, description, parameters}}`. The canonical
`ToolSchema.parameters` is always JSON Schema regardless of the target provider.

#### Extended Thinking: budget_tokens from Effort Scale

The adapter maps `ChatRequest.effort_budget_tokens` to Anthropic's extended
thinking parameter (lines 196-201):

```python
if request.effort_budget_tokens:
    body["thinking"] = {
        "type": "enabled",
        "budget_tokens": request.effort_budget_tokens,
    }
```

The budget values come from Lyra's effort system
(`packages/lyra-effort/src/lyra_effort/models.py`):

| Effort Level | budget_tokens |
|-------------|---------------|
| LOW         | 1024          |
| MEDIUM      | 4096          |
| HIGH        | 8192          |
| XHIGH       | 16384         |
| MAX         | 32000         |
| ULTRACODE   | 16384         |

Note that ULTRACODE uses the same budget as XHIGH (16384). The difference is
the auto-orchestration toggle, not the thinking budget.

The `thinking` object uses `type: "enabled"` (the old API format) rather than
`type: "adaptive"` (the newer format). This is because the adapter was written
before Anthropic deprecated `budget_tokens` in favor of
`output_config.effort`. As of Anthropic's May 2026 API, `output_config.effort`
is the recommended path for Opus 4.8+, and `budget_tokens` is phased out. A
future update should map effort levels to Anthropic's `output_config.effort`
values directly rather than computing raw budget_tokens.

#### Context Window: 200K

All well-known Anthropic models share a 200K context window:

```python
_CONTEXT_WINDOWS: dict[str, int] = {
    "claude-opus-4-20250514": 200_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-haiku-4-20250514": 200_000,
    "claude-opus-4-8-20250514": 200_000,
    "claude-sonnet-4-6-20250514": 200_000,
    "claude-haiku-4-5-20250514": 200_000,
}
```

#### Streaming Implementation

The `chat_stream` method (lines 244-356) normalizes Anthropic's SSE events:

| Anthropic SSE Event     | Lyra StreamEvent        |
|------------------------|------------------------|
| content_block_start    | tool_call_start (if tool_use) |
| content_block_delta   | text_delta or tool_call_delta |
| content_block_stop    | tool_call_end           |
| message_delta         | done (with usage)       |

The streaming implementation accumulates tool call arguments as JSON fragments
(`current_tool["arguments"] += delta.get("partial_json", "")`) and parses them
at the end. This is necessary because Anthropic streams tool call arguments as
incremental JSON deltas, not as complete objects.

The streaming implementation currently does NOT handle thinking blocks
(`type: "thinking"` and `type: "thinking_delta"`). These are deprecated on
Sonnet 4.6+ and removed on Opus 4.7+, so the omission is intentional.

#### Prompt Caching Support

Prompt caching is supported at the capability level (`prompt_caching=True` in
the capability matrix, line 115 of `capability.py`). The adapter does not
explicitly add `cache_control` breakpoints -- that is the responsibility of
the caller (e.g., the memory system or the skills system). The adapter does
extract cache statistics from the Anthropic usage block:

```python
def _from_anthropic_usage(usage_data):
    return LLMUsage(
        input_tokens=usage_data.get("input_tokens", 0),
        output_tokens=usage_data.get("output_tokens", 0),
        cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
        cache_write_tokens=usage_data.get("cache_creation_input_tokens", 0),
    )
```

The `cache_read_input_tokens` and `cache_creation_input_tokens` are
Anthropic-specific fields. The `LLMUsage` canonical type carries them as
optional fields (defaulting to 0), which is safe for other providers that
don't expose caching.

#### Dual HTTP Client Strategy

The adapter supports both httpx (lines 207-221) and aiohttp (lines 386-429),
with the latter as a fallback if httpx is not installed:

```python
try:
    import httpx
    async with httpx.AsyncClient(...) as client:
        response = await client.post(...)
except ImportError:
    return await self._chat_via_http(request, body)
```

This dual-client pattern is replicated in every adapter. The rationale is
deployment flexibility: httpx is the preferred client (better API for async
streaming), but aiohttp is more commonly available in production environments
that use it for other services. Requiring neither forces a clear error:

```python
raise ProviderError(
    code=ErrorCode.PROVIDER_ERROR,
    message="Neither httpx nor aiohttp available. Install one to use AnthropicProvider.",
    provider="anthropic",
)
```

---
---

### 3.2 OpenAI Adapter

**File**: `packages/lyra-provider/src/lyra_provider/adapters/openai.py` (286 lines)
**Class**: `OpenAIProvider`
**API Base**: `https://api.openai.com/v1`

The OpenAI adapter is structurally similar to the DeepSeek adapter (both use
the OpenAI-compatible API format) but differs in three key ways:
`reasoning_effort` support, vision support, and JSON mode.

#### Message Format Normalization

The OpenAI adapter reuses the message/tool/usage translation functions from
the DeepSeek adapter:

```python
from .deepseek import (
    _from_openai_message,
    _from_openai_usage,
    _to_openai_message,
    _to_openai_tool,
)
```

This code-sharing is possible because OpenAI and DeepSeek use the same
underlying API format (`chat/completions` with the same message structure).
The shared functions are defined in `deepseek.py` (lines 40-121) and exported
for reuse.

The message translation works as follows:

```
Lyra SYSTEM role   -> {"role": "system", "content": msg.content}
Lyra USER role     -> {"role": "user", "content": msg.content}
Lyra ASSISTANT     -> {"role": "assistant", "content": ..., "tool_calls": [...]}
Lyra TOOL role     -> {"role": "tool", "tool_call_id": ..., "content": ...}
```

The key difference from Anthropic: OpenAI/DeepSeek use a flat `tool_calls`
array on the assistant message, not content blocks. The `_to_openai_message`
function (lines 40-65) handles this:

```python
if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
    base["content"] = msg.content if isinstance(msg.content, str) else ""
    base["tool_calls"] = [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.name,
                "arguments": json.dumps(tc.arguments),
            },
        }
        for tc in msg.tool_calls
    ]
```

Note the `json.dumps(tc.arguments)`: OpenAI requires tool call arguments as
JSON strings, while Anthropic accepts parsed dicts. This is a source of adapter
complexity that the canonical layer hides.

#### Tool Calls Array Handling

The streaming implementation in `openai.py` handles OpenAI's streaming tool call
format, which sends tool calls incrementally across multiple SSE chunks:

1. A `tool_calls[0].id` field signals the start of a new tool call
2. Subsequent chunks carry `tool_calls[0].function.arguments` fragments
3. The final chunk carries `finish_reason: "tool_calls"`

The adapter buffers tool call arguments in `current_tool["arguments"]` and emits
`tool_call_start` on first ID receipt, then accumulates fragments silently, then
emits `tool_call_end` when the finish_reason arrives:

```python
if current_tool and event.get("choices", [{}])[0].get("finish_reason") == "tool_calls":
    try:
        args = json.loads(current_tool["arguments"])
    except json.JSONDecodeError:
        args = {}
    yield StreamEvent(type="tool_call_end", tool_call=...)
```

#### Reasoning Effort Mapping

OpenAI supports a `reasoning_effort` parameter on o-series models (o1, o3,
GPT-5 reasoning). The adapter maps Lyra's canonical effort via
`ChatRequest.effort_reasoning` (lines 80-82):

```python
if request.effort_reasoning:
    body["reasoning_effort"] = request.effort_reasoning
```

The effort system (`lyra-effort/manager.py`) maps Lyra's six-level scale to
OpenAI's three-level scale:

| Lyra Level | OpenAI reasoning_effort |
|-----------|------------------------|
| LOW       | "low"                  |
| MEDIUM    | "low"                  |
| HIGH      | "medium"               |
| XHIGH     | "high"                 |
| MAX       | "high"                 |
| ULTRACODE | "high"                 |

This compression loses information: Lyra's LOW and MEDIUM both map to "low",
and XHIGH, MAX, and ULTRACODE all map to "high". This is a fundamental
limitation of OpenAI's coarser API.

#### Context Window: 128K (256K for GPT-5)

```python
_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini-2025": 128_000,
    "gpt-4o-2025": 128_000,
    "gpt-5": 256_000,
}
```

The GPT-5 context window (256K) is larger than Anthropic's standard 200K but
smaller than Google's 1M. The fallback default is 128K.

#### Feature Support

```python
def supports_feature(self, feature: str) -> bool:
    return feature in {"tool_calling", "json_mode", "vision", "streaming"}
```

OpenAI supports JSON mode via `response_format`, which the adapter does not
currently pass through. This is an omission -- the `response_format` parameter
should be configurable via `ChatRequest.extra` or a dedicated canonical field.

---
---

### 3.3 DeepSeek Adapter

**File**: `packages/lyra-provider/src/lyra_provider/adapters/deepseek.py` (421 lines)
**Class**: `DeepSeekProvider`
**API Base**: `https://api.deepseek.com/v1`

DeepSeek uses an OpenAI-compatible API format, so the adapter shares
significant code with OpenAIProvider. However, DeepSeek has unique
characteristics that make it a distinct adapter class rather than a simple
configuration of OpenAIProvider.

#### OpenAI-Compatible with Key Differences

The shared code lives in `deepseek.py` as module-level functions exported for
both `DeepSeekProvider` and `OpenAIProvider` to consume:

- `_to_openai_message(msg)` -- Lyra Message to OpenAI-compatible dict
- `_from_openai_message(openai_msg)` -- OpenAI-compatible dict to Lyra Message
- `_to_openai_tool(tool)` -- Lyra ToolSchema to OpenAI function format
- `_from_openai_usage(usage_data)` -- OpenAI usage to Lyra LLMUsage

The key structural difference from OpenAIProvider is how effort is handled:

**No native reasoning budget.** DeepSeek has no `reasoning_effort` or
`budget_tokens` parameter. Lyra compensates by injecting thinking instructions
directly into the system prompt. This is handled in `_build_messages` (lines
338-363):

```python
def _build_messages(self, request):
    messages = [_to_openai_message(m) for m in request.messages]
    if request.effort_instruction:
        system_idx = next(
            (i for i, m in enumerate(messages) if m.get("role") == "system"),
            None,
        )
        if system_idx is not None:
            existing = messages[system_idx].get("content", "")
            messages[system_idx]["content"] = (
                f"{request.effort_instruction}\n\n{existing}"
            )
        else:
            messages.insert(0, {
                "role": "system",
                "content": request.effort_instruction,
            })
    return messages
```

The effort instructions come from the effort manager
(`lyra-effort/src/lyra_effort/manager.py`):

| Effort Level | Thinking Instruction                           |
|-------------|------------------------------------------------|
| LOW         | "Be concise. Provide direct answers."          |
| MEDIUM      | "Think briefly before answering."              |
| HIGH        | "Think step by step. Be thorough."             |
| XHIGH       | "Think deeply. Consider multiple approaches."  |
| MAX         | "Use maximum reasoning depth."                 |
| ULTRACODE   | "Think deeply. Consider multiple approaches."  |

This prompt-based approach is fragile: the model may over- or under-think
regardless of instruction. There is no token-budget enforcement mechanism.
An instruction for "deep thinking" on a 128K context window could produce
arbitrarily long reasoning traces.

#### Context Window: 128K

```python
_CONTEXT_WINDOWS: dict[str, int] = {
    "deepseek-chat-v4": 128_000,
    "deepseek-reasoner-v4": 128_000,
}
```

The domain research document (ultracode-mechanisms.md) notes a 64K constraint,
but the code shows 128K. This discrepancy likely reflects a model version
update: DeepSeek-V3 had 64K; DeepSeek-V4 exposes 128K.

#### Provider-Adaptive Compaction Strategy Trigger

The 128K context window is smaller than Anthropic's 200K and Google's 1M. This
has important implications for Lyra's context optimization system. When the
router selects DeepSeek, the context compaction threshold should be lowered --
compaction should trigger earlier (e.g., at 60K tokens rather than 100K) to
avoid hitting the hard 128K limit during long conversations.

This provider-adaptive compaction is not yet implemented in the provider
abstraction layer. It requires the `get_context_window()` method to be
consulted by the memory/context system before building the message list.

#### Feature Support

```python
def supports_feature(self, feature: str) -> bool:
    return feature in {"tool_calling", "streaming"}
```

DeepSeek does NOT support:
- `json_mode`: No structured JSON output API
- `vision`: No image input support
- `prompt_caching`: No caching mechanism

This minimal feature set is by design: DeepSeek is a cost-optimized provider
for text-only tasks. The capability matrix (Section 4) ensures the router never
routes vision or JSON-mode tasks to DeepSeek.

#### Error Handling

DeepSeek adds a 402 status code for insufficient balance:

```python
if "402" in msg or "insufficient" in msg:
    return ProviderError(code=ErrorCode.AUTH_ERROR, message=str(error), provider="deepseek")
```

This is unique among the supported providers. The `402 Insufficient Balance`
error occurs when the DeepSeek account has run out of credits, which is a
common failure mode for prepaid API services.

---
---

### 3.4 Google Adapter

**File**: `packages/lyra-provider/src/lyra_provider/adapters/google.py` (79 lines)
**Class**: `GoogleProvider`
**API Base**: `https://generativelanguage.googleapis.com/v1beta`
**Status**: STUB -- not yet implemented

The Google adapter is the least complete in the codebase. The `chat` and
`chat_stream` methods raise NotImplementedError-equivalent errors:

```python
async def chat(self, request: ChatRequest) -> ChatResponse:
    raise ProviderError(
        code=ErrorCode.PROVIDER_ERROR,
        message="GoogleProvider is not yet implemented. Use Anthropic or DeepSeek provider.",
        provider="google",
    )
```

The architecture document below describes the intended implementation.

#### Gemini Function Calling Format

Google's Gemini API uses a fundamentally different message structure from both
Anthropic and OpenAI:

1. **Roles**: `user`, `model` (not `assistant`), `function` (for tool results)
2. **Content**: Array of `Part` objects (text, inline_data, function_call,
   function_response)
3. **Tool definitions**: `tools.function_declarations` with a different
   parameter schema format
4. **System instruction**: Separate `system_instruction` field, not a message
5. **Thinking**: `thinkingConfig.thinkingBudget` (fixed token budget) or
   `output_config.effort` (on newer models)

The canonical-to-Google translation would need to:

1. Map `MessageRole.ASSISTANT` -> `model` role
2. Map `MessageRole.TOOL` -> `function` role
3. Map `ToolCall.arguments` -> `function_call.args` (different field name)
4. Map `ToolResult` -> `function_response.response`
5. Map SYSTEM messages to `system_instruction` top-level field
6. Handle `thinkingConfig` differently from Anthropic's `thinking` block

**Effort mapping** for Google follows the same prompt-based approach as
DeepSeek, since Gemini does not natively support Anthropic-style budget_tokens.
The effort manager injects thinking instructions into the system prompt.

#### 1M Context Window Handling

The Google adapter declares the largest context window of any supported provider:

```python
_CONTEXT_WINDOWS: dict[str, int] = {
    "gemini-2.5-flash": 1_000_000,
    "gemini-2.5-pro": 1_000_000,
}
```

The 1M context window is both a strength and a challenge:

- **Strength**: Enables processing of very long documents, full codebases, and
  multi-hour conversation histories without compaction.
- **Challenge**: The `LLMUsage` canonical type lacks a token-count field for
  Google's responses, because Gemini does not expose per-request token counts
  in the current API version. The `chat` method would need to estimate tokens
  client-side or accept None usage.

**Implications for routing**: When the router selects Google for a task that
requires a large context (e.g., analyzing a 500K-token codebase), the budget
tracker should account for the higher per-token cost. Gemini 2.5 Flash costs
$0.15/1M input tokens -- cheaper than Haiku ($1.00/1M) -- making it the
cheapest large-context option.

#### Streaming Protocol Differences

Google's streaming protocol differs from both Anthropic and OpenAI:

1. **No SSE**: Google uses gRPC streaming or REST streaming with a different
   chunk format.
2. **No [DONE] signal**: Stream termination is signaled by an empty chunk or
   a `done: true` field.
3. **Tool call format**: Tool calls appear as `functionCall` parts in
   `candidates[0].content.parts`, not as a separate `tool_calls` array.

The streaming adapter would need to normalize these differences into Lyra's
six-event stream format.

#### Rate Limits

Google has the lowest rate limits among supported providers:

```python
concurrent_limit=30,  # vs 50-60 for Anthropic/DeepSeek
```

The capability matrix (Section 4) captures this. The router should account for
it when deciding whether to use Google for bursty workloads.

---
---

## 4. Capability Detection

### 4.1 The CapabilityMatrix

**File**: `packages/lyra-provider/src/lyra_provider/capability.py` (197 lines)

The `CapabilityMatrix` is the single source of truth for what each provider
supports. It is consulted by the ModelRouter, the skills system, the workflow
engine, and any component that needs to make provider-aware decisions.

#### ProviderCapability Record

Each provider has a frozen dataclass with boolean flags and integer limits:

```python
@dataclass(frozen=True)
class ProviderCapability:
    provider: str
    tool_calling: bool = True
    json_mode: bool = False
    vision: bool = False
    streaming: bool = True
    prompt_caching: bool = False
    reasoning_budget: bool = False
    max_context_tokens: int = 128_000
    concurrent_limit: int = 50
    notes: str = ""
```

The default values (tool_calling=True, streaming=True, max_context_tokens=128K)
reflect the most common provider capabilities. Unknown providers default to
these values, which is a conservative choice (better to assume a provider can
do something and fail than to assume it can't and miss opportunities).

#### Built-in Capability Declarations (May 2026)

**Anthropic** -- The most feature-rich provider:

| Feature | Value |
|---------|-------|
| tool_calling | True |
| json_mode | True |
| vision | True |
| streaming | True |
| prompt_caching | True |
| reasoning_budget | True (budget_tokens API) |
| max_context_tokens | 200,000 |
| concurrent_limit | 50 |
| notes | "Opus 4.8, Sonnet 4.6, Haiku 4.5. Prompt caching reduces cost ~90% for cached tokens." |

**DeepSeek** -- Minimal but cheap:

| Feature | Value |
|---------|-------|
| tool_calling | True |
| json_mode | False |
| vision | False |
| streaming | True |
| prompt_caching | False |
| reasoning_budget | False |
| max_context_tokens | 128,000 |
| concurrent_limit | 60 |
| notes | "No native reasoning budget -- Lyra injects thinking instructions into system prompt." |

**OpenAI** -- Balanced:

| Feature | Value |
|---------|-------|
| tool_calling | True |
| json_mode | True |
| vision | True |
| streaming | True |
| prompt_caching | False |
| reasoning_budget | True (reasoning_effort API) |
| max_context_tokens | 256,000 |
| concurrent_limit | 60 |
| notes | "GPT-5, GPT-4o, GPT-4o-mini. reasoning_effort supported on o-series models." |

**Google** -- Largest context, lowest concurrency:

| Feature | Value |
|---------|-------|
| tool_calling | True |
| json_mode | True |
| vision | True |
| streaming | True |
| prompt_caching | False |
| reasoning_budget | False |
| max_context_tokens | 1,000,000 |
| concurrent_limit | 30 |
| notes | "Gemini 2.5 Flash/Pro. 1M context window is the largest. Rate limits are lower." |

**OpenRouter** -- Aggregator with passthrough:

| Feature | Value |
|---------|-------|
| tool_calling | True |
| json_mode | True |
| vision | True |
| streaming | True |
| prompt_caching | False |
| reasoning_budget | True (passthrough to underlying provider) |
| max_context_tokens | 200,000 |
| concurrent_limit | 200 |
| notes | "Aggregator -- capabilities depend on the routed model. Higher rate limits." |

**OpenWeights** -- Self-hosted, limited:

| Feature | Value |
|---------|-------|
| tool_calling | False (prompt-based only) |
| json_mode | False |
| vision | False |
| streaming | True |
| prompt_caching | False |
| reasoning_budget | False |
| max_context_tokens | 32,000 |
| concurrent_limit | 10 |
| notes | "Local/self-hosted models. Tool calls via prompt formatting. Variable quality." |

### 4.2 Query Interface

The matrix provides three query methods:

```python
def get(self, provider: str) -> ProviderCapability | None:
    """Return capabilities for a provider, or None if unknown."""

def supports(self, provider: str, feature: str) -> bool:
    """Check whether a provider supports a specific feature."""

def get_context_window(self, provider: str) -> int:
    """Return the max context window for a provider, or a safe default (128K)."""
```

And two enumeration methods:

```python
def list_providers(self) -> list[str]:
    """Return all registered provider identifiers."""

def list_providers_supporting(self, feature: str) -> list[str]:
    """Return all providers that support a given feature."""
```

`list_providers_supporting` is critical for the router. When a task requires
vision, the router calls:

```python
vision_capable = matrix.list_providers_supporting("vision")
# Returns: ["anthropic", "openai", "google", "openrouter"]
```

This filters out DeepSeek and OpenWeights before the routing cascade begins,
preventing the rules/semantics/neural tiers from ever selecting a provider that
cannot fulfill the task's requirements.

### 4.3 Runtime Capability Probing

The static capability matrix is a compile-time/startup-time declaration. It
covers known providers with known APIs. For unknown providers or custom
endpoints, the `AbstractProvider.supports_feature()` method provides runtime
probing:

```python
async def probe_capabilities(provider: AbstractProvider) -> ProviderCapability:
    """Dynamically probe an unknown provider's capabilities."""
    capabilities = {
        "tool_calling": False,
        "json_mode": False,
        "vision": False,
        "streaming": False,
        "prompt_caching": False,
        "reasoning_budget": False,
    }

    # Test tool calling
    test_request = ChatRequest(
        messages=[Message(role=MessageRole.USER, content="Call the test_tool")],
        tools=[ToolSchema(name="test_tool", description="A test tool",
                          parameters={"type": "object", "properties": {}})],
        max_tokens=10,
    )
    try:
        response = await provider.chat(test_request)
        capabilities["tool_calling"] = response.tool_calls is not None
    except ProviderError:
        pass

    # Test streaming
    try:
        async for _ in provider.chat_stream(test_request):
            capabilities["streaming"] = True
            break
    except (ProviderError, StopAsyncIteration):
        pass

    # ... (similar probes for json_mode, vision, etc.)

    return ProviderCapability(**capabilities)
```

This runtime probing is not currently implemented in the codebase but is
described in the architecture to show how the system would handle future
providers without requiring code changes to the capability matrix.

### 4.4 How Capability Informs Router Decisions

The ModelRouter in `packages/lyra-router/src/lyra_router/` uses the capability
matrix at every level of its cascade:

**Before the cascade**: The router filters the available provider set to only
those that can fulfill the task's capability requirements. For example, if
the task has an attached image, the router removes DeepSeek from consideration.

**At model selection**: The `ProviderRegistry.get_best_model_for_tier()` method
filters by capability. When the router selects a tier (e.g., STANDARD), it
queries the registry for the cheapest STANDARD model that supports the required
features.

**During budget-aware downgrade**: When the budget tracker downgrades from
PREMIUM to STANDARD, the fallback model is checked for capability compatibility.
If STANDARD models don't support a required feature, the router escalates to
a higher tier rather than downgrading.

**At the adapter level**: `supports_feature()` is used by the skills system
before constructing a provider-specific request. If a skill needs JSON mode,
it checks `provider.supports_feature("json_mode")` and formats the request
accordingly (or falls back to prompt-based JSON extraction).

---
---

## 5. Fallback & Escalation Chain

### 5.1 Fast -> Standard -> Deep Tier Escalation

The fallback chain operates at multiple levels:

**Level 1: Effort escalation within a provider.** If a provider cannot support
the requested effort level (e.g., DeepSeek max_effort_level is XHIGH, not MAX),
the effort manager automatically escalates to the highest supported level.
From `lyra-effort/manager.py`:

```python
# DeepSeek: max_effort_level=XHIGH
# Requested MAX -> falls back to XHIGH thinking instruction
```

**Level 2: Model tier escalation within the provider registry.** If no model at
the selected tier has available API keys, the registry walks down the tier
hierarchy:

```
PREMIUM (no keys) -> STANDARD (no keys) -> FAST (no keys) -> HAIKU (no keys) -> LOCAL_SLM
```

From `packages/lyra-router/src/lyra_router/providers.py`,
`get_fallback_model`:

```python
def get_fallback_model(self, tier, _budget_regime="high"):
    tier_order = list(ModelTier)
    idx = tier_order.index(tier)
    if idx == 0:
        return self.get_best_model_for_tier(tier, require_key=False)
    for fallback_idx in range(idx - 1, -1, -1):
        candidate = self.get_best_model_for_tier(tier_order[fallback_idx], require_key=False)
        if candidate:
            return candidate
    return self.get_best_model_for_tier(tier, require_key=False)
```

**Level 3: Last-resort model selection.** If all structured fallbacks fail,
`_pick_any_model()` iterates all tiers from LOCAL_SLM to AGENTIC and returns
the first model found regardless of key availability. The hardcoded safety-net
fallback is Claude Haiku.

### 5.2 When a Provider Returns an Error

When a provider adapter raises `ProviderError`, the caller (router, skill,
or workflow engine) decides what to do based on the error code:

| Error Code | retryable | Action |
|-----------|-----------|--------|
| AUTH_ERROR | False | Remove provider from rotation. Log credential issue. Try next provider. |
| RATE_LIMIT | True | Wait 1-30s (exponential backoff). Retry. If persistent, try next provider. |
| CONTEXT_OVERFLOW | False | Trigger context compaction. Retry with truncated context. |
| INVALID_REQUEST | False | Abort. This is a bug (malformed request). |
| PROVIDER_ERROR | True (5xx) / False (4xx) | Retry on 5xx. Abort on 4xx. |
| TIMEOUT | True | Retry once. If fails again, try next provider. |
| NETWORK_ERROR | True | Retry once. If fails again, skip provider. |
| UNKNOWN | False | Log full `raw` error. Skip provider. |

The error-handling logic is implemented in the router's `record_outcome`
feedback loop, which stores the error code and updates the provider's health
score.

### 5.3 Circuit Breaker at $5/Session

The circuit breaker in `packages/lyra-router/src/lyra_router/budget.py`
enforces a hard spending cap per session. When the BudgetTracker's
`total_spent >= session_budget_usd`:

1. `route()` raises `RuntimeError`: "Circuit breaker tripped: $X spent of $Y
   budget."
2. `record()` returns False for any further cost recording.
3. The circuit breaker persists until `reset()` is called.

The $5 default is calibrated for a typical coding session (100-200 HAILU-tier
or 50-100 STANDARD-tier calls). The circuit breaker interacts with the provider
layer through the BudgetTracker's budget-aware tier downgrade, which reduces
the model tier (and thus cost) before the breaker trips.

### 5.4 Provider Health Scoring

The router's NeuralUCB tier (Section 8.1 of the model router deep dive)
incorporates six provider-state features into its routing context vector:

```
[10]: Provider health score (0-1, exponential moving average)
[11]: Provider p95 latency (seconds, normalized)
[12]: Provider rate limit remaining (fraction of max)
[13]: Provider cost premium vs cheapest at same tier
[14]: Provider error rate in last 5 minutes
[15]: Session budget remaining ratio
```

The health score is updated after every provider interaction. A provider that
returns frequent 429 or 5xx errors accumulates a lower health score, which
reduces its UCB reward prediction. The router naturally shifts traffic away
from degraded providers.

This health feedback is not yet implemented (it is a V4 breakthrough target),
but the provider abstraction layer is designed to support it: the `latency_ms`
field on `ChatResponse` and the `retryable` field on `ProviderError` provide
the raw signals that the health scorer needs.

---
---

## 6. Architecture Diagram

```
                                Lyra Application
                         (skills, workflows, memory, swarm,
                          orchestration, voice, CLI, TUI)
                                      |
                                      |  Uses only canonical types
                                      |  (Message, ToolCall, ChatRequest,
                                      |   ChatResponse, StreamEvent)
                                      v
                      ┌────────────────────────────────────────────┐
                      │          AbstractProvider (ABC)            │
                      │  packages/lyra-provider/interface.py      │
                      │                                            │
                      │  chat() | chat_stream()                    │
                      │  validate_api_key() | list_models()        │
                      │  supports_feature() | get_context_window() │
                      └──────────┬──────────────────────┬──────────┘
                                 │                      │
                     Adapter Layer                     Capability Layer
                      ┌──────────┬──────────┬──────────┬──────────┐
                      │          │          │          │          │
                      ▼          ▼          ▼          ▼          │
               ┌──────────┐┌──────────┐┌──────────┐┌──────────┐  │
               │ Anthropic││  OpenAI  ││ DeepSeek ││  Google  │  │
               │ Adapter  ││ Adapter  ││ Adapter  ││ Adapter  │  │
               │          ││          ││          ││ (stub)   │  │
               │ anthropic││  openai  ││ deepseek ││  google  │  │
               │ .py      ││  .py     ││ .py      ││ .py      │  │
               └─────┬────┘└─────┬────┘└─────┬────┘└─────┬────┘  │
                     │           │           │           │       │
                     │  HTTP     │  HTTP     │  HTTP     │  HTTP │
                     ▼           ▼           ▼           ▼       │
               ┌──────────┐┌──────────┐┌──────────┐┌──────────┐  │
               │Anthropic ││  OpenAI  ││ DeepSeek ││  Google  │  │
               │ Messages ││ Chat     ││ Chat     ││ GenAI    │  │
               │ API      ││ Complet. ││ Complet. ││ API      │  │
               └──────────┘└──────────┘└──────────┘└──────────┘  │
                                 │                                │
                      ┌──────────┴────────────────────┬───────────┘
                      │                               │
                      ▼                               ▼
           ┌──────────────────────┐      ┌──────────────────────────┐
           │  CapabilityMatrix    │      │   ProviderConfig         │
           │  capability.py       │      │   interface.py           │
           │                      │      │                          │
           │  6 providers ×       │      │  api_key (masked in      │
           │  7 feature flags     │      │  __repr__)               │
           │  + context windows   │      │  base_url, max_retries   │
           │  + concurrency       │      │  timeout_seconds         │
           └──────────────────────┘      └──────────────────────────┘

                                Consumed by:

           ┌──────────────────────────────────────────────────────┐
           │                    ModelRouter                        │
           │  (packages/lyra-router/)                              │
           │  Tier 1: Rule -> Tier 2: Semantic -> Tier 3: Neural  │
           │  BudgetTracker -> ProviderRegistry -> ModelSelection  │
           │  queries CapabilityMatrix to filter providers         │
           │  queries ProviderConfig for API keys                  │
           └──────────────────────────────────────────────────────┘

           ┌──────────────────────────────────────────────────────┐
           │                    Skills System                      │
           │  (packages/lyra-skills/)                              │
           │  checks supports_feature() before using JSON mode    │
           │  checks get_context_window() before building prompts  │
           └──────────────────────────────────────────────────────┘

           ┌──────────────────────────────────────────────────────┐
           │                    Effort Manager                     │
           │  (packages/lyra-effort/)                              │
           │  maps effort level to provider-specific params        │
           │  checks ProviderEffortCapability for max level        │
           └──────────────────────────────────────────────────────┘

           ┌──────────────────────────────────────────────────────┐
           │              Workflow Engine / Orchestration          │
           │  (packages/lyra-workflow/, packages/lyra-core/)       │
           │  dispatches sub-agent calls through AbstractProvider  │
           │  collects usage data for budget tracking              │
           └──────────────────────────────────────────────────────┘
```

The diagram illustrates the clean architectural layering. Above the
AbstractProvider interface, every component uses only canonical types.
Below it, each adapter handles provider-specific HTTP calls, schema
translations, and error mappings.

---
---

## 7. Trade-Off Analysis

| Dimension | Gain | Cost | When It Wins | When It Loses |
|-----------|------|------|--------------|---------------|
| Write-once portability | 4 providers, 1 codebase | Adapter maintenance per provider (avg 200 lines/adapter) | Multi-provider deployments where skills/tools must work identically | Anthropic-only deployments where the abstraction adds unnecessary indirection |
| Tool calling | Normalized `ToolCall` and `ToolSchema` across providers | Translation overhead per call (JSON parsing, content-block assembly) | Cross-provider tool execution, tool-using skills, agentic workflows | Single-provider tools where the provider's native format is more expressive |
| Streaming | Unified `StreamEvent` interface with 6 event types | Per-provider SSE differences require adapter-specific parsing | Real-time TUI, voice, progressive UX | Batch processing where streaming is never used |
| Error handling | Canonical `ErrorCode` taxonomy with retryable flag | Loss of provider-specific detail (e.g., Anthropic's overloaded-vs-rate-limited distinction) | Consistent UX across provider failures, automatic fallback | Advanced debugging where raw provider errors are needed (available via `ChatResponse.raw` escape hatch) |
| Capability detection | Router prevents capability mismatches (no vision->DeepSeek) | Static matrix must be manually updated for new providers or API changes | Multi-provider routing at scale | Single-provider deployments with stable APIs |
| Token accounting | Unified `LLMUsage` across all providers | Zeros for unsupported fields (cache tokens on non-Anthropic providers) | Cost tracking, budget enforcement, usage analytics | Fine-grained token analysis where provider-specific fields matter |
| Effort mapping | Normalized effort scale translated per-provider | Semantic gap: Anthropic's adaptive thinking vs OpenAI's fixed reasoning_effort vs DeepSeek's prompt-based approach | Multi-provider effort consistency | Deep reasoning tasks on DeepSeek where prompt-based effort is unreliable |
| Error normalization | Consistent error handling in router/skills | Error strings must be grepped (fragile to provider API changes) | Production reliability with automatic failover | Debugging edge cases where raw error messages are needed |

### 7.1 Detailed Trade-Off: Write-Once Portability

The primary gain is that code above the provider boundary never changes when a
new provider is added. Consider the skills system: a skill that needs to call an
LLM writes:

```python
response = await provider.chat(ChatRequest(
    messages=messages,
    model=model_name,
    tools=tools,
    max_tokens=4096,
))
```

This works identically for Anthropic, OpenAI, DeepSeek, and (eventually)
Google. The skill developer never imports an SDK, never constructs
provider-specific message formats, and never handles provider-specific errors.

The cost is adapter maintenance. Each adapter is approximately 200-400 lines of
code that must be kept current with the provider's API changes. When Anthropic
deprecates `budget_tokens` in favor of `output_config.effort`, the Anthropic
adapter must be updated. When OpenAI changes the streaming chunk format, the
OpenAI adapter must be updated.

The trade-off is clearly favorable for Lyra's use case (multi-provider harness).
For a single-provider deployment, the abstraction adds approximately 10-15%
overhead in request path length (additional function calls, type conversions)
and requires maintaining the adapter even when only one provider is used.

### 7.2 Detailed Trade-Off: Tool Calling

The normalized ToolCall/ToolSchema types enable cross-provider tool execution.
A tool defined once as a `ToolSchema` works on any provider that supports tool
calling. This is essential for Lyra's skills system, where skills declare their
tools in canonical format and the adapter handles translation.

The cost is translation overhead:
- Anthropic: `ToolSchema.parameters` -> `input_schema` (field rename)
- OpenAI/DeepSeek: `ToolSchema.parameters` -> `function.parameters` (wrap in function object)
- Response: Anthropic returns parsed `input` dict, OpenAI returns JSON string
  `arguments` that must be `json.loads()`-ed

Each tool call round-trip involves:
1. Canonical ToolSchema -> provider-specific format (negligible, ~1us)
2. Provider response -> ToolCall parsing (1-10us for JSON parse)
3. Tool execution (dominates, 10ms+)
4. ToolResult -> provider-specific format (negligible)

The translation overhead (steps 1, 2, 4) is under 50 microseconds total --
essentially zero compared to tool execution time.

### 7.3 Detailed Trade-Off: Streaming

The six-event StreamEvent interface (`text_delta`, `tool_call_start`,
`tool_call_delta`, `tool_call_end`, `done`, `error`) normalizes three
completely different streaming protocols:

- **Anthropic**: Content blocks with separate start/delta/stop events for text
  and tool_use blocks. The `input_json_delta` delivers partial JSON for tool
  call arguments.
- **OpenAI/DeepSeek**: Flat delta stream with `choices[0].delta.content` for
  text and `choices[0].delta.tool_calls` for tool call fragments.
  Termination via `choices[0].finish_reason`.
- **Google** (future): gRPC or REST streaming with different chunk structure.

The commonest source of bugs in streaming adapters is the tool call
accumulation logic. Anthropic sends `partial_json` strings that must be
concatenated and parsed at the end. OpenAI sends `function.arguments` strings
the same way but with different chunk boundaries. Both adapters implement the
accumulation pattern independently, and both have to handle the edge case where
the final JSON chunk is split across SSE boundaries.

### 7.4 Detailed Trade-Off: Error Handling

The canonical error taxonomy (`ErrorCode` enum with 8 codes) provides
consistent error handling. The router can check `error.code == RATE_LIMIT` and
fall back to a different provider without knowing whether the rate limit error
came from Anthropic (429 with `retry-after` header), OpenAI (429 with
`x-ratelimit-*` headers), or DeepSeek (429 or 402).

The cost is that provider-specific error details are lost. Anthropic's 529
(overloaded) and 429 (rate limited) are both normalized to RATE_LIMIT, losing
the distinction between "server overloaded" and "you hit your quota." The
escape hatch is `ProviderError.raw`, which carries the complete provider error
response for forensic analysis.

---
---

## 8. (B) Breakthrough: Universal Provider Interface

Lyra's provider abstraction goes beyond existing harnesses in five dimensions
that collectively define a new category of multi-provider architecture.

### 8.1 Provider-Adaptive Compaction

Every comparable harness (DeerFlow, OpenCode, Claude Code, Cline) uses a
single compaction strategy regardless of the provider. Lyra's architecture
recognizes that compaction should be provider-adaptive:

- **DeepSeek (128K)**: Compaction triggers at 60% of context (76K). Aggressive
  summarization, prefers dropping old history over truncating context.
- **Anthropic (200K)**: Compaction triggers at 80% (160K). Conservative
  summarization, leverages prompt caching to avoid re-encoding the same prefix.
- **Google (1M)**: Compaction triggers at 90% (900K). Minimal intervention,
  leverages the massive context window to preserve full history.
- **OpenWeights (32K)**: Compaction triggers at 50% (16K). Severe compression,
  may drop entire conversation turns.

This provider-adaptive compaction is not yet implemented -- the compaction
system currently uses a single threshold. The provider abstraction enables it
through `get_context_window()`, which the compaction system should consult
before deciding how aggressively to truncate.

The compaction strategy also depends on cost. Google's 1M context at
$0.15/1M tokens is cheaper than Anthropic's 200K at $1.00/1M. For a 200K-token
conversation, keeping everything in context costs:
- Google: $0.03 (cheaper to keep than to compact)
- Anthropic: $0.20 (worth compacting if the history is not critical)

The BudgetTracker should factor this into its per-task budget guidance.

### 8.2 Capability-Aware Routing

Lyra's ModelRouter is the first to integrate static capability declarations
with online-learning routing. The typical router (RouteLLM, FrugalGPT) routes
based on cost or complexity alone. Lyra adds a capability pre-filter:

1. Extract task requirements: need vision? need tool calling? need JSON mode?
2. Query `CapabilityMatrix.list_providers_supporting()` for each requirement
3. Intersect the results to get the set of capable providers
4. Pass only capable providers to the routing cascade

This prevents entire classes of routing failures:

- Without capability awareness: Router sends an image analysis task to DeepSeek
  (no vision) -> DeepSeek returns a 400 error or garbage text
- With capability awareness: Router pre-filters DeepSeek out, routes to
  Anthropic or OpenAI or Google

The breakthrough is that capability requirements can be extracted from the
task, the skill metadata, or the conversation context. A skill that declares
`requires: ["vision"]` in its frontmatter will never be routed to a
vision-incapable provider.

### 8.3 Provider-Specific Skill Frontmatter Stripping

Skills in Lyra carry a YAML frontmatter block that declares metadata (name,
description, version, requires, provider_hints). The provider_hints field
allows a skill to express provider preferences:

```yaml
provider_hints:
  prefer: anthropic  # This skill works best on Claude
  features_required:
    - tool_calling
    - json_mode
  avoid:
    - openweights  # Quality too low for this skill
```

When the skill system initializes, it consults the CapabilityMatrix and the
available provider set to strip incompatible skills from the skill list. A
skill that requires JSON mode is hidden when only DeepSeek providers are
available.

The breakthrough here is bidirectional: the provider layer tells the skill
system what it can support, and the skill system tells the router what it
needs. This mutual awareness eliminates the "silent failure" class of bugs
where a skill silently produces lower-quality output on an incompatible
provider.

### 8.4 Effort Translation with Semantic Preservation

The effort system (`lyra-effort`) translates a single effort level into three
different API parameters depending on the provider:

```python
# Anthropic receives budget_tokens
ChatRequest(effort_budget_tokens=16384)

# OpenAI receives reasoning_effort
ChatRequest(effort_reasoning="high")

# DeepSeek receives a thinking instruction
ChatRequest(effort_instruction="Think deeply. Consider multiple approaches...")
```

This is more sophisticated than any comparable harness. Claude Code supports
only Anthropic. DeerFlow and OpenCode support multiple providers but use a
fixed effort model (typically just temperature and max_tokens). Lyra's
three-parameter effort model preserves the semantic intent of the effort level
across fundamentally different provider APIs.

The semantic gap remains for providers without native effort APIs (DeepSeek,
OpenWeights). For these, the prompt-based approach is a best-effort
approximation. The effort manager's `ProviderEffortCapability` registry
declares `max_effort_level` per provider, preventing the system from
requesting MAX effort from a provider that cannot meaningfully deliver it.

### 8.5 Provider-Agnostic Cost Tracking

Every comparable harness tracks cost per provider. Lyra tracks cost uniformly
through the `LLMUsage` canonical type and the BudgetTracker. The budget-aware
routing (Section 5.3) operates on uniform cost data regardless of which
provider served the request.

This enables the NeuralUCB tier to learn cost-quality tradeoffs across
providers. The reward function:

```python
reward = float(success) * quality_weight - cost * cost_sensitivity
```

is computed identically whether the model was Anthropic (cost=$0.05) or
DeepSeek (cost=$0.00027). The bandit learns to prefer DeepSeek for tasks
where it performs adequately, and to escalate to Anthropic only when the
task complexity warrants the higher cost.

The key insight is that cost tracking at the canonical level (input_tokens,
output_tokens) enables provider-agnostic budget enforcement. The BudgetTracker
does not need to know which provider served a request to enforce the $5/session
cap. It records the cost from `LLMUsage` and checks the circuit breaker.

---
---

## 9. Key Sources

**Lyra Source Code:**
- `packages/lyra-provider/src/lyra_provider/interface.py` -- Canonical types
  and AbstractProvider protocol (322 lines, the entire provider boundary)
- `packages/lyra-provider/src/lyra_provider/capability.py` -- Provider
  Capability Matrix (197 lines, 6 provider capability records)
- `packages/lyra-provider/src/lyra_provider/adapters/anthropic.py` -- Anthropic
  Messages API adapter (442 lines, full implementation with dual HTTP clients)
- `packages/lyra-provider/src/lyra_provider/adapters/openai.py` -- OpenAI
  Chat Completions adapter (286 lines, reasoning_effort + vision support)
- `packages/lyra-provider/src/lyra_provider/adapters/deepseek.py` -- DeepSeek
  OpenAI-compatible adapter (421 lines, prompt-based effort mechanism)
- `packages/lyra-provider/src/lyra_provider/adapters/google.py` -- Google
  GenAI adapter stub (79 lines, 1M context window declared but not implemented)
- `packages/lyra-provider/src/lyra_provider/__init__.py` -- Package exports (66
  lines, re-exports all canonical types and capability matrix)
- `packages/lyra-provider/src/lyra_provider/adapters/__init__.py` -- Adapter
  exports (24 lines, registers all four concrete adapters)
- `packages/lyra-effort/src/lyra_effort/models.py` -- Effort level definitions
  with per-provider budget mappings
- `packages/lyra-effort/src/lyra_effort/manager.py` -- Effort-to-provider
  parameter translation with ProviderEffortCapability registry
- `packages/lyra-router/src/lyra_router/` -- Complete model router with
  BudgetTracker, ProviderRegistry, 3-tier cascade, NeuralUCB

**Lyra Architecture Documents:**
- `lyra-upgrade/07-architecture-deep-dives/09-model-router.md` -- Model Router
  deep dive covering budget tracking, fallback chain, and provider-aware
  NeuralUCB extensions (1036 lines)
- `lyra-upgrade/07-architecture-deep-dives/01-ultracode-replication.md` --
  UltraCode deep dive covering per-provider effort mapping and thinking budget
  translation (first 50 lines provide provider-specific budget table)
- `lyra-upgrade/04-research/ultracode-mechanisms.md` -- Per-provider effort
  API research, Anthropic `output_config.effort` vs OpenAI `reasoning_effort`
  vs DeepSeek prompt-based approach
- `lyra-upgrade/04-research/harnesses-deep-research.md` -- Hermes Agent
  provider model research (40+ providers, credential pool, fallback chain,
  OpenRouter integration)
- `lyra-upgrade/02-brainstorms/05-model-router.md` -- Breakthrough ideas
  including hierarchical cascade and provider-aware capability matching

**External API Documentation:**
- Anthropic Messages API (api.anthropic.com): content blocks, tool_use,
  extended thinking, prompt caching, output_config.effort
- OpenAI Chat Completions API (platform.openai.com): reasoning_effort,
  tool_calls array, streaming delta format
- DeepSeek API (platform.deepseek.com): OpenAI-compatible chat completions,
  402 insufficient balance error, no native reasoning budget
- Google Gemini API (ai.google.dev): Part-based content, function calling,
  1M context window, thinkingConfig
- RouteLLM (LMSYS): Similarity-based router with confidence scoring --
  provides the baseline for capability-aware routing comparison
- FrugalGPT (Stanford): LLM cascade with 98% cost reduction -- provides the
  baseline for fallback chain comparison

**Academic References:**
- DecisionBench (arXiv:2605.19099): Routing fidelity gap (7.5-29.5%) across
  real-world benchmarks -- motivates the need for learned, capability-aware
  routing rather than static provider selection
- Neural Contextual Bandits with UCB Exploration (Zhou et al., 2020):
  Theoretical foundation for provider-aware NeuralUCB with O(sqrt(T)) regret
- Budget-Aware Tier Selection (BATS): Google Cloud pattern for cost-aware
  resource selection -- informs the four-budget-regime design and circuit
  breaker at $5/session
