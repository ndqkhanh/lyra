# Open-Code Deep Research - Complete Feature Inventory

## Executive Summary

OpenCode (sst/opencode) is an open-source, provider-agnostic AI coding agent built by the SST team. It emphasizes extensibility, multi-provider support, and terminal-first design.

---

## 1. TOOLS CATALOG

### Core Tools
- **bash** — Execute shell commands
- **edit/write** — Modify or create files
- **read** — Access file contents
- **grep** — Search using regex patterns
- **glob** — Find files by pattern matching
- **lsp** — Code intelligence (definitions, references, hover, diagnostics)
- **apply_patch** — Apply patch files
- **skill** — Load skill documentation on-demand
- **todowrite** — Manage task lists
- **webfetch** — Retrieve web content
- **websearch** — Search the web (requires OpenCode provider or Exa AI)
- **question** — Ask users for input during execution

### Tool Control
- Permissions: "allow," "deny," or "ask"
- Uses ripgrep internally for efficient searching
- Respects `.gitignore` patterns by default

**Lyra Comparison**: ✅ Lyra has all these tools + more

---

## 2. SKILLS SYSTEM

### Structure
- Defined in `SKILL.md` files in `.opencode/skills/<name>/SKILL.md`
- YAML frontmatter with `name` and `description`
- Loaded on-demand via native `skill` tool

### Access Control
- Three behaviors: `allow`, `deny`, `ask`
- Wildcard patterns like `internal-*`
- Per-agent overrides in frontmatter

### Instruction Files
- `SKILL.md` — Reusable behaviors
- `AGENTS.md` — Agent-specific guidance
- `CLAUDE.md` — Project-level AI guidance
- `CONTEXT.md` — Global AI guidance

**Lyra Comparison**:
- ✅ Has similar skill system
- ⚠️ Different file structure

---

## 3. PLUGIN ARCHITECTURE ⭐

### Extension Points
- **Tools** — Custom functions with Zod schemas
- **Hooks** — 25+ lifecycle points
- **Commands** — Custom commands via config or markdown

### Key Capabilities
- Integrate custom databases
- Modify AI behavior per agent type
- Enforce security policies
- Add domain-specific capabilities

### Distribution
- Via npm with automatic tool/skill discovery
- Commands require manual registration

### Community Plugins
- `opencode-agent-skills` — Agent skills tools
- `opencode-supermemory` — Persistent memory
- `opencode-mempalace` — MemPalace memory with MCP
- `opencode-agent-memory` — Memory blocks (Letta-inspired)
- `opencode-magic-context` — Long session memory
- `opencode-orchestrator` — AI-agent orchestration

**Lyra Comparison**:
- ✅ Has plugin system
- ❌ Missing: npm distribution
- ❌ Missing: 25+ lifecycle hooks
- ❌ Missing: Zod schema validation

---

## 4. AGENT COORDINATION ⭐

### Native Architecture
- **Build Agent** — Full-access development
- **Plan Agent** — Read-only analysis

### Oh My OpenAgent (OMO) Extension ⭐

**Three-Layer Architecture:**
1. **Planning Layer** — Prometheus and Metis break down intent
2. **Orchestration Layer** — Atlas routes subtasks
3. **Execution Layer** — Specialized workers

**Key Features:**
- 10+ specialized agents
- 32 lifecycle hooks
- 20+ development tools
- Multi-model routing (Claude, GPT, Gemini, Grok)
- Parallel execution
- Persistent state management
- "Ultrawork" mode for full autonomy

### Alternative Multi-Agent Systems
- `opencode-hermes-multiagent` — 17 specialized agents
- `opencode-ensemble` — Agent teams with parallel messaging
- `opencode-agent-hub` — Multiple agents with shared message bus

**Lyra Comparison**:
- ✅ Has multi-agent orchestration
- ❌ Missing: OMO-style three-layer architecture
- ❌ Missing: 32 lifecycle hooks
- ⚠️ Different: Uses OMC team system

---

## 5. MEMORY SYSTEMS

### Built-in Context Management
- Session history backed by SQLite
- Configuration files (`opencode.json`)
- Automatic context compaction
- Dual-agent architecture

### Memory Plugins ⭐
- **Hindsight** — Session recall, auto-retain
- **Supermemory** — Persistent memory across sessions
- **MemPalace** — Auto-registers MCP server
- **Magic Context** — Long session memory
- **Agent Memory** — Memory blocks (Letta-inspired)

### Context Assembly
1. `opencode.json` — Project configuration
2. Session history — SQLite-backed
3. MCP servers — External tools
4. LSP integration — Code intelligence
5. Codebase — Files and structure
6. Custom commands — Reusable operations

**Lyra Comparison**:
- ✅ Has session history
- ✅ Has project configuration
- ✅ Has MCP integration
- ❌ Missing: Memory plugins ecosystem
- ❌ Missing: Hindsight/Supermemory/MemPalace

---

## 6. CONTEXT MANAGEMENT

### Dual-Agent Architecture
- **Plan Agent** — Read-only analysis
- **Build Agent** — Full tool access
- Prevents premature coding

### Configuration-Based Approach
- `opencode.json` defines file visibility
- Instructions about coding standards
- Include/exclude patterns
- Provider-specific settings

### Model-Adaptive Context
- Local models require aggressive focus
- Cloud models handle broader context
- Automatic adjustment

### Sliding Window Context
- Feature request for long sessions
- Manages token limits
- Prevents overflow

**Lyra Comparison**:
- ✅ Has dual-mode system (plan/build)
- ✅ Has configuration-based approach
- ⚠️ Different: Uses permission modes instead

---

## 7. UNIQUE FEATURES

### Provider Agnosticism ⭐
- Supports 75+ LLM providers
- Claude, OpenAI, Google, Bedrock, DeepSeek, local models
- Not locked to any provider
- Custom OpenAI-compatible API support

### Open Source & Extensible
- MIT licensed
- TypeScript, built with Bun
- 158k GitHub stars, 18.5k forks
- Client/server architecture

### Terminal-First Design
- Built as TUI by neovim users
- Beta desktop app (macOS, Windows, Linux)
- IDE extension support

### Permission System
- Granular control over agent actions
- Three states: allow, ask, deny
- Wildcard patterns
- Agent-level overrides
- `.env` files denied by default

### Modes System
- **Build Mode** — All tools enabled
- **Plan Mode** — Read-only analysis
- Customizable via `opencode.json`
- Per-mode: model, temperature, system prompt, tools

### Custom Agents
- Create via `opencode agent create`
- JSON or markdown configuration
- Filename becomes identifier
- Configuration: description, mode, model, temperature, tools

### LSP Integration ⭐
- Built-in servers for 30+ languages
- Automatic server startup
- Provides diagnostics to LLM
- Custom server configuration
- Environment variables and init options

**Lyra Comparison**:
- ✅ Has LSP integration
- ✅ Has multi-provider support
- ✅ Has permission system
- ✅ Has modes system
- ❌ Missing: 75+ provider support (has ~6)
- ❌ Missing: Built-in LSP servers for 30+ languages
- ⚠️ Different: Python-based, not TypeScript

---

## 8. MCP INTEGRATION

### Capabilities
- Add external tools via MCP
- Local and remote MCP servers
- GitHub, PostgreSQL, custom APIs
- Context-aware tool loading

### Configuration
- Local and remote server patterns
- Context management
- Integration with 100+ MCP servers

### Use Cases
- GitHub integration
- Database connections
- Custom API integrations
- Social media analytics
- Infrastructure tools
- Deployment workflows

**Lyra Comparison**:
- ✅ Has MCP integration
- ⚠️ Different: Uses lyra-mcp package

---

## 9. CONFIGURATION SYSTEM

### Configuration Files
- `opencode.json` or `opencode.jsonc`
- Global: `~/.config/opencode/opencode.json`
- Project: `.opencode/opencode.json`
- Schema validation via `$schema`

### Configuration Scope
- Theme and keybindings
- Provider and model selection
- LSP server configuration
- Permission rules
- Agent definitions
- Tool settings
- MCP server connections
- Include/exclude patterns

### Multi-Format Support
- Native `opencode.json`
- OMO `oh-my-opencode.json`
- Markdown agent files
- YAML frontmatter

**Lyra Comparison**:
- ✅ Has similar configuration system
- ⚠️ Different: Uses `settings.json` instead

---

## 10. INTEGRATION ECOSYSTEM

### LLM Providers (75+)
- Anthropic Claude
- OpenAI GPT
- Google Vertex AI
- Amazon Bedrock
- GitHub Copilot
- DeepSeek
- Local models (Ollama, LM Studio, llama.cpp)
- Custom OpenAI-compatible APIs

### External Services
- MCP servers (100+)
- LSP servers (30+)
- GitHub integration
- Database connections
- Custom APIs

### IDE & Editor Support
- Terminal UI (primary)
- Desktop application (beta)
- IDE extensions
- Zed agentic-coding-protocol

**Lyra Comparison**:
- ✅ Has multi-provider support
- ❌ Missing: 75+ providers (has ~6)
- ❌ Missing: Desktop app
- ❌ Missing: IDE extensions

---

## 11. ARCHITECTURE

### Tech Stack
- TypeScript (63.4%)
- MDX documentation (33.6%)
- CSS (2.6%)
- Built with Bun runtime

### Design Philosophy
- Decouples agent runtime from intelligence provider
- Terminal-first but multi-platform
- Open source and community-driven
- Extensible through plugins and skills
- Security-conscious with granular permissions

### Positioning
- Open-source alternative to Claude Code
- Stronger extensibility
- Provider flexibility
- Not coupled to any single AI provider

**Lyra Comparison**:
- ⚠️ Different: Python-based, not TypeScript
- ⚠️ Different: Uses harness-core architecture
- ✅ Similar: Open source and extensible

---

## KEY GAPS TO STEAL

### High Priority
1. **75+ Provider Support** — Massive provider ecosystem
2. **OMO Three-Layer Architecture** — Planning/Orchestration/Execution
3. **32 Lifecycle Hooks** — Fine-grained control
4. **Memory Plugins Ecosystem** — Hindsight, Supermemory, MemPalace
5. **Built-in LSP Servers** — 30+ languages
6. **npm Plugin Distribution** — Easy sharing
7. **Zod Schema Validation** — Type-safe tool definitions
8. **Desktop App** — GUI alternative to CLI

### Medium Priority
1. **Bun Runtime** — Faster than Node.js
2. **TypeScript Rewrite** — Better type safety
3. **IDE Extensions** — VS Code, JetBrains
4. **Zed Integration** — Agentic-coding-protocol
5. **Custom Agent Creator** — Interactive CLI
6. **Markdown Agent Files** — Simpler than JSON
7. **Model-Adaptive Context** — Automatic adjustment
8. **Sliding Window Context** — Long session support

### Low Priority
1. **Client/Server Architecture** — Remote operation
2. **TUI by neovim users** — Terminal UX
3. **158k GitHub stars** — Community size
4. **MIT License** — Permissive licensing

---

## SOURCES

- [Claude Code vs OpenCode (2026): Comparison of AI Coding CLIs](https://www.infralovers.com/blog/2026-01-29-claude-code-vs-opencode/)
- [OpenCode vs Claude Code vs Cursor: AI Coding Agents Compared (2026)](https://computingforgeeks.com/opencode-vs-claude-code-vs-cursor/)
- [OpenCode vs Claude Code: Which Agentic Tool Should You Use in 2026?](https://www.datacamp.com/blog/opencode-vs-claude-code)
- [I Switched From Claude Code to OpenCode — Here's Why](https://thomas-wiegold.com/blog/i-switched-from-claude-code-to-opencode/)
- [Architecture, Capabilities, and Real-World Value for Developers](https://bryanwhiting.com/ai/opencode-vs-claude-code-architecture-capabilities/)
- [OpenCode vs Claude Code: When Open-Source Agents Win](https://teachmeidea.com/opencode-vs-claude-code/)
- [GitHub: sst/opencode](https://github.com/sst/opencode)
- [Plugin API Documentation](https://anomalyco-opencode.mintlify.app/sdk/plugin-api)
- [OpenCode Tools Documentation](https://dev.opencode.ai/docs/tools)
- [A Complete Guide to the Open-Source Terminal AI Agent](https://datalakehousehub.com/blog/2026-03-context-management-opencode)
- [What Is Oh My OpenAgent (OMO)? Complete 2026 Guide](http://a2a-mcp.org/blog/what-is-oh-my-openagent)
- [Agent Skills Documentation](https://frank.dev.opencode.ai/docs/skills/)
- [Permissions Documentation](https://docs.opencode.ai/docs/permissions/)
- [Providers Documentation](https://anomalyco-opencode.mintlify.app/providers)
- [Modes Documentation](https://anomalyco-opencode.mintlify.app/modes)
- [Custom Agents Configuration](https://thdxr.dev.opencode.ai/docs/agents/)
- [LSP Integration Documentation](https://docs.opencode.ai/docs/lsp)
- [MCP Servers Documentation](https://docs.opencode.ai/docs/mcp-servers)

---

**Research Completed**: 2026-05-11
**Agent**: Explore (Open-Code)
**Status**: ✅ Complete
