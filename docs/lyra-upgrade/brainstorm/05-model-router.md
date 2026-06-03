# Brainstorm — Model Router (§4.5)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Source Techniques Gathered

| Technique | Source | Core Idea | Key Numbers |
|-----------|--------|-----------|-------------|
| RouteLLM | LMSYS/Berkeley | Learned router for cost/quality trade-off | Matthews corr 0.62 |
| BEST-Route | Microsoft (ICML 2025) | Route model + #samples by difficulty | — |
| Hybrid LLM | Microsoft (ICLR 2024) | Cost/quality router for cascading | — |
| FrugalGPT | Stanford | LLM cascade — cheap first, escalate on low confidence | 98% cost reduction |
| Knowledge Access > Model Size | (2603.23013) | Memory lets cheap model answer repeats | 96% cost reduction |
| Diffusion LM Bitter Lesson | (2601.12979) | NEGATIVE: don't route agentic tasks to diffusion LMs | — |
| Claude Code Effort | Anthropic | 6-tier effort: low→max→ultracode | Per-model thinking budgets |

---

## Breakthrough Idea #1: Memory-Augmented Routing (Knowledge Access + Cost-Sensitive Stores)

**Sources Fused:** Knowledge Access Beats Model Size (2603.23013) + Cost-Sensitive Store Routing (iGRGjdhl9r) + FrugalGPT cascade

**Core Mechanism:**
- Every query + its answer is cached in memory with an embedding
- New query: compute embedding similarity to cached queries
- If similarity > threshold (0.92): route to cheap model with cached answer as context → ~96% cost reduction
- If similarity medium (0.7-0.92): route to mid-tier model with top-3 cached answers as context
- If similarity low (<0.7): route to expensive model for first-time reasoning
- The router itself is a cheap model decision (~10 tokens)
- Learning: track when cheap model answers were overridden, adjust thresholds

**Why It Beats Baseline:** Lyra has no routing. This alone could cut per-session cost by 40-60%.
**Impact:** 5 | **Effort:** 3 | **Risk:** Low

---

## Breakthrough Idea #2: Capability-Aware Multi-Provider Router with Degradation Map

**Sources Fused:** RouteLLM + Diffusion LM Bitter Lesson + Claude Code Effort + Provider Capability Matrix

**Core Mechanism:**
- Each provider registers its capabilities: tools (Y/N), vision (Y/N), audio (Y/N), JSON mode (Y/N), long context (Y/N), reasoning (Y/N), max context window, pricing tiers
- Router maintains a "degradation map" — for each capability, what to do when the active provider lacks it:
  - No vision? → describe images via OCR, route description to text model
  - No tools? → prompt-based instruction following, fallback to cheaper provider that HAS tools
  - No JSON mode? → regex extraction, retry with stronger formatting prompt
- Diffusion LM negative result: the router has a BLACKLIST — never route tool-calling/agentic tasks to models known to fail at them
- Task classifier: code_task → requires tools, JSON; reasoning_task → requires long context; research_task → requires web search; voice_task → requires audio

**Why It Beats Baseline:** Single hardcoded model means Lyra can't even use different providers.
**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: Effort Scale as Provider-Neutral Reasoning Budget

**Sources Fused:** Claude Code /effort menu + Anthropic effort API + DeepSeek thinking tokens + GPT reasoning_effort

**Core Mechanism:**
- Unified 6-tier effort scale (low/medium/high/xhigh/max/ultracode) mapped per-provider:

| Effort | Anthropic | DeepSeek | GPT | Open-Weights |
|--------|-----------|----------|-----|--------------|
| low | thinking: 1024 | prompt: "be concise, one attempt" | reasoning: low | max_tokens: 512 |
| medium | thinking: 4096 | default config | reasoning: medium | max_tokens: 2048 |
| high | thinking: 8192 | extended thinking enabled | reasoning: high | max_tokens: 4096 |
| xhigh | thinking: 16384 | CoT prompting + self-check | reasoning: max | max_tokens: 8192 |
| max | thinking: 31999 | CoT + multi-round self-critique | reasoning: max + extended | max_tokens: 16384 |
| ultracode | thinking: 16384 + orchestration ON | CoT + orchestration ON | reasoning: max + orch. ON | max_tokens: 8192 + orch. ON |

- Ultracode is NOT a 6th API budget tier — it's "xhigh + orchestration toggle"
- This makes it portable to providers with fewer effort levels (DeepSeek has no budget_tokens API)
- For providers with no thinking budget: use prompt-level analogs (CoT instructions, self-critique, multi-round)

**Why It Beats Baseline:** No effort concept exists in Lyra — every query gets the same model with default settings regardless of task complexity.
**Impact:** 5 | **Effort:** 3 | **Risk:** Low

---

## Expert Check (Router Personas)

**Senior AI Engineer (LLMOps):** "Idea #1 (memory-augmented routing) is the highest-impact, lowest-risk breakthrough. The Knowledge Access paper already proves the concept. Idea #2 (capability-aware degradation) is essential for multi-provider but adds complexity. Idea #3 (effort scale) is the foundation everything else builds on."

**Senior Performance/Cost Engineer:** "The 96% cost reduction from Knowledge Access is the headline number. Even at 50% reduction, memory-augmented routing pays for itself in a week. Ship Idea #1 first."

**Adversarial Skeptic:** "Idea #1 assumes queries repeat — how often does that actually happen? If every query is novel, the cache hit rate is 0% and we've just added routing overhead. Prove the cache-hit assumption with real Lyra usage data before making it the default."

**Resolution:** Idea #3 (effort scale) is the (A) parity foundation. Idea #1 (memory-augmented routing) is the (B) breakthrough — gated behind cache-hit rate data from production. Idea #2 (capability-aware degradation) ships alongside the provider abstraction.
