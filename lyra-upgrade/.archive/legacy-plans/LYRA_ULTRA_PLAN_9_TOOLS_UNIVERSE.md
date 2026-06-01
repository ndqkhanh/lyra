# LYRA ULTRA PLAN 9: Tools Universe — Complete Blueprint

**Version:** 1.0.0 | **Status:** In Progress | **Created:** 2026-05-25
**Parent Plan:** [LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md](LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md)

---

## Overview

Build Lyra's complete tools universe — 200+ tools across 20 toolsets, covering every domain from file operations to browser automation, from database management to audio/video processing. Tools are organized into a progressive disclosure system so agents only see relevant tools based on the current task.

---

## Part 1: Tools Architecture

### 1.1 Tool Definition Standard

```python
@tool(
    name="file_read",
    description="Read a file from the local filesystem",
    category="filesystem",
    requires_permission="read",
    token_cost_estimate=100,
    parallel_safe=True,
)
async def file_read(path: str, offset: int = 0, limit: int = 2000) -> ToolResult:
    """Read contents of a file with optional offset and line limit."""
    ...
```

### 1.2 Progressive Tool Disclosure

| Level | Description | Token Budget | When Visible |
|-------|-------------|-------------|--------------|
| L1 | Tool name + one-line description | ~30/tool | Always (all tools) |
| L2 | Full parameter schema + examples | ~200/tool | When task domain matches |
| L3 | Detailed usage guide + edge cases | ~500/tool | When tool is invoked |

### 1.3 Tool Categories

| Category | Tools | Always Visible |
|----------|-------|---------------|
| `filesystem` | 12 | Yes |
| `code` | 18 | Yes |
| `search` | 10 | Yes |
| `shell` | 8 | Permission-gated |
| `git` | 14 | Auto-detect |
| `web` | 12 | On-demand |
| `browser` | 8 | On-demand |
| `database` | 14 | On-demand |
| `api` | 10 | On-demand |
| `media` | 12 | On-demand |
| `document` | 14 | On-demand |
| `network` | 10 | On-demand |
| `security` | 10 | Permission-gated |
| `agent` | 12 | Always |
| `memory` | 10 | Always |
| `skill` | 8 | Always |
| `mcp` | 6 | On-demand |
| `observability` | 8 | Always |
| `automation` | 10 | Permission-gated |
| `communication` | 10 | On-demand |

---

## Part 2: Complete Tool Catalog (200+ Tools)

### 2.1 Filesystem Tools (12)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `file_read` | Read file contents with offset/limit | Claude Code |
| `file_write` | Write/create file (atomic: temp + rename) | Claude Code |
| `file_edit` | Exact string replacement in files | Claude Code |
| `file_glob` | Pattern-based file search | Claude Code |
| `file_grep` | Regex search across files | Claude Code |
| `file_list` | List directory contents recursively | Claude Code |
| `file_info` | File metadata (size, mtime, type, encoding) | Hermes-agent |
| `file_move` | Move/rename file or directory | Hermes-agent |
| `file_copy` | Copy file or directory recursively | Hermes-agent |
| `file_delete` | Delete file or directory (with trash support) | Hermes-agent |
| `file_watch` | Watch file/directory for changes (inotify/FSEvents) | New |
| `file_diff` | Compute diff between two files or directories | Hermes-agent |

### 2.2 Code Tools (18)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `code_analyze` | AST-based code analysis (tree-sitter) | CodeGraph |
| `code_lsp_goto_def` | Go to definition via LSP | Claude Code |
| `code_lsp_references` | Find all references via LSP | Claude Code |
| `code_lsp_hover` | Type info and documentation via LSP | Claude Code |
| `code_lsp_diagnostics` | Linter errors/warnings via LSP | Claude Code |
| `code_lsp_rename` | Safe symbol rename across project | Claude Code |
| `code_format` | Format code (ruff, prettier, gofmt, etc.) | Claude Code |
| `code_lint` | Run linter and return diagnostics | Claude Code |
| `code_typecheck` | Run type checker (mypy, tsc, etc.) | Claude Code |
| `code_test` | Run test suite with coverage report | Claude Code |
| `code_benchmark` | Run benchmarks and compare | Hermes-agent |
| `code_dependency_graph` | Build import/call dependency graph | CodeGraph |
| `code_symbol_search` | Search for symbols across codebase | CodeGraph |
| `code_complexity` | Cyclomatic/cognitive complexity analysis | New |
| `code_dead_code` | Detect unused code (vulture, ts-prune) | Hermes-agent |
| `code_api_extract` | Extract API surface from codebase | New |
| `code_scaffold` | Generate project scaffold from template | Hermes-agent |
| `code_migrate` | Automated code migration (codemods) | New |

### 2.3 Search Tools (10)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `search_code` | Semantic code search (embeddings + BM25) | Claude Code |
| `search_docs` | Search documentation (local + web) | Claude Code |
| `search_web` | Web search (Brave/Google/SerpAPI) | Claude Code |
| `search_academic` | Academic search (arXiv, Semantic Scholar, PubMed) | Lyra Research |
| `search_github` | GitHub code/repo/issue search | Claude Code |
| `search_memory` | Search Lyra's memory system (hybrid retrieval) | Lyra Memory |
| `search_skill` | Search across installed skills | Lyra Skills |
| `search_knowledge_graph` | Query the knowledge graph | Graphify |
| `search_package` | Search package registries (npm, PyPI, crates.io) | Hermes-agent |
| `search_history` | Search session/command history | Claude Code |

### 2.4 Shell Tools (8)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `shell_run` | Execute shell command (sandboxed) | Claude Code |
| `shell_run_background` | Execute in background, return task ID | Claude Code |
| `shell_stream` | Stream command output in real-time | Hermes-agent |
| `shell_interactive` | Interactive shell session (PTY) | Hermes-agent |
| `shell_env` | Manage environment variables per session | Hermes-agent |
| `shell_script` | Execute multi-line script (heredoc style) | Claude Code |
| `shell_status` | Check background task status/output | Claude Code |
| `shell_kill` | Kill running background task | Claude Code |

### 2.5 Git Tools (14)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `git_status` | Working tree status | Claude Code |
| `git_diff` | View staged/unstaged changes | Claude Code |
| `git_diff_staged` | View staged changes only | Claude Code |
| `git_log` | Commit history with formatting | Claude Code |
| `git_show` | Show commit details | Claude Code |
| `git_blame` | Line-by-line authorship | Claude Code |
| `git_add` | Stage files | Claude Code |
| `git_commit` | Create commit with message | Claude Code |
| `git_branch` | List/create/switch branches | Claude Code |
| `git_checkout` | Checkout branch or file | Claude Code |
| `git_pull` | Pull from remote | Claude Code |
| `git_push` | Push to remote | Claude Code |
| `git_stash` | Stash/unstash changes | Claude Code |
| `git_worktree` | Manage git worktrees for subagent isolation | Claude Code |

### 2.6 Web & Browser Tools (20)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `web_fetch` | Fetch URL content (HTML → Markdown) | Claude Code |
| `web_search` | Web search with domain filters | Claude Code |
| `browser_navigate` | Navigate browser to URL | Claude Code |
| `browser_click` | Click element by selector | Claude Code |
| `browser_type` | Type text into element | Claude Code |
| `browser_screenshot` | Take screenshot of page/element | Claude Code |
| `browser_evaluate` | Execute JavaScript in page | Claude Code |
| `browser_extract` | Extract structured data from page | Hermes-agent |
| `browser_fill_form` | Fill multi-field form | Hermes-agent |
| `browser_pdf` | Print page to PDF | Hermes-agent |
| `web_api_call` | Make HTTP request (GET/POST/PUT/DELETE) | Hermes-agent |
| `web_api_graphql` | Make GraphQL query | Hermes-agent |
| `web_websocket` | WebSocket client connection | Hermes-agent |
| `web_sse` | Server-Sent Events client | Hermes-agent |
| `web_download` | Download file with progress | Hermes-agent |
| `web_upload` | Upload file with progress | Hermes-agent |
| `web_rss` | Fetch and parse RSS/Atom feeds | Hermes-agent |
| `web_sitemap` | Parse sitemap.xml | Hermes-agent |
| `web_screenshot_full` | Full-page screenshot | Hermes-agent |
| `web_compare` | Visual regression comparison | New |

### 2.7 Database Tools (14)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `db_connect` | Connect to database (Postgres/MySQL/SQLite/Mongo/Redis) | Hermes-agent |
| `db_query` | Execute read-only SQL query | Hermes-agent |
| `db_execute` | Execute write SQL (permission-gated) | Hermes-agent |
| `db_schema` | Introspect database schema | Hermes-agent |
| `db_migrate` | Run database migrations | Hermes-agent |
| `db_seed` | Seed database with test data | Hermes-agent |
| `db_explain` | EXPLAIN query plan | Hermes-agent |
| `db_backup` | Create database backup | Hermes-agent |
| `db_restore` | Restore from backup | Hermes-agent |
| `db_monitor` | Show active queries, locks, stats | Hermes-agent |
| `db_erd` | Generate entity-relationship diagram | New |
| `db_optimize_index` | Suggest missing indexes | New |
| `db_validate` | Validate data integrity constraints | New |
| `db_vector_search` | Vector similarity search (pgvector, Chroma) | Lyra Memory |

### 2.8 Document Tools (14)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `doc_read` | Read document (PDF, DOCX, XLSX, PPTX, ODT) | Claude Code |
| `doc_create` | Create document from template | Claude Code |
| `doc_convert` | Convert between document formats | Hermes-agent |
| `doc_merge` | Merge multiple documents | Hermes-agent |
| `doc_split` | Split document into sections | Hermes-agent |
| `doc_extract_text` | Extract text content | Hermes-agent |
| `doc_extract_tables` | Extract tables to CSV/JSON | Hermes-agent |
| `doc_extract_images` | Extract embedded images | Hermes-agent |
| `doc_ocr` | OCR on images/scanned PDFs | Hermes-agent |
| `doc_fill_form` | Fill PDF form fields | Hermes-agent |
| `doc_sign` | Add digital signature | Hermes-agent |
| `doc_redact` | Redact sensitive information | New |
| `doc_compare` | Compare two documents (diff) | Hermes-agent |
| `doc_summarize` | AI-powered document summary | Hermes-agent |

### 2.9 Media Tools (12)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `media_info` | Media file metadata (FFprobe) | Hermes-agent |
| `media_convert` | Convert media format (FFmpeg) | Hermes-agent |
| `media_compress` | Compress media with quality target | Hermes-agent |
| `media_trim` | Trim/cut media segment | Hermes-agent |
| `media_concat` | Concatenate media files | Hermes-agent |
| `media_extract_audio` | Extract audio from video | Hermes-agent |
| `media_generate_thumbnail` | Generate video thumbnail grid | Hermes-agent |
| `media_subtitle` | Extract/burn subtitles | Hermes-agent |
| `media_screenshot` | Capture frame at timestamp | Hermes-agent |
| `media_transcribe` | Speech-to-text transcription | Hermes-agent |
| `media_gif` | Create GIF from video segment | New |
| `media_watermark` | Add text/image watermark | Hermes-agent |

### 2.10 Network Tools (10)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `net_curl` | Make HTTP request with full control | Hermes-agent |
| `net_dns` | DNS lookup (A, AAAA, MX, TXT, etc.) | Hermes-agent |
| `net_ping` | ICMP/TCP ping with latency stats | Hermes-agent |
| `net_traceroute` | Trace network path | Hermes-agent |
| `net_ssl_check` | SSL/TLS certificate validation | Hermes-agent |
| `net_port_scan` | Port scanning (permission-gated) | Hermes-agent |
| `net_headers` | Check HTTP security headers | Hermes-agent |
| `net_whois` | WHOIS domain lookup | Hermes-agent |
| `net_speedtest` | Network speed test | Hermes-agent |
| `net_websocket_test` | WebSocket connectivity test | Hermes-agent |

### 2.11 Security Tools (10)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `sec_secrets_scan` | Scan for hardcoded secrets (truffleHog, gitleaks) | Claude Code |
| `sec_sast` | Static Application Security Testing (semgrep) | ECC |
| `sec_dependency_scan` | Check dependencies for CVEs (npm audit, pip-audit) | Claude Code |
| `sec_sql_injection` | Test for SQL injection vectors | ECC |
| `sec_xss` | Test for XSS vulnerabilities | ECC |
| `sec_csrf` | Check CSRF protection | ECC |
| `sec_headers` | Security header audit (CSP, HSTS, etc.) | Hermes-agent |
| `sec_auth_check` | Authentication flow validation | ECC |
| `sec_threat_model` | Generate threat model (STRIDE) | Claude Code |
| `sec_pentest` | Automated penetration test (permission-gated) | ECC |

### 2.12 Agent & Orchestration Tools (12)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `agent_spawn` | Spawn subagent with task description | Claude Code |
| `agent_delegate` | Delegate task to specialist agent | Claude Code |
| `agent_team_create` | Create agent team with roles (PM/Eng/QA/etc.) | Claude Code |
| `agent_fleet_status` | View fleet status (agents, squads, metrics) | Lyra Fleet |
| `agent_fan_out` | Fan-out task to N parallel agents | Lyra Fleet |
| `agent_squad_form` | Form a squad for coordinated work | Lyra Fleet |
| `agent_interrupt` | Interrupt running agent | Claude Code |
| `agent_converse` | Inter-agent conversation (via RecursiveMAS) | Lyra Colony |
| `agent_consensus` | Multi-agent voting/consensus | Lyra Colony |
| `agent_worktree` | Create isolated worktree for subagent | Claude Code |
| `agent_timeline` | View agent execution timeline | Claude Code |
| `agent_handoff` | Hand off context between agents | Claude Code |

### 2.13 Memory & Context Tools (10)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `memory_store` | Store fact/memory with metadata | Lyra Memory |
| `memory_recall` | Recall relevant memories (hybrid BM25+vector) | Lyra Memory |
| `memory_forget` | Remove/expire stored memory | Lyra Memory |
| `memory_consolidate` | Trigger STM → LTM consolidation | Lyra Memory |
| `memory_search_timeline` | Chronological memory search | MemPalace |
| `memory_kg_add` | Add triple to knowledge graph | MemPalace |
| `memory_kg_query` | Query knowledge graph with temporal filter | MemPalace |
| `memory_stats` | Memory usage statistics by level | Lyra Memory |
| `context_compact` | Trigger context compaction | Claude Code |
| `context_budget` | Show context window usage | Claude Code |

### 2.14 Skill & Learning Tools (8)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `skill_list` | List available skills with metadata | Claude Code |
| `skill_get` | Get full skill content | Claude Code |
| `skill_invoke` | Invoke skill by name | Claude Code |
| `skill_create` | Create new skill from template | Lyra Skills |
| `skill_install` | Install skill from registry/URL | Claude Code |
| `skill_update` | Update installed skill | Claude Code |
| `skill_evaluate` | Run skill evaluation suite | Lyra Skills |
| `skill_evolve` | Trigger skill optimization | Lyra Skills |

### 2.15 Observability Tools (8)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `obs_trace` | View execution trace for session | Claude Code |
| `obs_metrics` | View session metrics (tokens, cost, time) | Claude Code |
| `obs_burn_report` | Token burn report by category (13 categories) | Claude Code |
| `obs_cost_report` | Cost report by model/provider | Claude Code |
| `obs_hir_dump` | Export HIR event stream | Lyra HIR |
| `obs_replay` | Replay session from HIR events | Lyra HIR |
| `obs_audit_log` | View permission audit log | Claude Code |
| `obs_health` | System health dashboard | Claude Code |

### 2.16 Automation Tools (10)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `auto_goal_set` | Set autonomous goal with criteria | Claude Code |
| `auto_goal_status` | Check goal progress | Claude Code |
| `auto_goal_list` | List active/completed goals | Claude Code |
| `auto_schedule` | Schedule recurring task (cron syntax) | Claude Code |
| `auto_schedule_list` | List scheduled tasks | Claude Code |
| `auto_schedule_delete` | Delete scheduled task | Claude Code |
| `auto_hook_create` | Create hook with event + matcher + handler | Claude Code |
| `auto_hook_list` | List configured hooks | Claude Code |
| `auto_continuous_start` | Start continuous autonomous mode | Continuous-Claude |
| `auto_continuous_status` | Check continuous mode status | Continuous-Claude |

### 2.17 Communication Tools (10)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `comm_slack_send` | Send Slack message | Hermes-agent |
| `comm_slack_thread` | Reply in Slack thread | Hermes-agent |
| `comm_email_send` | Send email (SMTP) | Hermes-agent |
| `comm_email_read` | Read recent emails (IMAP) | Hermes-agent |
| `comm_discord_send` | Send Discord message | Hermes-agent |
| `comm_teams_send` | Send Microsoft Teams message | Hermes-agent |
| `comm_telegram_send` | Send Telegram message | Hermes-agent |
| `comm_notify_desktop` | Send desktop notification | PeonPing |
| `comm_notify_mobile` | Send mobile push notification | PeonPing |
| `comm_gh_issue` | Create/comment on GitHub issues | Claude Code |

### 2.18 MCP Management Tools (6)

| Tool | Description | Inspired By |
|------|-------------|-------------|
| `mcp_list_servers` | List connected MCP servers | Claude Code |
| `mcp_list_tools` | List tools from MCP server | Claude Code |
| `mcp_call_tool` | Call tool on MCP server | Claude Code |
| `mcp_add_server` | Add MCP server configuration | Claude Code |
| `mcp_remove_server` | Remove MCP server | Claude Code |
| `mcp_search_tools` | Search across all MCP server tools | Claude Code |

---

## Part 3: Implementation Roadmap

### Phase 9.1: Core Tools (Weeks 1-3)
- [ ] Filesystem tools (12) — Always needed
- [ ] Shell tools (8) — Core execution
- [ ] Git tools (14) — Development workflow

### Phase 9.2: Code & Search (Weeks 4-6)
- [ ] Code tools (18) — LSP integration, analysis
- [ ] Search tools (10) — Multi-source search
- [ ] Agent tools (12) — Subagent orchestration

### Phase 9.3: Web, Database & Document (Weeks 7-10)
- [ ] Web & Browser tools (20) — Playwright integration
- [ ] Database tools (14) — Multi-database support
- [ ] Document tools (14) — Multi-format processing

### Phase 9.4: Media, Network & Security (Weeks 11-14)
- [ ] Media tools (12) — FFmpeg integration
- [ ] Network tools (10) — Diagnostics
- [ ] Security tools (10) — SAST/DAST scanning

### Phase 9.5: Automation & Communication (Weeks 15-18)
- [ ] Automation tools (10) — Goals, schedules, hooks
- [ ] Communication tools (10) — Multi-platform messaging
- [ ] MCP Management tools (6) — Server lifecycle
- [ ] Memory & Skill tools (18) — Already partially built

---

## Part 4: Reference & Inspiration

| Source | Tools Count | Key Patterns Adopted |
|--------|------------|---------------------|
| [Hermes-agent](https://github.com/nousresearch/hermes-agent) | 70+ tools, 28 toolsets | Toolset organization, multi-backend terminal, messaging gateway, learning loop |
| [Claude Code Tools](https://code.claude.com/docs/en/tools-reference) | ~20 tools | Read/Write/Edit/Glob/Grep/Bash pattern, LSP tools, agent tools |
| [DCI-Agent](https://github.com/DCI-Agent/DCI-Agent-Lite) | Zero-index retrieval | Grep/find over raw corpus — no vectors needed |
| [OpenCode](https://github.com/anomalyco/opencode) | 20+ crates | Tool modularity, per-workflow model binding |
| [CodeGraph](https://github.com/colbymchenry/codegraph) | 9 MCP tools | Pre-indexed semantic search, framework-aware routes |
| [CLI-Anything](https://github.com/HKUDS/CLI-Anything) | Universal --json | Structured output for every tool |
| [Continuous-Claude](https://github.com/AnandChowdhary/continuous-claude) | Autonomous loop | Continuous autonomous mode pattern |
