# Model Router System — Detailed Design

## Data Models

### Core Data Structures

#### 1. ModelSlot (Enum)

```python
class ModelSlot(Enum):
    """Five specialized model dispatch slots."""
    NORMAL = "normal"       # General-purpose coding (Sonnet-class)
    THINKING = "thinking"   # Deep reasoning, planning (Opus-class)
    COMPACT = "compact"     # Quick lookups, simple edits (Haiku-class)
    CRITIQUE = "critique"   # Code review, verification, testing
    VLM = "vlm"             # Vision tasks, screenshots, diagrams
```

**Design Rationale**: Slots are role-based, not model-based. A slot can be fulfilled by any model that meets the capability requirements. This decouples routing logic from provider APIs.

#### 2. SlotConfig (Frozen Dataclass)

```python
@dataclass(frozen=True)
class SlotConfig:
    """Configuration for a single model slot."""
    slot: ModelSlot
    cost_multiplier: float          # Relative to NORMAL baseline (1.0)
    max_tokens: int                 # Context window ceiling
    default_temperature: float
    supports_vision: bool
    supports_extended_thinking: bool
```

**Immutability**: Frozen dataclass ensures slot configs cannot be modified at runtime, preventing accidental misconfiguration. To change a slot config, create a new router instance.

**Default Configurations**:

```python
_DEFAULT_SLOT_CONFIGS = {
    ModelSlot.NORMAL: SlotConfig(
        slot=ModelSlot.NORMAL,
        cost_multiplier=1.0,
        max_tokens=200_000,
        default_temperature=0.3,
        supports_vision=False,
        supports_extended_thinking=False,
    ),
    ModelSlot.THINKING: SlotConfig(
        slot=ModelSlot.THINKING,
        cost_multiplier=3.0,           # 3× more expensive than NORMAL
        max_tokens=200_000,
        default_temperature=0.5,        # Higher temp for creativity
        supports_vision=False,
        supports_extended_thinking=True,
    ),
    ModelSlot.COMPACT: SlotConfig(
        slot=ModelSlot.COMPACT,
        cost_multiplier=0.33,           # 1/3 cost of NORMAL
        max_tokens=200_000,
        default_temperature=0.1,        # Low temp for deterministic edits
        supports_vision=False,
        supports_extended_thinking=False,
    ),
    ModelSlot.CRITIQUE: SlotConfig(
        slot=ModelSlot.CRITIQUE,
        cost_multiplier=1.0,
        max_tokens=200_000,
        default_temperature=0.1,        # Low temp for consistent reviews
        supports_vision=False,
        supports_extended_thinking=False,
    ),
    ModelSlot.VLM: SlotConfig(
        slot=ModelSlot.VLM,
        cost_multiplier=1.5,            # 50% premium for vision
        max_tokens=200_000,
        default_temperature=0.3,
        supports_vision=True,
        supports_extended_thinking=False,
    ),
}
```

#### 3. RoutingDecision (Frozen Dataclass)

```python
@dataclass(frozen=True)
class RoutingDecision:
    """Result of model routing for a task."""
    decision_id: str                        # UUID for tracing
    task_description: str                   # First 200 chars of task
    primary_slot: ModelSlot                 # Selected slot
    fallback_slot: ModelSlot | None         # Backup if primary unavailable
    reasoning: str                          # Human-readable explanation
    estimated_cost_multiplier: float        # Relative cost estimate
    timestamp: float                        # Unix timestamp
```

**Example**:

```python
RoutingDecision(
    decision_id="rd-a3f7b2c9d1e4",
    task_description="Implement user authentication with JWT tokens",
    primary_slot=ModelSlot.NORMAL,
    fallback_slot=None,
    reasoning="Task classified as 'implement' → slot=normal (cost=1.00x).",
    estimated_cost_multiplier=1.0,
    timestamp=1735826400.0,
)
```

#### 4. SlotHealthStatus (Mutable Dataclass)

```python
@dataclass
class SlotHealthStatus:
    """Runtime health tracking for a slot."""
    slot: ModelSlot
    health: SlotHealth = SlotHealth.HEALTHY
    error_count: int = 0
    avg_latency_ms: float = 0.0
    last_error: str | None = None
    last_checked: float = field(default_factory=time.time)

    def record_success(self, latency_ms: float) -> None:
        """Update after successful execution."""
        self.avg_latency_ms = (self.avg_latency_ms * 0.7) + (latency_ms * 0.3)  # EMA
        self.error_count = max(0, self.error_count - 1)  # Decay errors
        self._recalculate_health()

    def record_error(self, error: str) -> None:
        """Update after failed execution."""
        self.error_count += 1
        self.last_error = error
        self.last_checked = time.time()
        self._recalculate_health()

    def _recalculate_health(self) -> None:
        """Determine health state from error count."""
        if self.error_count >= 5:
            self.health = SlotHealth.UNAVAILABLE
        elif self.error_count >= 2:
            self.health = SlotHealth.DEGRADED
        else:
            self.health = SlotHealth.HEALTHY
```

**Health States**:

```python
class SlotHealth(Enum):
    HEALTHY = "healthy"         # error_count < 2
    DEGRADED = "degraded"       # 2 <= error_count < 5
    UNAVAILABLE = "unavailable" # error_count >= 5
```

**Exponential Moving Average (EMA)**: Latency is tracked with α=0.3 to smooth out transient spikes while remaining responsive to sustained changes.

#### 5. ModelSpec (Intelligent Router)

```python
@dataclass(frozen=True)
class ModelSpec:
    """Specification for a model in the routing pool."""
    name: str                       # e.g., "claude-sonnet-4.6"
    provider: ModelProvider         # ANTHROPIC, OPENAI, LITELLM, etc.
    tier: ModelTier                 # REASONING, STANDARD, FAST, CHEAP
    cost_per_1k_tokens: float       # USD per 1k tokens
    latency_ms: float               # Average latency
    accuracy_estimate: float        # 0.0-1.0 quality estimate
    context_window: int = 200_000   # Max context tokens
    supports_reasoning: bool = False # Extended thinking capability
```

**Model Tiers**:

```python
class ModelTier(Enum):
    REASONING = "reasoning"  # Opus 4.7, DeepSeek-v4-pro (0.92-0.95 accuracy)
    STANDARD = "standard"    # Sonnet 4.6, GPT-5.4 (0.87-0.88 accuracy)
    FAST = "fast"            # Haiku 4.5, GPT-5.4-nano (0.78-0.80 accuracy)
    CHEAP = "cheap"          # Small local models (0.70-0.75 accuracy)
```

#### 6. TaskRequirements

```python
@dataclass(frozen=True)
class TaskRequirements:
    """Analyzed requirements for a task to be routed."""
    category: str                       # architecture, coding, review, research, lookup, execution
    complexity_score: float             # 0.0-1.0 complexity estimate
    required_capabilities: tuple[str, ...] # ("reasoning", "planning", "deep_reasoning")
```

**Capability Tags**:
- `reasoning`: Requires multi-step reasoning
- `planning`: Requires structured planning
- `design`: Requires architectural design
- `coding`: Requires code generation
- `debugging`: Requires debugging skills
- `review`: Requires code review skills
- `analysis`: Requires analytical skills
- `verification`: Requires verification skills
- `simple_query`: Simple lookup/retrieval
- `retrieval`: Information retrieval
- `execution`: Task execution
- `batch_processing`: Batch processing
- `deep_reasoning`: Complex multi-turn reasoning
- `architectural`: System-level design

#### 7. Budget

```python
@dataclass(frozen=True)
class Budget:
    """Token/cost budget for routing decisions."""
    max_cost: float                 # Maximum $ to spend
    max_tokens: int                 # Maximum tokens to use
    spent_cost: float = 0.0         # Cumulative cost
    spent_tokens: int = 0           # Cumulative tokens

    @property
    def remaining_cost(self) -> float:
        return max(0.0, self.max_cost - self.spent_cost)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.spent_tokens)

    @property
    def cost_exhausted(self) -> bool:
        return self.spent_cost >= self.max_cost

    @property
    def tokens_exhausted(self) -> bool:
        return self.spent_tokens >= self.max_tokens
```

**Usage Pattern**:

```python
budget = Budget(max_cost=5.0, max_tokens=100_000)
decision = router.route(query, budget=budget)
# ... execute ...
budget = replace(budget, spent_cost=budget.spent_cost + actual_cost,
                         spent_tokens=budget.spent_tokens + actual_tokens)
```

## Algorithms

### 1. Task Classification Algorithm

**Purpose**: Map natural language task descriptions to model slots.

**Implementation**:

```python
# Priority-ordered keyword matching (checked in order)
_PRIORITY_KEYWORDS = (
    # VLM keywords (highest priority — overrides other matches)
    ("screenshot", ModelSlot.VLM),
    ("image", ModelSlot.VLM),
    ("vision", ModelSlot.VLM),
    ("diagram", ModelSlot.VLM),
    ("ui_review", ModelSlot.VLM),
    
    # COMPACT keywords
    ("fix_typo", ModelSlot.COMPACT),
    ("lookup", ModelSlot.COMPACT),
    ("quick", ModelSlot.COMPACT),
    ("simple", ModelSlot.COMPACT),
    ("edit", ModelSlot.COMPACT),
    
    # THINKING keywords
    ("architect", ModelSlot.THINKING),
    ("design", ModelSlot.THINKING),
    ("plan", ModelSlot.THINKING),
    ("research", ModelSlot.THINKING),
    ("analyze", ModelSlot.THINKING),
    
    # CRITIQUE keywords
    ("test", ModelSlot.CRITIQUE),
    ("review", ModelSlot.CRITIQUE),
    ("verify", ModelSlot.CRITIQUE),
    
    # NORMAL keywords (default)
    ("implement", ModelSlot.NORMAL),
    ("refactor", ModelSlot.NORMAL),
    ("debug", ModelSlot.NORMAL),
)

def classify_task_type(task: str) -> str:
    """Map a task description to a canonical task type."""
    task_lower = task.lower()
    for keyword, _ in _PRIORITY_KEYWORDS:
        if keyword in task_lower:
            return keyword
    return "implement"  # Default to NORMAL slot
```

**Algorithm Properties**:
- **Time complexity**: O(n) where n = number of keywords (constant, ~20)
- **Space complexity**: O(1)
- **Deterministic**: Same input always produces same output
- **Fast**: <0.1ms on typical hardware

**Example Classifications**:

| Task | Matched Keyword | Slot |
|------|----------------|------|
| "Review this code for security issues" | "review" | CRITIQUE |
| "Quick typo fix in README" | "quick" | COMPACT |
| "Design a scalable microservice architecture" | "design" | THINKING |
| "Analyze this screenshot for UI bugs" | "screenshot" | VLM |
| "Implement user authentication" | "implement" | NORMAL |

### 2. Cost-Aware Slot Selection

**Purpose**: Respect budget constraints while maximizing capability.

```python
def route(task: str, budget_multiplier: float | None) -> RoutingDecision:
    # 1. Classify task to get ideal slot
    task_type = classify_task_type(task)
    primary_slot = _TASK_TYPE_MAP[task_type]
    
    # 2. Check if slot exceeds budget
    if budget_multiplier is not None:
        config = slot_configs[primary_slot]
        if config.cost_multiplier > budget_multiplier:
            # 3. Find cheapest slot within budget
            for slot in _COST_AWARE_SLOT_ORDER:  # COMPACT < NORMAL < CRITIQUE < VLM < THINKING
                if slot_configs[slot].cost_multiplier <= budget_multiplier:
                    hs = health_status.get(slot, SlotHealthStatus(slot))
                    if hs.health != SlotHealth.UNAVAILABLE:
                        primary_slot = slot
                        break
    
    return RoutingDecision(primary_slot=primary_slot, ...)
```

**Cost-Aware Slot Ordering**:

```python
_COST_AWARE_SLOT_ORDER = (
    ModelSlot.COMPACT,    # 0.33× (cheapest)
    ModelSlot.NORMAL,     # 1.0×
    ModelSlot.CRITIQUE,   # 1.0×
    ModelSlot.VLM,        # 1.5×
    ModelSlot.THINKING,   # 3.0× (most expensive)
)
```

### 3. Fallback Selection Algorithm

**Purpose**: Find the best alternative when primary slot is unavailable.

```python
def find_fallback(
    primary: ModelSlot,
    health: dict[ModelSlot, SlotHealthStatus],
) -> ModelSlot | None:
    """Find the cheapest healthy alternative to the primary slot."""
    # Try cheaper slots first (cost optimization)
    primary_idx = _COST_AWARE_SLOT_ORDER.index(primary)
    for slot in _COST_AWARE_SLOT_ORDER[primary_idx + 1:]:
        if health.get(slot, SlotHealthStatus(slot)).health != SlotHealth.UNAVAILABLE:
            return slot
    
    # Try more expensive slots (availability over cost)
    for slot in _COST_AWARE_SLOT_ORDER[:primary_idx]:
        if health.get(slot, SlotHealthStatus(slot)).health != SlotHealth.UNAVAILABLE:
            return slot
    
    # No healthy slots available
    return None
```

**Fallback Strategy**:
1. Try cheaper slots first (cost-conscious degradation)
2. If no cheaper slots, try more expensive slots (availability over cost)
3. If all slots unavailable, return None (caller handles via hardcoded default)

**Example**:
- Primary: THINKING (3.0×)
- Health: THINKING=UNAVAILABLE, NORMAL=HEALTHY, COMPACT=HEALTHY
- Fallback search order: [VLM, CRITIQUE, NORMAL, COMPACT]
- First healthy: NORMAL (1.0×)
- Result: Fallback to NORMAL slot (save 2.0× cost)

### 4. Multi-Turn Routing Algorithm

**Purpose**: Escalate to stronger models when conversation history indicates complexity.

```python
def _multi_turn_route(query: str, candidates: list[ModelSpec]) -> RoutingDecision:
    """Route considering conversation history."""
    # 1. Aggregate history metrics
    context_tokens = sum(turn.history_tokens for turn in turn_history)
    avg_complexity = sum(turn.estimated_complexity for turn in turn_history) / len(turn_history)
    
    # 2. Escalation condition: high complexity OR large context
    if avg_complexity > 0.7 or context_tokens > 50_000:
        # Escalate to reasoning tier
        reasoning_models = [m for m in candidates if m.supports_reasoning]
        if reasoning_models:
            best = max(reasoning_models, key=lambda m: m.accuracy_estimate)
            return make_decision(best, RoutingStrategy.MULTI_TURN, avg_complexity, query)
    
    # 3. Default to standard/fast tier
    standard_models = [m for m in candidates if m.tier in (ModelTier.STANDARD, ModelTier.FAST)]
    if standard_models:
        best = min(standard_models, key=lambda m: m.cost_per_1k_tokens)
        return make_decision(best, RoutingStrategy.MULTI_TURN, avg_complexity, query)
    
    # 4. Ultimate fallback
    return make_decision(fallback_model(), RoutingStrategy.MULTI_TURN, avg_complexity, query)
```

**Escalation Triggers**:
- **High complexity**: `avg_complexity > 0.7` (70th percentile)
- **Large context**: `context_tokens > 50,000` (25% of 200k window)

**Design Rationale**: Multi-turn conversations that remain simple should use cheap models. Only escalate when accumulated evidence suggests the task is complex.

### 5. Complexity Estimation Algorithm

**Purpose**: Quantify task difficulty on a 0.0-1.0 scale.

```python
def compute_complexity(description: str, context_tokens: int, tools_required: int) -> float:
    """Compute complexity score from multiple factors."""
    # Length factor (0.0-0.4): longer descriptions suggest complexity
    length_score = min(1.0, len(description) / 500.0) * 0.4
    
    # Context factor (0.0-0.3): more context suggests complexity
    context_score = min(1.0, context_tokens / 100_000.0) * 0.3
    
    # Tools factor (0.0-0.3): more tools suggests complexity
    tools_score = min(1.0, tools_required / 5.0) * 0.3
    
    # Combine and clamp
    raw = length_score + context_score + tools_score
    return round(min(1.0, raw), 4)
```

**Scoring Weights**:
- **Length** (40%): Descriptions >500 chars → complexity score ≥0.4
- **Context** (30%): Context >100k tokens → complexity score ≥0.3
- **Tools** (30%): Requiring >5 tools → complexity score ≥0.3

**Example Complexities**:

| Task | Length | Context | Tools | Score | Interpretation |
|------|--------|---------|-------|-------|----------------|
| "Fix typo in README" | 20 chars | 1k | 0 | 0.03 | Trivial |
| "Implement user login" | 25 chars | 5k | 2 | 0.14 | Simple |
| "Design a microservice architecture..." | 150 chars | 20k | 3 | 0.30 | Moderate |
| "Refactor entire codebase for async..." | 500 chars | 80k | 5 | 0.94 | Complex |

## APIs

### Public Router API

#### ModelRouter

```python
class ModelRouter:
    """5-slot model router with health tracking."""
    
    def __init__(
        self,
        slot_configs: dict[ModelSlot, SlotConfig] | None = None,
        health_status: dict[ModelSlot, SlotHealthStatus] | None = None,
    ):
        """Initialize router with optional custom configs."""
        ...
    
    def route(
        self,
        task: str,
        *,
        budget_multiplier: float | None = None,
        require_vision: bool = False,
        require_thinking: bool = False,
        preferred_slot: ModelSlot | None = None,
    ) -> RoutingDecision:
        """Route a task to the optimal slot.
        
        Args:
            task: Natural language task description
            budget_multiplier: Max cost multiplier (None = no limit)
            require_vision: Force VLM slot
            require_thinking: Force THINKING slot
            preferred_slot: User override (bypasses auto-classification)
        
        Returns:
            RoutingDecision with selected slot and reasoning
        """
        ...
    
    def record_slot_result(
        self,
        slot: ModelSlot,
        success: bool,
        latency_ms: float = 0.0,
        error: str | None = None,
    ) -> None:
        """Update slot health after execution."""
        ...
    
    def get_healthy_slots(self) -> tuple[ModelSlot, ...]:
        """Return all currently healthy or degraded slots."""
        ...
    
    def get_cost_estimate(self, task: str) -> float:
        """Estimate relative cost without creating a decision."""
        ...
    
    @property
    def history(self) -> tuple[RoutingDecision, ...]:
        """Get all routing decisions made by this router."""
        ...
    
    def reset_health(self) -> None:
        """Reset all slot health to HEALTHY."""
        ...
```

#### IntelligentModelRouter

```python
class IntelligentModelRouter:
    """Multi-tier model router with budget enforcement."""
    
    def __init__(self, models: tuple[ModelSpec, ...] | None = None):
        """Initialize with optional custom model pool."""
        ...
    
    def route(
        self,
        query: str,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        budget: Budget | None = None,
        complexity: float = 0.5,
        is_reasoning: bool = False,
    ) -> RoutingDecision:
        """Route query to best model given constraints."""
        ...
    
    def select_tier(
        self,
        required_reliability: float,
        cost_budget: float | None = None,
        is_reasoning: bool = False,
    ) -> ModelSpec:
        """Select cheapest model meeting reliability threshold."""
        ...
    
    def record_turn(self, turn: TurnContext) -> None:
        """Record a turn for multi-turn routing."""
        ...
    
    def snapshot(self) -> RouterSnapshot:
        """Get current router statistics."""
        ...
    
    def add_model(self, model: ModelSpec) -> None:
        """Add a model to the routing pool."""
        ...
    
    def remove_model(self, name: str) -> bool:
        """Remove a model from the pool."""
        ...
    
    @property
    def model_count(self) -> int:
        """Number of models in pool."""
        ...
    
    @property
    def decision_count(self) -> int:
        """Total routing decisions made."""
        ...
    
    @property
    def turn_count(self) -> int:
        """Total turns recorded."""
        ...
```

#### CapabilityAnalyzer

```python
class CapabilityAnalyzer:
    """Analyze task requirements for routing."""
    
    async def analyze_task(
        self,
        description: str,
        context_tokens: int = 0,
        tools_required: int = 0,
    ) -> TaskRequirements:
        """Analyze a task and return routing requirements."""
        ...
```

## State Management

### Router State

**Stateful Components**:
1. **Slot health**: Mutable per-slot error counts and latency averages
2. **Routing history**: Append-only list of decisions
3. **Multi-turn history**: Append-only list of turn contexts

**State Lifecycle**:

```python
# 1. Initialization
router = ModelRouter()  # All slots start HEALTHY, empty history

# 2. Routing decisions append to history
decision = router.route("Implement login")
assert len(router.history) == 1

# 3. Execution updates slot health
router.record_slot_result(ModelSlot.NORMAL, success=True, latency_ms=320)

# 4. Health degrades on errors
router.record_slot_result(ModelSlot.NORMAL, success=False, error="API timeout")
router.record_slot_result(ModelSlot.NORMAL, success=False, error="Rate limit")
assert router.health_status[ModelSlot.NORMAL].health == SlotHealth.DEGRADED

# 5. Health recovers on success
router.record_slot_result(ModelSlot.NORMAL, success=True, latency_ms=310)
assert router.health_status[ModelSlot.NORMAL].health == SlotHealth.HEALTHY

# 6. Manual reset if needed
router.reset_health()  # All slots → HEALTHY
```

### State Persistence

**V1 Design**: No automatic persistence. Router state lives in memory.

**Rationale**: Routing decisions are fast (<1ms) and stateless. Re-routing on restart is acceptable. Health recovers naturally within minutes.

**V2 Consideration**: Persist health status to `.lyra/state/router_health.json` to avoid cold-start degradation after restarts.

## Scalability Considerations

### Memory Scalability

**Per-Router Overhead**:
- Slot configs: 5 slots × 80 bytes = 400 bytes
- Health status: 5 slots × 100 bytes = 500 bytes
- History: N decisions × 250 bytes = 250N bytes

**Growth Rate**: Linear with decisions. After 10,000 decisions → 2.5 MB.

**Mitigation**:
1. **History pruning**: Keep only last 1,000 decisions (configurable)
2. **Circular buffer**: Replace list with ring buffer for O(1) memory
3. **Separate persistence**: Write history to disk, keep only recent in memory

### Throughput Scalability

**Single Router**: Thread-safe for reads (immutable decisions), but writes to health status require locking.

**Design**:

```python
class ModelRouter:
    def __init__(self):
        self._health_lock = threading.Lock()
        self._history_lock = threading.Lock()
    
    def record_slot_result(self, slot, success, latency_ms, error):
        with self._health_lock:
            # Update health (mutable state)
            ...
    
    def route(self, task, **kwargs):
        # Read-only access to health (no lock needed)
        decision = ...
        with self._history_lock:
            self._history.append(decision)
        return decision
```

**Performance**: Contention only on health updates (post-execution). Routing path is lock-free.

### Distributed Routing

**V2 Design**: Shared health status across multiple router instances.

**Architecture**:

```python
class DistributedModelRouter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.local_router = ModelRouter()
    
    def route(self, task):
        # 1. Fetch global health from Redis
        global_health = self._fetch_global_health()
        
        # 2. Merge with local health
        merged_health = self._merge_health(global_health, self.local_router.health_status)
        
        # 3. Route with merged health
        decision = self.local_router.route(task, health_override=merged_health)
        
        return decision
    
    def record_slot_result(self, slot, success, latency_ms, error):
        # Update local health
        self.local_router.record_slot_result(slot, success, latency_ms, error)
        
        # Publish to Redis for global visibility
        self._publish_health_update(slot, self.local_router.health_status[slot])
```

**Trade-off**: Adds Redis dependency and 1-2ms latency. Only needed for multi-instance deployments (v2 scope).

## Reliability & Error Handling

### Error Scenarios

| Scenario | Handling | Example |
|----------|----------|---------|
| All slots unavailable | Return hardcoded default (Sonnet 4.6) | Provider outage across all slots |
| Primary slot unavailable | Fallback to next cheapest healthy slot | Anthropic API down → route to OpenAI |
| No models in budget | Use cheapest available model | Budget=0.5×, all models >0.5× → use COMPACT |
| Invalid task description | Default to NORMAL slot | Empty string, non-ASCII characters |
| Health corruption | Reset health to HEALTHY | Health desync after crash |

### Idempotency

**Routing**: Not idempotent. Calling `route("same task")` twice creates two decisions with different timestamps/IDs.

**Health Updates**: Idempotent within 1-second window. Duplicate success/error reports within 1s are deduplicated.

### Crash Recovery

**Assumptions**:
1. Router state is ephemeral (no persistence in v1)
2. All slots start HEALTHY after restart
3. Cold-start: First 5-10 requests may hit unhealthy slots before health converges

**Mitigation**: Implement health persistence (v2) to avoid cold-start errors.

---

**References**:
- [Architecture](architecture.md) — System overview and integration points
- [Tradeoffs](tradeoffs.md) — Design decision rationale
- [Implementation](implementation.md) — Code examples and deployment
