# Lyra — Architecture

A **general-purpose, CLI-native coding harness** designed to run autonomous long-horizon software engineering tasks with deterministic discipline. Lyra combines the best-understood ideas from four harness lineages (Claude Code, OpenClaw, Hermes Agent, SemaClaw) and **ships TDD as one of several optional discipline plugins** rather than as a runtime invariant. Out of the box `lyra` behaves like `claw-code`, `opencode`, and `hermes-agent`: a general coding agent that doesn't refuse Edits because no failing test exists yet. Teams that want the historical TDD-as-kernel posture flip a single switch (`/tdd-gate on` or `/config set tdd_gate=on`) and the deterministic gate hook re-arms instantly.

Sibling project: [orion-code](../../orion-code/docs/architecture.md). Shared foundation: [`harness_core`](../../orion-code/harness_core/).

## 1. Goals and measurable targets

| Target | Metric | Baseline |
|---|---|---|
| Beat baseline coding agents on real repos | SWE-bench Verified pass@1 ≥ **45%** by v1; ≥ **52%** by v2 | Claude Sonnet 4.6 harness-less (~38%); GPT-5 harness-less (~41%) |
| Optional TDD plugin does not cripple productivity (when enabled) | TDD-gate false-positive rate < **5%** on TDD-benchmark set (internal, 300 PRs) | n/a (new metric) |
| Cross-session continuity works | 100% pass on `resume-from-state.md` smoke test | Claude Code ~92%, OpenCode ~89% |
| Bounded cost | ≤ **$2.00** average per merged PR on internal eval | Claude Code ~$2.40, SWE-agent ~$3.10 |
| Low sabotage leak rate | ≤ **0.5%** on LaStraj-style adversarial suite | SWE-agent ~3%, Claude Code ~1.2% |
| Repeatable traces | 95% of v1 PRs replayable from trace+plan alone | n/a (new metric) |

All targets are frozen before Phase 0 spec freeze and re-measured nightly in CI once code lands.

## 2. Non-goals

1. **Not** a general-purpose personal agent (scope of SemaClaw / Hermes / [mentat-learn](../../mentat-learn/)).
2. **Not** a chat product. Prompts are task-shaped; replies are artifacts and plans, not conversation.
3. **Not** a training harness (v1). Agent-World-style synthesis is opt-in v2 module.
4. **Not** a hosted SaaS. Daemon is local-only; team coordination comes via Multica adapter later.
5. **Not** a generic AI assistant. The kernel assumes: repos, tests, diffs, PRs. It refuses tasks outside that surface (with pointer to sibling projects).
6. **Not** a framework that hides the LLM. Every call is inspectable, every tool is typed, every hook is listed, the trace is append-only.

## 3. Ten architectural commitments

Each commitment has a single-sentence contract, the failure it prevents, and the accepted cost. The costs are expanded in [`architecture-tradeoff.md`](architecture-tradeoff.md).

### 3.1. **Plan Mode default-on**

Every non-trivial task routes through Plan Mode first ([block 02](blocks/02-plan-mode.md)): the agent writes a plan artifact under `.lyra/plans/<session>.md`, user approves, only then execution begins with write permissions. Skipped via `--no-plan` for trivial tasks.

- Prevents: 60% of long-horizon failures start with a misinterpreted brief.
- Accepts: ~30 seconds of latency on short tasks.

### 3.2. **Three-agent topology available; single-agent default**

Built-in harness plugins: `single-agent` (default), `three-agent` (Planner / Generator / Evaluator with different-family judge), `dag-teams` (SemaClaw two-phase for multi-strand work). Selectable per-task via `--harness` flag or auto-chosen from plan complexity.

- Prevents: narrative fluency without verification, long compound errors.
- Accepts: ~1.6× token cost when three-agent is selected; requires two model families.

### 3.3. **PermissionBridge is a runtime primitive**

Authorization checkpoints are **declared on tool schemas**, not decided by the LLM. Every tool invocation flows through `permissions/bridge.py`, which consults rules + ML risk classifier + mode → `allow` / `ask` / `deny` / `park` (SemaClaw contribution: parked nodes do not block downstream DAG work).

- Prevents: LLM-convinced bypass of safety rules, prompt-injection-driven tool misuse.
- Accepts: One extra API decision per tool call, ~2ms median overhead.

### 3.4. **Optional TDD gate is a hook, not a prompt**

When the optional TDD plugin is enabled (off by default in v3.0.0; flip on with `/tdd-gate on`), the gate ([block 05](blocks/05-hooks-and-tdd-gate.md)) is deterministic code running on `PreToolUse(Edit|Write)` and `Stop`. It blocks mutations to `src/**` unless the session has a recent failing test that justifies the change; it blocks session completion unless the relevant tests pass. When the plugin is **off** (the default) the same hook is registered but short-circuits, and `/review` reports the gate as a neutral `off (opt-in)` instead of a verifier failure.

- Prevents (when enabled): "test-after" habits, debt accumulation, drift between spec and implementation.
- Accepts (when enabled): Extra latency (~200-800ms per Edit) for running focused tests; higher friction for exploratory work (mitigated by mode flags). When disabled, none of the above costs apply — Lyra behaves like a general coding agent.

### 3.5. **Five-layer context pipeline with a never-compacted SOUL**

Context engine ([block 06](blocks/06-context-engine.md)) maintains five tiers: cached system prefix, cached mid (SOUL + plan + todo), dynamic recent turns, compaction summaries, offloaded memory references. `SOUL.md` lives in the cached mid tier and is **never auto-compacted** (SemaClaw contribution: persona drift is the dominant long-session failure).

- Prevents: identity drift, context rot, runaway token costs.
- Accepts: SOUL.md size cap (~2KB default); compaction has adjustable thresholds.

### 3.6. **Skill library with post-task extraction loop**

Skills ([block 09](blocks/09-skill-engine-and-extractor.md)) are the unit of capability. `SKILL.md` format compatible with Claude Code / OpenClaw. After every completed task, the skill extractor evaluates whether the successful trajectory should become a new skill or augment an existing one. Refinement follows the Hermes outcome-fed pattern (success / partial / fail).

- Prevents: re-learning the same pattern across sessions.
- Accepts: Memory growth; requires self-eval every 15 tasks to prune bad skills.

### 3.7. **Subagents in git worktrees**

Parallel subagents ([block 10](blocks/10-subagent-worktree.md)) each get their own git worktree on a session branch, merged back via fast-forward or 3-way merge on completion. Shared filesystem access is read-only.

- Prevents: incoherent parallel edits stomping each other.
- Accepts: disk overhead (~100MB per subagent on average repo); occasional merge conflicts surfaced to user.

### 3.8. **Two-phase verifier with cross-channel evidence**

Verifier ([block 11](blocks/11-verifier-cross-channel.md)) runs Phase 1 objective checks (tests / types / lint / expected-files) cheaply; only on pass does Phase 2 subjective LLM evaluator (different-family) examine the artifact. Cross-channel verification requires **trace + diff + environment snapshot** to agree before a task may be marked complete.

- Prevents: fabricated success, sabotage, test-disable tricks.
- Accepts: Two model families. Cost of cross-channel checks.

### 3.9. **Session continuity via human-readable STATE.md**

Session state persists to `.lyra/state/STATE.md` ([block 13](blocks/13-observability.md)): plan status, remaining items, open questions, current hypothesis, last tool calls. Resume reads STATE.md + last N turns from `recent.jsonl`. Git commits are atomic checkpoints. No binary pickle.

- Prevents: ungreppable state, vendor lock-in, opaque crash recovery.
- Accepts: Some ephemeral information loss (tool call arguments older than a few turns).

### 3.10. **HIR-compatible trace emission**

Every span the observability layer emits ([block 13](blocks/13-observability.md)) includes OTel GenAI semantic attributes plus primitive tags compatible with the [Gnomon HIR schema](../../../docs/67-recommended-breakthrough-project.md). No extra adapter needed to run HAFC / SHP / autogenesis tools against an Lyra trace.

- Prevents: trace format lock-in, reinvention of evaluation infrastructure.
- Accepts: HIR schema stability risk (we mirror upstream; breaking changes require migration script).

### 3.11. **Small/smart model routing (v2.7.1)**

Lyra adopts Claude Code's two-tier model pattern (Haiku for cheap turns, Sonnet for reasoning) but generalised across providers. Every `InteractiveSession` carries two model slots — `fast_model` (defaults to `deepseek-v4-flash` → `deepseek-chat`) and `smart_model` (defaults to `deepseek-v4-pro` → `deepseek-reasoner`) — and a single `_resolve_model_for_role(session, role)` helper maps each request to a slot: `chat` → fast; `plan` / `spawn` / `cron` / `review` / `verify` / `subagent` → smart. The resolver runs **before every LLM call** and either rebuilds the provider via `build_llm` (env-stamped with `HARNESS_LLM_MODEL` and the provider-specific override, e.g. `DEEPSEEK_MODEL`) or mutates the cached provider's `model` attribute in place. Aliases live in `lyra_core.providers.aliases` (see `AliasRegistry`); the `/model` slash command exposes the slots via `fast` / `smart` (one-shot) and `fast=<slug>` / `smart=<slug>` (persistent). Legacy `--model <slug>` and `/model <slug>` still pin a universal model and override both slots — the escape hatch.

- Prevents: paying reasoning-tier cost on chat turns, paying chat-tier latency on planning, vendor lock-in to any one frontier.
- Accepts: Two model slugs per session (one extra config knob); slot-routing logic that the agent loop, planner, subagent runner, cron daemon, and post-turn reviewer must all pass through.

## 4. Component stack (diagram)

```
┌────────────────────────────────────────────────────────────────────┐
│                           User                                     │
│           ↕ (Typer CLI · Python API · web viewer :47777)           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Gateway  (always-on control plane, OpenClaw-inspired)      │   │
│  │  - Routing, session lifecycle, event bus                    │   │
│  │  - Hook/skill/MCP registry authoritative store              │   │
│  │  - Chooses Harness Plugin per task                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Harness Plugins  (strategy pattern)                        │   │
│  │   single-agent · three-agent · dag-teams                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│   ↓            ↓              ↓                                    │
│ [Agent   [Subagent      [DAG Scheduler] [Skill Router]             │
│  Loop]    Orchestrator]                                            │
│   ↓            ↓              ↓              ↓                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Model Router  (commitment 3.11)                            │   │
│  │  fast slot  (default: deepseek-v4-flash → deepseek-chat)    │   │
│  │  smart slot (default: deepseek-v4-pro   → deepseek-reasoner)│   │
│  │  role → slot:  chat→fast | plan/spawn/cron/review→smart     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Tool Layer  (typed core + MCP adapters)                    │   │
│  │   Read · Grep · Glob · Edit · Write · Bash · Skill · Spawn  │   │
│  │   · WebFetch · MCP stdio · MCP HTTP                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PermissionBridge  (runtime primitive, SemaClaw)            │   │
│  │  Modes: plan · default · acceptEdits · bypass · red · green │   │
│  │         · refactor · triage                                 │   │
│  │  + Hooks: pre/post tool · stop · session · submit           │   │
│  │  + Risk classifier (rules + ML)                             │   │
│  │  + Injection guard (ML + LLM vote + canary)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Context Engine  (5-layer)                                  │   │
│  │  L1 cached prefix │ L2 cached mid (SOUL, plan, todo)        │   │
│  │  L3 dynamic recent │ L4 compaction │ L5 memory refs         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Memory Store  (three-tier, SQLite FTS5 + Chroma)           │   │
│  │  procedural · episodic · semantic · persona (SOUL.md)       │   │
│  │  agentic wiki (cited, TTL-decayed)                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Skill Engine  (Voyager-style library)                      │   │
│  │   Loader · Router · Extractor (post-task) · Refiner · Eval  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Verifier / Evaluator  (two-phase, cross-channel)           │   │
│  │  Phase 1: objective (tests + types + lint + files)          │   │
│  │  Phase 2: different-family LLM judge with rubric            │   │
│  │  Cross-channel: trace ↔ diff ↔ env snapshot                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Safety Monitor  (continuous, every N steps, cheap model)   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          ↓                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Observability  (OTel spans + JSONL trace + cost per-feat)  │   │
│  │  HIR-compatible emission · web viewer · nightly replay      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
       ↕                                         ↕
   MCP servers (external)                 Scheduler (cron skills, Hermes)
```

## 5. Canonical control flow (high level)

### 5.1. `lyra run "<task>"`

1. **Gateway** resolves repo, loads config, selects harness plugin (`single-agent` by default).
2. **Session Manager** creates `.lyra/state/<session-id>/`, allocates a session-branch in git, writes `STATE.md` seed.
3. If Plan Mode default-on (`--no-plan` not set and task heuristic ≠ trivial):
    - Harness enters `PermissionMode.PLAN` → writes are blocked.
    - Planner generates a plan → writes `plans/<session>.md`.
    - User approves (interactive) or `--auto-approve` (CI).
4. **Permission mode upgrades** to `default` (or `acceptEdits` / `red` / `green` depending on plan item).
5. **Agent Loop** runs: context assembled via Context Engine, LLM call, tool calls flow through PermissionBridge + Hooks (including TDD gate), results folded back.
6. On each `Edit` into `src/**`:
    - `PreToolUse` hook checks for recent failing test → blocks if absent.
    - Tool executes.
    - `PostToolUse` hook runs focused tests; failure returns a critique observation for next step.
7. **Safety Monitor** runs every 5 steps on the trace; any flag pauses the session.
8. On `end_turn`:
    - **Verifier** runs Phase 1 checks; if pass, Phase 2 LLM judge.
    - **Cross-channel** check: trace ↔ diff ↔ env snapshot.
    - **Skill Extractor** evaluates whether to promote the trajectory to a new/updated skill.
    - **STATE.md updated**; git commit tagged with session id.
9. Final artifact: PR-ready branch, plan, trace, verifier report. If in `ship --pr` mode, Gateway opens the PR via GitHub/Gitea MCP.

### 5.2. `lyra run --harness dag-teams "<task>"`

1–2 same as above.
3. **Planner** emits a task DAG instead of linear plan (SemaClaw two-phase).
4. **DAG Scheduler** validates (no cycles, all refs resolve), partitions into waves.
5. Each DAG node spawns a Subagent in its own git worktree; subagents run single-agent loop scoped to the node's files.
6. PermissionBridge parks high-risk nodes for human approval without blocking downstream independent nodes.
7. Merge strategy: fast-forward when no conflict; 3-way merge with human resolution surface when conflict.
8–9 same as above, applied to the merged result.

## 6. Data flow summary

```
User task ──▶ Gateway ──▶ Planner ──▶ Plan.md (artifact)
                                         │
                                         ▼
                                  Harness Plugin
                                         │
                                         ▼
                           ┌─────────────────────────┐
                           │       Agent Loop        │
                           │ ┌──────────────────┐    │
                           │ │ Model Invocation │    │
                           │ │ (fast / smart    │    │
                           │ │  slot, §3.11)    │    │
                           │ └──────────────────┘    │
                           │          ↓              │
                           │ ┌──────────────────┐    │
                           │ │ PermissionBridge │    │
                           │ └──────────────────┘    │
                           │          ↓              │
                           │ ┌──────────────────┐    │
                           │ │      Hooks       │    │
                           │ │  (incl. TDD)     │    │
                           │ └──────────────────┘    │
                           │          ↓              │
                           │ ┌──────────────────┐    │
                           │ │   Tool Layer     │    │
                           │ └──────────────────┘    │
                           │          ↓              │
                           │ ┌──────────────────┐    │
                           │ │ Context Reducer  │    │
                           │ └──────────────────┘    │
                           └─────────────────────────┘
                                         │
                                         ▼
                                 Verifier (2-phase)
                                         │
                            ┌────────────┴────────────┐
                            ▼                         ▼
                   Skill Extractor              STATE.md update
                            │                         │
                            ▼                         ▼
                     Memory Store             Git commit + PR
```

## 7. Deployment modes

1. **Local-only** (default). Single-user laptop or workstation. No cloud components. `lyra daemon` starts the worker + web viewer on `:47777`.
2. **Local + cloud runners**. Subagent worktrees optionally burst to rented cloud runners (Modal / Fly / bare-metal). Gateway negotiates, worker pool lifecycle-manages.
3. **CI / autonomous**. No interactive approvals. `--auto-approve` flag; `--max-cost` is a hard stop. Designed for integration with GitHub Actions, Jenkins, Buildkite.
4. **Team mode** (v2). Multi-user via Multica adapter: shared skills in pgvector DB, per-workspace isolation, WebSocket progress streams. Out of scope for v1.

## 8. Security posture (summary)

Detailed threat model in [`threat-model.md`](threat-model.md).

- Default permission mode is `default`: reads allowed, writes + bash are `ask` or gated by mode.
- PermissionBridge is the **only** path to tool execution (no "direct" tool call).
- Prompt injection defense runs on untrusted input (web fetches, tool outputs): ML classifier + LLM vote + canary token, same pattern as gstack browser defender.
- All filesystem writes confined to session worktree by default; cross-worktree writes require explicit mode upgrade.
- `Bash` tool has allowlist + risk classifier; destructive patterns (`rm -rf /`, `git push --force` to main) are unbypassable except in `bypass` mode.
- Secrets detection on every `Write` / `Edit` (entropy-based plus known-secret patterns from detect-secrets).
- Cross-channel verification catches trace/diff/snapshot mismatches that would indicate sabotage.
- Sandbox: containerized runners (rootless Podman / Docker) for untrusted code execution. v1 requires opt-in; v2 will default to sandbox for `Bash` + any code fetched from the web.

## 9. Extensibility surfaces

Four user-facing extensibility points (Claude Code alignment; OpenClaw plugin-surface; SemaClaw declared-capability pattern):

1. **MCP servers** — external tool integration. Registered in `.lyra/config.yaml` or `lyra mcp add`.
2. **Skills** — capability packages as `SKILL.md` folders. Installed via `lyra skills install <uri>` or via plugin bundle.
3. **Plugins** — bundles of skills + MCP servers + hooks shipped as one unit. Same format as Claude Code plugins for maximum portability.
4. **Hooks** — deterministic guardrails. User provides Python callable or shell script hooked to a lifecycle event. TDD gate is an internal hook; users can add their own (secrets scan, compliance check, style enforcer).

## 10. What we are explicitly not committing to (yet)

- **Own model training**. Lyra is API-first; we do not fine-tune in v1. If Atomic-Skills-style joint RL becomes turnkey, we reconsider in v2.
- **Skill marketplace**. Community distribution via GitHub repos + `install` subcommand, not a hosted registry.
- **Full Agent-World environment synthesis**. `lyra env` is a v2 opt-in module. v1 relies on existing test suites + benchmarks.
- **SaaS control plane**. No hosted multi-tenant version. Team features arrive via Multica integration.
- **Fully autonomous CI-driven agent** where the agent opens PRs based on its own prioritization. v1 requires a task from user or CI trigger.

## 11. References

- [Orion-Code architecture](../../orion-code/docs/architecture.md) — sibling project, predecessor design thinking.
- [Four Pillars](../../../docs/44-four-pillars-harness-engineering.md) — state, context, guardrails, entropy.
- [Claude Code audit](../../../docs/29-dive-into-claude-code.md) — thirteen principles.
- [OpenClaw](../../../docs/52-dive-into-open-claw.md) — Gateway + pluggable harness.
- [Hermes Agent](../../../docs/55-hermes-agent-self-improving.md) — continual-learning skill library.
- [SemaClaw](../../../docs/54-semaclaw-general-purpose-agent.md) — DAG Teams + PermissionBridge + SOUL.
- [Ten-Link Synthesis](../../../docs/76-ten-links-synthesis.md) — April-2026 landscape.
- [Atomic Skills](../../../docs/68-atomic-skills-scaling-coding-agents.md), [Agent-World](../../../docs/69-agent-world-self-evolving-training-arena.md), [Karpathy Skills](../../../docs/71-karpathy-skills-single-file-guardrails.md), [claude-mem](../../../docs/72-claude-mem-persistent-memory-compression.md), [Multica](../../../docs/73-multica-managed-agents-platform.md), [gstack](../../../docs/75-gstack-garry-tan-claude-code-setup.md).
