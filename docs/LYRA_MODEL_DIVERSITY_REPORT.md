# Lyra Model Diversity & Auto-Switching Strategy Report

**Date:** 2026-05-15  
**Status:** ✅ VERIFIED - All providers implemented  
**Recommendation:** Enhance existing 3-tier routing with cost-aware model selection

---

## Executive Summary

Lyra has **excellent model diversity** with 13 providers and 20+ presets already implemented. The system includes a sophisticated 3-tier routing policy (fast/reasoning/advisor) that can be enhanced with cost-aware auto-switching logic.

---

## 1. Verified Provider Support

### ✅ Cloud Providers (API-based)

| Provider | Status | Default Model | Context Window | API Key Env Var |
|----------|--------|---------------|----------------|-----------------|
| **OpenAI** | ✅ Implemented | `gpt-4o` | 128K | `OPENAI_API_KEY` |
| **OpenAI Reasoning** | ✅ Implemented | `o3-mini` | 128K | `OPENAI_API_KEY` |
| **Anthropic** | ✅ Implemented | `claude-opus-4.5` | 200K | `ANTHROPIC_API_KEY` |
| **Google Gemini** | ✅ Implemented | `gemini-2.5-pro` | 2M | `GEMINI_API_KEY` |
| **DeepSeek** | ✅ Implemented | `deepseek-chat` | 128K | `DEEPSEEK_API_KEY` |
| **xAI (Grok)** | ✅ Implemented | `grok-4` | 256K | `XAI_API_KEY` |
| **Groq** | ✅ Implemented | `llama-3.3-70b-versatile` | 128K | `GROQ_API_KEY` |
| **Cerebras** | ✅ Implemented | `llama3.3-70b` | 128K | `CEREBRAS_API_KEY` |
| **Mistral** | ✅ Implemented | `codestral-latest` | 256K | `MISTRAL_API_KEY` |
| **Qwen/DashScope** | ✅ Implemented | `qwen-plus` | varies | `QWEN_API_KEY` / `DASHSCOPE_API_KEY` |
| **OpenRouter** | ✅ Implemented | `openrouter/auto` | 200K | `OPENROUTER_API_KEY` |

### ✅ Cloud-Routed Providers

| Provider | Status | Default Model | Auth Method |
|----------|--------|---------------|-------------|
| **AWS Bedrock** | ✅ Implemented | `anthropic.claude-3-5-sonnet-20241022-v2:0` | AWS credentials + boto3 |
| **Google Vertex AI** | ✅ Implemented | `gemini-2.5-pro` | GCP ADC + project ID |
| **GitHub Copilot** | ✅ Implemented | `gpt-4o` | GitHub OAuth token |

### ✅ Local Providers (Self-hosted)

| Provider | Status | Default Port | Auth Required |
|----------|--------|--------------|---------------|
| **Ollama** | ✅ Implemented | 11434 | No |
| **LM Studio** | ✅ Implemented | 1234 | No |
| **vLLM** | ✅ Implemented | 8000 | No |
| **llama.cpp server** | ✅ Implemented | 8080 | No |
| **HuggingFace TGI** | ✅ Implemented | 8081 | No |
| **Llamafile** | ✅ Implemented | 8082 | No |
| **MLX-LM** | ✅ Implemented | 8083 | No (Apple Silicon only) |

### ❌ Not Found

- **Mooshoot**: Not implemented (not found in codebase)

---

## 2. Current Auto-Cascade Logic

### Priority Order (from `llm_factory.py` lines 746-843)

```python
# v2.1+ cascade order:
1. DeepSeek       — Cost-aware default (10-20× cheaper than Claude/GPT-5)
2. Anthropic      — Reference target for tool-using agents
3. OpenAI         — Preset registry iteration
4. Gemini         — Preset registry iteration
5. xAI (Grok)     — Preset registry iteration
6. Groq           — Preset registry iteration
7. Cerebras       — Preset registry iteration
8. Mistral        — Preset registry iteration
9. Qwen           — Preset registry iteration
10. OpenRouter    — Meta-provider (300+ models)
11. LM Studio     — Local fallback
12. Ollama        — Local fallback (preferred if LYRA_PREFER_LOCAL=1)
```

**Key Design Decision:**
> "DeepSeek heads the cascade because in 2026 its coder models match Claude Sonnet / GPT-5 on agentic-coding benchmarks at roughly 10-20× lower per-token cost" (lines 21-26)

---

## 3. Existing 3-Tier Routing System

### Architecture (`lyra_core/routing/policy.py`)

Lyra **already has** a sophisticated routing system:

```python
ModelTier = Literal["fast", "reasoning", "advisor"]

class RoutingSignals:
    task_ambiguity: float = 0.0        # 0-1 normalized
    evidence_conflict: bool = False
    tool_risk: float = 0.0             # 0=read-only, 1=destructive
    context_pressure: float = 0.0      # context window % used
    uncertainty: float = 0.0
    repeated_failure: bool = False
    budget_pressure: float = 0.0       # cost_spent / budget

class TrajectoryBudget:
    max_cost_usd: float = 5.0
    max_advisor_calls: int = 3
    cost_spent_usd: float = 0.0
    advisor_calls: int = 0
    reasoning_calls: int = 0
    fast_calls: int = 0
```

### Routing Decision Logic

```python
def route_step(signals, budget, config) -> RoutingDecision:
    # 1. Advisor tier (most expensive, highest quality)
    if (tool_risk >= 0.7 AND 
        (uncertainty >= 0.75 OR evidence_conflict) AND
        budget_pressure < 0.85 AND
        advisor_calls < max_advisor_calls):
        return "advisor"
    
    # 2. Reasoning tier (medium cost, deep thinking)
    if (task_ambiguity >= 0.4 OR
        evidence_conflict OR
        context_pressure >= 0.70 OR
        uncertainty >= 0.5 OR
        repeated_failure):
        return "reasoning"
    
    # 3. Fast tier (default, cheapest)
    return "fast"
```

---

## 4. Cost Tracking Infrastructure

### Pricing Data (`transparency/cost_accumulator.py`)

```python
# Claude pricing (USD per 1M tokens) — May 2026
_PRICING = {
    "claude-opus-4-7":    {"in": 15.0, "out": 75.0, "cache_read": 1.5,  "cache_write": 18.75},
    "claude-sonnet-4-6":  {"in": 3.0,  "out": 15.0, "cache_read": 0.3,  "cache_write": 3.75},
    "claude-haiku-4-5":   {"in": 0.8,  "out": 4.0,  "cache_read": 0.08, "cache_write": 1.0},
}
```

### Cost Tracking (`harness_core/cost.py`)

```python
class CostTracker:
    def record(operation, project, user_id, input_tokens, output_tokens, cost_usd)
    def total(project=None, user_id=None, operation=None, period=None) -> float
    def report(group_by="project") -> CostReport
    def check_threshold(threshold_usd, **filters) -> CostThresholdAlert | None
```

---

## 5. Model Alias System

### Comprehensive Alias Registry (`providers/aliases.py`)

**456 lines** of model aliases mapping short names to canonical slugs:

```python
# Examples:
"opus" → "claude-opus-4.5"
"sonnet" → "claude-sonnet-4.5"
"haiku" → "claude-haiku-4"
"gpt" → "gpt-5.5"
"deepseek" → "deepseek-chat"
"deepseek-pro" → "deepseek-reasoner"
"grok" → "grok-4"
"gemini" → "gemini-3.1-pro"
"qwen" → "qwen-max"
"llama" → "llama-3.3-70b-versatile"
```

**Pattern-based aliases** for future-proofing:
```python
# Auto-routes deepseek-v5-pro, deepseek-v6-pro, etc.
r"^deepseek-v\d+(?:\.\d+)?-(?:pro|reasoner|smart)$" → "deepseek-reasoner"
r"^deepseek-v\d+(?:\.\d+)?-(?:flash|chat|fast|cheap)$" → "deepseek-chat"
```

---

## 6. Recommended Auto-Switching Strategy

### Tier → Model Mapping

Based on existing infrastructure, here's the recommended mapping:

#### **Fast Tier** (Simple tasks, code completion, quick questions)

| Provider | Model | Cost (per 1M tokens) | Speed | Use Case |
|----------|-------|----------------------|-------|-----------|
| **DeepSeek** | `deepseek-chat` | $0.14 in / $0.28 out | Fast | Default fast model |
| **Groq** | `llama-3.3-70b-versatile` | Free tier available | **Ultra-fast** (2000 t/s) | Speed-critical |
| **Cerebras** | `llama3.3-70b` | Low cost | **Ultra-fast** | Speed-critical |
| **Anthropic** | `claude-haiku-4` | $0.80 in / $4.00 out | Fast | High-quality fast |
| **OpenAI** | `gpt-4o-mini` | $0.15 in / $0.60 out | Fast | OpenAI ecosystem |
| **Gemini** | `gemini-2.5-flash` | $0.075 in / $0.30 out | Fast | Google ecosystem |

#### **Reasoning Tier** (Complex tasks, architecture, debugging, planning)

| Provider | Model | Cost (per 1M tokens) | Reasoning | Use Case |
|----------|-------|----------------------|-----------|-----------|
| **DeepSeek** | `deepseek-reasoner` (R1) | $0.55 in / $2.19 out | ✅ Chain-of-thought | Default reasoning |
| **Anthropic** | `claude-sonnet-4.5` | $3.00 in / $15.00 out | ✅ Extended thinking | High-quality reasoning |
| **OpenAI** | `o3-mini` | $1.10 in / $4.40 out | ✅ O-series reasoning | OpenAI reasoning |
| **Gemini** | `gemini-2.5-flash-thinking` | Low cost | ✅ Thinking mode | Google reasoning |

#### **Advisor Tier** (High-risk operations, critical decisions, security)

| Provider | Model | Cost (per 1M tokens) | Quality | Use Case |
|----------|-------|----------------------|---------|-----------|
| **Anthropic** | `claude-opus-4.5` | $15.00 in / $75.00 out | ⭐⭐⭐⭐⭐ | Highest quality |
| **OpenAI** | `gpt-5` | $10.00 in / $30.00 out | ⭐⭐⭐⭐⭐ | GPT flagship |
| **OpenAI** | `o3` | $15.00 in / $60.00 out | ⭐⭐⭐⭐⭐ | Deep reasoning |
| **Gemini** | `gemini-2.5-pro` | $1.25 in / $5.00 out | ⭐⭐⭐⭐ | Cost-effective advisor |

---

## 7. Implementation Plan

### Phase 1: Extend Routing Policy with Model Selection

**File:** `lyra_core/routing/policy.py`

```python
@dataclass(frozen=True)
class ModelSelection:
    """Maps tier to specific provider + model."""
    provider: str
    model: str
    estimated_cost_per_1k_tokens: float

@dataclass(frozen=True)
class RoutingConfig:
    # ... existing fields ...
    
    # New: Model selection per tier
    fast_models: tuple[ModelSelection, ...] = (
        ModelSelection("deepseek", "deepseek-chat", 0.00014),
        ModelSelection("groq", "llama-3.3-70b-versatile", 0.0),
        ModelSelection("anthropic", "claude-haiku-4", 0.0008),
    )
    
    reasoning_models: tuple[ModelSelection, ...] = (
        ModelSelection("deepseek", "deepseek-reasoner", 0.00055),
        ModelSelection("anthropic", "claude-sonnet-4.5", 0.003),
        ModelSelection("openai-reasoning", "o3-mini", 0.0011),
    )
    
    advisor_models: tuple[ModelSelection, ...] = (
        ModelSelection("anthropic", "claude-opus-4.5", 0.015),
        ModelSelection("openai", "gpt-5", 0.010),
        ModelSelection("gemini", "gemini-2.5-pro", 0.00125),
    )
    
    # Fallback strategy
    prefer_cost_over_quality: bool = True  # True = pick cheapest, False = pick best

def select_model(
    tier: ModelTier,
    config: RoutingConfig,
    budget: TrajectoryBudget,
) -> ModelSelection:
    """Select specific model for the tier based on budget and config."""
    
    if tier == "fast":
        candidates = config.fast_models
    elif tier == "reasoning":
        candidates = config.reasoning_models
    else:  # advisor
        candidates = config.advisor_models
    
    # Filter by availability (check if API key is set)
    available = [m for m in candidates if provider_has_credentials(m.provider)]
    
    if not available:
        raise NoProviderConfigured(f"No {tier} models available")
    
    # Sort by cost (ascending) or quality (descending based on order)
    if config.prefer_cost_over_quality or budget.budget_pressure > 0.7:
        # Pick cheapest available
        return min(available, key=lambda m: m.estimated_cost_per_1k_tokens)
    else:
        # Pick first (highest quality) available
        return available[0]
```

### Phase 2: Integrate with LLM Factory

**File:** `lyra_cli/llm_factory.py`

```python
def build_llm_with_routing(
    signals: RoutingSignals,
    budget: TrajectoryBudget,
    config: Optional[RoutingConfig] = None,
    *,
    task_hint: Optional[str] = None,
    session_id: Optional[str] = None,
) -> tuple[LLMProvider, RoutingDecision]:
    """Build LLM provider using 3-tier routing policy."""
    
    # Decide tier
    decision = route_step(signals, budget, config)
    
    # Select specific model for tier
    cfg = config or RoutingConfig()
    model_selection = select_model(decision.tier, cfg, budget)
    
    # Build provider
    llm = build_llm(
        kind=model_selection.provider,
        task_hint=task_hint,
        session_id=session_id,
    )
    
    # Override model if needed
    if hasattr(llm, 'model'):
        llm.model = model_selection.model
    
    return llm, decision
```

### Phase 3: Add Task Complexity Detection

**File:** `lyra_core/routing/signals.py` (new)

```python
def detect_task_complexity(
    user_message: str,
    conversation_history: list[Message],
    tools_available: list[dict],
) -> RoutingSignals:
    """Infer routing signals from task context."""
    
    # Task ambiguity: long messages, questions, uncertainty markers
    ambiguity = 0.0
    if len(user_message) > 500:
        ambiguity += 0.2
    if any(q in user_message.lower() for q in ["?", "how", "why", "what", "unclear"]):
        ambiguity += 0.3
    if any(w in user_message.lower() for w in ["maybe", "perhaps", "not sure", "unsure"]):
        ambiguity += 0.2
    
    # Tool risk: destructive operations
    tool_risk = 0.0
    destructive_keywords = ["delete", "remove", "drop", "truncate", "force", "reset"]
    if any(kw in user_message.lower() for kw in destructive_keywords):
        tool_risk = 0.9
    elif any(kw in user_message.lower() for kw in ["write", "update", "modify", "change"]):
        tool_risk = 0.5
    
    # Context pressure: estimate from conversation length
    total_chars = sum(len(m.content or "") for m in conversation_history)
    context_pressure = min(total_chars / 100_000, 1.0)  # Assume 100K char = full context
    
    # Repeated failure: check last N turns for errors
    repeated_failure = False
    recent_errors = sum(
        1 for m in conversation_history[-5:]
        if m.role == "tool" and any(r.is_error for r in (m.tool_results or []))
    )
    if recent_errors >= 2:
        repeated_failure = True
    
    return RoutingSignals(
        task_ambiguity=min(ambiguity, 1.0),
        tool_risk=min(tool_risk, 1.0),
        context_pressure=context_pressure,
        repeated_failure=repeated_failure,
    )
```

### Phase 4: Configuration File

**File:** `~/.lyra/routing.json` (new)

```json
{
  "routing": {
    "enabled": true,
    "prefer_cost_over_quality": true,
    "max_cost_usd_per_session": 5.0,
    "max_advisor_calls_per_session": 3,
    
    "fast_models": [
      {"provider": "deepseek", "model": "deepseek-chat"},
      {"provider": "groq", "model": "llama-3.3-70b-versatile"},
      {"provider": "anthropic", "model": "claude-haiku-4"}
    ],
    
    "reasoning_models": [
      {"provider": "deepseek", "model": "deepseek-reasoner"},
      {"provider": "anthropic", "model": "claude-sonnet-4.5"},
      {"provider": "openai-reasoning", "model": "o3-mini"}
    ],
    
    "advisor_models": [
      {"provider": "anthropic", "model": "claude-opus-4.5"},
      {"provider": "openai", "model": "gpt-5"},
      {"provider": "gemini", "model": "gemini-2.5-pro"}
    ],
    
    "thresholds": {
      "ambiguity_reasoning": 0.4,
      "context_reasoning": 0.70,
      "uncertainty_reasoning": 0.5,
      "tool_risk_advisor": 0.7,
      "uncertainty_advisor": 0.75,
      "budget_pressure_advisor_cap": 0.85
    }
  }
}
```

---

## 8. Cost Comparison Examples

### Scenario 1: Simple Code Completion (Fast Tier)

**Task:** "Add a docstring to this function"

| Model | Input (1K) | Output (500) | Total Cost |
|-------|------------|--------------|------------|
| DeepSeek Chat | $0.00014 | $0.00014 | **$0.00028** ⭐ Cheapest |
| Groq Llama 3.3 | $0 | $0 | **$0** (free tier) |
| Claude Haiku 4 | $0.0008 | $0.002 | $0.0028 |
| GPT-4o-mini | $0.00015 | $0.0003 | $0.00045 |

**Savings:** DeepSeek is **10× cheaper** than Claude Haiku

### Scenario 2: Complex Refactoring (Reasoning Tier)

**Task:** "Refactor this module to use dependency injection"

| Model | Input (10K) | Output (5K) | Total Cost |
|-------|-------------|-------------|------------|
| DeepSeek Reasoner | $0.0055 | $0.01095 | **$0.01645** ⭐ Cheapest |
| O3-mini | $0.011 | $0.022 | $0.033 |
| Claude Sonnet 4.5 | $0.03 | $0.075 | $0.105 |

**Savings:** DeepSeek Reasoner is **6× cheaper** than Claude Sonnet

### Scenario 3: Security Review (Advisor Tier)

**Task:** "Review this authentication code for security vulnerabilities"

| Model | Input (20K) | Output (10K) | Total Cost |
|-------|-------------|--------------|------------|
| Gemini 2.5 Pro | $0.025 | $0.05 | **$0.075** ⭐ Cheapest |
| GPT-5 | $0.20 | $0.30 | $0.50 |
| Claude Opus 4.5 | $0.30 | $0.75 | $1.05 |

**Savings:** Gemini is **14× cheaper** than Claude Opus

---

## 9. Usage Examples

### Example 1: Automatic Routing

```python
from lyra_core.routing.policy import RoutingSignals, TrajectoryBudget
from lyra_cli.llm_factory import build_llm_with_routing

# Initialize budget tracker
budget = TrajectoryBudget(max_cost_usd=5.0, max_advisor_calls=3)

# Simple task → Fast tier
signals = RoutingSignals(task_ambiguity=0.1, tool_risk=0.0)
llm, decision = build_llm_with_routing(signals, budget)
# → Uses DeepSeek Chat ($0.00028 per turn)

# Complex task → Reasoning tier
signals = RoutingSignals(task_ambiguity=0.8, context_pressure=0.75)
llm, decision = build_llm_with_routing(signals, budget)
# → Uses DeepSeek Reasoner ($0.01645 per turn)

# High-risk task → Advisor tier
signals = RoutingSignals(tool_risk=0.9, uncertainty=0.8)
llm, decision = build_llm_with_routing(signals, budget)
# → Uses Claude Opus 4.5 ($1.05 per turn)
```

### Example 2: Manual Override

```bash
# Force specific tier
lyra run --tier fast "add docstring"
lyra run --tier reasoning "refactor this module"
lyra run --tier advisor "security review"

# Force specific model
lyra run --model deepseek-chat "quick task"
lyra run --model claude-opus-4.5 "critical task"

# Cost-aware mode
lyra run --prefer-cost "optimize for cost"
lyra run --prefer-quality "optimize for quality"
```

---

## 10. Key Findings

### ✅ Strengths

1. **Comprehensive Provider Support**: 13 providers, 20+ presets, all major LLM vendors covered
2. **Sophisticated Routing**: 3-tier system with budget tracking already implemented
3. **Cost Infrastructure**: Full cost tracking, pricing tables, threshold alerts
4. **Alias System**: 456 lines of aliases, pattern-based future-proofing
5. **Local Fallbacks**: 7 local providers for offline/privacy scenarios
6. **Cloud Routing**: Bedrock, Vertex, Copilot for enterprise scenarios

### 🎯 Opportunities

1. **Model Selection**: Routing decides tier, but doesn't select specific model within tier
2. **Task Detection**: No automatic complexity detection from user input
3. **Cost Optimization**: Budget tracking exists but not used for model selection
4. **Configuration**: No user-facing config for tier → model mapping

### 💡 Recommendations

1. **Implement Phase 1-4** above to add model selection within tiers
2. **Default to cost-aware**: Use DeepSeek for fast/reasoning, Gemini for advisor
3. **Add task detection**: Automatically infer signals from user message
4. **Expose configuration**: Let users customize tier → model mapping
5. **Add telemetry**: Track tier usage, cost savings, quality metrics

---

## 11. Cost Savings Projection

### Current State (No Auto-Switching)

Assuming all tasks use Claude Sonnet 4.5:
- 100 turns/day × $0.105/turn = **$10.50/day**
- **$315/month**

### With Auto-Switching (Recommended)

Assuming 70% fast, 25% reasoning, 5% advisor:
- 70 fast turns × $0.00028 = $0.0196
- 25 reasoning turns × $0.01645 = $0.411
- 5 advisor turns × $0.075 = $0.375
- **Total: $0.806/day = $24.18/month**

**Savings: $290.82/month (92% reduction)** 🎉

---

## 12. Next Steps

1. ✅ **Verify providers** (DONE - all verified)
2. 🔨 **Implement model selection** (Phase 1-2)
3. 🔨 **Add task detection** (Phase 3)
4. 🔨 **Create configuration** (Phase 4)
5. 📊 **Add telemetry** (track usage patterns)
6. 🧪 **A/B testing** (compare quality vs cost)
7. 📚 **Documentation** (user guide for routing)

---

## Appendix A: Complete Model List

### Fast Models (by cost, ascending)

1. Groq Llama 3.3 70B - **$0** (free tier)
2. Gemini 2.5 Flash - **$0.075** in / $0.30 out
3. DeepSeek Chat - **$0.14** in / $0.28 out
4. GPT-4o-mini - **$0.15** in / $0.60 out
5. Claude Haiku 4 - **$0.80** in / $4.00 out

### Reasoning Models (by cost, ascending)

1. DeepSeek Reasoner (R1) - **$0.55** in / $2.19 out
2. O3-mini - **$1.10** in / $4.40 out
3. Gemini 2.5 Flash Thinking - **~$0.50** in / $2.00 out (estimated)
4. Claude Sonnet 4.5 - **$3.00** in / $15.00 out

### Advisor Models (by cost, ascending)

1. Gemini 2.5 Pro - **$1.25** in / $5.00 out
2. GPT-5 - **$10.00** in / $30.00 out
3. Claude Opus 4.5 - **$15.00** in / $75.00 out
4. O3 - **$15.00** in / $60.00 out

---

## Appendix B: Provider Capabilities Matrix

| Provider | Tools | Reasoning | Vision | Streaming | Context |
|----------|-------|-----------|--------|-----------|---------|
| Anthropic | ✅ | ✅ | ✅ | ✅ | 200K |
| OpenAI | ✅ | ❌ | ✅ | ✅ | 128K |
| OpenAI Reasoning | ✅ | ✅ | ❌ | ✅ | 128K |
| Gemini | ✅ | ✅ | ✅ | ✅ | 2M |
| DeepSeek | ✅ | ✅ | ❌ | ✅ | 128K |
| xAI Grok | ✅ | ❌ | ❌ | ✅ | 256K |
| Groq | ✅ | ❌ | ❌ | ✅ | 128K |
| Cerebras | ✅ | ❌ | ❌ | ✅ | 128K |
| Mistral | ✅ | ❌ | ❌ | ✅ | 256K |
| OpenRouter | ✅ | ✅ | ✅ | ✅ | 200K |
| Ollama | ✅ | ❌ | ❌ | ✅ | 8K-128K |

---

**Report Generated:** 2026-05-15  
**Lyra Version:** v2.7+  
**Status:** Ready for implementation
