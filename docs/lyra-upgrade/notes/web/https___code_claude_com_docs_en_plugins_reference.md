# Plugins Reference (code.claude.com / Anthropic)

Complete technical reference for the Claude Code plugin system, including component schemas, CLI commands, lifecycle hooks, and development tools. No author or date is listed on the page, but it ships as official Anthropic documentation for Claude Code.

## Key Technical Claims

- Claude Code plugins are **self-contained directories** of components that extend Claude Code with custom functionality. The plugin system supports six core component types plus two experimental ones: **skills**, **agents**, **hooks**, **MCP servers**, **LSP servers**, **monitors** (experimental), and **themes** (experimental).
- A plugin is **optionally** declared via `.claude-plugin/plugin.json`. If the manifest is absent, Claude Code auto-discovers components from default locations and derives the plugin name from the directory name.
- Plugins ship with **three installation scopes** -- `user` (global, default), `project` (shared via version control), and `local` (gitignored per-project) -- plus `managed` for admin-controlled deployment.
- **Skills-directory plugins**: any folder under `~/.claude/skills/` or `<cwd>/.claude/skills/` that contains a `.claude-plugin/plugin.json` manifest is loaded automatically on the next session with **no marketplace and no install step**.
- The **plugin cache** at `~/.claude/plugins/cache/` copies marketplace plugins rather than using them in-place for security. Orphaned versions remain for 7 days before cleanup.
- A **persistent data directory** at `~/.claude/plugins/data/{id}/` survives plugin updates. Recommended pattern: use a `SessionStart` hook that diffs `package.json` between the plugin root and data dir to detect dependency changes and re-install.
- **Version management** offers two modes: explicit semver in `plugin.json` (stable releases, version must be bumped to trigger updates) or implicit git commit SHA (every new commit is an update, suitable for active development).
- **User configuration** via `userConfig` in the manifest prompts users for values at enable time (string, number, boolean, directory, file). Sensitive values are stored in the system keychain rather than `settings.json`. Values are injected into all component configs via `${user_config.KEY}` variables.
- `plugin details` outputs projected token cost per component, split into an "always-on" cost (paid every session) and "on-invoke" cost (paid only when the component fires).

## Architecture / Mechanism Details

**Component registry** (six core + two experimental):
| Component | Location | Purpose |
|---|---|---|
| Manifest | `.claude-plugin/plugin.json` | Metadata + component path overrides |
| Skills | `skills/` | `/name` shortcuts, `SKILL.md` per subdirectory |
| Commands | `commands/` | Flat `.md` skill files |
| Agents | `agents/` | Subagent definitions with frontmatter (model, effort, maxTurns, tools, isolation) |
| Hooks | `hooks/hooks.json` | Event-driven lifecycle handlers |
| MCP servers | `.mcp.json` | External tool integration |
| LSP servers | `.lsp.json` | Language intelligence (go-to-def, references, diagnostics) |
| Monitors | `monitors/monitors.json` | Background processes, stdout lines delivered as notifications |
| Themes | `themes/` | Color theme files with base + overrides |

**Hook types**: `command` (shell scripts), `http` (POST event JSON to URL), `mcp_tool` (call MCP server tool), `prompt` (evaluate with LLM), `agent` (run agentic verifier).

**Hook lifecycle events** (22 total): SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, PostToolBatch, Notification, MessageDisplay, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, InstructionsLoaded, ConfigChange, CwdChanged, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, Elicitation, ElicitationResult, SessionEnd.

**Plugin agent frontmatter fields**: `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, `isolation` (only valid value: `"worktree"`). For security, `hooks`, `mcpServers`, and `permissionMode` are NOT supported in plugin-shipped agents.

**Path behavior rules**: 
- `commands`, `agents`, `outputStyles`, `themes`, `monitors` **replace** the default directory when specified.
- `skills` **adds to** the default directory.
- `hooks`, `mcpServers`, `lspServers` have their own merge rules (inline + file + default combine).

**Environment variables**: `${CLAUDE_PLUGIN_ROOT}` (installation dir, changes on update), `${CLAUDE_PLUGIN_DATA}` (persistent state dir, survives updates), `${CLAUDE_PROJECT_DIR}` (project root). All substituted inline in skill content, agent content, hook commands, monitor commands, and MCP/LSP configs. Also exported as env vars to subprocesses.

**Dependency system**: Plugins can declare `dependencies` (names + optional semver ranges). `claude plugin prune` removes auto-installed dependencies that no other plugin requires. Dependencies are resolved via git tags (created with `claude plugin tag`).

**Manifest design**: Unrecognized top-level fields are silently ignored (not errors). This allows a single `plugin.json` to double as a VS Code extension manifest, npm `package.json`, or MCPB bundle manifest.

## Numbers & Benchmarks

- **Agent maxTurns default**: 20 (configurable in frontmatter)
- **Plugin cache orphan cleanup**: 7 days after uninstall/update
- **Keychain sensitive storage limit**: approximately 2 KB total
- **Token cost example** (from `plugin details` output): always-on ~180 tok per session; on-invoke ~2400 tok per skill invocation
- **Min version requirements**: `displayName` requires v2.1.143, `defaultEnabled` requires v2.1.154, monitors require v2.1.105, plugin prune requires v2.1.121
- **Agent effort level**: `medium` is the documented default
- **Skills-directory plugin**: auto-loaded on next session with zero install steps
- **`claude plugin validate --strict`**: catches misspelled fields or cross-ecosystem remnants before publishing

## Transfer to Lyra

**One idea**: **Plugin manifest with `userConfig` + variable substitution** -- the pattern where each plugin declares a typed schema of configuration values (`string`, `number`, `boolean`, `directory`, `file`) with validation rules (`required`, `sensitive`, `min`/`max`, `default`), and those values are prompted at enable time then injected into all component configurations via `${user_config.KEY}` variables. Sensitive values are automatically routed to the system keychain.

**Why it transfers**: Lyra's current plugin/extension architecture (if it exists) likely requires users to hand-edit config files or environment variables. The `userConfig` schema pattern eliminates that friction: it provides a declarative, type-safe, validated configuration contract between the plugin author and the user, with built-in sensitive-value handling. The variable substitution mechanism (`${user_config.*}` in MCP configs, hook commands, skill content) means every component in the plugin stack accesses configuration the same way, regardless of where the value was defined.

**Workstream route**: §4.3 Plugin System -- make `userConfig` + `${user_config.*}` variable interpolation the core of Lyra's plugin configuration model. This is the single highest-leverage UX improvement for a plugin system: it eliminates hand-editing, enables typed configuration prompts, secures credentials automatically, and provides a uniform access pattern from all plugin components.
