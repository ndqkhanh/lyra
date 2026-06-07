# Designing AI Agents — Chapter Notes
**Author:** Manning Publications (MEAP V01) | **Year:** 2026 | **Core Thesis:** Agent architecture is *bounded resource allocation under uncertainty* — the model spends (context, compute, action opportunities); the harness budgets. The 27 named patterns across 7 cognitive functions × 6 execution topologies form a shared vocabulary for designing, reviewing, and communicating about agent systems, analogous to what the Gang of Four's 23 patterns gave object-oriented design.

---

## Chapter 1: The Agent Paradigm Shift
- **Key insight:** Traditional software assumes deterministic control flow, structured inputs, and human-selected strategies. Agent systems invert all three: the LLM (not the developer) selects its own strategy at runtime, communicates through natural language, and operates under probabilistic state. The engineer's role shifts from writing logic to *constraining the decision space*.
- **Core premise (thesis statement):** "Agent architecture is the design of bounded resource allocation under uncertainty. The model generates possibilities by spending context, compute, and action opportunities; the harness makes that spending viable by budgeting, constraining, routing, and verifying it."
- **Three uncertainties of agent systems:**
  1. *Output uncertainty* — same prompt, different responses (temperature, sampling, model drift)
  2. *Behavioral uncertainty* — agent selects its own tool/strategy at runtime
  3. *Environmental uncertainty* — the world changes between observations
- **Design inversion:** Past the "implementation plateau," improving the agent's code yields diminishing returns. Output quality is determined by the *specification* — the cognitive architecture, pattern composition, constraints. "The specification is the source code; the agent is the compiler." (Spec-Driven Development / SDD)
- **Token leverage:** Architecture quality is directly measurable in dollars. A spec that wastes 2,000 tokens per invocation across 50,000 daily calls is a $300/day design decision. Token leverage = ratio of output quality to token cost — treated as a first-class design criterion.
- **The gardener's mindset:** GoF engineer = watchmaker (controls gears). Distributed-systems engineer = doctor (diagnoses, heals). Agent engineer = gardener (selects seeds, prepares soil, sets fences, prunes). The gardener does not control growth but a well-tended garden is not accidental.
- **Harness engineering convergence (2026):** Mitchell Hashimoto coined "harness engineering": "anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again." On TerminalBench 2.0, harness optimization alone moved the same model from below baseline to top-five. Vercel removed 80% of their agent's tools → fewer steps, fewer tokens, faster responses.
- **Every agent pattern has an engineering ancestor:** Cache hierarchies → tiered memory. Circuit breakers → loop detectors. Saga transactions → plan-and-execute. Reconciliation loops → PRA loops. Event sourcing → episodic memory / failure journals. Bulkhead isolation → sandboxing.

---

## Chapter 2: Agent Architecture and the Two-Axis Map
- **Key insight:** Existing agent frameworks (Weng 2023, Huyen, Ng, Anthropic, arXiv 2026) each leave blind spots. The book synthesizes them into *seven cognitive modules* (not four): Perception, Memory, Reasoning, Action, Reflection, Collaboration, Governance. The last three are what separate a demo from a production system.
- **Agent Capability Stack (3 rings):**
  - Inner ring (Core Cognition): Perception, Memory, Reasoning, Action — what the agent does
  - Middle ring (Meta-Cognition): Reflection — self-evaluation; Shinn et al. showed Reflexion improved coding task success from 50% → 90%
  - Outer ring (System Intelligence): Collaboration + Governance — production concerns
- **The PRA loop (Perception-Reasoning-Action):** Descendant of Boyd's OODA loop (Observe-Orient-Decide-Act, USAF 1976). Two added sub-loops: Reflection loop (self-correction) and Memory loop (persistence across cycles).
- **Compound error:** If each step has 95% accuracy, a 20-step task has only 36% overall success (0.95²⁰ ≈ 0.36). Moving from 95% → 99% per-step accuracy doubles success rate at 20 steps. Four responses: minimize iterations, maximize per-step accuracy, add verification checkpoints, fail fast.
- **General Agent Architecture reference model:** Seven cognitive modules arranged as concentric architecture. Governance wraps all modules (cross-cutting). Information flows along 4 paths: primary (L→R), feedback (R→L), persistence (↕ Memory), lateral (Collaboration).
- **Runtime Virtual Machine (LLM-as-OS analogy):** Sandbox = process isolation, state manager = file system, MCP host = device drivers, skills = package manager, observability = system monitor. Key limitation: the LLM has *anterograde amnesia* — cannot form new long-term memories after training.
- **Production system bets (8 systems mapped):**
  - Claude Code → single-agent PRA loop + layered extensions
  - Cursor → multi-agent parallel (up to 8 agents, isolated worktrees)
  - Cline → Plan/Act separation + human approval on every action
  - Codex CLI → sandbox-first (OS-level isolation)
  - Augment → 200K-token semantic codebase index
  - Manus → KV-cache optimization as dominant production concern
- **The complete pattern map:** 7 cognitive functions × 6 execution topologies = 42 possible cells, 27 populated with named patterns, 15 empty (structurally impractical or unexplored).
- **Pattern Selection Card:** ASSESS (rate each cognitive function None/Light/Heavy) → ROUTE (select single vs. multi-agent based on collaboration + time budget) → SELECT (look up specific patterns from map coordinates).
- **Single-agent vs. multi-agent:** Four walls that force multi-agent: (1) context overflow, (2) expertise specialization, (3) parallelism, (4) adversarial verification. Costs: coordination cost, error amplification (up to 17.2× in poorly orchestrated teams per DeepMind), debugging opacity. The sweet spot = "agent + sub-agents" (delegate context, not control).
- **Progressive trust spectrum (4 levels):** Level 1 (Human-in-the-loop), Level 2 (Human-on-the-loop), Level 3 (Human-over-the-loop), Level 4 (Autonomous with audit).
- **Critical quote:** "Engineering an agent is mostly about making invisible things visible. Each cognitive module can be read through this lens: Perception makes context-allocation decisions visible; Memory makes persistence decisions visible; Reasoning makes thinking visible; Reflection makes self-evaluation visible; Governance makes permission decisions visible."

---

## Chapter 3: Perception — What Your Agent Sees Determines What It Does
- **Key insight:** "Intelligence without perception is not just useless; it is dangerous." A mediocre model with a well-curated 30K-token context outperforms the best model drowning in 180K tokens of noise. The context window is a *spotlight*, not a database.
- **The U-shaped attention curve (Liu et al. 2024):** Models attend most to beginning and end of context. Information in the middle receives ~30% less attention — the "dead zone." By cycle 30 of a 50-cycle task, critical information from cycle 12 is effectively invisible.
- **The three-way squeeze:** Token budget (finite, costly), attention quality (degrades with length), token cost (uncached = 10× cached). Perception is not preprocessing; it is the core architectural discipline.
- **Iatrogenic context:** Information added to "help" that actually degrades performance — analogous to iatrogenic illness in medicine. Every pattern in this chapter is a defense against it.
- **Perception ↔ Governance symmetry:** Perception filters what enters (input gate); Governance filters what leaves (output gate). Same mechanism (whitelist, threshold, audit). Different ends.
- **Four perception patterns:**
  1. **Context Triage (Perception × Route):** Four priority tiers (P0 Critical through P3 Deferrable). The key insight is P3 — information available but not loaded; lightweight handles (~10 tokens each) for JIT retrieval. Engineering ancestor: ER triage.
  2. **Semantic Compaction (Perception × Chain):** Three levels — tool result clearing, conversation summarization, progressive summarization. Cardinal rule: NEVER compact error traces. Losing failure information cuts the feedback loop.
  3. **Multi-Modal Fusion (Perception × Parallel):** Keep images when spatial information is the signal; convert everything else to compact text.
  4. **Progressive Discovery (Perception × Orchestrate):** Forage → Focus → Deepen. Three phases, each increasing depth while decreasing breadth.
- **Perception metrics:** Re-read ratio (<5% healthy, >15% hurting), token spend per successful outcome, attention zone coverage (critical items in first 10% or last 20%).
- **Claude Code's perception implementation:** Five-level CLAUDE.md hierarchy + Skills (progressive disclosure, ~100 tokens idle) + Sub-agents (context isolation — fresh window, only task prompt).
- **Signal-to-noise ratio (SNR) decision rule:** >50% → direct; 10-50% → consider sub-agent; <10% → sub-agent mandatory; <1% → multi-layer filtering.
- **Manus's critical rule:** Preserve error traces from failed actions at P1 priority, never compressing, never dropping. "Never triage away failure information."

---

## Chapter 4: Memory — What Your Agent Remembers Shapes What It Becomes
- **Key insight:** "An agent without memory is not just forgetful. It is dangerous in proportion to its intelligence because it will confidently act on an incomplete picture." The LLM has anterograde amnesia — cannot form new long-term memories after training.
- **Memory serves three purposes:** (1) State persistence (what was I doing?), (2) Knowledge retrieval (what do I need to know?), (3) Experience accumulation (what should I avoid doing again?).
- **Memory hierarchy (CoALA framework):** Working memory (context window, 128K-200K tokens) → Episodic memory (execution logs, GB) → Semantic memory (vector DB, unlimited). Maps to CPU L1 cache → RAM → disk.
- **Memory lifecycle (4 phases):** Encoding (what to save?), Consolidation (when to promote short-term → long-term?), Retrieval (how to find relevant memories?), Forgetting (what to evict?). Strategic forgetting is a feature, not a bug — an agent that retains everything suffers retrieval degradation (the "Funes" problem).
- **Public-private knowledge principle:** Use point-light keywords for public knowledge the model already knows (e.g., "follow SOLID"). Write full specifications only for private knowledge unique to your project (e.g., "indexes use idx_{table}_{col}"). Stronger models (Opus) need fewer tokens to activate the same knowledge.
- **Claude Code's six-tier memory hierarchy:** Managed policy → User memory → Project memory → Project rules → Local project memory → Auto memory. Key feature: *write-back memory* — agent writes its own future context; first 200 lines loaded into every system prompt.
- **CLAUDE.md is not "in memory":** It is re-sent with every API call as part of the system prompt. Never compressed during auto-compaction. Every line costs tokens every turn — concision is an engineering requirement, not a preference.
- **Sub-agent memory isolation:** Sub-agents do NOT inherit parent's CLAUDE.md, rules, or auto memory. Each starts with clean context. Parent must explicitly include needed conventions in task description. Architectural necessity for SNR.
- **Four memory patterns:**
  1. **Hierarchical Retention (Memory × Route):** Three tiers with explicit promotion/eviction. Eviction scoring: importance (50%) + recency (30%) + access frequency (20%). Consolidation: entries above 0.6 importance or from "reflection" source persist to vector DB.
  2. **RAG (Memory × Chain):** Three pipelines — index (offline), retrieve (online), generate. Hybrid search (semantic + keyword) with Reciprocal Rank Fusion. Claude Code uses tool-based retrieval (Grep/Glob/Read as retrieval, LLM as re-ranker) — Agentic RAG.
  3. **Progress Tracking (Memory × Orchestrate):** Checkpoint chain for crash recovery. Production approaches: Cursor (background indexing agents), Claude Code (TodoWrite), Codex CLI (sandbox state persistence).
  4. **Failure Journals (Memory × Loop):** Two levels — fix (surface-level workaround) vs. heuristic (why it happened, how to prevent). ExpeL showed autonomous extraction of failure heuristics. Token asymmetry: 200 tokens per entry prevents entire wasted PRA cycles costing thousands → 10x return.
- **Memory metrics:** Retrieval hit rate (>30%), repeated mistake rate, memory staleness (timestamp + decay), consolidation ratio (10-20% sweet spot).
- **Multi-agent memory:** Shared memory = blackboard pattern. Key risk: contamination — when one agent's context pollution spreads to others via shared memory.
- **Cache coherence problem:** When the same fact exists in multiple tiers with different values. Mitigation: treat long-term memory as authoritative; re-retrieve before critical decisions.

---

## Chapter 5: Reasoning — How Your Agent Decides What to Do Next
- **Key insight:** "Reasoning depth is an engineering variable, not a constant." The model can think brilliantly; the problem is letting it think brilliantly about everything, including things that don't deserve brilliance. The architecture must decide, for each input, how deeply to think.
- **The harness blind spot:** The standard harness formula (Tools + Knowledge + Observation + Action + Permissions) has no slot for Reasoning. It treats the model as a black box. But Chain-of-Thought vs. direct response, three-tier routing vs. flat inference, tree search vs. linear generation — these are architectural choices that determine agent quality.
- **Kahneman's dual-system mapping:** System 1 (fast, intuitive, low-cost) = direct LLM response. System 2 (slow, deliberate, high-cost) = Chain-of-Thought, tree search, hypothesis testing. Talker-Reasoner architecture splits these into cooperating modules.
- **Three waves of reasoning:**
  - Wave 1 (2022-2023): Prompt-elicited reasoning — "Let's think step by step" → GSM8K 17.7% → 78.7%
  - Wave 2 (2024-2025): Trained reasoning models — o1/o3, DeepSeek-R1, Claude extended thinking
  - Wave 3 (2025-present): Budget-aware reasoning — inference demand projected to exceed training demand by 100× by end of 2026
- **Why architectural patterns still matter:** (1) Cost/latency — routing prevents burning 10K thinking tokens on simple classification. (2) Auditability — external reasoning traces can be inspected; internal traces often hidden. (3) Compositional control — multi-step orchestrations no single model call can replicate.
- **Reasoning metrics:** Reasoning step count per resolution, routing accuracy (track false-simple rate), backtrack rate (healthy: 15-35%), confidence calibration.
- **ReasoningTrace dataclass** captures: classified_complexity, model_used, thinking_tokens, reasoning_steps, backtracks, hypotheses_generated/refuted, final_confidence, wall_time_ms.
- **Four reasoning patterns:**
  1. **Chain-of-Thought (Reasoning × Chain):** Three variants — Zero-shot CoT (simplest, highest ROI), Few-shot CoT (formatting template), Process supervision (PRM800K — 800K human-annotated step-level labels; catches errors outcome-only checking misses). Claude Code's implicit CoT: each tool invocation is a step in an externalized reasoning chain. Failure modes: unfaithful chains (Turpin et al.), chain collapse. Self-consistency (Wang et al.) improves accuracy by +17.9% via majority vote across multiple chains.
  2. **Complexity-Based Routing (Reasoning × Route):** Lightweight classifier (<100 tokens) → three tiers (SIMPLE/MODERATE/COMPLEX). RouteLLM (ICLR 2025): 85% cost reduction with minimal quality loss via matrix-factorization classifier. Token leverage: 50 classification tokens saves 100K reasoning tokens (1:2,000 ratio). Planner-Worker economic split: Opus plans, Haiku executes → 90% cost reduction. Key design: router should err toward over-estimation (false-simple is worse than false-complex). "Newspaper test": if wrong answer makes headlines, route to deepest tier regardless.
  3. **Parallel Exploration (Reasoning × Parallel):** Tree of Thoughts (Yao et al. — Game of 24: 4% → 74%), Graph of Thoughts (Besta et al. — adds aggregation + refinement), AGoT (+46.2% on GPQA-Diamond), MCTS-SWE (SWE-bench Lite +23%). Claude Code implements implicit depth-first search with backtracking. UCT formula from AlphaGo balances exploitation vs. exploration. Failure modes: evaluation hallucination, shallow breadth (need "maximally different" branches).
  4. **Iterative Hypothesis Testing (Reasoning × Loop):** Scientific method as agent architecture. Five-phase cycle: Hypothesize → Design Experiment → Execute → Observe → Revise. Explicit hypothesis management with evidence_ratio tracking. Antidote to "confidence drift" (mistaking sunk cost for evidence). SWE-bench evidence: Claude Opus 4.6 = 79.2%, Sonnet 4.6 = 79.6% — they outperform via better iteration, not deeper single-pass reasoning.
- **Composing reasoning patterns:** "You start at the top of the table and move down only when the simpler pattern fails." The four patterns form an escalation logic — CoT is simplest, Routing decides whether to apply CoT, Parallel Exploration branches CoT, Hypothesis Testing adds environment interaction.

---

## Overall Architecture Notes (Cross-Chapter)

### Budget Lens
Every architectural decision is a decision about how to spend a finite budget. The 27 patterns are 27 allocation strategies. Measurement framework: token leverage = output quality / token cost.

### Design Inversion
The specification (cognitive architecture, pattern composition, constraints) matters more than the implementation. "The agent's implementation is already competent; what determines output quality is the specification of what to perceive, what to remember, how deeply to reason."

### Engineering Ancestors
Every agent pattern maps to a proven ancestor from distributed systems or GoF:
- Cache hierarchy → Tiered memory
- Circuit breaker → Loop detection/halting
- Saga/Compensating Tx → Plan-and-execute
- Reconciliation loop → PRA loop
- Event sourcing → Episodic memory / Failure journals
- Bulkhead isolation → Sandboxing / minimal permissions
- BFS/DFS/A* → Tree of Thoughts / Parallel Exploration
- Scientific method → Iterative Hypothesis Testing
- ER triage → Context Triage
- Lossy compression → Semantic Compaction

### Production References Throughout
The book uses Claude Code as primary reference architecture, with supplementary analysis of Manus, Cursor, Cline, Codex CLI, OpenCode, Augment, and Windsurf.

### Key Numbers
- Compound error: 95% per-step × 20 steps = 36% overall; 99% per-step × 20 steps = 82% overall
- Reflexion: 50% → 90% on coding tasks (Shinn et al.)
- CoT on GSM8K: 17.7% → 78.7% (Wei et al.)
- Self-consistency: +17.9% over single-chain CoT (Wang et al.)
- RouteLLM: 85% cost reduction (ICLR 2025)
- ToT on Game of 24: 4% → 74% (Yao et al.)
- AGoT on GPQA-Diamond: +46.2%
- SWE-Search MCTS on SWE-bench: +23%
- Multi-agent error amplification: up to 17.2× vs single-agent (DeepMind)
- Claude Code KV-cache: cached $0.30/MTok vs uncached $3.00/MTok (10×)
- SDD: 3-5× reduction in rework cycles for teams using structured specs (GitHub Spec-Kit data)
- Planner-Worker: 90% cost reduction while maintaining planning quality
- 27 named patterns in the complete map (from 7×6 grid, 15 cells empty)
