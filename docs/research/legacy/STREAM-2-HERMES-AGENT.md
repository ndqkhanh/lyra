# STREAM 2: Hermes Agent Research Report
## Source: nousresearch/hermes-agent (v0.15.1, MIT License)

> **Date**: 2026-05-30
> **Analyst**: Automated deep-research scan of the full Hermes Agent repository
> **Repo**: `https://github.com/nousresearch/hermes-agent`
> **License**: MIT (fully compatible with Lyra's MIT license)
> **Codebase**: ~2,000 Python files, 1,389 Markdown files, 15.5K-line CLI

---

## 1. EXECUTIVE SUMMARY

Hermes Agent (by Nous Research) is the most full-featured open-source AI-agent harness currently available. It implements **55+ tools**, a **self-improving skill system**, a **multi-platform messaging gateway**, **subagent delegation**, **mixture-of-agents reasoning**, **built-in cron scheduling**, and a **SQLite/FTS5-based persistent memory** that spans sessions. Its architecture is remarkably production-hardened: every component has been stress-tested across Telegram, Discord, Slack, WhatsApp, Signal, and 12+ other platforms.

**Key takeaway for Lyra**: Hermes is the richest source of portable patterns among all surveyed harnesses. Its tool registry system, progressive tool disclosure, self-improving skills loop, subagent architecture, and context compression patterns are breakthrough-tier candidates for porting.

---

## 2. COMPLETE TOOL INVENTORY

### 2.1 Tool Registry Architecture

Tools are discovered via **AST-based module scanning** in `tools/registry.py`. Each tool module calls `registry.register()` at module level, declaring its schema, handler, toolset membership, and availability check (`check_fn`). The registry uses a **generation counter** for cache invalidation and supports **dynamic schema overrides** (zero-arg callables that override schema fields at definition time for runtime-config-dependent descriptions).

```python
# Registration pattern (from tools/registry.py)
registry.register(
    name="tool_name",
    toolset="toolset_name",     # which group this belongs to
    schema={...},               # OpenAI function-calling schema
    handler=handler_fn,         # sync or async callable
    check_fn=check_fn,          # returns bool for availability
    requires_env=["ENV_VAR"],   # optional env requirements
    is_async=True/False,        # async handler flag
    description="...",          # human-readable
    emoji="🔧",                # CLI display emoji
    max_result_size_chars=...,  # output truncation limit
    dynamic_schema_overrides=... # callable for runtime schema tweaks
)
```

**Check function caching**: `check_fn` results are TTL-cached (30s default) to avoid probing external state on every tool definition assembly.

### 2.2 Complete Tool Catalog

#### CORE TOOLS (always loaded, defined in `_HERMES_CORE_TOOLS`)

| # | Tool Name | Toolset | Description |
|---|-----------|---------|-------------|
| 1 | `web_search` | web | Web search via multiple backends (Firecrawl, Exa, Parallel Web) |
| 2 | `web_extract` | web | Extract/scrape content from URLs |
| 3 | `terminal` | terminal | Shell command execution with approval gating |
| 4 | `process` | terminal | Background process management (start, list, kill, wait, send_keys) |
| 5 | `read_file` | file | Read file contents with encoding detection |
| 6 | `write_file` | file | Write/create files with atomic replace |
| 7 | `patch` | file | Apply patches with fuzzy matching for line drift |
| 8 | `search_files` | file | Content search + filename search (via ripgrep) |
| 9 | `vision_analyze` | vision | Analyze images with multimodal models |
| 10 | `image_generate` | image_gen | Generate images (FAL, OpenAI backends) |
| 11 | `video_analyze` | video | Analyze video content (opt-in) |
| 12 | `video_generate` | video_gen | Text-to-video and image-to-video |
| 13 | `skills_list` | skills | List available skills with metadata (progressive disclosure tier 1) |
| 14 | `skill_view` | skills | Load full skill content (progressive disclosure tiers 2-3) |
| 15 | `skill_manage` | skills | Create, edit, patch, delete skills (agent-managed) |
| 16 | `browser_navigate` | browser | Navigate browser to URL |
| 17 | `browser_snapshot` | browser | Take accessibility-tree snapshot of page |
| 18 | `browser_click` | browser | Click elements on page |
| 19 | `browser_type` | browser | Type text into form fields |
| 20 | `browser_scroll` | browser | Scroll page |
| 21 | `browser_back` | browser | Navigate back |
| 22 | `browser_press` | browser | Press keyboard keys |
| 23 | `browser_get_images` | browser | Extract images from page |
| 24 | `browser_vision` | browser | Visual screenshot analysis of page |
| 25 | `browser_console` | browser | Read browser console output |
| 26 | `browser_cdp` | browser | Direct Chrome DevTools Protocol access |
| 27 | `browser_dialog` | browser | Handle browser dialogs (alert, confirm, prompt) |
| 28 | `text_to_speech` | tts | Text-to-speech (Edge TTS, ElevenLabs, OpenAI, xAI) |
| 29 | `todo` | todo | Task planning and tracking (in-memory, per-session) |
| 30 | `memory` | memory | Persistent memory across sessions (MEMORY.md + USER.md) |
| 31 | `session_search` | session_search | FTS5 full-text search across all past conversations |
| 32 | `clarify` | clarify | Interactive clarifying questions with multiple-choice UI |
| 33 | `execute_code` | code_execution | Programmatic Tool Calling (PTC) - run Python scripts that call tools via RPC |
| 34 | `delegate_task` | delegation | Spawn isolated subagents for parallel/complex subtasks |
| 35 | `cronjob` | cronjob | Create, list, update, pause, resume, remove, trigger scheduled tasks |
| 36 | `send_message` | messaging | Cross-platform messaging (Telegram, Discord, Slack, etc.) |
| 37 | `computer_use` | computer_use | macOS desktop control via cua-driver (screenshots, mouse, keyboard) |

#### PLATFORM-SPECIFIC TOOLS

| # | Tool Name | Toolset | Description |
|---|-----------|---------|-------------|
| 38 | `discord` | discord | Discord read/participate (fetch messages, search members, create threads) |
| 39 | `discord_admin` | discord_admin | Discord server management (list channels/roles, pin, assign roles) |
| 40 | `ha_list_entities` | homeassistant | List Home Assistant entities |
| 41 | `ha_get_state` | homeassistant | Get entity state from Home Assistant |
| 42 | `ha_list_services` | homeassistant | List Home Assistant services |
| 43 | `ha_call_service` | homeassistant | Call Home Assistant service |
| 44 | `spotify_playback` | spotify | Spotify playback control |
| 45 | `spotify_devices` | spotify | List Spotify devices |
| 46 | `spotify_queue` | spotify | Manage Spotify queue |
| 47 | `spotify_search` | spotify | Search Spotify |
| 48 | `spotify_playlists` | spotify | Manage playlists |
| 49 | `spotify_albums` | spotify | Browse albums |
| 50 | `spotify_library` | spotify | Library management |
| 51 | `x_search` | x_search | Search X/Twitter posts and threads via xAI |
| 52 | `feishu_doc_read` | feishu_doc | Read Feishu/Lark documents |
| 53 | `feishu_drive_list_comments` | feishu_drive | List Feishu/Lark doc comments |
| 54 | `feishu_drive_list_comment_replies` | feishu_drive | List comment replies |
| 55 | `feishu_drive_reply_comment` | feishu_drive | Reply to comment |
| 56 | `feishu_drive_add_comment` | feishu_drive | Add comment to doc |
| 57 | `yb_query_group_info` | yuanbao | Yuanbao group info (Chinese messaging) |
| 58 | `yb_query_group_members` | yuanbao | Yuanbao group members |
| 59 | `yb_send_dm` | yuanbao | Yuanbao DM |
| 60 | `yb_search_sticker` | yuanbao | Yuanbao sticker search |
| 61 | `yb_send_sticker` | yuanbao | Yuanbao send sticker |

#### KANBAN COORDINATION TOOLS (multi-agent orchestration)

| # | Tool Name | Description |
|---|-----------|-------------|
| 62 | `kanban_show` | Show current task details |
| 63 | `kanban_list` | List all tasks |
| 64 | `kanban_complete` | Mark task complete with structured handoff |
| 65 | `kanban_block` | Block task for human input |
| 66 | `kanban_heartbeat` | Heartbeat during long operations |
| 67 | `kanban_comment` | Comment on task thread |
| 68 | `kanban_create` | Create new task |
| 69 | `kanban_link` | Link tasks as dependencies |
| 70 | `kanban_unblock` | Unblock a task |

#### PROGRESSIVE DISCLOSURE BRIDGE TOOLS

| # | Tool Name | Description |
|---|-----------|-------------|
| 71 | `tool_search` | Search for tools by name/description (never loads tool schemas directly) |
| 72 | `tool_describe` | Get full schema for a specific tool |
| 73 | `tool_call` | Call a deferrable tool by name |

#### ADVANCED REASONING

| # | Tool Name | Description |
|---|-----------|-------------|
| 74 | `mixture_of_agents` | Multi-LLM collaboration (reference models + aggregator) |

### 2.3 Toolset Composition System

Toolsets are composable: toolsets can include other toolsets via the `includes` field. Platform-specific toolsets (e.g., `hermes-cli`, `hermes-telegram`, `hermes-discord`) all share `_HERMES_CORE_TOOLS` as their base, with platform-specific additions. The `resolve_toolset()` function handles recursive resolution with cycle detection.

```python
# Composition example from toolsets.py
"hermes-discord": {
    "description": "Discord bot toolset",
    "tools": _HERMES_CORE_TOOLS + ["discord", "discord_admin"],
    "includes": []
}
"hermes-gateway": {
    "description": "Gateway toolset - union of all platforms",
    "tools": [],
    "includes": ["hermes-telegram", "hermes-discord", "hermes-whatsapp", ...]  # 20+ platforms
}
```

**Security-conscious design**: The `hermes-webhook` toolset is intentionally constrained to only `web_search`, `web_extract`, `vision_analyze`, and `clarify` -- no file system, terminal, or browser access for untrusted third-party webhook content.

---

## 3. UX PATTERNS WORTH PORTING

### 3.1 TUI Architecture (cli.py: 15,493 lines)

| Pattern | Implementation | Portability |
|---------|---------------|-------------|
| **Fixed input area** | prompt_toolkit `Application` with `HSplit` layout; input pinned to bottom, output scrolls above | HIGH - prompt_toolkit is Python-only, but the concept is portable |
| **Multiline editing** | Shift+Enter / Ctrl+Enter aliases via `install_shift_enter_alias`, `install_ctrl_enter_alias` | HIGH - concept is universal |
| **Slash-command autocomplete** | prompt_toolkit completions menu with `/model`, `/new`, `/reset`, `/retry`, `/undo`, `/compress`, `/usage`, `/insights`, `/skills`, `/personality` | HIGH |
| **Streaming output** | Tool results stream inline; spinner during tool execution; rich formatting | HIGH |
| **Interrupt-and-redirect** | Ctrl+C sends interrupt to current tool, new message redirects conversation | HIGH - critical UX |
| **Kawaii spinner** | `KawaiiSpinner` class with cute messages like `(◕‿◕✿) Running terminal command...` | MEDIUM - fun but optional |
| **Skin engine** | Theme system with configurable colors (`hermes_cli/skin_engine.py`); diff colors adapt to skin | MEDIUM |
| **Reasoning tag stripping** | `_strip_reasoning_tags()` strips `<think>`, `<thinking>`, `<reasoning>`, `<REASONING_SCRATCHPAD>`, `<thought>` blocks, plus tool-call XML leakage | LOW - visual polish |
| **Tool emoji mapping** | Every tool has a display emoji via `get_tool_emoji()` | LOW |
| **Inline diff display** | After file writes, shows unified diff with colored +/- lines (up to 6 files / 80 lines) | MEDIUM |
| **Format compact** | `format_duration_compact()`, `format_token_count_compact()` for readable metrics | LOW |

### 3.2 Slash Commands (CLI)

```
/model [provider:model]   - Change model
/new                      - Start fresh conversation
/reset                    - Reset conversation
/retry                    - Retry last turn
/undo                     - Undo last turn
/compress                 - Manually trigger context compression
/usage                    - Show token usage
/insights [--days N]      - Conversation insights
/skills                   - Browse skills
/<skill-name>             - Invoke a skill
/personality [name]       - Set personality
/platforms                - Platform status
```

### 3.3 Error Handling Patterns

| Pattern | Description |
|---------|-------------|
| **Provider-aware error messages** | `classify_api_error()` maps API errors to `FailoverReason` enum; `_ollama_context_limit_error()` gives Ollama-specific context size guidance |
| **Billing/entitlement guidance** | `_billing_or_entitlement_message()` detects exhausted credits and provides provider-specific next steps |
| **Graceful degradation** | When session DB can't open (e.g., NFS/SMB), falls back to DELETE journal mode instead of crashing; surfaces cause to user via `format_session_db_unavailable()` |
| **Retry with jittered backoff** | `jittered_backoff()` from `agent/retry_utils.py` for API calls |
| **Tool result classification** | `agent/tool_result_classification.py` identifies file-mutating tools, destructive commands |
| **Error preview extraction** | `_extract_error_preview()` pulls the most relevant error line from large tool outputs |

---

## 4. ARCHITECTURE INSIGHTS

### 4.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTRY POINTS                             │
│  cli.py (TUI)  │  gateway/run.py (messaging)  │  batch_runner   │
│  mcp_serve.py  │  acp_adapter (VS Code)       │  api_server     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   run_agent.py::AIAgent                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │Tool Executor│  │Conv. Loop    │  │Context Engine         │   │
│  │sequential/  │  │(4697 lines)  │  │(pluggable: compressor, │   │
│  │concurrent   │  │              │  │ LCM, custom)          │   │
│  │(MAX=8 thds) │  │              │  │                       │   │
│  └─────────────┘  └──────────────┘  └───────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   model_tools.py (1067 lines)                    │
│  Thin orchestration over registry. get_tool_definitions(),      │
│  handle_function_call(). Lazy imports to avoid circular deps.   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│               tools/registry.py::ToolRegistry (singleton)        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │AST Discovery│  │check_fn TTL  │  │Generation Counter     │   │
│  │(auto-import │  │Cache (30s)   │  │(memoize against)     │   │
│  │ tool modules│  │              │  │                       │   │
│  └─────────────┘  └──────────────┘  └───────────────────────┘   │
│                                                                  │
│  74+ registered tools, each with: schema, handler, check_fn,     │
│  toolset, emoji, dynamic_schema_overrides                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    toolsets.py (882 lines)                       │
│  TOOLSETS dict → resolve_toolset() → recursive composition       │
│  _HERMES_CORE_TOOLS (37 tools) shared by all platforms           │
│  Platform-specific overlays (hermes-telegram + discord tools)    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   PERSISTENCE LAYER                              │
│  ┌──────────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │hermes_state.py   │  │Memory System   │  │Skills System    │  │
│  │SQLite + FTS5     │  │MEMORY.md       │  │~/.hermes/skills/│  │
│  │WAL mode, schema  │  │USER.md         │  │SKILL.md +       │  │
│  │v14, session      │  │§-delimited     │  │references/      │  │
│  │splitting on      │  │entries         │  │templates/       │  │
│  │compression       │  │                │  │scripts/assets/  │  │
│  └──────────────────┘  └────────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Key Architectural Patterns

#### A. Tool Registry with AST-Based Discovery

The most sophisticated tool registration system among all surveyed harnesses:

1. **AST scanning**: At import time, `_module_registers_tools()` parses each `.py` file's AST to detect `registry.register(...)` calls at module body level. This determines which modules need importing without executing them.
2. **Lazy import**: Only detected modules are imported via `importlib.import_module()`.
3. **Self-registration**: Each module calls `registry.register()` at module level, populating the singleton registry.
4. **Generation counter**: Monotonically increasing. External callers can memoize against it; a cache entry keyed on the generation is valid as long as the generation hasn't changed.
5. **Thread-safe snapshots**: `_snapshot_state()` returns coherent copies under an RLock.
6. **TTL-cached check functions**: `check_fn` results cached for 30 seconds.

**Lyra portability**: This is a BREAKTHROUGH-TIER pattern. Lyra should adopt a similar registry pattern but in TypeScript using decorators or static initialization.

#### B. Progressive Tool Disclosure (Tool Search)

When the number of deferrable tools exceeds a configurable threshold (default 10% of context window), those tools are replaced by three bridge tools:

- `tool_search(query)` -- search tool catalog by name/description
- `tool_describe(name)` -- get full schema for a tool
- `tool_call(name, args)` -- call a tool through the bridge

Core tools (defined in `_HERMES_CORE_TOOLS`) are **never** deferred. The catalog is rebuilt from current tool definitions every assembly (stateless, prevents drift).

**Lyra portability**: BREAKTHROUGH-TIER. Directly addresses the tool-catalog-bloat problem as Lyra's tool count grows.

#### C. Self-Improving Skills Loop

Skills are the agent's **procedural memory**. The agent can:
1. **Create** skills after complex tasks -- turning successful approaches into reusable knowledge
2. **Self-improve** skills during use -- the curation system detects underperforming skills and nudges improvement
3. **Discover** skills from the Skills Hub (agentskills.io compatible)

Skill format (`SKILL.md` with YAML frontmatter):
```yaml
---
name: skill-name              # max 64 chars
description: Brief description # max 1024 chars
version: 1.0.0
license: MIT
platforms: [macos, linux]     # OS restriction
prerequisites:
  env_vars: [API_KEY]
  commands: [curl, jq]
metadata:
  hermes:
    tags: [fine-tuning, llm]
    related_skills: [peft, lora]
---
# Skill content (full instructions)
```

Skills directory structure:
```
~/.hermes/skills/
├── my-skill/
│   ├── SKILL.md           # Main instructions (required)
│   ├── references/        # Supporting documentation
│   ├── templates/         # Output templates
│   ├── scripts/           # Executable scripts
│   └── assets/            # Supplementary files
└── category/
    └── another-skill/
        └── SKILL.md
```

**Skill security**: Skills are scanned for prompt injection patterns. `skills_guard.py` blocks suspicious installs. `_INJECTION_PATTERNS` include "ignore previous instructions", "system prompt:", `<system>`, etc.

**Skill provenance**: `tools/skill_provenance.py` tracks `set_current_write_origin()` so the system knows whether a skill was agent-created, hub-installed, or user-written.

**Lyra portability**: BREAKTHROUGH-TIER. Lyra's skill system should mirror this architecture, particularly the self-improving loop and provenance tracking.

#### D. Subagent Architecture (delegate_task)

```
┌─────────────────────────────────────────────┐
│                PARENT AGENT                  │
│  delegate_task(goal="...", role="worker")    │
│                                              │
│  ┌──────────────┐  ┌──────────────┐          │
│  │ Child Agent 1 │  │ Child Agent 2│  ...     │
│  │ Isolated ctx  │  │ Isolated ctx │          │
│  │ Restricted    │  │ Restricted   │          │
│  │ toolset       │  │ toolset      │          │
│  │ Own task_id   │  │ Own task_id  │          │
│  └──────────────┘  └──────────────┘          │
│                                              │
│  Parent sees only: delegation call + summary │
└─────────────────────────────────────────────┘
```

Key design decisions:
- **Blocked tools**: `delegate_task` (no recursion), `clarify` (no user interaction), `memory` (no shared writes), `send_message` (no cross-platform effects), `execute_code` (children should reason step-by-step)
- **Subagent approval**: Config-driven (`delegation.subagent_auto_approve`); default is auto-deny (safe)
- **Max depth**: Configurable via `max_spawn_depth` (default 1, cap 3)
- **Max concurrent**: Configurable via `max_concurrent_children` (default 3)
- **Spawning pause**: Global flag (`_spawn_paused`) to block all new spawns
- **Active subagent registry**: Tracks all running children for TUI observability and gateway RPCs
- **ThreadPoolExecutor**: Workers with per-thread persistent event loops

**Lyra portability**: BREAKTHROUGH-TIER. The subagent architecture with configurable depth, blocked tool lists, and spawning pause is directly portable to Lyra's agent fleet.

#### E. Context Compression (ContextCompressor)

```
┌─────────────────────────────────────────────┐
│            ContextCompressor                 │
│  (implements ContextEngine ABC)              │
│                                              │
│  Head Protection: first N messages preserved │
│  Tail Protection: last N messages preserved  │
│  Token-budget tail (not fixed count)         │
│                                              │
│  Compaction:                                  │
│  1. Identify middle segment to compress      │
│  2. Prune old tool outputs first (cheap)     │
│  3. LLM summarization of middle segment      │
│  4. Replace with structured summary          │
│  5. Iterative update (preserves prior info)  │
│                                              │
│  Summary template:                            │
│  - Resolved Questions                         │
│  - Pending / Open Questions                   │
│  - Remaining Work (NOT "Next Steps")          │
│  - Key Decisions Made                         │
│  - Important Context                          │
│                                              │
│  Filter-safe preamble: tells the model the    │
│  summary is background reference, not active  │
│  instructions.                                │
└─────────────────────────────────────────────┘
```

**Key insight**: The "Remaining Work" label instead of "Next Steps" prevents the model from reading the summary as active instructions. The filter-safe preamble explicitly states "this is background reference, NOT active instructions."

**Lyra portability**: BREAKTHROUGH-TIER. The structured summary template and filter-safe preamble are directly portable. The ContextEngine ABC pattern is a clean plugin interface.

#### F. Memory System

Two parallel stores:
- **MEMORY.md**: Agent's personal notes (environment facts, project conventions, tool quirks)
- **USER.md**: What the agent knows about the user (preferences, communication style)

Design:
- **Frozen snapshot pattern**: System prompt gets a snapshot at session start; mid-session writes are durable but don't change the system prompt (preserves prefix cache)
- **§-delimited entries**: Entry delimiter keeps parsing simple
- **Character limits** (not token limits): Model-independent
- **Drift detection**: If on-disk file has content that wouldn't round-trip through the parser, refuse mutation and save backup
- **Threat scanning**: Memory content scanned for injection/exfiltration patterns before entering system prompt

**Lyra portability**: HIGH. The frozen-snapshot pattern is elegant for prefix-cache stability. The §-delimiter is simple but effective.

#### G. Session Search (FTS5)

Three-mode tool with zero LLM cost:
1. **DISCOVERY**: `query="..."` -- FTS5 search, dedupes by session lineage, returns top N sessions with snippets and ±5 message windows, plus bookend context
2. **SCROLL**: `session_id + around_message_id` -- returns window of ±N messages; re-anchor to scroll forward/backward
3. **BROWSE**: No args -- recent sessions chronologically

Architecture:
- `hermes_state.py::SessionDB` with SQLite FTS5
- WAL mode for concurrent readers
- Session source tagging (cli, telegram, discord...) for filtering
- Parent session ID chains for compression-triggered session splitting
- `_resolve_to_parent()` walks parent chain to lineage root

**Lyra portability**: HIGH. The three-mode design (discovery/scroll/browse) with zero LLM cost is directly portable. The session lineage concept is particularly valuable.

#### H. Code Execution Sandbox (PTC)

Programmatic Tool Calling lets the LLM write Python scripts that call Hermes tools via RPC:

1. **Local backend**: Unix domain socket RPC between parent and child process
2. **Remote backend**: File-based RPC for Docker/SSH/Modal/Daytona backends
3. **Sandbox**: Only 7 tools allowed inside (`web_search`, `web_extract`, `read_file`, `write_file`, `search_files`, `patch`, `terminal`)
4. **Environment scrubbing**: Secrets filtered; only safe env vars passed to child
5. **Resource limits**: 300s timeout, 50 max tool calls, 50KB stdout, 10KB stderr
6. **Zero context cost**: Only script stdout returns to the LLM; intermediate tool results never enter context

**Lyra portability**: HIGH. The PTC pattern -- letting the model batch tool calls into a single script -- collapses multi-step workflows into single inference turns. The UDS RPC transport is elegant.

#### I. Mixture of Agents (MoA)

Multi-LLM collaboration architecture:
1. **Reference models** (4): `claude-opus-4.6`, `gemini-2.5-pro`, `gpt-5.4-pro`, `deepseek-v3.2` -- generate diverse responses in parallel
2. **Aggregator model** (1): `claude-opus-4.6` -- synthesizes reference responses
3. **Temperatures**: Reference at 0.6 (diverse), Aggregator at 0.4 (consistent)
4. **Fallback**: Minimum 1 successful reference needed to proceed

**Lyra portability**: MEDIUM. The concept is powerful but requires multiple model API keys. More suitable as a premium feature.

#### J. Approval System

Sophisticated dangerous-command detection and approval:
- **Pattern matching**: Regex patterns for destructive commands
- **Per-session state**: Thread-safe, keyed by session_key
- **Smart approval**: Auxiliary LLM for auto-approving low-risk commands
- **Platform adaptation**: CLI interactive vs gateway async queues
- **YOLO mode**: Frozen at import time (prevents runtime injection into approval bypass)
- **Plugin hooks**: `pre_approval_request`, `post_approval_response` lifecycle hooks
- **Permanent allowlist**: Persisted in config.yaml

**Lyra portability**: HIGH. The multi-tier approval system with pattern detection, session state, and auxiliary LLM check is a security best practice.

#### K. Plugin System

Pluggable extension architecture:
- **Context engines**: Pluggable via `ContextEngine` ABC (compressor, LCM, custom)
- **Memory providers**: Honcho dialectic user modeling as a plugin
- **Platform adapters**: Each messaging platform is a plugin
- **Browser providers**: Pluggable browser backends
- **TTS/STT providers**: Pluggable speech backends
- **Web search providers**: Pluggable search (Firecrawl, Exa, Parallel Web)
- **Image/Video gen providers**: Pluggable generation backends
- **Observability**: Plugin hooks for tracing
- **Dashboard plugins**: Custom dashboard widgets

All use registry + ABC pattern for clean interfaces.

**Lyra portability**: HIGH. The ABC + registry pattern for pluggable subsystems is a clean architecture.

---

## 5. FEATURE COMPARISON: HERMES vs LYRA

| Feature | Hermes Agent | Lyra (Projected) | Gap |
|---------|-------------|-------------------|-----|
| **Tool count** | 74+ registered tools | ~20 currently | LARGE |
| **Tool registry** | AST-based discovery, generation counter, TTL check_fn cache | Basic registration | LARGE |
| **Toolset system** | Composable, recursive resolution, platform-specific overlays | None | LARGE |
| **Progressive disclosure** | tool_search/tool_describe/tool_call bridge | None | LARGE |
| **Skill system** | Self-improving, provenance-tracked, security-scanned, hub-compatible | None | LARGE |
| **Subagent delegation** | Configurable depth/concurrency, blocked tools, pause control | Limited | MEDIUM |
| **Context compression** | LLM summarization with structured template, iterative updates | Basic summary | LARGE |
| **Memory system** | Dual-store (MEMORY.md + USER.md), frozen snapshot, drift detection | None | LARGE |
| **Session search** | FTS5, three-mode, zero LLM cost, lineage tracking | None | LARGE |
| **Code execution** | UDS/file RPC sandbox, env scrubbing, 7-tool allowlist | None | LARGE |
| **Mixture of Agents** | 4 reference + 1 aggregator model, configurable | None | LARGE |
| **Approval system** | Multi-tier, per-session, plugin hooks, YOLO mode | Basic | MEDIUM |
| **Cron scheduler** | Natural language, platform delivery, skill-attached | None | LARGE |
| **Kanban coordination** | Multi-agent task board, heartbeats, blocking | None | LARGE |
| **Browser automation** | Playwright-based, 13 tools, CDP access | None | LARGE |
| **Multi-platform** | Telegram, Discord, Slack, WhatsApp, Signal, iMessage, Matrix, SMS, Email, Mattermost, DingTalk, Feishu, WeChat, QQ, WeCom, Yuanbao | Terminal only | LARGE |
| **TUI quality** | prompt_toolkit, skin engine, kawaii spinner, inline diffs | Basic | MEDIUM |
| **Async bridging** | Persistent per-thread event loops, timeout safety | Unknown | MEDIUM |
| **Provider support** | 200+ models via 12+ providers | Few | LARGE |
| **Checkpoint system** | Git-based file checkpointing before destructive ops | None | MEDIUM |
| **Tool result storage** | Persist large results to files, enforce turn budget | None | MEDIUM |
| **Plugin system** | ABC + registry, context engines, memory providers, platform adapters | None | LARGE |
| **MCP integration** | Connect any MCP server as tool source | None | HIGH |

---

## 6. PRIORITY RANKING FOR PORTABLE FEATURES

Projects the value of porting each feature to Lyra against the estimated implementation effort. Scale: 1 (low) to 10 (high).

### BREAKTHROUGH TIER (impact >= 9, any effort)

| # | Feature | Impact | Effort | Score | Rationale |
|---|---------|--------|--------|-------|-----------|
| 1 | **Tool Registry with AST Discovery** | 9 | 7 | 63 | Foundational; makes all other tool work systematic |
| 2 | **Self-Improving Skills Loop** | 10 | 9 | 90 | Unique differentiator; no other MIT harness has this |
| 3 | **Progressive Tool Disclosure** | 9 | 5 | 45 | Solves tool-bloat elegantly; moderate effort |
| 4 | **Subagent Architecture** | 10 | 8 | 80 | Critical for multi-agent Lyra; delegate_task is a blueprint |
| 5 | **Context Compression (Structured)** | 9 | 7 | 63 | Essential for long-running agents; filter-safe preamble is novel |
| 6 | **Memory System (Frozen Snapshot)** | 9 | 4 | 36 | Simple to implement, high user value |

### HIGH PRIORITY (impact >= 7)

| # | Feature | Impact | Effort | Score | Rationale |
|---|---------|--------|--------|-------|-----------|
| 7 | **Toolset Composition System** | 8 | 4 | 32 | Composable tool groups with inherit/override |
| 8 | **Session Search (FTS5, 3-mode)** | 8 | 5 | 40 | Must-have for long-term agent use |
| 9 | **Approval System (Multi-tier)** | 8 | 4 | 32 | Security-critical |
| 10 | **Code Execution Sandbox (PTC)** | 8 | 7 | 56 | Unique capability; moderate effort |
| 11 | **ContextEngine ABC (pluggable)** | 7 | 3 | 21 | Clean plugin interface; low effort |
| 12 | **Plugin System (ABC + Registry)** | 8 | 6 | 48 | Architecture scalability |

### MEDIUM PRIORITY (impact >= 5)

| # | Feature | Impact | Effort | Score | Rationale |
|---|---------|--------|--------|-------|-----------|
| 13 | **Kawaii Spinner / Display** | 5 | 2 | 10 | Fun UX polish |
| 14 | **Skin Engine** | 6 | 5 | 30 | Theming is nice but lower priority |
| 15 | **Inline Diff Display** | 7 | 3 | 21 | Great UX for file operations |
| 16 | **Cron Scheduler** | 7 | 6 | 42 | Automation is powerful |
| 17 | **Mixture of Agents** | 6 | 8 | 48 | Powerful but high API cost |
| 18 | **Kanban Coordination** | 7 | 8 | 56 | Multi-agent orchestration specific |
| 19 | **Checkpoint Manager** | 6 | 4 | 24 | Git-based undo for file ops |

### LOWER PRIORITY (nice to have)

| # | Feature | Impact | Effort | Score | Rationale |
|---|---------|--------|--------|-------|-----------|
| 20 | **Browser Automation (13 tools)** | 5 | 9 | 45 | Heavy dependency (Playwright) |
| 21 | **Multi-platform Gateway** | 6 | 9 | 54 | Most platforms are Python-specific |
| 22 | **Home Assistant Integration** | 3 | 5 | 15 | Niche |
| 23 | **Voice/TTS Pipeline** | 4 | 6 | 24 | Optional polish |

---

## 7. ARCHITECTURE PATTERNS FOR LYRA ADOPTION

### Pattern 1: Tool Registry (TypeScript port)

Hermes uses AST-based discovery to auto-register tools. For Lyra/TypeScript, equivalent pattern:

```typescript
// tools/registry.ts
interface ToolEntry {
  name: string;
  toolset: string;
  schema: FunctionDefinition;
  handler: (args: any) => Promise<string>;
  checkFn?: () => boolean;
  requiresEnv?: string[];
  emoji?: string;
  maxResultSizeChars?: number;
  dynamicSchemaOverrides?: () => Partial<FunctionDefinition>;
}

class ToolRegistry {
  private tools: Map<string, ToolEntry> = new Map();
  private generation: number = 0;
  private checkFnCache: Map<() => boolean, { ts: number; value: boolean }> = new Map();
  private lock = new Mutex();

  register(entry: ToolEntry): void { /* ... */ }
  getDefinitions(enabled: string[], disabled: string[]): FunctionDefinition[] { /* ... */ }
  dispatch(name: string, args: any): Promise<string> { /* ... */ }
  
  // Generation counter for cache invalidation
  getGeneration(): number { return this.generation; }
}
```

### Pattern 2: Toolset Composition

```typescript
const TOOLSETS: Record<string, ToolsetDef> = {
  core: {
    description: "Core tools always available",
    tools: ["read_file", "write_file", "terminal", "web_search"],
    includes: []
  },
  coding: {
    description: "Development-focused tools",
    tools: ["lsp_diagnostics", "lsp_rename"],
    includes: ["core"]  // inherits all core tools
  }
};

function resolveToolset(name: string, visited = new Set<string>()): string[] {
  if (visited.has(name)) return [];
  visited.add(name);
  const ts = TOOLSETS[name];
  if (!ts) return [];
  const tools = [...ts.tools];
  for (const included of ts.includes) {
    tools.push(...resolveToolset(included, visited));
  }
  return [...new Set(tools)];
}
```

### Pattern 3: Frozen Snapshot Memory

```typescript
class MemoryStore {
  private memoryEntries: string[] = [];
  private userEntries: string[] = [];
  private systemPromptSnapshot: { memory: string; user: string } = { memory: "", user: "" };
  
  loadFromDisk(): void {
    // Load from disk once
    this.memoryEntries = parseDelimitedFile("MEMORY.md", "§");
    this.userEntries = parseDelimitedFile("USER.md", "§");
    
    // Freeze snapshot (never changes during session)
    this.systemPromptSnapshot = {
      memory: this.memoryEntries.join("\n"),
      user: this.userEntries.join("\n")
    };
  }
  
  getSystemPrompt(): { memory: string; user: string } {
    // Always returns frozen snapshot (prefix-cache stable)
    return this.systemPromptSnapshot;
  }
  
  async addMemory(content: string): Promise<void> {
    // Writes to disk immediately (durable)
    // Updates live state for tool responses
    // Does NOT change systemPromptSnapshot
    this.memoryEntries.push(content);
    await appendToFile("MEMORY.md", `§\n${content}`);
  }
}
```

### Pattern 4: Progressive Tool Disclosure

```typescript
function assembleToolDefinitions(
  allTools: ToolEntry[],
  enabledToolsetNames: string[],
  config: ToolSearchConfig
): FunctionDefinition[] {
  const coreToolNames = new Set(CORE_TOOLS);
  const coreDefs = allTools.filter(t => coreToolNames.has(t.name));
  const deferrableDefs = allTools.filter(t => !coreToolNames.has(t.name));
  
  if (config.enabled === "off") {
    return [...coreDefs, ...deferrableDefs]; // all inline
  }
  
  if (config.enabled === "auto") {
    const deferrableTokens = estimateTokens(deferrableDefs);
    const contextWindow = getContextLength();
    const pct = (deferrableTokens / contextWindow) * 100;
    
    if (pct < config.thresholdPct) {
      return [...coreDefs, ...deferrableDefs]; // under threshold, all inline
    }
  }
  
  // Replace deferrable tools with bridge tools
  return [
    ...coreDefs,
    TOOL_SEARCH_SCHEMA,
    TOOL_DESCRIBE_SCHEMA,
    TOOL_CALL_SCHEMA
  ];
}
```

### Pattern 5: Subagent Creation

```typescript
const DELEGATE_BLOCKED_TOOLS = new Set([
  "delegate_task",  // no recursion
  "clarify",        // no user interaction
  "memory",         // no shared writes
  "send_message",   // no cross-platform effects
]);

async function delegateTask(params: {
  goal: string;
  role?: "worker" | "orchestrator";
  toolset?: string[];
  max_iterations?: number;
  context_notes?: string;
}): Promise<string> {
  // Validate depth
  if (currentDepth >= maxSpawnDepth) {
    return error("Maximum delegation depth reached");
  }
  
  // Build restricted toolset
  const childToolsets = (params.toolset || ["web", "file", "terminal"])
    .filter(t => t !== "delegation");
  
  // Build child system prompt (focused, no parent history)
  const systemPrompt = buildChildSystemPrompt(params.goal, params.role);
  
  // Spawn child
  const child = new AgentInstance({
    systemPrompt,
    toolsets: childToolsets,
    blockedTools: DELEGATE_BLOCKED_TOOLS,
    maxIterations: params.max_iterations || 10,
    parentSessionId: currentSessionId,
    depth: currentDepth + 1,
  });
  
  const result = await child.run(params.goal);
  
  // Return only the summary (child internals never enter parent context)
  return result.summary;
}
```

---

## 8. LICENSE CONSIDERATIONS

**Hermes Agent**: MIT License (Copyright 2025 Nous Research)

**Lyra**: MIT License

**Compatibility**: Fully compatible. Copying code, patterns, or concepts from Hermes to Lyra carries no legal risk. The MIT license permits unrestricted use, modification, distribution, and sublicensing with only the requirement that the original copyright notice be preserved.

**Attribution**: If copying substantial code verbatim, include the Hermes Agent copyright notice. For architectural patterns and concepts, no attribution is legally required, but acknowledging Nous Research as inspiration is good practice.

---

## 9. SUMMARY OF FINDINGS

### What Makes Hermes Unique

1. **Closed learning loop**: Agent creates skills from experience, self-improves them, gets periodic nudges to persist knowledge -- no other MIT-licensed harness has this.

2. **Production-hardened**: Every feature has been stress-tested across 20+ messaging platforms, 200+ LLM models, and 6 terminal backends. The error handling is provider-aware and platform-specific.

3. **Security-first design**: Drift detection in memory files, threat scanning for skills, environment scrubbing in sandbox, approval gating per session, YOLO-mode freeze at import time.

4. **Scale-tested architecture**: The 15.5K-line CLI and 4.7K-line conversation loop show the architecture handles real complexity without collapsing.

5. **Zero-LLM-cost operations**: Session search uses FTS5 (SQLite), not an LLM. Tool search is stateless catalog lookup. These design choices reduce cost and latency.

6. **Prefix-cache awareness**: The frozen snapshot pattern for memory injection preserves the Anthropic prompt cache across an entire session.

### Critical Architecture Decisions Worth Adopting

| Decision | Why |
|----------|-----|
| Tool registry with generation counter | Enables external memoization without cache invalidation bugs |
| TTL-cached check functions | Prevents per-request external state probing |
| Toolset composition with cycle detection | Enables clean platform overlays without code duplication |
| Self-improving skills loop | Transforms the agent from tool-user to knowledge-creator |
| Filter-safe context compression preamble | Prevents model from treating compressed history as active instructions |
| Frozen snapshot memory | Preserves prefix cache, writes are durable but never destabilize the session |
| Blocked-tool list for subagents | Prevents recursive delegation, shared memory corruption, and cross-platform leakage |
| Import-time frozen YOLO mode | Prevents runtime injection into security bypass |
| Per-thread persistent event loops | Prevents "Event loop is closed" errors from cached async clients |

---

## 10. REFERENCES

- **Repository**: https://github.com/nousresearch/hermes-agent
- **Documentation**: https://hermes-agent.nousresearch.com/docs/
- **License**: MIT (https://github.com/NousResearch/hermes-agent/blob/main/LICENSE)
- **Key files analyzed**:
  - `cli.py` (15,493 lines) - CLI entry point and TUI
  - `run_agent.py` (4,709 lines) - AIAgent orchestrator
  - `agent/conversation_loop.py` (4,697 lines) - Conversation loop
  - `agent/tool_executor.py` - Concurrent tool execution
  - `model_tools.py` (1,067 lines) - Tool orchestration
  - `tools/registry.py` - Tool registry
  - `toolsets.py` (882 lines) - Toolset definitions
  - `hermes_state.py` (3,549 lines) - SQLite state store
  - `tools/memory_tool.py` - Memory system
  - `tools/delegate_tool.py` - Subagent architecture
  - `tools/skills_tool.py` - Skill listing/viewing
  - `tools/skill_manager_tool.py` - Skill creation/editing
  - `tools/tool_search.py` - Progressive disclosure
  - `tools/code_execution_tool.py` - PTC sandbox
  - `tools/mixture_of_agents_tool.py` - MoA
  - `tools/cronjob_tools.py` - Cron scheduling
  - `tools/approval.py` - Dangerous command approval
  - `agent/context_engine.py` - Pluggable context engine ABC
  - `agent/context_compressor.py` - Context compression
  - `agent/display.py` - CLI presentation layer
