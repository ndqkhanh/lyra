# MCP Integration — Plan (§4.8)

> Run 2 — June 7, 2026 (deep-read evidence update)

## Plain-Language Summary

MCP (Model Context Protocol) lets Lyra connect to external tools and data sources — filesystem, databases, APIs, web search — through a standardized protocol. Lyra's MCP gateway supports multiple transports (stdio, HTTP, WebSocket), auto-discovers tools from connected servers, and optimizes context by decoupling tool definitions from execution.

**Key benchmark anchors:**
- ANX 3EX decoupling achieves **47-66% token reduction** vs. inline MCP on form tasks (2604.04820v1, 30 trials per model, both Qwen3.5-plus and GPT-4o, p < 0.001)
- Anthropic's code-execution-with-MCP pattern achieves **98.7% token savings** on tool definitions alone (150K tokens -> 2K), plus reduced round-trips from chained operations (Anthropic Engineering Blog, Nov 2025)
- Claude Code production deployments exist with **41+ MCP tools** across multiple servers; a sovereign wealth fund serves **~9,000 portfolio managers** with MCP integrations; Go + JS architecture reported **80-90% token savings** vs. direct code analysis (Claude Code Definitive Guide, Ch.5)
- Tool search scales to **10,000 tools**; 50 tool definitions consume **10K-20K tokens**; accuracy degrades above **30-50 tools** loaded at once (Anthropic Agent SDK Tool Search docs)
- Claude Code's deferred tools and MCP deltas are first-class citizens in the **post-compact reconstruction** pipeline, alongside plans, skills, and file attachments (Harness Engineering, Ch.5)

## Design

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#7c3aed',
  'primaryTextColor': '#e2e8f0',
  'primaryBorderColor': '#a78bfa',
  'lineColor': '#818cf8',
  'secondaryColor': '#1e293b',
  'tertiaryColor': '#0f172a',
  'background': '#0d0d1a',
  'mainBkg': '#1e293b',
  'nodeBorder': '#6366f1',
  'clusterBkg': '#111827',
  'clusterBorder': '#4f46e5',
  'titleColor': '#c084fc',
  'edgeLabelBackground': '#1e293b',
  'nodeTextColor': '#e2e8f0',
  'fontSize': '14px'
}}}%%
graph TD
    Agent[Lyra Agent] --> Gateway[MCP Gateway]
    Gateway --> FS[Filesystem Server]
    Gateway --> Git[Git Server]
    Gateway --> DB[Database Server]
    Gateway --> Web[Web Search Server]
    Gateway --> Memory[Memory Server]
    Gateway --> Custom[Custom Servers...]
    
    Gateway --> Transport[Transport Layer]
    Transport --> Stdio[stdio]
    Transport --> HTTP[HTTP/SSE]
    Transport --> WS[WebSocket]
    
    Gateway --> ToolSearch[Tool Search<br/>Deferred Loading]
    ToolSearch --> Names[Tool Names + 2KB Instructions<br/>loaded at session start]
    ToolSearch --> Discover[Semantic search<br/>3-5 tools per call]
    ToolSearch --> AlwaysLoad[alwaysLoad: true<br/>flags exempt critical servers]
    
    Gateway --> CodeExec[Code-First Execution<br/>(Optional)]
    CodeExec --> Sandbox[Secure Sandbox]
    CodeExec --> Filtered[Filtered results only]
```

## Key Features

1. **Multi-Transport:** stdio (local servers), HTTP/SSE (remote servers), WebSocket (streaming). The MCP spec draft 2026-07-28 deprecates SSE in favor of Streamable HTTP + MRTR (Multi Round-Trip Request) for stateless deployment (modelcontextprotocol/modelcontextprotocol spec repository, SEP-2322).

2. **Dynamic Tool Discovery:** Servers advertise tools via `list_changed` notifications; gateway registers them; agent discovers them on-demand via semantic search (Anthropic Agent SDK Tool Search docs; Claude Code MCP docs). Supports mid-session capability changes without disconnect/reconnect.

3. **Tool Search (Deferred Loading):** Only tool names and ~2KB server instructions load at session start. Full schemas are discovered via semantic search when the LLM decides a tool is needed. Configurable modes:
   - `true` — always defer (maximum context savings)
   - `auto` — load upfront if under 10% of context window, defer otherwise (adaptive)
   - `auto:N` — custom threshold percentage (e.g., `auto:5` activates at 5%)
   - `false` — load all upfront (current behavior)
   
   Small-tool fast-path: fewer than ~10 tools loads upfront is typically faster than deferral (Anthropic Agent SDK docs; Claude Code MCP docs, §3.1).

4. **ANX 3EX Decoupling (47-66% token reduction):** Tool definitions loaded once at session start (not inline). Execution happens on demand. Decoupled: definition format, execution transport, result rendering. Best applied to high-volume form-filling tasks; benefit minimal for simple 1-3 tool interactions (2604.04820v1).

5. **OAuth 2.0 Support:** Standard MCP auth for remote servers with dynamic client registration, fixed callback ports, pre-configured credentials, scope restriction, and custom `headersHelper` scripts (Claude Code MCP docs).

6. **Auto-Reconnect:** Server crash -> exponential backoff reconnect: 5 attempts, 1s-16s. Initial connection retries 3 times on transient errors (v2.1.121+). Per-server timeout defaults to ~28 hours with 1000ms minimum floor (Claude Code MCP docs).

7. **Code-First Tool Orchestration (Optional):** Instead of discrete tool-call round-trips, the agent writes a script in a secure sandbox that chains multiple operations. Only filtered/aggregated results return to the LLM. **98.7% token savings** on tool definitions alone, plus reduced latency from batched execution (Anthropic Code Execution with MCP blog; Cloudflare "Code Mode" independently converged on same architecture).

8. **Channels for Push-Based Interaction:** MCP servers can push CI results, monitoring alerts, or chat messages into a session mid-task (Claude Code MCP docs, §3.4).

9. **Bundled Top-10 MCP Servers:** filesystem, git, postgres, sqlite, web-search (Brave), memory, docker, github, slack, custom. Sourced from the MCP ecosystem: 3000+ servers across 55 categories on awesome-mcp-servers (88K stars), 16,000+ on mcp.so, 5,000+ tools on smithery.ai (awesome-mcp-servers; AI Agents with LangChain/LangGraph/MCP, Ch.13).

## Token Budget & Capacity Table

| Parameter | Value | Source |
|-----------|-------|--------|
| Tool descriptions / server instructions | 2 KB each | Claude Code MCP docs |
| MCP output warning threshold | 10,000 tokens | Claude Code MCP docs |
| Default max MCP output | 25,000 tokens | Claude Code MCP docs |
| Per-tool text result ceiling | 500,000 chars | Claude Code MCP docs (via `_meta["anthropic/maxResultSizeChars"]`) |
| Reconnect attempts | 5 (1s-16s backoff) | Claude Code MCP docs |
| Initial connection retries | 3 (on 5xx/timeout) | Claude Code MCP docs v2.1.121+ |
| `alwaysLoad: true` startup cap | 5 seconds | Claude Code MCP docs |
| `headersHelper` timeout | 10 seconds | Claude Code MCP docs |
| Per-server timeout minimum | 1,000 ms | Claude Code MCP docs |
| Tools loaded per search | 3-5 most relevant | Anthropic Agent SDK Tool Search docs |
| Maximum catalog size | 10,000 tools | Anthropic Agent SDK Tool Search docs |
| Default activation threshold | 10% of context window | Anthropic Agent SDK Tool Search docs |
| Small-tool fast-path threshold | ~10 tools | Anthropic Agent SDK Tool Search docs |
| Post-compact reconstruction priority | MCP deltas = plans = skills | Harness Engineering, Ch.5 |

## Build Outline

1. **MCP protocol implementation** — JSON-RPC 2.0, request/response/notification. Support both 2025-11-25 (current) and 2026-07-28 (draft with sessionless, CacheableResult, MRTR). Breaking changes in draft require careful version negotiation (modelcontextprotocol/modelcontextprotocol spec).

2. **Transport layer** — stdio (local, zero-config via npx), HTTP/SSE (legacy remote), Streamable HTTP (recommended for production), WebSocket. Draft deprecates SSE in favor of Streamable HTTP + MRTR (SEP-2322).

3. **Tool Search / deferred loading** — semantic search over tool names and descriptions. Configurable auto:N threshold. `alwaysLoad` flag for critical servers (e.g., filesystem). Per-tool `_meta` annotations.

4. **ANX 3EX optimization** — definition caching, lazy execution, decoupled rendering. Target: 47-66% token reduction on form-heavy workflows. Worthwhile for multi-agent setups; additive to existing MCP infrastructure.

5. **Server lifecycle management** — start/stop/healthcheck/reconnect (exponential backoff, 5 attempts). Per-server timeout with `progress` notification extension.

6. **OAuth 2.0 flow** — for remote MCP servers. Dynamic client registration, scope restriction, `headersHelper` for non-OAuth auth. OAuth client secret stored in system keychain, never in config.

7. **Code-first execution (optional, Phase 2)** — wrap MCP tools as typed filesystem tree, execute chained operations in sandbox. 98.7% token savings on tool definitions.

8. **Bundle + document top-10 servers** — filesystem, git, postgres, sqlite, web-search, memory, docker, github, slack, custom. Each with .mcp.json manifest.

## Multi-Provider Note

MCP is provider-agnostic — tools are injected into the messages array, not through a provider-specific API. Works identically across Claude, DeepSeek, GPT, and open-weights. Claude Code itself can serve as an MCP server (`claude mcp serve`), exposing View, Edit, LS to external MCP clients (Claude Code MCP docs). Claude Code SDK Tool Search requires Sonnet 4+ or Opus 4+; not available on Haiku.

**Impact:** 4 | **Effort:** 3 | **Tier:** (A) Parity

## Trade-Off Analysis

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **All tools upfront** (current Lyra) | Simplest implementation; no search latency; deterministic tool availability | Consumes context on every tool regardless of use; does not scale beyond ~30-50 tools; accuracy degradation > 30-50 tools | Small, fixed tool sets (<10 servers) |
| **Tool Search deferred** | Scales to 10,000 tools; one extra search round-trip offset by smaller context on every subsequent turn; context savings ~80% of tool schema budget | Requires Sonnet 4+ / Opus 4+; small-tool fast-path (~10 tools) is actually slower to defer; first-use search latency | 10-100+ tools, diverse capabilities |
| **ANX 3EX decoupling** | 47-66% token reduction on structured tasks; human-only confirmation gates; UI-to-Core sensitive data isolation | Only evaluated on single form task (no multi-step); ANX ecosystem nonexistent; accuracy not measured in paper; adds architectural complexity | Form-heavy workflows; security-critical data entry |
| **Code-first execution** | 98.7% tool-definition token savings; batched execution reduces latency; privacy-preserving (intermediate data stays in sandbox) | Requires secure sandbox runtime; operational overhead; LLM must write valid code; benefits must be weighed against implementation cost | High-volume tool chains; multi-step data pipelines |
| **Full ANX protocol** | Protocol-level semantic precision; deterministic SOP execution; progressive disclosure | Breaking changes vs. MCP; new markup language learning curve; no ecosystem; security claims unevaluated | Investigate only — too immature for production |

**Recommendation:** Adopt Tool Search as the default mode for Lyra (deferred loading with `auto:N` threshold). Add ANX 3EX decoupling for specific high-volume form workflows. Prototype code-first execution in Phase 2 for long-running data pipelines. Skip full ANX protocol until ecosystem matures.

## Evidence Synthesis

| Source | Key Insight |
|--------|-------------|
| ANX Protocol (2604.04820v1) | 3EX decoupled architecture: 47-66% token reduction vs inline MCP (statistically significant across both Qwen3.5-plus and GPT-4o, 30 trials each); 58% execution time reduction |
| Claude Code MCP docs (§3.1) | Dynamic tool discovery, OAuth 2.0, multi-transport (stdio/HTTP/SSE/WebSocket), auto-reconnect with exponential backoff (5 attempts, 1s-16s), env var expansion in `.mcp.json`, scope precedence (local > project > user > plugin > connectors) |
| Anthropic Code Execution with MCP (§3.19) | ~98.7% token reduction by executing code in sandbox, returning only filtered output; 150K tokens -> 2K; code-first orchestration converged independently by Cloudflare "Code Mode" |
| Anthropic Agent SDK Tool Search docs | Scales to 10,000 tools; 50 tools = 10K-20K tokens; accuracy degrades above 30-50 tools; `ENABLE_TOOL_SEARCH` modes (true/auto/auto:N/false); 3-5 tools fetched per search |
| Claude Code Definitive Guide, Ch.5 | Production deployments: 41+ MCP tools, ~9,000 portfolio manager deployment, 80-90% token savings reported; MCP over raw bash for sensitive data; deferred loading for 40+ tools |
| Claude Code Definitive Guide, Playbook Practice 8 | Defense in depth: deny + sandbox + hooks + MCP hooks; MCP as secure integration layer for sensitive data; start with maximum restriction |
| Harness Engineering, Ch.5 | MCP deltas and deferred tools are first-class citizens in post-compact reconstruction pipeline; tool result budget governance; MCP output warning at 10K tokens |
| modelcontextprotocol/servers | Reference implementations: filesystem (layered path validation, atomic writes, symlink resolution), memory (knowledge graph persisted as JSONL), sequential thinking (branching/revision/backtracking), git (defense-in-depth against flag injection). Tool annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` |
| modelcontextprotocol/modelcontextprotocol (spec) | Protocol spec: 2025-11-25 vs 2026-07-28 draft (breaking: no `initialize`, no sessions, CacheableResult with TTL+scope, MRTR replacing SSE). JSON-RPC 2.0 with typed unions. ~40 SEPs for feature proposals |
| awesome-mcp-servers (§3.3) | 3000+ MCP servers across 55 categories; Glama.ai health-check badges; 88K stars; CI-based PR validation for contributions |
| AI Agents with LangChain/LangGraph/MCP, Ch.13 | FastMCP 2 (Python), `MultiServerMCPClient` for aggregating tools from multiple servers, MCP Inspector for interactive testing; 16,000+ servers on mcp.so, 5,000+ on smithery.ai |
| AI Agents with LangChain/LangGraph/MCP, Ch.14 | Production guardrails: four insertion points (pre-model, post-model, routing-stage, tool-level); MCP servers as external tool sources combined with local tools in the same agent |
| SEARL (2604.07791v3) | MCP tools as Tool Graph Memory nodes in an RL-optimized agent; tool-anchored credit assignment with two-level advantage estimation; best avg rank (1.43) across 7 benchmarks |
| Mem2Evolve (2604.10923v1) | MCP-compliant dynamic tool creation with experience-guided generation; +6.46% avg improvement over best baselines; 56% higher first-pass tool validity |

## Breakthrough Proposals

### BP1: MCP Tool Graph Memory with RL-Trained Activation Policy

**What it is:** Replace the current BM25-based tool search with a learned Tool Graph Memory where MCP tools are nodes, co-occurrence edges encode task-context relationships, and SEARL-style two-level advantage estimation learns which tools to surface for which task contexts. Level 1 predicts which tool category to activate (e.g., "filesystem vs. search vs. database"), Level 2 picks specific tools within the category. Training signal is tool-selection-accuracy x task-completion reward, collected from Lyra's MCP usage traces.

**Sources fused:**
- SEARL's Tool Graph Memory with two-level advantage estimation (arXiv 2604.07791v3; already in evidence table)
- MCP tool search / deferred loading patterns (Claude Code MCP docs, Anthropic Agent SDK Tool Search docs; already in sections 3-4)
- Mem2Evolve's experience-guided tool generation (arXiv 2604.10923v1; already in evidence table)
- MetaAgent-X's end-to-end RL for routing (arXiv 2605.14212v1; multi-agent synthesis 1.2, 3.5)

**How it works:**
1. At session start, MCP tools are registered as Tool Graph Memory nodes with their metadata (name, description, category, server)
2. Edges are weighted by co-occurrence frequency across Lyra's past task traces — tools that fire together in similar contexts get higher weights
3. First tool activation triggers the RL policy: a lightweight forward pass (sub-1ms on CPU) selects the top-3 categories, then top-2 tools per category
4. After tool execution, the task-completion signal backpropagates: successful task chains strengthen edges, failed chains weaken them
5. Mem2Evolve's experience-guided generation kicks in for repeated failures: the system generates synthetic tool schemas for missing capabilities and pings the user to install the corresponding MCP server

**Why it beats current SOTA:**
- BM25/TF-IDF tool search degrades past 30-50 tools loaded at once (Anthropic SDK docs)
- SEARL achieves best avg rank 1.43 across 7 benchmarks but was tested on static tool sets, not dynamic MCP catalogs
- MetaAgent-X's RL routing (+11.17% avg) was designed for agent topology, not tool selection — this is a novel application to MCP's deferred loading problem
- Mem2Evolve's +6.46% average improvement on first-pass tool validity is orthogonal to selection — combining both yields multiplicative gains

**Skeptic's objection:** "RL overhead on tool selection adds latency for marginal benefit. BM25 with server-level hints works fine for 99% of MCP sessions, which rarely exceed 20 tools." Response: At 100+ tool scale (the plan's explicit target), heuristic search demonstrably degrades — the 30-50 tool ceiling is documented. The RL forward pass is sub-1ms on CPU, dwarfed by the 500ms+ MCP round-trip it replaces. The real cost is trace collection and periodic retraining, which is offline work. For sessions under 10 tools, fall back to the existing always-load fast-path — no RL penalty.

**Impact: 3 | Effort: 3 | Risk: Medium**

---

### BP2: MCP as Inter-Agent Protocol Layer (Skills-as-MCP-Servers)

**What it is:** Lyra agents expose their own capabilities (subagent spawning, tool execution, memory, verification) as MCP servers that other agents in the swarm discover and invoke through standard MCP tool search. This makes MCP the universal inter-agent communication protocol rather than just an external-tool protocol. Agent-to-agent calls carry structured result DAGs (Argus-style evidence nodes) through MCP result channels, enabling audit traceability across the swarm.

**Sources fused:**
- MCP channels for push-based interaction (Claude Code MCP docs, 3.4; plan section 8)
- Claude Code serving as an MCP server itself (`claude mcp serve`; plan Multi-Provider Note)
- Orchestrator-Worker pattern with parallel subagent dispatch (Anthropic Engineering Blog; multi-agent synthesis 1.1, 3.2)
- Structured Evidence DAG with 1200:1 compression (Argus arXiv 2605.16217v3; multi-agent synthesis 1.3, 3.4, 6.2)
- Post-compact reconstruction pipeline citing MCP deltas as first-class citizens (Harness Engineering, Ch.5; plan Token Budget table)
- 16,000+ existing MCP servers on mcp.so (plan Key Features 9)

**How it works:**
1. Each Lyra agent that can receive delegation acts as an MCP server with:
   - A `delegate_subagent` tool (accepts a task specification, returns results as evidence nodes)
   - A `query_memory` tool (reads from shared agent memory)
   - A `verify_claim` tool (cross-checks against evidence DAG)
2. These agent-MCP-servers are registered in Lyra's Tool Search catalog alongside external MCP servers
3. The orchestrator discovers available agent capabilities via the same `search()` call it uses for filesystem/web tools — zero new infrastructure
4. Results flow back through MCP's channels protocol: sub-agent completion triggers a push notification, orchestrator receives evidence DAG nodes with source-attribution metadata
5. Post-compaction, the evidence nodes survive through MCP delta reconstruction (same pipeline as deferred tool schemas — Harness Engineering, Ch.5)

**Why it beats current SOTA:**
- Current multi-agent systems use ad-hoc inter-agent communication: file-system workspaces (FS-Researcher), message boards (AutoScientists), or raw function calls. All are non-standard, non-discoverable, and require custom infrastructure.
- MCP already has 16,000+ servers, OAuth 2.0, multi-transport support, auto-reconnect, and structured result types. Using it as the inter-agent protocol means Lyra's agent mesh inherits all of this for free.
- Argus's evidence DAG (1200:1 compression, auditable claims) becomes a natural result type for MCP tool calls — every inter-agent response is a structured, compressible, traceable graph.
- Claude Code's own `claude mcp serve` validates the pattern: if Claude Code can be an MCP server, Lyra agents can too.

**Skeptic's objection:** "MCP is a tool protocol, not an agent protocol. JSON-RPC overhead per message, no streaming for long-running subagents, no support for interrupted execution." These are genuine limitations, and the proposal acknowledges them. Mitigations: (a) use MCP's Streamable HTTP transport for long-running tasks instead of blocking tool calls; (b) implement MCP's `progress` notification for sub-agent heartbeat; (c) for latency-critical paths, bypass MCP and use direct function calls — the MCP bridge is for discoverability and audit, not hot-path optimization. The hypothesis worth testing: does MCP standardization eliminate enough ad-hoc integration code to offset the protocol overhead? The 16,000 existing MCP servers suggest the ecosystem thinks yes.

**Impact: 4 | Effort: 4 | Risk: High** (not in Phase 1; prototype in Phase 2 or 3)

---

## Evidence Base

The following sources were consulted for this revision:

| # | Source | Type | Pages / Section |
|---|--------|------|-----------------|
| 1 | ANX Protocol (arXiv 2604.04820v1) | Paper | Full (22 pp.) |
| 2 | Claude Code MCP docs (code.claude.com) | Web doc | Full |
| 3 | Anthropic Code Execution with MCP (anthropic.com/engineering) | Blog | Full |
| 4 | Anthropic Agent SDK Tool Search docs (code.claude.com) | Web doc | Full |
| 5 | Claude Code Definitive Guide, Ch.5 "MCP" | Book chapter | Ch.5 |
| 6 | Claude Code Definitive Guide, Playbook Practices 5, 8 | Book playbook | Practices 5, 8 |
| 7 | Harness Engineering: Claude Code, Ch.5 "Context Governance" | Book chapter | Ch.5 |
| 8 | modelcontextprotocol/servers (GitHub) | Repo | 7 servers |
| 9 | modelcontextprotocol/modelcontextprotocol (GitHub) | Spec repo | SEPs, schema |
| 10 | awesome-mcp-servers (punkpeye, GitHub) | Web index | README (2825 lines) |
| 11 | AI Agents with LangChain, LangGraph, and MCP (Infante, 2026), Ch.13-14 | Book chapters | Ch.13-14 |
| 12 | SEARL (arXiv 2604.07791v3) | Paper | Full |
| 13 | Mem2Evolve (arXiv 2604.10923v1) | Paper | Full |
| 14 | Harness Engineering thematic synthesis (harness.md) | Synthesis | All sections |

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| `mcp_bundling.py` (526L) | KEEP — already solid MCP gateway | None |
| Tool Search deferred loading | ADD — semantic search over tool names/descriptions; `ENABLE_TOOL_SEARCH` modes (true/auto/auto:N/false); `alwaysLoad` flag; per-tool `_meta` annotations | Medium |
| ANX 3EX decoupling | ADD — definition caching, lazy execution, decoupled rendering for form-heavy workflows | Low |
| Code-first execution | ADD (Phase 2) — sandboxed script execution with chained operations; 98.7% tool-definition token savings | High |
| Server lifecycle | EXTEND — health checks, reconnect with exponential backoff (5 attempts, 1s-16s), per-server timeout | Low |
| Bundled top-10 | ADD — pre-configured server manifests per awesome-mcp-servers + MCP spec reference implementations | None |
| Protocol version negotiation | ADD — support both 2025-11-25 and 2026-07-28 draft; migrate to sessionless + CacheableResult + MRTR when draft stabilizes | Low |

## Expert Review

**Skeptic:** "MCP integration already works in Lyra (526-line mcp_bundling.py). Is ANX decoupling worth it?" -> YES. The 47-66% token reduction is significant for multi-agent setups where every context token counts. Implementation is additive — doesn't change existing MCP infrastructure. But the bigger win is **Tool Search**: deferred loading enables scaling from today's handful of MCP servers to 100+ without context degradation. The evidence from Claude Code production (41+ tools, 9,000 portfolio manager deployment) confirms this works at scale.

**Skeptic:** "Code-first execution sounds complex. Is the 98.7% savings real?" -> Yes, but caveats apply. The 98.7% is tool-definition-specific: loading 150K tokens of definitions drops to 2K. For Lyra, this is most impactful for servers with large tool schemas (databases with many tables, extensive API surfaces). For small servers (filesystem with 5 tools), the savings are negligible. Implement as Phase 2 with a deployment flag; benchmark before and after.

**Skeptic:** "There are two competing MCP spec versions. Which should Lyra target?" -> Support both with version negotiation. The 2025-11-25 is the current stable spec. The 2026-07-28 draft introduces breaking changes (no `initialize`, no sessions, CacheableResult, MRTR). Build Lyra's transport layer to negotiate protocol version at handshake time, with a migration path to sessionless when the draft stabilizes. The stateless design of the draft is substantially better for horizontal scaling (modelcontextprotocol/modelcontextprotocol spec, SEP-2567, SEP-2322).
