# code-yeongyu/oh-my-openagent -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline: Multi-model, multi-agent orchestrator for OpenCode (and now Codex CLI) with hash-anchored editing, IntentGate mode detection, and a Ralph-style self-referential work loop.**

The core claim: install one plugin into OpenCode, type `ultrawork`, and get an automated dev team of 11 discipline agents (Sisyphus, Hephaestus, Oracle, Librarian, Explore, Prometheus, Metis, Momus, Atlas, Multimodal-Looker, Sisyphus-Junior) orchestrated by a single entry point -- no manual model juggling, no prompt engineering.

How it really works:

- **Plugin architecture.** `src/index.ts` (18 lines) delegates to `src/testing/create-plugin-module.ts` which runs a staged init pipeline: config loading (Zod v4 JSONC layered from user to project), manager creation (TmuxSessionManager, BackgroundManager, SkillMcpManager), tool registry composition (~20-39 tools depending on config flags), and hook composition (~53-61 lifecycle hooks across 57 directories).
- **Keyword Detector (IntentGate).** `src/hooks/keyword-detector/` scans every `chat.message` for keywords like `ultrawork`, `search`, `analyze`, `team`, `hyperplan`. When matched, it injects a tailored system message that reconfigures the agent's behavior -- no manual mode switching.
- **Hashline (hash-anchored edits).** `packages/hashline-core/` implements LINE#ID content hashing using runtime-aware xxHash32. Every file read annotates lines with content hashes (`11#VK| function hello() {`). Edits reference those hashes; if the file changed since the last read, the hash won't match and the edit is rejected before corruption. This is the single biggest concrete innovation -- the README cites a **Grok Code Fast 1 benchmark: 6.7% to 68.3% success rate** from swapping the edit tool alone.
- **Ralph Loop.** `src/hooks/ralph-loop/` is a self-referential continuation system. When the agent goes idle after incomplete work, the loop re-injects a continuation prompt, detects remaining todos, and re-dispatches. It keeps going until all todos are complete or a hard stop threshold is hit.
- **Team Mode.** A parallel multi-agent system (off by default). A lead agent orchestrates up to 8 category-specialized members, communicating through dedicated tools (`team_create`, `team_send_message`, `team_task_create`, `team_status`). Visualized in tmux panes. Powers `hyperplan` (5 hostile critics) and `security-research` (3 hunters + 2 PoC engineers).
- **Background Agents.** Async subagent spawning. Fire 5+ specialists in parallel (e.g., GPT debugs while Claude implements), context stays lean, results return when ready.
- **Multi-harness architecture.** The ROADMAP documents a package-layering refactor extracting pure-TS "Core" packages from adapter code. 7 core packages already extracted (`utils`, `model-core`, `rules-engine`, `agents-md-core`, `ast-grep-core`, `comment-checker-core`, `boulder-state`). The "Light Edition" ships 5 portable components into Codex CLI's plugin system, proving the adapter pattern works.

## 2. Architecture & Core Modules

**Entry point:** `src/index.ts` (6 LOC) -> `src/testing/create-plugin-module.ts` -> OpenCode `Plugin` async factory.

**Module structure (monorepo with workspaces):**

```
src/
  index.ts                    # Plugin entry, re-exports createPluginModule()
  create-plugin-module.ts     # Staged init: config -> managers -> tools -> hooks -> plugin interface
  create-managers.ts          # TmuxSessionManager + BackgroundManager + SkillMcpManager + ConfigHandler
  create-tools.ts             # ToolRegistry composition (20-39 tools gated by flags)
  create-hooks.ts             # 5-tier hook composition (session, tool-guard, transform, continuation, skill)
  plugin-interface.ts         # 12 OpenCode hook handlers wired to managers+hooks+tools

  agents/                     # 11 agent definitions with model routing + tool restrictions
  hooks/                      # ~52 lifecycle hooks across 57 dirs (ralph-loop, keyword-detector, etc.)
  features/                   # 20 feature modules (background-agent, team-mode, skill-mcp-manager, tmux-subagent)
  tools/                      # 13 native tool dirs; LSP + AST-grep now served via MCPs
  shared/                     # 297 utility files (logger, model-resolver, tmux, deep-merge, etc.)
  config/                     # Zod v4 schema system (30 schema files)
  cli/                        # CLI: install, run, doctor, mcp-oauth, boulder, sparkshell
  plugin/                     # 12 OpenCode hook handlers + 5-tier hook composition
  openclaw/                   # Bidirectional external integration (Discord/Telegram/HTTP)
  generated/                  # model-capabilities.generated.json

packages/
  utils/                      # Shared utilities (deep-merge, frontmatter, jsonc-parser)
  model-core/                 # Model resolution pipeline with ProviderCache DI
  prompts-core/               # Markdown prompt loading + bundled mode prompts
  rules-engine/               # Rule discovery + matching (symlink-safe, workspace-bound)
  agents-md-core/             # AGENTS.md walk-up discovery + injection
  hashline-core/              # LINE#ID edit primitives (the headline innovation)
  boulder-state/              # Work tracking state machine (Ralph Loop persistence)
  omo-codex/                  # Codex CLI Light edition (vendored plugin + TS installer + telemetry)
  git-bash-mcp/               # Windows-only git_bash stdio MCP
  shared-skills/              # Cross-harness SKILL.md bundle
  lsp-tools-mcp/              # LSP MCP server (vendored in-tree)
  ast-grep-mcp/               # AST-grep MCP server
```

**Architecture pattern:** Plugin adapter pattern with dependency-injected hook factories. The `create*` pattern is universal: every module exports a factory function that takes typed dependency objects and returns a configured instance. This enables DI-based testing (the `createPluginModule` accepts `overrides` for every dependency).

**Data flow:** user prompt -> OpenCode -> plugin hooks chain -> keyword detector (IntentGate) injects mode prompt -> agent model selected per category -> Sisyphus orchestrates -> delegates to subagents via `delegate_task` tool -> background agents run in parallel -> Ralph Loop detects idle -> continuation prompt re-injected -> Hashline edits all file writes.

**Language:** TypeScript (strict mode, ESNext target, Bun runtime). ~2167 TS files, ~313k LOC across the repo. Bun as the primary build/run tool.

## 3. Performance/Benchmarks

The repo cites exactly **one** benchmark:

- **Grok Code Fast 1: 6.7% to 68.3% success rate** from the hash-anchored edit tool alone. This is referenced in both README.md (line 332) and docs/guide/overview.md (line 249). The claim is attributed to switching from Claude Code's edit tool (which fails when the model can't reproduce lines exactly) to OmO's LINE#ID hashing.

No other formal benchmarks exist in the repo. No SWE-bench scores, no AgentBench scores, no TerminalBench runs. The IntentGate feature references TerminalBench from factory.ai but provides no numbers.

There is a `docs/reference/rules-injection-cross-module-comparison.md` that compares rule injection implementations across three repos (this one, codex-rules, pi-extensions) but notes "A unified cross-module benchmark harness does not yet exist."

## 4. Trade-offs

**Wins:**

1. **Hashline editing solves the harness problem.** The 10x improvement on Grok Code Fast 1 is the strongest empirical claim in any agent-harness repo we have reviewed. If this holds across other benchmarks, it is the single most impactful edit-tool innovation in the space.

2. **Multi-model orchestration that actually ships.** The 11-agent architecture with model-per-category routing (ultrabrain -> GPT-5.5 xhigh, visual -> K2.6, quick -> Haiku) is production-tested across multiple providers. This is not theoretical -- the CHANGELOG documents 4.7.x releases with real fixes for provider fallback, race conditions, and session recovery.

3. **Claude Code compatibility layer.** All hooks, commands, skills, MCPs, and plugins from Claude Code work unchanged. This dramatically lowers switching costs.

4. **Ralph Loop as a durable continuation primitive.** The boulder-state state machine persists work-tracking across sessions, enabling reliable multi-hour autonomous runs. This is exactly the pattern the Lyra team has been designing for the agent-hospital/preemptive-compaction system.

5. **Security-conscious rule injection.** `packages/rules-engine/` blocks symlink escapes from project rule files to host secrets (documented in CHANGELOG v4.2.3 as a security fix).

**Loses / Limitations:**

1. **Massive complexity.** 2167 TypeScript files, 313k LOC, 57 hook directories, 20 feature modules, 23 workspace packages. This is a full-time maintenance burden. The author (code-yeongyu) is the primary contributor; this level of complexity on a solo-ish project is a bus-factor risk.

2. **Single-license restriction.** SUL-1.0 (Sustainable Use License) permits internal business/personal use but prohibits commercial distribution for charge. This makes direct code porting to Lyra (MIT/ Apache) legally fraught without contacting the author.

3. **Tight OpenCode coupling.** Despite the ROADMAP's multi-harness refactor, the actual code is deeply coupled to OpenCode's plugin API. The Codex Light Edition is a separate codebase path (`packages/omo-codex/`), not a clean adapter.

4. **No formal benchmarks beyond one Grok score.** The 6.7% -> 68.3% is impressive but it's a single data point on a single benchmark. No SWE-bench, no HumanEval, no TerminalBench numbers.

5. **Prompt-async-gate complexity.** The CHANGELOG (v4.2.2) documents an 885-LOC module (`prompt-async-gate.ts`) past the 250-LOC ceiling, with known race conditions between post-dispatch failure and reservation release that required BLOCKER-2 fixes. The async session injection pattern is inherently risky.

6. **Known issues.** Delegate-task early-failure-fallback (BLOCKER-4 in v4.2.0) was merged and reverted. Custom LSP config in JSONC is silently ignored (issue #4225). Team-mode hard-rejects coordinator agents and had Windows EPERM crashes.

7. **Telemetry is on by default.** Anonymous daily-active-user telemetry via PostHog. Opt-out via env var, but this is against Lyra's design principles.

## 5. Design Rationale

The ROADMAP.md and Manifesto lay out the philosophy unambiguously:

1. **"Human intervention is a failure signal."** The entire architecture is built on the premise that the agent should complete the work without human babysitting. The Ralph Loop, Todo Enforcer, and background agents all serve this goal.

2. **"Prefer the representation that requires the least reasoning from the agent."** When in doubt, optimize for the agent's performance over human readability. This justifies the 57-hook-directory structure and 313k LOC sprawl.

3. **"Skills over MCPs over Tools over Hooks."** The hierarchy of expression: static SKILL.md files (zero runtime cost) are preferred; MCP servers (process boundary) come second; first-party runtime tools third; lifecycle hooks last. This minimizes context-window overhead.

4. **"Core has no harness dependencies."** The ROADMAP's strict dependency DAG (Core -> MCP -> Skills -> Adapters -> Platform) ensures pure-TS packages can be tested in isolation and reused across harnesses without adapter code leaking in.

5. **"Skeptical of multi-harness abstraction."** Despite building for multiple harnesses, the team explicitly avoids premature adapter-pattern abstraction: "If an adapter for a new harness is needed, an agent can write it in one shot."

6. **"Duplicate work. Infinite loops. State corruption."** The ROADMAP candidly documents why OpenCode's plugin API is dangerous (session.prompt returning before durably accepted, multiple hooks injecting into the same parent session). The plugin architecture exists to contain these risks.

## 6. Transfer to Lyra

**One idea: Hash-anchored edit tool (Hashline).**

The LINE#ID content-hash edit validation is the single most concrete, transferable mechanism in this repo. Lyra's current edit pipeline (direct file write via tool calls) is vulnerable to the same "harness problem" OmO solves -- the model must reproduce exact file content, and any deviation causes silent corruption or rejection. Porting the Hashline mechanism would:

1. Annotate every file read with per-line content hashes.
2. Require every edit to reference LINE#IDs.
3. Reject edits whose hashes don't match the current file state.
4. Fall back gracefully (re-read and retry) on mismatch.

**Workstream route:** Section 4.x (Tool System / Edit Infrastructure). Hashline belongs in the edit tool layer, not in orchestration or memory. It is a drop-in replacement for the current apply_patch / write mechanisms.

- **Impact:** 9/10 (editing reliability is a top-3 failure mode in autonomous agents; the 6.7% -> 68.3% Grok number is the strongest single-metric improvement we have seen).
- **Effort:** 5/10 (moderate). The core hashing algorithm (xxHash32) is compact (~200 lines in `packages/hashline-core/src/hash-computation.ts`). The real work is integrating LINE#ID annotation into every read surface and edit rejection into every write surface. Requires careful edge-case handling (binary files, append-only logs, very large files).
- **Tier:** P1 (high impact, moderate effort). This is a proven, measurable improvement that directly addresses Lyra's edit-reliability gaps.

**License constraint:** SUL-1.0 prohibits commercial distribution. The xxHash32 hashing algorithm itself is public-domain; the Hashline design pattern (LINE#ID references anchored to content hashes) is a method that likely cannot be patented. The Lyra team can independently implement the mechanism without importing any SUL-licensed code.

**Additional transferable patterns:**
- The boulder-state state machine (`packages/boulder-state/`) for durable work-tracking across session boundaries -- directly relevant to Lyra's preemptive-compaction / agent-hospital workstream.
- The rules-engine symlink-escaping security fix (symlink-boundary checking in `packages/rules-engine/src/index.test.ts`) -- directly applicable to Lyra's rule-injection system.
- The keyword-detector / IntentGate pattern for mode switching -- simpler than Lyra's current debate-based routing system.
