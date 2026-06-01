# Tools and Plugins Catalog: Comprehensive Analysis for Lyra Implementation

**Research Date:** 2026-05-30  
**Target:** Phase 3 - Tool System & MCP Integration  
**Status:** P0 Priority

## Executive Summary

This document provides a comprehensive catalog of tools and plugins from Hermes-agent and Claude Code, analyzing their architectures, interfaces, and implementation patterns for integration into Lyra's research engine with MCP (Model Context Protocol) support.

### Key Findings

1. **Hermes-agent**: 73+ tools across 15 toolsets with dynamic plugin architecture
2. **Claude Code**: 45+ built-in tools with MCP server integration
3. **MCP Protocol**: Standardized tool registration, discovery, and invocation
4. **Tool Search**: Progressive disclosure pattern for scaling to 500+ tools
5. **Plugin Architecture**: Registry-based with hot-reload and sandboxing

### Architecture Comparison

| Aspect | Hermes-agent | Claude Code | Recommendation for Lyra |
|--------|--------------|-------------|------------------------|
| Tool Count | 73+ tools | 45+ tools | Start with 30-40 core tools |
| Plugin System | Registry + dynamic loading | MCP servers | Hybrid: Registry + MCP |
| Tool Discovery | Toolset-based | MCP list + tool search | Progressive disclosure |
| Sandboxing | Process isolation | Permission system | Both approaches |
| Async Support | Mixed sync/async | Async-first | Async-first with sync bridge |

---

## Table of Contents

1. [Hermes-agent Tools Catalog](#hermes-agent-tools-catalog)
2. [Claude Code Tools Catalog](#claude-code-tools-catalog)
3. [MCP Protocol Specification](#mcp-protocol-specification)
4. [Tool Interface Patterns](#tool-interface-patterns)
5. [Plugin Architecture Design](#plugin-architecture-design)
6. [Tool Composition Patterns](#tool-composition-patterns)
7. [Implementation Roadmap](#implementation-roadmap)
8. [Architecture Diagrams](#architecture-diagrams)

---

## 1. Hermes-agent Tools Catalog

### 1.1 Overview

Hermes-agent implements a **registry-based tool system** with 73+ tools organized into 15 toolsets. The architecture supports:

- **Dynamic tool registration** at module import time
- **Toolset composition** (toolsets can include other toolsets)
- **Availability checking** via `check_fn` with 30-second TTL cache
- **Async/sync bridge** for mixed execution models
- **Plugin discovery** via AST parsing to find self-registering modules

### 1.2 Core Toolsets

#### Web Tools (`web` toolset)
- **web_search**: Search via Exa, Parallel, Tavily, Firecrawl, SearXNG, Brave, DuckDuckGo
- **web_extract**: Content extraction with LLM summarization (chunked processing for large content)

**Key Features:**
- Backend abstraction layer (7 providers)
- Automatic LLM summarization for content >5KB
- Chunked processing for content >500KB (parallel summarization + synthesis)
- SSRF protection and URL safety validation
- Base64 image removal to reduce token usage

**Interface Pattern:**
```python
def web_search_tool(query: str, limit: int = 5) -> str:
    """Returns JSON: {"success": bool, "data": {"web": [...]}}"""
    
async def web_extract_tool(
    urls: List[str],
    format: str = None,
    use_llm_processing: bool = True,
    model: Optional[str] = None,
    min_length: int = 5000
) -> str:
    """Returns JSON: {"results": [{"url", "title", "content", "error"}]}"""
```

#### Terminal Tools (`terminal` toolset)
- **terminal**: Execute shell commands with multiple backends
- **process**: Process management (list, kill, monitor)

**Backend Support:**
- Local shell (bash/zsh)
- Docker containers
- SSH remote execution
- Singularity containers
- Modal serverless
- Daytona cloud workspaces

**Security Features:**
- Command approval system
- Dangerous command detection
- Working directory restrictions
- Environment variable isolation

#### File Tools (`file` toolset)
- **read_file**: Read with encoding detection
- **write_file**: Write with backup
- **patch**: Fuzzy-match patching (handles whitespace/indentation drift)
- **search_files**: Content search with ripgrep

**Patch Tool Innovation:**
```python
# Handles imperfect matches - key differentiator from Claude Code's Edit
def patch(file_path: str, old_content: str, new_content: str) -> str:
    """Fuzzy matching allows for minor formatting differences"""
```

#### Browser Tools (`browser` toolset)
- **browser_navigate**: Navigate to URL
- **browser_snapshot**: Screenshot + DOM snapshot
- **browser_click**: Click elements
- **browser_type**: Type text
- **browser_scroll**: Scroll page
- **browser_back**: Navigate back
- **browser_press**: Press keys
- **browser_get_images**: Extract images
- **browser_vision**: Vision analysis of page
- **browser_console**: Execute JavaScript
- **browser_cdp**: Chrome DevTools Protocol access
- **browser_dialog**: Handle dialogs

**Architecture:**
- Playwright-based
- Persistent browser context
- Vision integration for element detection
- CDP for advanced automation

#### Skills System (`skills` toolset)
- **skills_list**: List available skills
- **skill_view**: View skill content
- **skill_manage**: Create/edit/delete skills

**Skills Hub Integration:**
- Compatible with agentskills.io standard
- Markdown-based skill documents
- Automatic skill creation after complex tasks
- Self-improvement during use

#### Memory Tools (`memory` toolset)
- **memory**: Persistent memory across sessions

**Providers:**
- Honcho (dialectic user modeling)
- Mem0, Supermemory, Holographic
- ByteRover, RetainDB, Hindsight, OpenViking

#### Vision Tools (`vision` toolset)
- **vision_analyze**: Image analysis

#### Image Generation (`image_gen` toolset)
- **image_generate**: Text-to-image generation

#### Video Tools (`video` and `video_gen` toolsets)
- **video_analyze**: Video understanding (opt-in)
- **video_generate**: Text-to-video and image-to-video

#### Text-to-Speech (`tts` toolset)
- **text_to_speech**: Convert text to audio

#### Planning Tools (`todo` toolset)
- **todo**: Task planning and tracking

#### Session Search (`session_search` toolset)
- **session_search**: Search past conversations with FTS5 + LLM summarization

#### Clarification (`clarify` toolset)
- **clarify**: Ask user questions (multiple choice, open-ended, confirmation)

#### Code Execution (`code_execution` toolset)
- **execute_code**: Run Python scripts with RPC tool calling

#### Delegation (`delegation` toolset)
- **delegate_task**: Spawn subagents with isolated context

#### Cron Scheduling (`cronjob` toolset)
- **cronjob**: Scheduled task management

#### Messaging (`messaging` toolset)
- **send_message**: Cross-platform messaging (Telegram, Discord, Slack, etc.)

#### Home Assistant (`homeassistant` toolset)
- **ha_list_entities**, **ha_get_state**, **ha_list_services**, **ha_call_service**

#### Kanban (`kanban` toolset)
- Multi-agent coordination with dispatcher-worker pattern
- **kanban_show**, **kanban_list**, **kanban_complete**, **kanban_block**, **kanban_heartbeat**, **kanban_comment**, **kanban_create**, **kanban_link**, **kanban_unblock**

#### Computer Use (`computer_use` toolset)
- **computer_use**: macOS desktop control (background, doesn't steal cursor)

### 1.3 Tool Registry Architecture

**Core Components:**

```python
class ToolEntry:
    """Metadata for a single registered tool."""
    name: str
    toolset: str
    schema: dict
    handler: Callable
    check_fn: Callable  # Availability check
    requires_env: list  # Required environment variables
    is_async: bool
    description: str
    emoji: str
    max_result_size_chars: int | float | None
    dynamic_schema_overrides: Callable  # Runtime schema updates
```

**Registration Pattern:**

```python
from tools.registry import registry, tool_error, tool_result

# At module level (runs at import time)
registry.register(
    name="web_search",
    toolset="web",
    schema=WEB_SEARCH_SCHEMA,
    handler=lambda args, **kw: web_search_tool(args.get("query", ""), limit=args.get("limit", 5)),
    check_fn=check_web_api_key,
    requires_env=["EXA_API_KEY", "PARALLEL_API_KEY", "TAVILY_API_KEY", ...],
    emoji="🔍",
    max_result_size_chars=100_000,
)
```

**Discovery Mechanism:**

```python
def discover_builtin_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """Import built-in self-registering tool modules via AST parsing."""
    # 1. Scan tools/ directory for *.py files
    # 2. Parse AST to find registry.register() calls at module level
    # 3. Import modules (triggers registration)
    # 4. Return imported module names
```

**Check Function Caching:**

```python
# 30-second TTL cache for availability checks
_CHECK_FN_TTL_SECONDS = 30.0
_check_fn_cache: Dict[Callable, tuple[float, bool]] = {}

def _check_fn_cached(fn: Callable) -> bool:
    """Return bool(fn()), TTL-cached across calls."""
    # Amortizes expensive probes (Docker daemon, Modal SDK, Playwright)
    # while allowing env-var changes to propagate quickly
```

### 1.4 Tool Search (Progressive Disclosure)

**Problem:** 500+ tools exceed context window limits

**Solution:** Progressive disclosure via bridge tools

**Architecture:**

```python
# Three bridge tools replace deferred tools
TOOL_SEARCH_NAME = "tool_search"      # Search catalog
TOOL_DESCRIBE_NAME = "tool_describe"  # Load full schema
TOOL_CALL_NAME = "tool_call"          # Invoke deferred tool

# Activation threshold
threshold_pct = 10.0  # Activate when deferred tools > 10% of context

# BM25 search over tool catalog
def search_catalog(catalog: List[CatalogEntry], query: str, limit: int = 5):
    """Return top-limit entries by BM25 score."""
```

**Call Sequence:**

1. Model calls `tool_search(query="github issue")`
2. Returns: `[{"name": "github_create_issue", "description": "..."}]`
3. Model calls `tool_describe(name="github_create_issue")`
4. Returns: Full JSON schema with parameters
5. Model calls `tool_call(name="github_create_issue", arguments={...})`
6. Executes tool and returns result

**Core Tools (Never Deferred):**

73 core tools including web_search, terminal, file operations, browser automation, etc.

### 1.5 MCP Server Integration

**Hermes MCP Server:**

Exposes messaging conversations as MCP tools for external clients (Claude Code, Cursor, etc.)

**Tools Exposed:**

- conversations_list, conversation_get, messages_read, attachments_fetch
- events_poll, events_wait, messages_send, channels_list
- permissions_list_open, permissions_respond

**Event Bridge Architecture:**

```python
class EventBridge:
    """Background poller that watches SessionDB for new messages."""
    
    def _poll_loop(self):
        """Poll every 200ms with mtime-based skip optimization."""
        # Check sessions.json mtime
        # Check state.db mtime
        # Skip if unchanged (makes polling essentially free)
```

---
