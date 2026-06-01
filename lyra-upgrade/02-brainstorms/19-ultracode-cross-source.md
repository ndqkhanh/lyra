# Cross-Source Brainstorm: Ultracode Deep Combinations

**Workstream**: Ultracode Replication (§3.1, §3.12, §4.5, §4.13, §4.14, §4.15)
**Date**: 2026-05-31 (Run 16)
**Sources fused**: Claude Code Dynamic Workflows (official docs), SABER (#67), AutoScientists (#154-156), IterResearch (#272), DecentMem (#99), RouteLLM (#222-223), BEST-Route (#225), Knowledge Access Beats Model Size (#227), MemGrad (#70), AOI (#68)

---

## Idea 1: Provider-Diverse Adversarial Workflow Engine (PDAWE)

### Sources Fused
Claude Code Dynamic Workflows (workflow.js runtime model) + SABER (mutation-gating) + RouteLLM (matrix factorization routing) + DecentMem (dual-pool shared memory)

### Mechanism (Step by Step)

**Phase 0: Effort → Orchestration Bridge**
1. User sets `/effort ultracode` → `EffortManager.map_effort()` resolves to `xhigh` budget (16384 tokens) + `orchestration_enabled=True`
2. For non-Anthropic providers (DeepSeek, open-weights): `thinking_instruction` string is injected into system prompt instead of native `budget_tokens`
3. The `OrchestrationConfig.auto_trigger_threshold` ("medium" by default) gates whether a task auto-triggers a workflow

**Phase 1: Complexity Estimation → Workflow Decision**
4. `estimateComplexity(prompt)` runs a fast regex + keyword heuristic:
   - Counts action verbs ("audit", "migrate", "refactor", "implement", "research")
   - Counts scope indicators ("entire", "all", "every", "comprehensive")
   - Counts domain indicators (file paths, module names, API references)
   - Output: `trivial | low | medium | high`
5. If `complexity >= auto_trigger_threshold`: spawn workflow script generation
6. Otherwise: proceed as normal turn-by-turn conversation

**Phase 2: Cross-Provider Script Generation**
7. Route script generation to strongest available model via `ModelRouter.route(task, effort_level="xhigh")`
8. The LLM writes a JavaScript workflow script using the Lyra workflow API (mirrors Claude Code's `agent()`, `parallel()`, `pipeline()`, `phase()`)
9. `ScriptVM.staticAnalyze()` validates the script (denied globals, denied modules)
10. If validation passes → execute; if fails → regenerate with error feedback

**Phase 3: Provider-Aware Task Distribution**
11. `WorkflowEngine._execute()` dispatches tasks in batches of `MAX_CONCURRENT` (16)
12. Each task's `model` field determines which provider executes it:
    - `model: "deepseek-flash"` → bulk discovery, cheap ($0.27/MTok input)
    - `model: "claude-sonnet"` → verification, reliable
    - `model: "claude-opus"` → synthesis, deepest reasoning
13. RouteLLM's matrix factorization runs ONCE per workflow to learn the best (task_type, model) mapping
14. BEST-Route's multi-sampling: for high-variance stages, generate 3 responses from cheap model, pick best via verifier

**Phase 4: SABER-Enhanced Adversarial Verification**
15. `MutationGate.classify(action)` determines if an action is mutating or non-mutating
16. Non-mutating actions (reads, searches, lists) skip verification → execute immediately
17. Mutating actions (writes, deletes, executes) trigger 3-critic panel
18. Each critic uses a DIFFERENT provider (maximizing architectural diversity):
    - Critic A (Anthropic Claude): refutation lens — "try to prove this wrong"
    - Critic B (DeepSeek): consistency lens — "does this contradict other findings?"
    - Critic C (OpenAI/Google): evidence lens — "grade the evidence quality"
19. `DecisionMatrix.resolve()`: ≥2 ACCEPT → pass; ≥2 REJECT → block; 1-1-1 → escalate
20. Cross-model correlation is ~14.6× worse than same-model for error detection → diverse critics catch errors homogeneous critics miss

**Phase 5: DecentMem Shared Context**
21. Each agent writes findings to its private memory pool (per-agent)
22. A shared memory pool accumulates cross-agent insights (O(log T) regret bound)
23. The shared pool is periodically compressed (AOI 72.4% compression) and promoted to episodic memory
24. Between workflow phases, the synthesizer reads the shared pool to avoid redundant work

**Phase 6: Pause/Resume with State Serialization**
25. `PauseResumeSerializer.serialize()` snapshots all agent states, phase progress, intermediate results
26. On resume, completed agents return cached results; queued/running agents are requeued
27. Works within the same session (matches Claude Code constraint)

### Why It Beats Individual Sources

| Source Alone | Limitation | PDAWE Fix |
|-------------|-----------|-----------|
| Claude Code Workflows | Anthropic-only, no cross-provider critic diversity | Routes each stage to optimal provider; 3 critics from different providers |
| SABER | Single-provider verification, no workflow orchestration | Cross-provider critics + workflow engine integration |
| RouteLLM | Per-query routing, no workflow awareness | Per-stage routing within workflow phases |
| DecentMem | Untested beyond 3 MAS frameworks | Integrated as shared memory layer in multi-phase workflows |

### Trade-Off Analysis

| Dimension | Gain | Cost | When It Wins | When It Loses |
|-----------|------|------|-------------|---------------|
| **Latency** | Parallel execution of 16 agents reduces wall-clock time | 3-critic verification adds 1-3s per mutating action (3 LLM calls) | Tasks with many independent sub-tasks (audits, migrations) | Tasks with sequential dependencies (each step depends on prior) |
| **Memory** | Intermediate results in script variables, not context window | Shared memory pool grows with agent count (O(n) storage) | Long workflows with many agents (100+) | Short workflows with few agents (<10) — overhead dominates |
| **Tokens** | 60-85% cost reduction via cheap-model bulk work + selective verification | Script generation costs ~2000 tokens; verification costs ~500-2000 tokens per action | Workflows with >10 agents where bulk work dominates | Simple tasks where workflow overhead > direct execution cost |
| **Accuracy** | Cross-model verification catches errors same-model misses (~14.6× better) | 3-critic consensus can deadlock (1-1-1 split → escalate to user) | Tasks where errors are costly (security audits, production changes) | Tasks with low error cost (exploratory research, drafts) |
| **Complexity** | Unified engine handles all orchestration patterns | Integration of 4 independent systems (workflow + SABER + RouteLLM + DecentMem) | Production systems where reliability matters | Prototypes where simplicity matters more |
| **Failure Modes** | — | Admission queue deadlock (Run 14 CRITICAL-1); critic unavailability (provider outage); script generation failure (malformed JS) | — | — |
| **Multi-Provider** | Works across Anthropic, DeepSeek, OpenAI, Google, open-weights | Each provider has different verification quality; DeepSeek critics are less reliable than Claude critics | Heterogeneous deployments with multiple API keys | Single-provider deployments (overhead without diversity benefit) |

### Design Rationale
The key insight is that Claude Code's workflow engine is the RIGHT architecture but WRONG provider assumption. Claude Code assumes Anthropic-only. Lyra's breakthrough is making the workflow engine provider-aware: bulk work on cheap providers, verification on diverse providers, synthesis on the strongest provider. This is architecturally impossible in Claude Code but natural in Lyra's provider abstraction.

---

## Idea 2: Memory-Augmented Workflow Cascades (MAWC)

### Sources Fused
Knowledge Access Beats Model Size (#227) + IterResearch (#272) + MemGrad (#70) + AOI (#68)

### Mechanism (Step by Step)

1. Before routing any workflow task, query the TKG: "Has this task (or a similar one) been done before?"
2. If YES (cosine similarity > 0.85 to a prior memory):
   - Retrieve the prior workflow script, agent outputs, and verification results
   - Route to CHEAP model (DeepSeek Flash, $0.27/MTok) with retrieved context
   - Only verify DIFFERENCES from prior execution
   - Expected: 90%+ token reduction for repeat tasks
3. If NO (novel task):
   - Route to STRONG model (Claude Opus/Sonnet) for first execution
   - Full verification pipeline
   - Store execution trace + verification results in TKG
4. IterResearch-style periodic synthesis:
   - Every N workflow phases, pause and synthesize insights
   - Compress phase outputs into structured memory nodes
   - Prevents context suffocation in long workflows
5. MemGrad feedback loop:
   - After workflow completion, generate textual gradient from outcomes
   - Update memory retrieval weights based on what proved useful
   - Retrospective: "What memory would have helped?" → create it
   - Prospective: "What will help next time?" → pre-compute it

### Trade-Off Analysis

| Dimension | Gain | Cost | When It Wins | When It Loses |
|-----------|------|------|-------------|---------------|
| **Tokens** | 90%+ reduction for repeat tasks (cache hit on prior execution) | TKG query costs ~100 tokens per task lookup | Repeated workflows (CI/CD, recurring audits, code review on every PR) | One-off tasks (TKG query is pure overhead) |
| **Latency** | Fast-path retrieval (<50ms) for cached results | TKG write adds ~500ms-2s per novel task (A-MAC admission) | Tasks where prior execution exists in memory | First-time tasks (no cache benefit, pay write cost) |
| **Accuracy** | Prior execution context improves consistency across runs | Stale memories can mislead (if codebase changed since last run) | Stable codebases with incremental changes | Rapidly changing codebases (memories stale quickly) |
| **Complexity** | Compound benefit: memory + routing > either alone | Must maintain TKG freshness and detect staleness | Production systems with history | Greenfield projects (no history to leverage) |

---

## Idea 3: AutoScientists-Inspired Self-Organizing Research Swarms (AS-SORS)

### Sources Fused
AutoScientists (#154-156) + IterResearch (#272) + SABER (#67) + DecentMem (#99)

### Mechanism (Step by Step)

1. **Hypothesis Generation Phase**: N agents independently generate research hypotheses from the task description
2. **Critique-Before-Spend Gate**: Each hypothesis is adversarially critiqued by 3 other agents (different providers)
3. Only hypotheses surviving ≥2/3 critic approval are allocated execution budget
4. **Execution Phase**: Approved hypotheses are tested in parallel (up to 16 concurrent)
5. **Shared Success/Failure Log** (DecentMem shared pool): All results are logged with evidence
6. **Dynamic Reallocation**: Agents self-organize around promising leads — agents abandon failing hypotheses and join successful ones
7. **Periodic Synthesis** (IterResearch pattern): Every K execution rounds, synthesize findings into an evolving report
8. **Termination**: When no new hypotheses are proposed OR budget exhausted → final report synthesis

### Trade-Off Analysis

| Dimension | Gain | Cost | When It Wins | When It Loses |
|-----------|------|------|-------------|---------------|
| **Accuracy** | Self-organizing around evidence avoids dead ends; >50% reduction in wasted work | Critique phase costs tokens even for rejected hypotheses | Open-ended research with uncertain answer (scientific discovery) | Well-defined tasks with known solution path (standard coding) |
| **Tokens** | Critique-before-spend prevents expensive execution of bad ideas | Each hypothesis costs 3 critic calls (~1500-6000 tokens) even if rejected | Tasks where execution is expensive (experiments, data processing) | Tasks where execution is cheap (text generation) |
| **Latency** | Parallel hypothesis testing reduces wall-clock time | Critique phase is sequential (must happen before execution) | Multi-hypothesis problems with independent tests | Single-hypothesis problems (critique is pure overhead) |

---

## Idea 4: Loop-Until-Dry with Cross-Model Verification (LUD-CMV)

### Sources Fused
Claude Code Workflows (loop-until-dry pattern) + SABER (mutation-gating) + AutoScientists (shared success/failure log) + RouteLLM (per-iteration model selection)

### Mechanism (Step by Step)

1. Configure: `target_coverage = 0.95` (95% of findings must survive verification), `max_rounds = 10`, `dry_rounds_for_convergence = 2`
2. **Round 1 — Find**: N finder agents (8-16) independently search for issues/findings from different angles
3. **Dedup**: Deduplicate findings across all finders by (file, line, category) tuple
4. **Verify**: Each unique finding is verified by 3 cross-provider critics
5. **Convergence Check**: Count findings surviving verification in this round
6. If `new_surviving_findings == 0` → increment `dry_rounds`
7. If `dry_rounds >= dry_rounds_for_convergence` → CONVERGED, report all verified findings
8. If `round >= max_rounds` → MAX ROUNDS, report with coverage caveat
9. **Else**: Feed surviving findings back to finders as context ("these are already found, find different ones") → Round N+1
10. **Model selection per round**: Early rounds use cheap models (wide exploration), later rounds use strong models (deep verification of remaining gaps)

### Trade-Off Analysis

| Dimension | Gain | Cost | When It Wins | When It Loses |
|-----------|------|------|-------------|---------------|
| **Coverage** | Converges on exhaustive coverage (no new findings after K dry rounds) | May never converge on unbounded problems | Bounded search spaces (codebase audit, API surface review) | Unbounded search spaces (open-ended research) |
| **Tokens** | Adaptive model selection reduces per-round cost | Each round costs N finders + M verifications | Large search spaces where coverage matters | Small search spaces (single-file review — one round sufficient) |
| **Latency** | Early termination when converged | Worst case: max_rounds × (finder_time + verifier_time) | Problems with finite finding surface | Problems where findings are inexhaustible |

---

## Comparative Assessment

| Idea | Impact | Effort | Novelty | Risk | Recommended For |
|------|--------|--------|---------|------|-----------------|
| PDAWE (Provider-Diverse AVP Workflows) | 5 | 3 | 4 | MEDIUM | **(B) Breakthrough** — Core ultracode engine |
| MAWC (Memory-Augmented Cascades) | 4 | 4 | 3 | MEDIUM | **(A) Parity+** — Router ↔ Memory bridge |
| AS-SORS (Self-Organizing Research) | 5 | 5 | 5 | HIGH | **(B) Breakthrough** — Deep research workstream |
| LUD-CMV (Loop-Until-Dry Verification) | 4 | 3 | 3 | LOW | **(A) Parity** — Quality pattern |

### Expert Sign-Off

**Senior AI Engineer (LLMOps)**: "PDAWE's cross-provider critic diversity is the strongest idea here. The 14.6× error-detection multiplier from architectural diversity is defensible from the RouteLLM paper's transfer-learning results. But the latency model needs validation: 3 parallel critic calls to different providers will be gated by the SLOWEST provider. If DeepSeek is throttled, verification latency spikes. **Recommendation**: Add a critic timeout (5s default) with graceful degradation to 2-critic panel if one provider is slow."

**Senior Architect**: "MAWC's memory-augmented cascades correctly identify that the router↔memory bridge is the compound win. But the staleness detection is underspecified. A memory from 3 months ago about 'the auth module' may be dangerously stale if the module was refactored. **Recommendation**: Add git-based staleness detection — tie memory validity to the git commit hash of the files it references."

**Senior SRE**: "LUD-CMV's convergence guarantee is appealing but the `dry_rounds_for_convergence=2` parameter is arbitrary. Two dry rounds on a 100K-line codebase may mean 'we stopped finding bugs because we're looking in the wrong places,' not because there are no bugs left. **Recommendation**: Add diversity check — if finders in round N all searched the same files, force diversification before declaring convergence."

**Senior Security**: "AS-SORS's critique-before-spend gate is the right safety pattern. But AutoScientists was designed for scientific hypothesis testing, not code modification. A 'promising lead' in code modification could be a destructive refactor. **Recommendation**: Add SABER mutation-gating BEFORE hypothesis execution — if a hypothesis involves mutating actions, require 3/3 critic approval (not just 2/3)."

---

## Changelog

| Run | Date | Changes |
|-----|------|---------|
| 16 | 2026-05-31 | Initial brainstorm — 4 cross-source combinations with mechanism-level detail and trade-off analysis |
