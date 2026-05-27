# Lyra Process Transparency Plan

**Goal**: Every background process, agent call, LLM request, tool invocation, cron routine,
subagent worker, and async task that Lyra spawns is visible to the user in real time.
Nothing is hidden.

**Research grounding**:
- *The Landscape of Open-Source Tools Comparable to abtop (May 2026)* — 13 tools surveyed,
  4 visibility approaches, 8 design patterns distilled
- Lyra codebase audit: existing `LifecycleBus`, `HIREmitter`, `CronDaemon`, `AgentLoop` hooks,
  `CacheTelemetry`, and OTel/OTLP bridge are partially built but not wired to any live UI
- Prior art: LangChain CallbackManager, CrewAI Task status enum, Claude Code's 12 hook types,
  OpenAI Responses API SSE event model, k9s (Kubernetes TUI) for process-table UX

**Implementation constraints**:
- Rule-based / no LLM calls inside any new module
- Stdlib + already-present project deps only (Rich, typer, prompt_toolkit already in)
- Each phase: new module(s) + tests → commit → push
- Phases 1–3 are prerequisites for everything else; later phases can parallelise

---

## Current State Inventory

### What exists (but is invisible to the user)
| Component | File | What it does |
|-----------|------|--------------|
| `LifecycleBus` | `lyra_core/hooks/lifecycle.py` | 15+ typed lifecycle events (TURN_START, TOOL_CALL, SESSION_END …) |
| `HIREmitter` | `lyra_core/observability/hir.py` | Structured JSONL traces → `.lyra/<session>/events.jsonl` |
| `CronDaemon` | `lyra_core/cron/daemon.py` | Threading tick loop, sleep-until-next-fire |
| `RoutineDaemon` | `lyra_core/cron/routine_daemon.py` | Per-routine exception isolation |
| `AgentLoop` hooks | `lyra_core/agent/loop.py` | `pre_llm_call`, `pre_tool_call`, `post_tool_call` |
| `EternalLoop` | `daemon_cmd.py` | Budget envelope + health endpoint on :9102 |
| `CacheTelemetry` | `lyra_core/context/cache_telemetry.py` | Per-turn cache hit ratio, cost multiplier |
| `OTel bridge` | `lyra_core/observability/otel_export.py` | Optional OTLP export to Jaeger/Honeycomb/Datadog |
| `TUI transport` | `lyra_cli/tui_v2/transport.py` | ThreadPoolExecutor + asyncio.Queue bridge to harness-tui |

### What is missing (the gap)
- No machine-readable `.lyra/process_state.json` written on state transitions
- No unified EventBus that all layers publish to and the UI subscribes from
- No live Rich/Textual display of: daemon health, cron queue, subagent DAG, tool call stream
- No lifecycle enum for subagent process states (pending → running → done/failed)
- No `lyra ps`, `lyra events`, `lyra trace` CLI commands
- No permission mode badge or contract state gauge in any UI surface

---

## Phase Summary

| Phase | Module(s) | Core deliverable | Research grounding |
|-------|-----------|------------------|--------------------|
| 1 | `observability/event_bus.py` | Unified typed EventBus + asyncio.Queue + process_state.json | LangChain CallbackManager, Claude Code 12 hooks, OpenAI SSE |
| 2 | `commands/ps.py` | `lyra ps` / `lyra events` postmortem CLI | ccusage, claudelytics, agent_farm JSON state |
| 3 | `observability/live_display.py` | `lyra status --live` Rich Live() transparency panel | Claude-Code-Usage-Monitor, Rich Live + Layout |
| 4 | `observability/process_tree.py` | Subagent process tree with lifecycle states | k9s, ittybitty, Claude-Code-Agent-Monitor |
| 5 | `commands/trace.py` | `lyra trace` span waterfall + `lyra cost` | agenttrace, Langfuse, claudelytics |
| 6 | status_bar + session + tui_v2 | EventBus → status bar, tool cards, permission badge | VibeMux, Claude-Code-Agent-Monitor, AutoGPT |
| 7 | `observability/telemetry_bridge.py` | `LYRA_ENABLE_TELEMETRY=1` OTel/Phoenix bridge | Arize Phoenix, OpenLLMetry, Langfuse |
| 8 | context_gauge + skill_panel + dag_display | Context saturation, skill activation, DAG graph | Original design — no prior art in surveyed tools |

---

## Phase 1 — Unified EventBus + Process State File
**New module**: `packages/lyra-core/src/lyra_core/observability/event_bus.py`

### What to build

**Typed event dataclasses** (the atoms of the transparency layer):
```
LLMCallStarted(session_id, model, prompt_tokens, turn)
LLMTokenChunk(session_id, delta_text, cumulative_tokens, turn)
LLMCallFinished(session_id, input_tokens, output_tokens, cache_read_tokens, duration_ms)
ToolCallStarted(session_id, tool_name, args_preview, span_id)
ToolCallFinished(session_id, tool_name, duration_ms, is_error, span_id)
ToolCallBlocked(session_id, tool_name, reason, hook_name)
SubagentSpawned(session_id, agent_id, agent_role, worktree, parent_agent_id)
SubagentFinished(session_id, agent_id, status, duration_ms, cost_usd)
StopHookFired(session_id, reason, extensions_used)
PermissionDecision(session_id, tool_name, decision, mode, hook_name)
CostThreshold(session_id, cost_usd, budget_usd, pct_consumed)
CronJobFired(job_name, next_fire_at, last_duration_ms)
DaemonIteration(iteration, budget_remaining_usd, wall_clock_elapsed_s)
```

**EventBus** — single in-process pub/sub:
- `emit(event)` — synchronous, best-effort, never blocks the agent loop
- `subscribe(queue: asyncio.Queue)` / `unsubscribe(queue)` — for live display consumers
- `listeners: list[Callable]` — sync listeners (for JSONL writer, ProcessStateWriter)
- Thread-safe: `threading.Lock` for subscriber list; `asyncio.Queue.put_nowait` (non-blocking)
- Global singleton: `get_event_bus() -> EventBus`

**ProcessStateWriter** — atomic JSON state file:
- Listens on EventBus as a sync listener (no async needed)
- Writes `.lyra/process_state.json` on every state-bearing event
- Atomic write: `tempfile.NamedTemporaryFile → os.replace` (POSIX atomic)
- Schema: `{session_id, started_at, status, agent_role, permission_mode, model_slot,
  current_step, max_steps, cost_usd_so_far, token_in, token_out, cache_hit_tokens,
  last_tool, contract, worktree}`

**Wire-up points** (minimal agent loop integration):
- `AgentLoop._execute_call()` → emit `ToolCallStarted/Finished/Blocked`
- `AgentLoop.run()` → emit `LLMCallStarted/Finished`
- `EternalLoop` → emit `DaemonIteration` on each tick
- `CronDaemon` → emit `CronJobFired` on each routine dispatch
- `SubagentOrchestrator` → emit `SubagentSpawned/Finished`

Research: LangChain `CallbackManager` callback taxonomy (10 callback types, `run_id`+`parent_run_id`
correlation), Claude Code's 12 hook types, OpenAI Responses API SSE typed event model,
`claude-code-hooks-multi-agent-observability` (disler) `send_event.py` pattern.

---

## Phase 2 — CLI Postmortem Tools
**New module**: `packages/lyra-cli/src/lyra_cli/commands/ps.py`

### What to build

**`lyra ps`** — current process table (no live connection required):
- Reads `.lyra/process_state.json`; falls back to scanning `.lyra/state/` dirs if absent
- Rich `Table`: `{session_id, status, agent_role, permission_mode, step/max, cost_usd,
  duration, last_tool}`
- `--json` flag for machine-readable output
- Color: running=green, failed=red, verifying=yellow, done=dim

**`lyra events [--session ID] [--tail N] [--type TYPE] [--since TIMESTAMP]`**:
- Reads `.lyra/<session>/events.jsonl` (existing HIREmitter output)
- Filters by type, session, time window
- Rich `Table`: `{timestamp, event_type, session_id, detail}`
- `--follow` flag: `tail -f` style live streaming (polls file every 0.5s via Rich `Live()`)

Research: ccusage (~9.7k stars), claudelytics 9-tab taxonomy, `claude_code_agent_farm`
`.claude_agent_farm_state.json` pattern, agenttrace log record schema.

---

## Phase 3 — Rich Live Transparency Panel
**New module**: `packages/lyra-core/src/lyra_core/observability/live_display.py`

### What to build

**LiveDisplay** — Rich `Live()` + `Layout` panel (separate from the Textual TUI):
```
Layout("root"):
  Layout("header")  — session ID, model, mode, elapsed time, health score
  Layout("body"):
    Layout("agents") — process table: all active subagents / daemon / routines
    Layout("events") — last 10 tool calls with status and duration
    Layout("stats")  — token burn rate gauge, cache hit ratio, cost/budget bar
  Layout("footer")  — keybinding hint (q=quit, r=refresh, d=detail)
```

**AgentProcessTable** — Rich `Table` updated from EventBus asyncio.Queue:
- One row per spawned agent; adds on `SubagentSpawned`, updates on `LLMCallFinished`

**TokenBurnGauge** — Rich `Progress` with calculated burn rate:
- `burn_rate = tokens_used / elapsed_seconds`
- `projected_exhaustion = (budget_tokens - tokens_used) / burn_rate`
- Color thresholds: green < 50%, yellow < 80%, orange < 95%, red ≥ 95%
- Secondary bar: 5-hour Anthropic rate-limit window

**CompositeHealthScore**:
```python
health = (
  0.35 * (1 - tool_error_rate_last_10)
  + 0.25 * (1 - token_budget_pct)    # inverted: lower usage = healthier
  + 0.25 * cache_hit_rate
  + 0.15 * (1 - pre_hook_block_rate)
)
```
Drives header color: green → yellow → orange → red.

**`lyra status [--live] [--session SESSION_ID]`**:
- Without `--live`: static snapshot from `process_state.json`
- With `--live`: subscribes an `asyncio.Queue` to EventBus, runs `Live()` update loop at 4 Hz

Research: Claude-Code-Usage-Monitor (6.1k stars, Python + Rich `Live()` pattern), Rich `Progress`
+ `Group` for multi-agent bars, Claude-Code-Agent-Monitor composite health score formula.

---

## Phase 4 — Subagent Process Tree with Lifecycle States
**New module**: `packages/lyra-core/src/lyra_core/observability/process_tree.py`

### What to build

**AgentLifecycleState enum**:
```python
PENDING   = "pending"    # spawned, not yet running
SPAWNING  = "spawning"   # worktree being created
RUNNING   = "running"    # agent loop active
VERIFYING = "verifying"  # in post-run verification step
DONE      = "done"       # finished successfully
FAILED    = "failed"     # terminated with error
KILLED    = "killed"     # user-interrupted or budget-exceeded
PARKED    = "parked"     # waiting on DAG dependency
```

**AgentNode dataclass**:
- `agent_id`, `parent_agent_id`, `agent_role`, `worktree`, `state`
- `span_id`, `current_step`, `max_steps`
- `cost_usd`, `token_in`, `token_out`, `started_at`, `finished_at`
- `children: list[AgentNode]`

**ProcessTree** — tree data structure + Rich render:
- `add_node(spawned_event)` — inserts child under parent via `parent_agent_id` linkage
- `update_node(event)` — transitions state on `ToolCallFinished` / `SubagentFinished`
- `render() → Rich.Tree` — recursive Rich `Tree` with colored state badges
- Node format: `[STATUS] role · step/max · cost · worktree · last_tool`

**Span attribute extension**:
- Add `agent_role` and `worktree_id` to spans emitted by `SubagentOrchestrator`
- Enables postmortem tree reconstruction from JSONL (no live data needed)

**`lyra tree [--session SESSION_ID] [--live]`** Typer command.

Research: k9s (pod-table → log → describe UX), ittybitty `ib tree` minimal design,
Claude-Code-Agent-Monitor `tool_use_id` dedup tree, CrewAI `Task.status` enum,
Octogent per-tentacle context file visibility.

---

## Phase 5 — Span Waterfall + Cost Breakdown
**New module**: `packages/lyra-cli/src/lyra_cli/commands/trace.py`

### What to build

**`lyra trace SESSION_ID [--limit N] [--format json]`**:
- Reads `.lyra/<session>/events.jsonl`; groups spans by `span_id + parent_id`
- Rich `Table` waterfall: `{depth_indent + span_name, duration_ms, tokens, status}`
- ASCII timing bars inline: `[████████░░] 420ms`

**`lyra cost [--session SESSION_ID] [--period today|week|month] [--breakdown]`**:
- Reads cost ledger or reconstructs from JSONL events
- Per-section breakdown (maps Phase 7 `SessionCostTracker` sections)
- Per-model breakdown (DeepSeek / Anthropic / OpenAI slots)
- Projected monthly cost at current burn rate
- `--breakdown`: per-tool-call cost (tokens × rate)

Research: agenttrace latency + anomaly score columns, Langfuse per-trace cost display,
claudelytics 5-hour block window, agent-deck budget threshold overlay.

---

## Phase 6 — TUI Integration: Status Bar, Tool Cards, Permission Badge
**Target files**: `lyra_cli/interactive/status_bar.py`, `lyra_cli/tui_v2/transport.py`,
`lyra_cli/interactive/session.py`

### What to build

**Permission mode badge** in status bar:
- Colored chip: `[PLAN]` blue, `[AGENT]` green, `[BYPASS]` red, `[RED]` dark-red + ⚠
- Updates on `PermissionDecision` events from EventBus
- Priority-drops when terminal < 80 cols

**Live tool call display** in session output:
- `ToolCallStarted` → append pending card: `⚙ bash  [running…]  ← args preview 80 chars`
- `ToolCallFinished` → update to done: `✓ bash  [1.2s]` or `✗ bash  [0.3s] exit 1`
- `ToolCallBlocked` → red blocked card: `⊘ write_file  [BLOCKED by destructive_pattern]`
- Streaming args: `LLMTokenChunk` events update args preview live as LLM generates them

**TUI transport wiring** (harness-tui v3.14 integration):
- Wire EventBus asyncio.Queue into `LyraTransport.receive()` loop
- Emit `ToolStarted/ToolFinished` from EventBus events (replaces the current mock)
- Emit `ContextBudget` from `LLMCallFinished.cache_hit_tokens`
- Subagent tree as a sidebar tab (subscribes to EventBus for live node updates)

**Daemon health indicator** in status bar:
- Background poll of EternalLoop health endpoint `:9102` every 10 s
- Shows: `⊙ daemon: iter=42 · budget=87% · 4h12m`
- Color: green if healthy, yellow if budget > 80%, red if unreachable

Research: VibeMux permission-mode-per-cell display, AutoGPT THOUGHT/REASONING/PLAN/ACTION/
OBSERVATION lifecycle labels, agent-deck `!/@/#/$` status encoding.

---

## Phase 7 — OTel Bridge (`LYRA_ENABLE_TELEMETRY=1`)
**New module**: `packages/lyra-core/src/lyra_core/observability/telemetry_bridge.py`

### What to build

**TelemetryBridge** — EventBus subscriber that emits OTel spans:
- Activated by `LYRA_ENABLE_TELEMETRY=1` environment variable
- Converts EventBus events → OTel spans using OpenInference semantic conventions:
  - `LLMCallFinished` → kind `LLM`; attrs: `gen_ai.model_name`, `gen_ai.usage.input_tokens`,
    `gen_ai.usage.cache_read_input_tokens`
  - `ToolCallFinished` → kind `TOOL`; attrs: `gen_ai.tool.name`, `tool.duration_ms`
  - `SubagentFinished` → kind `AGENT`; attrs: `agent.role`, `agent.worktree`
- Parent-child linkage via `span_id + parent_span_id`
- OTLP HTTP export to configured endpoint (default: `http://localhost:4318`)
- Optional deps: `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`
  (guarded by `try/import`; degrades gracefully if not installed)

**Drop-in compatibility**:
- Arize Phoenix: `python -m phoenix.server.main serve` → `LYRA_ENABLE_TELEMETRY=1 lyra run …`
- Langfuse: `OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel`

**Secrets masking**: inherit HIREmitter's 7 redaction patterns.

Research: Arize Phoenix offline mode, OpenLLMetry SDK auto-instrumentation, Langfuse
`CLAUDE_CODE_ENABLE_TELEMETRY` zero-code path, Traceloop/OpenLLMetry SDK.

---

## Phase 8 — Lyra-Original Transparency Capabilities
**New modules**: `lyra_core/observability/context_gauge.py`,
`lyra_cli/interactive/skill_panel.py`, `lyra_core/observability/dag_display.py`

*These capabilities have no adequate prior art in the surveyed ecosystem.*

### Context Window Saturation per Agent

**ContextGauge** — subscribes to `LLMCallFinished`, computes `tokens_used / model_context_limit`:
- Fill bar in subagent tree view: `[████████░░] 82%`
- At 80%: badge `[NGC]` orange (NGC compactor will trigger next step)
- At 95%: badge `[NGC!]` red
- Model context limits: constant map `{claude-sonnet-4-6: 200_000, gpt-4o: 128_000, …}`

### Skill Activation Panel

**SkillPanel** — shows for each activated skill:
- `{skill_name, tier (BM25|cross-encoder|embedding), trust_tier, success_rate, last_used}`
- Emitted by `SKILLS_ACTIVATED` `LifecycleEvent` (already exists in `lifecycle.py`)
- `lyra skills --active` command + TUI sidebar tab

### DAG Task Graph Display

**DagDisplay** — renders wave-execution DAG for `lyra run --harness dag-teams`:
- Rich `Table`: `{wave, node_id, depends_on, status, worktree, duration}`
- Status color: pending=dim, running=green+spinner, parked=yellow, done=dim, failed=red
- Merge conflict detection: flag nodes waiting on a blocked merge
- `lyra dag [--session SESSION_ID]` command

---

## Sequencing Rationale

Phase 1 (EventBus + state file) is the prerequisite for all later phases — everything reads
from or publishes to the bus.

Phases 2–3 deliver the fastest path to visible user value (CLI commands + Rich panel) without
touching the interactive session or TUI.

Phase 4 (process tree) needs Phase 1's `SubagentSpawned` events.

Phases 5–6 can proceed in parallel after Phase 3 is deployed.

Phase 7 (OTel) is independent and can proceed any time after Phase 1.

Phase 8 requires Phase 6 (TUI sidebar) and Phase 4 (process tree) to land first.
