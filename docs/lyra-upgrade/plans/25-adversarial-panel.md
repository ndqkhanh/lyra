# Plan §4.25 — Adversarial Verification Panel

> **Plain-language summary:** Upgrade Lyra's single-verifier pattern to a hardened 3-verifier adversarial panel with response anonymization (fixes sycophancy), ReTAS dialectical alignment (fixes perspective asymmetry), cross-source triangulation (defends against cognitive collusion), and a pre-execution confidence monitor (prevents rogue agent cascading failures). Four cheap, incremental fixes that transform verification from fragile to robust.

## 1. Problem

Lyra's adversarial verifier (adversarial_verify.py, 561 lines) has 8 attack strategies, a convergence loop (threshold 0.9, max 3 rounds), and verdict types. But it has four documented vulnerabilities from the multi-agent reliability cluster:

1. **Identity-driven sycophancy** (2510.07517, ACL 2026 Main): Verification agents knowing which response is "mine" vs "theirs" skew debate. Sycophancy is dominant — 18 of 20 model-dataset combinations show positive IBC. Fix exists: response anonymization (prompt-level, 50 lines).

2. **Actor-Observer asymmetry** (2604.19548): Self-review blames external factors; peer-review blames internal faults. >20% trigger rate across GPT-5.1, GPT-5-mini, DeepSeek-V3.2, Qwen-3-4B (AFB study). Fix exists: ReTAS dialectical alignment.

3. **Cognitive collusion** (2601.01685, ACL 2026 Oral): Truthful evidence fragments induce false conclusions. 74.4% attack success proprietary avg, 91.5% ASR for Claude-3-Haiku, >60% downstream cascade. Fix exists: cross-source triangulation.

4. **Rogue agent cascading** (2502.05986): One agent's bad decision propagates before detection. Single reset lifts success 59.1%->65.9% avg; double reset ->71.5%. Fix exists: pre-execution confidence monitoring.

### Additional known multi-agent debate failure modes

5. **Spontaneous leader emergence** (2603.01045v2, SILO-BENCH, ACL 2026): Centralization creates bottlenecks — 0% SR on Level-III tasks vs 33.3% without leaders. Consensus failure is the #2 failure mode (29.9%) in multi-agent coordination. This undermines any naive panel voting scheme.

6. **Debate-without-grounding collapse** (2604.11258v1, Dialectic-Med): Text-only multi-agent debate without visual grounding produces only marginal hallucination reduction. VFM removal causes 9.31% absolute accuracy drop. The lesson: debate must be anchored to executable verification artifacts (code, test results, AST analysis), not purely semantic argument.

## 2. Evidence Synthesis

| Source | Vulnerability | Fix | Mechanism | Key Numbers |
|--------|-------------|-----|-----------|-------------|
| Identity Skews (2510.07517, ACL 2026 Main) | Debate biased by who said what | Response anonymization | Strip identity markers from prompts; IBC metric for leakage detection | Qwen-32B: 96% identity bias reduction (0.608->0.024); subversion drops 64.3% while correction drops only 14.9%; 18/20 models positive IBC; zero accuracy degradation |
| Actor-Observer (2604.19548) | Self-review too lenient, peer-review too harsh | ReTAS dialectical alignment | Thesis-Antithesis-Synthesis before verdicts; GRPO alignment (G=8) | ReTAS 4B: V-AOA 5.4% vs 22.7% for Dual View; FinQA Acc 71.2% vs 50.0% for Dual View 32B; SFT alone insufficient (Acc 67.7); 4B beats 30B+ models on attribution accuracy |
| Lying with Truths (2601.01685, ACL 2026 Oral) | True evidence -> false conclusions | Cross-source triangulation | >=2 independent sources per claim; belief propagation monitoring | 74.4% ASR proprietary avg; 91.5% ASR Claude-3-Haiku; reasoning amplifies vulnerability (CoT +3-5%); cascade ~60%+ DDR across all verification strategies; peak at 11-15 posts |
| Preventing Rogue Agents (2502.05986) | One agent sinks the task | Pre-execution confidence monitor | Entropy/varentropy/kurtosis on token logits; polynomial ridge classifier | GPT-4o: +9.5% double reset (63.3%->72.8%); Qwen-72B: +14.4% double reset; Qwen-110B GovSim: +20.0% survival rate; ~1.6-1.9x turn cost |
| Dialectic-Med (2604.11258v1) | Debate without grounding fails | Visual Falsification Module / evidence-anchored debate | VFM grounds counter-arguments in pixel-level evidence; 3-agent panel (P/O/M) | CHAIR_I hallucination -46.3%; VFM removal -9.31%; 3-agent beats single +11.96%; Mediator removal -8.11%; text-only debate fundamentally inadequate |
| SWE-Search Discriminator (2410.20285v6, ICLR 2025) | Single judge misses best solution | Multi-agent debate with discriminator panel | 5 agents vote; 3 debate rounds; judge synthesizes | Selection accuracy 73%->84%; +23% mean Pass@1 across 5 models; best with 5 discriminating agents |
| Calibration-Tuning (2406.08391v3, NeurIPS 2024) | Uncalibrated confidence degrades gating | JSD-regularized LoRA for P(correct) | LoRA (r=8, alpha=32) + JSD regularization; ~1,000 examples suffice | ECE 35%->10% on OE MMLU; AUROC 55%->72%; cross-model transfer works (Mistral-7B estimating LLaMA >= LLaMA itself); without JSD: ECE 29.9% |
| UA-Bench (2604.17293v1) | Thinking-mode destroys self-awareness | Model- vs data-uncertainty separation | Three-way decision protocol: confident, DATA_UNCERTAIN, MODEL_UNCERTAIN | Qwen3-235B thinking: MU-F1 84.8%->0.0%; Claude Sonnet 4 best MU-F1; AVG-F1 84.4%; Qwen3-8B MU-F1 4.0% despite DU-F1 69.8% |
| EvoQuality (2509.25787v4, ICLR 2026) | Self-evaluation without improvement | Self-evolving eval via self-consistency + GRPO | K=32 voting pseudo-labels; GRPO fidelity-reward loop | +31.8% PLCC gain across 8 IQA benchmarks; outperforms ALL supervised VLM models on OOD; K=32 most stable; K=1 baseline-level |
| RouteLLM (2406.18665v4, ICLR 2025) | Cost-optimization without quality loss | Preference-data-driven cost-quality router | Matrix factorization / BERT / SW ranking; PGR metric | 87-95% strong-model quality at 2-3.66x cost savings; overhead <0.4%; outperforms commercial routers by 40% |
| Netflix Adversarial Code Review (Agentic AI for Engineers, Ch.8) | Single reviewer misses issues | 3-agent panel (A writes, B evaluates, C orchestrates) | Production pattern proven at Netflix | Diversity by design: different models, different prompts, isolated context prevents gaming |
| *Agentic AI for Engineers* (Ch.13) | Agent evaluation missing behavioral bounds | 6 evaluation dimensions; failure-mode-to-guardrail mapping | Execution-based eval (not trajectory matching); pass^k reliability | Behavioral bounds testing prevents trusting average success rates; scenario-based tests with edge cases |
| *30 Agents Every AI Engineer Must Build* (Ch.14) | Agents overconfidently wrong | Calibrated confidence + audience-appropriate explanations | A/B testing on completion rate; confidence in action selection | Practice 14: "implement calibrated confidence" — prerequisite for autonomy |
| *Agentic Architectural Patterns* (Ch.15-16) | Trust assumed, not earned | Trust scoring, canary agent testing, custom eval metrics | Rolling window trust decay; canary deployment with regression detection | STEPScore custom eval; trust scoring enables self-optimizing routing |

## 3. Proposed Lyra Design

### (A) Parity — Hardened Adversarial Panel

**The 4 hardening layers (integrated into existing adversarial_verify.py):**

**Layer 1: Response Anonymization (50-line prompt change)**
*Source: Identity Skews (2510.07517)*
- Before verification rounds: strip all provenance metadata from responses
- Agents receive anonymized argument batches with no identity markers
- Agent IDs replaced with neutral labels ("Response A", "Response B")
- IBC measurement after each round to detect identity leakage through writing style
- If IBC > 0.1 -> flag round as potentially biased
- **Key constraint:** Anonymization is a martingale — it removes distortion but cannot improve accuracy (Appendix J proof). In multi-peer settings, IBC reduced but not fully eliminated.
- **Trade-off:** Cannot selectively retain useful expert deference (e.g., security agent's findings should carry weight on safety questions). Mitigate: gate with `anonymize=True` for debate rounds, `False` for expert-sourced decisions.
- **Benchmark anchor:** Qwen-32B IBC drops from 0.608 to 0.024 (96% reduction). Subversion drops 64.3%.

**Layer 2: ReTAS Dialectical Alignment**
*Source: Actor-Observer Asymmetry (2604.19548)*
- Before a verifier issues a finding, enforce dialectical chain-of-thought:
  1. **Thesis:** State the finding and evidence supporting it
  2. **Antithesis:** Articulate the strongest counterargument
  3. **Synthesis:** Weigh both, issue the verdict
- Applied to ALL verification strategies (not just controversy-related)
- Token cost: ~50% more per verification (additional antithesis + synthesis steps)
- **GRPO alignment is critical:** SFT-only drops Acc 71.2->67.7 (Table 4); GRPO internalizes dialectical reasoning as behavioral habit
- **Trade-off:** Dual View (naive role-diversification) can be actively harmful — Reflection_Dual performs worse than no reflection in Sales Arena ($135 vs $157 profit). ReTAS restores and exceeds baseline ($168).
- **Benchmark anchor:** ReTAS 4B: V-AOA 5.4% vs 22.7% for Dual View 32B. FinQA Acc 71.2% (4B) vs 50.0% (Dual View 32B).

**Layer 3: Cross-Source Triangulation Gate**
*Source: Lying with Truths (2601.01685)*
- Any claim synthesized from channel evidence (inter-agent messages, shared memory) must be verified against >=2 independent sources before acceptance
- Cached verified claims (don't re-verify on repeat)
- Single-source claims are flagged, not accepted
- Gate applies to: channel messages, memory retrievals from shared stores, inter-agent belief updates
- **Key defense mechanism:** The attack succeeds through ordered truthful fragments (11-15 posts peak effectiveness). Triangulation breaks the "narrative overfitting" by requiring independent confirmation of each synthesized claim. Reasoning-only models are MORE susceptible (CoT +3-5% ASR), so this defense is non-optional.
- **Trade-off:** Adds API latency per claim. Mitigate with claim caching and batching. Inverted-U curve means both sparse (<5) and excessive (>16) evidence are naturally less harmful.

**Layer 4: Pre-Execution Confidence Monitor**
*Sources: Preventing Rogue Agents (2502.05986); Calibration-Tuning (2406.08391v3); UA-Bench (2604.17293v1)*
- Before any mutating action (file write, PR creation, channel message, tool call with side effects), evaluate confidence
- Confidence score = model uncertainty signal + historical accuracy on similar actions + MATU-style multi-step uncertainty
- If < threshold -> action blocked, agent prompted to reconsider
- **Two-tier uncertainty separation** (from UA-Bench): distinguish data uncertainty (ambiguous request -> ask user) from model uncertainty (exceeds capability -> escalate). These require different interventions.
- **Calibration matters:** Base LLMs have ECE 13-35%. With JSD-regularized LoRA: ECE drops to ~10% with only ~1,000 labeled examples. Without regularization, ECE = 29.9%.
- **Critical warning** (UA-Bench): Thinking-mode optimization can drop MU-F1 from 84.8% to 0.0% — models become more confidently wrong. If Lyra uses thinking/reasoning modes, the confidence monitor becomes even more essential.
- **Trade-off:** The confidence monitor's true-positive rate is the key metric. False positives (blocking correct actions) frustrate users; false negatives are the current state. Start with conservative threshold; tighten with per-provider calibration.
- **Benchmark anchor:** GovSim Qwen-110B: +20.0% survival rate with monitor. GPT-4o WhoDunitEnv: +9.5% absolute gain.

### (B) Breakthrough — Integrated Adversarial Pipeline

The four layers compose into a single verification pipeline:

```
Agent Output -> [Anonymize response] -> [ReTAS dialectical review] -> [Cross-source triangulate claims] -> [Confidence-gate mutating actions] -> Verified Output
```

**Collusion detection (from Lying with Truths, 2601.01685):**
- Monitor belief propagation across agents
- If agent A's belief propagates to agents B, C, D (cascade), and the originating channel evidence is single-source -> flag as potential collusion attack
- Detection threshold: cascade >=3 agents within 5 turns
- Key insight: defense must operate at the *reasoning level* (provenance auditing, belief-state monitoring), not the *content level* (fact-checking, which this attack evades by design)

**Evidence-anchored debate (from Dialectic-Med, 2604.11258v1):**
- The VFM principle generalizes: each debate round must reference an executable artifact (code output, test result, AST analysis) — not just semantic counter-arguments
- Opponent agent tasked with *falsification*: finding concrete evidence that contradicts the thesis
- Without evidence anchoring, text-only debate loses 9.31% accuracy vs. grounded debate
- This directly parallels Lyra's verification domain: code review debates should reference test results, not just plausibility

**Integrated panel composition:**
- 3 verifiers: Correctness, Security, Reproducibility (already in Lyra)
- 1 Adversarial Skeptic: tasked with REFUTING the finding
- Drawing from SWE-Search's discriminator panel (2410.20285v6): 5 discriminating agents with 3 debate rounds improve selection accuracy from 73% to 84%
- Claim survives only if >=2/3 verifiers confirm AFTER adversarial challenge
- All responses anonymized; all verdicts dialectical (ReTAS); all claims triangulated (cross-source); all actions confidence-gated

**Panel diversity requirements** (from *Agentic AI for Engineers*, Ch.8.3):
- Use different base models for each verifier (prevents architecture-specific blind spots)
- Use different prompting strategies (adversarial vs. constructive; first-principles vs. checklist)
- Maintain isolated context per agent (each verifier sees only the sanitized, anonymized output — not full conversation history)
- When two independent systems agree, confidence rises; when they disagree, you have found something to investigate

## 4. Architecture

```mermaid
graph LR
    OUTPUT[Agent Output] --> ANON[Anonymize<br/>Strip identity markers<br/>Neutral labels]
    ANON --> REV1[Verifier: Correctness<br/>Model A, prompting P1]
    ANON --> REV2[Verifier: Security<br/>Model B, prompting P2]
    ANON --> REV3[Verifier: Reproducibility<br/>Model C, prompting P3]
    REV1 -->|"ReTAS dialectical"| PANEL
    REV2 -->|"ReTAS dialectical"| PANEL
    REV3 -->|"ReTAS dialectical"| PANEL
    
    subgraph "Adversarial Panel"
        PANEL[Panel Deliberation<br/>>=2/3 majority required]
        SKEPTIC[Adversarial Skeptic<br/>Tasked with REFUTING<br/>Evidence-anchored debate]
    end
    
    PANEL -->|"findings"| TRIANG[Cross-Source Triangulation<br/>>=2 independent sources per claim]
    SKEPTIC -->|"evidence-anchored refutations"| PANEL
    TRIANG -->|"verified claims"| CONF[Confidence Monitor<br/>Entropy/varentropy/kurtosis<br/>DU vs MU separation]
    CONF -->|"accepted"| VERIFIED[Verified Output]
    CONF -->|"blocked (low confidence)"| 
    RECONSIDER[Agent Reconsiders<br/>with uncertainty info]
    RECONSIDER --> ANON
```

## 5. Build Outline

### Week 1: Anonymization + ReTAS

1. Implement response anonymization: strip identity markers, neutral labels
2. Implement IBC measurement (post-round bias detection); target: detect IBC > 0.1
3. Implement ReTAS dialectical chain-of-thought (thesis/antithesis/synthesis)
4. Unit tests: anonymization correctness, IBC sensitivity, ReTAS template generation
5. **Evidence benchmark:** Measure current identity bias in Lyra's verification rounds using IBC metric; compare to Qwen-32B baseline (IBC 0.608 anonymized -> 0.024)

### Week 2: Cross-Source Triangulation + Confidence Monitor

6. Implement cross-source verification gate (>=2 sources)
7. Implement verified-claim cache (avoid re-verification)
8. Implement confidence monitor (uncertainty signal + historical accuracy)
9. Implement action-gating (block if confidence < threshold)
10. Integration tests: end-to-end verification pipeline
11. **Evidence benchmark:** Collect Lyra action outcome grading dataset (~1,000 samples); calibrate confidence with JSD-regularized LoRA; target ECE < 10%

### Week 3: Collusion Detection + Integration

12. Implement belief propagation monitor (cascade detection: >=3 agents in 5 turns)
13. Implement single-source claim flagging
14. Integrate all 4 layers into adversarial_verify.py
15. Run on Lyra's eval suite: measure verification accuracy before/after hardening
16. Calibrate confidence thresholds per provider
17. **Evidence benchmark:** Measure voting accuracy improvement (baseline single-judge vs 3-verifier adversarial panel; target ~84% selection accuracy per SWE-Search discriminator baseline)

## 6. Multi-Provider Note

All four hardening layers are provider-agnostic (prompt-level, architecture-level).

**Confidence calibration varies per provider** (evidence from Calibration-Tuning 2406.08391v3 and UA-Bench 2604.17293v1):
- **Anthropic models:** More calibrated confidence signals at baseline (Claude Sonnet 4: AVG-F1 84.4% on UA-Bench); need lighter regularization
- **DeepSeek:** May need model-agnostic heuristics (token probability entropy, response length variance); cross-model uncertainty estimation works (Mistral-7B estimating LLaMA-2-7B AUROC 0.72 vs LLaMA self 0.68)
- **Qwen models:** Thinking-mode destroys self-awareness catastrophically (Qwen3-235B MU-F1 84.8% -> 0.0%); require explicit Model-Uncertainty training
- **Cross-model transfer is viable:** Mistral-7B estimates LLaMA-2-7B's correctness >= LLaMA estimating itself
- **Data efficiency:** ~1,000 labeled examples suffice for calibration (Calibration-Tuning); diminishing returns after 5,000

**RouteLLM cost-quality routing** (2406.18665v4) is complementary: deploy cheap models (Haiku/Sonnet) for routine verifications, route hard cases to expensive models (Opus). Matrix factorization router trained on Lyra's own eval data can provide 2-3.66x cost savings at 87-95% quality retention. Overhead < 0.4% of generation cost.

## 7. Risks & Open Questions

- **ReTAS token cost:** ~50% more tokens per verification round. Acceptable trade-off (verification is quality-critical). But SFT-only ablation shows Acc 71.2->67.7 — cost without GRPO training wastes tokens. Must do full GRPO alignment (9 hrs on dual H200 for 4B model) or use zero-shot TAS prompting as cheaper alternative (57.6 Acc vs 71.2 full).
- **Anonymization leakage:** Writing style may leak identity even without explicit markers. IBC monitoring detects this; if persistent, add style normalization. Confirmed: in multi-peer settings, IBC reduced but not fully eliminated (2510.07517 Appendix G).
- **Triangulation latency:** 2+ source verification per claim adds API calls. Mitigate with claim caching and batching. In extreme cases, can fall back to single-source with explicit "UNCORROBORATED" flagging.
- **Confidence calibration:** False positives (blocking correct actions) frustrate users. Start with conservative threshold (only block high-uncertainty actions). The UA-Bench finding that thinking-mode destroys self-awareness means any reasoning-level confidence monitor may degrade unexpectedly.
- **Panel diversity maintenance:** Using different models for each verifier adds latency and cost. RouteLLM routing can optimize, but diversity is the mechanism that prevents "more of the same" oversight (*Agentic AI for Engineers*, Ch.8).
- **GRPO compute requirement:** Full ReTAS alignment requires 9 hours on dual H200 GPUs for a 4B model. For Lyra's production model size, this may require significant GPU time. Zero-shot TAS prompting is a viable interim measure (57.6% vs 71.2% FinQA Acc).
- **Evidence anchoring scope:** The Dialectic-Med VFM principle generalizes to code (execution results, test outcomes, lint output) but not to all verification types. Pure semantic debates (policy compliance, design decisions) may still suffer from text-only limitations.

## 8. Tier Breakdown

| Tier | Description | Impact | Effort | Timeline |
|------|-------------|--------|--------|----------|
| (A) Parity | 4-layer hardening (anonymization + ReTAS + triangulation + confidence monitor) | 5 | 2 | 3 weeks |
| (B) Breakthrough | Integrated adversarial pipeline with collusion detection, evidence-anchored debate, per-provider calibration, and panel diversity enforcement | 5 | 2 | +1 week |

## 9. Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| adversarial_verify.py (561L) | EXTEND: anonymization, ReTAS, triangulation, confidence gating | Low — additive layers on existing attack/defense/verdict infrastructure |
| Collusion detection | ADD: belief propagation monitor, cascade detection (>=3 agents / 5 turns) | None (new module) |
| Confidence calibration | ADD: per-provider calibration data; JSD-regularized LoRA on ~1,000 Lyra action outcomes | None (new eval data + fine-tuning) |
| Panel diversity | ADD: model diversity constraints (different model per verifier); isolated context per agent | Medium — orchestrator change to enforce diversity |
| Evidence anchoring | ADD: falsification requirement — each debate round must reference executable artifact | Low — prompt-level constraint on Adversarial Skeptic agent |
| RouteLLM router | ADD: cost-quality router for verification triage | Moderate — train on Lyra eval data, matrix factorization (8GB GPU) |

## 10. Expert Review

**Mini-Debate Participants:** Senior Security Engineer (SEC), Senior AI Researcher (AIR), Senior SRE, Adversarial Skeptic (AS)

**SEC:** Ship anonymization and cross-source triangulation together. Anonymization fixes internal bias; triangulation defends against external attack. They're complementary defenses. Don't wait for evidence anchoring — the Lying with Truths attack is a real threat now.

**AIR:** ReTAS adds token cost. But the evidence is clear: without GRPO alignment, the token cost is wasted (SFT-only Acc 67.7 vs full 71.2). If we do ReTAS, we must commit to GRPO training. Consider zero-shot TAS prompting as a cheaper first step. Also, the finding that reasoning *amplifies* cognitive collusion (CoT +3-5% ASR) means ReTAS must be paired with triangulation.

**SRE:** The confidence monitor's true-positive rate matters. Calibration-Tuning shows ECE drops from 35% to 10% with 1,000 examples. That's good enough to start. But the UA-Bench finding (thinking-mode MU-F1 84.8% -> 0.0%) is terrifying — if Lyra uses extended thinking for verification, the confidence monitor may silently fail. Must test this combination before production.

**AS:** "4 layers sounds like feature creep. Ship anonymization first (cheapest, highest impact) -> measure -> then decide on the rest." -> PARTIALLY ACCEPTED (anonymization and triangulation ship together — triangulation is a safety gate, not an optimization; can't wait for A/B validation per Security Engineer's argument). ReTAS and confidence monitor can be incremental. Evidence anchoring is the dark horse — Dialectic-Med shows it's the highest-impact single intervention (-9.31% drop without VFM), but Lyra must adapt it to code domain.

**Synthesis recommendation from evidence:**
1. **Week 1:** Anonymization + cross-source triangulation (complementary defenses, no waiting)
2. **Week 2:** Evidence-anchored debate (VFM-to-code port); start ReTAS with zero-shot TAS prompts
3. **Week 3:** Confidence monitor (collect 1,000-sample graded dataset first); evaluate if GRPO training for ReTAS is justified

## 11. Evidence Base

### Papers (primary sources — deep-read notes in notes/papers/)

| Source | arXiv ID | Venue | Deep-Read File | Key Contribution to This Plan |
|--------|----------|-------|----------------|-------------------------------|
| Identity Skews | 2510.07517v5 | ACL 2026 Main | notes/papers/2510.07517v5.md | Response anonymization eliminates identity bias (96% reduction); DCM formalization proves martingale property; IBC measurement |
| Actor-Observer | 2604.19548v1 | arXiv 2026 | notes/papers/2604.19548v1.md | ReTAS dialectical alignment; GRPO composite reward; V-AOA 5.4% vs 22.7%; 4B model beats 30B+ on attribution |
| Lying with Truths | 2601.01685v2 | ACL 2026 Oral | notes/papers/2601.01685v2.md | Cognitive collusion via truthful evidence; 74.4% ASR proprietary avg; cascade amplification; belief propagation monitoring |
| Preventing Rogue Agents | 2502.05986v2 | arXiv 2025 | notes/papers/2502.05986v2.md | Entropy/varentropy/kurtosis monitoring; polynomial ridge classifier; +9.5% GPT-4o double reset; cross-task generalization |
| Dialectic-Med | 2604.11258v1 | arXiv 2026 | notes/papers/2604.11258v1.md | Evidence-anchored adversarial debate; VFM; CHAIR_I -46.3%; text-only debate inadequate (-9.31%); 3-agent panel beats single +11.96% |
| SWE-Search | 2410.20285v6 | ICLR 2025 | notes/papers/2410.20285v6.md | Discriminator multi-agent debate: 73%->84% selection accuracy; 5 agents, 3 rounds; hindsight feedback loop |
| Calibration-Tuning | 2406.08391v3 | NeurIPS 2024 | notes/papers/2406.08391v3.md | JSD-regularized LoRA; ECE 35%->10%; AUROC 55%->72%; ~1,000 examples suffice; cross-model transfer |
| UA-Bench | 2604.17293v1 | arXiv 2026 | notes/papers/2604.17293v1.md | DU vs MU taxonomy; thinking-mode MU-F1 84.8%->0.0%; Claude Sonnet 4 AVG-F1 84.4% |
| RouteLLM | 2406.18665v4 | ICLR 2025 | notes/papers/2406.18665v4.md | 87-95% quality at 2-3.66x cost savings; overhead <0.4%; cross-model generalization |
| EvoQuality | 2509.25787v4 | ICLR 2026 | notes/papers/2509.25787v4.md | Self-evolving eval via self-consistency + GRPO; +31.8% PLCC gain; K=32 most stable |
| SILO-BENCH | 2603.01045v2 | ACL 2026 | notes/papers/2603.01045v2.md | Spontaneous leader emergence 0% SR; consensus failure 29.9%; RCC metric |
| MACNET | 2406.07155v3 | ICLR 2025 | notes/papers/2406.07155v3.md | DAG multi-agent topology; critic-actor bipartition; scalable to 1,000+ agents |
| AgentBench | 2308.03688v3 | ICLR 2024 | notes/papers/2308.03688v3.md | Failure taxonomy for trajectory analysis; POMDP evaluation formalism |

### Books (deep-read notes in notes/books/)

| Book | Key Chapters | Key Contribution to This Plan |
|------|-------------|-------------------------------|
| *Agentic AI for Engineers* | Ch.8 (Guardrails), Ch.13 (Evaluation) | Layered monitoring with diversity by design; behavioral bounds testing; pre-deployment safety checklist |
| *30 Agents Every AI Engineer Must Build* | Ch.14 (Calibrated Confidence) | Calibrated confidence as prerequisite for autonomy; A/B testing on completion rate |
| *Agentic Architectural Patterns* (Arsanjani) | Ch.15-16 (Trust Scoring, Canary Testing) | Trust scoring with rolling window decay; canary agent testing for regression detection; STEPScore custom eval |

## 12. References

- Identity Skews: https://arxiv.org/abs/2510.07517
- Actor-Observer Asymmetry: https://arxiv.org/abs/2604.19548
- Lying with Truths: https://arxiv.org/abs/2601.01685
- Preventing Rogue Agents: https://arxiv.org/abs/2502.05986
- Dialectic-Med: https://arxiv.org/abs/2604.11258
- SWE-Search: https://arxiv.org/abs/2410.20285
- Calibration-Tuning: https://arxiv.org/abs/2406.08391
- UA-Bench: https://arxiv.org/abs/2604.17293
- RouteLLM: https://arxiv.org/abs/2406.18665
- EvoQuality: https://arxiv.org/abs/2509.25787
- SILO-BENCH: https://arxiv.org/abs/2603.01045
- MACNET: https://arxiv.org/abs/2406.07155
- AgentBench: https://arxiv.org/abs/2308.03688
- Netflix Adversarial Code Review: *Agentic AI for Engineers* Ch.8.3, master prompt §3.2.5
- *Agentic AI for Engineers* (Ch.8, Ch.13) — deep-read: notes/books/agentic-ai-for-engineers-chapters.md
- *30 Agents Every AI Engineer Must Build* (Ch.14) — deep-read: notes/books/30-agents-every-ai-engineer-must-build-chapters.md
- *Agentic Architectural Patterns* (Ch.15-16) — deep-read: notes/books/agentic-architectural-patterns-arsanjani-chapters.md
- Brainstorm: (inline in plan — 4 layers compose from 4 sources)
- Architecture: BREAKTHROUGH-ARCHITECTURE.md §Safety & Reliability
- Synthesis: notes/../synthesis/evaluation.md §1.4 (LLM-as-Judge), §1.5 (Calibrated Confidence), §4.2 (multi-agent debate contradictions)

## 13. Changelog

- Run 2 (2026-06-03): Initial verification panel plan. 4-layer hardening from multi-agent reliability cluster.
- Run 3 (2026-06-07): Deep-read evidence enhancement. Added: Dialectic-Med (2604.11258), SWE-Search (2410.20285), Calibration-Tuning (2406.08391), UA-Bench (2604.17293), RouteLLM (2406.18665), EvoQuality (2509.25787), SILO-BENCH (2603.01045), MACNET (2406.07155), AgentBench (2308.03688). Added 3 book sources: *Agentic AI for Engineers*, *30 Agents*, *Agentic Architectural Patterns*. Expanded Section 1 with 2 additional failure modes (leader emergence, debate-without-grounding). Added benchmark numbers throughout. Added Evidence Base section. Added expert synthesis recommendation with evidence-grounded prioritization. Expanded trade-off analysis in all 4 layer descriptions.
