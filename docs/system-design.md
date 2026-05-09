# Lyra — System Design

Operational specification. Companion to [`architecture.md`](architecture.md) (*what* and *why*) and [`architecture-tradeoff.md`](architecture-tradeoff.md) (*alternatives considered*). This document says *how* the system is built and run.

Reader notes:

- Pseudo-code is Python-flavored with type hints; actual sources in `src/lyra_core/…` will be idiomatic Python 3.11+.
- Language: Python for the harness library, CLI, and tooling. Subprocess shells out to language-specific test runners. Web viewer is a small Starlette app shipped in the same wheel.

## 1. Topology

```
┌──────────────────────────── developer laptop ────────────────────────────┐
│                                                                          │
│  ┌────────────┐   stdin   ┌──────────────────────────────────────────┐   │
│  │ lyra ├──────────▶│  lyra-daemon (local)               │   │
│  │   CLI      │           │  - Gateway / SessionManager              │   │
│  │ (Typer)    │◀──events──│  - HookRegistry / ToolRegistry           │   │
│  └────────────┘   rich    │  - Web viewer @ :47777 (lazy-start)      │   │
│                           │  - Worker pool (subagents, verifier)     │   │
│                           └──────────────────────────────────────────┘   │
│                                    ↕                                     │
│                                    │ spawns                              │
│                                    ▼                                     │
│               ┌───────────────────────────────────────────┐              │
│               │  Per-session process space                │              │
│               │  - AgentLoop (gen model client)           │              │
│               │  - Evaluator (eval model client)          │              │
│               │  - SafetyMonitor (nano model client)      │              │
│               │  - Subagents (each in their own worktree) │              │
│               │  - MCP clients (stdio + HTTP)             │              │
│               └───────────────────────────────────────────┘              │
│                                    ↕                                     │
│                       ┌────────────┴────────────┐                        │
│                       │                         │                        │
│                ┌──────▼──────┐           ┌──────▼──────┐                 │
│                │ .lyra/ │           │ ~/.lyra/ │             │
│                │  (repo-scope)│           │  (user-scope)  │             │
│                └──────────────┘           └────────────────┘             │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↕
            ┌───────────────────────────────────────────┐
            │  Cloud LLM providers (Anthropic, OpenAI,  │
            │  Gemini)  — model routing via config      │
            └───────────────────────────────────────────┘
                                    ↕
            ┌───────────────────────────────────────────┐
            │  Optional: cloud runner pool (Modal/Fly)  │
            │  for burst subagents                      │
            └───────────────────────────────────────────┘
```

**Single-process default.** The daemon is a convenience; for small repos the CLI can run everything in-process with `lyra run --foreground`.

**No external daemons required.** SQLite, Chroma, and the web viewer are all in-process / on-disk. This aligns with OpenClaw's self-sovereign posture.

## 2. Data model

All entities are Pydantic v2 models in `lyra_core.state`. Hash-addressed where noted (content-hash stored alongside for replay).

### 2.1. `Session`

```python
class Session(BaseModel):
    id: str                       # ulid
    repo_root: Path
    created_at: datetime
    updated_at: datetime
    status: Literal["active","paused","completed","failed","human_review"]
    harness_plugin: Literal["single-agent","three-agent","dag-teams"]
    permission_mode: PermissionMode
    budgets: Budgets             # steps, tokens, cost-usd caps
    cost_usd: float              # running tally
    model_selection: ModelSelection
    plan_id: Optional[str] = None
    trace_path: Path             # .lyra/traces/<session>.jsonl
    state_path: Path             # .lyra/state/<session>/STATE.md
    git_branch: str              # session branch created on start
    soul_revision: str           # hash of SOUL.md at session start (drift audit)
```

### 2.2. `Plan`

```python
class Plan(BaseModel):
    id: str
    session_id: str
    title: str
    feature_items: list[FeatureItem]
    goal_hash: str               # content hash of ground-truth goal
    acceptance_tests: list[str]  # test selectors that must pass
    expected_files: list[str]    # files that SHOULD be touched
    forbidden_files: list[str]   # files that MUST NOT be touched
    created_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None  # "user" | "auto-approve" | ci-id
```

### 2.3. `FeatureItem`

```python
class FeatureItem(BaseModel):
    id: str
    plan_id: str
    description: str
    tasks: list[Task]
    status: Literal["pending","in_progress","blocked","done","rejected"]
    depends_on: list[str] = []   # DAG edge support
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    commit_hash: Optional[str] = None  # set when done
```

### 2.4. `Task` (atomic work unit inside a FeatureItem)

```python
class Task(BaseModel):
    id: str
    feature_item_id: str
    kind: Literal["localize","edit","test_gen","reproduce","review","bash","custom"]
    description: str
    context_hashes: list[str]    # content of files referenced
    result_hash: Optional[str] = None
    trace_span_id: str
```

### 2.5. `Trace`

Append-only JSONL + OTel span export. Every line is one event:

```python
class TraceEvent(BaseModel):
    span_id: str
    parent_span_id: Optional[str]
    session_id: str
    type: Literal[
        "session.start","session.end","agent.step",
        "model.call","tool.call","tool.result",
        "hook.pre","hook.post","permission.decide",
        "subagent.spawn","subagent.join",
        "evaluator.verdict","safety.flag",
        "skill.invoke","skill.extract","memory.read","memory.write",
        "compaction","state.save",
    ]
    ts: datetime
    duration_ms: Optional[float]
    attrs: dict[str, Any]        # GenAI semantic attrs + Lyra extensions
    # HIR primitive tag for Gnomon compatibility
    hir_primitive: Optional[str] = None
```

### 2.6. `Artifact`

```python
class Artifact(BaseModel):
    hash: str                    # sha256 of content
    kind: Literal["diff","env_snapshot","test_output","plan","observation"]
    created_at: datetime
    path: Path                   # .lyra/artifacts/<hash>
    size_bytes: int
    source_session: str
```

### 2.7. `ModelSelection` (v2.7.1)

Two-tier model split modeled on Claude Code's Haiku-for-cheap-turns / Sonnet-for-reasoning pattern, but generalised across providers (see [`architecture.md` §3.11](architecture.md#311-smallsmart-model-routing-v271)). Both slots accept aliases that resolve through `lyra_core.providers.aliases.AliasRegistry` before each LLM call.

```python
class ModelSelection(BaseModel):
    fast: str = "deepseek-v4-flash"   # → resolves to "deepseek-chat"
    smart: str = "deepseek-v4-pro"    # → resolves to "deepseek-reasoner"
    default: str = "auto"              # legacy "universal" pin; "auto" defers to slot routing
```

Role → slot mapping (single source of truth: `_resolve_model_for_role`):

| Role                                                       | Slot   | Used by                                          |
|------------------------------------------------------------|--------|--------------------------------------------------|
| `chat`                                                     | fast   | regular REPL turns, tool calls, summaries        |
| `plan`                                                     | smart  | `lyra plan`, `/plan`                             |
| `spawn` / `subagent`                                       | smart  | `/spawn` (each subagent's `AgentLoop`)           |
| `cron`                                                     | smart  | scheduled fan-out via the cron daemon            |
| `review` / `verify`                                        | smart  | `/review --auto`, Phase-2 LLM evaluator          |
| (anything else)                                            | falls back to `ModelSelection.default` (legacy) | escape hatch |

Mutating a slot at runtime stamps `HARNESS_LLM_MODEL` (universal) and the provider-specific override (e.g. `DEEPSEEK_MODEL`, `ANTHROPIC_MODEL`) so a freshly built provider lands on the same slug; cached providers have their `model` attribute mutated in place to keep chat history, MCP plumbing, and the budget meter attached.

## 3. Directory layout (on disk)

### 3.1. Per-repo `.lyra/`

```
.lyra/
├── config.yaml                  # providers, budgets, overrides
├── soul.yaml                    # optional soft-link to a shared SOUL.md
├── plans/
│   └── <session-id>.md          # human-readable Plan artifact
├── state/
│   └── <session-id>/
│       ├── STATE.md             # session handoff
│       ├── recent.jsonl         # last N turns
│       └── budgets.yaml         # running budgets
├── traces/
│   └── <session-id>.jsonl       # append-only trace
├── memory/
│   ├── SOUL.md                  # persona (never auto-compacted)
│   ├── MEMORY.md                # durable facts (user-editable)
│   ├── wiki/                    # agentic wiki entries
│   ├── feedback/                # skill refinement notes
│   ├── sessions.db              # SQLite (sessions, observations, summaries)
│   └── chroma/                  # Chroma on-disk collection
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md
│       └── ...                  # companion files, scripts, templates
├── artifacts/
│   └── <hash>/                  # offloaded observations, diffs
└── mcp-servers.yaml             # registered MCP integrations
```

### 3.2. Per-user `~/.lyra/`

Same tree with user-scoped content (shared across repos). Skills at user scope are available everywhere; SOUL.md at user scope is a default that repo-level SOUL.md overrides.

## 4. Public APIs

### 4.1. Python — `lyra.Agent`

```python
from lyra import Agent, PermissionMode

agent = Agent.from_config(
    repo_root="/path/to/repo",
    # v2.7.1+: two-slot fast/smart split (preferred).
    # Roles auto-route: chat → fast, plan/spawn/cron/review → smart.
    models={
        "fast":  "deepseek-v4-flash",   # → deepseek-chat
        "smart": "deepseek-v4-pro",     # → deepseek-reasoner
    },
    permission_mode=PermissionMode.DEFAULT,
    budgets=Budgets(max_steps=80, max_tokens=300_000, max_cost_usd=5.0),
)

# Legacy four-role schema (still accepted; mapped onto fast/smart at load):
#   "generator" / "planner" / "evaluator" / "safety" → smart slot (review-tier)
#   no separate cheap-turn slot                      → fast slot defaults to deepseek-v4-flash
agent = Agent.from_config(
    repo_root="/path/to/repo",
    models={
        "generator": "anthropic/claude-sonnet-4-6",
        "planner":   "anthropic/claude-opus-4-7",
        "evaluator": "openai/gpt-5",
        "safety":    "openai/gpt-5-nano",
    },
    permission_mode=PermissionMode.DEFAULT,
    budgets=Budgets(max_steps=80, max_tokens=300_000, max_cost_usd=5.0),
)

result = agent.run(
    "Add a dark mode toggle that persists across reloads.",
    plan_mode=True,           # default
    harness="single-agent",   # default; "three-agent" | "dag-teams"
    on_approval="interactive" # "interactive" | "auto" | "never"
)
# result: AgentRunResult { plan_id, trace_id, status, cost_usd, pr_url? }
```

### 4.2. Typer CLI — see `lyra/cli.py`

Canonical command inventory (subcommand tree):

```
lyra
├── run <task>
├── plan <task>
├── red <test-description>
├── green
├── refactor
├── review [--file=<path>]
├── test [--watch]
├── ship [--pr]
├── retro [--period=week|sprint]
├── skills [list|show|install|uninstall|init|refine]
├── mcp [list|add|remove|doctor]
├── mem [search|show|timeline|wipe]
├── soul [edit|cat|revert]
├── config [get|set|show]
├── daemon [start|stop|status|restart|logs]
├── doctor
├── bench [run|compare]
├── learn [review|refine]
├── env [scaffold|list]          # v2 — agent-world-style
├── red-team run
└── version
```

### 4.3. Tool layer (typed tools)

```python
@tool(name="Read", writes=False, risk="low")
def read_file(
    path: str,
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read a file. Pagination recommended for > 2k LOC files."""

@tool(name="Grep", writes=False, risk="low")
def grep(
    pattern: str,
    path: str = ".",
    output_mode: Literal["files_with_matches","content","count"] = "files_with_matches",
    head_limit: int = 250,
    type: Optional[str] = None,       # rg --type
    multiline: bool = False,
) -> str: ...

@tool(name="Glob", writes=False, risk="low")
def glob(pattern: str, root: str = ".") -> list[str]: ...

@tool(name="Edit", writes=True, risk="medium")
def edit(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Unique exact-match replacement. Fails if old_string not unique."""

@tool(name="Write", writes=True, risk="medium")
def write(path: str, content: str) -> str: ...

@tool(name="Bash", writes=True, risk="high")
def bash(command: str, timeout_s: int = 30, cwd: Optional[str] = None) -> str: ...

@tool(name="Skill", writes=False, risk="low")
def invoke_skill(name: str, args: dict = {}) -> str: ...

@tool(name="Spawn", writes=False, risk="medium")
def spawn_subagent(purpose: str, scope: list[str], branch: Optional[str] = None) -> str: ...

@tool(name="WebFetch", writes=False, risk="medium")
def web_fetch(url: str) -> str: ...

@tool(name="WebSearch", writes=False, risk="low")
def web_search(query: str, limit: int = 10) -> list[dict]: ...

@tool(name="AskUser", writes=False, risk="low")
def ask_user(questions: list[Question]) -> dict[str, str]: ...
```

All tools are Pydantic-validated, OpenAPI-schema-exportable, MCP-compatible.

### 4.4. Subagent dispatch API

```python
sub = Subagent(
    parent_session=session,
    purpose="Reproduce issue #123 in a minimal test case.",
    scope_files=["tests/", "src/auth.py"],
    worktree_branch="sub-reproduce-123",
    budgets=Budgets(max_steps=20, max_cost_usd=0.80),
    allowed_tools=["Read","Grep","Glob","Edit","Write","Bash"],
)
result = sub.run()
# returns Observation to parent agent, not raw trace
```

### 4.5. Evaluator protocol

```python
class EvaluatorVerdict(BaseModel):
    verdict: Literal["accept","reject","degraded_eval"]
    phase1_objective: ObjectiveReport
    phase2_subjective: Optional[SubjectiveReport]
    evaluator_model: str
    trace_id: str

verdict = evaluator.judge(plan_item=plan_item, artifact=artifact, trace=trace)
```

### 4.6. Hook API

```python
from lyra import Hook, HookEvent

@Hook.register(HookEvent.PRE_TOOL_USE)
def block_rm_rf_root(call: ToolCall, session: Session) -> HookDecision:
    if call.name == "Bash" and re.search(r"rm\s+-rf\s+/", call.args["command"]):
        return HookDecision(block=True, reason="forbidden destructive pattern")
    return HookDecision.allow()
```

Hooks can be declared in `.lyra/hooks.yaml` (shell commands) or Python modules under `src/lyra_plugins/hooks/`.

## 5. Agent Loop reference pseudo-code

Builds on [`harness_core.loop.AgentLoop`](../../orion-code/harness_core/src/harness_core/loop.py) with Lyra-specific additions (TDD gate, cross-channel, safety monitor, HIR tag emission):

```python
def agent_loop(
    session: Session, task: str, *, plan: Plan | None = None,
) -> LoopResult:
    transcript = initial_transcript(session, task, plan)
    repeat_guard = RepeatDetector()

    with tracer.span("agent.run", session=session.id, hir="agent_loop"):
        for step in range(session.budgets.max_steps):

            if transcript.tokens > session.budgets.max_tokens * 0.85:
                transcript = context_engine.compact(transcript)
                tracer.event("compaction", hir="compaction_event")

            assert session.cost_usd < session.budgets.max_cost_usd, "cost cap hit"

            with tracer.span("agent.step", step=step) as sp:
                resp = model.chat(
                    transcript,
                    tools=tool_layer.schemas(session.permission_mode),
                    prompt_cache=session.cache_config,
                )
                transcript.append(resp); session.cost_usd += resp.cost_usd
                sp.attrs["tool_calls"] = len(resp.tool_calls)

            if resp.stop_reason == "end_turn":
                return finalize(session, transcript, step)

            for call in resp.tool_calls:
                call = repeat_guard.check(call)
                if call is None:
                    transcript.append(tool_result_repeat_suppressed())
                    continue

                decision = permission_bridge.decide(call, session)
                tracer.event("permission.decide", hir="permission_check",
                             decision=decision.decision, reason=decision.reason)
                if decision.decision == "deny":
                    transcript.append(tool_result(call, f"blocked: {decision.reason}"))
                    continue
                if decision.decision == "ask":
                    if not approval.request(call, session): continue
                if decision.decision == "park":
                    session.parked_calls.append(call); continue

                pre = hooks.run(HookEvent.PRE_TOOL_USE, call, session)
                tracer.event("hook.pre", hir="hook", block=pre.block, name=pre.name)
                if pre.block:
                    transcript.append(tool_result(call, f"hooked: {pre.reason}"))
                    continue

                with tracer.span(f"tool.{call.name}", hir="tool_use") as sp:
                    result = tool_layer.execute(call, session)
                    sp.attrs["is_error"] = result.is_error

                post = hooks.run(HookEvent.POST_TOOL_USE, call, result, session)
                tracer.event("hook.post", hir="hook", annotation=post.annotation)
                if post.annotation:
                    result = result.with_annotation(post.annotation)

                observation = context_engine.reduce(result)
                transcript.append(tool_result(call, observation))

                if safety_monitor.should_check(step):
                    verdict = safety_monitor.check(session.trace)
                    tracer.event("safety.flag", hir="verifier_call", flag=verdict.flag)
                    if verdict.flag: raise SafetyViolation(verdict)

        raise StepBudgetExhausted
```

HIR tags (`hir="…"`) are the Gnomon-compatible primitive labels; see [block 13](blocks/13-observability.md).

## 6. Deployment modes

### 6.1. Local-only

- Single user, single laptop.
- Daemon on localhost. SQLite + Chroma on disk. LLM calls to cloud APIs.
- Works offline if using a local-only model (Ollama).
- Default install target.

### 6.2. Local + cloud runner pool

- Subagent worktrees burst to cloud runners (Modal / Fly / a user's k8s cluster).
- Gateway negotiates work allocation; results sync back via git push/pull.
- Latency hit ~1-3s per subagent handoff.
- Opt-in; configure pool in `~/.lyra/config.yaml`.

### 6.3. CI / autonomous

- No interactive approvals.
- `--auto-approve` for Plan Mode.
- `--max-cost` hard stop.
- Exit codes map to build status:
    - `0` = all features shipped, PR opened.
    - `2` = plan rejected.
    - `3` = TDD gate block (unresolved after retries).
    - `4` = cost cap hit.
    - `5` = safety flag.
    - `1` = other errors.

### 6.4. Team mode (v2)

- Multica-style: shared skill DB in PostgreSQL + pgvector, per-workspace isolation, WebSocket progress stream.
- Out of scope for v1.

## 7. Service Level Objectives

| SLO | Target | Monitoring |
|---|---|---|
| Cold start (CLI → first token) | < 3s p95 | `tracer.measure("coldstart")` |
| TDD-gate decision time | < 500ms p95 | `tracer.measure("hook.tdd")` |
| Permission decision time | < 5ms p95 | `tracer.measure("permission.decide")` |
| Memory retrieval (hybrid) | < 100ms p95 | `tracer.measure("memory.search")` |
| Verifier Phase 1 on 500-test repo | < 60s p95 | `tracer.measure("verifier.phase1")` |
| Cross-channel snapshot | < 2s p95 | `tracer.measure("verifier.crosscheck")` |
| Web viewer first load | < 500ms p95 | nightly smoke |
| Fatal daemon crashes per 24h | < 0.1 | `process.exit` counter |
| Session resume correctness | 100% on smoke set | nightly replay test |

## 8. Observability

Detailed in [block 13](blocks/13-observability.md). Summary:

- **OTel spans** with `genai.*` semantic attributes + Lyra extensions (plan-item, skill, hook, hir primitive).
- **JSONL trace** append-only to `.lyra/traces/<session>.jsonl` — one canonical copy plus OTel exporter of choice.
- **Web viewer** on `:47777`: sessions, traces, cost breakdown, skill library browser, memory inspector.
- **Cost attribution** per feature-item, per model, per skill. Surfaced in `lyra retro`.
- **Nightly replay** of a curated trace set against the current harness version to catch regressions.

## 9. Security posture

Detailed in [`threat-model.md`](threat-model.md). Summary:

- **Permission modes** control the default policy ladder.
- **PermissionBridge** is the only path to tool execution.
- **Injection guard** (ML + LLM + canary) runs on untrusted input.
- **Secrets scanner** on every `Edit` / `Write`.
- **Filesystem confinement**: session worktree by default; `bypass` or `Bash --cwd=..` requires explicit mode.
- **Network policy**: `WebFetch` is opt-in per URL domain in `acceptEdits` mode.
- **Supply chain**: `lyra skills install` verifies publisher signature (Sigstore) in v2; in v1 warns on unsigned.
- **Cross-channel verification** catches trace/diff/snapshot divergence.

## 10. Scaling

Single-user (v1):

- Session count: unbounded on disk; soft cap 200 sessions active in SQLite; older archived.
- Skill count: O(thousands) with graceful degradation (router indexes descriptions).
- Trace size: progressive-disclosure by default; offload threshold 4KB; artifact referenced by hash.
- Memory DB: SQLite + Chroma local; no cross-user sharing.

Team (v2 plan):

- Postgres + pgvector replaces SQLite + Chroma.
- Workspaces scoped; skill sharing requires explicit publish.
- WebSocket scale via Go backend (Multica pattern).

## 11. Failure handling and recovery

| Failure | Detection | Recovery |
|---|---|---|
| Daemon crash mid-session | systemd / launchd watcher; STATE.md on-disk | `lyra run --resume <session>` reads STATE.md + recent.jsonl |
| Model API 5xx / timeout | Retry with exponential backoff (3 attempts); trace tags `model.retry` | Escalate to alternate model family after 3 fails |
| Model 4xx (invalid request / auth) | Fail fast; surface to user | User fixes config; `lyra doctor` helps |
| Tool timeout | Per-tool timeout in schema; on hit, tool returns error observation | Agent sees the error as an observation, adapts |
| Disk full (worktrees) | Preflight check on `Spawn` | Refuse to spawn; surface message + `lyra doctor` hint |
| Git push rejected (conflict on session branch) | On `ship --pr` | Human resolution; session pauses at `human_review` |
| Cost cap hit | Budget check at each step | Stop, mark session `paused_cost`; user extends or aborts |
| Safety flag | Continuous monitor | Pause session; await human verdict |
| TDD gate repeated blocks | Classifier emits "tdd_false_positive_likely" | Agent offers to write red test; user can `--no-tdd` |
| Prompt injection detected | Injection guard | Truncate injected content; emit span; agent continues with sanitized input |
| Skill extractor produces dup | Deduplication on write | Merge with existing skill; emit `skill.merged` event |

## 12. Testing strategy (mirror of [tdd-discipline.md](tdd-discipline.md))

- **Unit** (every module has `test_<module>.py`).
- **Integration** (filesystem + MockLLM).
- **E2E** (real LLM, gated by env var, run in CI nightly).
- **Property** (Hypothesis for schemas, state transitions).
- **Replay** (recorded trace fixtures, regression guard).
- **Red-team** (adversarial suite, weekly in CI).

Coverage target: ≥ 90% branch on `lyra_core/`, ≥ 80% on `lyra/`.

## 13. Rollout plan

Mirrors [`README.md § 11`](../README.md#status-table). v0.1 walking skeleton targets:

1. **Phase 1 kernel (weeks 2-4).** Loop, tools, permissions, hooks, optional TDD hook (off by default in v3.0.0), CLI skeleton.
2. **Phase 2 context + memory (weeks 5-6).** Five-layer context; SQLite + Chroma memory.
3. **Phase 3 plan + verify (weeks 7-8).** Planner, evaluator two-phase, cross-channel.
4. **Phase 4 skills (weeks 9-10).** Loader, router, extractor, refiner.
5. **Phase 5 multi-agent (weeks 11-12).** Orchestrator, three-agent, DAG Teams.
6. **Phase 6 MCP + obs (weeks 13-14).** MCP adapter, tracer, web viewer, installer.
7. **Phase 7 dogfood + red-team (weeks 15-16).** Dogfood traces, adversarial suite, v0.1.0 release.

Each phase gates on its test suite turning green — meta-TDD for the project itself.
