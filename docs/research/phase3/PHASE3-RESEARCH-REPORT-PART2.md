# Phase 3 Research Report: Part 2 - Model Routing

## §3.14 MODEL ROUTING SYSTEMS

### 1. RouteLLM (lm-sys)

**Source:** [lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM)

**Design Pattern:**
- Framework for serving and evaluating LLM routers
- Binary classifiers for strong vs weak model routing
- Multi-model routing (R2-Router, IRT-Router)
- Feature-based approaches for efficient model selection

**Benchmark Results:**
- Maintain 95% of frontier model quality while routing 85% of queries to cheaper models
- Cost reductions of 45-85% depending on workload
- Minimal quality degradation (<5%)

**Technique:**
- Analyzes query difficulty using multiple signals
- Routes easy queries to cheaper models (Haiku, GPT-4o-mini)
- Routes hard queries to expensive models (Opus, GPT-5)
- Supports multiple routing strategies: similarity-weighted, matrix factorization, BERT-based

**Lyra Relevance:** ⭐⭐⭐⭐⭐
- Direct cost optimization for Lyra's multi-provider architecture
- 45-85% cost reduction is transformative
- Framework provides production-ready implementation

**Adoption Strategy:**
1. Integrate RouteLLM as routing layer in lyra-core
2. Train router on Lyra's query distribution
3. Configure provider tiers: Haiku (cheap) → Sonnet (mid) → Opus/DeepSeek-V3 (expensive)
4. Add cost tracking and router performance monitoring
5. Implement fallback strategies for router failures

**Multi-Provider Notes:**
- Explicitly designed for heterogeneous LLM routing
- Works with any provider that supports function calling
- Router can be trained on mixed provider data
- Cost models need provider-specific pricing
- Quality thresholds may vary by provider

**Impact × Effort:** VERY HIGH × MEDIUM
- Very high impact: 45-85% cost reduction
- Medium effort: Integration + training + monitoring

**References:**
- [RouteLLM GitHub](https://github.com/lm-sys/RouteLLM)
- [Blog: How to Stop Paying Frontier Model Prices](https://tianpan.co/blog/2025-10-19-llm-routing-production)

---

### 2. BEST-Route (Microsoft)

**Source:** [microsoft/best-route-llm](https://github.com/microsoft/best-route-llm) | [arXiv:2506.22716](https://arxiv.org/abs/2506.22716)

**Design Pattern:**
- Adaptive LLM routing with test-time optimal compute
- Selects both model AND number of responses based on query difficulty
- Multi-sampling strategy: generate N responses, select best
- Dynamic quality threshold tuning

**Benchmark Results:**
- Up to 60% cost reduction with <1% performance drop
- Outperforms fixed routing strategies
- Adaptive to workload characteristics

**Technique:**
- Estimates query difficulty using lightweight classifier
- Easy queries → single response from cheap model
- Medium queries → multiple responses from mid-tier model, select best
- Hard queries → frontier model with multiple samples
- Quality threshold adjustable at test time

**Lyra Relevance:** ⭐⭐⭐⭐⭐
- Multi-sampling strategy improves reliability
- Dynamic threshold enables user control (speed vs quality)
- 60% cost reduction with minimal quality loss

**Adoption Strategy:**
1. Implement difficulty classifier for Lyra queries
2. Add multi-sampling capability to lyra-core
3. Build response selection mechanism (voting, scoring)
4. Create quality threshold API for user control
5. Add adaptive sampling based on user feedback

**Multi-Provider Notes:**
- Multi-sampling works across all providers
- Response selection is provider-agnostic
- Difficulty estimation may need provider-specific features
- Cost models must account for multiple samples

**Impact × Effort:** VERY HIGH × HIGH
- Very high impact: 60% cost reduction + quality improvement
- High effort: Requires classifier, multi-sampling, selection logic

**References:**
- [BEST-Route GitHub](https://github.com/microsoft/best-route-llm)
- [Paper](https://arxiv.org/abs/2506.22716)

---

### 3. Hybrid LLM (Microsoft Foundry)

**Source:** [Microsoft Research](https://www.microsoft.com/en-us/research/publication/hybrid-llm-cost-efficient-and-quality-aware-query-routing/) | [Foundry Model Router](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/model-router-agents)

**Design Pattern:**
- Cost-efficient and quality-aware query routing
- Hybrid inference: local model for simple/sensitive, cloud for complex
- Per-turn routing (not per-session)
- Real-time prompt analysis

**Benchmark Results:**
- Significant cost reduction while maintaining quality
- Latency reduction for simple queries (local execution)
- Privacy preservation for sensitive queries

**Technique:**
- Lightweight local model classifies requests first
- Simple queries → stay on-device (fast, private, free)
- Complex queries → escalate to cloud frontier models
- Sensitive queries → stay local for privacy
- Router assigns queries based on predicted difficulty and quality threshold

**Lyra Relevance:** ⭐⭐⭐⭐
- Hybrid architecture enables privacy-preserving local execution
- Per-turn routing provides fine-grained control
- Quality threshold tuning enables user preferences

**Adoption Strategy:**
1. Implement local lightweight model for classification
2. Add privacy detection for sensitive queries
3. Build escalation logic to cloud providers
4. Create quality threshold configuration
5. Add latency tracking for routing decisions

**Multi-Provider Notes:**
- Local model can be any small LLM (Phi-3, Gemma, Llama-3.2)
- Cloud routing works with any provider
- Privacy detection is provider-agnostic
- Hybrid architecture reduces vendor lock-in

**Impact × Effort:** HIGH × HIGH
- High impact: Cost + latency + privacy benefits
- High effort: Requires local model deployment + classification logic

**References:**
- [Hybrid LLM Paper](https://www.microsoft.com/en-us/research/publication/hybrid-llm-cost-efficient-and-quality-aware-query-routing/)
- [Foundry Model Router](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/model-router-agents)

---

### 4. FrugalGPT (Stanford)

**Source:** [stanford-futuredata/FrugalGPT](https://github.com/stanford-futuredata/FrugalGPT) | [arXiv:2305.05176](https://arxiv.org/abs/2305.05176)

**Design Pattern:**
- Cascading: route queries through models from cheapest to most expensive
- Prompt adaptation: optimize prompts per model
- Caching: reuse responses for similar queries
- Adaptive selection: choose which LLMs to use per query

**Benchmark Results:**
- Match GPT-4 performance with up to 98% cost reduction
- Improve accuracy over GPT-4 by 4% at same cost
- Demonstrated on news classification, reading comprehension, scientific QA

**Technique:**
- Start with cheapest model
- If confidence is low, escalate to next tier
- Continue until confidence threshold met or reach most expensive model
- Cache responses for similar queries
- Adapt prompts to each model's strengths

**Lyra Relevance:** ⭐⭐⭐⭐
- Cascading strategy is simple and effective
- Caching reduces redundant API calls
- Prompt adaptation improves per-model performance

**Adoption Strategy:**
1. Implement cascading router in lyra-core
2. Add confidence estimation for responses
3. Build semantic caching layer
4. Create per-provider prompt templates
5. Add escalation tracking and cost monitoring

**Multi-Provider Notes:**
- Cascading works with any provider hierarchy
- Confidence estimation may need provider-specific calibration
- Caching is provider-agnostic
- Prompt adaptation requires provider-specific templates

**Impact × Effort:** HIGH × MEDIUM
- High impact: Up to 98% cost reduction
- Medium effort: Cascading + caching + confidence estimation

**References:**
- [FrugalGPT GitHub](https://github.com/stanford-futuredata/FrugalGPT)
- [Paper](https://arxiv.org/abs/2305.05176)

---

### 5. Knowledge Access Beats Model Size (Memory-Augmented Routing)

**Source:** [arXiv:2603.23013](https://arxiv.org/abs/2603.23013)

**Design Pattern:**
- Memory-augmented inference framework
- Lightweight 8B model + retrieved conversational context
- Low-cost inference path for repetitive queries
- Knowledge retrieval beats larger models

**Benchmark Results:**
- 47% of production queries are semantically similar to prior interactions
- 8B model + memory matches frontier model performance on repetitive queries
- Significant cost reduction for high-repetition workloads

**Technique:**
- Detect query similarity to conversation history
- Retrieve relevant prior context
- Route to lightweight model with augmented context
- Fallback to frontier model for novel queries
- Build memory index for fast retrieval

**Lyra Relevance:** ⭐⭐⭐⭐⭐
- Lyra's conversation history is valuable routing signal
- Memory augmentation enables cheaper inference
- Particularly valuable for iterative workflows (debugging, refactoring)

**Adoption Strategy:**
1. Build conversation memory index in lyra-memory
2. Implement semantic similarity detection
3. Add memory-augmented routing path
4. Configure lightweight model for repetitive queries
5. Track memory hit rate and cost savings

**Multi-Provider Notes:**
- Memory retrieval is provider-agnostic
- Lightweight model can be any 8B+ model (DeepSeek-Coder, Llama-3.1)
- Similarity detection works across providers
- Memory format should be provider-neutral

**Impact × Effort:** VERY HIGH × MEDIUM
- Very high impact: Leverages Lyra's existing memory system
- Medium effort: Similarity detection + routing logic

**References:**
- [Paper](https://arxiv.org/abs/2603.23013)

---

## §3.14 MODEL ROUTING: SYNTHESIS

**Top 3 Recommendations for Lyra:**

1. **RouteLLM + BEST-Route** (CRITICAL PATH)
   - RouteLLM provides production-ready routing framework
   - BEST-Route adds multi-sampling for quality improvement
   - Combined: 60-85% cost reduction with quality guarantees

2. **Memory-Augmented Routing** (LEVERAGE EXISTING ASSETS)
   - Lyra already has conversation memory
   - 47% of queries are repetitive → huge cost savings
   - Lightweight model + memory beats frontier model

3. **FrugalGPT Cascading** (SIMPLE + EFFECTIVE)
   - Easy to implement cascading strategy
   - Caching provides additional savings
   - Prompt adaptation improves per-provider performance

**Implementation Priority:**
1. Phase 1: Implement RouteLLM framework (2 weeks)
2. Phase 2: Add memory-augmented routing (1 week - leverages existing memory)
3. Phase 3: Integrate BEST-Route multi-sampling (2 weeks)
4. Phase 4: Add FrugalGPT caching and cascading (1 week)

**Cost Reduction Estimate:**
- RouteLLM alone: 45-85% reduction
- + Memory augmentation: additional 20-30% on repetitive queries
- + BEST-Route multi-sampling: <1% quality loss, 60% cost reduction
- **Combined: 70-90% cost reduction with quality improvement**

**Multi-Provider Strategy:**
- Tier 1 (Cheap): Haiku 4.5, DeepSeek-Coder-8B, GPT-4o-mini
- Tier 2 (Mid): Sonnet 4.6, DeepSeek-V3, GPT-5.5
- Tier 3 (Expensive): Opus 4.8, GPT-5, DeepSeek-V3-671B
- Memory-augmented: Use Tier 1 with conversation context
- Cascading: Start Tier 1 → escalate to Tier 2 → Tier 3 if needed

---
