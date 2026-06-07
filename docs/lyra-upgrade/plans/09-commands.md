# Commands & Interactive Mode -- Plan (SS4.9)

> Run 4, 2026-06-07
> Updated with deep-read evidence: +21 citations from 6 papers + 4 repos + 1 web doc

## Plain-Language Summary

Lyra's slash command system provides a discoverable command palette. Custom commands are defined as markdown files (`.lyra/commands/<name>.md`) with YAML frontmatter for arguments, descriptions, and keybindings. The interactive mode provides a rich TUI with command autocomplete, history search, and context-aware suggestions. Two reference implementations -- Claude Code's plugin system and OpenCode/Kilo Code's session engine -- provide production-validated patterns for the command infrastructure.

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Plugins Reference (web, Anthropic) | Commands as flat `.md` files under `commands/` directory in a plugin; `plugin.json` manifest; userConfig schema + variable substitution |
| Claude Code Interactive Mode (SS3.1) | Full terminal REPL with history, completion, multi-line input |
| Lyra's slash_commands.py (368L) | Existing command registry, needs custom command support |
| OpenCode / Kilo Code (repo, anomalyco / Kilo-org) | Session V2 event-sourcing, TUI, 7 agent modes (build, plan, general, explore, debug, review, ask, architect), permission-gated tool registry, compaction at 80-100% |
| Goose (block/goose, repo, AAIF) | Command detection (`/`, `/clear`, etc.), interactive shell, tool inspection pipeline (5 inspectors), compaction at 80% threshold, hooks system with 22 lifecycle events |
| CowAgent (zhayujie/CowAgent, repo) | ReAct loop CLI, 12+ IM channels, CLI `cow` command (start/stop/restart/status/logs/update/skill install) |
| Terminal-Bench 2.0 (2601.11868v1) | Command-level failure analysis: 24.1% "executables not installed/in PATH", 9.6% "failures when running executables"; Docker sandbox with 32,155 trials |
| AgentBench (2308.03688v3, ICLR 2024) | Bash CLI via Docker containers; failure taxonomy: Context Limit Exceeded, Invalid Format, Invalid Action, Task Limit Exceeded |
| Safety Survey (2605.23989v1) | Progent: tool permission ASR from 39.9% to 1.0% via three-valued policy model (allow/deny/ask); sandbox isolation is mandatory |
| RMUX (Helvesec/rmux, repo) | tmux-compatible terminal multiplexer engine in Rust; key binding system, web share with PQ E2EE, cross-platform PTY |
| Claw AI Lab (2605.22662v1) | Tool surface: bash, read/write/edit file, glob, grep -- all in sandboxed workspace; runtime controller with time budgets |

## Proposed Design

1. **Built-in commands:** `/model`, `/effort`, `/skills`, `/memory`, `/fleet`, `/cost`, `/config`, `/help`, `/dream`, `/clear`
2. **Custom commands:** `.lyra/commands/<name>.md` -- YAML frontmatter (description, arguments, keybinding) + body (prompt template). Follows the Claude Code plugin pattern where commands are flat markdown skill files (Claude Code Plugins Reference: `commands/` component type).
3. **Agent modes (from Kilo Code pattern):** Named configurations with custom prompts, permission sets, and model overrides. Built-in: `build` (all tools), `plan` (read-only), `general` (subagent), `explore` (read-only research), `debug`, `review`, `ask`, `architect`. Custom modes via `.lyra/modes/<name>.json`.
4. **Command palette:** `/` opens fuzzy-search palette. Tab to autocomplete. Recent commands surfaced. Pattern validated by Claude Code (SS3.1) and CowAgent CLI (`cow` command dispatch).
5. **Interactive mode:** REPL with syntax highlighting, multi-line input, history search (Ctrl+R), context-aware suggestions based on current task. Follows OpenCode session V2 architecture: event-sourced session store, typed context sources, safe provider-turn boundaries.
6. **Command detection pipeline (from Goose):** Before any tool executes, passes through Inspection pipeline: SecurityInspector -> EgressInspector -> AdversaryInspector -> PermissionInspector -> RepetitionInspector. Approvals return allow/deny/ask buckets.

## Key Design Decisions with Evidence

**Decision 1: PWA vs. Native Terminal Multiplexer**
The RMUX project (Helvesec/rmux) demonstrates a full-featured Rust terminal multiplexer with key bindings, session management, and web share. However, Lyra's interactive mode should follow the OpenCode/Claude Code pattern of a lightweight REPL, not a full multiplexer. Rationale: Lyra is an agent harness, not a terminal emulator. Key bindings should be simple (Ctrl+R history, Ctrl+C interrupt, Tab autocomplete) without multiplexer complexity. RMUX's key binding system (core/key_bindings.rs) is a reference if Lyra needs advanced keyboard control.

**Decision 2: Commands as Shallow Files vs. Plugin Manifest**
Claude Code Plugins reference defines commands as flat `.md` files in a `commands/` directory within a plugin. This is the simplest possible pattern: no registry, no install step -- just file discovery. OpenCode/Kilo Code uses a more complex plugin architecture with Effect-TS Schema definitions. Lyra should start with the flat-file pattern (Claude Code approach) and graduate to the plugin system only when evidence shows it is needed. The Claude Code pattern has zero install friction and is production-validated across millions of sessions.

**Decision 3: Permission Model for Interactive Commands**
Terminal-Bench 2.0 (2601.11868v1) found that 24.1% of all command failures are "executables not installed or not in PATH" and 9.6% are "failures when running executables." This means Lyra's command system must validate tool availability before execution and provide clear error messages. Additionally, the Safety Survey (2605.23989v1) documents that Progent reduced ASR from 39.9% to 1.0% with three-valued permission policy (allow/deny/ask). Lyra's command execution must adopt this model: every command goes through a permission gate before the shell executes it.

**Decision 4: Sandbox Isolation for Bash Commands**
AgentBench (2308.03688v3) evaluates CLI agents inside Docker containers with pinned dependencies. Terminal-Bench 2.0 uses Docker containers with internet access and checks final container state. CowAgent provides a Bash sandbox tool with per-command seatbelt-style isolation. OpenHands separates the app server from the agent server, with agents running in Docker containers. All sources converge on sandbox isolation as mandatory for CLI agent execution. Lyra's commands mode must execute commands in a sandboxed environment, not directly on the host.

## Build Outline

1. Custom command file format + loader -- flat `.md` files with YAML frontmatter (week 1)
2. Command palette with fuzzy search + autocomplete -- `/` trigger, Tab completion, recent command surfacing (week 1)
3. Interactive REPL enhancements: multi-line, history search, agent mode switching (weeks 2-3)
4. Permission-gated command execution -- three-valued policy (allow/deny/ask) with tool availability validation (week 3)
5. Keybinding system for commands -- Ctrl+K to /code-review, etc., with configurable key bindings in `.lyra/keybindings.json` (week 4)
6. Sandbox isolation for bash execution -- Docker or seatbelt-style per-command sandbox matching Terminal-Bench 2.0 / AgentBench patterns (week 4)

## Detailed Component Architecture

### Command File Format
```
---
description: "Run code review on the current diff"
arguments:
  - name: "scope"
    type: "string"
    description: "Files or directories to review"
    required: false
  - name: "effort"
    type: "select"
    options: ["low", "medium", "high"]
    default: "medium"
keybinding: "ctrl+k"
---
You are a code reviewer. Review the diff of the following files:
{{ scope | default("all changed files") }}

Focus on:
- Correctness bugs
- Security vulnerabilities
- Code quality
- Performance issues
```

### Permission Pipeline (from Goose + Progent)
```
User command input
  -> Command parser (detect /command vs natural language)
  -> Fuzzy search (if ambiguous)
  -> Policy check [allow/deny/ask]
    -> Tool availability verification (Terminal-Bench 2.0 finding: 24.1% failure is "not installed")
    -> Permission check (Progent three-valued model)
  -> Sandbox allocation (Docker / seatbelt)
  -> Command execution in sandbox
  -> Result validation (check output, not trajectory)
  -> History logging + cost tracking
```

### Agent Mode Configuration
```json
{
  "modes": {
    "build": {
      "description": "Full access: all tools, write permissions",
      "prompt": "You are a software engineer implementing features.",
      "allowedTools": ["*"],
      "model": "sonnet"
    },
    "plan": {
      "description": "Read-only: research and design only",
      "prompt": "You are a software architect. Analyze and plan.",
      "allowedTools": ["read", "grep", "glob", "websearch"],
      "model": "opus"
    },
    "explore": {
      "description": "Read-only research mode",
      "prompt": "You are a researcher. Explore the codebase.",
      "allowedTools": ["read", "grep", "glob", "websearch", "webfetch"],
      "edit": false
    }
  }
}
```

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| slash_commands.py (368L) | EXTEND: custom commands, palette, keybindings | Low |
| New: commands/ directory | ADD: flat `.md` command file loader | Low |
| New: permission pipeline | ADD: three-valued allow/deny/ask for tool usage | Medium |
| New: agent modes | ADD: mode configuration and switching | Medium |
| New: sandbox isolation | ADD: Docker/seatbelt sandbox for command execution | Medium |

**Impact:** 3 | **Effort:** 3 | **Tier:** (A) Parity

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly -- don't invent something new unless the evidence proves it's better. The plugin commands pattern is already production-validated across millions of sessions."

**Resolved positions:**

1. **Command file format** -- Adopt Claude Code's flat `.md` pattern. No innovation needed. OpenCode's Effect-TS schema system and Goose's MCP integration are more complex without clear UX benefit for basic commands.

2. **Agent modes** -- Adopt Kilo Code's named mode pattern (build, plan, explore, debug, review, ask, architect) rather than Claude Code's implicit mode switching. Rationale: explicit mode names provide discoverability and documentation. Evidence: Kilo Code's multi-surface support (VS Code, JetBrains, CLI, Slack, Cloud) validates that mode switching across contexts is necessary.

3. **Permission model** -- Adopt Claude Code's three-valued model (allow/deny/ask) with Progent's SMT-based policy enforcement for Lyra's breakthrough tier. The Safety Survey (2605.23989v1) documents ASR reduction from 39.9% to 1.0% -- compelling evidence for structural enforcement over prompt-based defenses.

4. **Sandbox isolation** -- Terminal-Bench 2.0 (2601.11868v1) found that 37% of realistic CLI tasks remain unsolved even by frontier systems, but this is a capability gap, not a safety one. AgentBench (2308.03688v3) evaluates agents inside Docker with pinned dependencies. Claude Code uses seatbelt on macOS and bubblewrap on Linux. Lyra must ship with at minimum one per-command sandbox. Three implementation patterns available: per-command (seatbelt), per-process (Docker), per-session (VM).

**Sign-off:** Plan is feasible with moderate effort increase due to sandbox and permission pipeline. Parity implementation is well-documented in Claude Code docs (SS3.1, Plugins Reference), OpenCode/Kilo Code source, and Goose source. Agent modes from Kilo Code provide a differentiation opportunity. Sandbox isolation is mandatory, not optional, given the Safety Survey and Terminal-Bench 2.0 evidence.

## Comparison with Reference Implementations

| Feature | Claude Code | OpenCode/Kilo Code | Goose | CowAgent | Lyra (Proposed) |
|---------|------------|-------------------|-------|----------|-----------------|
| Custom commands | `.md` files in plugin | Plugin system (Effect-TS) | MCP tools | CLI subcommands | `.md` flat files |
| Interactive REPL | Full TUI | CLI + TUI + Desktop | CLI + Desktop | CLI + 12 IM channels | CLI + TUI |
| Agent modes | Implicit | 7 named modes | Per-agent config | N/A | 7 named modes |
| Permission model | 3-valued (allow/deny/ask) | Tool-gated | 5-inspector pipeline | N/A | 3-valued + sandbox |
| Sandbox | Seatbelt/Bubblewrap | None | Docker | N/A | Docker + seatbelt |
| Key bindings | Configurable | Configurable | Basic | N/A | Configurable JSON |
| Command history | Yes (Ctrl+R) | Yes | Yes | No | Yes (Ctrl+R) |
| Multi-line input | Yes | Yes | Yes | No | Yes |

## Evidence Base

### Papers
1. **Terminal-Bench 2.0**, 2601.11868v1 (arXiv, Jan 2026) -- Command-level failure analysis (24.1% executables not found), Docker sandbox evaluation, 32,155 trials across 6 agents and 16 models, 37% task ceiling
2. **AgentBench**, 2308.03688v3 (ICLR 2024) -- Bash CLI via Docker containers, failure taxonomy (CLE, IF, IA, TLE), 8-environment evaluation framework, gpt-4 at 4.01 vs best open-source codellama-34b at 0.96
3. **Safety Survey**, 2605.23989v1 (arXiv, May 2026) -- Progent three-valued permission model (ASR 39.9% -> 1.0%), five-stage agent lifecycle, defense-in-depth framework
4. **Claw AI Lab**, 2605.22662v1 (arXiv, May 2026) -- Tool surface (bash, read, write, edit, glob, grep), runtime controller with time budgets and anti-fabrication checks, 5-layer research framework
5. **AFlow**, 2410.10762v4 (arXiv, Oct 2024) -- Code-represented workflows as Python classes, MCTS-driven optimization, operator patterns (ContextualGenerate, CodeGenerate, Format, Review, Revise, Ensemble, Test, Programmer)

### Repositories
6. **Claude Code Plugins Reference** (code.claude.com / Anthropic) -- Commands as flat `.md` files under `commands/` directory, `plugin.json` manifest with `userConfig` schema, 22 lifecycle hook events
7. **OpenCode / Kilo Code** (anomalyco/opencode, Kilo-org/kilocode) -- Session V2 event-sourcing, 7 agent modes, permission-gated tool registry (30+ tools), compaction at 80-100%, TUI with xterm.js
8. **Goose** (block/goose, AAIF) -- Command detection pipeline (/, /clear), 5-inspector tool security pipeline, compaction at 80% threshold, 22 lifecycle hooks, MCP integration
9. **CowAgent** (zhayujie/CowAgent) -- ReAct loop CLI, 12+ IM channel abstraction, 3-tier memory (context/daily/core), CLI subcommands (start/stop/restart/status/logs/update/skill install)
10. **RMUX** (Helvesec/rmux) -- Terminal multiplexer in Rust, key binding system, web share with post-quantum E2EE, pure domain model first architecture

## Changelog

- Run 3 (2026-06-03): Initial plan, Expert Review section, Changelog
- Run 4 (2026-06-07): Deep-read evidence update -- +21 citations from 6 papers (Terminal-Bench 2.0, AgentBench, Safety Survey, Claw AI Lab, AFlow), 4 repositories (OpenCode/Kilo Code, Goose, CowAgent, RMUX), 1 web doc (Claude Code Plugins Reference). Added Detailed Component Architecture, Comparison Table, Evidence Base section. Built-in commands expanded to include `/clear`. Added agent modes pattern from Kilo Code. Permission pipeline aligned with Progent/Safety Survey evidence. Sandbox isolation elevated to mandatory. Effort estimate revised 2->3 due to sandbox and permission pipeline complexity.
