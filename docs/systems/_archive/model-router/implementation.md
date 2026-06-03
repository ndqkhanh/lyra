# Model Router System — Implementation Guide

## Quick Start

### Basic Usage

```python
from lyra_core.orchestration.model_router import ModelRouter, ModelSlot

# 1. Initialize router with defaults
router = ModelRouter()

# 2. Route a task
decision = router.route("Implement user authentication with JWT")

# 3. Execute with selected slot (Gateway resolves to concrete model)
model = gateway.resolve_model(decision.primary_slot)
result = model.invoke(task)

# 4. Record result for health tracking
router.record_slot_result(
    slot=decision.primary_slot,
    success=True,
    latency_ms=325.7
)
```

### With Budget Constraints

```python
# Route with cost constraint
decision = router.route(
    "Quick typo fix in README",
    budget_multiplier=0.5  # Max 0.5× NORMAL cost
)
# Result: Routes to COMPACT slot (0.33× cost)
```

### With Explicit Requirements

```python
# Force vision model
decision = router.route(
    "Analyze this screenshot for UI bugs",
    require_vision=True
)
# Result: Routes to VLM slot

# Force reasoning model
decision = router.route(
    "Design a distributed consensus algorithm",
    require_thinking=True
)
# Result: Routes to THINKING slot
```

### Multi-Turn Routing

```python
from lyra_model_router.router_v2 import IntelligentModelRouter, TurnContext, RoutingStrategy

router = IntelligentModelRouter()

# Record conversation turns
for i, query in enumerate(conversation):
    turn_ctx = TurnContext(
        turn_index=i,
        query=query,
        history_tokens=sum(t.tokens for t in history),
        estimated_complexity=estimate_complexity(query)
    )
    router.record_turn(turn_ctx)

# Route with multi-turn strategy (auto-escalates if complex)
decision = router.route(
    query="Explain the architecture",
    strategy=RoutingStrategy.MULTI_TURN
)
```

## Installation & Configuration

### Prerequisites

```bash
# Python 3.11+
python --version  # Python 3.11.0 or higher

# No external dependencies for core router
# Optional: LiteLLM for multi-provider support
pip install litellm
```

### Package Structure

```
lyra/
├── packages/
│   ├── lyra-core/
│   │   └── src/lyra_core/orchestration/
│   │       └── model_router.py          # 5-slot router
│   └── lyra-model-router/
│       └── src/lyra_model_router/
│           ├── router_v2.py              # Intelligent multi-tier router
│           ├── models_v2.py              # Data models
│           ├── capability_analyzer.py    # Task analysis
│           ├── complexity_estimator.py   # Complexity scoring
│           ├── cost_optimizer.py         # Cost optimization
│           ├── usage_tracker.py          # Usage tracking
│           └── performance_history.py    # Performance metrics
```

### Configuration Files

**1. Router Configuration** (`.lyra/config.yaml`):

```yaml
model_router:
  # Slot configurations
  slots:
    normal:
      cost_multiplier: 1.0
      max_tokens: 200000
      default_temperature: 0.3
      supports_vision: false
      supports_extended_thinking: false
    
    thinking:
      cost_multiplier: 3.0
      max_tokens: 200000
      default_temperature: 0.5
      supports_vision: false
      supports_extended_thinking: true
    
    compact:
      cost_multiplier: 0.33
      max_tokens: 200000
      default_temperature: 0.1
      supports_vision: false
      supports_extended_thinking: false
    
    critique:
      cost_multiplier: 1.0
      max_tokens: 200000
      default_temperature: 0.1
      supports_vision: false
      supports_extended_thinking: false
    
    vlm:
      cost_multiplier: 1.5
      max_tokens: 200000
      default_temperature: 0.3
      supports_vision: true
      supports_extended_thinking: false
  
  # Health tracking
  health:
    error_threshold_degraded: 2
    error_threshold_unavailable: 5
    latency_ema_alpha: 0.3
  
  # Routing behavior
  routing:
    default_strategy: balanced
    multi_turn_complexity_threshold: 0.7
    multi_turn_token_threshold: 50000
```

**2. Model Pool Configuration** (`.lyra/models.yaml`):

```yaml
models:
  - name: claude-opus-4.7
    provider: anthropic
    tier: reasoning
    cost_per_1k_tokens: 0.015
    latency_ms: 800
    accuracy_estimate: 0.95
    context_window: 200000
    supports_reasoning: true
    slots: [thinking]
  
  - name: claude-sonnet-4.6
    provider: anthropic
    tier: standard
    cost_per_1k_tokens: 0.003
    latency_ms: 300
    accuracy_estimate: 0.88
    context_window: 200000
    supports_reasoning: false
    slots: [normal, critique]
  
  - name: claude-haiku-4.5
    provider: anthropic
    tier: fast
    cost_per_1k_tokens: 0.001
    latency_ms: 100
    accuracy_estimate: 0.80
    context_window: 200000
    supports_reasoning: false
    slots: [compact]
  
  - name: claude-3.5-sonnet
    provider: anthropic
    tier: standard
    cost_per_1k_tokens: 0.003
    latency_ms: 350
    accuracy_estimate: 0.86
    context_window: 200000
    supports_reasoning: false
    supports_vision: true
    slots: [vlm]
  
  - name: deepseek-v4-pro
    provider: litellm
    tier: reasoning
    cost_per_1k_tokens: 0.008
    latency_ms: 700
    accuracy_estimate: 0.92
    context_window: 200000
    supports_reasoning: true
    slots: [thinking]
  
  - name: deepseek-v4-flash
    provider: litellm
    tier: cheap
    cost_per_1k_tokens: 0.0005
    latency_ms: 80
    accuracy_estimate: 0.75
    context_window: 200000
    supports_reasoning: false
    slots: [compact]
```

## Code Examples

### Example 1: Basic Gateway Integration

```python
from lyra_core.orchestration.model_router import ModelRouter, ModelSlot
from lyra_core.providers import build_llm
import logging

logger = logging.getLogger(__name__)

class Gateway:
    def __init__(self, config):
        self.router = ModelRouter()
        self.config = config
        self._model_cache = {}
    
    def execute_task(self, task: str, budget_multiplier: float | None = None):
        # 1. Route to optimal slot
        decision = self.router.route(task, budget_multiplier=budget_multiplier)
        
        logger.info(
            f"Routing decision: {decision.primary_slot.value}",
            extra={
                "decision_id": decision.decision_id,
                "reasoning": decision.reasoning,
                "cost_multiplier": decision.estimated_cost_multiplier,
            }
        )
        
        # 2. Resolve slot to concrete model
        model = self._resolve_model(decision.primary_slot)
        
        # 3. Execute with primary model
        start_time = time.time()
        try:
            result = model.invoke(task)
            latency_ms = (time.time() - start_time) * 1000
            
            # Record success
            self.router.record_slot_result(
                slot=decision.primary_slot,
                success=True,
                latency_ms=latency_ms
            )
            
            return result
        
        except Exception as e:
            # Record error
            self.router.record_slot_result(
                slot=decision.primary_slot,
                success=False,
                error=str(e)
            )
            
            # Try fallback if available
            if decision.fallback_slot:
                logger.warning(
                    f"Primary slot failed, trying fallback: {decision.fallback_slot.value}",
                    extra={"error": str(e)}
                )
                model = self._resolve_model(decision.fallback_slot)
                return model.invoke(task)
            
            raise
    
    def _resolve_model(self, slot: ModelSlot):
        """Resolve slot to concrete model."""
        # Check cache
        if slot in self._model_cache:
            return self._model_cache[slot]
        
        # Map slot to model based on config
        slot_to_model = {
            ModelSlot.NORMAL: "claude-sonnet-4.6",
            ModelSlot.THINKING: "claude-opus-4.7",
            ModelSlot.COMPACT: "claude-haiku-4.5",
            ModelSlot.CRITIQUE: "claude-sonnet-4.6",
            ModelSlot.VLM: "claude-3.5-sonnet",
        }
        
        model_name = slot_to_model[slot]
        model = build_llm(model_name, **self.config.model_kwargs)
        
        # Cache for reuse
        self._model_cache[slot] = model
        
        return model
```

### Example 2: Agent Loop with Multi-Turn Routing

```python
from lyra_model_router.router_v2 import (
    IntelligentModelRouter,
    TurnContext,
    RoutingStrategy,
    Budget,
)
from dataclasses import replace

class AgentLoop:
    def __init__(self, budget: Budget):
        self.router = IntelligentModelRouter()
        self.budget = budget
        self.history = []
    
    def run_turn(self, query: str):
        # 1. Record turn context
        turn_ctx = TurnContext(
            turn_index=len(self.history),
            query=query,
            history_tokens=sum(h.tokens for h in self.history),
            estimated_complexity=self._estimate_complexity(query),
            is_reasoning_task=self._is_reasoning_task(query),
        )
        self.router.record_turn(turn_ctx)
        
        # 2. Route with multi-turn strategy
        decision = self.router.route(
            query=query,
            strategy=RoutingStrategy.MULTI_TURN,
            budget=self.budget,
            complexity=turn_ctx.estimated_complexity,
            is_reasoning=turn_ctx.is_reasoning_task,
        )
        
        # 3. Check budget
        if self.budget.cost_exhausted:
            raise RuntimeError("Budget exhausted")
        
        # 4. Execute with selected model
        model = self._get_model(decision.model.name)
        result = model.invoke(query)
        
        # 5. Update budget
        actual_cost = self._calculate_cost(result)
        actual_tokens = result.usage.total_tokens
        self.budget = replace(
            self.budget,
            spent_cost=self.budget.spent_cost + actual_cost,
            spent_tokens=self.budget.spent_tokens + actual_tokens,
        )
        
        # 6. Record history
        self.history.append({
            "query": query,
            "result": result,
            "tokens": actual_tokens,
            "cost": actual_cost,
        })
        
        return result
    
    def _estimate_complexity(self, query: str) -> float:
        # Simple heuristic: length-based
        return min(1.0, len(query) / 500.0)
    
    def _is_reasoning_task(self, query: str) -> bool:
        reasoning_keywords = ["design", "architect", "plan", "analyze", "research"]
        return any(kw in query.lower() for kw in reasoning_keywords)
    
    def _get_model(self, model_name: str):
        # Model resolution logic
        ...
    
    def _calculate_cost(self, result) -> float:
        # Cost calculation based on token usage
        ...
```

### Example 3: Subagent Orchestration

```python
from lyra_core.orchestration.model_router import ModelRouter, ModelSlot
import concurrent.futures

class SubagentOrchestrator:
    def __init__(self, main_router: ModelRouter):
        self.main_router = main_router
    
    def spawn_parallel_tasks(self, tasks: list[str]):
        """Spawn multiple subagents with independent routing."""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self._execute_subagent_task, task)
                for task in tasks
            ]
            
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        return results
    
    def _execute_subagent_task(self, task: str):
        # Clone router state for subagent (independent health tracking)
        subagent_router = self._clone_router(self.main_router)
        
        # Route with lower budget (subagents use cheaper models)
        decision = subagent_router.route(
            task,
            budget_multiplier=0.5  # Force cheaper slots
        )
        
        # Execute
        model = self._resolve_model(decision.primary_slot)
        result = model.invoke(task)
        
        # Update health (isolated from main router)
        subagent_router.record_slot_result(
            slot=decision.primary_slot,
            success=True,
            latency_ms=result.latency_ms
        )
        
        return result
    
    def _clone_router(self, router: ModelRouter) -> ModelRouter:
        """Create independent router with same config."""
        return ModelRouter(
            slot_configs=dict(router.slot_configs),
            health_status={}  # Fresh health state
        )
    
    def _resolve_model(self, slot: ModelSlot):
        ...
```

### Example 4: Custom Slot Configuration

```python
from lyra_core.orchestration.model_router import (
    ModelRouter,
    ModelSlot,
    SlotConfig,
)

# Custom slot configs for cost-sensitive deployment
custom_configs = {
    ModelSlot.NORMAL: SlotConfig(
        slot=ModelSlot.NORMAL,
        cost_multiplier=1.0,
        max_tokens=100_000,  # Reduced context
        default_temperature=0.2,  # Lower temp
        supports_vision=False,
        supports_extended_thinking=False,
    ),
    ModelSlot.THINKING: SlotConfig(
        slot=ModelSlot.THINKING,
        cost_multiplier=2.0,  # Cheaper than default 3.0×
        max_tokens=150_000,
        default_temperature=0.4,
        supports_vision=False,
        supports_extended_thinking=True,
    ),
    # ... other slots
}

router = ModelRouter(slot_configs=custom_configs)
```

### Example 5: Health Monitoring & Alerts

```python
from lyra_core.orchestration.model_router import ModelRouter, SlotHealth
import logging

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.alert_threshold = SlotHealth.DEGRADED
    
    def check_health(self):
        """Check slot health and emit alerts."""
        unhealthy_slots = []
        
        for slot, status in self.router.health_status.items():
            if status.health == SlotHealth.UNAVAILABLE:
                logger.critical(
                    f"Slot {slot.value} is UNAVAILABLE",
                    extra={
                        "error_count": status.error_count,
                        "last_error": status.last_error,
                        "avg_latency_ms": status.avg_latency_ms,
                    }
                )
                unhealthy_slots.append(slot)
            
            elif status.health == SlotHealth.DEGRADED:
                logger.warning(
                    f"Slot {slot.value} is DEGRADED",
                    extra={
                        "error_count": status.error_count,
                        "avg_latency_ms": status.avg_latency_ms,
                    }
                )
        
        return unhealthy_slots
    
    def auto_reset_if_needed(self):
        """Reset health if all slots are unavailable."""
        healthy_slots = self.router.get_healthy_slots()
        
        if not healthy_slots:
            logger.critical("All slots unavailable, resetting health")
            self.router.reset_health()
            return True
        
        return False
```

## Deployment

### Development Environment

```bash
# 1. Install Lyra in editable mode
cd lyra/
pip install -e packages/lyra-core
pip install -e packages/lyra-model-router

# 2. Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export DEEPSEEK_API_KEY="sk-..."

# 3. Run tests
pytest packages/lyra-model-router/tests/
```

### Production Deployment

**1. Containerized Deployment** (Docker):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Lyra packages
COPY packages/lyra-core/ /app/lyra-core/
COPY packages/lyra-model-router/ /app/lyra-model-router/
RUN pip install /app/lyra-core /app/lyra-model-router

# Copy config
COPY .lyra/config.yaml /app/.lyra/config.yaml
COPY .lyra/models.yaml /app/.lyra/models.yaml

# Environment variables (use secrets manager in prod)
ENV ANTHROPIC_API_KEY=""
ENV OPENAI_API_KEY=""
ENV DEEPSEEK_API_KEY=""

# Run gateway
CMD ["python", "-m", "lyra_core.gateway"]
```

**2. Kubernetes Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lyra-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lyra-gateway
  template:
    metadata:
      labels:
        app: lyra-gateway
    spec:
      containers:
      - name: gateway
        image: lyra-gateway:latest
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: lyra-secrets
              key: anthropic-api-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: lyra-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
```

**3. Health Check Endpoint**:

```python
from fastapi import FastAPI
from lyra_core.orchestration.model_router import SlotHealth

app = FastAPI()

@app.get("/health")
def health_check():
    """Liveness probe."""
    return {"status": "healthy"}

@app.get("/ready")
def readiness_check():
    """Readiness probe (checks slot health)."""
    unhealthy = [
        slot.value
        for slot, status in gateway.router.health_status.items()
        if status.health == SlotHealth.UNAVAILABLE
    ]
    
    if unhealthy:
        return {"status": "degraded", "unhealthy_slots": unhealthy}, 503
    
    return {"status": "ready"}
```

## Integration Patterns

### Pattern 1: Router as Singleton

```python
# gateway.py
from lyra_core.orchestration.model_router import ModelRouter

# Global singleton router (shared across all sessions)
_router = None

def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
```

**Use Case**: Single-process deployment, shared health state across sessions.

### Pattern 2: Router per Session

```python
# session.py
class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.router = ModelRouter()  # Independent router per session
        self.budget = Budget(max_cost=5.0, max_tokens=100_000)
```

**Use Case**: Isolated routing decisions per user session, independent health tracking.

### Pattern 3: Layered Routing

```python
# Combine 5-slot router (Gateway) with intelligent router (Agent Loop)
class HybridGateway:
    def __init__(self):
        self.slot_router = ModelRouter()  # Fast slot selection
        self.intelligent_router = IntelligentModelRouter()  # Multi-turn logic
    
    def execute_task(self, task: str, is_multi_turn: bool = False):
        if is_multi_turn:
            # Use intelligent router for conversations
            decision = self.intelligent_router.route(
                task,
                strategy=RoutingStrategy.MULTI_TURN
            )
            return self._execute_with_model(decision.model.name, task)
        else:
            # Use slot router for one-off tasks
            decision = self.slot_router.route(task)
            return self._execute_with_slot(decision.primary_slot, task)
```

**Use Case**: Best-of-both-worlds routing.

### Pattern 4: Provider Load Balancing

```python
# Distribute load across multiple providers for same slot
class LoadBalancedRouter:
    def __init__(self):
        self.router = ModelRouter()
        self.provider_pool = {
            ModelSlot.NORMAL: [
                "claude-sonnet-4.6",
                "gpt-5.4",
                "deepseek-v4-flash",
            ]
        }
        self.round_robin_idx = 0
    
    def resolve_model(self, slot: ModelSlot):
        models = self.provider_pool[slot]
        model = models[self.round_robin_idx % len(models)]
        self.round_robin_idx += 1
        return model
```

**Use Case**: Distribute load, avoid rate limits on single provider.

## Testing Strategies

### Unit Tests

```python
import pytest
from lyra_core.orchestration.model_router import (
    ModelRouter,
    ModelSlot,
    SlotHealth,
)

def test_route_basic_task():
    router = ModelRouter()
    decision = router.route("Implement user login")
    
    assert decision.primary_slot == ModelSlot.NORMAL
    assert decision.fallback_slot is None
    assert decision.estimated_cost_multiplier == 1.0

def test_route_with_budget_constraint():
    router = ModelRouter()
    decision = router.route("Quick typo fix", budget_multiplier=0.5)
    
    assert decision.primary_slot == ModelSlot.COMPACT
    assert decision.estimated_cost_multiplier == 0.33

def test_health_degradation():
    router = ModelRouter()
    
    # Record 2 errors
    router.record_slot_result(ModelSlot.NORMAL, success=False, error="Timeout")
    router.record_slot_result(ModelSlot.NORMAL, success=False, error="Rate limit")
    
    # Slot should be DEGRADED
    assert router.health_status[ModelSlot.NORMAL].health == SlotHealth.DEGRADED

def test_health_recovery():
    router = ModelRouter()
    
    # Degrade slot
    router.record_slot_result(ModelSlot.NORMAL, success=False, error="Error")
    router.record_slot_result(ModelSlot.NORMAL, success=False, error="Error")
    
    # Record success
    router.record_slot_result(ModelSlot.NORMAL, success=True, latency_ms=300)
    
    # Error count should decrement
    assert router.health_status[ModelSlot.NORMAL].error_count == 1

def test_fallback_selection():
    router = ModelRouter()
    
    # Mark THINKING slot as unavailable
    for _ in range(5):
        router.record_slot_result(ModelSlot.THINKING, success=False, error="Error")
    
    # Route to THINKING task
    decision = router.route("Design a system architecture")
    
    # Should fallback to cheaper slot
    assert decision.fallback_slot is not None
    assert decision.primary_slot != ModelSlot.THINKING
```

### Integration Tests

```python
import pytest
from lyra_core.gateway import Gateway
from lyra_core.providers import MockLLM

@pytest.fixture
def gateway():
    return Gateway(config=MockConfig())

def test_end_to_end_routing(gateway):
    # Execute task through gateway
    result = gateway.execute_task("Implement login feature")
    
    # Verify routing occurred
    assert len(gateway.router.history) == 1
    assert gateway.router.history[0].primary_slot == ModelSlot.NORMAL
    
    # Verify health updated
    assert gateway.router.health_status[ModelSlot.NORMAL].error_count == 0

def test_fallback_on_error(gateway):
    # Inject error in primary slot
    gateway._inject_error(ModelSlot.NORMAL, "API timeout")
    
    # Execute task
    result = gateway.execute_task("Implement feature")
    
    # Verify fallback occurred
    decision = gateway.router.history[-1]
    assert decision.fallback_slot is not None
```

### Performance Tests

```python
import time
import pytest

def test_routing_latency():
    router = ModelRouter()
    
    # Warm up
    for _ in range(10):
        router.route("Test task")
    
    # Measure routing latency
    start = time.time()
    for _ in range(1000):
        router.route("Implement user authentication")
    end = time.time()
    
    avg_latency_ms = (end - start) / 1000 * 1000
    assert avg_latency_ms < 1.0, f"Routing too slow: {avg_latency_ms:.2f}ms"

def test_memory_footprint():
    router = ModelRouter()
    
    # Generate 10k decisions
    for i in range(10_000):
        router.route(f"Task {i}")
    
    # Check memory growth
    import sys
    size_bytes = sys.getsizeof(router.history)
    size_mb = size_bytes / 1024 / 1024
    
    assert size_mb < 5.0, f"History too large: {size_mb:.2f} MB"
```

## Troubleshooting

### Issue 1: All Slots Unavailable

**Symptom**: `RuntimeError: All slots are unavailable`

**Cause**: All slots have error_count ≥ 5

**Fix**:
```python
# Manual health reset
router.reset_health()

# Or configure more lenient thresholds
router.health_status[ModelSlot.NORMAL]._recalculate_health = lambda: SlotHealth.HEALTHY
```

### Issue 2: Unexpected Slot Selection

**Symptom**: Task routes to wrong slot (e.g., "implement feature" → COMPACT)

**Cause**: Budget constraint too tight, forces cheapest slot

**Fix**:
```python
# Check budget constraint
decision = router.route(task, budget_multiplier=None)  # Remove constraint
print(decision.reasoning)  # See why slot was chosen
```

### Issue 3: Slow Routing

**Symptom**: Routing takes >10ms

**Cause**: Large routing history (10k+ decisions)

**Fix**:
```python
# Prune old decisions
router._history = router._history[-1000:]  # Keep last 1k decisions
```

### Issue 4: Health Not Recovering

**Symptom**: Slot stuck in DEGRADED after errors resolved

**Cause**: Not enough successful requests to decay error_count

**Fix**:
```python
# Record multiple successes to accelerate recovery
for _ in range(5):
    router.record_slot_result(ModelSlot.NORMAL, success=True, latency_ms=300)
```

---

**References**:
- [Architecture](architecture.md) — System overview
- [System Design](system-design.md) — Detailed algorithms and APIs
- [Tradeoffs](tradeoffs.md) — Design decision rationale
- [Evaluation](evaluation.md) — Performance benchmarks
