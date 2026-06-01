# UltraCode Replication -- Architecture Deep Dive

## 1. Executive Summary

Ultracode is Lyra's replication of Claude Code's full-effort data path combined with its auto-orchestration toggle. It is emphatically NOT a sixth API budget tier -- ultracode sends the same `xhigh` reasoning budget (16,384 tokens) as Claude Code's `/effort xhigh` and simply adds the orchestration flag on top. This design choice is what makes ultracode portable to providers that only expose a handful of effort levels (DeepSeek, open-weight models): because the only semantic difference from `xhigh` is a boolean toggle, every provider already supports it. The whole system decomposes into four independently-useful primitives: a six-item effort scale with per-provider budget mapping, a lightweight auto-orchestration trigger, a code-driven dynamic workflow engine, and an adversarial cross-checking protocol. These four primitives compose through a thin bridge layer (`packages/lyra-core/src/lyra_core/orchestration/effort_bridge.py`) that reads the active effort level, evaluates task complexity, and dispatches to the workflow engine when the threshold is met.

The architecture spans six packages: `lyra-effort` (effort scale definition and per-provider mapping), `lyra-workflow` (orchestration trigger, workflow engine, and adversarial verifier), `lyra-provider` (provider interface, capability matrix, and provider-specific adapters), `lyra-core` (effort bridge that wires the primitives together), `lyra-cli` (steering engine for mid-run user corrections), and `lyra-orchestration` (general-purpose agent coordinator with event bus). The key architectural insight is that every provider adapter in `lyra-provider/src/lyra_provider/adapters/` already carries the `ChatRequest.effort_budget_tokens`, `ChatRequest.effort_instruction`, and `ChatRequest.effort_reasoning` fields from the canonical interface (`lyra-provider/src/lyra_provider/interface.py`, line 112-115), so ultracode is transparent to the adapter layer. The only change is the boolean orchestration flag that routes to the workflow engine instead of handling turn-by-turn.

The following deep-dive examines each primitive's code-level implementation, traces the full data path from `/effort ultracode` through provider dispatch, documents how behavior degrades across providers with different capabilities, and identifies the breakthroughs that Lyra adds beyond what Claude Code provides natively.

## 2. The Four Primitives

### 2.1 Primitive 1: Six-Item Effort Scale

The effort scale is defined in `packages/lyra-effort/src/lyra_effort/models.py` as the `EffortLevel` enum with six values: `LOW`, `MEDIUM`, `HIGH`, `XHIGH`, `MAX`, and `ULTRACODE`. Each level carries three derived properties. `is_persistent` determines whether the level survives a session restart -- `low` through `xhigh` persist; `max` and `ultracode` are session-only and reset to `high` on next load. `reasoning_budget` returns the default Anthropic `budget_tokens` equivalent (1024, 4096, 8192, 16384, 32000, and 16384 respectively). `orchestration_enabled` is `True` only for `ultracode` -- this is the invariant that distinguishes ultracode from every other level.

The budget constants live in `_DEFAULT_BUDGETS` (line 55 of `models.py`). The invariant `ultracode == xhigh` is enforced by the test suite at line 64 of `packages/lyra-effort/tests/test_effort.py`: `assert EffortLevel.ULTRACODE.reasoning_budget == EffortLevel.XHIGH.reasoning_budget`. The orchestration invariant is tested at line 67: `assert EffortLevel.ULTRACODE.orchestration_enabled is True` and every other level is `False`.

The data model comprises five dataclasses. `EffortLevel` is an enum (line 14) with the six string values and three computed properties (`is_persistent`, `reasoning_budget`, `orchestration_enabled`). `EffortMapping` (line 66) is a frozen dataclass carrying the resolved API parameters for a single (level, provider) pair: `budget_tokens`, `thinking_instruction`, `reasoning_effort`, `max_tokens_per_turn`, and `orchestration_enabled`. `OrchestrationConfig` (line 95) is a frozen dataclass for the orchestration toggle: `enabled: bool`, `auto_trigger_threshold: str` (one of trivial/low/medium/high/all), and `keyword_trigger_enabled: bool`. `ProviderEffortCapability` (line 113) declares what effort features a provider supports: `supports_budget_tokens`, `supports_reasoning_effort`, `supports_prompt_instructions`, and `max_effort_level`. `EffortConfig` (line 135) is the session-level config that gets persisted: `current_level`, `orchestration`, and `provider_overrides`.

Each of these models serves a distinct responsibility in the ultracode pipeline. `EffortLevel` is the user-facing enum, `EffortMapping` is the provider-facing translation result, `OrchestrationConfig` is the toggle that gates entry into the workflow engine, `ProviderEffortCapability` is the registry that prevents sending unsupported effort levels to a provider, and `EffortConfig` is the serialization boundary between sessions.

**Per-provider budget mapping table.**

The `EffortManager` class in `packages/lyra-effort/src/lyra_effort/manager.py` translates each abstract effort level into provider-specific API parameters through the `map_effort()` method (line 223). For each provider, it checks a capability registry and routes accordingly:

| Provider   | API mechanism for effort       | LOW  | MEDIUM | HIGH  | XHIGH | MAX   | ULTRACODE |
|------------|--------------------------------|------|--------|-------|-------|-------|-----------|
| Anthropic  | `thinking.budget_tokens`       | 1024 | 4096   | 8192  | 16384 | 32000 | 16384     |
| DeepSeek   | System-prompt instruction      | Be concise | Think briefly | Think step by step | Think deeply | Max reasoning | Think deeply |
| OpenAI     | `reasoning_effort` parameter   | low  | low    | medium| high  | high  | high      |
| Google     | System-prompt instruction      | Be concise | Think briefly | Think step by step | Think deeply | Max reasoning | Think deeply |
| OpenRouter | `thinking.budget_tokens`       | 1024 | 4096   | 8192  | 16384 | 32000 | 16384     |
| Open-weight| Prompt prefix                  | Quick answer | Brief analysis | Careful analysis | Deep analysis | Deep analysis | Deep analysis |

The provider effort capabilities are declared at line 41 of `manager.py` in `_PROVIDER_CAPABILITIES`:

- Anthropic: `supports_budget_tokens=True`, `max_effort_level=MAX`
- DeepSeek: `supports_budget_tokens=False`, `supports_reasoning_effort=False`, `supports_prompt_instructions=True`, `max_effort_level=XHIGH`
- OpenAI: `supports_budget_tokens=False`, `supports_reasoning_effort=True`, `max_effort_level=XHIGH`
- Google: `max_effort_level=HIGH`
- OpenRouter: `supports_budget_tokens=True`, `max_effort_level=MAX`
- Open-weights: `max_effort_level=HIGH`

The thinking instructions for providers without a native reasoning API are stored in `_THINKING_INSTRUCTIONS` (line 90 of `manager.py`). Each effort level maps to a prose instruction prepended to the system prompt. For open-weight models, the instructions are deliberately shorter because these models have smaller context windows and weaker instruction-following.

OpenAI's `reasoning_effort` mapping is in `_OPENAI_REASONING_EFFORT` (line 121): `low` and `medium` map to `"low"`, `high` maps to `"medium"`, and `xhigh`, `max`, and `ultracode` all map to `"high"`. This is because OpenAI only exposes three reasoning effort levels, so the six-level Lyra scale must compress.

**The EffortBridge mechanism -- how effort level gates orchestration.**

The `EffortBridge` class in `packages/lyra-core/src/lyra_core/orchestration/effort_bridge.py` is a frozen dataclass that reads the effort level and wires it to auto-orchestration. Its `should_orchestrate()` method (line 61) returns `False` unless `effort_level.orchestration_enabled` is `True` (i.e., only for ultracode). Its `evaluate()` method (line 70) delegates to the `AutoOrchestrator` when orchestration is enabled, returning an `OrchestrationDecision` that includes complexity classification and estimated phases/agents. Its `plan_workflow()` method (line 89) creates a `WorkflowScript` with phase names (Discover, Verify, Report) and multi-provider model assignments: DeepSeek Flash for cheap exploration, Claude Sonnet for reliable verification, Claude Opus for best-quality synthesis.

The `from_config()` factory (line 114) resolves string effort levels (e.g., `"ultracode"` from user config) and falls back to `HIGH` on invalid values.

**Step-by-step: The EffortManager.set_level() implementation.**

Looking at the `set_level()` method (line 191 of `manager.py`) more closely:

```python
def set_level(self, level: EffortLevel) -> None:
    self._config = EffortConfig(
        current_level=level,
        orchestration=OrchestrationConfig(
            enabled=(level == EffortLevel.ULTRACODE),
            auto_trigger_threshold=self._config.orchestration.auto_trigger_threshold,
            keyword_trigger_enabled=self._config.orchestration.keyword_trigger_enabled,
        ),
        provider_overrides=self._config.provider_overrides,
    )
```

It creates a new `EffortConfig` (not mutating the existing one -- follows the immutability principle from coding rules). The orchestration `enabled` field is set to `True` only when the level is `ULTRACODE`. All other levels leave orchestration at whatever it was before.

The orchestration can also be set independently via `set_orchestration()` (line 209), which separates the effort level from the orchestration toggle. This exists for the case where a user wants orchestration without the xhigh budget, but in practice the EffortBridge only respects orchestration if the effort level is ultracode (enforced by `should_orchestrate()` at line 61 of `effort_bridge.py` which checks `self.effort_level.orchestration_enabled`).

**Step-by-step: what happens when user types `/effort ultracode`.**

1. The CLI in `packages/lyra-cli/src/lyra_cli/steering.py` receives the `/effort ultracode` command. The steering module interprets the command via the `SteeringEngine` or a dedicated effort command handler.

2. It calls `EffortManager.set_level(EffortLevel.ULTRACODE)` in `packages/lyra-effort/src/lyra_effort/manager.py` line 191. This creates an entirely new `EffortConfig` -- no mutation (see immutability principle in coding rules).

3. `set_level()` creates a new `EffortConfig` with `current_level=ULTRACODE` and `orchestration.enabled=True` (line 200). The `auto_trigger_threshold` and `keyword_trigger_enabled` values are carried over from the previous config.

4. The persistence system in `save()` (line 351) treats ultracode as non-persistent -- it is saved as `"high"` on disk with `orchestration_enabled=False`. On next load, the session starts at high; ultracode must be re-enabled explicitly. This is a safety measure: if a user walks away from a terminal with ultracode active, the next session starts at a safe default.

5. When the user next types a task prompt, the system calls `EffortBridge.evaluate(prompt)`. The bridge is constructed at the agent-loop boundary and receives the current effort level from the EffortManager.

6. The bridge method `evaluate()` (line 70 of `effort_bridge.py`) first checks `self.effort_level.orchestration_enabled`. For ultracode, this is True. It then delegates to `self.orchestrator.evaluate(prompt)`, passing the provider for degradation decisions.

7. The `AutoOrchestrator.evaluate()` method (line 92 of `orchestrator.py`) applies the six-step algorithm: ultrathin detection, trivial rejection, keyword counting, complexity classification, threshold comparison, and provider-aware degradation. For a prompt like "Audit all auth endpoints for PCI compliance across the codebase", the keyword count would match "audit" (1 complex), "across" (1 complex), "all" (implicit in "all"), and "compliance" (1 complex) -- likely triggering HIGH complexity with `should_orchestrate=True`.

8. The bridge method `plan_workflow(decision)` (line 89 of `effort_bridge.py`) creates a `WorkflowScript` with phases. For HIGH complexity, it creates three phases: "Discover", "Verify", and "Report". The providers dict is set to `{"explore": "deepseek-flash", "verify": "claude-sonnet", "synthesize": "claude-opus"}`.

9. The script is dispatched to `WorkflowEngine.start(script)` in `packages/lyra-workflow/src/lyra_workflow/engine.py` line 315. This spawns a daemon thread that iterates through phases and dispatches tasks.

10. Meanwhile, the actual LLM call for the current task receives the xhigh budget (16,384 tokens) via `EffortManager.map_effort()` which resolves ultracode to `effective_level = XHIGH` (line 249) and returns `budget_tokens=16384`. The `map_effort()` method also checks for provider-specific overrides (line 241) and clamps to the provider's max supported level (line 253-255).

11. The `ChatRequest` built by the provider adapter carries the effort parameters. For Anthropic, `effort_budget_tokens=16384` is set on the request. The `AnthropicProvider.chat()` method (line 168 of `anthropic.py`) reads this and injects `thinking.budget_tokens=16384` into the API body.

12. If the provider is DeepSeek, the `ChatRequest.effort_instruction` is set to "Think deeply. Consider alternatives. Verify your reasoning." instead of the `budget_tokens` parameter. The `DeepSeekProvider._build_messages()` method (line 338 of `deepseek.py`) injects this into the system prompt.

**The ChatRequest effort fields in detail.**

The canonical `ChatRequest` dataclass (line 98 of `interface.py`) carries three effort-related fields:

- `effort_budget_tokens: int | None` (line 113): For providers with a native budget API (Anthropic, OpenRouter). Set by the EffortManager from `mapping.budget_tokens`.
- `effort_instruction: str | None` (line 114): For providers without a native API (DeepSeek, Google, open-weights). Set from `mapping.thinking_instruction`.
- `effort_reasoning: str | None` (line 115): For OpenAI's `reasoning_effort` parameter. Set from `mapping.reasoning_effort`.

All three fields are passed simultaneously -- the provider adapter ignores the ones it does not use. This is by design: the EffortMapping carries all three representations, and the adapter picks the right one. Each adapter has its own `if request.X:` check. The Anthropic adapter checks `if request.effort_budget_tokens:` (line 197 of `anthropic.py`). The OpenAI adapter checks `if request.effort_reasoning:` (line 81 of `openai.py`). The DeepSeek adapter checks `if request.effort_instruction:` (line 346 of `deepseek.py`). The Google adapter is a stub and ignores all three (line 53 of `google.py`).

### 2.2 Primitive 2: Auto-Orchestration Toggle

The auto-orchestration trigger lives in `packages/lyra-workflow/src/lyra_workflow/orchestrator.py`. The `AutoOrchestrator` class (line 50) estimates task complexity from the user prompt in <50ms using keyword matching and word count -- it never blocks the user.

**How Lyra decides whether a task warrants a workflow.**

The decision algorithm in `evaluate()` (line 92) proceeds in order:

1. **Ultrathink detection** (line 123): If the prompt contains the word "ultrathink", the decision immediately returns `should_orchestrate=False` with `ultrathink_triggered=True`. This triggers one-off deep reasoning on the current turn without escalating to a full workflow.

2. **Trivial rejection** (line 133): Prompts under 5 words are classified `TRIVIAL` and never orchestrated.

3. **Keyword counting** (line 142): Complex keywords (audit, migrate, refactor, research, investigate, across, all files, codebase, architecture, etc.) and medium keywords (multiple, analyze, review, optimize, integrate, etc.) are counted.

4. **Complexity classification** (line 150):
   - >= 3 complex keywords or (>= 2 complex keywords + word count > 50) = `HIGH`
   - >= 1 complex keyword or >= 3 medium keywords = `MEDIUM`
   - >= 1 medium keyword or word count > 30 = `LOW`
   - Otherwise = `TRIVIAL`

5. **Threshold comparison** (line 171): Orchestration triggers if complexity order >= threshold order. Default threshold is `MEDIUM`.

6. **Provider-aware degradation** (line 173): For open-weights, auto-trigger is suppressed entirely and replaced with a flag (`provider_fallback=True`). For DeepSeek, an explicit fallback prompt is appended: "This task may benefit from a workflow. Plan one?"

The `_COMPLEX_KEYWORDS` frozenset (line 66) and `_MEDIUM_KEYWORDS` frozenset (line 75) are deliberately curated sets. Complex keywords include `"security review"`, `"compliance"`, `"end-to-end"`, `"full pipeline"`, and `"enterprise"` -- these are the signals that a task needs more than a single-turn response.

**The understand--change--verify loop.**

The auto-orchestration toggle activates what Lyra calls the "ultracode loop": for any triggered task, the workflow engine runs a three-phase pipeline:

- **Discover phase**: Multiple agents fan out in parallel to understand the codebase, the problem domain, and the relevant context. They use DeepSeek Flash (cheap, fast) for this exploration.
- **Verify phase**: Findings are cross-checked by agents running on Claude Sonnet (reliable verification). The AdversarialVerifier runs claims through a 3-critic panel.
- **Report or Change phase**: If the task is read-only (audit, research), the synthesize phase produces a structured report using Claude Opus. If the task is mutating (write code, edit files), agents execute the changes under AVP gating.

Each phase runs sequentially (phases within a workflow are ordered) but all tasks within a phase run in parallel up to the 16-agent concurrency cap.

**The "workflow" keyword trigger as lighter-weight alternative.**

If a user includes the word "workflow" in their prompt without enabling ultracode, the `AutoOrchestrator` still triggers a one-off workflow. This is controlled by `OrchestrationConfig.keyword_trigger_enabled` (default `True` in `packages/lyra-effort/src/lyra_effort/models.py` line 109). When the word "workflow" appears in the prompt, the orchestrator treats it as an explicit request and routes through the workflow engine even if the session effort level is `high` or `medium`.

The keyword trigger is the lighter-weight alternative to setting `/effort ultracode` for the whole session. It creates exactly one workflow for the current task and then returns to turn-by-turn mode. This is the same pattern as Claude Code's `workflow:` keyword in prompts.

**Provider degradation: how auto-trigger reliability varies.**

The `evaluate()` method accepts a `provider` parameter (line 94) that enables provider-aware degradation:

- **Anthropic** (native): Full auto-trigger reliability. The orchestrator's complexity estimation is the sole gate. No fallback text is needed because the Anthropic model reliably follows orchestration instructions.
- **OpenAI** (good): Full auto-trigger. The `reasoning_effort` parameter is set by the EffortManager, and the complexity estimation runs identically to Anthropic. No fallback text.
- **DeepSeek** (prompt fallback): Auto-trigger runs, but the reasoning field gets an appended fallback prompt: "This task may benefit from a workflow. Plan one?" This is because DeepSeek models are less reliable at recognizing multi-step task requirements from implicit context. The fallback prompt makes the orchestration intent explicit.
- **Open-weight** (keyword-only): Auto-trigger is disabled entirely. If `should=True` is returned by the threshold logic, it is overridden to `False` and `provider_fallback=True` is set. Only explicit "workflow" keywords in the user prompt trigger workflows. Open-weight models have limited instruction following and unreliable self-initiation of multi-step plans.

### 2.3 Primitive 3: Dynamic Workflow Engine

The workflow engine in `packages/lyra-workflow/src/lyra_workflow/engine.py` is the execution substrate for ultracode. It runs workflow scripts as code in a separate runtime -- not as turn-by-turn subagent orchestration that fills the context window.

**Code-driven orchestration (JS/script format).**

Workflows are defined as `WorkflowScript` objects (line 95) containing named `WorkflowPhase`s (line 83), each containing `AgentTask`s (line 63). Each task specifies a prompt, a model, and an optional JSON schema for structured output. The `ScriptVM` class (line 105) is a static analyzer that validates workflow scripts before execution -- it checks for denied globals (`eval`, `exec`, `require`, `import`, `__import__`, `open`, `compile`) and denied modules (`fs`, `child_process`, `os`, `subprocess`, `sys`, `shutil`, `socket`, `http`, `urllib`). Scripts that fail analysis are rejected before they start.

The script format supports multi-provider assignment via the `providers` dict (line 101), mapping roles to specific models. In `EffortBridge.plan_workflow()` (line 89 of `effort_bridge.py`), the default provider assignment is:

```python
WorkflowScript(
    providers={
        "explore": "deepseek-flash",   # Cheap, fast discovery
        "verify": "claude-sonnet",     # Reliable verification
        "synthesize": "claude-opus",   # Best quality synthesis
    },
)
```

This is the key cost optimization: expensive models are reserved for the tasks where quality matters most, while cheap models handle the bulk of parallel exploration.

**Background execution with intermediate results in script variables.**

Workflows run in background threads. The `WorkflowEngine.start()` method (line 315) creates a daemon thread (`threading.Thread(target=self._execute, args=(workflow_id,), daemon=True)`) that immediately returns a workflow ID. The session stays responsive -- the user can check progress, pause, or steer mid-run.

The `_execute()` method (line 428) iterates through phases sequentially. Within each phase, tasks are dispatched in batches of `MAX_CONCURRENT` (16). Each task invokes the provider adapter layer through `_run_task()` (line 472), which builds a `ChatRequest`, dispatches through the `AbstractProvider.chat()` interface, and extracts real token usage from the provider response. Results are stored directly on the `AgentTask` object -- they do NOT flow through the orchestrator's context window. This is the critical architectural insight: intermediate results live in script variables on the task objects, not in the conversation history.

The `PauseResumeSerializer` class (line 165) serializes all completed agent results, in-progress agent states, phase metadata, and cumulative cost to a JSON snapshot. On resume, the `deserialize()` method restores the script, requeues incomplete tasks, and calls `start()` again.

**Subagent cap (16 concurrent, 1000/run).**

Two hard caps are enforced:

- `MAX_CONCURRENT = 16` (line 277): The maximum number of agents that run simultaneously. This matches Claude Code's default and prevents overwhelming the provider API rate limits. Within each phase, tasks are batched into groups of 16, dispatched, awaited, and the next batch is started.
- `MAX_TOTAL_AGENTS = 1000` (line 278): The absolute maximum number of agents across the entire workflow run. The `start()` method checks `self._agent_count >= self.MAX_TOTAL_AGENTS` before starting. This prevents runaway workflows.

Additionally, `BACKPRESSURE_QUEUE_DEPTH = 48` (line 279) signals congestion: when the agent count exceeds 48, the progress status includes `backpressure: True`, which the steering engine uses to advise the user to reduce scope.

**Resume/pause/stop/restart semantics.**

The workflow engine implements a state machine via `WorkflowStatus` (line 41):

- `PENDING`: Created but not started.
- `RUNNING`: Actively executing phases. From RUNNING, the user can call `pause()` or `cancel()`.
- `PAUSED`: Mid-run pause. The `pause()` method (line 379) returns a JSON snapshot. The engine discards in-progress agent threads and sets status to PAUSED. To resume, the user calls `resume(snapshot)` (line 402), which deserializes the snapshot into a new script, requeues any QUEUED or RUNNING tasks, and calls `start()`. The resumption picks up from the current phase.
- `COMPLETED`: All phases finished without error.
- `FAILED`: Fatal error during execution. Not resumable.
- `CANCELLED`: User-initiated cancellation via `cancel()` (line 418). Not resumable.

The `cancel()` method is straightforward: it removes the workflow ID from the running set and sets the status to CANCELLED. The background `_execute()` method checks the running set between phase iterations and returns early if cancelled.

**Progress view (phases x agent count x token total).**

The `get_status()` method (line 341) returns a structured status dict:

```python
{
    "workflow_id": str,
    "status": str,                  # running | paused | completed | failed | cancelled
    "current_phase": str,           # Discover | Verify | Report
    "total_tasks": int,
    "completed_tasks": int,
    "failed_tasks": int,
    "agent_count": int,             # Cumulative agents dispatched so far
    "total_tokens": int,            # Cumulative tokens consumed
    "total_cost_usd": float,
    "elapsed_seconds": float,
    "backpressure": bool,
}
```

The dashboard renderer (in `packages/lyra-cli/src/lyra_cli/steering.py` line 296, `stats` property) reads the workflow status and presents it as a live-updating table. The `total_cost_usd` is computed from actual provider usage, not estimated -- the `_estimate_cost()` method (line 565 of `engine.py`) uses provider-specific pricing when available or a conservative fallback ($0.01/1M input, $0.03/1M output).

**Detailed task execution lifecycle in the WorkflowEngine.**

When `_run_task()` executes (line 472), it follows a precise lifecycle:

1. **Status transition**: The task status changes from QUEUED to RUNNING. `started_at` is recorded from `time.time()`.

2. **Provider resolution** (line 485): The `_resolve_provider()` method (line 531) looks up the provider adapter for the task's model. It first checks the `_provider_registry` (from `lyra-router`) if available, then falls back to `_default_provider`. If neither is configured, it raises `RuntimeError` -- this is a hard fail because there is no safe default.

3. **ChatRequest construction** (line 488): A canonical `ChatRequest` is built with the task prompt as a single USER message. The model name from the task, max tokens from the engine's default, and temperature from the engine's default are used. Note that effort parameters are NOT injected here -- the ChatRequest in the workflow engine does not carry effort_budget_tokens. This is because workflow agents are ephemeral sub-tasks running on designated models (deepseek-flash, claude-sonnet, etc.), not the session's primary model. The effort parameters only apply to the primary session LLM call.

4. **Async bridge** (line 496): The provider's `chat()` method is async, but the workflow runs in a synchronous background thread (via `threading.Thread`). The `_run_async()` static method (line 547) handles this by calling `asyncio.run(coro)` in a new event loop. If the current thread already has an event loop (edge case), it falls back to a `ThreadPoolExecutor` to run the async call.

5. **Response processing** (line 499): The provider response is parsed. `task.result` gets the response `content`. `task.tokens_used` is computed as `input_tokens + output_tokens` from `response.usage`. `task.cost_usd` is computed from real usage data via `_estimate_cost()`.

6. **Retry on failure** (line 514): If a `ProviderError` is raised, the task increments retries. If `retries < max_retries`, status becomes RETRYING and the task is re-queued. After `max_retries` (default 2), status becomes FAILED. Non-provider exceptions (any other `Exception`) follow the same retry path.

7. **Status transition**: On success, status becomes COMPLETED with `completed_at` recorded. On permanent failure, status becomes FAILED with `completed_at` recorded and `error` set.

**Thread safety in the WorkflowEngine.**

The engine uses a `threading.Lock` (`self._lock` at line 294) to protect shared state: the `_workflows` dict, `_statuses` dict, `_running` set, `_agent_count`, `_total_tokens`, and `_total_cost`. All mutations to these fields happen inside `with self._lock:` blocks. The `start()` method acquires the lock to increment the agent count. The `pause()` method acquires the lock to serialize the snapshot and update the status. The `_execute()` method does NOT hold the lock during the long-running phase iteration -- it only acquires the lock for brief agent-count updates (line 456). This is correct because the status checks between phases (line 436, `if self._statuses.get(workflow_id) != WorkflowStatus.RUNNING`) are a non-atomic read that could see a stale status for a brief moment. In practice, this race is benign: the worst case is one extra task dispatch after a pause command, which is caught on the next iteration.

**Cost estimation strategy.**

The `_estimate_cost()` method (line 565) maps actual token counts to USD:

```python
pricing = self._pricing.get(provider, {}).get(model)
if pricing:
    return (
        input_tokens * pricing.input_per_1m / 1_000_000
        + output_tokens * pricing.output_per_1m / 1_000_000
    )
# Conservative fallback: $0.01/1M input, $0.03/1M output
return input_tokens * 0.00000001 + output_tokens * 0.00000003
```

The `self._pricing` dict is passed at construction time and maps `provider -> model -> {input_per_1m, output_per_1m}`. When pricing data is absent, the fallback uses Claude 4.5 Haiku rates (approximately $0.01/M input, $0.03/M output). This is a conservative estimate -- over-estimating cost is safer than under-estimating.

### 2.4 Primitive 4: Adversarial Cross-Check

The adversarial verification protocol (AVP) is implemented in `packages/lyra-workflow/src/lyra_workflow/avp.py`. It is the quality gate for ultracode workflows: every claim, tool execution, and agent decision passes through a 3-critic cross-model panel before it is accepted.

**Independent agents draft from multiple angles.**

The `AdversarialVerifier` class (line 290) takes a `Claim` and a `critics_fn` -- a callable that returns exactly 3 `CriticVerdict` instances. In production, each `CriticVerdict` comes from a different provider (Anthropic, DeepSeek, OpenAI) to maximize architectural diversity. The source cites research that cross-model correlation is ~14.6x worse than same-model for error detection, meaning diverse critics catch errors that homogeneous critics miss.

The `critics_fn` receives an anonymized copy of the claim (via `ReviewAnonymizer`, line 48). The anonymizer strips identity markers (`agent_id:`, `agent:`, `author:`, `source_agent:`, etc.) from the claim content using `_IDENTITY_MARKERS` (line 65) and generates a deterministic but opaque source ID via SHA-256 hash of `(source + id)` truncated to 12 hex characters. This mitigates identity-driven sycophancy (Run 17 finding from SYNTHESIS.md section 10.1: agents uncritically adopt peer views when they know who wrote what).

**Adversarial review + vote on each claim.**

Each critic produces a `CriticVerdict` (line 166) with four fields:

- `verdict`: `ACCEPT`, `REJECT`, `FLAG`, or `ABSTAIN`.
- `confidence`: Float 0.0-1.0.
- `reasoning`: Explanation string.
- `evidence_tier`: Quality of supporting evidence, A (gold standard) through D (weak).
- `trust_dimensions`: Optional 6-dimension trust vector for A-Trust integration (see below).

The `DecisionMatrix` class (line 233) resolves the 3 verdicts into a final outcome using majority logic:

| Votes (out of 3)   | Outcome  |
|--------------------|----------|
| >= 2 ACCEPT        | ACCEPT   |
| >= 2 REJECT        | REJECT   |
| >= 2 FLAG          | FLAG     |
| 1 each (ACCEPT/REJECT/FLAG) | FLAG (escalate) |

The `1-1-1 split -> FLAG` rule (line 287) is the escalation path. A split vote means the critics disagree fundamentally, and the claim is flagged for human review rather than being accepted or rejected by a narrow majority.

**Filter claims that don't survive cross-checking.**

The `verify()` method (line 345) returns a result dict with:

- `verified: bool`: True only if consensus is ACCEPT.
- `consensus`: The resolved verdict string.
- `confidence`: Average confidence across all 3 critics.
- `evidence_tier`: Best tier among accepting critics.
- `rogue_flag`: Optional boolean from the `RogueAgentMonitor`.
- `verdicts`: Full list with critic_id, provider, verdict, confidence, reasoning.

The calling orchestration layer checks `result["verified"]` before allowing a claim to proceed. Claims that are rejected or flagged are dropped. If a `rogue_flag` is True, the entire agent that produced the claim is paused for human review.

The `RogueAgentMonitor` (line 474 in `avp.py`) tracks per-agent confidence trajectories and detects four failure modes:

1. **Sudden confidence drop** (>0.3 in one step) -> FLAG.
2. **Sustained low confidence** (mean <0.4 over last 5 steps) -> FLAG.
3. **Deteriorating trend** (negative trend >0.2) -> FLAG.
4. **Frequent early termination** (>2 attempts to terminate while uncertain) -> FLAG.

Detection thresholds are at lines 490-493: `SUDDEN_DROP_THRESHOLD = 0.3`, `SUSTAINED_LOW_THRESHOLD = 0.4`, `TREND_DETERIORATION_THRESHOLD = 0.2`, `TERMINATION_LIMIT = 2`.

The `MutationGate` (line 191) optimizes AVP performance: only MUTATING actions (write, delete, execute, deploy) trigger the full 3-critic panel. NON_MUTATING actions (read, search, list, view) pass through without verification overhead. The gate uses keyword whitelists in `_MUTATING_KEYWORDS` and `_NON_MUTATING_KEYWORDS` (lines 203, 210) to classify action descriptions. UNCERTAIN classifications (no keyword match on either list) are treated as mutating by default -- the conservative path.

The A-Trust system in `packages/lyra-workflow/src/lyra_workflow/trust.py` extends AVP beyond simple accept/reject by introducing six Gricean trust dimensions: Quality, Quantity, Relevance, Manner, Sincerity, Competence. Each dimension is a float 0.0-1.0, aggregated via geometric mean (so a single near-zero dimension drags the overall score down). The `TrustWeightedRouter` (line 655 of `trust.py`) evaluates incoming messages, records per-agent trust histories, and computes routing weights. Messages from low-trust agents are downweighted; messages from high-trust agents are amplified. The `trust_from_critic_verdicts()` function (line 860) bridges AVP verdicts into A-Trust scores by mapping critic confidence to Quality, evidence tier to Competence, and consensus consistency to Sincerity.

**The MutationGate optimization in detail.**

The `MutationGate` (line 191 of `avp.py`) classifies action descriptions into MUTATING, NON_MUTATING, or UNCERTAIN using two keyword sets.

The mutating keywords (`_MUTATING_KEYWORDS`, line 203):
```
write, edit, delete, remove, create, update, replace,
commit, push, deploy, execute, run, install, uninstall,
move, rename, copy, chmod, chown, truncate
```

The non-mutating keywords (`_NON_MUTATING_KEYWORDS`, line 209):
```
read, view, list, show, search, find, grep, cat,
head, tail, ls, stat, diff, log, status, describe,
get, fetch, query, check, validate, inspect, audit
```

The `classify()` method (line 216) converts the action description to a set of lowercase words and checks intersection with both keyword sets. The classification rules are:

1. If only mutating keywords match -> MUTATING.
2. If only non-mutating keywords match -> NON_MUTATING.
3. If both match -> MUTATING (conservative: mutation wins).
4. If neither match -> UNCERTAIN.

UNCERTAIN actions are treated as mutating by the `should_trigger_avp()` method (line 418): only MUTATING classifications return True. NON_MUTATING actions skip AVP entirely, saving 3x per-critic cost.

Note that "audit" appears in the NON_MUTATING list (line 214). This is deliberate: a code audit reads files and does not write them. A `MutationGate.classify("audit the auth module")` returns NON_MUTATING. But the `AutoOrchestrator` might still trigger a workflow (because "audit" is a COMPLEX keyword), and that workflow's Verify phase would use AVP on the findings. The gate prevents AVP overhead on every read-only file operation, not on the workflow itself.

**The RogueAgentMonitor detection algorithm.**

The `RogueAgentMonitor` (line 474 of `avp.py`) tracks per-agent confidence trajectories in `AgentConfidenceTrajectory` objects (line 453). Each trajectory stores a list of confidence values and a count of early-termination attempts. The `record_and_check()` method (line 499) records a new data point and runs four independent detectors:

1. **Sudden drop detector** (`_detect_sudden_drop`, line 540): Compares the last two confidence values. If the drop exceeds 0.3, the agent is flagged. This catches the case where an agent suddenly becomes uncertain after being confident.

2. **Sustained low confidence detector** (`_detect_sustained_low`, line 547): Averages the last 5 confidence values. If the mean drops below 0.4, the agent is flagged. This catches agents that are persistently confused rather than momentarily uncertain.

3. **Deteriorating trend detector** (`_detect_deteriorating_trend`, line 554): If the overall trend (last - first) becomes worse than -0.2 over the window, the agent is flagged. This catches gradual degradation rather than sudden drops.

4. **Early termination detector** (`record_early_termination`, line 527): Increments the early termination counter. If the count exceeds 2, the agent is flagged. This is the "Preventing Rogue Agents" pattern: confused agents that terminate early while uncertain sink the task.

If any detector returns True, the `verify()` method sets `rogue_flag=True` in the result dict. The calling orchestration layer then pauses the entire agent for human review. The monitor maintains a `flagged_agents` property (line 571) that returns the list of currently flagged agent IDs, and a `stats` property (line 584) for diagnostics.

**The ReviewAnonymizer -- identity-driven sycophancy mitigation.**

The `ReviewAnonymizer` (line 48) addresses the ACL 2026 finding that multi-agent debate suffers from identity-driven sycophancy: agents uncritically adopt peer views when the author's identity is known. The fix is structural anonymization.

The `anonymize()` method (line 72) creates a new `Claim` with:

1. **Opaque source ID**: The `source` field is replaced with `f"review-item-{sha256(source + id)[:12]}"`. This is deterministic (same claim always gets the same anonymized source) but opaque (reveals nothing about the originating agent).

2. **Marker stripping**: Lines containing identity markers from `_IDENTITY_MARKERS` (line 65) are removed from the content. The markers are: `agent_id:`, `agent:`, `author:`, `reviewer:`, `critic:`, `produced by`, `created by`, `written by`, `submitted by`, `source_agent:`, `owner:`, `assigned_to:`.

The `shuffle_assignment()` method (line 106) randomizes critic-to-claim assignment via round-robin over a shuffled claim list. This ensures no critic reviews claims they authored (mitigating Actor-Observer Asymmetry bias from the same ACL 2026 finding: perspective-dependent attribution errors when reviewers know the author).

Anonymization is DEFAULT-ON per the design decision at SYNTHESIS.md section 10.6: identity-driven sycophancy is the dominant bias in multi-agent debate, and response anonymization is a one-line structural fix. The `AdversarialVerifier.__init__()` accepts `anonymize: bool = True` (line 325) -- it must be explicitly disabled.

**The DecisionMatrix -- majority consensus with escalation.**

The `DecisionMatrix` (line 233) resolves exactly 3 `CriticVerdict` instances into a single consensus verdict. The logic at `resolve()` (line 252):

```python
votes = [v.verdict for v in verdicts]
accept_count = votes.count(Verdict.ACCEPT)
reject_count = votes.count(Verdict.REJECT)
flag_count = votes.count(Verdict.FLAG)

if accept_count >= 2:
    return Verdict.ACCEPT
if reject_count >= 2:
    return Verdict.REJECT
if flag_count >= 2:
    return Verdict.FLAG
return Verdict.FLAG  # 1-1-1 split -> escalate
```

The 1-1-1 split case (line 287) is the escalation path: when ACCEPT/REJECT/FLAG each get one vote, the verdict becomes FLAG. This means a single strongly-argued REJECT cannot veto a majority, but a split vote cannot be resolved without human review.

The `resolve()` method requires exactly 3 verdicts and raises `ValueError` otherwise. This is enforced by the `verify()` method which checks `len(verdicts) != 3` at line 378.

**Bundled /deep-research workflow analog.**

AVP is also the core of Lyra's `/deep-research` equivalent. When the `AutoOrchestrator` classifies a task as HIGH complexity with research keywords (audit, investigate, research, benchmark), the `EffortBridge.plan_workflow()` creates a three-phase research workflow:

- Phase 1 (Discover): Multiple agents fan out with different research angles (security audit, compliance check, performance analysis).
- Phase 2 (Verify): Each agent's findings are adversarially cross-checked. The AVP runs on each claim. Claims that don't survive are filtered.
- Phase 3 (Report): Surviving claims are synthesized into a structured report.

This is the same pattern as Claude Code's `/deep-research` but generalized: the discovery agents can be running on DeepSeek Flash (cheap, fast), the verifiers on Claude Sonnet (reliable), and the synthesizer on Claude Opus (highest quality). The cross-provider AVP ensures that no single provider's blind spots make it into the final output.

**The A-Trust integration -- from scalar confidence to 6-dimension trust.**

The `TrustWeightedRouter` in `packages/lyra-workflow/src/lyra_workflow/trust.py` extends AVP's scalar `CriticVerdict.confidence` into a 6-dimension `TrustScore` vector. Each dimension maps to a Gricean communication maxim:

- **Quality**: Is the message factually accurate? Derived from AVP critic confidence.
- **Quantity**: Is the message appropriately detailed? Scored via word count heuristics.
- **Relevance**: Does the message address the task? Scored via keyword overlap with context.
- **Manner**: Is the message clear and well-structured? Scored via structural indicators.
- **Sincerity**: Does the message reflect genuine belief? Scored via anti-hedging analysis.
- **Competence**: Does the agent have the capability? Scored via technical precision heuristics.

The geometric mean (`TrustScore.overall`, line 91) ensures a single near-zero dimension drags the overall score down significantly. The `TrustWeightedRouter.route()` method (line 704) evaluates each incoming message, records the score in the sender's `TrustHistory` and `AgentTrustProfile`, and computes a routing weight from:
1. The current message's overall trust score.
2. The agent's historical average trust.
3. A volatility penalty (highly variable trust = less reliable).

The weight is clamped to `[min_weight=0.05, 1.0]`. Messages from low-trust agents are downweighted but never fully silenced (minimum 5% weight). The `route_batch()` method (line 764) sorts messages by weight descending, so high-trust messages are processed first.

The `trust_from_critic_verdicts()` function (line 860) bridges AVP verdicts into A-Trust scores. It maps AVP's `confidence` to Quality, `evidence_tier` to Competence (A=1.0, B=0.8, C=0.6, D=0.3), and consensus consistency to Sincerity (full consensus=0.9, 2-way split=0.6, 3-way split=0.3). Quality, Quantity, and Manner are left at neutral (0.5) because AVP critics do not evaluate these dimensions directly.

## 3. Architecture Diagram

```
                         +---------------------------+
                         |  User Prompt / Command    |
                         |  ("/effort ultracode")    |
                         +------------+--------------+
                                      |
                                      v
                    +-----------------+------------------+
                    |        EffortManager              |
                    |  (lyra-effort/manager.py)         |
                    |  map_effort(ULTRACODE, provider)  |
                    +---+-------------------+----------+
                        |                   |
                  effort level        budget_tokens=16384
                  = ULTRACODE         + orchestration=True
                        |                   |
                        v                   v
              +---------+--+         +------+---------+
              | EffortBridge |       | Provider       |
              | (effort_bridge.py)|  | Adapter        |
              | evaluate()    |       | (anthropic.py) |
              +---+-----------+      | thinking = {   |
                  |                  |  type: enabled, |
                  v                  |  budget_tokens: |
        +---------+----------+       |  16384 }        |
        | AutoOrchestrator   |       +----------------+
        | (orchestrator.py)  |
        | evaluate(prompt)   |       +---------------------------+
        +---+----------------+       | ChatRequest               |
            |                        | effort_budget_tokens=16384|
            v                        | effort_instruction=str   |
    +-------+--------+               | effort_reasoning=str    |
    | Orchestration  |               +---------------------------+
    | Decision       |
    | complexity=    |         +-----+---------------------------+
    |   HIGH         |         | Dynamic Workflow Engine         |
    | should_orch=   |         | (lyra-workflow/engine.py)       |
    |   True         |         | WorkflowScript{                 |
    +-------+--------+         |   phases: [                    |
            |                  |     {name: "Discover",          |
            v                  |      tasks: [agent1, agent2...]},
         EffortBridge          |     {name: "Verify",
         plan_workflow()       |      tasks: [avp_cross_check]},
            |                  |     {name: "Report",
            v                  |      tasks: [synthesize]},
         WorkflowScript        |   ],                            |
            |                  |   providers: {                  |
            v                  |     "explore": "deepseek",      |
    +--------------------------|---+ "verify": "claude-sonnet", |
    | WorkflowEngine          |   | "synthesize": "claude-opus"}|
    | start(script)           |   }                              |
    |    |                    |   +------------------------------+
    |    v                    |                  |
    | +--+---------+---------+|                  |
    | | Phase      | Phase   ||   +-------------+--------+
    | | Discover   | Verify  ||   | AdversarialVerifier  |
    | | (16 agents)| (3      ||   | (avp.py)             |
    | |  parallel) | critics)||   | review(claim)        |
    | +------------+---------+|   |   +--------------+   |
    |                         |   |   | MutationGate |   |
    | AgentTask{              |   |   | classify()   |   |
    |   prompt, model,        |   |   +--------------+   |
    |   result, tokens_used,  |   |   +--------------+   |
    |   cost_usd              |   |   |DecisionMatrix|   |
    | }                       |   |   | resolve()    |   |
    +-------------------------+   |   +--------------+   |
                                  |   +--------------+   |
                                  |   |RogueMonitor  |   |
                                  |   +--------------+   |
                                  +----------------------+
```

## 4. Multi-Provider Portability

### How ultracode works on Anthropic (native effort API).

Anthropic is the first-class provider for ultracode. The `AnthropicProvider` in `packages/lyra-provider/src/lyra_provider/adapters/anthropic.py` maps `request.effort_budget_tokens` directly into the Anthropic Messages API `thinking` parameter:

```python
# line 197 of anthropic.py
if request.effort_budget_tokens:
    body["thinking"] = {
        "type": "enabled",
        "budget_tokens": request.effort_budget_tokens,
    }
```

For ultracode, `budget_tokens` is 16,384 -- the same as xhigh. Anthropic also supports tool calling, JSON mode, vision, streaming, and prompt caching. The `supports_feature()` method (line 376) returns `True` for all of these. The context window is 200,000 tokens (`_CONTEXT_WINDOWS` at line 151).

The Anthropic adapter handles streaming via the `chat_stream()` method (line 244), which normalizes Anthropic SSE events (content_block_start, content_block_delta, content_block_stop, message_delta) into Lyra `StreamEvent` types (text_delta, tool_call_start, tool_call_end, done). The streaming includes extended thinking content, which is delivered through the same content block mechanism.

**The Anthropic adapter in detail -- how ChatRequest flows to the API.**

The `chat()` method (line 168) builds the Anthropic request body from the Lyra `ChatRequest`. The steps are:

1. **System message extraction** (line 179): System messages are separated from conversation messages. They are joined into a single `system` string field in the body, because Anthropic treats system as a top-level field, not a message role.

2. **Message conversion** (line 185): Each Lyra `Message` is converted via `_to_anthropic_message()` (line 41). The function handles four roles:
   - `SYSTEM`: Returns `{"role": "system", "content": msg.content}`.
   - `USER`: Returns `{"role": "user", "content": msg.content}`.
   - `ASSISTANT`: Returns `{"role": "assistant", "content": msg.content}`. If tool_calls are present (line 52), the content is replaced with a list of `tool_use` content blocks.
   - `TOOL`: Returns `{"role": "user", "content": [{"type": "tool_result", ...}]}` with the tool_call_id and is_error flag.

3. **Tool conversion** (line 193): Lyra `ToolSchema` objects are converted via `_to_anthropic_tool()` (line 112), which maps `name`, `description`, and `parameters` (JSON Schema) to Anthropic's `input_schema` format.

4. **Effort injection** (line 197): If `request.effort_budget_tokens` is set, the body gets `"thinking": {"type": "enabled", "budget_tokens": request.effort_budget_tokens}`. For ultracode, this is `budget_tokens: 16384`.

5. **HTTP dispatch** (line 209): The request is sent via `httpx.AsyncClient.post()` or falls back to `aiohttp` via `_chat_via_http()` (line 386). The Anthropic message API version is set to `2023-06-01`.

6. **Response parsing** (line 231): The Anthropic response content blocks are parsed back to Lyra `Message` format via `_from_anthropic_message()` (line 79), which handles both text and tool_use blocks. Usage data is extracted via `_from_anthropic_usage()` (line 121), which maps Anthropic's `input_tokens`, `output_tokens`, `cache_read_input_tokens`, and `cache_creation_input_tokens` to Lyra's `LLMUsage`.

The streaming path (`chat_stream()`, line 244) follows the same body construction but adds `"stream": True` and processes SSE events line-by-line. Key event types: `content_block_start` (tool_use block begins), `content_block_delta` (text content or partial JSON for tool arguments), `content_block_stop` (tool call complete with parsed arguments), `message_delta` (stream done with usage data). The streaming state machine tracks a `current_tool` variable to accumulate partial JSON arguments across multiple deltas.

### How it degrades on DeepSeek (keyword + prompt-based fallback).

DeepSeek has no native `budget_tokens` or `reasoning_effort` API. The `DeepSeekProvider` in `packages/lyra-provider/src/lyra_provider/adapters/deepseek.py` handles effort via the `_build_messages()` method (line 338):

```python
# line 345 of deepseek.py
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
```

The instruction is the thinking prompt from `_THINKING_INSTRUCTIONS["deepseek"]` in the EffortManager. For xhigh/ultracode: "Think deeply. Consider alternatives. Verify your reasoning." These instructions are not guarantees -- they are advisory hints. DeepSeek models may or may not follow them to the same degree as Anthropic's native `budget_tokens` parameter enforces extended thinking.

Auto-trigger on DeepSeek is the same keyword classifier as on Anthropic, but with an appended fallback prompt: "This task may benefit from a workflow. Plan one?" (line 192 of `orchestrator.py`). This is because DeepSeek models are less reliable at self-initiating multi-step workflows from implicit context.

DeepSeek also has limitations: no vision support, no JSON mode, no prompt caching. Its context window is 128K tokens. The `supports_feature()` method (line 330 of `deepseek.py`) returns `True` only for `tool_calling` and `streaming`.

### How it degrades on open-weight models (keyword trigger only).

Open-weight models (self-hosted, Ollama, LM Studio, etc.) have the most degraded ultracode experience. The `ProviderEffortCapability` for open-weights (line 77 of `manager.py`) sets:

```python
ProviderEffortCapability(
    provider="openweights",
    supports_budget_tokens=False,
    supports_reasoning_effort=False,
    supports_prompt_instructions=True,
    max_effort_level=EffortLevel.HIGH,
)
```

Three degradations apply:

1. **Effort clamping**: The `map_effort()` method clamps any effort level above HIGH to HIGH for open-weights. Ultracode becomes xhigh (resolved to xhigh, then clamped to high), losing the xhalf of the budget. The orchestration flag is preserved, but the reasoning budget is capped at 8,192 tokens.

2. **Thinking instructions are short**: The open-weights thinking instructions (line 107 of `manager.py`) are single-word prefixes ("Quick answer:", "Brief analysis:", "Careful analysis:", "Deep analysis:"). This is because open-weight models have smaller context windows (32K tokens) and weaker instruction following. Longer instructions would waste precious context.

3. **Auto-trigger disabled**: The `AutoOrchestrator.evaluate()` method (line 183 of `orchestrator.py`) suppresses auto-trigger for open-weights entirely:

```python
if provider == "openweights":
    if should:
        should = False
        provider_fallback = True
```

Only explicit "workflow" keywords in the user prompt trigger workflows. The assumption is that open-weight models cannot reliably self-initiate multi-step plans.

The `CapabilityMatrix` (line 173 of `packages/lyra-provider/src/lyra_provider/capability.py`) documents: `tool_calling=False`, `json_mode=False`, `vision=False`, `reasoning_budget=False`, `max_context_tokens=32_000`, `concurrent_limit=10`. With no tool calling, workflow agents can only generate text -- they cannot execute tools or invoke functions.

### Provider capability matrix.

The `CapabilityMatrix` in `packages/lyra-provider/src/lyra_provider/capability.py` is the single source of truth for provider feature support. Combined with `_PROVIDER_CAPABILITIES` in the EffortManager:

| Feature              | Anthropic | DeepSeek | OpenAI | Google | OpenRouter | OpenWeight |
|----------------------|-----------|----------|--------|--------|------------|------------|
| tool_calling         | Yes       | Yes      | Yes    | Yes    | Yes        | No         |
| json_mode            | Yes       | No       | Yes    | Yes    | Yes        | No         |
| vision               | Yes       | No       | Yes    | Yes    | Yes        | No         |
| streaming            | Yes       | Yes      | Yes    | Yes    | Yes        | Yes        |
| prompt_caching       | Yes       | No       | No     | No     | No         | No         |
| reasoning_budget     | Yes       | No       | Yes    | No     | Yes        | No         |
| max_effort_level     | MAX       | XHIGH    | XHIGH  | HIGH   | MAX        | HIGH       |
| max_context_tokens   | 200K      | 128K     | 256K   | 1M     | 200K       | 32K        |
| concurrent_limit     | 50        | 60       | 60     | 30     | 200        | 10         |
| Thinking mechanism   | budget_tokens | prompt inst | reasoning_effort | prompt inst | budget_tokens | prompt prefix |

The two capability systems are intentionally separate concerns: `CapabilityMatrix` covers general features (tool calling, vision, streaming), while `_PROVIDER_CAPABILITIES` covers effort-specific features (budget_tokens, reasoning_effort, max_effort_level). The `EffortManager.validate_against_capability_matrix()` method (line 435 of `manager.py`) cross-validates the two systems and reports discrepancies.

## 5. Trade-Off Analysis

| Dimension       | Gain                                                                  | Cost                                                                    | When It Wins                                                       | When It Loses                                              |
|-----------------|-----------------------------------------------------------------------|-------------------------------------------------------------------------|--------------------------------------------------------------------|------------------------------------------------------------|
| Token cost      | Ultracode uses xhigh budget (16,384 tokens) for the active turn, plus orchestration triggers multi-agent parallelism with cheap models (DeepSeek Flash for exploration) | Workflow execution consumes tokens across multiple agents in parallel; 16 concurrent agents at 4K output each = 64K tokens per phase | Large codebase audits: discovery agents running cheap models catch more issues than a single expensive model | Simple single-turn tasks pay the xhigh budget overhead for no benefit; orchestration adds agent token costs |
| Latency         | Background execution keeps session responsive; progress view updates in near-real-time; pause/resume preserves completed work | Parallel agent dispatch has fixed overhead (thread startup, async orchestration); AVP 3-critic panel triple-checks every claim | Multi-phase research reports: Discover phase runs 16 agents in parallel, completing in same wall-clock time as 1 agent | Trivial requests wait through effort-level evaluation (50ms) + orchestration decision + context injection |
| Accuracy        | Cross-model AVP (3 critics from different providers) catches errors homogeneous panels miss; 14.6x better cross-model error detection per ACL 2026 findings | 3-critic panel costs 3x per claim; rogue agent monitor adds trajectory tracking overhead | High-stakes claims: identity-driven sycophancy is structurally eliminated by ReviewAnonymizer; 1-1-1 splits escalate to humans | Turn-by-turn operations with no mutating action pass through MutationGate without verification -- read-only errors may be missed |
| Complexity      | Four primitives are independently useful; EffortBridge is a thin 122-line glue layer between them | Six-provider capability matrix must be maintained and cross-validated; effort calibration adds dynamic budget adjustment logic | Multi-provider deployments: effort scale protects from "works on Anthropic, silent fail on DeepSeek" | Single-provider setups pay the complexity overhead of multi-provider abstractions (provider interface, capability matrix, adapter pattern) |
| Provider portability | Six-item effort scale maps cleanly across providers with different effort APIs (budget_tokens, reasoning_effort, prompt instructions); ultracode = xhigh + boolean means ultracode works everywhere xhigh works | Degraded experience on open-weight models (effort clamped to HIGH, auto-trigger disabled, no tool calling); Google provider is currently a stub per google.py line 54 | Heterogeneous deployments: discover phase on DeepSeek Flash, verify on Claude Sonnet, synthesize on Claude Opus -- cost-optimized across providers | Anthropic-only shops: provider adapter abstraction adds unnecessary indirection; native budget_tokens API would be simpler |
| Steering & control | SteeringEngine supports mid-run corrections (focus, ignore, model switch, budget change, verify strictness); undo via git rollback; double-tap Ctrl+C barge-in | Steering adds user-facing command surface that must be documented and learned; undo requires git availability | Long-running autonomous workflows: user can redirect focus mid-run without restarting | Interactive single-turn tasks: steering commands are irrelevant overhead |
| Trust calibration | Correction-based autonomy levels (supervised -> collaborative -> autonomous); 6-dimension A-Trust scoring via Gricean maxims | Trust trajectories must be persisted across sessions; LLM-powered trust evaluation adds cost | Multi-agent fleets: low-trust agents are downweighted before their messages reach decision points | Single-agent sessions: trust routing is unnecessary overhead |
| Pause/resume    | Full state serialization preserves completed work across pauses; resume from snapshot avoids re-running expensive agent tasks | Serialization captures all AgentTask states including results, token usage, and error data -- snapshot can be large for long workflows | Interrupted sessions: user pauses at any point, resumes later with zero work lost | Workflows that complete in <1 second: pause/resume infrastructure is pure overhead |

## 6. (B) Breakthrough: What Lyra Does Beyond Claude Code

**Multi-provider effort mapping.**

Claude Code's `/effort` menu sends Anthropic-specific `budget_tokens` to the Messages API. It has no concept of other providers. Lyra's `EffortManager` abstracts the effort scale into three translation strategies:

1. **Native budget API** (Anthropic, OpenRouter): Pass `budget_tokens` as a direct API parameter. This is the same mechanism as Claude Code, but generalized to any provider that supports extended thinking budgets.

2. **Reasoning effort API** (OpenAI): Map the six-level scale onto OpenAI's three-level `reasoning_effort` parameter (`low`, `medium`, `high`). The EffortManager compresses: low/medium -> low, high -> medium, xhigh/max/ultracode -> high.

3. **Prompt-based fallback** (DeepSeek, Google, open-weights): Inject thinking instructions into the system prompt. The instructions are tiered by capability: DeepSeek gets prose instructions (~20 words), open-weights gets single-word prefixes (~5 characters).

The `EffortMapping` dataclass (line 66 of `models.py`) carries ALL three representations simultaneously (`budget_tokens`, `thinking_instruction`, `reasoning_effort`), so the provider adapter can choose which one to use at request time.

**Dynamic Effort Calibration (Breakthrough section 3.2).**

The `EffortManager` supports runtime calibration via `record_calibration()` (line 286 of `manager.py`). After each task, the calibration data (accuracy, tokens used, latency) is recorded per (provider, effort_level). The `_apply_calibration()` method (line 481) adjusts the token budget based on whether accuracy targets are met:

- If accuracy >= target: keep default budget (meeting requirements).
- If accuracy < target: increase budget proportionally by `shortfall * 2.0`, capped at 2x.

Target accuracies (line 508): LOW=0.70, MEDIUM=0.80, HIGH=0.88, XHIGH=0.93, MAX=0.96, ULTRACODE=0.93 (same as xhigh). Over time, Lyra learns the minimum tokens each (provider, model, effort_level) combination needs to achieve target accuracy -- potentially reducing costs below the static budget.

This is the breakthrough: Claude Code uses static budgets; Lyra dynamically adjusts budgets based on empirical accuracy measurements. If DeepSeek achieves target accuracy at 6,000 tokens for HIGH effort (instead of the default 8,192), Lyra will reduce the budget automatically.

**Provider-aware orchestration degradation.**

Claude Code's auto-orchestration assumes Anthropic capabilities. Lyra's `AutoOrchestrator` adjusts orchestration behavior per provider (section 4 of the orchestrator):

- Anthropic and OpenAI: Full auto-trigger, no fallback text.
- DeepSeek: Auto-trigger + explicit fallback prompt appended to the reasoning.
- Open-weight: Auto-trigger disabled entirely. Only explicit "workflow" keyword triggers.

This is the breakthrough: the same user prompt can result in different orchestration behavior depending on which provider is serving the session, without the user needing to know. The degradation is automatic and documented in the `OrchestrationDecision` provider_fallback flag.

**Open-weight model fallback with graceful degradation.**

When an open-weight model is the active provider, ultracode degrades in three ways:

1. **Effort clamping**: MAX and XHIGH request effort levels are silently clamped to HIGH (8,192 budget tokens). The user's `/effort max` command succeeds without error, but the actual budget is 8,192 not 32,000.

2. **No auto-orchestration**: The orchestrator sets `should_orchestrate=False` for all auto-triggered tasks. Only explicit "workflow" keywords initiate workflows. Users who want orchestration must add "workflow" to their prompt.

3. **No tool calling per adapter**: The `CapabilityMatrix` declares open-weights have `tool_calling=False`. This means workflow agents running on open-weight models can only generate text.

The `OrchestrationDecision` object carries `provider_fallback: bool` (True when any degradation was applied) so the CLI can communicate the degradation to the user.

**Steering engine with mid-run corrections and undo.**

Beyond Claude Code's pause/cancel, Lyra's `SteeringEngine` in `packages/lyra-cli/src/lyra_cli/steering.py` supports:

- `/steer focus on <topic>`: Redirect remaining workflow phases to prioritize a specific area.
- `/steer ignore <topic>`: Skip a specific area in remaining phases.
- `/steer use <model>`: Switch the active model for remaining tasks (e.g., "deepseek-flash" to "claude-sonnet").
- `/steer budget <amount>`: Change the cost budget for remaining tasks.
- `/steer verify more/less`: Adjust AVP verification strictness (0.0 to 1.0).
- `/undo` and `/undo <N>`: Rollback mutating actions via git checkout (captures `git rev-parse HEAD` before each action).
- **Double-tap Ctrl+C barge-in**: First tap pauses (with steering prompt), second tap within 1-second window stops entirely.

The `AutonomyLevel` enum (line 47 of `steering.py`) provides trust calibration: `correction_rate > 0.3` -> SUPERVISED (ask before every action), `correction_rate > 0.1` -> COLLABORATIVE, otherwise AUTONOMOUS. This means the system becomes less autonomous as the user corrects it more -- a self-regulating trust loop.

**Cross-model adversarial verification with A-Trust extension.**

Claude Code has no built-in adversarial cross-check. Lyra's AVP provides:

- **MutationGate**: Only mutating actions trigger the 3-critic panel. Non-mutating actions pass through. This optimization means reads are fast and writes are verified.
- **ReviewAnonymizer**: Strip identity markers from claims before review to prevent identity-driven sycophancy (ACL 2026 finding: identity-driven sycophancy is the dominant bias in multi-agent debate).
- **RogueAgentMonitor**: Track per-agent confidence trajectories to detect confused agents before they sink the task.
- **A-Trust extension** (in `packages/lyra-workflow/src/lyra_workflow/trust.py`): 6-dimension Gricean trust scoring extends the AVP's scalar confidence into a vector. The `TrustWeightedRouter` routes inter-agent messages with trust weighting -- low-trust agent messages are downweighted before they reach decision points.

**Workflow engine with pause/resume/serialization.**

Claude Code runs workflows in the session context window, meaning intermediate results consume context. Lyra's `WorkflowEngine` runs workflows in background threads with results stored as `AgentTask` data objects, not in the conversation. The `PauseResumeSerializer` converts the entire workflow state (all completed agent results, phase metadata, cumulative tokens and cost) to a JSON snapshot. On resume, the engine deserializes and continues from the current phase -- no work is lost.

**Effort persistence with session-only levels.**

Claude Code persists the effort level across sessions. Lyra's `EffortManager.save()` (line 351 of `manager.py`) applies the `is_persistent` rule: low through xhigh are saved, max and ultracode are written as "high" on disk with orchestration disabled. On load, the restored level is always one of the persistent four. Users must explicitly re-enable ultracode each session. This prevents accidental cost overruns from a forgotten ultracode session.

**Capability cross-validation.**

The `EffortManager.validate_against_capability_matrix()` method (line 435 of `manager.py`) cross-checks the effort capability registry (`_PROVIDER_CAPABILITIES`) against the general capability matrix (`CapabilityMatrix`). If a provider claims `supports_budget_tokens=True` in the effort caps but `reasoning_budget=False` in the general matrix, a discrepancy is reported. This automated cross-validation prevents the two capability systems from drifting out of sync -- a real risk in a system with six+ providers and two independently-maintained capability registries.

**Orchestration coordinator and agent-coalition integration.**

Beyond the standalone WorkflowEngine, Lyra also provides an `AgentCoordinator` in `packages/lyra-orchestration/src/lyra_orchestration/coordinator.py`. This coordinator manages agent tasks with dependency graphs via the event bus (`EventBus` in `packages/lyra-orchestration/src/lyra_orchestration/event_bus.py`). Tasks can declare dependencies on other tasks (line 74: `dependencies: list[str]`), and the coordinator only dispatches tasks whose dependencies are met.

The coordinator's `execute()` method (line 99) uses an event-driven loop: it finds ready tasks (those with all dependencies completed), runs them in parallel via `asyncio.gather()`, then finds newly-ready tasks and repeats. Results are collected per-agent with status, result, and error fields.

This coordinator is used by the `CoalitionCoordinator` in `packages/lyra-orchestration/src/lyra_orchestration/coalition_coordinator.py`, which manages squads of agents (different types: planner, executor, reviewer, researcher) working together on a shared goal. The coalition pattern extends the ultracode workflow: instead of a linear Discover -> Verify -> Report pipeline, coalitions can have agents of different types running simultaneously with dependencies between them.

**Steering engine integration with the WorkflowEngine.**

The `SteeringEngine` in `packages/lyra-cli/src/lyra_cli/steering.py` integrates with the WorkflowEngine through a `_active_workflow_id` field (line 96). When a steering command is issued:

1. `/steer focus on <topic>`: Adds the topic to the `_preferences` list and marks it as a correction. The WorkflowEngine is expected to check `preferences` between phases and adjust agent prompts for remaining tasks.

2. `/steer ignore <topic>`: Similar to focus but with a negative constraint. The WorkflowEngine should skip tasks related to the ignored topic.

3. `/steer use <model>`: Changes `self._model` (line 98). The WorkflowEngine reads this field when dispatching new tasks to select which model to use.

4. `/steer budget <amount>`: Changes `self._budget` (line 97). The WorkflowEngine checks `budget_remaining = budget - cumulative_cost` before dispatching each new phase. If the budget is exhausted, the remaining phases are cancelled.

5. `/steer verify more/less`: Adjusts `self._verify_strictness` (line 99) in 0.25 increments. The AdversarialVerifier uses this to adjust the confidence threshold for accepting claims (stricter = higher confidence required).

6. `/undo <N>`: Pops N entries from the undo stack and runs `git checkout <git_ref> -- .` for each entry. The undo stack records `git rev-parse HEAD` before each mutating action via `record_action()` (line 169). This requires git to be available in the execution environment.

The `InterruptHandler` (line 327) implements double-tap barge-in semantics. First Ctrl+C within the double_tap_window (1 second, line 339) pauses the workflow and shows a steering prompt. Second Ctrl+C within the window stops entirely. The resume command restarts execution.

**Trust calibration: how correction rate adjusts autonomy.**

The `calibrate_trust()` method (line 231) computes `correction_rate = corrections / total_decisions`. Three levels:

- `correction_rate > 0.3` -> SUPERVISED: The system asks the user before every mutating action. This is equivalent to the approval-gate pattern but self-imposed based on correction history.
- `correction_rate > 0.1` -> COLLABORATIVE: The system proactively prompts on high-stakes decisions but does not block low-risk actions.
- otherwise -> AUTONOMOUS: Full auto-execution with AVP gating. This is the default state for a new session.

The `should_ask_before_action()` method (line 250) returns `True` only for the SUPERVISED level. The calibration must be persisted across sessions to be effective -- currently it is reset on session start.

**Effort integration with the lyra-router.**

The router in `packages/lyra-router/src/lyra_router/router.py` and `models.py` integrates with the effort system. The `EffortBridge` is constructed at the agent-loop boundary and the router's model selection considers the effort level when choosing which model to route a task to. The effort integration tests (`packages/lyra-router/tests/test_effort_integration.py`) verify that routing decisions respect effort-based model recommendations.

The router's capability matching (L3 in the architecture) uses both `CapabilityMatrix` for general features and `_PROVIDER_CAPABILITIES` for effort-specific features. When deciding whether to route to OpenAI vs Anthropic for an ultracode session, the router considers:
1. Does the provider support the required effort level? (OpenAI supports up to XHIGH, Anthropic supports up to MAX)
2. Does the provider support the required features? (vision, tool calling, etc.)
3. What is the cost trade-off? (Anthropic prompt caching vs OpenAI reasoning_effort)

**Dynamic Effort Calibration -- the full algorithm.**

The `_apply_calibration()` method (line 481 of `manager.py`) adjusts the token budget based on empirical accuracy measurements. The algorithm:

```python
def _apply_calibration(self, provider, level, default_budget):
    provider_data = self._calibration_data.get(provider, {})
    if level not in provider_data:
        return default_budget          # No data yet -> use default
    
    cal = provider_data[level]
    target = self._target_accuracy(level)  # LOW=0.7, MEDIUM=0.8, ..., ULTRACODE=0.93
    
    if cal["accuracy"] >= target:
        return default_budget          # Meeting target -> keep budget
    
    # Below target: scale budget up
    shortfall = target - cal["accuracy"]
    adjustment = 1.0 + shortfall * 2.0
    return int(default_budget * min(adjustment, 2.0))  # Cap at 2x
```

There are two notable behaviors:

1. **No budget reduction below default**: The calibration only increases budgets, never decreases them. This is conservative: if a provider is hitting the target accuracy, Lyra keeps the default budget. A future enhancement could reduce budgets for over-performing configurations.

2. **2x cap**: The budget is capped at double the default. This prevents runaway costs from a single bad calibration point. If accuracy data is unreliable (small sample size), the 2x cap limits the damage.

3. **Per-(provider, level) granularity**: Calibration data is stored separately for each provider and level. Calibration for (anthropic, HIGH) does not affect (anthropic, XHIGH) or (deepseek, HIGH). This is correct because different providers and different effort levels have different accuracy profiles.

**Effort persistence -- the is_persistent rule and session safety.**

The `save()` method (line 351) implements the persistence safety rule:

```python
if level.is_persistent:
    save_level = level
    save_enabled = self._config.orchestration.enabled
else:
    save_level = EffortLevel.HIGH
    save_enabled = False
```

Non-persistent levels (MAX and ULTRACODE) are written as HIGH on disk with orchestration disabled. The `load()` method (line 385) handles the reverse: if the persisted level is MAX or ULTRACODE (from an older session that saved before this safety rule), it is restored as HIGH via the `is_persistent` check at line 418.

The persistence uses `.lyra/config.json` in the project root. The `_config_path()` method (line 338) walks up from cwd to find the `.lyra` directory. If none exists, it creates one in the current directory.

This safety design means:
- A user who sets `/effort ultracode` and closes the terminal starts the next session at HIGH.
- A user who sets `/effort max` and closes the terminal starts the next session at HIGH.
- Only low, medium, high, and xhigh persist across sessions.
- Orchestration state only persists for persistent levels (though in practice, orchestration is only enabled for ultracode, which is not persistent).

**Provider-specific adapter patterns -- how each adapter handles ChatRequest differently.**

The four provider adapters (anthropic, deepseek, openai, google) each handle the canonical `ChatRequest` differently:

1. **AnthropicProvider** (line 136 of `anthropic.py`): Uses `request.effort_budget_tokens` to set `thinking.budget_tokens`. Also uses `request.max_tokens` for the `max_tokens` field. Handles system messages as a top-level field, not a message role. Tools use the native Anthropic `tool_use` content block format with `input_schema` for parameters.

2. **DeepSeekProvider** (line 129 of `deepseek.py`): Uses `request.effort_instruction` to inject thinking instructions into the system prompt via `_build_messages()`. Uses an OpenAI-compatible API format (shared message conversion functions with OpenAIProvider). Tools use the OpenAI-compatible `type: "function"` format with `JSON.stringify()` for arguments. No extended thinking API available.

3. **OpenAIProvider** (line 38 of `openai.py`): Uses `request.effort_reasoning` to set `reasoning_effort` in the request body. Reuses DeepSeek's message conversion functions (`_to_openai_message`, `_from_openai_message`, `_to_openai_tool`) via import at line 28. Unlike DeepSeek, `_build_messages()` (line 241) does NOT inject thinking instructions -- OpenAI uses the native `reasoning_effort` parameter instead.

4. **GoogleProvider** (line 26 of `google.py`): Currently a stub. The `chat()` method (line 53) raises `ProviderError` with message "GoogleProvider is not yet implemented." The `chat_stream()` method (line 61) yields an error event. Both effort_instruction and effort_budget_tokens are ignored.

The message conversion patterns also differ between Anthropic and OpenAI-compatible formats:
- Anthropic uses `content` as a list of content blocks (each with a `type`: text, tool_use, tool_result).
- OpenAI-compatible format uses `content` as a string, with `tool_calls` as a separate field.
- DeepSeek and OpenAI reuse the same conversion functions because they share the same API format.
- Google's format is different again (SafetySettings, GenerationConfig, contents array) and not yet implemented.

## 7. Key Sources

### Lyra source files (all paths relative to `packages/`):

- **Effort scale enum and models**: `lyra-effort/src/lyra_effort/models.py` -- Defines `EffortLevel` with six values, `EffortMapping` for per-provider translation, `OrchestrationConfig`, and `ProviderEffortCapability`.
- **Effort manager with per-provider mapping**: `lyra-effort/src/lyra_effort/manager.py` -- `EffortManager` with `map_effort()`, capability clamping, calibration recording, and session persistence.
- **Provider interface**: `lyra-provider/src/lyra_provider/interface.py` -- Canonical `AbstractProvider` protocol, `ChatRequest` with effort fields (`effort_budget_tokens`, `effort_instruction`, `effort_reasoning`).
- **Provider capability matrix**: `lyra-provider/src/lyra_provider/capability.py` -- `CapabilityMatrix` with feature support declarations for 6 providers.
- **Anthropic adapter**: `lyra-provider/src/lyra_provider/adapters/anthropic.py` -- Maps `effort_budget_tokens` to Anthropic `thinking.budget_tokens`.
- **DeepSeek adapter**: `lyra-provider/src/lyra_provider/adapters/deepseek.py` -- Injects `effort_instruction` as system prompt prefix via `_build_messages()`.
- **OpenAI adapter**: `lyra-provider/src/lyra_provider/adapters/openai.py` -- Maps `effort_reasoning` to OpenAI `reasoning_effort` parameter.
- **Google adapter**: `lyra-provider/src/lyra_provider/adapters/google.py` -- Stub (not yet implemented per line 54).
- **Auto-orchestrator**: `lyra-workflow/src/lyra_workflow/orchestrator.py` -- `AutoOrchestrator` with keyword-based complexity estimation and provider-aware degradation.
- **Workflow engine**: `lyra-workflow/src/lyra_workflow/engine.py` -- `WorkflowEngine` with background thread execution, 16 concurrent agent cap, 1000 total agent cap, pause/resume serialization, and progress tracking.
- **Adversarial verification**: `lyra-workflow/src/lyra_workflow/avp.py` -- `AdversarialVerifier` with MutationGate, ReviewAnonymizer, DecisionMatrix (3-critic consensus), and RogueAgentMonitor.
- **A-Trust extension**: `lyra-workflow/src/lyra_workflow/trust.py` -- `TrustWeightedRouter` with 6-dimension Gricean trust scoring and `trust_from_critic_verdicts()` bridge.
- **Effort bridge**: `lyra-core/src/lyra_core/orchestration/effort_bridge.py` -- `EffortBridge` that wires effort level -> orchestration trigger -> workflow plan.
- **Steering engine**: `lyra-cli/src/lyra_cli/steering.py` -- `SteeringEngine` with mid-run corrections (focus, ignore, model switch, budget, verify), git-based undo, and interrupt handler with double-tap barge-in.
- **Effort tests**: `lyra-effort/tests/test_effort.py` -- Invariant tests for ultracode = xhigh + orchestration, per-provider mapping, capability clamping.
- **Effort bridge tests**: `lyra-core/tests/test_effort_bridge.py` -- Integration tests for EffortBridge with ultracode, multi-phase workflow planning.
- **Workflow tests**: `lyra-workflow/tests/test_workflow.py` -- Tests for ScriptVM, WorkflowEngine, MutationGate, DecisionMatrix, AdversarialVerifier, AutoOrchestrator.
- **Architecture reference**: `ARCHITECTURE.md` (project root) -- System topology, data flow diagrams, component relationships.
- **Phase 9 Breakthrough Architecture**: `docs/research/PHASE-9-BREAKTHROUGH-ARCHITECTURE-SYNTHESIS.md` -- Architectural vision: model router, context optimizer, safety monitor, multi-agent execution layer.
- **Implementation roadmap**: `docs/research/IMPLEMENTATION-ROADMAP.md` -- Week-by-week task breakdown across 20 weeks.

### Papers and external sources:

- **Identity-Skews-Debate** (Choi/Zhu/Li, ACL 2026 Main): Multi-agent debate suffers identity-driven sycophancy -- mitigated by ReviewAnonymizer in `avp.py` line 48.
- **Actor-Observer Asymmetry** (Li et al., ACL 2026 Main): Perspective-dependent attribution errors -- mitigated by randomized critic-to-claim assignment in `avp.py` line 106.
- **Preventing Rogue Agents** (Barbi et al., ACL 2025 Spotlight): Confused agents can sink multi-agent tasks -- mitigated by RogueAgentMonitor in `avp.py` line 474.
- **A-Trust: Attention-based Trust Management** (ACL 2026 Main): Six Gricean trust dimensions for inter-agent message routing -- implemented in `trust.py`.
- **Claude Code dynamic workflows documentation**: Primitive 3 replication -- code-driven background orchestration with intermediate results in script variables per `engine.py`.
- **Anthropic Messages API extended thinking**: `thinking.budget_tokens` parameter -- mapped in `anthropic.py` line 197.
- **OpenAI reasoning_effort API**: Three-level reasoning effort parameter -- mapped in `openai.py` line 82.
