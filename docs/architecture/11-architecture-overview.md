# Architecture

> This document describes Lyra's **TARGET architecture** — what we're building toward. For the honest current-state assessment, see [BASELINE.md](../lyra-upgrade/BASELINE.md). For implementation plans, see [lyra-upgrade/](../lyra-upgrade/).

## ⚠️ Important: CURRENT vs TARGET

This document describes the **TARGET** (planned/aspirational) architecture. Many components marked [IMPLEMENTED] below are aspirational — they exist in design docs but NOT in the current codebase. The honest baseline: Lyra currently has 5 partially-working subsystems (agents, memory, skills, hooks, coordination) and 23+ workstreams at `none` maturity. See the [Baseline Scorecard](../lyra-upgrade/BASELINE.md#2-baseline-scorecard) for per-workstream status.

## System Topology (Target Architecture)

> **Legend:** [DONE] = verified in current code. [PARTIAL] = code exists, incomplete. [PLANNED] = designed, not built. Status verified against actual `src/` codebase (June 2026).

```mermaid
graph TB
    subgraph Entry["Entry Points"]
        CLI["[IMPLEMENTED] lyra CLI<br/>(Typer + prompt_toolkit)"]
        TUI["[IMPLEMENTED] Terminal UI<br/>(Ink/React 19)"]
        ACP["[PLANNED] ACP Server<br/>(Agent Client Protocol)"]
        Voice["[PLANNED] Voice System<br/>(VAD · STT · TTS pipeline)"]
    end

    subgraph Kernel["Kernel (lyra-core)"]
        Loop["[IMPLEMENTED] AgentLoop<br/>plan → execute → verify"]
        SM["[PARTIAL] TDD State Machine<br/>IDLE → PLAN → RED → GREEN → REFACTOR → SHIP"]
        PB["[IMPLEMENTED] PermissionBridge<br/>plan | auto-edit | bypass"]
        HIR["[PLANNED] HIR Emitter<br/>(JSONL event stream)"]
        LC["[PLANNED] LifecycleBus<br/>(fan-out: chat, tool, plan, subagent, cron)"]
        AR["[PLANNED] AliasRegistry<br/>(model name resolution)"]
        PR["[PARTIAL] Pivot/Refine Loop<br/>(failure analysis → alternative → retry)"]
    end

    subgraph Tools["Tool Kernel"]
        TK["[IMPLEMENTED] ToolKernel"]
        FS["[IMPLEMENTED] Filesystem<br/>Read · Write · Edit · Glob · Grep"]
        CODE["[IMPLEMENTED] Code<br/>LSP · Analyze · Format · Typecheck"]
        WEB["[IMPLEMENTED] Web<br/>Fetch · Search · Browser"]
        DB["[PLANNED] Database<br/>Query · Schema · Migrate"]
        TS["[PLANNED] Tool Search<br/>(deferred schema · semantic match)"]
    end

    subgraph Agents["Agent System"]
        PA["[IMPLEMENTED] PrimaryAgent<br/>(orchestrator)"]
        CA["[IMPLEMENTED] CodeAgent"]
        TA["[IMPLEMENTED] TestAgent"]
        RA["[IMPLEMENTED] ReviewAgent"]
        RHA["[IMPLEMENTED] ResearchAgent"]
        UR["[PARTIAL] UnifiedRegistry<br/>(multi-index dispatch)"]
    end

    subgraph Fleet["Agent Fleet"]
        FO["[PARTIAL] FleetOrchestrator<br/>(fan-out, squads, DAG)"]
        SL["[PARTIAL] SquadLead<br/>(PM · Architect · Engineer · QA)"]
        RM["[PLANNED] RecursiveLink<br/>(latent-space comms · 75.6% token reduction)"]
    end

    subgraph Memory["Memory System (Current: flat JSON + planned 4-Tier)"]
        WM["[PARTIAL] Working Memory<br/>(active session context)"]
        IM["[PLANNED] Ingestion Memory<br/>(codebase/doc indexing)"]
        PM["[PLANNED] Persistent Memory<br/>(TKG + Field Memory hybrid)"]
        GM["[PLANNED] Graph Tier<br/>(KnowledgeGraph + WorldGraph)"]
        MR["[PLANNED] MemoryRetriever<br/>(hybrid BM25+vector · cost-sensitive)"]
        MC["[PARTIAL] MemoryConsolidator<br/>(offline pattern extraction)"]
        DREAM["[PLANNED] Dream Consolidator<br/>(Orient→Gather→Consolidate→Prune)"]
    end

    subgraph Router["Intelligent Router (PLANNED — models hardcoded)"]
        L1["[PLANNED] Cascade Layer 1<br/>(cheapest model first)"]
        L2["[PLANNED] Cascade Layer 2<br/>(mid-tier escalation)"]
        L3["[PLANNED] Cascade Layer 3<br/>(premium model fallback)"]
    end

    subgraph Evolution["Self-Evolution [PLANNED / PARTIAL]"]
        GEPA["[PLANNED] GEPA v2 Optimizer<br/>(multi-agent prompt evolution)"]
        T2S["[PARTIAL] Trace2Skill<br/>(auto-skill extraction)"]
    end

    subgraph Safety["Safety & Observability"]
        CES["[PARTIAL] Cognitive-Executive Split<br/>(Parallax concept)"]
        MAV["[PARTIAL] Multi-Agent Verifier<br/>(executor→validator→critic)"]
        AE["[PLANNED] Audit Engine<br/>(HIR replay)"]
    end

    subgraph Skills["Skills Ecosystem"]
        SR["[IMPLEMENTED] SkillRegistry<br/>(loader + router)"]
        SC["[IMPLEMENTED] SkillCurator<br/>(discovery · grading)"]
        SE["[PARTIAL] SkillEvolver<br/>(auto-optimization)"]
        SAC["[IMPLEMENTED] SkillCompactor<br/>(per-section tracking · merge · archive)"]
    end

    subgraph Autonomous["Autonomous Systems [PARTIAL]"]
        CM_L2["[PARTIAL] Continuous Mode<br/>(auto-loop)"]
        SCH["[PLANNED] Scheduler<br/>(cron + events)"]
        HK["HookEngine<br/>(27+ events)"]
        CK["Checkpoint System<br/>(snapshot · rewind · 30-day retention)"]
    end

    subgraph Providers["16+ LLM Providers"]
        Anthro["Anthropic<br/>Opus · Sonnet · Haiku"]
        DS["DeepSeek<br/>V4 Pro · Flash"]
        OAI["OpenAI<br/>GPT-4o · O3"]
        Gemini["Google<br/>Gemini 2.5/3.1"]
        Others["xAI · Mistral · Qwen<br/>Kimi · Bedrock · Ollama"]
    end

    CLI & TUI & ACP & Voice --> Loop
    Loop --> SM & PB & HIR & PR
    HIR --> LC
    Loop --> TK
    TK --> FS & CODE & WEB & DB & TS
    Loop --> PA
    PA --> CA & TA & RA & RHA
    PA --> UR
    PA --> FO --> SL
    FO --> RM
    Loop --> STM --> WM --> LTM
    STM --> MC --> LTM
    LTM --> DREAM
    DREAM -->|"enriched"| LTM & PM_L
    LTM --> PM_L & MM_L
    PM_L --> CM_L --> EM_L
    LTM --> MR
    Loop --> L1 --> L2 --> L3 --> L4 --> L5
    Loop --> GEPA --> MOSS
    MOSS --> AEvo_L
    GEPA --> T2S
    AEvo_L & MOSS --> ARIS_L
    GEPA --> PRISM
    Loop --> CES & AS & TO & MAV & IM & AE
    Loop --> SR --> SC & SL_L & SE & SAC
    Loop --> GS & CM_L2 & SCH & HK & CK
    FO & PA & Loop --> Anthro & DS & OAI & Gemini & Others
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as Lyra CLI
    participant Voice as Voice System
    participant Router as Intelligent Router
    participant Engine as AgentLoop
    participant CogExec as Cognitive-Executive Split
    participant Perms as PermissionBridge
    participant HIR as HIR Emitter
    participant Agent as Specialist Agent
    participant Fleet as FleetOrchestrator
    participant RecLink as RecursiveLink
    participant LLM as LLM Provider
    participant Tools as ToolKernel
    participant Hook as HookEngine
    participant Mem as Memory System
    participant Dream as Dream Consolidator
    participant Verify as Multi-Agent Verifier
    participant Drift as PRISM Drift Detector

    User->>CLI: "Add Redis caching to user service"
    CLI->>Voice: play(session.start, "Ready to work!")
    CLI->>Engine: run(task_description)

    Engine->>Hook: fire(SESSION_START)
    Engine->>Mem: recall(context)
    Mem-->>Engine: relevant history + skills + rules

    Engine->>Router: route(task)
    Router->>Router: classify → estimate → match → optimize
    Router-->>Engine: ModelSelection(slot=coding, model=sonnet)

    Engine->>CogExec: separate(reasoning, execution)
    CogExec-->>Engine: reasoning_ctx, execution_ctx

    Engine->>Engine: plan(steps)
    Engine->>HIR: emit(plan.created)

    loop For each step
        Engine->>Perms: check(step.action)
        Perms-->>Engine: plan-gated

        par Parallel agents
            Engine->>Fleet: fan_out(subtasks)
            Fleet->>Agent: dispatch(step_a)
            Fleet->>Agent: dispatch(step_b)
            Agent->>LLM: prompt + tools
            LLM-->>Agent: response
            Agent->>Tools: execute
            Tools-->>Agent: result
            Agent-->>Fleet: step_complete
        end

        Agent->>RecLink: share_latent_state(peer_agents)
        RecLink-->>Agent: compressed_context (75.6% fewer tokens)

        Fleet-->>Engine: aggregated_results
    end

    Engine->>Verify: verify(output, trace)
    Verify->>Verify: executor → validator → critic pipeline
    Verify-->>Engine: pass (step-level ✓, trace-level ✓, adversarial ✓)

    Engine->>Dream: consolidate(session_learnings)
    Dream->>Dream: Orient → Gather → Consolidate → Prune
    Dream-->>Mem: enriched memories stored

    Engine->>Drift: check(prompts)
    Drift-->>Engine: reliability: 99.3%

    Engine->>HIR: emit(session.complete)
    Engine->>Hook: fire(SESSION_END)
    Engine->>Voice: play(task.complete)

    Engine-->>CLI: final response
    CLI-->>User: Done. 3 files changed. Tests passing.
```

## Memory Hierarchy (with Dream Consolidation)

```mermaid
graph LR
    subgraph "Short-Term (Session)"
        STM["Sensory<br/>~500 tokens<br/>Current turn"]
    end

    subgraph "Working Memory"
        WM["Episodic<br/>~2000 tokens<br/>Recent turns"]
    end

    subgraph "Long-Term Storage"
        SM["Semantic<br/>JSON indexed<br/>Facts & knowledge"]
        PM_L2["Procedural<br/>Skills library<br/>Learned patterns"]
        STM2["Strategic<br/>Goal tracking<br/>Active objectives"]
    end

    subgraph "Meta-Cognitive"
        MM_L2["Meta<br/>Learning traces<br/>What worked/failed"]
        CM_L3["Collective<br/>Fleet knowledge<br/>Gossip memory"]
    end

    subgraph "Eternal"
        EM_L2["Eternal<br/>Cross-session<br/>Never expires"]
    end

    subgraph "Dream Consolidator (Background)"
        DC1["Phase 1: Orient<br/>Identify new knowledge<br/>from session traces"]
        DC2["Phase 2: Gather<br/>Collect related memories<br/>across all layers"]
        DC3["Phase 3: Consolidate<br/>ADD-only extraction<br/>Entity linking · Dedup"]
        DC4["Phase 4: Prune<br/>Ebbinghaus forgetting<br/>Staleness eviction · TTL"]
    end

    STM -->|"Consolidator<br/>(every 10 turns)"| WM
    WM -->|"Consolidator<br/>(session end)"| SM
    SM --> PM_L2
    PM_L2 --> STM2
    STM2 --> MM_L2
    MM_L2 --> CM_L3
    CM_L3 --> EM_L2

    SM & PM_L2 & STM2 & MM_L2 --> DC1
    DC1 --> DC2 --> DC3 --> DC4
    DC3 -->|"enriched memories"| SM & PM_L2

    MR_L["MemoryRetriever<br/>(BM25 + vector · RRF fusion<br/>verbatim-first · multi-signal)"]
    SM -.-> MR_L
    PM_L2 -.-> MR_L
    STM2 -.-> MR_L
    CM_L3 -.-> MR_L
```

## Safety Architecture (6-Layer Parallax-Style)

```mermaid
graph TB
    subgraph L0_S["Layer 0: Input Validation"]
        Input["User Task / Command"]
        Sanitize["Input Sanitization<br/>(injection detection · schema validation)"]
    end

    subgraph L1_S["Layer 1: Cognitive-Executive Separation (Parallax)"]
        Reasoning["Reasoning Context<br/>(READ-ONLY)<br/>Planning · Analysis · Memory"]
        Barrier["=== STRUCTURAL BARRIER ==="]
        Execution["Execution Context<br/>(ACTION-CAPABLE)<br/>Tools · Code · Deploy"]
    end

    subgraph L2_S["Layer 2: Permission Gating"]
        PermCheck["PermissionBridge<br/>plan | auto-edit | bypass"]
        ScopeCheck["Scope Validation<br/>(filesystem · network · shell boundaries)"]
    end

    subgraph L3_S["Layer 3: Multi-Agent Validation"]
        Executor["Executor Agent<br/>(performs action)"]
        Validator["Validator Agent<br/>(different model family)"]
        Critic["Critic Agent<br/>(reviews validator reasoning)"]
    end

    subgraph L4_S["Layer 4: Behavioral Monitoring"]
        IntentMon["Intent Monitor<br/>(action sequence analysis<br/>temporal pattern detection)"]
        AnomalyDetect["Anomaly Detection<br/>(deviation from expected<br/>behavior patterns)"]
    end

    subgraph L5_S["Layer 5: Static Analysis"]
        Shield["AgentShield<br/>(5 scanners · 102 rules<br/>secrets · injection · XSS · SQLi · path)"]
        AuditLog["Audit Engine<br/>(HIR replay · permission log<br/>full session traceability)"]
    end

    subgraph L6_S["Layer 6: Continuous Assurance"]
        DriftDetect["PRISM Drift Detector<br/>(prompt degradation monitoring<br/>auto-repair via GEPA)"]
        TEE["TEE Verifiability<br/>(cryptographic proof of<br/>guardrail execution)"]
    end

    Input --> Sanitize
    Sanitize --> Reasoning
    Reasoning --> Barrier
    Barrier -->|"approved"| Execution
    Barrier -->|"blocked (98.9% rate)"| Blocked["BLOCKED + Audit"]
    Execution --> PermCheck
    PermCheck --> ScopeCheck
    ScopeCheck --> Executor
    Executor --> Validator
    Validator --> Critic
    Critic -->|"anomaly"| Blocked
    Critic -->|"clean"| IntentMon
    IntentMon --> AnomalyDetect
    AnomalyDetect -->|"deviation"| Blocked
    AnomalyDetect -->|"normal"| Shield
    Shield --> AuditLog
    AuditLog --> DriftDetect
    DriftDetect --> TEE
    TEE --> SafeOutput["Safe Output"]

    style Barrier fill:#ff4444,stroke:#ff0000,color:#fff
    style Blocked fill:#ff4444,stroke:#ff0000,color:#fff
    style SafeOutput fill:#44ff44,stroke:#00ff00,color:#000
```

## Self-Evolving Harness Pipeline

```mermaid
flowchart TB
    subgraph Observe["1. OBSERVE: Collect Performance Data"]
        Traces["Execution Traces<br/>(HIR events · tool calls · outcomes)"]
        Metrics["Performance Metrics<br/>(success rate · latency · token usage)"]
        DriftSig["Drift Signals<br/>(prompt degradation · pattern shifts)"]
    end

    subgraph Analyze["2. ANALYZE: Identify Improvement Targets"]
        Bottleneck["Bottleneck Detection<br/>(harness inefficiencies · slow paths)"]
        Pattern["Pattern Mining<br/>(successful vs failed strategies<br/>across model families)"]
        Gap["Gap Analysis<br/>(benchmark target vs actual<br/>per-category breakdown)"]
    end

    subgraph Propose["3. PROPOSE: Generate Improvements"]
        GEPA2["GEPA v2<br/>Multi-agent prompt evolution<br/>Pareto frontier · Combee 17x speedup"]
        AEvo["AEvo Meta-Editor<br/>Procedure code edits<br/>26% relative improvement"]
        MetaHarness["Meta-Harness Loop<br/>Harness code search + optimization<br/>+7.7pts · 4x fewer tokens"]
    end

    subgraph Verify2["4. VERIFY: Adversarial Validation"]
        ARIS["ARIS 3-Stage Review<br/>1. Evidence integrity<br/>2. Result-to-claim mapping<br/>3. Claim auditing"]
        CrossModel["Cross-Model Testing<br/>Different provider families<br/>Generalization check"]
        Regression["Regression Test<br/>Performance vs baseline<br/>No degradation on holdout"]
    end

    subgraph Deploy2["5. DEPLOY: Safe Rollout"]
        Canary["Canary Release<br/>10% traffic · 24h observation"]
        Monitor["PRISM Continuous Monitor<br/>Drift detection · Alert on regression"]
        FullDeploy["Full Rollout<br/>Sustained improvement confirmed"]
    end

    Observe --> Analyze --> Propose --> Verify2
    Verify2 -->|"PASS: +5-8pts confirmed"| Deploy2
    Verify2 -->|"FAIL: regression or no improvement"| Refine["Refine & Retry<br/>(feedback loop)"]
    Refine --> Propose
    Monitor -->|"regression detected"| Rollback["Auto-Rollback<br/>Restore last known good"]
    Monitor -->|"drift detected"| Refine
    Canary -->|"degradation"| Rollback
```

## Intelligent Router Flow

```mermaid
flowchart TD
    Task["Task Input"] --> L1_L["Layer 1: Task Classifier<br/>15 categories"]
    L1_L --> L2_L["Layer 2: Complexity Estimator<br/>Score 1-10"]
    L2_L --> L3_L["Layer 3: Capability Matcher<br/>Reasoning · Vision · Context"]
    L3_L --> L4_L["Layer 4: Cost Optimizer<br/>Cascade by price"]
    L4_L --> L5_L["Layer 5: Performance History<br/>Learned success rates"]

    L5_L --> Decision{Confidence ≥ 0.75?}
    Decision -->|Yes| Execute["Execute with selected model"]
    Decision -->|No| Escalate["Escalate to next tier"]
    Escalate --> L4_L

    Execute --> Track["Track performance → Update history"]
    Track --> Result["Return result + cost breakdown"]
```

## Evolution Pipeline

```mermaid
flowchart LR
    Trace["Execution Trace<br/>(HIR events)"] --> Score["Quality Scoring<br/>(success · efficiency · novelty)"]
    Score --> Extract["Pattern Extraction<br/>(LLM + verifier)"]
    Extract --> Gen["Skill Generation<br/>(SKILL.md + tests)"]
    Gen --> Eval["Auto-Evaluation<br/>(holdout tasks)"]
    Eval -->|Pass| Deploy["Deploy Skill<br/>(registry update)"]
    Eval -->|Fail| Refine["Refine<br/>(GEPA v2 optimization)"]
    Refine --> Gen

    Deploy --> Monitor2["Continuous Monitoring<br/>(PRISM drift detection)"]
    Monitor2 -->|Regression| Rollback2["Auto-Rollback<br/>(last known good)"]
    Monitor2 -->|Underperform| Opt["Optimize<br/>(Meta-Harness + AEvo)"]
    Opt --> Refine
```

## Fleet Topology

```mermaid
graph TB
    subgraph Orchestrator["Lead Orchestrator"]
        TD["Task Decomposer"]
        DR["Dependency Resolver<br/>(DAG builder)"]
        RA_L["Resource Allocator"]
        AG["Result Aggregator"]
    end

    subgraph Squad1["Squad: api-refactor"]
        SL1["Squad Lead<br/>(Opus 4.7)"]
        PM1["PM Agent"]
        ARCH1["Architect Agent"]
        ENG1["Engineer (×3)"]
        TEST1["Test Agent"]
        REV1["Review Agent"]
    end

    subgraph Squad2["Squad: test-coverage"]
        SL2["Squad Lead<br/>(Sonnet 4.6)"]
        ENG2["Engineer (×2)"]
        TEST2["Test Agent (×2)"]
    end

    subgraph Squad3["Squad: docs-update"]
        SL3["Squad Lead<br/>(Haiku 4.5)"]
        DOC1["Docs Agent (×2)"]
        REV2["Review Agent"]
    end

    subgraph Shared["Shared Infrastructure"]
        GM["Gossip Memory<br/>(stigmergy trails)"]
        CK["Colony Knowledge Graph"]
        LS["Lesson Store<br/>(successes + failures)"]
        RL["RecursiveLink<br/>(latent-space comms)"]
    end

    Orchestrator --> Squad1 & Squad2 & Squad3
    Squad1 & Squad2 & Squad3 --> Shared
    Squad1 -.->|"RecursiveLink<br/>(latent · 75.6% token reduction)"| Squad2
    Squad2 -.->|"RecursiveLink<br/>(latent)"| Squad3
```

## Layer Architecture

```mermaid
graph LR
    subgraph L0["Layer 0: Interface"]
        CLI_L0["lyra CLI<br/>(Typer + prompt_toolkit)"]
        TUI_L0["Terminal UI<br/>(Ink/React 19 · 25 themes)"]
        ACP_L0["ACP Server<br/>(Agent Client Protocol)"]
        Voice_L0["Voice System<br/>(CESP v1.0 · 6-layer packs)"]
    end

    subgraph L1["Layer 1: Application"]
        REPL["Interactive REPL<br/>(driver · session · keybindings)"]
        CMD["Commands<br/>(run · plan · doctor · goal · fleet · theme)"]
        PROV["Providers<br/>(Anthropic · OpenAI · DeepSeek · Google · OpenRouter · Open-Weights)"]
        SKILLS_L1["Skills Runtime<br/>(56 skills · curator · loader · evolver · compaction)"]
        MEM_L1["Memory Runtime<br/>(3-tier (STM/LTM/Consolidation))"]
    end

    subgraph L2["Layer 2: Kernel"]
        LOOP["AgentLoop<br/>(plan → execute → verify)"]
        TDD["TDD Gate<br/>(RED → GREEN → REFACTOR)"]
        PERMS["PermissionBridge<br/>(plan | auto-edit | bypass)"]
        HIR_L2["HIR Emitter<br/>(JSONL event stream)"]
        TOOLS["ToolKernel<br/>(Read · Write · Edit · Grep · Glob · LSP · Web · Bash)"]
        PIVOT["Pivot/Refine<br/>(failure recovery loop)"]
    end

    subgraph L3["Layer 3: Intelligence"]
        ROUTER["Intelligent Router<br/>(5-layer · cascade · history)"]
        REASON["Deep Reasoning<br/>(CoT · Tree Search · Debate · SR2AM · RecursiveLink)"]
        RESEARCH["Research Pipeline<br/>(10-step · 7+ sources · DCI zero-index)"]
        EVOLVE["Self-Evolution<br/>(GEPA v2 · Meta-Harness · AEvo · ARIS · PRISM)"]
    end

    subgraph L4["Layer 4: Coordination"]
        FLEET["Agent Fleet<br/>(fan-out · squads · DAG · federation)"]
        COLONY["Colony Mode<br/>(persistent swarm · gossip memory)"]
        SCHED["Scheduler<br/>(cron · webhooks · triggers)"]
        HOOKS_L4["Hook System<br/>(27+ events · 5 handlers · 7 scopes)"]
    end

    subgraph L5["Layer 5: Safety (6-Layer)"]
        COGEXEC["Cognitive-Executive Split<br/>(Parallax · 98.9% block rate)"]
        SHIELD_L5["AgentShield<br/>(5 scanners · 102 rules)"]
        OBS_L5["Observability<br/>(13 categories · HIR · replay · burn reports)"]
        MAV_L5["Multi-Agent Verifier<br/>(executor→validator→critic)"]
        INTENT["Intent Monitor<br/>(behavioral anomaly detection)"]
    end

    L0 --> L1 --> L2 --> L3 --> L4 --> L5
```

## Package Dependency Graph (Expanded)

```mermaid
graph TD
    HC["harness_core"] --> LC["lyra-core"]
    LC --> LCLI["lyra-cli"]
    LC --> LAG["lyra-agents"]
    LC --> LMEM["lyra-memory"]
    LC --> LORCH["lyra-orchestration"]
    LC --> LSK["lyra-skills"]
    LC --> LEVALS["lyra-evals"]
    LC --> LMCP["lyra-mcp"]

    LCLI --> LREASON["lyra-reasoning"]
    LCLI --> LRESEARCH["lyra-research"]
    LCLI --> LEVOL["lyra-evolution"]
    LCLI --> LCOG["lyra-cognitive"]
    LCLI --> LCONT["lyra-continual"]
    LCLI --> LPERS["lyra-personalization"]
    LCLI --> LROUTER["lyra-router"]
    LCLI --> LRECLINK["lyra-recursive-link"]

    LORCH --> LCOLONY["lyra-colony"]
    LORCH --> LFLEET["lyra-fleet"]
    LORCH --> LAUTO["lyra-auto-mode"]
    LORCH --> LGOSSIP["lyra-gossip-memory"]

    LMEM --> LCOG
    LMEM --> LCONT
    LMEM --> LPERS

    LREASON --> LEVOL
    LREASON --> LVERIFY["lyra-verification"]
    LREASON --> LWORLD["lyra-world-model"]

    LRESEARCH --> LMEM
    LRESEARCH --> LKNOWLEDGE["lyra-knowledge-graph"]

    LEVOL --> LMETA["lyra-meta-evolution"]
    LEVOL --> LRSI["lyra-rsi"]

    LROUTER --> LCOST["lyra-cost"]
    LROUTER --> LSTREAM["lyra-streaming"]

    LCLI --> UIC["ui-core"]
    UIC --> UIT["ui-terminal"]
    UIT --> UITR["ui-transport"]

    LCLI --> LVOICE["lyra-voice"]
    LCLI --> LAUDIO["lyra-audio"]

    LSEC["lyra-safety"] --> LSHIELD["lyra-agentshield"]
    LSEC --> LOBS["lyra-observability"]
    LSEC --> LCONST["lyra-constitutional"]
    LSEC --> LPARALLAX["lyra-parallax"]
```

## Architectural Commitments (Updated — 13 Total)

1. **Plan Mode** — All work is plan-gated. The agent proposes, the user approves, then execution proceeds.
2. **Multi-Agent Topology** — PrimaryAgent orchestrates; specialist agents execute; fleet orchestrator scales; multi-agent verifier validates.
3. **PermissionBridge** — Three modes (plan/auto-edit/bypass) with per-tool granularity and audit logging.
4. **TDD Gate** — The RED→GREEN→REFACTOR cycle is enforced by a PreToolUse hook with numeric reward signal (KnowRL).
5. **4-Tier Memory System** — Working → Ingestion → Persistent (TKG + Field Memory) → Graph. Multi-tier memory with A-MAC 5-factor admission control, cost-sensitive retrieval across 4 stores (in-memory, SQLite, vector, graph), and Ebbinghaus-based consolidation. MemGrad pipeline for continuous optimization. Dream consolidator for offline pattern extraction (partial).
6. **Cognitive-Executive Separation** — Reasoning and execution run in structurally separated contexts (Parallax architecture). 98.9% adversarial block rate. Independent verification agent reviews all execution plans.
7. **Skill Library** — SKILL.md files with YAML frontmatter, trigger patterns, progressive disclosure (L1→L2→L3 loading), Trace2Skill auto-extraction, and per-section auto-compaction.
8. **Subagents in Worktrees** — Each subagent runs in an isolated git worktree with its own filesystem view.
9. **Multi-Agent Verifier** — Executor → Validator → Critic pipeline. Validator from different model family. 3-stage ARIS adversarial review (evidence integrity → result-to-claim → claim auditing).
10. **HIR Traces** — Every event (tool call, LLM request, plan change) emitted as JSONL to `.lyra/sessions/`. Replayable and auditable.
11. **5-Layer Intelligent Router** — Task classification → Complexity estimation → Capability matching → Cost optimization → Performance history. Confidence-thresholded escalation.
12. **Self-Evolving Harness** — GEPA v2 prompt optimization → Meta-Harness code optimization → AEvo procedure editing → ARIS adversarial review → PRISM drift detection. The harness observes, analyzes, proposes, verifies, and deploys improvements to itself.
13. **Progressive Tool Discovery** — Deferred tool schema loading with semantic tool search. 85% context savings. Auto-pruning based on task relevance.

## Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| Kernel separate from CLI | `lyra-core` has zero network deps — reusable by MCP, evals, CI, SDK | Two packages to version |
| Single Python package (`src/`), planned monorepo | Currently one package; monorepo expansion is aspirational | Requires build orchestration when expanded |
| prompt_toolkit over Textual | Faster startup, better stdin/stdout compatibility, closer to Claude Code UX | Less rich TUI out of the box |
| Optional Ink/React 19 TUI | React component model for complex UI (model picker, fleet panel, theme picker) | Requires Node.js runtime |
| HIR JSONL as source of truth | All observability flows from one event stream | ~1MB/hour disk usage |
| 3-tier memory (planned) | Working / Ingestion / Persistent (TKG+Field) / Graph tiers for multi-timescale agent learning | Consolidation needs hardening |
| Dream 4-phase consolidation | ADD-only extraction prevents overwrite; Ebbinghaus forgetting mimics human memory | Background processing adds ~2s latency per session |
| Hybrid BM25+vector retrieval | RRF fusion of keyword and semantic search; 96.6% R@5 without LLM | Slightly higher storage footprint |
| 5-layer intelligent router | Confidence-thresholded escalation prevents over-spending on simple tasks | Adds ~50ms routing latency |
| Cognitive-executive separation (PLANNED) | Aspirational — current code has basic AgentShield stub with secret detection | Requires architectural restructuring |
| RecursiveLink latent comms | 75.6% token reduction for inter-agent communication | Requires training/fine-tuning the RecursiveLink module |
| Meta-Harness self-optimization | Outer-loop harness code optimization yields +7.7pts with 4x fewer tokens | Risk of overfitting to benchmarks; mitigated by cross-model testing |
| Trace2Skill auto-extraction | Automatic skill creation from successful execution traces | Requires quality threshold to avoid noise |
| Regex-based security scanning | Fast, no external deps, catches 90% of common issues | Misses obfuscated patterns |
| PRISM drift detection | Daily automated prompt reliability monitoring with auto-repair | Requires baseline calibration per prompt |

## Innovation Lineage

Each Lyra innovation traces to its research source. The **Status** column indicates whether the component exists in the current codebase (`src/`) or is aspirational. See [`docs/research/papers.md`](docs/research/papers.md) for the complete absorption matrix and [lyra-upgrade/BASELINE.md](../lyra-upgrade/BASELINE.md) for per-workstream honesty.

| Innovation | Primary Source | Status |
|------------|---------------|--------|
| Tournament TTS | [Scaling Test-Time Compute (Meta, 2026)](https://arxiv.org/abs/2604.16529) | PLANNED |
| SR2AM Planning | [SR2AM (2026)](https://arxiv.org/abs/2605.22138) | PLANNED |
| ReasoningBank | [ReasoningBank (Google, 2025)](https://arxiv.org/abs/2509.25140) | PLANNED |
| Pivot/Refine Loop | [AutoResearchClaw (2026)](https://arxiv.org/abs/2605.20025) | PARTIAL |
| Skill-RAG Recovery | [Skill-RAG (UMich, 2026)](https://arxiv.org/abs/2604.15771) | PLANNED |
| TDD Reward Gate | [KnowRL (ZJU, 2025)](https://arxiv.org/abs/2506.19807) | PARTIAL |
| Neural GC Compaction | [NGC (Stanford, 2026)](https://arxiv.org/abs/2604.18002) | PLANNED |
| Tool-Call Verification | [Knowing-Doing Gap (2026)](https://arxiv.org/abs/2605.14038) | PLANNED |
| Cascade Router | [FrugalGPT (Stanford, 2023)](https://arxiv.org/abs/2305.05176) | PLANNED (models hardcoded) |
| Confidence Escalation | [RouteLLM (Berkeley, 2024)](https://arxiv.org/abs/2406.18665) | PLANNED |
| SOP Role Topology | [MetaGPT (ICLR 2024)](https://arxiv.org/abs/2308.00352) | PLANNED |
| Reflexion Loop | [Reflexion (NeurIPS 2023)](https://arxiv.org/abs/2303.11366) | PARTIAL |
| Skill Library | [Voyager (TMLR 2024)](https://arxiv.org/abs/2305.16291) | IMPLEMENTED (basic YAML parser) |
| GEPA v2 Optimizer | [GEPA (ICLR 2026 Oral)](https://arxiv.org/abs/2310.03714) | PLANNED |
| PRM Verifier | [Qwen PRM (2025)](https://arxiv.org/abs/2501.07301) | PLANNED |
| DAG Teams | [SemaClaw (Midea, 2026)](https://arxiv.org/abs/2604.11548) | PLANNED |
| AutoResearchClaw | [AutoResearchClaw (2026)](https://arxiv.org/abs/2605.20025) | PLANNED |
| RecursiveLink | [RecursiveMAS (2026)](https://arxiv.org/abs/2604.25917) | PLANNED |
| Meta-Harness | [Meta-Harness (2026)](https://arxiv.org/abs/2603.28052) | PLANNED |
| AEvo Meta-Editing | [AEvo (2026)](https://arxiv.org/abs/2605.13821) | PLANNED |
| ARIS Adversarial Review | [ARIS (2026)](https://arxiv.org/abs/2605.03042) | PLANNED |
| PRISM Drift Detection | [PRISM (2026)](https://arxiv.org/abs/2605.14454) | PLANNED |
| Cognitive-Executive Split | [Parallax (2026)](https://arxiv.org/abs/2604.12986) | PLANNED |
| Symbolic STM | [TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory) | PLANNED |
| Progressive Disclosure | [claude-mem](https://github.com/thedotmack/claude-mem) | IMPLEMENTED (3-level skill loading) |
| Dream Consolidation | Claude Code, [Mem0](https://github.com/mem0ai/mem0) | PLANNED |
| Pre-Indexed KG | [CodeGraph](https://github.com/colbymchenry/codegraph) | PLANNED |
| DCI Zero-Index | [DCI-Agent-Lite](https://github.com/DCI-Agent/DCI-Agent-Lite) | PLANNED |
| Verbatim-First Retrieval | [MemPalace](https://github.com/MemPalace/mempalace) | PLANNED |
| Skills as Memory | [Acontext](https://github.com/memodb-io/Acontext) | PLANNED |
| Progressive Tool Discovery | Claude Code Tool Search | PLANNED |

## Plans Index

| Plan | Focus | Lines |
|------|-------|-------|
| [LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md](plans/LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md) | Master plan — 16 dimensions | ~1286 |
| [LYRA_ULTRA_PLAN_7_SKILLS_ECOSYSTEM.md](plans/LYRA_ULTRA_PLAN_7_SKILLS_ECOSYSTEM.md) | Skills ecosystem — 56 skills, 14 packs | ~500 |
| [LYRA_ULTRA_PLAN_8_VOICE_AUDIO_SYSTEM.md](plans/LYRA_ULTRA_PLAN_8_VOICE_AUDIO_SYSTEM.md) | Voice & audio — packs, pipeline, dictation | ~400 |
| [LYRA_ULTRA_PLAN_9_TOOLS_UNIVERSE.md](plans/LYRA_ULTRA_PLAN_9_TOOLS_UNIVERSE.md) | Tools universe — 200+ tools, 20 toolsets | ~450 |
| [LYRA_ULTRA_PLAN_10_MODEL_ROUTER_V2.md](plans/LYRA_ULTRA_PLAN_10_MODEL_ROUTER_V2.md) | Intelligent router — 5 layers, cost cascading | ~400 |
| [LYRA_ULTRA_PLAN_11_AUTONOMOUS_SYSTEMS.md](plans/LYRA_ULTRA_PLAN_11_AUTONOMOUS_SYSTEMS.md) | Autonomous systems — goals, continuous, hooks | ~400 |
| [LYRA_ULTRA_PLAN_12_AGENT_FLEET_SWARM.md](plans/LYRA_ULTRA_PLAN_12_AGENT_FLEET_SWARM.md) | Agent fleet & swarm — parallel, colony, federation | ~400 |
| [**LYRA_ULTRA_PLAN_13_BREAKTHROUGH_SYNTHESIS.md**](plans/LYRA_ULTRA_PLAN_13_BREAKTHROUGH_SYNTHESIS.md) | **Breakthrough synthesis — 6 AGI gaps, meta-evolution, safety, Dream memory** | ~500 |

## Further Reading

- [`docs/architecture/`](docs/architecture/) — Canonical architecture reference
- [`docs/architecture/safety-architecture.md`](docs/architecture/safety-architecture.md) — Parallax-style cognitive-executive separation
- [`docs/architecture/memory-consolidation.md`](docs/architecture/memory-consolidation.md) — Dream 4-phase consolidation design
- [`docs/architecture/harness-evolution.md`](docs/architecture/harness-evolution.md) — Meta-optimization loop architecture
- [`docs/research/papers.md`](docs/research/papers.md) — 79 paper absorption matrix
- [`docs/research/repos.md`](docs/research/repos.md) — 50+ repository absorption matrix
- [`docs/research/breakthrough-synthesis.md`](docs/research/breakthrough-synthesis.md) — Plan 13 key findings
- [`docs/roadmap.md`](docs/roadmap.md) — Development roadmap
- [`README.md`](17-README.md) — Project overview with all visualizations
- [`SOUL.md`](SOUL.md) — Project persona and operating principles
- [`plans/`](plans/) — All ultra plans (Plans 6-13)
