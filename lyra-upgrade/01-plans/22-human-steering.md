# Plan: §4.22 Human Steering & Interruptibility

**Workstream**: Mid-run correction, barge-in, approval gates, undo/rewind
**Priority**: P1 — Required for safe autonomy and user trust
**Date**: 2026-05-31 (Run 16)
**Status**: Initial plan — integrates with existing `lyra-human-interaction`, `lyra-personalization` packages

---

## Plain-Language Summary

An autonomous agent that cannot be interrupted is not a tool — it is a liability. This workstream builds the steering wheel for Lyra: the ability to pause, redirect, and undo agent actions mid-run without losing completed work. Beyond basic stop/undo, it captures what users correct so Lyra learns their preferences over time, and calibrates how much autonomy to grant based on how often the user needs to intervene. If you have to override Lyra 30% of the time, it should start asking before acting; if you almost never override, it earns full autonomy.

---

## 📋 Quick Reference Card

| What | Mechanisms to interrupt, correct, and redirect autonomous Lyra runs without restarting |
| Why | Full autonomy without steering = runaway agent; users need barge-in, mid-run correction, undo |
| Key Insight | Steering is NOT just "add a stop button" — it requires state rollback, preference capture, and trust calibration |
| Timeline | 5 weeks (3 parity + 2 breakthrough) |
| Key Sources | Constitutional AI, interruptible agents (CHI/ACL), mid-task human feedback literature |

## 🎯 Executive Summary

When Lyra runs an autonomous ultracode workflow with 16 parallel agents, the user MUST be able to: (1) see what's happening, (2) stop/pause individual agents, (3) correct wrong direction mid-run, (4) undo agent actions, and (5) have Lyra learn from corrections. Without these, autonomy is unusable — the first wrong turn forces a full restart.

---

## 1. Problem

**Current state**: `lyra-human-interaction` package exists. Workflow engine supports pause/resume (`PauseResumeSerializer`). AVP supports escalation on 1-1-1 critic split. UI has keybindings.

**The gap**: No mid-run redirection, no action undo beyond git, pause/resume not wired to UI, no preference learning from corrections, no trust calibration based on correction frequency.

---

## 2. Evidence Synthesis

### 2.1 Core Sources (with Findings.md Citations)

| # | Source | Key Finding | Transfer to Lyra |
|---|--------|------------|-----------------|
| 67 | SABER mutation-gating (findings.md Lines 35-45) | "Each additional deviation in MUTATING actions reduces success odds by 55-96% (p<0.001), while non-mutating deviations have <10% effect." Mutation-gating catches ~92% of impactful errors while verifying only ~20-30% of actions. The ReAct pattern of "act first, reflect after error" was explicitly rejected because "by the time reflection happens, state is already corrupted." | Steering must be mutating-action-aware: barge-in priority is proportional to mutation risk. Non-mutating actions can be deferred; mutating actions require immediate interrupt capability. This is the EVIDENCE FOUNDATION for why steering exists — the 8% of errors that slip past AVP compound into corrupted state without human override. |
| 118 | [AutoResearchClaw](https://arxiv.org/abs/2605.20025) (findings.md Line 1236) | "7-mode human-in-the-loop collaboration; precise targeted collaboration at high-leverage points beats both full autonomy and step-by-step oversight." Outperforms AI Scientist v2 by 54.7%. Three human-in-the-loop gates at Stages 5, 9, 20 (can be bypassed with `--auto-approve`). Cross-run failure memory as guardrails: "store mistakes from past runs, convert into pre-execution checklist or prompt context." | Human gates belong at natural decision boundaries (phase transitions), not every action. Cross-run failure memory pattern: each steering event → stored with context hash → injected on matching future runs. |
| 162 | [Karpathy Skills](https://github.com/multica-ai/andrej-karpathy-skills) (findings.md Line 1275) | "Declarative over imperative steering: transform 'do X' into 'write tests for X, then make them pass.' Surgical diff discipline as built-in constraint." 163k stars, MIT-licensed. | `/steer` commands should translate natural language into declarative constraints, not imperative overrides. "Focus on auth" becomes "MUST prioritize authentication" injected into agent prompts. |
| 167 | [CheetahClaws](https://github.com/SafeRL-Lab/cheetahclaws) (findings.md Line 1280) | "Generator-based event loop for composable streaming/logging/UI. Checkpoint/rewind, multi-provider, 27 built-in tools. Security at tool level: hard denylists override accept-all." ~40K lines Python, 2,347 tests. | Adopt generator-based event loop pattern for clean interrupt injection points. The `yield` at each agent reasoning step is the natural steering hook. Checkpoint/rewind architecture is validated in production-grade code. |
| 245 | [ProgEnt](https://github.com/sunblaze-ucb/progent) (findings.md Line 917) | "Explicit approval gates for capability expansion. Monotonic confinement prevents silent escalation. LLM proposes, SMT solver decides. Narrowing actions auto-applied; expansion requires approval." Validated in LangChain and OpenAI Agents SDK. | Steering approval gates: narrowing actions (reducing scope) auto-approved; expansion actions (new capabilities, wider scope) require user confirmation. Minimizes steering fatigue while maintaining safety. |
| 247 | [Self-Evolving Agent Safety](https://arxiv.org/pdf/2509.26354) (findings.md Line 919) | "Fine-tuning on agent-generated data compromises alignment even from aligned base models. Safety degradation across HarmBench, SALAD-Bench." | Undo/rollback is a SAFETY mechanism, not just UX. Without reversibility, agent self-improvement (Phase 3+) will silently degrade alignment. Steering undo = safety reversibility. |
| 87 | [MOSS](https://arxiv.org/abs/2605.24220) (findings.md Line 413) | "User-consent-gated container swap with health-probe rollback. 0.25→0.61 mean grader score in single cycle." Source-level self-evolution with human consent gate. | User consent gate pattern: action proposed → user approves → executed with health probe → auto-rollback on failure. This is the safety envelope for autonomous actions. |
| Constitutional AI | Preference-based steering via natural language principles | Users state preferences in natural language; Lyra applies as constraints |
| Interruptible Agents (CHI) | Barge-in semantics: stop current action, preserve completed work, allow redirection | Implement at workflow engine level |
| Mid-task feedback (ACL/EMNLP) | Corrections during task improve outcomes more than post-hoc feedback | Capture corrections as structured feedback for current AND future runs |
| Trust calibration | Users trust appropriately when confidence is displayed AND calibrated | Integrate with §4.19 self-knowledge layer |

### 2.2 Extended Evidence

| Source | Key Finding | Transfer to Lyra |
|--------|------------|-----------------|
| Claude Code Agent View (Anthropic, 2025) | Steer-by-exception UX: agents run autonomously but surface a "peek" view where users can inspect, reply to, or attach context to any running agent | Adopt Agent View pattern for Lyra's TUI: running agents appear in a sidebar; user can select any agent to inspect/steer without stopping it |
| Identity Skews Debate (NeurIPS 2024) | Anonymizing agent identity (removing model name, confidence scores) reduces user over-trust and improves critical evaluation | In Lyra's verification mode, optionally anonymize which model produced which output — user evaluates the work, not the brand |
| Actor-Observer Asymmetry (Social Psychology → HCI) | Humans attribute their own errors to "situation" and others' errors to "disposition"; applies to how users judge agent mistakes | When Lyra makes an error, show the situational context (ambiguous instructions, missing context) alongside the error — reduces blame misattribution |
| Interactive Task Learning (AAAI 2024) | Agents that ask clarifying questions during task execution achieve 35% higher success rate than those that guess and correct | Add proactive steering prompts: "I'm about to modify the auth module — should I prioritize security review or speed?" |
| Mixed-Initiative Interaction (HCI literature) | Optimal human-AI collaboration occurs when human and AI each lead where they are strongest | Implement initiative handoff: Lyra leads on code generation, user leads on architectural decisions |

### 2.3 Design Principles Extracted

1. **Steer-by-exception, not steer-always**: The user should NOT watch every agent action; they should be alerted only when attention is needed
2. **Preserve work on interrupt**: Stopping an agent should never lose completed work — state must be serialized at interrupt points
3. **Capture why, not just what**: When a user corrects Lyra, capture the REASON, not just the instruction
4. **Trust calibrates autonomy**: More corrections → less autonomy; fewer corrections → more autonomy

---

## 3. Proposed Lyra Design

### 3.1 Interrupt/Steer/Undo State Machine

```mermaid
stateDiagram-v2
    [*] --> Running: Workflow starts
    Running --> Running: Agent completes task
    Running --> Paused: Ctrl+C / /pause
    Running --> Interrupted: /steer <instruction>
    Running --> Undoing: /undo [N]

    Paused --> Inspecting: User inspects state
    Inspecting --> Running: /resume
    Inspecting --> Interrupted: /steer while paused
    Inspecting --> Undoing: /undo while paused
    Inspecting --> Cancelled: /cancel

    Interrupted --> Steering: Capture preference
    Steering --> Rerouting: Apply to current agents
    Rerouting --> Running: Resume with new constraints
    Steering --> Learning: Store in TKG (preference)

    Undoing --> RollingBack: Identify last N mutating actions
    RollingBack --> GitRevert: File changes → git revert
    RollingBack --> StateRollback: State changes → restore checkpoint
    RollingBack --> Warning: Irreversible action detected
    Warning --> Running: User acknowledges

    Cancelled --> [*]: Workflow terminated

    note right of Interrupted: Preference captured as:<br/>{context, instruction,<br/>generalized_constraint,<br/>outcome (future)}

    note right of Undoing: Undo is partial:<br/>Git actions: reversible<br/>API calls: irreversible<br/>Sent messages: irreversible
```

### 3.2 Steering Architecture

```mermaid
graph TB
    USER[User] -->|Ctrl+C| INTERRUPT[Interrupt Handler]
    USER -->|"/steer ..."| STEER[Steering Command]
    USER -->|"/undo"| ROLLBACK[Rollback Engine]

    INTERRUPT --> PAUSE[Pause Workflow]
    INTERRUPT --> STOP[Stop Agent]
    INTERRUPT --> REDIRECT[Redirect Phase]

    STEER --> PREF[Preference Capture<br/>NL → Constraint]
    PREF --> APPLY[Apply to Current + Future]

    ROLLBACK --> GIT[Git-Based Rollback]
    ROLLBACK --> STATE[State Rollback]

    PREF --> TKG[Store in TKG]

    style INTERRUPT fill:#FFB6B6
    style PREF fill:#90EE90
```

### 3.3 Data Model (TypeScript)

The steering system requires six core data structures to enable interrupt, preference capture, rollback, and trust calibration.

```typescript
// ──── SteeringEvent: Every user steering action produces one ────
// Stored in TKG semantic tier. Retrieved by similarity matching for future runs.
interface SteeringEvent {
  id: string;                          // UUIDv7, time-ordered
  timestamp: string;                   // ISO 8601
  workflow_id: string;                 // Which workflow was running
  agent_id: string | null;             // Which agent was targeted (null = all)
  steering_type: SteeringType;

  // Context snapshot at time of steering (for preference generalization)
  context: {
    recent_actions: ActionSummary[];   // Last 10 actions before interrupt
    current_phase: string;             // Workflow phase name
    elapsed_time_ms: number;           // Time since workflow start
    agent_count: number;               // Active agents at time of steering
    mutation_count: number;            // Mutating actions in recent window
  };

  // What the user specified
  instruction: string;                 // Raw user text: "focus on auth layer"
  structured_intent: StructuredIntent; // Parsed: {action: "focus", target: "auth"}

  // Outcome (populated after workflow completes)
  outcome: {
    applied: boolean;                  // Was the steering applied?
    effect_size: number | null;        // Measured impact (0-1)
    user_satisfaction: number | null;  // Explicit or implicit (from subsequent corrections)
  };
}

type SteeringType =
  | 'pause'            // Temporarily freeze workflow
  | 'resume'           // Resume after pause
  | 'stop'             // Terminate workflow entirely
  | 'stop_agent'       // Terminate specific agent
  | 'redirect'         // Mid-run direction change
  | 'undo'             // Roll back last N actions
  | 'approve'          // Approve pending expansion action (ProgEnt pattern)
  | 'reject'           // Reject pending expansion action
  | 'priority_shift'   // Reorder task priorities
  | 'budget_change';   // Modify remaining budget

// ──── StructuredIntent: Parsed from NL steering ────
interface StructuredIntent {
  action: string;       // focus, ignore, switch_model, change_budget,
                        //   verify_more, verify_less, skip, retry
  target: string | null;
  parameters: Record<string, any>;
  scope: 'current_action' | 'current_phase' | 'entire_workflow' | 'future_runs';
  confidence: number;   // Parser confidence (0-1)
}

// ──── LearnedPreference: Stored in TKG semantic tier ────
// Retrieved by embedding similarity on future workflow startup
interface LearnedPreference {
  id: string;
  created_from_events: string[];       // SteeringEvent IDs that produced this
  trigger_context_embedding: number[]; // Embedding of context that triggered steering
  constraint: string;                  // LLM-readable: "Prioritize auth layer when..."
  scope: 'global' | 'project' | 'workflow_type';
  strength: number;                    // 0-1, reinforced by repeated steering, decays over time
  confidence: 'tentative' | 'confirmed' | 'permanent';
  // tentative: single steering event (needs confirmation)
  // confirmed: 2+ steering events OR user explicitly confirmed
  // permanent: user explicitly marked "remember this"
  last_applied: string;                // ISO 8601
  decay_half_life_days: number;       // Default 30 (AutoResearchClaw pattern)
}

// ──── RollbackPoint: AutoResearchClaw SHA256 pattern ────
interface RollbackPoint {
  id: string;
  timestamp: string;
  workflow_id: string;
  agent_id: string;

  // Git state
  git_commit: string;                  // SHA of pre-action commit

  // File state (for non-git-tracked files)
  file_snapshots: {
    path: string;
    sha256: string;                    // AutoResearchClaw pattern
    size_bytes: number;
  }[];

  // External actions (cannot be undone — user MUST be warned)
  irreversible_actions: {
    tool_name: string;
    description: string;
    external_id: string;               // API call ID, email message ID, etc.
    confirmed_by_user: boolean;        // Was user warned before execution?
  }[];

  // Metadata
  action_description: string;          // "Wrote auth middleware"
  mutation_risk: number;               // SABER-style 0-1 risk score
  rollbackable: boolean;               // CheetahClaws pattern
  parent_rollback_point: string | null;// Tree structure for parallel exploration
}

// ──── AutonomyState: Trust calibration per workflow ────
interface AutonomyState {
  workflow_id: string;
  current_level: 'supervised' | 'collaborative' | 'autonomous';

  // Rolling window metrics (last 100 decisions)
  corrections: number;
  total_decisions: number;
  correction_rate: number;             // corrections / total_decisions

  // Satisfaction-weighted metric (AI Safety reviewer resolution)
  explicit_satisfaction: number | null;// Post-workflow rating [1-5]
  satisfaction_weighted_rate: number;  // Detects learned helplessness

  // Thresholds (configurable per project)
  supervised_threshold: number;        // >0.3 → supervised mode
  collaborative_threshold: number;     // >0.1 → collaborative mode

  // Transition history with hysteresis (3-sample smoothing)
  level_changes: {
    from: string;
    to: string;
    timestamp: string;
    reason: string;
  }[];

  // Per-agent overrides
  agent_overrides: Record<string, {
    level: string;
    reason: string;
    expires_at: string;
  }>;
}

// ──── ConstraintInjection: How steering is applied to agent prompts ────
interface ConstraintInjection {
  source: 'user_steering' | 'learned_preference' | 'avp_critic' | 'safety_gate';
  constraint: string;                  // "MUST prioritize authentication layer"
  framing: 'hard' | 'soft';           // hard = "MUST", soft = "Consider"
  provider_adaptation: Record<string, string>;
  // DeepSeek: "MUST prioritize auth layer. This is a HARD constraint."
  // Claude: "As a priority, please focus on the authentication layer."
  // GPT-4o: "CRITICAL CONSTRAINT: prioritize authentication layer above all else."
  inserted_at: 'system_prompt' | 'first_user_message' | 'both';
  re_inject_on_context_shift: boolean; // DeepSeek: true, Claude: false
  max_violations_before_pause: number; // DeepSeek: 2, Claude: 3
}
```

### 3.4 Steering Commands

```
/steer focus on <topic>    — Redirect workflow to prioritize specific area
/steer ignore <topic>      — Tell workflow to skip specific area
/steer use <model>         — Switch model for remaining tasks
/steer budget <amount>     — Change budget for remaining tasks
/steer verify more/less    — Adjust verification strictness
/undo                      — Undo last mutating action
/undo <N>                  — Undo last N mutating actions
/peek <agent_id>           — Inspect a running agent's current state and thoughts
/reply <agent_id> <msg>    — Send a message to a running agent without stopping it
```

### 3.5 Preference Capture Algorithm

```
onSteer(instruction, workflowContext):
    preference = {
        type: "preference",
        trigger_context: summarize(workflowContext),  # What was happening
        instruction: instruction,                      # What user said
        outcome: None,                                 # Updated after workflow completes
        learned_constraint: generalize(instruction),   # LLM: "Generalize this to similar contexts"
    }
    tkg.store(preference, tier="semantic")
    applyToCurrentWorkflow(preference)
```

### 3.6 Trust Calibration

```
# Adjust autonomy level based on correction frequency
correctionRate = corrections / totalDecisions  # Over last 100 decisions

if correctionRate > 0.3:
    autonomyLevel = "supervised"     # Ask before every mutating action
elif correctionRate > 0.1:
    autonomyLevel = "collaborative"  # Proactive prompts on high-stakes decisions
else:
    autonomyLevel = "autonomous"     # Full auto (with AVP gating)
```

---

## 4. Build Outline — Ordered Tasks

| # | Task | Depends On | Effort | Description |
|---|------|-----------|--------|-------------|
| 1 | Wire pause/resume to UI | — | 0.5 week | Connect `WorkflowEngine.pause()` / `.resume()` to TUI keybindings; serialize state on pause via `PauseResumeSerializer`; display paused agent state in sidebar |
| 2 | Interrupt handler with state preservation | — | 0.5 week | `Ctrl+C` → graceful interrupt: finish current atomic action, serialize state, present options (resume/steer/undo/cancel). Never leave state corrupted on interrupt |
| 3 | `/steer` command with injection | #1 | 1 week | Parse natural-language steering instruction; inject as constraint into running workflow; apply to current AND queued tasks; capture as preference for future |
| 4 | `/undo` command with action classification | #1 | 1 week | Classify each completed action as `reversible` (file edits, git commits), `partially_reversible` (DB writes with rollback), or `irreversible` (API calls, sent messages); git-based rollback for reversible; state checkpoint restore for partially reversible; warn for irreversible |
| 5 | Preference capture and storage | #3 | 1 week | On each `/steer`: capture (context, instruction, generalized_constraint) as structured preference in TKG; after workflow completes, record outcome for future matching |
| 6 | Trust calibration with autonomy gating | #5 | 0.5 week | Track `correctionRate` over sliding window of 100 decisions; map to autonomy level (supervised/collaborative/autonomous); adjust agent behavior accordingly (ask-before-act vs. full-auto) |

**Critical path**: #1 → #3 → #5 → #6 (pause wiring → steer → preference capture → trust calibration). #2 and #4 can run in parallel with the main chain.

---

## 5. Multi-Provider Steering Behavior

### 5.1 Instruction Following Varies by Provider

| Provider | Instruction Following Quality | Steering Reliability | Notes |
|----------|------------------------------|---------------------|-------|
| Anthropic (Claude) | Excellent | High | Steer instructions reliably followed; constraint injection works well |
| OpenAI (GPT-4o) | Very Good | High | Slightly more likely to "helpfully" override constraints |
| Google (Gemini) | Good | Medium | Occasional constraint drift in long contexts |
| DeepSeek | Moderate | Medium-Low | May partially ignore constraints after context shift; need re-injection |
| Open-Weight (Llama, etc.) | Variable | Low-Medium | Constraint adherence depends heavily on model size and fine-tuning |

### 5.2 Provider-Specific Steering Strategies

- **Claude/Anthropic**: Steering is natural — inject constraint once, trust it holds. Use `system` message for constraint injection
- **OpenAI**: Re-inject constraint at context window boundaries; verify constraint adherence after major context shifts
- **Gemini/Google**: Use structured output format for constraints; avoid ambiguity
- **DeepSeek**: Inject constraint in BOTH system prompt AND first user message; verify before each mutating action
- **Local models**: Run a lightweight constraint-verification step before each action; if constraint is violated, re-inject with stronger emphasis

### 5.3 Cross-Provider Steering

- Steering commands are harness-level (not model-level) — the preference capture system works identically across all providers
- Preference generalization quality varies: Claude produces better generalizations than DeepSeek
- For workflows using multiple providers, constraints are translated to provider-optimal format by `ConstraintAdapter`

---

## 6. (B) Breakthrough — Natural-Language Steering with Preference Learning

### 6.1 The Insight

Current steering in AI tools is crude: you can stop or restart, but cannot say "actually, use a factory pattern instead of a builder" and have the agent adapt without losing progress. The breakthrough is treating steering as a *preference learning problem*: each correction is a training signal that improves the agent's model of what you want.

### 6.2 Position in the BREAKTHROUGH-ARCHITECTURE.md

This workstream directly instantiates the converged architecture from [BREAKTHROUGH-ARCHITECTURE.md](../BREAKTHROUGH-ARCHITECTURE.md), which is the winner of a multi-agent adversarial debate (3 proposers, 3 critics, 13-dimension trade-off analysis). Human Steering touches every layer of the converged design:

| Architecture Layer | Steering Integration | BREAKTHROUGH-ARCHITECTURE.md Reference |
|-------------------|---------------------|--------------------------------------|
| **Memory (TKG)** | Preference events stored in TKG semantic tier; A-MAC 5-factor admission control (#79) applied to preference admission; LearnedPreferences retrieved by embedding similarity using A-MEM Zettelkasten linking (#59) | §1: TKG as primary memory (Candidate A win); §0: "TKG stores verification records; verification gates memory writes" |
| **Workflow Engine** | Pause/resume/redirect hooks in Dynamic Workflow Engine; generator-based event loop for clean interrupt injection; PauseResumeSerializer integration | §1: "Workflow engine for orchestration (code-driven, background, resumable)" from Candidate B; §0a: Claude Code Dynamic Workflows (#203, #349) as design source |
| **AVP Middleware** | Steering events feed into verification context; high-correction agents get stricter AVP gating; critic identity anonymization (N3 Identity Skews) prevents user bias toward specific models | §1: AVP as universal middleware — "Critique-before-execute is a protocol every tool, skill, and agent passes through"; §0: Provider-diverse critics (Claude + DeepSeek + open-weight) |
| **Router** | Provider-aware steering: NL intent parsing routes to Claude (best accuracy); constraint framing adapted per provider; TF-TTCL Explore-Reflect-Steer loop for black-box providers | §1: Router as "Intelligence Distributor" — "Provider abstraction as first-class architectural concern"; §0a: RouteLLM matrix factorization (#222) |
| **Skills** | TF-TTCL N23 pattern: multi-agent trajectories → contrastive rule extraction → rules injected as context. Works on ANY provider, no weight access needed. | §1: Skills as "Capability Layer, Self-Evolving in Phase 3+"; §0: Self-evolution deferred to Phase 3+ (gated) |
| **Swarm** | Per-agent steering in parallel; AVP panel lock during steering deliberation; GTD N6 topology adaptation for steering-heavy workflows | §1: Swarm as "Adversarial Coordination Fabric" |
| **Safety** | ProgEnt monotonic confinement: narrowing actions auto-approved, expansion requires user confirmation; CaMeL control/data separation; self-evolving agent safety rollback (#247) | §1: CaMeL control/data separation (#243) → safety layer; §Safety: "Progent SMT gates + auto-rollback on violation" |

### 6.3 What Makes This a Breakthrough (Not Just Parity)

The BREAKTHROUGH-ARCHITECTURE.md identifies five novel contributions (§0a, Lines 65-70). Human Steering directly enables Novelty #4 (**"Self-evolution deferred, not rejected"**) and Novelty #1 (**"Memory + Verification fusion"**):

1. **Memory + Verification fusion (Novelty #1)**: Steering preferences stored in TKG; AVP verification uses preference history to weight critic agreement. If a user previously steered away from approach X, AVP critiques that mention X get amplified. This is a closed loop: user feedback → memory → verification → safer execution.

2. **Provider-adaptive everything (Novelty #2)**: Steering intent parsing and preference generalization route to optimal provider per task. DeepSeek workflows get harder constraint framing. This is NOT a feature — it is a first-class architectural concern that no other harness implements.

3. **Adversarial verification as universal middleware (Novelty #3)**: Before executing a mutating action, the AVP check now includes: "Has the user previously steered away from this pattern?" This makes verification personal, not just statistical. Each user's steering history is a personalized verification context.

4. **Self-evolution deferred, not rejected (Novelty #4)**: Steering events ARE the behavioral safety signal. When correction rate is low and stable, the autonomy gate opens. When it rises, the gate closes. This IS the "behavioral safety benchmark" that gates Phase 3+ evolution. The 10K execution history threshold includes both automated and steering-informed executions.

### 6.4 Integration with Breakthrough Safety Mechanisms

From [BREAKTHROUGH-ARCHITECTURE.md](../BREAKTHROUGH-ARCHITECTURE.md) §Safety:

- **EvolveMem auto-rollback on recall degradation >2%** (BREAKTHROUGH-ARCHITECTURE.md Line 1748): "4-8% of evolutionary updates cause recall degradation. The 2% threshold is deliberately conservative." Steering undo follows the same pattern — if a steering-induced change degrades outcome, auto-rollback the learned preference.

- **Progent SMT gates + auto-rollback on violation** (BREAKTHROUGH-ARCHITECTURE.md Line 627): Steering approval gates use the same monotonic confinement — narrowing auto-approved, expansion requires user. The LLM proposes, the SMT solver decides, and the user is only involved for capability expansion.

- **Self-evolution alignment decay** (BREAKTHROUGH-ARCHITECTURE.md Line 627): Risk classified as "Medium probability, Critical impact." Mitigation: "Progent SMT gates + auto-rollback on violation." Steering directly implements this mitigation.

### 6.5 Mechanism

```
Phase 1 — Immediate (current workflow):
  User: "/steer use factory pattern, not builder"
  → Lyra: Detects the affected task (the one that chose builder)
  → Lyra: Undoes only the builder-related work, preserves everything else
  → Lyra: Re-routes the task with constraint: "MUST use factory pattern"

Phase 2 — Learned (future workflows):
  → TKG stores: {context: "design pattern selection for object creation",
                  preference: "factory > builder",
                  generalizes_to: ["abstract factory", "simple factory"]}
  → Next workflow that involves object creation:
  → Auto-injects: "User prefers factory pattern for object creation (learned from prior steering)"

Phase 3 — Proactive (before user needs to steer):
  → Trust calibration detects correctionRate < 0.05 (rarely corrected)
  → Before making a design pattern choice, Lyra proactively asks:
    "I'll use factory pattern here (your preference) — OK?"
  → User confirms or redirects; either way, Lyra learned
```

### 6.6 Preference Generalization

```
function generalizePreference(instruction: str, context: str) -> Constraint:
    prompt = f"""
    The user gave this steering instruction in this context:
    
    Context: {context}
    Instruction: {instruction}
    
    Generalize this into a reusable constraint. Consider:
    - What principle does this preference express?
    - What similar situations would it apply to?
    - Are there exceptions where it should NOT apply?
    
    Output:
    constraint: <1-sentence reusable rule>
    applies_when: <description of triggering conditions>
    exceptions: <description of when NOT to apply>
    confidence: <0.0-1.0 how confident you are in the generalization>
    """
    return llm(prompt)
```

---

## 7. Expert Review

| Reviewer | Verdict | Key Objection | Resolution |
|----------|---------|---------------|------------|
| Senior UX Designer | ✅ Sign off | "Steering must be discoverable — users won't read docs for `/steer`" | Show hints in progress view footer; `/peek` reveals the steering bar on first use |
| Senior SRE | ✅ Sign off | "Undo on production is terrifying — need dry-run mode" | Add `--dry-run` for mutating workflows; show undo preview before executing |
| Senior Product Manager | ✅ Sign off | "Trust calibration is clever but what if the user doesn't WANT to steer? Some users want low autonomy by default, not earned autonomy" | Add `autonomy_mode` setting: "earned" (calibrated, default), "supervised" (always ask), "autonomous" (never ask, expert mode) |
| Adversarial Skeptic | ⚠️ Conditional | "Preference learning from a single correction is dangerous — the user might have been wrong, tired, or making a one-off exception. Generalizing a one-time correction to a permanent constraint creates phantom rules" | Require confidence threshold for generalization: only promote to permanent constraint if the preference is confirmed across 2+ steering events OR the user explicitly confirms "remember this"; mark single-event generalizations as "tentative" |

---

## 8. Risks & Open Questions

| Risk | Mitigation |
|------|-----------|
| Undo is incomplete (can't undo external API calls, sent emails) | Mark irreversible actions; require explicit confirmation before executing; show "undo available: partial" with clear description of what CAN and CANNOT be undone |
| Preference overfitting (learned constraint too specific) | LLM-based generalization: "Generalize this preference to similar contexts"; rank generalizations by confidence; only apply high-confidence generalizations |
| User doesn't steer (learned helplessness) | Proactive prompts: "I'm about to audit encryption — prioritize any area?"; show steering hints in footer during first 5 sessions |
| Steering during critical path corrupts workflow | Checkpoint workflow state before applying steering; if steering causes errors, auto-rollback to checkpoint with explanation |
| Multiple users steering same workflow | Lock steering to session owner; if multiple users have access, show "Currently steered by @alice" in UI; queue other steering requests |

---

## 9. References

### 9.1 Primary Sources (from findings.md with Row Numbers)

| Row | Source | Link | Key Evidence |
|-----|--------|------|-------------|
| 67 | SABER mutation-gating | (findings.md Lines 35-45) | 55-96% error impact from mutating deviations; ~92% error catch rate at 20-30% verification cost |
| 87 | MOSS source-level self-evolution | [arXiv:2605.24220](https://arxiv.org/abs/2605.24220) | User-consent-gated container swap; health-probe rollback |
| 118 | AutoResearchClaw 7-mode HITL | [arXiv:2605.20025](https://arxiv.org/abs/2605.20025) | 3 human gates (Stages 5, 9, 20); beats full autonomy by 54.7% |
| 162 | Karpathy Skills — declarative steering | [GitHub](https://github.com/multica-ai/andrej-karpathy-skills) | "Surgical diff discipline as built-in constraint" |
| 167 | CheetahClaws — checkpoint/rewind | [GitHub](https://github.com/SafeRL-Lab/cheetahclaws) | Generator-based event loop; 2,347 tests; 8+ providers |
| 245 | ProgEnt — approval gates | [GitHub](https://github.com/sunblaze-ucb/progent) | Monotonic confinement; SMT-based narrowing/expansion classification |
| 247 | Self-Evolving Agent Safety | [arXiv:2509.26354](https://arxiv.org/pdf/2509.26354) | Alignment decay from self-generated data; reversibility as safety |
| N3 | When Identity Skews Debate | [arXiv:2510.07517](https://arxiv.org/abs/2510.07517) | Response anonymization reduces identity bias; sycophancy dominates self-bias |
| N5 | Latent Agents — negative steering | [arXiv:2604.24881](https://arxiv.org/abs/2604.24881) | Activation-space steering; 93% token savings vs explicit debate |
| N23 | TF-TTCL — Explore-Reflect-Steer | [arXiv:2604.13552](https://arxiv.org/abs/2604.13552) | Preference learning without weight access via contrastive distillation |
| 8 | Full-Duplex-Bench v1 | [arXiv:2503.04721](https://arxiv.org/abs/2503.04721) | Systematic evaluation of pause/backchannel/turn-taking/interruption |
| 9 | Full-Duplex-Bench v3 | [arXiv:2604.04847](https://arxiv.org/abs/2604.04847) | Real disfluent audio; GPT-Realtime 0.600 Pass@1, 13.5% interruption |

### 9.2 Architecture References

- [BREAKTHROUGH-ARCHITECTURE.md](../BREAKTHROUGH-ARCHITECTURE.md) — Full converged architecture (Memory + Verification fusion, 5-layer stack)
- [ARCHITECTURE-DEBATE.md](../ARCHITECTURE-DEBATE.md) — Multi-agent adversarial design debate (3 proposers, 3 critics)
- §4.19 Self-Knowledge — Confidence display and calibration integration
- §4.17 Safety — ProgEnt integration, CaMeL control/data separation
- §4.10 Sessions & Checkpointing — State serialization and rollback persistence
- §4.13 Voice — Full-duplex voice barge-in and interruption handling
- §4.15 Reliability/Verification — Automated error recovery (complement to human steering)
- §4.18 Multi-Tenancy — Multi-user steering (deferred to Phase 2+)

### 9.3 Related Lyra Packages

| Package | Role | Integration Point |
|---------|------|------------------|
| `lyra-human-interaction` | Existing interaction layer (pause/resume, keybindings) | HS-01: Wire pause/resume to UI |
| `lyra-personalization` | User preference and personality management | HS-11: Auto-inject constraints from LearnedPreferences |
| `lyra-workflow` | Dynamic Workflow Engine with `PauseResumeSerializer` | HS-02: SIGINT handler + state serialization |
| Lyra TKG | Temporal Knowledge Graph (semantic tier) | HS-09: SteeringEvent storage; HS-10: Preference retrieval |

### 9.4 External References

- Constitutional AI (Anthropic) — Preference-based steering via natural language principles
- Interruptible agents (CHI/ACL literature) — Barge-in semantics for agent systems
- Claude Code Agent View (Anthropic, 2025) — Steer-by-exception UX pattern
- Interactive Task Learning (AAAI 2024) — Agents that ask clarifying questions achieve 35% higher success
- Mixed-Initiative Interaction (HCI literature) — Optimal human-AI collaboration with dynamic initiative handoff
- Actor-Observer Asymmetry (Jones & Nisbett, 1971) — Human attribution bias applied to agent error judgment

---

## 10. Deep Mechanism — Agent View Interrupt/Redirect/Approve Patterns

This section provides a code-level deep dive into the interrupt, redirect, and approve mechanisms as implemented in Claude Code's Agent View architecture (codename "nO" master loop), adapted for Lyra's multi-agent workflow engine.

### 10.1 The nO Master Loop — Foundation for All Steering

Claude Code's agent loop (internally codenamed "nO") is an `async generator` that iterates as long as the model produces tool calls. Plain text responses terminate the loop and return control to the user. This single-threaded design is deliberate: it prioritizes debuggability, transparency, and reliability over complex orchestration.

**Lyra adaptation**: Replace the generator with the existing Dynamic Workflow Engine's generator-based event loop (CheetahClaws pattern, §2.1 row 167). Each iteration of the loop represents one atomic reasoning step, which is the natural interrupt injection point.

```
async function* nO_loop(session, signal):
    while not signal.aborted:
        step = await model.generate(session.messages, {signal})
        if step.type == "text":
            yield {type: "response", text: step.text}
            return
        elif step.type == "tool_call":
            yield {type: "tool_call", tool: step.tool}
            result = await execute_tool(step.tool, signal)
            session.messages.push({role: "tool", content: result})
            yield {type: "tool_result", result: result}
```

### 10.2 Soft Steering — The h2A Async Queue Pattern

Soft steering (redirect without stopping) uses an async dual-buffer message queue internally called h2A:

1. User types `/steer focus on auth` --> message enters h2A queue
2. Scheduler `kq5` processes messages FIFO
3. A state lock (`isExecuting`) ensures atomicity -- only one task group runs at a time
4. New commands queue and execute AFTER current atomic action completes
5. No interruption of mid-execution state -- preserves work in progress

Key property: **soft steering is non-preemptive**. The user's instruction is guaranteed to be applied, but not immediately. This prevents state corruption from mid-action redirects.

**Lyra adaptation**: Replace h2A with Lyra's existing message bus. Steering commands are enqueued as high-priority workflow messages. The `isExecuting` lock maps to Lyra's `PauseResumeSerializer` critical section demarcation.

### 10.3 Hard Interrupt — The AbortController Pattern

Hard interrupt (barge-in, emergency stop) uses a propagated `AbortController`:

1. ESC key or `/cancel` creates an `AbortController` with `AbortSignal`
2. Signal is propagated to ALL sub-processes: main loop, model API calls, tool execution
3. Multiple checkpoints `if (signal.aborted)` are embedded throughout the execution pipeline
4. Sub-agents inherit the parent's AbortSignal -- killing parent kills all children
5. State is serialized at the LAST completed checkpoint (not mid-action)

Key property: **hard interrupt IS preemptive but graceful**. The AbortSignal is checked at yield points, not between individual CPU instructions. This means a tool call in-flight may complete before the interrupt is recognized, but no new tool call starts.

```
function createInterruptSystem():
    controller = new AbortController()
    signal = controller.signal

    # Checkpoints embedded at:
    # 1. Before each model.generate() call
    # 2. Before each tool execution
    # 3. After each tool result is received
    # 4. Between sub-agent dispatches

    handler = {
        barge_in: () => controller.abort(),
        is_aborted: () => signal.aborted,
        throw_if_aborted: () => { if signal.aborted throw "INTERRUPTED" }
    }
    return handler
```

### 10.4 Approve Pattern — ProgEnt Monotonic Confinement Applied

The approval mechanism combines Claude Code's permission system with ProgEnt's monotonic confinement (§2.1 row 245):

**Action classification** (at each mutating action boundary):
1. Extract action parameters: tools called, files modified, API targets
2. Classify as `narrowing` (scope-reducing: lower budget, fewer agents, faster model) or `expansion` (scope-increasing: new tools, wider file access, higher cost)
3. Narrowing actions: auto-approved, execute immediately
4. Expansion actions: queued for user approval, presented in peek panel with diff preview
5. User response: approve (execute) or reject (skip) or modify (steer with adjusted parameters)

**Permission system layered safety controls** (from Claude Code MH1 engine):
- Layer 1 -- Input validation: strict validation of all user inputs and tool parameters
- Layer 2 -- Tool permissions: explicit allow/deny for write operations, risky Bash, external tools
- Layer 3 -- Execution sandbox: sandboxed/restricted environments for dangerous operations
- Layer 4 -- Execution monitoring: AbortController prevents hangs/resource exhaustion
- Layer 5 -- Error recovery: exception classification with auto-retry or graceful degradation
- Layer 6 -- Audit logging: full audit trail for compliance and debugging

Lyra's approve pattern layers the ProgEnt SMT-based classification on top of the existing AVP critique system. An action must pass BOTH AVP critic consensus AND the steering approval gate before execution.

### 10.5 Sub-Agent Steering Isolation

Claude Code's sub-agents have `enableSteering = false` -- they cannot receive new user instructions mid-task. However, they can be hard-interrupted via the parent's AbortSignal.

**Lyra adaptation**: Lyra's parallel agents will have configurable `steering_mode`:
- `inherited` (default): sub-agent listens to parent's steering commands
- `locked`: sub-agent ignores all steering until current task completes (Claude Code default)
- `bypass`: sub-agent can be directly steered by user (reserved for critical-path agents)

### 10.6 Context Compression on Interrupt

When a hard interrupt occurs, Claude Code's `wU2` compressor triggers:
- 8-section structured summary: background, decisions, tool usage, user intent, results, errors, unresolved issues, next plans
- ~78% compression ratio, saving ~4,000-6,000 tokens per compression
- Triggered at ~92% context threshold OR on interrupt

Lyra's interrupt handler MUST invoke the compression layer before serializing state. This ensures that resume after interrupt preserves semantic context, not just raw message history.

---

## 11. Performance Benchmarks & Latency Targets

### 11.1 Interrupt Handling Latency

| Metric | Target (Lyra) | Measured (Claude Code) | Source |
|--------|----------------|----------------------|--------|
| Soft steer enqueue-to-apply | **<500ms** | ~200ms (h2A queue) | Agent View architecture |
| Hard interrupt (barge-in) | **<200ms** | ~50-150ms (AbortController) | Claude Code MH1 engine |
| Hard interrupt (sub-agent) | **<500ms** | ~200-400ms (signal propagation) | Sub-agent isolation analysis |
| Ctrl+C graceful shutdown | **<1s** | ~800ms (state serialization) | Industry best practice |
| Cancel --> state serialized | **<2s** | ~1.5s (wU2 compression + persist) | Agent View context management |
| Resume after interrupt | **<3s** | ~2-3s (deserialize + context restore) | Session resume benchmarks |

### 11.2 Steering UX Response Times

| Interaction | Target (Lyra) | Measured (Claude Code) | Notes |
|-------------|----------------|----------------------|-------|
| `/peek` panel open | **<100ms** | ~50ms | Pure UI rendering, no model call |
| `/peek` with status refresh | **<500ms** | ~200ms | Includes Haiku-generated summary (refreshed <=15s) |
| Suggested reply generation | **<800ms** | ~400-600ms | Lightweight model inference + UI render |
| Attach (enter session) | **<300ms** | ~100ms | State switch, no model call |
| Detach (return to dashboard) | **<200ms** | ~50ms | Navigation only |
| `/steer` parse + inject | **<2s** | ~1-1.5s | NL parsing + constraint formatting + prompt injection |
| `/undo` last action | **<5s** | N/A (not in Claude Code) | Git rollback + state restore (depends on action size) |
| Approval gate popup | **<200ms** | ~100ms | Classification (narrowing vs expansion) is near-instant |
| Approval decision apply | **<1s** | ~500ms | Execute or reject the queued action |

### 11.3 Autonomous Session Duration Benchmarks

From Anthropic's published telemetry (Oct 2025 -- Jan 2026):

| Metric | Oct 2025 | Jan 2026 | Trend |
|--------|----------|----------|-------|
| P99.9 session duration (autonomous) | ~25 min | **>45 min** | +80% -- trust increases |
| Median session duration | ~45s | ~45s | Unchanged (short tasks stay short) |
| Auto-approve mode (novice users) | ~20% | ~20% | Flat -- novices remain cautious |
| Auto-approve mode (veterans, 750+ sessions) | -- | **>40%** | Trust builds with experience |
| Human interrupt rate (novices) | ~5% of turns | ~5% | Flat |
| Human interrupt rate (veterans) | ~9% of turns | ~9% | Veterans monitor MORE, not less |
| Claude-initiated pauses (complex tasks) | -- | **>2x human interrupts** | Model proactively requests steering |

**Key insight for Lyra**: The data shows that as users gain experience, they shift from *micromanaging* to *monitoring*. They use auto-approve more (doubled to 40%) AND they interrupt more (9% vs 5%) -- they are not checking out, they are checking in at higher-leverage moments. This validates the steer-by-exception design principle.

### 11.4 Provider-Specific Latency for Steering Operations

| Provider | Model Call Latency (P50) | Steer Inject Latency | Notes |
|----------|------------------------|---------------------|-------|
| Anthropic Claude | ~1.2s | +200ms | Fastest constraint injection |
| OpenAI GPT-4o | ~1.5s | +400ms | Re-injection may be needed at context boundaries |
| Google Gemini | ~2.0s | +500ms | Structured output format adds overhead |
| DeepSeek | ~2.5s | +600ms | Dual injection (system + user message) required |
| Open-weight (local) | ~3-8s | +1-2s | Constraint verification step adds significant latency |

### 11.5 Context Window Cost of Steering

Steering operations consume context tokens. These are estimated per steering event:

| Operation | Token Cost | Notes |
|-----------|-----------|-------|
| `/steer` soft redirect | ~200-400 tokens | Constraint injection into system prompt |
| `/peek` + reply | ~500-1000 tokens | Reply appended to session transcript |
| Hard interrupt + state save | ~4000-6000 tokens | wU2 compression output |
| Learned preference injection | ~100-300 tokens | Compact constraint string |
| Full undo with rollback | ~0 tokens (offline) | No context impact -- happens outside model |
| Approval gate prompt | ~50-100 tokens | Classification overhead only |

---

## 12. Algorithm Specifications

### 12.1 Peek Panel Rendering Algorithm

```
Algorithm: RenderPeekPanel
Input: agentList (list of running agents with state)
Output: rendered peek panel UI with per-agent summaries

1. For each agent in agentList:
   a. Compute status: inspect agent.state_transition
      - If waiting_for_user --> status = "needs_input", icon = yellow
      - If executing_tool --> status = "working", icon = animated
      - If completed --> status = "completed", icon = green
      - If error --> status = "failed", icon = red
   b. Check cache for summary_line:
      - If cached_summary exists AND (now - cached_at) < 15s
        AND (state unchanged since cached_at):
           summary = cached_summary
        Else:
           - Extract last 2 assistant messages and last 4 tool results
             from transcript tail
           - Call Haiku-class model with: "Summarize in 1 line what
             this agent is doing/needs"
           - Cache result with timestamp
           - summary = result
   c. Format row:
      - Left: [icon] [agent_name] (truncate to 20 chars if needed)
      - Right: [elapsed_time] [status_label]
      - Body: summary (truncate to 60 chars with ellipsis)
   d. If agent.pending_approval exists:
      - Append approval line: "Expansion: [action_description]"
      - Show numbered options: "[1] Approve  [2] Reject  [3] Modify"

2. Compute layout:
   a. Total available_height = terminal_height - header_height - footer_height
   b. Per-agent_row_height = 3 lines (status + summary + padding)
   c. Max_visible_agents = floor(available_height / per-agent_row_height)
   d. If agent_count > max_visible_agents:
      - Show first (max_visible_agents - 1) agents + "... +N more"
      - Sort: needs_input > working > completed > failed

3. Render:
   a. Header: "Agent View -- [N] agents active  |  [H] help  |  [Q] quit"
   b. Rows: each agent as formatted above
   c. Footer: "> Type prompt to dispatch new agent  |  Tab to focus list"

4. On selection_change (up/down arrow):
   a. Update cursor position
   b. If selected agent has pending_approval: show approval action bar
   c. If selected agent.status == "needs_input": show reply textarea

5. On space press (peek open):
   a. Switch to peek panel view for selected agent
   b. Show last 8 transcript entries (scrollable)
   c. Show reply input at bottom
   d. If agent has suggested_replies: show as numbered buttons

Performance requirements:
- Full render: <100ms (no model calls in critical path)
- Summary refresh: background task, <=15s interval
- Selection change: <16ms (60fps target for smooth scrolling)
```

### 12.2 Suggested-Reply Generation Algorithm

```
Algorithm: GenerateSuggestedReplies
Input: agent (running agent with latest transcript tail)
       transcriptTail (last 6 messages: up to 2 assistant + up to 4 tool results)
Output: suggestedReplies (list of 3-4 suggested reply strings)

1. Classify the agent's current blocking state:
   a. Parse last message for question markers: ?, "which", "should I",
        "can I", "prefer"
   b. If message contains 2+ options (numbered list, bullet list):
        state_type = "multiple_choice"
   c. Else if message contains a single question with yes/no framing:
        state_type = "binary_choice"
   d. Else if agent is waiting for approval (expansion action detected):
        state_type = "approval_request"
        Extract: action_description, target_files, estimated_impact
   e. Else if agent is reporting status without explicit question:
        state_type = "status_update"
   f. Else:
        state_type = "general_input"

2. Generate replies based on state_type:

   If state_type == "multiple_choice":
      - Extract each option label from the message
      - For each option up to 4:
           suggestedReplies.push(option_label)
      - Add "None of the above -- let me specify" as final option
      - Return suggestedReplies as numbered list with action_keys

   If state_type == "binary_choice":
      - Generate "Yes, proceed" and "No, stop" as base replies
      - Add "Tell me more about the trade-offs first" as third option
      - Return 3 suggestions

   If state_type == "approval_request":
      - Generate "Approve" -- simple approval
      - Generate "Approve with higher budget" -- approval with modified params
      - Generate "Reject -- skip this action"
      - Generate "Reject and pause -- I want to discuss alternatives"
      - Return 4 suggestions

   If state_type == "status_update":
      - Generate "Continue working" -- tacit approval
      - Generate "Pause and show me what you have done so far"
      - Generate "Switch direction" -- triggers /steer flow
      - Return 3 suggestions

   If state_type == "general_input":
      - Call lightweight model (Haiku-class) with prompt:
           "Given this agent conversation tail, suggest 3-4 short replies
            the user might want to send next. Keep each under 40 chars.
            Cover: continue, redirect, and ask-for-info patterns."
      - Parse model output, extract suggestion list
      - Limit to 4 suggestions, truncate each to 60 chars

3. Render:
   a. Display as footer bar: "[1] suggestion1  [2] suggestion2  ..."
   b. Tab key fills the input with first suggestion
   c. Number key sends the suggestion immediately

Performance requirements:
- Binary/multiple_choice/approval classification: <50ms (pattern match, no model call)
- Haiku call for general_input: <800ms (small model, short context)
- Total end-to-end: <1s for all cases
```

### 12.3 Attach/Detach Flow Algorithm

```
Algorithm: AttachDetachFlow
Input: currentView (enum: "dashboard" | "session" | "peek")
       userInput (keydown or typed command)
Output: updated view state and context

State machine transitions:

  Dashboard View (agent list, summaries, dispatch)
      |
      |-- Enter/rightarrow on row --> Session View (full chat)
      |-- Leftarrow on empty input --> Detach -- return to shell
      |-- Space on row --> Peek Panel (overlay, not full switch)

  Session View
      |-- Leftarrow on empty input --> Dashboard (detach)

  Peek Panel (overlay)
      |-- Tab --> fill input with suggested reply
      |-- Enter --> send reply (stays in peek)
      |-- Esc --> close peek, return to dashboard
      |-- Ctrl+X on row --> stop agent, confirm, update dashboard

Algorithm:

1. On right_arrow or Enter press (attach):
   a. If in dashboard AND a row is selected:
      - Save dashboard scroll_position and cursor_state
      - Switch view state to "session"
      - Load full transcript for selected agent
      - Render full chat view with input prompt
      - Set agent_state.is_attached = true
   b. Transition time target: <300ms
   c. Attach establishes a context binding:
      - All further typed input goes to this agent, not the dashboard
      - Permission checks route through this agent's config
      - AbortSignal is scoped to this agent

2. On left_arrow press (detach):
   a. If in session view AND input is empty:
      - Save session context to cache (scroll position, unread messages)
      - Switch view state to "dashboard"
      - Restore dashboard scroll_position and cursor_state
      - Set agent_state.is_attached = false
   b. If in session view AND input is NOT empty:
      - Clear input first (left_arrow removes character)
      - On second left_arrow with empty input: detach
   c. Transition time target: <200ms
   d. Detach does NOT stop the agent -- it continues running in background

3. On space press (peek):
   a. If in dashboard AND a row is selected:
      - Overlay peek panel (does not switch full view)
      - Fetch latest transcript tail (last 8 entries cached)
      - Show reply input bar
      - If agent has pending_approval: show approval action buttons
   b. On Esc: close peek, return to dashboard
   c. On Enter with text: send reply, refresh peek content
   d. Transition time target: <100ms

4. On Tab press (suggested reply):
   a. If in peek panel OR session view:
      - Generate suggested replies (Algorithm 12.2)
      - Fill input with first suggestion text
      - Tab again cycles through suggestions
      - Enter sends the filled suggestion

5. Error handling:
   a. If agent process has exited mid-attach:
      - Show "[agent_name] (completed)" in session view header
      - Allow read-only browsing of transcript
      - Input shows "Session ended. Press leftarrow to return."
   b. If agent_state.json is corrupted on attach:
      - Log error: "Session state corrupted for {agent_id}"
      - Fall back to displaying last known transcript snapshot
      - Show warning in session header
      - Allow resume only if checkpoint exists

6. Supervisor integration (for background sessions):
   a. On attach to background session:
      - Verify supervisor daemon is running
        (check .claude/daemon/roster.json)
      - If daemon not running: show "Starting supervisor..."
      - Reconnect to session via supervisor IPC
   b. On detach from background session:
      - Notify supervisor: "session {id} detached, continue running"
      - Supervisor persists state to .claude/jobs/{id}/state.json
```

---

## 13. Trade-Off Analysis -- Steering Cost vs Full Autonomy

### 13.1 Cost Dimensions

| Dimension | Full Autonomy Cost | Steering Cost | Net Difference |
|-----------|-------------------|---------------|----------------|
| **Cognitive load** (user) | None (zero interaction) | Low-Medium (occasional decisions) | Steering costs 2-5 min/day of user attention |
| **Cognitive load** (system) | Maximum (AVP must catch all errors) | Reduced (user catches edge cases) | Steering saves ~20-30% of AVP compute |
| **Throughput** (wall clock) | Fastest (no waits) | Slowed by user response latency | Steering adds ~8-15% to workflow time |
| **Safety** (error rate) | Higher (8% AVP miss rate) | Lower (user catches 60-80% of AVP misses) | Steering reduces critical errors by ~5-7 percentage points |
| **Context cost** | Lower (no steering events) | Higher (+200-400 tokens per steer) | ~2-5% context overhead per workflow |
| **Development complexity** | Lower | Higher (~3x more code for interrupt system) | Steering adds ~2-3 weeks to initial build |
| **User trust** | Lower at first, grows over time | Higher initially, grows faster | Steering accelerates trust-building by ~2x |

### 13.2 When Each Mode Wins

**Full autonomy wins when:**
- Task is well-scoped with clear success criteria
- AVP gating provides sufficient safety (non-mutating actions, readonly operations)
- User is absent or multitasking (overnight runs, batch processing)
- Task risk is low (cosmetic changes, documentation, refactoring with tests)
- User has 100+ successful interactions (veteran trust pattern)

**Steering wins when:**
- Task involves architectural decisions (factory vs builder pattern)
- Task touches production systems (mutating actions on critical paths)
- Task scope is ambiguous or user's intent is evolving
- User has <20 successful interactions (novice calibration period)
- Correction rate exceeds 10% (trust calibration kicks in)

### 13.3 Quantified Trade-Off Model

```
Score = throughput_benefit + safety_benefit - cognitive_cost

Where:
  throughput_benefit = baseline_time * (1 - 0.15 * steering_fraction)
    # Each steering intervention adds ~2min of user time on average
    # 15% steering fraction --> ~30% throughput loss

  safety_benefit = error_rate_autonomous - error_rate_steering
    # Autonomous: 8% of AVP-missed errors reach user (0.64% of all actions)
    # Steering: user catches 70% of those (0.19% of all actions)
    # Net safety benefit of steering: 0.45 percentage points

  cognitive_cost = steering_fraction * attention_drain
    # Each steering event demands 15-30s of user context-switching
    # >20% steering fraction --> user fatigue, leading to worse decisions

Break-even point: steering_fraction ~= 15-20%
  Below 15%: steering provides safety benefit at acceptable cognitive cost
  Above 20%: user fatigue degrades steering quality, autonomy should increase
```

### 13.4 The Trust Curve Model

```
Phase 1 -- Supervised (day 1-7, ~50 decisions):
  Steering fraction: 25-40%
  Cost: High (user is actively learning the system)
  Benefit: Very high safety (catches 90%+ of AVP misses)
  -->

Phase 2 -- Collaborative (week 2-4, ~200 decisions):
  Steering fraction: 10-20%
  Cost: Moderate (user is comfortable but vigilant)
  Benefit: High safety (catches 70-80% of AVP misses)
  -->

Phase 3 -- Autonomous (month 2+, 500+ decisions):
  Steering fraction: 3-8%
  Cost: Low (user checks in at high-leverage moments)
  Benefit: Moderate safety (catches 50-60% of AVP misses,
           but misses are rarer)

The trust curve is NOT monotonic -- a single high-impact failure can
reset trust back to Phase 1. Lyra must detect trust resets (sudden
spike in steering events after a period of low steering) and proactively
offer supervised mode.
```

### 13.5 Steering Fatigue Mitigation

From HCI literature and Claude Code telemetry:

| Fatigue Signal | Detection | Mitigation |
|---------------|-----------|------------|
| Increasing response time to steering prompts | Time-to-respond >30s for 3 consecutive events | Reduce steering frequency; batch pending decisions |
| Abandoned steering (user sees prompt, closes without acting) | Peek panel opened then closed without reply | Escalate via notification (desktop/mobile); or auto-decide after timeout |
| Pattern of "approve all" without reading | Approval time <2s for 5 consecutive events | Flag to user: "You are approving quickly -- switch to full autonomy?" |
| Error spikes after steering reduction | Error rate doubles within 10 decisions after autonomy increase | Auto-regress one autonomy level; log "trust calibration rollback" |

---

## 14. Steering State Machine -- Detailed Specification

```mermaid
stateDiagram-v2
    [*] --> Idle: Workflow loaded
    Idle --> AutonomousRunning: User starts / no steering needed
    Idle --> AwaitingApproval: Expansion action detected (ProgEnt)

    AutonomousRunning --> AutonomousRunning: Agent completes atomic action
    AutonomousRunning --> Peeking: User requests /peek (non-blocking)
    AutonomousRunning --> SoftSteerQueued: User sends /steer (h2A queue)
    AutonomousRunning --> HardInterrupt: User presses Ctrl+C / ESC
    AutonomousRunning --> AwaitingApproval: Expansion action detected
    AutonomousRunning --> PendingUndo: User sends /undo
    AutonomousRunning --> Idle: Workflow completes naturally

    Peeking --> AutonomousRunning: User closes peek / Esc
    Peeking --> ReplyInline: User sends reply from peek panel
    ReplyInline --> Peeking: Reply sent, waiting for response

    SoftSteerQueued --> ProcessingSoftSteer: Current atomic action completes
    ProcessingSoftSteer --> InjectingConstraint: NL instruction parsed
    InjectingConstraint --> VerifyingConstraint: Constraint injected into agent prompt
    VerifyingConstraint --> AutonomousRunning: Constraint confirmed / re-inject if needed

    HardInterrupt --> CheckpointingState: AbortSignal propagated to all agents
    CheckpointingState --> wU2Compression: State serialized at last completed checkpoint
    wU2Compression --> PresentingOptions: Session frozen, options displayed
    PresentingOptions --> AutonomousRunning: User selects /resume
    PresentingOptions --> ProcessingSoftSteer: User provides new instruction
    PresentingOptions --> PendingUndo: User requests /undo
    PresentingOptions --> Idle: User selects /cancel (session terminated)

    AwaitingApproval --> ActionApproved: User approves (auto or explicit)
    AwaitingApproval --> ActionRejected: User rejects
    AwaitingApproval --> ActionModified: User sends /steer with adjusted params
    AwaitingApproval --> HardInterrupt: User escalates to hard interrupt
    ActionApproved --> AutonomousRunning: Action executed
    ActionRejected --> AutonomousRunning: Action skipped, agent continues
    ActionModified --> AutonomousRunning: Modified action executed

    PendingUndo --> ClassifyingActions: Identify last N actions
    ClassifyingActions --> GitRollback: Reversible action (file edit, git commit)
    ClassifyingActions --> StateRestore: Partially reversible (DB write with rollback)
    ClassifyingActions --> IrreversibleWarning: Irreversible (API call, sent message)
    GitRollback --> AutonomousRunning: Rollback complete, continue
    StateRestore --> AutonomousRunning: Restore complete, continue
    IrreversibleWarning --> PendingUndo: User must acknowledge before proceeding
    IrreversibleWarning --> UserConfirmRollbackIrreversible: User confirms despite warning
    UserConfirmRollbackIrreversible --> AutonomousRunning: Best-effort rollback applied

    note right of HardInterrupt: Timing targets:<br/>Interrupt propagation: <200ms<br/>State serialization: <2s<br/>Options display: <100ms
    note right of SoftSteerQueued: Queue depth: 0-5 pending steers<br/>FIFO processing<br/>State lock prevents overlap
    note right of AwaitingApproval: Auto-approve timeout: 300s<br/>On timeout: default = reject<br/>Configurable per workflow
```

### 14.1 State Transition Latency Budget

| Transition | Budget | Critical Path |
|------------|--------|---------------|
| Idle --> AutonomousRunning | <500ms | Workflow engine dispatch |
| AutonomousRunning --> Peeking | <100ms | UI render only |
| AutonomousRunning --> HardInterrupt | <200ms | AbortSignal propagation |
| HardInterrupt --> CheckpointingState | <2s | State serialization |
| PresentingOptions --> AutonomousRunning | <3s | State deserialize + resume |
| AutonomousRunning --> SoftSteerQueued | <50ms | Queue enqueue |
| SoftSteerQueued --> ProcessingSoftSteer | <500ms + current action remainder | Soft latency depends on current action |
| AwaitingApproval --> ActionApproved | <200ms (auto) / user-dependent (explicit) | Classification + permission check |
| PendingUndo --> AutonomousRunning | <5s | Git operations (file-size dependent) |

### 14.2 Error Recovery in State Machine

| Error Condition | Detection | Recovery |
|-----------------|-----------|----------|
| AbortSignal not received by sub-agent | Timeout after 1s | Force-kill sub-agent process |
| State serialization fails during interrupt | Exception in PauseResumeSerializer | Fall back to last completed checkpoint; log error |
| Constraint injection fails (model ignores steer) | Post-injection verification | Re-inject with stronger framing; after 3 failures, pause |
| Undo target no longer exists (git history rewritten) | git revert failure | Notify user; offer to manually restore from backup |
| Approval timeout (user away) | 300s elapsed | Default = reject; notify user on return |

---

## 15. Cross-Source Integration -- Agent View Steering + RADAR Debate Framework

### 15.1 Why RADAR for Steering

The RADAR framework (arXiv:2604.19005, ACL 2026) introduces a **role-anchored multi-agent debate** protocol that maps naturally to Lyra's steering architecture. While RADAR was designed for fact verification, its structural innovations -- complementary professional roles, shared evidence grounding, adaptive early termination -- transfer directly to steering decision-making.

**Core insight**: Steering is a debate. When Lyra proposes an action and the user wants to steer it, there are (at minimum) two perspectives: the agent's rationale (why it chose this action) and the user's correction (why a different action is better). RADAR provides a structured protocol for resolving this debate efficiently.

### 15.2 RADAR Roles Mapped to Steering

| RADAR Role | Steering Equivalent | Function in Steering Context |
|------------|-------------------|------------------------------|
| **Politician** | Proposing Agent | Constructs the strongest evidence-backed narrative for the CURRENT action (why this approach, this tool, this file) |
| **Scientist** | User / Steering System | Probes for missing context, weak support, selective framing in the agent's proposal (what the user corrects) |
| **Judge** | AVP Critic Panel (moderated) | Evaluates both arguments against shared evidence (workflow context, codebase state, user preferences) and issues a verdict: keep course, redirect, or halt |

### 15.3 Steering Debate Protocol (Adapted from RADAR)

**Round 1 -- Opening** (agent's proposal + steering system's counter-proposal):

```
Agent (Politician role): "I am about to modify auth.ts to add rate limiting.
   Rationale: The security audit found missing rate limiting on /api/login.
   Approach: Add express-rate-limit middleware with default config.
   Evidence: express-rate-limit docs, security audit findings."

Steering System (Scientist role): "Wait -- the user previously steered toward
   custom rate limiting using the lyra-security wrapper. The express-rate-limit
   approach was explicitly rejected in workflow #142. Captured preference:
   'Prefer lyra-security rate limiting for consistency across all endpoints.'
   Current approach conflicts with stored LearnedPreference (strength: 0.8,
   confidence: confirmed)."
```

**Round 2 -- Rebuttal** (each side addresses the other's evidence):

```
Agent: "The lyra-security wrapper requires Redis. This is a development
   environment without Redis. Let me check... no Redis instance running.
   My approach works without external dependencies."

Steering System: "The lyra-security wrapper was designed to fall back to
   in-memory rate limiting when Redis is unavailable (Section 3.2 of
   lyra-security docs). The Redis check is a deployment-time concern,
   not a development constraint. Preference stands."
```

**Round 3 -- Closing + Judge Verdict** (AVP panel decision):

```
AVP Judge: "Agent's concern about Redis is valid but based on incomplete
   knowledge of lyra-security's capabilities. Steering system's referenced
   preference is confirmed (2 steering events, explicit confirmation).
   Verdict: FOLLOW STEERING -- use lyra-security rate limiting wrapper.
   Order: AVP critic #2 (Claude) confirmed; critic #3 (DeepSeek)
   dissented -- majority holds."
```

### 15.4 Dual-Threshold Early Termination for Steering

RADAR's dual-threshold controller determines when a debate has reached sufficient resolution. Apply the same principle to steering debates:

**Stop margin** -- `s = p(STOP) - p(CONTINUE)`

Applied to the steering deliberation: should we stop debating and apply the steering, or continue gathering evidence?
- `s >= t_s` --> stop debating, apply steering decision
- `s < t_s` --> continue with another rebuttal round

**Confidence threshold** -- `c = max(p(mutating), p(non-mutating), p(uncertain))`

Applied to the action classification confidence:
- `c >= t_v` --> high confidence verdict, safe to decide
- `c < t_v` --> insufficient confidence, escalate to user

**Calibrated thresholds for Lyra steering** (tuning targets):
- `t_s = 0.0` (stop margin: any net preference for stopping should end debate -- favors responsiveness over exhaustive analysis)
- `t_v = 0.7` (confidence: matches RADAR's LLaMA3-8B calibration; high confidence needed before auto-applying steering)
- These are starting points -- tune based on empirical correction rate data

### 15.5 Shared Evidence Pool for Steering

Just as RADAR grounds all agents in the same retrieved evidence corpus, Lyra's steering system must ground both the agent and the steering system in the same context:

```
SteeringEvidencePool (constructed at each steering decision point):
{
  // Current workflow state
  "current_phase": "implementation",
  "recent_actions": [ActionSummary x 10],
  "active_agent_count": 16,
  "mutation_count_10min": 3,

  // Codebase state
  "modified_files_today": ["auth.ts", "middleware.ts"],
  "open_prs": ["PR #142: Security audit findings"],

  // Historical steering context
  "relevant_learned_preferences": [
    {constraint: "Prefer lyra-security rate limiting",
     strength: 0.8, confidence: "confirmed"}
  ],
  "similar_steering_events": [
    {instruction: "use lyra-security wrapper",
     outcome: "applied_positive"}
  ],

  // User profile
  "autonomy_level": "collaborative",
  "correction_rate_100": 0.12,
  "current_satisfaction": null
}
```

Both the proposing agent and the steering system reference this exact evidence pool when constructing their arguments. This eliminates information asymmetry as a source of steering conflict -- differences in recommendation arise from reasoning, not from seeing different data.

### 15.6 RADAR's Failure Analysis Applied to Steering

RADAR's failure analysis of 50 misclassified cases reveals three failure modes that directly inform steering design:

| Failure Mode (RADAR) | Steering Equivalent | Mitigation |
|-----------------------|---------------------|------------|
| **Claim constraint violations** (56%): Agent overlooked numerical, temporal, or scope constraints | Agent ignores steering scope ("focus on auth" applied globally instead of current phase) | Embed steering scope in constraint injection: `scope: 'current_phase'` by default; allow user escalation to `'entire_workflow'` |
| **Semantic framing instability** (30%): Inconsistent term interpretation across debate rounds | Steering intent drifts as conversation continues ("focus on auth" --> "hardening auth" --> "rewrite auth") | Anchor steering terminology in StructuredIntent at parse time; refer back to original parsed intent on each re-injection |
| **Causal attribution errors** (10%): Agent misidentifies root cause of observed outcome | Steering misattributes error cause ("agent chose wrong pattern" when root cause was missing context) | Include context snapshot in each SteeringEvent; AVP verifier cross-checks steering cause against context before applying |

### 15.7 Combined Steering Decision Flow (Agent View + RADAR)

```
1. Agent proposes action A with rationale R
2. AVP critic panel evaluates A against safety gates:
   - Passes all critics --> proceed to step 3
   - Fails any critic --> halt, escalate

3. Steering system checks for relevant LearnedPreferences (TKG query):
   - No matching preferences --> proceed autonomously (Agent View pattern)
   - Matching preferences found --> enter RADAR-style debate

4. RADAR debate (max 3 rounds, early-terminable):
   Round 1 -- Opening: Agent (Politician) vs Steering System (Scientist)
   Round 2 -- Rebuttal: Each addresses other's evidence
   Round 3 -- Closing: Summaries for Judge
   Judge: AVP panel lead, evaluates shared evidence pool
   Early termination: After any round if s >= t_s AND c >= t_v

5. Verdict:
   - Follow Steering: Apply constraint to current action + store preference
   - Maintain Course: Log attempted steering, continue with agent proposal
   - Escalate to User: Neither side has sufficient evidence for auto-decision
     (User sees: [1] Follow agent  [2] Follow steer  [3] Decide manually)

6. Post-action:
   - Store outcome in SteeringEvent.outcome
   - Update LearnedPreference.strength (reinforce or decay)
   - Adjust AutonomyState.correction_rate
```

### 15.8 Cost-Benefit of RADAR Integration

| Dimension | Without RADAR | With RADAR | Change |
|-----------|--------------|------------|--------|
| Steering decision accuracy | Estimated ~75% (heuristic preference matching) | ~90% (structured debate resolution) | +15% accuracy |
| False steer (applying wrong preference) | ~8% of steering events | ~3% of steering events | -62% false steers |
| Decision latency (auto-resolvable) | ~500ms (preference lookup + injection) | ~3-8s (debate rounds) | +5-7s per debate |
| Decision latency (escalated to user) | Same (user decides) | Lower (fewer escalations due to better auto-resolution) | -30% escalations |
| Implementation complexity | Moderate | High (+RADAR protocol engine) | ~1 week added dev time |
| Token cost per steering event | ~300 tokens (preference query + injection) | ~2000-4000 tokens (3-round debate) | +1700-3700 tokens per debated event |

**Recommendation**: Use RADAR-style debate only for HIGH-RISK steering decisions (mutation risk > 0.5 OR correction_rate > 0.15). For low-risk steering, use the simpler Agent View pattern (preference lookup --> immediate inject). This hybrid approach captures the accuracy gain where it matters most while limiting the token and latency cost.

### 15.9 RADAR Steering Protocol for AVP Critic Moderation

When AVP is acting as the Judge in a steering debate, the moderating function must incorporate RADAR's early-termination logic:

```
Function moderateSteeringDebate(proposal, counter_proposal, evidencePool):
    round = 1
    transcript = []
    while round <= 3:
        # Collect arguments
        agent_arg = formatDebateMessage("Politician", proposal, round, evidencePool)
        steer_arg = formatDebateMessage("Scientist", counter_proposal, round, evidencePool)
        transcript.push({round, agent_arg, steer_arg})

        # Judge evaluation
        judge_input = formatJudgePrompt(transcript, evidencePool)
        judge_decision = avp_panel.evaluate(judge_input)

        # Early termination check
        stop_margin = judge_decision.stop_prob - judge_decision.continue_prob
        verdict_confidence = max(judge_decision.label_probs)

        if stop_margin >= TAU_S and verdict_confidence >= TAU_V:
            return {
                verdict: judge_decision.verdict,
                confidence: verdict_confidence,
                rounds_used: round,
                rationale: judge_decision.rationale
            }

        round += 1

    # Max rounds reached without early termination
    return {
        verdict: "ESCALATE_TO_USER",
        rounds_used: 3,
        rationale: "Debate exhausted without sufficient confidence"
    }
```

---

## 16. Updated References

### 16.1 Primary Sources Added

| Row | Source | Link | Key Evidence |
|-----|--------|------|-------------|
| N24 | RADAR -- Role-Anchored Multi-Agent Debate | [arXiv:2604.19005](https://arxiv.org/abs/2604.19005) | Politician/Scientist/Judge roles; dual-threshold early termination (t_s, t_v); shared evidence grounding; +19.3% accuracy over single-agent baselines |

### 16.2 External References Added

- Claude Code Agent View official docs: [code.claude.com/docs/en/agent-view](https://code.claude.com/docs/en/agent-view)
- Claude Code Agent Architecture (ZenML LLMOps Database): Single-threaded nO master loop, h2A async queue, AbortController pattern
- Claude Code Agent View reverse engineering: Soft/hard interrupt mechanisms, sub-agent steering isolation, wU2 compression
- Anthropic autonomous session telemetry (2025-2026): P99.9 session duration >45min, veteran auto-approve >40%, self-interrupt rate >2x human interrupt rate
- MH1 tool execution engine: 6-stage pipeline, 96.8% claimed success rate, <2s average response time
- RADAR paper: [arxiv.org/abs/2604.19005](https://arxiv.org/abs/2604.19005) -- Role-anchored debate for half-truth detection, adapted for steering resolution

---

## Changelog

| Date | Run | Changes |
|------|-----|---------|
| 2026-05-31 | 16 | Initial plan created -- problem statement, basic architecture Mermaid, steering commands, parity + breakthrough task table, basic multi-provider notes, 2-person expert review, risks table, sparse references |
| 2026-06-01 | 19 | Deepened from ~169 to ~500+ lines: added plain-language summary, extended evidence synthesis (Claude Code Agent View steer-by-exception, Identity Skews Debate, Actor-Observer Asymmetry, Interactive Task Learning, Mixed-Initiative Interaction), interrupt/steer/undo state machine Mermaid diagram, 6-task build outline with dependencies and effort estimates, multi-provider steering behavior table with provider-specific strategies, (B) Breakthrough natural-language steering with preference learning, expert review with senior-product/UX + senior-PM + Adversarial Skeptic, expanded risks |
| 2026-06-01 | 20 | **Further deepened to 750+ lines**: added specific findings.md citations with row numbers and direct quotes in evidence synthesis (Section 2.1 -- now 8 rows with SABER, AutoResearchClaw, Karpathy, CheetahClaws, ProgEnt, Self-Evolving Safety, MOSS); complete TypeScript data model with 6 interfaces and ConstraintInjection provider-adaptation (Section 3.3); BREAKTHROUGH-ARCHITECTURE.md linking with 7-dimension layer mapping table and direct architecture document references (Section 6.2-6.4); expanded references with 13 primary sources in table format, architecture cross-references, related Lyra packages, and external references (Section 9); section renumbering to accommodate new content |
| 2026-06-01 | 21 | **Further deepened to 1100+ lines**: added deep mechanism descriptions for Claude Code Agent View interrupt/redirect/approve patterns with nO master loop, h2A async queue, AbortController propagation, ProgEnt monotonic confinement as approve pattern, sub-agent steering isolation, and wU2 context compression on interrupt (Section 10); real benchmark latency targets for interrupt handling (sub-200ms hard interrupt, sub-100ms peek), steering UX response times with breakdown by interaction type, autonomous session duration data from Anthropic telemetry showing veteran trust patterns, provider-specific steering latency, and context window cost per steering operation (Section 11); step-by-step algorithms for peek panel rendering (cache-before-render, 60fps target), suggested-reply generation (state-type classification with pattern-match fast path or Haiku-class model fallback), and attach/detach flow with supervisor integration and error handling (Section 12); explicit trade-off analysis covering cognitive load, throughput, safety, and context cost dimensions with quantified break-even model (15-20% steering fraction), 3-phase trust curve, and steering fatigue mitigation table (Section 13); detailed Mermaid steering state machine with 20+ states including SoftSteerQueued, CheckpointingState, wU2Compression, UserConfirmRollbackIrreversible, latency-annotated transition budget table, and 5-condition error recovery matrix (Section 14); cross-source integration combining Agent View steering patterns with RADAR debate framework (arXiv:2604.19005) including role mapping (Politician/ProposingAgent, Scientist/SteeringSystem, Judge/AVP), 3-round steering debate protocol with worked example, dual-threshold early termination (t_s stop margin, t_v confidence threshold), shared evidence pooling to eliminate information asymmetry, RADAR failure analysis applied to steering with 3 mitigation strategies, combined Agent View + RADAR decision flow, cost-benefit table with 6 dimensions, and Judge moderation function pseudocode (Section 15); expanded references with RADAR primary source and 6 external architecture references (Section 16) |
