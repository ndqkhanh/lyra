# Memory Mechanisms Deep-Read

Extracted from three papers:
1. **A-MEM: Agentic Memory for LLM Agents** -- Xu et al., arXiv 2502.12110v1 (NeurIPS 2025)
2. **A-MEM: Agentic Memory for LLM Agents** -- Xu et al., NeurIPS 2025 Workshop version (OpenReview FiM0M8gcct)
3. **Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers** -- Du, arXiv 2603.07670 (March 2026)

---

## PAPER 1: A-MEM (arXiv 2502.12110v1)

### FULL Algorithm (Pseudocode + Data Structures)

The system implements a Zettelkasten-inspired agentic memory with four stages.

#### Stage 1: Note Construction

Each memory note `mi` in collection `M = {m1, m2, ..., mN}`:

```
mi = {ci, ti, Ki, Gi, Xi, ei, Li}
```
- `ci` = original interaction content (raw text)
- `ti` = timestamp of the interaction
- `Ki` = LLM-generated keywords (captures key concepts)
- `Gi` = LLM-generated tags (categorization)
- `Xi` = LLM-generated contextual description (one-sentence summary)
- `ei` = dense vector embedding (all-minilm-l6-v2)
- `Li` = set of linked memories sharing semantic relationships

Construction prompt `Ps1`:
```
Ki, Gi, Xi <- LLM(ci || ti || Ps1)
```

Embedding computation:
```
ei = fenc[ concat(ci, Ki, Gi, Xi) ]
```

#### Stage 2: Link Generation

When new memory `mn` is added:

Cosine similarity to all existing memories:
```
sn,j = (en * ej) / (|en| * |ej|)
```

Top-k selection:
```
M_near = {mj | rank(sn,j) <= k, mj in M}
```

LLM-driven link analysis (prompt `Ps2`):
```
Li <- LLM(mn || M_near || Ps2)
```

Each generated link `li` is structured as `Li = {mi, ..., mk}`. Embedding-based retrieval acts as an efficient pre-filter; the LLM then performs nuanced analysis of relationships (causal, conceptual, etc.) beyond pure similarity.

#### Stage 3: Memory Evolution

For each memory `mj` in `M_near`, the system determines whether to update its context, keywords, and tags:

```
m*j <- LLM(mn || M_near \ mj || mj || Ps3)
```

The evolved `m*j` replaces `mj` in `M`. Actions supported: `strengthen` (reinforce connection), `merge`, `prune`, `update_neighbor` (update tags/context). Returns JSON:
```json
{
  "should_evolve": true/false,
  "actions": ["strengthen", "merge", "prune"],
  "suggested_connections": ["neighbor_memory_ids"],
  "tags_to_update": ["tag_1", ...],
  "new_context_neighborhood": ["new context", ...],
  "new_tags_neighborhood": [["tag_1","tag_n"], ...]
}
```

#### Stage 4: Memory Retrieval

Query embedding:
```
eq = fenc(q)
```

Cosine similarity:
```
sq,i = (eq * ei) / (|eq| * |ei|), where ei in mi, for all mi in M
```

Top-k retrieval:
```
M_retrieved = {mi | rank(sq,i) <= k, mi in M}
```

### Real Benchmark Numbers

**Dataset**: LoCoMo -- 7,512 QA pairs, 5 categories, up to 35 sessions, 9K avg tokens per conversation.

**Default k=10** (adjusted per category/model).

| Model | Method | Multi-Hop F1 | Multi-Hop BLEU-1 | Token Length |
|-------|--------|-------------|-----------------|-------------|
| GPT-4o-mini | LoCoMo | 18.41 | 14.77 | 16,910 |
| | ReadAgent | 12.60 | 8.87 | 643 |
| | MemoryBank | 9.68 | 6.99 | 432 |
| | MemGPT | 25.52 | 19.44 | 16,977 |
| | **A-MEM** | **45.85** | **36.67** | **2,520** |
| GPT-4o | LoCoMo | 9.09 | 5.78 | 16,910 |
| | **A-MEM** | **39.41** | **31.23** | **1,216** |
| Qwen2.5-1.5B | LoCoMo | 4.25 | 4.04 | 16,910 |
| | **A-MEM** | **24.32** | **19.74** | **1,300** |
| Qwen2.5-3B | LoCoMo | 3.11 | 2.71 | 16,910 |
| | **A-MEM** | **27.59** | **25.07** | **1,137** |
| Llama3.2-1B | LoCoMo | 7.38 | 6.82 | 16,910 |
| | **A-MEM** | **17.80** | **10.28** | **1,376** |
| Llama3.2-3B | LoCoMo | 4.37 | 4.40 | 16,910 |
| | **A-MEM** | **26.38** | **19.50** | **1,126** |

**Key pattern**: A-MEM achieves 2x-6x improvement on Multi-Hop tasks vs strongest baseline, while using 85-93% fewer tokens (1,200-2,500 vs 16,900 for LoCoMo/MemGPT).

#### Ablation Study (GPT-4o-mini)

| Method | Multi-Hop F1 | Temporal F1 | Open Domain F1 | Single Hop F1 | Adversarial F1 |
|--------|-------------|------------|---------------|--------------|---------------|
| w/o LG & ME | 9.65 | 24.55 | 7.77 | 13.28 | 15.32 |
| w/o ME (LG only) | 21.35 | 31.24 | 10.13 | 39.17 | 44.16 |
| **Full A-MEM** | **27.02** | **45.85** | **12.14** | **44.65** | **50.03** |

Link Generation provides the foundation; Memory Evolution adds refinement. Both together near-double Multi-Hop performance.

#### Hyperparameter Analysis (k values)

Peak k per category (GPT-4o-mini): Single Hop=40, Multi Hop=40, Temporal=50, Open Domain=50, Adversarial=40. Increasing k beyond 30-40 plateaus or degrades due to noise.

### Trade-off Analysis

| Dimension | Finding |
|-----------|---------|
| **Latency** | ~5.4s for GPT-4o-mini; ~1.1s for Llama 3.2 1B local. Multiple LLM calls per memory write (note construction + link generation + evolution) add latency vs simpler baselines. |
| **Memory overhead** | O(N) space complexity -- same as vector-only stores (MemoryBank, ReadAgent). 1,000 entries = 1.46 MB; 1M entries = 1,464.84 MB. No additional storage overhead vs baselines. |
| **Retrieval time** | Sub-microsecond at 1K (0.31us), 3.70us at 1M. Slower than MemoryBank (1.91us at 1M) but orders of magnitude faster than ReadAgent (120ms at 1M). |
| **Token cost** | 85-93% reduction vs LoCoMo/MemGPT. ~$0.0003 per memory operation with commercial APIs. |
| **Accuracy impact** | Multi-Hop tasks see 2-6x improvement. Diminishing returns beyond k=30-40. |

### Design Rationale

Why Zettelkasten over alternatives:
- **vs fixed graph databases** (Mem0): Predefined schemas cannot forge innovative connections; Zettelkasten allows organic emergence of links.
- **vs agentic RAG**: Agentic RAG has agency only at retrieval time (when/what to retrieve). A-MEM has agency at the storage/organization/evolution level, which is more fundamental.
- **vs MemGPT priority caching**: MemGPT prioritizes recency; A-MEM prioritizes semantic structure via links and tags.
- **vs MemoryBank forgetting curves**: Forgetting curves discard information mechanically; A-MEM evolves and retains.

### Failure Modes and Limitations (Authors Acknowledged)

1. **LLM quality dependency**: Quality of generated keywords, tags, and contextual descriptions depends on the underlying LLM. Different LLMs produce different organizational structures.
2. **Text-only**: Currently limited to text-based interactions. No image, audio, or multimodal support.
3. **No error bars**: Experiments used LLM APIs; multiple runs would significantly increase costs.
4. **LoCoMo-only evaluation**: No assessment on diverse agentic benchmarks (addressed partially in the NeurIPS workshop version with DialSim).
5. **Limited agentic evaluation**: Benchmark is QA on conversations, not end-to-end agent task completion.

---

## PAPER 2: A-MEM (NeurIPS 2025 Workshop / OpenReview)

### Additional Content vs arXiv Version

#### DialSim Dataset Results

DialSim: 1,300 sessions, ~350K tokens, from TV shows (Friends, Big Bang Theory, Office). Multi-party dialogue QA.

| Method | F1 | BLEU-1 | ROUGE-L | ROUGE-2 | METEOR | SBERT |
|--------|------|--------|---------|---------|--------|-------|
| LoCoMo | 2.55 | 3.13 | 2.75 | 0.90 | 1.64 | 15.76 |
| MemGPT | 1.18 | 1.07 | 0.96 | 0.42 | 0.95 | 8.54 |
| **A-MEM** | **3.45** | **3.37** | **3.54** | **3.60** | **2.05** | **19.51** |

A-MEM: 35% improvement over LoCoMo, 192% over MemGPT.

#### Additional Foundation Models

| Model | Method | Multi-Hop F1 | Multi-Hop BLEU-1 |
|-------|--------|-------------|-----------------|
| DeepSeek-R1-32B | LoCoMo | 8.58 | 6.48 |
| | MemGPT | 8.28 | 6.25 |
| | **A-MEM** | **15.02** | **10.64** |
| Claude 3.0 Haiku | LoCoMo | 4.56 | 3.33 |
| | **A-MEM** | **19.28** | **14.69** |
| Claude 3.5 Haiku | LoCoMo | 11.34 | 8.21 |
| | **A-MEM** | **29.70** | **23.19** |

#### Scaling Analysis Detail

| Memory Size | A-MEM Memory (MB) | A-MEM Retrieval Time (us) |
|-------------|-------------------|--------------------------|
| 1,000 | 1.46 | 0.31 ± 0.30 |
| 10,000 | 14.65 | 0.38 ± 0.25 |
| 100,000 | 146.48 | 1.40 ± 0.49 |
| 1,000,000 | 1464.84 | 3.70 ± 0.74 |

Comparable to MemoryBank. ReadAgent degrades catastrophically (120ms at 1M).

---

## PAPER 3: Memory Survey (arXiv 2603.07670)

### Formalization: The Write-Manage-Read Loop

The agent loop formalized as a POMDP:

```
at = pi_theta(xt, R(Mt, xt), gt)          # Action = f(input, read(memory), goals)
Mt+1 = U(Mt, xt, at, ot, rt)               # Memory update = f(old memory, input, action, obs, reward)
```

`U` is NOT a simple append: it summarizes, deduplicates, scores priority, resolves contradictions, and deletes. This forms a feedback loop: agent decisions determine writes; writes shape future decisions.

### Three-Axis Taxonomy

**Axis 1: Temporal Scope**
- Working memory: current context window (the LLM is executive, context is buffer -- Baddeley's model)
- Episodic memory: concrete timestamped experiences
- Semantic memory: abstracted de-contextualized knowledge
- Procedural memory: reusable skills, executable plans

**Axis 2: Representational Substrate**
- Context-resident text: summaries, scratchpads, CoT traces -- zero infra, finite capacity
- Vector-indexed stores: dense embeddings, ANN search -- scales to millions, no structured relations
- Structured stores: SQL, K-V, knowledge graphs -- complex queries, schema required
- Executable repositories: code libraries, tool defs, plan templates -- sidesteps regeneration
- Hybrid stores: MemGPT tiers context window + recall DB + vector archive

**Axis 3: Control Policy**
- Heuristic: hard-coded rules (top-k, summarize every n turns, expire after d days) -- predictable, context-blind
- Prompted self-control: memory as tool calls, LLM decides when -- quality depends on instruction-following
- Learned control: RL-optimized policy for store/retrieve/update/summarize/discard -- expensive training, discovers non-obvious strategies (preemptive summarization)

### Five Mechanism Families

#### 1. Context-Resident Compression
Strategies: sliding windows, rolling summaries, hierarchical summaries, task-conditioned compression.
**Key pathology**: summarization drift -- rare but critical facts vanish after multiple compression passes.
**Example**: 50 interactions/day x 7 days = 350 turns compressed through 3+ cycles. A critical "never call prod DB directly" instruction is exactly the kind of low-frequency, high-importance detail that disappears.
**Extended context (100k+) delays but doesn't solve** the problem and adds quadratic attention cost.
**Another pathology**: attentional dilution -- "lost in the middle" phenomenon where center-placed info is recalled less reliably.

#### 2. Retrieval-Augmented Memory Stores
Evolution from static document retrieval to agent-specific stores (tool logs, env observations, reflections).
Key design decisions:
- **Indexing granularity**: fine-grained (individual calls) vs coarse-grained (full sessions) -- practical sweet spot is multi-granularity
- **Query formulation**: raw user input is often a poor query; strategies include LLM-reformulation, multi-query fan-out, subgoal-as-query
- **Scale**: RETRO-style trillion-token stores suggest years of history feasible; bottleneck shifts from storage to relevance
- **Read-write memory**: RET-LLM bridges retrieval and structured storage -- schema at write time, flexibility at read time

#### 3. Reflective Self-Improvement
**Reflexion**: 91% pass@1 on HumanEval vs 80% GPT-4 baseline without reflection. Verbal self-critiques prepended to next attempt -- no gradient updates.
**Generative Agents**: richer pipeline -- observations -> episodic stream -> clustering -> higher-order reflections. Weighted scoring: recency (exponential decay) + relevance (embedding similarity) + importance (self-assessed integer).
**ExpeL**: systematically contrasts successful vs failed trajectories, extracts discriminative "rules of thumb."
**Think-in-Memory**: separates retrieval from reasoning -- recall first, then dedicated thinking step.

**Central risk**: self-reinforcing error. Incorrect conclusion "API X always fails" persists forever, preventing counter-evidence collection. **Over-generalization** sibling risk. Quality gates (confidence scores, contradiction checking, periodic expiration) are necessary but underdeveloped.

#### 4. Hierarchical Virtual Context
**MemGPT** borrows OS virtual memory:
- Main context (RAM): active window with system prompt, recent messages, relevant records
- Recall storage (disk): searchable DB of all past messages
- Archival storage (cold): vector-indexed store for documents/knowledge

Agent moves data between tiers via function calls (`archival_memory_search`, `core_memory_append`). Interrupt mechanism passes control on each user message or timer event.
**JARVIS-1**: extends to multimodal (visual obs, textual plans, executable skills).

**Achilles' heel**: orchestration -- paging the wrong data wastes context; over-archiving creates "memory blindness." Failures are **silent** (no exception, no log entry, just a worse response). Compounds over time.

#### 5. Policy-Learned Management
**Agentic Memory (AgeMem)**: 5 operations (store, retrieve, update, summarize, discard) as callable tools within the agent's policy, optimized via three-stage RL:
1. Supervised warm-up on memory demonstrations
2. Task-level RL with outcome rewards
3. Step-level GRPO for denser credit assignment

Learned policies discover non-obvious tactics: proactive summarization before context fills, selective discarding of records that add no new info vs existing entries.
**Open concerns**: expensive training, could delete safety-critical info, poor transfer across task distributions, interpretability lags behind capability.

### Evaluation Landscape

#### Key Benchmarks

| Benchmark | Year | Multi-session | Agentic | Key Finding |
|-----------|------|--------------|---------|-------------|
| LoCoMo | 2024 | Yes | No | Humans far ahead; even RAG-augmented LLMs lag on temporal/causal dynamics |
| MemBench | 2025 | No | No | Factual vs reflective; 3 dimensions: accuracy, efficiency, capacity |
| MemoryAgentBench | 2025 | No | No | No system masters all 4 competencies (accurate retrieval, test-time learning, long-range understanding, selective forgetting); most fail on forgetting |
| MemoryArena | 2026 | Yes | Yes | LoCoMo-saturated models drop to 40-60%; active memory agent 80% vs long-context-only 45% |

#### Cross-cutting lessons from benchmarks:
1. **Long context is NOT memory**: 200k-window models underperform purpose-built memory on selective retrieval
2. **RAG helps, gap to humans is wide**: bottleneck is retrieval quality, not storage
3. **Nobody evaluates forgetting well**: only MemoryAgentBench tests selective forgetting; inability to discard poisons retrieval precision
4. **Cross-session coherence is underexplored**: MemoryArena reveals maintaining knowledge across hours/days is a distinct unsolved challenge
5. **Parametric vs non-parametric gap**: different failure profiles -- parametric excels at integration but fails at deletion/audit; non-parametric supports inspection but feels "bolted on"
6. **Evaluation must include cost**: no benchmark systematically reports efficiency alongside effectiveness

### Applications Map

| Domain | Dominant Memory Type | Key Challenge |
|--------|---------------------|---------------|
| Personal assistants | Semantic (preferences/profiles) | Personalization vs privacy |
| Software engineering | Procedural (code patterns, arch decisions) | Structural scale (thousands of files) |
| Open-world games | Episodic + procedural | Compositional skill reuse |
| Scientific reasoning | Semantic with uncertainty tracking | Confidence updating, belief revision |
| Multi-agent | Coordination memory | Shared vs private boundaries, concurrent writes |
| Tool use / API | Tool catalog + usage patterns | Schema drift (API updates invalidate stored patterns) |

### Engineering Realities

**Write path design**: filtering -> canonicalization -> deduplication -> priority scoring -> metadata tagging.
Optimal filtering is application-specific: medical needs zero false negatives; casual chat can tolerate them.

**Read path optimizations**: two-stage retrieval (BM25/metadata filter -> cross-encoder), retrieval-or-not gating, token budgeting, cache layers for high-frequency records.

**Staleness handling**: temporal versioning, source attribution (user statement > agent inference), contradiction detection, periodic consolidation.

**Latency**: retrieval adds 200-500ms. Mitigations: async writes, progressive retrieval (generate while searching), dynamic routing (skip retrieval for simple queries).

**Three architecture patterns**:
- **Pattern A (Monolithic context)**: All memory in prompt. Zero infra, fully transparent, capacity-capped. Suitable for short-lived agents.
- **Pattern B (Context + retrieval store)**: Working memory in window, long-term in external store. Workhorse for production agents today. Main challenge: retrieval quality.
- **Pattern C (Tiered with learned control)**: Multiple tiers managed by learned/prompted controller. Most headroom, most engineering. MemGPT + AgeMem exemplars.
- **Recommendation**: Start with Pattern B, instrument thoroughly, graduate to C only when data justifies it.

**Observability**: memory operation logging (every write, read, update, delete with timestamps), replay tools, memory diff between conversation turns. Critical for production but absent in research papers.

### Open Challenges (10 Frontiers)

1. **Principled consolidation**: dual-buffer approach -- "hot" buffer during probation, promoted to long-term after quality checks. Mirrors hippocampal-to-neocortical transfer.
2. **Causally grounded retrieval**: semantic similarity is not causal relevance. Hybrid retrievers blending similarity + temporal ordering + causal graph traversal needed.
3. **Trustworthy reflection**: external validation, uncertainty quantification (decay confidence over time), adversarial probing (periodically challenge stored beliefs), expiration policies for unvalidated reflections.
4. **Learning to forget**: selective forgetting policies maximizing long-term utility under safety/compliance constraints. Connections to machine unlearning.
5. **Multimodal/embodied memory**: fusing text, vision, audio, proprioception, tool state. Cross-modal retrieval (finding visual memory via textual query).
6. **Multi-agent memory governance**: access control, consensus for concurrent writes, knowledge transfer across specialized agents.
7. **Memory-efficient architectures**: sparse retrieval, compressed session vectors, Recurrent Memory Transformers, retrieval-free injection via adapters.
8. **Deeper neuroscience integration**: spreading activation, memory reconsolidation theory, Ebbinghaus curves with spaced repetition.
9. **Foundation model for memory control**: trained across diverse tasks for write/retrieve/summarize/forget/consolidate with general competence. AgeMem takes a first step.
10. **Standardized evaluation**: GLUE-style shared leaderboard for agent memory with conversational, agentic, and multi-session tracks.

### Survey's Key Empirical Claims

- MemoryArena (2026): active memory agent 80% vs long-context-only ~45% on interdependent multi-session tasks
- Voyager w/o skill library: 15.3x slower tech-tree progression
- Generative Agents w/o reflection: behavior degenerates within 48 simulated hours
- Reflexion: 91% pass@1 HumanEval vs 80% GPT-4 baseline
- Agentic Memory (AgeMem, 2026): RL-trained memory operations outperform all memory-augmented baselines on 5 benchmarks

---

## Synthesis: Key Takeaways for Lyra

1. **A-MEM's architecture is directly implementable**: the four-stage pipeline (note construction -> link generation -> memory evolution -> retrieval) requires only an LLM API, an embedding model (all-minilm-l6-v2), and a vector store. No special training needed.

2. **The cost-benefit ratio is compelling**: 85-93% token reduction vs full-context baselines, 2-6x improvement on multi-hop reasoning, ~$0.0003 per operation.

3. **Critical failure modes to engineer around**:
   - Summarization drift in context-resident compression (use external stores to preserve raw records)
   - Self-reinforcing error in reflective memory (require citation of specific episodic evidence)
   - Silent orchestration failures in hierarchical memory (implement comprehensive memory operation logging)
   - Schema drift in tool-use memory (version tracking + validation on stored records)

4. **Architecture recommendation** (from survey): Pattern B (context + retrieval store) is the pragmatic starting point. Graduate to Pattern C (tiered + learned) only when empirical data warrants it.

5. **Missing evaluation dimensions**: no existing benchmark systematically reports efficiency (token consumption, latency overhead) alongside accuracy. Lyra should track both.

6. **The write path is often overlooked**: optimal write path design (filtering, canonicalization, deduplication, priority scoring, metadata tagging) is application-specific and directly determines retrieval quality downstream.
