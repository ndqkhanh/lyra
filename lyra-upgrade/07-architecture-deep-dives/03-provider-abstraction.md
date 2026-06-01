# Provider Abstraction Layer — Deep Dive

**Date**: 2026-06-01 | **Packages**: `lyra-provider`, `lyra-router` | **Tests**: 37+

## 1. Executive Summary

Lyra runs on 4+ AI providers (Anthropic, OpenAI, DeepSeek, Google) through a single abstraction layer. Every feature — skills, tools, memory, swarm, voice — is written once against a canonical interface and works across all backends. This is the architectural foundation that makes Lyra a *multi-provider omni-agent harness*, not an Anthropic-only tool.

The abstraction has three layers: (1) the `AbstractProvider` ABC defining canonical types and methods, (2) per-provider adapters translating canonical ↔ provider-specific formats, and (3) a capability registry that informs routing and fallback decisions. The key design principle: the canonical interface is the *intersection* of provider capabilities, not the union. Features only available on some providers (e.g., extended thinking on Anthropic) are exposed as optional fields that degrade gracefully on others.

## 2. The AbstractProvider Interface

Defined at `packages/lyra-provider/src/lyra_provider/interface.py`. Every provider adapter must implement this contract.

### 2.1 Canonical Types

```python
class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: str
    tool_call_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()

@dataclass(frozen=True)
class ChatRequest:
    messages: tuple[Message, ...]
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    tools: tuple[ToolDefinition, ...] = ()
    effort_budget_tokens: int | None = None       # Anthropic-specific
    effort_instruction: str | None = None          # Prompt-based fallback
    effort_reasoning: str | None = None            # OpenAI reasoning_effort

@dataclass(frozen=True)
class ChatResponse:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: TokenUsage | None = None
    finish_reason: str = "stop"
    model: str = ""
```

### 2.2 The ABC Contract

```python
class AbstractProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...
    
    @abstractmethod
    async def stream(self, request: ChatRequest) -> AsyncIterator[str]: ...
    
    @abstractmethod
    def count_tokens(self, text: str) -> int: ...
    
    @property
    @abstractmethod
    def provider_name(self) -> str: ...
    
    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapability: ...
```

### 2.3 Design Rationale

The `ChatRequest` carries three effort-related fields (`effort_budget_tokens`, `effort_instruction`, `effort_reasoning`) alongside the core message payload. This is intentional: the effort scale (§4.5) is a first-class concept that every provider adapter must handle, but each adapter interprets the fields differently:

- **Anthropic**: reads `effort_budget_tokens` → `thinking.budget_tokens`
- **OpenAI**: reads `effort_reasoning` → `reasoning_effort` parameter
- **DeepSeek/Google**: reads `effort_instruction` → prepends to system prompt
- **Open-weight**: reads `effort_instruction` → prepends a shorter version

The adapter that doesn't understand a field silently ignores it. This is the "intersection, not union" principle.

## 3. Provider Adapters

Each adapter lives at `packages/lyra-provider/src/lyra_provider/adapters/<provider>.py`.

### 3.1 Anthropic Adapter

**File**: `adapters/anthropic.py`

**Message format translation**:
```
Lyra canonical                    → Anthropic Messages API
Message(role=SYSTEM, content=...) → {"role": "system", "content": [...]}
Message(role=USER, content=...)   → {"role": "user", "content": [...]}
Message(role=ASSISTANT, ...)      → {"role": "assistant", "content": [...]}
```

**Tool use normalization**: Lyra's canonical `ToolCall` (with `id`, `name`, `arguments`) maps to Anthropic's `tool_use` content blocks. Tool results map to `tool_result` blocks with matching `tool_use_id`.

**Extended thinking**: The adapter reads `request.effort_budget_tokens` and sets `thinking.budget_tokens` on the API request. If the field is `None`, no thinking parameter is sent (uses Anthropic default). The `thinking` beta header is always included.

**Context window**: 200K tokens. The adapter validates that `count_tokens()` ≤ 200K before sending.

**API key**: Read from `ANTHROPIC_API_KEY` env var at init time. Validated at first `chat()` call, not at construction (lazy validation).

### 3.2 OpenAI Adapter

**File**: `adapters/openai.py`

**Message format**: Lyra canonical → OpenAI Chat Completions format. Tool calls use OpenAI's `tool_calls` array in the response, not Anthropic's `tool_use` content blocks.

**Reasoning effort**: The adapter reads `request.effort_reasoning` and maps it to OpenAI's `reasoning_effort` parameter (`"low"`, `"medium"`, `"high"`). Lyra's six effort levels compress to OpenAI's three: LOW/MEDIUM → `"low"`, HIGH → `"medium"`, XHIGH/MAX/ULTRACODE → `"high"`.

**Context window**: 128K for GPT-4o, varies by model. The adapter queries the model-specific limit from `ProviderCapability`.

**API key**: Read from `OPENAI_API_KEY`.

### 3.3 DeepSeek Adapter

**File**: `adapters/deepseek.py`

**API compatibility**: DeepSeek uses an OpenAI-compatible API format, so the adapter inherits much of the OpenAI translation logic. Key differences:

- **No native reasoning API**: DeepSeek does not expose `reasoning_effort`. Instead, the adapter prepends `request.effort_instruction` to the system prompt as a reasoning directive.
- **Context window**: 64K (DeepSeek-V3). This is the tightest constraint of all providers. The `ProviderAdaptiveCompactor` in `lyra-context` detects this and selects `AGGRESSIVE` compaction strategy.
- **Tool calling**: OpenAI-compatible format, but reliability is lower. The adapter adds explicit JSON schema instructions to the system prompt.

**API key**: Read from `DEEPSEEK_API_KEY`.

### 3.4 Google Adapter

**File**: `adapters/google.py`

**API format**: Gemini's native function-calling format, significantly different from both Anthropic and OpenAI. The adapter translates Lyra's canonical `ToolDefinition` into Gemini's `FunctionDeclaration` protobuf-like structures. Response `FunctionCall` objects are translated back to canonical `ToolCall`.

**Context window**: 1M tokens (Gemini 2.5 Pro) — the largest of any provider. The `ProviderAdaptiveCompactor` selects `MINIMAL` compaction strategy, preserving more context.

**API key**: Read from `GEMINI_API_KEY`.

## 4. Capability Detection

Defined at `packages/lyra-provider/src/lyra_provider/capability.py`.

### 4.1 Static Capability Map

```python
@dataclass(frozen=True)
class ProviderCapability:
    provider_name: str
    supports_tool_use: bool = True
    supports_json_mode: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    supports_extended_thinking: bool = False
    context_window_tokens: int = 128_000
    max_output_tokens: int = 4096
    tier: str = "standard"  # "fast", "standard", "deep"
```

Per-provider values:
| Provider | Tool Use | JSON | Vision | Streaming | Extended Thinking | Context Window | Tier |
|----------|----------|------|--------|-----------|-------------------|----------------|------|
| Anthropic | ✅ | ✅ | ✅ | ✅ | ✅ | 200K | deep |
| OpenAI | ✅ | ✅ | ✅ | ✅ | ❌ | 128K | standard |
| DeepSeek | ✅ | ✅ | ❌ | ✅ | ❌ | 64K | fast |
| Google | ✅ | ✅ | ✅ | ✅ | ❌ | 1M | standard |

### 4.2 Runtime Probing

For unknown providers (configured via custom endpoint URL), the adapter performs a lightweight capability probe on first connection: sends a minimal `chat()` request and inspects the response for tool use support, streaming capability, and actual context window size (via error messages on oversized requests).

## 5. Fallback & Escalation Chain

The router (`packages/lyra-router/src/lyra_router/router.py`) implements a 3-tier fallback chain:

```
Fast tier (DeepSeek, Haiku) 
  → failure → Standard tier (GPT-4o, Sonnet)
    → failure → Deep tier (Opus, Gemini Pro)
      → failure → Error to user
```

**Circuit breaker**: `BudgetTracker` at `packages/lyra-router/src/lyra_router/budget.py` tracks cumulative session cost. At $5/session, it trips and forces all subsequent requests to the cheapest available provider. Reset on new session.

**Provider health scoring** (planned): Track per-provider error rate, latency P95, and availability. Deprioritize providers with >5% error rate. Not yet wired into routing decisions (deferred to Tier 7).

## 6. Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    Lyra Application                       │
│  (skills, tools, memory, swarm, voice — written ONCE)    │
├──────────────────────────────────────────────────────────┤
│               AbstractProvider (ABC)                      │
│  chat(request: ChatRequest) → ChatResponse               │
│  stream(request: ChatRequest) → AsyncIterator[str]       │
│  count_tokens(text: str) → int                            │
│  capabilities → ProviderCapability                        │
├──────────────┬──────────────┬──────────────┬─────────────┤
│  Anthropic   │   OpenAI     │   DeepSeek   │   Google    │
│  Adapter     │   Adapter    │   Adapter    │   Adapter   │
│              │              │              │             │
│  API: Msgs   │  API: Chat   │  API: OpenAI │  API: GenAI │
│  Key: ANTH…  │  Key: OPEN…  │  -compat     │  Key: GEM…  │
│  Window:200K │  Window:128K │  Key: DEEP…  │  Window:1M  │
│              │              │  Window:64K  │             │
├──────────────┴──────────────┴──────────────┴─────────────┤
│              ProviderCapability Registry                   │
│  (tool_use, json_mode, vision, streaming, thinking, ctx)  │
└──────────────────────────────────────────────────────────┘
```

## 7. Trade-Off Analysis

| Dimension | Gain | Cost | When It Wins | When It Loses |
|-----------|------|------|--------------|---------------|
| Write-once portability | 4+ providers, 1 codebase | Adapter maintenance per provider (~200 lines each) | Multi-provider deployments; users who switch providers | Single-provider users who never switch |
| Tool calling | Normalized schema across all backends | Translation overhead per call (negligible: <1ms per message) | Cross-provider tool use | Single-provider, provider-native tools |
| Streaming | Unified `AsyncIterator[str]` interface | Per-provider SSE/stream differences handled in adapter | Real-time UX (voice, chat) | Batch processing where streaming adds complexity |
| Effort mapping | Abstract effort → provider-specific params | Some providers ignore effort (open-weight) | Production usage with reasoning models | Quick prototyping where effort is irrelevant |
| Error handling | Canonical error types → consistent UX | Loss of provider-specific error detail | User-facing applications | Provider-specific debugging |
| Context window | Provider-adaptive compaction strategy | Aggressive compaction may lose detail on small-window providers | Multi-provider with mixed window sizes | Single large-window provider |

## 8. (B) Breakthrough: Universal Provider Interface

What Lyra does beyond existing harnesses:

1. **Provider-adaptive context**: The `ProviderAdaptiveCompactor` selects compaction strategy based on detected context window (AGGRESSIVE for 64K, MODERATE for 128-200K, MINIMAL for 1M+). No other harness does this automatically.

2. **Capability-aware routing**: The router consults `ProviderCapability` before dispatching. Tasks requiring vision are never routed to DeepSeek (no vision support). Tasks requiring extended reasoning are preferentially routed to Anthropic.

3. **Provider-specific skill frontmatter stripping**: When routing to non-Claude providers, Claude-only SKILL.md frontmatter fields (`model:`, subagent config, dynamic injection) are stripped/translated before injection. This is the §4.4 provider-agnostic skill requirement.

4. **Effort mapping transparency**: The `EffortMapping` dataclass carries ALL provider-specific parameters in one object, making the translation explicit and debuggable. Other harnesses bury this logic in adapter internals.

5. **Lazy key validation**: API keys are validated at first use, not at startup, allowing offline configuration and provider switching without restart.

## 9. Key Sources

- Anthropic Messages API: https://docs.anthropic.com/en/api/messages
- OpenAI Chat Completions: https://platform.openai.com/docs/api-reference/chat
- DeepSeek API (OpenAI-compatible): https://platform.deepseek.com/api-docs
- Google Gemini API: https://ai.google.dev/gemini-api/docs
- Claude Code model-config: https://code.claude.com/docs/en/model-config
- DeerFlow 2.0 provider abstraction: https://github.com/bytedance/deer-flow
- OpenCode multi-provider design: https://github.com/sst/opencode
- RouteLLM cost-sensitive routing: https://arxiv.org/abs/2406.18665
- NVIDIA SLM paper (small models for agent calls): https://arxiv.org/abs/2506.02153
