# Lyra Super-Intelligent Self-Managed Memory System: Ultra Plan

**Research Date:** May 21, 2026  
**Objective:** Transform Lyra's memory system from basic storage to a cognitive architecture with autonomous memory management

---

## Executive Summary

The fundamental problem in AI agent memory is **not storage capacity** — it's **knowing what to remember and what to forget**. Current AI agents (including most production systems) lack:

1. **Memory importance scoring** - No mechanism to distinguish critical facts from noise
2. **Autonomous consolidation** - No sleep-like offline processing to compress and abstract memories
3. **Decay functions** - No forgetting curves; memories either exist forever or are deleted
4. **Retrieval-dependent learning** - No strengthening of memories through use
5. **Cross-session abstraction** - No ability to discover patterns across multiple sessions

This plan synthesizes cutting-edge research from 2025-2026 to build a **cognitive architecture** for Lyra that solves these problems.

---

## Part 1: Core Research Findings

### 1.1 The Memory Management Problem

**Current State (Most AI Agents):**
- Context window fills → oldest memories dropped (FIFO)
- No distinction between "user prefers dark mode" vs "user said hello"
- Every session starts from zero knowledge
- No learning from past mistakes
- No memory evolution or abstraction

**What Humans Do:**
- Encode memories with emotional/importance tags
- Consolidate during sleep (hippocampal replay)
- Forget irrelevant details, retain patterns
- Strengthen memories through retrieval
- Abstract specific episodes into general knowledge

### 1.2 Key Research Breakthroughs (2025-2026)

#### **Auto-Dreamer (May 2026)** - Offline Memory Consolidation
- **Paper:** arXiv:2605.20616
- **Key Innovation:** Decouples fast online acquisition from slow offline consolidation
- **Method:** 
  - Agent accumulates raw episodic memories during sessions
  - Offline "sleep" phase: consolidator reads memory regions, inspects trajectories, synthesizes compressed replacements
  - Trained via GRPO (Group Relative Policy Optimization) using end-task performance as reward
- **Results:** Outperforms fixed heuristics and prompt-based consolidation on ScienceWorld, WebShop, ALFWorld

#### **MAGMA (Jan 2026)** - Multi-Graph Memory Architecture
- **Paper:** arXiv:2601.03236
- **Key Innovation:** Represents each memory across 4 orthogonal graphs
  1. **Semantic graph** - concept relationships
  2. **Temporal graph** - time-ordered events
  3. **Causal graph** - cause-effect chains
  4. **Entity graph** - who/what/where connections
- **Retrieval:** Policy-guided traversal (query-adaptive graph selection)
- **Results:** Beats monolithic vector stores on LoCoMo and LongMemEval benchmarks

#### **ACT-R Cognitive Architecture** - Memory Activation Model
- **Source:** Carnegie Mellon, 40+ years of research
- **Key Innovation:** Base-level activation equation
  ```
  Activation = ln(Σ t_i^(-d)) + noise
  where t_i = time since i-th retrieval, d = decay parameter
  ```
- **Principles:**
  - Memories decay over time (power law)
  - Retrieval strengthens activation
  - Spreading activation from related concepts
  - Retrieval threshold determines accessibility

#### **Sleep-Inspired Consolidation** - Multiple Sources
- **Hippocampal replay:** Reactivate memory sequences offline to strengthen/reorganize
- **Defrag.md approach:** Light consolidation (merge duplicates) vs deep consolidation (pattern extraction, restructuring)
- **Benefits:**
  - Discover cross-session patterns
  - Resolve contradictions
  - Compress verbose memories
  - Archive stale information

#### **Cognitive Memory Tiers** (Cowan's Model)
1. **Sensory memory** - Raw input buffer (seconds)
2. **Working memory** - Active processing (4±1 items, ~30 seconds)
3. **Long-term memory** - Persistent storage (unlimited, but retrieval-gated)

### 1.3 Production Benchmarks (2026 Standards)

**LoCoMo Benchmark** (1,540 questions)
- Single-hop recall
- Multi-hop reasoning
- Open-domain queries
- Temporal reasoning

**LongMemEval** (500 questions)
- Single-session recall
- Multi-session recall
- Knowledge updates
- Contradiction handling

**BEAM** (1M-10M token scale)
- Accuracy at scale
- Token efficiency
- Latency under load

**State-of-the-art (Mem0, April 2026):**
- LoCoMo: 92.5
- LongMemEval: 94.4
- ~6,900 tokens per query
- +29.6 points on temporal reasoning vs baseline

---

## Part 2: Lyra's Current Memory System Analysis

### 2.1 What Lyra Has Now
*(Based on typical AI agent memory patterns)*

**Likely Architecture:**
- Vector database (embeddings for semantic search)
- Session-scoped conversation history
- Possibly: user preferences store
- Possibly: tool usage logs

**Limitations:**
1. **No importance scoring** - All memories treated equally
2. **No decay** - Memories persist forever or are manually deleted
3. **No consolidation** - Raw memories accumulate without abstraction
4. **No retrieval strengthening** - Accessing a memory doesn't make it more accessible
5. **No cross-session learning** - Each session is isolated
6. **No contradiction resolution** - Conflicting memories coexist
7. **No memory budget management** - No autonomous pruning when storage fills

### 2.2 Critical Gap: The "What to Remember" Problem

**Scenario:** User has 100 interactions with Lyra over a week.

**Current behavior:**
- All 100 interactions stored equally
- Retrieval returns semantically similar memories (may not be important ones)
- No distinction between:
  - "User's name is Alice" (critical, permanent)
  - "User asked about weather on Tuesday" (ephemeral, low value)
  - "User prefers TypeScript over JavaScript" (important, long-term)
  - "User said 'thanks'" (noise, should be forgotten)

**Desired behavior:**
- Automatic importance scoring on write
- Decay of low-importance memories
- Consolidation of repeated patterns into abstractions
- Strengthening of frequently-accessed memories
- Autonomous pruning when storage budget exceeded

---

## Part 3: The Ultra Plan - Cognitive Memory Architecture for Lyra

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LYRA COGNITIVE MEMORY                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Sensory    │→ │   Working    │→ │  Long-Term   │       │
│  │  Buffer     │  │   Memory     │  │   Memory     │       │
│  │  (raw I/O)  │  │  (active)    │  │  (persistent)│       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│                           ↓                  ↓               │
│                    ┌──────────────────────────┐             │
│                    │  Consolidation Engine    │             │
│                    │  (offline processing)    │             │
│                    └──────────────────────────┘             │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Multi-Graph Knowledge Store                │ │
│  │  • Semantic Graph    • Temporal Graph                  │ │
│  │  • Causal Graph      • Entity Graph                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Memory Management Subsystems                  │ │
│  │  • Importance Scorer  • Decay Manager                  │ │
│  │  • Retrieval Tracker  • Budget Controller              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Design

#### **Component 1: Importance Scoring System**

**Purpose:** Assign importance scores to memories at write time

**Scoring Dimensions:**
1. **Semantic importance** (0-1)
   - User preferences/settings: 0.9-1.0
   - Factual knowledge: 0.7-0.9
   - Task outcomes: 0.6-0.8
   - Casual conversation: 0.2-0.4
   - Greetings/acknowledgments: 0.0-0.2

2. **Emotional salience** (0-1)
   - User frustration/confusion: +0.3
   - User satisfaction: +0.2
   - Neutral: 0.0

3. **Recency** (time-decayed)
   - Recent memories get temporary boost
   - Decays according to power law

4. **Retrieval frequency** (cumulative)
   - Each retrieval adds +0.1 (capped at +0.5)
   - Implements "retrieval strengthens memory"

**Implementation:**
```python
def score_memory(content, context, metadata):
    # LLM-based semantic classification
    category = classify_memory_type(content)
    base_score = CATEGORY_SCORES[category]
    
    # Emotional detection
    emotion_boost = detect_emotional_salience(content, context)
    
    # Compute final importance
    importance = base_score + emotion_boost
    
    return {
        'importance': clip(importance, 0, 1),
        'category': category,
        'created_at': now(),
        'last_accessed': now(),
        'access_count': 0,
        'activation': compute_activation(importance)
    }
```

#### **Component 2: ACT-R Activation & Decay Manager**

**Purpose:** Implement human-like memory decay and retrieval strengthening

**ACT-R Base-Level Activation Formula:**
```
Activation(t) = ln(Σ t_i^(-d)) + β·Importance + ε
where:
  t_i = time since i-th retrieval
  d = decay rate (typically 0.5)
  β = importance weight
  ε = noise term
```

**Decay Behavior:**
- High-importance memories decay slower
- Each retrieval creates a new "spike" in activation
- Memories below threshold become inaccessible (soft delete)

**Implementation:**
```python
class MemoryActivationManager:
    def __init__(self, decay_rate=0.5, threshold=-1.0):
        self.decay_rate = decay_rate
        self.threshold = threshold
    
    def compute_activation(self, memory):
        """Compute current activation level"""
        now = time.time()
        
        # Sum over all retrieval times
        activation_sum = 0
        for retrieval_time in memory.retrieval_history:
            time_since = now - retrieval_time
            activation_sum += time_since ** (-self.decay_rate)
        
        # Base-level activation
        base_activation = math.log(activation_sum) if activation_sum > 0 else -10
        
        # Importance boost
        importance_boost = 2.0 * memory.importance
        
        # Final activation
        return base_activation + importance_boost
    
    def is_accessible(self, memory):
        """Check if memory is above retrieval threshold"""
        return self.compute_activation(memory) > self.threshold
    
    def on_retrieval(self, memory):
        """Update memory when retrieved"""
        memory.retrieval_history.append(time.time())
        memory.access_count += 1
        memory.last_accessed = time.time()
```

**Decay Schedule:**
- Run every 6 hours
- Compute activation for all memories
- Mark memories below threshold as "dormant"
- Archive dormant memories after 30 days

#### **Component 3: Multi-Graph Knowledge Store (MAGMA-inspired)**

**Purpose:** Represent memories across multiple relational dimensions

**Four Graph Types:**

1. **Semantic Graph**
   - Nodes: Concepts, entities, facts
   - Edges: IS-A, PART-OF, RELATED-TO
   - Example: "TypeScript" → IS-A → "Programming Language"

2. **Temporal Graph**
   - Nodes: Events, states
   - Edges: BEFORE, AFTER, DURING
   - Example: "Project started" → BEFORE → "First commit"

3. **Causal Graph**
   - Nodes: Actions, outcomes
   - Edges: CAUSES, ENABLES, PREVENTS
   - Example: "User reported bug" → CAUSES → "Fix deployed"

4. **Entity Graph**
   - Nodes: People, places, tools
   - Edges: USES, WORKS-WITH, LOCATED-AT
   - Example: "Alice" → USES → "VS Code"

**Retrieval Strategy:**
```python
def retrieve_memories(query, context):
    # Query-adaptive graph selection
    query_type = classify_query(query)
    
    if query_type == "temporal":
        # Traverse temporal graph
        results = temporal_graph.traverse(query, max_depth=3)
    elif query_type == "causal":
        # Traverse causal graph
        results = causal_graph.traverse(query, max_depth=2)
    elif query_type == "entity":
        # Traverse entity graph
        results = entity_graph.traverse(query, max_depth=2)
    else:
        # Default: semantic graph + vector search
        results = semantic_graph.traverse(query, max_depth=2)
        results += vector_search(query, top_k=10)
    
    # Rank by activation level
    results = [r for r in results if is_accessible(r)]
    results.sort(key=lambda r: compute_activation(r), reverse=True)
    
    return results[:20]
```

#### **Component 4: Offline Consolidation Engine (Auto-Dreamer-inspired)**

**Purpose:** Sleep-like memory processing to compress, abstract, and reorganize

**Consolidation Modes:**

1. **Light Consolidation** (runs every 6 hours)
   - Merge duplicate/similar memories
   - Resolve contradictions (keep most recent + high importance)
   - Update entity references
   - Recompute graph edges

2. **Deep Consolidation** (runs daily during low-activity periods)
   - Pattern extraction across sessions
   - Abstraction: specific episodes → general rules
   - Trajectory analysis: identify successful/failed patterns
   - Memory compression: verbose memories → concise summaries
   - Cross-session learning

**Implementation:**
```python
class ConsolidationEngine:
    def light_consolidation(self):
        """Fast cleanup and deduplication"""
        # Find duplicate memories
        duplicates = find_similar_memories(threshold=0.95)
        for group in duplicates:
            # Keep highest importance, merge metadata
            primary = max(group, key=lambda m: m.importance)
            for duplicate in group:
                if duplicate != primary:
                    primary.access_count += duplicate.access_count
                    primary.retrieval_history.extend(duplicate.retrieval_history)
                    archive_memory(duplicate)
        
        # Resolve contradictions
        contradictions = find_contradictory_memories()
        for pair in contradictions:
            # Keep most recent + high importance
            winner = max(pair, key=lambda m: (m.created_at, m.importance))
            loser = min(pair, key=lambda m: (m.created_at, m.importance))
            loser.status = "superseded"
            loser.superseded_by = winner.id
    
    def deep_consolidation(self):
        """Expensive pattern extraction and abstraction"""
        # Analyze recent sessions
        sessions = get_recent_sessions(days=7)
        
        # Extract patterns
        patterns = []
        for session_group in sliding_window(sessions, size=3):
            # Look for repeated sequences
            pattern = extract_common_pattern(session_group)
            if pattern and pattern.confidence > 0.7:
                patterns.append(pattern)
        
        # Create abstracted memories
        for pattern in patterns:
            abstract_memory = {
                'content': pattern.description,
                'type': 'abstraction',
                'importance': 0.8,
                'source_sessions': pattern.session_ids,
                'confidence': pattern.confidence
            }
            store_memory(abstract_memory)
        
        # Compress verbose memories
        verbose_memories = find_verbose_memories(min_length=500)
        for memory in verbose_memories:
            if memory.access_count < 2:  # Rarely accessed
                compressed = llm_summarize(memory.content)
                memory.content = compressed
                memory.original_content = archive_to_cold_storage(memory.content)
```

**Consolidation Triggers:**
- Scheduled (every 6 hours for light, daily for deep)
- On-demand when storage exceeds 80% capacity
- After significant events (user explicitly says "remember this")

#### **Component 5: Memory Budget Controller**

**Purpose:** Autonomous memory management when storage limits approached

**Budget Tiers:**
- **Tier 1 (Hot):** 0-70% capacity - Normal operation
- **Tier 2 (Warm):** 70-85% capacity - Light consolidation triggered
- **Tier 3 (Cold):** 85-95% capacity - Aggressive pruning
- **Tier 4 (Critical):** 95-100% capacity - Emergency archival

**Pruning Strategy:**
```python
def prune_memories(target_reduction_pct=20):
    """Remove low-value memories to free space"""
    
    # Compute pruning score for each memory
    memories = get_all_memories()
    for memory in memories:
        activation = compute_activation(memory)
        age_days = (now() - memory.created_at).days
        
        # Pruning score (lower = more likely to prune)
        prune_score = (
            activation * 0.5 +
            memory.importance * 0.3 +
            min(memory.access_count / 10, 1.0) * 0.2 -
            (age_days / 365) * 0.1  # Slight penalty for age
        )
        memory.prune_score = prune_score
    
    # Sort by prune score
    memories.sort(key=lambda m: m.prune_score)
    
    # Archive bottom N%
    num_to_prune = int(len(memories) * target_reduction_pct / 100)
    for memory in memories[:num_to_prune]:
        if memory.importance < 0.7:  # Never prune critical memories
            archive_memory(memory)
```

#### **Component 6: Three-Tier Memory System (Cowan's Model)**

**Purpose:** Separate memory by access patterns and lifecycle

**Tier 1: Sensory Buffer**
- Raw input/output from current session
- Capacity: Last 10 interactions
- Lifetime: Current session only
- Purpose: Immediate context for conversation

**Tier 2: Working Memory**
- Active memories for current task
- Capacity: 4-7 items (Cowan's limit)
- Lifetime: Current session + 1 hour
- Purpose: Task-relevant context

**Tier 3: Long-Term Memory**
- Persistent storage with activation-based retrieval
- Capacity: Unlimited (but activation-gated)
- Lifetime: Permanent (with decay)
- Purpose: Knowledge base

**Memory Flow:**
```
User Input → Sensory Buffer → [Importance Scoring] → 
  If important: Working Memory → Long-Term Memory
  If not: Discard after session
```

---

## Part 4: Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

**Week 1: Data Model & Storage**
- [ ] Design memory schema with activation fields
- [ ] Add importance, retrieval_history, access_count columns
- [ ] Implement memory versioning (for contradiction tracking)
- [ ] Set up graph database (Neo4j or similar)

**Week 2: Importance Scoring**
- [ ] Build LLM-based memory classifier
- [ ] Implement scoring function
- [ ] Add emotional salience detection
- [ ] Test on historical data

**Week 3: Activation & Decay**
- [ ] Implement ACT-R activation formula
- [ ] Build decay manager (background job)
- [ ] Add retrieval tracking
- [ ] Test decay curves on synthetic data

### Phase 2: Graph & Retrieval (Weeks 4-6)

**Week 4: Multi-Graph Construction**
- [ ] Build semantic graph from existing memories
- [ ] Extract temporal relationships
- [ ] Identify causal chains
- [ ] Create entity graph

**Week 5: Query-Adaptive Retrieval**
- [ ] Implement query classifier
- [ ] Build graph traversal algorithms
- [ ] Integrate activation-based ranking
- [ ] Benchmark against current retrieval

**Week 6: Retrieval Optimization**
- [ ] Add spreading activation
- [ ] Implement caching for hot memories
- [ ] Optimize graph queries
- [ ] A/B test retrieval quality

### Phase 3: Consolidation (Weeks 7-9)

**Week 7: Light Consolidation**
- [ ] Implement duplicate detection
- [ ] Build contradiction resolver
- [ ] Add scheduled consolidation job
- [ ] Test on production data

**Week 8: Deep Consolidation**
- [ ] Build pattern extraction pipeline
- [ ] Implement abstraction generator
- [ ] Add trajectory analysis
- [ ] Test cross-session learning

**Week 9: Consolidation Tuning**
- [ ] Optimize consolidation triggers
- [ ] Tune pattern confidence thresholds
- [ ] Add user feedback loop
- [ ] Measure consolidation impact

### Phase 4: Budget Management (Weeks 10-11)

**Week 10: Budget Controller**
- [ ] Implement storage monitoring
- [ ] Build pruning algorithm
- [ ] Add archival system
- [ ] Test emergency scenarios

**Week 11: Three-Tier System**
- [ ] Implement sensory buffer
- [ ] Build working memory manager
- [ ] Add tier promotion logic
- [ ] Benchmark memory flow

### Phase 5: Evaluation & Tuning (Weeks 12-14)

**Week 12: Benchmark Setup**
- [ ] Implement LoCoMo evaluation
- [ ] Add LongMemEval tests
- [ ] Create custom Lyra benchmarks
- [ ] Baseline current system

**Week 13: Optimization**
- [ ] Tune decay parameters
- [ ] Adjust importance weights
- [ ] Optimize consolidation frequency
- [ ] Improve retrieval ranking

**Week 14: Production Rollout**
- [ ] Gradual rollout (10% → 50% → 100%)
- [ ] Monitor memory quality metrics
- [ ] Collect user feedback
- [ ] Fix issues

---

## Part 5: Success Metrics & Evaluation

### 5.1 Quantitative Metrics

**Memory Quality:**
- **Recall accuracy:** % of correct answers on benchmark questions
  - Target: >90% on LoCoMo, >92% on LongMemEval
- **Precision:** % of retrieved memories that are relevant
  - Target: >85%
- **Temporal reasoning:** Accuracy on time-based queries
  - Target: +25 points vs baseline

**Efficiency:**
- **Token consumption:** Avg tokens per query
  - Target: <8,000 tokens (competitive with Mem0)
- **Retrieval latency:** Time to retrieve relevant memories
  - Target: <200ms for p95
- **Storage efficiency:** Compression ratio after consolidation
  - Target: 30-40% reduction in storage

**Autonomy:**
- **Pruning accuracy:** % of pruned memories that were truly low-value
  - Target: >95% (measured via user feedback)
- **Consolidation quality:** % of abstractions that are useful
  - Target: >80%
- **Contradiction resolution:** % of conflicts correctly resolved
  - Target: >90%

### 5.2 Qualitative Metrics

**User Experience:**
- "Lyra remembers what matters" - User survey score
  - Target: >4.5/5
- "Lyra forgets irrelevant details" - User survey score
  - Target: >4.0/5
- "Lyra learns from past interactions" - User survey score
  - Target: >4.3/5

**Agent Behavior:**
- Reduced repetition of questions
- Better personalization over time
- Improved task success rate
- Fewer "I don't remember" responses

### 5.3 Benchmark Comparison

**Target Performance (vs Current State-of-the-Art):**

| Metric | Current SOTA (Mem0) | Lyra Target | Improvement |
|--------|---------------------|-------------|-------------|
| LoCoMo Score | 92.5 | 94.0+ | +1.5 |
| LongMemEval | 94.4 | 95.5+ | +1.1 |
| Temporal Reasoning | Baseline +29.6 | Baseline +32 | +2.4 |
| Multi-hop Reasoning | Baseline +23.1 | Baseline +25 | +1.9 |
| Tokens/Query | ~6,900 | <7,500 | Competitive |
| Retrieval Latency | Not reported | <200ms p95 | - |

---

## Part 6: Advanced Features (Future Enhancements)

### 6.1 Reinforcement Learning for Consolidation

**Concept:** Train consolidation policy using task performance as reward
- **Method:** GRPO (Group Relative Policy Optimization) from Auto-Dreamer
- **Reward:** End-task success rate after consolidation
- **Training:** Offline on historical session data

### 6.2 Prospective Memory

**Concept:** Remember to do things in the future
- **Implementation:** Time-based triggers + context-based triggers
- **Example:** "Remind me to ask about project status next time user mentions deployment"

### 6.3 Episodic Memory Replay

**Concept:** Reactivate memory sequences to strengthen learning
- **Method:** Hippocampal replay during consolidation
- **Benefit:** Discover causal patterns, strengthen important sequences

### 6.4 Meta-Memory (Memory About Memory)

**Concept:** Track what Lyra knows vs doesn't know
- **Implementation:** Confidence scores on memories
- **Benefit:** "I'm not sure, but I think..." vs "I know for certain..."

### 6.5 Collaborative Memory

**Concept:** Share memories across Lyra instances (with user permission)
- **Implementation:** Federated learning + privacy-preserving aggregation
- **Benefit:** Learn from collective experience

### 6.6 Memory Explanation

**Concept:** Explain why Lyra remembers/forgets something
- **Implementation:** Activation trace + importance breakdown
- **Benefit:** User trust and transparency

---

## Part 7: Technical Stack Recommendations

### 7.1 Core Technologies

**Memory Storage:**
- **Vector DB:** Qdrant or Weaviate (for semantic search)
- **Graph DB:** Neo4j (for multi-graph relationships)
- **Time-series DB:** TimescaleDB (for activation history)
- **Cache:** Redis (for hot memories)

**Processing:**
- **Background Jobs:** Celery or Temporal (for consolidation)
- **LLM Calls:** OpenAI GPT-4 or Anthropic Claude (for classification/abstraction)
- **Embeddings:** OpenAI text-embedding-3-large or Cohere embed-v3

**Monitoring:**
- **Metrics:** Prometheus + Grafana
- **Logging:** ELK stack
- **Tracing:** Jaeger (for retrieval path analysis)

### 7.2 Architecture Pattern

```
┌─────────────────────────────────────────────────────────┐
│                    Lyra Application                      │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │   Memory Manager      │
         │   (Orchestrator)      │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼────┐    ┌─────▼─────┐    ┌────▼────┐
│ Write  │    │ Retrieval │    │ Consol. │
│ Path   │    │   Path    │    │ Engine  │
└───┬────┘    └─────┬─────┘    └────┬────┘
    │               │                │
    │         ┌─────▼─────┐          │
    │         │  Ranking  │          │
    │         │  Engine   │          │
    │         └─────┬─────┘          │
    │               │                │
┌───▼───────────────▼────────────────▼───┐
│         Storage Layer                   │
│  • Vector DB  • Graph DB  • Time-series│
└─────────────────────────────────────────┘
```

---

## Part 8: Key Research Papers & Resources

### 8.1 Must-Read Papers

1. **Auto-Dreamer: Autonomous Memory Consolidation**
   - arXiv:2605.20616 (May 2026)
   - Key contribution: Offline consolidation with GRPO training
   - Relevance: Core inspiration for consolidation engine

2. **MAGMA: Multi-Graph Memory Architecture**
   - arXiv:2601.03236 (Jan 2026)
   - Key contribution: Four orthogonal graph representations
   - Relevance: Multi-graph knowledge store design

3. **ACT-R: Adaptive Control of Thought—Rational**
   - Anderson et al., Carnegie Mellon (1993-present)
   - Key contribution: Base-level activation equation
   - Relevance: Decay and retrieval strengthening

4. **Cowan's Embedded Processes Model**
   - Cowan (2001), Behavioral and Brain Sciences
   - Key contribution: Working memory capacity limits
   - Relevance: Three-tier memory architecture

5. **Wixted's Hybrid Decay Theory**
   - Wixted (2004), Psychological Review
   - Key contribution: Power-law decay with retrieval strengthening
   - Relevance: Decay function design

### 8.2 Production Systems to Study

1. **Mem0** (mem0.ai)
   - State-of-the-art benchmarks (LoCoMo 92.5, LongMemEval 94.4)
   - Token-efficient retrieval (~6,900 tokens/query)
   - 21 framework integrations

2. **shodh-memory** (shodh-memory.com)
   - Cognitive architecture implementation
   - Hebbian learning + spreading activation
   - Local-first, privacy-focused

3. **MemGPT** (memgpt.ai)
   - Hierarchical memory management
   - OS-inspired memory paging
   - Context window optimization

### 8.3 Benchmarks

1. **LoCoMo** - 1,540 questions across 4 categories
   - Single-hop, multi-hop, open-domain, temporal
   - Standard for memory recall evaluation

2. **LongMemEval** - 500 questions across 6 categories
   - Single/multi-session recall, knowledge updates
   - Tests contradiction handling

3. **BEAM** - 1M-10M token scale evaluation
   - Accuracy, token efficiency, latency
   - Production-scale testing

---

## Part 9: Critical Success Factors

### 9.1 What Will Make This Work

1. **Accurate Importance Scoring**
   - This is the foundation - get this wrong and everything fails
   - Invest heavily in classification quality
   - Use human feedback to tune

2. **Conservative Decay Parameters**
   - Start with slow decay, tune based on user feedback
   - Better to keep too much than forget critical info
   - Monitor "I told you this before" complaints

3. **Transparent Consolidation**
   - Users should understand what's happening
   - Provide "memory report" showing what was consolidated
   - Allow manual override

4. **Gradual Rollout**
   - Don't replace entire memory system at once
   - A/B test each component
   - Measure impact before proceeding

5. **User Control**
   - "Pin" important memories (never decay)
   - "Forget this" command (immediate deletion)
   - Memory settings (aggressive vs conservative forgetting)

### 9.2 What Could Go Wrong

**Risk 1: Over-Aggressive Forgetting**
- Symptom: Users complain "Lyra forgot important things"
- Mitigation: Conservative decay, importance boost for user-flagged memories
- Monitoring: Track "I told you this" frequency

**Risk 2: Poor Abstraction Quality**
- Symptom: Consolidated memories lose critical details
- Mitigation: Keep original memories in archive, allow rollback
- Monitoring: User feedback on abstraction usefulness

**Risk 3: Computational Cost**
- Symptom: Consolidation takes too long, impacts performance
- Mitigation: Optimize graph queries, use incremental consolidation
- Monitoring: Consolidation job duration, resource usage

**Risk 4: Contradiction Mishandling**
- Symptom: Wrong memory kept when resolving conflicts
- Mitigation: Use recency + importance + user feedback
- Monitoring: Track contradiction resolution accuracy

**Risk 5: Cold Start Problem**
- Symptom: New users have poor experience (no memories yet)
- Mitigation: Aggressive importance scoring early, slower decay initially
- Monitoring: New user retention, satisfaction scores

---

## Part 10: Next Steps

### Immediate Actions (This Week)

1. **Audit Current Memory System**
   - Document existing architecture
   - Measure baseline metrics (recall, precision, latency)
   - Identify quick wins

2. **Set Up Benchmarks**
   - Implement LoCoMo evaluation framework
   - Create Lyra-specific test cases
   - Establish baseline scores

3. **Prototype Importance Scorer**
   - Build simple LLM-based classifier
   - Test on 100 historical memories
   - Measure classification accuracy

4. **Design Data Schema**
   - Add activation fields to memory table
   - Plan graph database structure
   - Design migration path

### First Month Goals

- [ ] Complete Phase 1 (Foundation)
- [ ] Baseline benchmarks established
- [ ] Importance scoring at 80%+ accuracy
- [ ] Decay manager running in test environment
- [ ] Initial A/B test plan approved

### Three Month Goals

- [ ] Phases 1-3 complete (Foundation, Graph, Consolidation)
- [ ] LoCoMo score >85 (vs baseline)
- [ ] Light consolidation running in production
- [ ] User feedback system operational
- [ ] 10% production rollout

### Six Month Goals

- [ ] All phases complete
- [ ] LoCoMo >90, LongMemEval >92
- [ ] Full production rollout
- [ ] User satisfaction >4.3/5
- [ ] Published case study/blog post

---

## Conclusion

The key insight from 2025-2026 research is clear: **AI agents need cognitive architectures, not just bigger context windows.**

Lyra's path to super-intelligent memory requires:

1. **Autonomous importance scoring** - Know what matters
2. **ACT-R-inspired decay** - Forget like humans do
3. **Multi-graph knowledge** - Represent relationships richly
4. **Offline consolidation** - Learn while "sleeping"
5. **Budget management** - Prune intelligently when needed

This isn't just about storage - it's about **building a system that learns what to remember and what to forget**, just like human memory does.

The research is mature. The benchmarks exist. The path is clear.

Time to build.

---

## Appendix: Quick Reference

### Key Formulas

**ACT-R Activation:**
```
A(t) = ln(Σ t_i^(-d)) + β·I + ε
```

**Importance Score:**
```
I = base_category_score + emotional_salience + user_flag_boost
```

**Pruning Score:**
```
P = 0.5·A + 0.3·I + 0.2·min(access_count/10, 1) - 0.1·(age/365)
```

### Default Parameters

- Decay rate (d): 0.5
- Retrieval threshold: -1.0
- Importance weight (β): 2.0
- Light consolidation: Every 6 hours
- Deep consolidation: Daily at 3 AM
- Pruning trigger: 85% storage capacity
- Working memory capacity: 4-7 items

### Contact & Resources

- **Research papers:** See Part 8.1
- **Benchmarks:** LoCoMo, LongMemEval, BEAM
- **Production systems:** Mem0, shodh-memory, MemGPT
- **This document:** Living document, update as research evolves

**Last Updated:** May 21, 2026
