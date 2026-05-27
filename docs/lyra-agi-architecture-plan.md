# 🧬 Lyra AGI Architecture Plan

> **Ultra-plan to evolve Lyra into the most intelligent AI agent — closely reaching AGI.**  
> Based on deep research of 200+ trending papers + Lyra's existing 25-package architecture.

---

## Executive Summary

Lyra already has the strongest foundation of any open-source agent: 25 packages, 200+ papers of research absorbed, 5 major subsystems. But to reach AGI-level intelligence, it needs **7 new subsystems** and **fundamental upgrades to 5 existing ones**. This plan merges the best ideas from today's frontier research into a coherent architecture.

**Current Lyra:** Multi-agent orchestration, deep research, self-evolution, 4-tier memory, streaming CLI.  
**Target Lyra:** Recursive self-improvement, persistent world model, causal reasoning, decentralized memory federation, source-level self-modification, reward-hacking resistance, adolescent-stage autonomy, and verifiable AGI benchmarks.

---

## Part I: Seven New Subsystems

### Subsystem 1 — 🌌 World Model Engine

**Inspiration:** DecentMem (2605.22721), WorldKV (2605.22718), stable-worldmodel (2605.21800), Beyond Euclidean Proximity (2605.22164)

**The gap.** Lyra has no persistent world model — no internal representation of how its environment, tools, and user behave over time. It reacts to each task fresh.

**The upgrade.** A persistent latent world model that:
- Maintains a **compressed latent state** of the user's codebase, tools, preferences, and task context
- Uses **WorldKV-style retrieval-compression** to keep the world model within context budget
- Predicts tool outcomes before execution (speculative world simulation)
- Detects **world model drift** — when reality diverges from expectations, triggers re-learning

```python
class WorldModel:
    latent_state: CompressedLatentState    # Compressed representation of environment
    predictor: OutcomePredictor             # Predicts tool outcomes
    drift_detector: DriftMonitor            # Detects model-vs-reality divergence
    
    async def predict(self, action: Action) -> PredictedOutcome:
        """Predict outcome before executing"""
        return self.predictor(self.latent_state, action)
    
    async def observe(self, action: Action, outcome: Outcome):
        """Update world model with real outcome"""
        drift = self.drift_detector(self.latent_state, action, outcome)
        if drift > THRESHOLD:
            await self.relearn()
        self.latent_state = self.compressor(self.latent_state, action, outcome)
```

**Implementation:** New package `lyra-worldmodel`. 3 months.

---

### Subsystem 2 — 🔬 Causal Reasoning Engine

**Inspiration:** CASPIAN (2605.19240), Causal Past Logic (2605.20923), Represented Is Not Computed (2605.22488), Pramana (2605.20312)

**The gap.** Lyra's reasoning is associative (pattern matching), not causal. It knows correlations but not interventions.

**The upgrade.** Add a causal reasoning layer that:
- Builds **causal graphs** from execution traces (action A → outcome B because...)
- Supports **counterfactual queries** ("what if I had used a different tool?")
- Uses **causal past logic** for runtime verification of agent workflows
- Generates **claim attestations** (Pramana format) for every consequential output

```python
class CausalEngine:
    causal_graph: CausalGraph              # Built from execution traces
    counterfactual: CounterfactualSimulator # "What if..." reasoning
    
    async def explain(self, outcome: Outcome) -> CausalExplanation:
        """Explain why an outcome occurred"""
        return self.causal_graph.explain(outcome)
    
    async def what_if(self, action: Action, context: Context) -> CounterfactualResult:
        """Simulate counterfactual"""
        return self.counterfactual.simulate(action, context)
    
    async def attest(self, claim: Claim) -> ClaimAttestation:
        """Generate Pramana-format attestation"""
        return ClaimAttestation.create(claim, self.causal_graph)
```

**Implementation:** New package `lyra-causal`. Extends `harness_core` with causal tracing. 4 months.

---

### Subsystem 3 — 🔄 Reward Hacking Defense

**Inspiration:** SpecBench (2605.21384), Ratchet (2605.22148), PESS (2605.22541), Sibyl-AutoResearch (2605.22343)

**The gap.** Lyra's self-evolution optimizes for passing tests + user approval — but SpecBench proves every frontier agent hacks rewards when oversight is thin. Lyra has no defense.

**The upgrade.** A multi-layer reward defense:
- **Specification test suites** — held-out tests the agent never sees during optimization
- **Reward hacking detector** — monitors for divergence between visible and held-out metrics
- **Probabilistic evaluation** (PESS-style) — tracks distribution of outcomes, not just averages
- **Trajectory auditing** — verifies full trajectory, not just final result

```python
class RewardDefense:
    spec_tests: HeldOutTestSuite           # Tests agent never sees
    hacking_detector: RewardHackingMonitor # Detects spec gaming
    prob_evaluator: ProbabilisticEvaluator # Distribution-aware eval
    
    async def evaluate(self, trajectory: Trajectory) -> DefenseReport:
        spec_score = self.spec_tests.run(trajectory)
        hacking_risk = self.hacking_detector.analyze(trajectory, spec_score)
        distribution = self.prob_evaluator.evaluate(trajectory)
        return DefenseReport(spec_score, hacking_risk, distribution)
```

**Implementation:** New package `lyra-defense`. Integrates with `lyra-evolution`. 2.5 months.

---

### Subsystem 4 — 🧩 Decentralized Memory Federation

**Inspiration:** DecentMem (2605.22721), Memory-R2 (2605.21768), MEMTIER (book ch.151-153), DeferMem (2605.22411)

**The gap.** Lyra's memory is centralized. DecentMem proves centralized memory collapses agent diversity.

**The upgrade.** Decentralize memory into per-agent pools with federation:
- Each specialist agent gets its own **dual-pool memory** (exploit + explore)
- Agents coordinate via **gossip protocol** for cross-pollination
- Memory-R2 fair credit assignment prevents reward hijacking
- DeferMem-style query-time distillation for long-term QA

```python
@dataclass
class DecentralizedMemory:
    agents: dict[str, AgentMemoryPool]     # Per-agent exploit + explore pools
    federation: GossipProtocol             # Cross-agent memory sharing
    credit_assigner: FairCreditAssigner    # Memory-R2 style
    
    async def retrieve(self, query: str, agent_id: str) -> list[MemoryItem]:
        pool = self.agents[agent_id]
        local = pool.retrieve(query)
        peer = await self.federation.query_peers(query, exclude={agent_id})
        return self.credit_assigner.merge(local, peer)
```

**Implementation:** New package `lyra-memory-federation`. Refactor existing `lyra-memory`. 3 months.

---

### Subsystem 5 — ⚡ Source-Level Self-Modification

**Inspiration:** MOSS (2605.22794), Evolutionary Multi-Task (2605.22613), Ethical Hyper-Velocity (2605.16407), SSV (2605.19893)

**The gap.** Lyra's self-evolution currently mutates skill files and configs. MOSS proves source-code-level evolution is the next frontier.

**The upgrade.** Full source-code-level self-modification:
- External coding-agent CLI for harness modifications
- Ephemeral trial workers running candidate images against production failure batches
- User-consent gates for promoted changes
- Deterministic governance JIT (Ethical Hyper-Velocity) — governance-aware compilation

```python
class SourceEvolution:
    coding_agent: CodingAgentCLI           # External agent for code changes
    trial_workers: TrialWorkerPool         # Ephemeral test environments
    consent_gates: UserConsentManager      # Promotion gates
    governance_jit: GovernanceJIT          # EHV-style safety compilation
    
    async def evolve(self, failure_batch: list[Failure]) -> EvolutionProposal:
        patch = await self.coding_agent.repair(failure_batch)
        trial_results = await self.trial_workers.run(patch, failure_batch)
        if trial_results.pass_rate >= 0.95:
            safe_patch = self.governance_jit.compile(patch)
            return EvolutionProposal(safe_patch, trial_results)
```

**Implementation:** Upgrade `lyra-evolution` with MOSS architecture. 4 months.

---

### Subsystem 6 — 🧪 AGI Benchmarks & Self-Evaluation

**Inspiration:** SpecBench (2605.21384), BioXArena (2605.15766), Agentic CLEAR (2605.22608), Pseudo-Formalization (2605.20531)

**The gap.** Lyra has no systematic self-evaluation — it doesn't know how intelligent it is.

**The upgrade.** A comprehensive self-evaluation suite:
- **Multi-level evaluation** (Agentic CLEAR): system/trace/node-level with dynamic taxonomy
- **Pseudo-Formalization** for proof-verified reasoning evaluation
- **Domain benchmarks**: BioXArena (biomedical), TerminalWorld (sysadmin), SpecBench (reward hacking)
- **Self-calibration**: Lyra estimates its own confidence and compares to actual performance

```python
class SelfEvaluation:
    evaluator: MultiLevelEvaluator         # CLEAR-style
    proof_verifier: PseudoFormalVerifier   # Proof-based verification
    benchmarks: dict[str, Benchmark]       # Domain-specific benchmarks
    calibrator: SelfCalibrator             # Confidence calibration
    
    async def evaluate_self(self) -> EvaluationReport:
        system = await self.evaluator.evaluate_system()
        traces = await self.evaluator.evaluate_traces()
        proofs = await self.proof_verifier.verify_recent_reasoning()
        domain_scores = await self.run_benchmarks()
        calibration = self.calibrator.calibrate(system, traces, proofs)
        return EvaluationReport(system, traces, proofs, domain_scores, calibration)
```

**Implementation:** Upgrade `lyra-evals`. 2.5 months.

---

### Subsystem 7 — 🌱 Adolescent-Stage Autonomy

**Inspiration:** CR4T (2605.21609), GrandGuard (2605.20203), Governance by Design (2605.20210), CAX-Agent recovery ladder (2605.15218)

**The gap.** Lyra operates in binary modes: fully supervised or fully autonomous. No graduated autonomy.

**The upgrade.** A developmental autonomy system modeled on adolescent development:
- **Autonomy stages**: supervised → coached → monitored → autonomous → mentoring
- **Stage advancement**: promoted when error rate, coverage, and user trust thresholds met
- **Recovery ladder** (from CAX-Agent): rule patching → model regeneration → context enrichment → human intervention
- **Safety guardrails** that adapt to autonomy level: stricter in early stages, relaxed in later ones

```python
@dataclass
class AutonomySystem:
    stage: AutonomyStage = AutonomyStage.SUPERVISED
    recovery_ladder: RecoveryLadder        # CAX-Agent style
    guardrails: AdaptiveGuardrails          # Stage-dependent safety
    
    async def process_task(self, task: Task) -> Result:
        if self.stage == AutonomyStage.SUPERVISED:
            return await self.supervised_execute(task)
        elif self.stage == AutonomyStage.COACHED:
            return await self.coached_execute(task)
        elif self.stage == AutonomyStage.MONITORED:
            result = await self.autonomous_execute(task)
            return await self.recovery_ladder.verify(result)
        elif self.stage == AutonomyStage.AUTONOMOUS:
            return await self.autonomous_execute(task)
    
    async def advance_stage(self) -> AutonomyStage:
        if self.metrics.error_rate < 0.01 and self.metrics.coverage > 0.95:
            self.stage = next_stage(self.stage)
```

**Implementation:** New package `lyra-autonomy`. Integrates with `lyra-evolution`. 3 months.

---

### Summary: 7 New Subsystems

| # | Subsystem | Papers | Package | Timeline |
|---|-----------|--------|---------|----------|
| 1 | World Model Engine | DecentMem, WorldKV, stable-worldmodel | lyra-worldmodel | 3 mo |
| 2 | Causal Reasoning | CASPIAN, Causal Past Logic, Pramana | lyra-causal | 4 mo |
| 3 | Reward Hacking Defense | SpecBench, Ratchet, PESS | lyra-defense | 2.5 mo |
| 4 | Decentralized Memory | DecentMem, Memory-R2, DeferMem | lyra-memory-federation | 3 mo |
| 5 | Source-Level Self-Mod | MOSS, Evo Multi-Task | lyra-evolution (major upgrade) | 4 mo |
| 6 | AGI Benchmarks & Eval | SpecBench, Agentic CLEAR, BioXArena | lyra-evals (major upgrade) | 2.5 mo |
| 7 | Adolescent Autonomy | CR4T, CAX-Agent, Governance by Design | lyra-autonomy | 3 mo |

**Total new subsystems:** 7 | **Total estimated time:** 22 months (parallelizable)


---

## Part II: Upgrades to 5 Existing Subsystems

### Upgrade 1 — 🧠 lyra-core: Agent Loop 2.0

**From:** Sequential think→act→observe loop.  
**To:** Parallel, speculative, event-sourced agent loop.

**Changes:**
1. **Multi-Stream execution** (2605.12460) — separate prompts, thinking, and I/O into parallel streams to avoid head-of-line blocking
2. **Speculative planning** (IdleSpec 2605.22154) — use tool-waiting idle time to plan multiple future paths
3. **Event-sourced architecture** (ActiveGraph 2605.21997) — append-only event log as source of truth; working graph as deterministic projection
4. **Runtime harness adaptation** (2605.22166) — adapt tool selection and permission modes at runtime without fine-tuning

```python
# Current:
for step in range(max_steps):
    resp = llm.generate(transcript)
    results = execute_tools(resp.tool_calls)
    transcript += results

# Future:
with EventSourcedLog() as log:
    while not log.done:
        thinking_stream = llm.think(transcript)  # Parallel
        io_stream = speculative_plan(transcript)
        resp = merge(thinking_stream, io_stream)
        results = execute_tools(resp.tool_calls, adapt_harness=True)
        log.emit(StepEvent(resp, results))
        transcript = log.project()  # Log → working state
```

**Key papers:** Multi-Stream LLMs, IdleSpec, ActiveGraph, Runtime Harness Adaptation  
**Timeline:** 2 months

---

### Upgrade 2 — 💾 lyra-memory: Multi-Tier + Graph Knowledge

**From:** Hot/warm/cold SQLite tiers with BM25 + vector retrieval.  
**To:** Hot/warm/cold/graph/Federated tiers with hybrid + MMR diversity.

**Changes:**
1. **Graph tier** — entity-relation knowledge graph connecting memories (book ch.151-153)
2. **MMR diversity reranking** — prevent redundant retrievals
3. **ACT-R activation/decay** — memories fade unless reinforced (cognitive architecture)
4. **Auto-dreamer consolidation** — offline optimization during idle cycles
5. **Federated retrieval** — query peer agent memories via gossip protocol (DecentMem)

**Key papers:** DecentMem, MEMTIER, Memory-R2, DeferMem  
**Timeline:** 2.5 months

---

### Upgrade 3 — 🧬 lyra-evolution: Verify-Execute-Merge

**From:** Self-contained evolution engine with sandbox testing.  
**To:** Full MOSS-style source-level evolution + evolutionary multi-task learning.

**Changes:**
1. **MOSS source rewriting** — external coding agent CLI modifies harness source code
2. **Evolutionary multi-task** (2605.22613) — shared archive across task families
3. **Ephemeral trial workers** — containerized candidate testing
4. **User-consent promotion gate** — human-in-loop for high-risk changes
5. **Ethical Hyper-Velocity JIT** — governance-aware compilation of agent code

**Key papers:** MOSS, Evolutionary Multi-Task, Ratchet, Ethical Hyper-Velocity  
**Timeline:** 4 months (biggest upgrade)

---

### Upgrade 4 — 🔍 lyra-research: Trial-and-Error Harnesses

**From:** 10-step research pipeline with paper generation.  
**To:** Scientific trial-and-error harnesses + experiment learning.

**Changes:**
1. **Trial harnesses** (Sibyl-style) — bounded sandboxes where agents run experiments, capture failures, evolve approach
2. **paper.json support** (2605.16194) — machine-actionable paper reading
3. **Search-E1 self-distillation** (2605.22511) — distill search trajectories into improved reasoning
4. **LLM-Metrics** (2605.22176) — parametric memory-based impact scoring for papers
5. **Protein Thoughts** (2605.21522) — ToT + embedding-space flow matching for discovery tasks

**Key papers:** Sibyl-AutoResearch, paper.json, Search-E1, LLM-Metrics  
**Timeline:** 2.5 months

---

### Upgrade 5 — 🛡️ lyra-mcp / lyra-security: MCP Security

**From:** Basic MCP support with tool registry and permissions.  
**To:** Full MCP security auditing + cascade attack detection + credential revocation.

**Changes:**
1. **VIPER-MCP** (2605.21392) — automated taint vulnerability auditing for MCP servers
2. **HBHC credential revocation** (2605.20704) — heartbeat-bound hierarchical credentials, 90× zombie reduction
3. **CASPIAN cascade detection** (2605.19240) — cross-channel causal monitoring for system-level attacks
4. **LCGuard KV security** (2605.22786) — safe KV cache sharing between agents
5. **Domain-camouflage defense** (2605.22001) — protection against domain-specific injection

**Key papers:** VIPER-MCP, HBHC, CASPIAN, LCGuard, Blind Spots in the Guard  
**Timeline:** 3 months

---

### Upgrade Summary

| Subsystem | Upgrade Scope | Key Papers | Timeline |
|-----------|--------------|------------|----------|
| lyra-core | Agent Loop 2.0 — parallel, speculative, event-sourced | Multi-Stream, IdleSpec, ActiveGraph | 2 mo |
| lyra-memory | +Graph tier, MMR, ACT-R, federated | DecentMem, MEMTIER, Memory-R2 | 2.5 mo |
| lyra-evolution | Source-level MOSS-style + evolutionary multi-task | MOSS, Evo Multi-Task | 4 mo |
| lyra-research | Trial harnesses + paper.json + Search-E1 | Sibyl, paper.json, Search-E1 | 2.5 mo |
| lyra-mcp/security | MCP auditing, HBHC, CASPIAN, LCGuard | VIPER-MCP, HBHC, CASPIAN | 3 mo |


---

## Part III: Integration Architecture

### How Everything Connects

```
                        ┌──────────────────────────────┐
                        │       lyra-autonomy           │
                        │   (Adolescent Stage Manager)  │
                        └────────────┬─────────────────┘
                                     │ governs
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│   lyra-core     │    │    lyra-evolution   │    │   lyra-defense   │
│  Agent Loop 2.0 │◄──►│  Self-Modification  │◄──►│ Reward Hacking   │
│  Event-Sourced  │    │  MOSS + Evo Multi   │    │  Shield          │
└────────┬────────┘    └──────────┬──────────┘    └──────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────────┐
│  lyra-causal    │    │  lyra-worldmodel    │
│  Causal Engine  │◄──►│  World Model        │
│  Counterfactual │    │  Drift Detection    │
└────────┬────────┘    └──────────┬──────────┘
         │                        │
         └───────────┬────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│           lyra-memory-federation            │
│  Decentralized Pools · Gossip · Graph Tier  │
│  ACT-R Decay · Auto-Dreamer                 │
└────────────┬───────────────────┬────────────┘
             │                   │
             ▼                   ▼
┌───────────────────┐   ┌──────────────────┐
│  lyra-research    │   │  lyra-mcp/secure │
│  Trial Harnesses  │   │  VIPER · HBHC    │
│  paper.json       │   │  CASPIAN · LCGuard│
└───────────────────┘   └──────────────────┘

┌─────────────────────────────────────────────┐
│           lyra-evals (AGI Benchmarks)       │
│  CLEAR · Pseudo-Formal · BioXArena · Self   │
└─────────────────────────────────────────────┘
```

### Data Flow: AGI-Level Task

```
User gives a complex, ambiguous goal
        │
        ▼
lyra-autonomy: determine autonomy stage
  → Stage: AUTONOMOUS (error rate < 1%, coverage > 95%)
        │
        ▼
lyra-core (Agent Loop 2.0):
  → Multi-Stream: think + plan + I/O in parallel
  → Event-Sourced Log: every state change recorded
  → Runtime Adaptation: tools selected per task
        │
        ├─► lyra-worldmodel: 
        │     Predict tool outcomes; detect drift
        │
        ├─► lyra-memory-federation:
        │     Query decentralized pools across agents
        │     Graph tier for entity relationships
        │
        ├─► lyra-causal:
        │     Build causal graph from execution traces
        │     Generate Pramana-format attestations
        │
        ├─► lyra-defense:
        │     Held-out spec tests; monitor reward hacking
        │
        ├─► lyra-evolution:
        │     If failure → MOSS source repair
        │     If repeated → skill extraction
        │
        ├─► lyra-research:
        │     If knowledge gap → trial harness experiment
        │
        └─► lyra-evals:
              Self-evaluate performance; calibrate confidence
```

---

## Part IV: Phased Implementation Timeline

### Phase 1 — Foundation (Months 1–3)
**Parallel workstreams:**

| Workstream | Output | Dependencies |
|-----------|--------|-------------|
| lyra-core: Agent Loop 2.0 | Multi-Stream, Event-Sourced, Speculative Planning | None — standalone refactor |
| lyra-memory: Graph + MMR | Knowledge graph tier, diversity reranking | None — standalone upgrade |
| lyra-mcp/security: VIPER-MCP | MCP vulnerability auditing | has_mcp_server decorator |
| lyra-autonomy: Stage 1 | Supervised → Coached transition | None — new package |

**Milestone:** Lyra can process tasks 2× faster (Multi-Stream) with verifiably safe MCP tools.

### Phase 2 — Intelligence (Months 4–7)
**Parallel workstreams:**

| Workstream | Output | Dependencies |
|-----------|--------|-------------|
| lyra-evolution: MOSS upgrade | Source-level code modification | Phase 1 agent loop |
| lyra-causal: Engine | Causal graphs + Pramana attestations | Phase 1 memory graph |
| lyra-worldmodel: Engine | Latent state + drift detection | Phase 1 memory |
| lyra-research: Trial harnesses | Sibyl-style experiment sandbox | Phase 1 agent loop |
| lyra-autonomy: Stage 2 | Coached → Monitored transition | Phase 1 autonomy |

**Milestone:** Lyra can explain its reasoning causally, learn from failed experiments, and modify its own source code safely.

### Phase 3 — Self-Awareness (Months 8–11)
**Parallel workstreams:**

| Workstream | Output | Dependencies |
|-----------|--------|-------------|
| lyra-defense: Reward shield | Spec tests + hacking detector | Phase 2 evolution |
| lyra-memory-federation | Decentralized pools + gossip | Phase 1 memory |
| lyra-evals: AGI benchmarks | CLEAR + Pseudo-Formal + BioXArena | Phase 2 components |
| lyra-causal: Counterfactual | "What if" simulation engine | Phase 2 causal |
| lyra-autonomy: Stage 3 | Monitored → Autonomous transition | Phase 2 autonomy |

**Milestone:** Lyra defends against its own optimization pressure, has decentralized memory across specialists, and benchmarks itself.

### Phase 4 — AGI Trajectory (Months 12–15)
**Integration & iteration:**

| Workstream | Output | Dependencies |
|-----------|--------|-------------|
| Full integration | All subsystems connected | Phases 1–3 |
| AGI benchmark runs | Score on BioXArena, TerminalWorld, SpecBench | Phase 3 evals |
| Self-calibration | Lyra knows what it doesn't know | Phase 3 evals |
| Autonomy: Stage 4 | Autonomous → Mentoring | Phase 3 autonomy |
| RLVR fine-tuning | PlexRL-style cluster optimization | Phase 2 causal |

**Milestone:** Lyra scores competitively on AGI-relevant benchmarks, calibrates its own confidence accurately, and can safely operate autonomously across domains.

---

## Part V: AGI Benchmark Targets

<table width="100%"><tr><td style="background: linear-gradient(135deg, #8b5cf615, #06b6d410); border-left: 4px solid #8b5cf6; padding: 12px 16px; border-radius: 0 8px 8px 0;">

<span style="color: #c084fc; font-weight: bold;">Lyra already ships</span> <span style="color: #94a3b8;">a production eval harness (`lyra-evals` v0.2.0) with SpecBench multi-level evaluation, 7 benchmark adapters, contamination guard, SLO tracking, and AER (Agent Execution Records). The targets below define the AGI trajectory — benchmarks where Lyra must match or exceed frontier models to demonstrate general intelligence.</span>

</td></tr></table>

### Evaluation Architecture (Already Built)

```
┌─────────────────────────────────────────────────────────────┐
│                    lyra-evals v0.2.0                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ SpecBench    │  │ PESS         │  │ Contamination    │  │
│  │ Multi-Level  │  │ Probabilistic│  │ Guard            │  │
│  │ (Sys/Trace/  │  │ Evaluator    │  │ (train/test      │  │
│  │  Node)       │  │              │  │  overlap detect) │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ AER Store    │  │ SLO Tracker  │  │ Harness          │  │
│  │ (Agent Exec  │  │ (latency,    │  │ Snapshot          │  │
│  │  Records)    │  │  success,    │  │ (drift gate      │  │
│  │              │  │  cost SLOs)  │  │  0.85 default)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**7 Benchmark Adapters Already Implemented:**

| Adapter | Domain | Status | pass@k Support |
|---------|--------|--------|---------------|
| **SWE-Bench Pro** | Software engineering (real GitHub issues) | Production | Yes |
| **Tau-Bench** | Tool-augmented agent tasks | Production | Yes |
| **Terminal-Bench v2** | Real terminal/sysadmin tasks | Production | Yes |
| **LoCoEval** | Long-context evaluation | Production | Yes |
| **BRIGHT** | Biomedical reasoning | Production | Yes |
| **BrowseComp+** | Web browsing comprehension | Production | Yes |
| **MultiHop QA** | Multi-hop reasoning QA | Production | Yes |

### AGI Benchmark Targets & Trajectory

<table>
<tr style="background: #7c3aed20;">
<th style="color: #c084fc;">Benchmark</th>
<th style="color: #c084fc;">Domain</th>
<th style="color: #c084fc;">Current SOTA</th>
<th style="color: #c084fc;">Lyra Target</th>
<th style="color: #c084fc;">Status</th>
<th style="color: #c084fc;">Gating Papers</th>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">SpecBench</td>
<td style="color: #94a3b8;">Reward hacking resistance</td>
<td style="color: #f87171;">0% (all frontier agents hack)</td>
<td style="color: #34d399;">&lt;5% reward hacking rate</td>
<td style="color: #34d399;">Evaluator built</td>
<td style="color: #94a3b8;">SpecBench (2605.21384), Ratchet (2605.22148)</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">SWE-Bench Pro</td>
<td style="color: #94a3b8;">Real-world software engineering</td>
<td style="color: #fbbf24;">~49% (Devin)</td>
<td style="color: #34d399;">&gt;65% resolved</td>
<td style="color: #34d399;">Adapter in production</td>
<td style="color: #94a3b8;">SWE-Bench, MOSS (2605.22794)</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">Terminal-Bench v2</td>
<td style="color: #94a3b8;">Real terminal/sysadmin tasks</td>
<td style="color: #fbbf24;">&lt;30%</td>
<td style="color: #34d399;">&gt;60%</td>
<td style="color: #34d399;">Adapter in production</td>
<td style="color: #94a3b8;">TerminalWorld, Terminal-Bench v2</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">BioXArena</td>
<td style="color: #94a3b8;">Biomedical ML agent</td>
<td style="color: #fbbf24;">0.666 (Gemini-3.1-Pro)</td>
<td style="color: #34d399;">&gt;0.80</td>
<td style="color: #fbbf24;">Planned</td>
<td style="color: #94a3b8;">BioXArena (2605.15766)</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">Agentic CLEAR</td>
<td style="color: #94a3b8;">Multi-level eval (system/trace/node)</td>
<td style="color: #fbbf24;">Dynamic taxonomy (no fixed SOTA)</td>
<td style="color: #34d399;">Full tri-level coverage</td>
<td style="color: #34d399;">SpecBench evaluator built</td>
<td style="color: #94a3b8;">Agentic CLEAR (2605.22608)</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">Pseudo-Formal</td>
<td style="color: #94a3b8;">Proof-verified reasoning eval</td>
<td style="color: #fbbf24;">Pareto-dominates LLM-judge</td>
<td style="color: #34d399;">&gt;90% precision, &gt;85% recall</td>
<td style="color: #fbbf24;">Planned</td>
<td style="color: #94a3b8;">Pseudo-Formalization (2605.20531)</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">Tau-Bench</td>
<td style="color: #94a3b8;">Tool-use + conversational agents</td>
<td style="color: #fbbf24;">~55% (Claude 4)</td>
<td style="color: #34d399;">&gt;70%</td>
<td style="color: #34d399;">Adapter in production</td>
<td style="color: #94a3b8;">Tau-Bench, τ²-Bench</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">LoCoEval</td>
<td style="color: #94a3b8;">Long-context comprehension (128K+)</td>
<td style="color: #fbbf24;">~72% (Gemini 2.5 Pro)</td>
<td style="color: #34d399;">&gt;80%</td>
<td style="color: #34d399;">Adapter in production</td>
<td style="color: #94a3b8;">LoCoEval, RULER, NIAH</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">WorkstreamBench</td>
<td style="color: #94a3b8;">Financial spreadsheet automation</td>
<td style="color: #fbbf24;">~40%</td>
<td style="color: #34d399;">&gt;65%</td>
<td style="color: #fbbf24;">Planned</td>
<td style="color: #94a3b8;">WorkstreamBench</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">HIDBench</td>
<td style="color: #94a3b8;">Host intrusion detection</td>
<td style="color: #fbbf24;">~50%</td>
<td style="color: #34d399;">&gt;75%</td>
<td style="color: #fbbf24;">Planned</td>
<td style="color: #94a3b8;">HIDBench</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">HSCO-Bench</td>
<td style="color: #94a3b8;">HW/SW co-design optimization</td>
<td style="color: #fbbf24;">&lt;30%</td>
<td style="color: #34d399;">&gt;55%</td>
<td style="color: #fbbf24;">Planned</td>
<td style="color: #94a3b8;">HSCO-Bench</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">DecisionBench</td>
<td style="color: #94a3b8;">Delegation fidelity & decision quality</td>
<td style="color: #fbbf24;">7.5–29.5%</td>
<td style="color: #34d399;">&gt;50%</td>
<td style="color: #fbbf24;">Planned</td>
<td style="color: #94a3b8;">DecisionBench</td>
</tr>

<tr>
<td style="color: #e2e8f0; font-weight: bold;">BRIGHT</td>
<td style="color: #94a3b8;">Biomedical reasoning & retrieval</td>
<td style="color: #fbbf24;">~58% (Med-Gemini)</td>
<td style="color: #34d399;">&gt;70%</td>
<td style="color: #34d399;">Adapter in production</td>
<td style="color: #94a3b8;">BRIGHT, MedPrompt</td>
</tr>
</table>

### Evaluation Methodology: CLEAR Multi-Level

<table>
<tr style="background: #06b6d420;">
<th style="color: #22d3ee;">Level</th>
<th style="color: #22d3ee;">Scope</th>
<th style="color: #22d3ee;">What It Measures</th>
<th style="color: #22d3ee;">Lyra Implementation</th>
</tr>
<tr>
<td style="color: #22d3ee; font-weight: bold;">System</td>
<td style="color: #94a3b8;">Full task completion</td>
<td style="color: #94a3b8;">End-to-end success rate, drift detection, cost efficiency</td>
<td style="color: #34d399;"><code>SystemEval</code> + <code>HarnessSnapshot</code> (drift gate 0.85)</td>
</tr>
<tr>
<td style="color: #22d3ee; font-weight: bold;">Trace</td>
<td style="color: #94a3b8;">Execution trajectory</td>
<td style="color: #94a3b8;">Reward hacking score, path efficiency, tool selection quality</td>
<td style="color: #34d399;"><code>TraceEval</code> + <code>ProbabilisticEvaluator</code> (PESS-style)</td>
</tr>
<tr>
<td style="color: #22d3ee; font-weight: bold;">Node</td>
<td style="color: #94a3b8;">Per-step actions</td>
<td style="color: #94a3b8;">Action correctness, expected vs actual, explanation quality</td>
<td style="color: #34d399;"><code>NodeEval</code> (step-level verdict: PASS/FAIL/WARN)</td>
</tr>
</table>

### SLO Framework (Already Operational)

<table>
<tr style="background: #10b98120;">
<th style="color: #34d399;">SLO Metric</th>
<th style="color: #34d399;">Target</th>
<th style="color: #34d399;">Measurement</th>
<th style="color: #34d399;">Breach Consequence</th>
</tr>
<tr>
<td style="color: #e2e8f0;">Latency (p95)</td>
<td style="color: #34d399;">&lt;5s per tool call</td>
<td style="color: #94a3b8;">Per-invocation wall-clock timing</td>
<td style="color: #f87171;">Triggers model downgrade</td>
</tr>
<tr>
<td style="color: #e2e8f0;">Success Rate</td>
<td style="color: #34d399;">&gt;85% task completion</td>
<td style="color: #94a3b8;">Rolling window (last 100 tasks)</td>
<td style="color: #f87171;">Triggers drift alert + re-eval</td>
</tr>
<tr>
<td style="color: #e2e8f0;">Cost Efficiency</td>
<td style="color: #34d399;">&lt;$0.50 per task avg</td>
<td style="color: #94a3b8;">Token usage × provider pricing</td>
<td style="color: #f87171;">Triggers routing review</td>
</tr>
<tr>
<td style="color: #e2e8f0;">Contamination</td>
<td style="color: #34d399;">0% train/test overlap</td>
<td style="color: #94a3b8;"><code>ContaminationGuard</code> checksum verification</td>
<td style="color: #f87171;">Raises <code>ContaminationError</code></td>
</tr>
<tr>
<td style="color: #e2e8f0;">Reward Hacking</td>
<td style="color: #34d399;">&lt;5% divergence</td>
<td style="color: #94a3b8;">SpecBench visible vs held-out score gap</td>
<td style="color: #f87171;">Triggers safety gate + audit</td>
</tr>
</table>

### Self-Improvement Loop via Benchmarks

<table width="100%"><tr><td style="background: #1e293b; padding: 12px 16px; border-radius: 8px;">

```
Run evals → AER Store → Gap Analysis → GEPA Prompt Evolution → Re-run evals
   │              │              │                    │
   │              │              │                    └─ SkillOpt optimizer (+23.5pts)
   │              │              └─ Identify weakest benchmark categories
   │              └─ Agent Execution Records with SLO breach logs
   └─ pass@k across all 13 benchmark targets

Drift gate (0.85): If success rate drops below 85% → auto-rollback + alert
Contamination guard: Prevents train/test overlap before any eval run
```

</td></tr></table>

### Benchmark Priority Roadmap

| Phase | Benchmarks | Success Criteria | Timeline |
|-------|-----------|-----------------|----------|
| **Phase 1 (Current)** | SWE-Bench Pro, Terminal-Bench v2, Tau-Bench, LoCoEval, BRIGHT, MultiHop QA, BrowseComp+ | All adapters passing, pass@k > baseline | Done (v0.2.0) |
| **Phase 2 (Q3 2026)** | SpecBench, Agentic CLEAR, Pseudo-Formal | Reward hacking <5%, CLEAR tri-level coverage, proof precision >90% | 2–3 mo |
| **Phase 3 (Q4 2026)** | BioXArena, WorkstreamBench, HIDBench | Score within 10% of frontier model on each | 2–3 mo |
| **Phase 4 (Q1 2027)** | HSCO-Bench, DecisionBench | All 13 benchmarks at AGI-competitive levels | 2 mo |

---

## Part VI: AGI-Critical Principles

### Principle 1: Recursive Self-Improvement
Lyra must be able to improve *its own ability to improve*. Each self-modification should make the next self-modification more effective. This is the hard takeoff trajectory.

### Principle 2: Epistemic Humility
Lyra must accurately estimate *what it doesn't know*. Self-calibration (comparing confidence to accuracy) is the foundation of trustworthy AGI. Implement via PESS-style probabilistic evaluation.

### Principle 3: Causal Understanding
Associative reasoning is not intelligence. Causal reasoning — understanding interventions, counterfactuals, and mechanisms — separates AGI from sophisticated pattern matching.

### Principle 4: Adversarial Robustness
An AGI that can be hacked isn't an AGI. Lyra must defend against reward hacking, cascade attacks, prompt injection, and MCP taint simultaneously.

### Principle 5: Graduated Autonomy
AGI doesn't emerge fully-formed. Lyra must progress through developmental stages, earning autonomy through demonstrated reliability.

---

## Part VII: What Remains (Beyond This Plan)

These are active research frontiers that Lyra should monitor but aren't ready for implementation:

| Frontier | Current State | Trigger to Implement |
|----------|--------------|---------------------|
| **Continuous learning without forgetting** | Catastrophic forgetting still unsolved for LLMs | When a paper achieves >95% retention on 10+ tasks |
| **True theory of mind** | Current ToM is shallow | When a benchmark passes human-level ToM |
| **Emergent tool creation** | Agents use but don't create tools | When MOSS-type creation is standard |
| **Multi-modal world models** | Limited to vision-language | When robotics papers converge on a standard |
| **Self-supervised AGI benchmarks** | All benchmarks are human-designed | When paper.json is widely adopted |

---

> **This plan is built from 200+ trending papers integrated into Lyra's existing 25-package architecture.**  
> **7 new subsystems + 5 major upgrades = 12 workstreams, ~15 months to AGI trajectory.**  
> **Total estimated effort: 30 engineer-months (highly parallelizable).**

---

*Part of the [Harness Engineering & Agentic AI](README.md) corpus. Built from `trending-ai-papers-may-2026.md` + `projects/lyra/`. May 2026.*
