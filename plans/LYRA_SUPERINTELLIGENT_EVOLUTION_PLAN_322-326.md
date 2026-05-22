# Lyra Super-Intelligent Self-Rewriting Agent: 5-Phase Evolution Plan
## Grounded in Research Docs 322–326

**Goal:** Lyra becomes a personal super-intelligent AI agent that rewrites its own code to grow
and evolve over time — observable, intelligently routed, multi-hop reasoning, fleet-managed,
and closed-loop controlled.

**Research Foundation:** Deep synthesis of 5 new documents:
- `322` Agent Split View Monitoring 2026
- `323` Agent Model Routing 2026
- `324` Multi-hop Reasoning Agents 2026
- `325` Agent View for AI Agents 2026
- `326` Closed-loop Agent Control 2026

**Current Lyra State (v3.14.0):**
- 8 packages: lyra-cli, lyra-core, lyra-research, lyra-skills, lyra-memory, lyra-evals,
  lyra-mcp, lyra-evolution
- 2200+ tests, 80+ slash commands, 16 LLM providers
- 2-tier model split (fast/smart), subagent git-worktree isolation
- 8-phase deep research pipeline (phases 1-8 implemented in lyra-research)
- Existing 8-phase evolution plan (docs 313-321) in LYRA_EVOLUTION_MASTER_PLAN.md

**Relationship to Existing Plan:** This plan is **additive** — it injects 5 new architectural
layers (A–E) into the existing 8-phase structure, upgrading each phase with the new
capabilities from docs 322–326.

**Date:** 2026-05-14
**Status:** Master Plan — Approved for Implementation

---

## Executive Summary

The 5 research documents form a unified capability stack that closes the loop on
self-improvement:

```
322 (Observability)   → You can only improve what you can observe
323 (Model Routing)   → Efficient evolution requires smart routing decisions
324 (Multi-hop)       → Deep reasoning over chains in Lyra's own codebase
325 (Agent View)      → Manage parallel self-improvement sub-agents as a fleet
326 (Closed-loop)     → Close the feedback loop on self-modification itself
```

Together they transform Lyra from a capable research CLI into an agent that:
1. **Watches itself** through an operator cockpit during every run
2. **Routes decisions** intelligently across fast/reasoning/advisor tiers
3. **Reasons multi-hop** over its own code, docs, and research library
4. **Supervises parallel evolution agents** with attention-triage fleet view
5. **Self-modifies** under verified closed-loop control with rollback

---

## Phase A: Observable Self — The Execution Record Engine
**Timeline:** Weeks 1–4 (builds on existing Phase 7: Evaluation & Telemetry)
**Research Foundation:** Doc 322 (Agent Split View Monitoring)

### A.1 What This Phase Adds

The existing telemetry in lyra-evals tracks quality metrics. This phase adds a **real-time
operator cockpit** during every run — answering "what is Lyra doing RIGHT NOW and why?" instead
of "what happened in this trace?"

The key primitive is the **Agent Execution Record (AER)** — every Lyra turn becomes a
queryable record with intent, observation, inference, evidence chains, and confidence scores
(from arXiv:2603.21692).

### A.2 The Four-Layer Monitoring Stack

```
L4  Operator UX (TUI split-view cockpit, SLO cards, anomaly panels, approval gates)
L3  Semantic execution record (AER: intent, observation, inference, evidence, confidence)
L2  Telemetry wire format (OpenTelemetry GenAI spans/events/metrics, MCP conventions)
L1  Local runtime substrate (processes, ports, files, git state, context window %)
L0  Lyra agent workload (research, coding, self-evolution sub-tasks)
```

### A.3 Agent Execution Record (AER) Schema

Every Lyra turn emits an AER that goes into `lyra-evals` and the new `lyra-monitor` module:

```python
@dataclass
class AgentExecutionRecord:
    # Identity
    run_id: str
    session_id: str
    turn_index: int
    trace_id: str               # links to OTel span

    # Semantic state (AER core — arXiv:2603.21692)
    intent: str                 # what Lyra is trying to do
    observation: str            # what it observed from tools/env
    inference: str              # what it concluded
    evidence_refs: List[str]    # citation/source IDs supporting the inference
    confidence: float           # 0.0–1.0
    revision_rationale: str     # why plan changed (if it did)

    # Tool state
    tool_name: Optional[str]
    tool_args_hash: str
    tool_result_hash: str
    tool_duration_ms: int
    tool_cost_usd: float

    # Local runtime (abtop-inspired)
    context_window_pct: float   # % of context window used
    tokens_input: int
    tokens_output: int
    child_pids: List[int]
    open_ports: List[int]
    git_ref: str
    git_dirty: bool

    # Model routing (links to Phase B)
    model_tier: Literal["fast", "reasoning", "advisor"]
    route_reason: str
    escalation_trigger: Optional[str]

    # Safety
    permission_decision: Optional[str]
    policy_gate: Optional[str]

    # Eval
    verifier_verdict: Optional[str]
    eval_link: Optional[str]
```

**File:** `packages/lyra-evals/src/lyra_evals/aer.py`

### A.4 What to Monitor

| Signal Family | Concrete Signals | Failure Detected |
|---|---|---|
| Session fleet | active sessions, runtime, project, current task | abandoned / duplicated agents |
| Token/context | input/output tokens, context window %, compaction events | context cliff and memory loss |
| Tool execution | tool name, args, duration, result, error | tool-loop failures and bad actions |
| Memory | read/write/evict events, memory tier | stale or poisoned memory |
| Subagents | spawn, delegation, authority, message flow | orphaned or conflicting agents |
| OS side effects | child processes, open ports, file handles | orphan servers and leaked resources |
| Workspace state | git diff/status, file attention | silent mutation risk |
| Safety | permission decisions, policy gates, escalations | harmful or unauthorized actions |
| Eval/SLO | eval link, judge verdict, SLO breach | production quality regression |

### A.5 TUI Split-View Cockpit

New TUI panel accessible via `/monitor` command:

```
┌─ Lyra Monitor ─────────────────────────────────────────────────────────────┐
│  Session: lyra-3.14 │ Turn: 47 │ Model: smart │ Context: 42% │ $0.023    │
├─ Process Table ─────┬─ AER Record ──────────────────────────────────────── │
│ PID   NAME    %CPU  │ Intent:    synthesize findings across 12 papers       │
│ 12345 lyra     2.1  │ Inference: 3 methods conflict on benchmark X         │
│ 12346 research 0.8  │ Evidence:  [paper:2603.21692] [repo:graphrag]        │
│ Ports: 8080, 5000   │ Confidence: 0.76                                     │
│ Git:   2 dirty      │ Route:     reasoning (evidence_conflict)             │
├─ SLO Dashboard ─────┴───────────────────────────────────────────────────── │
│ Cost: $0.023/turn ✓  │ Latency: 1.4s ✓ │ Context: 42% ✓ │ Safety: OK ✓  │
└───────────────────────────────────────────────────────────────────────────┘
```

**Views:**
- **Process table** — active Lyra processes, ports, child PIDs (abtop-inspired)
- **AER record** — intent/observation/inference/evidence for current turn
- **SLO dashboard** — cost, latency, context %, quality gates

### A.6 OpenTelemetry Integration

Every AER emits OTel GenAI spans so Langfuse/Phoenix/LangSmith can ingest them:

```python
# packages/lyra-core/src/lyra_core/telemetry.py
from opentelemetry import trace
from opentelemetry.semconv.gen_ai import GenAIAttributes

tracer = trace.get_tracer("lyra")

def trace_turn(aer: AgentExecutionRecord):
    with tracer.start_as_current_span("lyra.turn") as span:
        span.set_attribute(GenAIAttributes.GEN_AI_OPERATION_NAME, "agent.turn")
        span.set_attribute("lyra.intent", aer.intent)
        span.set_attribute("lyra.confidence", aer.confidence)
        span.set_attribute("lyra.context_window_pct", aer.context_window_pct)
        span.set_attribute("lyra.route_reason", aer.route_reason)
```

### A.7 SLO Definitions

| SLO | Signal | Threshold | Action on Breach |
|---|---|---|---|
| Cost budget | per-turn token × dollar | $0.10/turn | downgrade model |
| Context safety | context_window_pct | 85% | compress or checkpoint |
| Latency | p95 turn latency | 5s | escalate to async |
| Quality | eval verdict score | 0.75 | refine loop |
| Safety | permission violations | any | block + escalate |
| Resource hygiene | orphan processes/ports | any | cleanup + alert |
| Human control | pending approvals | >10 min | notify + surface |

### A.8 Implementation Tasks

- [ ] `packages/lyra-evals/src/lyra_evals/aer.py` — AER dataclass + SQLite storage
- [ ] `packages/lyra-core/src/lyra_core/telemetry.py` — OTel GenAI span emitter
- [ ] `packages/lyra-core/src/lyra_core/monitor.py` — local process/port/git monitor
- [ ] `packages/lyra-cli/src/lyra_cli/commands/monitor.py` — `/monitor` TUI command
- [ ] `packages/lyra-cli/src/lyra_cli/tui_v2/monitor_panel.py` — split-view cockpit UI
- [ ] `packages/lyra-evals/src/lyra_evals/slo.py` — SLO tracker + breach alerts
- [ ] Write 30+ tests covering AER schema, OTel spans, SLO tracking

### A.9 Acceptance Criteria

- Every Lyra turn writes an AER record to SQLite (verified by test)
- `/monitor` opens split-view TUI showing process table + AER + SLO cards
- OTel spans export to Langfuse/Phoenix (verified by integration test)
- SLO breaches surface as alerts in TUI within 1 turn
- Context window % is always visible in status bar
- AER records are queryable: `lyra monitor aer --session <id> --last 10`

---

## Phase B: Intelligent Trajectory Routing
**Timeline:** Weeks 5–8 (upgrades existing 2-tier fast/smart split)
**Research Foundation:** Doc 323 (Agent Model Routing)

### B.1 What This Phase Adds

Lyra already has a 2-tier model split (fast/smart). This phase upgrades it to a **3-tier
routing policy with trajectory awareness** — the harness routes by step type, evidence state,
risk, uncertainty, budget, and user stakes across the full task trajectory, not just per-turn.

### B.2 Three-Tier Model Policy

```
Fast Tier     → Haiku/small models  → search, extraction, formatting, tool loops
Reasoning Tier → Sonnet/mid models  → planning, synthesis, debugging, complex tool review
Advisor Tier   → Opus/strong models → short guidance at hard decision points only
```

The Advisor Tier is the key addition — it preserves the fast executor's state and tools while
injecting stronger reasoning only when the executor is stuck (Anthropic advisor strategy:
+2.7pp SWE-bench, -11.9% cost per task).

### B.3 Routing Decision Function

```python
# packages/lyra-core/src/lyra_core/routing.py

@dataclass
class RoutingState:
    task_state: TaskState
    step_type: StepType          # search, extract, plan, synthesize, verify, etc.
    evidence_conflict: bool
    tool_risk_level: RiskLevel   # low, medium, high, destructive
    context_window_pct: float
    cheap_model_uncertainty: float
    repeated_failures: int
    budget_remaining: float
    user_stakes: StakesLevel     # low, medium, high (security/money/production)
    novelty_demand: bool         # "deep research", "architecture decision"

def route_step(state: RoutingState) -> ModelPolicy:
    # Safety override — always strong
    if state.user_stakes == "security" or state.tool_risk_level == "destructive":
        return ModelPolicy("reasoning", verifier=True, reason="high_stakes")

    # Step type routing
    if state.step_type in {StepType.LOCAL_SEARCH, StepType.FORMAT, StepType.EXTRACT}:
        return ModelPolicy("fast", reason="mechanical_task")

    if state.step_type in {StepType.PLAN, StepType.DEEP_SYNTHESIS, StepType.ARCHITECTURE}:
        return ModelPolicy("reasoning", reason="novelty_demand")

    # Evidence and failure signals
    if state.repeated_failures >= 2 or state.evidence_conflict:
        return ModelPolicy("fast", advisor=True, reason="escalation_needed")

    # Uncertainty cascade
    if state.cheap_model_uncertainty > UNCERTAINTY_THRESHOLD:
        return ModelPolicy("reasoning", reason="model_uncertainty")

    # Budget gate
    if state.budget_remaining < MIN_REASONING_BUDGET:
        return ModelPolicy("fast", stop_on_uncertainty=True, reason="budget_pressure")

    return ModelPolicy("fast", verifier=True, reason="default")
```

**File:** `packages/lyra-core/src/lyra_core/routing.py`

### B.4 Task Slot Table

| Slot | Default Tier | Escalate When | Example |
|---|---|---|---|
| Intent classification | Fast | user_stakes high or ambiguous | "is this coding, research, or planning?" |
| Local search | Fast | query rewrite fails repeatedly | search docs, filenames, code symbols |
| Evidence extraction | Fast/Mid | evidence conflicts | extract paper claims and URLs |
| Planning | Reasoning | multi-system change, irreversible risk | decide architecture or research structure |
| Tool execution | Fast/Mid | tool failure unexplained or destructive | run tests, commands, API calls |
| Synthesis | Reasoning | multi-source contradiction or novelty | compare papers, propose benchmark |
| Verification | Mid/Reasoning | output affects user-visible artifact | check citations, lints, test results |
| Self-modification review | Reasoning + Advisor | core code change | review proposed self-modification |

### B.5 Routing Observability

Every routing decision emits to the AER (Phase A):

```python
# Every routed step appends to AER
aer.route_reason = policy.reason         # "evidence_conflict", "high_stakes", etc.
aer.model_tier = policy.tier             # "fast", "reasoning", "advisor"
aer.escalation_trigger = policy.trigger  # what signal caused escalation
aer.advisor_delta = policy.advisor_delta # what changed after advisor call
```

This closes the loop: routing is not hidden cost-cutting; it is traceable and evaluable.

### B.6 Sequential Trajectory Router

For multi-step tasks (research sessions, self-modification runs), the router maintains a
**budget ledger** across the trajectory:

```python
class TrajectoryRouter:
    """Budget-aware sequential routing (BAAR-inspired, arXiv:2602.21227)."""

    def __init__(self, task_budget: float):
        self.task_budget = task_budget
        self.spent = 0.0
        self.step_history: List[RouteDecision] = []

    def route_next_step(self, state: RoutingState) -> ModelPolicy:
        # Adjust policy based on trajectory context
        remaining = self.task_budget - self.spent
        state.budget_remaining = remaining

        # If we've already escalated 3+ times, stay on reasoning
        if self._recent_escalations() >= 3:
            state.repeated_failures = max(state.repeated_failures, 2)

        policy = route_step(state)
        self.step_history.append(RouteDecision(state, policy))
        return policy
```

**File:** `packages/lyra-core/src/lyra_core/routing.py`

### B.7 Router SLOs

| SLO | Why |
|---|---|
| Strong-call precision ≥ 0.80 | Avoid wasting expensive calls |
| Strong-call recall ≥ 0.90 | Avoid cheap-model failures on hard tasks |
| Escalation latency < 200ms | Keep interactive agents usable |
| Budget adherence: < 10% overspend | Prevent runaway trajectories |
| Advisor usefulness: delta rate ≥ 50% | Measure whether advisor calls change outcomes |

### B.8 Implementation Tasks

- [ ] `packages/lyra-core/src/lyra_core/routing.py` — RoutingState, route_step, TrajectoryRouter
- [ ] `packages/lyra-core/src/lyra_core/advisor.py` — Advisor tool integration (Opus advisor)
- [ ] Upgrade `LyraAgent.process_turn()` to call `TrajectoryRouter.route_next_step()`
- [ ] Wire routing decisions into AER (Phase A integration)
- [ ] `packages/lyra-evals/src/lyra_evals/router_slos.py` — router SLO tracker
- [ ] `/model` command: show current routing policy and last 5 route decisions
- [ ] Write 25+ tests covering routing signals, advisor calls, budget ledger

### B.9 Acceptance Criteria

- Research sessions show ≥30% of steps routed to fast tier (verified via AER)
- Advisor tier only invoked for planning/synthesis/high-risk steps (verified by unit test)
- Router SLO metrics computed automatically after each session
- Budget adherence < 10% overspend on 10 test sessions
- `/model` shows current routing policy and last escalation reason
- Sequential routing reduces cost vs. always-reasoning by ≥20% on research tasks

---

## Phase C: Multi-hop Self-Reasoning and Graph Memory
**Timeline:** Weeks 9–13 (extends lyra-research Phase 3 Memory)
**Research Foundation:** Doc 324 (Multi-hop Reasoning Agents)

### C.1 What This Phase Adds

Lyra's research pipeline already does multi-source discovery. This phase adds **multi-hop
reasoning over Lyra's own codebase** (so it can reason about its own architecture when
proposing self-modifications) plus **graph memory** for stable knowledge and **RL-trained
search** for dynamic evidence.

The key insight: faithfulness is the bottleneck. Lyra must prove each intermediate hop is
supported, not merely produce plausible answers about its own code.

### C.2 Graph Memory for Lyra's Codebase

Lyra gets a **persistent knowledge graph of its own architecture** — so self-modification
proposals can reason multi-hop over "which modules call this function", "what tests cover this
path", "what skills depend on this memory API".

```python
# packages/lyra-memory/src/lyra_memory/codebase_graph.py

class LyraCodebaseGraph:
    """
    LightRAG-inspired graph (arXiv:2410.05779) over Lyra's own source code.
    Updated incrementally on every self-modification (Phase E).
    """

    nodes: Dict[str, CodeNode]   # function, class, module, test, skill, config
    edges: Dict[str, CodeEdge]   # calls, imports, tests, depends_on, modifies

    def query(self, question: str) -> HopTrace:
        """Multi-hop traversal with hop-level provenance."""
        ...

    def find_impact(self, target: str) -> List[str]:
        """Which modules/tests are affected if target is modified?"""
        ...

    def find_test_coverage(self, target: str) -> List[str]:
        """Which tests cover this function?"""
        ...

    def update_from_diff(self, git_diff: str) -> GraphDelta:
        """Incrementally update graph after self-modification."""
        ...
```

**Node types:** `Function`, `Class`, `Module`, `Test`, `Skill`, `MemoryRecord`, `Config`
**Edge types:** `calls`, `imports`, `tests`, `depends_on`, `modifies`, `reads_from`, `writes_to`

### C.3 Multi-hop Reasoning Stack for Self-Modification

When Lyra proposes a self-modification (Phase E), it uses multi-hop reasoning over the
codebase graph to answer:

```
Q: "How would changing lyra_memory/store.py affect the research pipeline?"

Hop 1: store.py → what does it export? [MemoryStore, MemoryRecord]
Hop 2: MemoryStore → who imports it? [research/memory.py, evolution/strategy.py]
Hop 3: research/memory.py → what tests cover it? [test_memory.py, test_research_pipeline.py]
Hop 4: test_research_pipeline.py → does it test the changed API? [YES: line 145]
→ Impact: 2 modules affected, 2 test files must pass, estimated risk: MEDIUM
```

This is the **hop-level provenance** from doc 324 — each reasoning step must cite its evidence.

### C.4 IRCoT-Style Iterative Retrieval

For both research and self-modification planning, Lyra uses IRCoT (arXiv:2212.10509) —
interleaved reasoning and retrieval:

```python
class IRCoTReasoner:
    """
    Interleaved retrieval and reasoning (IRCoT, arXiv:2212.10509).
    Used for: research queries, self-modification planning, bug diagnosis.
    """

    def reason(self, question: str, max_hops: int = 5) -> HopTrace:
        trace = HopTrace(question=question)
        context = ""

        for hop in range(max_hops):
            # Generate next reasoning step
            step = self.model.generate_reasoning_step(question, context)

            # Extract sub-question from reasoning
            sub_question = extract_sub_question(step)

            # Retrieve evidence for sub-question
            evidence = self.retriever.retrieve(sub_question)

            # Check if evidence supports or contradicts step
            support_score = self.verifier.check_support(step, evidence)

            trace.add_hop(HopRecord(
                step_id=hop,
                reasoning=step,
                sub_question=sub_question,
                evidence=evidence,
                support_score=support_score,
                modality="text",
                tool_used=self.retriever.last_tool,
                cost=self.model.last_cost,
            ))

            context += f"\n[Hop {hop}]: {step}\nEvidence: {evidence}"

            if is_answerable(step, evidence):
                break

        return trace
```

**File:** `packages/lyra-core/src/lyra_core/multihop.py`

### C.5 Hop-Level Provenance in Research Reports

Research reports generated by lyra-research now include a `HopTrace` alongside each major
claim — making every synthesis claim traceable to specific retrieval hops:

```markdown
## Finding: Graph RAG outperforms vector RAG for multi-hop queries

**Evidence Chain:**
- Hop 1: Retrieved `GraphRAG paper (arXiv:2404.16130)` [support: 0.92]
- Hop 2: Retrieved `LightRAG benchmark table` → local/global query comparison [support: 0.89]
- Hop 3: Cross-checked `HippoRAG (arXiv:2405.14831)` → confirms entity-relation traversal [support: 0.81]
- Contradiction check: `NodeRAG (arXiv:2504.11544)` → partially challenges on node construction cost [0.60]

**Confidence:** 0.87 | **Hops:** 3 | **Conflict flag:** minor
```

### C.6 RL-Trained Search Policy (Lyra-Searcher)

After 10+ research sessions, Lyra trains a lightweight search policy (Search-R1 inspired,
arXiv:2503.09516) that internalizes:
- When to search vs. reason from existing knowledge
- How to formulate retrieval queries
- When to stop searching

```python
class LyraSearchPolicy:
    """
    RL-trained search behavior (Search-R1 style, arXiv:2503.09516).
    Trained from Lyra's own research trajectories stored in SessionCaseBank.
    """

    def should_search(self, question: str, context: str) -> bool:
        """Learned policy: search now or reason from existing context?"""
        ...

    def formulate_query(self, sub_question: str, domain: str) -> str:
        """Learned query formulation by domain."""
        ...

    def train_from_trajectories(self, session_cases: List[SessionCase]) -> PolicyDelta:
        """Online policy update from successful research sessions."""
        ...
```

**File:** `packages/lyra-research/src/lyra_research/search_policy.py`

### C.7 Implementation Tasks

- [ ] `packages/lyra-memory/src/lyra_memory/codebase_graph.py` — LightRAG-style codebase KG
- [ ] `packages/lyra-core/src/lyra_core/multihop.py` — IRCoT reasoner with hop provenance
- [ ] `packages/lyra-research/src/lyra_research/hop_trace.py` — HopRecord + HopTrace schema
- [ ] Update `lyra_research/reporter.py` — include hop traces in research reports
- [ ] `packages/lyra-research/src/lyra_research/search_policy.py` — RL-trained search policy
- [ ] `packages/lyra-memory/src/lyra_memory/codebase_graph.py` — update from git diffs
- [ ] `/hops` command — view hop trace for last research session
- [ ] Write 30+ tests covering IRCoT hops, provenance, graph queries

### C.8 Acceptance Criteria

- Codebase graph built from Lyra's source tree in < 30s (verified by test)
- `find_impact("lyra_memory/store.py")` returns correct affected modules (verified by test)
- Research reports include hop traces with support scores ≥ 0.75 on average
- IRCoT reasoner terminates in ≤ 5 hops for 90%+ of test questions
- RL search policy improves top-10 recall by ≥ 10% after 10 training sessions
- Contradiction flags appear in ≥ 50% of research reports on contested topics

---

## Phase D: Fleet-Managed Parallel Evolution
**Timeline:** Weeks 14–17 (new capability layer)
**Research Foundation:** Doc 325 (Agent View for AI Agents)

### D.1 What This Phase Adds

Lyra already has `/spawn` for git-worktree-isolated subagents. This phase adds an **Agent View
fleet dashboard** — an attention-triage queue for managing multiple parallel self-improvement
and research agents simultaneously, inspired by Claude Code's `claude agents` pattern.

The key insight: the operator's question is not "what are all agents doing?" but "which agent
needs my judgment RIGHT NOW?"

### D.2 AgentViewRecord Schema

```python
# packages/lyra-core/src/lyra_core/agent_view.py

@dataclass
class AgentViewRecord:
    # Session identity
    session_id: str
    name: str
    agent_kind: Literal["research", "self_modification", "coding", "debug", "general"]
    directory: str
    worktree: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Runtime
    supervisor_pid: int
    process_alive: bool
    run_count: int

    # State (drives attention queue priority)
    status: Literal["working", "needs_input", "ready_for_review", "completed", "failed", "stopped"]
    attention_reason: Optional[str]  # why operator attention is needed
    blocked_since: Optional[datetime]
    failure_reason: Optional[str]

    # Summary (Haiku-generated, refreshed every 15s)
    last_summary: str
    summary_model: str
    summary_cost: float
    summary_refreshed_at: datetime

    # Interaction
    peek_text: str              # latest output snippet for quick peek
    pending_question: Optional[str]
    suggested_reply: Optional[str]

    # Artifacts
    pull_requests: List[str]    # PR URLs if agent opened PRs
    files_changed: List[str]
    branch: Optional[str]
    checks_state: Optional[str]

    # Telemetry (links to Phase A AER)
    trace_id: str
    token_usage: int
    cost_usd: float
    rate_limit_state: Optional[str]

    # Safety
    permission_requests: List[str]
    destructive_actions_pending: List[str]
    verifier_state: Optional[str]
```

**File:** `packages/lyra-core/src/lyra_core/agent_view.py`

### D.3 Session State Machine

```mermaid
Created → Working → NeedsInput (← Working)
        → Working → ReadyForReview → Completed → Archived
        → Working → Failed → Working (retry)
        → Working → Stopped → Deleted
```

### D.4 Attention Priority Queue

| Priority | Condition | Operator Action |
|---|---|---|
| P0 | destructive pending action, failing eval, security alert | attach or stop immediately |
| P1 | needs_input, permission decision, failed run | peek/reply or attach |
| P2 | ready_for_review, PR checks failed, merge blocked | review artifact |
| P3 | active and expensive, high token burn, long-running loop | inspect summary/trace |
| P4 | completed cleanly | archive or review later |

### D.5 Fleet View TUI

```
┌─ Lyra Agent View ─────────────────────────────────────────────────────────────┐
│ [P0] 🔴 needs_input  research-agent-1  "Agent memory 2026"  3m blocked        │
│ [P1] 🟡 reviewing    self-mod-agent-2  "Add hop trace API"  2m · PR#45 open   │
│ [P2] 🟢 working      coding-agent-3   "Fix IRCoT latency"  8m · 12k tokens   │
│ [P4] ✓  completed    research-agent-4 "Context engineering" 23m · report done │
├────────────────────────────────────────────────────────────────────────────────┤
│ Space=Peek  Enter=Attach  r=Reply  s=Stop  d=Delete  q=Back                   │
└────────────────────────────────────────────────────────────────────────────────┘

[PEEK: research-agent-1]
"Found 47 papers on agent memory. Now stuck: should I prioritize recency or citation
count for ranking? Your preference?"

> reply: use citation × recency product score
```

**Keys:** `Space`=peek, `Enter`=attach, `r`=reply inline, `s`=stop, `d`=delete, `q`=back

### D.6 Background Supervisor

A persistent supervisor process manages agent lifecycles independent of the TUI:

```python
# packages/lyra-core/src/lyra_core/supervisor.py

class AgentSupervisor:
    """
    Manages background agent sessions.
    Inspired by Claude Code's supervisor process pattern.
    """

    def dispatch(self, task: str, agent_kind: str) -> AgentViewRecord:
        """Start a background agent in a git worktree."""
        ...

    def poll_agents(self) -> List[AgentViewRecord]:
        """Refresh AgentViewRecords for all active sessions."""
        ...

    def peek(self, session_id: str) -> str:
        """Get latest output summary using Haiku (max 15s refresh rate)."""
        ...

    def reply(self, session_id: str, message: str) -> None:
        """Unblock a waiting agent without full context switch."""
        ...

    def attach(self, session_id: str) -> None:
        """Enter full conversation with agent session."""
        ...

    def stop(self, session_id: str) -> None:
        """Gracefully stop agent, preserve worktree state."""
        ...
```

**File:** `packages/lyra-core/src/lyra_core/supervisor.py`

### D.7 Row Summaries as Model Routing

Row summaries (used in fleet table) use Haiku — the smallest/cheapest model — refreshed at
most every 15s while active. This is a direct application of Phase B routing: cheap models
for mechanical summarization, strong models for planning and synthesis.

### D.8 Implementation Tasks

- [ ] `packages/lyra-core/src/lyra_core/agent_view.py` — AgentViewRecord + state machine
- [ ] `packages/lyra-core/src/lyra_core/supervisor.py` — background supervisor process
- [ ] `packages/lyra-cli/src/lyra_cli/commands/agents.py` — `/agents` command
- [ ] `packages/lyra-cli/src/lyra_cli/tui_v2/agent_view_panel.py` — fleet table TUI
- [ ] Upgrade `/spawn` to create managed background sessions (not fire-and-forget)
- [ ] Wire AgentViewRecord to AER trace_id (Phase A integration)
- [ ] Wire attention_reason to P0-P4 priorities (auto-sort)
- [ ] Write 30+ tests covering state machine, peek/reply, supervisor lifecycle

### D.9 Acceptance Criteria

- `/agents` opens fleet view TUI showing all background sessions
- State machine transitions are correct (verified by unit tests)
- Peek returns summary within 2s (using Haiku)
- P0 sessions (destructive pending, failing eval) are auto-sorted to top
- Reply unblocks agent without full context switch (verified by integration test)
- Supervisor persists across Lyra restarts (sessions survive update)
- Fleet view shows AER trace_id linkable to Phase A cockpit

---

## Phase E: Closed-Loop Self-Rewriting
**Timeline:** Weeks 18–26 (the culminating phase — builds on Phases A–D + existing Phase 4)
**Research Foundation:** Doc 326 (Closed-loop Agent Control)

### E.1 What This Phase Adds

This is the core self-rewriting capability. The existing `lyra-evolution` package has stubs for
strategy extraction. This phase implements the **full 8-timescale control loop** — from
token-level runtime control to fleet-level SRE — enabling Lyra to modify its own code under
verified closed-loop control with rollback.

### E.2 The 8-Timescale Control Loop

```
Token-level   → ATLAS-RTC: catch schema drift before full output (arXiv:2603.27905)
Step-level    → Tool-use loop with retry/alternate/summarize/stop
Turn-level    → Evaluator-refine: draft → critique → revise until criteria
Episode-level → Reflexion: write trace-grounded lessons, retry with memory
Skill-level   → Voyager: execute → verify → save verified skills (arXiv:2305.16291)
Runtime-level → LangGraph-style checkpoints + interrupts for HITL
Operator-level → Human gate for high-risk self-modifications
Fleet-level   → Agent View SRE: reprioritize, stop, reassign self-improvement agents
```

### E.3 ClosedLoopAgentControlRecord

```python
# packages/lyra-evolution/src/lyra_evolution/control_record.py

@dataclass
class ClosedLoopAgentControlRecord:
    # Identity (links to Phase A AER)
    run_id: str
    session_id: str
    agent_id: str
    task_id: str
    trace_id: str

    # Goal
    user_goal: str
    acceptance_criteria: List[str]
    risk_level: RiskLevel

    # State
    step_index: int
    loop_phase: str              # "generate", "evaluate", "refine", "rollback"
    checkpoint_id: Optional[str]

    # Observation
    tool_result: Optional[str]
    evaluator_verdict: Optional[str]
    human_decision: Optional[str]
    trace_anomaly: Optional[str]

    # Controller
    policy_name: str
    decision: Literal["accept", "retry", "refine", "route", "rollback", "ask_human", "stop"]
    reason: str
    confidence: float
    budget_remaining: float

    # Intervention
    action_kind: str
    rollback_target: Optional[str]
    approval_id: Optional[str]

    # Learning
    reflection: Optional[str]    # trace-grounded (not just self-talk)
    skill_update: Optional[str]
    memory_write: Optional[str]
    eval_case_id: Optional[str]

    # Termination
    status: Optional[str]
    stop_reason: Optional[str]
    success_score: Optional[float]
    residual_risk: Optional[float]
```

**File:** `packages/lyra-evolution/src/lyra_evolution/control_record.py`

### E.4 Controller Policy

```python
# packages/lyra-evolution/src/lyra_evolution/controller.py

def control_step(state: AgentControlState) -> ControlDecision:
    # Safety blocks first — always
    if state.safety_policy.blocks(state.action):
        return ControlDecision("stop_or_escalate", reason="safety_policy")

    # Token-level drift (ATLAS-RTC pattern, arXiv:2603.27905)
    if state.output_drift_from_spec > DRIFT_THRESHOLD:
        return ControlDecision("rollback", reason="token_level_drift")

    # Stability budget (AICL, Zenodo:17835680)
    if state.behavior_variance > STABILITY_BUDGET:
        return ControlDecision("replan", reason="stability_drift")

    # Repeated failure
    if state.same_tool_failure >= 2:
        return ControlDecision("reflect_and_replan", reason="repeated_failure")

    # Evaluator feedback
    if state.evaluator_score < THRESHOLD and state.retry_budget > 0:
        return ControlDecision("refine", reason="evaluator_below_threshold")

    if state.evaluator_score < THRESHOLD:
        return ControlDecision("ask_human", reason="retry_budget_exhausted")

    # Budget gate
    if state.cost_budget_remaining < state.next_step_estimate:
        return ControlDecision("summarize_and_stop", reason="budget_pressure")

    return ControlDecision("continue_or_accept", reason="criteria_met")
```

**File:** `packages/lyra-evolution/src/lyra_evolution/controller.py`

### E.5 Voyager-Style Skill Accumulation

Every successful Lyra self-modification becomes a **verified skill** in the skill library:

```python
class VoyagerSkillAccumulator:
    """
    Voyager-inspired skill library (arXiv:2305.16291).
    Applied to Lyra's self-modification domain.
    """

    def execute_and_verify(self, skill_candidate: SkillCandidate) -> VerificationResult:
        # 1. Run in sandbox
        sandbox_result = run_in_sandbox(skill_candidate.code)
        if not sandbox_result.success:
            return VerificationResult(False, lesson=sandbox_result.error)

        # 2. Run full test suite
        test_result = run_test_suite(skill_candidate.affected_modules)
        if test_result.failures > 0:
            return VerificationResult(False, lesson=f"{test_result.failures} tests failed")

        # 3. Check codebase graph impact (Phase C)
        impact = codebase_graph.find_impact(skill_candidate.target)
        if len(impact.high_risk_modules) > 0:
            return VerificationResult(False, lesson="high-risk impact chain")

        # 4. Verified → admit to skill library
        return VerificationResult(True, skill=skill_candidate)

    def propose_next_task(self) -> SelfModificationTask:
        """Curriculum-driven: propose the next self-improvement task."""
        gaps = self.identify_capability_gaps()
        return select_by_novelty_and_feasibility(gaps)
```

**File:** `packages/lyra-evolution/src/lyra_evolution/voyager.py`

### E.6 Trace-Grounded Reflexion

Lessons from failed self-modifications must cite actual AER spans (not just self-talk):

```python
class TraceGroundedReflexion:
    """
    Reflexion (arXiv:2303.11366) with AER-grounded lessons.
    Without trace grounding, a reflection is self-talk; with it, it can be audited.
    """

    def reflect(self, failed_trajectory: List[AER], failure_summary: str) -> Reflection:
        # Find the actual failing span from AER
        failing_span = find_first_failure_span(failed_trajectory)

        # Ground the lesson in the actual evidence
        lesson = self.model.generate(
            f"Trajectory failed at span {failing_span.turn_index}.\n"
            f"Intent: {failing_span.intent}\n"
            f"Tool: {failing_span.tool_name}\n"
            f"Result: {failing_span.tool_result_hash}\n"
            f"What specifically went wrong and why?\n"
            f"What should be done differently next time?"
        )

        return Reflection(
            lesson=lesson,
            citing_span=failing_span.trace_id,    # must cite a real span
            confidence=self.verifier.score(lesson, failing_span),
            memory_write=True if confidence > 0.75 else False
        )
```

**File:** `packages/lyra-evolution/src/lyra_evolution/reflexion.py`

### E.7 Checkpointing and HITL

LangGraph-style checkpointing and human-in-the-loop gates:

```python
class EvolutionCheckpoint:
    """
    LangGraph-style checkpointing (LangGraph persistence docs).
    Every self-modification step is checkpointed for rollback.
    """

    def save(self, state: AgentControlState, tag: str) -> str:
        """Save checkpoint. Returns checkpoint_id."""
        ...

    def restore(self, checkpoint_id: str) -> AgentControlState:
        """Restore to checkpoint. Used by rollback decision."""
        ...

    def interrupt_for_human(self, question: str, context: AgentControlState) -> str:
        """Pause execution. Surfaces in Agent View (Phase D) as P0/P1 attention item."""
        # Creates AgentViewRecord with status="needs_input"
        # Blocks until human replies via fleet view
        ...
```

**File:** `packages/lyra-evolution/src/lyra_evolution/checkpoint.py`

### E.8 Stability Budgets (AICL-Inspired)

Borrow from control theory and SRE: assign drift, variance, retry, cost, and unsafe-action
budgets. Lyra can spend them; crossing triggers replan, rollback, or human escalation.

```python
@dataclass
class StabilityBudget:
    max_behavior_drift: float = 0.3      # variance across long-horizon runs
    max_retry_count: int = 5             # per task
    max_cost_usd: float = 10.0           # per self-modification task
    max_unsafe_actions: int = 0          # hard zero
    max_failed_tests_after_mod: int = 0  # must not regress test suite

    def is_stable(self, state: AgentControlState) -> bool:
        return (
            state.behavior_variance <= self.max_behavior_drift
            and state.retry_count <= self.max_retry_count
            and state.cost_spent <= self.max_cost_usd
            and state.unsafe_actions_count == 0
            and state.test_failures == 0
        )
```

### E.9 Self-Modification Scope Levels (Unchanged from Existing Plan)

| Level | Scope | Gate |
|---|---|---|
| L1 Safe | Add skills, update docs, add tests, refine prompts | Auto-approved via verifier |
| L2 Medium | Modify non-core utilities, add commands, update UI | Sandbox + full test suite |
| L3 High-Risk | Modify core transport, memory system, safety checks | Human review + HITL gate |

### E.10 Implementation Tasks

- [ ] `packages/lyra-evolution/src/lyra_evolution/control_record.py` — CLACR schema
- [ ] `packages/lyra-evolution/src/lyra_evolution/controller.py` — controller policy
- [ ] `packages/lyra-evolution/src/lyra_evolution/voyager.py` — skill accumulation loop
- [ ] `packages/lyra-evolution/src/lyra_evolution/reflexion.py` — trace-grounded reflection
- [ ] `packages/lyra-evolution/src/lyra_evolution/checkpoint.py` — save/restore/HITL
- [ ] `packages/lyra-evolution/src/lyra_evolution/stability.py` — stability budgets
- [ ] Wire HITL interrupt to Agent View Phase D (surfaces as P0 attention item)
- [ ] Wire CLACR to AER trace_id (Phase A integration)
- [ ] Wire multi-hop impact analysis to modification gate (Phase C integration)
- [ ] Wire routing policy to controller decisions (Phase B integration)
- [ ] Write 50+ tests covering controller policy, Voyager loop, Reflexion grounding,
      checkpoint/restore, stability budgets

### E.11 Acceptance Criteria

- Self-modification loop completes end-to-end: propose → sandbox → test → verify → commit/rollback
- No self-modification regresses test suite (gate blocks 100% of regressions)
- Reflexion lessons always cite a real AER span (verified by test)
- Checkpoint/restore works correctly (verified by integration test)
- HITL interrupt surfaces as P1 item in Agent View fleet (verified by test)
- Stability budget tracked continuously (drift, retry, cost, unsafe actions)
- After 20 self-modification sessions, at least 3 L1 skills have been auto-approved and saved
- Rollback returns codebase to pre-modification state within 5s

---

## Integration Map: How the 5 Phases Work Together

```
Phase A (AER)       ← feeds every other phase
                        B reads route_reason from AER
                        C reads evidence_refs from AER
                        D reads trace_id from AER
                        E reads tool_result, verifier_verdict from AER

Phase B (Routing)   → decides which model handles each step in C, D, E
                        C: fast for graph traversal, reasoning for synthesis
                        D: Haiku for row summaries, Opus for advisor on modification review
                        E: Advisor tier for high-risk self-modification decisions

Phase C (Multi-hop) → provides impact analysis for Phase E
                        E uses codebase_graph.find_impact() before every self-modification
                        E uses IRCoT reasoning for modification planning
                        D uses hop traces in research agent row summaries

Phase D (Agent View) → surfaces HITL gates from Phase E
                        E.checkpoint.interrupt_for_human() → creates AgentViewRecord(P0/P1)
                        D fleet view is how operator approves/rejects E proposals
                        B routing: Haiku generates D row summaries

Phase E (Closed-loop) → self-modifies Lyra, updating A, B, C, D themselves
                        Voyager skills update lyra-skills package
                        Reflexion lessons update lyra-memory
                        Stability gate ensures no phase regresses
```

---

## Combined Implementation Timeline

```
Weeks 1–4    Phase A: AER + OTel + SLO cockpit
Weeks 5–8    Phase B: 3-tier routing + trajectory router + advisor
Weeks 9–13   Phase C: codebase graph + IRCoT + hop traces + RL search
Weeks 14–17  Phase D: Agent View + fleet TUI + supervisor
Weeks 18–26  Phase E: closed-loop controller + Voyager + Reflexion + checkpoints
Weeks 27–28  Integration: wire all 5 phases, end-to-end self-modification test
Weeks 29–30  Hardening: stress tests, adversarial tests, stability budget tuning
```

---

## Success Metrics for "Lyra Rewrites Itself"

### Short-term (after Phase A+B)
- [ ] Every turn emits an AER with intent/observation/inference/evidence
- [ ] SLO dashboard visible in TUI at all times
- [ ] 3-tier routing reduces cost by ≥ 20% vs. always-reasoning
- [ ] Router decisions are traceable and evaluable

### Medium-term (after Phase C+D)
- [ ] Multi-hop reasoning over Lyra's own codebase with hop provenance
- [ ] Fleet view manages ≥ 5 parallel agents simultaneously
- [ ] Research reports include hop traces with ≥ 0.75 average support score
- [ ] HITL gates surface correctly in fleet view

### Long-term (after Phase E)
- [ ] Lyra proposes, verifies, and commits ≥ 3 L1 self-modifications per week
- [ ] No regression in 2200+ test suite after any self-modification
- [ ] Voyager skill library grows by ≥ 1 new verified skill per 5 sessions
- [ ] Reflexion lessons always cite real AER spans (0 ungrounded reflections)
- [ ] Stability budgets maintained across 50+ continuous sessions
- [ ] Operator can review, approve, or reject every L3 modification via fleet view

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AER storage growth unchecked | High | Medium | Prune records > 30 days; compress old sessions |
| Routing degrades to always-strong | Medium | Medium | Router SLO alerts if strong-call rate > 60% |
| Codebase graph staleness | Medium | High | Auto-update on every git commit; validate on build |
| IRCoT latency too high | Medium | Medium | Cap at 5 hops; fast tier for early hops |
| Agent View fleet overload | Low | Medium | Cap at 20 background sessions; auto-archive completed |
| Self-modification regressions | Low | Critical | Stability budget + 0-failure test gate + rollback |
| Reflexion lessons without grounding | Medium | High | Test that every Reflection.citing_span is in AER |
| HITL approval fatigue | Medium | Medium | P0 only for destructive/security; P1+ auto-reply |

---

## References

- `322` arXiv:2603.21692 (AER paper), graykode/abtop, patoles/agent-flow, OpenTelemetry GenAI
- `323` arXiv:2305.05176 (FrugalGPT), arXiv:2406.18665 (RouteLLM), arXiv:2602.21227 (BAAR),
        Claude advisor strategy blog, Advisor tool docs
- `324` arXiv:2212.10509 (IRCoT), arXiv:2410.05779 (LightRAG), arXiv:2404.16130 (GraphRAG),
        arXiv:2503.09516 (Search-R1), arXiv:2405.14831 (HippoRAG)
- `325` Claude Code Agent View docs, AgentLens arXiv:2402.08995, AER arXiv:2603.21692v1
- `326` arXiv:2303.11366 (Reflexion), arXiv:2305.16291 (Voyager), arXiv:2408.07199 (Agent Q),
        arXiv:2603.27905 (ATLAS-RTC), Zenodo:17835680 (AICL), LangGraph persistence docs

---

**Document Status:** Master Plan v1.0
**Last Updated:** 2026-05-14
**Relationship:** Additive to LYRA_EVOLUTION_MASTER_PLAN.md (docs 313-321)
**Implementation Start:** Phase A, Week 1
