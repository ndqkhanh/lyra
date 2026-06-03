# Permission Bridge -- How It Works

> Runtime authorization primitive that intercepts every tool call with 4 authorization modes, scope-based allowlists (file/net/command), an unwatched escalation guard, and full audit logging. Code-enforced, not prompt-based.
> **Block:** 05 | **Phase:** 1 (Core Infrastructure) | **Depends on:** Agent Loop | **Provides:** `resolve_lyra_decision()`, `PermissionStack`, `StackDecision`

## The Authorization Function

Every tool call flows through `resolve_lyra_decision()`, which combines mode-based rules, a 3-guard pipeline, and risk classification into a single `StackDecision`:

```python
@dataclass(frozen=True)
class StackDecision:
    block: bool               # True = deny execution
    guard: str = ""           # Which guard blocked: "destructive" | "secrets" | "injection" | "scope"
    reason: str = ""          # Human-readable explanation
    mode: LyraMode | None = None
```

The LLM never sees the approval logic, mode definitions, or guard code. It cannot reason around or manipulate the enforcement layer.

## 4 Authorization Modes

| Mode | Guards Active | Read-Only Filter | Use Case |
|------|---------------|-------------------|----------|
| **LOCKED** | Yes | Yes (whitelist only) | Planning dry-runs, investigation |
| **DEFAULT** | Yes | No | General development |
| **YOLO** | No | No | Trusted bulk operations |
| **BYPASS** | No | No | Batch processing |

Mode transitions are one-directional: a subagent in DEFAULT cannot escalate to BYPASS. This prevents privilege escalation within a session.

## Scope Rules (Allowlists)

Three independent allowlists govern tool access:

### File Allowlist

```python
FILE_ALLOWLIST = {
    "read":  Set["Read", "Grep", "Glob", "LSP", "List"],
    "write": Set["Write", "Edit", "Create", "Delete"],
    "exec":  Set["Bash", "Python", "Execute"],
    "net":   Set["WebFetch", "WebSearch", "Curl"],
}

# Per-mode filtering
def allowed_tools(mode: LyraMode) -> Set[str]:
    if mode == LyraMode.LOCKED:
        return FILE_ALLOWLIST["read"]  # read-only
    return FILE_ALLOWLIST["read"] | FILE_ALLOWLIST["write"] | FILE_ALLOWLIST["exec"] | FILE_ALLOWLIST["net"]
```

### Command Allowlist

Plan mode permits only a built-in set of commands: `ls`, `cat`, `echo`, `pwd`, `grep`, `diff`, and similar. Requiring approval for every `ls` would create >100 interruptions per session with zero safety benefit.

### Network Allowlist

Domains and URL patterns for WebFetch/WebSearch tools. By default, only documentation domains (`docs.*`, `pypi.org`, `npmjs.com`, `github.com`, etc.) are allowed. Other domains escalate to user approval.

## Guard Pipeline (3 guards, first-block-wins)

```
Tool Call → Mode Lookup → Read-Only Check → Guard 1: Destructive → Guard 2: Secrets → Guard 3: Injection → Decision
```

| Order | Guard | Method | Blocks | Latency |
|-------|-------|--------|--------|---------|
| 1 | Destructive | Regex patterns | `rm -rf /`, fork bombs, DROP TABLE, chmod 777 | <500us |
| 2 | Secrets | Regex + scoring | AWS keys, GitHub PATs, SSH private keys | <300us |
| 3 | Injection | Pattern matching | Prompt injection in tool args, delimiter smuggling | <400us |

**Compound command parsing**: Shell operators (`&&`, `||`, `;`, `|`) split commands into individual subcommands. Each is evaluated independently. `rm -rf / && echo "done"` blocks the destroy while allowing the echo.

## Unwatched Escalation Guard

If the safety monitor detects that a session has been compromised (e.g., sudden spike in blocked destructive commands, rogue agent behavior), it can dynamically escalate the mode:

```
DEFAULT → LOCKED   (compromised session)
YOLO    → DEFAULT  (if safety risk detected)
```

Escalation is enforced at the resolver level, not by trust. Subagents inherit the parent mode and cannot escalate to a more permissive one.

## Audit Log

Every decision is logged as a structured JSONL event:

```jsonl
{"ts": 1717201234.567, "session": "sess_abc", "tool": "bash", "action": "rm -rf /data",
 "mode": "LOCKED", "guard": "destructive", "block": true, "reason": "Destructive pattern: rm -rf"}
{"ts": 1717201235.012, "session": "sess_abc", "tool": "grep", "args": "-r \"API_KEY\" .",
 "mode": "DEFAULT", "guard": "secrets", "block": true, "reason": "Potential secret in args"}
```

Audit logs feed into the Observability block (Block 11) and the Safety Monitor (Block 12) for real-time alerting and post-hoc analysis.

## Performance

| Metric | P50 | P99 |
|--------|-----|-----|
| Mode lookup | <10us | <50us |
| Full stack check (block) | <200us | <600us |
| Full stack check (no block) | <400us | <950us |
| Total authorization overhead | ~760us | ~1.8ms |
| Throughput (single core) | ~1,300 checks/s | -- |

The permission bridge is not a bottleneck: at <0.2% of total per-step latency, it is effectively free in the critical path.

## Security Properties

- **Unprivileged LLM**: The model never sees approval logic or guard code.
- **Fail-closed**: No guard match = ask user (not allow). A crash blocks execution.
- **Monotonic security**: Each guard only increases restriction. No guard can override a block from a previous guard.
- **No TOCTOU**: Decision and execution are atomic within the same call.
- **Symlink-aware path validation**: Checks both the unresolved path and the resolved symlink target.

## Related Documents

- **Concepts:** [Permission Bridge](../concepts/09-permission-bridge.md), [Tools and Hooks](../concepts/02-tools-and-hooks.md)
- **Architecture:** [Safety and Security](../architecture/08-safety-security.md), [Architecture Overview](../architecture/11-architecture-overview.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Plan Mode](04-plan-mode.md), [Hooks and TDD Gate](06-hooks-tdd.md), [Safety Monitor](12-safety-monitor.md), [Subagent Worktree](08-subagent-worktree.md)

---

*References: SemaClaw (arXiv:2604.11548), Greshake et al. "Not What You've Signed Up For" (arXiv:2302.12173)*
