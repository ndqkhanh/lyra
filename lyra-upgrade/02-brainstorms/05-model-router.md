# Brainstorm: Model Router (§4.5) — Memory-Augmented Routing

**Workstream**: §4.5 Intelligent Model Router  
**Date**: 2026-05-31  
**Status**: Breakthrough ideas generated

---

## Sources Gathered

### Routing Frameworks
1. **RouteLLM** (LMSYS/Berkeley) — 4 router types (similarity, BERT, causal LM, matrix factorization)
2. **BEST-Route** (Microsoft ICML 2025) — Route model + dynamic sample count by difficulty
3. **Hybrid LLM** (Microsoft ICLR 2024) — Cost/quality router
4. **FrugalGPT** (Stanford) — LLM cascade, 98% cost reduction
5. **Knowledge Access Beats Model Size** (2026) — Memory-augmented routing, 90%+ reduction for repeats

### Multi-Provider Context
6. **Lyra's provider abstraction** (§4.5 requirement) — Claude, DeepSeek, Qwen, GPT, open-weights
7. **Small Language Models are the Future** (NVIDIA) — SLMs sufficient for repetitive calls
8. **Skills system** (§4.4) — Router-aware skill selection with complexity metadata

---

## Novel Breakthrough Ideas (≥3 Required)

### Idea 1: **Hierarchical Cascade with Confidence-Based Escalation**

**Sources Combined**:
- FrugalGPT cascade (98% cost reduction)
- BEST-Route dynamic sampling
- RouteLLM similarity-based routing
- Lyra's memory architecture (§4.2)

**Mechanism**:
Implement a **3-tier cascade** with smart escalation:
1. **Tier 1 (Memory)**: Check if query answered before → return cached (§4.2 integration)
2. **Tier 2 (Cheap model)**: Route to haiku/deepseek-flash → if confidence >0.85, return
3. **Tier 3 (Expensive model)**: Escalate to sonnet/opus if confidence <0.85

**Confidence scoring**:
- Similarity to training data (RouteLLM)
- Query complexity (BEST-Route difficulty estimation)
- Historical success rate for similar queries
- Model's own uncertainty signals (logprobs, hedging language)

**Dynamic sampling** (BEST-Route):
- Simple queries: 1 sample from cheap model
- Medium queries: 3 samples, majority vote
- Complex queries: Escalate immediately to expensive model

**Why It Beats Individual Sources**:
- FrugalGPT alone: Fixed cascade, no confidence-based escalation
- BEST-Route alone: No memory tier, no multi-provider support
- **Fusion**: 3-tier system with memory (90%+ savings for repeats) + confidence escalation (prevents cheap model failures)

**Expected Impact**: 85-90% cost reduction overall, 95%+ quality maintenance

**Rough Effort**: MEDIUM-HIGH (8-10 weeks) — confidence scoring + escalation logic + memory integration

**Failure Modes**:
- Confidence scoring inaccurate → wrong escalation decisions
- Cascade overhead → slower than direct routing for novel queries
- Memory cache misses → wasted lookup time

---

### Idea 2: **Provider-Aware Routing with Capability Matching**

**Sources Combined**:
- Lyra's provider abstraction (5 providers)
- Skills system complexity metadata (§4.4)
- RouteLLM matrix factorization
- NVIDIA SLMs paper (heterogeneous multi-model systems)

**Mechanism**:
Route based on **provider capabilities** + **task requirements**:
1. **Capability matrix**: Track what each provider supports
   ```
   Provider | Tool Use | JSON Mode | Vision | Long Context | Cost/MTok
   Claude   | ✓        | ✓         | ✓      | 200K         | $15
   DeepSeek | ✓        | ✓         | ✗      | 64K          | $0.27
   Qwen     | ✓        | ✓         | ✓      | 32K          | $0.40
   GPT      | ✓        | ✓         | ✓      | 128K         | $5
   Local    | ✗        | ✓         | ✗      | 8K           | $0
   ```

2. **Task requirements extraction**:
   - Needs tool use? → Filter to Claude/DeepSeek/Qwen/GPT
   - Needs vision? → Filter to Claude/Qwen/GPT
   - Needs long context? → Filter to Claude/GPT
   - Skill complexity >3? → Filter to Claude/GPT

3. **Cost-optimal selection**: Among capable providers, pick cheapest

4. **Fallback chain**: If primary fails, try next-cheapest capable provider

**Why It Beats Individual Sources**:
- RouteLLM alone: Single-provider, no capability awareness
- Provider abstraction alone: Handles calls but doesn't route intelligently
- **Fusion**: True multi-provider optimization, never routes to incapable provider

**Expected Impact**: 60-70% cost reduction, 100% capability match, zero provider-mismatch failures

**Rough Effort**: MEDIUM (6-8 weeks) — capability detection + requirement extraction + fallback logic

**Failure Modes**:
- Capability matrix outdated → routes to incapable provider
- Requirement extraction misses edge cases → wrong provider selected
- Fallback chain too long → high latency on failures

---

### Idea 3: **Adaptive Router with Online Learning**

**Sources Combined**:
- BEST-Route dynamic sampling
- RouteLLM matrix factorization (learns query-model affinity)
- Darwin self-evolution (§3.18)
- Lyra's memory architecture (§4.2 trajectory logging)

**Mechanism**:
Router **learns from outcomes** and adapts over time:
1. **Trajectory logging**: Every query → model → outcome (success/failure, latency, cost)
2. **Affinity matrix**: Learn which query types work best on which models
3. **Online updates**: After each query, update routing policy based on outcome
4. **A/B testing**: Periodically route 10% of queries to non-optimal models to explore
5. **Drift detection**: If success rate drops, trigger re-calibration

Example learning:
```
Initial: "Debug auth bug" → route to opus (expensive)
After 10 successes with sonnet: Update affinity, route to sonnet
After 3 failures with sonnet: Revert to opus, mark "auth debugging" as opus-preferred
```

**Why It Beats Individual Sources**:
- BEST-Route alone: Static routing policy
- RouteLLM alone: Learns offline, not online
- **Fusion**: Continuous adaptation to actual performance, personalizes to user's query distribution

**Expected Impact**: 10-20% additional cost reduction over time, 98%+ success rate

**Rough Effort**: HIGH (10-12 weeks) — online learning + A/B testing + drift detection

**Failure Modes**:
- Learning instability → routing policy thrashes
- Exploration overhead → wastes budget on suboptimal models
- Overfitting to recent queries → poor generalization

---

### Idea 4: **Context-Aware Routing with Conversation State**

**Sources Combined**:
- RouteLLM similarity-based routing
- Lyra's memory architecture (§4.2 episodic memory)
- Claude Code sessions (§4.11)
- NVIDIA SLMs paper (heterogeneous systems)

**Mechanism**:
Route based on **conversation context**, not just current query:
1. **Session state tracking**: Track conversation complexity over time
2. **Escalation triggers**:
   - User frustration signals ("that's wrong", "try again") → escalate to better model
   - Complex follow-ups → maintain expensive model for continuity
   - Simple follow-ups → de-escalate to cheap model
3. **Context window optimization**: Long conversations → prefer models with larger context
4. **Memory integration**: If answer likely in memory, skip LLM entirely

Example flow:
```
User: "What's the capital of France?"
Router: Memory hit → return "Paris" (no LLM call)

User: "Tell me about its history"
Router: No memory hit, simple query → haiku

User: "Compare its architecture to Rome's"
Router: Complex comparison, follow-up → escalate to sonnet

User: "Thanks!"
Router: Simple acknowledgment → haiku
```

**Why It Beats Individual Sources**:
- RouteLLM alone: Routes per-query, ignores conversation state
- Memory alone: Doesn't consider conversation complexity
- **Fusion**: Conversation-aware routing, maintains quality while minimizing cost

**Expected Impact**: 40-50% cost reduction in multi-turn conversations, better UX continuity

**Rough Effort**: MEDIUM (6-8 weeks) — state tracking + escalation logic + memory integration

**Failure Modes**:
- State tracking overhead → slower routing decisions
- Escalation too aggressive → unnecessary cost
- De-escalation too aggressive → quality drops mid-conversation

---

## Parked Ideas (For Future Runs)

### Idea 5 (ADVANCED in Run 5): **Harness-Level Routing with Provider-Specific Optimization**

**Sources Fused**: Meta-Harness outer-loop search (#121) + RouteLLM matrix factorization (#222) + BEST-Route dynamic sampling (#225) + Provider Capability Matrix (BREAKTHROUGH-ARCHITECTURE §6.1)

**Mechanism**: Route not just queries but entire TASK WORKFLOWS:
1. Meta-agent analyzes a skill's full execution trace across multiple providers
2. Learns which subtasks within a skill work best on which provider (e.g., "code generation = Claude, search = DeepSeek")
3. Generates per-skill routing policies that route SUBTASKS differently within a single workflow
4. Tracks provider reliability drift and auto-updates routing when providers change

**Why It Beats Individual Sources**: RouteLLM routes queries; Meta-Harness optimizes code. Neither routes WORKFLOWS across providers. This decomposes skills into provider-optimized subtasks.

**Expected Impact**: 15-25% additional cost reduction over query-level routing (RouteLLM: 85% baseline)
**Rough Effort**: HIGH (10-12 weeks)

### Idea 6 (ADVANCED in Run 5): **Confidence-Calibrated Cascade with STITCH Filtering**

**Sources Fused**: STITCH intent-based indexing (#139) + FrugalGPT cascade (#226) + Know-Doing Gap analysis (#104) + RouteLLM confidence scoring

**Mechanism**: Before routing to LLM, filter the query through STITCH triples to determine if it's been answered before with HIGH confidence. If confidence >0.95 and STITCH intent matches exactly, return cached answer. If confidence 0.7-0.95, route to cheap model with retrieved context. If <0.7, route to expensive model. The critical innovation: STITCH filtering eliminates the "knowing-doing gap" — cases where the system has the answer but routes to LLM anyway.

**Why It Beats Individual Sources**: FrugalGPT cascades on confidence alone; STITCH adds semantic intent matching. The Know-Doing Gap paper showed 26.5-54% of queries route to LLM when memory already has the answer. STITCH + cascade eliminates this gap.

**Expected Impact**: 26-54% reduction in unnecessary LLM calls (eliminating the knowing-doing gap)
**Rough Effort**: MEDIUM (6-8 weeks)

1. **Router analytics dashboard**: Visualize routing decisions, cost savings, success rates
2. **User-defined routing policies**: Let users override router for specific query patterns
3. **Multi-model ensemble**: Route to multiple models, combine answers
4. **Latency-aware routing**: Factor in response time, not just cost/quality
5. **Provider health monitoring**: Auto-failover if provider is slow/down

---

## Promoted to Plan (B) Breakthrough Tier

**Selected**: Idea 1 (Hierarchical Cascade) + Idea 2 (Provider-Aware Routing)

**Rationale**:
- Idea 1: Highest cost savings (85-90%), integrates with memory (§4.2)
- Idea 2: Critical for multi-provider support (Lyra requirement), prevents capability mismatches
- Idea 3: Good but high complexity, defer to v2
- Idea 4: Useful but overlaps with Idea 1's confidence-based escalation

---

**END OF BRAINSTORM**
