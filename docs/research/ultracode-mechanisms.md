# Ultracode / Orchestration Stack: Complete Mechanism Extraction

> Deep-research of Claude Code's full ultracode/orchestration stack for Lyra replication.
> Sources: 7 official documentation pages + 1 supplementary API guide, fetched 2026-06-01.

---

## Table of Contents

1. [Primitive 1: Effort Menu](#primitive-1-effort-menu)
2. [Primitive 2: Auto-Orchestration Toggle](#primitive-2-auto-orchestration-toggle)
3. [Primitive 3: Dynamic-Workflow Engine](#primitive-3-dynamic-workflow-engine)
4. [Primitive 4: Adversarial Quality Pattern](#primitive-4-adversarial-quality-pattern)
5. [Cross-Cutting: Subagent Architecture](#cross-cutting-subagent-architecture)
6. [Cross-Cutting: Agent Teams](#cross-cutting-agent-teams)
7. [Cross-Cutting: Channels (Inter-Agent Comms)](#cross-cutting-channels-inter-agent-comms)
8. [Lyra Transfer Blueprint](#lyra-transfer-blueprint)

---

## Primitive 1: Effort Menu

### Exact Levels

There are **5 API-level effort values** plus **1 Claude-Code-only composite**:

| # | Level | API Value | API Scope | Claude Code Scope |
|---|-------|-----------|-----------|-------------------|
| 1 | `low` | `output_config.effort = "low"` | All supported models | All supported models |
| 2 | `medium` | `output_config.effort = "medium"` | All supported models | All supported models |
| 3 | `high` | `output_config.effort = "high"` (default) | All supported models | All supported models |
| 4 | `xhigh` | `output_config.effort = "xhigh"` | NextOpus (4.8), Opus 4.7 only | Opus 4.8, Opus 4.7 |
| 5 | `max` | `output_config.effort = "max"` | NextOpus, Mythos Preview, Opus 4.7, Opus 4.6, Sonnet 4.6 | Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 4.6 |
| 6* | `ultracode` | **NOT an API level** | N/A | Claude Code session-only composite |

*`ultracode` is NOT a 6th API budget tier. It is `xhigh` effort + auto-orchestration toggle, applied only at the Claude Code harness level. The API never receives `"ultracode"` as an effort value.

### Model Support Matrix

| Model | Supported Effort Levels | Default | Thinking Mechanism |
|-------|------------------------|---------|-------------------|
| Opus 4.8 (NextOpus) | low, medium, high, xhigh, max | high | Adaptive thinking (mandatory; `budget_tokens` returns 400) |
| Opus 4.7 | low, medium, high, xhigh, max | xhigh | Adaptive thinking (mandatory; `budget_tokens` not supported) |
| Opus 4.6 | low, medium, high, max | high | Adaptive thinking (recommended; `budget_tokens` deprecated) |
| Sonnet 4.6 | low, medium, high, max | high | Adaptive thinking (recommended; interleaved manual thinking deprecated) |
| Opus 4.5 | Not supported via effort | N/A | Manual thinking (`budget_tokens` required) |

Fallback rule: If a level is unsupported, Claude Code falls back to the highest supported level at or below the requested one. Example: `xhigh` on Opus 4.6 runs as `high`.

### API Wire Format

```json
{
  "model": "claude-opus-4-8",
  "max_tokens": 64000,
  "thinking": {"type": "adaptive"},
  "output_config": {"effort": "xhigh"},
  "messages": [...]
}
```

Key: `output_config.effort` is the single field. There is no `budget_tokens` or `reasoning_effort` on Anthropic-native calls. The effort value controls ALL token spend: text output, tool calls, AND thinking depth. This is the crucial architectural decision -- one parameter governs total spend, not just reasoning budget.

### Per-Provider Mapping

#### Anthropic (api.anthropic.com)
- **Mechanism**: `output_config.effort` + `thinking: {type: "adaptive"}`
- **Budget tokens**: Deprecated on Opus 4.6+, removed on Opus 4.7+. Replaced entirely by effort.
- **Interleaved thinking**: Deprecated on Sonnet 4.6. Adaptive thinking with effort is the sole recommended path.
- **Redaction**: Thinking output is redacted by default in interactive sessions; set `showThinkingSummaries: true` for full summaries.

#### OpenAI (via LLM gateway or custom integration)
- **Mechanism**: `reasoning_effort` parameter on reasoning models (o1, o3, etc.)
- **Mapping**: No automatic translation. Must be manually mapped: `low` -> `reasoning_effort: "low"`, `xhigh` -> `reasoning_effort: "high"`
- **Caveat**: OpenAI's `reasoning_effort` affects only reasoning tokens, not tool-call verbosity. Anthropic's effort affects both. This is a semantic gap.

#### DeepSeek (via prompt instruction)
- **Mechanism**: No native effort API. Effort is conveyed through system prompt instructions.
- **Approach**: Inject directives like "Think step by step. Be thorough. Consider multiple approaches before answering."
- **Caveat**: Entirely prompt-based; no token-budget control. Model may over- or under-think regardless of instruction.

#### Google (Vertex AI / Gemini)
- **Mechanism**: Gemini 2.5 Pro supports a thinking budget via `thinkingConfig`. No direct effort parameter.
- **Mapping**: Effort must be translated to `thinkingConfig.thinkingBudget` + includeThoughts boolean.
- **Caveat**: Gemini's thinking budget is a fixed token allocation, not an adaptive behavioral signal. Different semantics.

#### Open-Weight Models (Llama, Mistral, etc.)
- **Mechanism**: System prompt instruction only. No API-level control.
- **Approach**: "Think carefully and thoroughly" / "Be concise and direct" variations.
- **Caveat**: No guarantee of compliance. Model-dependent behavior.

### Session Persistence Rules

| Level | Persists Across Sessions? | Set Via |
|-------|--------------------------|---------|
| `low` | **Yes** | `/effort low`, `effortLevel` in settings, `--effort low`, `CLAUDE_CODE_EFFORT_LEVEL=low` |
| `medium` | **Yes** | Same as above |
| `high` | **Yes** (and is default) | Same as above |
| `xhigh` | **Yes** | Same as above |
| `max` | **Session-only** (except via env var) | `/effort max`, `--effort max`. If set via `CLAUDE_CODE_EFFORT_LEVEL=max`, persists as long as env var is set |
| `ultracode` | **Session-only** (never persists) | `/effort ultracode`, `--settings '{"ultracode": true}'`, Agent SDK control request. NOT accepted in `effortLevel` setting, `--effort` flag, or `CLAUDE_CODE_EFFORT_LEVEL` |

### CLI / Config Surface

```
# Interactive
/effort              # opens slider
/effort ultracode    # set directly
/effort auto         # reset to model default

# CLI flags
claude --effort xhigh
claude --settings '{"ultracode": true}'

# Environment variable (highest precedence)
CLAUDE_CODE_EFFORT_LEVEL=xhigh

# Settings file (persistent)
{ "effortLevel": "xhigh" }   # max and ultracode rejected here

# Subagent/skill frontmatter
---
effort: xhigh
---
```

Precedence order: env var > configured level > model default. Frontmatter effort overrides session level but not env var.

### Effort Semantics (Behavioral Signal, Not Budget)

Critical architectural point: Effort is a **behavioral signal**, not a strict token budget. At lower effort, Claude will still think on sufficiently hard problems, but less than at higher effort for the same problem. This is fundamentally different from `max_tokens` or `budget_tokens` which are hard ceilings.

**Effort's effect on tool use:**
- Lower effort: fewer tool calls, combined operations, direct action without preamble, terse confirmations
- Higher effort: more tool calls, explained plans, detailed summaries, comprehensive code comments

**Effort's effect on thinking:**
- Opus 4.7+ / 4.8: adaptive thinking always on. At xhigh/max: almost always thinks deeply. At low/medium: may skip thinking on simple problems.
- Opus 4.6 / Sonnet 4.6: adaptive thinking recommended. At high/max: almost always thinks. Lower: may skip.
- Opus 4.5: manual thinking only; effort not supported.

### Recommended Starting Points Per Model

| Model | Coding/Agentic | General Intelligence | Cost-Sensitive |
|-------|---------------|---------------------|----------------|
| Opus 4.8 | **xhigh** | high | medium |
| Opus 4.7 | **xhigh** | high | medium |
| Sonnet 4.6 | **medium** | high | low |

---

## Primitive 2: Auto-Orchestration Toggle

### Mechanism Overview

The auto-orchestration toggle is built from **three layered mechanisms** at the API level, plus a **keyword trigger** at the Claude Code level.

### Layer 1: Mid-Conversation System Messages (API)

This is the core enabling mechanism. Claude Code uses mid-conversation system messages (placed AFTER the user turn) to toggle orchestration mode without breaking prompt cache on the static `system` field.

**Static system prompt** (never changes, fully cached):
```
You are a helpful general-purpose agent. Answer the user's request directly.
```

**Mode entry message** (sent once, after user turn, when mode activates):
```
Orchestration mode is on: optimize for the most exhaustive, correct answer rather than
the fastest or cheapest one. Use the Workflow tool on every substantive task; token cost
is not a constraint. See the Workflow tool's standing consent section and quality
patterns. Work solo only on conversational or trivial turns.
```

**Mode refresh** (sent every 10 turns while mode is active):
```
Orchestration mode is still on. Use the Workflow tool; see its standing consent section.
```

**Mode exit notice** (sent once when mode deactivates):
```
Orchestration mode is off. The Workflow tool's standard opt-in rule applies again.
```

**API message ordering:**
```json
{
  "messages": [
    {"role": "user", "content": "Explore the current directory..."},
    {"role": "system", "content": "Orchestration mode is on: optimize for the most exhaustive..."}
  ]
}
```

System messages follow the user turn they apply to. This preserves every cached byte before them in the static `system` field.

### Layer 2: Workflow Tool Description with Standing Consent (API)

The Workflow tool's description carries a behavioral contract with two modes:

```
"Opt-in: only use this tool when the user explicitly asks for a workflow, or when a
system message confirms that orchestration mode is on.

Quality patterns: adversarial verification (a second wave of agents checks the first
wave's findings against the source), a completeness critic (one agent hunts for what
the others missed), and multi-phase sequencing (understand, design, implement, and
review as separate workflow calls, reading results between phases). A useful default
is hybrid: scout inline first to discover the work-list, then fan out over it.

Standing consent: while a system message confirms orchestration mode is on, that
opt-in is standing. Author and run a workflow for every substantive task by default,
and lean toward verifying findings adversarially. Work solo only on conversational
turns or trivial mechanical edits. When a system message says the mode is off,
revert to the opt-in rule above."
```

The tool description itself encodes the quality patterns the model should use. This means the quality patterns are part of the tool contract, not a separate configuration.

### Layer 3: Mode Toggle State Machine (Client-Side)

```python
class ModeAgent:
    def __init__(self):
        self.mode_on = False
        self._mode_announced = False
        self._exit_pending = False
        self._turns_since_reminder = 0

    def set_mode(self, mode_on: bool) -> None:
        if mode_on == self.mode_on:
            return  # no-op if already in requested state
        if not mode_on:
            if self._mode_announced:
                self._exit_pending = True  # queue exit notice for next turn
        else:
            self._exit_pending = False
        self.mode_on = mode_on

    def _due_system_messages(self):
        # Returns messages in priority order
        if self._exit_pending:
            self._exit_pending = False
            self._mode_announced = False
            return [EXIT_NOTICE]
        if self.mode_on and not self._mode_announced:
            self._mode_announced = True
            self._turns_since_reminder = 0
            return [ENTRY_MESSAGE]
        if self.mode_on and self._turns_since_reminder >= TURNS_BETWEEN_REFRESHERS:
            self._turns_since_reminder = 0
            return [REFRESH_MESSAGE]
        return []
```

Key behaviors:
- Mode toggle is a **session-level client-side flag**, not an API parameter
- The Claude Code harness manages system message injection turn-by-turn
- Refresh every 10 turns prevents the model from forgetting the mode
- Exit is polite (notice sent) rather than abrupt
- Entry is announced once; subsequent `set_mode(True)` calls are no-ops

### "workflow" Keyword Trigger (Claude Code Level)

At the Claude Code harness level, including the word `workflow` in any prompt triggers workflow generation without changing the session's effort level:

```text
Run a workflow to audit every API endpoint under src/routes/ for missing auth checks
```

Claude Code highlights the word in the input. Press `alt+w` to ignore the trigger for that prompt. Backspace after the highlighted word also cancels. The trigger can be disabled entirely via `/config` (Workflow keyword trigger toggle).

### Ultracode = xhigh + Auto-Orchestration (Claude Code Composite)

Ultracode is a pure Claude Code setting. It combines:
1. Sends `effort: "xhigh"` to the API on every message
2. Grants **standing permission** for Claude to launch workflows without per-task confirmation

The API never sees `"ultracode"`. It sees `effort: "xhigh"` plus the orchestration system message pattern described above.

### How the Model Decides to Auto-Orchestrate

The decision mechanism operates through:
1. **System message priming**: The mode entry message instructs the model to "use the Workflow tool on every substantive task"
2. **Tool description contract**: The Workflow tool's description defines "substantive" implicitly through its quality patterns
3. **Model judgment**: The model evaluates task complexity and decides whether to fan-out. There is NO explicit complexity heuristic, no token-count threshold, no pre-determined trigger.
4. **`understand -> change -> verify` loop**: With ultracode on, a single user request can trigger multiple sequential workflows: one to understand the codebase, one to implement changes, one to verify correctness.

The decision is entirely model-driven. The harness provides the permission and the behavioral prompt; the model exercises judgment.

---

## Primitive 3: Dynamic-Workflow Engine

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Claude Code Session                 │
│  ┌─────────────┐   ┌────────────────────────────┐   │
│  │ Conversation │   │     Workflow Runtime        │   │
│  │   Context    │   │  ┌──────────────────────┐  │   │
│  │              │   │  │   ScriptVM (JS)       │  │   │
│  │  (isolated   │   │  │  - script variables   │  │   │
│  │   from       │   │  │  - phase orchestration│  │   │
│  │   workflow)  │   │  │  - agent spawning     │  │   │
│  │              │   │  └──────┬───────────────┘  │   │
│  │              │   │         │                   │   │
│  │  Final       │◄──┤  ┌──────▼───────────────┐  │   │
│  │  report      │   │  │  Subagent Pool        │  │   │
│  │  only        │   │  │  (max 16 concurrent)  │  │   │
│  └─────────────┘   │  │  (max 1000/run)       │  │   │
│                    │  └──────────────────────┘  │   │
│                    └────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

The workflow runtime executes a JavaScript script in an isolated environment (ScriptVM). The script coordinates subagents but has no direct filesystem or shell access itself. Intermediate results stay in script variables, not in Claude's conversation context. Only the final answer lands in the session.

### JavaScript API

Claude writes the workflow script. The runtime provides these primitives:

#### `agent(prompt, options?)` -- Spawn a Subagent

Spawns a single subagent with the given prompt. Returns a result object.

```javascript
// Single agent
const result = await agent("Analyze src/auth/ for security vulnerabilities", {
  model: "sonnet",       // model alias or full ID
  tools: ["Read", "Grep", "Glob"],  // restrict tools
  isolation: "worktree", // git worktree isolation
  effort: "high",        // per-agent effort override
  maxTurns: 20,          // max agentic turns
});

// Result object
// { output: "...", tokens: 12345, status: "completed" }
```

#### `parallel(prompts, options?)` -- Fan-Out

Runs multiple agents concurrently. Returns array of results in order.

```javascript
const results = await parallel([
  "Audit auth module",
  "Audit database layer",
  "Audit API routes",
], {
  model: "haiku",
  concurrency: 5,  // max concurrent within this batch
});
```

#### `pipeline(stages, options?)` -- Sequential Stages

Runs stages in sequence, passing results between them.

```javascript
const result = await pipeline([
  { name: "understand", prompt: "Analyze the codebase structure" },
  { name: "design", prompt: (prev) => `Design changes based on: ${prev.output}` },
  { name: "implement", prompt: (prev) => `Implement: ${prev.output}` },
  { name: "verify", prompt: (prev) => `Verify: ${prev.output}` },
]);
```

#### `phase(name, work)` -- Named Phase (for progress display)

Wraps work in a named phase for the progress view.

```javascript
await phase("Research", async () => {
  const sources = await parallel([...]);
  return sources;
});

await phase("Cross-Check", async () => {
  const verified = await parallel([...]);
  return verified;
});

await phase("Synthesize", async () => {
  return await agent("Synthesize findings into a report");
});
```

#### `log(message)` -- Log to Progress View

Logs a message visible in the progress view.

```javascript
log("Starting audit of 500 endpoints...");
```

#### `args` -- Input Arguments

The workflow receives arguments from the user's prompt or CLI invocation.

```javascript
// Access input arguments
const targetDir = args.target || "src/";
const maxDepth = args.depth || 3;
```

#### `budget` -- Token Budget Tracking

```javascript
// Check remaining budget
if (budget.remaining < 100000) {
  log("Approaching budget limit, switching to haiku");
}
```

### meta Object Schema

The workflow script exports a `meta` object:

```javascript
export const meta = {
  name: "security-audit",           // command name: /security-audit
  description: "Audit codebase for security vulnerabilities",
  phases: ["Research", "Cross-Check", "Synthesize"],  // displayed in progress view
};
```

### Execution Model

**Constraints:**

| Constraint | Value | Rationale |
|-----------|-------|-----------|
| Max concurrent agents | 16 (fewer on low-CPU machines) | Bounds local resource use |
| Max agents per run | 1,000 | Prevents runaway loops |
| No mid-run user input | Only permission prompts can pause | For sign-off between stages, run separate workflows |
| No direct filesystem/shell from workflow script | Agents read/write/run commands; script coordinates | Security boundary |
| ScriptVM isolation | Script runs in isolated JS runtime | Prevents script from affecting host |

**Threading model:**
- Workflow runs in background threads, separate from conversation
- Session stays responsive while workflow executes
- Agent results are checkpointed as they complete

**Pause/Resume/Stop/Restart (per agent):**

| Key | Action |
|-----|--------|
| `p` | Pause or resume the entire run |
| `x` | Stop selected agent, or stop whole workflow when focus is on run |
| `r` | Restart the selected running agent |

**Resume semantics:**
- Resume works within the same Claude Code session only
- Agents that already completed return cached results
- Remaining agents run fresh
- If you exit Claude Code during a workflow, the next session starts fresh (no cross-session resume)

### Progress View

```
┌──────────────────────────────────────────────────────────┐
│ Workflow: security-audit                                  │
│                                                          │
│ Phase 1: Research         12 agents  45,230 tokens  2:31 │
│ Phase 2: Cross-Check       5 agents  18,400 tokens  1:05 │
│ Phase 3: Synthesize        1 agent    8,200 tokens  0:22 │
│                                                          │
│ Total: 18 agents  71,830 tokens  3:58                    │
│                                                          │
│ p:pause x:stop r:restart s:save  ↑↓:navigate  Enter:drill│
└──────────────────────────────────────────────────────────┘
```

Navigation:
- `↑`/`↓`: Select phase or agent
- `Enter` or `→`: Drill into phase, then into agent (prompt, recent tool calls, result)
- `Esc`: Back out one level
- `j`/`k`: Scroll within agent detail when it overflows

### Script Variables (Intermediate Results)

All intermediate results live in JavaScript variables within the ScriptVM. They never enter Claude's conversation context.

```javascript
// Phase 1 results stored in script variables
const researchFindings = await phase("Research", async () => {
  return await parallel([
    "Analyze authentication flow",
    "Analyze authorization logic",
    "Analyze data validation",
  ]);
});

// Phase 2 uses Phase 1 results without polluting Claude's context
const verifiedFindings = await phase("Cross-Check", async () => {
  return await parallel(
    researchFindings.map(f =>
      `Verify this finding against the source code: ${f.output}`
    )
  );
});

// Only final result reaches Claude's context
await phase("Report", async () => {
  return await agent(`Synthesize into report: ${JSON.stringify(verifiedFindings)}`);
});
```

### Agent Isolation: Worktree Frontmatter

Agents can be isolated in git worktrees:

```yaml
---
name: code-migrator
description: Migrates code across the codebase
isolation: worktree
tools: Read, Write, Edit, Bash
---
```

When `isolation: worktree` is set:
- Subagent gets a temporary git worktree (branched from default branch by default)
- Edits are written to the worktree, not the parent session's checkout
- Worktree is automatically cleaned up if the subagent makes no changes
- The worktree persists if changes were made (for review before merging)

In workflow scripts:
```javascript
const result = await agent("Refactor the auth module", {
  isolation: "worktree",
});
```

### Workflow Permissions

The permission prompt on launch depends on mode:

| Permission Mode | Prompt Behavior |
|----------------|-----------------|
| Default, accept edits | Every run (unless "don't ask again" was selected) |
| Auto | First launch only; later launches skip prompt. Skipped entirely with ultracode |
| Bypass, `claude -p`, Agent SDK | Never prompted; runs immediately |

Subagents within workflows always run in `acceptEdits` mode and inherit the user's tool allowlist. File edits are auto-approved. Shell commands, web fetches, and MCP tools not in the allowlist can still prompt mid-run.

### Save Workflow as Command

From `/workflows` view, press `s` to save a completed run's script as a command:

- `.claude/workflows/` (project): shared via version control, takes priority over user
- `~/.claude/workflows/` (user): available in all projects, private

Saved workflows run as `/<name>` in future sessions. They appear in `/` autocomplete alongside bundled workflows.

### Bundled Workflow: `/deep-research`

The reference implementation of the adversarial quality pattern:

```
/deep-research <question>
```

Flow:
1. Fan out web searches across several angles
2. Fetch sources found
3. Cross-check claims against sources
4. Vote on each claim
5. Filter out claims that didn't survive cross-checking
6. Return a cited report

This is the canonical example of the adversarial verification pattern applied to research.

### Disable Mechanisms

```
# Individual user
/config -> Dynamic workflows toggle -> off
~/.claude/settings.json: { "disableWorkflows": true }
CLAUDE_CODE_DISABLE_WORKFLOWS=1

# Organization-wide
Managed settings: { "disableWorkflows": true }
Admin settings page: toggle off
```

When disabled: bundled commands unavailable, keyword trigger disabled, ultracode removed from `/effort` menu.

### Cost Model

- Every agent uses the session's model unless the script routes a stage to a different model
- Runs count toward plan usage and rate limits
- A single workflow run can consume meaningfully more tokens than conversational work
- Control costs by: (1) Checking `/model` before large runs, (2) Using smaller models for stages that don't need the strongest model

---

## Primitive 4: Adversarial Quality Pattern

### Pattern Catalog

The Workflow tool description and `/deep-research` implementation encode these quality patterns:

#### 1. Adversarial Verification (Cross-Check)

**Algorithm:**
```
1. Wave 1: N agents investigate the problem from independent angles
2. Wave 2: M agents receive Wave 1's findings and attempt to refute them against the source
3. Each Wave 2 agent reports: [CONFIRMED] with evidence, or [REFUTED] with counter-evidence
4. Claims that survive adversarial review are kept; refuted claims are discarded
5. Final report surfaces only verified findings
```

**Concrete implementation in `/deep-research`:**
```
Phase 1: Fan out web searches across several angles (Wave 1)
Phase 2: Fetch sources, cross-check claims (Wave 2)
Phase 3: Vote on each claim (Judge panel)
Phase 4: Filter claims that didn't survive cross-checking
Phase 5: Synthesize cited report from verified claims
```

#### 2. Completeness Critic

```
After primary investigation completes:
1. Spawn a single "completeness critic" agent
2. Give it all findings so far
3. Task: "Find what the others missed. Check edge cases, assumptions, and gaps."
4. If critic finds gaps, spawn new agents to fill them
5. Repeat until critic reports no significant gaps
```

#### 3. Multi-Phase Sequencing (Understand -> Change -> Verify)

```
Phase 1: UNDERSTAND
  - Scout codebase structure, identify relevant files and patterns
  - Output: work-list of changes needed

Phase 2: DESIGN
  - Draft approach for each item in work-list
  - Output: implementation plan

Phase 3: IMPLEMENT
  - Execute changes in parallel where independent
  - Each change in isolated worktree

Phase 4: VERIFY
  - Run tests, lint, type-check
  - Adversarial review of each change
  - Loop until clean (loop-until-dry)
```

#### 4. Loop-Until-Dry

```
1. Apply changes
2. Run build + test suite
3. If failures:
   a. Agent analyzes failures
   b. Agent applies fixes
   c. Goto 2
4. When clean: report success
```

Real-world example: The Bun port used "hundreds of agents working in parallel with two reviewers on each file" across ~750K lines of Rust, completing in 11 days.

#### 5. Judge Panel (Vote/Filter)

```
1. Multiple agents independently evaluate the same claim
2. Each agent votes: CONFIRMED, REFUTED, UNCERTAIN
3. Claims with majority CONFIRMED survive
4. Claims with majority REFUTED are discarded
5. Split decisions trigger deeper investigation
```

#### 6. Hybrid Default (Scout Then Fan-Out)

```
1. Single agent scouts inline to discover the work-list
2. Agent identifies independent subtasks
3. Workflow fans out over the work-list with parallel agents
4. Results are collected and cross-checked
```

### Quality Pattern Implementation in Workflow Scripts

```javascript
// Adversarial verification pattern
export const meta = {
  name: "security-audit",
  description: "Audit codebase with adversarial verification",
};

const FINDINGS = await phase("Investigate", async () => {
  return await parallel([
    "Audit authentication flow for vulnerabilities",
    "Audit authorization logic for privilege escalation",
    "Audit input validation for injection attacks",
    "Audit data handling for leaks and exposures",
  ], { model: "sonnet" });
});

const VERIFIED = await phase("Adversarial Review", async () => {
  return await parallel(
    FINDINGS.map(f =>
      `CRITIC MODE: Attempt to refute this finding by checking the actual source code.
       If the finding is valid, confirm with additional evidence.
       If invalid, explain why with counter-evidence from the code.

       Finding to verify: ${f.output}`
    ),
    { model: "opus" }  // stronger model for verification
  );
});

const GAPS = await phase("Completeness Check", async () => {
  return await agent(
    `Review ALL findings below and identify what was MISSED.
     Consider: edge cases, error paths, configuration issues, dependency vulnerabilities.
     List specific gaps that need investigation.

     Verified findings: ${JSON.stringify(VERIFIED.map(v => v.output))}`,
    { model: "opus" }
  );
});

const REPORT = await phase("Synthesize", async () => {
  return await agent(
    `Create a security audit report from the verified findings.
     Include: severity ratings, affected files, remediation steps.
     Only include findings that survived adversarial review.

     Verified: ${JSON.stringify(VERIFIED.map(v => v.output))}
     Additional gaps found: ${GAPS.output}`,
    { model: "sonnet" }
  );
});
```

---

## Cross-Cutting: Subagent Architecture

### Spawning Mechanism

Subagents are spawned via the `Agent` tool (formerly `Task`). Claude Code composes a delegation message summarizing the task, and the subagent runs in its own context window with its own system prompt.

**Context isolation:**
- Subagent starts with a **fresh context window**
- Does NOT see conversation history, previously read files, or invoked skills
- Receives: (1) its own system prompt, (2) delegation message, (3) CLAUDE.md/memory files, (4) git status snapshot
- Exception: Forked subagents inherit full conversation history

**Startup payload per subagent:**
1. System prompt (from subagent definition body or built-in prompt)
2. Task message (delegation prompt Claude writes)
3. CLAUDE.md and memory hierarchy (all levels main conversation loads)
4. Git status snapshot (from parent session start)
5. Preloaded skills (if `skills` field is set)

Explore and Plan built-in agents skip CLAUDE.md and git status for speed.

### Subagent Types

| Type | Model | Tools | Purpose |
|------|-------|-------|---------|
| Explore | Haiku | Read-only (no Write/Edit) | Fast codebase search/exploration |
| Plan | Inherits from parent | Read-only (no Write/Edit) | Codebase research during plan mode |
| General-purpose | Inherits from parent | All tools | Complex multi-step tasks |
| statusline-setup | Sonnet | Specific | Configuring status line |
| claude-code-guide | Haiku | Specific | Claude Code feature questions |

Custom subagents can define any combination of model, tools, and permissions.

### Subagent Definition Format

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
permissionMode: acceptEdits
maxTurns: 30
skills: [api-conventions]
memory: user
background: false
effort: high
isolation: worktree
color: blue
initialPrompt: "Review the current diff for issues"
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

### Subagent Scope and Priority

| Priority | Scope | Location |
|----------|-------|----------|
| 1 (highest) | Managed (org-wide) | Managed settings directory |
| 2 | CLI flag | `--agents '{...}'` |
| 3 | Project | `.claude/agents/` |
| 4 | User | `~/.claude/agents/` |
| 5 (lowest) | Plugin | Plugin `agents/` directory |

### Model Resolution Order (per invocation)

1. `CLAUDE_CODE_SUBAGENT_MODEL` env var (if set)
2. Per-invocation `model` parameter
3. Subagent definition's `model` frontmatter
4. Main conversation's model

### Tools Unavailable to Subagents

These are always unavailable to subagents, even if listed in `tools`:
- `Agent` (subagents cannot spawn subagents)
- `AskUserQuestion`
- `EnterPlanMode`
- `ExitPlanMode` (unless `permissionMode: plan`)
- `ScheduleWakeup`
- `WaitForMcpServers`

### Background vs Foreground

- **Foreground**: blocks main conversation until complete; permission prompts pass through
- **Background**: runs concurrently; auto-denies any unprompted tool call; surface via `/tasks`
- Fork mode: all subagent spawns run in background regardless of `background` field

### Forked Subagents (Experimental)

Fork differs from named subagents:

| | Fork | Named Subagent |
|---|------|----------------|
| Context | Full conversation history | Fresh context |
| System prompt + tools | Same as main session | From definition file |
| Model | Same as main session | From `model` field |
| Permissions | Prompts surface in terminal | Auto-denied in background |
| Prompt cache | Shared with main session | Separate cache |

Enable: `CLAUDE_CODE_FORK_SUBAGENT=1`. Requires v2.1.117+.

---

## Cross-Cutting: Agent Teams

### Architecture

Agent teams coordinate multiple independent Claude Code sessions. Unlike subagents (which report back to one parent), teammates communicate directly with each other.

```
┌─────────────────────────────────────────────┐
│              Agent Team                      │
│                                              │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   │
│  │  Lead   │   │Teammate │   │Teammate │   │
│  │ Session │   │Session 1│   │Session 2│   │
│  │         │   │         │   │         │   │
│  │ ┌─────┐ │   │ Own     │   │ Own     │   │
│  │ │Task │◄┼───┤ context │◄──┤ context │   │
│  │ │List │ │   │ window  │   │ window  │   │
│  │ └─────┘ │   │         │   │         │   │
│  │         │   └─────────┘   └─────────┘   │
│  │ ┌─────┐ │        ▲              ▲        │
│  │ │Mail │◄┼────────┼──────────────┼────────│
│  │ │box  │ │   Direct messaging     │        │
│  │ └─────┘ │                        │        │
│  └─────────┘                        │        │
└─────────────────────────────────────┘────────┘
```

### Key Components

| Component | Description |
|-----------|-------------|
| Team lead | Main session that creates team, spawns teammates, coordinates work |
| Teammates | Separate Claude Code instances with independent context windows |
| Task list | Shared work items with file-locking to prevent race conditions |
| Mailbox | Messaging system for direct inter-agent communication |

### Communication Patterns

1. **Automatic message delivery**: Messages delivered automatically; no polling
2. **Idle notifications**: Teammates auto-notify lead when finished
3. **Shared task list**: All agents see task status, claim available work
4. **Direct messaging**: Any teammate can message any other by name
5. **Plan approval**: Teammates can be required to submit plans for lead approval before implementing

### Task Coordination

Tasks have three states: pending, in progress, completed. Tasks can have dependencies: a blocked task cannot be claimed until dependencies resolve. File locking prevents race conditions on task claims.

### Display Modes

| Mode | Mechanism | Requirements |
|------|-----------|--------------|
| In-process | All teammates in main terminal; Shift+Down to cycle | Any terminal |
| Split panes | Each teammate in own tmux/iTerm2 pane | tmux or iTerm2 |

### Limitations (Experimental)

- No session resumption with in-process teammates
- Task status can lag (manual override needed)
- Shutdown can be slow (teammates finish current request first)
- One team at a time per lead
- No nested teams
- Lead is fixed for team lifetime
- Permissions set at spawn, not per-teammate

### Enablement

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Requires Claude Code v2.1.32+.

---

## Cross-Cutting: Channels (Inter-Agent Comms)

### Architecture

Channels are MCP servers that push external events into Claude Code sessions. Claude Code spawns them as subprocesses over stdio transport.

```
External System ──► Channel Server (MCP, stdio) ──► Claude Code Session
                       ▲
                       │
                   Your MCP server
                   (Bun/Node/Deno)
```

### Channel Registration

The server declares itself as a channel via MCP capabilities:

```typescript
const mcp = new Server(
  { name: 'webhook', version: '0.0.1' },
  {
    capabilities: {
      experimental: {
        'claude/channel': {},             // registers notification listener
        'claude/channel/permission': {},  // optional: permission relay
      },
      tools: {},  // optional: enables reply tool (for two-way channels)
    },
    instructions: 'Events arrive as <channel source="webhook" ...>. Reply with the reply tool.',
  },
);
```

### Event Format

```typescript
await mcp.notification({
  method: 'notifications/claude/channel',
  params: {
    content: 'build failed on main: https://ci.example.com/run/1234',
    meta: { severity: 'high', run_id: '1234' },
  },
});
```

Arrives in Claude's context as:
```xml
<channel source="webhook" severity="high" run_id="1234">
build failed on main: https://ci.example.com/run/1234
</channel>
```

### Two-Way Channels (Reply Tool)

Standard MCP tool registration for replies:

```typescript
mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'reply',
    description: 'Send a message back over this channel',
    inputSchema: {
      type: 'object',
      properties: {
        chat_id: { type: 'string' },
        text: { type: 'string' },
      },
      required: ['chat_id', 'text'],
    },
  }],
}));
```

### Permission Relay

When a permission dialog opens:
1. Claude Code generates a 5-letter request ID (alphabet: a-z minus 'l')
2. Notifies channel server via `notifications/claude/channel/permission_request`
3. Server forwards to remote chat platform
4. User replies with `yes <id>` or `no <id>`
5. Server emits `notifications/claude/channel/permission` verdict
6. First answer (local terminal or remote) wins; the other is closed

Permission request fields: `request_id`, `tool_name`, `description`, `input_preview` (truncated to 200 chars).

### Security

- Gating: Check sender identity against allowlist BEFORE emitting events. Gate on sender, not room/chat ID.
- No acknowledgment: `mcp.notification()` resolves when written to transport, not when Claude processes it. Events dropped silently if session hasn't loaded the channel.
- Dev flag: `--dangerously-load-development-channels server:name` bypasses allowlist for testing.

### Research Preview Limitations

- Custom channels not on approved allowlist (need dev flag)
- `channelsEnabled` organization policy still applies even with dev flag
- Requires Claude Code v2.1.80+ (v2.1.81+ for permission relay)

---

## Lyra Transfer Blueprint

### What Transfers Directly

| Mechanism | Transferability | Notes |
|-----------|----------------|--------|
| Effort levels (low-high) | **Universal** | Any provider, any model. Just a behavioral signal. |
| Effort xhigh/max | **Anthropic-only** | Requires Opus 4.7/4.8 with adaptive thinking. Not portable. |
| Mid-conversation system messages | **Anthropic-only** (Opus currently) | API feature; not available on OpenAI/DeepSeek. Can approximate with regular user messages on other providers but breaks prompt caching. |
| Workflow JS engine | **Replicable** | Pure software architecture. ScriptVM, agent pool, progress tracking -- all replicable in Python/TypeScript. |
| Subagent spawning | **Replicable** | Can implement with any LLM provider that supports tool use. Independent context windows + tool restrictions. |
| Agent teams (shared task list + messaging) | **Replicable** | File-locked task list + inter-process messaging. No provider dependency. |
| Channels (MCP-based event push) | **Replicable** | Standard MCP protocol. MCP SDK available for Python, TypeScript, Kotlin, etc. |
| Adversarial quality patterns | **Universal** | Pure orchestration logic. No provider dependency. Works with any model that supports tool use. |
| Worktree isolation | **Git-dependent** | Requires git. Replicable anywhere git is available. |
| Keyword triggers | **Trivial** | Simple text pattern matching in prompt preprocessing. |

### What Needs Adaptation

| Mechanism | Issue | Adaptation |
|-----------|-------|------------|
| Effort -> OpenAI | Different semantics (effort affects all output; reasoning_effort affects only thinking) | Map effort to `reasoning_effort` + add tool-use brevity instructions in system prompt |
| Effort -> DeepSeek | No native effort API | Inject effort directives in system prompt; no budget control |
| Effort -> Open-weight | No API control at all | System prompt only; prepare for inconsistent compliance |
| Mid-conversation system messages | OpenAI doesn't support system messages after conversation start | Use user-role messages with special delimiter or use OpenAI's `developer` role |
| Adaptive thinking | Proprietary to Anthropic Opus 4.6+ | Accept fixed thinking budgets or no thinking on other providers |
| Workflow keyword trigger | Claude Code harness feature | Reimplement as prompt preprocessing in Lyra's CLI layer |
| Ultracode composite | Claude Code harness feature | Implement as Lyra session mode: effort level + orchestration permission |
| Agent tool (Agent SDK) | Claude Code internal tool | Implement as MCP tool or custom tool in Lyra's agent loop |
| Progress view (TUI) | Claude Code terminal UI | Reimplement with Rich/Textual (Python) or Ink (Node) |
| Channels allowlist | Anthropic-curated | Replace with Lyra's own plugin trust model |

### Architecture for Lyra's Ultracode Equivalent

```
┌────────────────────────────────────────────────────────────┐
│                    Lyra Session                             │
│                                                            │
│  ┌──────────────┐   ┌──────────────────────────────────┐   │
│  │ Effort Manager│   │     Orchestration Manager         │   │
│  │              │   │                                  │   │
│  │ - level:     │   │  - mode: on/off/keyword-trigger │   │
│  │   low|med|   │   │  - state machine (entry/refresh/ │   │
│  │   high|xhigh │   │    exit messages)                │   │
│  │ - provider   │   │  - turn counter                 │   │
│  │   mapping    │   │  - quality pattern registry     │   │
│  └──────┬───────┘   └──────────────┬───────────────────┘   │
│         │                          │                       │
│         ▼                          ▼                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Agent Loop (Provider-Agnostic)           │   │
│  │                                                      │   │
│  │  1. Build messages (system + user + orchestration)   │   │
│  │  2. Send to LLM with effort config                   │   │
│  │  3. Parse response (text + tool calls)               │   │
│  │  4. Execute tool calls                              │   │
│  │     - Workflow tool -> Workflow Runtime              │   │
│  │     - Bash/Read/Write -> Direct execution            │   │
│  │  5. Inject orchestration refreshers as needed        │   │
│  │  6. Loop                                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Workflow Runtime (Python)                │   │
│  │                                                      │   │
│  │  - ScriptVM: isolated Python/Rust runtime            │   │
│  │  - agent(prompt, options) -> subagent spawn          │   │
│  │  - parallel(prompts) -> ThreadPoolExecutor           │   │
│  │  - pipeline(stages) -> sequential with data flow     │   │
│  │  - phase(name, work) -> progress tracking            │   │
│  │  - Concurrency cap: 16 (configurable)                │   │
│  │  - Run cap: 1000 agents                              │   │
│  │  - Checkpoint: save completed agent results          │   │
│  │  - Resume: replay cached + run remaining             │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Subagent Pool                            │   │
│  │                                                      │   │
│  │  - Per-agent: fresh context, own system prompt       │   │
│  │  - Tool allowlist/denylist                           │   │
│  │  - Model routing (per-agent or inherited)            │   │
│  │  - Worktree isolation (git worktree per agent)       │   │
│  │  - Memory scopes (user/project/local)                │   │
│  │  - Max turns, effort override                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Channels (MCP-Based)                     │   │
│  │                                                      │   │
│  │  - MCP servers with claude/channel capability        │   │
│  │  - One-way: alerts, webhooks, CI events              │   │
│  │  - Two-way: chat bridges with reply tools            │   │
│  │  - Permission relay: remote approve/deny             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Quality Pattern Library                  │   │
│  │                                                      │   │
│  │  - adversarial_verify(findings, source_checker)      │   │
│  │  - completeness_critic(findings, gap_hunter)         │   │
│  │  - multi_phase([understand, design, implement,       │   │
│  │                  verify])                            │   │
│  │  - loop_until_dry(apply_fn, test_fn, max_iterations) │   │
│  │  - judge_panel(claims, voters, threshold)            │   │
│  │  - scout_then_fanout(scout_prompt, fanout_fn)        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### Key Design Decisions for Lyra

1. **Effort abstraction layer**: Map Lyra effort levels to provider-specific mechanisms. `low/medium/high` become universal. `xhigh/max` become provider-gated (available on Anthropic, degraded gracefully elsewhere).

2. **Orchestration as session mode, not tool**: The mode toggle is a session-level flag that controls: (a) system message injection pattern, (b) tool behavior contract, (c) quality pattern defaults. This is more maintainable than encoding it in tool descriptions.

3. **Workflow engine in Python**: Use `asyncio` + `ThreadPoolExecutor` for agent fan-out. Implement ScriptVM as a restricted Python execution context. Checkpoint agent results to SQLite for resume support.

4. **Subagent context via provider-native patterns**: Each provider handles subagents differently. Anthropic: spawn with separate API key/session. OpenAI: use Assistants API or separate chat completions. Open-weight: manage separate conversation state.

5. **Quality patterns as composable functions**: Each pattern (adversarial verify, completeness critic, loop-until-dry) is a pure function that takes agents and data, returns verified results. Composability allows stacking patterns.

6. **Channels via MCP**: Adopt the MCP-based channel architecture directly. It's protocol-standard, not Anthropic-specific. The `claude/channel` capability string can be renamed to `lyra/channel`.

7. **Progressive disclosure**: Not all models support all primitives. Lyra should auto-detect provider capabilities and degrade gracefully: xhigh -> high -> medium, adaptive thinking -> fixed budget -> no thinking, orchestration mode -> keyword trigger only.

### Risk Factors

| Risk | Severity | Mitigation |
|------|----------|------------|
| Effort semantics differ across providers | High | Abstract into Lyra effort levels with documented per-provider behavior. Test eval suite per provider. |
| Adaptive thinking is Anthropic-only | High | Accept that thinking quality will vary. Use fixed thinking budgets where available. |
| Mid-conversation system messages are Opus-only | Medium | Fall back to user-role orchestration messages on other providers. Accept prompt cache penalty. |
| Token cost explosion with fan-out | High | Implement budget tracking, per-phase model routing, user warnings before large runs. |
| Subagent context isolation varies by provider | Medium | Standardize context assembly in Lyra's agent loop. Document per-provider differences. |
| Worktree isolation requires git | Low | Git is near-universal. Fall back to copy-on-write directories for non-git projects. |
| Rate limits on parallel API calls | Medium | Implement backpressure, queue, and retry with exponential backoff. Configurable concurrency. |

---

## Summary: Primitive Count and Mapping

| # | Primitive | API-Level? | Provider-Portable? | Lyra Strategy |
|---|-----------|-----------|-------------------|---------------|
| 1 | Effort Menu (5 levels) | Yes (Anthropic `output_config.effort`) | Partially (semantics differ) | Abstract with per-provider mapping |
| 2 | Auto-Orchestration Toggle | Partially (mid-conversation system msgs) | Partially (Opus-only for system msgs) | Session mode + tool contract pattern |
| 3 | Dynamic Workflow Engine | No (Claude Code harness) | Fully replicable | Python asyncio + ThreadPoolExecutor |
| 4 | Adversarial Quality Patterns | No (orchestration logic) | Fully replicable | Composable function library |

The orchestration stack is fundamentally a **harness-level architecture** built on top of standard LLM APIs. The only truly provider-gated components are: (a) the effort parameter's tight integration with adaptive thinking (Anthropic-only), and (b) mid-conversation system messages for mode toggling (Opus-only). Everything else -- the workflow engine, subagent pool, quality patterns, channels, and agent teams -- is replicable software architecture.
