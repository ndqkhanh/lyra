# Claude Code Settings (Anthropic)

Fetched: 2026-06-07
URL: https://code.claude.com/docs/en/settings

---

## Key Technical Claims

1. **Four-tier configuration scopes with strict precedence:** Managed (highest, cannot be overridden) > CLI flags > Local > Project > User. Permission rules *merge* across scopes rather than overriding.

2. **Hot-reload for nearly all keys:** `permissions`, `hooks`, credential helpers, `apiKeyHelper` reload without restart. A `ConfigChange` hook fires for each detected change. Only `model` and `outputStyle` require restart.

3. **Organizational IT controls are first-class:** Managed settings deployable via Anthropic server push, MDM (Jamf/Kandji for macOS, Group Policy/Intune for Windows), or file-based (`managed-settings.json` at `/Library/Application Support/ClaudeCode/` on macOS, `/etc/claude-code/` on Linux, `C:\Program Files\ClaudeCode\` on Windows).

4. **Drop-in directory convention:** `managed-settings.d/` alongside `managed-settings.json` merges all `*.json` files alphabetically (systemd convention). Scalar values are overridden by later files; arrays concatenated and de-duplicated; objects deep-merged. Hidden files (dot-prefixed) are ignored.

5. **Auto-backup:** Timestamped backups of configuration files automatically created; five most recent retained.

6. **Effort level persistence:** `effortLevel` setting persists `"low"`, `"medium"`, `"high"`, or `"xhigh"` across sessions, toggleable at runtime via `/effort`.

7. **Self-contained CLAUDE.md-style managed memory:** `claudeMd` setting (managed-only) serves as org-wide memory/instructions, ignored in user/project/local scopes.

---

## Architecture/Mechanism Details

### Scope Model

| Scope | Location | Shared? |
|-------|----------|---------|
| Managed | Server-pushed, MDM policies, or `managed-settings.json` | Yes (IT-deployed) |
| User | `~/.claude/settings.json` | No (personal) |
| Project | `.claude/settings.json` | Yes (committed to git) |
| Local | `.claude/settings.local.json` | No (gitignored) |

Precedence: Managed > CLI args > Local > Project > User. Permission rules are an exception -- they merge rather than override (union semantics for allow/deny).

### Merge Semantics for Drop-in Directories
- Scalars: last file wins
- Arrays: concatenated and de-duplicated
- Objects: deep-merged

### Managed Setting Delivery Mechanisms
1. **Server-managed:** Pushed from Claude.ai admin console via Anthropic servers.
2. **MDM/OS-level:** macOS `com.anthropic.claudecode` preferences domain (Jamf/Kandji); Windows `HKLM\SOFTWARE\Policies\ClaudeCode` registry key (Group Policy/Intune).
3. **File-based:** `managed-settings.json` + `managed-settings.d/*.json` in OS-specific system directories.
4. **Dynamic:** `policyHelper` executable (v2.1.136+) computes managed settings at startup.

### Settings Lifecycle
- Most keys hot-reload on file change; `ConfigChange` hook notifies agents.
- `model` and `outputStyle` require session restart (use `/model` or `/clear` mid-session).
- `ultracode` is session-only -- never read from `settings.json`.

### Notable Security/Compliance Controls
- `forceLoginMethod`: Lock to `claudeai` or `console` authentication; blocks API key sessions.
- `forceLoginOrgUUID`: Require login to specific org UUID(s).
- `allowManagedHooksOnly`: Only managed/SDK/force-enabled plugin hooks load; user/project hooks blocked.
- `allowManagedPermissionRulesOnly`: Prevents user/project `allow`/`ask`/`deny` rules.
- `strictPluginOnlyCustomization`: Block skills/agents/hooks/MCP from user/project scopes.
- `deniedMcpServers` takes precedence over `allowedMcpServers`.
- `requiredMinimumVersion` / `requiredMaximumVersion`: Version floor and ceiling enforced at startup.

---

## Numbers and Benchmarks

- **`cleanupPeriodDays`:** Default 30 days, minimum 1 day. Controls session file and orphaned subagent worktree cleanup.
- **`feedbackSurveyRate`:** 0-1 probability float. 0 suppresses session quality surveys entirely.
- **`maxSkillDescriptionChars`:** Default 1,536 characters per skill `description` + `when_to_use`.
- **`skillListingBudgetFraction`:** Default 0.01 (1% of context window). Truncation info visible via `/doctor`.
- **`autoUpdatesChannel`:** `"stable"` delivers builds ~1 week old, skips major regressions; `"latest"` is the default (bleeding edge).
- **Backup retention:** 5 most recent timestamped configuration backups.
- **`autoMemoryEnabled`:** Default `true` (toggleable via `/memory`).
- **Managed deployment templates:** Available at github.com/anthropics/claude-code/tree/main/examples/mdm.

---

## Transfer to Lyra

### One Transferable Idea: Layered Configuration with Merge Semantics

Claude Code's four-scope config system (Managed > CLI > Local > Project > User) with well-defined merge behavior (scalar override, array concat+dedup, object deep-merge) is a battle-tested pattern Lyra should adopt directly.

Lyra's current config is single-file and single-scope. This creates pain points:
- No way to separate team-shared settings from personal overrides.
- No mechanism for env-specific or deployment-specific config.
- No merge protocol when multiple sources contribute settings.

### Proposed Route: SS4.2 (Configuration and Dependency Management)

Add a subsection to the configuration architecture that defines:

1. **Tiers:** System defaults > Deployment env (Docker/K8s manifest) > Project `.lyra/config.yml` > User `~/.lyra/config.yml` > Runtime (CLI flags / env vars).
2. **Merge semantics:** Documented as: scalars override, arrays uniq-merge, objects deep-merge, with the highest precedence taking final say.
3. **Hot-reload:** Most operational keys (agent timeouts, retry limits, model selection) should hot-reload via a `ConfigChange` event, similar to Claude Code's hook.
4. **Drop-in dirs:** Support `config.d/*.yml` alongside the main config file for modular decomposition.

This single pattern eliminates the most common config friction in Lyra without adding complexity -- the semantics are already proven in the field.
