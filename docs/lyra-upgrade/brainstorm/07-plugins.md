# Brainstorm: §4.7 Plugins — Breakthrough Ideas

> Generated: 2026-06-06 | Target: Feed (B) tier of plans/07-plugins.md

## Context Review

**Synthesis findings (tools-plugins cluster):**
- No dedicated section in SYNTHESIS.md yet; synthesis focuses on memory, context, skills, swarm
- Plugins mentioned tangentially in skills/self-evolution (SkillNet auto-generation from repos/PDFs)
- Harness engineering consensus: harness quality > model selection

**Current baseline (BASELINE.md §4.7):**
- Maturity: `none`
- No plugin system exists
- Lyra has skills (YAML parser, registry, trigger matching) but skills ≠ plugins

**Existing plan (plans/07-plugins.md):**
- (A) Parity: Port Claude Code's plugin system (manifest.json, discovery, lifecycle, hot-reload, marketplace)
- Build outline: 4 weeks (loader → lifecycle → hot-reload → marketplace → sandboxing)
- Impact: 3 | Effort: 3 | Tier: (A) Parity

**Key gap:** The plan is pure parity. No (B) breakthrough tier exists yet.

---

## Breakthrough Idea 1: Self-Synthesizing Plugin Factory

### Sources Fused
1. **SkillNet** (2603.04448): Auto-generates skill packages from repos/PDFs/trajectories with 5-dimension quality scoring
2. **Hyperagents/DGM-H** (2603.19461): Self-rewriting harness, cross-domain transfer, meta-skills
3. **GEPA** (ICLR 2026 Oral): Gradient-free prompt evolution beats GRPO
4. **TF-TTCL** (2604.13552): Training-free evolution via Explore-Reflect-Steer
5. **"Is Grep All You Need?"** (2605.15184): Harness matters more than retrieval algorithm

### Mechanism

**Step-by-step:**

1. **Plugin Genesis Trigger:** User executes a workflow repeatedly (e.g., `/verify → run tests → format → commit` 5+ times). Lyra detects the pattern via execution trajectory logging.

2. **Trajectory Analysis:** SkillNet-style graph extraction identifies:
   - Tool sequence (Bash → Read → Edit → Bash)
   - Conditional branches (if tests fail, do X)
   - Shared context (same file paths, same error patterns)
   - Success/failure signals (test exit codes)

3. **Plugin Scaffolding:** Auto-generate plugin structure:
   ```python
   # lyra-plugin-verify-and-commit/
   manifest.json  # name, description, version, triggers, hooks
   __init__.py    # entry point
   handlers/
     pre_commit_hook.py   # hook: before Bash(git commit)
     post_test_hook.py    # hook: after Bash(pytest)
   tools/
     verify_tool.py       # tool: combines test + format + verify
   ```

4. **Quality Scoring:** GEPA-style gradient-free evaluation across 5 dimensions:
   - **Correctness:** Does the synthesized plugin reproduce the manual workflow outcome?
   - **Efficiency:** Token cost vs manual (target: 50% reduction via one-shot tool vs multi-turn)
   - **Robustness:** Success rate across 10 similar tasks
   - **Composability:** Can the plugin be chained with others?
   - **Explainability:** Can the plugin generate a human-readable trace?

5. **Iterative Refinement:** TF-TTCL Explore-Reflect-Steer loop:
   - **Explore:** Try the auto-generated plugin on 3 similar tasks
   - **Reflect:** Compare outcomes to manual baseline (GEPA scoring)
   - **Steer:** Mutate plugin (add error handling, parameterize hardcoded paths, merge redundant steps)
   - Repeat 3 rounds or until 95% baseline parity

6. **User Review Gate:** Present synthesized plugin to user:
   ```
   Lyra detected you've run "verify + commit" 5 times.
   I synthesized a plugin: lyra-plugin-verify-commit
   Preview: [show manifest + key code]
   Quality: Correctness 98% | Efficiency +52% tokens | Robustness 9/10
   Install? [y/n/edit]
   ```

7. **Marketplace Push (Optional):** If user accepts + opts in, anonymize and publish to plugins.lyra.dev with community voting.

### Why It Beats Baseline

**vs BASELINE.md (§4.7 maturity: none):**
- Baseline has NO plugin system
- This adds plugin system + auto-synthesis from user behavior
- Converts repeated manual work into reusable automation without manual plugin authoring

**vs Existing Plan (parity port):**
- Parity plan requires manual plugin creation (user writes manifest.json + Python code)
- This auto-generates plugins from execution traces
- Example: User runs same 5-command workflow 3 times → Lyra offers a one-click plugin
- Token efficiency: 50%+ reduction on repeated workflows (one tool call vs 5+ turn conversation)

**vs Claude Code (reference implementation):**
- Claude Code plugins are manually authored and installed from marketplace
- This enables in-session learning: Lyra watches you work, offers automation
- Harness-first insight (§3.28): The plugin's tool/hook integration matters more than LLM smarts — auto-synthesis focuses on harness quality (correct hook placement, proper tool chaining)

### Impact × Effort

**Impact: 8/10**
- Transforms repetitive workflows into installable automation
- Builds plugin marketplace organically (users share auto-generated plugins)
- Differentiates Lyra from Claude Code (they have plugins; we have self-learning plugins)

**Effort: 7/10 (HIGH)**
- Requires: Trajectory logger (2 weeks), SkillNet-style graph extraction (3 weeks), plugin scaffolding codegen (2 weeks), GEPA scorer (2 weeks), TF-TTCL refinement loop (2 weeks), user review UI (1 week)
- Total: ~12 weeks (3× longer than parity plan)
- Dependencies: Needs baseline plugin system (parity plan) as foundation

**Net ROI: Medium-High**
- 3× effort, but creates compounding value (each user contributes synthesized plugins to marketplace)
- Best as Phase 2 (ship parity plugin system first, add auto-synthesis as v2 feature)

### Failure Modes

1. **Over-generalization:** Plugin synthesized from 3 similar tasks fails on 4th because it hardcoded assumptions
   - **Mitigation:** Parameterize all file paths, tool names, error patterns during scaffolding; require 10-task validation before offering to user

2. **Low adoption:** Users don't trust auto-generated code
   - **Mitigation:** Show full plugin source in review UI; allow edit-before-install; start with read-only preview mode

3. **Security:** Auto-generated plugin contains unsafe operations (rm -rf, curl to unknown domain)
   - **Mitigation:** Sandbox auto-generated plugins in restricted subprocess (same as parity plan); allowlist safe operations (Bash commands, file ops within project dir only); flag destructive ops for manual review

4. **Noise:** False positives (Lyra offers plugins for one-off workflows)
   - **Mitigation:** Require 5+ repetitions with 80%+ similarity before triggering synthesis; let user disable auto-synthesis per-project

5. **Quality variance:** GEPA scoring is approximate (gradient-free means no ground-truth feedback)
   - **Mitigation:** Use human feedback loop — if user rejects synthesized plugin, log rejection reason and retrain scorer heuristics offline

---

## Breakthrough Idea 2: Hot-Swappable Multi-Provider Plugin Compatibility Layer

### Sources Fused
1. **Claude Code Plugins** (§3.1): Manifest format, lifecycle hooks, hot-reload
2. **Kilo Marketplace** (§3.2): Curated skills/MCP servers packaged as plugins
3. **Lyra Router/Economics** (SYNTHESIS §4): Multi-provider support (Anthropic/DeepSeek/GPT/open-weights)
4. **RouteLLM** (2406.18665): Lightweight router predicts best LLM per task
5. **BEST-Route** (2506.22716): Dynamic difficulty estimation for model selection

### Mechanism

**Step-by-step:**

1. **Provider-Agnostic Plugin API:** Define a plugin interface that abstracts provider-specific details:
   ```python
   # Plugin manifest.json
   {
     "name": "lyra-plugin-code-review",
     "tools": [
       {
         "name": "review_diff",
         "capabilities_required": ["code_analysis", "streaming"],
         "fallback_chain": ["claude-opus-4", "deepseek-v3", "gpt-4"]
       }
     ],
     "hooks": [
       {
         "type": "PostToolUse",
         "when": "tool == 'Edit'",
         "handler": "handlers/post_edit.py",
         "min_context_window": 32000
       }
     ]
   }
   ```

2. **Capability Declaration Per Provider:** Router maintains `ProviderCapabilityMap`:
   ```python
   PROVIDER_CAPS = {
     "anthropic": {
       "claude-opus-4": ["code_analysis", "streaming", "thinking", "vision"],
       "claude-sonnet-4.6": ["code_analysis", "streaming", "thinking"],
     },
     "deepseek": {
       "deepseek-v3": ["code_analysis", "streaming"],  # no thinking/vision
     },
     "openai": {
       "gpt-4-turbo": ["code_analysis", "streaming", "vision"],
     }
   }
   ```

3. **Plugin Validation at Load Time:** When plugin is activated:
   - Check `capabilities_required` against current active provider
   - If provider lacks capability, warn user: `"Plugin 'code-review' requires 'thinking' but DeepSeek doesn't support it. Fallback to Claude?"`
   - Auto-route to fallback_chain[0] if available

4. **Hot-Swap on Provider Change:** When user switches provider mid-session (`/provider deepseek`):
   - Re-validate all active plugins
   - Deactivate incompatible plugins (log: "Deactivated 'vision-analyzer' — DeepSeek lacks vision")
   - Re-activate compatible plugins when switching back

5. **Cost-Aware Plugin Routing:** Integrate with BEST-Route difficulty estimation:
   - Plugin declares: `"max_cost_per_call": 0.05` (dollars)
   - Router checks: If task difficulty = "easy", use cheap model (Haiku); if "hard", escalate to Opus
   - Plugin fails gracefully if cost cap exceeded: "Task requires Opus ($0.15) but plugin budget is $0.05. Approve override?"

6. **Multi-Provider Marketplace Tags:** plugins.lyra.dev tags plugins:
   - `claude-only` (uses thinking/citations/prompt-caching)
   - `multi-provider` (works on any LLM)
   - `requires-vision` / `requires-streaming` / `requires-thinking`
   - Users filter by active provider setup

### Why It Beats Baseline

**vs BASELINE.md (§4.7 maturity: none):**
- Baseline has no plugin system AND no router
- This adds plugin system with provider-aware routing baked in

**vs Existing Plan (parity port):**
- Parity plan ports Claude Code's single-provider plugin system (Anthropic-centric)
- Lyra's multi-provider thesis requires plugins to work across Claude/DeepSeek/GPT
- This makes plugins portable: one plugin, any provider (with graceful fallback)

**vs Claude Code:**
- Claude Code plugins assume Anthropic backend
- Lyra plugins declare capabilities and route to best available provider
- Example: A "summarize-paper" plugin can use cheap DeepSeek for abstracts, escalate to Opus for complex math proofs

### Impact × Effort

**Impact: 7/10**
- Enables plugin marketplace to serve multi-provider users (not just Claude users)
- Plugins become more reusable (one plugin works across Lyra deployments with different provider setups)
- Aligns with Lyra's core differentiation (multi-provider harness)

**Effort: 5/10 (MEDIUM)**
- Requires: ProviderCapabilityMap (1 week), capability validation at plugin load (1 week), hot-swap logic (1 week), cost-aware routing integration (1 week), marketplace tag system (1 week)
- Total: ~5 weeks
- Dependencies: Needs router (§4.5) to exist first; plugin system (parity plan) as foundation

**Net ROI: High**
- Moderate effort, high strategic value (multi-provider is Lyra's moat vs Claude Code)

### Failure Modes

1. **Provider capability drift:** Provider adds new capability (e.g., DeepSeek adds vision), plugin manifest is stale
   - **Mitigation:** Periodic provider capability probing (query API for supported features); warn user if manifest is outdated

2. **Fallback chain exhaustion:** All providers in fallback_chain lack required capability
   - **Mitigation:** Plugin fails gracefully with actionable message: "This plugin requires 'vision'. Install a vision-capable provider or disable the plugin."

3. **Cost blowup:** Plugin routes to expensive model without user awareness
   - **Mitigation:** Cost cap per plugin call (manifest field); confirm with user if cap exceeded; log cost per plugin in session summary

4. **Marketplace fragmentation:** 50% of plugins tagged `claude-only`, unusable for DeepSeek users
   - **Mitigation:** Incentivize multi-provider plugins (marketplace ranks higher); provide plugin porting guide (Claude-specific features → provider-agnostic alternatives)

5. **Complexity creep:** Plugin authors must understand multi-provider nuances
   - **Mitigation:** Provide plugin scaffold CLI: `lyra plugin init --multi-provider` generates boilerplate with fallback_chain, capability checks, cost hints

---

## Breakthrough Idea 3: Real-Time Collaborative Plugin Authoring via Ghost Mode

### Sources Fused
1. **Agent View** (Claude Code internals): Peek/attach/detach UX, suggested replies, state-grouped rows
2. **Lyra Swarm/Fleet** (BASELINE §4.13): PrimaryAgent orchestration, TaskAllocator, no detached sessions yet
3. **Hyperagents/DGM-H** (2603.19461): Self-rewriting harness, meta-skills transfer
4. **Steer-by-Exception UX** (SYNTHESIS §10): Users watch states, not transcripts; cheap-model row summaries
5. **"Knowledge Access Beats Model Size"** (2603.23013): Memory lets cheap models handle repeat queries

### Mechanism

**Step-by-step:**

1. **Ghost Mode Invocation:** User types `/plugin create my-verifier` → Lyra spawns a Ghost Agent in background session

2. **Conversational Scaffolding:** Ghost Agent interviews user in split-pane TUI:
   ```
   [Left: User's work session]          [Right: Ghost Agent]
   $ lyra verify                         Ghost: What should this plugin do?
   [running tests...]                    User: Run tests, check coverage, format
                                         Ghost: Which test command? 
                                         User: pytest
                                         Ghost: Coverage threshold?
                                         User: 80%
                                         Ghost: Format tool?
                                         User: black + isort
                                         [Ghost generates plugin scaffold...]
   ```

3. **Live Preview:** Ghost Agent writes plugin files to `.lyra/plugins-wip/my-verifier/` and shows live diff in right pane:
   ```python
   # Generated: handlers/post_test.py
   def handle(context):
       result = context.tool_result
       if result.exit_code != 0:
           return "Tests failed. Aborting."
       coverage = extract_coverage(result.stdout)
       if coverage < 0.8:
           return f"Coverage {coverage:.0%} < 80%. Add tests."
       return "OK"
   ```

4. **Test-Driven Plugin Development:** Ghost Agent runs plugin in sandbox against user's actual codebase:
   - User continues working in left pane
   - Ghost Agent observes tool calls in real-time (via channels/message bus)
   - When user runs `lyra verify`, Ghost Agent's plugin hook fires in sandbox
   - Ghost Agent shows: "Plugin would have output: 'Coverage 75% < 80%. Add tests.'"

5. **Iterative Refinement:** User provides feedback in right pane:
   ```
   User: The coverage check is too strict for test files themselves
   Ghost: [updates handler to exclude test_*.py from coverage check]
   Ghost: [re-runs sandbox test]
   Ghost: "Updated. Now showing coverage for src/ only: 82%."
   ```

6. **One-Click Activation:** After 3-5 refinement rounds:
   ```
   Ghost: Plugin ready. Tested on 5 workflows. Activate? [y/n/keep-editing]
   User: y
   [Plugin moves from .lyra/plugins-wip/ to .lyra/plugins/, hot-reloaded]
   ```

7. **Memory Consolidation:** Ghost Agent's conversation history is consolidated into plugin's README.md as "Design Rationale" section:
   ```markdown
   # Design Rationale
   - Coverage threshold: 80% (user requirement, 2026-06-06)
   - Excludes test files from coverage check (test_*.py pattern)
   - Format tools: black + isort (user's existing setup)
   ```

### Why It Beats Baseline

**vs BASELINE.md (§4.7 maturity: none):**
- Baseline has no plugin system, no ghost agents, no TUI
- This adds plugin system + AI pair-programming for plugin authoring

**vs Existing Plan (parity port):**
- Parity plan requires user to manually write manifest.json + Python handlers
- This reduces plugin authoring to a conversation: user describes intent, Ghost Agent codes
- Lowers barrier to entry: non-Python users can create plugins

**vs Idea 1 (Self-Synthesizing Factory):**
- Idea 1 is passive (watches behavior, offers automation)
- Idea 3 is active (user explicitly requests plugin, Ghost guides authoring)
- Idea 1 = auto-extract patterns; Idea 3 = co-create custom logic
- Complementary, not competing

**vs Claude Code:**
- Claude Code requires leaving the harness to write plugin code
- Lyra's Ghost Mode keeps user in flow: work session in left pane, plugin dev in right pane
- Leverages Lyra's swarm/fleet architecture (Ghost Agent = background session)

### Impact × Effort

**Impact: 6/10**
- Democratizes plugin authoring (non-coders can create plugins via conversation)
- Sticky feature (users emotionally invest in co-created tools)
- Drives marketplace growth (more users = more plugins)

**Effort: 8/10 (HIGH)**
- Requires: Split-pane TUI (2 weeks), Ghost Agent session management (2 weeks), plugin sandbox testing (2 weeks), live diff preview (1 week), message bus for inter-agent observation (2 weeks), memory consolidation into README (1 week)
- Total: ~10 weeks
- Dependencies: Needs parity plugin system, fleet/swarm infrastructure (supervisor daemon §4.13), TUI framework (§4.1)

**Net ROI: Medium**
- High effort, medium impact
- Best as Phase 3 feature (after parity plugins + fleet mature)

### Failure Modes

1. **Ghost Agent misunderstands intent:** User says "verify", Ghost Agent builds plugin that only runs tests (misses coverage/format)
   - **Mitigation:** Multi-turn clarification (Ghost asks 3-5 scoping questions before coding); show generated code for approval at each step

2. **Sandbox escape:** Plugin under development accesses user's real files instead of sandbox copy
   - **Mitigation:** Strict sandbox isolation (temp directory, read-only mount of real codebase, no network access); same sandboxing as parity plan

3. **UX clutter:** Split-pane TUI distracts from main work
   - **Mitigation:** Ghost Mode is opt-in (user invokes `/plugin create`); can detach right pane (Ghost continues in background, notifies when ready); minimalist UI (1-line status in main pane: "Ghost building plugin: 60% done")

4. **Ghost Agent gets stuck:** User's requirements are ambiguous, Ghost loops asking questions
   - **Mitigation:** Timeout after 10 clarification questions → fallback to manual editing (Ghost generates partial plugin, user finishes in IDE)

5. **Memory bloat:** Plugin authoring conversation fills memory
   - **Mitigation:** Ghost Agent has separate ephemeral memory (cleared after plugin activation); only design rationale persists to README

---

## Stress-Test Comparison

| Criterion | Idea 1: Self-Synth Factory | Idea 2: Multi-Provider Compat | Idea 3: Ghost Mode Authoring |
|-----------|----------------------------|-------------------------------|------------------------------|
| **Beats baseline?** | ✅ (none → auto-gen) | ✅ (none → multi-provider) | ✅ (none → AI co-creation) |
| **Cites sources?** | ✅ (SkillNet, GEPA, DGM-H, TF-TTCL, Grep) | ✅ (Claude Code, RouteLLM, BEST-Route) | ✅ (Agent View, DGM-H, Knowledge Access) |
| **Effort realistic?** | ⚠️ (12 weeks, complex) | ✅ (5 weeks, moderate) | ⚠️ (10 weeks, complex) |
| **Impact measurable?** | ✅ (50% token reduction on repeat workflows) | ✅ (multi-provider plugin usage %) | ⚠️ (qualitative: user satisfaction) |
| **Failure mitigated?** | ✅ (5 mitigations listed) | ✅ (5 mitigations listed) | ✅ (5 mitigations listed) |
| **Strategic fit?** | ⚠️ (competes with skills self-evolution §4.3) | ✅ (aligns with Lyra multi-provider moat) | ⚠️ (requires fleet/TUI dependencies) |
| **Minimal-change test?** | ❌ (no simpler alternative) | ✅ (start with single-provider, add fallback_chain incrementally) | ✅ (start with CLI wizard instead of TUI) |

**Winner (feasibility × impact):** **Idea 2 (Multi-Provider Compatibility Layer)**

**Reasoning:**
- Moderate effort (5 weeks), clear value (multi-provider is Lyra's differentiation)
- Incremental path exists (start single-provider, add fallback logic progressively)
- No competing workstreams (§4.5 router and §4.7 plugins are complementary)
- Measurable success criteria (% of plugins tagged `multi-provider`, cost savings from smart routing)

---

## Recommendations for plans/07-plugins.md (B) Tier

### Promote Idea 2 to (B) Breakthrough

**Update plans/07-plugins.md with:**

```markdown
## (B) Breakthrough: Multi-Provider Plugin Compatibility Layer

### Design
- Plugin manifest declares `capabilities_required` (vision, thinking, streaming, etc.)
- Plugin manifest includes `fallback_chain` (preferred providers in order)
- Router validates capabilities at plugin load time
- Hot-swap: re-validate plugins when user switches provider mid-session
- Cost-aware routing: plugin declares `max_cost_per_call`, router escalates only if needed

### Build Outline
1. Define `ProviderCapabilityMap` in router (week 1)
2. Plugin manifest schema: add `capabilities_required`, `fallback_chain`, `max_cost_per_call` (week 1)
3. Capability validation at plugin load + hot-swap logic (week 2)
4. Cost-aware routing integration with BEST-Route difficulty estimation (week 3)
5. Marketplace tagging system (`claude-only`, `multi-provider`, `requires-vision`) (week 4)
6. Plugin porting guide + `lyra plugin init --multi-provider` scaffold CLI (week 5)

### Evidence
- RouteLLM (2406.18665): Lightweight router predicts best LLM per task
- BEST-Route (2506.22716): Dynamic difficulty estimation for model routing
- Lyra's multi-provider thesis (BASELINE constraint): Must work across Claude/DeepSeek/GPT
- Harness-first consensus (SYNTHESIS §Cross-Cutting): Harness quality > model selection

### Impact: 7 | Effort: 5 | Net ROI: High
```

### Park Idea 1 and 3 for Later Phases

- **Idea 1 (Self-Synth Factory):** High value but competes with §4.3 Skills self-evolution. Revisit after skills + plugins both mature (Phase 3+).
- **Idea 3 (Ghost Mode):** Requires §4.13 Fleet and §4.1 TUI as dependencies. Revisit when those ship (Phase 4+).

---

## Final Synthesis

The breakthrough for §4.7 Plugins is **multi-provider compatibility as a first-class design constraint**. Claude Code's single-provider plugin model won't differentiate Lyra. By baking provider-awareness into the plugin manifest and routing layer, Lyra's plugins become:
1. More reusable (one plugin, any provider)
2. Cost-optimized (auto-route to cheap model when safe)
3. Gracefully degradable (fallback chain when preferred provider unavailable)

This aligns with Lyra's core thesis (multi-provider harness) and has moderate implementation cost (~5 weeks on top of 4-week parity baseline). Ship parity plugin system first (A tier), then layer multi-provider compatibility as breakthrough (B tier).
