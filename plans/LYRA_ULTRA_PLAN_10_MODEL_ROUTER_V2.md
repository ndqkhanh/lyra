# LYRA ULTRA PLAN 10: Intelligent Model Router v2 — Complete Blueprint

**Version:** 1.0.0 | **Status:** In Progress | **Created:** 2026-05-25
**Parent Plan:** [LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md](LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md)

---

## Overview

Build a 5-layer intelligent model router that automatically maps every task to the optimal model based on complexity, capability requirements, cost budget, and performance history. The router cascades through layers at inference time, escalating to stronger models only when confidence drops below threshold.

---

## Part 1: 5-Layer Router Architecture

```
Task Input → Layer 1 (Task Classifier) → Layer 2 (Complexity Estimator) →
Layer 3 (Capability Matcher) → Layer 4 (Cost Optimizer) → Layer 5 (Performance History) →
Model Selection + Fallback Chain
```

### Layer 1: Task Classifier

Classifies the task into one of 15 categories:

| Category | Typical Models | Reasoning Required |
|----------|---------------|-------------------|
| `code_generation` | Sonnet, DeepSeek V4 Flash | Low-Medium |
| `code_review` | Sonnet, DeepSeek V4 Pro | Medium |
| `code_debugging` | Sonnet, Opus | High |
| `architecture_design` | Opus, DeepSeek V4 Pro | Very High |
| `research_literature` | Opus, Gemini 2.5 Pro | Very High |
| `research_synthesis` | Opus, DeepSeek V4 Pro | Very High |
| `data_analysis` | Sonnet, DeepSeek V4 Pro | Medium-High |
| `writing_creative` | Opus, Sonnet | Medium |
| `writing_technical` | Sonnet, DeepSeek V4 Pro | Medium |
| `refactoring` | Sonnet, DeepSeek V4 Flash | Medium |
| `testing` | Sonnet, DeepSeek V4 Flash | Low-Medium |
| `documentation` | Haiku, DeepSeek V4 Flash | Low |
| `triage_triage` | Haiku, Gemini Flash | Low |
| `shell_command` | Haiku, DeepSeek V4 Flash | Low |
| `conversation` | Sonnet, DeepSeek V4 Pro | Medium |

### Layer 2: Complexity Estimator

Estimates task complexity on a 1-10 scale:

```python
complexity_factors = {
    "files_touched": 0-3,        # Estimated files to modify
    "dependencies": 0-2,         # External dependency count
    "ambiguity": 0-2,            # How clear the requirements are
    "risk_level": 0-3,           # Impact radius of changes
}

complexity_score = sum(complexity_factors.values())  # 0-10

if complexity_score <= 3:    tier = "simple"      # Haiku/Flash
elif complexity_score <= 6:  tier = "moderate"     # Sonnet
else:                        tier = "complex"      # Opus/Pro
```

### Layer 3: Capability Matcher

Maps required capabilities to model features:

```python
CAPABILITY_MATRIX = {
    "reasoning_deep": ["claude-opus-4-7", "deepseek-v4-pro", "gpt-4o"],
    "reasoning_medium": ["claude-sonnet-4-6", "deepseek-v4-pro", "gemini-2.5-pro"],
    "coding_fast": ["claude-sonnet-4-6", "deepseek-v4-flash", "gemini-flash"],
    "coding_precise": ["claude-opus-4-7", "deepseek-v4-pro", "gpt-4o"],
    "vision": ["claude-opus-4-7", "claude-sonnet-4-6", "gpt-4o", "gemini-2.5-pro"],
    "long_context": ["gemini-2.5-pro", "gemini-3.1-pro"],  # 1M+ tokens
    "multilingual": ["claude-sonnet-4-6", "gemini-2.5-pro", "qwen-3.7-max"],
    "cost_optimized": ["claude-haiku-4-5", "deepseek-v4-flash", "gemini-flash"],
    "local_only": ["ollama-llama4", "ollama-qwen-coder"],
}
```

### Layer 4: Cost Optimizer

Cascading cost strategy with automatic fallback:

```python
CASCADE_CHAIN = {
    "simple": [
        ("deepseek-v4-flash", 0.14),     # $0.14/M input tokens
        ("claude-haiku-4-5", 0.80),      # $0.80/M input tokens
        ("gemini-flash", 0.15),           # $0.15/M input tokens
    ],
    "moderate": [
        ("claude-sonnet-4-6", 3.00),     # $3.00/M input tokens
        ("deepseek-v4-pro", 1.10),        # $1.10/M input tokens
        ("gemini-2.5-pro", 1.25),         # $1.25/M input tokens
    ],
    "complex": [
        ("claude-opus-4-7", 15.00),      # $15.00/M input tokens
        ("deepseek-v4-pro", 1.10),        # $1.10/M input tokens
        ("gpt-4o", 2.50),                 # $2.50/M input tokens
    ],
}
```

### Layer 5: Performance History

Learns from historical success rates per (task_category, model) pair:

```python
# Continuously updated from execution traces
PERFORMANCE_HISTORY = {
    ("code_generation", "claude-sonnet-4-6"): {"success_rate": 0.94, "samples": 1523},
    ("code_generation", "deepseek-v4-flash"): {"success_rate": 0.91, "samples": 892},
    ("architecture_design", "claude-opus-4-7"): {"success_rate": 0.96, "samples": 234},
    ("architecture_design", "deepseek-v4-pro"): {"success_rate": 0.89, "samples": 156},
    # ... continuously updated
}
```

---

## Part 2: Router Configuration

### 2.1 Model Slots

```json
// ~/.lyra/router.json
{
  "slots": {
    "reasoning": {
      "primary": "anthropic:claude-opus-4-7",
      "fallback": ["deepseek:deepseek-v4-pro", "openai:gpt-4o"],
      "max_budget_per_task_usd": 2.00
    },
    "coding": {
      "primary": "anthropic:claude-sonnet-4-6",
      "fallback": ["deepseek:deepseek-v4-pro", "google:gemini-2.5-pro"],
      "max_budget_per_task_usd": 0.50
    },
    "fast": {
      "primary": "deepseek:deepseek-v4-flash",
      "fallback": ["anthropic:claude-haiku-4-5", "google:gemini-flash"],
      "max_budget_per_task_usd": 0.05
    },
    "vision": {
      "primary": "anthropic:claude-sonnet-4-6",
      "fallback": ["openai:gpt-4o", "google:gemini-2.5-pro"]
    },
    "long_context": {
      "primary": "google:gemini-2.5-pro",
      "fallback": ["google:gemini-3.1-pro"]
    }
  },
  "auto_detect": true,
  "confidence_threshold": 0.75,
  "escalation_limit": 3,
  "track_performance": true,
  "history_window_days": 30,
  "cost_alerts": {
    "per_task_warning_usd": 1.00,
    "per_session_limit_usd": 10.00,
    "daily_limit_usd": 50.00
  }
}
```

### 2.2 Task-to-Slot Mapping

```python
TASK_SLOT_MAP = {
    "code_generation": "coding",
    "code_review": "coding",
    "code_debugging": "reasoning",
    "architecture_design": "reasoning",
    "research_literature": "reasoning",
    "research_synthesis": "reasoning",
    "data_analysis": "coding",
    "writing_creative": "reasoning",
    "writing_technical": "coding",
    "refactoring": "coding",
    "testing": "fast",
    "documentation": "fast",
    "triage_triage": "fast",
    "shell_command": "fast",
    "conversation": "coding",
}
```

---

## Part 3: Confidence-Thresholded Escalation

### 3.1 Escalation Logic

```python
async def route_task(task: str, context: dict) -> ModelSelection:
    # Layer 1: Classify
    category = classify_task(task)
    
    # Layer 2: Estimate complexity
    complexity = estimate_complexity(task, context)
    tier = complexity_to_tier(complexity)
    
    # Layer 3: Match capabilities
    slot = TASK_SLOT_MAP[category]
    candidates = CAPABILITY_MATRIX[slot]
    
    # Layer 4: Cost-optimize
    chain = CASCADE_CHAIN[tier]
    
    # Layer 5: Performance-history boost
    chain = reorder_by_performance(chain, category)
    
    # Try each model in cascade order
    for i, (model, cost_per_mtok) in enumerate(chain):
        if i > 0 and i >= config.escalation_limit:
            break  # Don't escalate beyond limit
        
        result = await try_model(model, task)
        
        # Confidence check
        if result.confidence >= config.confidence_threshold:
            record_success(category, model, cost_per_mtok)
            return ModelSelection(model=model, tier=tier, escalated=(i > 0))
        
        # Below threshold → escalate to next model
        log_escalation(task, model, result.confidence)
    
    # All models tried → use strongest available
    return ModelSelection(model=chain[-1][0], tier="max", escalated=True)
```

### 3.2 Confidence Score Computation

```python
def compute_confidence(result: AgentResult) -> float:
    factors = {
        "self_reported": result.confidence or 0.5,    # 0-1 from model
        "output_validity": verify_output(result),       # Did verifier pass?
        "consistency": check_consistency(result),       # Internal consistency
        "completeness": check_completeness(result),     # All sub-tasks done?
    }
    weights = {"self_reported": 0.2, "output_validity": 0.4, 
               "consistency": 0.2, "completeness": 0.2}
    return sum(factors[k] * weights[k] for k in factors)
```

---

## Part 4: Provider Fallback Chain

### 4.1 Global Fallback

```json
// ~/.lyra/settings.json
{
  "fallback_chain": [
    "anthropic",
    "deepseek", 
    "google",
    "openai",
    "xai",
    "mistral"
  ],
  "fallback_strategy": "next_available",
  "fallback_on": ["rate_limit", "timeout", "content_filter", "server_error"],
  "fallback_cooldown_seconds": 300
}
```

### 4.2 Health Monitoring

```python
@dataclass
class ProviderHealth:
    provider: str
    model: str
    last_checked: datetime
    latency_p50_ms: float
    latency_p99_ms: float
    error_rate_1h: float
    rate_limit_remaining: int
    status: Literal["healthy", "degraded", "unavailable"]

# Updated every 60s via background health checks
HEALTH_REGISTRY: dict[str, ProviderHealth] = {}
```

---

## Part 5: Cost Tracking & Budgeting

### 5.1 Real-Time Cost Tracking

```python
@dataclass
class SessionCost:
    model: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    cost_usd: float
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def cache_savings_usd(self) -> float:
        return self.cache_read_tokens * CACHE_READ_PRICE

class CostTracker:
    costs: list[SessionCost]
    
    @property
    def total_usd(self) -> float: ...
    
    @property
    def by_model(self) -> dict[str, float]: ...
    
    @property
    def by_category(self) -> dict[str, float]: ...
    
    def alert_if_exceeds(self, limit_usd: float) -> None: ...
```

### 5.2 Burn Report (13 Categories)

```python
BURN_CATEGORIES = {
    "prompt_overhead": "System prompt + tool schemas",
    "context_redundancy": "Repeated context across turns",
    "tool_output_bloat": "Overly verbose tool outputs",
    "thinking_overrun": "Thinking tokens beyond budget",
    "cache_miss": "Tokens that could have been cached",
    "over_prompting": "Unnecessarily long prompts",
    "history_baggage": "Old conversation turns kept in context",
    "skill_bloat": "Skills loaded but never triggered",
    "rule_bloat": "Rules evaluated but never matched",
    "schema_overhead": "Large tool schemas in system prompt",
    "retry_waste": "Tokens spent on failed attempts",
    "streaming_overhead": "Streaming protocol overhead",
    "unknown": "Uncategorized token usage",
}
```

---

## Part 6: Implementation Roadmap

### Phase 10.1: Core Router (Weeks 1-2)
- [ ] Task classifier (Layer 1) — 15 categories, prompt-based
- [ ] Complexity estimator (Layer 2) — heuristic scoring
- [ ] Capability matcher (Layer 3) — static matrix
- [ ] Basic slot system (reasoning/coding/fast)

### Phase 10.2: Cost & Performance (Weeks 3-4)
- [ ] Cost optimizer (Layer 4) — cascading price chains
- [ ] Performance history (Layer 5) — per-category tracking
- [ ] Confidence-thresholded escalation
- [ ] Provider health monitoring

### Phase 10.3: Advanced Routing (Weeks 5-6)
- [ ] ML-based task classifier (fine-tuned BERT)
- [ ] Dynamic capability matrix from model benchmarks
- [ ] Predictive cost estimation before execution
- [ ] Cross-task pattern learning

### Phase 10.4: Optimization (Weeks 7-8)
- [ ] Cost tracking dashboard with burn reports
- [ ] Budget alerts and auto-throttling
- [ ] Router A/B testing framework
- [ ] Self-optimizing routing (router learns from outcomes)

---

## Part 7: Reference & Inspiration

| Source | Key Ideas Adopted |
|--------|------------------|
| [FrugalGPT (Stanford, 2023)](https://arxiv.org/abs/2305.05176) | Cost-aware cascading routing, LLM cascade chains |
| [RouteLLM (Berkeley, 2024)](https://arxiv.org/abs/2406.18665) | Fast/smart slot routing with preference data |
| [Confidence-Driven Router (2025)](https://arxiv.org/abs/2502.11021) | Confidence-thresholded escalation, dynamic routing |
| [Lyra Router v1](packages/lyra-router/) | Existing 2-tier routing, slot system |
| [Claude Code Model Config](https://code.claude.com/docs/en/model-config) | Model slots, fast/smart aliases |
| [OpenRouter](https://openrouter.ai/) | Multi-provider aggregation, price sorting |
