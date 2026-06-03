# Tier 1 Review — Provider & Reasoning Foundation

**Date**: 2026-06-01
**Scope**: Provider abstraction, model router, effort scale, capability maps, cost tracking, credential handling, fallback/reliability
**Reference Architecture**: BREAKTHROUGH-ARCHITECTURE.md (tiers 1-3, SS1 "Provider Abstraction Layer")
**Reference Plan**: lyra-upgrade/plans/19-ultracode-replication.md (Primitives 1-3)
**Files examined**: 17+ source files across 4 packages (lyra-effort, lyra-provider, lyra-router, lyra-core)

---

## Reviewers

- **Senior Architect**: BLOCKING — 1 blocking defect (DeepSeek streaming tool-call termination)
- **Senior AI Engineer**: BLOCKING — 4 blocking defects (Google stub in router, no runtime fallback, unenforced feature/context constraints, disconnected cost estimates)
- **Senior Security Engineer**: NON-BLOCKING — No hardcoded secrets, no credential leakage, no code injection surfaces

---

## Architect Review

**Verdict: BLOCKING** — one blocking defect found in the DeepSeek streaming adapter. All other concerns are non-blocking. Architecture conformance is sound overall.

### 1. Effort Scale — ultracode = xhigh + orchestration toggle (PASS)

**Evidence**:

- `EffortLevel` enum (`lyra_effort/models.py:21-28`): Docstring explicitly states "ultracode is special: it sends xhigh to the model AND flips on auto-orchestration -- it is NOT a distinct 6th API budget tier."
- Shared budget (`lyra_effort/models.py:55-62`): `_DEFAULT_BUDGETS[ULTRACODE] = 16384`, identical to `_DEFAULT_BUDGETS[XHIGH] = 16384`.
- Orchestration gating (`lyra_effort/models.py:49-51`): `orchestration_enabled` returns `True` only for `ULTRACODE`.
- Resolution logic (`lyra_effort/manager.py:245-249`): `map_effort()` resolves ultracode: `effective_level = EffortLevel.XHIGH if is_ultracode else level`. The actual API budget sent to the model is always `xhigh`.
- Auto-orchestration enable (`lyra_effort/manager.py:197-206`): `set_level()` sets `OrchestrationConfig(enabled=(level == EffortLevel.ULTRACODE))`.

**Assessment**: The architecture's key insight -- "Ultracode is NOT a 6th API budget tier" -- is correctly implemented. Budget flows at xhigh; the orchestration toggle is the sole differentiator. This makes the effort scale portable to providers with only 2-3 effort levels (DeepSeek, open-weights). **PASS.**

**Non-blocking concern**: When a provider's `max_effort_level` is `HIGH` (e.g., Google, open-weights at `manager.py:63-68, 77-82`), setting ultracode causes the effective budget to be clamped to `HIGH` (16384 xhigh -> clamped to 8192 high, per `manager.py:252-256`). The orchestration flag is preserved correctly, but the user may believe they are getting xhigh-level thinking when they are actually getting high. The `reported_level` remains `ultracode` (manager.py:270), masking the clamp. Document this behavior for the user-facing effort indicator.

### 2. Provider Abstraction — Normalization Across Providers (PASS with BLOCKING defect)

**Evidence**:

- Canonical interface (`lyra_provider/interface.py:241-322`): `AbstractProvider` ABC with `chat()`, `chat_stream()`, `supports_feature()`, `validate_api_key()`, `list_models()`, `get_context_window()`.
- Canonical types (`lyra_provider/interface.py`): `Message`, `MessageRole`, `ToolCall`, `ToolResult`, `ChatRequest`, `ChatResponse`, `LLMUsage`, `StreamEvent`, `ProviderError`.
- ChatRequest effort fields (`lyra_provider/interface.py:113-115`): Three provider-agnostic effort parameters -- `effort_budget_tokens` (Anthropic native), `effort_instruction` (prompt-level, for DeepSeek/open-weights), `effort_reasoning` (OpenAI `reasoning_effort`). Each adapter reads the field(s) it needs.
- Anthropic adapter (`adapters/anthropic.py:196-201`): Maps `effort_budget_tokens` -> `body["thinking"]["budget_tokens"]`.
- OpenAI adapter (`adapters/openai.py:81-82`): Maps `effort_reasoning` -> `body["reasoning_effort"]`.
- DeepSeek adapter (`adapters/deepseek.py:346-361`): Injects `effort_instruction` into the system message prefix via `_build_messages()`.
- Google adapter (`adapters/google.py:53-58`): Stub -- raises `ProviderError` for `chat()` and `chat_stream()`.
- CapabilityMatrix (`capability.py:107-184`): Six providers registered with per-provider feature flags.

#### BLOCKING: DeepSeek streaming tool call completion

**File**: `packages/lyra-provider/src/lyra_provider/adapters/deepseek.py`, lines 258-306

**Defect**: The streaming tool call termination logic never emits `tool_call_end` or `done` StreamEvents when DeepSeek finishes a tool-calling response.

**Root cause**: In the OpenAI-compatible streaming format (which DeepSeek follows), tool call termination arrives as a chunk with empty `delta` and `choices[0].finish_reason: "tool_calls"`. The DeepSeek adapter's handling:

1. Lines 259-294: The `tool_call_end` emission is gated by `if tool_calls_delta:` -- but the final chunk has `delta.tool_calls` as `[]` (falsy), so this block is never entered.
2. Lines 302-305: The `done` emission is gated by `if finish_reason and finish_reason != "tool_calls":` -- when finish_reason IS `"tool_calls"`, this is `True and False` = False, so `done` is never yielded.

**Impact**: Any caller relying on streaming events to detect tool call completion will see the stream terminate without a `tool_call_end` or `done` event. The `current_tool` state leaks. Usage data in the `done` event is lost.

**Comparison**: The OpenAI adapter (`openai.py:194-213`) handles this correctly by checking `finish_reason` at the outer level (not inside `if tool_calls_delta:`), ensuring both `tool_call_end` and `done` are always emitted regardless of whether `delta.tool_calls` is present.

**Fix**: The finish_reason check should yield `tool_call_end` (if `current_tool` is set) even when `finish_reason == "tool_calls"`, and the `done` event should be emitted unconditionally on any finish_reason.

### 3. Module Boundaries — Clean (PASS)

**Dependency Graph**:

```
lyra_effort ------> lyra_provider (optional validation)
     |
     +--> lyra_workflow (via EffortBridge)
              |
              +--> lyra_provider (via ModelRouter)
```

- lyra-effort: Self-contained effort scale definitions. No dependency on any other Lyra package for core logic.
- lyra-provider: interface.py + capability.py + adapters/. No dependencies on lyra-effort, lyra-router, or lyra-core.
- lyra-router: routes to providers. Imports provider abstractions.
- lyra-core/orchestration/: orchestrator.py, dynamic_workflow.py, effort_bridge.py. EffortBridge imports from `lyra_effort.models` and `lyra_workflow`.

Clean separation of concerns at each layer. No circular imports. **PASS.**

**Non-blocking naming collision**: Two `orchestrator` modules exist with different contents:
- `lyra_workflow.orchestrator` — `AutoOrchestrator` (Primitive 2: auto-trigger decision)
- `lyra_core.orchestration.orchestrator` — `TeamOrchestrator` (agent team lifecycle)

Consider renaming one (e.g., `lyra_workflow.auto_orchestrator`).

### 4. EffortBridge — Connection to Orchestration Engine (PASS)

**Evidence**:

- Location: `lyra_core/orchestration/effort_bridge.py` — correctly placed in the orchestration layer.
- Construction (`effort_bridge.py:55-59`): `__post_init__` auto-creates `AutoOrchestrator` when effort is ULTRACODE.
- Decision chaining: `should_orchestrate(prompt)` checks `effort_level.orchestration_enabled` + `orchestrator.evaluate()`; `evaluate(prompt)` returns `OrchestrationDecision`; `plan_workflow(decision)` creates `WorkflowScript`.
- Config restore (`effort_bridge.py:115-121`): `from_config()` creates bridge from a string effort value.

**Non-blocking concerns**:

1. `effort_bridge.py:89-112` creates a fixed WorkflowScript with hardcoded phases (Discover/Verify/Report). The plan document specifies LLM-based script generation. This static template is a placeholder.
2. `effort_bridge.py:54` stores `_orchestration_provider` as an empty string on a frozen dataclass. Only settable via `__post_init__` or `object.__setattr__`. Awkward for callers needing provider-aware degradation.

### Architect Summary

| # | File | Line | Severity | Defect |
|---|------|------|----------|--------|
| A1 | `adapters/deepseek.py` | 280-306 | **BLOCKING** | Streaming tool call completion: `tool_call_end` and `done` events never emitted when `finish_reason == "tool_calls"` |
| A2 | `lyra_effort/manager.py` | 248-270 | NON-BLOCKING | Provider clamping silently reduces ultracode budget when max_effort_level < xhigh |
| A3 | `lyra_core/orchestration/effort_bridge.py` vs `lyra_workflow/orchestrator.py` | across | NON-BLOCKING | Name collision: two `orchestrator` modules |
| A4 | `lyra_core/orchestration/effort_bridge.py` | 89-112 | NON-BLOCKING | Static plan_workflow should be replaced with LLM-based script generation |
| A5 | `lyra_core/orchestration/effort_bridge.py` | 54 | NON-BLOCKING | `_orchestration_provider` is awkward to set on frozen dataclass |
| A6 | `adapters/google.py` | 53-58 | NON-BLOCKING | Google provider is a stub; must be implemented for multi-provider parity |
| A7 | `capability.py` vs `adapters/__init__.py` | 160-184 | NON-BLOCKING | CapabilityMatrix registers openrouter/openweights but no adapters exist |

---

## AI Engineer Review

**Reviewer**: AI Engineer (LLMOps perspective)
**Verdict: BLOCKING** — four blocking issues found. The foundation is well-structured but has critical gaps in runtime enforcement and error recovery.

### BLOCKING Issues

#### B1. Google provider is registered as routable but non-functional

The `ProviderRegistry` at `providers.py:185-205` registers `gemini-2.5-flash` and `gemini-2.5-pro` as valid models in the STANDARD tier. The router can and will route tasks to these models. However, `GoogleProvider.chat()` at `google.py:53-58` immediately raises `ProviderError("GoogleProvider is not yet implemented")`, and `chat_stream()` at `google.py:61-66` yields an error event. There is no guard in `get_best_model_for_tier()` (providers.py:83-101) or `_build_decision()` (router.py:299-359) to exclude providers whose adapter is stubbed. At runtime this means the router will confidently return a `RoutingDecision` for `gemini-2.5-pro`, but the subsequent API call will unconditionally fail.

**Fix**: Either implement the Google adapter, or add a `provider_status: str = "functional" | "stub"` flag to `ModelAssignment` that `get_best_model_for_tier()` respects.

#### B2. No runtime provider failure fallback loop

The router selects a model and returns a `RoutingDecision`, but there is no mechanism to catch a failed provider call and retry with an alternative. The `ProviderConfig.max_retries=3` (interface.py:217) is declared but no adapter implements retry logic around its HTTP calls. None of the four adapters (anthropic.py, deepseek.py, openai.py, google.py) contain a retry loop. The `BudgetTracker` circuit breaker (budget.py:108) is session-level only -- it guards spend, not provider health. If Anthropic returns 429s for ten seconds, the router has no way to shift traffic to DeepSeek until it resets.

**Fix**: Add an adapter-level retry decorator or loop using exponential backoff and jitter. For cross-provider fallback at the router level, add a "retry with next-best" path that the caller can invoke on `ProviderError(..., retryable=True)`.

#### B3. `supports_tool_use` and `context_window` are stored but never enforced

`ModelAssignment` has fields `supports_tool_use: bool = True` (models.py:63) and `context_window: int = 200000` (models.py:62), and they are populated with correct values in providers.py (e.g., DeepSeek gets 128K, Google gets 1M). However, `_build_decision()` (router.py:299-359) selects the cheapest model at a tier without checking either:

- It does not check whether the task requires tool calling and whether the candidate model supports it.
- It does not check whether the task's context length fits in the model's context window.

A task with a 150K-token context can be routed to `deepseek-chat-v4` which has a 128K window. A task requiring tool calling can be routed to any model where `supports_tool_use` might be False (`openweights` models have `tool_calling=False` in CapabilityMatrix). The data exists but the routing logic doesn't use it.

**Fix**: Add a `required_features: list[str]` parameter to `router.route()` and filter `ModelAssignment` candidates by both context window and feature support before picking the cheapest.

#### B4. Cost estimates are disconnected from actual model pricing

`get_cost_estimate()` in models.py:150-152 returns a fixed USD value per `TaskComplexity` (TRIVIAL=$0.0001, MODERATE=$0.01, COMPLEX=$0.05). These numbers are hardcoded and do not reflect the per-model pricing in providers.py. For example, a COMPLEX task routed to `claude-opus-4-20250514` at $15/M input tokens will very likely cost more than $0.05, while the same complexity routed to `deepseek-chat-v4` at $0.27/M tokens will cost much less. The estimate is also only for input tokens -- output tokens are typically 3-5x more expensive per token (Anthropic charges $75/M for Opus output vs. $15/M for input).

This affects `RoutingDecision.cost_estimate_usd` which is used for logging and potentially for user-facing cost previews (see the ultracode walkthrough in `19-ultracode-replication.md` line 75: "Estimated cost: $3.42"). The estimate will be consistently wrong for any model other than the (unstated) assumed model behind the complexity-based estimate.

**Fix**: Compute cost estimates dynamically from `ModelAssignment.cost_per_1m_tokens`, an estimated output token count, and an estimated input token count. Remove the static `_COST_ESTIMATES` dict.

### NON-BLOCKING Issues

#### N1. NeuralUCB cost estimates are a second source of truth

`_MODEL_COST_ESTIMATES` in neural_ucb.py:20-27 duplicates a subset of the pricing data already stored in `ProviderRegistry._models`. The NeuralUCB cost estimates are per-tier (not per-model) and are hardcoded separately from providers.py. These can and will drift. The NeuralUCB cost estimates should be derived from the provider registry's per-model pricing.

#### N2. CONTEXT_OVERFLOW error code is defined but never raised

`ErrorCode.CONTEXT_OVERFLOW` is defined at interface.py:182, but no adapter's `_translate_error` method maps the provider's context-length-exceeded error to this code. The Anthropic adapter (anthropic.py:432-441) only checks for 401, 429, and 400 patterns. The OpenAI adapter (openai.py:279-285) checks 401 and 429. If a provider returns a 400 with "input too long" or "context length exceeded", it gets mapped to `UNKNOWN`, robbing the caller of the ability to detect and handle context overflow specifically.

#### N3. Router does not consult CapabilityMatrix

The `CapabilityMatrix` in capability.py is a well-structured, current-as-of-May-2026 per-provider feature matrix. However, `lyra_router` never imports or consults it. The EffortManager at manager.py:434-460 already has a `validate_against_capability_matrix()` method that cross-checks -- this pattern should extend to the router layer.

#### N4. No feature-requirement annotation on RoutingDecision

`RoutingDecision` (models.py:66-100) carries `model`, `tier`, `complexity`, `confidence`, `cost_estimate_usd`, and effort fields, but does not indicate what features the routed model supports. The caller cannot tell whether the model supports `vision` or `json_mode` without separately consulting the CapabilityMatrix. Adding a `features: dict[str, bool]` field to `RoutingDecision` would make the decision self-describing.

#### N5. OpenAI streaming doesn't emit `tool_call_start` for continued tool calls

In `openai.py` streaming (lines 168-187), when a `tool_calls` delta contains only `arguments` (no `id` — meaning a continuation of a previously started tool call), the code correctly appends arguments to `current_tool` but does not check for tool_call_end when a `finish_reason` is present. The OpenAI streaming path may silently drop tool call termination for streaming tool calls that complete across multiple SSE events.

#### N6. Anthropic adapter silently uses aiohttp fallback for errors too

In `anthropic.py:222-225`, the `except ImportError` block catches `httpx` not being installed and falls back to `_chat_via_http`. However, the broader `except Exception` at line 224 catches all other exceptions and calls `_translate_error`. If `httpx` is installed but the HTTP call fails with a transport error, `_chat_via_http` is never tried. The aiohttp fallback is only for import failures, not network failures.

### AI Engineer Summary

The Tier 1 foundation is architecturally well-structured: the provider protocol, capability matrix, effort scale, and 3-tier router are cleanly separated with well-defined interfaces. However, the router operates as a **model recommender**, not a **runtime dispatcher**. It selects a model name and returns it, but does not enforce feature compatibility, context window fit, or provider health at decision time. The connection between the router's output and the actual adapter call is a handoff point with no error recovery.

| # | File | Line | Severity | Defect |
|---|------|------|----------|--------|
| B1 | `providers.py` / `google.py` | 185-205 / 53-58 | **BLOCKING** | Google provider registered as routable but non-functional stub |
| B2 | `interface.py` / all adapters | 217 / across | **BLOCKING** | No runtime provider failure fallback loop; retry config declared but never implemented |
| B3 | `router.py` / `models.py` | 299-359 / 62-63 | **BLOCKING** | `supports_tool_use` and `context_window` stored but never enforced during routing |
| B4 | `models.py` | 150-152 | **BLOCKING** | Cost estimates are hardcoded complexity constants, disconnected from actual per-model pricing |
| N1 | `neural_ucb.py` | 20-27 | NON-BLOCKING | NeuralUCB cost estimates duplicate pricing data from ProviderRegistry |
| N2 | `interface.py` / all adapters | 182 / across | NON-BLOCKING | CONTEXT_OVERFLOW error code defined but never raised by any adapter |
| N3 | `router.py` vs `capability.py` | across | NON-BLOCKING | Router never consults CapabilityMatrix for feature-aware routing |
| N4 | `models.py` | 66-100 | NON-BLOCKING | RoutingDecision lacks feature-support annotation |
| N5 | `openai.py` | 168-187 | NON-BLOCKING | OpenAI streaming may silently drop tool call termination for multi-SSE-event tool calls |
| N6 | `anthropic.py` | 222-225 | NON-BLOCKING | aiohttp fallback only activates on ImportError, not on transport errors |

---

## Security Review

**Reviewer**: Senior Security Engineer
**Verdict: NON-BLOCKING** — No authentication bypass, no credential leakage in transit or logs, no code injection surfaces, no hardcoded secrets. All findings are improvement suggestions.

### Credential Handling

Credentials are handled per-provider exclusively from environment variables. No hardcoded keys exist in the source tree.

- **interface.py:214** — `ProviderConfig.api_key` is the single point where all adapters receive their key.
- **interface.py:222-233** — `ProviderConfig.__repr__` masks the key to `"prefix...suffix"` pattern, preventing leak in logs and `repr()` output.
- **providers.py:66-75** — `ProviderRegistry.get_api_key()` reads keys from `os.environ`. Keys are never persisted in files or config objects.
- **providers.py:138,167,189,211,240** — Built-in registrations map providers to env var identifiers (`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`). Only the name of the env var is stored.

Each adapter applies the key to its HTTP transport via headers (`x-api-key` or `Authorization: Bearer`). The Google adapter is a stub and does not use the key at all.

### Secret Leakage in Logs

Logging across all four adapters is minimal and avoids credential emission.

- All adapters create `logger = logging.getLogger(__name__)` but never log the request body or the API key.
- **providers.py:70,74** — Warning/debug messages log only the env var name, not the value.
- **interface.py:143** — `ChatResponse.raw: Any = None` stores the full provider API response body. Provider responses do not echo back the API key, but downstream consumers could log or serialize this field. **Recommendation**: add a docstring note advising consumers not to log `raw` directly.
- **interface.py:198** — `ProviderError.raw: Any = None` similarly stores raw error bodies. Currently never populated, but fragile if future code changes this.
- **anthropic.py:411, deepseek.py:390** — Error messages in fallback HTTP paths embed `error_text[:500]`. If a provider error response echoes back the request payload, the first 500 characters could contain sensitive content. This is a provider-behavior risk, not a Lyra bug.

### Injection Surfaces

No code injection vectors found.

1. **consensus_router.py:347** — `logger.error(f"Model {name} failed: {e}")` uses f-string formatting instead of lazy %-formatting. Data comes from within the system, so not exploitable, but f-strings in logging defeat deferred string construction. Recommend `logger.error("Model %s failed: %s", name, e)`.
2. **deepseek.py:346-361** — `_build_messages()` injects `effort_instruction` into the system message content. `effort_instruction` is supplied by the EffortManager (system-level configuration), not user input. No injection vector.
3. No `eval()`, `exec()`, `subprocess`, `os.system`, `pickle`, or unsafe `yaml.load()` found in any Tier 1 source file.
4. All streaming parsers parse provider-sourced SSE data with `json.loads()`. Data originates from the provider API, not user input.

### Other Security Observations

5. **interface.py:214** — `ProviderConfig` is a mutable `@dataclass` storing the API key as a plain string. For a CLI session this is standard. Would be a concern if serialized or shared across process boundaries.
6. **anthropic.py:160-162, openai.py:56, deepseek.py:148** — All adapters construct `self._base_url` from `config.base_url` using `or` fallback to a hardcoded default. Custom base URLs are by design (self-hosted/open-weights providers) and not a defect. The `base_url` should come from user configuration, not unvalidated input.
7. **Google adapter is a stub** (google.py:53-58) — Non-operational. No security concern, but the empty shell could mislead callers.
8. **Missing `get_provider` factory** — The `__init__.py` docstring shows `get_provider("anthropic", api_key="sk-...")` as an example, but no such factory function exists. No centralized credential-validation gate. Not a vulnerability but an inconsistency.

### Security Summary

| Area | Finding | Severity |
|------|---------|----------|
| Hardcoded keys | None found. All keys from env vars. | -- |
| Credential masking | `ProviderConfig.__repr__` masks key. | -- |
| Log leakage (keys) | No key values logged. | -- |
| Log leakage (raw response) | `ChatResponse.raw` stores full response. Advise documentation. | NON-BLOCKING |
| f-string in logging | `consensus_router.py:347` | NON-BLOCKING |
| Code injection | No eval/exec/subprocess/os.system in Tier 1 | -- |
| Missing factory | `get_provider` referenced in docstring but not implemented | NON-BLOCKING |
| Google stub | Not operational; no key validation | NON-BLOCKING |
| Error body in message | 500-char truncation in fallback paths | NON-BLOCKING |

**FINAL VERDICT: NON-BLOCKING.** No authentication bypass, no credential leakage, no code injection surfaces, no hardcoded secrets. The Tier 1 provider abstraction is architecturally sound from a security perspective. All findings are improvement suggestions -- none would block a release.

---

## Consolidated Verdict

**BLOCKING**

Five blocking defects were identified across the Architect and AI Engineer reviews. The Security review found no blocking issues. The consolidated blocking items are:

1. **A1**: DeepSeek streaming tool-call completion — `tool_call_end` and `done` events never emitted when `finish_reason == "tool_calls"` (Architect)
2. **B1**: Google provider registered as routable but non-functional stub — router can route to a provider that unconditionally fails (AI Engineer)
3. **B2**: No runtime provider failure fallback loop — `max_retries=3` declared in `ProviderConfig` but never implemented in any adapter; no cross-provider fallback mechanism (AI Engineer)
4. **B3**: `supports_tool_use` and `context_window` stored in `ModelAssignment` but never enforced by `_build_decision()` — tasks exceeding a model's context window or requiring unsupported features can be routed to incompatible models (AI Engineer)
5. **B4**: Cost estimates disconnected from actual model pricing — `get_cost_estimate()` returns hardcoded complexity constants, not per-model pricing, producing consistently misleading cost previews (AI Engineer)

The router currently operates as a model recommender, not a runtime dispatcher. It selects a model name and returns it but does not enforce feature compatibility, context window fit, or provider health at decision time. The connection between the router's output and the actual adapter call is a handoff point with no error recovery.

---

## Required Remediations

### Blocking (5)

| # | Source | File(s) | Remediation |
|---|--------|---------|-------------|
| R1 | Architect A1 | `adapters/deepseek.py:280-306` | Fix streaming tool-call termination: yield `tool_call_end` (if `current_tool` is set) and `done` unconditionally when `finish_reason` is present, regardless of whether `delta.tool_calls` is falsy. Match the OpenAI adapter's correct behavior at `openai.py:194-213`. Re-run streaming tool call tests for DeepSeek. |
| R2 | AI Engineer B1 | `providers.py:83-101,185-205` / `google.py:53-58` | Add a `provider_status: Literal["functional", "stub"]` field to `ModelAssignment` and filter stub providers out of `get_best_model_for_tier()` candidates. Alternatively, implement the Google adapter. |
| R3 | AI Engineer B2 | `interface.py:217` / all adapters | Implement adapter-level retry with exponential backoff and jitter in each adapter's HTTP call path. Add a cross-provider fallback mechanism at the router level triggered by `ProviderError(..., retryable=True)`. |
| R4 | AI Engineer B3 | `router.py:299-359` / `models.py:62-63` | Add a `required_features: list[str]` parameter to `router.route()`. Filter `ModelAssignment` candidates by `context_window` (against estimated input size) and `supports_tool_use` (when the task declares tool requirements) before selecting the cheapest model. |
| R5 | AI Engineer B4 | `models.py:150-152` | Replace the static `_COST_ESTIMATES` dict with dynamic computation using `ModelAssignment.cost_per_1m_tokens`, estimated input token count, and estimated output token count (accounting for output tokens being 3-5x more expensive). |

### High-Priority Non-Blocking (recommended before Phase 3)

| # | Source | Remediation |
|---|--------|-------------|
| R6 | AI Engineer N1 | Derive NeuralUCB `_MODEL_COST_ESTIMATES` from ProviderRegistry per-model pricing. |
| R7 | AI Engineer N2 | Map provider context-length-exceeded errors to `ErrorCode.CONTEXT_OVERFLOW` in each adapter's `_translate_error`. |
| R8 | AI Engineer N3 | Wire `CapabilityMatrix` into the router's feature-aware filtering (alongside R4). |
| R9 | AI Engineer N4 | Add `features: dict[str, bool]` to `RoutingDecision` for self-describing routing outputs. |
| R10 | AI Engineer N5 | Audit OpenAI streaming path for tool-call termination parity with the DeepSeek fix (R1). |
| R11 | Architect A4 | Replace static `plan_workflow()` with LLM-based script generation per 19-ultracode-replication.md:88. |

### Non-Blocking (improvement suggestions)

| # | Source | Remediation |
|---|--------|-------------|
| R12 | Architect A2 | Document provider clamping behavior in user-facing effort indicators. |
| R13 | Architect A3 | Rename one of the two `orchestrator` modules to avoid naming collision. |
| R14 | Architect A5 | Make `_orchestration_provider` a mutable field or add a constructor parameter. |
| R15 | AI Engineer N6 | Fix anthropic.py fallback to try `_chat_via_http` on transport errors, not only ImportError. |
| R16 | Security | Add docstring warning to `ChatResponse.raw` and `ProviderError.raw` about sensitivity. |
| R17 | Security | Replace f-string logging with lazy %-formatting in `consensus_router.py:347`. |
| R18 | Security | Implement `get_provider()` factory function referenced in `__init__.py` docstring. |

---

## Sign-off

| Reviewer | Role | Verdict | Date |
|----------|------|---------|------|
| [Pending] | Senior Architect | BLOCKING — DeepSeek streaming tool-call termination must be fixed (R1) | 2026-06-01 |
| [Pending] | Senior AI Engineer | BLOCKING — Four runtime gaps: Google stub routing (R2), no fallback loop (R3), unenforced feature/context constraints (R4), disconnected cost estimates (R5) | 2026-06-01 |
| [Pending] | Senior Security Engineer | NON-BLOCKING — No security defects. All keys from env vars, no credential leakage, no injection surfaces. | 2026-06-01 |

**Sign-off criteria**: All five blocking remediations (R1-R5) must be implemented and verified before Tier 1 can be signed off as production-ready. The six high-priority non-blocking items (R6-R11) are strongly recommended before Phase 3 multi-provider deployment.
