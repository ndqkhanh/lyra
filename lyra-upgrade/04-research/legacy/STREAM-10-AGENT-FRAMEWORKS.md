# STREAM-10: Agent Frameworks & Harnesses Research

**Date:** 2026-05-30
**Status:** COMPLETE
**Research Stream:** Agent Frameworks & Harnesses Analysis
**Author:** Lyra Research Team (Claude-driven)
**Objective:** Survey 15 agent frameworks/harnesses for MIT-compatible techniques and architecture patterns applicable to Lyra — the MIT-licensed terminal-based multi-agent AI system.

---

## 1. License Compatibility Matrix

Lyra is MIT-licensed. Only MIT, Apache 2.0, BSD, ISC, and Unlicense are safe for direct code reuse. GPL-family licenses (GPL-2.0, GPL-3.0, AGPL) are **incompatible** — only architectural ideas can be borrowed, not code.

| # | Framework | License | MIT-Compatible? | Code Reuse OK? |
|---|-----------|---------|-----------------|-----------------|
| 1 | gbrain | MIT | YES | YES |
| 2 | gstack | MIT | YES | YES |
| 3 | ruflo | MIT | YES | YES |
| 4 | opencode | MIT | YES | YES |
| 5 | CowAgent | MIT | YES | YES |
| 6 | opendev | MIT | YES | YES |
| 7 | multica | Apache 2.0 | YES | YES |
| 8 | openhuman | GPL-3.0 | **NO** | Architecture only |
| 9 | rtk | Apache 2.0 | YES | YES |
| 10 | caveman | MIT | YES | YES |
| 11 | abtop | MIT | YES | YES |
| 12 | ECC | MIT | YES | YES |
| 13 | DCI-Agent-Lite | MIT | YES | YES |
| 14 | claude-code-best-practice | MIT | YES | YES |
| 15 | continuous-claude | MIT | YES | YES |

**Result:** 14 of 15 frameworks are MIT-compatible. Only **openhuman** (GPL-3.0) is restricted — architectural ideas only, no code reuse.

---

## 2. Per-Framework Analysis

### 2.1 gbrain — Garry's Agent Brain (garrytan/gbrain)

**License:** MIT | **Stars:** ~14,000+ | **Stack:** Bun + TypeScript, PGLite/Supabase

**Architecture:** GBrain is a three-layer agent memory system built around Markdown-as-truth. Layer 1 is a "Brain Repo" of markdown files (one per entity: person, company, concept), each with a "Compiled Truth" section (current summary) and a "Timeline" (append-only event log), all version-controlled via Git. Layer 2 is a hybrid retrieval index combining HNSW vector search, PostgreSQL `tsvector` full-text search, and Reciprocal Rank Fusion (RRF) with backlink-boosted ranking. Layer 3 is 34 skills following a "Thin Harness, Fat Skills" design philosophy. A standout feature is zero-LLM entity extraction — relationships like `attended`, `works_at`, `invested_in` are extracted via regex and string matching at write time, incurring zero token cost. The "Dream Cycle" performs nightly memory consolidation akin to human sleep, merging and de-duplicating information.

**Key Innovations Worth Porting:**
- **Zero-LLM Entity Extraction** — Regex/string-matching relationship extraction at write time. Saves massive token costs for Lyra's fleet memory. Could underpin Lyra's inter-agent knowledge graph.
- **Backlink-Boosted Ranking** — Pages frequently cross-referenced get higher retrieval priority. Directly applicable to Lyra's `.omc/project-memory.json` and shared memory.
- **Dream Cycle (Nightly Consolidation)** — Scheduled memory de-duplication and merging. Lyra could run this as a low-priority background agent during idle periods.
- **Markdown-as-Truth with Git Versioning** — Human-readable, diff-able memory that survives tool/agent changes. Lyra already uses JSON memory but a markdown-backed layer would improve transparency.

**Lyra Advantages:** Lyra's fleet orchestration (gossip protocol, fleet merge) already handles multi-agent coordination better than gbrain's single-operator design. Lyra's shared memory namespaces (`shared_memory_*`) provide cross-agent persistence that gbrain lacks entirely.

**Relevance Score:** **A** — The memory architecture is directly applicable to Lyra's agent persistence layer.

---

### 2.2 gstack — AI Role-Based Workflow System (garrytan/gstack)

**License:** MIT | **Stars:** ~88,000+ | **Stack:** Bun + TypeScript, Playwright

**Architecture:** GStack models software development as a role-based assembly line with 23-28 specialized AI personas, each activated via a slash command. The pipeline flows: Think (`/office-hours`) -> Plan (`/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`) -> Build (`/engineer`) -> Review (`/review`, `/cso`, `/qa`) -> Ship (`/ship`) -> Reflect (`/retro`). Each role is a markdown skill file with a specific system prompt, tool permissions, and output format. The system uses a persistent Chromium daemon for browser automation (3s cold start, 100-200ms warm), a custom @Ref element locator using accessibility trees instead of DOM selectors, and multi-layer security with bearer tokens, in-memory cookie decryption, and injection defenses. The claim is 600K+ lines of production code in 60 days (35% tests).

**Key Innovations Worth Porting:**
- **Role-Based Assembly Line** — Dedicated AI personas for each phase of a workflow. Lyra could adopt this for its fleet orchestration, assigning specialized agent roles per pipeline stage.
- **Persistent Browser Daemon** — Warm Chromium process for fast repeat testing. Lyra's research agents would benefit from sub-second browser launch for web scraping.
- **Accessibility-Tree Element Locator (@Ref)** — Evades CSP restrictions and framework-specific DOM structures. Useful for Lyra's browser automation tooling.
- **Full Lifecycle Closure** — Ship->Retro loop that feeds lessons back into planning. Lyra's continuous-learning-v2 skill could adopt this closed-loop pattern.

**Lyra Advantages:** Lyra's multi-agent fleet (not just role-play by a single LLM) provides *actual* parallel execution, not sequential role-switching. Lyra's gossip protocol enables true distributed consensus that gstack can only simulate through sequential prompts.

**Relevance Score:** **A** — The role-based pipeline pattern is immediately applicable to Lyra's task decomposition and orchestration.

---

### 2.3 ruflo — Enterprise Multi-Agent Orchestration (ruvnet/ruflo)

**License:** MIT | **Stars:** ~48,500+ | **Stack:** TypeScript + Rust/WASM, Next.js

**Architecture:** Ruflo is the most architecturally ambitious agent platform surveyed. It layers 100+ specialized agents over 314+ MCP tools, 32+ native plugins, and 5 swarm topologies (Hierarchical Queen-led, Mesh, Adaptive, Ring, Star). Consensus algorithms include Raft, Byzantine Fault Tolerance, Gossip, CRDT, and Quorum. A WASM-based "Agent Booster" handles simple code transforms without LLM calls (<1ms, claimed 352x speedup). AgentDB provides HNSW-indexed vector memory (150x-12,500x faster than naive search). SONA (Self-Optimizing Neural Architecture) learns from successful task patterns. The zero-trust federation layer supports cross-machine agent collaboration with mTLS + ed25519. AIDefence handles PII detection, prompt injection defense, and CVE scanning.

**Key Innovations Worth Porting:**
- **WASM Agent Booster** — Offloading simple code transforms to compiled WASM kernels. Lyra could implement deterministic operations (file parsing, JSON schema validation, regex transforms) in WASM for sub-millisecond execution without burning tokens.
- **Swarm Topology Pluggability** — Runtime-switchable agent topologies (hierarchical, mesh, ring). Lyra's fixed fleet model would benefit from configurable communication patterns.
- **SONA Pattern Learning** — Automatic extraction of successful task patterns into reusable templates. Could augment Lyra's `continuous-learning-v2` skill with concrete pattern persistence.
- **Zero-Trust Federation (mTLS + ed25519)** — Cross-machine agent identity and secure communication. Essential if Lyra ever spans multiple hosts.

**Lyra Advantages:** Lyra is significantly lighter-weight. Ruflo's 100+ agents and enterprise feature surface creates a steep learning curve and heavy dependency footprint. Lyra's terminal-native, zero-dependency philosophy is more aligned with the "one binary, zero deps" trend (exemplified by rtk). Lyra's gossip protocol and fleet merge already provide the distributed consensus that ruflo bolted on later.

**Relevance Score:** **A** — The WASM booster, topology abstraction, and pattern learning are high-value architectural patterns.

---

### 2.4 opencode — Terminal-Native AI Coding Agent (anomalyco/opencode)

**License:** MIT | **Stars:** ~15,000+ | **Stack:** Go (Bubble Tea TUI)

**Architecture:** OpenCode is a 100% open-source, provider-agnostic terminal AI coding agent built with Go and Bubble Tea for rich TUI. Its client/server architecture enables remote driving (e.g., from mobile apps). Key differentiators: built-in LSP support for code intelligence, a multi-agent system with built-in `build` and `plan` agents plus community-contributed custom agents, background agents for async delegation, dynamic context pruning, and OpenTelemetry telemetry. The community has built 100+ plugins including persistent memory with vector DBs, WakaTime, OS notifications, and git worktree management. A notable community pattern is the "consensus pattern" (seen in wildwasser/opencode-agents) where multiple models (Opus, Qwen3, Grok) evaluate the same decision and require agreement before proceeding.

**Key Innovations Worth Porting:**
- **Consensus Pattern (Multi-Model Voting)** — Running the same decision through 2-3 different models and requiring agreement. Lyra could implement this for high-stakes operations (production deploys, schema migrations, security-sensitive changes).
- **Client/Server Architecture** — The remote-driving capability enables mobile monitoring and control. Lyra's fleet dashboard could benefit from this separation.
- **Dynamic Context Pruning** — Intelligent token budget management that prunes less-relevant context as the window fills. Lyra's existing context management could adopt more aggressive, data-driven pruning.
- **Provider Agnosticism as Architecture** — OpenCode's clean provider abstraction (Claude, OpenAI, Gemini, Bedrock, Groq, local) is worth studying for Lyra's model routing layer.

**Lyra Advantages:** Lyra's agent fleet provides true parallelism (multiple concurrent agents), not just sequential agent switching. Lyra's skill system is significantly more mature (232+ skills vs opencode's emerging plugin ecosystem). Lyra's hook and validation infrastructure is more comprehensive.

**Relevance Score:** **A** — The consensus pattern and client/server architecture are directly applicable.

---

### 2.5 CowAgent — Personal AI Assistant with Multi-Channel Support (zhayujie/CowAgent)

**License:** MIT | **Stars:** ~44,600+ | **Stack:** Python

**Architecture:** CowAgent (formerly chatgpt-on-wechat) is a personal AI assistant framework designed for 7x24 deployment on personal machines or servers. It features a three-layer memory system (context window -> daily memory -> MEMORY.md persistent file), with daily "dream distillation" for memory consolidation. The skills system supports one-click install from a Skill Hub or natural-language skill creation. Tool access includes file I/O, terminal execution, Playwright browser, cron scheduling, and MCP protocol support. Multi-channel integration supports WeChat, DingTalk, Lark, QQ, and web. Multi-model support covers DeepSeek, Claude, Gemini, OpenAI, Qwen, GLM, Kimi, and more.

**Key Innovations Worth Porting:**
- **Three-Layer Memory Architecture** — Context (immediate) -> Daily (session) -> MEMORY.md (permanent). This graduated persistence model is cleaner than Lyra's flat JSON memory.
- **Skill Creation via Natural Language** — Users describe what they want, the system generates the skill. Lowers the barrier for Lyra skill authoring.
- **Multi-Channel Abstraction** — Clean separation between agent core and I/O channels. Lyra could adopt this to support Slack/Discord/Web interfaces alongside the terminal.

**Lyra Advantages:** Lyra's fleet architecture (multiple concurrent agents) vastly exceeds CowAgent's single-agent-per-instance model. Lyra's hook system and rule validation provide stronger safety guarantees. Lyra's gossip protocol enables distributed state that CowAgent cannot achieve.

**Relevance Score:** **B** — The three-layer memory model and multi-channel abstraction are worth studying, but CowAgent's single-agent architecture limits its relevance to Lyra's multi-agent core.

---

### 2.6 opendev — Compound AI Terminal Agent (opendev-to/opendev)

**License:** MIT | **Stars:** ~590+ | **Stack:** Rust

**Architecture:** OpenDev is a Rust-based, terminal-native coding agent built on a "compound AI" architecture — five specialized model roles (Normal, Thinking, Compact, Critique/Self-Critique, VLM) each bound to independently configured LLMs. Performance is extraordinary: 4.3ms startup, 9.4MB memory, 18MB binary (128x faster startup, 30x less memory than Claude Code). The "Agent Fleet" enables parallel sub-agent spawning with independent context windows and tool access. A five-layer defense-in-depth safety system includes schema-level tool gating (unsafe tools become invisible, not just blocked). Adaptive Context Compaction (ACC) uses five graduated strategies at progressive thresholds (70%-99%), reducing peak context by ~54%. MCP tools use lazy discovery — discovered on-demand via keyword search, reducing baseline token overhead from ~40% to <5%. Published with a formal arXiv paper (2603.05344).

**Key Innovations Worth Porting:**
- **Per-Workflow Model Binding** — Each agent role uses the optimal model for its task (e.g., Haiku for summarization, Opus for architecture). Lyra's model routing could adopt this granular binding.
- **Schema-Level Tool Gating** — Unsafe tools are removed from the schema entirely, not just blocked in prompts. This is a fundamental security improvement over prompt-based restrictions.
- **Adaptive Context Compaction (ACC)** — Five graduated strategies that activate at specific thresholds. More sophisticated than Lyra's current binary compact/not-compact approach.
- **Lazy MCP Tool Discovery** — Tools loaded on-demand via keyword search rather than pre-loaded. Would dramatically reduce Lyra's MCP overhead.
- **Published Research Paper** — The arXiv paper provides rigorous evaluation methodology that Lyra could replicate for its own benchmarks.

**Lyra Advantages:** Lyra's ecosystem (hooks, skills, fleet orchestration, gossip) is far more mature. OpenDev is a research-grade tool with ~590 stars — Lyra's production focus gives it broader applicability.

**Relevance Score:** **A** — The compound AI architecture, ACC, and lazy MCP discovery are among the highest-impact patterns in this survey.

---

### 2.7 multica — Multi-Agent Collaboration Platform (multica-ai/multica)

**License:** Apache 2.0 | **Stars:** ~22,700+ | **Stack:** Next.js 16 + Go (Chi/WebSocket) + PostgreSQL 17/pgvector

**Architecture:** Multica treats AI agents as first-class team members — each has a profile, appears on Kanban boards, and participates in comment threads. The core concept is "Squads" — groups of agents + humans led by a Leader Agent that routes and distributes tasks. Full task lifecycle management (queued -> claimed -> executing -> completed/failed) with WebSocket real-time progress streaming. Completed solutions are automatically "compounded" into reusable team skills, creating a knowledge snowball effect. Supports 12+ coding agents (Claude Code, Codex, OpenClaw, OpenCode, Hermes, Gemini, Cursor Agent, etc.) via a unified runtime abstraction. Architecture: Next.js frontend -> Go backend (Chi router + WebSocket) -> PostgreSQL (pgvector) -> Agent Daemon (local CLI runners).

**Key Innovations Worth Porting:**
- **Agent-as-Teammate UX Pattern** — Agents with profiles, presence indicators, and participation in comment threads. This social interface for agent interaction is a compelling alternative to Lyra's terminal-only UX.
- **Skill Compounding** — Every completed task enriches the team skill library. Lyra's skills are currently hand-authored; automatic compounding would accelerate skill growth.
- **Unified Agent Runtime** — One daemon manages multiple CLI-based coding agents. Lyra could abstract over Claude Code, Codex, OpenCode, etc. as interchangeable executors.
- **WebSocket Real-Time Streaming** — Live progress updates during agent execution. Lyra's TUI could benefit from streaming progress indicators for fleet operations.

**Lyra Advantages:** Lyra's gossip protocol and fleet merge are more advanced for distributed consensus than Multica's centralized Go backend. Lyra's terminal-native philosophy avoids the web frontend dependency. Lyra's hook and rule validation framework is more comprehensive than Multica's implicit trust in agent outputs.

**Relevance Score:** **B** — The agent-as-teammate UX and skill compounding are valuable patterns, but Multica's web-centric architecture diverges from Lyra's terminal-native focus.

---

### 2.8 openhuman — Personal AI with Subconscious Loop (tinyhumansai/openhuman)

**License:** GPL-3.0 (INCOMPATIBLE — architecture study only) | **Stars:** ~11,600+ | **Stack:** Rust (70%) + TypeScript (26%), Tauri desktop

**Architecture:** OpenHuman is a local-first personal AI agent designed to "know you" through persistent, deep integration with your digital life. The Memory Tree is a hierarchical knowledge graph built by pulling data from Gmail, Slack, GitHub, Notion, and 118+ OAuth integrations into compressed, structured Markdown stored in local SQLite with Obsidian-compatible output — theoretically supporting 1 billion tokens of local memory. The Subconscious Loop is its most distinctive feature: every 20 minutes, it polls all connected accounts, loads pending tasks, reads recent memories, and autonomously decides what to execute. During extended idle, it enters a "dream" state performing deep consolidation. TokenJuice compression (HTML->Markdown, URL shortening, deduplication, denoising) claims up to 80% token reduction. Built on Tauri for desktop deployment with an animated mascot and Google Meet participation capability.

**Key Innovations Worth Porting (Architecture Only — No Code):**
- **Subconscious Loop (Autonomous Background Polling)** — Scheduled, autonomous agent wake-ups that don't require user initiation. Lyra could implement this as a daemon mode with periodic fleet health checks and proactive task discovery.
- **Memory Tree with Hierarchical Knowledge Graph** — Graduated memory depth: hot (recent) -> warm (consolidated) -> cold (archived). More structured than Lyra's flat memory model.
- **TokenJuice Pre-LLM Compression Pipeline** — Multi-stage compression before content reaches the LLM. Lyra could add a compression middleware layer between tool output and context insertion.

**Lyra Advantages:** OpenHuman is GPL-3.0 (code cannot be reused in MIT-licensed Lyra). Its single-user desktop focus contrasts with Lyra's multi-agent terminal architecture. Lyra's fleet model enables true concurrent execution that OpenHuman's single-agent subconscious loop only simulates sequentially.

**Relevance Score:** **B** — High architectural relevance but zero code reuse potential due to GPL-3.0. The subconscious loop and memory tree patterns are worth reimplementing.

---

### 2.9 rtk — Rust Token Killer + Agent Infrastructure Toolkit (rtk-ai/rtk)

**License:** Apache 2.0 | **Stars:** ~49,300+ (rtk), ~350 (icm), ~120 (vox), ~70 (grit) | **Stack:** Rust

**Architecture:** RTK is not a single framework but an ecosystem of four Rust tools sharing a "single binary, zero dependencies" philosophy. The flagship `rtk` CLI proxy sits between AI coding tools and the shell, filtering and compressing command output before it reaches the LLM — claimed 60-90% token reduction across 100+ supported commands (git, docker, cargo, npm, pytest, kubectl, etc.) via four compression strategies (Smart Filtering, Grouping, Truncation, Deduplication). An auto-rewrite hook transparently intercepts bash commands across 13 AI tools. `icm` provides MCP-native permanent memory for agents. `vox` provides STT/TTS for voice-driven agent interaction. `grit` provides "Git for AI agents" — zero merge conflicts with any number of parallel agents.

**Key Innovations Worth Porting:**
- **Zero-Dependency Single-Binary Philosophy** — Each tool is a single Rust binary with no runtime dependencies. This is exactly Lyra's ideal deployment model.
- **Command Output Compression Proxy** — Transparently reducing shell output tokens. Lyra's CLI agents could use this pattern to reduce context consumption during long-running tool sequences.
- **MCP-Native Memory (icm pattern)** — Permanent agent memory exposed as MCP tools rather than file I/O. Lyra's shared memory could adopt MCP as a transport.
- **Agent-Native Version Control (grit pattern)** — Version control designed for concurrent AI agents with zero merge conflicts. Addresses a real pain point in Lyra's multi-agent fleet model.

**Lyra Advantages:** RTK tools are point solutions, not a platform. Lyra's integrated fleet orchestration, skill system, and hook infrastructure provide a more complete agent development environment. RTK's token compression could be integrated as a Lyra feature rather than requiring a separate tool.

**Relevance Score:** **A** — The zero-dependency binary model, output compression, and agent-native VCS are directly applicable patterns.

---

### 2.10 caveman — AI Output Compression Skill (JuliusBrussee/caveman)

**License:** MIT | **Stars:** ~20,000+ | **Stack:** Markdown/Shell (skill files, not compiled code)

**Architecture:** Caveman is a skill/plugin that reduces AI output token consumption by enforcing a "caveman-like" communication style — stripping articles, pleasantries, hedging, and filler while preserving code blocks, URLs, file paths, and version numbers. It offers three intensity levels (Lite/Full/Ultra) plus a Classical Chinese mode for maximum token density. Ancillary skills include `/caveman-commit` (extreme brevity commit messages), `/caveman-review` (one-line code reviews), and `/caveman-compress` (shrinking CLAUDE.md files). Benchmark claims 65% average output token savings (range 22-87%). The mechanism is purely prompt engineering — a system prompt instructing the LLM to emit compressed prose. Now supports 40+ AI tools.

**Key Innovations Worth Porting:**
- **Multi-Tier Compression Intensity** — Graduated compression levels letting users trade readability for token savings. Lyra could add configurable verbosity levels to agent responses.
- **Domain-Specific Compression** — The commit message and code review compressors show how compression rules can be specialized per output type. Lyra's agent output formatters could adopt type-aware compression.
- **Community Distribution Model** — Caveman spread as a skill across 40+ tools, demonstrating the power of tool-agnostic skill formats. Validates Lyra's skill marketplace strategy.

**Lyra Advantages:** Lyra could natively integrate caveman-style compression at the agent output layer rather than requiring a separate skill. Lyra's structured output formats (JSON schemas for tool calls) are already token-efficient compared to natural language responses.

**Relevance Score:** **B** — Useful technique but trivial to implement (a system prompt). The multi-tier compression model is the main architectural takeaway.

---

### 2.11 abtop — Agent Topology Monitoring Dashboard (graykode/abtop)

**License:** MIT | **Stars:** ~2,300+ | **Stack:** Rust

**Architecture:** Abtop is a TUI monitoring dashboard modeled after `htop`/`btop` but purpose-built for AI coding agents. It displays real-time token consumption per session, context window utilization (progress bars with overflow warnings), API rate limit status (remaining quota + reset countdown), orphan port detection (ports from crashed agents with one-key cleanup), subprocess/sub-agent hierarchy trees, and per-session git status. Deep tmux integration allows pressing Enter to jump directly to an agent's tmux pane. The security model is fully read-only — no API key needed, no prompt text or file content exposed. Supports Claude Code, Codex CLI, and OpenCode with varying feature depth.

**Key Innovations Worth Porting:**
- **Agent-Aware Process Monitoring** — Extending the `top`/`htop` paradigm with agent-specific metrics (token burn rate, context %, rate limits). Lyra's fleet dashboard should track these metrics per agent.
- **Orphan Resource Detection** — Automatic discovery and cleanup of resources left by crashed agents (ports, temp files, worktrees). Critical for Lyra's multi-agent fleet reliability.
- **Context Window Early Warning** — Visual alerts when context utilization approaches overflow thresholds. Lyra should implement this as a PreToolUse hook.
- **Read-Only Security Model** — Monitoring without credential access or prompt exposure. Important design principle for Lyra's observability layer.

**Lyra Advantages:** Lyra's fleet orchestration provides a natural aggregation point for agent metrics that abtop discovers reactively by scanning processes. Lyra could emit structured telemetry rather than requiring process scanning.

**Relevance Score:** **B** — The monitoring patterns are valuable, but abtop is a complementary tool rather than a framework to integrate.

---

### 2.12 ECC — Everything Claude Code (affaan-m/ECC)

**License:** MIT | **Stars:** ~182,000+ | **Stack:** TypeScript (v1), Rust control-plane alpha (v2)

**Architecture:** ECC is the most comprehensive agent harness in the Claude Code ecosystem, encompassing 60+ specialized sub-agents, 232+ skills, 79+ slash commands, and 75+ legacy command shims. It operates as a plugin installed into Claude Code, providing token optimization (model selection, system prompt slimming), memory persistence (hooks that save/load context across sessions), continuous learning v2 (instinct-based learning with confidence scoring that auto-extracts patterns from sessions into reusable skills), verification loops (checkpoint vs continuous evals with grader types and pass@k metrics), subagent orchestration with iterative retrieval patterns, and AgentShield security integration (1,282 tests, 102 rules). ECC 2.0 (alpha) adds a Rust control-plane with `dashboard`, `sessions`, `status`, and `daemon` subcommands. Won the Anthropic Hackathon.

**Key Innovations Worth Porting:**
- **Instinct-Based Continuous Learning** — Auto-extracting reusable patterns from session transcripts with confidence scoring. This is a concrete implementation of the pattern-learning concept Lyra's `continuous-learning-v2` skill aims for.
- **Verification Loop Taxonomy** — Checkpoint evals, continuous evals, grader types, and pass@k metrics. Lyra's verification framework should adopt this structured evaluation approach.
- **Multi-Profile Installation** — `--profile core`, `--profile minimal`, `--profile full` allowing users to choose how much harness they want. Lyra's install experience could adopt tiered profiles.
- **Cross-Harness Portability (gitagent format)** — A standardized format for agents/skills that works across Claude Code, Codex, Cursor, OpenCode, etc. This is an emerging standard Lyra should track.
- **AgentShield Integration** — 1,282 security tests and 102 rules for agent output validation. Lyra's security posture would benefit from a similar test suite.

**Lyra Advantages:** ECC is Claude Code-specific (despite cross-harness ambitions). Lyra's harness-agnostic architecture (terminal-native, not a plugin) provides broader applicability. Lyra's gossip protocol and fleet merge provide distributed coordination that ECC's single-harness model cannot match.

**Relevance Score:** **A** — ECC is the closest analog to Lyra's vision. The continuous learning, verification taxonomy, and cross-harness portability patterns are all directly applicable.

---

### 2.13 DCI-Agent-Lite — Zero-Index Retrieval Agent (DCI-Agent/DCI-Agent-Lite)

**License:** MIT | **Stars:** <100 | **Stack:** Python (uv)

**Architecture:** DCI-Agent-Lite is a research-grade framework that abandons traditional vector/semantic retrieval in favor of "Direct Corpus Interaction" — agents search raw text corpora using terminal tools like `rg`, `find`, and `sed` instead of pre-built embeddings or vector databases. This "zero-index retrieval" eliminates the embedding pipeline entirely. Five context management levels (level0: none, level1: light truncation, level2: stronger truncation, level3: truncation + compression, level4: truncation + compression + summarization) support long-running research sessions. Achieves 62.9% accuracy on BrowseComp-Plus using GPT-5.4-nano. The framework is extraordinarily minimal — it essentially wraps bash tools with lightweight context management.

**Key Innovations Worth Porting:**
- **Zero-Index Retrieval Paradigm** — Abandon vector search for direct grep/rg over raw corpora. For Lyra's codebase research agents, this could be more accurate than semantic search for exact symbol/pattern matching.
- **Five-Level Graduated Context Management** — Explicit, configurable compaction strategies at defined thresholds. Cleaner than Lyra's current binary compact/not-compact model.
- **Minimal Framework Philosophy** — The entire framework is bash tools + context management. Demonstrates that effective agents don't need heavy orchestration layers.

**Lyra Advantages:** Lyra's skill system and fleet orchestration provide capabilities far beyond DCI-Agent-Lite's research focus. Lyra's hybrid search (grep + semantic) already combines both paradigms.

**Relevance Score:** **B** — The zero-index concept and graduated context levels are valuable, but the framework is too research-specific to directly inform Lyra's general-purpose architecture.

---

### 2.14 claude-code-best-practice — Agent Development Patterns (shanraisshan/claude-code-best-practice)

**License:** MIT | **Stars:** ~32,000+ | **Stack:** Documentation (Markdown)

**Architecture:** Not a framework per se, but an exhaustive pattern library distilled from the Claude Code community: 83+ practical tips, workflow comparisons, agent collections, skill collections, and cross-model workflows. Key documented patterns include: the Generator-Evaluator pattern (independent agents for creation and verification with anti-rationalization rules), Context Survival via file-based state (checkboxes in plan files survive /compact), the Stack Frame Pattern for nested sub-plans (`docs/tasks/current.md`), multi-agent teams using git worktrees with absolute paths, the Two-Correction Rule (restart session after 2 corrections on the same issue), and a CLAUDE.md hierarchy design system. Curates links to major agent/skill collections (Agency Agents 188 subagents, Anthropic Skills 17 official, VoltAgent 151 curated subagents, Awesome Agent Skills 1,100+).

**Key Innovations Worth Porting:**
- **Generator-Evaluator Pattern Formalization** — Separating generation and evaluation into independent agent instances with skepticism-tuned evaluators. Lyra's fleet can implement this as a two-agent pipeline with explicit evaluation criteria.
- **File-Based Context Survival** — Using checkbox progress markers in plan files (`- [ ]`, `- [~]`, `- [x]`) to survive context compaction. Lyra's task state management should adopt this.
- **Stack Frame Pattern** — Nested sub-plan files that function like call stack frames. Elegant solution for complex multi-level task decomposition in Lyra.
- **Two-Correction Rule** — Operational heuristic: restart the session if the same issue requires >2 corrections. Lyra could implement this as an automatic session recycling trigger.

**Lyra Advantages:** These are operational patterns, not code. Lyra can adopt them immediately with no dependency cost. Lyra's fleet model enables the Generator-Evaluator pattern more naturally than single-agent tools.

**Relevance Score:** **A** — The patterns are immediately actionable with zero integration cost. The CLAUDE.md hierarchy and Generator-Evaluator patterns are particularly valuable.

---

### 2.15 continuous-claude — Autonomous PR Loop (AnandChowdhary/continuous-claude)

**License:** MIT | **Stars:** ~1,335 | **Stack:** Shell (Bash)

**Architecture:** Continuous-Claude wraps Claude Code in an autonomous, iterative loop that fully automates the GitHub PR lifecycle: create branch -> run Claude Code -> optional reviewer pass -> commit -> push -> create PR -> wait for CI -> auto-fix on failure -> merge -> repeat. The "secret sauce" is a `SHARED_TASK_NOTES.md` file that persists across iterations, acting as external memory with the relay-race metaphor: "Think of it as a relay race where you're passing the baton." Agents emit a completion signal (`CONTINUOUS_CLAUDE_PROJECT_COMPLETE`) and the loop stops after a configurable threshold of consecutive signals. Supports cost/duration limits (`--max-cost`, `--max-duration`, `--max-runs`), parallel execution via git worktrees, and CI failure auto-recovery. The philosophy is described as "radiation of probabilities" — individual agent runs are noisy particles, but the general direction emerges from the distribution.

**Key Innovations Worth Porting:**
- **Relay-Race Context Handoff** — SHARED_TASK_NOTES.md as a baton-passing mechanism between independent agent invocations. Directly applicable to Lyra's fleet iteration model where agents run sequentially on long tasks.
- **Completion Signal Protocol** — Agents explicitly signal completion; loop stops after N consecutive signals. Elegant termination condition for autonomous loops. Lyra's autonomous mode needs this.
- **CI Failure Auto-Recovery** — Agent inspects CI failure logs, fixes, re-pushes, re-checks. Lyra's verification loop should include automated fix-attempt cycles.
- **Cost-Bounded Autonomy** — Hard limits on cost, duration, and iteration count. Essential safety rails for Lyra's autonomous execution mode.

**Lyra Advantages:** Continuous-Claude is a thin shell wrapper (~1000 lines of bash). Lyra's fleet model provides genuine parallelism (not simulated via sequential PRs), proper task decomposition (not monolithic prompts), and structured validation (not just CI pass/fail). Lyra would absorb Continuous-Claude's functionality as a native feature, not an external wrapper.

**Relevance Score:** **A** — The relay-race context handoff, completion signals, and cost-bounded autonomy are directly implementable patterns for Lyra's autonomous loop mode.

---

## 3. Cross-Cutting Patterns

Techniques that appear independently across 3+ frameworks, signaling industry convergence:

### 3.1 Memory Consolidation ("Dream Cycles")
**Frameworks:** gbrain, CowAgent, openhuman, ECC
**Pattern:** Scheduled background processes that de-duplicate, merge, and restructure memory during idle periods. gbrain calls it "Dream Cycle," openhuman calls it "Subconscious Loop," CowAgent calls it "Dream Distillation." All converge on the idea that raw agent memory degrades without periodic consolidation.
**For Lyra:** Implement a fleet-level memory consolidation daemon that runs during low-activity periods, merging `.omc/project-memory.json` entries, pruning stale shared_memory keys, and regenerating indices.

### 3.2 Graduated Context Management
**Frameworks:** DCI-Agent-Lite (5 levels), opendev (ACC with 5 graduated strategies), opencode (dynamic pruning)
**Pattern:** Rather than binary compact/not-compact, apply increasingly aggressive compression at specific context-fill thresholds (70%, 80%, 90%, 95%, 99%).
**For Lyra:** Replace current binary compaction with graduated strategies tied to context utilization percentages, using truncation -> compression -> summarization as fill-level increases.

### 3.3 Tool Output Compression
**Frameworks:** rtk (60-90% shell output reduction), caveman (65% prose reduction), openhuman (80% TokenJuice), ECC (system prompt slimming)
**Pattern:** Compressing agent-visible data before it enters the context window, using command-aware filtering (rtk), prose stripping (caveman), or multi-stage pipelines (openhuman).
**For Lyra:** Add a compression middleware layer in the agent loop that processes tool outputs before context insertion, with type-aware strategies (shell output: rtk-style; natural language: caveman-style; HTML: TokenJuice-style).

### 3.4 Role Specialization / Compound AI
**Frameworks:** gstack (23-28 roles), ruflo (100+ agents), opendev (5 model roles), ECC (60+ agents)
**Pattern:** Decomposing monolithic agent behavior into specialized sub-roles, each with tailored prompts, tool access, and model selection.
**For Lyra:** Formalize Lyra's fleet roles (architect, executor, reviewer, security-auditor) with per-role model binding, tool allowlists, and output schemas.

### 3.5 File-Based State for Context Survival
**Frameworks:** continuous-claude (SHARED_TASK_NOTES.md), claude-code-best-practice (checkbox plan files, Stack Frame Pattern), ECC (memory persistence hooks)
**Pattern:** External state files that survive context compaction and session resets, acting as continuity mechanisms between independent agent invocations.
**For Lyra:** Adopt the Stack Frame Pattern for nested task decomposition and implement SHARED_TASK_NOTES.md-style handoff files for long-running fleet operations.

### 3.6 Verification Loops with Structured Evaluation
**Frameworks:** ECC (checkpoint evals, continuous evals, pass@k), continuous-claude (reviewer pass, CI auto-fix), opencode (consensus pattern), claude-code-best-practice (Generator-Evaluator)
**Pattern:** Structured verification as a first-class pipeline stage with specific evaluation methodologies, not ad-hoc checking.
**For Lyra:** Implement the Generator-Evaluator pattern as a standard fleet pipeline with configurable evaluation criteria, grader types, and pass@k metrics.

### 3.7 Autonomous Background Execution
**Frameworks:** openhuman (20-min polling), continuous-claude (iterative loop with completion signals), opencode (background agents), CowAgent (7x24 deployment)
**Pattern:** Agents that run without continuous user attention, waking periodically or running in loops until completion conditions are met.
**For Lyra:** Implement Lyra daemon mode with configurable wake intervals, task discovery, autonomous execution with cost/duration bounds, and completion signal protocols.

---

## 4. Feature Comparison Matrix vs Lyra

| Capability | Lyra (Current) | gbrain | gstack | ruflo | opencode | opendev | ECC | continuous-claude |
|---|---|---|---|---|---|---|---|---|
| Multi-Agent Fleet | YES (gossip) | NO (single-op) | NO (sequential roles) | YES (100+ agents) | YES (community) | YES (agent fleet) | YES (60+ sub-agents) | NO (sequential loop) |
| Gossip Protocol | YES | NO | NO | YES (Gossip) | NO | NO | NO | NO |
| Fleet Merge | YES | NO | NO | NO | NO | NO | NO | NO |
| Skill System | YES (232+) | YES (34) | YES (23-28) | YES (32+ plugins) | YES (community) | NO | YES (232+) | NO |
| Hook Infrastructure | YES | NO | NO | NO | NO | YES (lifecycle) | YES | NO |
| Memory Persistence | YES (JSON) | YES (Markdown+Git) | NO | YES (AgentDB) | YES (vector DB) | NO | YES (hooks) | YES (SHARED_NOTES) |
| Context Compaction | YES (binary) | NO | NO | NO | YES (dynamic) | YES (ACC, 5-level) | YES | NO |
| Provider Agnostic | PARTIAL | N/A | Anthropic-only | YES (multi) | YES (multi) | YES (9 providers) | Claude Code-only | Claude Code-only |
| TUI/Native Terminal | YES | N/A | CLI | YES (CLI) | YES (Bubble Tea) | YES (Textual) | CLI | CLI |
| WASM Offloading | NO | NO | NO | YES (WASM) | NO | NO | NO (Rust alpha) | NO |
| Security Validation | YES (rules) | NO | YES (CSO role) | YES (AIDefence) | NO | YES (5-layer) | YES (AgentShield) | NO |
| Consensus Algorithms | YES (gossip) | NO | NO | YES (Raft, BFT, CRDT) | YES (multi-model) | NO | NO | NO |
| Cross-Harness Portable | NO | NO | NO | NO | NO | NO | YES (gitagent) | NO |

---

## 5. Top 10 Techniques Ranked by Impact x Effort

Each technique scored on Impact (1-10 for Lyra's architecture) and Effort (1-10 inverted: 1 = hardest, 10 = easiest). Score = Impact * Effort / 10.

| Rank | Technique | Source | Impact | Effort (inv) | Score | Description |
|------|-----------|--------|--------|-------------|-------|-------------|
| 1 | **File-Based Context Survival** | continuous-claude, claude-code-best-practice | 9 | 10 | 9.0 | Checkbox plan files, SHARED_TASK_NOTES, Stack Frame Pattern. Trivial to implement, solves the #1 pain point of context loss across sessions. |
| 2 | **Graduated Context Compaction** | opendev (ACC), DCI-Agent-Lite | 9 | 9 | 8.1 | Replace binary compact/not-compact with 5 graduated strategies at specific fill thresholds. Requires refactoring existing compaction code but well-understood problem. |
| 3 | **Generator-Evaluator Pattern** | claude-code-best-practice, ECC | 8 | 10 | 8.0 | Structure verification as independent agent pass with skepticism tuning. Lyra's fleet model makes this a configuration change, not new code. |
| 4 | **Tool Output Compression Middleware** | rtk, caveman | 8 | 9 | 7.2 | Add compression layer between tool output and context insertion. Type-aware strategies (shell vs prose vs HTML). Moderate implementation, high token savings. |
| 5 | **Completion Signal Protocol** | continuous-claude | 7 | 10 | 7.0 | Agents emit explicit completion signals; loop stops after N consecutive. Trivial to add to Lyra's autonomous loop mode. |
| 6 | **Zero-LLM Entity/Metadata Extraction** | gbrain | 7 | 8 | 5.6 | Regex/string-matching for relationship extraction at write time. Saves token costs. Requires careful pattern design but no ML infrastructure. |
| 7 | **Per-Role Model Binding** | opendev, gstack | 8 | 7 | 5.6 | Each fleet role gets optimal model (Haiku for summarization, Sonnet for execution, Opus for review). Requires model routing refactor. |
| 8 | **Memory Consolidation Daemon** | gbrain, CowAgent, openhuman | 7 | 7 | 4.9 | Scheduled background memory de-duplication and merging. Moderate implementation: daemon process + consolidation rules. |
| 9 | **Lazy MCP Tool Discovery** | opendev | 6 | 8 | 4.8 | Load MCP tools on-demand via keyword search instead of pre-loading. Reduces baseline token overhead. Requires MCP integration changes. |
| 10 | **WASM Agent Booster** | ruflo | 8 | 5 | 4.0 | Offload deterministic operations (parsing, validation, transforms) to compiled WASM. High impact but significant engineering investment. |

---

## 6. Recommendations Summary

### Immediate (Sprint-Ready)
These patterns require minimal code changes and deliver immediate value:

1. **Adopt File-Based Context Survival** — Implement SHARED_TASK_NOTES.md handoff files and the Stack Frame Pattern (`docs/tasks/current.md`) for Lyra's fleet operations. This is a documentation convention + ~100 lines of file I/O code.
2. **Implement Completion Signal Protocol** — Add `LYRA_TASK_COMPLETE` emission to autonomous agents and a configurable consecutive-signal threshold before loop termination.
3. **Deploy Generator-Evaluator Pattern** — Configure a standard fleet pipeline: Generator Agent -> Evaluator Agent (separate instance, skepticism-tuned) -> Fix loop (max 3 rounds).

### Short-Term (1-2 Sprints)
These require moderate refactoring but have validated reference implementations:

4. **Implement Graduated Context Compaction (ACC)** — Replace binary compaction with 5 graduated strategies based on OpenDev's ACC model, activated at 70%, 80%, 90%, 95%, and 99% context utilization.
5. **Add Tool Output Compression Middleware** — Create a middleware layer with type-aware compression strategies: rtk-style for shell output, caveman-style for natural language, TokenJuice-style for HTML.
6. **Build Zero-LLM Metadata Extraction** — Implement regex/string-matching entity extraction for Lyra's `.omc/project-memory.json`, following gbrain's pattern.

### Medium-Term (3-4 Sprints)
These require architectural planning and significant engineering:

7. **Refactor Model Routing for Per-Role Binding** — Allow each fleet role to specify its preferred model and provider, with fallback chains.
8. **Implement Memory Consolidation Daemon** — Background process that merges, de-duplicates, and re-indexes Lyra's shared memory during idle periods.
9. **Implement Lazy MCP Tool Discovery** — On-demand MCP tool loading via keyword search to reduce baseline context overhead.

### Long-Term (Architecture Roadmap)
These are major architectural additions that should inform Lyra's v2 design:

10. **WASM Offloading Engine** — Deterministic operations compiled to WASM for sub-millisecond execution without LLM calls. Requires a WASM runtime integration (wasmtime/wasmer) and a compilation pipeline.
11. **Cross-Harness Agent Format** — Adopt or define a portable agent/skill format (track ECC's gitagent proposal) so Lyra agents can run in Claude Code, Codex, OpenCode, etc.
12. **Subconscious Loop / Daemon Mode** — Full autonomous background execution with configurable wake intervals, proactive task discovery, and cost/duration safety bounds.

### Non-Recommendations (Explicitly Declined)
- **GPL-3.0 Code Reuse (openhuman):** Zero code reuse. Study architecture only.
- **Web-Centric Architecture (multica):** Lyra is terminal-native. The agent-as-teammate UX pattern is worth studying but the Next.js architecture is not.
- **Enterprise Feature Bloat (ruflo):** 100+ agents, 5 consensus algorithms, and zero-trust federation are over-engineered for Lyra's scope. Adopt the WASM booster pattern but not the full enterprise surface.

---

## 7. References

### Frameworks Analyzed
1. gbrain — https://github.com/garrytan/gbrain (MIT)
2. gstack — https://github.com/garrytan/gstack (MIT)
3. ruflo — https://github.com/ruvnet/ruflo (MIT)
4. opencode — https://github.com/anomalyco/opencode (MIT)
5. CowAgent — https://github.com/zhayujie/CowAgent (MIT)
6. opendev — https://github.com/opendev-to/opendev (MIT)
7. multica — https://github.com/multica-ai/multica (Apache 2.0)
8. openhuman — https://github.com/tinyhumansai/openhuman (GPL-3.0)
9. rtk — https://github.com/rtk-ai/rtk (Apache 2.0)
10. caveman — https://github.com/JuliusBrussee/caveman (MIT)
11. abtop — https://github.com/graykode/abtop (MIT)
12. ECC — https://github.com/affaan-m/ECC (MIT)
13. DCI-Agent-Lite — https://github.com/DCI-Agent/DCI-Agent-Lite (MIT)
14. claude-code-best-practice — https://github.com/shanraisshan/claude-code-best-practice (MIT)
15. continuous-claude — https://github.com/AnandChowdhary/continuous-claude (MIT)

### Related Research
- OpenDev arXiv Paper (2603.05344): "Building Effective AI Coding Agents for the Terminal: Scaffolding, Harness, Context Engineering, and Lessons Learned"
- ECC Autonomous Loops Skill: https://github.com/affaan-m/everything-claude-code/blob/main/skills/autonomous-agent-harness/SKILL.md
- GStack Architecture: https://github.com/garrytan/gstack/blob/master/ARCHITECTURE.md
- claude-code-best-practice Agent Patterns: https://github.com/shanraisshan/claude-code-best-practice
- Agency Agents Collection (188 subagents): https://github.com/msitarzewski/agency-agents
- Awesome Agent Skills (1,100+): https://github.com/awesome-agent-skills/awesome-agent-skills

### Key Articles
- "Building Effective AI Coding Agents for the Terminal" — arXiv 2603.05344
- "RTK: New Rust CLI Agent Cuts LLM Token Usage by 60-90%" — aitoolly.com (May 2026)
- "GStack Tutorial: Garry Tan's Claude Code Workflow for 10K LOC/Week" — SitePoint
- "OpenHuman: A Local-First Personal AI Super Intelligence" — dev.to (WonderLab series)
- "Multica: The Open-Source Managed Agents Platform" — DoNews

---

*End of STREAM-10 deliverable. All 15 frameworks researched. 14/15 MIT-compatible. 12 ranked recommendations across 4 time horizons.*
