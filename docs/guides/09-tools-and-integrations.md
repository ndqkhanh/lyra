# Guide: Tools and Integrations

> 📖 Guide — Explore Lyra's built-in tools, Model Context Protocol (MCP) integration, and plugin system. Learn what each tool does, how MCP servers connect, and how to extend functionality.

Tools are how Lyra interacts with the world -- reading files, running commands, fetching web content, and accessing external services. Built-in tools and MCP-provided tools are indistinguishable to the agent loop.

---

## Built-in Tools Catalog

These tools ship with every Lyra installation and require no configuration:

| Tool | Risk | Writes | What It Does |
|---|---|---|---|
| Read | low | no | Read file contents |
| Write | medium | yes | Write content to file |
| Edit | medium | yes | Edit specific lines in a file |
| Bash | high | yes | Execute shell commands |
| Grep | low | no | Search file contents by pattern |
| Glob | low | no | Find files by glob pattern |
| WebFetch | low | no | Fetch and process URL content |
| WebSearch | low | no | Search the web |
| LSP | low | no | Query language server (go-to-def, references, hover) |
| Task | low | no | Create and manage task lists |

Each tool has:
- A typed JSON Schema for arguments
- A risk level (low/medium/high/critical) that determines permission behavior
- A `writes` flag indicating state modification
- Observation reduction for large outputs (head-tail elision with artifact links)

### Tool Observation Reduction

Large outputs never enter the full transcript:

| Tool | Reduced Form |
|---|---|
| Read (large file) | First 50 + last 20 lines + `[truncated, view <hash>]` |
| Bash (long log) | Last 80 lines + exit code + duration |
| WebFetch | Title + first 500 words |
| Grep (many matches) | First 20 hits + total count |

The full payload is always available as a hash-addressed artifact; the model can pull it back with `view <hash>`.

---

## MCP Integration

The Model Context Protocol (MCP) is an open standard for connecting LLM applications to external tools and data sources. MCP servers are process-isolated, language-independent, and crash-resilient.

### Protocol Lifecycle

Each MCP server follows a 5-stage lifecycle:

1. **Discovery**: Server advertises tools via `tools/list` (JSON-RPC 2.0)
2. **Handshake**: Client and server agree on protocol version (`initialize` / `initialized`)
3. **Invocation**: Client sends `tools/call` with typed arguments
4. **Result**: Server returns structured result or error
5. **Cleanup**: Server releases resources on `notifications/stopping`

### 10 Bundled MCP Servers

Lyra ships with these MCP servers pre-configured:

| Server | Category | Tools Provided |
|---|---|---|
| filesystem | Core | Read, Write, Edit, Search |
| database (SQLite) | Data | query, execute, schema |
| web | Search | fetch, search |
| github | Dev | pr, issue, file operations |
| terminal | Shell | command execution |
| memory | Memory | store, retrieve, search |
| notebook | Analysis | execute cells, create notebooks |
| vision | Multimodal | analyze images, OCR |
| audio | Voice | transcribe, synthesize |
| mcp-tools | Utility | mcp_discover, mcp_invoke |

### Adding Your Own MCP Server

Configure in `~/.lyra/config.toml`:

```toml
[[mcp_servers.server]]
name = "my-custom-tool"
command = "python"
args = ["path/to/server.py"]
allowed_tools = ["my_tool"]
```

The server must implement the MCP protocol (any language). Once registered, its tools appear in the agent loop alongside built-in tools, with the same permission gating, hook lifecycle, and observation reduction.

---

## Performance: Built-in vs MCP

| Dimension | Built-in | MCP (stdio) |
|---|---|---|
| Latency p50 | ~5ms | ~35-150ms |
| Process isolation | None | Full subprocess |
| Crash resilience | Loop halts | Server restarts |
| Language | Python only | Any language |
| Startup cost | None | 200-800ms handshake |

Rule of thumb: built-ins for hot-path operations (read/write loops, batch greps); MCP for everything else.

---

## Plugin System

Beyond MCP, Lyra supports:
- **Pre/Post hooks**: Python callables injected at tool execution boundaries (see the [Hooks concept](../concepts/02-tools-and-hooks.md))
- **Custom tools**: Python functions registered in the tool pool with a typed schema
- **Provider plugins**: Custom LLM backends implementing the `Provider` protocol

---

## Related Docs

- [Architecture: MCP Adapter](../blocks/09-mcp-adapter.md) -- protocol lifecycle, server management
- [Block: Tools and Hooks](../concepts/02-tools-and-hooks.md) -- tool registration, hook lifecycle
- [Concept: Permission Bridge](../concepts/09-permission-bridge.md) -- tool risk classification, access control
- [Guide: Agent Execution](01-agent-execution.md) -- how the loop invokes tools
- [Guide: Safety and Permissions](05-safety-and-permissions.md) -- tool call validation pipeline
- [MCP Specification](https://modelcontextprotocol.io/) -- official protocol docs
