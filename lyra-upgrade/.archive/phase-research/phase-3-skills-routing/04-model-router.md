# §4.5 Model Router Architecture Plan

## Executive Summary

Multi-provider intelligent routing system combining RouteLLM's preference-based routing, BEST-Route's dynamic sampling, FrugalGPT's cascade strategy, and memory-augmented routing for cost-effective, high-quality inference across Claude, DeepSeek, Qwen, GPT, and open-weights models.

---

## 1. Multi-Provider Abstraction Layer

### 1.1 Provider Interface

**Unified Provider API**:
```typescript
interface Provider {
  id: string;                    // 'anthropic' | 'deepseek' | 'qwen' | 'openai' | 'open-weights'
  name: string;                  // Human-readable name
  models: Model[];               // Available models
  capabilities: Capability[];    // Supported features
  pricing: PricingTier[];        // Cost structure
  
  // Core methods
  complete(request: CompletionRequest): Promise<CompletionResponse>;
  stream(request: CompletionRequest): AsyncIterator<CompletionChunk>;
  embeddings(texts: string[]): Promise<number[][]>;
}

interface Model {
  id: string;                    // 'claude-opus-4', 'deepseek-v3', etc.
  tier: 'cheap' | 'standard' | 'premium' | 'reasoning';
  contextWindow: number;         // Max tokens
  capabilities: Capability[];    // Tool use, vision, etc.
  pricing: {
    inputPerMToken: number;      // Cost per million input tokens
    outputPerMToken: number;     // Cost per million output tokens
  };
  performance: {
    latencyP50: number;          // Median latency (ms)
    latencyP99: number;          // 99th percentile latency (ms)
    throughput: number;          // Tokens per second
  };
}

interface Capability {
  name: string;                  // 'tool_use' | 'vision' | 'thinking' | 'streaming'
  required: boolean;             // Must have vs. nice to have
  fallback?: string;             // Alternative capability if missing
}
```

### 1.2 Provider Registry

**Supported Providers**:

1. **Anthropic Claude**
   - Models: claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5
   - Tiers: premium (Opus), standard (Sonnet), cheap (Haiku)
   - Capabilities: tool_use, vision, thinking, streaming, prompt_caching
   - Pricing: Opus ($15/$75), Sonnet ($3/$15), Haiku ($0.80/$4)

2. **DeepSeek**
   - Models: deepseek-v3, deepseek-r1 (reasoning), deepseek-lite
   - Tiers: reasoning (R1), standard (V3), cheap (Lite)
   - Capabilities: tool_use, streaming, long_context (128K)
   - Pricing: V3 ($0.27/$1.10), R1 ($0.55/$2.19), Lite ($0.14/$0.28)

3. **Alibaba Qwen**
   - Models: qwen-3-235b, qwen-2.5-72b, qwen-2.5-7b
   - Tiers: premium (3-235B), standard (2.5-72B), cheap (2.5-7B)
   - Capabilities: tool_use, vision, streaming, long_context (32K)
   - Pricing: 3-235B ($2/$6), 2.5-72B ($0.50/$1.50), 2.5-7B ($0.10/$0.20)

4. **OpenAI GPT**
   - Models: gpt-4o, o1, o3-mini
   - Tiers: reasoning (o1/o3), standard (4o), cheap (4o-mini)
   - Capabilities: tool_use, vision, streaming, structured_outputs
   - Pricing: 4o ($2.50/$10), o1 ($15/$60), 4o-mini ($0.15/$0.60)

5. **Open-Weights**
   - Models: llama-3.3-70b, mistral-large-2, gemma-2-27b
   - Tiers: standard (70B), cheap (27B)
   - Capabilities: tool_use, streaming (depends on hosting)
   - Pricing: Self-hosted (compute cost only)

### 1.3 Capability Mapping

**Per-Provider Capability Map**:
```typescript
const capabilityMatrix = {
  tool_use: {
    anthropic: { native: true, format: 'claude_tools' },
    deepseek: { native: true, format: 'openai_tools' },
    qwen: { native: true, format: 'qwen_tools' },
    openai: { native: true, format: 'openai_tools' },
    open_weights: { native: false, format: 'prompt_based' }
  },
  vision: {
    anthropic: { native: true, formats: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'] },
    deepseek: { native: false },
    qwen: { native: true, formats: ['image/jpeg', 'image/png'] },
    openai: { native: true, formats: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'] },
    open_weights: { native: false }
  },
  thinking: {
    anthropic: { native: true, extended: true },
    deepseek: { native: true, extended: false },
    qwen: { native: false },
    openai: { native: true, extended: false },
    open_weights: { native: false }
  },
  streaming: {
    anthropic: { native: true, sse: true },
    deepseek: { native: true, sse: true },
    qwen: { native: true, sse: true },
    openai: { native: true, sse: true },
    open_weights: { native: true, sse: true }
  }
};
```

---

## 2. Routing Policy

### 2.1 Decision Mechanism (RouteLLM Foundation)

**Router Types**:

1. **Matrix Factorization (mf)** - Recommended default
   - Trained on preference data
   - Fast inference (<10ms)
   - Good generalization

2. **Similarity-Weighted Ranking (sw_ranking)**
   - Uses weighted Elo calculations
   - Based on prompt similarity
   - No training required

3. **BERT Classifier**
   - BERT model trained on preferences
   - Higher accuracy, slower inference (~50ms)
   - Good for complex queries

4. **Causal LLM**
   - LLM-based classifier
   - Highest accuracy, slowest inference (~200ms)
   - Best for critical decisions

**Routing Algorithm**:
```python
def route_request(query: str, context: Context) -> RoutingDecision:
    # 1. Calculate strong model win rate
    win_rate = router.calculate_strong_win_rate(query)
    
    # 2. Apply threshold
    if win_rate > threshold:
        model_tier = 'premium'  # Use strong model
    else:
        model_tier = 'cheap'    # Use weak model
    
    # 3. Select specific model based on requirements
    model = select_model(
        tier=model_tier,
        capabilities=context.required_capabilities,
        provider_preference=context.provider_preference
    )
    
    # 4. Determine sampling strategy (BEST-Route)
    num_samples = determine_samples(
        query_difficulty=win_rate,
        model_tier=model_tier,
        cost_budget=context.cost_budget
    )
    
    return RoutingDecision(
        model=model,
        num_samples=num_samples,
        reasoning=f"Win rate: {win_rate:.3f}, Threshold: {threshold:.3f}"
    )
```

### 2.2 Routing Strategies

**Strategy 1: Reasoning-Heavy Tasks**
- Trigger: Complex logic, multi-step reasoning, code generation
- Route to: claude-opus-4, deepseek-r1, o1, o3
- Sampling: 1 sample (reasoning models are expensive)
- Cost: High ($15-60 per MTok output)

**Strategy 2: Standard Tasks**
- Trigger: General coding, documentation, analysis
- Route to: claude-sonnet-4, deepseek-v3, qwen-3-235b, gpt-4o
- Sampling: 1-2 samples
- Cost: Medium ($1.50-15 per MTok output)

**Strategy 3: Simple/Repetitive Tasks**
- Trigger: Formatting, simple edits, boilerplate
- Route to: claude-haiku-4, deepseek-lite, qwen-2.5-7b, gpt-4o-mini
- Sampling: 3-5 samples (best-of-n)
- Cost: Low ($0.20-4 per MTok output)

**Strategy 4: Memory-Augmented (Breakthrough)**
- Trigger: Repeat query detected in memory
- Route to: Cheap model + memory retrieval
- Sampling: 1 sample (memory provides context)
- Cost: Ultra-low (memory lookup + cheap inference)

### 2.3 Cascade Logic (FrugalGPT)

**Sequential Escalation**:
```python
def cascade_route(query: str, quality_threshold: float) -> Response:
    models = [
        ('cheap', 3),      # Try cheap model with 3 samples
        ('standard', 2),   # Escalate to standard with 2 samples
        ('premium', 1)     # Final escalation to premium
    ]
    
    for tier, num_samples in models:
        responses = []
        for _ in range(num_samples):
            response = generate(query, tier)
            responses.append(response)
        
        best_response = select_best(responses)
        quality = evaluate_quality(best_response)
        
        if quality >= quality_threshold:
            return best_response  # Early stopping
    
    # If all fail, return best attempt
    return best_response
```

**Early Stopping Conditions**:
- Quality score > threshold
- Confidence score > threshold
- Verification tests pass
- User satisfaction signal

---

## 3. Cost & Latency Targets

### 3.1 Cost Optimization Goals

**Baseline** (all premium models):
- Average cost: $45 per MTok output
- Target: 60-85% cost reduction

**Target** (intelligent routing):
- Average cost: $6.75-18 per MTok output
- Maintain 95%+ quality vs. baseline

**Cost Breakdown by Strategy**:
- Reasoning-heavy: 10% of queries, $15-60 per MTok
- Standard: 40% of queries, $1.50-15 per MTok
- Simple: 40% of queries, $0.20-4 per MTok
- Memory-augmented: 10% of queries, $0.10-0.50 per MTok

**Weighted Average**:
```
Cost = 0.10 × $37.50 + 0.40 × $8.25 + 0.40 × $2.10 + 0.10 × $0.30
     = $3.75 + $3.30 + $0.84 + $0.03
     = $7.92 per MTok output
```

**Savings**: 82% vs. all-premium baseline

### 3.2 Latency Targets

**Routing Decision**: <50ms
- Matrix Factorization: <10ms
- Similarity-Weighted: <20ms
- BERT Classifier: <50ms
- Causal LLM: <200ms (use sparingly)

**Model Inference** (P50):
- Cheap models: 500-1000ms
- Standard models: 1000-2000ms
- Premium models: 2000-4000ms
- Reasoning models: 5000-15000ms

**Total Latency Budget**:
- Simple queries: <1500ms (routing + cheap model)
- Standard queries: <2500ms (routing + standard model)
- Complex queries: <5000ms (routing + premium model)
- Reasoning queries: <20000ms (routing + reasoning model)

---

## 4. Router ↔ Skills Interop

### 4.1 Skill Complexity Metadata

**Skill declares requirements**:
```yaml
---
id: senior-frontend
complexity: medium
estimated_tokens: 1200
min_model_tier: standard
recommended_models:
  - claude-sonnet-4
  - deepseek-v3
  - qwen-3-235b
  - gpt-4o
capabilities_required:
  - tool_use
  - streaming
capabilities_optional:
  - thinking
---
```

### 4.2 Router Uses Skill Metadata

**Routing Decision with Skill Context**:
```python
def route_with_skill(query: str, skill: Skill) -> RoutingDecision:
    # 1. Filter models by skill requirements
    eligible_models = filter_models(
        min_tier=skill.min_model_tier,
        required_capabilities=skill.capabilities_required
    )
    
    # 2. Calculate win rate for query
    win_rate = router.calculate_strong_win_rate(query)
    
    # 3. Adjust threshold based on skill complexity
    adjusted_threshold = base_threshold * skill.complexity_multiplier
    
    # 4. Select model
    if win_rate > adjusted_threshold:
        model = select_from_tier(eligible_models, 'premium')
    else:
        model = select_from_tier(eligible_models, skill.min_model_tier)
    
    # 5. Determine sampling
    num_samples = determine_samples(win_rate, model.tier)
    
    return RoutingDecision(model, num_samples)
```

### 4.3 Skill-Specific Routing Policies

**Engineering Skills** (high complexity):
- Min tier: standard
- Prefer: claude-sonnet-4, deepseek-v3
- Sampling: 1-2
- Reasoning: Use premium for architecture decisions

**Product/Design Skills** (medium complexity):
- Min tier: cheap
- Prefer: claude-haiku-4, qwen-2.5-72b
- Sampling: 2-3
- Reasoning: Rarely needed

**Brainstorming Skills** (low complexity):
- Min tier: cheap
- Prefer: deepseek-lite, qwen-2.5-7b
- Sampling: 3-5
- Reasoning: Never needed

---

## 5. Parity Implementation (A)

### 5.1 RouteLLM Cascade

**4 Router Types**:
- Matrix Factorization (mf) - default
- Similarity-Weighted Ranking (sw_ranking)
- BERT Classifier
- Causal LLM

**Preference-Based Training**:
- Train on human preference data (Chatbot Arena, custom datasets)
- Learn query difficulty patterns
- Transfer learning across model pairs

**Threshold Calibration**:
- Calibrate on representative query dataset
- Set threshold for desired strong model usage %
- Example: 50% usage → threshold = 0.11593 (mf router)

### 5.2 FrugalGPT Cascade

**Sequential Escalation**:
1. Try cheap model with multiple samples
2. Evaluate quality with reward model
3. If quality < threshold, escalate to next tier
4. Repeat until quality met or max tier reached

**Early Stopping**:
- Stop as soon as quality threshold met
- Avoid unnecessary expensive calls
- Achieve 98% cost reduction in best case

**Prompt Adaptation**:
- Optimize prompts per model tier
- Cheap models get more explicit instructions
- Premium models get concise prompts

---

## 6. Breakthrough Implementation (B)

> **Architecture Slice**: This breakthrough implements [§3: Provider-Aware Router](../BREAKTHROUGH-ARCHITECTURE.md) of [BREAKTHROUGH-ARCHITECTURE.md](../BREAKTHROUGH-ARCHITECTURE.md) — specifically the memory-augmented cascade routing with provider capability matching.

### 6.1 Memory-Augmented Routing

**Core Insight** (Knowledge Access Beats Model Size):
- Small model + relevant memory > large model alone
- Repeat queries benefit from cached context
- Memory retrieval is cheaper than inference

**Implementation**:
```python
def memory_augmented_route(query: str) -> RoutingDecision:
    # 1. Check if query is similar to previous queries
    similar_queries = memory.search(query, threshold=0.85)
    
    if similar_queries:
        # 2. Retrieve cached context
        context = memory.get_context(similar_queries[0].id)
        
        # 3. Route to cheap model with memory
        return RoutingDecision(
            model=select_model(tier='cheap'),
            num_samples=1,
            context=context,
            reasoning="Similar query found in memory"
        )
    else:
        # 4. No memory hit, use standard routing
        return standard_route(query)
```

**Memory Structure**:
```typescript
interface MemoryEntry {
  id: string;
  query: string;
  query_embedding: number[];
  response: string;
  model_used: string;
  quality_score: number;
  timestamp: number;
  context: {
    files_read: string[];
    tools_used: string[];
    key_insights: string[];
  };
}
```

**Expected Gains**:
- 90%+ cost reduction for repeat queries
- <100ms memory lookup latency
- Improved consistency across similar queries
- Learning from past successful executions

### 6.2 Dynamic Sampling (BEST-Route)

**Adaptive Best-of-N**:
```python
def determine_samples(query_difficulty: float, model_tier: str) -> int:
    if model_tier == 'premium':
        return 1  # Premium models are expensive, single sample
    elif model_tier == 'standard':
        if query_difficulty > 0.7:
            return 2  # Harder queries get 2 samples
        else:
            return 1
    else:  # cheap
        if query_difficulty > 0.8:
            return 5  # Very hard queries get 5 samples
        elif query_difficulty > 0.5:
            return 3
        else:
            return 1  # Easy queries get 1 sample
```

**Sample Selection**:
- Generate N responses from cheap model
- Score with reward model
- Select best response
- If best score > threshold, use it
- Otherwise, escalate to stronger model

**Cost-Quality Tradeoff**:
- 5 samples from cheap model < 1 sample from premium
- Example: 5 × $0.28 = $1.40 < $75 (Opus)
- Achieve premium quality at 98% cost reduction

---

## 7. Implementation Roadmap

### Phase 1: Provider Abstraction (Weeks 1-2)
- Define unified Provider interface
- Implement provider adapters (Anthropic, DeepSeek, Qwen, OpenAI)
- Build capability mapping
- Create provider registry

### Phase 2: Basic Routing (Weeks 3-4)
- Implement Matrix Factorization router
- Add threshold calibration
- Build model selection logic
- Create routing decision logger

### Phase 3: Advanced Routing (Weeks 5-6)
- Add Similarity-Weighted Ranking router
- Implement BERT Classifier router
- Add Causal LLM router
- Build router comparison framework

### Phase 4: Cascade & Sampling (Weeks 7-8)
- Implement FrugalGPT cascade
- Add dynamic sampling (BEST-Route)
- Build quality evaluation framework
- Create early stopping logic

### Phase 5: Memory Integration (Weeks 9-10)
- Build memory storage and retrieval
- Implement similarity search
- Add memory-augmented routing
- Create memory management policies

### Phase 6: Skills Integration (Weeks 11-12)
- Integrate with skills system (§4.4)
- Add skill-aware routing
- Implement skill-specific policies
- Build end-to-end testing framework

---

## 8. Success Metrics

### Cost Metrics
- 60-85% cost reduction vs. all-premium baseline
- Target: $6.75-18 per MTok output
- Memory-augmented: 90%+ reduction for repeat queries

### Quality Metrics
- 95%+ quality vs. premium baseline
- <1% performance drop with BEST-Route
- Maintain user satisfaction scores

### Latency Metrics
- Routing decision: <50ms (P50)
- Total latency within budget per query type
- Memory lookup: <100ms

### Efficiency Metrics
- 50% of queries routed to cheap models
- 40% to standard models
- 10% to premium/reasoning models
- Early stopping rate: 70%+ in cascade

---

## 9. Risk Mitigation

### Risk: Provider Outages
**Mitigation**: Multi-provider fallback, automatic retry with different provider

### Risk: Quality Degradation
**Mitigation**: Continuous quality monitoring, automatic escalation on low scores

### Risk: Cost Overruns
**Mitigation**: Budget caps, cost alerts, automatic downgrade to cheaper models

### Risk: Latency Spikes
**Mitigation**: Timeout policies, fallback to faster models, caching

### Risk: Router Inaccuracy
**Mitigation**: Multiple router types, ensemble voting, human feedback loop

---

## 10. Future Enhancements

### Reinforcement Learning Router
- Learn from execution outcomes
- Adapt to user preferences
- Optimize for custom objectives

### Multi-Objective Optimization
- Balance cost, latency, quality
- Pareto frontier exploration
- User-configurable tradeoffs

### Provider-Specific Optimizations
- Leverage unique capabilities (Claude thinking, DeepSeek long context)
- Automatic feature detection
- Graceful degradation

### Enterprise Features
- Cost allocation and tracking
- Provider quotas and limits
- Compliance and audit logging
- SLA guarantees

## 11. Changelog

**2026-05-31 — Run 3**: Linked to unified BREAKTHROUGH-ARCHITECTURE.md. This plan's (B) tier implements §3: Provider-Aware Router of the architecture.
