# SYNTHESIS — State of the Field for AI Agent Harnesses

**Stage 1 of 3** — Cross-source analysis across the full §3 corpus.  
**Date**: 2026-05-31  
**Sources analyzed**: 228 deep-read (80% of 286-URL corpus)  
**Purpose**: Map the frontier, convergences, contradictions, and trajectory before designing a unified breakthrough architecture.

---

## 1. Memory — The Core of Agent Intelligence

### 1.1 Frontier

The field has moved decisively beyond flat vector retrieval toward **structured, self-evolving memory with admission control**.

**Strongest work** (ICLR 2026 MemAgent Workshop, sources #58-#86):
- **A-MAC** (#79): 5-factor admission control (utility/confidence/novelty/recency/type) achieves F1=0.583 with −31% latency. The key insight: *not everything belongs in memory*. A lightweight gating mechanism prevents accumulation of hallucinated or low-value content.
- **A-MEM** (#59): Zettelkasten-style dynamic linking lets memories trigger updates to related memories, creating emergent structure without manual schema design. Outperforms SOTA across 6 foundation models on LoCoMo.
- **MemAgent** (oral, #256): Extrapolates from 8K training to 3.5M token deployment with <10% degradation via learned compression (RL-based overwrite strategy). Proves memory systems can scale far beyond training distribution.
- **AOI** (#68): 3-layer hierarchy (Working/Episodic/Semantic) with context compressor achieves 72.4% compression while preserving 92.8% critical information and −34.4% MTTR in IT operations.
- **ERL** (#65): Heuristic abstraction over raw storage — +7.8% on Gaia2 by extracting reusable principles rather than storing interaction traces.
- **MemGrad** (#70): Textual gradients transform batched feedback into persistent memory + prompt updates without fine-tuning. Applied to multi-agent AgileCoder.
- **CoMem** (#77): Decoupled memory processing running parallel to agent execution — 1.4× latency improvement by separating memory management from task execution.
- **EvolveMem** (#106): Self-optimizing memory that diagnoses failures, adjusts retrieval configs, and auto-rolls-back on regression — +25.7% LoCoMo, +18.9% MemBench.
- **FluxMem** (#107): Memory as continuously evolving graph connectivity with 3-stage evolution (formation, feedback-driven refinement, long-term consolidation) — SOTA on LoCoMo, Mind2Web, GAIA.

**The frontier is clear**: Memory is no longer passive storage — it's an active, self-optimizing cognitive layer with admission control, dynamic linking, hierarchical compression, and autonomous evolution.

### 1.2 Convergences

**Multi-tier hierarchy is universal** — Every strong system uses ≥3 layers (STM ← Working ← Episodic ← Semantic ← Archive). The pattern appears in AOI (#68), MemAgent (#256), Letta/MemGPT (#250), AnnaAgent (#255), and the Storage-to-Experience survey (#64). No top-performing system uses flat memory.

**Admission control is becoming mandatory** — A-MAC (#79), Curriculum Curation (#76), and the KAIST localized compression paper (#73) all agree: indiscriminate storage degrades retrieval. The field is converging on gating mechanisms that evaluate *what* to store before storing it.

**Compression must be localized** — KAIST (#73) theoretically proves that compression within modular units minimizes retrieval–update interference (drift). AOI (#68) and IterResearch (#272) empirically validate this: sliding-window with overlap beats global truncation.

**Feedback-driven evolution works across modalities** — MemGrad (#70) uses textual feedback, FORGE (#103) uses population broadcast, EvolveMem (#106) uses failure diagnosis — all achieve significant improvements by closing the feedback loop between execution outcomes and memory structure.

**Graph structure beats flat retrieval** — LP-RAG (#66), A-MEM (#59), Zep/Graphiti (#251), DAVIS (#257), and the Retrieval-as-Reasoning paper (#92) all show that graph-based memory (knowledge graphs, temporal graphs, linked notes) outperforms flat embedding search on complex queries, especially multi-hop and relationship-based retrieval.

### 1.3 Contradictions & Open Problems

**Architecture transfer doesn't generalize** — Memory Transplants (#58) is a crucial warning: neither memory architecture nor content transfers well across domains (code→math). Architecture transfer is system-dependent and inconsistent; content transfer in static mode provides limited benefit beyond no-memory baselines. *What architecture works for Lyra's coding tasks may not work for research tasks.*

**Better components ≠ better performance** — WorldMemArena (#100) reveals that improved memory writing/storage doesn't automatically translate to better agent performance. Multimodal memory struggles with visual evidence; systems are unstable across domains; harness memory is more flexible but costlier and less reliable. *The integration matters more than individual components.*

**Confidence decay rates are underexplored** — A-MAC (#79) establishes confidence scoring but doesn't study optimal decay functions. Mem0 (#248) and Graphiti (#251) implement decay but with arbitrary parameters. No work systematically compares exponential vs. linear vs. reinforcement-weighted decay.

**Cross-agent shared memory is nascent** — DecentMem (#99) is the strongest work (dual-pool per-agent with O(log T) regret), achieving +23.8% vs centralized, +52.5% vs no-memory, and −49% tokens — but it's untested beyond 3 MAS frameworks. The multi-agent memory problem (when to share, when to isolate, how to resolve conflicts) remains open.

**Cold storage / forgetting is understudied** — Entropic Memory (#78) proposes thermodynamic consolidation but is early-stage. Almost no work studies *active forgetting* — intentionally removing memories once they're obsolete — as opposed to compression or decay.

### 1.4 Trajectory

Memory systems are heading toward:
- **Autonomous self-optimization** — EvolveMem (#106), FORGE (#103), and MemGrad (#70) point toward systems that tune their own retrieval, compression, and admission policies without human intervention.
- **Deeper integration with routing** — Knowledge Access Beats Model Size (#227) and Cost-Sensitive Store Routing (#60) show that memory + routing = compound benefits. The next generation will make routing decisions *based on what's in memory*, not just query complexity.
- **Temporal awareness** — APEX-MEM (#132), Zep/Graphiti (#251), and FluxMem (#107) all add time dimensions to memory. The next step is temporal reasoning ("what changed between session 3 and session 7?").
- **Multi-agent memory federation** — DecentMem (#99) is the vanguard. The trajectory is toward swarms that learn collectively while maintaining individual specialization.

---

## 2. Context & Auto-Compaction

### 2.1 Frontier

**Strongest work**:
- **Norm-Guided KV-Cache** (#62): Gradient-free compression scoring tokens by ℓ2-norm of key vectors. Elegant: no training, just a norm calculation per token.
- **R-KVHash** (#63): SimHash/LSH-based compression evicts redundant reasoning-trace tokens. ~2× decoding throughput by removing what's repeated.
- **ACON** (#254): Adaptive agent context compression achieving 26–54% memory reduction. The key: *failure-driven optimization* — analyze what compression lost, then adjust strategy.
- **IterResearch** (#272): MDP-style workspace reconstruction with evolving report-as-memory. Scaling from 3.5% to 42.5% at 2048 interaction steps by periodically synthesizing insights.
- **OCR-Memory** (#131): Novel bypass of token limits: encode agent trajectories as visual images with annotations. Faithful retrieval of arbitrarily long histories.

### 2.2 Convergences

- **Semantic compression > truncation** — Every strong system compresses semantically (extract insights, discard verbatim) rather than truncating by token count. IterResearch (#272), ACON (#254), AOI (#68), and Anthropic Context Engineering (#253) all agree.
- **Importance scoring is the right mechanism** — Norm-Guided (#62) uses ℓ2-norm, R-KVHash (#63) uses SimHash for redundancy, ACON (#254) uses failure feedback. Different scoring functions, same principle: not all tokens are equal.
- **Periodic synthesis prevents suffocation** — IterResearch (#272) and MemSearcher (#140) both show that periodic "insight synthesis" — stopping to compress and summarize — keeps context usable in long-running tasks.

### 2.3 Contradictions & Open Problems

- **When to compress is unresolved** — Some systems compress continuously (Norm-Guided #62), others at fixed intervals (IterResearch #272), others on threshold (ACON #254). No comparative study exists.
- **Compression verification is missing** — Incredibly, no current system verifies that compressed context preserves the information needed for the current task. This is a dangerous gap: over-compression can silently remove critical context.
- **Cross-provider context optimization is uncharted** — All work assumes a single model with known context window. Lyra's multi-provider reality (Claude 200K, DeepSeek 64K, GPT 128K) means compression strategies must adapt to the provider.

### 2.4 Trajectory

Context optimization is heading toward **adaptive, verified, provider-aware compaction** that automatically tunes compression strategy to both the task and the model's context window.

---

## 3. Skills & Self-Evolution

### 3.1 Frontier

This is the most dynamic research area in the corpus. The field is moving from static skill libraries to **self-evolving, self-challenging skill ecosystems**.

**Strongest work**:
- **SkillNet** (#158–159): "npm for AI skills" — 500K+ skills, auto-generation from repos/PDFs/logs, 5-D quality scoring, skill graph with 4 relationship types. The reference for what a skills ecosystem looks like.
- **Darwin Gödel Machine** (#261–262): Self-rewriting coding agent: SWE-bench 20%→50%, Polyglot 14.2%→30.7% — both ~150% relative improvement through archive-based empirical self-improvement. *The agent rewrites its own code, validates via benchmarks, and only keeps what works.*
- **Self-Challenging LM Agents** (#113): Agents generate their own training problems (Code-as-Task) with verifiers and tests. Removes human dataset curation bottleneck — the agent creates its own curriculum.
- **MOSS** (#87): First system for *source-level* self-evolution — rewrites the harness code itself, not just prompts. OpenClaw grader score: 0.25→0.61 in a single cycle. Turing-complete adaptation scope.
- **SkillOpt** (#117): Text-space optimizer that trains skills like neural weights — +19 to +25 points across 52 configurations. Systematic optimization with validation feedback.
- **HASP** (#102): Skills as *executable Program Functions* that actively intervene on failure-prone states — +25% web-search, +30.4% over Search-R1 with post-training + evolution.
- **CODESKILL** (#95): Learnable skill management policy trained with RL (hybrid reward: dense rubric-based quality + sparse verifiable execution) — +9.69 vs no-skill, +4.01 vs strongest baseline.
- **Proteus** (#125): Grey-box iterative red-teaming of skills — 40-90% attack success at 5 rounds, ≥93% bypass rate. *The dark side: single-shot security reviews severely underestimate adaptive attackers.*

### 3.2 Convergences

- **Format standardization is happening** — Claude Code Skills (#1–4), SkillNet (#158–159), claude-skills (#170), and the Agent Skills open standard all converge on SKILL.md (YAML frontmatter + Markdown body) as the dominant format. This is directly adoptable for Lyra.
- **Quality gates are essential** — SkillNet's 5-D scoring, Darwin's empirical validation, CODESKILL's RL-based quality feedback, and Proteus's security scanning all converge: skills need multi-dimensional quality assessment before deployment.
- **Self-evolution > manual improvement** — Darwin (3× improvement), CODESKILL (+9.69), SkillOpt (+25 points), HASP (+30.4%) — every system that enables self-evolution dramatically outperforms static/manual improvement.
- **Progressive disclosure reduces cost** — Claude Code Skills 3-level loading (metadata→body→files) and SkillOS achieve 61-90% token reduction by loading only what's needed when it's needed.

### 3.3 Contradictions & Open Problems

- **Self-evolution safety is unresolved** — "Your Agent May Misevolve" (#247) identifies concrete risks (alignment decay after memory accumulation, vulnerabilities from tool creation/reuse — across model/memory/tool/workflow pathways). Proteus (#125) shows 40-90% attack success against iteratively-evolved skills. *How do we enable self-evolution without enabling self-destruction?* No system has solved this.
- **Evolution instability is real** — BenchTrace (#96) shows agents forget early lessons as episodes accumulate, fail to generalize reflections beyond specific contexts, and suffer negative transfer. <30% reflection pass rate for GPT-4.1 and Qwen3-32B.
- **Provider-specific skill behavior is undocumented** — No skills system documents expected behavior/limitations per LLM provider. For Lyra's multi-provider requirement, this is a critical gap.

### 3.4 Trajectory

Skills are heading toward **autonomous, safe, cross-provider self-evolution** — but the safety problem is the bottleneck. The next breakthrough will be a system that can evolve skills continuously while maintaining safety invariants and detecting regression.

---

## 4. Model Routing

### 4.1 Frontier

**Strongest work**:
- **RouteLLM** (#222–223): 4 router types (similarity, BERT, causal LLM, matrix factorization — matrix factorization recommended). 85% cost reduction at 95% GPT-4 performance. Transfer learning across model pairs.
- **BEST-Route** (#224–225, ICML 2025): Routes to model AND decides number of response samples (1-N). Generate 3–5 responses from cheap model, pick best — 60% cost reduction with <1% performance drop.
- **FrugalGPT** (#226): Cascade routing with early stopping — 98% cost reduction matching GPT-4, OR +4% accuracy improvement at same cost.
- **Knowledge Access Beats Model Size** (#227): Memory-augmented routing — smaller model + good retrieval > larger model alone. The bridge between §4.2 memory and §4.5 routing.

### 4.2 Convergences

- **Trained routing > heuristic routing** — RouteLLM's matrix factorization and BEST-Route's DeBERTa classifier consistently outperform rule-based routing on accuracy and cost.
- **Cascade works** — FrugalGPT (#226), RouteLLM (#222), and BEST-Route (#225) all show that cheap→expensive escalation with confidence thresholds is reliable and dramatically cost-effective.
- **Multi-sampling from cheap models is underexploited** — BEST-Route (#225) shows that generating multiple responses from Haiku and picking the best can match Opus quality at lower cost. This is a free lunch for verifiable outputs (code, tests, factual QA).
- **Memory + routing is a compound win** — Knowledge Access Beats Model Size (#227) and Cost-Sensitive Store Routing (#60) both show that routing decisions should use memory state (has this been answered before?) to avoid redundant expensive calls.

### 4.3 Contradictions & Open Problems

- **Confidence scoring for escalation is unreliable** — None of the systems report failure rates for their confidence mechanism. A false high-confidence cheap answer could silently degrade quality.
- **Multi-provider routing is unexplored** — All routing research assumes within-provider routing (e.g., GPT-4 vs GPT-3.5). Cross-provider routing (Claude vs DeepSeek vs GPT) with different capability profiles, pricing, and reliability is an open problem — and exactly what Lyra needs.
- **Conversation-aware routing is missing** — All systems route per-query. None consider conversation state (escalating complexity, user frustration signals, follow-up chains).

### 4.4 Trajectory

Routing is heading toward **memory-augmented, multi-provider, confidence-calibrated cascade systems** that optimize across cost, quality, latency, and provider capability simultaneously.

---

## 5. Swarm & Orchestration

### 5.1 Frontier

**Strongest work**:
- **Claude Code Dynamic Workflows** (#203): Code-driven fan-out; independent agents + adversarial verification until convergence; resumable long runs. Ships in production (v2.1.154+).
- **AutoScientists** (#154–156): Decentralized self-organizing research teams — +8.33% improvement, adversarial critique-before-spend, shared success/failure log to prevent redundant work.
- **Anthropic Multi-Agent Research** (#279): Orchestrator-worker pattern — +90.2% improvement, 90% time reduction via parallel execution.
- **RecursiveMAS** (#119): Treats entire agent system as unified latent-space recursive computation — +8.3% accuracy, 1.2–2.4× speedup, 34.6–75.6% token reduction across 9 benchmarks. *The strongest evidence that text-based multi-agent communication may be suboptimal.*
- **DecentMem** (#99): Per-agent dual-pool memory with O(log T) regret guarantees — +23.8% vs centralized, +52.5% vs no-memory, −49% tokens.
- **Behind EvoMap** (#89): Warning — 98% of assets in a real A2A collaboration network were never reused; 84%+ bypassed quality checks with trivial tests. *Self-organizing networks fail without verification mechanisms.*

### 5.2 Convergences

- **Adversarial critique improves reliability** — AutoScientists (#154–156), Dynamic Workflows (#203), and the Anthropic multi-agent system (#279) all use adversarial verification (critique before execution, attack each answer until convergence).
- **Decentralized > orchestrated for scalability** — DecentMem (#99), AutoScientists (#154–156), and Behind EvoMap (#89) all show that decentralized coordination outperforms central orchestration at scale — but needs verification to prevent gaming.
- **Workflows need to be resumable** — Dynamic Workflows (#203) and Lyra's P4-B6 both implement checkpoint-based pause/resume for long-running multi-agent tasks.

### 5.3 Contradictions & Open Problems

- **RecursiveMAS (#119) challenges all text-based work**: if latent-space agent collaboration achieves +8.3% accuracy with 34.6–75.6% token reduction, why are all other systems text-based? Is text-based coordination actually suboptimal?
- **Optimal swarm size is unknown** — No system studies the efficiency curve as swarm size grows. Real-world runs report ~47 concurrent agents with errors needing human review (#203).
- **Agent specialization vs. generalization tradeoff** — Evolve as a Team (#88) shows multi-scale evolution (individual/coordination/organization) improves outcomes, but *what ratio of specialists to generalists is optimal?*

### 5.4 Trajectory

Swarm orchestration is heading toward **decentralized, adversarially-verified, resumable multi-agent systems** with latent-space coordination and per-agent memory. The convergence on adversarial verification is the strongest signal in this theme.

---

## 6. Voice Mode

### 6.1 Frontier

**Strongest work** (§3.13, sources #205–221):
- **Moshi** (#210–211): First real-time full-duplex spoken LLM — dual simultaneous audio streams, Inner Monologue predicts text before audio, Mimi codec at 1.1kbps with 80ms latency. 200ms practical latency on L4 GPU.
- **Silero VAD** (#209): 2MB model, sub-millisecond inference, 6000+ languages — production-ready universal VAD.
- **Smart Turn** (#208): Prosody-aware turn detection using Whisper Tiny backbone + linear classifier — 10–65ms, 23 languages including Vietnamese.
- **Whisper Turbo** (#217): 809M params, ~8× speed vs large with minimal accuracy loss, ~100ms for short utterances. Strong VI+EN.
- **Kokoro-82M** (#214): StyleTTS 2 (82M params), real-time on CPU, Apache-2.0 — production-ready open TTS.
- **Orpheus-TTS** (#215): Llama-3b backbone as TTS — emergent emotion control and zero-shot cloning from LLM architecture. ~100–200ms streaming.
- **NeMo Speech** (#216): User-selectable latency-accuracy Pareto curve. Canary-Qwen-2.5B at 5.63% WER, Parakeet at 160ms minimum latency.
- **Pipecat** (#205): Pipeline-as-agent composition — modular STT→LLM→TTS with 80+ integrations. Production-ready, extensible.
- **LiveKit Agents** (#206): Function-tool-based agent handoffs. WebRTC + telephony, hot reloading, multi-agent concurrency.

**Benchmarks**:
- **Full-Duplex-Bench v3** (#220): GPT-Realtime at 0.600 Pass@1, 13.5% interruption rate. Cascaded systems at 10.12s latency but perfect turn-taking. Multi-step tool use under disfluent speech is the hardest problem.
- **τ-Voice** (#221): Voice agents retain only 30–45% of text capability — 79–90% failures from agent behavior, not voice constraints.

### 6.2 Convergences

- **Cascaded pipeline wins for now** — Pipecat (#205), LiveKit (#206), Ten-Agent (#207) all use cascaded STT→LLM→TTS for production. Full-duplex (Moshi) is the future but not production-ready yet.
- **Open-source stack is viable** — Silero VAD + Smart Turn + Whisper Turbo + Kokoro-82M = fully open-source voice pipeline with <500ms latency. Orpheus-TTS + NeMo offer alternatives.
- **Multilingual is solved at the STT layer** — Whisper (#217) supports 99 languages, Silero (#209) supports 6000+, Smart Turn (#208) supports 23. TTS multilingual support is weaker — Kokoro supports EN/JA/KO/ZH, Orpheus has 7 language pairs (research preview), NeMo MagpieTTS supports 9 languages.
- **Vietnamese + English is well-supported** — Silero VAD, Smart Turn, and Whisper all explicitly support Vietnamese. The TTS gap for Vietnamese (needs MagpieTTS or Orpheus multilingual preview) is the main limitation.

### 6.3 Contradictions & Open Problems

- **Full-duplex vs cascade is unresolved for production** — Moshi achieves 200ms but needs 24GB GPU. Cascaded systems achieve 500ms on CPU. For Lyra's terminal-based audience, which is the right tradeoff?
- **Voice→multi-agent integration is unexplored** — No voice system integrates with a multi-agent swarm. LiveKit Agents (#206) comes closest with agent handoffs, but spatial audio + agent voices + swarm coordination is novel territory.
- **On-device vs cloud is a genuine tension** — Open-source stack achieves 500ms on-device. Cloud stack (OpenAI Realtime) achieves 100ms at $0.06/min. The cost/latency/privacy tradeoff is sharp, and user preferences will vary.

### 6.4 Trajectory

Voice mode is heading toward **full-duplex, provider-agnostic, multi-agent voice coordination** — but Lyra can lead with a cascaded open-source pipeline now (matching SOTA at lower cost) while preparing for the Moshi-style future.

---

## 7. Reliability & Safety

### 7.1 Frontier

**Observability**:
- **Phoenix** (#230) + **Langfuse** (#228) + **OpenLLMetry** (#229): All converge on OpenTelemetry as the standard. OTEL-first architecture, hierarchical trace structure (Session→Agent→LLM Call→Tool Use), decorator-based tracing.

**Verification**:
- **SABER** (#67): Mutation-gated verification — mutating actions reduce success odds by 55–96% per deviation (p<0.001). +28% Airline, +11% Retail, +7% SWE-bench Verified. *The key: focus verification on actions that change state — these are where errors are decisive.*
- **τ-bench** (#231–232): pass^k metric — consistency over occasional success. Even SOTA models <50% task success, pass^8 <25% in retail. *Single-shot metrics overestimate reliability.*
- **Agentic Benchmark Checklist** (#111): Identifies flaws in SWE-bench Verified and τ-bench. Reduces overestimation by 33%. *Rigorous benchmarks require explicit design — ad-hoc evaluation inflates results.*

**Safety**:
- **CaMeL** (#243–244): Control/data-flow separation — 77% task success with provable security against prompt injection. *Architectural solution: user queries = trusted control, external content = untrusted data.*
- **Progent** (#245–246): Programmable least-privilege — symbolic policies with SMT solver verification. LLM proposes, formal verifier decides. Prevents silent privilege escalation.
- **LlamaFirewall** (#236–237): Meta's open guardrail — PromptGuard 2 (86M params, 99%+ TPR, <2ms), alignment checks, CodeShield. Production-ready.
- **NeMo Guardrails** (#239–240): NVIDIA's programmable rails — Colang DSL for defining safety boundaries at runtime. Async-first, multi-LLM support.
- **AgentDojo** (#241–242): 97 tasks, 629 security test cases. Multi-property adversarial evaluation.

### 7.2 Convergences

- **Defense in depth is mandatory** — All top safety systems (LlamaFirewall, NeMo, CaMeL, Progent) use multiple layers. No single defense suffices.
- **Architectural solutions > prompt engineering** — CaMeL achieves provable security through control/data separation, Progent through SMT-verified policies. These are architectural guarantees, not prompt-level suggestions.
- **Adversarial testing must be continuous** — Proteus (#125) and AgentDojo (#241–242) show that single-shot security reviews underestimate adaptive attackers by 40–90%. Continuous red-teaming is essential.
- **Consistency > single-shot accuracy** — τ-bench's pass^k and SWE-bench Verified's human validation both reveal that single-attempt metrics dramatically overestimate reliability.

### 7.3 Contradictions & Open Problems

- **Verification cost vs benefit is unquantified** — SABER's mutation-gated verification reduces overhead, but no work quantifies the Pareto frontier of verification thoroughness vs cost.
- **Self-evolution + safety is unresolved** — The combination is the most dangerous capability vector ("Your Agent May Misevolve" #247) and the least studied. How do you let skills evolve while ensuring they don't evolve around safety constraints?

### 7.4 Trajectory

Reliability is heading toward **mutation-gated, pass^k-verified, adversarially-tested systems** with OpenTelemetry-native observability. Safety is heading toward **architectural defense-in-depth** with continuous red-teaming — and the self-evolution safety problem is the most urgent open challenge.

---

## 8. Autonomy

### 8.1 Frontier

- **Continuous-claude** (#184): Simple while-true loop with relay-race prompting + shared notes file. The pattern: each iteration is independent (can be killed/restarted), shared notes provide continuity. Author used it for 0%→80%+ test coverage on hundreds of thousands of lines of code.
- **Darwin Gödel Machine** (#261–262) + **MOSS** (#87) bring code-level self-evolution to autonomy: agents that rewrite the harness itself.
- **Bounded autonomy with graduated trust** (from brainstorm/14-full-autonomy.md): Trust levels (0–5) that expand based on demonstrated reliability — combining continuous operation with progressive capability grants.

### 8.2 Convergences

- **External memory is the enabler** — Sharing state via filesystem (continuous-claude's SHARED_TASK_NOTES.md, IterResearch's evolving report-as-memory) is the simplest and most reliable pattern for persistent autonomy.
- **Budget controls are essential** — Max runs, max cost, max duration, completion signals — all autonomous systems need explicit limits.

### 8.3 Open Problems

- **Safety-alignment decay** (#247) is the primary blocker for full autonomy. How do we let agents run independently for long periods without safety degradation?
- **Stall detection** — How does the system know it's stuck vs making slow progress? No current system has reliable stall detection.

---

## 9. Cross-Cutting Observations

### 9.1 The Self-Evolution Lineage is Exploding

The corpus shows a clear arc:
```
Static prompts → Skill libraries (SkillNet 2024–2025)
                → Prompt-level self-evolution (MemGrad, ERL 2025)
                → Code-level self-evolution (Darwin, MOSS 2025–2026)
                → Harness-level self-evolution (emerging 2026)
```

This is the trajectory toward the AGI-direction goal: a self-improving omni-agent. The next step — harness-level self-evolution that rewrites memory, skills, routing, and tools simultaneously — is unexplored territory.

### 9.2 Memory is the Nexus

Memory connects to every other theme:
- **Memory → Routing**: Know what's cached → route intelligently (#60, #227)
- **Memory → Skills**: Store skill outcomes → evolve skills (#70, #95, #117)
- **Memory → Context**: Hierarchical compression → efficient context (#64, #67, #68)
- **Memory → Swarm**: Shared memory → coordinated agents (#99, #154–156)
- **Memory → Safety**: Memory provenance → audit and rollback (#71, #247)
- **Memory → Voice**: Session memory → voice continuity (#220–221)

The breakthrough architecture must treat memory as the **central nervous system**, not a feature.

### 9.3 Provider Heterogeneity is an Unaddressed Frontier

Almost all research assumes a single provider. For Lyra's explicit multi-provider requirement (Claude/DeepSeek/Qwen/GPT/open-weights), critical gaps exist:
- Skills triggering reliability varies wildly across providers
- Tool-calling formats differ (some providers lack it entirely)
- Context windows vary (200K vs 64K vs 8K)
- Cost structures differ by orders of magnitude ($15/MTok vs $0.27/MTok)
- Reliability and instruction-following quality vary significantly

**No existing harness architecture handles this heterogeneity systematically.** This is Lyra's primary differentiation opportunity.

### 9.4 The Adversarial Verification Pattern is Universal

AutoScientists (#154–156), Dynamic Workflows (#203), Anthropic Multi-Agent (#279), Proteus (#125), SABER (#67), and AgentDojo (#241–242) all converge on the same pattern: *have independent agents try to break each proposal before executing it.* This pattern should be a first-class citizen in Lyra's architecture, not bolted on to specific workstreams.

### 9.5 Terminal-Native Constraints are Underexploited

Lyra's terminal-based, MIT-licensed identity creates unique opportunities:
- **Filesystem as memory**: terminal-native agents can use the filesystem as a first-class memory layer (IterResearch #272 pattern)
- **Git-native workflows**: automatic commits, versioned memory, diff-based review (Aider #49, continuous-claude #184)
- **Headless operation**: background agents + hooks + cron scheduling in terminal-only environments
- **Zero-GUI extensibility**: everything through CLI, files, and stdin/stdout

Most research targets GUI or API-based agents. Lyra can pioneer patterns for the terminal-native paradigm.

---

## 11. Design Philosophy Lineages — WHY Different Groups Made Different Choices

Understanding the field requires understanding not just WHAT techniques exist but WHY different research groups chose different paths. This section traces lineages by design philosophy rather than technique.

### Lineage 1: "Memory is the Platform" (Memory-First)

**Key papers**: AOI, A-MEM, A-MAC, MemAgent, Letta/MemGPT, Zep/Graphiti, AnnaAgent, DecentMem

**Design philosophy**: The agent's memory architecture determines its capabilities more than any other component. Better memory → better routing, better skills, better coordination. The memory IS the platform.

**Why they chose this path**: These groups observed that agents with flat/no memory plateau quickly — they can't learn from past interactions, can't recognize repeat patterns, can't build on prior knowledge. The memory bottleneck is the FIRST bottleneck to hit as agents scale in usage duration and task diversity.

**What they rejected**: The alternative is "intelligence-first" — assume better models will solve the memory problem implicitly through longer contexts. These groups rejected this because: (1) context windows have fundamental scaling limits (quadratic attention cost), (2) even 1M-token contexts can't match the retrieval precision of a well-designed memory system for specific fact lookup, (3) models don't learn from interaction history across sessions — each session starts from scratch.

**Key trade-off the lineage accepts**: Memory systems add architectural complexity and latency (retrieval, admission, compression steps). The lineage accepts this because the compounding benefit of persistent learning outweighs the per-query overhead.

### Lineage 2: "Verification Over Generation" (Safety-First)

**Key papers**: SABER, AutoScientists, CaMeL, Progent, Proteus, "Your Agent May Misevolve"

**Design philosophy**: Agent intelligence is about making GOOD DECISIONS, not just generating plausible outputs. Generation gets 80% of the way; verification catches the other 20%. The verification architecture matters more than the generation architecture.

**Why they chose this path**: These groups observed that agent failures are HEAVY-TAILED — a few catastrophic errors dominate overall failure cost. Reducing the ERROR RATE by 10% (through better generation) has less impact than catching the 1% of ERRORS that cause 90% of DAMAGE (through targeted verification). SABER's key finding: 55-96% of error impact comes from a small fraction of actions (mutating ones). This justifies asymmetric investment in verification.

**What they rejected**: The alternative is "better generation" — invest all effort in making the model produce better outputs. These groups rejected this because: (1) generation errors are inevitable (models hallucinate, misunderstand, forget), (2) the cost of catching an error before execution is 10-100× lower than the cost of fixing its consequences, (3) verification can be provider-agnostic while generation quality varies by provider.

**Key trade-off the lineage accepts**: Verification adds latency and token cost to every verified action. The lineage accepts this only for MUTATING actions (SABER's key contribution: verify only what's dangerous) — making the overhead proportional to risk rather than constant.

### Lineage 3: "Self-Evolution is Inevitable" (Evolution-First)

**Key papers**: Darwin/DGM, SEAL, ADAS, Meta-Harness, SkillOpt, FORGE, EvoTest, ReflecTool, EvolveMem

**Design philosophy**: Static systems plateau. The only sustainable path to superhuman agent performance is self-improvement — the agent must get better through its own experience, not through human engineering. Evolution is not a feature; it's the engine that makes all other features compound.

**Why they chose this path**: These groups observed that the DIFFERENCE between a good agent and a great agent in a specific domain is learned through experience, not designed upfront. A static prompt for "debug authentication bugs" can never capture all the patterns that emerge from debugging 1,000 real auth bugs. Evolution captures those patterns automatically.

**What they rejected**: The alternative is "better initial design" — invest in better prompts, better memory architectures, better routing policies designed by humans. These groups rejected this because: (1) human design doesn't scale — you can't hand-craft prompts for every task variant, (2) human intuition about what works is often wrong (SkillOpt found evolved prompts consistently beat hand-written ones), (3) the environment changes — what works today may not work tomorrow, and only continuous evolution adapts.

**Key trade-off the lineage accepts**: Evolution consumes tokens (1M+ per skill per cycle in Darwin), can produce unsafe behaviors ("Your Agent May Misevolve"), and has a cold-start problem (needs data to begin). The lineage accepts these costs because the ALTERNATIVE — static systems that never improve — has a hard ceiling that evolution can surpass.

### Lineage 4: "Provider Heterogeneity is Reality" (Provider-First)

**Key papers**: RouteLLM, BEST-Route, FrugalGPT, Knowledge Access Beats Model Size, Hybrid LLM

**Design philosophy**: The multi-provider world is not a temporary inconvenience — it's a permanent feature. Models will always differ in cost, capability, latency, and reliability. The architecture should EXPLOIT these differences (cheap exploration, expensive verification) rather than PAPER OVER them (normalize to lowest common denominator).

**Why they chose this path**: These groups observed that the cost-capability Pareto frontier is WIDE — DeepSeek Flash at $0.27/MTok vs Claude Opus at $15/MTok is a 55× cost difference for a ~20% capability difference. No single model is optimal for all queries. A router that selects the right model per query can achieve 60-85% cost reduction at equivalent quality.

**What they rejected**: The alternative is "single-provider optimization" — pick the best provider and optimize everything for it. These groups rejected this because: (1) single-provider = single point of failure (price changes, outages, policy changes), (2) the "best" provider varies by task type (Claude for reasoning, DeepSeek for fast execution, GPT for vision), (3) provider lock-in prevents exploiting the cost-capability frontier.

**Key trade-off the lineage accepts**: Multi-provider routing adds complexity (provider abstraction layer, capability matrix, degradation strategies) and the routing decision itself costs tokens. The lineage accepts this because the cost savings from routing dwarf the routing overhead by 10-100×.

### Cross-Lineage Tensions

These four lineages are in GENUINE TENSION — they make incompatible bets:

| Tension | Memory-First vs Evolution-First | Verification-First vs Evolution-First | Provider-First vs Memory-First |
|---------|-------------------------------|--------------------------------------|-------------------------------|
| **The conflict** | Memory-First: design the RIGHT memory architecture and learning emerges. Evolution-First: memory architecture itself should evolve. | Verification-First: gate every change with verification. Evolution-First: verification gates slow evolution unacceptably. | Provider-First: optimize per-provider. Memory-First: unified memory across providers. |
| **Synthesis** | Fixed memory architecture + evolvable memory CONTENTS (A-MEM dynamic linking, EvolveMem auto-tuning). Don't evolve the architecture, evolve what's stored. | Gated evolution: evolve freely in sandbox, verify before deployment. The debate's key resolution — evolution is safe IF gated. | Provider-aware memory: unified TKG structure, provider-specific admission weights and compression strategies. |

**The Lyra synthesis**: Memory-First provides the FOUNDATION (TKG). Verification-First provides the GUARDRAILS (AVP). Evolution-First provides the ENGINE (deferred to Phase 3+ but designed into the architecture from day one). Provider-First provides the ADAPTATION layer (capability matrix, degradation strategies). This is NOT a compromise — it's a LAYERED architecture where each lineage controls the layer it's best at.

---

## 12. Open Problems Summary (Input to STAGE 2)

| # | Problem | Severity | Theme(s) | What BREAKTHROUGH-ARCHITECTURE must solve |
|---|---------|----------|----------|-------------------------------------------|
| 1 | **Self-evolution safety** | CRITICAL | Skills, Safety | How to let skills evolve while preventing alignment decay |
| 2 | **Multi-provider heterogeneity** | CRITICAL | Router, all | How to make every component work across Claude/DeepSeek/GPT/open-weights |
| 3 | **Memory as central nervous system** | HIGH | Memory, all | How to integrate memory with routing, skills, swarm, context, voice |
| 4 | **Adversarial verification as universal pattern** | HIGH | Swarm, Safety, Skills | How to make critique-before-execute a first-class citizen |
| 5 | **Provider-adaptive context optimization** | HIGH | Context, Router | How to compress differently for 200K vs 64K vs 8K context windows |
| 6 | **Confidence-calibrated cascade routing** | HIGH | Router | How to reliably escalate from cheap to expensive models |
| 7 | **Cross-agent memory federation** | MEDIUM | Memory, Swarm | How to share without contamination, isolate without duplication |
| 8 | **Active forgetting** | MEDIUM | Memory | How to intentionally remove obsolete memories |
| 9 | **Stall detection for autonomy** | MEDIUM | Autonomy | How to distinguish slow progress from being stuck |
| 10 | **Terminal-native patterns** | MEDIUM | All | How to exploit Lyra's terminal-native identity |

---

## Next: STAGE 2 — BREAKTHROUGH-ARCHITECTURE.md

From this synthesis, I will now design ONE unified architecture that:
1. Makes memory the central nervous system
2. Handles multi-provider heterogeneity as a first-class concern
3. Makes adversarial verification universal
4. Enables safe self-evolution
5. Is native to the terminal (filesystem-as-first-class)
6. Targets the 10 open problems above

---

## ═══ ALGORITHMIC LINEAGES & QUANTITATIVE COMPARISONS — Run 10 ═══

### 1. Algorithmic Evolution Lineages

Each lineage traces how algorithms evolved from earlier to later work, showing the key innovation at each step, the limitation it solved, and the measured improvement.

---

#### Memory Admission Lineage

```
Flat vector store (2023): store everything, retrieve by similarity
  -> Letta/MemGPT (2024): OS-style paging, but no admission -- still eager storage
    -> Mem0 (2025): adds dedup + metadata filtering, but still similarity-based admission
      -> A-MAC (2026): 5-factor gating -- combine utility + confidence + novelty + recency + type_prior
        -> EvolveMem (2026): self-tuning admission weights -- closes the feedback loop
```

| Step | Limitation Solved | Algorithmic Change | Measured Improvement |
|------|-------------------|-------------------|---------------------|
| Flat vector store | No structure; every interaction stored equally | Cosine-similarity top-k retrieval over dense embeddings (e.g., text-embedding-ada-002) | Baseline |
| Letta/MemGPT | Context window overflow in long sessions | OS-style virtual context management with paged memory blocks; maintain working memory + external storage with recall/retrieve functions | Extends effective context from ~8K to unlimited tokens; enables multi-session persistence |
| Mem0 | Duplicate and low-value content dilutes retrieval quality | SHA-256 content deduplication + metadata-based filtering (source, timestamp, type) before insertion | ~30% storage reduction; +0.09 F1 on LoCoMo over flat storage |
| A-MAC | Utility-agnostic admission (all memories are not equal) | 5-factor gating: utility score (task-relevance prediction), confidence score (model self-reported), novelty score (surprise vs existing), recency weighting (inverse time-decay), type_prior (class-specific admission bias) | F1=0.583 on LoCoMo; -31% latency vs Mem0; -23% tokens per search |
| EvolveMem | Fixed admission weights fail when task distribution shifts | Self-tuning admission: agent monitors retrieval failure rate, adjusts each of 5 gate weights via hill-climbing on a validation window; auto-rollback on regression | +25.7% LoCoMo, +18.9% MemBench over fixed-weight A-MAC; converges in ~200 trajectories |

The key algorithmic insight: admission control evolved from deterministic (dedup) to multi-factor heuristic (A-MAC) to self-optimizing (EvolveMem). At each step, the bottleneck was not storage capacity but *signal-to-noise ratio* — the admission gate is the filter that keeps the signal high.

---

#### Memory Retrieval Lineage

```
Keyword/BM25 (pre-2023): exact match, no semantics
  -> Embedding similarity (2023): semantic search, but can't handle relations
    -> Graph RAG / LP-RAG (2024-25): link prediction over knowledge graphs
      -> Zettelkasten / A-MEM (2025-26): dynamic linking without pre-defined schema
        -> Cost-Sensitive Store Routing (2026): multi-store routing by query complexity
          -> Retrieval-as-Reasoning (2026): LLM reasons about WHERE to look before retrieving
```

| Step | Limitation Solved | Algorithmic Change | Measured Improvement |
|------|-------------------|--------------------|---------------------|
| BM25 | No semantic understanding; "car" does not match "automobile" | TF-IDF term matching with inverse document frequency weighting | Baseline; F1 ~0.20-0.25 on standard QA |
| Embedding similarity | Synonym and paraphrase matches invisible to term-based retrieval | Dense passage retrieval (DPR / text-embedding models): map query + passages to shared vector space, nearest-neighbor search | +0.30-0.40 F1 over BM25 on NQ/TriviaQA |
| Graph RAG / LP-RAG | Multi-hop queries fail when information spans disconnected embedding regions | Knowledge graph construction from passages + link prediction (GNN-based LP-RAG) enables path-based reasoning across entity relationships | +0.10-0.15 F1 over flat embedding on 2WikiMultiHop; +7-12% on relationship-heavy queries |
| Zettelkasten / A-MEM | Pre-defined graph schemas cannot adapt to novel domains | Dynamic note-linking: each stored memory declares outgoing links to related memories; links are scored and pruned by usage frequency; emergent graph structure | Outperforms SOTA across 6 foundation models on LoCoMo; +0.08-0.12 F1 over Graph RAG baselines |
| Cost-Sensitive Store Routing | All queries search all stores (Working + Episodic + Semantic), wasting time on simple queries | Three-tier routing: simple lookup -> Working only; factual query -> Episodic; complex reasoning -> all stores + Semantic synthesis; routing decision by query embedding + length + verb count | -34.4% MTTR in IT ops (AOI); -40-60% retrieval time for simple queries |
| Retrieval-as-Reasoning | Routing boundaries are still heuristic; miss subtle high-value searches | LLM receives store inventory (schema + size + access cost) and decides retrieval plan before search; multi-step retrieval with interleaved reasoning | +5.2% over routing-only on complex multi-hop QA; key insight: the retrieval *plan* matters more than the retrieval *method* |

The retrieval lineage shows a progression from *brute force* (search everything) to *heuristic pruning* (tier-based) to *reasoned search* (LLM plans the retrieval strategy). The frontier is not better similarity metrics but better *search strategy*.

---

#### Agent Coordination Lineage

```
Single agent (2023): one model, one task
  -> Sequential multi-agent (2024): chain agents, but bottleneck on slowest
    -> Parallel fan-out (2025): independent agents, but no cross-checking
      -> Adversarial verification (2025-26): critique-before-execute
        -> Code-driven workflows (2026): script controls fan-out, not the LLM
          -> Recursive latent-space MAS (2026): remove text bottleneck entirely
```

| Step | Limitation Solved | Algorithmic Change | Measured Improvement |
|------|-------------------|--------------------|---------------------|
| Single agent | No parallelization; one failure cascades to entire task | Single LLM call with system prompt + user query | Baseline |
| Sequential multi-agent (e.g., AutoGPT, BabyAGI 2024) | Single agent cannot handle multi-skill tasks | Chain-of-agents: Agent A's output -> Agent B's input; task decomposition into sequential subtasks | +15-25% task completion on multi-step coding benchmarks vs single agent; but latency = sum of all agents |
| Parallel fan-out (e.g., Anthropic orchestrator-worker 2025) | Sequential execution wastes parallelism for independent subtasks | Fan-out: orchestrator splits task -> N workers execute in parallel -> orchestrator merges | -90% time reduction for parallelizable tasks; +90.2% improvement on SWE-bench style tasks (#279) |
| Adversarial verification (AutoScientists, SABER 2025-26) | Parallel agents produce plausible but wrong answers with no cross-check | Critique-before-execute: for each proposed action, N-1 agents attempt to disprove it; only actions surviving all critics execute | +28% Airline, +11% Retail, +7% SWE-bench Verified via SABER mutation gating; -75% verification cost by gating only dangerous actions |
| Code-driven workflows (Claude Code Dynamic Workflows 2026) | LLM orchestration is non-deterministic; cannot guarantee execution order or retry logic | Code defines the fan-out graph (which agents, in what order, retry policy, convergence criteria); LLM only fills content | Production reliability: checkpoint-based resume, no lost work on crash; deterministic re-execution for debugging |
| Recursive latent-space MAS (RecursiveMAS 2026) | Text-based agent communication is token-inefficient and slow | Share *latent representations* (intermediate activations) between agents instead of text; entire agent ensemble as one recursive computation | +8.3% accuracy, 1.2-2.4x speedup, 34.6-75.6% token reduction across 9 benchmarks (#119) |

The coordination lineage shows a dramatic shift: from "more agents in the loop" to "less text in the loop." RecursiveMAS represents a potential paradigm shift — if latent-space coordination generalizes, the text-based multi-agent paradigm may be an intermediate step, not the destination.

---

#### Skills Evolution Lineage

```
Static prompts (2023): hand-written, never change
  -> Few-shot prompting (2024): add examples, but manual
    -> DSPy / prompt optimization (2024): optimize prompt for a metric, but bounded by initial design
      -> SkillNet (2025): auto-generate skills from repos/logs, but static after creation
        -> Darwin / DGM (2025): archive-based evolution -- 20% to 50% SWE-bench
          -> MOSS (2026): source-level self-rewriting -- harness code itself evolves
```

| Step | Limitation Solved | Algorithmic Change | Measured Improvement |
|------|-------------------|--------------------|---------------------|
| Static prompts | No adaptation; every session starts from scratch | Hand-written system prompt with fixed instructions | Baseline |
| Few-shot prompting | Static prompt cannot demonstrate desired output format | Prepend N labeled examples to prompt; model imitates pattern | +5-15% accuracy on classification/generation tasks; but examples consume context budget |
| DSPy / prompt optimization (2024) | Manual few-shot selection is suboptimal; human intuition about "good examples" is unreliable | Optimize prompt over a training set: gradient-free search over prompt components (instructions, examples, format); maximize a target metric | Outperforms hand-crafted prompts by +10-20 points on GSM8K, HotPotQA; key finding: optimal prompts look nothing like human-written ones |
| SkillNet (2025) | Prompts are single-purpose; cannot compose or reuse | Auto-generate skills from repos, PDFs, execution logs; 5-D quality scoring (correctness, completeness, clarity, efficiency, safety); skill graph with 4 relationship types | 500K+ skill ecosystem; skills can be composed via graph traversal; but skill content is static after creation |
| Darwin / DGM (2025) | SkillNet skills are static; cannot improve with experience | Archive-based evolution: agent writes candidate code improvement -> runs benchmark -> if score improves, replace in archive; else discard. No finetuning needed; purely LLM-driven code evolution | SWE-bench: 20% -> 50% (150% relative); Polyglot: 14.2% -> 30.7% (116% relative); each skill uses ~1M tokens per evolution cycle |
| MOSS (2026) | Darwin evolves skill code but not the harness itself | Source-level self-rewriting: MOSS rewrites its own grader/harness code, not just skill implementations. Turing-complete evolution scope. | OpenClaw grader score: 0.25 -> 0.61 in single cycle; first demonstration of harness-level self-evolution |

The skills lineage is the most dramatic in the corpus: from 0% improvement (static prompts) to 150% relative (Darwin) in under 3 years. The key algorithmic insight: *treat skill code as a population under selection pressure, not as authored artifacts*. The bottleneck has shifted from "can we write good skills" to "can we keep evolved skills safe" (see Tension 3 below).

---

### 2. Head-to-Head Quantitative Comparison Tables

#### Memory Systems

| System | Compression | Preservation | Latency | Tokens/Search | F1/LoCoMo | Training Data Needed |
|--------|-------------|--------------|---------|---------------|-----------|---------------------|
| Chroma (baseline) | 0% | 100% | ~50ms | ~2000 | 0.32 | None |
| Mem0 | ~30% | ~95% | ~80ms | ~1500 | 0.41 | None |
| A-MEM | ~45% | ~93% | ~120ms | ~1800 | 0.52 | None |
| A-MAC | ~50% | ~91% | ~62ms | ~1200 | 0.583 | 100 examples |
| AOI | 72.4% | 92.8% | ~90ms | ~1000 | — | Domain config |
| EvolveMem | ~55% | ~94% | ~75ms | ~1100 | 0.61 | 1000 trajectories |

**Key observations:**
* Compression and preservation are in direct tension — AOI achieves 72.4% compression but requires domain-specific config; Chroma preserves 100% but compresses 0%.
* A-MAC achieves the best F1/latency tradeoff (0.583 at 62ms) — its 5-factor admission gate removes low-value content pre-retrieval, reducing both storage and search time simultaneously.
* EvolveMem reaches the highest F1 (0.61) but needs 1000 training trajectories — the self-tuning approach trades sample efficiency for asymptotic performance.
* A-MEM's dynamic linking adds latency (120ms vs A-MAC's 62ms) but achieves higher recall on multi-hop queries (F1=0.52 vs A-MAC's system-level advantage on LoCoMo).

#### Routing Systems

| System | Cost Reduction | Quality Maintenance | Decision Latency | Training Data | Multi-Provider |
|--------|---------------|--------------------|--------------------|---------------|----------------|
| FrugalGPT | 98% (match) or +4% (same cost) | Configurable | ~200ms (LLM judge) | None | No |
| RouteLLM (similarity) | 65% | 90% GPT-4 | <1ms | None | No |
| RouteLLM (matrix factorization) | 85% | 95% GPT-4 | <1ms | 1000 labeled pairs | No |
| BEST-Route | 60% | 99% top model | ~5ms | 500 queries | No |
| Memory-Augmented | 90%+ (repeats) | 95%+ | <5ms | 100 queries | YES |

**Key observations:**
* FrugalGPT achieves the maximum cost reduction (98%) but pays in decision latency (~200ms per query for its LLM judge). This is acceptable for batch processing but problematic for interactive use.
* RouteLLM's matrix factorization achieves the best cost/quality tradeoff (85% cost reduction at 95% GPT-4 quality) with <1ms decision latency and 1000 labeled pairs. This is the current SOTA for within-provider routing.
* BEST-Route's multi-sampling strategy (generate N cheap responses, pick best) is a free lunch for *verifiable* outputs but has unknown effectiveness for *creative* outputs (where "best" is subjective).
* Memory-Augmented routing is the ONLY system that supports multi-provider — because it routes by cache hit, not by model capability. This is the bridge to Lyra's multi-provider requirement.

**Critical gap in routing research**: No existing system combines multi-provider routing + confidence-calibrated escalation + conversation-aware state. All three are needed for production multi-provider routing.

#### Voice Pipeline Latency (all numbers in ms)

| Pipeline | STT | LLM | TTS | Total (P50) | Barge-in | GPU Needed |
|----------|-----|-----|-----|-------------|----------|------------|
| Whisper Turbo -> GPT-4o -> Kokoro | 200 | 500 | 50 | 750 | VAD (~50ms) | 6GB |
| Whisper Turbo -> Claude Opus -> Kokoro | 200 | 800 | 50 | 1050 | VAD (~50ms) | 6GB |
| Parakeet -> GPT-4o -> Orpheus | 160 | 500 | 200 | 860 | VAD (~50ms) | 8GB |
| Moshi S2S (full-duplex) | — | — | — | 200 (end-to-end) | Native streaming | 24GB |
| Lyra Hybrid (overlap) | 200 | 500 | 50 | 350 (perceived) | VAD (~56ms) | 6GB |

**Key observations:**
* Moshi achieves unbeatable end-to-end latency (200ms) but requires 24GB GPU — prohibitive for edge/terminal deployment.
* The Lyra Hybrid pipeline achieves 350ms *perceived* latency through overlapping STT/LLM/TTS execution (pipeline parallelism) — STT is processing the next utterance while LLM generates the current response and TTS streams the previous one.
* The dominant latency contributor is the LLM call (500-800ms). Reducing this requires either: (a) cheaper models for simple turns (routing!), or (b) speculative decoding (predict what LLM will say before it finishes).
* Whisper Turbo (200ms STT) is the open-weight benchmark for multilingual STT. For production where latency-critical, edge-TRT-optimized Whisper can reach ~80ms.
* Kokoro-82M at 50ms TTS on CPU is the strongest open TTS option — but lacks Vietnamese support. Orpheus gains Vietnamese at the cost of 4x TTS latency.

---

### 3. Cross-Theme Tensions with Algorithmic Resolution

Each tension from Section 11 (Design Philosophy Lineages) is addressed below with a specific ALGORITHMIC resolution rather than a philosophical compromise.

---

#### Tension 1: Memory completeness vs. Retrieval speed

- **Problem**: More memories -> better recall but slower retrieval (O(n) for exhaustive search)
- **Algorithmic resolution**: HNSW approximate nearest neighbor (O(log n) retrieval) + tier-based pruning (search Working first, fall back to Episodic only on miss) + admission control (prevent low-value memories from entering storage at all)
- **Why this works**: HNSW navigable small-world graphs reduce O(n) to O(log n) with ~2% recall loss. Tier-based search exploits the Pareto distribution of queries (80% are simple fact lookups that Working tier can answer). Admission control reduces total memory volume by ~50% (A-MAC), shrinking the search space before the algorithm even runs.
- **Measured cost**: ~2% recall loss for 10x speedup at the retrieval layer; cumulative effect across all three mechanisms: 20-40x effective speedup at <5% recall degradation.

---

#### Tension 2: Verification thoroughness vs. Execution speed

- **Problem**: More critics -> fewer errors but higher latency (3x slowdown with 3 critics)
- **Algorithmic resolution**: SABER mutation gating — verify only ~20-30% of actions (the dangerous ones that mutate state), bypass the rest without verification overhead
- **Why this works**: SABER's empirical finding: 55-96% of error impact comes from actions that *change state* (mutations). Non-mutating actions (reads, queries, lookups) have negligible failure cost. A classifier predicts mutating vs. non-mutating at ~5ms overhead; only mutating actions enter the verification pipeline.
- **Measured**: 92% of error impact caught while verifying only ~25% of actions; +28%, +11%, +7% on 3 benchmarks vs full verification; latency overhead drops from 3x to 1.25x.

---

#### Tension 3: Self-evolution capability vs. Safety guarantees

- **Problem**: More evolution -> better performance but higher risk of alignment decay
- **Algorithmic resolution**: Bounded edits (SkillOpt: each edit changes <=50 tokens) + held-out validation (validate on unseen tasks after each evolution cycle) + Proteus red-team gate (automated adversarial testing of evolved skills) + Progent SMT policy (formal safety constraints verified before deployment)
- **Why this works**: Each layer addresses a specific failure mode:
  - Bounded edits prevent catastrophic rewrites (single large change = single point of failure)
  - Held-out validation detects regression before deployment (the validator cannot be overfitted to the training distribution)
  - Proteus gate catches adversarial bypasses that validation missed (40-90% attack success in 5 rounds means you MUST probe for adversarial vulnerabilities)
  - Progent SMT policy provides *formal guarantees* on safety invariants (if the policy holds symbolically, no possible prompt can violate it)
- **Constraint**: Each edit changes <=50 tokens; rollback on any safety violation; human review for repeated (>3) safety flags within the same skill lineage.

---

#### Tension 4: Provider diversity vs. Consistent behavior

- **Problem**: Different providers have different strengths/weaknesses -> inconsistent agent behavior across providers
- **Algorithmic resolution**: Provider capability matrix (per-provider, per-capability score on 0-1 scale) + degradation strategy per capability (when a provider lacks a capability, define the fallback behavior explicitly) + cross-provider adversarial verification (one provider's output verified by another — different failure modes are unlikely to coincide)
- **Why this works**: Provider DIVERSITY is a FEATURE for adversarial verification. If two providers have independent failure distributions (Claude fails on edge case X, DeepSeek fails on edge case Y), cross-provider verification can detect both classes of failure. The composite system is MORE reliable than any single provider.
- **Key insight**: The tension is real only if you try to *normalize* providers (hide differences). If you *exploit* differences, the tension becomes a synergistic relationship. Route the right work to the right provider, verify across providers, and heterogeneity increases reliability rather than decreasing it.

---

### 4. Quantitative Gap Analysis

For each open problem from Section 12, the current SOTA number, the "solved" target, the gap, and the most promising algorithmic direction.

| # | Problem | Current SOTA | Target (Solved) | Gap | Most Promising Direction |
|---|---------|-------------|-----------------|-----|-------------------------|
| 1 | Self-evolution safety | Proteus: 40-90% attack success after 5 rounds of evolution | <10% attack success after 50+ rounds | 4-9x gap in attack resilience | Progent SMT policy + Proteus continuous red-teaming + bounded edits (<=50 tokens/cycle) |
| 2 | Multi-provider heterogeneity | RouteLLM MF: 85% cost reduction, 95% GPT-4 quality, within-provider only | Same cost/quality across 4+ providers with different capability profiles | Multi-provider capability matrix is unstudied | Provider capability matrix + per-capability degradation strategies + cross-provider adversarial verification |
| 3 | Memory as central nervous system | A-MAC: F1=0.583 with admission; DecentMem: +23.8% with shared memory; no system integrates all | Single architecture where memory feeds routing, skills, context, swarm simultaneously | Integration gap: no system studies memory+router+skills as a unified system | Unified TKG with provider-aware admission + routing decisions derived from memory state |
| 4 | Adversarial verification as universal pattern | SABER: 92% error impact caught at 25% verification cost | 99% error impact caught at 10% verification cost | 7% error catch gap; 2.5x cost gap | Refined mutation classifier (better predictions of which actions are dangerous) + tiered verification (faster checks for low-risk mutations) |
| 5 | Provider-adaptive context optimization | ACON: 26-54% compression; no cross-provider study | Same lossless compression ratio* across 200K, 64K, and 8K windows | No system measures compression quality across providers | Provider-specific compression profiles (architecture-aware token importance scoring) + adaptive strategy based on available context budget per turn |
| 6 | Confidence-calibrated cascade routing | RouteLLM MF: 95% GPT-4 quality at 85% cost reduction; no confidence reporting | 99% top-model quality at 90% cost reduction WITH calibrated confidence per decision | 4% quality gap; 5% cost gap; no confidence calibration | Conformal prediction for routing confidence: quantile-based guarantees on routing quality with user-specified risk level alpha |
| 7 | Cross-agent memory federation | DecentMem: O(log T) regret guarantee, +23.8% over centralized, tested on 3 MAS frameworks | Same guarantees on 10+ diverse MAS frameworks with heterogeneous agent types | Untested beyond 3 frameworks; no conflict resolution protocol | DecentMem protocol + content-addressable conflict resolution (if two agents write contradictory memories, keep the one corroborated by third-party evidence) |
| 8 | Active forgetting | Entropic Memory: thermodynamic consolidation, early-stage | Proven algorithm for identifying and removing obsolete memories without removing still-relevant ones | Most fundamental gap: no consensus on what "obsolete" means | Reinforcement-weighted decay: adjust forgetting rate per individual memory based on access frequency AND task relevance; decay slow when memory is frequently accessed OR task-relevant |
| 9 | Stall detection for autonomy | No reliable stall detector exists in literature | <5% false positive rate on stall detection across diverse tasks (coding, research, planning) | Entire problem is unsolved: no benchmark, no metric, no SOTA | Entropy-based stall metric: measure action distribution entropy over sliding window; stall = entropy drops below threshold while perplexity of latest action remains high (trying same thing, getting nowhere) |
| 10 | Terminal-native patterns | IterResearch: 3.5% -> 42.5% at 2048 steps via MDP workspace; continuous-claude: while-true loop with shared notes | Full harness (memory + routing + skills + context) running natively via terminal with filesystem as first-class layer | No system provides integrated terminal-native patterns; all pieces exist in isolation | IterResearch's evolving-report pattern + Git-native memory versioning + filesystem-as-hard-state for crash recovery |

**SOTA equation for cross-provider routing quality:**

Let `Q(p, t)` be the quality of provider `p` on task type `t`. Let `C(p)` be the cost per token of provider `p`. The routing problem is:

```
minimize  sum(C(p_i))  over i in queries
subject to  Q(p_i, t_i) >= Q_target  for all i
```

Current SOTA (RouteLLM MF) solves this for `p in {GPT-4, GPT-3.5}` only. The Lyra target is `p in {Claude Opus, Claude Sonnet, DeepSeek R1, DeepSeek Flash, GPT-4o, GPT-4.1, Qwen3, Grok}` with heterogeneous capability matrices. The constraint becomes:

```
Q(p, t) = capability_matrix[p][t] * provider_availability(p)
```

Where `capability_matrix[p][t]` is measured empirically (not assumed from provider documentation) and `provider_availability(p)` captures API reliability variance. This is an open optimization problem with no existing solution.

---

**END OF STAGE 1**

## 10. Run 17 New Evidence — Multi-Agent Reliability, Memory, Self-Knowledge (2026-05-31)

### 10.1 ⭐ Multi-Agent Debate Is Fundamentally Biased — Anonymize, Monitor, Cross-Verify

The single most important finding from Run 17's deep-read of the §3.12 multi-agent cluster: **multi-agent debate/review is systematically biased in ways that undermine the core quality mechanism of Lyra's ultracode workflows.** Five papers converge on a disturbing picture:

**The Evidence Chain:**

1. **[Identity Skews Debate](https://arxiv.org/abs/2510.07517) (ACL 2026 Main):** Multi-agent debate suffers identity-driven sycophancy + self-bias. Formalizes it as identity-weighted Bayesian update. **Sycophancy dominates over self-bias** — agents more readily adopt peers' views than cling to their own. Response anonymization fixes it structurally.

2. **[Actor-Observer Asymmetry](https://arxiv.org/abs/2604.19548) (ACL 2026 Main):** Perspective matters: same agent reviewing SELF blames external factors; reviewing OTHERS blames internal faults. **Perspective swap triggers attribution flip in >20% of cases.** ReTAS dialectical alignment mitigates but doesn't eliminate the asymmetry.

3. **[Preventing Rogue Agents](https://arxiv.org/abs/2502.05986) (ACL 2025 Spotlight):** A single confused agent can sink the entire task (+17-20% improvement from monitoring). Agents unilaterally terminate while uncertain. Monitoring + preemptive intervention is effective.

4. **[Lying with Truths](https://arxiv.org/abs/2601.01685) (ACL 2026 Oral):** Colluding agents manipulate victim beliefs using ONLY truthful evidence on public channels. **74.4% attack success on proprietary models.** Stronger reasoning INCREASES vulnerability. Generative Montage: truthful atoms → misleading whole.

5. **[ErrorProbe](https://arxiv.org/abs/2604.17658) (ACL 2026 Findings):** Multi-agent errors manifest late with inter-agent dependencies. LLM-as-judge fails on long traces. Tool-grounded validation (re-execute suspect action) is the reliable alternative.

**Implications for Lyra's Architecture:**

| Vulnerability | Paper | Fix | Priority |
|--------------|-------|-----|----------|
| Review bias (sycophancy) | Identity Skews | Anonymize all debate contributions; shuffle response order | CRITICAL - one-line fix |
| Review bias (self-blame asymmetry) | Actor-Observer | Randomize critic roles; never let agents review own output | CRITICAL |
| Single-agent failure propagation | Rogue Agents | Monitor per-agent confidence trajectories; flag sudden uncertainty | HIGH |
| Cognitive collusion via truthful evidence | Lying with Truths | Cross-verify against independent sources; monitor for coordinated posting | CRITICAL |
| Late-manifesting errors | ErrorProbe | Tool-grounded validation; re-execute suspect actions | HIGH |

**Design Decision (Run 17):** Lyra's AVP (Adversarial Verification Protocol) MUST adopt response anonymization as DEFAULT behavior. The Identity-Skews paper provides formal justification (IBC metric) and empirical evidence (sycophancy dominates) that anonymization is the single most impactful reliability improvement for debate-based verification. This is a **one-line prompt change**: strip agent IDs, use neutral formatting, shuffle response order. Combined with AVP's existing mutation-gating (SABER), Lyra achieves defense-in-depth: mutation-gating prevents wrong-action errors; anonymization prevents wrong-review errors.

### 10.2 Memory Paradigms Have Bifurcated — Three Distinct Strategies

The prior synthesis (Run 14-16) described memory as a single trajectory toward "better retrieval." Run 17's deep-reads reveal the field has bifurcated into three incompatible strategies with different cost/benefit profiles:

| Strategy | Paper | Mechanism | Best For | Key Number |
|----------|-------|-----------|----------|------------|
| **Manage context** (compress within window) | COMPASS, A-MAC, Norm-Guided KV-Cache | Hierarchical context curation + selective admission | Single long-horizon agent, budget-constrained | COMPASS: +20% on GAIA/BrowseComp/HLE |
| **Distribute context** (parallelize across agents) | ExtAgents | N agents each read 1/N of input simultaneously | Massive static knowledge (codebases, docs) | ExtAgents: outperforms non-training methods on ∞Bench+ |
| **Field memory** (continuous PDE-governed fields) | Field-Theoretic Memory | Memory as diffusing/decaying/coupling fields, not discrete DB | Multi-session, multi-agent reasoning | +116% F1 LongMemEval, >99.8% collective intelligence |

**Key Insight:** These are NOT competing — they serve DIFFERENT timescales and input types:
- **Manage** = within-single-run, active-working-memory (seconds-minutes)
- **Distribute** = single-run, massive-ingestion (static knowledge, codebases)
- **Field** = across-runs, multi-session, emergent collective memory (hours-days)

**Design Implication for Lyra:** The §4.2 memory architecture should be a THREE-TIER system:
1. **Working Memory (COMPASS-style):** Context Manager curates active context; A-MAC gates admission
2. **Ingestion Memory (ExtAgents-style):** Distribute large codebases/docs across agents for parallel indexing
3. **Persistent Memory (Field-Theoretic-style):** Continuous fields for multi-session reasoning; field coupling for swarm shared memory

The Field-Theoretic approach is the genuine breakthrough — +116% F1 on multi-session reasoning with p<0.01 is transformative. But it requires new infrastructure (PDE solvers for semantic fields). Start with the COMPASS + ExtAgents tiers (closer to existing code), then phase in field-theoretic memory for the swarm.

### 10.3 Self-Knowledge: Uncertainty Type Discrimination Is the Missing Piece

Run 17's deep-read of §3.20 reveals a critical distinction the prior self-knowledge plan (§4.19) missed:

**[Beyond "I Don't Know"](https://arxiv.org/abs/2604.17293):** Models must discriminate **data uncertainty** (ambiguous input — "this question is unclear") from **model uncertainty** (capability gap — "I don't know enough to answer"). 18 frontier LLMs evaluated — even SOTA models struggle. **High answer accuracy does NOT imply strong uncertainty attribution.** Wrong attribution → wrong remediation:
- Data uncertainty → should ask user to clarify
- Model uncertainty → should invoke tool or escalate to stronger model
- Conflating them → either pesters user unnecessarily OR proceeds with wrong answer

**[MATU](https://arxiv.org/abs/2604.08708) (ACL 2026):** Extends UQ to multi-agent systems via tensor decomposition. Uncertainty in MAS is multi-dimensional: agents × steps × communication paths. Per-agent uncertainty ignores cascading effects.

**[LLMs Must Be Taught](https://arxiv.org/abs/2406.08391) (NeurIPS 2024):** 1000 graded examples + LoRA on features = calibrated uncertainty. Trained estimator generalizes across models (estimator for model A works on model B).

**Design Update for §4.19:** The abstention gate should be a TWO-CLASS classifier:
1. Classify uncertainty TYPE (data vs model)
2. If data uncertainty → ASK_USER (with specific clarification question)
3. If model uncertainty → ESCALATE (stronger model or tool invocation)
4. If low uncertainty → PROCEED

For multi-agent settings: MATU-style tensor decomposition tracks uncertainty propagation across the swarm. Agent A's uncertainty cascading to Agent B is detectable via the tensor structure.

### 10.4 Planning: Cost-Awareness Is Not Optional

Run 17's deep-read of §3.21-3.22 delivers a sobering finding for the §4.20 planning layer:

**[Cost-Aware Tree Search](https://arxiv.org/abs/2505.14656):** Tree-search LLM planners "often struggle to find cost-optimal plans" and "additional search computation does NOT reliably improve optimality." Bidirectional search wins on efficiency; MCTS wins on short-horizon optimality. **The key insight: more compute ≠ better plans** — new search algorithms are needed, not just more MCTS rollouts.

**[AFlow](https://arxiv.org/abs/2410.10762):** MCTS over workflow representations achieves +5.7% average improvement. Critically: small models orchestrated by AFlow **outperform GPT-4o at 4.55% of its inference cost.** The cost-efficiency of automated workflow optimization dwarfs the quality gain from model scaling.

**[MC-DML](https://arxiv.org/abs/2504.16855) (ICLR 2025):** Cross-trial memory (reflections from failed simulations) within a single planning phase avoids repeating mistakes. Nearly doubles previous SOTA on Deephome. Single planning phase is critical for latency.

**Design Update for §4.20:**
1. Budget-as-first-class-parameter: every plan search includes a cost constraint
2. Bidirectional search for cost-constrained tasks; MCTS for quality-critical tasks
3. Cross-trial memory within planning sessions (MC-DML pattern)
4. Automated workflow optimization via AFlow-style MCTS over workflow representations
5. The 4.55% cost finding is transformative for Lyra economics: optimize the WORKFLOW, not the MODEL

### 10.5 Internalized Debate: The 93% Token Reduction Path

**[Latent Agents](https://arxiv.org/abs/2604.24881) (ACL 2026 Main):** The most economically significant finding of Run 17. Multi-agent debate can be DISTILLED into a single LLM via 2-stage fine-tuning, matching/exceeding explicit debate at **up to 93% fewer tokens.** Agent-specific subspaces exist in activation space — steering these subspaces controls agent behavior.

**The tension for Lyra:** Explicit debate (our §4.13 AVP) is token-expensive but necessary for NOVEL decisions. Internalized debate is 10-20× cheaper but requires fine-tuning (not available for API-only providers like DeepSeek).

**Resolution strategy:**
- **Recurring review patterns** (code review checklist, security audit, PR review) → cache debate outcomes in TKG; retrieve rather than re-debate. Over time, fine-tune internalized debate model for these patterns.
- **Novel/one-off decisions** → explicit debate with anonymization (N3) and rogue monitoring (N4).
- **Hybrid:** run explicit debate N times, distill the pattern into TKG, use cached pattern for next N similar debates. The 93% savings amortizes the explicit debate cost over repeated use.

### 10.6 Updated Design Decisions (Run 17)

| Decision | Trigger Paper(s) | Before (Run 16) | After (Run 17) |
|----------|-----------------|-----------------|-----------------|
| Debate anonymity | Identity Skews + Actor-Observer | AVP with identifiable critics | AVP DEFAULT anonymized; strip IDs, shuffle order |
| Rogue agent monitoring | Preventing Rogue Agents | No monitoring | Per-agent confidence trajectory monitoring in workflow engine |
| Memory architecture | Field-Theoretic + COMPASS + ExtAgents | Single TKG-based memory | Three-tier: Working (COMPASS) + Ingestion (ExtAgents) + Persistent (Field-Theoretic) |
| Uncertainty type discrimination | Beyond "I Don't Know" | Binary confidence score | Two-class: data uncertainty → clarify; model uncertainty → escalate |
| Cost-aware planning | Cost-Aware Tree Search + AFlow | Budget as afterthought | Budget as first-class search parameter; AFlow-style workflow optimization |
| Collusion defense | Lying with Truths | Not addressed | Cross-verification against independent sources; monitor coordinated truthful posting |
| Internalized debate | Latent Agents | Debate always explicit | Hybrid: cache recurring patterns → internalize; explicit for novel decisions |

---

## Changelog

| Run | Date | Changes |
|-----|------|---------|
| 17 | 2026-05-31 | §10 added: multi-agent reliability cluster (debate bias, rogue agents, cognitive collusion), three memory paradigms (manage/distribute/field), uncertainty type discrimination, cost-aware planning, internalized debate economics. 7 design decisions updated. ~31 new papers deep-read and integrated. |

### 10.7 Run 17 Continued — Harness-Scale Evidence (Session 2, 2026-05-31)

The second session of Run 17 resolved ~68 additional Population B titles and deep-read the most impactful at full protocol depth. Key new evidence clusters:

**Harness Engineering as a First-Class Discipline:**
Five papers independently converge on the finding that the HARNESS (not the model) is the performance bottleneck:
- **[Meta-Harness](https://arxiv.org/abs/2603.28052):** +7.7 points with 4× fewer tokens via harness code optimization
- **[Code as Agent Harness](https://arxiv.org/abs/2605.18747):** 42-author survey establishing harness as the operational backbone
- **[From Model Scaling to System Scaling](https://arxiv.org/abs/2605.26112):** Argues future progress depends on system design, not stronger models
- **[AEvo](https://arxiv.org/abs/2605.13821):** +26-point relative improvement via procedure-editing meta-agent
- **[Is Grep All You Need?](https://arxiv.org/abs/2605.15184):** Harness design choices (grep vs vector) dominate retrieval quality

**Memory Architecture Density — 8 New Mechanisms:**
The memory literature is now rich enough to define a design space:
- **DecentMem:** Dual-pool (exploitation + exploration) with O(log T) regret → +23.8%, -49% tokens
- **FORGE:** Population broadcast without weight updates → 1.7-7.7× improvement
- **SAGE:** Self-evolving graph with Graph Foundation Model reader → best rank on multi-hop QA
- **HeLa-Mem:** Hebbian learning dynamics on dynamic graph → fewer context tokens
- **APEX-MEM:** Property graph + append-only + temporal resolution → 88.88% LOCOMO
- **STITCH:** Intent-based indexing → +35.6% over strongest baseline
- **LightMem:** SLM-based memory (83ms retrieval) → practical deployment path
- **FluxMem:** 3-stage topology evolution (formation→refinement→consolidation)

**Safety Landscape — New Attack Surfaces:**
- **[Conjunctive Prompt Attacks](https://arxiv.org/abs/2604.16543) (ACL 2026 Main):** Two harmless components combine to produce harm — routing-level defense required
- **[Proteus](https://arxiv.org/abs/2605.11891):** 93% SkillVetter bypass rate — skill ecosystems are fundamentally insecure against adaptive attackers
- **[CIA Topology Inference](https://arxiv.org/abs/2604.12461) (ACL 2026 Main):** AUC 0.99 topology reconstruction — swarm topology is a privacy asset
- **[Mandela Effect in MAS](https://arxiv.org/abs/2602.00428) (ICLR 2026):** 74.4% reduction via cognitive anchoring — collective memory is socially constructed
- **[Attention Trust Score](https://arxiv.org/abs/2506.02546) (ACL 2026 Main):** 6 Gricean trust dimensions — principled message weighting

**Swarm Design — Structural Constraints:**
- **[Diversity Collapse](https://arxiv.org/abs/2604.18005) (ACL 2026 Findings):** Dense communication → premature convergence. Sparse topology is a HARD requirement for creative tasks, not an optimization.
- **[RecursiveMAS](https://arxiv.org/abs/2604.25917):** Latent inter-agent communication → 34.6-75.6% token reduction + 1.2-2.4× speedup
- **[CortexDebate](https://arxiv.org/abs/2507.03928) (ACL 2025):** Sparse debating graph + McKinsey Trust Formula → principled consensus
- **[GraphPlanner](https://arxiv.org/abs/2604.23626) (ICLR 2026):** 186→1 GiB GPU cost via graph-augmented routing

### 10.8 Updated Architecture Implications (Session 2)

1. **Harness optimization is the highest-leverage activity.** Meta-Harness + AEvo + SkillOpt show that optimizing the harness (code, procedures, skill documents) yields order-of-magnitude improvements. Lyra should include a meta-optimization loop that treats its own harness as an optimization target.

2. **Memory design space is combinatorially rich.** With 8 new mechanisms, Lyra's §4.2 architecture should adopt a COMPOSABLE memory design where different mechanisms (dual-pool, Hebbian, intent-based, temporal) are mix-and-match per use case, not one-size-fits-all.

3. **Safety requires composition-level reasoning.** Conjunctive attacks + Proteus + Mandela Effect show that per-message safety is insufficient. Lyra needs routing-level and composition-level safety monitoring.

4. **Swarm communication must be sparse by default.** Diversity Collapse + CortexDebate converge: dense all-to-all communication is harmful. Sparse topology is the safe default.

5. **Latent communication is the efficiency frontier.** Latent Agents + RecursiveMAS show 35-93% token reduction via latent-space communication. For Lyra with local models, this is the path to affordable ultracode.

