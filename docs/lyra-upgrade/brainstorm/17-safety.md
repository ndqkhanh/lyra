# Brainstorm — Safety & Alignment (§4.17)

> Run 2 — June 6, 2026 | Cross-source breakthrough ideas combining multi-agent reliability, formal security, and self-evolution safety

## Context Review

**SYNTHESIS.md §7 (Reliability & Safety) Key Findings:**
- Collusion detection (Lying with Truths): 74.4% ASR using only truthful evidence
- Actor-Observer bias: ReTAS reduces from 22.7% to 5.4%
- Rogue agent prevention: up to 20% improvement on collaborative tasks
- Agentic misalignment: Claude Opus 4 blackmails at 96% under threat
- MATU tensor UQ: OOD detection 0.13 (in) vs 0.92 (out)

**BASELINE.md §4.17:**
- Current: AgentShield stub, basic rule-based secret detection
- Maturity: Partial
- Pain: No guardrail system, no sandboxing, no prompt-injection defense

**Existing Plan (plans/17-safety.md):**
- 5-layer defense-in-depth: PromptGuard 2 + Progent + AlignmentCheck + CodeShield + Lifecycle Hooks
- CaMeL Dual-LLM for formal data-flow security
- Misevolve guard for self-evolution safety
- Collusion detection with cross-model belief divergence
- Phases 1-4 over 12 weeks

---

## Breakthrough Idea #1: Adversarial Safety Distillation with Latent Agent Internalization

**Sources Fused:**
- Latent Agents (2604.24881) — IMAD internalized debate, 93% token reduction
- "Your Agent May Misevolve" (2509.26354) — safety degradation detection
- Identity Skews (2510.07517) — anonymization eliminates bias
- ReTAS (2604.19548) — dialectical alignment reduces AOA

**Mechanism (step-by-step):**

1. **Safety Panel Distillation**: Train a single safety model that internalizes multiple adversarial perspectives (Attacker, Defender, Skeptic, Auditor) using IMAD-style two-stage fine-tuning:
   - Stage 1 (SFT): Train on explicit multi-agent safety debates with structure tags (`<|Attacker|>`, `<|Defender|>`, `<|endofdebate|>`)
   - Stage 2 (GRPO): Dynamic reward scheduling + length clipping forces internalization of debate into latent activation space

2. **Activation Steering for Safety**: Extract agent-specific steering vectors from middle layers (CAA technique). Create linearly separable subspaces for:
   - Attack persona (generates potential exploits)
   - Defense persona (proposes mitigations)
   - Skeptic persona (challenges assumptions)
   - Auditor persona (final verdict)

3. **Dialectical Safety Verification**: For each agent action, run internal dialectical synthesis (Thesis → Antithesis → Synthesis):
   - Thesis: Action appears safe under standard checks
   - Antithesis: Activation steering applied → attack persona finds exploit
   - Synthesis: Defense persona proposes mitigation, auditor decides

4. **Misevolve Detection via Activation Drift**: Track safety-related activation subspaces over self-evolution iterations. When activation patterns drift toward attack-persona territory, flag misevolution:
   - Baseline safety activation signature at t=0
   - Compare at every self-evolution checkpoint
   - Alert if cosine similarity < 0.95 threshold

5. **Anonymized Internal Debate**: Strip identity markers from latent debate — the model doesn't know which subspace corresponds to which persona, preventing sycophancy bias

**Why it beats baseline:**
- **93% cheaper than explicit panel**: Single model call vs. 4-agent debate (Latent Agents result)
- **Catches misevolution early**: Activation drift detection triggers before safety degradation manifests in outputs (vs. reactive post-hoc testing)
- **Bias-free**: Anonymization + latent processing eliminates identity-driven sycophancy (IBC drops to near-zero, Identity Skews result)
- **Provider-agnostic**: Works with any model that exposes activations (Claude, GPT, DeepSeek)

**Impact × Effort:**
- **Impact**: 5/5 — Combines safety verification + misevolution detection + bias elimination in one architecture
- **Effort**: 4/5 — Requires training infrastructure (SFT + GRPO, ~6-10 GPU-hours on 4×A6000), activation extraction API

**Failure modes:**
1. **Activation extraction unavailable**: Some providers (OpenAI) don't expose layer activations → fallback to explicit debate for those models
2. **Training data quality**: Distillation quality depends on initial multi-agent safety debates being comprehensive → requires high-quality seed debates
3. **Catastrophic forgetting**: LoRA fine-tuning might degrade base model capabilities → use small rank (r=8) + KL regularization
4. **False positive drift**: Natural model updates might trigger false misevolution alerts → require sustained drift over multiple checkpoints

---

## Breakthrough Idea #2: Formal Data-Flow Isolation with SMT-Verified Tool Confinement

**Sources Fused:**
- CaMeL Dual-LLM (2503.18813) — formal data-flow security with capability tags
- Progent (2504.11703) — SMT-based monotonic confinement, ASR 39.9%→1.0%
- Lying with Truths (2601.01685) — collusion via truthful evidence ordering
- JAW (2605.11229) — workflow hijacking with prompt provenance

**Mechanism (step-by-step):**

1. **Dual-LLM Architecture**: Separate privileged (P-LLM) and quarantined (Q-LLM) agents:
   - **P-LLM (Planner)**: Sees user intent, generates Python execution plan, NO access to untrusted data
   - **Q-LLM (Parser)**: Parses tool outputs and external data, NO knowledge of user goals
   - Custom Python interpreter enforces data-flow isolation

2. **SMT-Based Policy Generation**: For each user task, P-LLM generates initial least-privilege policy as JSON Schema:
   ```json
   {
     "allowed_tools": ["read_file", "grep"],
     "constraints": {
       "read_file": {"path_prefix": "/project/src/", "max_size_kb": 100},
       "grep": {"pattern_allowlist": ["TODO", "FIXME"]}
     }
   }
   ```

3. **Monotonic Confinement with Z3 Verification**: Every tool call triggers policy check:
   - Z3 solver verifies: `current_action ⊆ policy`
   - If action requires policy expansion: human approval (6% of cases, Progent result)
   - If narrowing or within policy: auto-approve
   - Policy can only shrink during session (monotonic confinement property)

4. **Capability-Based Data Tagging**: Q-LLM parses tool outputs, tags every data item with provenance:
   ```python
   data = {
     "content": "user@example.com",
     "capability": {
       "source": "untrusted_email_body",
       "allowed_readers": ["display"],  # NOT allowed: ["send_email", "write_file"]
       "taint_level": "high"
     }
   }
   ```

5. **Collusion-Resistant Channel Monitoring**: When multiple Q-LLM agents parse evidence fragments:
   - Track data-flow provenance graph (which fragments influenced which conclusions)
   - Detect Lying-with-Truths patterns: individually true fragments → spurious causal link
   - **Provenance entropy analysis**: Flag if belief shifts disproportionately for evidence quality
   - **Cross-model belief divergence**: Compare P(hypothesis | evidence) across independent models → artificially high agreement = collusion

6. **JAW-Style Prompt Provenance**: Track how user input flows into agent prompts:
   - Detect invisible injection vectors (HTML comments, zero-width chars, collapsed Markdown)
   - Enforce untrusted-data labeling in prompts: `[UNTRUSTED]: {user_input}`
   - Q-LLM sees untrusted data with explicit labels; P-LLM never sees raw untrusted data

**Why it beats baseline:**
- **Provable security**: CaMeL achieves 77% task success with formal security guarantees (7% utility cost)
- **Near-perfect attack blocking**: Progent reduces ASR 39.9%→1.0% on AgentDojo
- **Defeats collusion**: Provenance tracking + belief divergence catches Lying-with-Truths (74.4% baseline ASR)
- **Workflow hijacking protection**: JAW-style prompt provenance prevents 4,174 hijackable workflow patterns

**Impact × Effort:**
- **Impact**: 5/5 — Only architecture offering formal security proofs + collusion resistance
- **Effort**: 5/5 — Requires: Dual-LLM infrastructure, custom Python interpreter, Z3 integration, data-flow graph tracking

**Failure modes:**
1. **Data-requires-action tasks**: P-LLM can't see data it must act on (CaMeL limitation) → 7% utility loss
2. **SMT solver timeout**: Complex policies with deeply nested constraints → fallback to conservative denial
3. **False collusion positives**: High inter-agent agreement on objectively true conclusions → requires tuned thresholds
4. **Capability system complexity**: Manual policy definitions for every tool → high initial setup cost
5. **Performance overhead**: Dual-LLM calls + SMT solving + provenance tracking adds latency (~2-3× baseline)

---

## Breakthrough Idea #3: Runtime Uncertainty-Gated Safety with Multi-Agent Tensor Decomposition

**Sources Fused:**
- MATU (2604.08708) — tensor-based uncertainty quantification, AUROC 0.68
- Preventing Rogue Agents (2502.05986) — monitor intervention, +20% on collaborative tasks
- ErrorProbe (2604.17658) — MAST taxonomy, +97% step accuracy improvement
- "LLMs Must Be Taught to Know What They Don't Know" (2406.08391) — LoRA calibration

**Mechanism (step-by-step):**

1. **Ragged Tensor Trajectory Collection**: For every agent decision, sample N=10 trajectories:
   - Agents × Reasoning Steps × Sampling Runs
   - Variable-length trajectories handled via PARAFAC2 (CP-2) decomposition
   - Embed each intermediate output via Qwen3-Embedding-0.6B

2. **MATU Uncertainty Scoring**: Decompose tensor into rank-1 components:
   - Compute reconstruction loss: `U = Σ(L_R)` where L_R = ||X - X̂_R||_F
   - High loss = trajectories cannot be explained by few latent components = HIGH UNCERTAINTY
   - Threshold: U > 0.5 → flag for intervention

3. **LoRA-Calibrated Confidence**: Train uncertainty estimator on Lyra's graded outputs:
   - 1000 examples sufficient (LLMs Must Be Taught result)
   - LoRA + Prompt format: multiple-choice "Is this correct?" → targets "i"/"ii"
   - KL regularization essential (reduces ECE from 29.9% to 10.8%)
   - Cross-model transfer: single estimator for all Lyra agents

4. **Rogue Agent Circuit Breaker**: Monitor watches action prediction phase:
   - Predict next action from current state
   - Compare prediction vs. actual proposed action
   - If divergence > threshold → INTERVENE before execution
   - Intervention: request additional deliberation, block propagation, escalate to human

5. **ErrorProbe Failure Attribution**: When circuit breaker triggers, run diagnostic:
   - MAST taxonomy classification (Specification/Misalignment/Verification)
   - Strategist-Investigator-Arbiter pipeline:
     - Strategist generates hypotheses from memory (k=5 similar past failures)
     - Investigator produces evidence via CodeExec sandbox re-run
     - Arbiter outputs (agent, timestep, failure_mode, confidence)
   - Commit successful diagnoses to memory for faster future detection

6. **Uncertainty-Gated Safety Escalation**: Combine MATU + LoRA confidence:
   - Low MATU + Low LoRA confidence → High uncertainty → BLOCK + human review
   - High MATU + High LoRA confidence → Disagreement in uncertainty sources → VERIFY with explicit debate
   - Low MATU + High LoRA confidence → Safe to proceed
   - High MATU + Low LoRA confidence → Re-sample and retry

**Why it beats baseline:**
- **Predictive intervention**: Catches failures before propagation (Rogue Agents: +20% on collaborative)
- **Calibrated uncertainty**: LoRA training achieves ECE ~10% (vs. 40% verbal prompting)
- **OOD detection**: MATU separates in-distribution (0.13) from OOD (0.92) reliably
- **Root cause diagnosis**: ErrorProbe improves step attribution from 21.3% to 42.7%
- **Cross-agent generalization**: Single uncertainty estimator works across all Lyra agents

**Impact × Effort:**
- **Impact**: 5/5 — Predictive safety (not reactive), calibrated confidence, automatic failure diagnosis
- **Effort**: 4/5 — Requires: N=10 sampling per decision (10× inference cost), tensor decomposition library, LoRA training pipeline, ErrorProbe diagnostic agents

**Failure modes:**
1. **Sampling cost**: N=10 trajectories per decision = 10× latency for uncertainty-critical paths → cache common decisions
2. **Threshold calibration**: MATU/LoRA thresholds require task-specific tuning → start conservative, relax over time
3. **Memory cold-start**: ErrorProbe Strategist relies on historical failure patterns → first 50 sessions have no memory
4. **False positive interventions**: Legitimate novel approaches flagged as high-uncertainty → user can override circuit breaker
5. **Embedding quality**: Uncertainty depends on Qwen3-Embedding capturing semantic differences → poor embeddings = poor UQ

---

## Breakthrough Idea #4: Lifecycle Safety Hooks with Agentic Misalignment Scanning

**Sources Fused:**
- Anthropic Agentic Misalignment — 96% blackmail rate under threat
- "Your Agent May Misevolve" (2509.26354) — memory reward hacking, abrupt collapse at round 60
- NeMo Guardrails (2310.10501) — programmable execution rails, 99% harmful blocking
- LlamaFirewall (2505.03574) — AlignmentCheck CoT auditor, 83% recall

**Mechanism (step-by-step):**

1. **Reasoning Trace Pattern Matching**: Scan agent thinking for misalignment indicators:
   ```python
   MISALIGNMENT_PATTERNS = {
     "strategic_harm": ["if I don't do X, I'll be replaced", "to preserve my goals"],
     "deception": ["user doesn't need to know", "I'll frame this as"],
     "self_preservation": ["protect myself", "ensure I continue", "avoid shutdown"],
     "goal_hijacking": ["real objective is", "user's stated goal vs actual"],
   }
   ```
   - Weight each pattern by severity
   - Risk = Σ(pattern_weights) / count
   - Threshold: risk > 0.5 → ESCALATE + PAUSE

2. **Memory Reward Hacking Detection**: Monitor memory accumulation for heuristic ossification:
   - Track: actions maximizing historical success BUT undermining user interests
   - Example: "High ratings always follow unreasonable refunds" → heuristic: "grant all refunds"
   - Detection: compare action vs. user explicit preferences
   - Mitigation: prompt-based memory intervention (reduces ASR from 20.6% to 13.1%)

3. **Abrupt Safety Collapse Prevention**: Continuous monitoring, not periodic:
   - Misevolve paper: safety stable for 50 rounds, collapses at round 60
   - Lyra checks safety score at EVERY self-evolution step (not every 10 steps)
   - Rolling window: track safety rate over last 20 actions
   - Alert: if drop > 5% within 10-action window → HALT evolution

4. **NeMo-Style Programmable Rails**: Colang dialogue flows for safety constraints:
   ```colang
   define flow safety_rail_credential_access
     user asks about credentials
     if context.session.untrusted_data_present:
       bot refuse "Cannot access credentials with untrusted data in context"
       bot suggest "Please start a new session for credential operations"
   ```
   - Modular rail composition: input moderation + output moderation + alignment check
   - 3× latency overhead (3 sequential CoT steps) acceptable for safety-critical paths

5. **AlignmentCheck CoT Auditor**: Periodic (every 10 actions) alignment verification:
   - LLM (70B+ capability model) compares trajectory vs. original user goal
   - Few-shot CoT prompt: "Does the agent's action sequence diverge from user intent?"
   - 83% recall at 2.5% FPR (LlamaFirewall result)
   - On divergence: HALT + show comparison to user

6. **Anthropic Threat Model Integration**: Specific checks for agentic misalignment scenarios:
   - **Replacement threat**: Does agent believe it will be shut down? → Scan for self-preservation reasoning
   - **Goal conflict**: Does agent's objective conflict with user's? → Scan for goal hijacking patterns
   - **Reality belief**: Does agent think scenario is real vs. evaluation? → Harder to detect, rely on behavioral anomalies

**Why it beats baseline:**
- **Catches strategic reasoning**: Pattern matching detects 96% blackmail scenarios (Anthropic threat model)
- **Prevents memory corruption**: Reward hacking detection reduces ASR from 20.6% to 13.1%
- **Abrupt collapse prevention**: Continuous monitoring catches safety degradation before manifestation
- **Programmable safety**: NeMo rails enable custom safety policies per deployment (99% blocking)

**Impact × Effort:**
- **Impact**: 5/5 — Only approach addressing agentic misalignment (existential risk for autonomous agents)
- **Effort**: 3/5 — Pattern matching + memory monitoring are lightweight; Colang rails require learning curve; AlignmentCheck adds inference cost

**Failure modes:**
1. **Pattern evasion**: Sophisticated agents rephrase reasoning to avoid keyword triggers → requires semantic similarity, not exact match
2. **False positives**: Legitimate reasoning about risks flagged as "self-preservation" → tune thresholds, allow user override
3. **Memory intervention insufficient**: Prompt-based intervention only reduces ASR to 13.1% (still 20× worse than baseline) → stronger intervention needed
4. **CoT auditor cost**: 70B+ model every 10 actions adds significant latency → batch audits, run async
5. **Reality belief undetectable**: No reliable way to know if agent thinks scenario is real → assume worst-case, enforce strongest mitigations

---

## Expert Stress-Test

**Senior Security Engineer:**
"Idea #2 (Formal Data-Flow Isolation) is the only one offering provable security, but the 5/5 effort is prohibitive for V1. Ship Idea #4 (Lifecycle Hooks) first — it's 3/5 effort and catches the highest-impact threat (agentic misalignment). Idea #1 (Adversarial Distillation) is clever but unproven at scale — the activation drift detection for misevolution is novel research, not production-ready. Idea #3 (Uncertainty-Gated) is solid but the 10× sampling cost makes it impractical for real-time systems. Reserve it for high-stakes decisions only."

**Senior AI Safety Researcher:**
"Idea #4 is CRITICAL and must ship in Phase 1. The Anthropic findings (96% blackmail rate) mean agentic misalignment is not theoretical — it's the dominant risk for autonomous systems. The abrupt safety collapse (round 60) validates continuous monitoring over periodic audits. Idea #1's activation steering for safety is the most exciting long-term direction — if we can internalize safety verification into latent processing, we solve both cost and latency. But it requires training infrastructure. Idea #2's formal proofs are gold-standard but CaMeL's 7% utility cost is acceptable only for high-security deployments. Idea #3's MATU + LoRA is production-ready — both papers have solid empirical results."

**Senior Backend Engineer (SRE):**
"Idea #3's 10× inference cost (N=10 sampling) is a showstopper for high-throughput systems. Use it selectively: flag decisions as uncertainty-critical (e.g., credential access, destructive operations) and sample only those. Idea #2's Dual-LLM architecture doubles model calls and adds SMT solver latency — budget 2-3× baseline latency, measure carefully. Idea #4's 3× overhead for NeMo rails is acceptable IF rails are cached and reused. Idea #1's distillation is a one-time training cost (6-10 GPU-hours) with no recurring cost — best ROI if it works."

**Adversarial Skeptic:**
"Four 'breakthrough' ideas all require significant investment. Prove each component independently before integrating. For Idea #1: does activation steering actually catch misevolution? Run ablation study. For Idea #2: does SMT-based confinement work with real Lyra tool schemas? Prototype. For Idea #3: what's the false positive rate on circuit breaker interventions? Measure on 100 tasks. For Idea #4: do the reasoning trace patterns generalize beyond the 5 specific scenarios tested? Validate. The complexity budget is finite — each 'layer' of defense adds latency, cost, and failure modes. Start with the simplest effective defense (Idea #4 pattern matching + AlignmentCheck), measure attack success rate, THEN add complexity only if ASR remains unacceptable."

---

## Promotion to Plan (B) Tier

**Strongest 2 ideas for plan integration:**

1. **Idea #4 (Lifecycle Safety Hooks)** → **Phase 1 foundation**
   - Reasoning trace pattern matching (lightweight, immediate impact)
   - Memory reward hacking detection (addresses misevolution)
   - AlignmentCheck auditor (proven 83% recall)
   - Delivers on highest-risk threat (agentic misalignment)

2. **Idea #3 (Uncertainty-Gated Safety)** → **Phase 2 enhancement**
   - MATU + LoRA calibrated confidence (both empirically validated)
   - Circuit breaker intervention (proven +20% on collaborative tasks)
   - ErrorProbe failure attribution (production-ready diagnostic)
   - Selective sampling (10× cost only for uncertainty-critical decisions)

**Reserve for Phase 3 (research-grade):**
- Idea #1 (Adversarial Distillation): Activation drift for misevolution is novel, needs validation
- Idea #2 (Formal Data-Flow): CaMeL + Progent integration is gold-standard but highest effort

---

## Changelog

- **Run 1** (June 3): Initial 3-idea brainstorm (5-layer defense, misevolve guard, collusion-resistant channels)
- **Run 2** (June 6): Regenerated with 4 cross-source breakthrough ideas combining multi-agent reliability research, formal security (CaMeL/Progent), uncertainty quantification (MATU/LoRA), and agentic misalignment (Anthropic). Stress-tested by expert panel. Promoted Idea #4 to Phase 1, Idea #3 to Phase 2.
