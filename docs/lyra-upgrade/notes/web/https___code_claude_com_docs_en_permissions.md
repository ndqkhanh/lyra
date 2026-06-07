# Configure Permissions (Claude Code Docs / Anthropic)

Source: https://code.claude.com/docs/en/permissions
Author/Org: Anthropic (Claude Code team)
Date: Undated (current docs as of mid-2026)

---

## Key Technical Claims

1. **Tiered Permission System**: Three tiers of tool access -- Read-only (no approval), Bash/shell execution (approval required, permanent per project directory), and File modification (approval required, until session end). This is the core access-control model.

2. **Three Rule Types (Allow / Ask / Deny)**: Evaluated in strict precedence: **deny -> ask -> allow**. The first matching rule wins. Deny rules always take precedence by evaluation order, not by config source. A matching deny at any settings level blocks the tool call regardless of allow rules at higher levels.

3. **Permission Modes**: Six modes controlling how tools are approved: `default` (prompt per tool), `acceptEdits` (auto-accept file edits + common filesystem cmds), `plan` (read-only), `auto` (background safety checks, research preview), `dontAsk` (auto-deny unless pre-approved), `bypassPermissions` (skip all prompts except root/home rm as circuit breaker).

4. **Wildcard Pattern Matching for Bash**: Glob patterns with `*` at any position. Word boundary enforcement via space-before-`*` (`Bash(ls *)` does not match `lsof`, but `Bash(ls*)` does). The `:*` suffix is equivalent to trailing ` *` but only recognized at end of pattern.

5. **Compound Command Awareness**: Claude Code parses shell operators (`&&`, `||`, `;`, `|`, `|&`, `&`, newlines) and checks each subcommand independently. A rule must match every subcommand for the compound command to be allowed. Up to 5 rules may be saved per compound command.

6. **Process Wrapper Stripping**: A built-in, non-configurable set of wrappers (`timeout`, `time`, `nice`, `nohup`, `stdbuf`, bare `xargs`) are stripped before matching. Exec wrappers (`watch`, `setsid`, `ionice`, `flock`) and `find -exec/-delete` always prompt.

7. **Read-Only Commands**: Built-in, non-configurable set (`ls`, `cat`, `echo`, `pwd`, `head`, `tail`, `grep`, `find`, `wc`, `which`, `diff`, `stat`, `du`, `cd`, read-only `git` forms). Unquoted globs are permitted for read-only commands but prompt for write/exec-capable commands (find, sort, sed, git).

8. **Read/Edit Path Rules**: Follow [gitignore](https://git-scm.com/docs/gitignore) specification with four pattern types: absolute (`//path`), home-relative (`~/path`), project-root-relative (`/path`), and cwd-relative (`path` or `./path`). Deny blocks when EITHER symlink path or target matches.

9. **MCP Permissions**: Convention `mcp__server__tool` to name tools from MCP servers. Wildcard `mcp__server__*` matches all tools from a server.

10. **Agent/Subagent Permissions**: `Agent(AgentName)` syntax to control which subagents Claude can use. Deny rules remove the agent from context entirely.

11. **Hooks Extend Permissions**: PreToolUse hooks run before permission prompt. Hook exit codes: 0 (skip prompt, let call proceed), 1 (force prompt), 2 (deny call). Hook decisions do NOT override deny rules -- built-in deny/ask evaluation still applies. But a blocking hook (exit 2) takes precedence over allow rules.

12. **Managed Settings**: Organization-level admin controls that cannot be overridden. Several settings are managed-only: `allowManagedHooksOnly`, `allowManagedPermissionRulesOnly`, `allowManagedMcpServersOnly`, `strictPluginOnlyCustomization`, sandbox restrictions.

13. **Sandboxing Integration**: Complementary OS-level enforcement. When sandboxing is enabled with `autoAllowBashIfSandboxed: true` (default), sandboxed Bash commands run without prompting. The sandbox boundary substitutes for the per-command prompt. Explicit deny rules still apply. Filesystem restrictions combine `sandbox.filesystem` with Read/Edit deny rules.

14. **Settings Precedence**: Managed > CLI args > local project > shared project > user. If denied at any level, no other level can allow it.

---

## Architecture/Mechanism Details

### Deny-Ask-Allow Pipeline
```
Input: Tool call
   |
   v
[Deny rules from ALL settings levels] -- match? --> BLOCK
   | no
   v
[Ask rules from ALL settings levels]  -- match? --> PROMPT
   | no
   v
[Allow rules from ALL settings levels] -- match? --> AUTO-APPROVE
   | no
   v
DEFAULT: PROMPT (unless mode says otherwise)
```

The key insight: deny rules from any settings scope (managed, CLI, project, user) are evaluated first. So a user-level deny of `Bash(git push *)` blocks `git push` even if project-level settings allow `Bash(*)`. This is the opposite of typical "last write wins" config merge -- it is a **conjunctive deny model** where any source can veto.

### Rule Syntax
- Bare tool name: `Bash`, `WebFetch`, `Read`, `Edit` -- matches all uses
- With specifier: `Tool(specifier)` -- fine-grained matching
- Bash: glob wildcard in specifier, word boundary with space, `:*` trailing suffix
- Read/Edit: gitignore patterns with four path types (absolute `//`, home `~`, root `/`, cwd `./` or bare)
- PowerShell: cmdlet aliases canonicalized before matching; AST-parsed for subcommand splitting
- MCP: `mcp__server__tool` (double underscore as separator)
- Agent: `Agent(Name)`

### Compound Command Handling
When a user selects "Yes, don't ask again" for a compound command like `git status && npm test`, Claude Code:
1. Parses the command into subcommands at `&&`, `||`, `;`, `|`, `|&`, `&`, newlines
2. Saves a separate rule for each subcommand that requires approval
3. For `cd path`, generates a Read rule for that path
4. Maximum 5 rules saved per compound command

### Read-Only Command Identification
Claude Code has a built-in whitelist of read-only Bash commands. These run without prompting in all modes. The set is not configurable; to require prompts for these, add ask/deny rules. Unquoted glob patterns are safe (no prompt) only for commands whose every flag is read-only.

### Process Wrapper Stripping
Before matching, Claude Code strips from the command: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, bare `xargs`. These are hardcoded, not configurable. `find -exec/-delete` and exec wrappers (`watch`, `setsid`, `ionice`, `flock`) always prompt.

### PreToolUse Hook Exit Codes
| Code | Meaning |
|------|---------|
| 0    | Skip prompt (let call proceed) |
| 1    | Force prompt |
| 2    | Force deny (takes precedence over allow rules) |

---

## Numbers & Benchmarks

- **Max 5 rules** saved per compound command approval
- **Built-in read-only cmd set**: ~15 commands (ls, cat, echo, pwd, head, tail, grep, find, wc, which, diff, stat, du, cd, read-only git)
- **6 permission modes**: default, acceptEdits, plan, auto, dontAsk, bypassPermissions
- **Settings levels**: 5 (managed, CLI, local project, shared project, user)
- **4 path pattern types**: absolute, home, root, cwd

No latency/performance benchmarks or throughput numbers are provided.

---

## Transfer to Lyra

### Core Idea: Deny-First, Multi-Layer Permission Architecture

Lyra should adopt a **deny-first, conjunctive permission model** where any policy source (system-level config, user overrides, per-instance settings) can veto a capability. This is architecturally distinct from "last write wins" merges -- it is a union-based deny set and an intersection-based allow set.

### Why It Matters for Lyra
Lyra's Agent Layer (router, delegator, subagent executor) needs to enforce capability boundaries. The Claude Code model shows how to:
- Categorize tools as read-only vs. mutating without per-tool annotations
- Parse compound commands to prevent subcommand smuggling
- Use PreToolUse hooks as an extension mechanism for custom policies
- Distinguish between "not explicitly allowed" (ask/prompt) and "explicitly denied" (block)

### Concrete Implementation Sketch for Lyra
```python
# Lyra PermissionEvaluator concept
class LyraPermissionEvaluator:
    deny_rules: list[Rule]   # union across all sources
    ask_rules: list[Rule]    # from any source
    allow_rules: list[Rule]  # intersection across all sources
    
    def evaluate(self, tool_call: ToolCall) -> PermissionDecision:
        if any(matches(r, tool_call) for r in self.deny_rules):
            return DENY
        if any(matches(r, tool_call) for r in self.ask_rules):
            return ASK
        if any(matches(r, tool_call) for r in self.allow_rules):
            return ALLOW
        return ASK  # default prompt
```

### Workstream Route: §4.6 - Safety / Layer Architecture
This maps to Lyra's Safety workstream. The permission engine would sit as a middleware layer in the Agent Runtime, between the Router (which parses intent) and the Executor (which dispatches tool calls). The hooks mechanism (§4.6.3) enables extensible policy without modifying core code.

### Impact and Effort
- **Impact**: High -- this is foundational safety infrastructure for any autonomous agent system
- **Effort**: Medium -- building a permission parser, rule engine, and hook system is non-trivial but well-scoped
- **Tier**: P1 (critical path for production deployment of autonomous agents)

---

## References

- https://code.claude.com/docs/en/permissions (this page)
- https://code.claude.com/docs/en/permission-modes
- https://code.claude.com/docs/en/hooks-guide
- https://code.claude.com/docs/en/sandboxing
- https://code.claude.com/docs/en/settings
- https://github.com/anthropics/claude-code/tree/main/examples/settings (starter configs)
