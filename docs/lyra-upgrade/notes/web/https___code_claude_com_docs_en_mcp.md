# Connect Claude Code to Tools via MCP (Claude Code Docs / Anthropic)

## Key Technical Claims

1.  **MCP is an open-source standard** for AI-tool integrations connecting Claude Code to hundreds of external tools and data sources across four transport modes: HTTP (recommended), SSE (deprecated), stdio (local processes), and WebSocket (persistent bidirectional).
2.  **Tool Search defers tool definitions** to keep context usage low -- only tool names and server instructions load at session start; full schemas are discovered on-demand via a semantic search tool.
3.  **Three configuration scopes** for MCP servers: local (per-project, private in `~/.claude.json`), project (shared via `.mcp.json` in version control), user (cross-project in `~/.claude.json`).
4.  **Channels enable push-based interaction**: MCP servers can push CI results, monitoring alerts, or chat messages into a session so Claude reacts unprompted.
5.  **Plugin MCP servers bundle automatically** with plugins -- tools and servers are distributed together with no manual configuration needed.
6.  **Dynamic tool updates** via `list_changed` notifications allow servers to update capabilities mid-session without disconnect/reconnect.
7.  **Automatic reconnection** with exponential backoff (5 attempts, 1s initial delay doubling each time) for HTTP/SSE servers; initial connection retries 3 times on transient errors (v2.1.121+).
8.  **Claude Code can itself serve as an MCP server** (`claude mcp serve`), exposing its built-in tools (View, Edit, LS) to external MCP clients.
9.  **Managed MCP configuration** for enterprises: centralized control with `managed-mcp.json`, `allowedMcpServers`, `deniedMcpServers`.
10. **Elicitation support**: MCP servers can request structured input mid-task via form mode or URL mode dialogs.
11. **OAuth 2.0 authentication** with support for dynamic client registration, fixed callback ports, pre-configured credentials, scope restriction, and custom `headersHelper` scripts for non-OAuth auth (Kerberos, short-lived tokens, SSO).
12. **MCP Resources referenced via `@` mentions** (e.g., `@github:issue://123`) with fuzzy-searchable autocomplete.
13. **MCP Prompts become slash commands** (`/mcp__servername__promptname`) with argument parsing.

## Architecture/Mechanism Details

- **Tool Search (default enabled)**: At session start, only tool names and server instructions load into context. When Claude needs a tool, it uses a `ToolSearch` call to discover relevant tool definitions. Only tools Claude actually uses enter context.
- **`ENABLE_TOOL_SEARCH`** modes: unset (default deferral), `true` (force deferral), `auto` (threshold mode -- load upfront if under 10% of context window, defer otherwise), `auto:N` (custom threshold %), `false` (load all upfront).
- **Model requirements**: Tool search requires Sonnet 4+ or Opus 4+ -- Haiku models do not support `tool_reference` blocks. On Vertex AI, supported from Claude Sonnet 4.5 and Claude Opus 4.5 onward.
- **`alwaysLoad: true`**: Per-server flag to exempt critical servers from deferral -- every tool from that server loads upfront regardless of `ENABLE_TOOL_SEARCH` setting. Also blocks startup until the server connects (5-second cap).
- **Per-tool `_meta` annotations**: `"anthropic/maxResultSizeChars"` up to 500,000 chars raises a tool's output threshold. `"anthropic/alwaysLoad": true` marks individual tools as always-loaded.
- **Automatic reconnection**: HTTP/SSE disconnect triggers up to 5 retries (1s, 2s, 4s, 8s, 16s). Initial connection retries 3 times on transient errors (5xx, connection refused, timeout). Auth errors are not retried.
- **Per-server timeout**: Hard wall-clock limit per tool call. Below 1000ms falls through to `MCP_TOOL_TIMEOUT` (default ~28 hours). Progress notifications do not extend it.
- **Headers helper**: `headersHelper` command runs fresh on each connection (session start and reconnect), outputs a JSON object of string headers. Has a 10-second shell timeout. Environment variables `CLAUDE_CODE_MCP_SERVER_NAME` and `CLAUDE_CODE_MCP_SERVER_URL` are set for the helper script.
- **OAuth scope restriction**: `oauth.scopes` pins authorization scopes (space-separated string). Takes precedence over server-discovered scopes. `offline_access` is appended automatically when the auth server supports it.
- **Environment variable expansion** in `.mcp.json`: `${VAR}` and `${VAR:-default}` syntax supported in `command`, `args`, `env`, `url`, and `headers` fields.
- **Scope precedence**: local > project > user > plugin-provided > claude.ai connectors. Plugins and connectors deduplicate by endpoint URL.
- **Claude.ai server integration**: MCP servers configured in claude.ai automatically appear in Claude Code when authenticated via claude.ai subscription. Disabled when `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `apiKeyHelper`, or third-party provider is active.

## Numbers & Benchmarks

- **Tool descriptions / server instructions**: truncated at **2 KB** each.
- **MCP output warning threshold**: **10,000 tokens**.
- **Default max MCP output**: **25,000 tokens** (configurable via `MAX_MCP_OUTPUT_TOKENS`).
- **Per-tool text result ceiling**: **500,000 characters** via `_meta["anthropic/maxResultSizeChars"]`.
- **Per-server timeout minimum**: **1,000 ms** (below falls through to `MCP_TOOL_TIMEOUT` default of ~28 hours).
- **HTTP/SSE first-byte minimum**: **60 seconds**.
- **Reconnection backoff**: **5 attempts**, starting at **1 second**, **doubling** each time.
- **Initial connection retries** (v2.1.121+): **3 attempts** on transient errors.
- **`headersHelper` timeout**: **10 seconds**.
- **`alwaysLoad: true` startup cap**: **5 seconds**.
- **OAuth client secret**: stored in system keychain (macOS) or credentials file, never in config.

## Transfer to Lyra (One Idea + SS4.x Route)

**Idea**: **Deferred Capability Loading (Tool Search Pattern)**

Lyra's plugin/tool subsystem can adopt the **Tool Search** pattern: instead of loading all plugin tool schemas at session start (which consumes precious context window), load only capability names and short descriptions. When the LLM's intent router decides a tool is needed, trigger a semantic search to fetch the full schema on-demand.

**SS4.x Route**: Maps directly to **SS4.3 Tool/Plugin Subsystem -- Dynamic Plugin/Tool Discovery**. Specifically:

1.  **Implement a `ENABLE_TOOL_SEARCH` equivalent** for Lyra's plugin router with modes: `on` (defer all tool schemas), `auto:15` (load upfront if schemas fit within 15% of context window), `off` (current behavior -- load all upfront).
2.  **Add `alwaysLoad` per-plugin flags** -- small, frequently-needed tool sets (e.g., file system, terminal) load upfront; large, rarely-used sets (e.g., advanced data analysis) defer.
3.  **Adopt server instructions / tool descriptions** -- each plugin provides a 2KB-or-less capability summary that the router uses to decide when to search for it. Critical details go at the start of the description.
4.  **Use the threshold mode (`auto:N`)** as Lyra's default: tools that fit within a user-configurable percentage of context load upfront, and the overflow defers. This gives adaptive behavior -- users with large context windows get more tools upfront; context-constrained users get deferral automatically.

**Impact**: Medium (reduces context overhead of a large plugin ecosystem; enables scaling to 50+ plugins without degrading response quality).
**Effort**: Medium (requires changes to plugin loader, router, and context budget subsystems).
**Tier**: SS4.3 (Tool/Plugin Subsystem - Dynamic Plugin/Tool Discovery).
