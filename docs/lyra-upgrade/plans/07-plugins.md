# Plugins — Plan (§4.7)

> Run 4, 2026-06-07

## Plain-Language Summary

Lyra's plugin system loads Python packages that extend agent capabilities — adding custom tools, hook handlers, MCP servers, and UI components. Plugins are discovered from project-local and user-global directories, versioned, and hot-reloaded. A marketplace enables community sharing.

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Plugins Reference (web, Anthropic) | Plugin directory structure, component registry (6 core + 2 experimental types), manifest format, 22 lifecycle hooks, three installation scopes (user/project/local), userConfig + variable substitution pattern, plugin cache at `~/.claude/plugins/cache/`, persistent data directory surviving updates, explicit semver vs. implicit git SHA versioning, token cost split into "always-on" (~180 tok/session) and "on-invoke" (~2400 tok/skill) |
| Claude Code MCP Docs (web, Anthropic) | Deferred capability loading via Tool Search; only tool names + 2KB server instructions at session start; full schemas on-demand; three config scopes; dynamic tool updates via `list_changed` notifications; auto-reconnection with exponential backoff (5 attempts, 1s-16s); OAuth 2.0 support |
| Claude Code Agent SDK Tool Search (web, Anthropic) | 50 tool definitions consume 10K-20K tokens; accuracy degrades at >30-50 tools loaded at once; 3-5 most relevant tools fetched per search; max catalog 10,000 tools; default activation threshold at 10% of context window (`auto`); small-tool fast-path at ~10 tools |
| Claude Code Skills Docs (web, Anthropic) | SKILL.md directory-based plugin architecture with YAML frontmatter; lazy loading (description always in context at 1% of window, full body only on invoke); after compaction: 5K tokens/skill, 25K combined budget; four storage tiers with precedence rules; dynamic context injection via `!`command`` syntax; subagent isolation via `context: fork` |
| Claude Code Hooks Docs (web, Anthropic) | 17 lifecycle events, 5 hook types (command/http/mcp_tool/prompt/agent); four-state permission model (allow/deny/ask/defer); matcher patterns with regex; structured JSON decision output; async hooks with non-blocking audit logging; path placeholders `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` |
| Claude Code Sandboxing Docs (web, Anthropic) | OS-level subprocess sandbox (Seatbelt on macOS, bubblewrap on Linux); filesystem isolation (write only to CWD by default); network isolation via outbound proxy; two orthogonal layers: permission rules + OS sandbox; escape hatch via `dangerouslyDisableSandbox`; managed lockdown settings |
| Claude Code Security Docs (web, Anthropic) | Default-deny permission model; write-scoping to project directory; command blocklist (`curl`, `wget` blocked by default); isolated context windows for web fetch; Accept Edits mode for auto-approve of safe commands |
| Claude Code Sub-agents Docs (web, Anthropic) | Plugin agents restricted: cannot define `hooks`, `mcpServers`, or `permissionMode`; tool restriction via allowlist/denylist; MCP server scoping (parent never sees subagent tools); auto-compaction at ~95% |
| Kilo Marketplace (repo, Kilo-Org) | Federated plugin index as static YAML files; sparse checkout installer (`git init + git sparse-checkout + git fetch --depth 1`); patch-based local customization (`local.patch` surviving upstream syncs); zero operational overhead (flat files on GitHub); no versioning, no dependency management, no security model |
| Progent 2504.11703v3 (paper) | Monotonic privilege confinement via SMT-validated narrowing policy; middleware intercepting every tool call; ASR reduced from 39.9% to 1.0% on AgentDojo; ASR from 70.3% to 3.9% on ASB; works across GPT-4o, Claude-Sonnet-4, Gemini-2.5-Flash, Meta-SecAlign-70B |
| OpenHands (repo, All-Hands-AI) | Sandboxed agent execution with three isolation backends (Docker, Process, Remote); app server separated from agent server; MCP for tool execution across sandbox boundary; API key isolation via MCP proxy |
| Harness Engineering, Ch.5 (book) | Deferred capability loading as production infrastructure; 2KB tool description truncation; 10K token MCP output warning; 25K default max; 500K char per-tool ceiling; empirically tuned production thresholds |
| Harness Engineering, Ch.4 (book) | "Design permission before capability"; deny is sticky; three-valued permission model (allow/deny/ask); two dedicated Bash governance layers |
| Safety Survey 2605.23989v1 (paper) | "Mitigations across stages are complementary, not substitutable"; defense-in-depth required for agent systems; process metrics (CVR, DCR) complement outcome metrics |
| Agentic Reasoning 2502.04644v2 (paper) | 3 carefully chosen tools outperform 109 LangChain tools; "many capabilities already exist inside the reasoning model; external duplicates introduce noise and inappropriate tool selection" |
| Terminal-Bench 2.0 2601.11868v1 (paper) | Different agent scaffolding yields 17pp difference with same model (Gemini 2.5 Pro: 32.6% Terminus 2 vs. 15.7% OpenHands) — harness quality matters more than model capability |
| OpenClaw / ClawHub (repo, openclaw) | 700+ community skills on ClawHub marketplace; gateway + transport-agnostic agent loop; plugin-based extensibility with in-process and bundle-style plugins; descriptor-driven tool dispatch |
| MCP Spec (repo, modelcontextprotocol) | Transport-agnostic JSON-RPC 2.0 protocol; cacheable results with TTL+scope; extensions framework via SEP-2133; breaking draft removing sessions for stateless deployment |

## Proposed Design

### 1. Plugin Structure

Each plugin is a self-contained directory `lyra-plugin-<name>/` with:

- **`manifest.json`** — Metadata (name, version, semver dependencies), component declarations (tools, hooks, MCP servers, agents, skills), `userConfig` schema for typed configuration prompts
- **`__init__.py`** — Python entry point
- **`tools/`** — Tool definitions (one per file or subdirectory)
- **`agents/`** — Agent definitions with YAML frontmatter (model, effort, maxTurns, tools, isolation, memory). Per Claude Code security boundary: plugin agents must NOT define `hooks`, `mcpServers`, or `permissionMode` (Claude Code Sub-agents docs).
- **`skills/`** — SKILL.md with frontmatter (allowed-tools, disallowed-tools, model, effort, context: fork, agent type, paths). Skills are loaded lazily: description at session start, full body only on invoke (Claude Code Skills docs).
- **`hooks/`** — Event-driven lifecycle handlers via `hooks.json` (command, http, mcp_tool, prompt, agent types)
- **`.mcp.json`** — MCP server definitions (bundled with plugin, zero-config)

Manifest design rule (from Claude Code Plugins Reference): Unrecognized top-level fields are silently ignored. This allows a single `manifest.json` to double as an npm `package.json`, VS Code extension manifest, or MCP bundle manifest, enabling cross-ecosystem compatibility.

### 2. Discovery

Three scopes with defined precedence (Claude Code Plugins Reference):
- **Project-local** (`.lyra/plugins/`) — Shared via version control
- **User-global** (`~/.lyra/plugins/`) — Cross-project personal plugins
- **System** (`/usr/share/lyra/plugins/`) — Managed/deployment-wide

Within each scope, directories containing `manifest.json` are discovered. The `skills` directory adds to (does not replace) the default skill path. `agents`, `hooks`, and `.mcp.json` merge according to scope precedence: project-local overrides user-global overrides system.

A **plugin cache** at `~/.lyra/plugins/cache/` copies marketplace plugins for security (Claude Code pattern: copies, not in-place references). Orphaned versions cleaned after 7 days.

### 3. Lifecycle

**Install -> Validate -> Activate -> Deactivate -> Uninstall**

- **Install**: Copy/move plugin to discovery directory or cache. Resolve dependencies (explicit semver in manifest or implicit git SHA).
- **Validate**: Run `lyra plugin validate --strict` to catch misspelled fields or cross-ecosystem remnants (Claude Code Plugins Reference: `--strict` catches errors before publishing).
- **Activate**: Load manifest, register tools/hooks/MCP servers, inject `userConfig` values via `${user_config.KEY}` variable substitution into all component configurations (Claude Code Plugins Reference: the variable substitution mechanism means every component accesses configuration the same way).
- **Deactivate**: Unregister components, disconnect MCP servers, preserve persistent data directory (`~/.lyra/plugins/data/{id}/` survives updates).
- **Uninstall**: Remove plugin directory and cache copy.

**Hot-reload**: File change detection on plugin directories triggers re-activation. Critical for skills-directory plugins that should auto-load on the next session with zero install steps (Claude Code Plugins Reference).

**Persistent data pattern**: Also recommend the Claude Code pattern of using a `SessionStart` hook that diffs `requirements.txt`/`package.json` between plugin root and data dir to detect dependency changes and re-install.

### 4. Marketplace

**Registry model**: A community-curated index at `plugins.lyra.dev` — search, install, publish. Namespaced (`@user/plugin-name`). Two viable patterns:

**Option A: Static YAML Index (Kilo Marketplace pattern, lower effort)**
- Marketplace is a flat YAML file on GitHub (static, zero ops, committed to a registry repo)
- Clients fetch from `raw.githubusercontent.com` or release tarballs
- Sparse checkout installer: `git init; git sparse-checkout; git fetch --depth 1` — most portable, dependency-free install
- `local.patch` mechanism: diffs from upstream saved as patch files that survive `plugin update`
- **No versioning**: pinned to HEAD of upstream branch. No deprecation mechanism.

**Option B: Named Registry (ClawHub/OpenClaw pattern, higher effort)**
- Service with search, filtering, rating, analytics
- Version pinning, dependency resolution, deprecation
- Security audit pipeline for submissions
- 700+ skills ecosystem validates this model (OpenClaw / ClawHub)

**Recommendation**: Start with Option A (static YAML index) for v1. The entire Kilo Marketplace infrastructure is ~500 lines of TypeScript, 3 npm dependencies, zero runtime infrastructure. Option B can follow as a v2 enhancement when the ecosystem reaches critical mass.

### 5. Sandboxing

Plugins execute in a restricted environment. Two complementary layers (Claude Code Sandboxing + Security docs):

**Layer 1: Tool-level permissions** — Controls which tools the model can invoke and on what paths:
- Default-deny: all write/execute/network actions require approval
- Write-scoping: write restricted to project directory + plugin data directory by default
- Command blocklist: `curl`, `wget` blocked by default (Claude Code Security docs); Lyra adds `pip install --global`, `sudo`, `chmod -R` to the blocklist
- Three-valued permission model: allow / deny / ask (Harness Engineering, Ch.4; Progent 2504.11703v3)
- "Deny is sticky": once denied for a tool_use_id, permission cannot auto-escalate

**Layer 2: OS-level subprocess sandbox** — Controls what running processes can access:
- Bash subprocess isolation via Seatbelt (macOS) or bubblewrap (Linux)
- Filesystem: write only to CWD and plugin data dir; read to entire filesystem except denied paths (credential dirs like `~/.ssh/`, `~/.aws/`)
- Network: outbound proxy with domain allowlist. No domains pre-allowed. `allowManagedDomainsOnly` for hardened deployments.
- Escape hatch: `dangerouslyDisableSandbox` with user approval, disableable via managed settings

**Progent integration (Breakthrough tier)**: Insert an MCP middleware proxy that generates per-query JSON Schema restrictions and validates every tool call before execution. SMT-based monotonic narrowing ensures privilege can only shrink, never expand. Target: ASR < 1.0% on injection attacks, matching Progent's measured performance (2504.11703v3).

## Build Outline

1. Plugin loader + manifest parser with `userConfig` schema + `${user_config.*}` variable interpolation (week 1)
2. Lifecycle management: install/validate/activate/deactivate/uninstall with persistent data dir (week 1)
3. Hot-reload on file change detection (week 2)
4. Marketplace registry (Option A: static YAML index on GitHub) + CLI (`lyra plugin search/install/publish`) (weeks 3-4)
5. Plugin sandboxing: Layer 1 tool permissions + Layer 2 OS-level sandbox (weeks 4-5)
6. Progent-style privilege confinement middleware for injection defense (week 6, Breakthrough)
7. Tool Search integration: deferred capability loading with `auto:N` threshold (weeks 5-6)

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| plugins/manifest.py (359L) | EXTEND: lifecycle, discovery, marketplace (6x-7x) | Medium |
| router/context assembly | ADD: deferred capability loading (Tool Search) | Medium |
| execution sandbox | ADD: OS-level subprocess isolation | Medium |
| CLI | ADD: `lyra plugin` subcommands (search, install, publish, prune) | Medium |

**Impact:** 3 (parity) / 5 (breakthrough with Tool Search + Progent) | **Effort:** 3 | **Tier:** (A) Parity, (S) Breakthrough with sandbox + deferred loading

## Trade-Off Analysis

### Static YAML Index vs. Named Registry (Marketplace)

| Dimension | Static YAML (Option A) | Named Registry (Option B) |
|-----------|----------------------|--------------------------|
| Operational cost | Zero (flat files + GitHub CDN) | Server, DB, auth, API |
| Versioning | None (pinned to HEAD) | Semver pinning, lockfiles |
| Discovery | Client-side YAML parsing | Search, filter, rating, analytics |
| Security | No validation pipeline | Automated audit + manual review |
| Scalability | Unlimited (no server bottleneck) | Requires horizontal scaling |
| Breakage risk | Upstream breaking change breaks marketplace until next sync | Version pinning prevents unexpected breakage |
| Effort to build | ~500 lines codegen scripts | Full-stack web service |

**Verdict**: Option A for v1. The trade-off (no versioning, manual sync) is acceptable at small scale. Option B when 50+ community plugins exist.

### Full Schema Loading vs. Deferred (Tool Search)

| Dimension | Load All Upfront | Tool Search (Deferred) |
|-----------|-----------------|----------------------|
| Context cost (50 tools) | 10K-20K tokens every turn | ~2KB server instructions + one search round-trip per discovery |
| Latency | No extra round-trips | +1 round-trip on first tool discovery per turn |
| Small ecosystem (<10 tools) | Faster | Slower (unnecessary search overhead) |
| Large ecosystem (50+ tools) | Wastes context, degrades accuracy | Efficient (loads only used tools) |
| Accuracy degradation threshold | At >30-50 tools | No degradation (model never sees full list) |
| Model requirement | Any | Sonnet 4+ / Opus 4+ (Claude Code Tool Search docs) |

**Verdict**: Default to `auto:10` (activate when tool schemas exceed 10% of context window). Small plugin ecosystems load upfront; large ecosystems defer. This matches the Claude Code Tool Search Agent SDK recommended pattern.

### In-Process vs. Sandboxed Execution

| Dimension | In-Process | Sandboxed (Layer 2) |
|-----------|-----------|-------------------|
| Start latency | None | 2-15s per sandbox (OpenHands) |
| File system isolation | None (inherits host) | Write-scoped to CWD (Seatbelt/bubblewrap) |
| Network isolation | Full host network | Proxy-restricted domain allowlist |
| Startup overhead | Zero | Docker: 120s timeout default (OpenHands) |
| Dev iteration speed | Fast (no container) | Slower (container build/start) |
| Exploitation impact | Full host compromise | Sandbox-contained |

**Verdict**: Use process-mode sandbox (lighter than Docker) for development. Use Docker container sandbox for production/CI. Matches OpenHands' `SandboxService` pattern with configurable runtime via `LYRA_RUNTIME` env var.

### Permission Models

| Dimension | Prompt-based | Three-valued (Allow/Deny/Ask) | SMT-enforced (Progent) |
|-----------|-------------|------------------------------|----------------------|
| Overhead | Zero (prompt engineering) | Minimal (intercept + classify) | Per-call LLM + Z3 check |
| Robustness | ASR 25-73% under attack (Safety Survey) | Production-hardened | ASR < 1.1% (Progent, all models) |
| Complexity | Low | Medium | High (Z3 integration) |
| User friction | Constant prompting | Configurable per action | Minimal (auto-narrowing) |

**Verdict**: Start with three-valued (parity with Claude Code). Add Progent-style monotonic confinement as Breakthrough tier. The 39.9% -> 1.0% ASR reduction (Progent 2504.11703v3) justifies the investment for safety-critical deployments.

## Breakthrough Enhancements (Evidence-Gated)

The Parity baseline ports Claude Code's plugin system. The following enhancements are gated on specific evidence:

### Enhancement 1: Deferred Capability Loading (Tool Search)
- **Evidence**: 10K-20K tokens saved per turn with 50 tools; accuracy degrades at >30-50 tools; 3-5 tools loaded per search (Claude Code Tool Search Agent SDK docs)
- **Mechanism**: At session start, load only plugin names + 2KB capability summaries. On tool intent, semantic search fetches 3-5 most relevant schemas.
- **Implementation**: Add `ENABLE_TOOL_SEARCH` equivalent with modes: `on`, `off`, `auto:N` (default `auto:10`). Per-plugin `alwaysLoad: true` flag for critical tool sets.
- **Model requirement**: Requires Sonnet 4+ / Opus 4+ class model (Claude Code Agent SDK Tool Search docs)
- **Impact**: Enables 50+ plugin ecosystems without context degradation; 10K-20K token savings per turn

### Enhancement 2: Monotonic Privilege Confinement (Progent-style)
- **Evidence**: ASR from 39.9% to 1.0% on AgentDojo; ASR from 70.3% to 3.9% on ASB (Progent 2504.11703v3)
- **Mechanism**: MCP middleware proxy generates per-query JSON Schema restrictions; Z3 SMT solver validates policy updates as narrowing (auto-approve) vs. expansion (require approval)
- **Implementation**: Insert middleware in Lyra's tool execution pipeline. Policy generated from user task description; updated after each tool call result following the Claude Code "deny is sticky" principle.
- **Impact**: Formal safety guarantee against indirect prompt injection via tool results

### Enhancement 3: Federated Plugin Registry with Patch-Based Customization
- **Evidence**: Kilo Marketplace's 39 skills + 60+ MCP servers curated via ~500 lines of codegen scripts; 700+ community skills on ClawHub (Kilo Marketplace, OpenClaw)
- **Mechanism**: Plugin registry as static YAML index; sparse checkout installer; `local.patch` system for site-local fixes that survive upstream syncs
- **Implementation**: Codegen scripts in Lyra's marketplace repo; CI builds YAML index on each PR merge
- **Impact**: Zero operational cost for marketplace; community-contribution flywheel

### Enhancement 4: Unified Hook Architecture for Plugin Lifecycle
- **Evidence**: 17 lifecycle events, 5 hook types, four-state permission model (Claude Code Hooks docs)
- **Mechanism**: Replace ad-hoc interceptors with a unified Hook Registry where PreToolUse hooks handle routing + safety gating, PostToolUse hooks handle verification, and Stop hooks handle summary
- **Impact**: Reduces architectural surface area; each hook handler is a pure function (event JSON -> decision JSON)

### Enhancement 5: Plugin Token Cost Transparency
- **Evidence**: Claude Code `plugin details` shows always-on (~180 tok/session) and on-invoke (~2400 tok/skill) costs; 1% of context window for skill descriptions (Claude Code Plugins Reference + Skills docs)
- **Mechanism**: `lyra plugin details` outputs projected token cost per component. After compaction: 5K tokens per skill, 25K combined budget (Claude Code Skills docs).
- **Impact**: Users can evaluate plugin cost before installation; prevents context budget surprise

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity, security) with cited evidence. The Breakthrough Enhancements above (Tool Search, Progent, federated registry) each cite specific papers or docs with benchmark numbers. Tool Search and sandboxing are production-deployed (Technique 5 and Technique 2 in the Harnessing Engineering synthesis). Progent is lab-validated with strong evidence (ASR 1.0%). All three are recommended for Breakthrough tier.

**New challenge from synthesis findings:** "Tool Search requires Sonnet 4+ / Opus 4+ — what is Lyra's fallback for Haiku-class models?" Resolution: `ENABLE_TOOL_SEARCH` defaults to `off` when model class < Sonnet 4. The `auto:N` mode checks model capability and falls through to upfront loading when search is not supported. This matches the Claude Code Agent SDK behavior.

**Sign-off:** Plan is feasible. Parity implementation is well-documented in Claude Code Plugins Reference, MCP docs, and Skills docs. Breakthrough tier gated on evidence from the findings batch (Progent ASR numbers, Tool Search benchmark thresholds, Kilo Marketplace codebase size).

## Evidence Base

The following sources were consulted and cited in this plan:

| # | Source | Type | Citation ID |
|---|--------|------|-------------|
| 1 | Claude Code Plugins Reference (code.claude.com) | Web doc | Claude Code Plugins Reference |
| 2 | Claude Code MCP Docs (code.claude.com) | Web doc | Claude Code MCP Docs |
| 3 | Claude Code Agent SDK Tool Search (code.claude.com) | Web doc | Claude Code Tool Search Agent SDK |
| 4 | Claude Code Skills Docs (code.claude.com) | Web doc | Claude Code Skills Docs |
| 5 | Claude Code Hooks Docs (code.claude.com) | Web doc | Claude Code Hooks Docs |
| 6 | Claude Code Sandboxing Docs (code.claude.com) | Web doc | Claude Code Sandboxing Docs |
| 7 | Claude Code Security Docs (code.claude.com) | Web doc | Claude Code Security Docs |
| 8 | Claude Code Sub-agents Docs (code.claude.com) | Web doc | Claude Code Sub-agents Docs |
| 9 | Kilo-Org/kilo-marketplace (GitHub) | Repo | Kilo Marketplace |
| 10 | sunblaze-ucb/progent (GitHub) / 2504.11703v3 | Paper + repo | Progent 2504.11703v3 |
| 11 | All-Hands-AI/OpenHands (GitHub) | Repo | OpenHands |
| 12 | openclaw/openclaw (GitHub) | Repo | OpenClaw |
| 13 | modelcontextprotocol/modelcontextprotocol (GitHub) | Repo | MCP Spec |
| 14 | Safety Survey 2605.23989v1 | Paper | Safety Survey 2605.23989v1 |
| 15 | Agentic Reasoning 2502.04644v2 | Paper | Agentic Reasoning 2502.04644v2 |
| 16 | Terminal-Bench 2.0 2601.11868v1 | Paper | Terminal-Bench 2.0 2601.11868v1 |
| 17 | Harness Engineering: Claude Code, Ch.4-5 (book, chapters) | Book | Harness Engineering |
| 18 | Lyra's plugins/manifest.py (359L) | Code | Lyra's manifest.py |

## Changelog

- Run 4 (2026-06-07): Deep-read enhancement — added Tool Search pattern with 10K-20K token benchmarks, Progent monotonic privilege confinement (ASR 1.0%), federated YAML registry pattern, trade-off analysis (3 dimensions), unified hook architecture, plugin token cost transparency, Evidence Base section. All techniques cite specific sources. 18 sources total from 3 document types.
- Run 3 (2026-06-03): Added Expert Review section, Changelog
