"""Centralized tool registry — 200+ tools across 20 toolsets.

Plan 9 implementation with:
- 20 toolsets covering the full tool landscape
- Progressive disclosure (L1 ~50t, L2 ~200t, L3 full)
- Tool search by category, capability tag, and keyword
- Dependency-aware tool loading
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Top-level tool category — one per toolset."""

    FILESYSTEM = "filesystem"
    CODE = "code"
    SEARCH = "search"
    SHELL = "shell"
    GIT = "git"
    WEB_BROWSER = "web_browser"
    DATABASE = "database"
    DOCUMENT = "document"
    MEDIA = "media"
    NETWORK = "network"
    SECURITY = "security"
    AGENT = "agent"
    MEMORY = "memory"
    SKILL = "skill"
    OBSERVABILITY = "observability"
    AUTOMATION = "automation"
    COMMUNICATION = "communication"
    MCP = "mcp"
    VOICE = "voice"
    UI = "ui"


class ToolDisclosureLevel(Enum):
    """Progressive disclosure level for tool descriptions."""

    L1 = 1  # ~50 tokens — name + one-line summary
    L2 = 2  # ~200 tokens — name + description + params
    L3 = 3  # Full — everything including examples


@dataclass(frozen=True)
class ToolManifest:
    """Registry entry for a single tool.

    Attributes:
        name: Unique tool identifier (e.g. 'file_read').
        category: Which toolset this belongs to.
        description: One-line summary (~50 chars).
        parameters: Parameter names and types.
        disclosure: Progressive disclosure level.
        required_capabilities: Optional capability tags for access control.
        dependencies: Other tools this tool depends on.
        is_destructive: Whether this tool can cause irreversible changes.
        since_version: Lyra version this tool was introduced.
        tags: Searchable tags for discovery.
    """

    name: str
    category: ToolCategory
    description: str
    parameters: tuple[str, ...] = ()
    disclosure: ToolDisclosureLevel = ToolDisclosureLevel.L1
    required_capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    is_destructive: bool = False
    since_version: str = "1.0.0"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Toolset:
    """A named collection of tools within a category.

    Attributes:
        name: Display name.
        category: Which ToolCategory this belongs to.
        description: What this toolset provides.
        tools: Tuple of ToolManifest entries.
    """

    name: str
    category: ToolCategory
    description: str
    tools: tuple[ToolManifest, ...]

    @property
    def tool_count(self) -> int:
        return len(self.tools)

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(t.name for t in self.tools)


# ── Helper to build tool manifests concisely ────────────────────────────


def _t(
    name: str,
    cat: ToolCategory,
    desc: str,
    params: tuple[str, ...] = (),
    disc: ToolDisclosureLevel = ToolDisclosureLevel.L1,
    caps: tuple[str, ...] = (),
    deps: tuple[str, ...] = (),
    destructive: bool = False,
    tags: tuple[str, ...] = (),
) -> ToolManifest:
    return ToolManifest(
        name=name,
        category=cat,
        description=desc,
        parameters=params,
        disclosure=disc,
        required_capabilities=caps,
        dependencies=deps,
        is_destructive=destructive,
        tags=tags,
    )


# ── 20 Toolsets — 200+ tools ────────────────────────────────────────────

FILESYSTEM_TOOLS = Toolset(
    name="Filesystem",
    category=ToolCategory.FILESYSTEM,
    description="Read, write, edit, and manage files and directories.",
    tools=(
        _t(
            "file_read",
            ToolCategory.FILESYSTEM,
            "Read a file from the local filesystem",
            ("file_path", "offset", "limit"),
        ),
        _t(
            "file_write",
            ToolCategory.FILESYSTEM,
            "Write a file to the local filesystem",
            ("file_path", "content"),
            destructive=True,
        ),
        _t(
            "file_edit",
            ToolCategory.FILESYSTEM,
            "Perform exact string replacements in files",
            ("file_path", "old_string", "new_string"),
            destructive=True,
        ),
        _t(
            "file_delete",
            ToolCategory.FILESYSTEM,
            "Delete a file at the specified path",
            ("file_path",),
            destructive=True,
        ),
        _t(
            "file_move",
            ToolCategory.FILESYSTEM,
            "Move or rename a file",
            ("source", "destination"),
            destructive=True,
        ),
        _t(
            "file_copy",
            ToolCategory.FILESYSTEM,
            "Copy a file to a new location",
            ("source", "destination"),
        ),
        _t(
            "file_search",
            ToolCategory.FILESYSTEM,
            "Search for files matching a pattern",
            ("pattern", "path", "recursive"),
        ),
        _t(
            "file_watch",
            ToolCategory.FILESYSTEM,
            "Watch a file or directory for changes",
            ("path", "events"),
        ),
        _t(
            "file_stat", ToolCategory.FILESYSTEM, "Get file metadata and statistics", ("file_path",)
        ),
        _t(
            "file_glob",
            ToolCategory.FILESYSTEM,
            "Find files matching glob patterns",
            ("pattern", "root"),
        ),
        _t(
            "dir_create",
            ToolCategory.FILESYSTEM,
            "Create a new directory",
            ("path", "parents"),
            destructive=True,
        ),
        _t(
            "dir_list",
            ToolCategory.FILESYSTEM,
            "List contents of a directory",
            ("path", "recursive"),
        ),
    ),
)

CODE_TOOLS = Toolset(
    name="Code",
    category=ToolCategory.CODE,
    description="Code analysis, generation, refactoring, and LSP integration.",
    tools=(
        _t(
            "code_lsp_goto_def",
            ToolCategory.CODE,
            "Go to definition of a symbol",
            ("file", "line", "character"),
        ),
        _t(
            "code_lsp_find_refs",
            ToolCategory.CODE,
            "Find all references to a symbol",
            ("file", "line", "character"),
        ),
        _t(
            "code_lsp_hover",
            ToolCategory.CODE,
            "Get type info and docs at a position",
            ("file", "line", "character"),
        ),
        _t(
            "code_lsp_rename",
            ToolCategory.CODE,
            "Rename a symbol across the project",
            ("file", "line", "character", "new_name"),
            destructive=True,
        ),
        _t("code_lsp_diagnostics", ToolCategory.CODE, "Get LSP diagnostics for a file", ("file",)),
        _t(
            "code_lsp_code_actions",
            ToolCategory.CODE,
            "Get available code actions/refactorings",
            ("file", "start_line", "end_line"),
        ),
        _t("code_lsp_symbols", ToolCategory.CODE, "Get document symbols outline", ("file",)),
        _t(
            "code_ast_search",
            ToolCategory.CODE,
            "Search code by AST pattern matching",
            ("pattern", "language", "path"),
        ),
        _t(
            "code_ast_replace",
            ToolCategory.CODE,
            "Replace code using AST matching",
            ("pattern", "replacement", "language"),
            destructive=True,
        ),
        _t(
            "code_format",
            ToolCategory.CODE,
            "Format code using project formatter",
            ("file", "formatter"),
        ),
        _t("code_lint", ToolCategory.CODE, "Run linter on a file or directory", ("path", "linter")),
        _t(
            "code_typecheck",
            ToolCategory.CODE,
            "Run type checker on a file or directory",
            ("path",),
        ),
        _t(
            "code_test_run",
            ToolCategory.CODE,
            "Run tests for a file or package",
            ("path", "marker"),
        ),
        _t("code_test_coverage", ToolCategory.CODE, "Get test coverage report", ("path",)),
        _t(
            "code_dependency_graph",
            ToolCategory.CODE,
            "Generate import/require dependency graph",
            ("entry_point",),
        ),
        _t(
            "code_complexity",
            ToolCategory.CODE,
            "Analyze cyclomatic/cognitive complexity",
            ("file",),
        ),
        _t("code_dead_imports", ToolCategory.CODE, "Find unused imports and dead code", ("path",)),
        _t("code_smells", ToolCategory.CODE, "Detect code smells and anti-patterns", ("file",)),
    ),
)

SEARCH_TOOLS = Toolset(
    name="Search",
    category=ToolCategory.SEARCH,
    description="Code search, semantic search, grep, and content discovery.",
    tools=(
        _t(
            "search_grep",
            ToolCategory.SEARCH,
            "Search file contents with regex patterns",
            ("pattern", "path", "include"),
        ),
        _t(
            "search_code",
            ToolCategory.SEARCH,
            "Semantic code search across the codebase",
            ("query", "language"),
        ),
        _t("search_file", ToolCategory.SEARCH, "Find files by name pattern", ("pattern", "path")),
        _t("search_symbol", ToolCategory.SEARCH, "Search for symbols across workspace", ("query",)),
        _t(
            "search_content",
            ToolCategory.SEARCH,
            "Full-text search across files",
            ("query", "path", "max_results"),
        ),
        _t(
            "search_regex",
            ToolCategory.SEARCH,
            "Advanced regex search with capture groups",
            ("pattern", "path"),
        ),
        _t(
            "search_history",
            ToolCategory.SEARCH,
            "Search prior session history",
            ("query", "limit"),
        ),
        _t(
            "search_web",
            ToolCategory.SEARCH,
            "Search the web for current information",
            ("query", "domains"),
        ),
        _t(
            "search_docs",
            ToolCategory.SEARCH,
            "Search documentation and API references",
            ("query", "source"),
        ),
        _t("search_wiki", ToolCategory.SEARCH, "Search the project wiki", ("query", "tags")),
    ),
)

SHELL_TOOLS = Toolset(
    name="Shell",
    category=ToolCategory.SHELL,
    description="Execute shell commands, manage processes, and terminal interaction.",
    tools=(
        _t(
            "shell_run",
            ToolCategory.SHELL,
            "Execute a shell command",
            ("command", "timeout", "workdir"),
            destructive=True,
        ),
        _t("shell_run_bg", ToolCategory.SHELL, "Run a command in the background", ("command",)),
        _t("shell_pipe", ToolCategory.SHELL, "Pipe multiple commands together", ("commands",)),
        _t(
            "shell_env",
            ToolCategory.SHELL,
            "Get or set environment variables",
            ("action", "key", "value"),
        ),
        _t("shell_which", ToolCategory.SHELL, "Find the path of an executable", ("program",)),
        _t(
            "shell_kill",
            ToolCategory.SHELL,
            "Kill a running process",
            ("pid", "signal"),
            destructive=True,
        ),
        _t(
            "shell_tmux",
            ToolCategory.SHELL,
            "Manage tmux sessions for CLI testing",
            ("action", "session"),
        ),
        _t(
            "shell_script",
            ToolCategory.SHELL,
            "Run a shell script from file",
            ("script_path", "args"),
            destructive=True,
        ),
    ),
)

GIT_TOOLS = Toolset(
    name="Git",
    category=ToolCategory.GIT,
    description="Version control operations — status, diff, commit, branch, PR.",
    tools=(
        _t("git_status", ToolCategory.GIT, "Show working tree status", ()),
        _t(
            "git_diff",
            ToolCategory.GIT,
            "Show changes between commits or working tree",
            ("target",),
        ),
        _t("git_log", ToolCategory.GIT, "Show commit history", ("n", "format")),
        _t("git_branch", ToolCategory.GIT, "List, create, or delete branches", ("action", "name")),
        _t(
            "git_checkout",
            ToolCategory.GIT,
            "Switch branches or restore files",
            ("target",),
            destructive=True,
        ),
        _t(
            "git_commit",
            ToolCategory.GIT,
            "Create a new commit",
            ("message", "files"),
            destructive=True,
        ),
        _t("git_add", ToolCategory.GIT, "Stage file changes for commit", ("files",)),
        _t(
            "git_push",
            ToolCategory.GIT,
            "Push commits to remote repository",
            ("remote", "branch"),
            destructive=True,
        ),
        _t(
            "git_pull",
            ToolCategory.GIT,
            "Pull changes from remote repository",
            ("remote", "branch"),
        ),
        _t("git_stash", ToolCategory.GIT, "Stash working directory changes", ("action",)),
        _t(
            "git_rebase",
            ToolCategory.GIT,
            "Reapply commits on top of another base",
            ("target",),
            destructive=True,
        ),
        _t("git_tag", ToolCategory.GIT, "Create or list tags", ("action", "name")),
        _t("git_blame", ToolCategory.GIT, "Show who last modified each line", ("file",)),
        _t(
            "git_bisect",
            ToolCategory.GIT,
            "Binary search for the commit that introduced a bug",
            ("good", "bad"),
        ),
    ),
)

WEB_TOOLS = Toolset(
    name="Web Browser",
    category=ToolCategory.WEB_BROWSER,
    description="Web fetching, browser automation, API interaction, and scraping.",
    tools=(
        _t(
            "web_fetch",
            ToolCategory.WEB_BROWSER,
            "Fetch and process content from a URL",
            ("url", "prompt"),
        ),
        _t(
            "web_search",
            ToolCategory.WEB_BROWSER,
            "Search the web with domain filtering",
            ("query", "allowed_domains", "blocked_domains"),
        ),
        _t(
            "web_browse",
            ToolCategory.WEB_BROWSER,
            "Interactive browser for complex navigation",
            ("url", "actions"),
        ),
        _t(
            "web_screenshot",
            ToolCategory.WEB_BROWSER,
            "Capture a screenshot of a web page",
            ("url", "viewport"),
        ),
        _t(
            "web_extract",
            ToolCategory.WEB_BROWSER,
            "Extract structured data from a page",
            ("url", "schema"),
        ),
        _t(
            "web_form_fill",
            ToolCategory.WEB_BROWSER,
            "Fill and submit a web form",
            ("url", "form_data"),
        ),
        _t(
            "web_api_call",
            ToolCategory.WEB_BROWSER,
            "Make an HTTP API request",
            ("method", "url", "headers", "body"),
        ),
        _t(
            "web_download",
            ToolCategory.WEB_BROWSER,
            "Download a file from a URL",
            ("url", "destination"),
        ),
        _t(
            "web_websocket",
            ToolCategory.WEB_BROWSER,
            "Connect to a WebSocket endpoint",
            ("url", "messages"),
        ),
        _t(
            "web_graphql",
            ToolCategory.WEB_BROWSER,
            "Execute a GraphQL query",
            ("endpoint", "query", "variables"),
        ),
        _t("web_rss", ToolCategory.WEB_BROWSER, "Fetch and parse RSS/Atom feeds", ("url",)),
        _t("web_sitemap", ToolCategory.WEB_BROWSER, "Parse and crawl a sitemap.xml", ("url",)),
        _t(
            "web_auth",
            ToolCategory.WEB_BROWSER,
            "Authenticate with OAuth/OIDC flow",
            ("provider", "scopes"),
        ),
        _t(
            "web_cookie",
            ToolCategory.WEB_BROWSER,
            "Manage browser cookies",
            ("action", "name", "value"),
        ),
        _t("web_pdf", ToolCategory.WEB_BROWSER, "Render a web page as PDF", ("url", "options")),
    ),
)

DATABASE_TOOLS = Toolset(
    name="Database",
    category=ToolCategory.DATABASE,
    description="Database queries, schema management, migrations, and data operations.",
    tools=(
        _t("db_query", ToolCategory.DATABASE, "Execute a read-only SQL query", ("query", "params")),
        _t(
            "db_execute",
            ToolCategory.DATABASE,
            "Execute a write SQL statement",
            ("statement", "params"),
            destructive=True,
        ),
        _t("db_schema", ToolCategory.DATABASE, "Inspect database schema and tables", ("table",)),
        _t(
            "db_migrate",
            ToolCategory.DATABASE,
            "Run database migrations",
            ("direction", "steps"),
            destructive=True,
        ),
        _t("db_seed", ToolCategory.DATABASE, "Seed database with test data", ("fixture",)),
        _t(
            "db_backup",
            ToolCategory.DATABASE,
            "Create a database backup/dump",
            ("format", "output"),
        ),
        _t(
            "db_restore",
            ToolCategory.DATABASE,
            "Restore database from backup",
            ("file",),
            destructive=True,
        ),
        _t("db_explain", ToolCategory.DATABASE, "Explain query execution plan", ("query",)),
        _t(
            "db_index",
            ToolCategory.DATABASE,
            "Manage database indexes",
            ("action", "table", "columns"),
        ),
        _t("db_connect", ToolCategory.DATABASE, "Connect to a database", ("connection_string",)),
        _t(
            "db_vector_search",
            ToolCategory.DATABASE,
            "Vector similarity search",
            ("embedding", "collection", "top_k"),
        ),
        _t(
            "db_graph_query",
            ToolCategory.DATABASE,
            "Execute a graph database query",
            ("query", "params"),
        ),
        _t("db_cache", ToolCategory.DATABASE, "Manage query result cache", ("action", "key")),
        _t("db_replication_status", ToolCategory.DATABASE, "Check replication lag and health", ()),
    ),
)

DOCUMENT_TOOLS = Toolset(
    name="Document",
    category=ToolCategory.DOCUMENT,
    description="Parse, generate, and convert documents — PDF, Markdown, Office, etc.",
    tools=(
        _t(
            "doc_read",
            ToolCategory.DOCUMENT,
            "Read a document in any supported format",
            ("file_path", "pages"),
        ),
        _t(
            "doc_write",
            ToolCategory.DOCUMENT,
            "Create a document from content",
            ("file_path", "content", "format"),
            destructive=True,
        ),
        _t(
            "doc_convert",
            ToolCategory.DOCUMENT,
            "Convert between document formats",
            ("source", "target_format"),
        ),
        _t(
            "doc_parse_table",
            ToolCategory.DOCUMENT,
            "Extract tables from a document",
            ("file_path", "page"),
        ),
        _t(
            "doc_ocr",
            ToolCategory.DOCUMENT,
            "Extract text from an image or scanned PDF",
            ("file_path", "language"),
        ),
        _t(
            "doc_translate",
            ToolCategory.DOCUMENT,
            "Translate a document to another language",
            ("file_path", "target_language"),
        ),
        _t(
            "doc_summarize",
            ToolCategory.DOCUMENT,
            "Generate a summary of a document",
            ("file_path", "max_length"),
        ),
        _t(
            "doc_diff",
            ToolCategory.DOCUMENT,
            "Show differences between two documents",
            ("file_a", "file_b"),
        ),
        _t(
            "doc_merge",
            ToolCategory.DOCUMENT,
            "Merge multiple documents into one",
            ("files", "output"),
        ),
        _t(
            "doc_template",
            ToolCategory.DOCUMENT,
            "Fill a document template with data",
            ("template", "data"),
        ),
        _t("doc_toc", ToolCategory.DOCUMENT, "Generate a table of contents", ("file_path",)),
        _t(
            "doc_citations",
            ToolCategory.DOCUMENT,
            "Extract and format citations",
            ("file_path", "style"),
        ),
    ),
)

MEDIA_TOOLS = Toolset(
    name="Media",
    category=ToolCategory.MEDIA,
    description="Image, audio, and video processing, generation, and analysis.",
    tools=(
        _t("media_image_view", ToolCategory.MEDIA, "View and analyze an image", ("file_path",)),
        _t(
            "media_image_edit",
            ToolCategory.MEDIA,
            "Edit an image (crop, resize, filter)",
            ("file_path", "operations"),
            destructive=True,
        ),
        _t(
            "media_image_generate",
            ToolCategory.MEDIA,
            "Generate an image from a description",
            ("prompt", "style", "size"),
        ),
        _t("media_audio_play", ToolCategory.MEDIA, "Play an audio file", ("file_path", "volume")),
        _t(
            "media_audio_record",
            ToolCategory.MEDIA,
            "Record audio from microphone",
            ("duration", "format"),
        ),
        _t(
            "media_audio_transcribe",
            ToolCategory.MEDIA,
            "Transcribe audio to text",
            ("file_path", "language"),
        ),
        _t("media_video_play", ToolCategory.MEDIA, "Play a video file", ("file_path",)),
        _t(
            "media_video_extract",
            ToolCategory.MEDIA,
            "Extract frames or audio from video",
            ("file_path", "type", "timestamp"),
        ),
        _t(
            "media_svg_render",
            ToolCategory.MEDIA,
            "Render an SVG to PNG",
            ("svg_content", "width", "height"),
        ),
        _t(
            "media_color_analyze",
            ToolCategory.MEDIA,
            "Analyze color palette of an image",
            ("file_path",),
        ),
        _t(
            "media_metadata",
            ToolCategory.MEDIA,
            "Read and write media metadata/EXIF",
            ("file_path", "action"),
        ),
        _t(
            "media_compress",
            ToolCategory.MEDIA,
            "Compress image/audio/video file",
            ("file_path", "quality"),
        ),
    ),
)

NETWORK_TOOLS = Toolset(
    name="Network",
    category=ToolCategory.NETWORK,
    description="HTTP, DNS, WebSocket, SSH, and network diagnostics.",
    tools=(
        _t(
            "net_http",
            ToolCategory.NETWORK,
            "Make an HTTP request",
            ("method", "url", "headers", "body"),
        ),
        _t(
            "net_dns",
            ToolCategory.NETWORK,
            "DNS lookup and resolution",
            ("hostname", "record_type"),
        ),
        _t(
            "net_ping",
            ToolCategory.NETWORK,
            "Ping a host for latency/availability",
            ("host", "count"),
        ),
        _t("net_traceroute", ToolCategory.NETWORK, "Trace network route to a host", ("host",)),
        _t(
            "net_ssh",
            ToolCategory.NETWORK,
            "Execute a command over SSH",
            ("host", "command", "user"),
            destructive=True,
        ),
        _t("net_port_scan", ToolCategory.NETWORK, "Scan open ports on a host", ("host", "ports")),
        _t(
            "net_ssl_check",
            ToolCategory.NETWORK,
            "Check SSL/TLS certificate validity",
            ("hostname",),
        ),
        _t("net_bandwidth", ToolCategory.NETWORK, "Test network bandwidth/latency", ("target",)),
        _t("net_proxy", ToolCategory.NETWORK, "Configure and test HTTP proxy", ("proxy_url",)),
        _t(
            "net_grpc",
            ToolCategory.NETWORK,
            "Make a gRPC service call",
            ("service", "method", "request"),
        ),
    ),
)

SECURITY_TOOLS = Toolset(
    name="Security",
    category=ToolCategory.SECURITY,
    description="Security scanning, vulnerability detection, secret management, and compliance.",
    tools=(
        _t(
            "sec_secrets_scan",
            ToolCategory.SECURITY,
            "Scan codebase for hardcoded secrets",
            ("path",),
        ),
        _t(
            "sec_vuln_scan",
            ToolCategory.SECURITY,
            "Scan dependencies for known vulnerabilities",
            ("ecosystem",),
        ),
        _t(
            "sec_sast",
            ToolCategory.SECURITY,
            "Static application security testing",
            ("path", "rules"),
        ),
        _t("sec_dast", ToolCategory.SECURITY, "Dynamic application security testing", ("url",)),
        _t("sec_sbom", ToolCategory.SECURITY, "Generate software bill of materials", ("path",)),
        _t(
            "sec_license_check",
            ToolCategory.SECURITY,
            "Check dependency license compliance",
            ("path",),
        ),
        _t("sec_owasp_check", ToolCategory.SECURITY, "Check against OWASP Top 10", ("path",)),
        _t(
            "sec_permission_audit",
            ToolCategory.SECURITY,
            "Audit file and API permissions",
            ("path",),
        ),
        _t("sec_encrypt", ToolCategory.SECURITY, "Encrypt data with a key", ("data", "algorithm")),
        _t("sec_decrypt", ToolCategory.SECURITY, "Decrypt data with a key", ("data", "algorithm")),
        _t("sec_hash", ToolCategory.SECURITY, "Generate cryptographic hash", ("data", "algorithm")),
        _t("sec_jwt", ToolCategory.SECURITY, "Decode and validate JWT tokens", ("token",)),
        _t("sec_csrf", ToolCategory.SECURITY, "Generate/validate CSRF tokens", ("action", "token")),
    ),
)

AGENT_TOOLS = Toolset(
    name="Agent Orchestration",
    category=ToolCategory.AGENT,
    description="Agent spawning, task delegation, squad management, and fleet coordination.",
    tools=(
        _t(
            "agent_spawn",
            ToolCategory.AGENT,
            "Spawn a new sub-agent for a task",
            ("agent_type", "prompt"),
        ),
        _t(
            "agent_delegate",
            ToolCategory.AGENT,
            "Delegate a task to a specific agent",
            ("agent_id", "task"),
        ),
        _t(
            "agent_squad_create",
            ToolCategory.AGENT,
            "Create a new agent squad",
            ("name", "members", "domain"),
        ),
        _t(
            "agent_fanout",
            ToolCategory.AGENT,
            "Fan-out a task across multiple agents",
            ("task", "items", "agent_type"),
        ),
        _t(
            "agent_map_reduce",
            ToolCategory.AGENT,
            "Map-reduce a task across agents",
            ("map_fn", "reduce_fn", "items"),
        ),
        _t("agent_debate", ToolCategory.AGENT, "Run K-agent debate on a topic", ("proposal", "k")),
        _t(
            "agent_handoff",
            ToolCategory.AGENT,
            "Hand off context from one agent to another",
            ("from_agent", "to_agent"),
        ),
        _t("agent_fleet_status", ToolCategory.AGENT, "Get fleet-wide status and health", ()),
        _t(
            "agent_colony_start",
            ToolCategory.AGENT,
            "Start a persistent agent colony",
            ("workers", "squads"),
        ),
        _t(
            "agent_schedule", ToolCategory.AGENT, "Schedule a recurring agent task", ("job", "cron")
        ),
        _t(
            "agent_broadcast", ToolCategory.AGENT, "Broadcast a message to all agents", ("message",)
        ),
        _t(
            "agent_kill",
            ToolCategory.AGENT,
            "Terminate a running agent",
            ("agent_id",),
            destructive=True,
        ),
    ),
)

MEMORY_TOOLS = Toolset(
    name="Memory & Context",
    category=ToolCategory.MEMORY,
    description="Memory management, context optimization, knowledge graph, and compaction.",
    tools=(
        _t(
            "mem_save",
            ToolCategory.MEMORY,
            "Save information to persistent memory",
            ("content", "memory_type"),
        ),
        _t(
            "mem_recall",
            ToolCategory.MEMORY,
            "Recall information from memory",
            ("query", "memory_type"),
        ),
        _t(
            "mem_search",
            ToolCategory.MEMORY,
            "Semantic search across all memory layers",
            ("query", "layers"),
        ),
        _t(
            "mem_compact",
            ToolCategory.MEMORY,
            "Trigger context compaction",
            ("strategy", "target_tokens"),
        ),
        _t(
            "mem_prune",
            ToolCategory.MEMORY,
            "Prune old or low-priority memories",
            ("max_age_days",),
        ),
        _t(
            "mem_kg_query", ToolCategory.MEMORY, "Query the knowledge graph", ("query", "node_type")
        ),
        _t(
            "mem_kg_add",
            ToolCategory.MEMORY,
            "Add a node or edge to the knowledge graph",
            ("entity", "relation"),
        ),
        _t("mem_context_stats", ToolCategory.MEMORY, "Get context window usage statistics", ()),
        _t(
            "mem_forget",
            ToolCategory.MEMORY,
            "Remove specific memories",
            ("memory_ids",),
            destructive=True,
        ),
        _t("mem_consolidate", ToolCategory.MEMORY, "Consolidate related memories", ("topic",)),
    ),
)

SKILL_TOOLS = Toolset(
    name="Skill & Learning",
    category=ToolCategory.SKILL,
    description="Skill management, loading, creation, evolution, and evaluation.",
    tools=(
        _t("skill_list", ToolCategory.SKILL, "List all available skills", ("category",)),
        _t("skill_load", ToolCategory.SKILL, "Load a skill by name", ("name", "level")),
        _t(
            "skill_create",
            ToolCategory.SKILL,
            "Create a new skill from a template",
            ("name", "category", "content"),
        ),
        _t(
            "skill_evolve", ToolCategory.SKILL, "Trigger skill self-evolution", ("name", "strategy")
        ),
        _t(
            "skill_evaluate",
            ToolCategory.SKILL,
            "Evaluate skill quality and effectiveness",
            ("name", "benchmark"),
        ),
        _t(
            "skill_weave",
            ToolCategory.SKILL,
            "Compose multiple skills together",
            ("skill_ids", "strategy"),
        ),
        _t(
            "skill_search",
            ToolCategory.SKILL,
            "Search for skills by capability",
            ("query", "domain"),
        ),
        _t(
            "skill_import",
            ToolCategory.SKILL,
            "Import a skill from external source",
            ("source", "format"),
        ),
        _t("skill_export", ToolCategory.SKILL, "Export a skill for sharing", ("name", "format")),
        _t(
            "skill_benchmark", ToolCategory.SKILL, "Benchmark a skill against test cases", ("name",)
        ),
        _t(
            "skill_trace2skill",
            ToolCategory.SKILL,
            "Extract a skill from an execution trace",
            ("trace_id",),
        ),
    ),
)

OBSERVABILITY_TOOLS = Toolset(
    name="Observability",
    category=ToolCategory.OBSERVABILITY,
    description="Logging, metrics, tracing, dashboards, and alerting.",
    tools=(
        _t(
            "obs_log",
            ToolCategory.OBSERVABILITY,
            "Log an event or message",
            ("level", "message", "context"),
        ),
        _t(
            "obs_metric",
            ToolCategory.OBSERVABILITY,
            "Record a metric data point",
            ("name", "value", "tags"),
        ),
        _t(
            "obs_trace_start",
            ToolCategory.OBSERVABILITY,
            "Start a distributed trace span",
            ("name", "parent_id"),
        ),
        _t(
            "obs_trace_end",
            ToolCategory.OBSERVABILITY,
            "End a distributed trace span",
            ("span_id",),
        ),
        _t(
            "obs_dashboard",
            ToolCategory.OBSERVABILITY,
            "Render the observability dashboard",
            ("refresh",),
        ),
        _t(
            "obs_alert",
            ToolCategory.OBSERVABILITY,
            "Create or manage an alert rule",
            ("action", "rule"),
        ),
        _t("obs_health", ToolCategory.OBSERVABILITY, "Get system health status", ()),
        _t(
            "obs_audit", ToolCategory.OBSERVABILITY, "Query the audit log", ("filter", "time_range")
        ),
    ),
)

AUTOMATION_TOOLS = Toolset(
    name="Automation",
    category=ToolCategory.AUTOMATION,
    description="Goal management, scheduling, continuous mode, and workflow automation.",
    tools=(
        _t(
            "auto_goal_create",
            ToolCategory.AUTOMATION,
            "Create a new autonomous goal",
            ("title", "description", "criteria"),
        ),
        _t("auto_goal_list", ToolCategory.AUTOMATION, "List active goals", ("status",)),
        _t(
            "auto_goal_status",
            ToolCategory.AUTOMATION,
            "Get goal details and progress",
            ("goal_id",),
        ),
        _t(
            "auto_continuous_start",
            ToolCategory.AUTOMATION,
            "Start continuous autonomous mode",
            ("interval", "until"),
        ),
        _t("auto_continuous_stop", ToolCategory.AUTOMATION, "Stop continuous autonomous mode", ()),
        _t(
            "auto_schedule",
            ToolCategory.AUTOMATION,
            "Schedule a recurring autonomous task",
            ("cron", "task"),
        ),
        _t(
            "auto_webhook",
            ToolCategory.AUTOMATION,
            "Register an event-driven webhook trigger",
            ("event", "task"),
        ),
        _t(
            "auto_workflow",
            ToolCategory.AUTOMATION,
            "Run a predefined workflow",
            ("workflow_id", "params"),
        ),
        _t(
            "auto_checkpoint",
            ToolCategory.AUTOMATION,
            "Create or restore a session checkpoint",
            ("action", "checkpoint_id"),
        ),
        _t(
            "auto_rollback",
            ToolCategory.AUTOMATION,
            "Rollback to a previous state",
            ("checkpoint_id",),
            destructive=True,
        ),
    ),
)

COMMUNICATION_TOOLS = Toolset(
    name="Communication",
    category=ToolCategory.COMMUNICATION,
    description="Slack, email, Discord, and other communication channel integrations.",
    tools=(
        _t(
            "comm_slack_send",
            ToolCategory.COMMUNICATION,
            "Send a message to a Slack channel",
            ("channel", "message"),
        ),
        _t(
            "comm_slack_thread",
            ToolCategory.COMMUNICATION,
            "Reply in a Slack thread",
            ("channel", "thread_ts", "message"),
        ),
        _t(
            "comm_email_send",
            ToolCategory.COMMUNICATION,
            "Send an email",
            ("to", "subject", "body"),
        ),
        _t(
            "comm_discord_send",
            ToolCategory.COMMUNICATION,
            "Send a message to Discord",
            ("channel", "message"),
        ),
        _t(
            "comm_teams_send",
            ToolCategory.COMMUNICATION,
            "Send a message to Microsoft Teams",
            ("channel", "message"),
        ),
        _t(
            "comm_notify",
            ToolCategory.COMMUNICATION,
            "Send a desktop notification",
            ("title", "message"),
        ),
        _t(
            "comm_webhook",
            ToolCategory.COMMUNICATION,
            "Call an outgoing webhook",
            ("url", "payload"),
        ),
        _t(
            "comm_whatsapp",
            ToolCategory.COMMUNICATION,
            "Send a WhatsApp message",
            ("to", "message"),
        ),
    ),
)

MCP_TOOLS = Toolset(
    name="MCP Management",
    category=ToolCategory.MCP,
    description="Model Context Protocol server/client management and discovery.",
    tools=(
        _t("mcp_server_start", ToolCategory.MCP, "Start an MCP server", ("name", "config")),
        _t("mcp_server_stop", ToolCategory.MCP, "Stop an MCP server", ("name",)),
        _t("mcp_list_servers", ToolCategory.MCP, "List running MCP servers", ()),
        _t("mcp_list_tools", ToolCategory.MCP, "List tools exposed by an MCP server", ("server",)),
        _t(
            "mcp_call_tool",
            ToolCategory.MCP,
            "Call a tool on an MCP server",
            ("server", "tool", "args"),
        ),
        _t("mcp_discover", ToolCategory.MCP, "Discover available MCP servers", ("registry_url",)),
        _t("mcp_install", ToolCategory.MCP, "Install an MCP server plugin", ("plugin_name",)),
        _t(
            "mcp_security_scan",
            ToolCategory.MCP,
            "Scan MCP servers for security issues",
            ("server",),
        ),
    ),
)

VOICE_TOOLS = Toolset(
    name="Voice & Audio",
    category=ToolCategory.VOICE,
    description="Voice input/output, TTS, STT, sound effects, and voice packs.",
    tools=(
        _t("voice_speak", ToolCategory.VOICE, "Convert text to speech and play", ("text", "voice")),
        _t(
            "voice_listen",
            ToolCategory.VOICE,
            "Listen and transcribe speech to text",
            ("duration", "language"),
        ),
        _t("voice_pack_set", ToolCategory.VOICE, "Set active voice/sound pack", ("pack_name",)),
        _t("voice_pack_list", ToolCategory.VOICE, "List available voice packs", ()),
        _t(
            "voice_sound_play",
            ToolCategory.VOICE,
            "Play a sound effect for an event",
            ("event", "pack"),
        ),
        _t("voice_volume", ToolCategory.VOICE, "Get or set audio volume", ("level",)),
        _t(
            "voice_dictation_start",
            ToolCategory.VOICE,
            "Start continuous dictation mode",
            ("language",),
        ),
        _t("voice_dictation_stop", ToolCategory.VOICE, "Stop continuous dictation mode", ()),
    ),
)

UI_TOOLS = Toolset(
    name="UI & Terminal",
    category=ToolCategory.UI,
    description="Terminal UI rendering, themes, keybindings, and display formatting.",
    tools=(
        _t("ui_theme_set", ToolCategory.UI, "Set the active UI theme", ("theme_name",)),
        _t("ui_theme_list", ToolCategory.UI, "List available UI themes", ()),
        _t("ui_banner", ToolCategory.UI, "Display the welcome banner", ("style",)),
        _t("ui_keybinding_set", ToolCategory.UI, "Set a keybinding", ("key", "action")),
        _t("ui_keybinding_list", ToolCategory.UI, "List all keybindings", ()),
        _t("ui_render_markdown", ToolCategory.UI, "Render markdown in the terminal", ("content",)),
        _t(
            "ui_progress_bar",
            ToolCategory.UI,
            "Display a progress bar",
            ("current", "total", "label"),
        ),
        _t("ui_table", ToolCategory.UI, "Display a formatted table", ("headers", "rows")),
        _t("ui_diff_view", ToolCategory.UI, "Display a side-by-side diff", ("old", "new")),
    ),
)


# ── Registry ────────────────────────────────────────────────────────────

ALL_TOOLSETS: tuple[Toolset, ...] = (
    FILESYSTEM_TOOLS,
    CODE_TOOLS,
    SEARCH_TOOLS,
    SHELL_TOOLS,
    GIT_TOOLS,
    WEB_TOOLS,
    DATABASE_TOOLS,
    DOCUMENT_TOOLS,
    MEDIA_TOOLS,
    NETWORK_TOOLS,
    SECURITY_TOOLS,
    AGENT_TOOLS,
    MEMORY_TOOLS,
    SKILL_TOOLS,
    OBSERVABILITY_TOOLS,
    AUTOMATION_TOOLS,
    COMMUNICATION_TOOLS,
    MCP_TOOLS,
    VOICE_TOOLS,
    UI_TOOLS,
)


class ToolRegistry:
    """Centralized registry of all Lyra tools across 20 toolsets.

    Provides:
    - Tool lookup by name
    - Category-based browsing
    - Keyword search
    - Progressive disclosure filtering
    - Dependency resolution
    - Destructive tool flagging
    """

    def __init__(self, toolsets: tuple[Toolset, ...] | None = None) -> None:
        self._toolsets = toolsets or ALL_TOOLSETS
        self._by_name: dict[str, ToolManifest] = {}
        self._by_category: dict[ToolCategory, list[ToolManifest]] = {}
        self._destructive: set[str] = set()
        self._build_index()

    def _build_index(self) -> None:
        for ts in self._toolsets:
            for tool in ts.tools:
                self._by_name[tool.name] = tool
                self._by_category.setdefault(tool.category, []).append(tool)
                if tool.is_destructive:
                    self._destructive.add(tool.name)

    # ── Lookup ────────────────────────────────────────────────────────

    def get(self, name: str) -> ToolManifest | None:
        """Get a tool by name."""
        return self._by_name.get(name)

    def get_toolset(self, category: ToolCategory) -> Toolset | None:
        """Get a complete toolset by category."""
        for ts in self._toolsets:
            if ts.category == category:
                return ts
        return None

    def list_categories(self) -> tuple[ToolCategory, ...]:
        """List all tool categories."""
        return tuple(self._by_category.keys())

    def list_tools(self, category: ToolCategory | None = None) -> tuple[ToolManifest, ...]:
        """List tools, optionally filtered by category."""
        if category:
            return tuple(self._by_category.get(category, []))
        return tuple(self._by_name.values())

    # ── Search ─────────────────────────────────────────────────────────

    def search(self, query: str) -> list[ToolManifest]:
        """Search tools by name, description, or tags."""
        q = query.lower()
        scored: list[tuple[int, ToolManifest]] = []
        for tool in self._by_name.values():
            score = 0
            if q in tool.name.lower():
                score += 3
            if q in tool.description.lower():
                score += 2
            if any(q in tag.lower() for tag in tool.tags):
                score += 1
            if score > 0:
                scored.append((score, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored]

    # ── Safety ─────────────────────────────────────────────────────────

    def is_destructive(self, name: str) -> bool:
        """Check if a tool is marked as destructive."""
        return name in self._destructive

    def list_destructive(self) -> tuple[ToolManifest, ...]:
        """List all destructive tools."""
        return tuple(self._by_name[n] for n in self._destructive if n in self._by_name)

    # ── Disclosure ─────────────────────────────────────────────────────

    def get_disclosure(self, name: str, level: ToolDisclosureLevel) -> ToolManifest | None:
        """Get a tool manifest at a specific disclosure level."""
        tool = self.get(name)
        if tool is None:
            return None
        if level.value <= tool.disclosure.value:
            return tool
        return None  # Tool not available at this disclosure level

    # ── Dependencies ───────────────────────────────────────────────────

    def resolve_dependencies(self, name: str) -> tuple[ToolManifest, ...]:
        """Resolve the full dependency chain for a tool."""
        seen: set[str] = set()
        result: list[ToolManifest] = []

        def _resolve(n: str) -> None:
            if n in seen:
                return
            seen.add(n)
            tool = self.get(n)
            if tool is None:
                return
            for dep in tool.dependencies:
                _resolve(dep)
            result.append(tool)

        _resolve(name)
        return tuple(result)

    # ── Stats ──────────────────────────────────────────────────────────

    @property
    def total_tools(self) -> int:
        return len(self._by_name)

    @property
    def total_toolsets(self) -> int:
        return len(self._toolsets)

    @property
    def destructive_count(self) -> int:
        return len(self._destructive)

    def stats(self) -> dict:
        """Return comprehensive registry statistics."""
        return {
            "total_tools": self.total_tools,
            "total_toolsets": self.total_toolsets,
            "destructive_tools": self.destructive_count,
            "tools_per_category": {
                cat.value: len(tools) for cat, tools in self._by_category.items()
            },
        }


# Singleton instance
tool_registry = ToolRegistry()
