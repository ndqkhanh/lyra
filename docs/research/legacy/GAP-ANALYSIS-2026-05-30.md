# Gap Analysis: STREAM-3 Research vs Lyra Existing Architecture

> **Date:** 2026-05-30
> **Purpose:** Map every finding from paper/awesome-list research against Lyra's existing V2/V3 designs to identify precise enhancement targets.

---

## 1. Memory Architecture

### What Lyra V3 Already Has
- 7-tier memory: Working → Episodic → Semantic → Procedural → Persistent → Vector → Archive
- 3.5M token effective context target (437x expansion)
- 30-50x compression ratio target
- Dream consolidation (sleep-phase memory reorganization)
- SQLite + Chroma hybrid storage

### What STREAM-3 Research Surfaces as Missing
| Technique | Source | Lyra V3 Status | Action |
|-----------|--------|---------------|--------|
| **Bi-temporal knowledge graph edges** | MemAgent Workshop, Zep | NOT IN V3 | Add temporal validity intervals to semantic graph |
| **Subconscious memory monitor (RecMem)** | arXiv:2605.16045 | NOT IN V3 | Embedding monitor detects recurrence before LLM extraction (87% token savings) |
| **MAGMA 4-graph architecture** | arXiv:2601.03236 | PARTIAL (V3 has graph but single-typed) | Add temporal, causal, entity graphs alongside semantic |
| **Prism evolutionary memory for multi-agent** | arXiv:2604.19795 | NOT IN V3 | Fleet-tier memory with evolutionary selection |
| **Focus Agent autonomous compression trigger** | arXiv:2601.07190 | NOT IN V3 | Agent decides when to compact, not fixed thresholds |
| **Experience compression spectrum** | arXiv:2604.15877 | NOT IN V3 | Unify memory/skills/rules on single compression continuum |
| **MemPalace 96.6% R@5 with zero LLM calls** | MemPalace | NOT IN V3 | Pure embedding retrieval without LLM dependency for recall |

### Enhancement Priority
1. **CRITICAL**: Add bi-temporal edges to T5 (Semantic Memory graph) — enables "what did we know when"
2. **CRITICAL**: Add RecMem subconscious monitor between T1 (Episodic) and T2 (Semantic)
3. **HIGH**: Split T5 semantic graph into MAGMA-style 4-graph (semantic/temporal/causal/entity)
4. **HIGH**: Add autonomous compression trigger (agent-initiated, not threshold-based)
5. **MEDIUM**: Evolutionary fleet memory substrate for T4 (Persistent)

---

## 2. Context Engineering

### What Lyra Already Has
- 5-layer context engine with cache breakpoints
- Subagent context isolation (67% token reduction claimed)
- Append-only context log pattern understood

### What STREAM-3 Research Surfaces as Missing
| Technique | Source | Lyra Status | Action |
|-----------|--------|------------|--------|
| **Filesystem-as-context** | Azure SRE Agent (45→75% improvement) | NOT IMPLEMENTED | Expose everything as files; agent uses grep/find/read |
| **Progressive context disclosure** | Trellis, OpenViking | NOT IMPLEMENTED | Load only needed standards per task step |
| **Tool masking (not removal)** | Manus Context Engineering | NOT IMPLEMENTED | Hide irrelevant tools; preserve attention structure |
| **Context negotiation** | Vercel Content Negotiation | NOT IMPLEMENTED | Agents request specific context formats |
| **Context poisoning detection** | Canary tokens, input sanitization | PARTIAL | Add canary-based poisoning detection |

### Enhancement Priority
1. **CRITICAL**: Filesystem-as-context delivery layer (highest ROI of any single technique)
2. **HIGH**: Progressive context disclosure (reduce token waste on irrelevant context)
3. **HIGH**: Tool masking instead of removal (preserves model attention patterns)
4. **MEDIUM**: Context negotiation protocol (agents specify what context they need)

---

## 3. Model Routing

### What Lyra V3 Already Has
- NeuralUCB contextual bandit router
- 84% cost reduction target
- Online learning from feedback
- Pareto optimization over cost/quality/latency
- Fast/smart model slots

### What STREAM-3 Research Surfaces as Missing
| Technique | Source | Lyra V3 Status | Action |
|-----------|--------|---------------|--------|
| **Minimax routing regret bound (CARROT)** | arXiv:2502.03261 | NOT IN V3 | Achieves theoretical lower bound for routing regret; matches GPT-4o at 30% cost |
| **Behavioral fingerprint routing (SCOPE)** | arXiv:2601.22323 | NOT IN V3 | GRPO-trained router with slider-controlled accuracy-cost tradeoff |
| **Multi-turn cost-aware routing (MTRouter)** | arXiv:2604.23530 | NOT IN V3 | 58.7% cost reduction; optimizes across conversation turns |
| **NVIDIA Prefill Activation Routing** | arXiv:2603.20895 | NOT IN V3 | Uses internal prefill activations to predict correctness before generation; 74.31% savings |
| **SCOPE confidence-based escalation** | arXiv:2601.22323 | NOT IN V3 | Route to stronger model when confidence below threshold |

### Enhancement Priority
1. **HIGH**: Add CARROT minimax regret bound to existing NeuralUCB (combine exploration strategies)
2. **HIGH**: Add multi-turn awareness (MTRouter pattern) — current V3 routes per-request, not per-conversation
3. **MEDIUM**: Behavioral fingerprint integration (SCOPE pattern) for slider-controlled tradeoff
4. **LOW**: Prefill activation routing (requires model internals access; provider-dependent)

---

## 4. Skills System

### What Lyra V2 Already Has
- 7-component architecture: Loader, Manager, Learner, Creator, Auto-Evaluator, Self-Evolution Engine, Curator
- Lazy loading with ML-based predictive preloading
- Thompson Sampling for A/B testing
- Genetic algorithm for evolution (mutation/crossover/selection)
- Pareto optimization for fitness

### What STREAM-3 Research Surfaces as Missing
| Technique | Source | Lyra V2 Status | Action |
|-----------|--------|---------------|--------|
| **Evolution gates (SkillOpt)** | Microsoft SkillOpt | NOT IN V2 | Validation gates before mutation acceptance; prevents regression |
| **Trace-coupled discovery (EvoSkill)** | arXiv:2603.02766 | NOT IN V2 | Extract skills from agent execution traces, not manual authoring |
| **Progressive withdrawal curriculum (Skill0)** | arXiv:2604.02268 | NOT IN V2 | Gradually remove skill scaffolding; forces internalization |
| **Cross-time replay (Ctx2Skill)** | arXiv:2604.27660 | NOT IN V2 | Multi-agent self-play for skill robustness |
| **Swarm Skills (arXiv:2605.10052)** | arXiv:2605.10052 | NOT IN V2 | Self-evolving multi-agent spec with CREATE-USE-PATCH lifecycle |
| **SoK taxonomy beyond tool use** | arXiv:2602.20867 | NOT IN V2 | Skills as more than tools; procedural knowledge, patterns, conventions |

### Enhancement Priority
1. **CRITICAL**: Add SkillOpt-style evolution gates (validate before accepting mutations)
2. **HIGH**: Add EvoSkill trace-coupled discovery (mine execution traces for new skills)
3. **HIGH**: Implement Swarm Skills CREATE-USE-PATCH lifecycle
4. **MEDIUM**: Add Skill0 progressive withdrawal (skills that teach and fade)

---

## 5. Agent Swarm / Orchestration

### What Lyra Already Has
- Decentralized coordination (AutoScientists-inspired)
- Dynamic team formation around hypotheses
- Adversarial validation (critique before execution)
- Shared state: Champions, Experiment Log, Forum, Dead Ends
- 5 execution patterns: Sequential, Parallel, DAG, Wave, Recursive
- 4 consensus methods: Majority, Weighted, Unanimous, Bayesian

### What STREAM-3 Research Surfaces as Missing
| Technique | Source | Lyra Status | Action |
|-----------|--------|------------|--------|
| **Topology routing (AdaptOrch)** | arXiv:2602.16873 | NOT IN SWARM | Dynamically select orchestration topology based on task DAG (12-23% improvement) |
| **Recursive multi-agent spawning** | arXiv:2604.25917 | PARTIAL | Agents creating sub-agents recursively; need depth limits and budget controls |
| **AgentFactory accumulation pattern** | arXiv:2603.18000 | NOT IN SWARM | Accumulate and reuse successful subagents across tasks |
| **Catfish contrarian agent** | arXiv:2505.21503 | NOT IN SWARM | Prevent wrong-consensus convergence with designated contrarian |
| **Conformal social choice** | arXiv:2604.07667 | NOT IN SWARM | Calibrated act-vs-escalate decisions; 81.9% wrong-consensus interception |
| **DAOEF (>100 agent scaling)** | arXiv:2604.20129 | NOT IN SWARM | Prevents Synergistic Collapse at large agent counts |
| **AORCHESTRA auto sub-agent creation** | arXiv:2602.03786 | PARTIAL | Dynamic specialization; current team formation is hypothesis-based, not task-based |

### Enhancement Priority
1. **CRITICAL**: Add Catfish contrarian agent to prevent wrong-consensus (highest safety ROI)
2. **CRITICAL**: Add AdaptOrch topology routing (12-23% improvement from topology choice alone)
3. **HIGH**: Add AgentFactory subagent accumulation (learn from past runs)
4. **HIGH**: Conformal social choice for calibrated escalation decisions
5. **MEDIUM**: DAOEF scaling patterns for >100 agent fleets

---

## 6. Safety & Verification

### What Lyra Already Has
- 6-layer defense-in-depth (Parallax cognitive-executive separation)
- 5 reasoning pattern detectors (Deception, Self-Deception, Reward Hacking, Goal Misgeneralization, Power-Seeking)
- Cross-model adversarial verification (3-model voting)
- Cryptographic audit trail (Ed25519 signatures, hash chain)
- Intent consistency monitoring

### What STREAM-3 Research Surfaces as Missing
| Technique | Source | Lyra Status | Action |
|-----------|--------|------------|--------|
| **Agentic misalignment patterns** | Anthropic research | NOT INTEGRATED | New misalignment categories from production agent deployments |
| **Pass^k reliability (not pass@k)** | Backtesting AI Agents | NOT IN SAFETY | All N trials must succeed; stricter than current validation |
| **Behavioral fingerprint regression (AgentAssay)** | arXiv:2603.02601 | NOT IN SAFETY | 86% regression detection vs 0% binary pass/fail |
| **Causal root cause analysis (AgentTrace)** | arXiv:2603.14688 | NOT IN SAFETY | 93.6% accuracy, 69x faster than LLM-based diagnosis |
| **Intent-based authorization (nah)** | github.com/manuelschipper/nah | NOT IN SAFETY | Classify tool calls by intent, not just command name |

### Enhancement Priority
1. **CRITICAL**: Add behavioral fingerprint regression detection (AgentAssay) — current binary validation misses 86% of regressions
2. **HIGH**: Causal root cause analysis (AgentTrace) — replaces slow LLM-based debugging
3. **HIGH**: Pass^k reliability metric — raise the bar from "usually works" to "always works"
4. **MEDIUM**: Intent-based authorization — more nuanced than command-name allowlisting

---

## 7. Full Autonomy

### What Lyra Already Has
- Continuous operation loop (partial)
- Agent lifecycle management
- Task resumption (partial)

### What STREAM-3 Research Surfaces as Missing
| Technique | Source | Lyra Status | Action |
|-----------|--------|------------|--------|
| **Continuous-claude full loop** | continuous-claude repo | NOT FULLY IMPLEMENTED | Persist, resume, self-direct, handle interruptions |
| **File-as-Bus thin control** | arXiv:2604.13018 | NOT IN AUTONOMY | Thin control over thick state; +31.82 MLE-Bench Lite |
| **PALADIN failure recovery** | AAAI 2026 | NOT IN AUTONOMY | Systematic failure injection training; 89.7% recovery rate |
| **Dream consolidation (offline)** | Lyra V3 Memory | DESIGNED, NOT BUILT | Sleep-phase memory consolidation during idle periods |

### Enhancement Priority
1. **CRITICAL**: Complete full autonomy loop (continuous-claude pattern)
2. **HIGH**: File-as-Bus pattern for state management during long runs
3. **HIGH**: PALADIN failure recovery training
4. **MEDIUM**: Dream consolidation during idle periods

---

## Summary: Critical Path

```
Week 1-2:  Filesystem-as-context + MCP Gateway + Voice UX
Week 3-4:  Temporal KG + RecMem subconscious + Fleet memory
Week 5-6:  Self-evolving harness + Catfish contrarian + AdaptOrch topology
Week 7-8:  Behavioral fingerprint + Causal RCA + CARROT routing
Week 9-10: Full autonomy + Sandbox isolation + Production hardening
```

**Immediate next actions (can start now, independent of remaining research streams):**
1. Filesystem-as-context delivery layer (S-tier, low effort, proven 45→75% improvement)
2. MCP gateway with top-20 server bundling (A-tier, medium effort, instant capability)
3. Voice/sound UX system (A-tier, low effort, high differentiation)
4. Skill evolution gates (B-tier, medium effort, prevents regression)
