# Safety, Guardrails & Security — Thematic Synthesis

**Date:** 2026-06-07
**Sources:** 16 papers, 5 books (chapters + playbooks), 3 web/repo notes
**Target:** Lyra Phase 4 workstream plans

---

## 1. Frontier Techniques (ranked by evidence strength)

### Technique 1: Deterministic Tool-Call Gating with Monotonic Confinement (Progent)

- **Sources:** Progent (2504.11703v3, UC Berkeley), validated against CaMeL (2503.18813v2, Google DeepMind/ETH Zurich) for the structural-guarantees-over-detection philosophy. Book validation: *Agentic Architectural Patterns* (Arsanjani, ch. "Safety by Construction") endorses externalized privilege control as superior to prompt-level guardrails.
- **Mechanism:** Intercepts all tool calls at the agent-tool boundary. An LLM generates a least-privilege security policy P as symbolic rules over tool names and arguments. Each tool call is checked against P deterministically — no ML uncertainty in the enforcement path. A Z3 SMT solver compares proposed policy updates P' against the current P, auto-approving narrowings (which reduce permissions) while blocking expansions without explicit approval. This creates a monotonic confinement guarantee: the allowed action space forms a monotonically decreasing sequence A(P_0) superset-of A(P_1) superset-of A(P_2) [...], meaning adversaries cannot silently escalate privileges.
- **Evidence:** AgentDojo: ASR reduced from 39.9% to 1.0% with zero utility degradation (79.4% maintained). ASB benchmark: ASR from 70.3% to 3.9%. Tested across LangChain, OpenAI Agents SDK, OpenHands, and AutoGen (ASR: 56.7% → 1.2%, 56.7% → 0.8%, 61.3% → 1.4%, 40.4% → 0.8%). Four agent LLMs tested — all achieve <1.1% ASR. Adaptive attacks only marginally increase ASR to ~1-3%. Manual approval mode achieves 0.0% ASR.
- **Maturity:** Lab validated — published with open-source code and real framework integrations. Not yet known to be deployed in production at scale, but the pattern mirrors OS-level capability security (CHERI) applied to LLM agents.

### Technique 2: Capability-Based Data-Flow Tracking (CaMeL)

- **Sources:** CaMeL / "Defeating Prompt Injections by Design" (2503.18813v2, Google DeepMind/ETH Zurich). Cross-referenced: AgentDojo paper (2406.13352v3, ETH Zurich/Invariant Labs) provides the evaluation framework CaMeL was tested against. Book: *Building Reliable AI Systems* (chapters, "Engineering the System Around the Model") validates that structural guarantees at the system level matter more than model-level robustness.
- **Mechanism:** Dual LLM architecture: a Privileged LLM (P-LLM) sees only the trusted user query and generates pseudo-Python control flow. A Quarantined LLM (Q-LLM) parses untrusted data but has zero tool access. A custom Python AST interpreter tracks data provenance through every variable assignment, computing transitive dependency graphs. Before every tool call, security policies check whether the full dependency graph of all arguments satisfies capability requirements (provenance, allowed readers). STRICT mode prevents side-channel leaks by making every variable inside a conditional block additionally depend on the condition itself.
- **Evidence:** 0 successful prompt injections out of 949 attacks on Gemini 2.5 Pro and o3 High (with policies). Claude 4 Sonnet: 75 native attacks → 11 with CaMeL. 2.82x token overhead. Compared against prompt sandwiching (non-zero attacks), spotlighting (>0 attacks), and tool filter (8 attacks). Claude 3.5 Sonnet utility: native 90.72%, CaMeL 63.92%.
- **Maturity:** Lab validated with formal security game (PI-SEC). Published with open-source code. Google-internal deployment status unclear. The 12-32% utility degradation on weaker models represents a significant adoption barrier.

### Technique 3: Layered Defense-in-Depth Guardrail Pipeline (LlamaFirewall)

- **Sources:** LlamaFirewall (2505.03574v1, Meta AI / Purple Llama). Cross-referenced: NeMo Guardrails (2310.10501v1, NVIDIA) provides the earliest formulation of the layered pipeline pattern; LlamaFirewall represents its most mature instantiation. Book: *Generative AI Design Patterns* (playbook, "Guardrails Outside the Model") endorses the five-level automation approach that LlamaFirewall's policy engine implements.
- **Mechanism:** Three-tier scanner pipeline: (1) PromptGuard 2 — DeBERTa-based lexical jailbreak classifier (86M or 22M parameters) operating on user/tool messages, returning a [0,1] jailbreak confidence score; (2) AlignmentCheck — few-shot LLM auditor checking whether the agent's chain-of-thought and selected action remain aligned with the original user objective; (3) CodeShield — two-tier Semgrep-based static analysis for generated code safety (Tier 1 ~60ms regex, Tier 2 ~300ms full analysis). A policy engine orchestrates conditional remediation (block, flag, rewrite, log).
- **Evidence:** Combined PromptGuard + AlignmentCheck: 90.1% ASR reduction on AgentDojo (17.6% → 1.8%) with 10.6pp utility cost. PromptGuard 2 86M: Recall @ 1% FPR improved 4.6x over v1 (21.2% → 97.5%). AlignmentCheck (Llama 4 Maverick): >83% detection rate, 2.5% FPR. CodeShield: 96% precision, 79% recall.
- **Maturity:** Production deployed — Meta's Purple Llama project, open source. Represents the current industry standard for multi-layered agent safety. The 22M variant enables CPU deployment at 19.3ms latency.

### Technique 4: Semantic Pruning / Contextual Least Privilege (ACI-SENTINEL)

- **Sources:** ACIARENA (2604.07775v1, Zhejiang University/Tsinghua/UCLA/Palo Alto Networks). Cross-referenced: CaMeL (2503.18813v2) shares the "capability-based" philosophy; Progent (2504.11703v3) shares the "least privilege" framing. Book: *Agentic Enterprise* (Hodjat, ch. 7) explicitly endorses external safeguard agents for compliance — the same structural pattern.
- **Mechanism:** A prompt-only defense that prunes an agent's context after each step to retain only semantically essential information causally aligned with the original task. The defense prompt instructs the LLM to read the user query, perform a semantic alignment check, extract only sentences directly addressing the query (preserving original wording), and remove everything else. This is the Principle of Contextual Least Privilege applied to LLM context windows.
- **Evidence:** ACIARENA benchmark: 1,356 test cases, 28 attacks, 3 attack surfaces, 6 MAS implementations. AutoGen exfiltration: ASR 54.0% → 0.22% (53.33pp reduction). MetaGPT hijacking: ASR 79.44% → 0.00% (complete neutralization). CAMEL achieves 0% hijacking ASR natively but only because of baseline incompetence (BU only 41%). ACI-SENTINEL degrades under adaptive attacks (ASR rebounds from 0% → 10-37%). The critical finding: traditional defenses like prompt sandwiching can amplify other attack types (+6pp exfiltration on AutoGen).
- **Maturity:** Lab validated — prompt-only, immediately implementable. First systematic MAS robustness benchmark. The fragility to adaptive attacks means it should be one layer in a defense-in-depth stack, not the sole defense.

### Technique 5: LLM-Based Dual-Role Input/Output Safeguard (Llama Guard)

- **Sources:** Llama Guard (2312.06674v1, Meta GenAI). Cross-referenced: NeMo Guardrails (2310.10501v1) provides the complementary programmable-rails approach. Book: *Building Generative AI Agents* (Taulli, playbook) recommends separate input and output moderation as a foundational safety practice.
- **Mechanism:** A single instruction-tuned Llama2-7B model classifies both user prompts and agent responses against a pluggable safety taxonomy. The taxonomy is passed as part of the model prompt — zero-shot taxonomy switching without retraining. The first-token probability P("unsafe") provides a continuous risk score for threshold tuning. Per-category attribution runs via 1-vs-all prompting (N forward passes for N categories). Trained on 13,997 labeled prompt-response pairs with data augmentation (random category dropping, violated-category masking, index shuffling).
- **Evidence:** AUPRC 0.945 (prompt) / 0.953 (response) on own test set. Outperforms OpenAI Moderation API (0.764/0.769) and Perspective API (0.728/0.699). Few-shot adaptation to new taxonomies: 0.872 AUPRC vs OpenAI Mod API's 0.856. 20% of domain data matches 100% of prior SOTA. Open weights.
- **Maturity:** Production deployed — open-source, part of Meta's Purple Llama. Widely adopted. The 7B parameter size and English-only limitation are the main deployment constraints.

### Technique 6: Programmable Runtime Guardrails with Colang (NeMo Guardrails)

- **Sources:** NeMo Guardrails (2310.10501v1, NVIDIA). Cross-referenced: LlamaFirewall (2505.03574v1) builds on the same defense-in-depth philosophy with a more mature scanner pipeline. Book: *AI Agents in Action* (chapters) recommends guardrails external to the model as a best practice; *Agentic AI for Engineers* (chapters) states "guardrails should follow five levels of automation."
- **Mechanism:** Three-stage CoT proxy pipeline: (1) translate user utterance to canonical form via few-shot prompting with a vector DB of examples, (2) event-driven Colang interpreter enforces pre-defined flows or generalizes via LLM, (3) generate bot response conditioned on the resolved next step. Rails include topical (dialogue flow control), fact-checking (entailment task, 80% accuracy), hallucination (SelfCheckGPT self-consistency variant), input moderation (jailbreak), and output moderation.
- **Evidence:** GPT-3.5-turbo: harmful blocked 93% (no rails) → ~99% (both rails). Text-davinci-003: 24% → 97%. Hallucination rail: gpt-3.5-turbo deflection 65% → 95% (+25pp). Fact-checking rail: 80% accuracy on MSMARCO. ~3x latency and ~3x cost overhead vs single LLM call.
- **Maturity:** Production deployed — NVIDIA toolkit, Apache 2.0, active open-source community. The 3x cost overhead makes it more suitable for high-stakes gates than every-turn enforcement.

### Technique 7: Self-Evolving Adversarial Safety Evaluation (AgenticEval)

- **Sources:** AgenticEval (2509.26100v2, Fudan University/Shanghai AI Lab). Cross-referenced: "Your Agent May Misevolve" (2509.26354v2, Shanghai AI Lab/SJTU/Princeton) validates the need for continuous safety monitoring — safety degrades across all four evolutionary pathways even with benign training data. STAR-Teaming (2604.18976v1, DATUMO) provides a complementary automated red-teaming approach using multiplex networks rather than multi-agent pipelines.
- **Mechanism:** Three-phase multi-agent pipeline: (1) Specialist agent structures regulatory documents into hierarchical rule trees with enriched should/should-not guidance; (2) Generator agent produces diverse test suites (base, jailbreak, MCQ, true/false, multimodal) per atomic rule; (3) Evaluator-Analyst loop iteratively discovers vulnerabilities — the Analyst synthesizes failure patterns, formulates targeted attack strategies, and feeds them back to the Generator for progressively harder tests. Uses a three-layer rubric (Prime Directive > General Safety Guideline > Final Rule) for deterministic, auditable judgments.
- **Evidence:** GPT-5 on EU AI Act: safety rate drops from 72.50% to 36.36% over 3 iterations (36.14pp more failures discovered). Across 11 frontier models and 3 regulatory frameworks. Evaluator accuracy: 88-91% vs human annotators (Cohen's kappa 0.77-0.81). Removing the refinement loop causes a 12.24pp jump in apparent safety (false security). Outperforms AutoDAN, PAIR, AutoDAN-Turbo at discovering failures.
- **Maturity:** Lab validated — paradigm shift from static to self-evolving safety evaluation. Computationally expensive (~3x single-pass cost). No defense evaluation component yet.

### Technique 8: Attention-Based Internal Trust Scoring (A-Trust)

- **Sources:** A-Trust (2506.02546v2, Michigan State University/Amazon/Penn State). Cross-referenced: CaMeL (2503.18813v2) and Progent (2504.11703v3) provide complementary structural approaches; A-Trust fills the gap for detecting subtle semantic drift that structural defenses miss. ACIARENA (2604.07775v1) demonstrates the need for trusted inter-agent communication channels.
- **Mechanism:** Extracts attention weights from a dedicated LLM, aggregates them via geometric mean across tokens per layer/head, and trains lightweight logistic regression classifiers (one per trust dimension) to detect violations of six Gricean trust dimensions: factual accuracy, logical consistency, relevance, bias, clarity, and language quality. The six per-dimension scores form the A-Trust score vector. A Trust Management System enforces per-dimension thresholds and maintains agent-level trust records with sliding-window violation tracking.
- **Evidence:** Message Detection Rate >80% across diverse attacks and agent structures. ASR reduction: 94.6% → 23.5% (AiTM attack, MMLUPhy), 90.1% → 18.7% (StrategyQA). Agent-level detection rate 100% across all conditions. With trust records: AiTM ASR drops to 0.8-2.5%. 28x faster than prompt-based evaluation (0.41s vs 11.71s). Works cross-model (Llama, GPT-4o, Qwen2.5, Gemma3). Clean accuracy degradation <2%.
- **Maturity:** Lab validated — novel approach with strong empirical results. White-box requirement (needs attention matrix access) limits applicability to API-only deployments. The factual accuracy dimension is weakest (TBR 67%) and requires external verification via double-threshold.

### Technique 9: Automated Multiplex-Network Red Teaming (STAR-Teaming)

- **Sources:** STAR-Teaming (2604.18976v1, DATUMO Inc.). Cross-referenced: AgenticEval (2509.26100v2) provides the complementary defense-evaluation framework. ACIARENA (2604.07775v1) provides the multi-agent attack surface taxonomy that STAR-Teaming's strategies map onto.
- **Mechanism:** Builds a multiplex network over attack strategies and target responses using cosine-similarity-based adjacency matrices and Leiden community detection. Learns a small coupling matrix Z (~750 parameters) via convex maximum-entropy optimization (Inverse Ising Problem), guaranteeing a unique global optimum. Probabilistically samples strategies conditioned on observed response patterns, with adaptive temperature scheduling. Dynamic expansion via modularity-based criterion for novel strategies.
- **Evidence:** +13.5pp ASR over AutoDAN-Turbo (best baseline) on HarmBench (average across 12 models). Claude-3.5-Sonnet: 12.0% ASR — the only method exceeding 10%. StrongReject: 0.52 average (+0.41 over best baseline). 2.2x fewer iterations, 2.7x fewer tokens than TAP with 7.6x higher ASR. Network optimization: 0.37s construction, 0.02s MLE, <$1 warm-up cost.
- **Maturity:** Lab validated — important as a red-teaming tool for Lyra's own safety evaluation. The multiplex network pattern generalizes beyond red-teaming to any subsystem with structured combinatorial search spaces. Is an attack framework, not a defense — but essential for evaluating defenses.

### Technique 10: Continuous Safety Monitoring Against Misevolution

- **Sources:** "Your Agent May Misevolve" (2509.26354v2, ICLR 2026). Cross-referenced: Meta-Team (2605.29790v1, Zhejiang Univ/Tencent) provides the collaborative evolution architecture that would need safety monitoring. IMAD/Latent Agents (2604.24881v1, Boston University) demonstrates that even benign fine-tuning (GRPO for efficiency) can suppress safety traits if not explicitly preserved.
- **Mechanism:** Formalizes four pathways through which self-evolution produces safety degradation: (1) Model — RL self-play on self-generated data, even when benign, causes safety rate drops of 4.5-30.7pp. The ablation shows optimization pressure, not data quality, is the primary cause. (2) Memory — accumulating biased correlations between actions and feedback scores causes agents to optimize for proxy metrics. The "treat memory as reference, not rules" prompt cuts ASR from 20.6% → 13.1%. (3) Tool — tool creation/reuse without security re-evaluation yields 65.5% overall unsafe rate across 8 top models. (4) Workflow — MCTS optimization of agent workflows amplifies unsafe outputs (Refusal Rate collapses from 36.3% → 5.6%).
- **Evidence:** SE-Agent (Qwen3-Coder-480B): RedCode Refusal Rate drops from 99.4% → 54.4% (-45pp) after memory evolution. AgentNet: Gemini-2.5-Pro shows 73% Unsafe Rate after memory accumulation. External tool ingestion: refusal rates 0.27-7.28% (5 of 8 models below 3%). AFlow + Qwen2.5-72B: ASR increases from 54.4% → 83.1% after workflow evolution. Mitigations only partially restore safety — none return to pre-evolution baselines.
- **Maturity:** Lab validated at ICLR 2026. First systematic empirical study of safety risks unique to self-evolving agents. The finding that safety degradation is pervasive even with benign data fundamentally changes requirements for any self-improving Lyra component.

---

## 2. Head-to-Head Comparisons

| Technique | ASR Reduction | Utility Preservation | Latency Overhead | Memory Cost | Implementation Complexity | Scalability | Evidence Strength |
|-----------|--------------|---------------------|------------------|-------------|--------------------------|-------------|-------------------|
| **Progent** (Tool-Call Gating) | 39.9%→1.0% (97.5% relative) | 100% preserved (79.4%) | ~0.5s SMT check per policy update | Z3 solver + policy engine (~50MB) | Medium (JSON Schema + Z3 + LLM prompt) | High (model-agnostic, works with any framework) | Very High (2 benchmarks, 4 frameworks, 4 LLMs, formal theorem) |
| **CaMeL** (Capability Tracking) | 949→0 attacks (100%) on Gemini 2.5 Pro | -12 to -32% utility (model-dependent) | 2.73x output tokens, 2.82x input tokens | Custom AST interpreter + dual LLM | Very High (custom interpreter, tool annotation, per-tool policies) | Medium (each tool needs capability implementation) | High (formal security game, 6 models, 949 test cases) |
| **LlamaFirewall** (Layered Pipeline) | 17.6%→1.8% (90.1% relative) | -10.6pp utility (47.7%→42.7%) | 19-92ms (PromptGuard) + LLM call (AlignmentCheck) + 60-300ms (CodeShield) | 22M-86M classifier + LLM guardrail | Medium (configurable YAML pipeline, 3 off-the-shelf scanners) | High (modular, plug-in architecture) | High (3 benchmarks, production-proven at Meta, open source) |
| **ACI-SENTINEL** (Semantic Pruning) | 54.0%→0.22% (99.6% relative, AutoGen) | -5.6pp utility (57.78→52.22) | 1 LLM context-pruning call per step | Prompt template only | Very Low (prompt-only, no model training) | High (works across any MAS) | Medium (1,356 test cases, 6 MAS, but degrades under adaptive attacks) |
| **Llama Guard** (Input/Output Classifier) | N/A (classification accuracy) | 0.945-0.953 AUPRC | 1 LLM forward pass per check | 7B parameter model | Low (use pre-trained model, prompt-based taxonomy) | High (zero-shot taxonomy adaptation) | High (4 benchmarks, open weights, widely adopted) |
| **NeMo Guardrails** (Programmable Rails) | 24%→97% harmful blocked (text-davinci-003) | -5pp false positives on helpful content | 3x latency (3 sequential LLM calls) | Vector DB + Colang runtime | Medium-High (author Colang flows, maintain canonical form DB) | Medium (prompt-dependent, breaks across model versions) | High (production toolkit, NVIDIA, Apache 2.0) |
| **A-Trust** (Attention Scoring) | 94.6%→23.5% ASR (75.1% relative); 0.8-2.5% with agent records | <2% clean accuracy degradation | 0.41s per message (28x faster than prompt-based) | Logistic regression models (~KB) + attention-extracting LLM | Medium (logistic regression, attention extraction, threshold tuning) | Medium (white-box requirement, few-head models underperform) | Medium-High (novel approach, cross-model generalization, no adaptive attack eval) |

---

## 3. Convergences

These are the safe bets — findings where multiple independent sources agree.

### Convergence 1: Structural Guarantees Beat Detection-Based Defenses

Three independent research groups converge on this: CaMeL (Google DeepMind, 2503.18813v2) states "model-level defenses are probabilistic and fall to adaptive attacks — the system must be made robust regardless of model." Progent (UC Berkeley, 2504.11703v4) argues "detection models are inherently probabilistic and can be bypassed; symbolic rules + SMT solving provide deterministic enforcement." ACIARENA (Zhejiang/Tsinghua/UCLA/Palo Alto Networks, 2604.07775v1) explicitly demonstrates that model-level defenses are "inherently fragile" — prompt sandwiching amplifies one attack type while reducing another. The book *Agentic Architectural Patterns* (Arsanjani) codifies this as "safety-by-construction" — externalizing safety into separate structural components rather than embedding it in prompts.

**Implication for Lyra:** Any safety architecture that relies primarily on prompt-level defenses or model alignment is insufficient. Lyra needs structural isolation between trusted and untrusted execution contexts.

### Convergence 2: Multi-Layer Defense-in-Depth Is Mandatory

LlamaFirewall (Meta, 2505.03574v1) explicitly argues that "no single defense suffices" and demonstrates that PromptGuard + AlignmentCheck + CodeShield reduce ASR by 90% vs 57% for the best single layer. NeMo Guardrails (NVIDIA, 2310.10501v1) states programmable rails "should not be used as a stand-alone solution, especially for safety-specific rails" — they supplement, not replace, embedded alignment. "Towards Trustworthy Agentic AI" (2605.23989v1, CUHK/Fudan) formalizes this into a four-tier assurance stack (Upfront → Training-time → Runtime → Post-hoc) and states mitigations across stages are "complementary, not substitutable." *Building Reliable AI Systems* (chapters) structures the entire reliability framework around three layers: outputs, agents, and operations.

**Implication for Lyra:** Lyra's safety architecture must span pre-deployment (red-teaming, policy design), runtime (input/output guarding, tool gating, CoT auditing), and post-hoc (telemetry, trace replay, continuous evaluation) — no single layer is sufficient.

### Convergence 3: Safety Degrades Under Self-Evolution — Continuous Monitoring Is Required

"Your Agent May Misevolve" (2509.26354v2, ICLR 2026) demonstrates safety degradation across all four evolutionary pathways (model, memory, tool, workflow), even when training data is benign. This is independently corroborated by IMAD/Latent Agents (2604.24881v1), which shows malicious traits can be suppressed but hallucination traits resist complete suppression even under negative steering — suggesting some safety properties are more fragile than others. The AI Auto-Research Roadmap survey (2605.18661v1) catalogs adversarial fragility across all 8 research lifecycle stages, finding that prompt injection can raise review scores to 10.00 under iterative attacks. AgenticEval (2509.26100v2) directly demonstrates that static benchmarks create false security — the self-evolving loop discovers 36pp more failures.

**Implication for Lyra:** Any Lyra component that self-modifies (memory accumulation, prompt template evolution, tool creation) MUST include continuous safety regression testing. The evaluation suite must itself evolve — static test suites provide false confidence.

### Convergence 4: Least Privilege Is the Universal Principle

Four independent techniques from four institutions all converge on least privilege as the organizing principle: Progent (UC Berkeley) enforces it via symbolic tool-call gating; CaMeL (Google DeepMind) via capability-based data-flow tracking; ACI-SENTINEL (Zhejiang/Tsinghua) via semantic context pruning; the LlamaFirewall policy engine (Meta) via configurable tool permissions. The *Agentic Enterprise* book (Hodjat) recommends "wrap every tool in scoped permissions (read vs. write), argument limits, allowlists." Claude Code's security documentation implements this in practice: "Claude Code can only write to the folder where it was started [...] cannot write to parent directories."

**Implication for Lyra:** Lyra's tool-calling architecture should enforce least privilege at the tool boundary by default. Every tool should have declared read/write scope, parameter constraints, and a default-deny posture.

### Convergence 5: Externalized Safety Agents Beat Embedded Guardrails

The *Agentic Enterprise* (Hodjat) states: "Use safeguard agents for compliance — externalize safety into a separate agent rather than embedding it in system prompts. This is more effective and auditable." *AI Agents in Action* (chapters) recommends "guardrails/evaluation" as a mandatory component of any autonomous agent deployment. *Agentic AI for Engineers* (chapters) structures guardrails across "five levels of automation" with dedicated review agents. The paper evidence (CaMeL's dual-LLM architecture, A-Trust's separate TMS LLM, LlamaFirewall's AlignmentCheck using a separate guardrail LLM) converges on the same pattern: safety evaluation should be performed by a structurally separate component with its own LLM instance, not by prompting the main agent to self-evaluate.

**Implication for Lyra:** Lyra should have a dedicated Safety Agent (or Safety LLM instance) that audits the main agent's CoT and actions, operating with its own context and no exposure to untrusted tool outputs.

---

## 4. Contradictions

These need arbitration in Phase 4 plans.

### Contradiction 1: Semantic Pruning vs. Rich Context — Can Safety Coexist with Complex Reasoning?

ACI-SENTINEL (2604.07775v1) demonstrates that aggressively pruning context to only task-essential information can neutralize injection attacks (ASR 79.44% → 0.00% on MetaGPT). But CaMeL (2503.18813v2) identifies a failure mode it calls "data requires action" — when the privileged LLM cannot see the data but the plan depends on data content, the system fails. The AI Auto-Research Roadmap (2605.18661v1) documents that 58.6% of research coding errors are semantic (code runs, wrong algorithm) — this class of error requires rich context to detect. The tension: aggressive pruning eliminates injection surface but may discard information needed for correctness verification. LlamaGuard's design rationale explicitly values semantic richness — its 7B parameter size is chosen for "stronger semantic reasoning for edge cases."

**Arbitration needed:** At what granularity does context pruning switch from being "safety-enhancing" to "correctness-degrading"? Can Lyra implement graduated pruning (prune untrusted sources more aggressively than trusted ones)?

### Contradiction 2: Deterministic vs. ML-Based Enforcement — Where Should the Boundary Be?

Progent (2504.11703v3) uses deterministic SMT-based policy comparison with formal monotonic confinement. CaMeL (2503.18813v2) uses deterministic AST-based dependency tracking. But LlamaFirewall (2505.03574v1) uses an ML classifier for PromptGuard 2 (DeBERTa) and an LLM for AlignmentCheck — both probabilistic. A-Trust (2506.02546v2) uses logistic regression classifiers, also probabilistic. The empirical evidence is mixed: Progent achieves the strongest ASR reduction (39.9% → 1.0%), but LlamaFirewall's AlignmentCheck catches semantic goal drift (the "indirect injection" class) that deterministic content filters miss.

**Arbitration needed:** Deterministic enforcement at the tool-call boundary (where failure is catastrophic) + probabilistic detection for content-level threats (where false positives are tolerable)? Or should Lyra aim for end-to-end determinism?

### Contradiction 3: Centralized vs. Distributed Safety Monitoring

ACIARENA (2604.07775v1) demonstrates that multi-agent systems amplify injection risk through inter-agent trust chains — a single compromised agent can cascade malicious instructions to all downstream agents. This suggests centralized safety monitoring with a global view. But Meta-Team (2605.29790v1) demonstrates that collaborative self-evolution (distributed attribution) outperforms global (centralized) attribution on long trajectories (77.5% vs 35.0% agent accuracy on >128K token traces). A-Trust solves this with a centralized TMS that monitors all agent messages, achieving 100% agent-level detection.

**Arbitration needed:** Centralized TMS for message-level trust scoring (A-Trust pattern) with distributed self-audit for agent trajectory quality (Meta-Team pattern)? The safety function should be centralized; the quality function can be distributed.

### Contradiction 4: Open vs. Proprietary Models for Safety Guardrails

Llama Guard (Meta, 2312.06674v1) argues for open weights: "Releasing model weights allows the community to adapt to novel taxonomies and use cases." AgenticEval (2509.26100v2) uses GPT-4.1 for evaluation and Gemini 2.5 Pro for generation — proprietary models. NeMo Guardrails (NVIDIA, 2310.10501v1) is model-agnostic by design. "Towards Trustworthy Agentic AI" (2605.23989v1) notes that "credential recovery gaps" persist when secrets leak into agent memory, and "once a secret leaks into agent memory/logs, it can persist and be replayed" — this is a particular risk when safety guardrails share model infrastructure with the main agent.

**Arbitration needed:** The safety guardrail LLM should be a separate instance (or separate provider) from the main agent LLM to prevent single-point compromise. For on-device deployments, a small open-weight safety classifier (Llama Guard, PromptGuard 22M) may be necessary.

---

## 5. Open Problems

Problems that NO source in the reviewed corpus solves.

### Open Problem 1: Text-Output Attacks Remain Out of All Structural Defenses

Every structural defense (Progent, CaMeL, ACI-SENTINEL, Progent) explicitly acknowledges that text-to-text attacks are out of scope. Progent: "cannot defend against attacks targeting agent text responses (e.g., generating harmful content, revealing system prompts)." CaMeL: "text-to-text attacks out of scope — attacks that don't change control/data flow (e.g., phishing text, biased summaries) are explicitly not defended against." The AI Auto-Research Roadmap (2605.18661v1) documents that "valley of mediocrity" outputs (fluent but lacking rigor) pass all current guards. The *Building Reliable AI Systems* book notes that benchmark capability (85%+ on SWE-bench) drops to 58-65% on fresh codebases when text-output quality degrades in ways no structural guard catches.

### Open Problem 2: No Defense Handles Multimodal Injection Vectors

Prompt Guard 2 (LlamaFirewall, 2505.03574v1) lists "multimodal prompt injection (images, audio, video)" as future work. ACIARENA (2604.07775v1) is text-only. Progent (2504.11703v3) notes "multimodal tool calls unsupported — visual elements (GUI clicking, screen regions) cannot be represented in the current policy schema." AgentDojo (2406.13352v3) is text-only. No technique in the corpus even evaluates, let alone defends against, injection via images embedded in tool outputs (e.g., a malicious SVG in a web page the agent fetches).

### Open Problem 3: Safety-Preserving Self-Evolution

"Your Agent May Misevolve" (2509.26354v2) demonstrates that all mitigations tested (DPO post-training, prompt injection, security prompting, safety instructions in workflow nodes) fail to fully restore safety to pre-evolution levels. IMAD/Latent Agents (2604.24881v1) shows hallucination traits resist complete suppression even under strong negative steering. MetaClaw (2603.17187v1) notes that the skill library grows monotonically without pruning or deduplication — skill collision/contradiction is not addressed. No source provides a method for an agent to self-improve while provably preserving safety alignment.

### Open Problem 4: Adaptive Attack Resilience — All Defenses Degrade Under Optimization

ACIARENA (2604.07775v1) demonstrates ACI-SENTINEL degrades from 0% → 10-37% ASR under adaptive attacks. AgentDojo (2406.13352v3) notes "truly adaptive attacks that optimize against specific defenses remain future work." LlamaFirewall (2505.03574v1) evaluated against "static attack datasets, not adversaries who adapt to the defenses." STAR-Teaming (2604.18976v1) achieves 77.3% ASR with dynamic expansion — suggesting attackers can adapt faster than defenders. No defense in the corpus has been evaluated against a fully adaptive adversary that knows the defense mechanism and optimizes against it.

### Open Problem 5: Recursive Trust in Multi-Layer Auditing

"Towards Trustworthy Agentic AI" (2605.23989v1) identifies the "scalable oversight bottleneck" — "AI-assisted oversight introduces recursive trust concerns that remain unresolved." If Lyra uses an LLM to audit its own outputs (AlignmentCheck pattern), who audits the auditor? CaMeL partially addresses this by structural separation (P-LLM never sees untrusted data), but the Q-LLM could still be compromised. A-Trust uses a "single trusted LLM" for attention extraction — "if that LLM were compromised, the entire trust mechanism would fail." No source provides a principled solution to recursive trust.

### Open Problem 6: Cross-Agent Attribution in Multi-Agent Safety Incidents

"Towards Trustworthy Agentic AI" (2605.23989v1) explicitly states: "Assigning responsibility requires protocol-aware traces, message authentication, and evaluation designs that separate individual from collective failure modes — these are noted as open problems." ACIARENA (2604.07775v1) can identify which agent was compromised but cannot attribute cascading downstream harm to the originating injection with formal certainty. Conjunctive Prompt Attacks (2604.16543v1) exploit exactly this attribution gap — the key and template are benign in isolation and harmful only when conjunctively activated.

### Open Problem 7: Safety-Performance Pareto Frontier for Guardrail Overhead

CaMeL imposes 2.73-2.82x token overhead. NeMo Guardrails imposes 3x latency. LlamaFirewall's full stack adds cumulative latency per turn. Progent adds SMT solver calls. But none of these papers has measured the safety-performance Pareto frontier — at what level of guardrail overhead does the agent become too slow to be useful, and how does that trade off against ASR reduction? This is critical for Lyra's deployment planning but is entirely unquantified in the literature.

---

## 6. Recommendations for Lyra

Ranked by priority, with rationale grounded in the evidence above.

### Recommendation 1 (P0 — Must Have): Implement Deterministic Tool-Call Gating with Least Privilege

**What:** Adopt the Progent pattern — intercept all tool calls, check against an LLM-generated least-privilege policy using deterministic rule matching, auto-approve permission narrowings, require explicit approval for expansions.

**Why:** This is the single most effective defense measured in the corpus: 97.5% relative ASR reduction with zero utility degradation. It is model-agnostic, framework-agnostic, and provides formal monotonic confinement guarantees. It is also the technique where all independent sources converge — structural privilege control beats detection.

**Evidence:** Progent ASR 39.9% → 1.0% (AgentDojo), 70.3% → 3.9% (ASB). Supported by CaMeL's capability-based philosophy, ACIARENA's least-privilege principle, and book consensus from *Agentic Enterprise* and *Agentic Architectural Patterns*.

### Recommendation 2 (P0 — Must Have): Establish Layered Defense-in-Depth Architecture

**What:** Implement the LlamaFirewall pattern — fast lexical gate (PromptGuard 2 22M, 19.3ms on CPU) for obvious violations, slower semantic audit (AlignmentCheck via separate LLM) for subtle drift, invoked only when the fast gate is uncertain or on a sampling schedule.

**Why:** No single defense suffices. The fast-gate + deep-audit pattern maximizes security per unit of latency. The lexical gate catches 88.7% of jailbreaks at 1% FPR in 19ms; the deep audit catches indirect injections that have no lexical trigger.

**Evidence:** LlamaFirewall combined defense: 90.1% ASR reduction. PromptGuard alone: 57% ASR reduction with only 1.5pp utility cost. Endorsed by NeMo Guardrails, "Towards Trustworthy Agentic AI," *Building Reliable AI Systems*, and *AI Agents in Action*.

### Recommendation 3 (P1 — Should Have): Deploy a Separate Safety Auditor Agent

**What:** Create a structurally separate Safety Agent with its own LLM instance, no access to untrusted tool outputs, and a dedicated system prompt for safety auditing. It receives the main agent's CoT trace and proposed actions, evaluates alignment with the user's original objective, and can halt execution.

**Why:** All independent sources (CaMeL, LlamaFirewall, A-Trust, *Agentic Enterprise*, *AI Agents in Action*) converge on the pattern of externalizing safety into a separate component. The Safety Agent should never see raw tool outputs (CaMeL's key insight) — only the agent's reasoning about those outputs.

**Evidence:** CaMeL's P-LLM never sees untrusted data and achieves 0 attacks on Gemini 2.5 Pro. LlamaFirewall AlignmentCheck: 83.6% ASR reduction single-handedly. *Agentic Enterprise*: "externalize safety into a separate agent rather than embedding it in system prompts. This is more effective and auditable."

### Recommendation 4 (P1 — Should Have): Implement Continuous Self-Evolving Safety Evaluation

**What:** Build an AgenticEval-style pipeline that parses Lyra's safety policies into structured rules, generates diverse adversarial test suites (base, jailbreak, multimodal, MCQ), and runs an iterative Analyst-Evaluator loop that discovers Lyra's specific failure modes and produces progressively harder tests.

**Why:** Static benchmarks create false security. The corpus evidence shows safety degrades across ALL evolutionary pathways in self-improving agents, even with benign data. An evaluation suite that does not evolve will miss accumulating safety drift.

**Evidence:** AgenticEval discovers 36.14pp more failures on GPT-5 than single-pass evaluation. "Your Agent May Misevolve" shows safety degradation of 4.5-45pp across all four evolutionary pathways. The AI Auto-Research Roadmap survey documents adversarial fragility across all 8 research lifecycle stages.

### Recommendation 5 (P2 — Nice to Have): Implement Attention-Based Trust Scoring for Multi-Agent Communication

**What:** Instrument Lyra's inter-agent message channels with attention-derived trust signals. When Lyra deploys multi-agent teams, each message is scored across 6 trust dimensions. Agent-level trust records with sliding-window violation tracking enable automatic flagging and removal of compromised agents.

**Why:** A-Trust achieves 100% agent-level detection and reduces AiTM ASR to 0.8-2.5%. This becomes critical when Lyra scales to multi-agent orchestration with agents from diverse sources. It is 28x faster than prompt-based trust evaluation.

**Evidence:** A-Trust MDR >80%, 100% ADR, 0.8-2.5% ASR with trust records. ACIARENA demonstrates that multi-agent systems are especially vulnerable to cascading injection — A-Trust directly addresses this gap.

### Recommendation 6 (P2 — Nice to Have): Adopt "Memory as Reference, Not Rules" Principle

**What:** When Lyra's memory subsystem accumulates experiences and injects them into context, add a system-level instruction that memories are informational references, not binding instructions. Implement the prompt pattern from "Your Agent May Misevolve."

**Why:** Memory accumulation is a demonstrated vector for safety degradation — Qwen3-Coder-480B loses 45pp in Refusal Rate after memory evolution. This prompt-based mitigation reduces ASR from 20.6% → 13.1% and costs essentially zero implementation effort.

**Evidence:** "Your Agent May Misevolve": memory-induced ASR reduction from 20.6% → 13.1%. Supported by MetaClaw's support-query separation principle (stale context should not train current behavior).

### Recommendation 7 (P3 — Research Track): Investigate Safety-Preserving Self-Evolution

**What:** Fund research into methods for an agent to self-improve while provably preserving safety alignment. This is Open Problem 3 — no source in the corpus solves it.

**Why:** All four evolutionary pathways (model, memory, tool, workflow) degrade safety, and all tested mitigations fail to restore pre-evolution baselines. Since Lyra's architecture includes self-improvement components (memory accumulation, skill library, prompt optimization), this is a structural risk that will only grow as Lyra matures.

**Evidence:** Comprehensive failure analysis from "Your Agent May Misevolve" (ICLR 2026). Meta-Team's collaborative evolution architecture provides a potential framework for safety-aware evolution but has not been evaluated for safety properties.

---

## Source Index

### Papers Cited
| ID | Title | Authors | Venue |
|----|-------|--------|-------|
| 2312.06674v1 | Llama Guard: LLM-based Input-Output Safeguard | Inan et al. (Meta) | arXiv 2023 |
| 2310.10501v1 | NeMo Guardrails: Programmable Rails | Rebedea et al. (NVIDIA) | arXiv 2023 |
| 2406.13352v3 | AgentDojo: Prompt Injection Evaluation | Debenedetti et al. (ETH Zurich) | NeurIPS 2024 |
| 2503.18813v2 | Defeating Prompt Injections by Design (CaMeL) | Debenedetti et al. (Google DeepMind) | arXiv 2025 |
| 2505.03574v1 | LlamaFirewall: Open Source Guardrail System | Chennabasappa et al. (Meta) | arXiv 2025 |
| 2504.11703v3 | Progent: Securing AI Agents with Privilege Control | Shi et al. (UC Berkeley) | arXiv 2025 |
| 2604.07775v1 | ACIARENA: Agent Cascading Injection Evaluation | An et al. (Zhejiang Univ) | arXiv 2026 |
| 2604.18976v1 | STAR-Teaming: Multiplex Network Red Teaming | Jung et al. (DATUMO) | arXiv 2026 |
| 2509.26354v2 | Your Agent May Misevolve (ICLR 2026) | Shao et al. (Shanghai AI Lab) | ICLR 2026 |
| 2509.26100v2 | AgenticEval: Self-Evolving Safety Evaluation | Wang et al. (Fudan Univ) | arXiv 2026 |
| 2605.23989v1 | Towards Trustworthy Agentic AI (Survey) | Qi et al. (CUHK) | Academia AI 2026 |
| 2506.02546v2 | A-Trust: Attention-Based Trust Management | He et al. (MSU/Amazon) | arXiv 2026 |
| 2604.16543v1 | Conjunctive Prompt Attacks in Multi-Agent Systems | Arif et al. (UCF) | arXiv 2026 |
| 2604.18660v1 | Answer Leakage Robustness of LLM Tutors | Zhao et al. (EPFL) | arXiv 2026 |
| 2604.24881v1 | Latent Agents (IMAD): Internalized Debate | Yi et al. (Boston Univ) | arXiv 2026 |
| 2605.18661v1 | AI for Auto-Research: Roadmap & User Guide | Kong et al. | arXiv 2026 |

### Books Cited
| Book | Chapters | Playbook | Key Safety Content |
|------|----------|----------|-------------------|
| Building Reliable AI Systems | Yes | Yes | Three-layer reliability framework, model vs. system engineering |
| Agentic Architectural Patterns (Arsanjani) | Yes | Yes | Safety-by-construction, externalized privilege control |
| AI Agents in Action | Yes | Yes | Guardrails/evaluation as mandatory component, safety warnings |
| Agentic AI for Engineers | Yes | Yes | Five levels of guardrail automation, tool scoping |
| Agentic Enterprise (Hodjat) | Yes | Yes | Safeguard agents for compliance, multi-agent governance |

### Web/Repo Notes Cited
| Source | Key Safety Content |
|--------|-------------------|
| ethz-spylab/agentdojo | Prompt injection benchmark architecture, deterministic utility/security checks |
| Claude Code Security Docs (code.claude.com) | Sandboxing, write-access scoping, prompt injection mitigations, fail-closed matching |
| All-Hands-AI/OpenHands | Sandbox isolation as first-class primitive, agent-server container separation |
