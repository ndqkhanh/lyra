# Provider Abstraction System — System Design

## Executive Summary

This document details the implementation design of Lyra's provider abstraction layer, covering data models, algorithms, APIs, state management, and scalability considerations. The system normalizes 16 LLM providers into a unified interface supporting 200K-1M token contexts with <100μs translation overhead.

---

## Data Models

### 1. Core Message Types

#### MessageRole Enum

```python
class MessageRole(str, Enum):
    """Four canonical roles across all providers."""
    SYSTEM = "system"      # System instructions
    USER = "user"          # User inputs
    ASSISTANT = "assistant"  # Model outputs
    TOOL = "tool"          # Tool execution results
```

**Design rationale:**
- Flat 4-role taxonomy (no nested hierarchies)
- String enum for JSON serialization compatibility
- Maps to all major provider formats:
  - Anthropic: user/assistant (system separate, tool→user with tool_result)
  - OpenAI/DeepSeek: system/user/assistant/tool (1:1 mapping)
  - Google: user/model/function (model=assistant, function=tool)

#### Message Class

```python
@dataclass
class Message:
    role: MessageRole
    content: str | list[dict[str, Any]]  # Text or multimodal
    tool_calls: list[ToolCall] | None = None
    tool_result: ToolResult | None = None
    name: str | None = None
```

**Field semantics:**
- `content`: String for text-only, list for vision (text + image blocks)
- `tool_calls`: Present on ASSISTANT messages with tool invocations
- `tool_result`: Present on TOOL messages with execution results
- `name`: Optional identifier for multi-agent scenarios

**Invariants:**
- `tool_calls` and `tool_result` are mutually exclusive
- ASSISTANT messages may have both `content` and `tool_calls`
- TOOL messages must have `tool_result` field populated

#### ToolCall Class

```python
@dataclass(frozen=True)
class ToolCall:
    id: str              # Unique identifier for tracking
    name: str            # Tool function name
    arguments: dict[str, Any]  # Always parsed dict, never JSON string
```

**Immutability:** Frozen to prevent bugs during:
- Streaming accumulation (multiple references to same object)
- Tool execution dispatch (parallel tool calls)
- Error recovery (rollback requires original state)

**Normalization:** `arguments` field is always a parsed Python dict:
- Anthropic returns `input` as dict → copy directly
- OpenAI returns `arguments` as JSON string → `json.loads()` in adapter
- DeepSeek same as OpenAI

#### ToolSchema Class

```python
@dataclass(frozen=True)
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object
```

**JSON Schema standard:** All providers accept JSON Schema for parameter definitions:
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string", "description": "Search query"},
    "limit": {"type": "integer", "default": 10}
  },
  "required": ["query"]
}
```

Adapters translate the wrapping:
- Anthropic: `{"name": "...", "input_schema": {...}}`
- OpenAI/DeepSeek: `{"type": "function", "function": {"name": "...", "parameters": {...}}}`
- Google: `{"name": "...", "parameters": {...}}`

### 2. Request/Response Models

#### ChatRequest

```python
@dataclass
class ChatRequest:
    messages: list[Message]
    model: str
    tools: list[ToolSchema] | None = None
    max_tokens: int = 4096
    temperature: float | None = None
    stream: bool = False
    # Effort parameters
    effort_budget_tokens: int | None = None
    effort_instruction: str | None = None
    effort_reasoning: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
```

**Effort parameter semantics:**

| Parameter | Target Providers | Mechanism |
|-----------|-----------------|-----------|
| `effort_budget_tokens` | Anthropic | Maps to `thinking.budget_tokens` |
| `effort_reasoning` | OpenAI | Maps to `reasoning_effort` (low/medium/high) |
| `effort_instruction` | DeepSeek, Google | Injected into system prompt |

**Extra field:** Escape hatch for provider-specific parameters:
```python
# Anthropic seed for reproducibility
extra={"seed": 12345}

# OpenAI logprobs
extra={"logprobs": True, "top_logprobs": 5}
```

#### ChatResponse

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

**finish_reason values:**
- `"stop"`: Natural completion
- `"length"`: Hit max_tokens limit
- `"tool_calls"`: Model wants to invoke tools
- `"content_filter"`: Blocked by safety filter

#### LLMUsage

```python
@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
```

**Provider mappings:**

| Provider | input_tokens | output_tokens | Cache Support |
|----------|--------------|---------------|---------------|
| Anthropic | `input_tokens` | `output_tokens` | ✅ cache_read/write |
| OpenAI | `prompt_tokens` | `completion_tokens` | ❌ |
| DeepSeek | `prompt_tokens` | `completion_tokens` | ❌ |
| Google | Not exposed | Not exposed | ❌ |

### 3. Streaming Models

#### StreamEvent

```python
@dataclass(frozen=True)
class StreamEvent:
    type: str  # Event discriminator
    content: str = ""
    tool_call: ToolCall | None = None
    usage: LLMUsage | None = None
    error: str | None = None
```

**Event types and payloads:**

| Type | Fields | Meaning |
|------|--------|---------|
| `text_delta` | `content` | Incremental text chunk |
| `tool_call_start` | `tool_call` (partial) | Tool invocation begins |
| `tool_call_delta` | (internal accumulation) | Tool arguments fragment |
| `tool_call_end` | `tool_call` (complete) | Tool invocation complete |
| `done` | `usage` | Stream finished |
| `error` | `error` | Stream errored |

**Streaming state machine:**
```
START
  ↓
text_delta* → done
  or
tool_call_start → (tool_call_delta*) → tool_call_end → done
  or
error (terminal)
```

### 4. Error Models

#### ErrorCode Enum

```python
class ErrorCode(str, Enum):
    AUTH_ERROR = "auth_error"           # 401, invalid API key
    RATE_LIMIT = "rate_limit"           # 429, quota exceeded
    CONTEXT_OVERFLOW = "context_overflow"  # Too many tokens
    INVALID_REQUEST = "invalid_request"  # 400, malformed
    PROVIDER_ERROR = "provider_error"    # 5xx, provider issue
    TIMEOUT = "timeout"                  # Request timeout
    NETWORK_ERROR = "network_error"      # Connection failure
    UNKNOWN = "unknown"                  # Uncategorized
```

#### ProviderError

```python
@dataclass(frozen=True)
class ProviderError(Exception):
    code: ErrorCode
    message: str
    provider: str = ""
    retryable: bool = False
    raw: Any = None
```

**Retryable classification:**

| ErrorCode | retryable | Router Action |
|-----------|-----------|---------------|
| AUTH_ERROR | False | Remove provider from rotation |
| RATE_LIMIT | True | Wait + retry or try next provider |
| CONTEXT_OVERFLOW | False | Trigger compaction, retry |
| INVALID_REQUEST | False | Terminal (bug in request) |
| PROVIDER_ERROR | Depends on 4xx vs 5xx | 5xx→retry, 4xx→abort |
| TIMEOUT | True | Retry once |
| NETWORK_ERROR | True | Retry once |

---

## Algorithms

### 1. Message Translation Algorithm

**Canonical → Provider Format**

```python
def translate_messages(messages: list[Message], provider: str) -> Any:
    """
    Algorithm: Provider-specific translation with role normalization.
    
    Complexity: O(n*m) where n=messages, m=avg content blocks per message
    """
    if provider == "anthropic":
        # Extract system messages (separate parameter in Anthropic)
        system = [m for m in messages if m.role == MessageRole.SYSTEM]
        conversation = [m for m in messages if m.role != MessageRole.SYSTEM]
        
        result = {
            "system": "\n".join(m.content for m in system) if system else None,
            "messages": []
        }
        
        for msg in conversation:
            if msg.role == MessageRole.TOOL:
                # Tool results → user message with tool_result blocks
                result["messages"].append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_result.tool_call_id,
                        "content": msg.content,
                        "is_error": msg.tool_result.is_error
                    }]
                })
            elif msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                # Tool calls → tool_use content blocks
                result["messages"].append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments
                    } for tc in msg.tool_calls]
                })
            else:
                # Regular message
                result["messages"].append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        return result
    
    elif provider in ["openai", "deepseek"]:
        # Flat message array with tool_calls field
        result = []
        for msg in messages:
            if msg.role == MessageRole.TOOL:
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_result.tool_call_id,
                    "content": msg.content
                })
            elif msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                result.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [{
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    } for tc in msg.tool_calls]
                })
            else:
                result.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        return result
```

### 2. Streaming Accumulation Algorithm

**Tool Call Argument Buffering**

```python
async def stream_with_tool_accumulation(
    events: AsyncIterator[ProviderEvent]
) -> AsyncIterator[StreamEvent]:
    """
    Algorithm: Incremental JSON accumulation for tool call arguments.
    
    Problem: Providers stream tool arguments as JSON fragments that may
    split at any character boundary. Must accumulate and parse at end.
    
    State: Dict of tool_id → accumulated JSON string
    Complexity: O(n) where n = number of SSE chunks
    """
    tool_buffers: dict[str, str] = {}
    current_tool_id: str | None = None
    
    async for event in events:
        if event.type == "tool_call_start":
            current_tool_id = event.tool_id
            tool_buffers[current_tool_id] = ""
            yield StreamEvent(
                type="tool_call_start",
                tool_call=ToolCall(
                    id=current_tool_id,
                    name=event.tool_name,
                    arguments={}
                )
            )
        
        elif event.type == "tool_call_delta":
            if current_tool_id:
                tool_buffers[current_tool_id] += event.arguments_fragment
                # Don't yield — accumulate silently
        
        elif event.type == "tool_call_end":
            if current_tool_id:
                # Parse accumulated JSON
                try:
                    args = json.loads(tool_buffers[current_tool_id])
                except json.JSONDecodeError:
                    args = {}  # Fallback for malformed JSON
                
                yield StreamEvent(
                    type="tool_call_end",
                    tool_call=ToolCall(
                        id=current_tool_id,
                        name=event.tool_name,
                        arguments=args
                    )
                )
                current_tool_id = None
        
        elif event.type == "text_delta":
            yield StreamEvent(type="text_delta", content=event.text)
        
        elif event.type == "done":
            yield StreamEvent(type="done", usage=event.usage)
```

**Failure modes:**
- Split occurs mid-unicode character → httpx/aiohttp handle correctly
- Split occurs mid-JSON escape sequence → accumulate until valid
- Invalid JSON at end → empty dict `{}`

### 3. Error Translation Algorithm

**Provider Exception → ProviderError**

```python
def translate_error(error: Exception, provider: str) -> ProviderError:
    """
    Algorithm: Pattern matching on error strings + status codes.
    
    Input: Raw exception from HTTP client
    Output: Canonical ProviderError with ErrorCode
    Complexity: O(1) string matching
    """
    msg = str(error).lower()
    
    # HTTP status code extraction
    status_code = None
    if hasattr(error, 'status_code'):
        status_code = error.status_code
    elif hasattr(error, 'status'):
        status_code = error.status
    
    # Auth errors (401, 403, invalid key)
    if status_code in [401, 403] or any(
        pattern in msg for pattern in ["unauthorized", "invalid api key", "forbidden"]
    ):
        return ProviderError(
            code=ErrorCode.AUTH_ERROR,
            message=str(error),
            provider=provider,
            retryable=False,
            raw=error
        )
    
    # Rate limits (429, quota)
    if status_code == 429 or any(
        pattern in msg for pattern in ["rate limit", "quota", "too many requests"]
    ):
        return ProviderError(
            code=ErrorCode.RATE_LIMIT,
            message=str(error),
            provider=provider,
            retryable=True,
            raw=error
        )
    
    # Context overflow
    if any(pattern in msg for pattern in ["context", "too long", "token limit"]):
        return ProviderError(
            code=ErrorCode.CONTEXT_OVERFLOW,
            message=str(error),
            provider=provider,
            retryable=False,
            raw=error
        )
    
    # Invalid request (400)
    if status_code == 400 or "invalid" in msg:
        return ProviderError(
            code=ErrorCode.INVALID_REQUEST,
            message=str(error),
            provider=provider,
            retryable=False,
            raw=error
        )
    
    # Provider errors (5xx)
    if status_code and 500 <= status_code < 600:
        return ProviderError(
            code=ErrorCode.PROVIDER_ERROR,
            message=str(error),
            provider=provider,
            retryable=True,
            raw=error
        )
    
    # Timeouts
    if isinstance(error, asyncio.TimeoutError) or "timeout" in msg:
        return ProviderError(
            code=ErrorCode.TIMEOUT,
            message=str(error),
            provider=provider,
            retryable=True,
            raw=error
        )
    
    # Network errors
    if any(pattern in msg for pattern in ["connection", "network", "unreachable"]):
        return ProviderError(
            code=ErrorCode.NETWORK_ERROR,
            message=str(error),
            provider=provider,
            retryable=True,
            raw=error
        )
    
    # Unknown
    return ProviderError(
        code=ErrorCode.UNKNOWN,
        message=str(error),
        provider=provider,
        retryable=False,
        raw=error
    )
```

---

## API Design

### 1. AbstractProvider Interface

**Seven required methods:**

```python
class AbstractProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Identifier: 'anthropic', 'openai', 'deepseek', etc."""
        ...
    
    @abc.abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Blocking chat completion."""
        ...
    
    @abc.abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Streaming chat completion."""
        ...
    
    @abc.abstractmethod
    async def validate_api_key(self) -> bool:
        """Check API key validity (lightweight)."""
        ...
    
    @abc.abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model IDs."""
        ...
    
    @abc.abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """Check feature support."""
        ...
    
    @abc.abstractmethod
    def get_context_window(self, model: str) -> int:
        """Return context window size."""
        ...
```

**Design principles:**
- All async (enables concurrent provider requests)
- All methods return canonical types (no provider leakage)
- Minimal surface area (7 methods, not 20+)
- No configuration in methods (use ProviderConfig at init)

### 2. Capability Query API

```python
class CapabilityMatrix:
    def supports(self, provider: str, feature: str) -> bool:
        """Check single feature."""
        ...
    
    def list_providers_supporting(self, feature: str) -> list[str]:
        """Get all providers with feature."""
        ...
    
    def get_context_window(self, provider: str) -> int:
        """Get context limit."""
        ...
    
    def get(self, provider: str) -> ProviderCapability | None:
        """Get full capability record."""
        ...
```

**Usage patterns:**

```python
# Pre-filter providers for vision tasks
matrix = get_capability_matrix()
vision_providers = matrix.list_providers_supporting("vision")
# Returns: ["anthropic", "openai", "google"]

# Check context window for compaction
context_limit = matrix.get_context_window("deepseek")
# Returns: 128000

# Query all capabilities
cap = matrix.get("anthropic")
if cap and cap.prompt_caching:
    # Use caching optimization
    ...
```

---

## State Management

### 1. Provider Instances

**Stateless by design:** No conversation state in provider instances.

```python
class AnthropicProvider(AbstractProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config  # Configuration only
        self._base_url = config.base_url or "https://api.anthropic.com/v1"
        # No conversation state, no history, no buffers
```

**State location:**
- Conversation history → Application layer (Skills, Router)
- Tool execution state → Application layer
- Streaming buffers → Local to `chat_stream()` generator

**Concurrency:** Multiple concurrent requests to same provider instance are safe:
```python
provider = AnthropicProvider(config)

# Safe concurrent calls
results = await asyncio.gather(
    provider.chat(request1),
    provider.chat(request2),
    provider.chat(request3),
)
```

### 2. Connection Pooling

**httpx AsyncClient manages connection pool:**

```python
async with httpx.AsyncClient(
    timeout=config.timeout_seconds,
    limits=httpx.Limits(
        max_connections=config.max_concurrent,
        max_keepalive_connections=20
    )
) as client:
    response = await client.post(...)
```

**Pool configuration:**
- `max_connections`: Total connections per provider
- `max_keepalive_connections`: Persistent connections
- Automatic connection reuse for sequential requests

### 3. Capability Matrix Singleton

**Global singleton pattern:**

```python
_capability_matrix: CapabilityMatrix | None = None

def get_capability_matrix() -> CapabilityMatrix:
    global _capability_matrix
    if _capability_matrix is None:
        _capability_matrix = CapabilityMatrix()
    return _capability_matrix
```

**Rationale:**
- Read-only after initialization
- No per-request overhead
- Thread-safe (no writes after init)

---

## Scalability Considerations

### 1. Concurrent Request Handling

**Per-provider limits:**

| Provider | max_concurrent | Rate Limit (RPM) |
|----------|----------------|------------------|
| Anthropic | 50 | ~3000 |
| OpenAI | 60 | ~3600 |
| DeepSeek | 60 | ~3000 |
| Google | 30 | ~1500 |

**Horizontal scaling strategy:**

```python
# Multiple provider instances with different API keys
providers = [
    AnthropicProvider(ProviderConfig(api_key=key1)),
    AnthropicProvider(ProviderConfig(api_key=key2)),
    AnthropicProvider(ProviderConfig(api_key=key3)),
]

# Round-robin dispatch
async def dispatch(request: ChatRequest) -> ChatResponse:
    provider = providers[request_count % len(providers)]
    return await provider.chat(request)
```

**Effective rate limit:** `N_keys × per_key_limit`

### 2. Memory Scaling

**Memory per request:**

```python
# Typical request (20 messages, 100 tokens/message, 3 tools)
Request overhead:
  - ChatRequest: ~300 bytes
  - 20 Messages: 20 × 200 = 4 KB
  - Message content: 20 × 100 × 4 = 8 KB (UTF-8)
  - 3 ToolSchemas: 3 × 150 = 450 bytes
  Total: ~13 KB

Response overhead:
  - ChatResponse: ~400 bytes
  - Response content: ~10-50 KB
  - Total: ~11-51 KB

Peak memory per request: ~64 KB
```

**Concurrent request memory:**
- 100 concurrent requests: ~6.4 MB
- 1000 concurrent requests: ~64 MB
- 10000 concurrent requests: ~640 MB

**Scaling limit:** Memory is not the bottleneck. Rate limits dominate.

### 3. Latency Characteristics

**Request path breakdown:**

```
Total latency = translation + network + provider + parsing

Translation: 5-10μs (message/tool conversion)
Network RTT: 20-100ms (depends on geography)
Provider processing: 100-5000ms (depends on model/complexity)
Parsing: 50-200μs (JSON parsing + object construction)

Translation overhead: <0.01% of total
```

**Optimization opportunities:**
1. **Connection pooling** (already implemented) — saves 10-50ms per request
2. **Request batching** (not implemented) — could reduce overhead for bulk tasks
3. **Caching** (Anthropic-specific) — 90% cost reduction for repeated prefixes

### 4. Error Recovery Scaling

**Retry strategy:**

```python
async def chat_with_retries(
    provider: AbstractProvider,
    request: ChatRequest,
    max_retries: int = 3
) -> ChatResponse:
    """
    Exponential backoff retry with jitter.
    
    Backoff: 1s, 2s, 4s, 8s, ...
    Jitter: ±25% randomization to avoid thundering herd
    """
    for attempt in range(max_retries):
        try:
            return await provider.chat(request)
        except ProviderError as e:
            if not e.retryable or attempt == max_retries - 1:
                raise
            
            delay = (2 ** attempt) * (0.75 + 0.5 * random.random())
            await asyncio.sleep(delay)
    
    raise RuntimeError("Max retries exceeded")
```

**Circuit breaker pattern (router layer):**
- After N consecutive failures, mark provider unhealthy
- Skip unhealthy providers for M seconds
- Periodically probe to detect recovery

---

## Performance Optimizations

### 1. Lazy Initialization

```python
class AnthropicProvider(AbstractProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client = None  # Lazy init
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout_seconds
            )
        return self._client
```

**Benefit:** Avoid connection overhead until first use.

### 2. Streaming Optimization

**Zero-copy text deltas:**

```python
# Don't accumulate text — yield immediately
async for chunk in provider_stream:
    if chunk.type == "text_delta":
        yield StreamEvent(type="text_delta", content=chunk.text)
        # No buffering, no concatenation
```

**Tool call accumulation (required):**

```python
# Must accumulate tool arguments (JSON fragments)
buffer = ""
async for chunk in provider_stream:
    if chunk.type == "tool_delta":
        buffer += chunk.arguments_fragment
        # Don't yield until complete
```

### 3. Async Context Manager

```python
async with httpx.AsyncClient() as client:
    response = await client.post(...)
    # Client closed automatically
    # Connection pool cleaned up
```

**Benefit:** Guaranteed cleanup, no leaked connections.

---

## Key Design Decisions

### 1. Why No Provider SDKs?

**Decision:** Use raw HTTP (httpx/aiohttp) instead of provider SDKs.

**Rationale:**
- Avoid dependency bloat (each SDK adds 5-20 dependencies)
- Control exact wire format (SDKs hide details)
- Uniform error handling (SDKs throw different exceptions)
- Faster updates (no waiting for SDK releases)

**Trade-off:** More code per adapter (~400 lines vs ~100 with SDK), but better control.

### 2. Why Three Effort Parameters?

**Decision:** `effort_budget_tokens`, `effort_instruction`, `effort_reasoning` instead of single `effort_level`.

**Rationale:**
- Providers use incompatible APIs (budget vs instructions vs enum)
- Effort manager handles translation (keeps adapters simple)
- Preserves semantic intent across providers
- Extensible (new providers add new parameters)

### 3. Why Frozen Dataclasses?

**Decision:** `ToolCall` and `ToolSchema` are frozen (immutable).

**Rationale:**
- Prevents bugs during streaming (multiple references)
- Safe for concurrent tool execution
- Explicit about intent (these are values, not entities)

**Trade-off:** Cannot modify after creation, must create new instances.

---

## Key Sources

**Implementation:**
- `packages/lyra-provider/src/lyra_provider/interface.py` — Data models (322 lines)
- `packages/lyra-provider/src/lyra_provider/adapters/anthropic.py` — Reference implementation (442 lines)
- `packages/lyra-provider/src/lyra_provider/capability.py` — Capability matrix (197 lines)

**Documentation:**
- `lyra-upgrade/07-architecture-deep-dives/03-provider-abstraction.md` — Deep dive
- `docs/howto/configure-providers.md` — User guide
