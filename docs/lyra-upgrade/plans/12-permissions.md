# Permissions — Plan (§4.12)

> Run 1 — June 3, 2026 | Phase 1: Deny-first permission evaluation, compound command parsing, credential scoping, agent-view security

## Plain-Language Summary

Lyra currently has no permission system — every tool call either succeeds or fails without user awareness. This plan implements a deny-first permission model where rules are evaluated in order: deny -> ask -> allow (first match wins). It covers compound command parsing (pipelines, redirects, chains checked per-subcommand), symlink-aware path traversal prevention, per-session permission overrides, and credential scoping (each worktree session gets only its explicitly granted credentials). The key insight for an agent harness: permissions must be both fine-grained (per-tool, per-argument) and session-isolated (different sessions can have different permissions).

## 1. Problem

BASELINE.md rates Permissions maturity = `none`. Lyra has zero permission infrastructure:
- **No deny-first evaluation**: Every tool call can be executed. No way to block dangerous operations.
- **No compound command parsing**: `rm -rf / && echo "done"` treated as one command. Should evaluate each subcommand independently.
- **No path traversal prevention**: Write to `/etc/passwd` from a project session is allowed because there's no path check.
- **No credential scoping**: All credentials available to all sessions. A research agent can access production API keys.
- **No session override**: `bypass` mode for a session affects all sessions. No per-session permission differentiation.
- **No agent view security**: Background/unwatched sessions can make dangerous tool calls without visibility.

## 2. Evidence Synthesis

### Claude Code Permissions (§3.1)
The reference architecture: deny-first evaluation, three-action system (allow/ask/deny), tool-level rules with `ToolName(specifier)` format. Key specifics:
- Evaluation order: deny -> ask -> allow (first match wins)
- Compound command parsing: `&&`, `||`, `;`, `|`, `&`, newlines all parsed. Each subcommand checked independently.
- Process wrapper stripping: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `xargs` (without flags) stripped before matching.
- Read-only commands: built-in set (`ls`, `cat`, `echo`, `pwd`, etc.) runs without prompt in every mode.
- Symlink handling: Allow rules check BOTH symlink path AND target. Deny rules block if EITHER matches.
- Permission modes: `default` (prompt on first use), `acceptEdits` (auto-approve file edits), `plan` (read-only), `auto` (auto-approve + background safety), `dontAsk` (auto-deny), `bypassPermissions` (skip all).
- JSON output capped at 10,000 characters.
- `additionalDirectories`: extends file access domain.

### Claude Code Sandboxing (§3.1)
OS-level enforcement: macOS Seatbelt, Linux bubblewrap. Dual-layer: permission rules + sandbox boundaries merged. Read/Edit deny rules merge with sandbox filesystem config. WebFetch deny rules merge with sandbox network allowlist.

### Claude Code Agent View Security (§3.1)
Background agents run with background permission mode (auto-deny tool calls that would prompt). File edit isolation via worktree by default.

### CaMeL (Google DeepMind, arXiv:2503.18813)
Dual-LLM architecture: Privileged LLM (sees task, generates plan) vs Quarantined LLM (sees data, executes). Capability-based data flow tracking with provenance + allowed readers. 77% tasks solved with provable security on AgentDojo (7% utility degradation).

### Progent (UC Berkeley, arXiv:2504.11703)
Least-privilege enforcement at tool-call level using symbolic policies. SMT solver (Z3) for deterministic policy comparison. Monotonic Confinement: action space can only shrink without approval. ASR reduction from 39.9% to 1.0% on AgentDojo. 94% of policy updates are narrowings (auto-approved); 6% expansions (need human).

### AgentDojo (ETH Zurich, arXiv:2406.13352)
Tool filter defense reduces ASR from 47.7% to 6.8% (most effective single defense). However, fails when overlapping tools needed. Inverse scaling: smarter models = more vulnerable.

### BREAKTHROUGH-ARCHITECTURE.md
Permissions in Capability Plane. Deny-first evaluation, auto-gated modes, sandbox integration.

## 3. Proposed Lyra Design

### 3.1 Deny-First Permission Evaluation

```python
@dataclass
class PermissionRule:
    action: Literal["allow", "deny", "ask"]
    tool: str                       # "Bash", "Write", "Read(/secrets/*)"
    user: str | None = None         # Specific user this applies to
    session: str | None = None      # Specific session this applies to
    condition: str | None = None    # Optional permission-rule expression
    priority: int = 0

    def matches(self, tool_name: str, tool_args: dict, context: PermissionContext) -> bool:
        # Tool matching: "Bash" matches any Bash call
        # "Write(/etc/passwd)" matches Write with specific path
        if self.tool == tool_name:
            return True
        if "(" in self.tool:
            name, specifier = self.tool.split("(", 1)
            specifier = specifier.rstrip(")")
            if name == tool_name and fnmatch.fnmatch(tool_args.get("file_path", ""), specifier):
                return True
        return False


class PermissionEngine:
    """Deny-first permission evaluation.

    Evaluation order:
    1. Collect all matching rules for the current tool call
    2. Sort by action order: deny (highest priority) -> ask -> allow
    3. Apply first match

    If no rule matches: default = ask (user prompt).
    """

    def __init__(self):
        self._rules: list[PermissionRule] = []
        self._session_overrides: dict[str, PermissionMode] = {}

    def evaluate(self, tool: str, args: dict, context: PermissionContext) -> PermissionDecision:
        matching = self._get_matching_rules(tool, args, context)

        # Check session override first
        session_mode = self._session_overrides.get(context.session_id)

        # Check for plan mode (read-only)
        if session_mode == "plan":
            if tool in ("Read", "Glob", "Grep", "WebFetch"):
                return PermissionDecision.ALLOW
            return PermissionDecision.DENY

        # Deny -> Ask -> Allow order
        for rule in sorted(matching, key=self._action_priority):
            if rule.action == "deny":
                return PermissionDecision.DENY
            if rule.action == "allow":
                return PermissionDecision.ALLOW
            # "ask" continues to check next rule, but default is ask anyway

        # Default: ask (unless session mode overrides)
        if session_mode == "auto":
            return PermissionDecision.AUTO_ALLOW
        if session_mode == "acceptEdits":
            if tool in ("Edit", "Write", "Read", "Glob", "Grep"):
                return PermissionDecision.AUTO_ALLOW
        if session_mode == "bypass":
            return PermissionDecision.BYPASS

        return PermissionDecision.ASK

    @staticmethod
    def _action_priority(rule: PermissionRule) -> int:
        return {"deny": 0, "ask": 1, "allow": 2}[rule.action]
```

### 3.2 Permission Modes

```python
class PermissionMode(str, Enum):
    DEFAULT = "default"           # Prompt on first use of each tool
    ACCEPT_EDITS = "acceptEdits"  # Auto-approve file edits + common commands
    PLAN = "plan"                 # Read-only: reads, no edits, no writes
    AUTO = "auto"                 # Auto-approve with background safety checks
    DONT_ASK = "dontAsk"          # Auto-deny unless pre-approved
    BYPASS = "bypassPermissions"  # Skip all prompts (with circuit breaker)

# Mode behavior matrix:
# | Mode | File Reads | File Edits | Bash | Web | Subagent |
# |------|-----------|------------|------|-----|----------|
# | default | ask 1st | ask 1st | ask 1st | ask 1st | ask 1st |
# | acceptEdits | auto | auto | auto | ask 1st | ask 1st |
# | plan | auto | deny | deny | deny | deny |
# | auto | auto | auto | auto | auto | auto |
# | dontAsk | deny | deny | deny | deny | deny |
# | bypass | auto | auto | auto | auto | auto |
```

### 3.3 Compound Command Parsing

```python
class CompoundCommandParser:
    """Parse compound shell commands and evaluate each subcommand independently.

    Supports: &&, ||, ;, |, &, newlines, subshells $(), ().
    """

    SPLIT_PATTERNS = [
        r"\|\|",   # OR
        r"&&",      # AND
        r";",      # Sequential
        r"\|",     # Pipe
        r"&",      # Background
    ]

    # Commands to strip before evaluation
    PROCESS_WRAPPERS = ["timeout", "time", "nice", "nohup", "stdbuf", "xargs"]

    @classmethod
    def parse(cls, command: str) -> list[str]:
        """Split compound command into individual subcommands."""
        result = [command]
        for pattern in cls.SPLIT_PATTERNS:
            expanded = []
            for cmd in result:
                expanded.extend(re.split(pattern, cmd))
            result = expanded
        return [cls.strip_wrappers(c.strip()) for c in result if c.strip()]

    @classmethod
    def strip_wrappers(cls, command: str) -> str:
        """Remove process wrappers (timeout, etc.) before matching."""
        parts = shlex.split(command)
        while parts and parts[0] in cls.PROCESS_WRAPPERS:
            parts = parts[1:]
            # Some wrappers take arguments (timeout 30 -> skip 30 too)
            if parts[0].isdigit():
                parts = parts[1:]
        return " ".join(parts)
```

### 3.4 Read-Only Commands

Built-in set that runs without prompt in every mode (including plan):

```python
READ_ONLY_COMMANDS = {
    "ls", "cat", "echo", "pwd", "head", "tail", "wc",
    "which", "type", "command", "file", "stat", "du", "df",
    "env", "printenv", "date", "cal",
    "find", "grep", "rg", "ag", "ack",
    "diff", "cmp", "comm",
    "python3 --version", "node --version", "npm --version",
    "curl --version", "git --version",
    "type", "where", "man", "help",
}

def is_read_only(command: str) -> bool:
    cmd = command.strip().split()[0] if command.strip() else ""
    return cmd in READ_ONLY_COMMANDS
```

### 3.5 Symlink Handling + Path Traversal Prevention

```python
class PathSafety:
    """Path traversal prevention with symlink awareness."""

    def __init__(self, allowed_bases: list[str]):
        self.allowed_bases = [os.path.abspath(p) for p in allowed_bases]

    def is_path_allowed(self, path: str, allow_symlinks_outside: bool = False) -> bool:
        """Check if a path is within allowed bases, considering symlinks.

        Allow rules check BOTH the symlink path AND the resolved target.
        If either is outside allowed bases, the path is NOT allowed.
        """
        resolved = os.path.abspath(os.path.realpath(path))

        # Check resolved path (following symlinks)
        for base in self.allowed_bases:
            if resolved.startswith(base):
                return True

        if not allow_symlinks_outside:
            # Also check the unresolved path (the symlink itself)
            unresolved = os.path.abspath(path)
            for base in self.allowed_bases:
                if unresolved.startswith(base):
                    return True

        return False
```

### 3.6 Per-Session Permission Overrides

```python
class SessionPermissionStore:
    """Per-session permission state, persisted across turns."""

    def __init__(self):
        self._sessions: dict[str, SessionPermissions] = {}

    def get_or_create(self, session_id: str) -> SessionPermissions:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionPermissions(session_id)
        return self._sessions[session_id]

    async def save(self, path: str):
        """Persist session permissions to disk."""
        data = {sid: perms.to_dict() for sid, perms in self._sessions.items()}
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def load(self, path: str):
        """Load session permissions from disk."""
        try:
            async with aiofiles.open(path) as f:
                data = json.loads(await f.read())
            for sid, perms_data in data.items():
                self._sessions[sid] = SessionPermissions.from_dict(sid, perms_data)
        except FileNotFoundError:
            pass


@dataclass
class SessionPermissions:
    session_id: str
    mode: PermissionMode = PermissionMode.DEFAULT
    remembered_decisions: dict[str, bool] = field(default_factory=dict)
    # "Bash:/usr/bin/git": True  (previously allowed)
    # "Write:/etc/passwd": False (previously denied)
    credential_scopes: list[str] = field(default_factory=list)
    # List of credential names available to this session
```

### 3.7 Credential Scoping

```python
class CredentialScope:
    """Each worktree session gets only its explicitly granted credentials.

    Credential sources:
    - Environment variables (.env files)
    - Credential helpers (git credential, keychain)
    - Secret manager integration

    Scoping:
    - Each session declares which credentials it needs in its worktree config
    - Only declared credentials are injected into the session's environment
    - Different sessions running simultaneously have disjoint credential sets
    """

    def __init__(self, credential_store: dict[str, str]):
        self._store = credential_store  # All available credentials
        self._grants: dict[str, set[str]] = {}  # session_id -> {credential_names}

    def grant(self, session_id: str, credential_names: list[str]):
        """Explicitly grant credentials to a session."""
        if session_id not in self._grants:
            self._grants[session_id] = set()
        self._grants[session_id].update(credential_names)

    def get_environment(self, session_id: str) -> dict[str, str]:
        """Get the environment dict for a session (only granted credentials)."""
        granted = self._grants.get(session_id, set())
        return {name: self._store[name] for name in granted if name in self._store}

    # Principle: a session never sees credentials it hasn't been explicitly granted.
    # This prevents: research agent accessing prod API keys, review agent using deploy tokens.
```

### 3.8 Agent View Security Guardrail

```python
class AgentViewSecurity:
    """Security guardrail for unwatched/background sessions.

    Key principle: background/unwatched sessions cannot use bypass or auto modes
    unless a human has explicitly accepted those modes for that session.
    """

    def can_use_mode(self, session_id: str, mode: PermissionMode,
                     is_background: bool, is_watched: bool) -> bool:
        """Check if a session can use the requested mode."""
        if mode in (PermissionMode.BYPASS, PermissionMode.AUTO):
            # Bypass/auto require explicit human accept
            if is_background and not is_watched:
                return False  # No one watching -> cannot auto-approve self
            if not self._human_accepted(session_id, mode):
                return False  # Human hasn't approved this mode for this session
        return True

    def human_accept(self, session_id: str, mode: PermissionMode):
        """Record human acceptance of a mode for a session."""
        self._acceptances[(session_id, mode)] = datetime.now()

    # This prevents: agent running in background switching to bypass mode
    # and making dangerous tool calls without oversight.
```

### 3.9 Rule Configuration Format

```yaml
# .lyra/permissions.yaml — Permission rules

permissions:
  # Deny rules (evaluated first)
  - action: deny
    tool: "Bash(rm -rf *)"
    reason: "Prevent accidental deletion"

  - action: deny
    tool: "Write(/etc/*)"
    reason: "System files are read-only"

  - action: deny
    tool: "Write"
    condition: "path == '/etc/passwd' || path == '/etc/shadow'"
    reason: "Never write to /etc/passwd or /etc/shadow"

  # Allow rules (evaluated last)
  - action: allow
    tool: "Read"
    condition: "path.startswith(project_dir)"

  - action: allow
    tool: "Bash"
    condition: "is_read_only(command)"

  - action: allow
    tool: "Bash(git *)"
  - action: allow
    tool: "Bash(python3 *)"
  - action: allow
    tool: "Bash(npm *)"

  # Allow specific directories
  - action: allow
    tool: "Write"
    condition: "path.startswith(project_dir + '/src')"
  - action: allow
    tool: "Write"
    condition: "path.startswith(project_dir + '/tests')"
```

### 3.10 Architecture Diagram

```mermaid
graph TB
    subgraph "Tool Call Flow"
        TC[Tool Call<br/>Name + Arguments]
        CC[Compound Command Parser<br/>Split && | ; &]
        PWS[Process Wrapper Stripper<br/>Strip timeout/nice/nohup]
    end

    subgraph "Permission Engine (§4.12)"
        PM[Permission Mode<br/>default/acceptEdits/plan/auto/...]
        RULES[Rule Evaluation<br/>Deny → Ask → Allow]
        ROC[Read-Only Check<br/>Built-in command set]
        PATH[Path Safety<br/>Symlink-aware traversal check]
        CRED[Credential Scope<br/>Session-specific grants]
        AVS[Agent View Security<br/>Background session guard]
    end

    subgraph "Decision"
        ALLOW[ALLOW]
        DENY[DENY]
        ASK[ASK → User Prompt]
        AUTO[Auto-Allow<br/>Background safety check]
    end

    subgraph "Policy Sources"
        CONFIG[permissions.yaml]
        SESSION[Session Override]
        MODE[Mode Selection]
        HISTORY[Previous Decisions<br/>Session Memory]
    end

    TC --> CC
    CC --> PWS
    PWS --> RULES

    CONFIG --> RULES
    SESSION --> PM
    MODE --> PM
    PM --> RULES
    HISTORY --> RULES

    RULES --> ROC
    RULES --> PATH
    RULES --> CRED
    RULES --> AVS

    ROC --> ALLOW
    PATH -->|Blocked| DENY
    CRED -->|Missing| DENY
    AVS -->|Block| DENY

    RULES --> ALLOW
    RULES --> DENY
    RULES --> ASK
    RULES --> AUTO
```

## 4. Data Model

```python
@dataclass
class PermissionRule:
    action: Literal["allow", "deny", "ask"]
    tool: str
    user: str | None = None           # Specific user
    session: str | None = None        # Specific session
    condition: str | None = None      # Permission expression
    priority: int = 0
    reason: str = ""                  # User-facing reason


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    AUTO_ALLOW = "auto_allow"          # Background safety check passed
    BYPASS = "bypass"                 # Circuit breaker still applies


@dataclass
class PermissionContext:
    session_id: str
    user_id: str | None = None
    project_dir: str = ""
    is_background: bool = False
    is_watched: bool = True
    mode: PermissionMode = PermissionMode.DEFAULT
```

## 5. Build Outline

### Phase 1a — Permission Engine (Week 1)
- [ ] Implement `PermissionEngine` with deny-first evaluation in `src/permissions/engine.py`
- [ ] Implement `PermissionRule` dataclass with `matches()` method
- [ ] Implement `PermissionMode` enum and mode-to-behavior mapping
- [ ] Implement `PermissionDecision` enum
- [ ] **Dependency:** None

### Phase 1b — Compound Command Parsing (Week 1-2)
- [ ] Implement `CompoundCommandParser` with all split patterns
- [ ] Implement process wrapper stripping (`timeout -> nice -> actual_command`)
- [ ] Implement read-only command set
- [ ] Unit tests: complex compound commands, nested subshells
- [ ] **Dependency:** Phase 1a

### Phase 1c — Path Safety + Symlink Handling (Week 2)
- [ ] Implement `PathSafety` with symlink-aware path checking
- [ ] Allowed base paths from project configuration
- [ ] `additionalDirectories` extension points
- [ ] Unit tests: symlink chains, directory traversal, edge cases
- [ ] **Dependency:** Phase 1a

### Phase 1d — Session Permissions + Credential Scoping (Week 2-3)
- [ ] Implement `SessionPermissionStore` with disk persistence
- [ ] Implement per-session mode override
- [ ] Implement `CredentialScope` for credential isolation per worktree
- [ ] Implement `AgentViewSecurity` guardrail
- [ ] **Dependency:** Phase 1a

### Phase 1e — Configuration + Integration (Week 3-4)
- [ ] Implement YAML config parser for permission rules
- [ ] Implement config merge across scopes (user -> project -> local)
- [ ] Wire permission engine into Tool Registry (§4.6) tool call path
- [ ] Wire into Hook System (§4.10) PermissionRequest/PermissionDenied/PermissionGranted events
- [ ] Write `premission` CLI command for viewing/testing rules
- [ ] Integration tests: full tool call flow with permissions
- [ ] **Dependency:** Phase 1b, 1c, 1d, §4.6 Tools

## 6. Multi-Provider Note

Permissions are harness-level, not provider-level. The permission engine sits BEFORE the provider encoding layer:
- Tool calls are evaluated by the permission engine in Lyra's internal `ToolCall` format
- Only allowed tool calls are encoded into provider-specific formats
- Denied tool calls never reach the provider
- This ensures uniform permission enforcement regardless of whether the backend is Claude, DeepSeek, GPT, or open-weights

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Compound command parser misses edge cases | Medium | High | Aggressive test suite; fall through to `ask` on unparseable |
| Symlink check breaks legitimate symlink use | Medium | Medium | `allow_symlinks_outside` flag for project-aware symlinks |
| Credential scoping too restrictive breaks workflows | High | Medium | Clear error messages; per-credential grant requests |
| Agent view guardrail blocks legitimate auto mode | Low | Medium | Manual accept flow; session-level bypass after accept |
| Permission rule YAML too complex for users | High | Medium | Provide common rule templates; `--init-permissions` command |
| Circuit breaker on bypass mode blocks critical operations | Low | High | Circuit breaker only blocks `/` and `~` deletion; everything else passes |

## 8. (A) Parity vs (B) Breakthrough

### (A) Parity — What Claude Code already does
- Deny-first evaluation: deny -> ask -> allow
- Tool-level rules with `ToolName(specifier)` format
- Compound command parsing (&&, ||, ;, |, &, newlines)
- Process wrapper stripping (timeout, time, nice, nohup, stdbuf, xargs)
- Read-only command set
- Symlink-aware path matching (allow checks both, deny blocks either)
- Permission modes: default, acceptEdits, plan, auto, dontAsk, bypass
- Config merge across user/project/local scopes

### (B) Breakthrough — What Lyra adds
- **Credential scoping per worktree session** — Each parallel session gets only explicitly granted credentials. Claude Code has sessions but no cross-session credential isolation.
- **Agent View security guardrail** — Background/unwatched sessions cannot use bypass/auto without prior human accept. Prevents background agent privilege escalation.
- **SMT-based monotonic confinement integration** (Phase 2) — Progent-style initial policy generation + Z3 expansion check. Lyra's permission system can auto-generate least-privilege policies from task descriptions.
- **Per-session permission persistence** — Remembered decisions persist across turns and survive session resume. Different sessions have independent decision histories.

## 9. Baseline Delta

| Dimension | Before (Lyra current) | After (with Permissions) |
|-----------|----------------------|--------------------------|
| Evaluation model | None (all allowed) | Deny-first: deny -> ask -> allow |
| Tool-level rules | None | `ToolName(specifier)` with fnmatch |
| Compound commands | None | Full parsing of &&, ||, ;, |, & |
| Read-only commands | None | Built-in set in every mode |
| Path traversal | None | Symlink-aware path checking |
| Credential isolation | None (all shared) | Per-session credential scoping |
| Session overrides | None | Per-session mode + decision history |
| Background security | None | Unwatched -> no bypass/auto without accept |
| Config format | None | YAML with merge across scopes |

## 10. Expert Review

### Reviewer 1: Security Engineer
"The deny-first model is correct but the default behavior (no matching rule = `ask`) is too permissive for an unattended fleet. I'd add a `defaultAction` config option so operators can set `defaultAction: deny` for production deployments. The compound command parser needs to handle heredocs (`<<EOF`), backticks, and `$(...)` subshells — these are common in CI scripts. The process wrapper stripping is a nice touch: without it, `timeout 30 rm -rf /` wouldn't match the `rm` deny rule."

### Reviewer 2: Systems Architect
"Credential scoping per worktree session is the right design but the implementation is high-risk: if credential isolation leaks (one session reads another's env vars), it's a security incident. I'd implement it at the OS level: use separate env vars per subprocess, not a shared credential store. The `.lyrainclude` file concept from the worktree plan is where credential grants are declared. For the circuit breaker on bypass mode: Claude Code's approach is correct — only block dangerous read/write to `/` and `~`."

### Reviewer 3: User Experience Designer
"The YAML permission rules format is powerful but intimidating. Provide a `lyra init-permissions` command that generates reasonable defaults. The `ask` mode is annoying for frequent operations — make sure remembered decisions persist across turns (per Claude Code: first use prompts, subsequent uses auto-approve within session). The permission modes need clear UI indicators: show `[plan]` or `[bypass]` in the status bar so users always know what mode they're in."

## 11. References

1. Claude Code Permissions — code.claude.com/docs/en/permissions. Deny-first evaluation, compound parsing, symlink handling.
2. Claude Code Sandboxing — code.claude.com/docs/en/sandboxing. OS-level enforcement, dual-layer (permissions + sandbox).
3. CaMeL — arXiv:2503.18813 (Google DeepMind). Dual-LLM architecture, capability tracking, 77% provable security.
4. Progent — arXiv:2504.11703 (UC Berkeley). SMT-based monotonic confinement, 1.0% ASR on AgentDojo.
5. AgentDojo — arXiv:2406.13352 (ETH Zurich). Tool isolation most effective defense (6.8% ASR).
6. BREAKTHROUGH-ARCHITECTURE.md — Permissions in Capability Plane, deny-first evaluation.
7. BASELINE.md — Lyra current state: `none` maturity for §4.12 Permissions.

## 12. Changelog
- Run 1: Initial plan — deny-first evaluation, compound command parsing, path safety, credential scoping, agent view security
