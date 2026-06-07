# garrytan/gstack -- Deep-Read

## 1. Headline Feature & Mechanism

**gstack is an open-source software factory by Y Combinator CEO Garry Tan: a collection of 23+ opinionated Claude Code slash-command skills backed by a persistent headless Chromium daemon, designed to let a single developer operate at the velocity of a team of twenty.**

The core mechanism is the **long-lived browser daemon**. Rather than spawning a new Playwright browser per command (3-5 second cold start, lost state between calls), gstack runs a Bun.serve HTTP server on localhost that holds a persistent Chromium session. The first command boots everything (~3s); every subsequent command is a ~100-200ms HTTP POST. State -- cookies, tabs, localStorage, login sessions -- survives across commands. A state file at `.gstack/browse.json` records the server's PID, port, and auth token; the CLI auto-starts the server if the state file is missing or the health check fails, and auto-shuts it down after 30 minutes idle.

The skill system is equally central. Each skill is a markdown file (SKILL.md) generated from a .tmpl template via `bun run gen:skill-docs`. Heavy skills (e.g., `/ship` was 167KB) are carved into a skeleton + on-demand sections to manage token budgets -- the skeleton stays in context, the deep review bodies load only when the agent reaches them. Skills run in a sprint order: Think (`/office-hours`) -> Plan (`/plan-ceo-review`, `/plan-eng-review`) -> Build -> Review (`/review`) -> Test (`/qa`) -> Ship (`/ship`) -> Reflect (`/retro`). Each skill's output feeds into the next.

## 2. Architecture & Core Modules

**Entry points:**
- `browse/src/cli.ts` -- Compiled binary CLI that reads state file, finds/launches server, sends HTTP commands, prints responses. Ships as a single ~58MB standalone binary via `bun build --compile`.
- `browse/src/server.ts` -- Bun.serve HTTP on localhost, dispatches commands to Playwright, manages console/network/dialog circular buffers, handles SSE endpoints, and enforces auth. ~700 lines of imports and routing.
- `browse/src/browser-manager.ts` -- Browser lifecycle: Chromium launch options, context recreation (cookie/state preservation on user-agent change), crash handling, sandbox policy. ~1500 lines.
- `browse/src/commands.ts` -- Single source of truth command registry. Categories: READ (text, html, links, forms, accessibility), WRITE (goto, click, fill, scroll), META (tabs, screenshot, snapshot, handoff). ~400 lines.

**Data flow:**
```
Claude Code --(Tool call: "$B snapshot -i")--> CLI (compiled binary)
  --> reads .gstack/browse.json for port+token
  --> POST /command to localhost:PORT
  --> Server dispatches to Playwright on Chromium via CDP
  --> Returns plain text response
```

**Security model:**
- Dual-listener architecture: Local listener (127.0.0.1, full command surface) vs tunnel listener (ngrok, locked allowlist of browser-driving commands only). Physical TCP port separation prevents tunnel callers from reaching `/health`, `/cookie-picker`, or root-token endpoints.
- Bearer token auth (random UUID per session, written 0o600).
- Layered prompt injection defense for sidebar agent: L1-L3 content security (datamarking, hidden element strip, URL blocklist), L4 ONNX ML classifier (22MB BERT-small, local), L4b transcript classifier (Claude Haiku), L5 canary token (deterministic leak detection), L6 ensemble combiner (requires 2 classifiers to agree).
- Cookie security: macOS Keychain dialog for first import, in-memory AES decryption, read-only SQLite access, cookie values never appear in logs.

**Core modules:**
| Module | Path | Purpose |
|--------|------|---------|
| Browse daemon | `browse/src/` | Persistent Chromium server (CLI + HTTP + Playwright) |
| Skills | `review/`, `ship/`, `qa/`, `office-hours/`, `plan-*-review/`, `cso/`, etc. | 20+ independent workflow skills, each a generated SKILL.md |
| Host adapters | `hosts/claude.ts`, `codex.ts`, `cursor.ts`, etc. | Configuration for 10+ AI coding agents |
| Shared libs | `lib/redact-engine.ts`, `lib/gbrain-guards.ts`, `lib/worktree.ts` | Redaction engine, gbrain guardrails, worktree utilities |
| CLI tools | `bin/` | 80+ CLI utilities (gstack-config, gstack-redact, gstack-next-version, gstack-version-bump, etc.) |
| Scripts | `scripts/gen-skill-docs.ts`, `scripts/build.sh` | Documentation generation, build, eval utilities |
| Chrome extension | `extension/` | Chrome side panel with PTY terminal, CSS inspector, activity feed |
| Design binary | `design/src/` | GPT Image API CLI for design mockup generation |

**Key dependencies:** playwright, @huggingface/transformers (ONNX ML), @ngrok/ngrok, puppeteer-core, bun (runtime + bundler). Dev: @anthropic-ai/sdk, @anthropic-ai/claude-agent-sdk.

## 3. Performance/Benchmarks

| Metric | Value | Source |
|--------|-------|--------|
| Browse command latency (warm) | ~100-200ms | ARCHITECTURE.md |
| Browse command latency (cold start) | ~3s | ARCHITECTURE.md |
| Browser idle timeout | 30 minutes | server.ts config |
| Compiled binary size | ~58MB | ARCHITECTURE.md |
| /ship always-loaded tokens (v1.54) | 69KB / ~17.2K tokens (was 167KB / ~41.8K, -59%) | CHANGELOG v1.54.0.0 |
| /plan-ceo-review skeleton (v1.56) | 80.7KB (-42% from 138.8KB) | CHANGELOG v1.56.0.0 |
| /office-hours skeleton (v1.56) | 89.0KB (-24.8% from 118.3KB) | CHANGELOG v1.56.0.0 |
| /plan-eng-review skeleton (v1.56) | 54.9KB (-48.7% from 107.0KB) | CHANGELOG v1.56.0.0 |
| Eval run cost | ~$4/run max | CLAUDE.md |
| E2E test cost | ~$3.85/run max | CLAUDE.md |
| Sidebar ML classifier model | 22MB ONNX (int8 BERT-small), opt-in 721MB DeBERTa-v3 | ARCHITECTURE.md |
| Productivity claim (Garry Tan) | ~810x 2013 pace (11,417 vs 14 logical LOC/day) | README + docs/ON_THE_LOC_CONTROVERSY.md |
| Parallel sprints | 10-15 via Conductor | README |
| Port range | Random 10000-60000, no config needed for multi-workspace | ARCHITECTURE.md |

## 4. Trade-offs

**Wins:**
- **Persistent browser state is transformative for agent-based QA.** Log in once, stay logged in across 20+ commands. Sub-second latency vs 3-5s per cold start. The CHANGELOG claims `/qa` "let me go from 6 to 12 parallel workers."
- **Opinionated skill pipeline prevents the "blank prompt" problem.** First-time Claude Code users get a structured workflow instead of staring at an empty chat.
- **Compiled binary distribution** means zero `node_modules` at runtime. One binary, zero PATH management.
- **Cross-agent compatibility** is first-class: 10 host adapters (Claude Code, Codex CLI, Cursor, OpenClaw, etc.) from day one, not bolted on.
- **Prompt injection defense** is unusually thorough for an open-source tool: ML classifier + transcript pass + canary tokens + ensemble verdict. Most similar tools do none of this.
- **MIT license** means anyone can fork and customize.

**Loses:**
- **Claude Code is the primary design target.** Other agents get the same skills but may not render or execute them identically. The README says "gstack works on 10 AI coding agents" but the architecture is clearly Claude-first.
- **Bun compile limitation.** The distributed binaries are Mach-O arm64 only -- they do NOT work on Linux, Windows, or Intel Macs. `./setup` builds from source on those platforms, so it works, but there is no precompiled option.
- **Markdown as "code" is hard to validate.** Skill templates are prose prompts that guide LLM behavior. There is no type system, no schema, no static analysis for prompt correctness. The project mitigates this with E2E evals ($4/run), LLM-as-judge evals, and A/B tests on carved sections.
- **Extreme complexity for a "single developer" tool.** 80+ CLI binaries, 20+ skill directories, a Chrome extension, a browser daemon, gbrain integration, iOS QA daemon -- the surface area is enormous. The CHANGELOG shows 56+ versions in rapid iteration.
- **Token efficiency is a constant battle.** v1.54-1.56 are dominated by skill carving to reduce token consumption. Heavy skills started at 100-167KB. The project acknowledges this is a perpetual engineering cost.
- **Prompt injection defense has a narrow coverage scope.** The layered ML models only protect the sidebar agent, not the main Claude Code session. Claude's own prompts are not scanned; only page content that the sidebar reads.
- **gbrain data-loss race** (v1.55.0.0 fix note): `/sync-gbrain` could trigger gbrain's autopilot to rm-rf a working tree. The fix added guards but the bug existed through earlier versions.
- **E2E tests are non-deterministic and expensive** (~$4/run). CI gate covers only "gate" tier; periodic tests run weekly. Diff-based test selection reduces cost but adds complexity.

## 5. Design Rationale

Every major architectural choice in gstack is a direct response to a concrete failure mode of existing AI-coding tools, documented explicitly in ARCHITECTURE.md and CHANGELOG entries.

- **Daemon over per-command browser**: "The key insight: an AI agent interacting with a browser needs sub-second latency and persistent state." This is a first-principles observation about the difference between human and agent browser use. Humans tolerate startup time because they use sessions. Agents issue 20+ commands per QA session; 3s cold-start per command = 60s overhead.
- **Bun over Node**: Not for speed (the bottleneck is Chromium) but for compiled binaries (no node_modules at runtime) and native SQLite (cookie decryption without native addon compilation). Purely practical engineering.
- **Dual-listener tunnel security**: "Header inference (check x-forwarded-for, check origin) is unreliable; socket separation isn't." A principled rejection of soft security for hard network topology.
- **Skill skeletons over monolithic prompts**: "The skills you run most start markedly lighter... You will not notice any behavior change in the reviews themselves; they run section for section as before. What you get is more of the context window left for your actual work." This mirrors the Lyra problem exactly -- how to deliver comprehensive capability without exhausting context windows.
- **Boil the Lake philosophy** (ETHOS.md): "When the complete implementation costs minutes more than the shortcut -- do the complete thing. Every time." This is an explicit rejection of the "ship minimal" startup ethos, informed by the AI compression ratios the author has measured.
- **Self-forking design**: "Fork it. Improve it. Make it yours." The MIT license and permissive ethos acknowledge that every engineering team has different preferences for AI tooling. gstack provides an opinionated default that can be customized per-team.

## 6. Transfer to Lyra

### One Idea: Persistent Skill-Stage Browser Daemon with On-Demand Workflow Sections

Lyra's agent already needs a browser for the "browse for research" task. The gstack pattern -- a long-lived browser daemon that persists state across commands and auto-manages lifecycle -- is a perfect fit. Lyra should run a persistent Playwright/BrowserBase session per user, stored in memory/redis, keyed by session ID. The daemon keeps authenticated state (login cookies, session tokens) alive, eliminating the cold-start pain for tasks like "continue scraping from where you left off."

Complementing this: gstack's **skill carving pattern** (skeleton + on-demand sections) is directly applicable to Lyra's workstream architecture. Each Lyra workstream (router, planner, memory, context, etc.) could ship a lightweight "skeleton" that references deeper on-demand instructions -- solving Lyra's perennial context-window problem without sacrificing capability.

### Workstream Route

This maps to **section 4.3 (Agent Memory & State Management)** in the Lyra upgrade plan. The browser-daemon pattern fits under the "persistent state" subsection. The on-demand skill-section pattern fits under "context window optimization" / "prompt compression." Both are concrete, well-tested implementations of problems Lyra currently solves with hackier approaches.

### Impact/Effort/Tier

- **Impact: 8/10** -- The browser daemon alone eliminates a major pain point (agent browser automation is currently flaky and stateless). The skill-section pattern is a permanent fix for context-window pressure.
- **Effort: 6/10** -- Implementing a persistent browser daemon requires infrastructure (redis/Postgres for session state, Playwright management, crash recovery). Implementing skill sections is simpler but requires revamping how Lyra's skills reference their detailed instructions.
- **Tier: Core** -- This is not a nice-to-have. Reliable browser automation is foundational to Lyra's "research" capability. Context-window pressure affects every single Lyra session.

### License

**MIT License.** Compatible with Lyra's codebase. No restrictions on use, modification, or distribution. The LICENSE file (Copyright (c) 2026 Garry Tan) explicitly permits sublicensing, so portions of the daemon or skill architecture can be adapted into Lyra freely.

---

**Note path:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/garrytan__gstack.md`
