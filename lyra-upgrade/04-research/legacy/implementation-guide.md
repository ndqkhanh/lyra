# Quick Implementation Guide: Memory Architecture Upgrades

**For**: Lyra Development Team  
**Based on**: ICLR 2026 MemAgent Workshop Research  
**Priority**: High-impact, low-complexity improvements first

## Week 1: Cost-Sensitive Store Routing

### What It Does
Routes queries to the cheapest memory store that meets accuracy requirements.

### Implementation

```python
# File: lyra-core/src/lyra_core/memory/retrieval/cost_router.py

from enum import Enum
from typing import Dict, Optional

class MemoryStore(Enum):
    WORKING = "working"      # Fast, recent context
    SEMANTIC = "semantic"    # General knowledge
    EPISODIC = "episodic"    # Detailed experiences

class CostSensitiveRouter:
    """Routes queries to optimal memory store based on cost/accuracy tradeoff."""
    
    def __init__(self):
        self.store_profiles = {
            MemoryStore.WORKING: {
                "cost": 1,           # Tokens per query
                "accuracy": 0.70,    # Expected accuracy
                "latency_ms": 10
            },
            MemoryStore.SEMANTIC: {
                "cost": 5,
                "accuracy": 0.85,
                "latency_ms": 50
            },
            MemoryStore.EPISODIC: {
                "cost": 10,
                "accuracy": 0.95,
                "latency_ms": 100
            }
        }
    
    def route(
        self,
        query: str,
        accuracy_threshold: float = 0.8,
        latency_budget_ms: int = 100
    ) -> MemoryStore:
        """Select optimal store given constraints."""
        candidates = []
        
        for store, profile in self.store_profiles.items():
            if (profile["accuracy"] >= accuracy_threshold and
                profile["latency_ms"] <= latency_budget_ms):
                candidates.append((store, profile["cost"]))
        
        if not candidates:
            return MemoryStore.EPISODIC  # Fallback to most accurate
        
        return min(candidates, key=lambda x: x[1])[0]
```

### Integration Point

```python
# In lyra-core/src/lyra_core/memory/base.py

class MemoryManager:
    def __init__(self):
        self.router = CostSensitiveRouter()
        self.stores = {
            MemoryStore.WORKING: WorkingMemory(),
            MemoryStore.SEMANTIC: SemanticMemory(),
            MemoryStore.EPISODIC: EpisodicMemory()
        }
    
    def retrieve(self, query: str, accuracy: float = 0.8):
        store_type = self.router.route(query, accuracy)
        return self.stores[store_type].search(query)
```

### Testing

```python
# tests/test_cost_router.py

def test_router_selects_cheapest_sufficient():
    router = CostSensitiveRouter()
    
    # Should select SEMANTIC (0.85 accuracy, cost 5)
    # when threshold is 0.8
    store = router.route("test query", accuracy_threshold=0.8)
    assert store == MemoryStore.SEMANTIC
    
    # Should select EPISODIC (0.95 accuracy, cost 10)
    # when threshold is 0.9
    store = router.route("test query", accuracy_threshold=0.9)
    assert store == MemoryStore.EPISODIC
```

**Expected Impact**: 30-40% token reduction

---

## Week 2: Experiential Reflective Learning

### What It Does
Learns reusable heuristics from task trajectories for better transfer.

### Implementation

```python
# File: lyra-core/src/lyra_core/memory/evolution/reflective_learning.py

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Trajectory:
    """Record of agent actions and outcomes."""
    task: str
    actions: List[str]
    observations: List[str]
    success: bool
    metadata: Dict

@dataclass
class Heuristic:
    """Transferable lesson learned from experience."""
    pattern: str          # What situation this applies to
    lesson: str           # What to do
    confidence: float     # How reliable (0-1)
    examples: List[str]   # Supporting trajectories

class ExperientialMemory:
    """Learns from experience via reflection on trajectories."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.heuristics: List[Heuristic] = []
    
    def reflect(self, trajectory: Trajectory) -> Heuristic:
        """Extract transferable lesson from trajectory."""
        
        # Use LLM to analyze trajectory
        prompt = f"""
        Analyze this task trajectory and extract a transferable lesson:
        
        Task: {trajectory.task}
        Actions: {trajectory.actions}
        Success: {trajectory.success}
        
        Extract:
        1. Pattern: What type of situation was this?
        2. Lesson: What general principle can be learned?
        3. Applicability: What other tasks would this help with?
        """
        
        response = self.llm.generate(prompt)
        
        heuristic = Heuristic(
            pattern=response["pattern"],
            lesson=response["lesson"],
            confidence=0.8 if trajectory.success else 0.5,
            examples=[trajectory.task]
        )
        
        self.heuristics.append(heuristic)
        return heuristic
    
    def retrieve_guidance(self, current_task: str, top_k: int = 3) -> List[Heuristic]:
        """Get relevant heuristics for current task."""
        
        # Score heuristics by relevance
        scored = []
        for h in self.heuristics:
            relevance = self._compute_relevance(h, current_task)
            scored.append((h, relevance * h.confidence))
        
        # Return top-k
        scored.sort(key=lambda x: x[1], reverse=True)
        return [h for h, _ in scored[:top_k]]
    
    def _compute_relevance(self, heuristic: Heuristic, task: str) -> float:
        """Compute relevance score (0-1)."""
        # Simple keyword overlap for now
        h_words = set(heuristic.pattern.lower().split())
        t_words = set(task.lower().split())
        overlap = len(h_words & t_words)
        return overlap / max(len(h_words), len(t_words))
```

### Integration Point

```python
# In lyra-core/src/lyra_core/orchestration/agent.py

class Agent:
    def __init__(self):
        self.experiential_memory = ExperientialMemory(llm_client)
    
    async def execute_task(self, task: str):
        # Retrieve guidance from past experience
        heuristics = self.experiential_memory.retrieve_guidance(task)
        
        # Include in context
        context = f"Relevant lessons from past experience:\n"
        for h in heuristics:
            context += f"- {h.lesson}\n"
        
        # Execute with guidance
        trajectory = await self._execute_with_context(task, context)
        
        # Reflect on outcome
        self.experiential_memory.reflect(trajectory)
        
        return trajectory
```

**Expected Impact**: 5-10% accuracy improvement

---

## Week 3: Two-Tier Memory System

### What It Does
Fast summary tier + accurate raw tier with selective escalation.

### Implementation

```python
# File: lyra-core/src/lyra_core/memory/tiers/two_tier.py

from typing import Dict, List, Optional
from dataclasses import dataclass
import time

@dataclass
class MemoryItem:
    id: str
    content: str          # Full content
    summary: str          # Compressed version
    timestamp: float
    metadata: Dict

class TwoTierMemory:
    """Two-tier memory with summary and raw tiers."""
    
    def __init__(
        self,
        summary_budget: int = 1000,
        raw_budget: int = 10000,
        llm_client = None
    ):
        self.summary_tier: Dict[str, str] = {}
        self.raw_tier: Dict[str, MemoryItem] = {}
        self.provenance: Dict[str, List[str]] = {}
        
        self.summary_budget = summary_budget
        self.raw_budget = raw_budget
        self.llm = llm_client
    
    def add(self, item: MemoryItem):
        """Add item to both tiers with provenance link."""
        # Store in raw tier
        self.raw_tier[item.id] = item
        
        # Generate and store summary
        if not item.summary:
            item.summary = self._generate_summary(item.content)
        self.summary_tier[item.id] = item.summary
        
        # Create provenance link
        self.provenance[item.id] = [item.id]
        
        # Enforce budgets
        self._enforce_budgets()
    
    def retrieve(
        self,
        query: str,
        sufficiency_threshold: float = 0.7
    ) -> List[MemoryItem]:
        """Summary-first retrieval with selective escalation."""
        
        # Phase 1: Search summary tier
        summary_results = self._search_summaries(query)
        
        # Phase 2: Check sufficiency
        if self._is_sufficient(summary_results, sufficiency_threshold):
            # Summaries are good enough
            return [self.raw_tier[id] for id in summary_results]
        
        # Phase 3: Escalate to raw tier
        raw_results = self._search_raw(query)
        
        # Phase 4: Verified write-back
        self._update_summaries(raw_results)
        
        return [self.raw_tier[id] for id in raw_results]
    
    def _generate_summary(self, content: str) -> str:
        """Generate compressed summary of content."""
        if len(content) < 100:
            return content
        
        prompt = f"Summarize in 1-2 sentences:\n{content}"
        return self.llm.generate(prompt)
    
    def _search_summaries(self, query: str) -> List[str]:
        """Search summary tier (fast, approximate)."""
        # Simple keyword matching for now
        results = []
        query_words = set(query.lower().split())
        
        for id, summary in self.summary_tier.items():
            summary_words = set(summary.lower().split())
            overlap = len(query_words & summary_words)
            if overlap > 0:
                results.append((id, overlap))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [id for id, _ in results[:10]]
    
    def _search_raw(self, query: str) -> List[str]:
        """Search raw tier (slow, accurate)."""
        # Use semantic search on full content
        results = []
        for id, item in self.raw_tier.items():
            score = self._semantic_similarity(query, item.content)
            results.append((id, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [id for id, _ in results[:10]]
    
    def _is_sufficient(self, results: List[str], threshold: float) -> bool:
        """Check if summary results are sufficient."""
        if not results:
            return False
        
        # Check if top result has high enough confidence
        # (simplified - in practice, use LLM to judge)
        return len(results) >= 3
    
    def _update_summaries(self, raw_ids: List[str]):
        """Verified write-back from raw to summary tier."""
        for id in raw_ids:
            if id in self.raw_tier:
                item = self.raw_tier[id]
                # Regenerate summary with new context
                self.summary_tier[id] = self._generate_summary(item.content)
    
    def _enforce_budgets(self):
        """Evict oldest items when budgets exceeded."""
        # Evict from summary tier
        while len(self.summary_tier) > self.summary_budget:
            oldest = min(self.summary_tier.keys(),
                        key=lambda id: self.raw_tier[id].timestamp)
            del self.summary_tier[oldest]
        
        # Evict from raw tier
        while len(self.raw_tier) > self.raw_budget:
            oldest = min(self.raw_tier.keys(),
                        key=lambda id: self.raw_tier[id].timestamp)
            del self.raw_tier[oldest]
            if oldest in self.summary_tier:
                del self.summary_tier[oldest]
```

### Integration Point

```python
# Replace existing memory in lyra-core/src/lyra_core/memory/base.py

class MemoryManager:
    def __init__(self):
        self.two_tier = TwoTierMemory(
            summary_budget=1000,
            raw_budget=10000,
            llm_client=get_llm_client()
        )
    
    def add_memory(self, content: str, metadata: Dict):
        item = MemoryItem(
            id=generate_id(),
            content=content,
            summary="",  # Will be generated
            timestamp=time.time(),
            metadata=metadata
        )
        self.two_tier.add(item)
    
    def retrieve_memories(self, query: str):
        return self.two_tier.retrieve(query)
```

**Expected Impact**: 50% token reduction, 60% latency reduction

---

## Testing Strategy

### Unit Tests

```python
# tests/test_two_tier_memory.py

def test_summary_first_retrieval():
    memory = TwoTierMemory()
    
    # Add items
    memory.add(MemoryItem(
        id="1",
        content="Long detailed content about Python...",
        summary="Python programming",
        timestamp=time.time(),
        metadata={}
    ))
    
    # Retrieve
    results = memory.retrieve("Python")
    assert len(results) > 0
    assert results[0].id == "1"

def test_escalation_to_raw_tier():
    memory = TwoTierMemory()
    
    # Add item with poor summary
    memory.add(MemoryItem(
        id="1",
        content="Detailed explanation of async/await in Python",
        summary="Programming",  # Too vague
        timestamp=time.time(),
        metadata={}
    ))
    
    # Should escalate to raw tier for specific query
    results = memory.retrieve("async await Python")
    assert len(results) > 0
```

### Integration Tests

```python
# tests/integration/test_memory_system.py

async def test_end_to_end_memory_flow():
    agent = Agent()
    
    # Execute task
    result = await agent.execute_task("Write a Python function")
    
    # Verify memory was stored
    memories = agent.memory_manager.retrieve_memories("Python function")
    assert len(memories) > 0
    
    # Verify heuristics were learned
    heuristics = agent.experiential_memory.retrieve_guidance("Write a function")
    assert len(heuristics) > 0
```

### Performance Benchmarks

```python
# tests/benchmarks/test_memory_performance.py

def benchmark_retrieval_latency():
    memory = TwoTierMemory()
    
    # Add 10k items
    for i in range(10000):
        memory.add(create_test_item(i))
    
    # Measure retrieval time
    start = time.time()
    results = memory.retrieve("test query")
    latency = time.time() - start
    
    assert latency < 0.1  # Should be under 100ms
    assert len(results) > 0

def benchmark_token_usage():
    memory = TwoTierMemory()
    
    # Add items
    for i in range(100):
        memory.add(create_test_item(i))
    
    # Measure tokens used
    results = memory.retrieve("test query")
    tokens = sum(len(r.summary.split()) for r in results)
    
    # Should use significantly fewer tokens than raw
    raw_tokens = sum(len(r.content.split()) for r in results)
    assert tokens < raw_tokens * 0.5  # At least 50% reduction
```

---

## Deployment Checklist

### Week 1: Cost-Sensitive Routing
- [ ] Implement `CostSensitiveRouter` class
- [ ] Add unit tests
- [ ] Integrate with existing memory manager
- [ ] Run benchmarks
- [ ] Deploy behind feature flag
- [ ] Monitor token usage metrics

### Week 2: Experiential Learning
- [ ] Implement `ExperientialMemory` class
- [ ] Add trajectory tracking
- [ ] Integrate with agent execution
- [ ] Add unit tests
- [ ] Run accuracy benchmarks
- [ ] Deploy to staging

### Week 3: Two-Tier Memory
- [ ] Implement `TwoTierMemory` class
- [ ] Add provenance tracking
- [ ] Migrate existing memories
- [ ] Run performance benchmarks
- [ ] Integration tests
- [ ] Gradual rollout (10% → 50% → 100%)

---

## Monitoring Metrics

### Key Metrics to Track

```python
# Add to lyra-core/src/lyra_core/monitoring/metrics.py

class MemoryMetrics:
    # Efficiency
    tokens_per_query = Histogram("memory_tokens_per_query")
    retrieval_latency = Histogram("memory_retrieval_latency_ms")
    
    # Accuracy
    retrieval_precision = Gauge("memory_retrieval_precision")
    retrieval_recall = Gauge("memory_retrieval_recall")
    
    # Usage
    store_routing_distribution = Counter("memory_store_routing", ["store"])
    tier_escalation_rate = Gauge("memory_tier_escalation_rate")
    
    # Learning
    heuristics_count = Gauge("experiential_heuristics_count")
    heuristics_usage_rate = Counter("experiential_heuristics_used")
```

### Dashboards

Create Grafana dashboards for:
1. **Memory Efficiency**: Token usage, latency, cache hit rates
2. **Memory Accuracy**: Precision, recall, escalation rates
3. **Learning Progress**: Heuristics learned, usage patterns
4. **Cost Analysis**: Token costs by store, ROI of routing

---

## Rollback Plan

If issues arise:

1. **Feature Flags**: Disable new features immediately
2. **Fallback**: Revert to previous memory system
3. **Data Migration**: Keep old and new systems parallel for 2 weeks
4. **Monitoring**: Alert on metric regressions

```python
# Feature flag configuration
ENABLE_COST_ROUTING = os.getenv("ENABLE_COST_ROUTING", "false") == "true"
ENABLE_EXPERIENTIAL_LEARNING = os.getenv("ENABLE_EXPERIENTIAL_LEARNING", "false") == "true"
ENABLE_TWO_TIER_MEMORY = os.getenv("ENABLE_TWO_TIER_MEMORY", "false") == "true"
```

---

## Success Criteria

### Week 1 Success
- ✅ Cost routing reduces token usage by 20%+
- ✅ No latency regression
- ✅ All tests passing

### Week 2 Success
- ✅ Experiential learning improves accuracy by 5%+
- ✅ Heuristics are being learned and reused
- ✅ No memory leaks

### Week 3 Success
- ✅ Two-tier memory reduces tokens by 40%+
- ✅ Latency reduced by 50%+
- ✅ Accuracy maintained or improved
- ✅ Stable under load

---

## Next Steps After Week 3

1. **Surprise-Gated Memory**: Add SAE-based memory formation
2. **Multi-Graph Structure**: Implement MAGMA-style memory
3. **RL Optimization**: Train memory policies with DAPO
4. **Thermodynamic Arbitration**: Add MARTA-style retrieval

See full roadmap in [memagent-synthesis-2026.md](./memagent-synthesis-2026.md)

---

*Quick Start Guide | Last Updated: 2026-05-29*
