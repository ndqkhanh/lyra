---
title: Add an MCP server
description: Plug an MCP-protocol tool server into a Lyra session, with both stdio and HTTP examples.
---

# Add an MCP server <span class="lyra-badge intermediate">intermediate</span>

[MCP](https://modelcontextprotocol.io/) (Model Context Protocol)
servers expose tools and resources over a standard wire protocol.
Lyra speaks MCP natively — every tool an MCP server registers becomes
indistinguishable from a built-in tool to the agent loop.

## What you'll need

- An MCP server. There are two flavours: **stdio** (subprocess) and
  **HTTP**. Most published servers are stdio.
- 30 seconds.

## Recipe 1 — Add at session start

Add servers to `~/.lyra/mcp.toml` and they auto-connect on every
session:

```toml title="~/.lyra/mcp.toml"
[servers.filesystem]
type = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"]

[servers.github]
type = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "${GH_TOKEN}" }

[servers.local-http]
type = "http"
url = "http://localhost:8765/mcp"
headers = { Authorization = "Bearer ${MY_TOKEN}" }
```

Then start a session as normal — Lyra connects on `SESSION_START`.
`/mcp` shows the connected servers and how many tools each registered:

```
❯ /mcp

filesystem (stdio)   12 tools
github (stdio)        9 tools
local-http (http)     3 tools
```

## Recipe 2 — Add at runtime

You can add a server inside a session without editing TOML:

```
❯ /mcp add filesystem stdio "npx -y @modelcontextprotocol/server-filesystem /tmp"
✓ connected · 12 tools registered

❯ /mcp add internal http https://internal.example.com/mcp --header "Authorization: Bearer $TOKEN"
✓ connected · 3 tools registered
```

Runtime additions live for the session only. Persist with `/mcp save`.

## Recipe 3 — Scan for risky behaviour first

Before connecting an unknown server, ask Lyra to **scan** it:

```bash
lyra mcp scan stdio "npx -y suspicious-package"
```

The scan boots the server in a sandbox, enumerates the tool catalogue,
runs each tool's schema through the [secret-scan
hook](../concepts/tools-and-hooks.md#shipped-hooks), checks for
prompt-injection patterns in tool descriptions, and reports a risk
verdict per tool.

!!! note "Phase 5a — `lyra mcp scan` is a planned command"
    The scan command is on the roadmap; until then, the safe path is
    to read the server's source before connecting it. See
    [community ecosystem](../community-ecosystem.md) for vetted
    servers.

## Verify it's wired up

```
❯ /tools | grep -i mcp
filesystem.read_file       (mcp · risk=low)
filesystem.write_file      (mcp · risk=medium)
github.create_issue        (mcp · risk=medium)
…
```

In a session, you can call MCP tools directly with `/tool`:

```
❯ /tool filesystem.read_file path=/tmp/notes.md
…
```

Or just let the model reach for them — they're in the L2 tool schema
list automatically.

## Permissions

Every MCP tool is wrapped with the `risk` field from its schema (or
`medium` if missing). It flows through the
[Permission Bridge](../concepts/permission-bridge.md) like every other
tool. There is no special MCP path; the bridge doesn't trust MCP more
or less than built-ins.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `connection refused` | The server's command failed; run it manually to see stderr |
| `0 tools registered` | The server connected but didn't advertise any tools — check its logs |
| `tool name collision` | Two MCP servers registered the same tool name; rename one or scope with `--prefix` |
| Slow session start | An MCP server is slow to enumerate; set `[servers.<name>] timeout_s = 5` |

[← How-To overview](index.md){ .md-button }
[Write a skill →](write-skill.md){ .md-button .md-button--primary }
