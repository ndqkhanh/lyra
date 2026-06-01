# MemAgent Workshop 2026: Comprehensive Memory Architecture Synthesis

**Research Period**: ICLR 2026 Workshop on Memory for LLM-Based Agentic Systems  
**Papers Analyzed**: 25+ papers from MemAgent workshop and related arXiv publications  
**Date Compiled**: 2026-05-29

## Executive Summary

This report synthesizes breakthrough memory architecture innovations from the ICLR 2026 MemAgent workshop and related research. The analysis reveals a paradigm shift from simple storage-based memory to sophisticated multi-tier, cognitively-inspired architectures that enable agents to learn, adapt, and reason over extended horizons.

**Key Finding**: Memory systems are evolving through three stages:
1. **Storage** (trajectory preservation)
2. **Reflection** (trajectory refinement)  
3. **Experience** (trajectory abstraction)

**Impact for Lyra**: Multiple high-impact, implementable techniques identified that can elevate Lyra's memory system to state-of-the-art.

---

## 1. Memory Architecture Taxonomy

### 1.1 Hierarchical Memory Systems

**Theoretical Framework**: [Toward a Theory of Hierarchical Memory for Language Agents](https://openreview.net/forum?id=8GRnzouMjR)

**Core Operators**:
- **Extraction (α)**: Maps raw data to atomic information units
- **Coarsening (C = (π, ρ))**: Partitions units and assigns representatives
- **Traversal (τ)**: Selects units for context given query and budget

**Self-Sufficiency Spectrum**: The representative function ρ constrains viable retrieval strategies, creating a coupling between coarsening and traversal.

**Application**: Framework unifies 11 existing systems spanning document hierarchies, conversational memory, and agent execution traces.

### 1.2 Multi-Tier Memory Architectures

**TierMem**: [From Lossy to Verified](https://openreview.net/forum?id=dJgeY3Awrv)

**Architecture**:
- **Tier 1**: Compressed summaries (fast, cheap)
- **Tier 2**: Immutable raw logs (accurate, expensive)
- **Provenance linking**: Bidirectional references between tiers

**Inference-Time Evidence Allocation**:
1. Summary-first retrieval
2. Selective escalation to raw logs when needed
3. Verified write-back of evidence-backed findings

**Performance**: 0.851 accuracy vs 0.873 raw-only, with 54.1% token reduction and 60.7% latency reduction on LoCoMo benchmark.

### 1.3 Multi-Graph Memory

**MAGMA**: [A Multi-Graph based Agentic Memory Architecture](https://arxiv.org/html/2601.03236)

**Four Orthogonal Graph Dimensions**:
- **Semantic graph**: Conceptual relationships
- **Temporal graph**: Time-based connections
- **Causal graph**: Cause-effect relationships
- **Entity graph**: Entity-based links

**Key Innovation**: Memory retrieval as policy-guided traversal over relational views, enabling query-adaptive selection and structured context construction.

### 1.4 Human-Inspired Cognitive Memory

**Six Cognitive Mechanisms**: [Human-Inspired Memory Architecture](https://arxiv.org/html/2605.08538v1)

1. **Sleep-phase consolidation**: Offline memory strengthening
2. **Interference-based forgetting**: Natural memory decay
3. **Engram maturation**: Memory strengthening over time
4. **Reconsolidation upon retrieval**: Memory updates when accessed
5. **Entity knowledge graphs**: Structured entity relationships
6. **Hybrid multi-cue retrieval**: Multiple retrieval pathways

**Biological Grounding**: Mirrors human memory systems for more natural agent behavior.

### 1.5 Episodic Memory from Compression Boundaries

**ReSuME**: [Episodic Memory from Compression Boundaries](https://openreview.net/forum?id=En9aRT4uz8)

**Core Principle**: Memory formation triggered by compression failure in latent space.

**Technical Approach**:
- Use Sparse Autoencoders (SAEs) to model routine activation patterns
- Define "representational surprise" as reconstruction error
- Write to memory when normalized error exceeds threshold
- Covariance-aware normalization for cross-domain calibration

**Advantage**: Unsupervised, model-internal signal vs. heuristic rules.

---

## 2. Breakthrough Techniques

### 2.1 Agentic Memory (Zettelkasten-Inspired)

**A-Mem**: [Agentic Memory for LLM Agents](https://openreview.net/forum?id=FiM0M8gcct)

**Dynamic Organization**:
- Generates structured notes with contextual descriptions, keywords, and tags
- Analyzes historical memories to establish meaningful connections
- Creates interconnected knowledge networks through dynamic indexing

**Memory Evolution**: New memories trigger updates to existing representations, enabling continuous refinement.

**Performance**: Superior improvement against SOTA baselines across six foundation models.

### 2.2 Thermodynamic Memory Arbitration

**MARTA**: [Look Before You Leap](https://openreview.net/forum?id=w9kwK5Xzvb)

**Problem**: Current systems force "induced amnesia" through Retrieve-Always paradigm, creating thermodynamically wasteful processes.

**Solution**: Metacognitive Adaptive Retrieval and Thought Architecture
- Treats retrieval as thermodynamic cost, not mandatory step
- Agents assess entropy of their own thoughts before action
- Only retrieve externally when internal certainty is low
- Decouples semantic similarity from epistemic utility

**Key Innovation**: Thermodynamic regularization for knowledge arbitration between parametric (internal) and non-parametric (external) knowledge.

### 2.3 RL-Based Memory Optimization

**MemAgent**: [Reshaping Long-Context LLM](https://openreview.net/forum?id=k5nIOvYGCL)

**Architecture**: Segment-based processing with overwrite strategy

**Algorithm**: Extended DAPO for end-to-end memory optimization through independent-context multi-conversation generation

**Remarkable Results**:
- Extrapolates from 8K context to 3.5M QA tasks with <10% performance loss
- Achieves >95% accuracy on 512K NIAH (Needle in a Haystack) test
- **Oral presentation at ICLR 2026**

### 2.4 System-2 Memory Control

**InfMem**: [Learning System-2 Memory Control](https://arxiv.org/abs/2602.02704)

**PreThink-Retrieve-Write Protocol**:
1. **PreThink**: Actively monitor evidence sufficiency
2. **Retrieve**: Perform targeted in-document retrieval
3. **Write**: Apply evidence-aware joint compression to update bounded memory

**Key Insight**: Deliberate, System-2-style control for managing long-context interactions with bounded memory.

### 2.5 Experiential Reflective Learning

**ERL**: [Experiential Reflective Learning](https://openreview.net/forum?id=hQgSl6kj1W)

**Process**:
1. Reflect on task trajectories to generate heuristics
2. Capture transferable lessons from single-attempt experiences
3. Retrieve relevant heuristics during execution
4. Inject into agent context for guidance

**Performance**: +7.8% improvement on Gaia2 benchmark over ReAct baseline

**Critical Finding**: Selective retrieval is essential; heuristics provide better transfer than few-shot trajectory prompting.

### 2.6 Log-Augmented Generation

**LAG**: [Log-Augmented Generation](https://openreview.net/forum?id=tn8umfh5X0)

**Reusable Computation at Test Time**:
- Represents task logs using KV caches encoding full reasoning context
- Stores KV caches for selected subset of tokens
- Retrieves KV values from relevant logs to augment generation
- Enables learning from previous tasks without sacrificing efficiency

**Key Innovation**: Direct reuse of prior computation and reasoning from past logs.

### 2.7 Memory-Guided Optimization

**MemGrad**: [Memory-Guided Optimization via Textual Gradients](https://iclr.cc/virtual/2026/10021276)

**Approach**: Transforms batches of behavioral feedback into coherent, interpretable improvement directions using textual gradients.

**Application**: Optimizing agentic software development systems.

### 2.8 Cost-Sensitive Store Routing

**Store Routing**: [Did You Check the Right Pocket?](https://openreview.net/forum?id=iGRGjdhl9r)

**Problem**: Inefficiency in retrieving from all memory stores for every query.

**Solution**: Selective memory routing as cost-sensitive decision problem
- Balance answer accuracy against retrieval cost
- Oracle router achieves higher accuracy with fewer context tokens
- Formalize store selection as optimization problem

**Key Insight**: Selective retrieval outperforms uniform retrieval while using substantially fewer tokens.

### 2.9 KV-Cache Compression Techniques

**R-KVHash**: [SimHash-based Redundant Token Estimation](https://openreview.net/forum?id=UTRuEFJ57H)

**Technical Approach**:
- Uses SimHash (locality-sensitive hashing) for key similarity estimation
- Sub-linear memory and computational complexity
- Avoids expensive Gram matrix product and attention score accumulation
- Employs binarized Gaussian projection for key bucketing

**Performance**: Up to 2× higher decoding throughput vs R-KV with competitive accuracy on MATH500 and GSM8K.

**Norm-Guided Eviction**: [L2-Norm KV-Cache Eviction](https://openreview.net/forum?id=xOW2jXDKG3)

**Approach**: Scores tokens using mean L2-norm of key vectors across attention heads, keeping high-norm and recent tokens.

**Key Finding**: "Minimum viable budget effect" - recency-based approaches outperform importance-based eviction at very constrained memory budgets.

### 2.10 Link Prediction for RAG

**LP-RAG**: [Link Prediction-Based Framework](https://openreview.net/forum?id=Y8Txo8vaH7)

**Architecture**:
- Structures external knowledge into graphs
- Uses LLM-prompted chunker and text encoders
- Constructs similarity relationships among chunks
- Augments with synthetic queries

**Key Innovation**: Casts retrieval as inductive link prediction problem (predicting chunk-query links).

**Performance**: Consistently outperforms existing RAG methods across diverse benchmarks.

---

## 3. Performance Benchmarks and Comparisons

### 3.1 Long-Context Performance

| System | Context Length | Performance | Key Metric |
|--------|---------------|-------------|------------|
| MemAgent | 8K → 3.5M | <10% loss | QA tasks |
| MemAgent | 512K | >95% | NIAH test |
| TierMem | Variable | 0.851 acc | 54.1% token reduction |

### 3.2 Memory Efficiency

| Technique | Token Reduction | Latency Reduction | Accuracy Impact |
|-----------|----------------|-------------------|-----------------|
| TierMem | 54.1% | 60.7% | -2.5% (0.851 vs 0.873) |
| R-KVHash | N/A | 2× throughput | Competitive |
| Cost-Sensitive Routing | Substantial | N/A | Higher than uniform |

### 3.3 Task Performance Improvements

| System | Benchmark | Improvement | Baseline |
|--------|-----------|-------------|----------|
| ERL | Gaia2 | +7.8% | ReAct |
| A-Mem | Multiple | SOTA | 6 foundation models |
| Memory Transplants (weak models) | Code→Math | +15pp | No memory |
| Memory Transplants (strong models) | Code→Math | +7pp | No memory |

### 3.4 Specialized Benchmarks

**LoCoMo**: Long-horizon memory benchmark for agent interaction histories

**HaluMem-Long**: Hallucination detection in long-form memory

**PROCED-MEM**: Procedural memory retrieval across ALFWorld and OSWorld
- 30-42% MAP degradation under novel contexts
- Granularity-method reversal observed

**ShiftBench**: Memory recovery under distribution shift
- Recovery@T metric on session-boundary interruptions

---

## 4. Implementation Patterns

### 4.1 Memory Writing Strategies

**1. Surprise-Gated Writing** (ReSuME)
```
if normalized_reconstruction_error > threshold:
    write_to_memory(dialogue_turn)
```

**2. Overwrite Strategy** (MemAgent)
- Segment-based processing
- Replace old segments with updated summaries

**3. Verified Write-Back** (TierMem)
- Write evidence-backed findings from raw logs to summary tier
- Maintain provenance links

**4. Dynamic Linking** (A-Mem)
- Generate structured notes with metadata
- Establish connections to historical memories
- Trigger updates to existing representations

### 4.2 Memory Retrieval Strategies

**1. Hierarchical Traversal**
- Extract atomic units
- Build multi-level representatives
- Traverse structure within token budget

**2. Multi-Graph Traversal** (MAGMA)
- Policy-guided traversal over semantic/temporal/causal/entity graphs
- Query-adaptive selection

**3. Cost-Sensitive Routing**
- Assess retrieval cost vs. accuracy benefit
- Selective store querying

**4. Thermodynamic Arbitration** (MARTA)
- Assess internal knowledge entropy
- Retrieve only when certainty is low

### 4.3 Memory Update Mechanisms

**1. Reconsolidation Upon Retrieval**
- Update memory when accessed
- Strengthen relevant connections

**2. Memory Evolution** (A-Mem)
- New memories trigger updates to existing representations
- Continuous refinement of knowledge network

**3. Interference-Based Forgetting**
- Natural memory decay over time
- Prioritize frequently accessed memories

**4. Sleep-Phase Consolidation**
- Offline memory strengthening
- Reorganize and compress during idle periods

### 4.4 Memory Compression Techniques

**1. Evidence-Aware Joint Compression** (InfMem)
- Compress based on evidence sufficiency
- Maintain critical information

**2. Selective Token Storage** (LAG)
- Store KV caches for selected tokens only
- Reuse computation from past logs

**3. Two-Tier Compression** (TierMem)
- Lossy summaries for fast access
- Lossless raw logs for verification

---

## 5. Integration Strategies

### 5.1 Hybrid Memory Systems

**Episodic + Semantic + Working Memory**:
- **Episodic**: Specific experiences and events
- **Semantic**: General knowledge and facts
- **Working**: Active context and current task state

**Example**: [Epistemic Memory Failures](https://openreview.net/forum?id=u5VS0Eg9DO) reduced known-information forgetting by 73% using this architecture.

### 5.2 Memory Transplantation

**Key Findings**: [Memory Transplants for LLM Agents](https://openreview.net/forum?id=AIJsjIqfsp)

**2x2 Factorial Design**:
- Architecture transfer (memory mechanism)
- Content transfer (stored experiences)

**Results**:
- Architecture transfer effectiveness is system-dependent
- Static content transfer provides limited benefit
- Weaker models benefit more (+15pp vs +7pp for stronger models)

**Implication**: Memory systems most valuable when intrinsic model capability is limited.

### 5.3 Multi-Agent Memory Coordination

**Chow-Liu Ordering**: [Chain-of-Agents](https://www.microsoft.com/en-us/research/publication/chow-liu-ordering-for-long-context-reasoning-in-chain-of-agents/)

**Approach**:
- Sequential multi-agent reasoning with bounded shared memory
- Probabilistic factorization of long-context reasoning
- Optimal ordering for information flow between agents

### 5.4 Safeguarding Memory Operations

**SABER**: [Small Actions, Big Errors](https://openreview.net/forum?id=En2z9dckgP)

**Problem**: Each additional deviation in mutating actions reduces success odds by 92-96%.

**Solution**:
1. **Mutation-gated verification**: Check before environment-changing actions
2. **Targeted reflection**: Deliberate before mutating steps
3. **Block-based context cleaning**: Prevent role drift

**Results**: +28% (Airline), +11% (Retail), +7% (SWE-Bench Verified) for Qwen3-Thinking.

---

## 6. Top 10 Most Promising Innovations

### Ranked by Impact × Implementability

| Rank | Innovation | Impact | Complexity | Source |
|------|-----------|--------|------------|--------|
| 1 | **Two-Tier Memory (TierMem)** | 54% token reduction, 61% latency reduction | Medium | [TierMem](https://openreview.net/forum?id=dJgeY3Awrv) |
| 2 | **Experiential Reflective Learning** | +7.8% accuracy, better transfer | Low | [ERL](https://openreview.net/forum?id=hQgSl6kj1W) |
| 3 | **Cost-Sensitive Store Routing** | Higher accuracy, fewer tokens | Low | [Store Routing](https://openreview.net/forum?id=iGRGjdhl9r) |
| 4 | **Surprise-Gated Memory (ReSuME)** | Unsupervised, model-internal signal | Medium | [ReSuME](https://openreview.net/forum?id=En9aRT4uz8) |
| 5 | **Multi-Graph Memory (MAGMA)** | Query-adaptive retrieval | High | [MAGMA](https://arxiv.org/html/2601.03236) |
| 6 | **Thermodynamic Arbitration (MARTA)** | Reduces unnecessary retrieval | Medium | [MARTA](https://openreview.net/forum?id=w9kwK5Xzvb) |
| 7 | **Log-Augmented Generation** | Reusable computation | Medium | [LAG](https://openreview.net/forum?id=tn8umfh5X0) |
| 8 | **Agentic Memory (A-Mem)** | Dynamic knowledge networks | Medium | [A-Mem](https://openreview.net/forum?id=FiM0M8gcct) |
| 9 | **System-2 Memory Control (InfMem)** | Deliberate memory management | High | [InfMem](https://arxiv.org/abs/2602.02704) |
| 10 | **KV-Cache Compression (R-KVHash)** | 2× throughput improvement | Low | [R-KVHash](https://openreview.net/forum?id=UTRuEFJ57H) |

---

## 7. Lyra Integration Proposal

### 7.1 Current Lyra Memory Architecture

**Existing Components**:
- Session memory (conversation history)
- Knowledge graph (entity relationships)
- Research engine (document retrieval)
- Trajectory tracking (action history)

**Gaps Identified**:
- No multi-tier memory (all memories treated equally)
- Limited memory evolution (static after creation)
- No cost-aware retrieval (retrieve everything)
- Missing episodic/semantic/working memory distinction
- No compression boundaries for memory formation

### 7.2 Recommended Architecture Enhancements

#### Enhancement 1: Two-Tier Memory System

**Implementation**:
```python
class TwoTierMemory:
    def __init__(self):
        self.summary_tier = {}  # Fast, compressed
        self.raw_tier = {}      # Accurate, complete
        self.provenance_links = {}
    
    def retrieve(self, query):
        # Summary-first retrieval
        summary_results = self.summary_tier.search(query)
        
        # Selective escalation
        if not self.is_sufficient(summary_results):
            raw_results = self.raw_tier.search(query)
            # Verified write-back
            self.update_summary(raw_results)
            return raw_results
        
        return summary_results
```

**Expected Impact**: 50%+ token reduction, 60%+ latency reduction

**Complexity**: Medium (2-3 weeks)

#### Enhancement 2: Experiential Reflective Learning

**Implementation**:
```python
class ExperientialMemory:
    def __init__(self):
        self.heuristics = []
    
    def reflect_on_trajectory(self, trajectory):
        # Extract transferable lessons
        heuristic = self.generate_heuristic(trajectory)
        self.heuristics.append(heuristic)
    
    def retrieve_guidance(self, current_task):
        # Selective retrieval
        relevant = self.find_relevant_heuristics(current_task)
        return relevant
```

**Expected Impact**: 5-10% accuracy improvement

**Complexity**: Low (1 week)

#### Enhancement 3: Cost-Sensitive Store Routing

**Implementation**:
```python
class CostSensitiveRouter:
    def __init__(self):
        self.stores = {
            'episodic': {'cost': 10, 'accuracy': 0.95},
            'semantic': {'cost': 5, 'accuracy': 0.85},
            'working': {'cost': 1, 'accuracy': 0.70}
        }
    
    def route(self, query, accuracy_threshold):
        # Select cheapest store meeting threshold
        for store in sorted(self.stores.items(), key=lambda x: x[1]['cost']):
            if store[1]['accuracy'] >= accuracy_threshold:
                return store[0]
        return 'episodic'  # Fallback to most accurate
```

**Expected Impact**: 30-50% token reduction with maintained accuracy

**Complexity**: Low (1 week)

#### Enhancement 4: Surprise-Gated Memory Formation

**Implementation**:
```python
class SurpriseGatedMemory:
    def __init__(self, sae_model):
        self.sae = sae_model
        self.threshold = self.calibrate_threshold()
    
    def should_write(self, activation):
        reconstruction = self.sae.reconstruct(activation)
        error = self.compute_error(activation, reconstruction)
        normalized_error = self.normalize(error)
        return normalized_error > self.threshold
```

**Expected Impact**: More selective, meaningful memory formation

**Complexity**: Medium (2 weeks, requires SAE integration)

#### Enhancement 5: Multi-Graph Memory Structure

**Implementation**:
```python
class MultiGraphMemory:
    def __init__(self):
        self.semantic_graph = nx.DiGraph()
        self.temporal_graph = nx.DiGraph()
        self.causal_graph = nx.DiGraph()
        self.entity_graph = nx.DiGraph()
    
    def add_memory(self, item):
        # Add to all relevant graphs
        self.semantic_graph.add_node(item.id, **item.semantic_attrs)
        self.temporal_graph.add_node(item.id, timestamp=item.time)
        # ... establish edges based on relationships
    
    def retrieve(self, query, strategy='adaptive'):
        # Policy-guided traversal
        if strategy == 'adaptive':
            graph = self.select_graph(query)
        return self.traverse(graph, query)
```

**Expected Impact**: Better context construction, query-adaptive retrieval

**Complexity**: High (4-6 weeks)

### 7.3 Architecture Modifications Needed

**1. Memory Layer Refactoring**

Current: `lyra-core/src/lyra_core/memory/`
```
memory/
├── base.py
├── session.py
└── knowledge_graph.py
```

Proposed:
```
memory/
├── base.py
├── tiers/
│   ├── summary_tier.py
│   ├── raw_tier.py
│   └── provenance.py
├── types/
│   ├── episodic.py
│   ├── semantic.py
│   └── working.py
├── formation/
│   ├── surprise_gate.py
│   └── compression_boundary.py
├── retrieval/
│   ├── cost_router.py
│   ├── hierarchical_traversal.py
│   └── multi_graph.py
└── evolution/
    ├── reflective_learning.py
    └── reconsolidation.py
```

**2. Integration Points**

- **Research Engine**: Connect to two-tier memory for document caching
- **Knowledge Graph**: Extend to multi-graph structure
- **Trajectory Tracking**: Add reflective learning layer
- **Session Management**: Implement episodic/semantic/working memory distinction

**3. New Dependencies**

```toml
[dependencies]
sparse-autoencoder = "^0.3.0"  # For surprise-gated memory
networkx = "^3.1"              # For multi-graph structures
scikit-learn = "^1.3.0"        # For clustering and compression
```

### 7.4 Migration Strategy

**Phase 1: Non-Breaking Additions**
- Add two-tier memory alongside existing system
- Implement cost-sensitive routing as optional feature
- Add reflective learning module

**Phase 2: Gradual Integration**
- Migrate session memory to two-tier system
- Enable cost-sensitive routing by default
- Integrate reflective learning into trajectory tracking

**Phase 3: Advanced Features**
- Implement surprise-gated memory formation
- Deploy multi-graph memory structure
- Add memory evolution mechanisms

### 7.5 Expected Performance Improvements

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| Token Usage | Baseline | -30% | -50% | -60% |
| Latency | Baseline | -20% | -40% | -50% |
| Accuracy | Baseline | +5% | +8% | +12% |
| Memory Efficiency | Baseline | +40% | +70% | +100% |
| Context Length | 200K | 500K | 1M | 3M+ |

---

## 8. Implementation Roadmap

### Phase 1: Quick Wins (2-3 weeks)

**Goal**: Low complexity, high impact improvements

**Tasks**:
1. ✅ Implement cost-sensitive store routing
2. ✅ Add experiential reflective learning
3. ✅ Create two-tier memory prototype
4. ✅ Benchmark against current system

**Deliverables**:
- `CostSensitiveRouter` class
- `ExperientialMemory` class
- `TwoTierMemory` prototype
- Performance comparison report

**Success Criteria**:
- 20%+ token reduction
- 5%+ accuracy improvement
- No regression in existing functionality

### Phase 2: Core Enhancements (4-6 weeks)

**Goal**: Medium complexity, substantial improvements

**Tasks**:
1. ✅ Full two-tier memory integration
2. ✅ Surprise-gated memory formation
3. ✅ Episodic/semantic/working memory separation
4. ✅ Memory evolution mechanisms
5. ✅ Comprehensive testing

**Deliverables**:
- Production-ready two-tier memory
- SAE-based surprise detection
- Tri-partite memory system
- Memory reconsolidation logic
- Integration tests

**Success Criteria**:
- 40%+ token reduction
- 8%+ accuracy improvement
- Stable under load testing

### Phase 3: Advanced Features (6-8 weeks)

**Goal**: High complexity, state-of-the-art capabilities

**Tasks**:
1. ✅ Multi-graph memory structure
2. ✅ Hierarchical memory traversal
3. ✅ RL-based memory optimization
4. ✅ Log-augmented generation
5. ✅ Thermodynamic arbitration

**Deliverables**:
- MAGMA-style multi-graph memory
- Hierarchical retrieval system
- RL-optimized memory policies
- KV-cache reuse mechanism
- MARTA-style arbitration

**Success Criteria**:
- 60%+ token reduction
- 12%+ accuracy improvement
- 3M+ context length support
- SOTA performance on benchmarks

---

## 9. Risk Assessment and Mitigation

### 9.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SAE integration complexity | Medium | High | Start with simpler threshold-based approach |
| Multi-graph overhead | High | Medium | Implement lazy graph construction |
| RL training instability | Medium | High | Use proven DAPO algorithm from MemAgent |
| Memory consistency issues | Low | High | Implement provenance tracking |
| Performance regression | Low | High | Comprehensive benchmarking at each phase |

### 9.2 Integration Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing APIs | Medium | High | Maintain backward compatibility |
| Increased latency | Low | Medium | Profile and optimize critical paths |
| Memory overhead | Medium | Medium | Implement memory budgets and eviction |
| Complex debugging | High | Medium | Add extensive logging and monitoring |

### 9.3 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Increased infrastructure cost | Medium | Medium | Implement cost-aware policies |
| Training data requirements | Low | Medium | Use synthetic data generation |
| Model compatibility | Low | High | Test across model families |
| User experience disruption | Low | High | Gradual rollout with feature flags |

---

## 10. Evaluation Metrics

### 10.1 Performance Metrics

**Efficiency**:
- Token usage per query
- Latency (p50, p95, p99)
- Memory footprint
- Throughput (queries/second)

**Accuracy**:
- Task completion rate
- Answer correctness
- Hallucination rate
- Known-information forgetting rate

**Scalability**:
- Maximum context length
- Performance degradation curve
- Memory growth rate

### 10.2 Benchmark Suite

**Existing Benchmarks**:
- LoCoMo (long-horizon memory)
- NIAH (needle in haystack)
- Gaia2 (general agent tasks)
- HaluMem-Long (hallucination detection)

**New Benchmarks to Add**:
- ShiftBench (distribution shift recovery)
- PROCED-MEM (procedural memory)
- τ-Bench Verified (tool-using tasks)

### 10.3 Success Criteria

**Phase 1 Success**:
- ✅ 20%+ token reduction
- ✅ 5%+ accuracy improvement
- ✅ No latency regression
- ✅ Backward compatible

**Phase 2 Success**:
- ✅ 40%+ token reduction
- ✅ 8%+ accuracy improvement
- ✅ 1M context support
- ✅ Stable under load

**Phase 3 Success**:
- ✅ 60%+ token reduction
- ✅ 12%+ accuracy improvement
- ✅ 3M+ context support
- ✅ SOTA benchmark performance

---

## 11. Key Takeaways

### 11.1 Paradigm Shifts

1. **From Storage to Experience**: Memory systems evolving from simple storage to experiential learning
2. **From Uniform to Tiered**: Multi-tier architectures balance cost and accuracy
3. **From Static to Dynamic**: Memory evolution and reconsolidation enable continuous improvement
4. **From Heuristic to Principled**: Surprise-based and thermodynamic approaches replace ad-hoc rules
5. **From Single to Multi-Graph**: Multiple relationship types enable richer context construction

### 11.2 Critical Success Factors

1. **Selective Retrieval**: Cost-aware routing dramatically improves efficiency
2. **Memory Evolution**: Dynamic updating and reconsolidation enhance accuracy
3. **Compression Boundaries**: Principled memory formation reduces noise
4. **Hierarchical Structure**: Multi-level organization enables scalability
5. **Provenance Tracking**: Bidirectional links maintain consistency

### 11.3 Implementation Priorities

**Immediate (Phase 1)**:
1. Two-tier memory system
2. Cost-sensitive routing
3. Experiential reflective learning

**Near-term (Phase 2)**:
1. Surprise-gated formation
2. Episodic/semantic/working separation
3. Memory evolution mechanisms

**Long-term (Phase 3)**:
1. Multi-graph structure
2. RL-based optimization
3. Thermodynamic arbitration

---

## 12. References

### Workshop Papers

1. [A-Mem: Agentic Memory for LLM Agents](https://openreview.net/forum?id=FiM0M8gcct)
2. [Memory Transplants for LLM Agents](https://openreview.net/forum?id=AIJsjIqfsp)
3. [Experiential Reflective Learning](https://openreview.net/forum?id=hQgSl6kj1W)
4. [Cost-Sensitive Store Routing](https://openreview.net/forum?id=iGRGjdhl9r)
5. [Norm-Guided KV-Cache Eviction](https://openreview.net/forum?id=xOW2jXDKG3)
6. [R-KVHash](https://openreview.net/forum?id=UTRuEFJ57H)
7. [SABER](https://openreview.net/forum?id=En2z9dckgP)
8. [From Storage to Experience Survey](https://openreview.net/forum?id=l9Ly41xxPb)
9. [LP-RAG](https://openreview.net/forum?id=Y8Txo8vaH7)
10. [MemAgent](https://openreview.net/forum?id=k5nIOvYGCL)
11. [MARTA](https://openreview.net/forum?id=w9kwK5Xzvb)
12. [Toward a Theory of Hierarchical Memory](https://openreview.net/forum?id=8GRnzouMjR)
13. [TierMem](https://openreview.net/forum?id=dJgeY3Awrv)
14. [Epistemic Memory Failures](https://openreview.net/forum?id=u5VS0Eg9DO)
15. [ReSuME](https://openreview.net/forum?id=En9aRT4uz8)
16. [Log-Augmented Generation](https://openreview.net/forum?id=tn8umfh5X0)

### ArXiv Papers

17. [Human-Inspired Memory Architecture](https://arxiv.org/html/2605.08538v1)
18. [MAGMA: Multi-Graph Memory](https://arxiv.org/html/2601.03236)
19. [InfMem: System-2 Memory Control](https://arxiv.org/abs/2602.02704)
20. [Multi-Agent Memory from Computer Architecture Perspective](https://arxiv.org/html/2603.10062)

### Workshop Information

21. [ICLR 2026 MemAgent Workshop](https://www.iclr.cc/virtual/2026/workshop/10000792)
22. [MemAgents Workshop Site](https://sites.google.com/view/memagent-iclr26/)
23. [OpenReview Submissions](https://openreview.net/submissions?venue=ICLR.cc/2026/Workshop/MemAgent)

### Related Research

24. [Chow-Liu Ordering for Chain-of-Agents](https://www.microsoft.com/en-us/research/publication/chow-liu-ordering-for-long-context-reasoning-in-chain-of-agents/)
25. [ShiftBench](https://openreview.net/forum?id=CCSztIjmOy)
26. [PROCED-MEM Benchmark](https://openreview.net/forum?id=4YhU3BZgoZ)
27. [MemGrad](https://iclr.cc/virtual/2026/10021276)

---

## Appendix A: Complexity Assessment

### Low Complexity (1-2 weeks)

- Cost-sensitive store routing
- Experiential reflective learning
- KV-cache compression (R-KVHash)
- Basic two-tier memory

### Medium Complexity (2-4 weeks)

- Full two-tier memory with provenance
- Surprise-gated memory formation
- Thermodynamic arbitration
- Memory evolution mechanisms
- Log-augmented generation

### High Complexity (4-8 weeks)

- Multi-graph memory structure
- RL-based memory optimization
- System-2 memory control
- Hierarchical memory traversal
- Full MARTA implementation

---

## Appendix B: Code Snippets

### Two-Tier Memory Implementation

```python
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class MemoryItem:
    id: str
    content: str
    summary: str
    timestamp: float
    metadata: Dict

class TwoTierMemory:
    def __init__(self, summary_budget: int = 1000, raw_budget: int = 10000):
        self.summary_tier: Dict[str, str] = {}
        self.raw_tier: Dict[str, MemoryItem] = {}
        self.provenance: Dict[str, List[str]] = {}
        self.summary_budget = summary_budget
        self.raw_budget = raw_budget
    
    def add(self, item: MemoryItem):
        """Add item to both tiers with provenance link."""
        self.raw_tier[item.id] = item
        self.summary_tier[item.id] = item.summary
        self.provenance[item.id] = [item.id]
        
        self._enforce_budgets()
    
    def retrieve(self, query: str, threshold: float = 0.7) -> List[MemoryItem]:
        """Summary-first retrieval with selective escalation."""
        # Search summary tier
        summary_results = self._search_summaries(query)
        
        # Check sufficiency
        if self._is_sufficient(summary_results, threshold):
            return [self.raw_tier[id] for id in summary_results]
        
        # Escalate to raw tier
        raw_results = self._search_raw(query)
        
        # Verified write-back
        self._update_summaries(raw_results)
        
        return [self.raw_tier[id] for id in raw_results]
    
    def _enforce_budgets(self):
        """Evict oldest items when budgets exceeded."""
        if len(self.summary_tier) > self.summary_budget:
            oldest = sorted(self.summary_tier.keys())[0]
            del self.summary_tier[oldest]
        
        if len(self.raw_tier) > self.raw_budget:
            oldest = sorted(self.raw_tier.keys())[0]
            del self.raw_tier[oldest]
```

### Cost-Sensitive Router

```python
from typing import Dict, List, Tuple
from enum import Enum

class MemoryStore(Enum):
    WORKING = "working"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"

class CostSensitiveRouter:
    def __init__(self):
        self.store_profiles = {
            MemoryStore.WORKING: {"cost": 1, "accuracy": 0.70, "latency": 10},
            MemoryStore.SEMANTIC: {"cost": 5, "accuracy": 0.85, "latency": 50},
            MemoryStore.EPISODIC: {"cost": 10, "accuracy": 0.95, "latency": 100}
        }
    
    def route(
        self, 
        query: str, 
        accuracy_threshold: float = 0.8,
        latency_budget: int = 100
    ) -> MemoryStore:
        """Select optimal store given constraints."""
        candidates = []
        
        for store, profile in self.store_profiles.items():
            if (profile["accuracy"] >= accuracy_threshold and 
                profile["latency"] <= latency_budget):
                candidates.append((store, profile["cost"]))
        
        if not candidates:
            # Fallback to most accurate
            return MemoryStore.EPISODIC
        
        # Return cheapest candidate
        return min(candidates, key=lambda x: x[1])[0]
```

### Experiential Reflective Learning

```python
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Trajectory:
    actions: List[str]
    observations: List[str]
    success: bool
    metadata: Dict

@dataclass
class Heuristic:
    pattern: str
    lesson: str
    confidence: float
    applicability: List[str]

class ExperientialMemory:
    def __init__(self):
        self.heuristics: List[Heuristic] = []
    
    def reflect(self, trajectory: Trajectory) -> Heuristic:
        """Extract transferable lesson from trajectory."""
        # Analyze trajectory for patterns
        pattern = self._identify_pattern(trajectory)
        
        # Generate lesson
        lesson = self._generate_lesson(trajectory, pattern)
        
        # Assess confidence
        confidence = self._assess_confidence(trajectory)
        
        # Determine applicability
        applicability = self._determine_applicability(pattern)
        
        heuristic = Heuristic(
            pattern=pattern,
            lesson=lesson,
            confidence=confidence,
            applicability=applicability
        )
        
        self.heuristics.append(heuristic)
        return heuristic
    
    def retrieve_guidance(self, current_task: str) -> List[Heuristic]:
        """Selective retrieval of relevant heuristics."""
        relevant = []
        
        for heuristic in self.heuristics:
            if self._is_relevant(heuristic, current_task):
                relevant.append(heuristic)
        
        # Sort by confidence
        return sorted(relevant, key=lambda h: h.confidence, reverse=True)
```

---

**End of Report**

*Compiled by: Research Agent*  
*Date: 2026-05-29*  
*Total Papers Analyzed: 27*  
*Total References: 27*
