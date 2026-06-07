# Lyra Upgrade — Research Update (June 2026)
> Web-sourced developments since the original 546-source corpus was finalized.
> Adds 15 new sources across harness engineering, multi-agent, memory, voice, and safety.

## Executive Summary

Three months of additional research have validated Lyra's architecture decisively:
1. **Harness engineering is now the consensus frontier** — Anthropic, OpenAI, LangChain, and multiple ICLR 2026 papers independently confirm that the harness, not the model, determines agent capability
2. **Self-evolving harnesses have arrived** — meta-learning loops that optimize the harness itself (Adaptive Auto-Harness, AHE, Polar, "The Last Harness") prove the §4.27 RL Optimizer direction
3. **Voice Mode is production-standard** — Claude Code shipped it, validating Lyra's §4.18 flagship priority
4. **Memory consolidation ("Dreaming") is shipping** — AutoDream in Claude Code, FORGE population broadcast, MemGen latent tokens all converge on Lyra's §4.24 design
5. **Safety misevolution is the critical open problem** — ICLR 2026 and NeurIPS 2025 papers confirm Lyra's §4.17 guardrails are on the right track

---

## 1. Harness Engineering — The Paradigm Validated

### Anthropic: "Harness Design for Long-Running Apps" (2026)
> *"The same model can produce 20× better results with a well-designed harness."*

Anthropic's experiments showed a broken $9 solo-agent run vs. a fully functional $200 harness run on the same coding task with the same model. Three-agent GAN-inspired architecture: Planner → Generator → Evaluator. The Evaluator uses Playwright MCP to test like a real user.

**Lyra implication:** The harness-first thesis (§3.28, OpenJarvis) is confirmed by the leading provider. Invest in harness quality above model upgrades.

### "The Last Harness You'll Ever Build" (Seong et al., April 2026, arXiv:2604.21003)
Meta-learning with two nested loops:
- Inner: Worker → Evaluator (adversarial diagnosis) → Evolution Agent (modify harness)
- Outer: Optimize the evolution blueprint itself across diverse tasks

> Zero human harness engineering for new tasks after meta-training.

**Lyra implication:** This is the §4.27 RL Optimizer's endgame — not just evolving prompts, but evolving the harness architecture itself.

### Adaptive Auto-Harness (Liu et al., June 2026, arXiv:2606.01770)
Stateful multi-agent evolver with harness tree routing. Different harness branches for different task types. Critical finding: *"A single repeatedly updated harness becomes brittle, causing performance to peak early and then decline."*

**Lyra implication:** Validates the OpenJarvis 5-primitive approach — different failure modes need different primitives edited (Intelligence vs Tools vs Agent vs Engine vs Learning).

### Agentic Harness Engineering — AHE (Lin et al., April 2026, arXiv:2604.25850)
Closed-loop observability-driven evolution. Three pillars: component observability (file-level), experience observability (drill-down from raw traces), decision observability (falsifiable predictions per edit). Results: +5.1 to +10.1pp cross-family gains when transferred.

**Lyra implication:** The DEBATE_LEDGER.md pattern is exactly "decision observability." Add component-level traceability per edit.

### Polar: Agentic RL on Any Harness (Xu et al., May 2026, arXiv:2605.24220)
Treats agent harness as black box, proxies LLM API calls, reconstructs token-faithful trajectories. +22.6 points on SWE-Bench Verified with Qwen3.5-4B + GRPO.

**Lyra implication:** Lyra's multi-provider design makes this directly applicable. Each provider backend can be wrapped as a Polar-compatible harness.

---

## 2. Claude Code 2026 — Direct Port Targets

| Feature | Lyra Equivalent | Status |
|---------|----------------|--------|
| **Voice Mode** (/voice, PTT, 20 languages) | §4.18 — Tier A implemented | ✅ Builds on existing voice pipeline |
| **Tasks System** (DAG, persistent, cross-session) | §4.13 supervisor + workflow engine | Existing foundation |
| **Kairos daemon** (persistent background, proactive) | §4.13 supervisor daemon | Existing foundation |
| **AutoDream** (idle consolidation, dedup, trim) | §4.24 dreaming consolidator | Existing consolidation loop |
| **Agent View** (fleet overview screen) | §4.13 fleet TUI | Existing scaffold |
| **/loop scheduled tasks** (cron-style) | §4.14 autonomy scheduled mode | Existing RunMode.SCHEDULED |
| **Computer Use** (remote desktop control) | §4.28 desktop | Deferred |
| **1M context window** | §4.3 context compaction | Existing M_t pattern |

---

## 3. New Papers for the Corpus

### Memory — 4 new sources

| Paper | Venue | Key Finding | Lyra Route |
|-------|-------|------------|------------|
| **MemGen** (arXiv:2605.????) | ICLR 2026 | Generative latent memory tokens woven into inference stream, no external DB. +38.22% over ExpeL/AWM. Spontaneously evolves planning, procedural, working memory | §4.2 |
| **G-Memory** (NeurIPS 2025) | NeurIPS 2025 | 3-tier hierarchical memory (insight→query→interaction graphs) for multi-agent. Bi-directional traversal. +20.89% on embodied tasks | §4.2, §4.13 |
| **FORGE** (arXiv:2605.16233) | 2026 | Population broadcast propagates best memory across agents. 1.7-7.7× reward improvement. Weaker models benefit disproportionately | §4.2, §4.13 |
| **MemoryAgentBench** (arXiv:2507.05257) | ICLR 2026 | Selective forgetting is hardest challenge — best method ~7% accuracy. Validates Lyra's active forgetting design | §4.2, §4.24 |

### Safety — 2 new sources

| Paper | Venue | Key Finding | Lyra Route |
|-------|-------|------------|------------|
| **GUARDIAN** (NeurIPS 2025) | NeurIPS 2025 | Temporal graph modeling detects hallucination amplification in multi-agent. Information Bottleneck Theory | §4.17, §4.13 |
| **Misevolve** update | ICLR 2026 Oral | Four-pathway misevolution (model, memory, tool, workflow). Even Gemini-2.5-Pro degrades | §4.17, §4.4 |

### Self-Evolving — 1 new source

| Paper | Venue | Key Finding | Lyra Route |
|-------|-------|------------|------------|
| **ReasoningBank** (Google) | ICLR 2026 | Memory-aware Test-Time Scaling (MaTTS). More compute → richer memory → better guidance. Emergent self-evolution | §4.27, §4.2 |

---

## 4. Updated Recommendations

### P0 — Integrate immediately
1. **FORGE population broadcast** for cross-agent memory sharing (§4.2 + §4.13)
2. **AutoDream consolidation loop** — already have the infrastructure, add the idle-triggered review cycle
3. **AHE-style edit traceability** — each harness edit paired with a falsifiable prediction

### P1 — Add to plans
4. **MemGen latent memory tokens** — alternative to external DB, worth exploring for on-device Lyra
5. **GUARDIAN temporal graph safety** — add to the §4.17 defense-in-depth pipeline
6. **Adaptive Auto-Harness tree routing** — extend §4.27 with task-type-specific harness branches

### P2 — Monitor and revisit
7. **Polar RL integration** — once Lyra has enough trajectory data for training
8. **"Last Harness" meta-learning** — long-term vision for fully automated harness engineering

---

## Sources

1. [Anthropic — Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) — 20× improvement from harness alone
2. [Adaptive Auto-Harness](https://export.arxiv.org/abs/2606.01770) (Liu et al., June 2026) — stateful multi-agent evolver
3. [The Last Harness You'll Ever Build](https://browse-export.arxiv.org/abs/2604.21003) (Seong et al., April 2026) — meta-learning harness engineering
4. [Agentic Harness Engineering — AHE](https://browse-export.arxiv.org/abs/2604.25850) (Lin et al., April 2026) — observability-driven auto-evolution
5. [Polar: Agentic RL on Any Harness](https://export.arxiv.org/abs/2605.24220) (Xu et al., May 2026) — black-box RL +22.6pp SWE-Bench
6. [Claude Code Voice Mode](https://techstory.in/anthropic-unveils-voice-mode-for-claude-code/) — push-to-talk, 20 languages, full-duplex
7. [Claude Code Tasks Update](https://venturebeat.com/orchestration/claude-codes-tasks-update-lets-agents-work-longer-and-coordinate-across) — DAG-based persistent cross-session tasks
8. [MemGen — ICLR 2026](https://iclr.cc/virtual/2026/poster/10006821) — generative latent memory, +38.22%
9. [G-Memory — NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/136a45cd9b841bf785625709a19c6508-Abstract-Conference.html) — hierarchical multi-agent memory
10. [FORGE — arXiv:2605.16233](https://arxiv.org/abs/2605.16233) — population broadcast memory, 1.7-7.7× improvement
11. [GUARDIAN — NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/0bc795afae289ed465a65a3b4b1f4eb7-Abstract-Conference.html) — temporal graph safety for multi-agent
12. [ReasoningBank — ICLR 2026](https://iclr.cc/virtual/2026/poster/10007887) — MaTTS, emergent self-evolution
13. [MemoryAgentBench — arXiv:2507.05257](https://arxiv.org/pdf/2507.05257) — selective forgetting is the hardest problem
14. [Sakana AI Conductor — ICLR 2026](https://sakana.ai) — 7B orchestrator outperforms all individual models
15. [OpenAI 1M Lines Zero Human Code](https://openai.com) — harness as the product
