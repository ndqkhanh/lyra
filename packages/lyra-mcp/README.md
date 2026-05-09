# lyra-mcp

**Model Context Protocol (MCP)** integration for Lyra. Two halves
ship in this package:

* **Consumer** — Lyra connects to third-party MCP servers
  (filesystem, sqlite, jira, notion, github, …) via stdio or HTTP and
  exposes their tools to the agent loop with trust-banner wrapping
  and progressive disclosure.
* **Server** — Lyra exposes itself as an MCP server (`lyra mcp serve
  --transport {stdio,http}`) so other clients (Claude Desktop, the
  ACP REPL, custom tooling) can drive it the same way.

Current as of **v2.7.1** (2026-04-27). Test count: **57 passing**.

## Consumer side

```bash
# Add an MCP server (writes to ~/.lyra/mcp.json)
lyra mcp add filesystem -- npx @modelcontextprotocol/server-filesystem /path/to/dir
lyra mcp add github -- env GITHUB_TOKEN=… npx @modelcontextprotocol/server-github

# Inspect / validate
lyra mcp list
lyra mcp doctor      # JSON-RPC handshake + list_tools probe per server

# Remove
lyra mcp remove filesystem
```

The `~/.lyra/mcp.json` autoload runs at REPL boot — every server
listed there is `initialize`d, `list_tools`-probed, and its tools are
adapted into the OpenAI `tools=` shape (`mcp__<server>__<tool>`
naming) before the first prompt.

## Server side

```bash
lyra mcp serve --transport stdio
# or HTTP, loopback-bound by default with a generated bearer token:
lyra mcp serve --transport http --port 47780
```

Exposed tools (read-only by default; write tools opt-in via config):

| Tool                      | Reads                                           |
|---------------------------|-------------------------------------------------|
| `read_session(session_id)`| session metadata + recent turns from `.lyra/sessions/state.db` |
| `get_plan(plan_id)`       | full plan artifact + acceptance tests           |
| `list_skills()`           | every loaded SKILL.md (description + path)      |
| `read_artifact(hash)`     | content-addressed artifact lookup               |

## Architecture

See [`docs/blocks/14-mcp-adapter.md`](../../docs/blocks/14-mcp-adapter.md) for:

* the JSON-RPC framing and timeout / malformed-response handling;
* the trust-banner wrapping and injection-guard chain;
* the progressive-disclosure tier model (cold tools surface via the
  umbrella `MCP` tool; hot tools graduate to flat schemas);
* the consumer cache (TTL'd `list_tools` results to keep boot fast);
* the server's auth and write-tool opt-in story.

## Testing

```bash
# from projects/lyra/packages/lyra-mcp/
uv run pytest -q             # 57 tests in v2.7.1
```

## See also

* [`projects/lyra/CHANGELOG.md`](../../CHANGELOG.md)
* [`projects/lyra/docs/blocks/14-mcp-adapter.md`](../../docs/blocks/14-mcp-adapter.md)
* [`projects/lyra/packages/lyra-cli/README.md`](../lyra-cli/README.md) — the consumer entry-point.
