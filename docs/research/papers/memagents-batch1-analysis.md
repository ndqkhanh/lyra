# MemAgents Workshop ICLR 2026 - Batch 1 Analysis

**Analysis Date:** May 26, 2026  
**Papers Analyzed:** 5 papers from MemAgents Workshop @ ICLR 2026  
**Analyst:** Lyra Research Team

---

## Executive Summary

This analysis examines five papers from the MemAgents workshop at ICLR 2026, focusing on memory architectures for LLM-based agents. The papers reveal converging trends toward:

1. **Hierarchical memory systems** with distinct short-term and long-term storage
2. **Dynamic memory organization** through graph-based linking and consolidation
3. **Cost-sensitive retrieval** balancing accuracy and efficiency
4. **Cross-domain memory transfer** for knowledge reuse across tasks
5. **Physical consistency** in memory-augmented world models

### Key Findings

- **Architecture transfers better than content** across domains (Paper 1)
- **Graph-based memory networks** with atomic notes outperform flat storage (Paper 2)
- **Selective store routing** improves both accuracy and efficiency (Paper 3)
- **KV-cache compression** enables memory-efficient reasoning at 75% reduction (Paper 5)
- **Consistency-driven repair** maintains physical coherence in world models (Paper 4)
- **Weaker models benefit more** from memory augmentation than stronger models (Paper 1)

---

## Paper 1: Memory Transplantation Protocol

**Title:** Memory Transplant Protocol for LLM Agents  
**ID:** AIJsjIqfsp  
**Pages:** 13

### Core Contribution

Introduces a **memory transplantation protocol** that separates architecture from content, enabling transfer of learned knowledge across:
- Different solver architectures (code-based vs math-based)
- Different content domains (code problems vs math problems)
- Static vs dynamic evaluation modes

### Memory Architecture

**Four-Phase Protocol:**

1. **Phase A: Build Stream & Memory Construction**
   - Solver LLM processes problems with memory operations enabled
   - Memory Provider system captures canonical items
   - Items stored in domain-specific canonical format

2. **Phase B: Memory Export/Import**
   - Export canonical items as JSONL
   - Architecture-agnostic serialization
   - Import reconstructs memory in target architecture

3. **Phase C: Transplant Conditions & Configuration**
   - Seven experimental conditions (NM, E_MATH, E_CODE, C_ONLY, FULL, IN_DOM, CROSS)
   - Tests architecture transfer, content transfer, and interaction effects

4. **Phase D: Evaluation & Grading**
   - Memory Provider injects context during evaluation
   - Measures transfer effectiveness via accuracy metrics

### Memory Systems Evaluated

**Five memory architectures tested:**

1. **NO_MEMORY:** Baseline with no retrieval
2. **SIMPLE_RAG:** Flat store (200 items max), FIFO pruning, lexical retrieval
3. **LIGHTWEIGHT_MEMORY:** Dual-tier (80 short-term + 160 long-term)
   - Retrieval frequency control (every 3 episodes)
   - Success-based routing: successful episodes → long-term, failed → short-term
   - 50/50 budget split during retrieval
4. **AGENT_KB:** Single store (220 items), two-stage retrieval
   - Broad retrieval (2× top-k) + reranking by success signal, type, recency
   - Optional disagreement gating to filter conflicting conclusions
5. **EXPEL:** Dual stores (140 insights + 140 trajectories)
   - 65% budget to insights, 35% to trajectories
   - Insight-distilled abstractions more transferable than traces

### Key Results

**Architecture Transfer (H1):**
- E_CODE (code arch, empty memory) → E_MATH (math arch, empty memory): **mixed results**
- AGENT_KB favors E_MATH at budget 400 (71.0% vs 66.3%)
- EXPEL favors E_CODE at budget 800 (68.0% vs 66.7%)
- **Finding:** Transfer is system-dependent and budget-sensitive, no universal direction

**Content Transfer (H2):**
- C_ONLY (math arch, code content, static) vs NM: **limited gains**
- EXPEL shows only notable static content transfer (70.0% at budget 800 vs 64.0% NM)
- **Finding:** Content transfer in static mode is limited; dynamic learning dominates

**Architecture × Content Interaction (H3):**
- FULL (code arch + code content) shows non-additive patterns
- EXPEL: C_ONLY 70.0% but FULL drops to 65.3% at budget 800
- **Finding:** Code architecture hurts when combined with code content (for math tasks)

**Solver Capability Moderates Transfer (Section 7.1):**
- Stronger solver (Qwen 2.5 7B): 64% baseline → 71% best (AGENT_KB E_MATH)
- Weaker solver (Llama 3.2 3B): 37% baseline → 52% best (EXPEL E_MATH)
- **Finding:** Memory provides larger absolute gains for weaker models

**Dynamic vs Static Mode:**
- Dynamic conditions (E_MATH, E_CODE) produce highest individual accuracies
- Static conditions isolate imported-content effects
- AGENT_KB peaks in dynamic mode (E_MATH 71.0%)
- EXPEL shows strongest static content transfer (C_ONLY 70.0%)

### Memory Management Techniques

**Canonical Export/Import:**
- Items serialized as JSONL with one `canonicalMemoryItem` per line
- JSON schema validation before import
- Architecture-dependent structures (embeddings, tier placements, graph edges) recomputed on import
- Ensures no prompt leakage or domain adaptation during transfer

**Retrieval Strategies:**
- **SIMPLE_RAG:** Lexical term-overlap retrieval
- **LIGHTWEIGHT_MEMORY:** Frequency control + success-based tier routing
- **AGENT_KB:** Two-stage (broad retrieval → reranking by composite score)
- **EXPEL:** Budget allocation (65% insights, 35% trajectories)

**Negative Controls (Section 4.5):**
1. **Random retrieval:** Replaces real items with random items (matched count/budget)
2. **Placebo context:** Neutral filler text at matched token count
3. **Write-only:** TAKE-IN/MANAGE enabled, PROVIDE returns empty
4. **Frozen-store marginal utility:** Identical store snapshot, PROVIDE on vs off

### Novel Insights

1. **Memory as capability augmentation:** Weaker models benefit more from memory (3B solver: ~15pp gain vs 7B solver: ~7pp gain)
2. **Negative transfer is real:** Several conditions perform below no-memory baseline in static mode
3. **Budget effects are non-monotonic:** Increasing retrieval budget 400→800 helps some systems, hurts others
4. **Architecture-over-content advantage:** For stronger solvers, high-quality distilled content (EXPEL C_ONLY 70.0%) can match or exceed dynamic learning

---

## Paper 2: A-MEM - Agentic Memory with Atomic Notes

**Title:** A-MEM: Agentic Memory for LLM Agents  
**ID:** FiM0M8gcct  
**Pages:** 20

### Core Contribution

Introduces **A-MEM**, an agentic memory system with:
- **Atomic note construction** (structured analysis of content)
- **Dynamic link generation** (graph-based memory network)
- **Memory evolution** (strengthen, merge, prune connections)
- **Top-k retrieval** with selective memory updates

### Memory Architecture

**Three-Phase Pipeline:**

1. **Phase 1: Note Construction (P₁)**
   - Structured analysis of incoming content
   - Extracts: keywords (3+ distinct terms), context (one-sentence summary), tags (3+ categorical)
   - Format: JSON object with keywords, context, tags
   - Creates atomic, self-contained memory units

2. **Phase 2: Link Generation (P₂)**
   - Analyzes new note with k nearest neighbors
   - Determines relationships based on keywords and context
   - Builds graph edges between related memories
   - Enables associative retrieval

3. **Phase 3: Memory Evolution (P₃)**
   - Evaluates connections: strengthen, merge, prune, or update neighbors
   - Actions: `["strengthen", "merge", "prune"]`
   - Updates tags and context based on understanding
   - Maintains memory network health

**Retrieval Mechanism:**
- Top-k retrieval based on semantic similarity
- Returns k nearest neighbors for each query
- Neighbors inform link generation and evolution decisions

### Key Results

**Performance on LoCoMo Dataset (QA tasks across 5 categories):**

**ROUGE-2 Scores (Multi-Hop, best performing category):**
- LoCoMo (no memory): 2.64
- ReadAgent: 2.47
- MemoryBank: 1.18
- MemGPT: 1.88
- **A-MEM: 18.61** (7× improvement over LoCoMo)

**ROUGE-L Scores (Multi-Hop):**
- LoCoMo: 23.92
- **A-MEM: 25.86** (consistent improvement)

**F1 Scores (Multi-Hop):**
- LoCoMo: 8.58
- MemGPT: 8.28
- **A-MEM: 15.02** (75% improvement)

**Across all categories (Multi-Hop, Temporal, Open Domain, Single Hop, Adversarial):**
- A-MEM achieves best or near-best performance in 4 of 5 categories
- Particularly strong in Multi-Hop (complex reasoning) tasks
- Demonstrates 6-fold improvement over LoCoMo in Multi-Hop ROUGE-L (27.23 vs 4.68)

### Memory Management Techniques

**Note Construction:**
- Identifies salient keywords (nouns, verbs, key concepts)
- Extracts core themes and contextual elements
- Creates categorical tags for classification
- Minimum 3 keywords, 1 context sentence, 3 tags

**Link Generation:**
- Retrieves k nearest neighbors for new note
- Analyzes relationships based on keywords and context
- Determines if memory should be evolved
- Considers relationships with other memories

**Memory Evolution:**
- **Strengthen:** Increase connection weight between related memories
- **Merge:** Combine redundant or highly related memories
- **Prune:** Remove weak or outdated connections
- **Update neighbors:** Modify tags and context based on new understanding

**Retrieval Strategy:**
- Top-k retrieval mechanism
- Varies k by task category and model (k=10 to k=50)
- Higher k for complex tasks (Multi-Hop: k=40-50)
- Lower k for simpler tasks (Single Hop: k=40)

### Novel Insights

1. **Interconnected memory networks:** Graph-based linking creates more effective memory structures than flat storage
2. **Atomic notes outperform full documents:** Structured analysis into atomic units improves retrieval precision
3. **Dynamic evolution maintains quality:** Active memory management prevents degradation over time
4. **Computational efficiency:** Only 1,200-2,500 tokens per query (vs 16,900 for MemGPT)
5. **Multi-Hop reasoning benefits most:** Complex tasks show largest gains from structured memory

// __CONTINUE_HERE__