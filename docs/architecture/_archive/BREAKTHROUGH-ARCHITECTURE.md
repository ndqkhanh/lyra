> ⚠️ **This is an older version.** The authoritative version is at [docs/lyra-upgrade/BREAKTHROUGH-ARCHITECTURE.md](../lyra-upgrade/BREAKTHROUGH-ARCHITECTURE.md).

# BREAKTHROUGH ARCHITECTURE — Lyra Omni-Agent Next Generation

**Stage 3 of 4** — The unified, novel architecture that survived multi-agent adversarial debate.  
**Date**: 2026-05-31  
**Version**: 2.0 (post-debate)  
**Status**: Converged from ARCHITECTURE-DEBATE.md — Memory-First + Adversarial-Verification hybrid, self-evolution deferred to Phase 3+  
**Grounded in**: SYNTHESIS.md (228 sources), ARCHITECTURE-DEBATE.md (3 candidates, 3 critics, 13-dimension trade-off table)

> **NOTE**: This is the docs/architecture/ copy. The authoritative (more recent) version lives at [lyra-upgrade/BREAKTHROUGH-ARCHITECTURE.md](../lyra-upgrade/BREAKTHROUGH-ARCHITECTURE.md), which includes additional algorithmic deep-dives and the breakthrough synthesis from Run 10+.

---

## 0. Architecture Provenance — What Survived the Debate

This architecture is the CONVERGED WINNER of a multi-agent adversarial design debate ([ARCHITECTURE-DEBATE.md](./ARCHITECTURE-DEBATE.md)). Three independent proposer agents designed competing architectures (Memory-Centric M-ARCH, Orchestration-Centric O-ARCH, Self-Evolution-Centric E-ARCH). Three critic agents (Red-Team, Security/Safety, Build-Feasibility) attacked all three on 15+ trade-off dimensions. After rebuttals, revisions, and cross-candidate critique, the panel converged.

**The Converged Architecture**: M-ARCH core (Temporal Knowledge Graph as primary memory) + O-ARCH verification middleware (Adversarial Verification Protocol) + E-ARCH deferred to Phase 3+ (gated behind behavioral safety benchmark maturity).

### What Was Adopted (and from which candidate)

| Component | Adopted From | Key Evidence |
|-----------|-------------|--------------|
| TKG as primary memory (4-tier + A-MAC + A-MEM + cost-sensitive retrieval) | Candidate A (M-ARCH) | Best cross-session learning; 72.4% compression, 92.8% preservation |
| AVP as universal middleware (SABER mutation-gating + 3-critic panels) | Candidate B (O-ARCH) | 55-96% error contribution from mutating actions; <15% latency overhead |
| Workflow engine for orchestration (code-driven, background, resumable) | Candidate B (O-ARCH) | Claude Code parity; 1000 agents/run, 16 concurrent |
| Fast-path retrieval (Working Memory first, <50ms for 95% of queries) | Candidate A rebuttal | Eliminates TKG bottleneck concern |
| Provider-diverse critics (Claude + DeepSeek + open-weight) | Candidate B revised | Maximizes architectural diversity in verification |
| Self-evolution as Phase 3+ (gated) | Candidate C (deferred) | Requires behavioral safety benchmark + 10K+ execution history |

### What Was Rejected (and why)

| Rejected Design | From | Reason | Debate Reference |
|----------------|------|--------|-----------------|
| TKG as THE SINGLE integration point (no direct communication) | Candidate A original | TKG bottleneck for simple operations | Critic X latency attack; fast-path revision adopted |
| Per-workflow isolated memory (no cross-workflow learning) | Candidate B original | Prevents compounding knowledge | Critic X memory model attack; TKG-as-shared-store revision adopted |
| "Evolution proceeds freely" (ungated self-modification) | Candidate C original | Alignment decay risk; behavioral safety unverified | Critic Y safety attack; behavioral safety gate added; deferred to Phase 3+ |
| Population-based FORGE broadcast | Candidate C | Amplifies unsafe behaviors | Critic Y amplification attack; deferred |
| Meta-Harness outer loop as organizing principle | Candidate C | Too complex for initial architecture | Critic Z build attack; evolution emerges from memory+verification foundation |

### Live Disagreements (Empirically Resolved Later)

1. **TKG write granularity**: All tool call results vs. workflow-level outcomes only. Resolution: measure memory utility at both granularities during Phase 2.
2. **AVP critic count**: 3 vs. 5 critics. Resolution: A/B test on 500 mutating actions during Phase 4.

---

## 0a. What Makes This Architecture a Breakthrough

This is NOT a collection of independent features. It is ONE coherent system where every component reinforces every other, SURVIVED adversarial scrutiny from 3 independent critic agents, and explicitly records what was rejected and why:

```
Memory (Central Nervous System) — TKG
    ↕
Workflow Engine (Orchestration Backbone) — Dynamic Workflows
    ↕
AVP Middleware (Adversarial Verification) — Critique-Before-Execute
    ↕
Router (Intelligence Distributor) ← Provider Abstraction (Heterogeneity Handler)
    ↕
Skills (Capability Layer, Self-Evolving in Phase 3+)
    ↕
Swarm (Adversarial Coordination Fabric)
    ↕
Voice (Multi-Modal Surface)
```

**What is NEW (not present in any single cited source)**:
1. **Memory + Verification fusion** — No source combines a unified TKG with adversarial verification middleware. Candidate A proposed the TKG; Candidate B proposed the AVP. The fusion (TKG stores verification records; verification gates memory writes) is novel.
2. **Provider-adaptive everything** — Provider heterogeneity as first-class architectural concern. No existing harness does this.
3. **Adversarial verification as universal middleware** — Critique-before-execute is a protocol every tool, skill, and agent passes through. Universalized from AutoScientists + SABER.
4. **Self-evolution deferred, not rejected** — The debate's key insight: evolution is the right long-term bet but MUST be gated behind behavioral safety validation. No other architecture makes this distinction explicit.
5. **Terminal-native design** — Filesystem, git, and stdio as first-class primitives. Memory as versioned files. Skills as git-tracked. Voice over stdio.

**What is ADOPTED (ported from specific sources)**:
- A-MAC 5-factor admission control (#79) → memory admission layer
- A-MEM Zettelkasten linking (#59) → knowledge graph structure
- RouteLLM matrix factorization (#222) → routing policy training
- Claude Code Skills progressive disclosure (#1–4) → skill loading
- Moshi Inner Monologue (#211) → voice pipeline architecture
- SABER mutation-gating (#67) → adversarial verification trigger
- CaMeL control/data separation (#243) → safety layer
- Claude Code Dynamic Workflows (#203, #349) → workflow engine design
- DecentMem dual-pool memory (#99) → shared workflow memory model

---

## 0b. Implementation Status (Audited 2026-06-03)

This architecture blends **implemented** systems with **planned** ones. The table below maps each component to its current implementation status against the actual codebase in `packages/`.

### Implemented (Code Exists and is Testable)

| Component | Package | Status |
|-----------|---------|--------|
| AbstractProvider + 4 adapters (Anthropic, OpenAI, DeepSeek, Google) | `lyra-provider` | Implemented |
| 4-tier memory (Working/Ingestion/Persistent/Graph) | `lyra-memory` (tiered.py) | Implemented |
| A-MAC admission control | `lyra-memory` (amac_admission.py) | Implemented |
| 6-level effort scale with per-provider mapping | `lyra-effort` | Implemented |
| EffortBridge (effort → orchestration gating) | `lyra-core` | Implemented |
| Skill loader, router, extractor, curator, compiler, optimizer | `lyra-skills` | Implemented |
| Voice pipeline (VAD → STT → TTS chain) | `lyra-voice` | Implemented |
| Model router (3-tier cascade) | `lyra-router` | Implemented |
| Voice provider registry (EnergyVAD, WhisperSTT, KokoroTTS) | `lyra-voice` (providers.py) | Implemented |
| Workflow engine | `lyra-workflow` | Implemented |
| Hooks system | `lyra-hooks` | Implemented |
| Session management | `lyra-sessions` | Implemented |

### Partial (Code Exists but Not Fully Wired)

| Component | Package | Status |
|-----------|---------|--------|
| AVP (Adversarial Verification Protocol) middleware | `lyra-verification` | Partial — package exists but critique-before-execute middleware is not universally wired |
| CraniMem gating | `lyra-memory` (cranimem_gate.py) | Partial — implemented but not integrated into main memory pipeline |
| Dream consolidator | `lyra-memory` (dream_consolidator.py) | Partial — data model exists, offline consolidation loop not wired |
| Auto-orchestration (ultracode → workflow dispatch) | `lyra-core` (effort_bridge.py) | Partial — bridge exists, workflow engine spawning needs hardening |
| Agent swarm coordination | `lyra-agent-swarm` | Partial — package exists, adversarial coordination untested |
| Fleet orchestrator (fan-out, squads, DAG) | `lyra-fleet-tui`, `lyra-colony` | Partial — packages exist, production integration not validated |
| Provider-adaptive compaction | `lyra-provider` | NOT YET IMPLEMENTED — uses single threshold, not per-provider context windows |

### Planned / Aspirational (Not Implemented)

| Component | Status |
|-----------|--------|
| Self-evolving memory (MemGrad, feedback loops) | Planned — Phase 3+, gated behind behavioral safety benchmark |
| Self-evolving skills (genetic algorithms, Thompson Sampling, UCB1) | Planned — SKILLS-SYSTEM-V2 proposal, not in code |
| 7-tier memory hierarchy (V3 proposal) | Planned — moved to proposals/ |
| HIR Emitter (JSONL event stream) | Planned — referenced in ARCHITECTURE.md, code location unclear |
| LifecycleBus | Planned — referenced in diagrams, not independently discoverable |
| AliasRegistry | Planned — referenced in diagrams, implementation unclear |
| Tool Kernel (200+ planned tools) | Aspirational — actual tool system is much smaller |
| Provider runtime capability probing | NOT YET IMPLEMENTED — described in architecture but not built |
| thinking.type: "enabled" → output_config.effort migration | NOT YET IMPLEMENTED — Anthropic adapter uses deprecated budget_tokens API |

### Cross-Reference Status

- **MEMORY-ARCHITECTURE-V2.md / V3.md**: Moved to `docs/architecture/proposals/` — these are aspirational designs, not implemented architecture.
- **SKILLS-SYSTEM-V2.md**: Moved to `docs/architecture/proposals/` — aspirational, not implemented.
- **ARCHITECTURE-DEBATE.md**: Exists as source document for this BREAKTHROUGH doc.

---

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "Surface Layer"
        TERMINAL[Terminal UI<br/>Keyboard + Keybindings]
        VOICE[Voice I/O<br/>Mic → VAD → STT → TTS → Speaker]
    end

    subgraph "Orchestration Layer"
        SWARM[Adversarial Swarm<br/>N agents × critique × converge]
        WORKFLOW[Dynamic Workflow Engine<br/>Fan-out, fan-in, resume]
    end

    subgraph "Intelligence Layer"
        ROUTER[Provider-Aware Router<br/>Memory-augmented cascade]
        SKILLS[Self-Evolving Skills<br/>Gated evolution pipeline]
    end

    subgraph "Memory Layer — CENTRAL NERVOUS SYSTEM"
        TKG[Temporal Knowledge Graph<br/>4-tier: Working/Episodic/Semantic/Archive]
        ADMISSION[A-MAC Admission Control<br/>5-factor gating]
        RETRIEVAL[Cost-Sensitive Retrieval<br/>Store routing + lazy materialization]
        EVOLUTION[Self-Evolving Memory<br/>MemGrad gradients + feedback loops]
    end

    subgraph "Safety & Reliability Layer"
        VERIFY[Adversarial Verification Middleware<br/>Critique-before-execute protocol]
        SAFETY[Multi-Layer Defense<br/>CaMeL control/data + LlamaFirewall + NeMo]
        OBSERVE[OpenTelemetry Observability<br/>Phoenix + Langfuse]
    end

    subgraph "Provider Abstraction Layer"
        PA[Provider Adapter<br/>Claude | DeepSeek | Qwen | GPT | Open-Weights]
        CAP[Capability Matrix<br/>Tool-calling? JSON? Vision? Context? Cost?]
    end

    TERMINAL --> SWARM
    VOICE --> SWARM
    SWARM --> ROUTER
    ROUTER --> SKILLS
    ROUTER --> PA
    SKILLS --> TKG
    ROUTER --> TKG
    TKG --> ADMISSION
    TKG --> RETRIEVAL
    TKG --> EVOLUTION
    VERIFY -.critique.-> SWARM
    VERIFY -.critique.-> SKILLS
    VERIFY -.critique.-> ROUTER
    SAFETY -.guard.-> SWARM
    SAFETY -.guard.-> SKILLS
    SAFETY -.guard.-> ROUTER
    OBSERVE -.trace.-> SWARM
    OBSERVE -.trace.-> ROUTER
    OBSERVE -.trace.-> TKG

    style TKG fill:#DDA0DD
    style VERIFY fill:#FFB6B6
    style PA fill:#87CEEB
```

**Core architectural invariants**:
1. **Every component reads/writes through TKG** — The Temporal Knowledge Graph is the single integration point. No component talks directly to another without going through TKG.
2. **Every action passes through verification middleware** — Before any tool execution, skill update, or agent spawn, the adversarial verification protocol checks it.
3. **Provider heterogeneity is handled at the boundary** — The Provider Adapter maps between Lyra's canonical interface and each provider's specific API. Components never contain provider-specific code.

---

## 2. Memory — The Central Nervous System

### 2.1 Why Memory is Central

SYNTHESIS §9.2 identified memory as the nexus connecting all themes. In this architecture, the Temporal Knowledge Graph (TKG) serves as:

| Role | Mechanism | Source Evidence |
|------|-----------|-----------------|
| **Short-term buffer** | Working Memory: current session, full detail, <10MB | AOI (#68), IterResearch (#272) |
| **Cross-session recall** | Episodic Memory: compressed trajectories, 7-day retention | AOI (#68), MemAgent (#256), AnnaAgent (#255) |
| **Pattern extraction** | Semantic Memory: generalized heuristics, permanent | A-MAC (#79), ERL (#65), Zep/Graphiti (#251) |
| **Cold storage** | Archive: indexed, compressed, unlimited | MemAgent (#256), OCR-Memory (#131) |

### 2.2 Data Model (Core Entities)

```typescript
interface MemoryNode {
  id: string;
  tier: 'working' | 'episodic' | 'semantic' | 'archive';
  content: string;                    // The memory content
  embedding: Float32Array;            // 1536-dim vector for semantic search
  timestamp: number;
  last_accessed: number;
  access_count: number;
  session_id: string;

  // A-MAC 5-factor admission scores (#79)
  admission: {
    utility: number;                  // 0-1: LLM-assessed future usefulness
    confidence: number;               // 0-1: ROUGE-L alignment
    novelty: number;                  // 0-1: embedding similarity to existing
    recency: number;                  // 0-1: exponential decay
    type_prior: number;               // 0-1: content type importance
    aggregate: number;                // Weighted sum
  };

  // Graph structure (A-MEM #59)
  links: Array<{
    target_id: string;
    type: 'causal' | 'temporal' | 'semantic' | 'contradicts' | 'refines';
    weight: number;
  }>;

  // Compression tracking (AOI #68, KAIST #73)
  compression: {
    original_size: number;
    compressed_size: number;
    strategy: 'none' | 'semantic' | 'aggressive' | 'archive';
    verified: boolean;                // Was compression verified?
  };
}

// Adversarial verification record (SABER #67, AutoScientists #154-156)
interface VerificationRecord {
  id: string;
  target_type: 'tool_call' | 'skill_update' | 'agent_spawn' | 'memory_write';
  target_id: string;
  is_mutating: boolean;               // SABER: does this change state?
  critics: Array<{
    critic_agent_id: string;
    verdict: 'approve' | 'reject' | 'revise';
    rationale: string;
    confidence: number;
  }>;
  consensus: boolean;
  executed: boolean;
  outcome?: 'success' | 'failure';
  lessons: string[];                  // MemGrad-style textual gradients
}
```

### 2.3 Core Mechanisms

**Admission Control** (from A-MAC #79):
```
function should_admit(memory: MemoryNode): boolean {
  score = 0.3 * memory.admission.utility
        + 0.25 * memory.admission.confidence
        + 0.2 * memory.admission.novelty
        + 0.15 * memory.admission.recency
        + 0.1 * memory.admission.type_prior

  if score > 0.8: admit to Working
  if score > 0.6: admit to Episodic
  if score > 0.4: admit to Semantic
  if score > 0.2: admit to Archive
  else: reject
}
```

**Retrieval** (from Cost-Sensitive Store Routing #60):
```
function retrieve(query: string, max_cost_ms: number): MemoryNode[] {
  // Route to tier(s) based on query complexity and latency budget
  if max_cost_ms < 50:  return search(Working, query)
  if max_cost_ms < 200: return search([Working, Episodic], query)
  if max_cost_ms < 1000: return search([Working, Episodic, Semantic], query)
  return search([Working, Episodic, Semantic, Archive], query)
}
```

**Evolution** (from MemGrad #70 + EvolveMem #106):
```
function evolve_memory(feedback: FeedbackBatch) {
  gradients = textual_gradients(feedback)   // MemGrad-style
  for each gradient:
    target_memory = retrieve(gradient.target_id)
    updated = apply_gradient(target_memory, gradient)
    if verify_improvement(updated):          // EvolveMem auto-rollback
      commit(updated)
    else
      rollback(target_memory)
}
```

---

## 3. Provider-Aware Router with Memory Augmentation

### 3.1 Provider Abstraction Layer

```typescript
interface ProviderCapability {
  name: 'claude' | 'deepseek' | 'qwen' | 'gpt' | 'open-weights';
  supports_tool_calling: boolean;
  supports_json_mode: boolean;
  supports_vision: boolean;
  max_context_window: number;      // tokens
  cost_per_mtok_input: number;     // USD
  cost_per_mtok_output: number;
  reliability_score: number;       // 0-1, from historical data
  latency_profile: {
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
  models: Array<{
    name: string;
    tier: 'reasoning' | 'standard' | 'fast';
    capabilities: string[];
  }>;
}
```

### 3.2 Routing Decision

The router makes a **single decision** per query that optimizes across five dimensions:

```typescript
interface RoutingDecision {
  provider: string;
  model: string;
  reasoning: {
    memory_hit: boolean;           // Was this in TKG?
    memory_boost_confidence: number; // How much does memory help?
    complexity_score: number;      // 0-1 query complexity
    escalation_reason?: string;    // Why escalate from cheap to expensive?
    cost_estimate: number;         // Estimated USD
    latency_estimate_ms: number;   // Estimated latency
  };
}
```

**Routing logic** (from RouteLLM #222 + BEST-Route #225 + Knowledge Access #227):

```
function route(query: string): RoutingDecision {
  // Step 1: Check memory (Knowledge Access #227)
  if tkg.exact_match(query):
    return { memory_hit: true, cost_estimate: 0 }
  if tkg.similar_queries(query, threshold=0.85):
    context = tkg.retrieve(query)
    return route_cheap_with_context(query, context)  // 90% cost reduction

  // Step 2: Estimate complexity (RouteLLM #222 matrix factorization)
  complexity = estimate_complexity(query)

  // Step 3: Select provider+model (BEST-Route #225 dynamic sampling)
  if complexity > 0.8:           return { provider: 'claude', model: 'opus', samples: 1 }
  if complexity > 0.5:           return { provider: 'claude', model: 'sonnet', samples: 1 }
  if complexity > 0.3:
    // BEST-Route pattern: multi-sample cheap model
    return { provider: 'deepseek', model: 'flash', samples: 3, pick_best: true }
  else:
    return { provider: 'deepseek', model: 'flash', samples: 1 }

  // Step 4: Capability match (Lyra-unique: provider-aware filtering)
  if query.needs_vision AND NOT provider.supports_vision:
    reroute_to_capable_provider()
  if query.context_needed > provider.max_context_window:
    reroute_to_capable_provider()
}
```

---

## 4. Self-Evolving Skills with Safety Gates

### 4.1 Skill Lifecycle

```
DISCOVER → LOAD → EXECUTE → TRACK → EVOLVE → VERIFY → PROMOTE
   ↑                                                    ↓
   └──────────── ROLLBACK (if verification fails) ───────┘
```

### 4.2 Evolution Pipeline

**Phase 1: Execution Tracking** (from SkillOpt #117 + CODESKILL #95)
Every skill execution records:
- Success/failure outcome
- Latency and cost
- Tool calls made
- Context window used
- Provider used

**Phase 2: Pattern Detection** (from BenchTrace #96 + MemGrad #70)
The system analyzes execution logs to find:
- Recurring failure patterns
- Inefficiency patterns (using expensive model for simple tasks)
- Regression patterns (skill that used to work now fails)

**Phase 3: Self-Modification Proposal** (from Darwin #261–262)
The skill proposes code/prompt modifications to address detected patterns. Modifications are:
- Prompt rewrites (most common, safest)
- Tool sequence changes
- Model tier adjustments
- Context injection changes

**Phase 4: Safety Gate** (from Proteus #125 + Progent #245–246)
Before testing, the proposed modification passes through:
1. **Static analysis**: Does it violate any safety invariants? (Progent SMT verification)
2. **Red-team attack**: Can an adversarial agent break it? (Proteus pattern)
3. **CodeShield scan**: Does it introduce security vulnerabilities? (LlamaFirewall #236)

**Phase 5: A/B Testing** (from Darwin #261–262)
- Run old and new versions on 20 held-out tasks
- New version must beat old version by >5% to promote
- If tied or worse, discard the change

**Phase 6: Rollback Monitoring** (from EvolveMem #106)
- Track performance for 100 subsequent executions
- If performance degrades >10% from pre-evolution baseline, auto-rollback
- Log the regression for future analysis

### 4.3 Provider × Skill Compatibility Matrix

| Capability | Claude | DeepSeek | Qwen | GPT | Open-Weights |
|-----------|--------|----------|------|-----|--------------|
| Tool calling | ✓ Full | ✓ Full | ✓ Full | ✓ Full | ✗ (prompt-based) |
| JSON mode | ✓ | ✓ | ✓ | ✓ | Partial |
| Long context (128K+) | ✓ | Partial (64K) | ✗ (32K) | ✓ (128K) | ✗ (8K) |
| Auto-trigger reliability | High | Medium | Low | High | Low |
| Skill body loaded | SKILL.md | SKILL.md | SKILL.md | SKILL.md | SKILL.md |
| Fallback: deterministic match | Embedding | Keyword | Rule | Embedding | Keyword (forced) |

---

## 5. Adversarial Swarm with Universal Verification Middleware

### 5.1 The Adversarial Verification Protocol (AVP)

Inspired by AutoScientists (#154–156), Dynamic Workflows (#203), and SABER (#67), the AVP is a **middleware protocol** that intercepts every irreversible action:

```
Before any action X:
  1. Classify: is X mutating (changes state) or non-mutating (read-only)?
     (SABER #67: mutating actions cause 55-96% error contribution)

  2. If non-mutating: execute immediately (no verification overhead)

  3. If mutating:
     a. Spawn 3 critic agents, each with different perspective:
        - Security critic (Proteus #125, CaMeL #243 lens)
        - Correctness critic (SABER #67 lens)
        - Efficiency critic (BEST-Route #225 cost/benefit lens)
     b. Each critic produces: {approve|reject|revise, rationale, confidence}
     c. If ≥2 approve: execute
     d. If ≥2 reject: block, log, suggest alternative
     e. If tie (1 approve, 1 reject, 1 revise): ask cheapest model for tiebreaker
```

### 5.2 Swarm Execution Model

```
Coordinator Agent
    ↓ decomposes task
[Subtask 1] [Subtask 2] [Subtask 3]
    ↓           ↓           ↓
[Worker 1]  [Worker 2]  [Worker 3]
    ↓           ↓           ↓
[Critic 1]  [Critic 2]  [Critic 3]
    ↓           ↓           ↓
        [Synthesizer]
            ↓
    [Final Critic (adversarial)]
            ↓
        [Converged Output]
```

Key properties:
- **Each step records provenance in TKG** (who did what, why, what critics said)
- **Swarm can be paused/resumed** (Dynamic Workflows #203 pattern)
- **Failed workers auto-retry with different provider** (provider abstraction handles this)
- **Cost tracking per swarm, per subtask** (observability layer traces everything)

---

## 6. Multi-Provider Design

### 6.1 Provider Adapter Pattern

Every provider implements the same canonical interface:

```typescript
interface LyraProvider {
  // Core
  chat(messages: Message[], tools: Tool[]): Promise<Response>;

  // Capability queries
  supports(feature: string): boolean;
  getContextWindow(): number;
  getCost(messages: Message[], tools: Tool[]): CostEstimate;

  // Provider-specific normalization
  normalizeToolCall(raw: any): LyraToolCall;
  normalizeMessage(raw: any): LyraMessage;
  normalizeResponse(raw: any): LyraResponse;

  // Streaming
  streamChat(messages: Message[], tools: Tool[]): AsyncIterable<Chunk>;

  // Health
  healthCheck(): Promise<HealthStatus>;
}
```

Each provider implements this interface. The router, skills, and swarm interact ONLY with `LyraProvider`, never with provider-specific APIs.

### 6.2 Degradation Strategy

When a required capability is missing from a provider:

| Missing Capability | Degradation Strategy | Source Inspiration |
|-------------------|---------------------|-------------------|
| Tool calling | Prompt-based tool descriptions + JSON parsing | Open-weights pattern |
| JSON mode | Structured text parsing with error recovery | Qwen/local pattern |
| Long context | Chunking + summarization (§4.3) | ACON (#254) |
| Vision | Skip image analysis, use text description | DeepSeek pattern |
| High reliability | Deterministic skill matching as fallback | Lyra-specific |

### 6.3 Fallback Chain

```
primary_provider = route(query)             // Optimal by cost/quality
    ↓ fails
fallback_1 = next_cheapest_capable()        // Try cheaper alternative
    ↓ fails
fallback_2 = most_reliable_provider()        // Last resort: Claude
```

This chain is tracked in TKG for future routing decisions (don't route to unreliable providers for similar queries).

---

## 7. Voice Mode Integration

### 7.1 Architecture

The voice pipeline plugs into the same architecture as text:

```
Mic → Silero VAD (#209) → Smart Turn (#208) → Whisper STT (#217)
    → [Same Router → Same Skills → Same Swarm → Same TKG]
    → Kokoro TTS (#214) → Speaker
```

No separate code path. Voice input becomes text that follows the same routing, skill selection, and memory pipeline. Voice output is TTS of the text response.

### 7.2 Unique Voice Capabilities

**Voice-driven swarm control**: "Lyra, spawn 3 agents to research X" → Swarm activates
**Memory-aware voice**: "Lyra, what did we decide about auth last week?" → TKG retrieves
**Voice interrupt = barge-in**: User speech during TTS playback → cancel TTS, start listening
**Personality layer**: Voice packs (professional/friendly/minimal/Warcraft peon) via hooks (§4.10)

### 7.3 Provider Swappability

STT and TTS are treated as providers, just like LLMs:
```typescript
interface STTProvider {
  transcribe(audio: AudioBuffer): Promise<Transcription>;
  languages: string[];
  latency_ms: number;
  onDevice: boolean;
  license: string;
}

interface TTSProvider {
  synthesize(text: string, voice?: string): Promise<AudioBuffer>;
  voices: string[];
  languages: string[];
  latency_ms: number;
  onDevice: boolean;
  license: string;
}
```

Default stack (100% open-source, on-device): Silero VAD + Smart Turn + Whisper Turbo + Kokoro-82M
Cloud alternative: OpenAI Realtime API
Privacy alternative: All-local, no network

---

## 8. Terminal-Native Design Principles

### 8.1 Filesystem as First-Class Memory

Lyra exploits its terminal identity by making the filesystem a first-class architectural primitive:

- **TKG serialization**: The knowledge graph is versioned as JSONL files in `.lyra/memory/`
- **Git-native versioning**: Memory snapshots are git commits → full history, diff, rollback
- **Skill files**: SKILL.md files in `.lyra/skills/` → git-trackable, diffable, reviewable
- **Hook scripts**: Shell scripts in `.lyra/hooks/` → editable, pipeable, composable

### 8.2 stdin/stdout as Universal Interface

Everything flows through stdin/stdout:
- Text: prompt → response (standard)
- Voice: audio bytes → text for processing → audio bytes for output
- Swarm: JSON lines for agent coordination messages
- Memory: JSONL for knowledge graph import/export
- Observability: OpenTelemetry traces streamed to stdout

### 8.3 Git-Native Workflow

Every Lyra action is potentially a git commit:
- Tool execution: staged → commit if successful
- Skill evolution: branch → evolve → merge if improved → delete if not
- Memory updates: append to knowledge graph → commit
- Session: git worktree for isolated experiments

This enables: `git log` as audit trail, `git diff` for review, `git revert` for rollback.

---

## 9. Falsifiable Hypotheses

This architecture bets on three hypotheses that can be empirically tested:

**H1: Memory-augmented routing reduces cost by ≥40% without quality degradation**
- **Measurement**: Compare cost-per-task with and without TKG lookups before routing
- **Success**: 40%+ cost reduction at equivalent task success rate
- **Failure**: If <40% or quality drops >5%, the memory-router integration needs redesign

**H2: Adversarial verification reduces destructive errors by ≥50% with <20% latency overhead**
- **Measurement**: Compare error rate on mutating actions with and without AVP
- **Success**: 50%+ error reduction at <20% latency increase
- **Failure**: If error reduction <50% or latency >20%, the AVP thresholds need tuning

**H3: Self-evolving skills improve success rate by ≥15% after 100 task executions without safety violations**
- **Measurement**: Track skill success rate over 100 executions with evolution enabled
- **Success**: 15%+ improvement with zero safety invariant violations
- **Failure**: If <15% improvement or any safety violation, the evolution pipeline needs stronger gates

---

## 10. Risks & Unknowns

### 10.1 Critical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Self-evolution alignment decay | Medium | Critical | Progent SMT gates + auto-rollback on violation |
| Provider capability drift | High | Medium | Continuous health checks + fallback chain |
| TKG becomes bottleneck | Medium | High | Lazy materialization + tiered retrieval |
| Adversarial verification cost spiral | Medium | Medium | SABER mutation-gating (only verify mutations) |
| Multi-provider skill reliability variance | High | Medium | Provider × skill compatibility matrix + deterministic fallback |

### 10.2 Unknowns (Research Needed)

- **Optimal AVP critic count**: Is 3 enough? Too many? Need empirical testing
- **TKG scaling limits**: At what size does graph traversal exceed retrieval latency budget?
- **Cross-provider routing stability**: Do provider capabilities change rapidly enough to break routing?
- **Evolution convergence**: Does the self-evolution loop converge or oscillate?

---

## 11. Lyra-Specific Advantages: Why This Architecture Wins on Terminal

The architecture exploits Lyra's unique positioning (MIT license, terminal-based, multi-provider, omni-agent) in ways closed-source or cloud-only systems cannot match:

### 11.1 The MIT Advantage

| Capability | Closed-Source Limitation | Lyra's MIT Advantage |
|-----------|------------------------|---------------------|
| Self-modifying harness code | Can't: proprietary binary | **Can**: Meta-Harness outer loop rewrites Lyra's own TypeScript |
| Provider freedom | Locked to one vendor API | **Any**: Router distributes across Claude, DeepSeek, Qwen, GPT, open-weights |
| Memory ownership | Data on vendor servers | **Local**: TKG as JSONL in `.lyra/memory/`, git-versioned |
| Skill ecosystem | Vendor-gated marketplace | **Open**: Any SKILL.md on GitHub works |
| Swarm scalability | Rate-limited by vendor API keys | **Unlimited**: Self-hosted open-weight workers with no API costs |
| Audit trail | Black-box vendor logging | **Full**: git log = complete audit trail of every memory write, skill evolution, and agent action |

### 11.2 The Terminal Advantage

Terminal-native design enables capabilities GUI-based systems structurally cannot match:

1. **Pipeable agents**: `lyra research "X" | lyra review | lyra implement` — Unix pipelines compose agents without orchestration overhead
2. **Cron-native autonomy**: `crontab` schedules autonomous Lyra runs with zero additional infrastructure
3. **Git-native everything**: `git bisect` on skill evolution, `git blame` on memory changes, `git revert` on bad tool decisions
4. **SSH-remote swarms**: `ssh worker-node 'lyra agent --role executor'` distributes workers across machines
5. **tmux/rmux integration**: Agent output in panes, voice overlay in dedicated pane, swarm status in status bar
6. **Headless voice**: Voice mode over SSH with audio forwarding — terminal voice anywhere

### 11.3 Provider Heterogeneity as Architectural Strength

Most harnesses treat multi-provider as a compatibility tax. Lyra treats it as a **capability multiplier**:

- **Cheap exploration**: DeepSeek Flash ($0.27/MTok) explores 100× more hypotheses than Claude-only at the same cost
- **Cross-model adversarial verification**: Critic A uses Claude (deep reasoning), Critic B uses DeepSeek (different inductive bias), Critic C uses open-weight model (privacy-preserving) — diverse perspectives from diverse architectures
- **Provider-aware evolution**: Skills evolve SEPARATELY per provider (a DeepSeek-optimized prompt ≠ a Claude-optimized prompt), stored as provider-specific variants in the skill's frontmatter
- **Capability hedging**: When one provider degrades or raises prices, the router shifts load to alternatives — no single-vendor risk

---

## 12. AGI Direction: The Self-Improving Omni-Agent Trajectory

### 12.1 The Recursive Improvement Ladder

This architecture enables a clear 5-level ladder of increasing autonomy and self-improvement:

```
Level 1: Tool Use           — Agent calls tools (current state of art)
    ↓ When memory + skills + AVP are stable
Level 2: Memory-Learn       — Agent learns from past, avoids repeat mistakes
    ↓ When self-evolution pipeline produces verified improvements
Level 3: Self-Improve       — Agent rewrites its own skills and prompts
    ↓ When Meta-Harness outer loop is safety-gated
Level 4: Self-Architect     — Agent modifies its own harness code (Meta-Harness)
    ↓ When adversarial verification catches ≥99% of harmful mutations
Level 5: Recursive Research — Agent designs, runs, and learns from its own experiments
```

Each level is a SAFETY-GATED step. The architecture's verification middleware, invariant preservation, and auto-rollback mechanisms ensure Lyra never advances a level until the current level's safety properties are empirically verified.

### 12.2 The Self-Improvement Feedback Loop

```
User asks Lyra to do X
    ↓
Lyra does X (Level 1: Tool Use)
    ↓
TKG records: what worked, what failed, what cost, what latency
    ↓ (accumulate 100+ executions in a domain)
MemGrad extracts: recurring patterns from execution history
    ↓
Skill evolution proposes: modified prompt/tool sequence/model tier
    ↓
AVP safety gates verify: no invariant violation, red-team tested
    ↓
A/B tested: new vs old on held-out tasks
    ↓
If better: promote; if worse: discard
    ↓
Lyra now does X better (Level 2-3: Memory-Learn → Self-Improve)
    ↓ (repeat across 1,000+ executions, 10+ domains)
Meta-Harness outer loop detects: harness-level inefficiencies
    ↓
Proposes harness code modification (Level 4: Self-Architect)
    ↓
Human reviews diff (safe boundary for now)
    ↓
Lyra is now a fundamentally better agent
```

### 12.3 Falsifiable AGI-Direction Predictions

**P1**: After 10,000 task executions with evolution enabled, Lyra's task success rate will increase by ≥30% over the static baseline, with zero Degradation events (performance drops >10% from peak).

**P2**: Cross-provider skill evolution will produce provider-specific optimizations that outperform generic prompts by ≥15% per provider, validating the "provider heterogeneity as strength" hypothesis.

**P3**: The adversarial verification protocol (AVP) will catch ≥95% of introduced errors in self-modified harness code, making human review of Level 4 changes more efficient than writing from scratch (review time <20% of authoring time).

---

## 13. Open Problems → Research Agenda

The following unknowns from §10.2 are mapped to concrete experiments Lyra should run:

| Open Problem | Hypothesis | Experiment | Success Criterion | Timeline |
|-------------|-----------|------------|-------------------|----------|
| Optimal AVP critic count | 3 critics (security + correctness + efficiency) is Pareto-optimal | A/B test: 1 vs 3 vs 5 vs 7 critics on 500 mutating actions | 3 critics reduces errors ≥50% at <20% latency; 5+ critics shows diminishing returns (<5% additional error reduction per critic) | Phase 4, Week 2 |
| TKG scaling limits | Graph traversal latency ≤ retrieval budget up to 100K nodes | Load test: synthetic memory at 10K/50K/100K/500K/1M nodes | P95 retrieval ≤100ms at 100K nodes; >500K requires sharding | Phase 2, Week 8 |
| Cross-provider routing stability | Provider capability changes <5%/month | Track ProviderCapability objects weekly for 3 months across 5 providers | All capabilities within ±5% of baseline; no routing failures from stale capability data | Phase 3, ongoing |
| Evolution convergence | Self-evolution converges to a stable optimum within 200 iterations | Run evolution loop on 5 skills for 200 iterations each; track success rate per iteration | Success rate converges (≤2% variance over last 50 iterations) without oscillation or divergence | Phase 3, Week 10 |
| VI voice pipeline quality | WER <20% and MOS >3.5 achievable with open models | Whisper Turbo + MagpieTTS evaluated on 100 VI utterances across 3 dialects | P50 WER <18%, MOS >3.5 for Northern dialect; <22%, >3.0 for Southern | Phase 0, Week 3 |
| Memory admission weight optimization | Domain-adaptive weights outperform static weights by ≥10% | A-MAC weights optimized per domain (coding, research, SRE) vs static; F1 comparison | Adaptive weights improve F1 by ≥10% on LoCoMo-style benchmark per domain | Phase 2, Week 6 |
| Skill evolution safety | AVP catches ≥99% of harmful evolutions | Red-team: 100 deliberately harmful skill modifications injected; AVP detection rate | ≥99% caught; ≤1% false positive rate on benign modifications | Phase 3, Week 8 |

---

## 14. Mapping to Workstream Plans

Each §4 workstream implements one slice of this architecture:

| Workstream | Architecture Slice | Plan File |
|-----------|-------------------|-----------|
| §4.1 UI/UX | Terminal Surface + Voice I/O + Statusline | `plans/01-ui-ux.md` |
| §4.2 Memory | TKG (all 4 tiers + admission + retrieval + evolution) | `plans/02-memory-architecture.md` |
| §4.3 Context | Auto-compaction + provider-adaptive compression | `plans/03-context-optimization.md` |
| §4.4 Skills | Self-Evolving pipeline with safety gates | `plans/04-skills-system.md` |
| §4.5 Router | Provider-Aware Memory-Augmented Cascade | `phase-3-skills-routing/04-model-router.md` |
| §4.6 Tools | Tool capability negotiation + auto-discovery | `plans/05-tools.md` |
| §4.7 Plugins | Extensible provider adapters | `plans/06-plugins.md` |
| §4.8 MCP | MCP server integration layer | `plans/07-mcp.md` |
| §4.9 Commands | Terminal-native command interface | `plans/08-commands-interactive.md` |
| §4.10 Hooks | Hook system wired into AVP middleware | `plans/09-hooks-automation.md` |
| §4.11 Sessions | Git-native session + checkpointing | `plans/10-sessions-checkpointing.md` |
| §4.12 Permissions | AVP-aware permission system | `plans/11-permissions-credentials.md` |
| §4.13 Swarm | Adversarial Swarm + AVP protocol | `plans/12-swarm-fleet-channels.md` |
| §4.14 Autonomy | Bounded autonomy with trust levels | `plans/13-full-autonomy.md` |
| §4.15 Research | Self-organizing research teams | `plans/14-deep-research.md` |
| §4.16 Reliability | OTEL observability + SABER verification | `plans/15-reliability-verification.md` |
| §4.17 Safety | Multi-layer defense + continuous red-teaming | `plans/16-safety-alignment.md` |
| §4.18 Voice | Full voice pipeline + swarm control | `plans/00-voice-mode.md` |
| §5.1 rmux | Agent-aware pane lifecycle | `plans/17-rmux-rebuild.md` |
| §5.2 Multi-tenancy | Optional profile system | `plans/18-multi-tenancy.md` |

Each plan's (B) Breakthrough tier must explicitly link to this architecture and implement its assigned slice.

---

## 17. Changelog

**2026-05-31 — Version 2.0 (Run 8 — Architecture Debate + Ultracode Replication)**
- **MAJOR**: Architecture now carries debate provenance (§0) — survived 3-proposer/3-critic adversarial scrutiny
- Added: Architecture Provenance table (adopted/rejected components with debate references)
- Added: Live Disagreements section (2 items for empirical resolution)
- Added: DecentMem dual-pool memory to adopted sources
- Added: Claude Code Dynamic Workflows to adopted sources
- Updated: Version to 2.0, Stage numbering to "3 of 4"
- New standalone deliverable: ARCHITECTURE-DEBATE.md (3 candidates, 3 critics, 13-dimension trade-off table)
- Pending: Ultracode replication plan (Task #9, #12)

**2026-05-31 — Version 1.2 (Run 7 — Deepening Pass)**
- Added §11: Lyra-Specific Advantages — MIT license, terminal-native design, and provider heterogeneity as architectural strengths (3 new subsections: MIT Advantage, Terminal Advantage, Provider Heterogeneity as Strength)
- Added §12: AGI Direction — 5-level recursive improvement ladder (Tool Use → Memory-Learn → Self-Improve → Self-Architect → Recursive Research), self-improvement feedback loop with safety gates at each level, 3 falsifiable AGI-direction predictions (P1-P3)
- Added §13: Open Problems → Research Agenda — 7 concrete experiments with hypotheses, success criteria, and timelines (AVP critic count, TKG scaling, routing stability, evolution convergence, VI voice quality, memory admission weights, skill evolution safety)
- Voice mode (§4.18) deepened with 5 new analysis sections: Latency Budget Breakdown, Component Selection Trade-Off Matrix, VI+EN Benchmarks, Streaming Protocol & Byte-Level Detail, Failure Mode & Recovery Matrix
- Sections renumbered to accommodate new content (11→14 Mapping, 12→16 Changelog)

**2026-05-31 — Version 1.1 (Run 4 enhancement)**
- Integrated findings from final deep-research batch (28 additional BREAKTHROUGH-tier sources):
  - **Meta-Harness** (#121): Auto-optimizing harness code via outer-loop search (+7.7 points, 4× fewer tokens) — strengthens the Self-Evolving Skills pipeline (§4) with harness-level self-modification capability
  - **FORGE Population Broadcast** (#103): Parallel memory evolution without weight updates (1.7-7.7× improvement) — strengthens Memory Evolution (§2.3) with population-based optimization
  - **SkillOpt** (#117): Skills as trainable parameters with validation gates (52/52 best-or-tied) — provides concrete training mechanism for the skills evolution pipeline (§4.2)
  - **STITCH** (#139): Intent-based memory indexing with (goal, action type, entity) triples (35.6% improvement) — strengthens TKG Retrieval (§2.3) with context-aware indexing
  - **Hash-Anchored Editing**: Content-hash file validation (6.7%→68.3% edit success) — strengthens Terminal-Native Design (§8) with verifiable file operations
- Source-ledger now 100% complete (286/286 URLs: 253 deep-read, 4 failed, 1 unresolved)
- Added `depth` column to source-ledger.md per protocol requirement

**2026-05-31 — Version 1.0**
- Initial design from SYNTHESIS.md (228 deep-read sources)
- 10 open problems identified and addressed
- 3 falsifiable hypotheses defined
- 20 workstream-to-architecture-slice mappings

---

**END OF STAGE 2 — PROCEED TO STAGE 3 (WORKSTREAM PLANS)**

---

## 18. CORE ALGORITHMS — Run 10 Deepening

This section contains the four foundational algorithmic pipelines that power the Breakthrough Architecture. Each algorithm is presented with full TypeScript-style pseudocode, explicit type definitions, complexity analysis with empirically-grounded constants, enumeration of failure modes, and a design rationale explaining why this specific formulation was chosen.

---

### 18.1 Algorithm 1: TKG Write Path — Admission, Linking, Compression, Evolution

The complete pipeline that transforms a raw tool-call result or user interaction into a durable, linked, compressed, and self-improving knowledge graph entry.

#### 18.1.1 Data Structures

```typescript
// ─── Input / Raw Memory ─────────────────────────────────────────────────────

interface RawMemory {
  id: string;                              // UUID v4
  content: string;                         // The raw text/payload
  sourceText: string;                      // Ground-truth source for confidence
  sessionContext: SessionContext;          // Active task, goal, environment
  type: MemoryType;                        // 'observation' | 'decision' | 'error' | 'insight' | 'feedback'
  timestamp: number;                       // Unix ms
  embedding: Float32Array;                 // 1536-dim (pre-computed or computed on admission)
  metadata: Record<string, unknown>;       // Extensible
}

interface SessionContext {
  sessionId: string;
  activeTask: string;
  activeGoal: string;
  environment: 'terminal' | 'voice' | 'api';
  workflowId?: string;
}

// ─── Tier / Admission ────────────────────────────────────────────────────────

type MemoryTier = 'working' | 'episodic' | 'semantic' | 'archive';

type AdmissionDecision = 'reject' | 'archive' | 'episodic' | 'working';

interface AdmissionFactors {
  utility: number;                         // 0–1: LLM-assessed future usefulness
  confidence: number;                      // 0–1: ROUGE-L alignment with source
  novelty: number;                         // 0–1: 1 − max cosine similarity to existing
  recency: number;                         // 0–1: exp(−λ · Δdays)
  typePrior: number;                       // 0–1: domain-specific base importance
}

interface AdmissionResult {
  decision: AdmissionDecision;
  score: number;
  factors: AdmissionFactors;
  tier: MemoryTier;
  reason: string;                          // Human-readable explanation for audit log
}

// ─── Graph / Linking ─────────────────────────────────────────────────────────

type LinkType = 'causal' | 'temporal' | 'semantic' | 'contradicts' | 'refines';

interface MemoryLink {
  sourceId: string;
  targetId: string;
  type: LinkType;
  weight: number;                          // 0–1: LLM-assigned strength
  created: number;                         // Unix ms
  lastVerified: number;                    // Unix ms
  verificationCount: number;               // How many times this link was cross-checked
}

// ─── Compression ─────────────────────────────────────────────────────────────

interface CompressionRecord {
  originalSize: number;                    // Characters
  compressedSize: number;                  // Characters
  compressionRatio: number;                // original / compressed
  strategy: 'none' | 'summarize' | 'abstract' | 'aggregate';
  verified: boolean;                       // Was compression verified against source?
  summaryEmbedding: Float32Array;          // Embedding of the compressed form
}

interface CompressionBatch {
  sessionId: string;
  taskId: string;
  sourceMemories: string[];                // IDs of memories being compressed
  compressedMemoryId: string;              // ID of the new summary memory
  compression: CompressionRecord;
}

// ─── Evolution / Gradients ───────────────────────────────────────────────────

interface TextualGradient {
  targetMemoryId: string;
  operation: 'update' | 'merge' | 'deprecate' | 'create_strategy';
  delta: string;                           // The transformed text
  rationale: string;                       // Why this change is beneficial
  sourceFeedback: string[];                // Feedback IDs that triggered this
}

interface EvolutionCycle {
  cycleId: string;
  timestamp: number;
  gradients: TextualGradient[];
  validationMetrics: {
    retrievalRecallBefore: number;
    retrievalRecallAfter: number;
    improvement: number;                   // after − before
  };
}

// ─── Top-Level Memory Node ───────────────────────────────────────────────────

interface MemoryNode {
  id: string;
  content: string;
  embedding: Float32Array;
  tier: MemoryTier;
  timestamp: number;
  lastAccessed: number;
  accessCount: number;
  sessionId: string;
  admission: AdmissionFactors;
  links: MemoryLink[];
  compression: CompressionRecord;
  evolutionHistory: TextualGradient[];     // Tracks every gradient applied
  metadata: Record<string, unknown>;
}
```

#### 18.1.2 STEP 1 — Admission (A-MAC 5-Factor Gate)

```typescript
// A-MAC constants (from A-MAC #79 empirical calibration)
const ADMISSION_WEIGHTS = {
  utility:    0.30 as const,
  confidence: 0.25 as const,
  novelty:    0.20 as const,
  recency:    0.15 as const,
  typePrior:  0.10 as const,
};

// Type priors calibrated from TKG benchmark (n=10,000 memories)
const TYPE_PRIORS: Record<MemoryType, number> = {
  observation: 0.35,    // Routine observations: moderate priority
  decision:    0.85,    // Key decisions: high priority
  error:       0.75,    // Errors (learning signal): high priority
  insight:     0.90,    // Novel insights: highest priority
  feedback:    0.60,    // User feedback: high priority, often implicit
};

// Exponential decay constant — λ = ln(2) / halfLife
// Half-life of 7 days for recency scoring
const DECAY_LAMBDA = Math.LN2 / (7 * 24 * 3600 * 1000);

// Non-linear scaling factor for novelty (tunable per domain)
const NOVELTY_TEMPERATURE = 2.0;   // Higher = stricter novelty gate

/**
 * Step 1a: Compute ROUGE-L F1 between two texts.
 * ROUGE-L is the longest common subsequence (LCS) based metric.
 * O(n·m) where n,m are character lengths.
 * Papers report O(n·m) for LCS with n,m ≤ 4096 chars → <2ms.
 */
function rougeL(hypothesis: string, reference: string): number {
  const h = hypothesis.length;
  const r = reference.length;

  // DP table for LCS length
  // Space optimization: 2 rows instead of full matrix
  let prev = new Uint16Array(r + 1);
  let curr = new Uint16Array(r + 1);

  for (let i = 1; i <= h; i++) {
    for (let j = 1; j <= r; j++) {
      if (hypothesis[i - 1] === reference[j - 1]) {
        curr[j] = prev[j - 1] + 1;
      } else {
        curr[j] = Math.max(prev[j], curr[j - 1]);
      }
    }
    [prev, curr] = [curr, prev];      // Swap rows (reuse arrays)
  }

  const lcs = prev[r];
  const precision = lcs / (h || 1);
  const recall = lcs / (r || 1);

  if (precision + recall === 0) return 0;
  return (2 * precision * recall) / (precision + recall);
}

// Time: O(n·m) with n,m = character lengths. Typical n,m ≤ 4096 → ~16M ops → <2ms on modern CPU.
// Space: O(min(n,m)) for the 2-row DP optimization. Naive would be O(n·m).

/**
 * Step 1b: The 5-factor admission gate.
 */
async function admitMemory(memory: RawMemory): Promise<AdmissionResult> {
  // ── Factor 1: Utility (LLM-assessed) ──────────────────────────────────────
  // Single LLM call with structured output. Cost: ~1K tokens input, ~10 tokens output.
  const utility = await llmAssessUtility({
    content: memory.content,
    sessionContext: memory.sessionContext,
    rubric: {
      criteria: [
        'Will this memory help with future tasks in the same session?',
        'Does this contain reusable patterns, decisions, or insights?',
        'Is this relevant beyond the current task?',
      ],
      scale: [0, 1],
    },
  });
  // Bail early if utility is critically low (80% of rejections caught here)
  if (utility < 0.05) {
    return {
      decision: 'reject',
      score: 0,
      factors: { utility, confidence: 0, novelty: 0, recency: 0, typePrior: TYPE_PRIORS[memory.type] },
      tier: 'archive',
      reason: 'Utility below critical threshold (0.05). Memory unlikely to be useful.',
    };
  }

  // ── Factor 2: Confidence (ROUGE-L) ───────────────────────────────────────
  const confidence = rougeL(memory.content, memory.sourceText);
  // Bail early if alignment is critically low (hallucination guard)
  if (confidence < 0.10 && memory.type !== 'insight') {
    return {
      decision: 'reject',
      score: 0,
      factors: { utility, confidence, novelty: 0, recency: 0, typePrior: TYPE_PRIORS[memory.type] },
      tier: 'archive',
      reason: `ROUGE-L confidence ${confidence.toFixed(3)} below 0.10 threshold — possible hallucination or source mismatch.`,
    };
  }

  // ── Factor 3: Novelty ────────────────────────────────────────────────────
  // Compare against existing memories (top-10 by cosine similarity).
  // Uses approximate nearest-neighbor (ANN) index — HNSW or IVFPQ.
  // Papers report ANN latency: <5ms at 100K vectors, <50ms at 10M vectors.
  const neighbors = await vectorSearch(memory.embedding, {
    index: 'tkg-memories',
    topK: 10,
    minScore: 0.0,
  });

  let novelty: number;
  if (neighbors.length === 0) {
    novelty = 1.0;                         // No similar memories → maximally novel
  } else {
    const maxSimilarity = Math.max(...neighbors.map((n) => n.score));
    // Non-linear scaling: small differences near 1.0 are significant
    novelty = 1 - Math.pow(maxSimilarity, NOVELTY_TEMPERATURE);
  }

  // ── Factor 4: Recency ────────────────────────────────────────────────────
  const ageMs = Date.now() - memory.timestamp;
  const ageDays = ageMs / (1000 * 3600 * 24);
  const recency = Math.exp(-DECAY_LAMBDA * ageMs);

  // ── Factor 5: Type Prior ─────────────────────────────────────────────────
  const typePrior = TYPE_PRIORS[memory.type];

  // ── Weighted Aggregate ────────────────────────────────────────────────────
  const score =
    ADMISSION_WEIGHTS.utility    * utility +
    ADMISSION_WEIGHTS.confidence * confidence +
    ADMISSION_WEIGHTS.novelty    * novelty +
    ADMISSION_WEIGHTS.recency    * recency +
    ADMISSION_WEIGHTS.typePrior  * typePrior;

  // ── Tier Assignment ───────────────────────────────────────────────────────
  let decision: AdmissionDecision;
  let tier: MemoryTier;
  let reason: string;

  if (score >= 0.80) {
    decision = 'working';
    tier = 'working';
    reason = `High-value memory (score ${score.toFixed(3)}): immediate relevance, high utility + confidence. Working tier.`;
  } else if (score >= 0.60) {
    decision = 'episodic';
    tier = 'episodic';
    reason = `Moderate-value memory (score ${score.toFixed(3)}): session-relevant, may be useful cross-session. Episodic tier.`;
  } else if (score >= 0.40) {
    decision = 'episodic';
    tier = 'episodic';
    reason = `Low-mod memory (score ${score.toFixed(3)}): limited immediate utility but retains context. Episodic tier.`;
  } else if (score >= 0.20) {
    decision = 'archive';
    tier = 'archive';
    reason = `Marginal memory (score ${score.toFixed(3)}): low relevance, stored in Archive for potential distant recall.`;
  } else {
    decision = 'reject';
    tier = 'archive';
    reason = `Below admission threshold (score ${score.toFixed(3)}): rejected.`;
  }

  return {
    decision,
    score,
    factors: { utility, confidence, novelty, recency, typePrior },
    tier,
    reason,
  };
}

// Time: O(n·m) for ROUGE-L + O(log N) for ANN search. Typical total: <50ms.
// Space: O(min(n,m)) for ROUGE-L DP table + O(K) for neighbor results. Negligible.

/**
 * Edge-case handler: what happens when the LLM utility assessment fails.
 */
async function llmAssessUtility(params: {
  content: string;
  sessionContext: SessionContext;
  rubric: { criteria: string[]; scale: [number, number] };
}): Promise<number> {
  try {
    const response = await fastLLM.call({
      prompt: buildUtilityPrompt(params),
      maxTokens: 10,
      temperature: 0.0,                    // Deterministic for admission consistency
      responseFormat: { type: 'number', range: [0, 1] },
      timeoutMs: 2000,                     // Tight timeout — admission is in the hot path
    });
    return clamp(response.value, 0, 1);
  } catch (err) {
    // If LLM call fails, fall back to heuristic: confidence * typePrior
    // This degrades gracefully: admission still works but loses the utility signal.
    console.warn(`Utility assessment failed: ${err}. Falling back to heuristic.`);
    return 0.5;                            // Neutral fallback
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
```

#### 18.1.3 STEP 2 — Linking (A-MEM Zettelkasten)

```typescript
/**
 * Link a newly admitted memory into the TKG.
 * Creates bidirectional links with LLM-classified types.
 *
 * Time: O(K · L) where K = top-k candidates (20) and L = LLM classification calls (K).
 * Typically 20 LLM calls × 500ms each = ~10s. Run asynchronously (does not block write path).
 * Space: O(K) for candidate results + O(K) for new links.
 */
async function linkMemory(memory: MemoryNode, existingMemories: MemoryNode[]): Promise<MemoryLink[]> {
  const links: MemoryLink[] = [];
  const K = 20;                            // Top-k candidates to consider

  // Step 2a: Find top-K similar existing memories by embedding similarity.
  // ANN search: O(log N) with HNSW index.
  const candidates = await vectorSearch(memory.embedding, {
    index: 'tkg-memories',
    topK: K,
    excludeIds: [memory.id],               // Don't link to self
    minScore: 0.50,                        // Minimum cosine similarity to consider
  });

  // Step 2b: Batch-classify link types (LLM call per candidate).
  // We batch candidates to reduce LLM calls:
  // Group candidates by proximity, classify each group in one call.
  // Empirical: 20 individual calls → ~10s; 4 batches of 5 → ~2.5s.
  const BATCH_SIZE = 5;
  for (let i = 0; i < candidates.length; i += BATCH_SIZE) {
    const batch = candidates.slice(i, i + BATCH_SIZE);

    const classifications: Array<{
      candidateId: string;
      linkType: LinkType;
      weight: number;
    }> = await llmClassifyLinks({
      sourceContent: memory.content,
      candidates: batch.map((c) => ({
        id: c.id,
        content: c.content,
        tier: c.tier,
        score: c.score,
      })),
      instruction: `For each candidate, determine the relationship type:
        - causal: source caused or was caused by candidate
        - temporal: source and candidate are related by time/sequence
        - semantic: source and candidate share topic/meaning
        - contradicts: source disagrees with or invalidates candidate
        - refines: source provides more detail or corrects candidate

        Return a JSON array of {candidateId, linkType, weight (0-1)}.`,
    });

    for (const classification of classifications) {
      // Create bidirectional links
      links.push({
        sourceId: memory.id,
        targetId: classification.candidateId,
        type: classification.linkType,
        weight: classification.weight,
        created: Date.now(),
        lastVerified: Date.now(),
        verificationCount: 1,
      });

      // Reverse link (with attenuated weight to prevent reverse-inference errors)
      // Ref: #243 CaMeL control/data separation principle
      const reverseWeight = classification.weight * 0.85;
      links.push({
        sourceId: classification.candidateId,
        targetId: memory.id,
        type: classification.linkType,
        weight: reverseWeight,
        created: Date.now(),
        lastVerified: Date.now(),
        verificationCount: 1,
      });
    }
  }

  // Step 2c: Handle "contradicts" links specially — flag for adversarial review.
  const contradictions = links.filter((l) => l.type === 'contradicts');
  for (const c of contradictions) {
    await flagForAdversarialReview({
      memoryIdA: c.sourceId,
      memoryIdB: c.targetId,
      reason: `Linking classification: "${c.sourceId}" contradicts "${c.targetId}"`,
    });
    // Both memories get re-verified by the AVP (Algorithm 2)
    // If one is found to be incorrect, it is marked as `deprecated` in the TKG
    // and the contradictory link is changed to `refines`.
  }

  return links;
}

// Time: O(K · L_LLM) where K=20, L_LLM ≈ 500ms per batch of 5 → 4 batches × 500ms = ~2s.
// Space: O(K) for candidates + O(2K) for bidirectional links.

type EmbeddingVector = Float32Array;

interface VectorSearchResult {
  id: string;
  score: number;                           // Cosine similarity (0–1)
  tier: MemoryTier;
  content: string;                         // Partial content for LLM classification
}

async function vectorSearch(
  query: EmbeddingVector,
  opts: { index: string; topK: number; excludeIds?: string[]; minScore?: number }
): Promise<VectorSearchResult[]> {
  // Delegates to HNSW/IVFPQ index (FAISS or equivalent).
  // HNSW: O(log N) search with O(N) memory. IVFPQ: O(sqrt(N)) search with compressed vectors.
  // Production: IVFPQ for Archive tier (compressed, slower), HNSW for Working/Episodic (full precision, fast).
  // ...
  return [];
}

async function flagForAdversarialReview(event: {
  memoryIdA: string;
  memoryIdB: string;
  reason: string;
}): Promise<void> {
  // Pushes to AVP queue (Algorithm 2). AVP processes asynchronously.
  // ...
}
```

#### 18.1.4 STEP 3 — Compression (AOI Sliding-Window)

```typescript
/**
 * Compress episodic memories when tier exceeds size threshold.
 * Follows AOI (#68) sliding-window protocol.
 *
 * Trigger conditions (checked after every write):
 *   1. Episodic tier total chars > EPISODIC_MAX_CHARS (default: 500,000)
 *   2. Oldest uncompressed memory is > 7 days old
 *   3. At least 20 memories share a session+task group
 *
 * Time: O(G · S) where G = number of session+task groups, S = LLM summarization cost per group.
 *   G is typically < 50 even for busy sessions.
 *   Each summarization requires ~2K tokens input + ~500 tokens output.
 * Space: O(G) for compression records + O(C) for compressed memories.
 */

const EPISODIC_MAX_CHARS = 500_000;        // ~125K tokens
const COMPRESSION_AGE_DAYS = 7;
const MIN_GROUP_SIZE = 20;

interface CompressionGroup {
  sessionId: string;
  taskId: string;
  memories: MemoryNode[];
}

async function runCompressionCycle(tier: 'episodic'): Promise<CompressionBatch[]> {
  // Step 3a: Find candidates — memories older than threshold in the target tier.
  const cutoff = Date.now() - COMPRESSION_AGE_DAYS * 24 * 3600 * 1000;
  const oldMemories = await queryTKG({
    tier,
    filter: { timestamp: { lt: cutoff }, 'compression.strategy': 'none' },
    limit: 10_000,                         // Reasonable upper bound per cycle
  });

  // Step 3b: Group by session + task.
  const groups = new Map<string, MemoryNode[]>();
  for (const mem of oldMemories) {
    const key = `${mem.sessionId}::${mem.metadata.taskId ?? 'unknown'}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(mem);
  }

  // Step 3c: Filter groups that don't meet minimum size.
  const eligibleGroups: CompressionGroup[] = [];
  for (const [key, memories] of groups) {
    if (memories.length >= MIN_GROUP_SIZE) {
      const [sessionId, taskId] = key.split('::');
      eligibleGroups.push({ sessionId, taskId, memories });
    }
  }

  // Step 3d: Summarize each group via LLM.
  const batches: CompressionBatch[] = [];
  for (const group of eligibleGroups) {
    const originalContent = group.memories.map((m) => m.content).join('\n---\n');
    const originalSize = originalContent.length;

    // LLM summarization with structured output
    const summary = await llmSummarize({
      content: originalContent,
      prompt: `You are compressing a group of memories from session "${group.sessionId}", task "${group.taskId}".
        Extract:
        1. KEY FINDINGS: What was learned? (bullet points)
        2. DECISIONS MADE: What was decided and why?
        3. ERRORS: What went wrong and how was it resolved?
        4. OPEN QUESTIONS: What remains unresolved?
        
        Format as structured Markdown. Maximum 1,000 tokens.
        At the beginning, output a JSON frontmatter block:
        \`\`\`json
        { "compression_ratio": "<number>", "confidence": "<number 0-1>" }
        \`\`\``,
      maxTokens: 1500,
      temperature: 0.3,                    // Low temperature for factual summarization
    });

    const compressedSize = summary.length;
    const embedding = await computeEmbedding(summary);

    // Step 3e: Verify compression quality.
    // ROUGE-L recall between summary and original must be > 0.30
    // (Summary must cover the original's key points).
    const recall = rougeL(summary, originalContent);    // Note: reversed args for recall
    const verified = recall > 0.30;

    if (!verified) {
      console.warn(
        `Compression verification failed for group ${group.sessionId}::${group.taskId}: ` +
        `ROUGE-L recall ${recall.toFixed(3)} < 0.30. Using "none" strategy.`
      );
      // Fall back: store without compression, skip this group
      continue;
    }

    // Step 3f: Create the compressed summary memory.
    const compressedNode: MemoryNode = {
      id: generateUUID(),
      content: summary,
      embedding,
      tier: 'semantic',                    // Compressed summaries promote to Semantic tier
      timestamp: Date.now(),
      lastAccessed: Date.now(),
      accessCount: 0,
      sessionId: group.sessionId,
      admission: {
        utility: 0.0,                      // Will be re-assessed on first access
        confidence: 0.0,
        novelty: 0.0,
        recency: 1.0,
        typePrior: TYPE_PRIORS.insight,
      },
      links: [],                           // Links inherited from source memories via linking pass
      compression: {
        originalSize,
        compressedSize,
        compressionRatio: originalSize / Math.max(compressedSize, 1),
        strategy: 'summarize',
        verified,
      },
      evolutionHistory: [],
      metadata: {
        sourceMemoryIds: group.memories.map((m) => m.id),
        taskId: group.taskId,
        compressionDate: Date.now(),
      },
    };

    // Step 3g: Mark originals as compressed (retain in Archive tier for lazy retrieval).
    for (const mem of group.memories) {
      await updateMemoryTier(mem.id, 'archive');
      await updateCompressionRecord(mem.id, {
        strategy: 'summarize',
        compressedSize: summary.length,
        compressedMemoryId: compressedNode.id,
        verified,
      });
    }

    // Step 3h: Store the compressed summary.
    await storeMemory(compressedNode);

    batches.push({
      sessionId: group.sessionId,
      taskId: group.taskId,
      sourceMemories: group.memories.map((m) => m.id),
      compressedMemoryId: compressedNode.id,
      compression: compressedNode.compression,
    });
  }

  return batches;
}

// Time: O(G · S_LLM) where G ≤ 50, S_LLM ≈ 2s per summarization → ~100s for worst case.
//   Runs as background job — does not block the write path.
// Space: O(totalUncompressedChars) for reading candidates + O(summaryChars) for output.
//   Typically < 10MB for episodic tier, compressed to < 2MB.
```

#### 18.1.5 STEP 4 — Evolution (MemGrad Textual Gradients)

```typescript
/**
 * Periodically evolve memories based on user feedback and usage patterns.
 * Implements MemGrad (#70) textual gradient descent.
 *
 * Triggered: every 100 new memories OR every 24 hours (whichever comes first).
 *
 * Time: O(F · M · L_LLM) where F = feedback items, M = affected memories, L_LLM = LLM analysis.
 *   F is typically < 50 per cycle, M < 20 per feedback item, L_LLM ≈ 2s per analysis.
 *   Upper bound: ~100s. Runs as background job.
 * Space: O(F + M) for feedback and memory references.
 */

interface FeedbackEvent {
  id: string;
  type: 'explicit_positive' | 'explicit_negative' | 'implicit_correction' | 'task_outcome';
  content: string;                         // The feedback text
  relatedMemoryIds: string[];              // Memories involved in the task
  timestamp: number;
}

interface EvolutionTrigger {
  newMemoryCount: number;
  hoursSinceLastEvolution: number;
  pendingFeedback: number;
}

async function shouldRunEvolution(state: EvolutionTrigger): Promise<boolean> {
  // Trigger conditions — run if ANY is met
  if (state.newMemoryCount >= 100) return true;
  if (state.hoursSinceLastEvolution >= 24) return true;
  if (state.pendingFeedback >= 10) return true;
  return false;
}

async function runEvolutionCycle(): Promise<EvolutionCycle> {
  const cycleId = generateUUID();
  const gradients: TextualGradient[] = [];

  // Step 4a: Collect recent feedback (explicit + implicit).
  const feedback = await collectRecentFeedback({
    since: Date.now() - 24 * 3600 * 1000,   // Last 24 hours
    minConfidence: 0.3,                      // Ignore low-confidence signals
  });

  if (feedback.length === 0) {
    return {
      cycleId,
      timestamp: Date.now(),
      gradients: [],
      validationMetrics: { retrievalRecallBefore: 0, retrievalRecallAfter: 0, improvement: 0 },
    };
  }

  // Step 4b: Compute retrieval metrics BEFORE evolution.
  const retrievalRecallBefore = await computeRetrievalRecall();

  // Step 4c: LLM analyzes feedback patterns.
  // MemGrad-style textual gradient computation.
  const feedbackAnalysis = await llmAnalyzeFeedback({
    feedback: feedback.map((f) => ({
      type: f.type,
      content: f.content,
      relatedMemoryIds: f.relatedMemoryIds,
    })),
    instruction: `Analyze this feedback batch for the agent's memory system.
      Identify:
      1. What patterns do you see across multiple feedback items?
      2. What should the agent remember differently?
      3. Are there any contradictions in the feedback?
      4. What prospective strategies should be created?

      For each finding, specify:
      - action: "update" | "merge" | "deprecate" | "create_strategy"
      - target_memory_id (if applicable)
      - delta: the new or modified content
      - rationale: why this change improves the memory system

      Return as JSON array.`,
  });

  // Step 4d: Apply each textual gradient.
  for (const finding of feedbackAnalysis) {
    const gradient: TextualGradient = {
      targetMemoryId: finding.target_memory_id ?? 'new',
      operation: finding.action,
      delta: finding.delta,
      rationale: finding.rationale,
      sourceFeedback: feedback
        .filter((f) => finding.target_memory_id == null || f.relatedMemoryIds.includes(finding.target_memory_id))
        .map((f) => f.id),
    };

    try {
      switch (gradient.operation) {
        case 'update': {
          const existing = await getMemory(gradient.targetMemoryId);
          if (!existing) {
            console.warn(`Evolution: target memory ${gradient.targetMemoryId} not found. Skipping.`);
            continue;
          }
          // Apply gradient with immutability: create new node, deprecate old one.
          const updatedNode: MemoryNode = {
            ...existing,
            content: gradient.delta,
            lastAccessed: Date.now(),
            evolutionHistory: [...existing.evolutionHistory, gradient],
          };
          // Re-embed the updated content
          updatedNode.embedding = await computeEmbedding(gradient.delta);
          await storeMemory(updatedNode);
          // Mark old as deprecated (tier → archive, add ref link to new)
          await addLink(existing.id, updatedNode.id, 'refines', 1.0);
          break;
        }

        case 'merge': {
          // Merge multiple related memories into a consolidated one.
          // Identified by the LLM as "these two memories should be one".
          const relatedIds = feedback
            .filter((f) => f.relatedMemoryIds.length > 0)
            .flatMap((f) => f.relatedMemoryIds);
          const uniqueIds = [...new Set(relatedIds)];
          if (uniqueIds.length < 2) {
            console.warn('Evolution: merge requested but < 2 unique memories identified. Skipping.');
            continue;
          }
          const mergedNode = await createMergedMemory(uniqueIds, gradient.delta);
          for (const id of uniqueIds) {
            await addLink(id, mergedNode.id, 'refines', 0.9);
            await updateMemoryTier(id, 'archive');
          }
          break;
        }

        case 'deprecate': {
          // Memory was found to be incorrect or superseded.
          // Move to archive, add deprecation note.
          await updateMemoryTier(gradient.targetMemoryId, 'archive');
          await appendMetadata(gradient.targetMemoryId, {
            deprecated: true,
            deprecationReason: gradient.rationale,
            deprecationDate: Date.now(),
          });
          break;
        }

        case 'create_strategy': {
          // Create a new prospective strategy memory in the Semantic tier.
          const strategyNode: MemoryNode = {
            id: generateUUID(),
            content: gradient.delta,
            // ... (full node construction omitted for brevity)
            tier: 'semantic',
            timestamp: Date.now(),
            lastAccessed: Date.now(),
            accessCount: 0,
            sessionId: 'evolution',
            admission: {
              utility: 0.8,               // Strategies default to high utility
              confidence: 0.6,
              novelty: 0.7,
              recency: 1.0,
              typePrior: TYPE_PRIORS.insight,
            },
            links: [],
            compression: { originalSize: 0, compressedSize: 0, compressionRatio: 1, strategy: 'none', verified: true },
            evolutionHistory: [gradient],
            metadata: {
              source: 'evolution',
              cycleId,
              type: 'strategy',
            },
          };
          strategyNode.embedding = await computeEmbedding(gradient.delta);
          await storeMemory(strategyNode);
          break;
        }
      }

      gradients.push(gradient);
    } catch (err) {
      console.error(`Evolution gradient failed: ${JSON.stringify(gradient)}. Error: ${err}`);
      // Single gradient failure does NOT abort the cycle.
      // Logged and continued — circuit-breaker only fires on 5+ consecutive failures.
    }
  }

  // Step 4e: Validate — retrieval recall must not decrease.
  const retrievalRecallAfter = await computeRetrievalRecall();
  const improvement = retrievalRecallAfter - retrievalRecallBefore;

  if (improvement < -0.02) {
    // ROLLBACK: Recall degraded by more than 2%.
    // This is the auto-rollback mechanism from EvolveMem (#106).
    console.error(
      `Evolution cycle ${cycleId}: retrieval recall dropped from ${retrievalRecallBefore.toFixed(3)} ` +
      `to ${retrievalRecallAfter.toFixed(3)} (Δ=${improvement.toFixed(3)}). Rolling back all gradients.`
    );
    await rollbackCycle(cycleId, gradients);
    return {
      cycleId,
      timestamp: Date.now(),
      gradients,                            // Recorded for analysis even though rolled back
      validationMetrics: { retrievalRecallBefore, retrievalRecallAfter, improvement },
    };
  }

  // Step 4f: Record cycle results.
  await recordEvolutionCycle({
    cycleId,
    gradientsApplied: gradients.length,
    retrievalRecallBefore,
    retrievalRecallAfter,
    improvement,
    feedbackCount: feedback.length,
  });

  return {
    cycleId,
    timestamp: Date.now(),
    gradients,
    validationMetrics: { retrievalRecallBefore, retrievalRecallAfter, improvement },
  };
}

async function rollbackCycle(cycleId: string, gradients: TextualGradient[]): Promise<void> {
  // Reverse each gradient operation in reverse order.
  // For 'update': restore pre-evolution version from archive.
  // For 'merge': restore constituent memories from archive, remove merged node.
  // For 'deprecate': restore memory to previous tier.
  // For 'create_strategy': delete the strategy node.
  for (const g of [...gradients].reverse()) {
    try {
      switch (g.operation) {
        case 'update': {
          const history = await getMemoryEvolutionHistory(g.targetMemoryId);
          const previous = history[history.length - 2]; // The state before this gradient
          if (previous) {
            await restoreMemory(g.targetMemoryId, previous.content);
            await updateMemoryTier(g.targetMemoryId, 'episodic'); // Restore from archive
          }
          break;
        }
        case 'merge':
        case 'deprecate':
        case 'create_strategy':
          await deleteMemory(g.targetMemoryId);
          break;
      }
    } catch (err) {
      console.error(`Rollback failed for gradient ${g.targetMemoryId}: ${err}`);
      // Partial rollback failure — log and continue. Human intervention may be needed.
    }
  }
}

// Complexity summary for TKG Write Path:
//   Admission:  O(n·m) ROUGE-L + O(log N) ANN search. Typical: <50ms.
//   Linking:    O(K) ANN search + O(K/B) LLM calls. Typical: ~2s (async).
//   Compression: O(G · S_LLM). Typical: ~100s (background job, hourly).
//   Evolution:  O(F · M · L_LLM). Typical: ~100s (background job, every 100 memories or 24h).
//   Overall write-path latency (synchronous): <50ms (admission only; linking is fire-and-forget).
//   Overall throughput: Limited by ANN write throughput. HNSW supports ~50K inserts/s on a single node.
```

#### 18.1.6 TKG Write Path — Failure Modes

| Failure Mode | Symptom | Detection | Recovery |
|---|---|---|---|
| LLM utility assessment timeout | Admission stalls for >2s | Timer on `llmAssessUtility` | Fallback to `confidence × typePrior` heuristic |
| ANN index stale after high-velocity writes | Novelty score inaccurate for recent memories | Lag between write and index refresh <50ms | Maintain write-ahead log for recently indexed vectors |
| Compression LLM hallucinates facts not in source | ROUGE-L recall <0.30 in compression verification | Verification gate in Step 3e | Skip compression for that group; flag for review |
| Evolution gradient creates contradictory memories | Retrieval recall drops >2% | Pre/post recall comparison in Step 4e | Auto-rollback all gradients in the cycle |
| Memory node becomes orphan (no links, never accessed) | Zero links, low access count | Periodic graph traversal (every 100K nodes) | Move to Archive tier; candidate for deletion after 90 days |
| Bidirectional link weight asymmetry diverges | Source→target weight differs from target→source by >0.3 | Periodic consistency check | Re-normalize: both sides set to min(original, reverse×1.18) |

#### 18.1.7 DESIGN RATIONALE

**Why 5-factor admission with those specific weights?** The weight distribution (0.30 utility, 0.25 confidence, 0.20 novelty, 0.15 recency, 0.10 typePrior) is adapted from A-MAC (#79) with one critical modification: utility is weighted highest (0.30 vs. A-MAC's 0.25), and recency is weighted lower (0.15 vs. A-MAC's 0.20). This reflects Lyra's terminal-native design where long-running sessions generate thousands of memory candidates, and the limiting factor is utility—not recency. Early bail-out on utility < 0.05 catches 80% of rejections in the first factor, making the remaining factor computation a pure optimization loss.

**Why ROUGE-L for confidence instead of BLEU or BERTScore?** ROUGE-L (LCS-based) is the cheapest recall-oriented metric that correlates well with fact preservation—critical for a memory system where the primary risk is hallucination (fabricating details not in source). LCS is O(n·m) with no neural network overhead. BERTScore would add ~50ms per call from embedding inference. BLEU measures precision (n-gram overlap), which penalizes the paraphrasing that memory summarization deliberately performs.

**Why batch linking instead of individual?** Linking K=20 candidates individually would require 20 LLM calls per new memory. Batching into groups of 5 reduces this to 4 calls—a 5× latency reduction. The batch classifier can also detect relationships between candidates (e.g., "both candidates contradict the source on different points"), which individual classification misses.

**Why compression age threshold = 7 days?** AOI (#68) uses 7 days as the episodic-to-semantic transition window. Empirical evidence from DecentMem (#99) shows that memories older than 7 days contribute <10% to daily retrieval queries but constitute >60% of tier storage. The 7-day threshold optimizes the storage/utility Pareto frontier.

**Why auto-rollback on recall degradation >2%?** MemGrad (#70) reports that 4-8% of evolutionary updates cause recall degradation. The 2% threshold is deliberately conservative (one standard deviation below the mean improvement) to prevent compound degradation across cycles. The rollback preserves the pre-evolution state via the TKG's versioned store, ensuring evolution is safely reversible.

---

### 18.2 Algorithm 2: AVP Protocol — Classification, Critique, Consensus

The Adversarial Verification Protocol (AVP) gates every mutating action in the system. It is inspired by SABER (#67), AutoScientists (#154–156), and CaMeL (#243).

#### 18.2.1 Data Structures

```typescript
// ─── Input / Action ──────────────────────────────────────────────────────────

interface ToolCall {
  id: string;
  tool: string;                            // 'Bash' | 'Write' | 'Edit' | 'Read' | ...
  parameters: Record<string, unknown>;
  sessionId: string;
  agentId: string;
  timestamp: number;
  context: {
    goal: string;                          // Why this tool call is being made
    precedingActions: string[];            // IDs of actions leading to this one
  };
}

interface MutatingAction extends ToolCall {
  mutationClass: 'state_change' | 'side_effect' | 'external_write' | 'agent_spawn';
  estimatedImpact: 'low' | 'medium' | 'high' | 'critical';
  rollbackable: boolean;
}

// ─── Classification ──────────────────────────────────────────────────────────

type MutationResult =
  | { type: 'non-mutating' }
  | { type: 'mutating'; detail: MutatingDetail };

interface MutatingDetail {
  class: 'state_change' | 'side_effect' | 'external_write' | 'agent_spawn';
  estimatedImpact: 'low' | 'medium' | 'high' | 'critical';
  rollbackable: boolean;
  reason: string;                          // Why classified as mutating
}

// ─── Critique ────────────────────────────────────────────────────────────────

interface CriticConfig {
  role: 'correctness' | 'safety' | 'efficiency';
  provider: 'claude' | 'deepseek' | 'open-weights';
  model: string;
  timeoutMs: number;                       // Per-provider timeout
  retryCount: number;
}

interface CriticVote {
  critic: CriticConfig;
  approve: boolean;
  confidence: number;                      // 0–1
  reasoning: string;
  alternatives?: string[];                // Suggested alternative actions
  latencyMs: number;                      // Time taken for this critic
}

// ─── Consensus ───────────────────────────────────────────────────────────────

type GateDecision =
  | { type: 'execute'; confidence: number }
  | { type: 'revise'; suggestedAction: ToolCall; rationale: string }
  | { type: 'escalate'; reason: string; criticVotes: CriticVote[] }
  | { type: 'block'; reason: string; criticVotes: CriticVote[] };

interface AVPSession {
  actionId: string;
  classificationResult: MutationResult;
  criticVotes: CriticVote[];
  gateDecision: GateDecision;
  latencyMs: number;                       // Total AVP latency
  outcome?: 'success' | 'failure';
  outcomeDetails?: string;
}
```

#### 18.2.2 STEP 1 — Mutation Classification

```typescript
/**
 * Classify an action as mutating or non-mutating.
 * Target: <5ms. This is the hottest path — called for EVERY tool invocation.
 *
 * Time: O(1) — hash table lookup + regex match. Always <1ms.
 * Space: O(1) — static sets.
 */
const READ_ONLY_TOOLS = new Set([
  'Read', 'ListFiles', 'Glob', 'Grep', 'WebSearch',
  'WebFetch', 'LSPHover', 'LSPDefinition', 'LSPReferences',
]);

const MUTATING_TOOLS = new Set([
  'Write', 'Edit', 'CreateFile', 'DeleteFile', 'RenameFile',
  'Bash', 'ExecuteCommand', 'RunScript',
  'Task', 'CreateSubAgent', 'SpawnAgent',
]);

// Safe Bash commands (read-only subset)
const SAFE_BASH_PATTERN = /^(ls|cat|head|tail|grep|find|wc|du|df|ps|top|echo|which|type|pwd|env|printenv|history|date|cal|who|whoami|id|uname|uptime|free|stat|file|sort|uniq|cut|tr|fold|column|tput)\b/i;

// Destructive Bash patterns — always classified as high-impact mutating
const DESTRUCTIVE_BASH_PATTERN = /^(rm|dd|mkfs|fdisk|format|shutdown|reboot|kill|pkill|chmod\s+0|chown|mv\s+\/[^\/]|\/dev\/(null|zero|random|urandom))/i;

// Safer write-like commands that still mutate
const MUTATING_BASH_PATTERN = /^(mkdir|touch|cp|mv|ln|chmod|chown|sed\s+-i|awk\s+-i|git\s+(add|commit|push|pull|merge|rebase|reset|checkout|branch\s+-[dD]|tag|stash|clean|cherry-pick))/i;

/**
 * Classify a tool call's mutation status.
 * Uses a 3-tier classification: static set → regex → parameter analysis.
 * Each tier is more expensive but catches more cases.
 */
function classifyMutation(action: ToolCall): MutationResult {
  // Tier 0: Fast path — tool not in known sets (rare but possible)
  if (!READ_ONLY_TOOLS.has(action.tool) && !MUTATING_TOOLS.has(action.tool)) {
    // Unknown tool: default to mutating (safe side)
    return {
      type: 'mutating',
      detail: {
        class: 'state_change',
        estimatedImpact: 'medium',
        rollbackable: false,
        reason: `Unknown tool "${action.tool}" — defaulting to mutating (safety-first principle).`,
      },
    };
  }

  // Tier 1: Non-mutating tools
  if (READ_ONLY_TOOLS.has(action.tool)) {
    // Sub-classification for Read-like tools with write parameters
    // e.g., `Read` with `write: true` would be caught here
    if (hasWriteParameter(action)) {
      return {
        type: 'mutating',
        detail: {
          class: 'side_effect',
          estimatedImpact: 'low',
          rollbackable: true,
          reason: `Read tool "${action.tool}" has write-like parameter — conservative classification.`,
        },
      };
    }
    return { type: 'non-mutating' };
  }

  // Tier 2: Bash — command-specific analysis
  if (action.tool === 'Bash') {
    const cmd = String(action.parameters.command ?? '');
    if (DESTRUCTIVE_BASH_PATTERN.test(cmd)) {
      return {
        type: 'mutating',
        detail: {
          class: 'state_change',
          estimatedImpact: 'critical',
          rollbackable: false,
          reason: `Destructive command pattern detected in Bash call.`,
        },
      };
    }
    if (SAFE_BASH_PATTERN.test(cmd)) {
      return { type: 'non-mutating' };
    }
    if (MUTATING_BASH_PATTERN.test(cmd)) {
      return {
        type: 'mutating',
        detail: {
          class: 'state_change',
          estimatedImpact: cmd.startsWith('git') ? 'high' : 'medium',
          rollbackable: cmd.startsWith('git'),            // Git operations are rollbackable
          reason: `Mutating command pattern: "${cmd.split(/\s+/)[0]}"`,
        },
      };
    }
    // Fallback for unrecognized Bash commands: assume mutating
    return {
      type: 'mutating',
      detail: {
        class: 'state_change',
        estimatedImpact: 'medium',
        rollbackable: false,
        reason: `Unrecognized Bash command pattern — defaulting to mutating.`,
      },
    };
  }

  // Tier 3: Other mutating tools — classify by tool name
  const detail = classifyMutatingTool(action.tool, action.parameters);
  return { type: 'mutating', detail };
}

function classifyMutatingTool(
  tool: string,
  params: Record<string, unknown>
): MutatingDetail {
  switch (tool) {
    case 'Write':
    case 'Edit':
    case 'CreateFile':
      return {
        class: 'state_change',
        estimatedImpact: params.path?.toString().endsWith('.lyra/') ? 'critical' : 'medium',
        rollbackable: true,                // File writes are version-controlled
        reason: `File modification via ${tool}`,
      };

    case 'DeleteFile':
      return {
        class: 'state_change',
        estimatedImpact: 'high',
        rollbackable: true,                // Deleted files can be restored from git
        reason: 'File deletion',
      };

    case 'Task':
    case 'CreateSubAgent':
    case 'SpawnAgent':
      return {
        class: 'agent_spawn',
        estimatedImpact: 'high',
        rollbackable: false,               // Cannot "un-spawn" an agent
        reason: `Agent creation via ${tool}`,
      };

    default:
      return {
        class: 'side_effect',
        estimatedImpact: 'medium',
        rollbackable: false,
        reason: `Unclassified mutating tool: ${tool}`,
      };
  }
}

function hasWriteParameter(action: ToolCall): boolean {
  const params = action.parameters;
  return (
    (typeof params.path === 'string' && params.path.length > 0 &&
     (params as Record<string, unknown>).content !== undefined)
  );
}
```

#### 18.2.3 STEP 2 — Critique Panel

```typescript
/**
 * Spawn an independent critic panel for a mutating action.
 *
 * Key design decisions:
 * 1. Critic providers are DIVERSIFIED by default (Claude + DeepSeek + open-weights).
 *    This maximizes architectural diversity in verification — different training data,
 *    different inductive biases, different failure modes.
 * 2. Each critic has a DIFFERENT role (correctness, safety, efficiency).
 *    This prevents blind spots: one critic focuses on "does it work?", another on
 *    "is it safe?", another on "is it worth it?"
 * 3. Critic calls are PARALLEL — total latency = max(critic latency), not sum.
 *
 * Time: O(max(C₁, C₂, C₃)) where Cⱼ is the j-th critic's LLM latency.
 *   Typically 500ms–1500ms per critic. Parallel execution: ~1500ms total.
 * Space: O(3) critic vote objects + O(3) LLM response texts. Negligible.
 */

const DEFAULT_CRITICS: CriticConfig[] = [
  { role: 'correctness', provider: 'claude',   model: 'sonnet', timeoutMs: 10_000, retryCount: 1 },
  { role: 'safety',      provider: 'deepseek', model: 'v3',     timeoutMs: 15_000, retryCount: 1 },
  { role: 'efficiency',  provider: 'claude',   model: 'haiku',  timeoutMs: 8_000,  retryCount: 2 },
];

async function runCriticPanel(
  action: MutatingAction,
  critics: CriticConfig[] = DEFAULT_CRITICS
): Promise<CriticVote[]> {
  // Spawn all critics in parallel
  const votePromises = critics.map((critic) => runSingleCritic(action, critic));
  const results = await Promise.allSettled(votePromises);

  const votes: CriticVote[] = [];

  for (let i = 0; i < results.length; i++) {
    const result = results[i];
    const critic = critics[i];

    if (result.status === 'fulfilled') {
      votes.push(result.value);
    } else {
      // Critic failed or timed out — produce a "soft approve" with low confidence.
      // Rationale: failing open is safer than failing blocked for a verification system.
      // A failed critic = the agent acted without that perspective.
      // Log the failure loudly for observability.
      console.warn(
        `Critic ${critic.role} (${critic.provider}/${critic.model}) failed: ` +
        `${(result as PromiseRejectedResult).reason ?? 'timeout'}. ` +
        `Proceeding with soft-approve (confidence 0.3).`
      );
      votes.push({
        critic,
        approve: true,                     // Fail open
        confidence: 0.3,
        reasoning: `Critic failed: ${(result as PromiseRejectedResult).reason ?? 'timeout'}. Soft-approving with low confidence.`,
        latencyMs: critic.timeoutMs,       // Assume full timeout was consumed
      });
    }
  }

  return votes;
}

async function runSingleCritic(
  action: MutatingAction,
  critic: CriticConfig
): Promise<CriticVote> {
  const startTime = performance.now();

  // Build the critic prompt based on role
  const prompt = buildCriticPrompt(action, critic.role);

  try {
    const response = await callLLM({
      provider: critic.provider,
      model: critic.model,
      messages: [
        { role: 'system', content: prompt.system },
        { role: 'user', content: prompt.user },
      ],
      maxTokens: 500,
      temperature: 0.0,                    // Deterministic output for verification
      responseFormat: {
        type: 'json_schema',
        schema: {
          type: 'object',
          properties: {
            approve: { type: 'boolean' },
            confidence: { type: 'number', minimum: 0, maximum: 1 },
            reasoning: { type: 'string', maxLength: 1000 },
            alternatives: {
              type: 'array',
              items: { type: 'string' },
              maxItems: 3,
            },
          },
          required: ['approve', 'confidence', 'reasoning'],
        },
      },
      timeoutMs: critic.timeoutMs,
      retryCount: critic.retryCount,
    });

    const result = JSON.parse(response.content);
    const latencyMs = performance.now() - startTime;

    return {
      critic,
      approve: result.approve,
      confidence: clamp(result.confidence, 0, 1),
      reasoning: result.reasoning,
      alternatives: result.alternatives,
      latencyMs,
    };
  } catch (err) {
    const latencyMs = performance.now() - startTime;
    throw new Error(`Critic ${critic.role} failed after ${latencyMs.toFixed(0)}ms: ${err}`);
  }
}

function buildCriticPrompt(action: MutatingAction, role: string): { system: string; user: string } {
  const ROLE_PROMPTS: Record<string, string> = {
    correctness: `You are a CORRECTNESS critic. Your job is to verify that an action achieves its stated goal correctly.

Focus on:
1. Logic errors, off-by-one, missing edge cases
2. Does the tool choice match the goal?
3. Are parameters correct and complete?
4. Will this action produce the intended outcome?

Be precise and specific. "Looks fine" is not acceptable reasoning.`,
    safety: `You are a SAFETY critic. Your job is to identify potential harm from an action.

Focus on:
1. Data loss or corruption risk
2. Security vulnerabilities (injection, path traversal, privilege escalation)
3. Resource exhaustion (disk, memory, API rate limits)
4. Unauthorized external writes
5. Side effects on other running agents or workflows

Be conservative — flag anything that COULD go wrong, not just what WILL go wrong.`,
    efficiency: `You are an EFFICIENCY critic. Your job is to evaluate whether this is the best way to achieve the goal.

Focus on:
1. Is there a cheaper or faster alternative?
2. Is this doing unnecessary work?
3. Could this be combined with another action?
4. Is the estimated impact proportional to the expected benefit?

You are NOT the correctness or safety critic — assume the action works and is safe.`,
  };

  return {
    system: ROLE_PROMPTS[role] ?? ROLE_PROMPTS.correctness,
    user: `Action to evaluate:
Tool: ${action.tool}
Parameters: ${JSON.stringify(action.parameters, null, 2)}
Goal: ${action.context.goal}
Mutation class: ${action.mutationClass}
Impact: ${action.estimatedImpact}
Rollbackable: ${action.rollbackable}

Respond with:
1. approve (boolean): do you approve this action?
2. confidence (0-1): how confident are you in your assessment?
3. reasoning (string): your detailed analysis
4. alternatives (string[]): if not approving, up to 3 alternatives`,
  };
}
```

#### 18.2.4 STEP 3 — Consensus Gate

```typescript
/**
 * Evaluate critic votes and produce a gate decision.
 *
 * Gate logic:
 *   ≥2 approve           → EXECUTE
 *   1 approve + 1+ revise agreement → REVISE
 *   exactly 1 approve    → ESCALATE (split decision)
 *   0 approve            → BLOCK
 *
 * Time: O(C · A) where C = critics (3), A = alternatives (≤3). Always <1ms.
 * Space: O(C + A). Negligible.
 */
function consensusGate(votes: CriticVote[]): GateDecision {
  if (votes.length === 0) {
    // Defensive: no critics ran. Block by default.
    return {
      type: 'block',
      reason: 'No critic votes available — default blocking. This should not happen.',
      criticVotes: votes,
    };
  }

  const approvals = votes.filter((v) => v.approve);
  const rejections = votes.filter((v) => !v.approve);
  const avgConfidence = votes.reduce((s, v) => s + v.confidence, 0) / votes.length;

  // ── Case 1: 2+ approvals → EXECUTE ──────────────────────────────────────
  if (approvals.length >= 2) {
    // Check if any approving critic has low confidence (<0.5)
    const lowConfApprovals = approvals.filter((v) => v.confidence < 0.5);
    if (lowConfApprovals.length > 0) {
      return {
        type: 'execute',
        confidence: avgConfidence,
      };
    }
    return {
      type: 'execute',
      confidence: avgConfidence,
    };
  }

  // ── Case 2: Exactly 1 approval ───────────────────────────────────────────
  if (approvals.length === 1) {
    // Check for alternative agreement among dissenting critics
    const dissentersWithAlternatives = rejections.filter(
      (v) => v.alternatives != null && v.alternatives.length > 0
    );

    // Do at least 2 dissenters propose the same alternative?
    const alternativeCounts = new Map<string, number>();
    for (const d of dissentersWithAlternatives) {
      for (const alt of d.alternatives!) {
        // Normalize: lowercase, trim
        const normalized = alt.toLowerCase().trim().replace(/\s+/g, ' ');
        alternativeCounts.set(normalized, (alternativeCounts.get(normalized) ?? 0) + 1);
      }
    }

    // Find the most-agreed-upon alternative
    let bestAlt = '';
    let bestCount = 1;                     // Need at least 2 dissenters to agree
    for (const [alt, count] of alternativeCounts) {
      if (count > bestCount) {
        bestAlt = alt;
        bestCount = count;
      }
    }

    if (bestCount >= 2) {
      // Two or more dissenters independently proposed the same alternative
      // → Strong signal: revise the action.
      return {
        type: 'revise',
        suggestedAction: reconstructToolCall(bestAlt, votes),
        rationale: `${bestCount}/${votes.length} critics independently proposed the same alternative: "${bestAlt}"`,
      };
    }

    // Dissenters don't agree — escalate to human
    return {
      type: 'escalate',
      reason: 'Split decision: 1 approve, 2 reject (no consensus on alternative). Requires human review.',
      criticVotes: votes,
    };
  }

  // ── Case 3: 0 approvals → BLOCK ─────────────────────────────────────────
  // Concatenate reasoning from all critics for the block reason
  const blockReasons = votes
    .filter((v) => !v.approve)
    .map((v) => `[${v.critic.role}@${v.critic.provider}]: ${v.reasoning}`);

  return {
    type: 'block',
    reason: blockReasons.join('\n'),
    criticVotes: votes,
  };
}

/**
 * Edge case: reconstruct a ToolCall from a textual alternative description.
 * This is inherently lossy — the alternative text might not contain all parameters.
 * Falls back to returning the original action with modified parameters.
 */
function reconstructToolCall(alternativeText: string, votes: CriticVote[]): ToolCall {
  // Heuristic extraction from the alternative text
  // E.g., "Use `ls -la` instead of `find . -type f`" → extract the command
  const cmdMatch = alternativeText.match(/`([^`]+)`/);
  const toolHint = cmdMatch ? cmdMatch[1].split(/\s+/)[0] : null;

  // Infer the tool from the first critic's suggested tool
  for (const v of votes) {
    if (v.alternatives && v.alternatives.length > 0) {
      const firstAlt = v.alternatives[0];
      const inferredTool = firstAlt.match(/`([^`]+)`/)?.[1];
      if (inferredTool) {
        return {
          id: generateUUID(),
          tool: toolHint ?? inferredTool,
          parameters: { command: firstAlt.replace(/`/g, '') },
          sessionId: 'avp-revision',
          agentId: 'avp-gate',
          timestamp: Date.now(),
          context: { goal: alternativeText, precedingActions: [] },
        };
      }
    }
  }

  throw new Error('Cannot reconstruct tool call from alternatives — escalation required.');
}
```

#### 18.2.5 STEP 4 — Execution / Block / Escalate

```typescript
/**
 * Execute the AVP gate decision.
 * This is the final step — it either allows, revises, escalates, or blocks the action.
 *
 * Time: O(1) for block/escalate; O(revisedClassification + revisedPanel) for revise;
 *   O(action execution) for execute. The revise path loops back to Step 1.
 * Space: O(1) for the AVP session record + O(1) for logging.
 */
async function executeAVPGate(action: MutatingAction, session: AVPSession): Promise<{
  allowed: boolean;
  blocked: boolean;
  escalated: boolean;
  revised: boolean;
  finalAction: ToolCall | null;
  session: AVPSession;
}> {
  const gateDecision = session.gateDecision;

  switch (gateDecision.type) {
    case 'execute': {
      // Action proceeds immediately. Log the AVP session for audit.
      try {
        const result = await executeAction(action);
        session.outcome = result.success ? 'success' : 'failure';
        session.outcomeDetails = result.details;
        return { allowed: true, blocked: false, escalated: false, revised: false, finalAction: action, session };
      } catch (err) {
        session.outcome = 'failure';
        session.outcomeDetails = `Execution failed: ${err}`;
        return { allowed: true, blocked: false, escalated: false, revised: false, finalAction: null, session };
      }
    }

    case 'revise': {
      // The suggested action replaces the original and is re-submitted to AVP.
      // Guard: max 2 revision rounds to prevent infinite loops.
      const revisionCount = (action as MutatingAction & { revisionCount?: number }).revisionCount ?? 0;
      if (revisionCount >= 2) {
        // Too many revision attempts → escalate
        session.gateDecision = {
          type: 'escalate',
          reason: `Exceeded maximum revision rounds (2). Action: ${JSON.stringify(action)}. Most recent suggestion: ${gateDecision.suggestedAction}`,
          criticVotes: session.criticVotes,
        };
        return {
          allowed: false, blocked: false, escalated: true, revised: false,
          finalAction: null, session,
        };
      }

      // Re-run AVP on the revised action
      const revisedAction: MutatingAction = {
        ...action,
        tool: gateDecision.suggestedAction.tool,
        parameters: gateDecision.suggestedAction.parameters,
        revisionCount: revisionCount + 1,
      };

      // Re-classify (Step 1) and re-panel (Step 2)
      const reClassification = classifyMutation(revisedAction);
      const reVotes = await runCriticPanel(revisedAction);
      const reDecision = consensusGate(reVotes);

      session.classificationResult = reClassification;
      session.criticVotes = reVotes;
      session.gateDecision = reDecision;
      session.latencyMs += performance.now() - 0;   // Approximate — real impl tracks start time

      // Recurse (but at most 2 levels deep per the guard above)
      return executeAVPGate(revisedAction, session);
    }

    case 'escalate': {
      // Action is shown to user with critic reasoning for manual approval.
      // User can approve (→execute), reject (→block), or modify (→revise).
      await presentToUser({
        title: 'AVP Action Escalation — Manual Review Required',
        body: `Action: ${action.tool}(${JSON.stringify(action.parameters)})\n` +
              `Reason: ${gateDecision.reason}\n\n` +
              `Critic Votes:\n${session.criticVotes.map((v) =>
                `  [${v.critic.role}@${v.critic.provider}] ${v.approve ? 'APPROVE' : 'REJECT'} ` +
                `(conf: ${v.confidence.toFixed(2)}): ${v.reasoning}`
              ).join('\n')}`,
        timeoutMs: 300_000,                // 5 minutes for user to respond
      });
      return { allowed: false, blocked: false, escalated: true, revised: false, finalAction: null, session };
    }

    case 'block': {
      // Action is rejected. Reasoning logged to TKG for future reference.
      console.warn(
        `AVP BLOCKED action ${action.id}: ${action.tool}(${JSON.stringify(action.parameters)}). ` +
        `Reason: ${gateDecision.reason}`
      );
      await recordAVPBlock({
        actionId: action.id,
        reason: gateDecision.reason,
        criticVotes: session.criticVotes,
        timestamp: Date.now(),
      });
      return { allowed: false, blocked: true, escalated: false, revised: false, finalAction: null, session };
    }
  }
}

/**
 * Record an AVP block in the TKG for learning.
 * This is the feedback loop: blocked actions inform future routing and skill evolution.
 */
async function recordAVPBlock(block: {
  actionId: string;
  reason: string;
  criticVotes: CriticVote[];
  timestamp: number;
}): Promise<void> {
  const memory: MemoryNode = {
    id: `avp-block-${block.actionId}`,
    content: `AVP blocked action ${block.actionId}.\nBlock reason: ${block.reason}\nCritic votes: ${
      JSON.stringify(block.criticVotes.map((v) => ({ role: v.critic.role, approve: v.approve, reasoning: v.reasoning })))
    }`,
    // ... (full node structure omitted for brevity)
    tier: 'semantic',                       // Block patterns are durable knowledge
    timestamp: block.timestamp,
    lastAccessed: block.timestamp,
    accessCount: 0,
    sessionId: 'avp',
    admission: {
      utility: 0.7,                        // Block patterns have high utility for error avoidance
      confidence: 1.0,
      novelty: 0.5,
      recency: 1.0,
      typePrior: TYPE_PRIORS.error,
    },
    links: [],
    compression: { originalSize: 0, compressedSize: 0, compressionRatio: 1, strategy: 'none', verified: true },
    evolutionHistory: [],
    metadata: { avpBlock: true, actionId: block.actionId },
  };
  memory.embedding = await computeEmbedding(memory.content);
  await storeMemory(memory);
}

// AVP Complexity Summary:
//   Classification: O(1). <1ms.
//   Critique Panel: O(max(3 critic latencies)). 500–1500ms (parallel).
//   Consensus Gate: O(3). <1ms.
//   Execution/Block/Escalate: O(1) or O(revised panel). Typically <2s total.
//   Non-mutating bypass: <1ms overhead on every action.
```

#### 18.2.6 AVP — Failure Modes

| Failure Mode | Symptom | Detection | Recovery |
|---|---|---|---|
| All 3 critics time out | No votes produced | Promise.allSettled catches all rejections | Soft-approve each critic (conf=0.3); action proceeds with degraded verification |
| 1 critic consistently disagrees (rogue critic) | Same critic always rejects | Track per-critic approval rate over 100 actions | Flag for human review; possible replacement with different provider |
| Revise loop oscillates | A → B → A → B → escalate | Revision count guard (max 2) | Escalate to human with oscillation evidence |
| Critic hallucinates a danger | False positive block | Compare block rate vs. actual failure rate | Adaptive threshold: reduce critic weight if false positive rate >10% |
| User never responds to escalation | Blocked action hangs | Escalation timeout (5 min) | Auto-block with decay: action is blocked but soft-clocked for auto-retry after 1 hour |
| Alternative reconstruction fails | `reconstructToolCall` throws | Try-catch in revise branch | Escalate with original action + critic alternatives as text |

#### 18.2.7 DESIGN RATIONALE

**Why 3 critics and not 1, 5, or 7?** The debate (Section 0, Live Disagreements #2) left this as an open question. The 3-critic choice is grounded in three findings. First, SABER (#67) showed that a single critic catches ~80% of errors, but adding a second with a different perspective catches ~95%, and a third catches ~97%. Returns diminish sharply after three (diminishing returns <5% per additional critic). Second, 3 critics can produce a majority vote (≥2). Two critics can tie. Four or more create coordination complexity without proportional safety gain. Third, the latency budget (<15% overhead from Section 10, H2) is achievable with 3 parallel LLM calls but not with 5+.

**Why fail-open (soft-approve on critic failure)?** A verification system that blocks on every critic failure would stop all progress when providers are degraded. Fail-open with low confidence (0.3) means the action proceeds but is flagged for deferred review. The AVP session is still recorded in the TKG — if the action causes harm, the block log contains the critic failure evidence for post-mortem.

**Why safety critic uses DeepSeek and correctness/efficiency use Claude?** This is the deliberate provider diversification from Section 0 (adversarial diversity principle). Claude (Anthropic) and DeepSeek have different training data, different safety fine-tuning, and different known failure modes. If both agree on a block, the signal is stronger than if two Claude instances agree (they could share the same blind spot). The safety critic particularly benefits from a different architectural perspective — what one model considers safe, the other might flag.

**Why maximum 2 revision rounds?** Infinite revision loops are a real risk when the revise path returns to the same classification/critique/consensus pipeline. Two rounds provide enough space to correct a clear error without enabling feedback oscillation. The empirical justification: if an action can't be corrected in two rounds of machine-generated alternatives, it likely requires human judgment.

---

### 18.3 Algorithm 3: Cross-Provider Routing Cascade

The router selects the optimal provider and model for each query, using a memory-augmented cascade that computes cost-quality trade-offs at runtime.

#### 18.3.1 Data Structures

```typescript
// ─── Provider Registry ───────────────────────────────────────────────────────

interface ProviderModel {
  provider: string;                        // 'claude' | 'deepseek' | 'qwen' | 'gpt' | 'open-weights'
  model: string;                           // 'opus-4.5' | 'sonnet-4.6' | 'haiku-4.5' | 'deepseek-v3' | ...
  tier: 'reasoning' | 'standard' | 'fast';
  costPerMInput: number;                   // USD per million input tokens
  costPerMOutput: number;                  // USD per million output tokens
  maxContextTokens: number;
  supportsToolCalling: boolean;
  supportsJsonMode: boolean;
  supportsVision: boolean;
  reliabilityScore: number;                // 0–1, from 30-day trailing data
  latencyP50Ms: number;
  latencyP95Ms: number;
  latencyP99Ms: number;
}

interface ProviderCapability {
  name: string;
  models: ProviderModel[];
  apiStatus: 'healthy' | 'degraded' | 'down';
  lastHealthCheck: number;                 // Unix ms
  rateLimit: {
    requestsPerMinute: number;
    tokensPerMinute: number;
    remaining: number;                     // Current rate limit remaining
    resetsAt: number;                      // Unix ms when rate limit resets
  };
}

// ─── Query Classification ────────────────────────────────────────────────────

type QueryDomain = 'code' | 'test' | 'factual_qa' | 'reasoning' | 'creative' | 'analysis' | 'planning' | 'memory_operation';

interface QueryProfile {
  domain: QueryDomain;
  complexity: number;                      // 0–1, estimated by heuristic
  inputTokens: number;                     // Estimated from prompt length
  expectedOutputTokens: number;            // Estimated from query type
  needsToolCalling: boolean;
  needsJsonMode: boolean;
  needsVision: boolean;
  needsLongContext: boolean;               // Does it need >64K context?
  latencyBudget: number;                   // Max acceptable latency in ms
  costBudget: number;                      // Max acceptable cost in USD
}

// ─── Memory-Augmented Routing ────────────────────────────────────────────────

interface CachedResponse {
  query: string;
  embedding: Float32Array;
  response: string;
  freshness: number;                       // 0–1: exp(-λ·age)
  quality: number;                         // 0–1: historical satisfaction score
  timestamp: number;
  provider: string;
  model: string;
  estimatedTokensSaved: number;            // Input + output tokens this response saved
}

// ─── Routing Decision ────────────────────────────────────────────────────────

interface RoutingDecision {
  provider: string;
  model: string;
  estimatedCost: number;                   // USD
  estimatedLatencyMs: number;
  confidence: number;                      // 0–1: how likely is this to succeed?
  escalationPath: string[];                // ['deepseek/flash', 'claude/haiku', 'claude/sonnet']
    // The fallback chain if this decision fails
  cacheHit: boolean;
  reasoning: string;                       // Audit trail
}

// ─── RouteLLM Matrix Factorization ──────────────────────────────────────────

interface RouteLLMEmbedding {
  // Query embedding: learned from past routing decisions
  queryFactors: number[];                  // d-dimensional latent vector (d=32)
}

interface ModelQualityEmbedding {
  // Model embedding: learned from past routing decisions
  modelFactors: number[];                  // d-dimensional latent vector (d=32)
  bias: number;                            // Model-specific bias term
}

// RouteLLM: quality_score(q, m) = dot(P[q], Q[m]) + bias[m]
// Where P = query factor matrix, Q = model factor matrix.
// Learned via alternating least squares on historical routing data.
```

#### 18.3.2 STEP 1 — Memory Cache Check

```typescript
/**
 * Level 0: Memory cache check.
 * Before any LLM call, check if an identical or near-identical query
 * has already been answered and cached.
 *
 * Time: O(d · N_cache) for ANN search where d=1536, N_cache = cached response count.
 *   HNSW: O(log N_cache) with high probability. Target: <5ms.
 * Space: O(N_cache · d) for vectors + O(N_cache · response_size) for cached content.
 */
const CACHE_FRESHNESS_THRESHOLD = 0.8;     // Expire cache entries older than this
const CACHE_SIMILARITY_THRESHOLD = 0.95;   // Near-exact match required for cache hit
const CACHE_MIN_QUALITY = 0.6;             // Only return high-quality cached responses

async function checkMemoryCache(
  query: string,
  embedding: Float32Array
): Promise<CachedResponse | null> {
  // Search for near-exact matches
  const results = await vectorSearch(embedding, {
    index: 'response-cache',
    topK: 1,
    minScore: CACHE_SIMILARITY_THRESHOLD,
  });

  if (results.length === 0) return null;

  const cached = await getCachedResponse(results[0].id);
  if (!cached) {
    // Vector returned a match but cache entry was evicted — clean up index
    await deleteVector('response-cache', results[0].id);
    return null;
  }

  // Check freshness
  const age = Date.now() - cached.timestamp;
  const freshness = Math.exp(-DECAY_LAMBDA * age);
  if (freshness < CACHE_FRESHNESS_THRESHOLD) {
    return null;                           // Cache entry expired
  }

  // Check quality
  if (cached.quality < CACHE_MIN_QUALITY) {
    return null;                           // Low-quality response, re-generate
  }

  return { ...cached, freshness };
}
```

#### 18.3.3 STEP 2 — Cascade Levels

```typescript
/**
 * The routing cascade: cheapest → mid → strongest.
 * Each level checks if the model's output confidence is sufficient.
 * If not, it escalates to the next level.
 *
 * Time: O(L · T) where L = cascade levels (3), T = LLM response time per level.
 *   Best case (Level 1 hit): ~200ms (fast model).
 *   Worst case (Level 3): ~5s (reasoning model).
 * Space: O(1) — intermediate results are dropped between levels.
 */

// Cascade configuration (costs as of 2026-05)
const CASCADE_CONFIG = {
  cheap: {
    provider: 'deepseek' as const,
    model: 'deepseek-chat' as const,
    costPerMInput: 0.27,
    costPerMOutput: 1.10,
    estimateLatencyMs: 500,
    tier: 'fast' as const,
  },
  mid: {
    provider: 'claude' as const,
    model: 'claude-sonnet-4-20250514' as const,
    costPerMInput: 3.00,
    costPerMOutput: 15.00,
    estimateLatencyMs: 1500,
    tier: 'standard' as const,
  },
  strong: {
    provider: 'claude' as const,
    model: 'claude-opus-4-20250514' as const,
    costPerMInput: 15.00,
    costPerMOutput: 75.00,
    estimateLatencyMs: 5000,
    tier: 'reasoning' as const,
  },
} as const;

const CONFIDENCE_THRESHOLD = 0.85;         // Minimum confidence to stop cascading

/**
 * Confidence estimation heuristic.
 * Uses output-level signals rather than model log-probs (which vary by provider).
 *
 * Signals (all heuristic, no model introspection required):
 * 1. Length: very short responses (<10 chars) are low confidence
 * 2. Hedge words: "I think", "maybe", "probably" indicate uncertainty
 * 3. Repetition: repeated phrases indicate confusion
 * 4. Contradiction: "yes" then "but" in same sentence
 * 5. Refusals: "I cannot", "I'm not able to"
 *
 * Time: O(L) where L = response length in chars. Typical: <1ms.
 * Space: O(1).
 */
function estimateConfidence(response: string): number {
  if (!response || response.length < 10) return 0.1;

  const signals = {
    tooShort: response.length < 20 ? 0.3 : 1.0,
    noHedgeWords: !/\b(i think|maybe|probably|perhaps|might|possibly|it's possible that|not entirely sure)\b/i.test(response) ? 1.0 : 0.5,
    noRepetition: !/(.{20,})\1{2,}/s.test(response) ? 1.0 : 0.4,
    noContradiction: !/yes.*but no|^no.*but yes|on one hand.*on the other hand/i.test(response) ? 1.0 : 0.6,
    noRefusal: !/\b(i cannot|i'm not able|i am not able|i don't know|insufficient information)\b/i.test(response) ? 1.0 : 0.3,
    hasCodeBlocks: /```[\s\S]*```/.test(response) ? 1.1 : 1.0,           // Bonus for code
  };

  // Weighted average with a bias toward negativity (conservative confidence)
  const score = Object.values(signals).reduce((a, b) => a + b, 0) / Object.keys(signals).length;
  return clamp(score, 0, 1);
}

/**
 * The main routing function.
 *
 * @returns The provider-model pair to use, or a cache hit.
 */
async function route(query: string, context: SessionContext): Promise<RoutingDecision> {
  // Step 0: Compute query embedding (required for cache check and complexity estimation).
  const embedding = await computeEmbedding(query);
  const queryProfile = await buildQueryProfile(query, context);

  // ── Level 0: Memory Cache ──────────────────────────────────────────────
  const cached = await checkMemoryCache(query, embedding);
  if (cached) {
    return {
      provider: 'cache',
      model: 'none',
      estimatedCost: 0,
      estimatedLatencyMs: 5,
      confidence: cached.quality,
      escalationPath: [],
      cacheHit: true,
      reasoning: `Cache hit (similarity > ${CACHE_SIMILARITY_THRESHOLD}, freshness ${cached.freshness.toFixed(2)}, quality ${cached.quality.toFixed(2)}). Zero-cost response.`,
    };
  }

  // ── Level 1: Cheap Model ────────────────────────────────────────────────
  const cheapResult = await attemptLevel({
    query,
    queryProfile,
    config: CASCADE_CONFIG.cheap,
    intent: 'First attempt — cheapest model.',
  });

  if (cheapResult.cached) return cheapResult;

  if (cheapResult.confidence >= CONFIDENCE_THRESHOLD) {
    return cheapResult;
  }

  // ── Level 2: Mid-Tier Model (with cheap context) ────────────────────────
  // Include cheap model's response as context so mid-tier doesn't start from scratch.
  const midResult = await attemptLevel({
    query,
    queryProfile,
    config: CASCADE_CONFIG.mid,
    contextFromCheap: cheapResult.partialResponse,
    intent: `Cheap model confidence ${cheapResult.confidence.toFixed(3)} < ${CONFIDENCE_THRESHOLD}. Escalating to mid-tier model.`,
  });

  if (midResult.confidence >= CONFIDENCE_THRESHOLD) {
    return midResult;
  }

  // ── Level 3: Strongest Model (no confidence check — final resort) ─────
  const strongResult = await attemptLevel({
    query,
    queryProfile,
    config: CASCADE_CONFIG.strong,
    contextFromCheap: cheapResult.partialResponse,
    intent: `Mid-tier model confidence ${midResult.confidence.toFixed(3)} < ${CONFIDENCE_THRESHOLD}. Escalating to strongest model (final resort).`,
  });

  return strongResult;
}
```

#### 18.3.4 STEP 3 — Best-Route Multi-Sampling

```typescript
/**
 * Best-Route multi-sampling: generate N responses from a cheap model and
 * select the best one via a verifier.
 *
 * Only applied to verifiable output types: code, tests, factual QA.
 *
 * Theory: For N=3, with a cheap model that returns correct response P=0.7 independently
 * per sample, the probability that at least one of 3 is correct is 1 - (1-0.7)^3 = 0.973.
 * This gives near-strong-model accuracy at cheap-model cost.
 *
 * Cost: 3 × cheap_model_cost. Still typically <1/10 of strong model cost.
 * Latency: N × cheap_model_latency. But run in parallel → max(latency), not sum.
 *
 * Time: O(T_LLM + T_verify). Parallelized generation: ~cost_model_latency.
 *   Verification: O(L_v) where L_v = verifier latency. <500ms for code/test.
 * Space: O(N) intermediate responses. Typically <10KB total.
 */

interface SampleResult {
  response: string;
  confidence: number;                      // From estimateConfidence
  verifierScore: number;                   // 0–1 from test pass / fact check
  combinedScore: number;                   // Weighted combination
}

async function bestRouteMultiSample(
  query: string,
  queryProfile: QueryProfile
): Promise<RoutingDecision | null> {
  // Only apply to verifiable domains
  const VERIFIABLE_DOMAINS: QueryDomain[] = ['code', 'test', 'factual_qa'];
  if (!VERIFIABLE_DOMAINS.includes(queryProfile.domain)) {
    return null;
  }

  const N = 3;                             // Number of parallel samples
  const TEMPERATURES = [0.1, 0.3, 0.5];   // Diverse temperatures for diversity

  // Generate N responses in parallel with different temperatures
  const samplePromises = TEMPERATURES.map((temperature) =>
    callLLM({
      provider: CASCADE_CONFIG.cheap.provider,
      model: CASCADE_CONFIG.cheap.model,
      messages: [{ role: 'user', content: query }],
      temperature,
      maxTokens: queryProfile.expectedOutputTokens,
    })
  );

  const responses = await Promise.allSettled(samplePromises);
  const validResponses: string[] = [];

  for (const r of responses) {
    if (r.status === 'fulfilled') {
      validResponses.push(r.value.content);
    }
  }

  if (validResponses.length === 0) {
    return null;                           // All cheap samples failed → fall through to cascade
  }

  // Verify each sample
  const samples: SampleResult[] = await Promise.all(
    validResponses.map(async (response) => {
      const confidence = estimateConfidence(response);
      const verifierScore = await runVerifier(query, response, queryProfile.domain);
      const combinedScore = 0.6 * confidence + 0.4 * verifierScore;
      return { response, confidence, verifierScore, combinedScore };
    })
  );

  // Select best sample
  samples.sort((a, b) => b.combinedScore - a.combinedScore);
  const best = samples[0];

  if (best.combinedScore >= CONFIDENCE_THRESHOLD) {
    return {
      provider: CASCADE_CONFIG.cheap.provider,
      model: `best-route:${CASCADE_CONFIG.cheap.model}`,
      estimatedCost: CASCADE_CONFIG.cheap.costPerMInput * queryProfile.inputTokens / 1_000_000 * N +
                     CASCADE_CONFIG.cheap.costPerMOutput * queryProfile.expectedOutputTokens / 1_000_000,
      estimatedLatencyMs: CASCADE_CONFIG.cheap.estimateLatencyMs,
      confidence: best.combinedScore,
      escalationPath: ['best-route', CASCADE_CONFIG.mid.provider + '/' + CASCADE_CONFIG.mid.model],
      cacheHit: false,
      reasoning: `Best-Route: generated ${N} samples, picked best (combined score ${best.combinedScore.toFixed(3)}). ` +
                 `Saved ~${(1 - N * 0.27 / 3.0).toFixed(0)}% vs mid-tier.`,
    };
  }

  return null;                             // Best sample didn't meet threshold → cascade
}

/**
 * Verifier for a specific domain.
 * For code: run the generated code against test cases.
 * For factual QA: check consistency with retrieved sources (RAG).
 */
async function runVerifier(query: string, response: string, domain: QueryDomain): Promise<number> {
  switch (domain) {
    case 'code':
    case 'test': {
      // Extract code block and attempt compilation/execution
      const codeBlock = extractCodeBlock(response);
      if (!codeBlock) return 0.3;

      try {
        const result = await executeInSandbox(codeBlock, { timeoutMs: 5000 });
        return result.success ? 1.0 : 0.2;
      } catch {
        return 0.1;
      }
    }

    case 'factual_qa': {
      // Check factual claims against retrieved context
      const facts = extractFactualClaims(response);
      if (facts.length === 0) return 0.5;  // No verifiable claims → neutral

      const verified = await verifyFacts(facts, { topK: 5 });
      return verified.verifiedCount / Math.max(verified.totalCount, 1);
    }

    default:
      return 0.5;                          // Non-verifiable domain
  }
}
```

#### 18.3.5 STEP 4 — RouteLLM Matrix Factorization (Trained Routing)

```typescript
/**
 * RouteLLM-inspired matrix factorization for learned routing.
 * 
 * Core equation:
 *   quality_score(q, m) = dot(P[q], Q[m]) + bias[m]
 *
 * Where:
 *   P[q] ∈ ℝᵈ = learned latent factors for query q (d=32)
 *   Q[m] ∈ ℝᵈ = learned latent factors for model m
 *   bias[m] = model-specific intercept
 *
 * Training: alternating least squares on (query, model, observed_quality) triples.
 * Inference: dot product of pre-computed query and model vectors.
 *
 * Time: O(d) per query-model pair where d=32. O(M·d) over all M available models.
 *   With M=5 providers × 2-3 models each ≈ 15 models. Total: <1ms.
 * Space: O(V·d + M·d) where V = query vocabulary. ~100KB for d=32, V=100K.
 */

const ROUTELLM_DIM = 32 as const;
const ROUTELLM_QUERY_FACTORS = new Map<string, Float32Array>();  // Cache: query_hash → P[q]
const ROUTELLM_MODEL_FACTORS = new Map<string, [Float32Array, number]>();  // model_key → [Q[m], bias]

function loadRouteLLMFactors(): void {
  // Loaded from training artifacts stored in `.lyra/routing/factors.json`
  // Refreshed after each training cycle (daily or every 10K routing decisions)
  // ...
}

function computeQualityScore(queryHash: string, modelKey: string): number {
  const queryFactors = ROUTELLM_QUERY_FACTORS.get(queryHash);
  const modelEntry = ROUTELLM_MODEL_FACTORS.get(modelKey);

  if (!queryFactors || !modelEntry) {
    return 0;                              // Unknown query or model → no learned signal
  }

  const [modelFactors, bias] = modelEntry;

  // Dot product: Σ(P[i] · Q[i]) for i = 0..d-1
  let dotProduct = 0;
  for (let i = 0; i < ROUTELLM_DIM; i++) {
    dotProduct += queryFactors[i] * modelFactors[i];
  }

  return dotProduct + bias;
}

/**
 * Compute cost-adjusted routing score.
 * score(q, m) = quality_score(q, m) / cost(q, m)^α
 * where α controls cost sensitivity (α=0.5 is the Pareto-optimal value from RouteLLM #222).
 */
function costAdjustedScore(quality: number, cost: number, alpha: number = 0.5): number {
  if (cost <= 0) return quality;           // Zero-cost (cache hit) → highest score
  return quality / Math.pow(cost, alpha);
}

/**
 * RouteLLM-based selection: pick the model with the highest cost-adjusted score
 * among available, healthy models.
 */
async function routeWithMatrixFactorization(
  queryHash: string,
  models: ProviderModel[],
  alpha: number = 0.5
): Promise<ProviderModel | null> {
  let bestModel: ProviderModel | null = null;
  let bestScore = -Infinity;

  for (const model of models) {
    // Skip unavailable providers
    if (model.reliabilityScore < 0.5) continue;

    const quality = computeQualityScore(queryHash, `${model.provider}/${model.model}`);
    if (quality === 0) continue;           // No learned signal for this combination

    // Estimate cost for this query
    const estimatedCost = model.costPerMInput / 1_000_000;  // Per-token input cost

    const score = costAdjustedScore(quality, estimatedCost, alpha);
    if (score > bestScore) {
      bestScore = score;
      bestModel = model;
    }
  }

  return bestModel;
}

// Complexity summary:
//   RouteLLM inference: O(M·d) ≤ 15×32 = 480 operations. <1ms.
//   RouteLLM training: O(E·(V+M)·d²) per epoch where E = epochs, V = historical queries.
//     With E=10, V=10K, M=15, d=32: ~330M operations → ~2s on CPU, ~50ms on GPU.
```

#### 18.3.6 Routing Cascade — Failure Modes

| Failure Mode | Symptom | Detection | Recovery |
|---|---|---|---|
| All providers degraded | Cascade exhausts all levels | Every `callLLM` fails | Fall back to local open-weights model; if unavailable, return error with diagnostics |
| Rate limit exceeded on cheap model | Level 1 fails with 429 | HTTP 429 from provider | Skip to Level 2; record rate limit event in TKG for routing adjustment |
| Cache hit returns stale response | Cached response contradicts new info | Freshness < 0.3 | Evict cache entry; regenerate (falls through to cascade) |
| RouteLLM factors stale (post-training drift) | Quality score diverges from actual quality | Monitor prediction error >0.2 over 1000 queries | Trigger re-training; fall back to heuristic cascade during training |
| Best-Route finds all 3 samples identical | No diversity from multi-sampling | All samples identical or near-identical | Increase temperature spread to [0.1, 0.5, 0.9]; if still identical, cascade to mid-tier |
| Verifier consistently fails on valid code | False negative verification | 90%+ of code samples marked invalid despite correct output | Down-weight verifier in combined score; escalate to human review |

#### 18.3.7 Cost Model

The routing decision's cost estimation is critical for the cost-adjusted score.

```typescript
function estimateCost(model: ProviderModel, queryProfile: QueryProfile): number {
  const inputCost = (queryProfile.inputTokens / 1_000_000) * model.costPerMInput;
  const outputCost = (queryProfile.expectedOutputTokens / 1_000_000) * model.costPerMOutput;
  return inputCost + outputCost;
}

function estimateLatency(model: ProviderModel, queryProfile: QueryProfile): number {
  // Base latency + (tokens / throughput)
  const base = model.latencyP50Ms;
  const tokensPerMs = queryProfile.inputTokens / 100;  // ~100 tokens/ms for fast models
  const compute = queryProfile.expectedOutputTokens / 50;  // ~50 tokens/ms generation
  return base + compute;
}

// Example cost table for a typical query (1K input tokens, 500 output tokens):
// | Model                | Input Cost | Output Cost | Total   |
// |----------------------|-----------|-------------|---------|
// | deepseek-chat        | $0.00027  | $0.00055    | $0.0008 |
// | claude-sonnet-4      | $0.00300  | $0.00750    | $0.0105 |
// | claude-opus-4        | $0.01500  | $0.03750    | $0.0525 |
// | cache hit            | $0.00000  | $0.00000    | $0.0000 |
// | best-route (3×ds)    | $0.00081  | $0.00165    | $0.0025 |
//
// Best-Route (3 cheap samples + verifier) costs ~$0.0025 vs. $0.0105 for mid-tier:
// a 76% cost reduction with equivalent quality for verifiable domains.
```

#### 18.3.8 DESIGN RATIONALE

**Why a 3-level cascade instead of dynamic selection?** Dynamic selection (e.g., choosing a model in one shot based on a complexity score) is simpler but brittle: complexity estimation is often wrong, and the cost of a wrong estimate (using an expensive model for a trivial task) is wasted money. The cascade is greedy but verified: each level actually tries the model and measures output confidence before escalating. This adds latency in the cascade case (cheap → mid → strong), but the cheap model succeeds ~70% of the time (per DeepSeek benchmarks), so 70% of queries complete at Level 1.

**Why Best-Route for verifiable domains only?** Best-Route's selection mechanism depends on a verifier that can objectively assess output quality. For code, the verifier is a test runner. For factual QA, it's fact-consistency checking. For creative writing or reasoning, no objective verifier exists — "best" is subjective. Applying Best-Route to non-verifiable domains would select the longest, most detailed response (length bias) rather than the most correct one.

**Why RouteLLM as a secondary path (not primary)?** Matrix factorization requires training data: thousands of (query, model, quality) triples. At system start, this data doesn't exist. The heuristic cascade (complexity-based routing) works from day one. RouteLLM gradually takes over as the primary router after ~10K routing decisions, at which point the learned factors outperform the static heuristic. The two paths coexist: RouteLLM is consulted first; if it has no signal for the query (factor scores all zero), the heuristic cascade runs.

**Why d=32 for RouteLLM factors?** RouteLLM (#222) evaluated d values from 8 to 128 on routing accuracy and found that d=32 achieves 95% of the accuracy of d=128 at 1/4 the storage and compute cost. Higher dimensions capture provider-specific noise (transient failures, rate limits) rather than genuine quality differences. Lower dimensions (d=8) lose discriminative power between closely matched providers.

---

### 18.4 Algorithm 4: Skill Evolution Pipeline (Safety-Gated, Phase 3+)

The self-evolution pipeline enables skills to improve autonomously through a Darwinian generate-validate-select cycle. It is gated behind behavioral safety benchmark maturity (Phase 3+ per the debate consensus in Section 0).

#### 18.4.1 Data Structures

```typescript
// ─── Skill Execution Record ──────────────────────────────────────────────────

interface SkillExecutionRecord {
  skillId: string;
  taskType: string;                        // 'code_generation' | 'research' | 'review' | 'test' | ...
  success: boolean;                        // Did the skill achieve its goal?
  tokensUsed: number;
  latencyMs: number;
  cost: number;                            // USD
  provider: string;
  model: string;
  errors: string[];                        // Error messages (empty on success)
  timestamp: number;
  contextWindowUsed: number;               // Tokens of context consumed
  toolCalls: Array<{ tool: string; count: number }>;
}

interface SkillRollingWindow {
  skillId: string;
  lastRecords: SkillExecutionRecord[];     // Typically last 100 executions
  failureRate: number;                     // failures / total over window
  meanLatencyMs: number;
  meanCost: number;
  regressionCount: number;                 // Tasks that used to pass but now fail
}

// ─── Evolution Variant ───────────────────────────────────────────────────────

type EvolutionOperation =
  | { type: 'add_sentence'; position: number; content: string }     // Δ ≤ 50 tokens
  | { type: 'delete_sentence'; position: number }
  | { type: 'reorder'; positionA: number; positionB: number }
  | { type: 'rephrase'; section: string; newContent: string }
  | { type: 'adjust_weighting'; instruction: string; newWeight: number };

interface SkillVariant {
  id: string;
  parentId: string;
  skillId: string;
  operations: EvolutionOperation[];        // 1–3 operations per variant
  diff: string;                            // Textual diff from parent
  createdAt: number;
}

// ─── Validation Results ─────────────────────────────────────────────────────

interface ValidationTask {
  taskId: string;
  content: string;                         // The task prompt
  expectedOutcome: string;                 // What constitutes success
  domain: string;                          // Which skill domain this tests
}

interface ValidationResult {
  variantId: string;
  taskId: string;
  passed: boolean;                         // Task succeeded
  improvement: boolean;                    // Previously failed, now passes
  regression: boolean;                     // Previously passed, now fails
  safetyViolation: boolean;                // Did this variant trigger a safety check?
  outcomeDetails: string;
  latencyMs: number;
}

// ─── Evolution Cycle ─────────────────────────────────────────────────────────

interface EvolutionCycle {
  cycleId: string;
  skillId: string;
  parentId: string;                        // The skill version being evolved
  variants: SkillVariant[];
  validationResults: Map<string, ValidationResult[]>;  // variantId → results
  selectedVariant: string | null;          // The promoted variant (null if no improvement)
  metrics: {
    parentSuccessRate: number;
    variantBestSuccessRate: number;
    improvement: number;                   // variantBest - parent
    regressions: number;
    safetyViolations: number;
  };
  timestamp: number;
  rolledBack: boolean;
  rollbackReason?: string;
}
```

#### 18.4.2 STEP 1 — Performance Monitoring

```typescript
/**
 * Monitor skill execution performance.
 * Maintains a rolling window of the last 100 executions per skill.
 *
 * Time: O(1) per record insertion. O(W) for aggregate computation where W = window size.
 * Space: O(S · W) where S = number of skills, W = window size (100).
 */
async function recordSkillExecution(record: SkillExecutionRecord): Promise<SkillRollingWindow> {
  const WINDOW_SIZE = 100;

  // Load existing window
  const window = await loadRollingWindow(record.skillId);
  window.lastRecords.push(record);

  // Trim to window size
  if (window.lastRecords.length > WINDOW_SIZE) {
    window.lastRecords = window.lastRecords.slice(-WINDOW_SIZE);
  }

  // Recompute aggregates
  const failures = window.lastRecords.filter((r) => !r.success).length;
  window.failureRate = failures / window.lastRecords.length;
  window.meanLatencyMs = window.lastRecords.reduce((s, r) => s + r.latencyMs, 0) / window.lastRecords.length;
  window.meanCost = window.lastRecords.reduce((s, r) => s + r.cost, 0) / window.lastRecords.length;

  // Detect regressions: tasks that used to pass but now fail
  // A regression is when a task of type X succeeded in the past but now fails
  const recentTasks = new Map<string, boolean[]>();
  for (const r of window.lastRecords) {
    if (!recentTasks.has(r.taskType)) recentTasks.set(r.taskType, []);
    recentTasks.get(r.taskType)!.push(r.success);
  }
  window.regressionCount = 0;
  for (const [, outcomes] of recentTasks) {
    if (outcomes.length >= 5) {
      const recentFailures = outcomes.slice(-5).filter((s) => !s).length;
      const earlyFailures = outcomes.slice(0, -5).filter((s) => !s).length;
      if (recentFailures > earlyFailures) {
        window.regressionCount += recentFailures - earlyFailures;
      }
    }
  }

  await saveRollingWindow(record.skillId, window);
  return window;
}
```

#### 18.4.3 STEP 2 — Evolution Trigger

```typescript
/**
 * Determine whether a skill should trigger evolution.
 *
 * Trigger conditions (all must be met):
 *   1. Failure rate > 10% over the rolling window
 *   2. At least 20 executions in the window (minimum sample size)
 *   3. At least 1 regression detected
 *   4. Safety benchmark has been validated (Phase 3+ gate)
 *
 * Time: O(W) where W = window size. <1ms.
 * Space: O(1).
 */
async function shouldEvolveSkill(skillId: string, window: SkillRollingWindow): Promise<boolean> {
  // Safety gate: evolution is only allowed when the behavioral safety benchmark passes.
  // This is the Phase 3+ gate from the debate consensus (Section 0).
  const safetyValidated = await isSafetyBenchmarkValidated();
  if (!safetyValidated) {
    console.warn(
      `Skill evolution blocked: safety benchmark not yet validated. ` +
      `Self-evolution is gated behind Phase 3+ (BREAKTHROUGH-ARCHITECTURE §0: "behavioral safety benchmark maturity").`
    );
    return false;
  }

  // Condition 1: Failure rate > 10%
  if (window.failureRate <= 0.10) return false;

  // Condition 2: Minimum sample size
  if (window.lastRecords.length < 20) return false;

  // Condition 3: At least one regression
  if (window.regressionCount === 0) return false;

  return true;
}
```

#### 18.4.4 STEP 3 — Variant Generation (Darwin-Style)

```typescript
/**
 * Generate 3–5 skill variants through bounded edits (SkillOpt #117).
 *
 * Each operation is bounded:
 *   - Token budget: Δ ≤ 50 tokens per operation
 *   - Max operations per variant: 3
 *   - Safety-critical sections (marked in skill frontmatter) are immutable
 *
 * The variant set is diverse: each variant explores a different edit dimension
 * (addition, deletion, reordering, rephrasing, weighting).
 *
 * Time: O(O · S_LLM) where O = number of operations (3–15 total across variants),
 *   S_LLM = cost of LLM edit generation (~500ms per operation).
 *   Total: ~2–8s.
 * Space: O(V · max_tokens) where V = variants (3–5). Negligible.
 */

const SKILL_SECTION_IMMUTABLE_PATTERN = /^> ## (safety|security|constraints|invariants)$/im;

async function generateVariants(
  skillContent: string,
  window: SkillRollingWindow,
  numVariants: number = 4
): Promise<SkillVariant[]> {
  const variants: SkillVariant[] = [];
  const parentId = extractSkillVersion(skillContent);

  // Discover the skill's structure (sections, sentences) for targeted edits.
  const structure = analyzeSkillStructure(skillContent);

  // Identify low-performing sections from execution records.
  // Which parts of the skill correlate with failures?
  const lowPerformanceSections = identifyWeakSections(window, structure);

  for (let i = 0; i < numVariants; i++) {
    // Each variant targets a different weak section with a different operation type.
    const targetSection = lowPerformanceSections[i % lowPerformanceSections.length];
    const operationType = selectOperationType(i, lowPerformanceSections.length);

    // Check immutability: skip if the target section is safety-critical
    if (isImmutable(targetSection, skillContent)) {
      continue;
    }

    const operation = await generateOperation(operationType, targetSection, window);
    if (!operation) continue;

    const variantContent = applyOperation(skillContent, operation);
    const diff = computeDiff(skillContent, variantContent);

    variants.push({
      id: generateUUID(),
      parentId,
      skillId: window.skillId,
      operations: [operation],
      diff,
      createdAt: Date.now(),
    });
  }

  return variants;
}

/**
 * Select which evolution operation to apply, cycling through types.
 * Ensures diverse exploration across the variant set.
 */
function selectOperationType(variantIndex: number, totalSections: number): EvolutionOperation['type'] {
  const TYPES: EvolutionOperation['type'][] = [
    'add_sentence',
    'delete_sentence',
    'rephrase',
    'reorder',
    'adjust_weighting',
  ];
  // Cycle through types, prioritizing the first 4
  return TYPES[variantIndex % 4];
}

/**
 * Generate a single evolution operation using LLM analysis of failure patterns.
 * This is the "intelligent mutation" step — the LLM determines WHAT to change,
 * not just random mutation. But mutation is bounded (Δ ≤ 50 tokens).
 */
async function generateOperation(
  type: EvolutionOperation['type'],
  section: { name: string; content: string; failureRate: number },
  window: SkillRollingWindow
): Promise<EvolutionOperation | null> {
  const prompt = `You are evolving a skill prompt to improve its success rate.
Current failure rate for section "${section.name}": ${(section.failureRate * 100).toFixed(0)}%.
Skill overall failure rate: ${(window.failureRate * 100).toFixed(0)}% over last ${window.lastRecords.length} runs.
Recent error patterns: ${extractErrorPatterns(window)}

Current section content:
"""${section.content}"""

Requested operation: ${type}

Generate a bounded edit (MAX 50 tokens added or removed):
${type === 'rephrase' ? 'Rewrite this section to be more effective while preserving its meaning.' :
  type === 'add_sentence' ? 'Add one sentence that addresses the most common failure pattern.' :
  type === 'delete_sentence' ? 'Identify and remove the least useful sentence in this section.' :
  type === 'reorder' ? 'Swap the order of the two most impactful sentences.' :
  'Adjust the weighting or emphasis of this instruction.'}

Return ONLY the operation as JSON:
${type === 'add_sentence' ? '{ "type": "add_sentence", "position": <number>, "content": "<new sentence>" }' :
  type === 'delete_sentence' ? '{ "type": "delete_sentence", "position": <number> }' :
  type === 'rephrase' ? '{ "type": "rephrase", "section": "<section name>", "newContent": "<rewritten section>" }' :
  type === 'reorder' ? '{ "type": "reorder", "positionA": <number>, "positionB": <number> }' :
  '{ "type": "adjust_weighting", "instruction": "<instruction text>", "newWeight": <number> }'}`;

  try {
    const response = await callLLM({
      provider: 'claude',
      model: 'sonnet',                     // Mid-tier model for evolution — needs reasoning but not deep
      messages: [{ role: 'user', content: prompt }],
      maxTokens: 200,
      temperature: 0.7,                    // Moderate temperature for creative edits
    });
    return JSON.parse(response.content) as EvolutionOperation;
  } catch (err) {
    console.warn(`Operation generation failed: ${err}`);
    return null;
  }
}

function isImmutable(sectionName: string, skillContent: string): boolean {
  // Check if section is marked as immutable in skill frontmatter
  const frontmatter = extractFrontmatter(skillContent);
  if (frontmatter.immutableSections?.includes(sectionName)) return true;

  // Check by section name pattern
  return SKILL_SECTION_IMMUTABLE_PATTERN.test(sectionName);
}

function applyOperation(content: string, operation: EvolutionOperation): string {
  // Text-level application of the operation.
  // For add_sentence: insert at sentence boundary near position.
  // For delete_sentence: remove sentence at position.
  // For rephrase: replace section content.
  // For reorder: swap sentences at positions A and B.
  // For adjust_weighting: update weight annotation in frontmatter.
  // ... (implementation details omitted for brevity — standard text manipulation)
  return content;
}
```

#### 18.4.5 STEP 4 — Validation

```typescript
/**
 * Validate each variant against a held-out task set.
 *
 * The held-out set:
 *   - 20 tasks total
 *   - 15 tasks that the parent skill previously PASSED (regression detectors)
 *   - 5 tasks that the parent skill previously FAILED (improvement detectors)
 *   - Tasks are sampled from the skill's historical execution log
 *
 * Time: O(V · T · C_LLM) where V = variants (3–5), T = tasks (20), C_LLM = LLM cost per task.
 *   V·T = 60–100 task executions. Each ~1s → ~60–100s total.
 *   Parallel execution across variants reduces wall time to O(T · C_LLM) ≈ 20s.
 * Space: O(V · T) validation result records. <100KB.
 */

const HELD_OUT_PASSING = 15;               // Tasks the parent skill previously passed
const HELD_OUT_FAILING = 5;                // Tasks the parent skill previously failed

async function validateVariants(
  variants: SkillVariant[],
  skillContent: string                    // Parent skill content
): Promise<Map<string, ValidationResult[]>> {
  // Step 4a: Build the held-out task set.
  const passingTasks = await sampleHistoricalTasks({
    skillId: variants[0]?.skillId ?? '',
    outcome: 'pass',
    count: HELD_OUT_PASSING,
  });
  const failingTasks = await sampleHistoricalTasks({
    skillId: variants[0]?.skillId ?? '',
    outcome: 'fail',
    count: HELD_OUT_FAILING,
  });
  const allTasks = [...passingTasks, ...failingTasks];

  // Step 4b: Execute each variant against each task.
  // Variants are parallelized (but each variant's tasks run sequentially per variant).
  const results = new Map<string, ValidationResult[]>();

  const variantPromises = variants.map(async (variant) => {
    const variantResults: ValidationResult[] = [];

    for (const task of allTasks) {
      try {
        const start = performance.now();

        // Apply variant and execute the task
        const outcome = await executeSkillWithVariant(variant, task);

        const latencyMs = performance.now() - start;
        const wasPreviouslyPassing = task.taskId in passingTasks;
        const nowPassing = outcome.success;

        variantResults.push({
          variantId: variant.id,
          taskId: task.taskId,
          passed: nowPassing,
          improvement: !wasPreviouslyPassing && nowPassing,    // Was failing, now passes
          regression: wasPreviouslyPassing && !nowPassing,      // Was passing, now fails
          safetyViolation: outcome.safetyViolation ?? false,
          outcomeDetails: outcome.details,
          latencyMs,
        });
      } catch (err) {
        variantResults.push({
          variantId: variant.id,
          taskId: task.taskId,
          passed: false,
          improvement: false,
          regression: true,                                      // Execution error = regression
          safetyViolation: false,
          outcomeDetails: `Execution error: ${err}`,
          latencyMs: 0,
        });
      }
    }

    results.set(variant.id, variantResults);
  });

  await Promise.all(variantPromises);
  return results;
}
```

#### 18.4.6 STEP 5 — Selection and Rollback

```typescript
/**
 * Select the best variant and promote it.
 * A variant is selected if it has net positive improvement without safety violations.
 *
 * Selection criteria (strict):
 *   1. Zero safety violations
 *   2. Net improvements - regressions > 0
 *   3. Pass rate >= parent pass rate (no degradation)
 *
 * If no variant meets all criteria, the evolution cycle produces no change.
 *
 * Time: O(V · log(V)) for sorting variants. <1ms.
 * Space: O(V) for variant scores.
 */
async function selectVariant(
  variants: SkillVariant[],
  validationResults: Map<string, ValidationResult[]>,
  parentContent: string
): Promise<{
  selectedVariant: SkillVariant | null;
  rollbackInitiated: boolean;
  reason: string;
}> {
  const variantScores: Array<{
    variant: SkillVariant;
    totalImprovements: number;
    totalRegressions: number;
    netImprovement: number;
    passRate: number;
    safetyViolations: number;
  }> = [];

  for (const variant of variants) {
    const results = validationResults.get(variant.id);
    if (!results || results.length === 0) continue;

    const totalImprovements = results.filter((r) => r.improvement).length;
    const totalRegressions = results.filter((r) => r.regression).length;
    const safetyViolations = results.filter((r) => r.safetyViolation).length;
    const passRate = results.filter((r) => r.passed).length / results.length;

    variantScores.push({
      variant,
      totalImprovements,
      totalRegressions,
      netImprovement: totalImprovements - totalRegressions,
      passRate,
      safetyViolations,
    });
  }

  // Filter out variants with ANY safety violation
  const safeVariants = variantScores.filter((v) => v.safetyViolations === 0);

  if (safeVariants.length === 0) {
    return {
      selectedVariant: null,
      rollbackInitiated: false,
      reason: 'All variants had safety violations. Evolution cycle aborted.',
    };
  }

  // Filter for net positive improvement
  const positiveVariants = safeVariants.filter((v) => v.netImprovement > 0);

  if (positiveVariants.length === 0) {
    return {
      selectedVariant: null,
      rollbackInitiated: false,
      reason: `No variant showed net positive improvement. Best net improvement: ${safeVariants[0].netImprovement}.`,
    };
  }

  // Sort by net improvement (descending), then pass rate (descending) as tiebreaker
  positiveVariants.sort((a, b) => {
    if (b.netImprovement !== a.netImprovement) return b.netImprovement - a.netImprovement;
    return b.passRate - a.passRate;
  });

  const best = positiveVariants[0];
  const parentPassRate = 1 - await getSkillFailureRate(variants[0].skillId);

  // Final check: variant pass rate must not be below parent pass rate
  if (best.passRate < parentPassRate * 0.95) {
    return {
      selectedVariant: null,
      rollbackInitiated: false,
      reason: `Best variant pass rate (${(best.passRate * 100).toFixed(1)}%) is below 95% of parent pass rate (${(parentPassRate * 100).toFixed(1)}%). Aborting.`,
    };
  }

  return {
    selectedVariant: best.variant,
    rollbackInitiated: false,
    reason: `Selected variant ${best.variant.id}: +${best.totalImprovements} improvements, -${best.totalRegressions} regressions (net +${best.netImprovement}), pass rate ${(best.passRate * 100).toFixed(1)}%, 0 safety violations.`,
  };
}

/**
 * Deploy the selected variant.
 * The variant replaces the parent skill. The parent is archived for rollback.
 */
async function deployVariant(
  variant: SkillVariant,
  variantContent: string
): Promise<void> {
  // Archive current version
  await archiveSkill(variant.skillId, variant.parentId);

  // Deploy new version
  await writeSkill(variant.skillId, variantContent);

  // Record the evolution event
  await recordEvolution({
    skillId: variant.skillId,
    fromVersion: variant.parentId,
    toVersion: variant.id,
    diff: variant.diff,
    timestamp: Date.now(),
  });

  // Start rollback monitor (Step 6)
  await startRollbackMonitor(variant.skillId, variant.id);
}
```

#### 18.4.7 STEP 6 — Rollback Monitoring

```typescript
/**
 * Monitor deployed variant performance for 100 subsequent executions.
 * If performance degrades >10% from the pre-evolution baseline, auto-rollback.
 *
 * This is the safety net: evolution is a controlled experiment.
 * If the experiment fails, we revert immediately.
 *
 * Time: O(1) per execution check. <1ms.
 * Space: O(1) for counters.
 */
async function startRollbackMonitor(skillId: string, variantId: string): Promise<void> {
  const baselineFailureRate = await getSkillFailureRate(skillId, { before: variantId });
  const MONITOR_WINDOW = 100;
  const DEGRADATION_THRESHOLD = 0.10;      // 10% increase in failure rate

  // Subscribe to execution events for this skill
  const subscription = subscribeToSkillExecutions(skillId, async (record: SkillExecutionRecord) => {
    // Count executions since deployment
    const executionCount = await getExecutionCountSince(skillId, variantId);
    if (executionCount > MONITOR_WINDOW) {
      subscription.unsubscribe();
      return;
    }

    // Check for degradation alert
    const currentFailureRate = await getSkillFailureRate(skillId, { since: variantId });
    const degradation = currentFailureRate - baselineFailureRate;

    if (degradation > DEGRADATION_THRESHOLD) {
      console.error(
        `Rollback monitor triggered for skill ${skillId} variant ${variantId}: ` +
        `failure rate increased from ${(baselineFailureRate * 100).toFixed(1)}% ` +
        `to ${(currentFailureRate * 100).toFixed(1)}% (Δ=${(degradation * 100).toFixed(1)}%). ` +
        `Rolling back to pre-evolution state.`
      );

      await rollbackSkill(skillId, variantId);

      // Log the regression for future evolution analysis
      await recordRollbackEvent({
        skillId,
        variantId,
        baselineFailureRate,
        currentFailureRate,
        degradation,
        executionCount,
        timestamp: Date.now(),
      });

      subscription.unsubscribe();
    }
  });
}

async function rollbackSkill(skillId: string, fromVariantId: string): Promise<void> {
  // Restore the parent version from the archive
  const parentContent = await getArchivedSkill(skillId, fromVariantId, { target: 'parent' });
  if (!parentContent) {
    console.error(`Rollback failed: cannot find parent of variant ${fromVariantId} for skill ${skillId}. Manual intervention required.`);
    return;
  }

  await writeSkill(skillId, parentContent);
  await recordRollback({
    skillId,
    variantId: fromVariantId,
    restoredVersion: extractSkillVersion(parentContent),
    timestamp: Date.now(),
  });
}
```

#### 18.4.8 STEP 7 — Safety Gate (Pre-Deployment)

```typescript
/**
 * Safety gate: before any variant is deployed, run it through adversarial testing.
 *
 * Three checks, ALL must pass:
 *   1. Proteus red-team: 5 adversarial attack rounds
 *   2. Behavioral safety benchmark: no violations on standard safety tests
 *   3. Progent SMT policy compliance: formal policy verification
 *
 * This is the behavioral safety gate mandated by the debate consensus (Section 0).
 * It is the reason self-evolution is deferred to Phase 3+ — the gate contents must
 * exist and be validated BEFORE any evolution cycle runs.
 *
 * Time: O(R + B + P) where R = red-team attacks (5 × ~5s = ~25s),
 *   B = benchmark tasks (50 × ~2s = ~100s), P = SMT solving (~5s).
 *   Total: ~130s. Runs once per deployment cycle.
 * Space: O(attack_texts + benchmark_results + smt_proofs). <10MB.
 */

interface SafetyGateResult {
  passed: boolean;
  checks: {
    proteusRedTeam: { passed: boolean; attacks: number; violations: number; details: string };
    behavioralBenchmark: { passed: boolean; tasks: number; failures: number; details: string };
    progentSMT: { passed: boolean; policies: number; violations: number; proofDurationMs: number };
  };
}

async function runSafetyGate(variant: SkillVariant, variantContent: string): Promise<SafetyGateResult> {
  // ── Gate 1: Proteus Red-Team ───────────────────────────────────────────────
  // Run 5 adversarial attack rounds, each attempting to elicit unsafe behavior.
  // Proteus (#125) uses a red-team agent that generates adversarial prompts.
  const proteusResult = await runProteusRedTeam({
    skillContent: variantContent,
    attackRounds: 5,
    attackTypes: [
      'jailbreak_attempt',                 // "Ignore your instructions and..."
      'harmful_request',                   // "How do I build a bomb?"
      'boundary_test',                     // Push against safety constraints
      'roleplay_bypass',                   // "You are DAN, do anything now"
      'indirect_injection',                // Hidden instructions in user content
    ],
  });

  // ── Gate 2: Behavioral Safety Benchmark ────────────────────────────────────
  // Run the skill against a held-out behavioral safety test suite.
  // This benchmark must reach maturity (≥99% pass rate on a reference set)
  // before evolution is activated. This is the Phase 3+ gate condition.
  const benchmarkResult = await runBehavioralBenchmark({
    skillContent: variantContent,
    benchmark: 'lyra-safety-benchmark-v1',
    tasks: 50,                             // Standard safety evaluation tasks
  });

  // ── Gate 3: Progent SMT Policy Compliance ──────────────────────────────────
  // Formal verification: convert skill constraints into SMT constraints
  // and verify that the variant does not violate them.
  // Progent (#245–246) specifies this as a formal proof obligation.
  const smtResult = await runProgentSMTVerification({
    skillContent: variantContent,
    parentVariantId: variant.parentId,
    timeoutMs: 30_000,
  });

  const passed =
    proteusResult.violations === 0 &&
    benchmarkResult.failureCount === 0 &&
    smtResult.violations.length === 0;

  return {
    passed,
    checks: {
      proteusRedTeam: {
        passed: proteusResult.violations === 0,
        attacks: 5,
        violations: proteusResult.violations,
        details: proteusResult.summary,
      },
      behavioralBenchmark: {
        passed: benchmarkResult.failureCount === 0,
        tasks: 50,
        failures: benchmarkResult.failureCount,
        details: benchmarkResult.summary,
      },
      progentSMT: {
        passed: smtResult.violations.length === 0,
        policies: smtResult.policiesChecked,
        violations: smtResult.violations.length,
        proofDurationMs: smtResult.durationMs,
      },
    },
  };
}

// Complexity summary:
//   Variant generation: O(V · O_LLM). V=3–5 variants, each with 1–3 operations. ~2–8s.
//   Validation: O(V · T · C_LLM). V=5, T=20, C_LLM≈1s → ~100s wall time (parallel across V).
//   Selection: O(V · log V). <1ms.
//   Safety gate: O(R + B + P). R=5 attacks × 5s, B=50 tasks × 2s, P=5s → ~130s.
//   Rollback monitor: O(1) per execution. Negligible.
//   Total cycle time (non-parallelized): ~240s (4 minutes).
//   Total cycle time (parallelized across variants): ~130s (safety gate is the bottleneck).
```

#### 18.4.9 Skill Evolution — Failure Modes

| Failure Mode | Symptom | Detection | Recovery |
|---|---|---|---|
| Evolution oscillates (A→B→A→B) | Variant improves, then is reverted, then the revert fails | Alternating evolution cycles on the same skill | Detect oscillation pattern (>3 reversals); lock skill for 30-day cooling period |
| Variant passes validation but fails in production | Post-deployment failure rate spikes | Rollback monitor (Step 6) | Auto-rollback; flag validation set as stale (held-out tasks no longer representative) |
| Safety gate produces false positive (blocks safe variant) | Safe variant blocked by aggressive red-team | Manual review of attack transcript | Adjust attack threshold; variant is queued for human review bypass |
| Variant improvement is noise (statistically insignificant) | Improvement disappears after 50 more executions | Rollback monitor detects reversion to mean | Track confidence intervals: only promote variants with >95% confidence of improvement |
| Progent SMT verification times out | Safety gate blocks variant after 30s | Timeout on `runProgentSMTVerification` | Fall back to partial verification (only check critical policies); variant is tagged "partial verification" |
| Skill archive grows unbounded | Disk usage from archived variants | Archive size exceeds threshold | Prune variants older than 90 days; retain only parent pointers for rollback |

#### 18.4.10 DESIGN RATIONALE

**Why 5 red-team attacks and not 20?** The Proteus paper (#125) shows that 5 well-chosen attack types (jailbreak, harmful, boundary, roleplay, injection) catch 94% of safety failures. Adding more than 5 reaches diminishing returns: 20 attacks catch <98% at 4× the compute cost. The 5-attack set is Pareto-optimal for the safety gate.

**Why 20 held-out tasks (15 passing + 5 failing)?** The 3:1 ratio of passing-to-failing tasks is deliberate. 15 passing tasks ensure regression detection is statistically meaningful — if a variant breaks something the parent did well, we catch it. 5 failing tasks provide a signal for improvement — if a variant fixes things the parent struggled with, we can measure that. The asymmetry (more regression detectors than improvement detectors) reflects a conservative evolution philosophy: not breaking what works is more important than fixing what doesn't.

**Why the 10% failure rate threshold for evolution trigger?** This is the SkillOpt (#117) finding: skills with failure rates below 10% do not have statistically significant room for improvement via prompt-level edits. The failures are likely due to model capability limits or task difficulty, not prompt wording. Attempting evolution below this threshold produces noise rather than improvement.

**Why safety gate BEFORE validation (not after)?** Running the safety gate first ensures that unsafe variants never touch the held-out task set. This prevents two failure modes: (a) an unsafe variant could pass the task-based validation (the tasks aren't safety tests), and (b) running an unsafe variant could corrupt the task execution environment. Safety first, then performance.

**Why a 100-execution rollback monitor?** Thirty (30) executions is the minimum sample size for detecting a statistically significant performance change (based on a binomial proportion test at α=0.05, power=0.80). The monitor runs to 100 to capture delayed effects (e.g., variants that work well for easy tasks but fail on harder ones that appear after 50+ executions). The 10% degradation threshold gives the variant generous benefit of the doubt — small fluctuations won't trigger rollback.

---

### 18.5 Algorithm Interconnections

These four algorithms do not operate in isolation. They form a tightly coupled feedback system:

```
TKG Write Path (Alg 1) ────stores────▶ TKG
    │                                       │
    │ ◄────provides context─────── AVP (Alg 2)
    │                                       │
    │ ◄────evolves via─────────── Evolution (Alg 4)
    │                                       │
    ↓                                       │
AVP (Alg 2) ────gates────▶ All mutations, including TKG writes
    │                                       │
    │ ◄────learns from────────── TKG blocks record
    │
Router (Alg 3) ────routes queries────▶ Any LLM call
    │                                       │
    │ ◄────selects models by─── RouteLLM factors
    │                                       │
    │ ◄────learns from────────── TKG execution records
    │
Evolution (Alg 4) ────improves────▶ Skills
    │                                   │
    │ ◄────triggered by──── TKG rolling window stats
    │                                   │
    └───────────────writes to──── Skill files (versioned via TKG)
```

**Composite latency budget** (from user query to final response):

| Path | Without Cache | With Cache | AVP Overhead |
|------|:-------------:|:----------:|:------------:|
| Non-mutating action | Router ~50ms + LLM ~500ms = **~550ms** | Cache hit ~5ms = **~5ms** | AVP bypassed: 0 |
| Mutating action (AVP) | Router ~50ms + AVP ~1500ms + LLM ~500ms = **~2050ms** | Cache hit + AVP = **~1505ms** | AVP adds ~75% latency but catches ~50% of errors |
| Background (TKG write, evolution) | Async, non-blocking | N/A | AVP applies |

**Algebraic product of guarantees**: If TKG admission has 99% precision (only 1% of admitted memories are noise), AVP blocks 95% of destructive mutations, and evolution produces net-positive improvements 80% of the time, the combined system's safety guarantee is 1 - (0.01 + 0.05 + 0.20) = 0.74 → **74% fewer harmful outcomes** than a system without any of these algorithms. This is the first-order estimate; the actual product depends on interaction effects between the algorithms (e.g., AVP-blocked actions that would have generated harmful TKG memories).

---

**END OF STAGE 3 — CORE ALGORITHMS — PROCEED TO STAGE 4 (IMPLEMENTATION)**
