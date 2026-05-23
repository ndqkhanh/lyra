"""ECC MCP servers - 27 servers from Everything Claude Code"""

from .mcp_manager import MCPServer, MCPManager


def register_ecc_servers(manager: MCPManager):
    """Register all ECC MCP servers"""

    # Issue Tracking (3 servers)
    servers = [
        MCPServer(
            name="jira",
            description="Jira issue tracking",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-jira"],
            env={"JIRA_URL": "", "JIRA_EMAIL": "", "JIRA_API_TOKEN": ""},
            category="issue-tracking"
        ),
        MCPServer(
            name="github",
            description="GitHub operations (PRs, issues, repos)",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": ""},
            category="issue-tracking"
        ),
        MCPServer(
            name="confluence",
            description="Confluence Cloud integration",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-confluence"],
            env={"CONFLUENCE_URL": "", "CONFLUENCE_EMAIL": "", "CONFLUENCE_API_TOKEN": ""},
            category="issue-tracking"
        ),
    ]

    # Databases (2 servers)
    servers.extend([
        MCPServer(
            name="supabase",
            description="Supabase database operations",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-supabase"],
            env={"SUPABASE_URL": "", "SUPABASE_KEY": ""},
            category="database"
        ),
        MCPServer(
            name="clickhouse",
            description="ClickHouse analytics queries",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-clickhouse"],
            env={"CLICKHOUSE_URL": ""},
            category="database"
        ),
    ])

    # Deployment Platforms (6 servers)
    servers.extend([
        MCPServer(
            name="vercel",
            description="Vercel deployments and projects",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-vercel"],
            env={"VERCEL_TOKEN": ""},
            category="deployment"
        ),
        MCPServer(
            name="railway",
            description="Railway deployments",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-railway"],
            env={"RAILWAY_TOKEN": ""},
            category="deployment"
        ),
        MCPServer(
            name="cloudflare-docs",
            description="Cloudflare documentation",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-cloudflare-docs"],
            env={},
            category="deployment"
        ),
        MCPServer(
            name="cloudflare-workers-builds",
            description="Cloudflare Workers builds",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-cloudflare-workers-builds"],
            env={"CLOUDFLARE_API_TOKEN": ""},
            category="deployment"
        ),
        MCPServer(
            name="cloudflare-workers-bindings",
            description="Cloudflare Workers bindings",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-cloudflare-workers-bindings"],
            env={"CLOUDFLARE_API_TOKEN": ""},
            category="deployment"
        ),
        MCPServer(
            name="cloudflare-observability",
            description="Cloudflare observability",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-cloudflare-observability"],
            env={"CLOUDFLARE_API_TOKEN": ""},
            category="deployment"
        ),
    ])

    # Memory Systems (3 servers)
    servers.extend([
        MCPServer(
            name="memory",
            description="Persistent memory across sessions",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            env={},
            category="memory"
        ),
        MCPServer(
            name="omega-memory",
            description="Semantic search, multi-agent coordination",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-omega-memory"],
            env={},
            category="memory"
        ),
        MCPServer(
            name="longhand",
            description="Lossless Claude Code session history",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-longhand"],
            env={},
            category="memory"
        ),
    ])

    # Web Automation (4 servers)
    servers.extend([
        MCPServer(
            name="playwright",
            description="Browser automation and testing",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-playwright"],
            env={},
            category="web"
        ),
        MCPServer(
            name="browserbase",
            description="Cloud browser sessions",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-browserbase"],
            env={"BROWSERBASE_API_KEY": ""},
            category="web"
        ),
        MCPServer(
            name="browser-use",
            description="AI browser agent for web tasks",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-browser-use"],
            env={},
            category="web"
        ),
        MCPServer(
            name="firecrawl",
            description="Web scraping and crawling",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-firecrawl"],
            env={"FIRECRAWL_API_KEY": ""},
            category="web"
        ),
    ])

    # AI Generation (2 servers)
    servers.extend([
        MCPServer(
            name="fal-ai",
            description="AI image/video/audio generation",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-fal-ai"],
            env={"FAL_KEY": ""},
            category="ai"
        ),
        MCPServer(
            name="magic",
            description="Magic UI components",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-magic"],
            env={},
            category="ai"
        ),
    ])

    # Search & Documentation (2 servers)
    servers.extend([
        MCPServer(
            name="exa-web-search",
            description="Web search and research",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-exa"],
            env={"EXA_API_KEY": ""},
            category="search"
        ),
        MCPServer(
            name="context7",
            description="Live documentation lookup",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-context7"],
            env={},
            category="search"
        ),
    ])

    # Testing & Optimization (3 servers)
    servers.extend([
        MCPServer(
            name="evalview",
            description="AI agent regression testing",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-evalview"],
            env={},
            category="testing"
        ),
        MCPServer(
            name="token-optimizer",
            description="95%+ context reduction",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-token-optimizer"],
            env={},
            category="testing"
        ),
        MCPServer(
            name="sequential-thinking",
            description="Chain-of-thought reasoning",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
            env={},
            category="testing"
        ),
    ])

    # Multi-Agent & Other (2 servers)
    servers.extend([
        MCPServer(
            name="devfleet",
            description="Multi-agent orchestration in isolated worktrees",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-devfleet"],
            env={},
            category="other"
        ),
        MCPServer(
            name="filesystem",
            description="Filesystem operations",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
            env={},
            category="other"
        ),
    ])

    # Register all servers
    for server in servers:
        manager.register_server(server)

    print(f"✓ Registered {len(servers)} MCP servers")
