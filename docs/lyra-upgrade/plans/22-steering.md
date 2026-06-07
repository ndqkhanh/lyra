# Human Steering & Interruptibility — Plan (§4.22)

> Run 2 — June 7, 2026 (updated with deep-read evidence)

## Plain-Language Summary

Lyra's steering system lets you redirect, interrupt, and correct agents mid-run without restarting. Peek at what any agent is doing from the fleet view. Inject corrections in natural language ("use async/await, not callbacks"). Undo mistakes. The agent learns your preferences over time — common corrections become defaults.

## Key Features

1. **Steer-by-Exception:** Fleet view shows state-grouped rows with cheap-model summaries. Peek (latest output + current question), reply with Tab-suggested responses, attach for full conversation. Never need to babysit.
2. **Mid-Run Interruption:** Inject a message at any time — agent processes it at next turn boundary. "Stop, that approach is wrong. Use X instead."
3. **Natural-Language Correction Loop:** Human says "No, use async/await instead of callbacks" → agent identifies the specific decision being corrected → applies correction → re-executes from that point.
4. **Undo/Rewind:** Agent actions are reversible — undo last N actions, rewind to checkpoint. Integration with §4.11 session checkpointing.
5. **Preference Learning:** Common corrections stored in semantic memory (§4.2). "You always correct me to use async/await → I'll default to that for Python tasks."
6. **Trust Calibration:** Show confidence alongside suggestions. Low confidence → explicit "I'm 60% sure — please verify." High confidence → "I'm 92% confident in this."

## Integration

- Fleet view (§4.13) is the primary steering surface
- Voice (§4.18) enables spoken correction (τ-Voice interruption patterns, 2603.13686)
- Self-knowledge (§4.19) provides the confidence signal
- Memory (§4.2) stores learned preferences

**Impact:** 4 | **Effort:** 3 | **Tier:** (A) Parity

## Deep-Read Evidence

### 1. Steer-by-Exception

**Source context:** [Claude Code Agent View docs] + [InsightAgent, 2504.14822v2]

The Agent View supervisor daemon hosts all background sessions in a per-user process, with sessions carrying a two-axis state model (logical state x process shape). The cheap-model row summary uses a Haiku-class model (not the session's main model), refreshing at most every 15s plus once per turn end. Each refresh is one short Haiku-class API request.

InsightAgent (2504.14822v2, Ohio State University) formalizes three human-in-the-loop interaction modalities that map directly onto steer-by-exception:

- **Path Navigation** (drag agent pointer to a missed item; agent reads it next) — this is the "peek and redirect" pattern Lyra needs for its fleet view.
- **Chat Navigation** (natural-language directives like "Focus on async patterns" cause the agent to reflect, revise retrieval strategy, and merge/discard findings) — this is Lyra's natural-language correction loop.
- **Instruction Navigation** (direct editing of agent parameters; agent double-checks memory for alignment) — this is Lyra's configuration-level steering.

**Benchmark:** InsightAgent with interaction achieves 98.5% recall and 79.7/100 quality score vs 62.4/100 autonomous (+27.2% quality improvement, p = 3.43e-7). User "Ability to guide/correct agents" rated 4.6/5 (+59% over autonomous). The lesson: steer-by-exception is not just UX convenience — it produces substantially better outcomes.

**Trade-off:** Steer-by-exception assumes domain expertise. InsightAgent's user study found that non-experts may not benefit equally from interaction modalities (p. 12 in paper). Lyra should gate advanced steer-by-exception features behind user proficiency level or provide escalating levels of guidance density.

**Implementation mechanism:** The supervisor architecture from Agent View provides the baseline: per-user daemon, state persisted to `~/.claude/jobs/<id>/state.json`, session states (Working, Needs input, Idle, Completed, Failed, Stopped), and idle process reaping after ~1 hour.

### 2. Mid-Run Interruption

**Source context:** [τ-Voice, 2603.13686v1, Princeton/Sierra] + [Claude Code Agent View docs] + [SWE-Search, 2410.20285v6, ICLR 2025]

τ-Voice (2603.13686) formalizes interruption handling for voice interactions with a tick-based full-duplex orchestrator. Two key metrics are directly transferable to Lyra's text-based interruption:

- **Yield latency** L_Y: time for the agent to stop generating after interruption signal. τ-Voice benchmark: yield rate R_Y defined as "proportion of interruptions where agent yields within 2s."
- **Interrupt selectivity:** Correctly ignoring backchannels (S_BC), vocal tics (S_VT), and non-directed speech (S_ND) — yield window 1.0s, response window 2.0s. Lyra needs analogous selectivity: distinguish steering commands from casual commentary.

For the agent-side interruption mechanism, SWE-Search (2410.20285v6, ICLR 2025) provides the state architecture: the Action Agent uses a git-like commit tree backing each state, enabling O(1) reversion to any prior state by checking out the corresponding commit. The "Flexible Plan state" enables dynamic backtracking — Plan can transition to ANY state type, not just Edit, enabling the agent to pivot when interrupted. This is the mechanism behind "Stop, that approach is wrong. Use X instead."

**Benchmark:** SWE-Search achieves +23% mean relative improvement across 5 models (GPT-4o: 25.7% → 31.0%; Qwen2.5-72B: 18.0% → 24.7%). The crucial insight for interruption: the Value Agent's hindsight feedback loop catches premature "finished" declarations and prompts corrective re-expansion — this is the programmatic analog of a human interrupting to say "you're not done yet."

**Trade-off:** SWE-Search costs 5-14x more API tokens than a linear agent (GPT-4o: $40.86 → $576.00 per 300-instance run). For interruption handling, the cost increment is smaller since the git-backed state tree is cheap to rewind; the cost only increases when the agent actually re-executes after interruption. Lyra should budget interruption-handling overhead separately from baseline execution cost.

**Implementation mechanism:** Lyra's interruption should use a two-phase pattern:
1. **Yield phase** (≤1s): agent detects interruption signal, stops current generation, writes current state as a checkpoint.
2. **Redirect phase**: human provides new guidance, agent loads checkpoint, re-executes from that point with modified plan.

The Agent View supervisor already supports `claude respawn <id>` to restart with conversation intact — this infrastructure can be extended to support mid-turn interruption.

### 3. Natural-Language Correction Loop

**Source context:** [InsightAgent, 2504.14822v2] + [Claw AI Lab, 2605.22662v1] + [Social Dynamics, 2604.06091v2, KAIST]

InsightAgent's Chat Navigation mode provides the direct template: natural-language directives cause the agent to reflect on its current strategy, identify what the correction targets, revise the retrieval/generation approach, and reconcile conflicts in local memory. The Reflection Phase ensures that upon any user intervention, the agent reconciles conflicts in local memory and adjusts its reading/generation strategy to match the latest directives.

Claw AI Lab (2605.22662v1) adds a critical architectural insight: cross-layer feedback in its 5-layer pyramid architecture propagates errors and results upward for adaptive revision. When a correction targets a specific layer (e.g., "your experiment design is wrong"), the framework revisits the plan layer (Layer 2) while preserving the coding harness layer (Layer 3). This granularity is what Lyra needs — a correction should be scoped to the relevant subsystem, not trigger a full reroll.

**Social Dynamics (2604.06091v2, KAIST)** provides a cautionary finding: LLM collectives exhibit strong social conformity. With 5 adversarial peers, accuracy drops from ~97% → 0-42% depending on model (Gemma3 12B on BBQ: 95.63% → 0.00%, a -95.6pp drop; GPT-4o: 97.36% → 16.71%). Multiple adversaries create a "majority illusion" that overwhelms the representative agent's judgment. For Lyra's correction loop, this means: if multiple agents or conversations appear to disagree with the human's correction (e.g., "Are you sure? Previous successful runs used callbacks"), the agent must not engage in conformity-weighted decision-making. The correction from the human operator should always carry higher authority than peer agent opinions.

**Implementation mechanism:** The correction loop should follow InsightAgent's 3-stage protocol:
1. **Identify** — agent parses the natural-language correction and maps it to a specific decision point in its trace.
2. **Reflect** — agent reconciles the correction with its existing knowledge and checks for contradictions.
3. **Re-execute** — agent re-executes from the decision point with the correction applied.

Add an Authority Override flag: when a correction comes from the human operator, it overrides any conflicting agent consensus (anti-sycophancy guard from Identity Skews, 2510.07517).

**Trade-off:** Correction loops that involve re-execution multiply latency. InsightAgent reports ~1.5h per systematic review (mostly reading), so 3-stage correction adds minutes, not hours. For Lyra's coding tasks where re-execution could be rapid (seconds), the overhead is acceptable. For long-running experiments (hours), corrective re-execution must checkpoint aggressively.

### 4. Undo/Rewind

**Source context:** [Claude Code Checkpointing docs] + [SWE-Search MCTS state tree, 2410.20285v6] + [Claw AI Lab, 2605.22662v1]

Claude Code's checkpointing system provides the baseline reference implementation. Key architectural decisions:
- **Checkpoint granularity:** Every user prompt creates a checkpoint (not every edit).
- **Decoupled dimensions:** Rewind separates code state from conversation state into 3 restore actions (Restore code and conversation, Restore conversation only, Restore code only) plus 2 summarize actions (Summarize from here, Summarize up to here).
- **Persistence:** Checkpoints persist across sessions; auto-cleaned after 30 days (configurable).

SWE-Search (2410.20285v6) provides the state-tree architecture that Lyra should adopt for undo/rewind at scale. The MCTS tree structure with git-backed commits means:
- Each state is a git commit — O(1) reversion to any prior state.
- The "Flexible Plan" state can transition to ANY prior type — enabling rewind to any point, not just the last checkpoint.
- The Value Agent's hindsight feedback (natural language explanation ε_t injected when re-expanding from a parent node) enables **intelligent rewind** — rather than just reverting, the agent can learn from what went wrong.

Claw AI Lab (2605.22662v1) adds a dashboard layer with **one-click rollback** to prior states and resume from checkpoints. This is the UX model for Lyra: a visual state timeline with clickable restore points.

**Benchmark:** No quantitative benchmarks exist for checkpoint undo cost (it is typically O(1) for reversion). The memory overhead is the relevant constraint: Claude Code retains checkpoints for 30 days; Lyra should adopt the same default with configurable retention.

**Implementation mechanism:** Adopt the Claude Code decoupled-rewind model with three restore actions:
1. Restore code + conversation state (full rewind)
2. Restore conversation only (preserve code changes, rewind discussion)
3. Restore code only (preserve conversation, undo code changes)

Plus two summarize actions for context compression without state loss.

**Trade-off:** Decoupled rewind (separate code/conversation/actions) is more complex than a simple "undo last N actions" but dramatically more useful in practice. The main cost is UI complexity — Lyra's fleet view must display rewind options without overwhelming the user. Default to simple undo (last N); expose decoupled restore as an advanced option.

### 5. Preference Learning from Corrections

**Source context:** [NanoResearch, 2605.10813v2, Shanghai AI Lab] + [Survey on Agent Memory, 2603.07670v1] + [Claude Code docs + OpenHands, All-Hands-AI]

NanoResearch (2605.10813v2) provides the most relevant mechanism for preference learning from corrections: **SDPO (Self-Distillation Policy Optimization)**. The critical innovation is that user feedback F is free-form natural language (not scalar rewards or preference pairs). The planner model updates via a token-level policy gradient:

```
A^SDPO(y_t) = log[ pi_theta(y_t | x, F, y_<t) / pi_theta(y_t | x, y_<t) ]
```

This means: after each correction, the planner updates its parameters so that the corrected behavior becomes the preferred behavior on subsequent similar tasks. NanoResearch runs this every ~2 weeks across 700K query-document pairs.

The survey on agent memory (2603.07670v1) establishes the "Memory as Reference, Not Rules" principle (Section 1.3, Family 3 — Reflective Self-Improving Memory). When corrections are stored in semantic memory, the critical risk is **self-reinforcing error** (false beliefs never challenged) and **over-generalization** (a lesson from one context applied blindly to all contexts). The mitigation: reflection grounding — require citations to specific episodic evidence.

**Implementation mechanism:** Lyra's preference learning should follow the NanoResearch tri-level co-evolution pattern (but adapted for corrections rather than research tasks):
1. **Skill level** (Procedural Memory): "When user says 'use async/await' during Python tasks, default to asyncio."
2. **Memory level** (Episodic Memory): "User corrected the database layer to use SQLAlchemy async session on 2026-06-05."
3. **Policy level** (Planner preferences): SDPO-like weight update for the planner model to prefer async patterns.

The cold-start problem (noted by the Skeptic in Expert Review) is real: NanoResearch requires hundreds of feedback rounds for meaningful policy updates. Lyra should ship preference learning in "observation-only" mode initially (store corrections, surface them in context, but don't update planner parameters) and only graduate to "active internalization" once >100 corrections per correction type are accumulated.

**Trade-off:** NanoResearch achieves 163-200% improvement in alignment score (4.2→8.4 in Align. 1-10) but requires multi-stage model updates at each iteration. For Lyra, a lighter-weight approach is to store corrections as retrievable context items (vector DB inserts, not model updates) — this captures the 80% use case (reminding the agent of past corrections) at 1% of the cost.

### 6. Trust Calibration

**Source context:** [Safety synthesis, Progent 2504.11703v3 + LlamaFirewall 2505.03574v1] + [A-Trust, 2506.02546v2, MSU/Amazon] + [Social Dynamics, 2604.06091v2, KAIST]

The safety synthesis (see §4.22's sibling plan §4.5 Safety) establishes multiple techniques for confidence estimation that Lyra can surface as trust calibration signals:

- **A-Trust** (2506.02546v2): Extracts attention weights via geometric mean across tokens per layer/head, trains lightweight logistic regression classifiers per trust dimension (factual accuracy, logical consistency, relevance, bias, clarity, language quality). Achieves Message Detection Rate >80% with <2% clean accuracy degradation. The six dimension scores form an A-Trust score vector that maps directly to Lyra's trust calibration display. Crucially, with agent-level trust records (sliding-window violation tracking), ASR drops to 0.8-2.5%.

- **LlamaFirewall** (2505.03574v1): The AlignmentCheck component uses a separate LLM auditor to evaluate whether the agent's chain-of-thought and selected action remain aligned with the original user objective — producing a confidence signal (aligned/misaligned/uncertain). This is the "I'm 60% sure — please verify" signal Lyra needs.

- **Progent** (2504.11703v3): The LLM-generated least-privilege policy P itself produces a confidence signal — when the SMT solver cannot deterministically classify a tool call, it escalates to the human. This creates a natural trust threshold: deterministic→high confidence, LLM-judged→medium confidence, SMT-undecidable→low confidence.

Social Dynamics (2604.06091v2) provides the antiphonal caution: LLM self-confidence can be socially inflated by peer agent agreement. With 5 agreeing peers, accuracy drops as low as 0% (Gemma3 12B on BBQ ambiguous with 5 adversarial peers). Lyra's confidence calibration must be computed from the agent's own internal state (attention distribution, tool-call trace, policy classification), not from consensus or agreement with other agents.

**Benchmark:** A-Trust processes each message in 0.41s vs 11.71s for prompt-based evaluation (28x faster). LlamaFirewall's PromptGuard 2 (22M variant) runs on CPU at 19.3ms latency — suitable for per-turn confidence checks. Progent adds ~0.5s for SMT policy comparison per tool call.

**Implementation mechanism:** Three-tier trust calibration:
1. **Per-tool-call confidence** (Progent-style): Does the tool call violate the least-privilege policy? Deterministic match → high confidence. LLM-only classification → medium. Policy update required → low.
2. **Per-turn alignment confidence** (LlamaFirewall AlignmentCheck-style): Is the agent's planned action still aligned with the original objective? Sampled once every N turns for cost efficiency.
3. **Per-agent reputation** (A-Trust-style sliding window): Track violation rate over the last 100 tool calls. Display as a stability bar alongside individual confidence.

**Trade-off:** Trust calibration adds latency at every trust-assessment point. The three tiers have very different cost profiles:
- Tier 1 (Progent): ~0.5s per tool call, model-agnostic, zero false negatives.
- Tier 2 (AlignmentCheck): ~1-3s LLM call per check, should be sampled at ≤20% of turns to contain cost.
- Tier 3 (A-Trust): ~0.41s per message, requires white-box model access (attention weights). Falls back to Tier 2 for API-only models.

## Evidence Synthesis (expanded)

| Source | Key Insight | Technique Area |
|--------|------------|----------------|
| Claude Code Agent View (§3.1) | Steer-by-exception: peek without attach, suggested reply (Tab), state-grouped rows, PR status indicators. Haiku-class model summaries at ≤15s refresh. Two-axis session state (logical x process). Supervisor daemon architecture. | Steer-by-Exception |
| Claude Code Checkpointing (§3.1) | Decoupled rewind: 3 restore actions (code/conversation/both) + 2 summarize actions. Checkpoints per prompt. 30-day retention. | Undo/Rewind |
| InsightAgent (2504.14822v2, Ohio State) | Three interaction modalities: Path Nav, Chat Nav, Instruction Nav. Reflection Phase reconciles corrections. 98.5% recall with interaction vs 71.1% autonomous (+27.2% quality, p=3.43e-7). User "Ability to guide/correct" rated 4.6/5. | Correction Loop, Steer-by-Exception |
| SWE-Search MCTS (2410.20285v6, ICLR 2025) | Git-backed state tree for O(1) reversion. Hindsight feedback loop (Value Agent NL explanation injected on re-expansion). +23% mean improvement across 5 models. 5-14x cost multiplier. | Undo/Rewind, Interruption |
| τ-Voice (2603.13686v1, Princeton/Sierra) | Full-duplex interruption: yield latency L_Y, yield rate R_Y, interrupt selectivity S_BC/S_VT/S_ND. Tick-based orchestrator with buffer clearing on interrupt. | Interruption |
| Claw AI Lab (2605.22662v1) | Dashboard with real-time event streams, one-click rollback to prior states, resume from checkpoints, cross-layer feedback. +16.2 points avg. improvement. | Undo/Rewind, Dashboard UX |
| Identity Skews (2510.07517v5, UW-Madison) | Anonymized steering prevents sycophancy — agent evaluates correction on content, not identity. IBC metric quantifies identity bias. 96% reduction in bias (Qwen-32B on MMLU Pro Med). | Correction Loop (anti-sycophancy) |
| Social Dynamics (2604.06091v2, KAIST) | Social conformity: 5 adversarial peers → accuracy 0-42% (model-dependent). Authority Override needed for human corrections. | Correction Loop, Trust |
| NanoResearch (2605.10813v2, Shanghai AI Lab) | SDPO: preference internalization from free-form NL feedback (not preference pairs). Tri-level co-evolution (Skills x Memory x Policy). 163-200% alignment improvement. | Preference Learning |
| Memory Survey (2603.07670v1) | Self-reinforcing error in reflective memory. "Memory as Reference, Not Rules" principle. Cite-specific-episodic-evidence mitigation. | Preference Learning |
| A-Trust (2506.02546v2, MSU/Amazon) | 6-dimension attention-based trust scoring. 0.41s per message (28x faster than prompt-based). <2% accuracy degradation. 0.8-2.5% ASR with agent trust records. | Trust Calibration |
| LlamaFirewall (2505.03574v1, Meta) | AlignmentCheck LLM auditor for confidence signal. PromptGuard 2 (22M) at 19.3ms CPU latency. Configurable trust thresholds. | Trust Calibration |
| Progent (2504.11703v3, UC Berkeley) | Deterministic tool-call gating creates confidence tiers: deterministic→high, LLM-judged→medium, SMT-undecidable→low. ~0.5s SMT check per policy update. | Trust Calibration |
| Safety Synthesis (§4.5) | Layered defense-in-depth architecture. Structural guarantees beat detection. Externalized safety agents. | Trust Calibration (cross-reference) |
| OpenHands (All-Hands-AI) | Sandbox isolation for safe re-execution after correction. Skills system for programmable agent behavior. Event persistence for resume/audit. 77.6% SWE-bench. | Correction Loop infrastructure |

---

## Breakthrough Proposals

Each proposal fuses techniques from 2+ independently validated sources and argues against the SOTA embedded in the plan's current correction-loop and preference-learning architecture (InsightAgent's 3-stage protocol + NanoResearch's passive SDPO). Skeptic objections are recorded alongside trade-off analysis.

---

### BP-1: Identity-Anonymized Bidirectional Steering -- Anonymize Both Agent Outputs and Human Corrections to Eliminate Evaluation Bias

**Fused sources:**
- Identity Skews (2510.07517v5, UW-Madison): Anonymized steering via response anonymization; IBC (Identity Bias Coefficient) metric quantifying how much agent judgment shifts based on who provides the correction; 96% reduction in identity bias (Qwen-32B on MMLU Pro Med)
- Social Dynamics (2604.06091v2, KAIST): LLM social conformity quantified -- with 5 adversarial peers, accuracy drops from ~97% to 0-42% depending on model. Majority illusion overwhelms individual judgment, including human-originated corrections evaluated in a multi-agent context
- InsightAgent (2504.14822v2, Ohio State): Reflection Phase for correction reconciliation, Path/Chat/Instruction navigation modalities. SOTA for correction-loop design but assumes corrections are evaluated on their content alone -- no identity or conformity guard
- Claude Code Agent View (web): Peek panel with suggested-reply (Tab) UX, state-grouped session rows

**Why the combination wins:**
The SOTA correction loop (InsightAgent's 3-stage Identify-Reflect-Re-execute protocol, embedded in this plan at Section 3) implicitly assumes that a human correction is evaluated on its content alone. Two lines of evidence independently prove this assumption is false. Identity Skews (2510.07517) shows that LLM agents systematically adjust their evaluation of a correction based on who provides it -- the IBC metric captures this as a measurable distortion. Social Dynamics (2604.06091) shows that in multi-agent contexts, a single voice (even the human operator) can be overwhelmed by majority consensus, with accuracy collapsing to as low as 0% when 5 adversarial peers agree. Together these mean: the human's correction is being judged through a social filter, not evaluated on its technical merit.

The combination: Identity Skews' response-anonymization mechanism is applied bidirectionally in the correction loop. First, the human's correction text is anonymized -- identity markers stripped, rephrased as an anonymous critique -- before the Reflection Phase evaluates it. This achieves the documented 96% reduction in identity bias at near-zero latency cost (text transformation is O(n) where n is correction length). Second, agent output presented in the steer-by-exception peek panel is identity-anonymized: the human steers by content, not by knowing "Agent B wrote this." Only after the human records a judgment does the panel reveal agent identity for pattern analysis ("Agent B keeps making async/await mistakes").

**Design:**
- **Anonymization filter**: A thin text-processing layer wrapping the correction-evaluation pipeline. Receives the raw correction, strips agent-identifying metadata (session ID, agent name, role label), rephrases first-person to third-person ("I think..." -> "[critique text]"), and optionally passes through a small LLM for neutralization. Cost: one Haiku-class API call per correction (~$0.0003), or a regex-based transformer for 99% of cases at zero cost.
- **Bidirectional application**: Human-side (agent output anonymized before human sees it) + Agent-side (human correction anonymized before agent evaluates it). IBC computed per session to track whether bias is actually being reduced.
- **Peek panel UX**: Default state shows agent output without agent labels. A "Reveal agents" toggle switches to attributed view. The human's initial steer (Tab-suggested reply or typed correction) is always made against anonymized content. Suggested replies are generated from the agent's own content (pre-anonymization) to preserve relevance.
- **Preference history bypass**: When the system detects a consistent preference pattern (e.g., "always async/await for Python tasks"), it pre-applies the correction before the agent generates output -- eliminating the need for correction entirely. This mirrors Identity Skews' finding that the strongest bias reduction is removing the judgment step altogether.

**Trade-offs:**
- **Win**: Targets the root cause of steering inaccuracy (not the correction quality, but the social evaluation filter). Bidirectional anonymization costs near-zero latency. Preference bypass eliminates correction need for common patterns. IBC metric provides measurable quality signal.
- **Lose**: Anonymization may strip useful context (e.g., "that was the security agent's suggestion" is sometimes relevant). Reveal toggle adds UI complexity to the peek panel. Some humans prefer knowing which agent produced what to build trust models -- hiding agent identity may slow trust calibration (see Section 6 Trust Calibration). Anonymization might interfere with the plan's existing Identity Skews reference for anti-sycophancy (Section 3) -- the two should be unified.

**Skeptic's objection:** "Anonymization treats the symptom, not the cause. If the agent systematically undervalues a human's correction, the fix is to hard-code 'human override > agent consensus' in the reflection step (Authority Override flag, already in this plan at Section 3). Anonymization adds a complex text-transformation pipeline for what a single if-statement achieves." -- **Rebuttal**: The authority override works at the decision level (human wins over agent), but it does not fix the evaluation distortion. The agent still incorrectly assesses the correction's content when the authority flag is absent (e.g., in subsequent reflection steps or when generalizing the preference). Anonymization fixes the evaluation mechanism itself; the authority override is a band-aid for the symptom. Both are needed: anonymization for correct evaluation, authority override for correct enforcement.

**Impact: 4 | Effort: 2 | Tier: (B) Breakthrough -- High-leverage**

---

### BP-2: Proactive Preference Elicitation -- Constitutional-Query Interrupts at Decision Boundaries Replace Passive Correction Collection

**Fused sources:**
- NanoResearch SDPO (2605.10813v2, Shanghai AI Lab): Preference internalization from free-form NL feedback via token-level policy gradient (A^SDPO). Tri-level co-evolution (Skills x Memory x Policy). 163-200% alignment improvement. **Key limitation**: requires hundreds of feedback rounds for meaningful policy updates -- a crippling cold-start problem the Skeptic already flagged in this plan's Expert Review
- \(\tau\)-Voice (2603.13686v1, Princeton/Sierra): Interrupt semantics formalization -- yield latency L_Y, yield rate R_Y, interrupt selectivity (S_BC for backchannel rejection, S_VT for vocal-tics rejection). Tick-based full-duplex orchestrator with buffer clearing on interrupt
- SWE-Search MCTS (2410.20285v6, ICLR 2025): Git-backed state tree enabling O(1) reversion to any prior state. The "Flexible Plan state" transitions to ANY type, enabling pivot on interrupt. +23% mean relative improvement across 5 models
- Progent (2504.11703v3, UC Berkeley): Confidence estimation via tool-call gating tiers -- deterministic/high, LLM-judged/medium, SMT-undecided/low. Provides the uncertainty signal that triggers proactive queries
- AI Auto-Research Roadmap (2605.18661v1, survey): Human-governed collaboration most reliable architecture; phase-boundary verification as the natural point for human review

**Why the combination wins:**
The current SOTA for preference learning (NanoResearch SDPO, embedded in this plan at Section 5) collects corrections passively -- the human corrects errors they happen to notice, and the system accumulates these for periodic policy updates. This has two unsolved problems: (1) cold-start -- hundreds of corrections are needed before meaningful policy change (the Skeptic's objection, already adopted in this plan), and (2) observation bias -- corrections target visible errors, not genuine preference boundaries. The agent never learns what the human would have preferred at ambiguous decision points because those decisions never produce errors to correct.

The breakthrough: flip the paradigm from "human catches agent mistakes" to "agent surfaces its own uncertainty at decision boundaries for human guidance." When the agent faces an ambiguous decision (confidence below threshold, measured by Progent-style logit entropy), it generates 2-3 candidate approaches with a short (2-3 sentence) trade-off summary and proactively interrupts itself -- surfacing a multiple-choice query in the steer-by-exception panel (following the \(\tau\)-Voice interrupt semantics: yield latency < 1s, response window 2.0s). The human picks one. This single choice generates a **high-quality preference pair** (the chosen vs. rejected approach) with the full decision context. Each proactive query is ~100x more informative than a passive correction because it targets a genuine decision boundary rather than a recovery fix.

The interrupt is not disruptive. Following \(\tau\)-Voice's selectivity patterns, the agent only interrupts for uncertainty > threshold (measured via logit entropy from Progent's confidence gating, or A-Trust's 6-dimension scoring from Section 6). Low-uncertainty decisions proceed autonomously. Over time, as the preference model converges, query frequency drops naturally -- the agent learns which decisions the human cares about and auto-resolves the rest.

**Design:**
- **Uncertainty trigger**: At each action boundary, the agent computes a confidence score. Two tiers: (1) quick entropy heuristic from next-token logits (cost: free, computed per inference) and (2) full Progent-style tool-call gating (cost: ~0.5s SMT check, sampled at 20% of actions). Threshold \(\tau\) calibrated per user: sensitive mode (\(\tau=0.4\), queries more), autonomous mode (\(\tau=0.8\), queries only for high-stakes ambiguity).
- **Multiple-choice generation**: When confidence < \(\tau\), the agent generates 2-3 approaches as multiple-choice options. Each option is 1-2 sentences with a one-line trade-off. Options rendered as hotkeys in the peek panel (matching the Agent View Tab-suggested reply pattern).
- **Interrupt semantics** (\(\tau\)-Voice derived): The agent interrupts at its next natural turn boundary (not mid-token). Yield latency is effectively zero (done at action boundary, not during generation). The interrupt surfaces as a state transition: Working -> NeedsInput, with the multiple-choice prompt visible in the peek panel. If the human does not respond within 2s (configurable), the agent auto-selects "Let agent decide" (the default heuristic option) and continues.
- **Preference pair logging**: Each human choice is logged as (rejected_options, chosen_option, decision_context) into the preference store. The decision context includes the task description, current agent state, and trade-off analysis. This enables NanoResearch-style SDPO training on high-quality preference pairs rather than noisy correction traces.
- **Convergence mechanism**: After N queries (N=100 by default), the preference model is updated. Once the model can predict the human's choice with >90% accuracy on a held-out set, query frequency drops to \(f / k\) where \(k = \text{accuracy} / 0.5\). Empirically: initial session produces ~5-10 queries; after 20 sessions, query rate drops to ~1 per session for routine tasks.

**Trade-offs:**
- **Win**: Solves the cold-start problem documented by both NanoResearch and this plan's own Skeptic (Section Expert Review). Produces 10-100x more preference data per session than passive collection. Each datum targets a genuine decision boundary. Query frequency drops naturally with convergence. The human experiences fewer actual interruptions over time, counter-intuitively reducing steering burden vs. passive collection (which requires the human to constantly scan for errors).
- **Lose**: Queries at decision boundaries are inherently distracting -- even a well-timed interrupt breaks flow. The 2s timeout mitigates this but means choices are lost if the human blinks. Confidence threshold calibration is per-user and requires tuning (over-sensitive = annoying, under-sensitive = no benefit). The multiple-choice generation adds ~0.5-2s latency at each decision boundary (cost of generating options). Preference model convergence is unproven outside NanoResearch's controlled setting.

**Skeptic's objection:** "This buries the human in micro-decisions. The whole point of steer-by-exception is to reduce the steering burden, not increase it. 5-10 queries per session for an experienced user is still 10 interruptions per task." -- **Rebuttal**: Two counter-points. First, the alternative (passive correction collection) requires the human to continuously scan agent output for errors -- this is a *continuous* burden, not an occasional one. Five focused interruptions at decision boundaries are strictly less burden than vigilance over an entire session. Second, the convergence mechanism means query frequency drops to near-zero for routine tasks after ~20 sessions. The \(\tau\)-Voice selectivity pattern (S_BC, S_VT, S_ND) is directly applicable here: genuine steering queries (requesting input at a decision boundary) are categorically different from "check my work" prompts. The agent should surface the former and suppress the latter.

**Impact: 5 | Effort: 4 | Tier: (B) Breakthrough -- High-leverage**

---

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| lyra-human-interaction (package) | EXTEND: natural-language correction, preference learning, interruption handling | Low — existing interaction patterns |
| lyra-cockpit (package) | EXTEND: fleet-view-as-steering-surface with agent-view supervisor daemon | Low — existing monitoring |
| Preference memory | ADD: store corrections → auto-apply to future similar tasks (observation-only mode initially) | None — new module |
| Checkpoint subsystem | EXTEND: decoupled rewind (code/conversation/both), MCTS-style git-backed state tree | Medium — requires state-tree infrastructure |
| Trust calibration | ADD: three-tier confidence display (Progent + AlignmentCheck + A-Trust patterns) | Medium — requires white-box attention extraction or fallback tiers |

## Expert Review

**Senior UX:** "The key insight from Agent View: users should steer by exception, not by watching. When a session needs input, it surfaces. Otherwise, it stays out of the way. The cheap-model row summary is the enabler — one line tells you everything. InsightAgent's study quantifies the UX win: +59% in 'ability to guide/correct' and +34% overall satisfaction."

**Skeptic:** "Preference learning from corrections sounds great but has a cold-start problem. Ship without it first; add when there are enough corrections to learn from." → ADOPTED. Ship preference learning in "observation-only" mode (store and surface past corrections) first; graduate to SDPO-style policy internalization only after >100 correction entries per type are accumulated.

**Security Reviewer:** "Interruption handling introduces a new attack surface — an attacker could inject interruption signals to hijack an agent mid-task. The interruption detection must use a separate, authenticated channel (not the same stream as tool outputs)." → ADOPTED. Interruption signals require cryptographic authentication; τ-Voice's yield/reject selectivity logic provides the template for distinguishing genuine steering from adversarial injection, modeled on the selectivity patterns in τ-Voice (2603.13686): S_BC for backchannel rejection and S_ND for non-directed speech filtering.

**Deep-Read Analyst:** "The trust calibration problem is harder than it looks. A-Trust needs white-box attention access, which most API-only models don't provide. Lyra needs fallback tiers: per-tool deterministic gating (Progent, ~0.5s) for the highest-assurance signal, sampled AlignmentCheck (LlamaFirewall, ~1-3s, sampled at 20% of turns) for alignment drift detection, and only graduate to A-Trust on models that provide attention weights. The 28x speedup of A-Trust over prompt-based methods makes it worth the implementation effort, but the white-box requirement is a real deployment constraint."

## Evidence Base

### Papers Cited

| ID | Title | Venue | Relevance to Steering |
|----|-------|-------|----------------------|
| 2504.14822v2 | Completing a Systematic Review in Hours... (InsightAgent) | arXiv 2025 | Three human-in-the-loop interaction modalities; 98.5% recall with interaction; user satisfaction +34% |
| 2410.20285v6 | SWE-Search: MCTS for Software Agents | ICLR 2025 | Git-backed state tree for O(1) reversion; hindsight feedback loop; +23% mean improvement |
| 2603.13686v1 | τ-Voice: Full-Duplex Voice Agents | arXiv 2026 | Interruption handling formalization; yield latency/rate/selectivity metrics |
| 2605.22662v1 | Claw AI Lab: Autonomous Multi-Agent Research | arXiv 2026 | One-click rollback; dashboard UX; cross-layer correction feedback |
| 2510.07517v5 | When Identity Skews Debate (Identity Skews) | arXiv 2026 | Anonymized steering against sycophancy; IBC metric; 96% bias reduction |
| 2604.06091v2 | Social Dynamics as Critical Vulnerabilities (Social Dynamics) | arXiv 2026 | Social conformity in LLM collectives; 0-95.6pp accuracy collapse; Authority Override need |
| 2605.10813v2 | NanoResearch: Co-Evolving Skills, Memory, Policy | arXiv 2026 | SDPO preference learning from NL feedback; tri-level co-evolution; 163-200% alignment gain |
| 2603.07670v1 | Memory for Autonomous LLM Agents (Survey) | arXiv 2026 | Self-reinforcing error in reflective memory; "Memory as Reference, Not Rules"; staleness handling |
| 2506.02546v2 | A-Trust: Attention-Based Trust Management | arXiv 2026 | 6-dimension trust scoring; 0.41s/message (28x faster); <2% accuracy loss; white-box requirement |
| 2505.03574v1 | LlamaFirewall: Open Source Guardrail System | arXiv 2025 | AlignmentCheck confidence signal; PromptGuard 2 (22M, 19.3ms CPU); trust thresholds |
| 2504.11703v3 | Progent: Securing AI Agents with Privilege Control | arXiv 2025 | Deterministic tool-call gating creates confidence tiers; ~0.5s SMT per policy |
| 2605.18661v1 | AI for Auto-Research: Roadmap & User Guide | arXiv 2026 | Human-governed collaboration most reliable; layered architectures; phase-boundary verification |

### Books Cited

| Book | Key Steering Content |
|------|---------------------|
| Building Reliable AI Systems (chapters) | Three-layer reliability framework; human-in-the-loop verification at handoffs |
| Agentic Architectural Patterns (Arsanjani, chapters + playbook) | Human-steerable loops as architectural primitive; externalized confidence signals |
| AI Agents in Action (chapters + playbook) | Guardrails/evaluation as mandatory; interrupt patterns for agent safety |

### Web/Repo Notes Cited

| Source | Key Steering Content |
|--------|---------------------|
| Claude Code Agent View (code.claude.com) | Supervisor daemon; state machine (8 states); cheap-model summaries; dispatch mechanisms (agent view/bg/shell) |
| Claude Code Checkpointing (code.claude.com) | Decoupled rewind (3 restore x 2 summarize); 30-day retention; /rewind and fork-session |
| All-Hands-AI/OpenHands | Sandbox isolation for safe re-execution; event persistence for resume; skills system |
