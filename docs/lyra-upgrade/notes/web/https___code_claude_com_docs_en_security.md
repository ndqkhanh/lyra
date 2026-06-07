# Security (Anthropic / Claude Code Docs)

Source: https://code.claude.com/docs/en/security
Fetched: 2026-06-07

---

## Key Technical Claims

1. **Permission-based architecture**: Claude Code is strict read-only by default; any write, execute, or network action requires explicit user approval. Users can configure per-action or auto-approve patterns.

2. **Sandboxed bash tool**: Commands can be run with filesystem and network isolation via `/sandbox`, reducing permission prompts while maintaining security boundaries.

3. **Write-access scoping**: Claude Code can only write to the folder where it was started and its subfolders. It can read files outside the working directory (system libs, dependencies) but *cannot* write to parent directories without explicit permission. This creates a clear security boundary.

4. **Prompt injection mitigations**: Multi-layer defense -- permission system, context-aware instruction analysis, input sanitization, command blocklist (`curl`, `wget` blocked by default), command injection detection (suspicious commands require manual approval even if previously allowlisted), and fail-closed matching (unmatched commands default to manual approval).

5. **Isolated context windows for web fetch**: Web fetch uses a separate context window to prevent malicious prompts from injected content reaching the main session.

6. **Trust verification**: First-time codebase runs and new MCP servers require explicit trust acceptance before proceeding.

7. **Accept Edits mode**: Auto-approves file edits and a fixed set of filesystem Bash commands (`mkdir`, `touch`, `rm`, `mv`, `cp`, `sed`) for paths in the working directory. Other Bash commands and out-of-scope paths still prompt.

8. **Cloud execution isolation**: Each cloud session runs in an isolated, Anthropic-managed VM with network access controls, credential protection via secure proxy, branch restrictions on git push, audit logging, and automatic cleanup after session completion.

9. **Remote Control credential model**: Multiple short-lived, narrowly scoped credentials, each limited to a specific purpose and expiring independently, to limit blast radius of any single compromised credential. Code execution stays local; only data flows through Anthropic API over TLS.

10. **Security guidance plugin**: Optional in-session plugin that has Claude review and fix vulnerabilities in its own code changes during the session.

---

## Architecture / Mechanism Details

- **Default deny**: All actions require permission except read-only file access within the project directory.
- **Allowlisting**: Users can create per-user, per-codebase, or per-organization allowlists for frequently used safe commands, mitigating prompt fatigue.
- **Blocklist priority**: Even for allowed commands, `curl` and `wget` are blocked by default. If explicitly allowed, permission pattern limitations still apply.
- **Natural language descriptions**: For complex bash commands, Claude Code generates NL descriptions to help users understand what a command does before approving it.
- **MCP security**: MCP server list is configured in source-controlled settings. Anthropic reviews connectors against listing criteria for the directory but does not security-audit third-party MCP servers.
- **Credential management**: API keys and tokens are encrypted at rest.
- **Managed settings**: Organizations can enforce standards via managed settings files, share approved permission configs through version control, and monitor usage through OpenTelemetry metrics.
- **ConfigChange hooks**: Allows auditing or blocking settings changes during sessions.
- **Dev containers**: Recommended for additional isolation on sensitive repositories.

---

## Numbers & Benchmarks

- **Blocked by default**: `curl`, `wget`
- **Auto-approved (Accept Edits mode)**: `mkdir`, `touch`, `rm`, `mv`, `cp`, `sed`
- **Write scope**: Working directory + subdirectories only (read can go wider)
- **Certifications**: SOC 2 Type 2, ISO 27001 (see Anthropic Trust Center)
- **Cloud sessions**: Isolated VMs, automatic cleanup on session end
- **Remote Control**: TLS-encrypted data flow, multiple short-lived scoped credentials
- **Security reporting**: Via HackerOne program

---

## Transfer to Lyra

### One Idea: Permission-Tiered Agent Sandbox with Write-Scoping

Claude Code's most transferable mechanism is its **tiered permission model** combined with **filesystem write-scoping**. The key insight: restrict write operations to the project directory by default, require explicit approval for network/risky operations, and allow read access to system paths. This is cleaner than a binary "all or nothing" approach and preserves user autonomy while preventing accidental damage.

### Why This Matters for Lyra

Lyra's autonomous operation mode needs a permission model that:
- Allows productive work (file writes, command execution) without constant prompting
- Prevents catastrophic actions (writing outside project scope, unconstrained network access, arbitrary code execution)
- Provides clear audit trails for all approvals
- Can be configured per-environment (dev vs. prod)

### Workstream Route

This maps most naturally to the **Safety & Guardrails** workstream. The Claude Code sandbox + permissions pattern directly informs Lyra's safety layer design -- specifically how to balance autonomy with containment.

### Effort / Impact

- **Impact**: High (foundational safety mechanism, required for autonomous operation)
- **Effort**: Medium (implementation is not trivial but the pattern is well-understood)
- **Tier**: Tier 1 (must-have for production deployment)

### Suggested Lyra sections

- §4.4 (Safety Guardrails) -- Permission tiering, write-scoping, command blocklist
- §4.3 (Reliability & Verification) -- Audit logging, trust verification, ConfigChange hooks
