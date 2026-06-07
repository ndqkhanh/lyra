# S1: Provider Abstraction + Real LLM Calls

> Plan: §4.5 (05-model-router.md) | Sources: 9 papers, 3 books, 4 repos
> Breakthrough fusion: BEST-Route + RouteLLM + Claude Code Effort

## Scope

Build the provider abstraction layer that every other Lyra component depends on:
1. `ProviderBackend` protocol — unified interface for LLM API calls
2. Concrete adapters — Anthropic, DeepSeek, OpenAI, Google (Gemini)
3. Message/tool-call/streaming normalization
4. Token accounting + cost tracking
5. Basic model router (task-type → model tier)
6. Fallback chain
7. Configuration via settings.json

## Out of Scope (Phase 2+)
- Multi-head learned router (BEST-Route) — requires training infrastructure
- Speculative decoding pipeline
- Prompt caching optimization
- Full cost optimization engine

## Interfaces

### ProviderBackend (Protocol)
```python
class ProviderBackend(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...
    async def complete_stream(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]: ...
    def supports(self, capability: Capability) -> bool: ...
    def cost_estimate(self, request: CompletionRequest) -> CostEstimate: ...

@dataclass(frozen=True)
class CompletionRequest:
    messages: tuple[Message, ...]
    model: str
    max_tokens: int = 4096
    temperature: float = 0.0
    tools: tuple[ToolDef, ...] | None = None
    effort: EffortLevel = EffortLevel.MEDIUM

@dataclass(frozen=True)
class CompletionResponse:
    content: str
    tool_calls: tuple[ToolCall, ...] | None
    usage: TokenUsage
    finish_reason: str
    model: str
    latency_ms: float

@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
```

### ModelRouter
```python
class ModelRouter:
    def route(self, task: Task, context: RouteContext) -> RouteDecision: ...
    def register_provider(self, name: str, provider: ProviderBackend, models: list[ModelInfo]): ...

@dataclass(frozen=True)
class RouteDecision:
    provider_name: str
    model: str
    effort: EffortLevel
    fallback_chain: tuple[RouteDecision, ...]
```

## Data Model

### Capability enum
- TEXT_GENERATION
- TOOL_USE
- VISION
- STREAMING
- JSON_MODE
- LONG_CONTEXT (200K+)
- AUDIO_INPUT/OUTPUT

### EffortLevel enum
- LOW (Haiku-class, simple tasks)
- MEDIUM (Sonnet-class, standard)
- HIGH (Opus-class, complex reasoning)
- XHIGH (Opus + max thinking)
- MAX (best available, cost-insensitive)

## Test Plan

1. `test_provider_protocol.py` — Protocol conformance tests for each adapter
2. `test_anthropic_adapter.py` — Real Anthropic API calls (integration)
3. `test_deepseek_adapter.py` — DeepSeek API calls using DEEPSEEK_API_KEY
4. `test_model_router.py` — Routing logic unit tests
5. `test_fallback_chain.py` — Fallback behavior when primary fails
6. `test_cost_tracking.py` — Token accounting accuracy
7. `test_streaming.py` — Streaming response handling

## Book Practices (binding)
- Agentic Design Patterns Ch16: Cost tracking as first-class metric — every response logs input/output cost
- Architecting GenAI Apps Ch6: Model fallback chains with circuit-breaker pattern
- Generative AI Design Patterns Ch6: BEST_MODEL/DEFAULT_MODEL/SMALL_MODEL deployment constants
