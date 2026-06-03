# MCP Adapter -- How It Works

> Bidirectional connectivity with external MCP servers using JSON-RPC 2.0 over stdio/HTTP/WebSocket transports. Employs ANX 3EX decoupling for 47-66% token reduction. Ships 10+ bundled servers.
> **Block:** 09 | **Phase:** 4 (Integration) | **Depends on:** Agent Loop, Permission Bridge, Hooks, Context Engine, Verifier

## MCP Protocol (JSON-RPC 2.0)

All communication with external MCP servers follows the Model Context Protocol, built on JSON-RPC 2.0:

```
--> {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}
<-- {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}}}}

--> {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
<-- {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"search","description":"...","inputSchema":{...}}]}}

--> {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search","arguments":{"query":"lyra"}}}
<-- {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"Results: ..."}]}}
```

Three lifecycle steps: `initialize` (handshake + capability negotiation), `tools/list` (server advertises its tools), `tools/call` (agent invokes a tool).

## Multi-Transport Architecture

Three transports are supported, selected per-server:

| Transport | Latency | Use Case | Implementation |
|-----------|---------|----------|---------------|
| **stdio** | ~340ms | Local servers, subprocess | `subprocess.Popen` with stdin/stdout JSON-RPC |
| **HTTP** | ~450ms | Remote servers, cloud | `httpx` client with connection pooling |
| **WebSocket** | ~400ms | Streaming servers, real-time | `websockets` library with persistent connection |

The `TransportPool` manages connection reuse across sequential calls, avoiding cold-start on every invocation. A 100ms batched RPC window coalesces multiple tool calls into a single transport round-trip when they fire in quick succession.

## ANX 3EX Decoupling (47-66% Token Reduction)

ANX (Agent-Native eXchange) decoupling separates tool responses into three exchange tiers:

| Tier | What | Token Cost | Example |
|------|------|------------|---------|
| **1EX** | Metadata | ~50 tokens | `{"status":"ok","tool_id":"search_1"}` |
| **2EX** | Summary | ~200 tokens | `"Found 3 repositories matching 'lyra'"` |
| **3EX** | Full content | Full payload | Full search results, file contents, diffs |

By default, the agent receives only 1EX + 2EX responses. Full 3EX content is fetched on demand when the agent explicitly requests it. This reduces per-request token consumption by 47-66% depending on payload size.

```python
class ANXExchange:
    def deliver(self, response: ToolResponse, tier: int) -> str:
        if tier >= 3:
            return response.full_content           # full payload
        elif tier >= 2:
            return response.summary                # 2EX: ~200 tok summary
        else:
            return response.metadata               # 1EX: ~50 tok status
```

## 10+ Bundled Servers

Lyra ships with 10+ pre-configured MCP servers:

| Server | Transport | Purpose | Default Trust |
|--------|-----------|---------|---------------|
| `filesystem` | stdio | File read/write operations | trusted |
| `github` | stdio | GitHub API (issues, PRs, repos) | first_party |
| `brave-search` | stdio | Web search | first_party |
| `puppeteer` | stdio | Browser automation | third_party |
| `postgres` | stdio | Database queries | third_party |
| `sqlite` | stdio | Local database operations | trusted |
| `redis` | stdio | Cache operations | third_party |
| `docker` | stdio | Container management | third_party |
| `shell` | stdio | System commands | trusted |
| `custom` | HTTP | User-defined external servers | user_config |

## Progressive Tool Disclosure

To combat prompt bloat from many tool definitions, the adapter uses three tiers:

| Tier | Always Available? | Tools | Token Cost |
|------|-------------------|-------|------------|
| Umbrella | Always | Single `mcp` tool with actions: `list_servers`, `list_tools`, `call` | ~150 tok |
| Hot Set | If promoted | Up to 5 first-class tools (usage-scored, auto-promoted) | ~2000 tok for 5 |
| Cold Set | Discovery only | All other servers' tools | 0 tok until discovered |

An `AdaptiveHotSetManager` tracks tool usage with exponential score decay (decay=0.95/hour). Frequently used tools auto-promote to the hot set; unused tools decay back to cold.

Progressive disclosure cuts prompt tokens by 95%: from ~10,000 tokens (all tools flat) to ~500 tokens (umbrella + 5 hot tools).

## Performance

| Metric | Cold (no cache) | Warm (cache hit) |
|--------|----------------|-----------------|
| Single call latency | 340ms | 12ms |
| Prompt tokens | ~10,000 | ~500 |
| ANX 3EX token reduction | 47-66% | -- |
| Cost per 1K requests | $150.00 | $7.50 |

## Related Documents

- **Concepts:** [Tools and Hooks](../concepts/02-tools-and-hooks.md), [Sessions and State](../concepts/08-sessions-and-state.md)
- **Architecture:** [Architecture Overview](../architecture/11-architecture-overview.md), [Provider Abstraction](../architecture/03-provider-abstraction.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Permission Bridge](05-permission-bridge.md), [Subagent Worktree](08-subagent-worktree.md)

---

*References: MCP Specification (Anthropic, 2024), ReAct (arXiv:2210.03629), Tiered Tool Selection (arXiv:2402.07398), Data-Flow Taint Analysis (arXiv:2406.15065)*
