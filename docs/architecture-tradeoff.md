# Lyra — Architecture Trade-offs

Companion to [`architecture.md`](architecture.md). Every commitment there has a cost; the cost is inventoried here. Ordered by blast radius: first the decisions that shape the whole system, then the merely local ones. For each: **decision**, **chosen alternative**, **rejected alternatives**, **why**, **cost**, **mitigation**.

The cost discipline follows the pattern used in [`orion-code/docs/architecture-tradeoff.md`](../../orion-code/docs/architecture-tradeoff.md).

---

## A. Foundational decisions

### A.1. TDD gate at kernel level — prompt discipline only → rejected

**Decision.** Hook-enforced TDD on `PreToolUse(Edit|Write)` and `Stop`. RED test must exist before any `src/**` edit; GREEN must hold before session completes.

**Rejected alternatives.**

- *System-prompt-only TDD reminder.* Works ~95% of the time (the LLM knows the convention). In production ~5% slip → drift compounds → bad habits encoded in generated code. Pillar 3 of [Four Pillars](../../../docs/44-four-pillars-harness-engineering.md): code-enforced rules are 100%.
- *Test-after verification only.* Allows untested mutations in long traces, creating debt even when the final test passes. Violates Surgical Changes principle from Karpathy-skills.
- *Off-by-default.* User has to remember to opt in; adoption collapses.

**Why chosen.** The only way the gate is load-bearing is if it is a hook. It catches the LLM the way a compiler catches a typo.

**Cost.**

- Extra ~200-800ms per `Edit` (focused test run).
- Friction on exploratory / scratch work (e.g. prototyping).
- False positives on refactors where no new behavior is introduced.

**Mitigation.**

- Per-directory `.lyra/tdd.yaml` overrides (`scratch/`, `examples/`, `docs/` can be marked TDD-exempt).
- Mode flags: `--no-tdd` for one task; `--tdd-mode=advisory` for project-wide downgrade. Telemetry tracks usage of these flags as a health signal — not as a feature to grow.
- Fast test runner selection (pytest-xdist, vitest's worker threads, `go test -run=<subset>`).
- `lyra red` subcommand pre-stages the failing test so the user is never blocked by forgetting to add one.

### A.2. Plan Mode default-on — execute-first → rejected

**Decision.** Every non-trivial task routes through Plan Mode first.

**Rejected alternatives.**

- *Execute-first, show plan after.* Encourages the LLM to commit to a plan via action rather than articulation. Common in simple assistants; catastrophic on long horizons.
- *Opt-in plan mode.* Matches Aider default. Data from [Claw-Eval](../../../docs/38-claw-eval.md) shows Plan Mode adoption below 40% when optional.
- *Plan always, never execute (read-only)*. Defeats the purpose of a coding agent.

**Why chosen.** Front-loading misunderstandings is cheaper than discovering them after 30 tool calls. Plan artifact is also the hand-off doc for resume, audit, and Multica team-mode later.

**Cost.** ~30 seconds of latency on short tasks. User approval friction in CI (mitigated by `--auto-approve` flag or `--no-plan` heuristic).

**Mitigation.** Heuristic auto-skip for tasks under a complexity threshold (single file, no new tests required, no imports added). Configurable per-repo.

### A.3. Single-agent default; multi-agent opt-in — always-multi-agent → rejected

**Decision.** `single-agent` is the default plugin. `three-agent` auto-selected when plan has ≥5 items or includes refactor. `dag-teams` is explicit only.

**Rejected alternatives.**

- *Always three-agent.* ~1.6× token cost on every task; unjustifiable for trivial work.
- *Always DAG teams.* Even higher overhead; optimal for personal-task parallelism (SemaClaw's target) but mismatched for coding workflows that are often linear.
- *Single-agent only.* Loses the verifier + planner benefits entirely.

**Why chosen.** "[Don't Build Multi-Agents](../../../docs/50-dont-build-multi-agents.md)" essay applies when orchestration has no clear motivation. We pick multi-agent only when the motivation is explicit (long plan, parallel-friendly task graph, high safety requirement).

**Cost.** Config surface to learn (three plugins); heuristics for auto-routing may mis-classify; user-education burden.

**Mitigation.** `lyra doctor` explains current plugin selection and why. `--harness` explicit flag is always available. Benchmarks publish per-plugin cost/quality curves.

### A.4. PermissionBridge as runtime primitive — prompt-level permission → rejected

**Decision.** Every tool invocation flows through `permissions/bridge.py`. Decisions are `allow` / `ask` / `deny` / `park`. LLM cannot bypass; it can only *request* a mode change which is a user-approved event.

**Rejected alternatives.**

- *LLM-driven permission* ("the model decides if this is dangerous"). Leak-prone; prompt injection can override.
- *Binary sandbox / no sandbox.* Either too restrictive (every action needs a container) or too open.
- *Mode-only, no classifier.* Misses edge cases where the mode is `default` but the specific operation is actually risky (e.g. `rm -rf` inside a legitimate `acceptEdits` session).

**Why chosen.** The SemaClaw paper's load-bearing insight: behavioral safety as a runtime primitive. The LLM never holds the keys.

**Cost.** Extra median ~2ms per tool call for classifier + rule lookup. `park` state requires the DAG scheduler to handle out-of-order completion, which adds complexity.

**Mitigation.** Classifier is a small sklearn model (~2MB) + cached rules. Policy file is YAML, user-editable. Policy evaluator is deterministic and unit-tested (property tests).

### A.5. SOUL.md never-compacted — full compaction → rejected

**Decision.** `SOUL.md` lives in the cached-mid context tier and is never subject to auto-compaction. Size cap enforced (~2KB default).

**Rejected alternatives.**

- *Treat SOUL as regular memory.* Risk of identity drift during long sessions — documented failure of earlier frameworks.
- *SOUL is dynamic.* Persona keeps changing; user trust collapses.
- *No persona at all.* Every turn, the agent reinvents its own behavioral contract; anti-pattern.

**Why chosen.** SemaClaw documents persona drift as the dominant long-session failure. A never-compacted partition is the cheapest fix and it's human-editable, which is a feature.

**Cost.** Always-loaded bytes eat context budget (mitigated by the size cap). User may want to version SOUL.md changes (supported via `lyra soul edit --versioned`).

**Mitigation.** Size cap + warning if SOUL grows too large. The file is user-owned; the agent does not write to it without explicit user command.

### A.6. Three-tier memory with SQLite FTS5 + Chroma — vector-only → rejected

**Decision.** Keyword (SQLite FTS5) and semantic (Chroma) stores work in parallel; queries fan out, results merged. Three tiers: procedural (skills), episodic (traces/observations), semantic (facts/wiki).

**Rejected alternatives.**

- *Vector-only.* Misses exact-match lookups ("that error I saw on Tuesday"); semantic search is fuzzy.
- *Keyword-only.* Misses paraphrased / multilingual queries.
- *Graph DB.* Too heavy for single-developer deployment; higher ops.
- *Single tier.* Blurs procedural (how-to) with semantic (what-is). Retrieval quality degrades.

**Why chosen.** [`claude-mem` doc 72](../../../docs/72-claude-mem-persistent-memory-compression.md) reports that hybrid retrieval materially improves recall vs either store alone. 3-tier taxonomy aligns with cognitive science (procedural, episodic, semantic memory) and matches the Hermes 3-layer design.

**Cost.** Two index stores to maintain; write amplification on every observation (both indexes updated). Deployment dependencies (Chroma requires an embedding model).

**Mitigation.** Both indexes are local SQLite files + Chroma on-disk (no separate server). Embedding model is a small local model (e.g. BGE-small) by default; can upgrade to cloud embeddings if user opts in.

### A.7. Worktree-isolated subagents — shared filesystem → rejected

**Decision.** Each concurrent subagent gets its own git worktree on a session branch. Shared fs access is read-only for subagents.

**Rejected alternatives.**

- *Shared fs + file locks.* Fine on trivial tasks; breaks on semantic conflicts (two subagents legitimately edit the same region).
- *Purely linear subagents.* Loses the parallelism benefit entirely.
- *Separate repos / containers per subagent.* Higher isolation; too heavy, loses cross-subagent context.

**Why chosen.** Git has solved this — use it. Worktree is cheap, merge is explicit, conflict surface is a first-class artifact.

**Cost.** Disk overhead (one copy of the index per worktree, ~100MB per typical repo). Conflict merges sometimes require human resolution.

**Mitigation.** Shallow clone for worktrees. Merge strategy defaults to fast-forward; on conflict, summary + pointer to manual resolution; after max-retry of auto-resolve, surface to user.

### A.8. Different-family evaluator — same-family only → degraded mode

**Decision.** Default evaluator model is a different family from the generator. We ship configs for (Anthropic Sonnet generator + OpenAI GPT-5 evaluator + GPT-5-nano safety monitor). Same-family fallback emits `degraded_eval=same_family` tag.

**Rejected alternatives.**

- *Same-family always.* CRITIC (arXiv:2305.11738) and Self-Refine research show substantially higher miss rates on shared blind spots.
- *Ensemble of three families.* Cost explosion on every verification.
- *Human-only evaluation.* Does not scale.

**Why chosen.** Cheap way to break shared-blind-spot miss rate. The operational overhead (two API vendors) is real but manageable.

**Cost.** Two vendor relationships, two API keys, two cost budgets. Pricing may diverge. Latency may be higher than single-family because the evaluator model is not locally cached-prefixed.

**Mitigation.** Model router abstracts vendor. Config can point both roles to the same vendor for small repos / budget users with the warning tag. Cost monitor alerts when evaluator cost ratio exceeds generator by more than 2×.

### A.9. Cross-channel verification — trace-only → rejected

**Decision.** A task is marked `complete` only when trace + git diff + environment snapshot agree.

**Rejected alternatives.**

- *Trace-only.* Self-reports are exactly the wrong channel to trust when sabotage is a concern.
- *Diff-only.* Misses side effects outside the tracked repo (DB state, untracked files).
- *Snapshot-only.* Loses the narrative ("why" this change).

**Why chosen.** [Claw-Eval (doc 38)](../../../docs/38-claw-eval.md) reports 44% more safety violations caught by cross-channel agreement. The cost is small (snapshot is O(files-touched), not O(repo-size) with incremental filesystem tracking).

**Cost.** Snapshot mechanism adds dependency (fanotify on Linux, fsevents on macOS) or falls back to filesystem polling. Environment snapshot for DB tests requires DB plugin.

**Mitigation.** Snapshot defaults to incremental; cost scales with touched-file count. Full snapshot is opt-in for high-assurance workflows.

### A.10. MIT license — AGPL → rejected for this project

**Decision.** MIT.

**Rejected alternatives.**

- *AGPL-3.0.* Protects against hosted-SaaS closed-source forks (the [claude-mem choice](../../../docs/72-claude-mem-persistent-memory-compression.md)) but blocks many commercial adoptions.
- *BUSL-1.1.* Commercial restriction for 4 years, converts to MIT after. Growing in popularity; user-hostile initially.
- *GPLv3.* Strict copyleft; incompatible with MIT-licensed dependencies like `harness_core` sibling.

**Why chosen.** Maximum adoption, consistent with [orion-code](../../orion-code/) sibling and [gstack](https://github.com/garrytan/gstack). Coding tools benefit disproportionately from wide adoption and contribution flow; AGPL tax isn't worth it.

**Cost.** Vendors can fork and sell hosted Lyra; no reciprocation required. This is a deliberate trade.

**Mitigation.** The product moat is trace-compatibility with Gnomon + skill library quality + TDD gate maturity, not the code itself.

---

## B. Local decisions

### B.1. Typer CLI — Click / argparse → rejected

Typer gives type-driven CLI definition, matches Pydantic models for config, and ships with rich completions. Click is more powerful but more boilerplate; argparse is stdlib-only but lacks ergonomics. Cost: one extra dependency.

### B.2. Pydantic for all schemas — dataclasses + jsonschema → rejected

Pydantic gives us: validation, serialization, OpenAPI-compatible JSON schema for tool definitions, MCP-compatible argument schemas. Dataclasses need hand-rolled validators. Cost: Pydantic v2 learning curve.

### B.3. Typed native tools for core ops; MCP for everything else — MCP-only → rejected

MCP hop adds 10-50ms per call and complicates debugging. Core ops (Read / Grep / Edit / Write / Bash) stay native typed. External integrations (Slack, Jira, custom DB) via MCP. Cost: two codepaths to maintain; mitigated by shared `Tool` ABC.

### B.4. STATE.md (human-readable Markdown) — binary state blob → rejected

STATE.md is human-readable, greppable, git-friendly, and editable mid-run. Binary blobs are faster to load but opaque at crash time. Cost: some information loss (tool call arguments older than N turns). Mitigated by append-only `recent.jsonl`.

### B.5. OTel + JSONL trace — structured logs only → rejected

OTel spans give distributed-trace semantics, which line up with subagent / MCP / LLM-call boundaries. JSONL trace is the append-only ledger that Gnomon HAFC consumes. Cost: two emission paths (span API + JSONL); shared tracer reconciles.

### B.6. Web viewer on :47777 — TUI only → rejected

The TUI (rich) works for interactive CLI; web viewer is better for trace inspection, cost breakdown, skill library browse. Cost: one more service to run. Mitigated by `lyra daemon` lifecycle command (start / stop / status) and lazy-start on first open.

### B.7. Hermes skill extractor — Voyager-style skill writing in prompt → different trade

Voyager's approach emits skills as a side-channel output during the task. Hermes separates skill extraction into a post-task step with success/partial/fail feedback. We adopt Hermes because (a) skills only written on actual success are higher-quality, (b) refinement via outcome signal avoids rot. Cost: extra post-task LLM call.

### B.8. Claude Code–compatible skill format — custom format → rejected

`SKILL.md` with YAML frontmatter (name, description, allowed-tools) matches Claude Code, Multica, gstack. Users can bring skills from those systems. Cost: constraint on internal skill metadata; mitigated by opting-in fields.

### B.9. Three harness plugins (single / three / dag) — N plugins → deferred

Keep the public plugin surface to three in v1. Internal experimentation may add more (e.g. "teacher-student" from [doc 26](../../../docs/26-agent-supervisor-pattern.md)) but they stay behind a flag. Cost: advanced users will want more; provide plugin SDK in v2.

### B.10. Safety monitor as separate concern — inside the loop → rejected

Safety monitor runs on the full trace every N steps, not as part of the agent's own tool-decision. This mirrors [Orion-Code block 07](../../orion-code/docs/blocks/07-verifier-evaluator.md#safety-monitor-separate-concern-runs-continuously). Cost: extra model (tiny, `gpt-5-nano` class). Mitigated by infrequent cadence (default every 5 steps).

### B.11. Ship 5 atomic skills + 7-phase sprint pack — curated 23 specialists → deferred

v1 ships the [Atomic-Skills basis-vectors](../../../docs/68-atomic-skills-scaling-coding-agents.md) + the 7 sprint-phase skills (inspired by [gstack](../../../docs/75-gstack-garry-tan-claude-code-setup.md)). 23 specialists (gstack's full set) is opt-in plugin. Cost: users who love specialists miss them initially; plugin registry mitigates.

### B.12. Continuous git checkpoint — end-of-task only → rejected

Every plan-item completion = git commit on session branch (gstack pattern). Makes rollback trivial (`git reset --hard <item-hash>`) and enables per-step trace/diff alignment. Cost: commit noise on the session branch; squashed at PR time.

### B.13. Two-phase TDD hook vs single-phase — single phase lacks granularity

Two phases (RED proof on PreToolUse, GREEN proof on PostToolUse/Stop) distinguish "intent to change" from "change succeeded". Single phase would collapse failure modes.

### B.14. Node.js test runner via subprocess, not Node.js-in-process — embedded runners → rejected for v1

Reduces coupling; v1 spawns vitest/jest/`go test` as subprocesses. v2 may embed via IPC if latency demands it.

### B.15. Embed claude-mem pattern, don't vendor — vendor claude-mem → rejected

`claude-mem` is a separate project with its own lifecycle. Lyra implements its own memory layer following the same 3-tier + progressive-disclosure pattern but tuned for coding. Avoids coupling our release cadence to theirs; keeps MCP server compatibility so users of `claude-mem` can point it at Lyra traces.

### B.16. Injection guard = ML + LLM + canary — pure LLM vote → rejected

Pure LLM vote is slow and expensive. ML classifier (cheap, offline-trainable) front-runs to catch obvious cases; LLM vote + canary is the backstop for subtle cases. Cost: 22MB classifier dependency; mitigated by default-on cache.

### B.17. No multi-host agent CLI adapter layer in v1 — ship only Lyra CLI → yes

Multica-style 8-CLI adapter is too much surface for v1. We ship the installer script that wires our skills + SOUL.md into other CLIs (Claude / Gemini / Cursor) but we don't orchestrate other CLIs at runtime. v2 explores this via a proper adapter layer.

### B.18. No own model training — plans for Atomic-Skills-style RL → v2

API-first. Joint RL over 5 atomic skills (arXiv:2604.05013) is a v2 exploration contingent on maintained fine-tuning APIs + open-weight candidates.

### B.19. Scheduler is Hermes-style cron, not full workflow engine — Airflow/Dagster → rejected

Airflow is too heavy for single-user. Hermes's cron scheduler is small, easy to reason about, and matches the "skill can be scheduled" contract. Cost: some workflow patterns (backfills, DAG-of-schedules) not supported in v1.

### B.20. Bash sandboxing opt-in v1; default v2

Rootless Podman / Docker containerized runner for Bash is opt-in v1 (via `--sandbox` flag) because it adds dependency. v2 will default-on on Linux/macOS where rootless containers are available.

---

## C. Patterns we explicitly rejected

### C.1. Monolithic system prompt

Trying to jam skill discovery, permissions, persona, and plan into a single mega-prompt. Rejected because it defeats progressive disclosure and forces everything into context.

### C.2. LLM-as-permission-oracle

Having the LLM decide what is safe. Rejected because prompt injection makes the oracle unreliable.

### C.3. Fully asynchronous subagents without a coordinator

Subagents fire-and-forget with no cross-talk coordinator. Rejected because of result-chaos and lack of conflict handling.

### C.4. Skill marketplace with payments in v1

Out of scope. We support community skills via GitHub repos + `lyra skills install <uri>`; no payment, no curation fees.

### C.5. Graph-based agent framework (LangGraph replacement)

Lyra is *not* a generic agent framework. DAG Teams plugin is specific to coding workflows. If users want a generic graph orchestrator they should use LangGraph or our sibling [syndicate](../../syndicate/).

### C.6. Full autonomous CI agent

We deliberately stop short of "agent opens PRs by itself on its own backlog." Human intent starts each task. Pure-autonomous mode is explored in [mentat-learn](../../mentat-learn/), not here.

### C.7. Prompt caching leaked across sessions

Prompt caches are per-session. Cross-session reuse is tempting (cost savings!) but leaks context between unrelated tasks and violates auditability. Rejected.

### C.8. RL at the harness level in v1

Joint RL over atomic skills is powerful (Atomic-Skills paper); we defer to v2. v1 is API-first deterministic harness.

### C.9. Single-family evaluation

Same-family evaluator is a known miss-rate liability. We keep a warning tag even for fallback.

### C.10. Implicit state

Everything the harness relies on is either a file the user can read or a span in the trace. No hidden state, no daemon-only state that the user cannot inspect. This is Pillar 1 (state management) from [Four Pillars](../../../docs/44-four-pillars-harness-engineering.md).

---

## D. Known honest risks

1. **TDD gate false positives** on legacy codebases without tests will frustrate users initially. Mitigation: `lyra doctor` flags lack of baseline tests and suggests `lyra init-tests` scaffolding.
2. **Prompt-injection ML classifier drift.** Attackers iterate; our classifier is static between updates. Mitigation: scheduled updates + LLM-vote fallback + canary.
3. **Model version churn.** Anthropic, OpenAI ship new model generations regularly; cache-prefix layout may need adjustment. Mitigation: version pins in config + CI regression suite.
4. **Skill library growth.** Left unpruned, skill count goes to the hundreds in months. Self-eval every 15 tasks prunes; if disabled, library becomes noise. Monitor skill cardinality as an SLO.
5. **DAG Teams plugin in coding domain.** Not yet widely validated in coding workflows (SemaClaw was personal-task). Ship behind explicit flag until corpus of positive outcomes builds.
6. **HIR schema churn.** Gnomon HIR may evolve; we track and provide migration scripts. We emit a schema version tag on every trace.
7. **Cross-channel false negatives.** Agreement can mask coordinated manipulation if all three channels are attacker-influenced. This is a theoretical weakness; safety monitor is the backstop.
8. **Cost attribution accuracy.** Feature-level cost requires tagging, which requires structured tasks. Legacy "do X and Y" tasks may have poor attribution. Mitigation: planner assigns feature IDs; user can adjust.
