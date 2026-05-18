# MCP Integration Guide

Complete guide to integrating Model Context Protocol (MCP) servers with Lyra.

---

## What is MCP?

**Model Context Protocol (MCP)** is a standard protocol for connecting AI agents to external tools and data sources.

Lyra supports MCP through the `lyra-mcp` package, allowing you to:
- Connect to filesystem operations
- Access GitHub repositories
- Query PostgreSQL databases
- Create custom tool integrations

---

## Quick Start

### 1. Install MCP Package

```bash
pip install -e packages/lyra-mcp
```

### 2. Configure MCP Server

Create `.lyra/mcp/config.json`:

```json
{
  "servers": {
    "filesystem": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    },
    "github": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your-token-here"
      }
    },
    "postgres": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    }
  }
}
```

### 3. Start Lyra with MCP

```bash
lyra --mcp
```

---

## Available MCP Servers

### 1. Filesystem Server

**Purpose:** File operations with permission control

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**Configuration:**
```json
{
  "filesystem": {
    "enabled": true,
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "permissions": {
      "read": true,
      "write": true,
      "delete": false
    }
  }
}
```

**Available Tools:**
- `read_file` - Read file contents
- `write_file` - Write to file
- `list_directory` - List directory contents
- `create_directory` - Create new directory
- `move_file` - Move/rename file
- `search_files` - Search for files

### 2. GitHub Server

**Purpose:** GitHub repository access

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-github
```

**Configuration:**
```json
{
  "github": {
    "enabled": true,
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "ghp_..."
    }
  }
}
```

**Available Tools:**
- `search_repositories` - Search GitHub repos
- `get_file_contents` - Read file from repo
- `create_issue` - Create GitHub issue
- `create_pull_request` - Create PR
- `list_commits` - List commit history
- `get_issue` - Get issue details

### 3. PostgreSQL Server

**Purpose:** Database queries

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-postgres
```

**Configuration:**
```json
{
  "postgres": {
    "enabled": true,
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/db"],
    "permissions": {
      "read": true,
      "write": false
    }
  }
}
```

**Available Tools:**
- `query` - Execute SQL query
- `list_tables` - List database tables
- `describe_table` - Get table schema
- `list_databases` - List databases

---

## Creating Custom MCP Servers

### 1. Server Structure

```typescript
// my-custom-server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  {
    name: "my-custom-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Register tools
server.setRequestHandler("tools/list", async () => {
  return {
    tools: [
      {
        name: "my_tool",
        description: "My custom tool",
        inputSchema: {
          type: "object",
          properties: {
            input: { type: "string" }
          }
        }
      }
    ]
  };
});

server.setRequestHandler("tools/call", async (request) => {
  const { name, arguments: args } = request.params;
  
  if (name === "my_tool") {
    // Implement tool logic
    return {
      content: [
        {
          type: "text",
          text: `Result: ${args.input}`
        }
      ]
    };
  }
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

### 2. Register with Lyra

Add to `.lyra/mcp/config.json`:

```json
{
  "servers": {
    "my-custom-server": {
      "enabled": true,
      "command": "node",
      "args": ["path/to/my-custom-server.js"]
    }
  }
}
```

### 3. Use in Lyra

```bash
lyra --mcp

# In REPL
agent › use my_tool with input "test"
```

---

## MCP Tool Usage

### In REPL

```bash
# List available MCP tools
agent › /mcp list

# Use MCP tool
agent › /mcp use filesystem read_file --path "README.md"

# Or natural language
agent › read the README file using MCP
```

### In Code

```python
from lyra_mcp import MCPClient

# Initialize client
client = MCPClient(config_path=".lyra/mcp/config.json")

# List tools
tools = client.list_tools()

# Call tool
result = client.call_tool(
    server="filesystem",
    tool="read_file",
    arguments={"path": "README.md"}
)

print(result)
```

---

## Advanced Configuration

### Permission Control

```json
{
  "servers": {
    "filesystem": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
      "permissions": {
        "read": true,
        "write": true,
        "delete": false,
        "allowed_paths": [
          "/allowed/path",
          "/another/path"
        ],
        "denied_paths": [
          "/allowed/path/secrets"
        ]
      }
    }
  }
}
```

### Environment Variables

```json
{
  "servers": {
    "github": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "GITHUB_API_URL": "https://api.github.com"
      }
    }
  }
}
```

### Timeout Configuration

```json
{
  "servers": {
    "postgres": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/db"],
      "timeout": 30000,
      "retry": {
        "max_attempts": 3,
        "backoff": "exponential"
      }
    }
  }
}
```

---

## Examples

### Example 1: File Operations

```python
from lyra_mcp import MCPClient

client = MCPClient()

# Read file
content = client.call_tool(
    server="filesystem",
    tool="read_file",
    arguments={"path": "src/main.py"}
)

# Write file
client.call_tool(
    server="filesystem",
    tool="write_file",
    arguments={
        "path": "output.txt",
        "content": "Hello, MCP!"
    }
)

# List directory
files = client.call_tool(
    server="filesystem",
    tool="list_directory",
    arguments={"path": "src/"}
)
```

### Example 2: GitHub Operations

```python
# Search repositories
repos = client.call_tool(
    server="github",
    tool="search_repositories",
    arguments={"query": "language:python stars:>1000"}
)

# Get file contents
content = client.call_tool(
    server="github",
    tool="get_file_contents",
    arguments={
        "owner": "anthropics",
        "repo": "anthropic-sdk-python",
        "path": "README.md"
    }
)

# Create issue
issue = client.call_tool(
    server="github",
    tool="create_issue",
    arguments={
        "owner": "myorg",
        "repo": "myrepo",
        "title": "Bug report",
        "body": "Description of the bug"
    }
)
```

### Example 3: Database Queries

```python
# List tables
tables = client.call_tool(
    server="postgres",
    tool="list_tables",
    arguments={}
)

# Query data
results = client.call_tool(
    server="postgres",
    tool="query",
    arguments={
        "sql": "SELECT * FROM users WHERE active = true LIMIT 10"
    }
)

# Describe table
schema = client.call_tool(
    server="postgres",
    tool="describe_table",
    arguments={"table": "users"}
)
```

---

## Troubleshooting

### Issue: MCP server not starting

**Solution:**
```bash
# Check server installation
npx @modelcontextprotocol/server-filesystem --version

# Check configuration
cat .lyra/mcp/config.json | jq .

# Check logs
cat .lyra/logs/mcp.log
```

### Issue: Permission denied

**Solution:**
```json
{
  "filesystem": {
    "permissions": {
      "read": true,
      "write": true,
      "allowed_paths": ["/your/path"]
    }
  }
}
```

### Issue: Tool not found

**Solution:**
```bash
# List available tools
lyra --mcp
agent › /mcp list

# Check server status
agent › /mcp status
```

---

## Security Best Practices

1. **Limit permissions** - Only grant necessary permissions
2. **Restrict paths** - Use `allowed_paths` and `denied_paths`
3. **Secure credentials** - Use environment variables for tokens
4. **Audit logs** - Enable MCP logging
5. **Timeout limits** - Set reasonable timeouts

---

## Next Steps

- **[Skills Guide](skills.md)** - Create custom skills
- **[Hooks Guide](hooks.md)** - Create custom hooks
- **[API Reference](../reference/api.md)** - Full API documentation

---

**Last Updated:** 2026-05-18
