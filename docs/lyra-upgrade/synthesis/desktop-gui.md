# Desktop GUI & User Experience -- Thematic Synthesis

**Date:** 2026-06-07
**Scope:** Interface architecture, interaction paradigms, user experience patterns, and desktop/GUI agent capabilities for Lyra's upgrade
**Sources:** 25 paper notes + 6 web/repo deep-reads + 5 book chapters, cross-referenced against Lyra's §4 subsystem architecture

---

## 1. Frontier Techniques (ranked by evidence strength)

### Technique 1: Dual-Grounding Perception (Visual + Semantic)
- **Sources:** OS Agents Survey [paper: 2508.04482v1, ACL 2025], OSWORLD [paper: 2404.07972v2], WebArena [paper: 2307.13854v4, ICLR 2024], UI-TARS-desktop [repo: bytedance/UI-TARS-desktop, Apache 2.0]
- **Mechanism:** The agent captures both a screenshot (pixel input to VLM) and a structured semantic representation (accessibility tree, DOM, or element IDs). In Set-of-Marks (SoM) mode, bounding boxes are overlaid with numeric labels on the screenshot, transforming coordinate prediction into n-way classification. The dual channel enables the agent to use visual cues (layout, color, icons) and semantic cues (element role, text content, state) jointly.
- **Evidence:**
  - OSWORLD (real Ubuntu VM, 369 tasks): GPT-4V with Screenshot-only achieves 5.26% success; with A11y Tree-only achieves 12.24%; with **Screenshot+A11y** achieves 12.17%. Best SoM result is 11.77% (GPT-4V). Human baseline: 72.36%.
  - WebArena (4 websites, 812 tasks): Accessibility tree with unique element IDs is the default mode. GPT-4 with CoT achieves 14.41% end-to-end success vs. 78.24% human -- a 5.4x gap.
  - UI-TARS-desktop: Pure screenshot-based approach works on any GUI universally (desktop apps, browsers, games, terminals) with no platform-specific API needed. Grounding relies on VLM outputting normalized bounding-box coordinates via regex-parsed action text format.
  - OS Agents Survey catalogs 27+ frameworks and finds visual-only misses semantics of identical-looking elements; semantic-only misses spatial layout and visual state. Dual grounding is identified as the most promising strategy.
- **Maturity:** Research concept (OSWORLD/WebArena are academic benchmarks), but UI-TARS-desktop v0.2.4 is a working Electron app deployed via Homebrew. The gap between best models (12-14%) and humans (72-78%) remains large.

### Technique 2: Operator Abstraction Pattern (Environment-Agnostic Execution)
- **Sources:** UI-TARS-desktop [repo: bytedance/UI-TARS-desktop], OSWORLD [paper: 2404.07972v2], OpenHands [repo: All-Hands-AI/OpenHands, MIT]
- **Mechanism:** Define an `Operator` interface with two essential methods:
  ```
  interface Operator {
    screenshot(): Promise<ScreenshotOutput>;  // capture current environment state
    execute(action: ParsedAction): Promise<ExecuteOutput>;  // perform action
  }
  ```
  Concrete implementations (NutJSOperator for desktop, BrowserOperator for web, AdbOperator for Android) are interchangeable under the same GUIAgent loop. The agent does not know which operator it is driving. OSWORLD extends this with pyautogui code generation for full human-computer action space (mouse, keyboard, drag, scroll, hotkeys, wait). OpenHands uses Docker sandboxes with a similar abstraction -- the agent-server runs isolated, communicating with the app-server via HTTP.
- **Evidence:**
  - UI-TARS-desktop ships 4 operator implementations (Electron-nut-js, browser-Playwright, mobile-adb, general-nut-js) sharing the same GUIAgent loop.
  - OSWORLD benchmarks across Ubuntu (369 tasks) and Windows (43 tasks) with 0.70 cross-OS correlation coefficient.
  - OpenHands runs agents in Docker containers with 3 sandbox implementations (Docker/Process/Remote) behind a single `SandboxService` ABC. Achieves SWE-bench 77.6%.
- **Maturity:** Production deployed (UI-TARS-desktop on Homebrew, OpenHands as hosted service + OSS). Environment-agnostic execution is a proven architectural pattern.

### Technique 3: Execution-Based Evaluation with Programmatic State Inspection
- **Sources:** WebArena [paper: 2307.13854v4, ICLR 2024], OSWORLD [paper: 2404.07972v2], tau-bench [paper: 2406.12045v1]
- **Mechanism:** Instead of comparing agent actions to a gold-standard trajectory (surface-form matching), evaluate by programmatically inspecting final system state. WebArena's `r_prog(s)` uses locators (DB queries, API calls, `document.querySelector` JS selectors) to retrieve goal-relevant state, then applies keyword matching. OSWORLD uses 134 unique per-task evaluation functions (getter→evaluator pipelines checking file contents, a11y tree nodes, cookie state). tau-bench compares final database state to unique ground truth: `r = r_action * r_output` where r_action checks DB state and r_output checks required information substrings.
- **Evidence:**
  - WebArena: GPT-4 fuzzy-match judge achieves 100% accuracy on 900 date/time format equivalence judgments.
  - tau-bench: DB-state evaluation is deterministic, instantaneous, and cost-free (no LLM judge needed for core metric).
  - OSWORLD: 134 custom evaluation functions validated with ~400 man-hours of double-checking.
- **Maturity:** Research validated on 3 major benchmarks. Production adoption requires per-task evaluator engineering (DB queries, JS selectors, API calls), but the pattern is clear and reusable.

### Technique 4: pass^k Reliability Metric (Consistency over Average Success)
- **Sources:** tau-bench [paper: 2406.12045v1], tau2-bench [paper: 2506.07982v1]
- **Mechanism:** `pass^k = E_task [ (c choose k) / (n choose k) ]` where n = total trials, c = successful trials. This is an unbiased estimator measuring the probability that ALL k independent trials succeed -- i.e., consistency/reliability, not best-of-k discovery (pass@k). Meant to surface fragility that average metrics hide.
- **Evidence:**
  - tau-bench (retail, gpt-4o): pass^1 = 61%, pass^2 = ~50%, pass^4 = ~35%, **pass^8 < 25%**. The agent solves the same task 8/8 times less than 25% of the time.
  - tau2-bench (telecom, dual-control): Best model (claude-3.7-sonnet) pass^1 = 49%, pass^4 = 25%. pass^k decay reveals substantial reliability gaps invisible in pass^1.
- **Maturity:** Research concept (tau-bench is preprint, under review). pass^k is the most principled reliability metric in the agent-evaluation literature. No production agent system is yet evaluated this way.

### Technique 5: Context-Window-Based Experience Replay (Training-Free Self-Improvement)
- **Sources:** CER [paper: 2506.06698v1], ReasoningBank [paper: 2509.25140v2]
- **Mechanism:** Distill structured memory items from agent trajectories directly into the context window. No embeddings, no training, no vector database required. CER separates "dynamics" (state awareness -- where am I, what's available) from "skills" (action heuristics -- what to do, step-by-step). ReasoningBank stores structured reasoning strategies (title + description + content) and learns from both successes AND failures, using LLM-as-a-Judge (72.7% accuracy) for self-supervision.
- **Evidence:**
  - CER (WebArena, 812 tasks, GPT-4o): +51.0% relative improvement over baseline (24.3% → 36.7% hybrid), with only +17.3% token overhead. Outperforms tree search by 20.8% relative while using 3x fewer tokens.
  - CER stability (93%) and plasticity (141%) -- retains old capabilities while gaining new ones.
  - ReasoningBank (WebArena, 684 instances): +20.5% relative improvement over No Memory (40.5% → 48.8% Gemini-2.5-flash). Token overhead only 4.3% (vs. Synapse's 15.1% and AWM's 16.8%). Learns from failures where baselines degrade.
- **Maturity:** Lab validated (CER and ReasoningBank on WebArena, SWE-Bench-Verified, Mind2Web). Training-free nature makes it immediately deployable. Combined dynamics+skills dual-channel architecture is well-motivated by ablation.

### Technique 6: Inner Monologue Retrieval (Multi-Turn KG Querying Before Action)
- **Sources:** DAVIS [paper: 2410.09252v2]
- **Mechanism:** Replace static one-shot RAG with a conversational multi-turn retrieval loop between the planner and a structured Temporal Knowledge Graph (TKG). Before committing to a plan, the planner iteratively queries the KG (up to k=5 turns), the KG returns structured subgraph responses, and the planner identifies remaining gaps. Only when confidence is sufficient does the agent execute. The TKG preserves relational structure and temporal ordering -- entities, relations, timestamps -- enabling causal reasoning that fragmented vector-based retrieval cannot.
- **Evidence:**
  - DAVIS on ScienceWorld (30 tasks, 9 subjects): **1.8x higher average score** than next-best baseline (65.06 vs. Reflexion 33.64). Wins 8/9 subjects. Perfect scores on 2 tasks (Find Living Thing, Genetics 10-1).
  - Multi-hop QA: HotpotQA F1 73.8 (beats GraphReader 70.0, competitive with HOLMES 78.0).
  - Cost: $0.43/action, $43/episode at GPT-4o pricing -- prohibitive for routine use but acceptable for high-stakes tasks.
- **Maturity:** Lab validated. The inner monologue concept is transferable, but the full TKG construction pipeline (Stanford CoreNLP + LLM parsing + temporal reordering) is heavy. A lighter version using Lyra's existing memory stores would be a pragmatic first step.

### Technique 7: MCTS-Driven Agent Architecture Search
- **Sources:** AFlow [paper: 2410.10762v4], SWE-Search [paper: 2410.20285v6, ICLR 2025], RAP [paper: 2305.14992v2]
- **Mechanism:** Monte Carlo Tree Search over code-represented agent workflows (AFlow) or solution-state trees (SWE-Search). LLM serves as optimizer (proposing node modifications) or value agent (scoring states). UCT formula balances exploration/exploitation. Key innovations: hindsight feedback (value-agent explanation injected when re-expanding from parent nodes), soft mixed probability selection with blank-template escape, dynamic early stopping.
- **Evidence:**
  - AFlow: 5.7% average improvement over human-designed SOTA baselines; 19.5% over prior automated method (ADAS). Found workflows where GPT-4o-mini **outperforms** GPT-4o at 4.55% of the inference cost.
  - SWE-Search (SWE-bench Lite, 300 instances): +23% mean relative improvement across 5 models (GPT-4o: 25.7% → 31.0%). Discriminator debate improves selection accuracy from 73% to 84%.
  - RAP (Blocksworld, LLaMA-33B): surpasses GPT-4 with CoT by 33% relative. RAP(20) achieves 42% on 6-step problems where CoT is 0%.
- **Maturity:** Lab validated with strong empirical evidence across multiple benchmarks. SWE-Search's 5-14x cost multiplier is prohibitive for default operation. The hindsight feedback mechanism can be extracted for selective use (e.g., only when agent prematurely declares "done").

### Technique 8: Progressive Skill Loading with Deferred Tool Registry
- **Sources:** DeerFlow [repo: bytedance/deer-flow, MIT], Claude Code [docs: output-styles, skills], Cline [repo: cline/cline, Apache 2.0], OpenHands [repo: All-Hands-AI/OpenHands, MIT]
- **Mechanism:** Skills are Markdown files with YAML frontmatter (name, description, allowed-tools). The system prompt lists enabled skills by name only -- full content loads on demand when the agent references a skill or an associated tool. MCP tools are similarly deferred: hidden from the model until an explicit query tool promotes them. This is a direct answer to the context-window problem: hundreds of MCP tool schemas are withheld from context until needed.
- **Evidence:**
  - DeerFlow: 20 built-in skill packs. Progressive loading via `load_skills()` scanning for `SKILL.md` files. MCP tools hidden until `tool_search` promotes them.
  - Claude Code: Skills are loaded on demand (descriptions only in system prompt). MCP can defer-load 40+ tools.
  - OpenHands: Skills loaded at sandbox start, injected into system prompt.
  - No published quantitative ablation comparing progressive vs. eager loading, but the context-window savings are mechanically obvious: M schemas of O tokens each → deferred = 0 tokens unless needed.
- **Maturity:** Production deployed (DeerFlow, Claude Code, Cline, OpenHands all use variations). The Markdown-file skill format is the emerging standard across 4+ independent projects.

### Technique 9: Surface-Agnostic Engine Architecture with Capability Masks
- **Sources:** OpenGUI [repo: akemmanuel/OpenGUI, MIT], Claude Code [book: Claude Code Definitive Guide, Ch.7], OpenCode [repo: anomalyco/opencode, MIT]
- **Mechanism:** The agent engine is decoupled from any specific UI surface (terminal, desktop, web, IDE). A protocol interface (e.g., `OpenGuiClient`, `Workspace` interface) defines the API between engine and surfaces. Each surface is a thin rendering layer. Capability masks (`HarnessCapabilities` interface with boolean flags: sessions, streaming, models, agents, commands, mcp, skills, etc.) drive which UI controls appear. Claude Code separates engine from interface -- the terminal is the primary surface, the IDE is supplementary, with cross-surface session teleport (`/teleport`).
- **Evidence:**
  - OpenGUI: Single React frontend runs identically on Desktop (Electron), Web (browser), and Mobile (Capacitor). 4 harness adapters (OpenCode, Claude Code, Codex, Pi) each with capability mask.
  - Claude Code: Terminal-first with IDE assists. Cross-surface teleport enables fluid session migration. "The architecture separates engine from interface."
  - OpenCode: 22 packages across CLI, TUI, web, desktop (Electron), and SDK. Event-sourced, functional-effect architecture using Effect-TS.
- **Maturity:** Production deployed (Claude Code, OpenCode, OpenGUI at v0.5.24). Surface-agnostic engine architecture is proven at scale across both commercial and open-source products.

### Technique 10: Output Persona Profiles (Separating "How" from "What")
- **Sources:** Claude Code Output Styles [docs: code.claude.com/docs/en/output-styles], 30 Agents Every AI Engineer Must Build [book: Ahmad 2026, Ch.3, Ch.10]
- **Mechanism:** Agent response behavior (tone, verbosity, decision-making style, output format) is separated from domain knowledge. In Claude Code, output styles are Markdown files with YAML frontmatter that modify the system prompt without changing the knowledge base. The PTCF blueprint (Persona, Task, Context, Format) from Ahmad (2026) provides a principled framework: Persona defines identity and tone, Task articulates the mission, Context establishes operational boundaries, Format ensures structured output. Personality is modeled as a first-class architectural layer (constraint layer), not a post-hoc filter.
- **Evidence:**
  - Claude Code: 3 built-in styles (Proactive, Explanatory, Learning) + custom Markdown styles with `keep-coding-instructions` toggle. Plugins can force styles via `force-for-plugin: true`.
  - Ahmad 2026, Ch.10: "Personality modeling is implemented as a first-class architectural layer (Profile/Persona) -- not an emergent property." Dual-memory hierarchy (working + semantic memory) with ConversationSummaryBufferMemory pattern.
- **Maturity:** Production deployed (Claude Code). Conceptually validated by Ahmad's agent architecture framework. Low engineering cost, high UX leverage.

### Technique 11: Accept-Sequence Dispatch (Race-Free Concurrent Prompt Handling)
- **Sources:** Crush [repo: charmbracelet/crush, FSL-1.1-MIT]
- **Mechanism:** Every prompt dispatch gets a monotonically increasing accept sequence number (`acceptSeqGen`). `BeginAccepted()` increments the counter and returns a handle. `Cancel()` records a high-water mark at the current sequence. On entry, `Run()` checks if the handle's sequence is at or below the mark → cancel-on-entry. Queue-drain also checks sequences to drop only covered prompts while keeping post-cancel prompts alive. This means cancel is lossless, race-free, and compositional -- a user can cancel a busy session, immediately send a new prompt, and the new prompt runs correctly.
- **Evidence:**
  - Code-level validation: the pattern is implemented in `internal/agent/agent.go` with explicit sequence tracking, cancel marks, queue draining logic, and background cleanup contexts with 5s timeouts.
  - No published race-condition bug reports in Crush's agent dispatch layer (despite supporting concurrent prompts, cancellations, and queueing).
  - Lossless cancel means a cancelled prompt with a RunID still gets a terminal `RunComplete` event so callers don't hang.
- **Maturity:** Production deployed (Crush). This is an industrial-grade concurrency primitive that most CLI assistants lack. Directly transferable as a ~200-line implementation.

### Technique 12: Side Questions as Non-Interrupting Ephemeral Context Queries
- **Sources:** Claude Code Interactive Mode [docs: code.claude.com/docs/en/interactive-mode]
- **Mechanism:** The `/btw` (by-the-way) mechanism allows users to query the LLM's existing context without adding to conversation history and without interrupting a running turn. It is the inverse of a subagent: full context, zero tools. The answer is ephemeral (not stored in history) and forkable into a real session. Reuses parent prompt cache for minimal cost.
- **Evidence:**
  - Production deployed in Claude Code. Architecture: context reuse without tool dispatch, ephemeral overlay rendering, fork-to-session bridge.
  - This is an inverse-subagent pattern: where subagents have no context but full tools, `/btw` has full context but no tools. Together they form a complete delegation spectrum.
- **Maturity:** Production deployed (Claude Code). The concept is simple but the UX impact is high -- it unblocks "quick answer" paths that currently force users to either flood history or open a separate agent.

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy/Quality | Latency | Memory/Context Cost | Implementation Complexity | Scalability | Evidence Strength |
|-----------|-----------------|---------|---------------------|--------------------------|-------------|-------------------|
| **Dual Grounding (Visual+Semantic)** | 12-14% SR on OSWORLD (vs. 5-6% visual-only). Gap to human: 60pp | +1-2s per observation for SoM annotation + VLM inference | 6K tokens/obs (a11y tree, 90th pctl); screenshot tokens model-dependent | High: requires vision encoder + a11y tree parser + SoM overlay + fusion logic | Low: per-OS APIs (AT-SPI2, UIA), per-app compliance | Strong: 27 frameworks surveyed, 2 major benchmarks |
| **Operator Abstraction** | Cross-platform: 0.70 correlation Ubuntu→Windows | VLM-dependent (operator adds near-zero latency) | Zero incremental context cost | Low: ~200 lines of TypeScript interface + abstract classes | High: add operators without changing agent loop | Strong: 4+ production implementations |
| **Execution-Based Eval (r_prog)** | 100% on date-format equivalence (judge). Deterministic, no LLM cost | Instant (DB query / API call) | Zero (no LLM judge needed for core metric) | High: per-task evaluator engineering (134 unique functions for OSWORLD) | Medium: per-task cost, ~400 man-hours for OSWORLD | Strong: 3 independent benchmarks converge |
| **pass^k Reliability** | pass^8 < 25% for gpt-4o (vs. pass^1 = 61%). Reveals 36pp hidden fragility | Zero (post-hoc metric) | Zero (post-hoc) | Low: combinatoric counter, k independent runs | Medium: k × cost multiplier per task | Medium: 2 papers, same lab (Sierra). No third-party adoption yet |
| **CER (Context-Window Experience Replay)** | +51% relative over baseline on WebArena. 93% stability, 141% plasticity | +5.8% - 17.3% token overhead. LLM retrieval prompt latency | Buffer grows unboundedly; retrieval cap at k_d=5 + k_s=5 | Low: pure prompt engineering, no embeddings/training | Medium: buffer growth unbounded over long streams | Strong: 2 benchmarks (WebArena, VisualWebArena), 3 settings (offline/online/hybrid) |
| **Inner Monologue (DAVIS)** | 1.8× over baselines on ScienceWorld (65.06 vs 33.64). Wins 8/9 subjects | $0.43/action, $43/episode (GPT-4o). Up to k=5 LLM turns per action | 43K tokens/action (send+receive) | Very High: TKG construction (CoreNLP+LLM parsing+temporal reorder) | Low: TKG grows, retrieval slows. KG dependency bias on novel scenarios | Medium: 1 paper, 3 benchmarks. Strong results but cost-prohibitive |
| **MCTS Architecture Search (AFlow)** | +5.7% over human designs, +19.5% over prior automated method | 100 evaluations per search (20 iterations × 5). Requires Claude-3.5-sonnet as optimizer | Search overhead significant upfront, inference-time cost can be 4.55% of GPT-4o | Very High: MCTS tree + code-represented workflows + LLM optimizer | Medium: per-task optimization, no transfer learning | Strong: 6 benchmarks. MCTS pattern validated by 3+ papers |
| **Progressive Skill Loading** | No quantitative ablation published | Near-zero: YAML frontmatter parse at load time | Major context savings: M tools × O tokens → 0 if deferred | Low: Markdown-file format is trivial. Deferred tool registry requires search/promote mechanism | High: skills scale independently of context budget | Medium: 4+ independent implementations converge on pattern, no formal benchmark |

---

## 3. Convergences

Where do multiple independent sources agree? These are the safe bets for Lyra.

### Convergence 1: Accessibility Tree + Screenshot is the Consensus Perception Mode
**Sources:** OS Agents Survey (ACL 2025), OSWORLD (arXiv 2024), WebArena (ICLR 2024), UI-TARS-desktop (bytecode), CER (2025)
- All major research systems and production tools converge on the same observation space: structured element trees (accessibility tree or filtered DOM) combined with pixel-based screenshots.
- Visual-only fails on semantically identical elements (two similar-looking buttons); semantic-only fails on spatial layout and visual state (colors, icons, positions).
- WebArena's accessibility tree with unique element IDs transforms element selection from coordinate prediction to n-way classification -- a provably easier problem for LLMs.
- **Lyra implication:** Do not choose between visual and semantic; implement both. Start with accessibility APIs (AT-SPI2 on Linux, UIA on Windows, NSAccessibility on macOS) and add screenshot-based grounding when needed.

### Convergence 2: Agent Logic Must Be Separated from Execution Environment
**Sources:** UI-TARS-desktop (Operator interface), OSWORLD (pyautogui code generation), OpenHands (SandboxService ABC), OpenGUI (HarnessCapabilities), OpenCode (event-sourced session runtime)
- Every mature system independently converges on the same architectural pattern: an abstract action-execution boundary separating reasoning logic from environment-specific implementation.
- The interface is always minimal: capture state (screenshot, a11y tree, file read), execute action (mouse, keyboard, bash, API call).
- This enables: (a) testing with mock operators, (b) porting across platforms, (c) sandboxing for safety.
- **Lyra implication:** Define a `LyraOperator` interface with `observe()` and `execute()` methods. Implement for terminal (bash), desktop (a11y+pyautogui), and web (Playwright). Route through a sandbox for untrusted operations.

### Convergence 3: Skills/Tools Should Be Deferred, Not Always-Loaded
**Sources:** DeerFlow (18-middleware chain, progressive skill loading), Claude Code (skills loaded on demand), Cline (modular system prompt with deferred MCP tools), OpenHands (skills loaded at sandbox start)
- All four independent projects converge on the same design: tools and skills are NOT loaded into the system prompt eagerly. They are listed by name/description only, with full content injected on demand.
- The economic argument is consistent: context budget is the scarcest resource; MCP servers with 40+ tools would dominate the context window if loaded eagerly.
- **Lyra implication:** Adopt the SKILL.md format (Markdown + YAML frontmatter). Maintain a deferred tool registry. Inject tool schemas only when the agent queries for them or when a task classifier predicts relevance.

### Convergence 4: Functional Correctness Beats Trajectory Matching for Evaluation
**Sources:** WebArena (r_prog state inspection), OSWORLD (execution-based with 134 getter→evaluator pipelines), tau-bench (DB-state comparison)
- All three major benchmarks independently reject action-sequence matching in favor of end-state verification. The rationale is consistent: complex tasks have many valid execution paths, and penalizing alternative valid trajectories is both unfair and unscalable.
- **Lyra implication:** Build a `StateInspector` abstraction (locators + predicates). For each benchmark task, define: (1) how to retrieve goal-relevant state, (2) what must be true about it. This is path-agnostic, objective, and reproducible.

### Convergence 5: Terminal-Native TUI is the Preferred Primary Surface for Developer Agents
**Sources:** Crush (Go + Bubble Tea TUI), Claude Code (terminal-first, IDE-supplementary), OpenCode (CLI + TUI), Cline (CLI + VS Code + JetBrains + SDK)
- Every production coding agent converges on the terminal as primary surface, with IDE/Web/Desktop as secondary. The rationale: zero-config startup, composability with Unix pipelines, no Electron/WebView overhead, works in SSH/CI/headless environments.
- Terminal UI frameworks: Bubble Tea (Go, Crush), OpenTUI (TypeScript, Cline), custom (Claude Code).
- **Lyra implication:** Terminal-first with TUI. Support headless mode for CI/CD. Add web/desktop surfaces later as thin rendering layers over the same engine protocol.

---

## 4. Contradictions

Where do sources disagree? These need arbitration in Phase 4 plans.

### Contradiction 1: Set-of-Marks Effectiveness -- Better or Worse than Screenshot+A11y?
- **For SoM:** OS Agents Survey identifies SoM as a key grounding strategy. OSWORLD shows SoM helps coordinate grounding.
- **Against SoM:** OSWORLD results: SoM with GPT-4V (11.77%) is **worse than** Screenshot+A11y with GPT-4V (12.17%) and worse than A11y-only with GPT-4 (12.24%). SoM degrades on dense UIs: professional software (spreadsheets, GIMP, VS Code) has too many elements for numbered bounding boxes. At cell-level operations, bounding boxes are insufficient.
- **Resolution needed:** Is SoM worth implementing for Lyra, or should Lyra skip directly to dual-grounding (screenshot + a11y tree)? The OSWORLD data suggests SoM underperforms on real OS tasks. But WebArena (web-only) uses element IDs (a form of SoM) effectively. The contradiction may be domain-specific: SoM works for web pages (10s of elements) but breaks on desktop apps (100s of elements). Phase 4 should test SoM specifically on Lyra's target domains.

### Contradiction 2: Pure Vision vs. Hybrid Structural Access
- **For pure vision (screenshot-only):** UI-TARS-desktop argues that screenshots work on **any** GUI universally -- desktop apps, browsers, games, terminals -- with no platform-specific API. This is the "teach the model to see" philosophy.
- **For hybrid (a11y tree + screenshot):** OS Agents Survey, OSWORLD, and WebArena all converge on hybrid being superior. A11y tree provides element identities and states that pure vision struggles to infer (is this button disabled? what is this unlabeled icon?).
- **Resolution needed:** OSWORLD data shows pure screenshot (5.26% GPT-4V) is categorically worse than a11y (12.24% GPT-4) and Screenshot+A11y (12.17% GPT-4V). However, a11y trees are only available on OSes with accessibility APIs (not all apps comply). Lyra should prioritize hybrid where APIs exist, fall back to pure vision where they don't.

### Contradiction 3: Model Training vs. Agent Framework (Embed Capability in Weights or Prompts?)
- **For foundation models (train):** OS Agents Survey catalogs 27 fine-tuned models (CogAgent, Ferret-UI, ShowUI, OS-Atlas, AutoGLM) achieving better grounding accuracy and OOD generalization. CogAgent uses a dedicated high-res encoder (1120x1120) for small text/icons.
- **For agent frameworks (prompt):** SeeAct, OS-Copilot, WebVoyager, CER use zero-shot prompting with no fine-tuning. CER achieves +51% relative improvement with pure prompt engineering. Training-free methods are immediately deployable and model-agnostic.
- **Resolution needed:** The survey identifies this as the central unresolved tension in the field. For Lyra Phase 4: start with training-free methods (CER, dual-grounding prompts). Invest in model fine-tuning only if the gap to production requirements cannot be closed with prompting alone.

### Contradiction 4: Context-Window Memory vs. External Vector Memory for Experience
- **For context-window memory:** CER and ReasoningBank both argue that in-context replay is sufficient, simpler, and avoids embedding infrastructure. CER: +51% improvement with zero embeddings. ReasoningBank: 4.3% token overhead with simple additive consolidation.
- **For external memory:** DAVIS, ReflecTool, and DITS advocate for structured external stores (Temporal KG, tool-wise experience banks, influence-scored experience buffers). DAVIS: 1.8× improvement with TKG over baselines. ReflecTool: 12-72× reduction in tool selection errors with persistent per-tool experience.
- **Resolution needed:** This is not a binary choice. CER shows context-window replay is the pragmatic starting point (low cost, immediate benefit). DAVIS shows that for complex multi-hop reasoning, structured external memory provides multiplicative gains. Lyra should implement CER-style in-context replay first (Phase 4, Sprint 1), then layer DAVIS-style structured retrieval for high-value paths (Phase 4, Sprint 3+).

---

## 5. Open Problems

What problems does NO source solve yet? These are research opportunities.

### Problem 1: Human-Performance Gap Remains Catastrophic
- OSWORLD: best agent 12.24% vs. human 72.36% (gap: 60pp)
- WebArena: best agent 14.41% vs. human 78.24% (gap: 64pp)
- Even with CER (+51% relative improvement), the absolute performance on WebArena is 36.7% -- still far below human.
- No source proposes a credible path to close the remaining 60+pp gap. This is the defining open problem of GUI agent research.

### Problem 2: Safety Monitoring During Self-Evolution
- The misevolution paper (2509.26354v2, ICLR 2026) shows safety degrades across ALL evolutionary pathways (model, memory, tool, workflow), even with benign training data, and even for top-tier models (GPT-5, Gemini-2.5-Pro, Claude-4-Sonnet).
- Tool-creation agents fail to detect malicious external code 92.7%+ of the time.
- Available mitigations (DPO post-training, prompt injection) only partially recover safety -- none restore it to pre-evolution levels.
- No source provides a unified safety framework for continuously evolving agents with GUI access.

### Problem 3: Cross-Platform Generalization
- OS Agents Survey explicitly identifies cross-platform generalization as unsolved (OS-Atlas attempts it but results are limited).
- OSWORLD: Ubuntu-trained agents show 0.70 correlation to Windows but absolute Windows performance is worse (2.55% vs. 4.88% screenshot-only).
- No model generalizes from web to desktop to mobile without platform-specific training or prompting.

### Problem 4: Screenshot-Only Temporal Understanding
- OSWORLD explicitly finds that "current VLMs cannot extract temporal context from image sequences," making pure-vision agents unable to use past observations effectively.
- Screenshot-only history encoding is broken: VLMs treat each screenshot independently rather than as a temporal sequence.
- No architecture solves video-level understanding of GUI interaction sequences.

### Problem 5: Cold-Start Experience (Zero-Shot GUI Agents)
- CER and ReasoningBank both start with empty memory buffers. Early tasks receive no benefit.
- CER's online setting requires the agent to accumulate trajectories before memory becomes useful.
- No source solves the bootstrap problem for agents encountering a completely novel GUI environment.

### Problem 6: Evaluation Reliability at Scale
- OSWORLD's 134 custom evaluation functions required ~400 man-hours of double-checking and may still have false positives/negatives.
- WebArena's per-task evaluator engineering (DB queries, JS selectors) is not scalable to arbitrary tasks.
- tau-bench's task annotation used gpt-4-turbo for tuning, creating implicit model bias in task design.
- No source provides an automated, scalable, unbiased evaluation methodology for GUI agents.

### Problem 7: Multi-Monitor and Multi-Window Coordination
- UI-TARS-desktop explicitly limits to single-monitor setups ("Multi-monitor configuration may cause failure").
- OSWORLD shows 28-50% performance drops from window position changes and 70% drops from window size changes.
- No source addresses coordinated multi-window workflows where agents must track focus, window layering, and cross-window drag-and-drop.

---

## 6. Recommendations for Lyra

Ranked by priority (P0 = launch-critical, P1 = Phase 4, P2 = post-Phase 4).

### P0: Launch-Critical (implement in current upgrade cycle)

1. **Operator Abstraction for Environment-Agnostic Execution** -- Define `LyraOperator` interface with `observe()` and `execute()`. Start with `TerminalOperator` (bash + file system). Plan for `DesktopOperator` (a11y + pyautogui) and `BrowserOperator` (Playwright) as Phase 4 additions. This is the architectural foundation for all GUI capability. Cost: ~200 lines of interface definition. Evidence: proven in 4+ production systems (UI-TARS-desktop, OSWORLD, OpenHands, OpenGUI).

2. **Output Persona Profiles** -- Adopt Claude Code's output style pattern: Markdown files with YAML frontmatter that separate tone/verbosity/decision-style from knowledge. Define at least 3 profiles (Proactive/execution, Explanatory/mentoring, Concise/debugging). Cost: trivial (~50 lines of Markdown parsing + system prompt injection). Evidence: production-validated (Claude Code), architecturally endorsed (Ahmad 2026, Ch.3, Ch.10).

3. **pass^k Reliability Gate** -- Add pass^k (k=4) to Lyra's CI/CD pipeline as a release gate. Track pass^k decay curves over time. This surfaces consistency failures that average metrics hide. Cost: moderate (requires k independent evaluation runs per task). Evidence: tau-bench's pass^8 < 25% for gpt-4o reveals fragility invisible in pass^1.

### P1: Phase 4 Priorities (implement in Phase 4 workstream)

4. **Dual-Grounding Perception (A11y Tree + Screenshot)** -- Implement accessibility tree parsing (AT-SPI2 for Linux, UIA for Windows, NSAccessibility for macOS) paired with screenshot capture. Use Set-of-Marks overlay for web elements, element ID enumeration for desktop elements. This is the prerequisite for Lyra to interact with arbitrary GUI applications. Cost: high (platform-specific APIs, VLM integration, grounding fusion logic). Evidence: OS Agents Survey (27 frameworks), OSWORLD (12.17% dual vs. 5.26% visual-only), WebArena (accessibility tree as default).

5. **Execution-Based Evaluation with StateInspector** -- Build `StateInspector` abstraction (locators + predicates). Define per-task: (1) how to retrieve goal-relevant state, (2) what must be true. Apply to Lyra's internal evaluation suite. This replaces brittle trajectory matching with objective, path-agnostic evaluation. Cost: moderate (per-task evaluator engineering). Evidence: WebArena r_prog, OSWORLD getter/evaluator pipelines, tau-bench DB-state comparison.

6. **CER-Style Context-Window Experience Replay** -- Implement dual-channel memory (dynamics + skills) distilled from Lyra's agent trajectories. Store in grow-only buffer with redundancy checks. Retrieve top-k per task using LLM-as-retriever. This is training-free self-improvement that works across session boundaries. Cost: low (pure prompt engineering, no embeddings infrastructure). Evidence: +51% relative improvement on WebArena (CER), +20.5% on WebArena (ReasoningBank).

7. **Progressive Skill Loading with SKILL.md Format** -- Convert Lyra's skill/plugin system to Markdown files with YAML frontmatter. Defer full skill content until agent references it. Defer MCP tool schemas until explicitly queried. This directly addresses context-bloat. Cost: moderate (redesign skill loading pipeline, migrate existing skills). Evidence: DeerFlow, Claude Code, Cline, OpenHands all converge on this pattern.

8. **Accept-Sequence Dispatch** -- Implement Crush's race-free concurrent prompt handling with monotonic accept sequence numbers, cancel high-water marks, and lossless queue drain. This eliminates a class of race conditions in concurrent prompt handling. Cost: moderate (~200 lines of Go/TypeScript). Evidence: production-validated (Crush), no known race-condition bugs.

### P2: Post-Phase 4 Investigations

9. **Inner Monologue Retrieval (Lite)** -- Adapt DAVIS's multi-turn conversational retrieval pattern. Start with Lyra's existing memory stores (no full TKG construction). Let the planner query memory iteratively (up to k=3 turns) before committing to plans. Cost: moderate (LLM orchestration, no new infrastructure). Evidence: 1.8× improvement on ScienceWorld, but full DAVIS is cost-prohibitive ($43/episode).

10. **Side Questions (/btw) as Ephemeral Context Queries** -- Implement Claude Code's `/btw` pattern: full context, zero tools, ephemeral output, forkable to session. The inverse of a subagent. Cost: low (context reuse without tool dispatch). Evidence: production-validated (Claude Code).

11. **MCTS-Driven Architecture Search (Selective)** -- Extract SWE-Search's hindsight feedback mechanism (value-agent critique injected when re-expanding from parent nodes). Use only for high-stakes agent decisions (premature "done" declarations, complex multi-step plans). Avoid full MCTS infrastructure (14x cost multiplier). Cost: moderate (git-backed state tree + lightweight value agent). Evidence: +23% relative improvement on SWE-bench Lite.

12. **Continuous Safety Regression for Self-Evolving Components** -- Implement automated safety regression testing on Lyra's memory, tool-creation, and workflow-optimization loops. Test refusal behavior on HarmBench-equivalent queries before and after each self-evolution step. Apply "treat memory as reference, not rules" prompt pattern. Cost: moderate (benchmark suite + automated judge). Evidence: misevolution paper (ICLR 2026) -- safety degrades across ALL evolutionary pathways.

### Explicit Non-Recommendations (things the evidence argues AGAINST)

- **Do NOT build a custom desktop GUI framework from scratch.** The Operator abstraction (recommendation #1) is the right boundary. Build Lyra's reasoning engine; integrate existing operator implementations (nut-js, pyautogui, Playwright) rather than reinventing mouse/keyboard primitives.
- **Do NOT invest in screenshot-only perception.** OSWORLD data (5.26% GPT-4V screenshot-only) and the temporal-understanding failure (VLMs cannot extract temporal context from image sequences) make this a dead end for Lyra's near-term needs. Invest in hybrid (a11y + screenshot) instead.
- **Do NOT build an IDE-first interface.** The terminal is the consensus primary surface for developer agents (Crush, Claude Code, OpenCode, Cline). IDE/web should be supplementary rendering layers, not the primary development surface.
- **Do NOT build a custom evaluation framework.** Adopt WebArena's r_prog + OSWORLD's getter/evaluator + tau-bench's pass^k pattern. These three patterns together provide state inspection, execution-based correctness, and reliability measurement. A custom framework would add no novel capability and would lack community validation.

---

## Source Index

### Papers (primary evidence)
| ID | Title | Venue | Key contribution to this theme |
|----|-------|-------|-------------------------------|
| 2508.04482v1 | OS Agents: A Survey on MLLM-based Agents for General Computing Devices Use | ACL 2025 | Comprehensive taxonomy: perception→planning→memory→action loop, dual grounding, 27 frameworks + 27 models catalogued |
| 2404.07972v2 | OSWORLD: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments | arXiv 2024 | Real VM evaluation, pyautogui action space, 12.24% vs 72.36% human gap, execution-based evaluation |
| 2307.13854v4 | WebArena: A Realistic Web Environment for Building Autonomous Agents | ICLR 2024 | Accessibility tree observation, functional correctness via r_prog, multi-tab support, 14.41% vs 78.24% human |
| 2406.12045v1 | tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains | arXiv 2024 | pass^k reliability metric, LM-simulated users, DB-state evaluation, pass^8 < 25% for gpt-4o |
| 2506.07982v1 | tau2-bench: Dual-Control Environment | arXiv 2025 | Dec-POMDP formalization, dual-control ablation for failure diagnosis |
| 2506.06698v1 | CER: Contextual Experience Replay for Self-Improvement of Language Agents | arXiv 2025 | Training-free dual-channel memory (dynamics+skills), +51% relative improvement, 93% stability + 141% plasticity |
| 2509.25140v2 | ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory | arXiv 2025 | Structured reasoning memory, learns from failures, 4.3% token overhead, +20.5% relative improvement |
| 2410.09252v2 | DAVIS: Planning Agent with Knowledge Graph-Powered Inner Monologue | arXiv 2025 | TKG world model, inner monologue retrieval, 1.8× over baselines on ScienceWorld |
| 2410.10762v4 | AFlow: Automating Agentic Workflow Generation | arXiv 2025 | MCTS-driven architecture search, 5.7% over human designs, GPT-4o-mini beats GPT-4o at 4.55% cost |
| 2410.20285v6 | SWE-Search: MCTS and Iterative Refinement for Software Agents | ICLR 2025 | Hindsight feedback loop, +23% mean relative improvement, discriminator debate |
| 2305.14992v2 | RAP: Reasoning with Language Model is Planning with World Model | EMNLP 2023 | LLM-as-World-Model + MCTS, UCT selection, surpasses GPT-4 with LLaMA-33B |
| 2509.26354v2 | Your Agent May Misevolve: Emergent Risks in Self-Evolving LLM Agents | ICLR 2026 | Safety degradation across 4 evolutionary pathways, 65.5% tool misuse rate across 8 models |
| 2410.17657v3 | ReflecTool: Reflection-Aware Tool-Augmented Clinical Agents | arXiv 2025 | Tool-wise experience accumulation, 12-72× tool error reduction |
| 2506.02718v2 | MHGPO: End-to-End Optimization of LLM-Driven Multi-Agent Search | ACL 2026 | Critic-free RL, heterogeneous group advantage estimation, 30-40% GPU memory savings |
| 2502.00955v2 | DITS: Data Influence-Oriented Tree Search | arXiv 2026 | Influence-score-guided data selection, 46% lower GPU cost |
| 2510.18407v1 | HAP: Heterogeneous Adversarial Play in Interactive Environments | NeurIPS 2025 | Adversarial curriculum for agent training |

### Web / Repositories (implementation evidence)
| Name | URL | Key contribution to this theme |
|------|-----|-------------------------------|
| UI-TARS-desktop | github.com/bytedance/UI-TARS-desktop | Operator abstraction pattern, screenshot-inference-execute loop, action parsing |
| OpenGUI | github.com/akemmanuel/OpenGUI | Multi-harness desktop UI, capability masks, protocol decoupling |
| DeerFlow | github.com/bytedance/deer-flow | Progressive skill loading, 18-middleware chain, sandbox abstraction |
| Crush | github.com/charmbracelet/crush | Accept-sequence dispatch, terminal-native TUI, multi-provider |
| Cline | github.com/cline/cline | File-based automations, hub architecture, layered agent runtime |
| OpenCode | github.com/anomalyco/opencode | Surface-agnostic event-sourced architecture, 22 packages |
| OpenHands | github.com/All-Hands-AI/OpenHands | Sandboxed agent execution, SWE-bench 77.6% |

### Books (architectural principles)
| Title | Author/Year | Key contribution to this theme |
|-------|-------------|-------------------------------|
| 30 Agents Every AI Engineer Must Build | Ahmad 2026 | Ch.3 PTCF framework, Ch.5 cognitive architectures, Ch.10 personality as architectural layer, Ch.7 tool orchestration |
| Claude Code: The Definitive Guide to Agentic Development | Korostyshevskiy 2026 | Ch.3 context engineering, Ch.7 surface-agnostic engine, Ch.8 verification-first design, Ch.10 failure modes |
| Designing Multi-Agent Systems | Dibia 2026 | Agent topology patterns, communication protocols |

### Documentation (production patterns)
| Doc | Source | Key contribution to this theme |
|-----|--------|-------------------------------|
| Output Styles | code.claude.com/docs/en/output-styles | Persona profiles, Markdown + YAML format, keep-coding-instructions toggle |
| Interactive Mode | code.claude.com/docs/en/interactive-mode | Side questions (/btw), session recap, task lists, background bash |
