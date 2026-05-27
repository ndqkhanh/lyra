# Lyra Block 04 — PermissionBridge

SemaClaw's load-bearing contribution: behavioral safety as a **runtime primitive**, not an LLM decision. Every tool call, no matter the mode, flows through a single `decide(call, session) → Decision` code path. The LLM never holds the keys.

Reference: [SemaClaw paper arXiv:2604.11548 § PermissionBridge](../../../../docs/54-semaclaw-general-purpose-agent.md#permissionbridge), [Permission-modes dive](../../../../docs/06-permission-modes.md).

## Responsibility

1. Authoritative authorization of every tool invocation.
2. Combine mode + policy + risk classifier into one `Decision`.
3. Surface user-visible approval prompts in `ask` mode.
4. Implement `park` for DAG Teams so parallel work is not blocked by a single permission.
5. Emit a `permission.decide` trace event with HIR tag.

## Decision types

```python
class Decision(StrEnum):
    ALLOW = "allow"   # proceed silently
    ASK   = "ask"     # block on user approval
    DENY  = "deny"    # do not proceed
    PARK  = "park"    # defer; downstream may proceed

@dataclass
class PermissionDecision:
    decision: Decision
    reason: str                # human-readable, stable ids
    suggestion: Optional[str]  # what the agent could do instead
    elevate_to: Optional[PermissionMode]  # mode the user could switch to
    cost_of_approval: Optional[str]       # "no-op" | "reversible" | "irreversible"
```

## Permission modes (v1 set)

Eight modes, ordered roughly by capability:

| Mode | Reads | Writes to worktree | Writes outside worktree | Bash | Network | Typical use |
|---|---|---|---|---|---|---|
| `plan` | ✅ | ❌ (deny) | ❌ (deny) | ❌ (deny) | only allowlisted | Planner / explore |
| `triage` | ✅ | ask | ❌ | ask | ask | Initial investigation |
| `default` | ✅ | ask | ❌ | ask | ask | Normal interactive |
| `acceptEdits` | ✅ | ✅ | ❌ | ask (risk-classified) | ask | Steady execution |
| `red` | ✅ | tests only | ❌ | ask | ❌ | TDD RED phase |
| `green` | ✅ | tests + src | ❌ | ask | ❌ | TDD GREEN phase |
| `refactor` | ✅ | src (coverage-guarded) | ❌ | ask | ❌ | Refactor phase |
| `bypass` | ✅ | ✅ | ask | ask | ask | Power user (friction prompt) |

`bypass` deliberately is not a silent-allow-all: destructive patterns still deny; secrets still scanned; Stop hook still runs.

### Mode transitions

LLM cannot change mode unilaterally. Transitions happen via:

- CLI flag / subcommand (`lyra green`, `lyra refactor`).
- Plan Mode → execution transition (triggered by plan approval).
- Explicit user request in-session (`switch mode to acceptEdits`) which goes through approval.
- Hook-driven (phase transitions after RED proof).

Every transition emits `permission.mode_change` trace event with before/after + reason.

## Decision pipeline

```python
def decide(call: ToolCall, session: Session) -> PermissionDecision:
    # 1) Mode check — the coarse gate
    mode_verdict = permission_mode_table.lookup(session.mode, call.name, call)
    if mode_verdict.decision == Decision.DENY:
        return mode_verdict

    # 2) Policy rules (user + repo + organization)
    policy_verdict = policy_engine.evaluate(call, session)
    if policy_verdict.decision == Decision.DENY:
        return policy_verdict

    # 3) Risk classifier (rules + ML)
    risk = risk_classifier.score(call, session)
    if risk.score > session.config.risk_deny_threshold:
        return PermissionDecision(Decision.DENY, reason=f"risk: {risk.label}")
    if risk.score > session.config.risk_ask_threshold and mode_verdict.decision == Decision.ALLOW:
        mode_verdict = PermissionDecision(Decision.ASK, reason=f"risk: {risk.label}")

    # 4) DAG parking (only in dag-teams)
    if mode_verdict.decision == Decision.ASK and session.harness == "dag-teams":
        if session.config.dag_teams.park_on_ask:
            return PermissionDecision(Decision.PARK,
                                      reason=mode_verdict.reason,
                                      elevate_to=mode_verdict.elevate_to)

    return mode_verdict
```

Decision order is: **mode → policy → risk → parking**. Each layer can only *deny more*, never *allow more*.

## Mode × tool lookup table

Concrete slice (full table in `permissions/modes.py`):

```yaml
plan:
  Read: allow
  Grep: allow
  Glob: allow
  WebFetch: ask-allowlist
  Edit: deny
  Write: deny
  Bash: deny
  Spawn: deny
  AskUser: allow
  Skill: read-only
default:
  Read: allow
  Edit: ask
  Write: ask
  Bash:
    safe_patterns: allow   # e.g. pytest, vitest, go test
    mutating_patterns: ask
    destructive_patterns: deny  # regardless of mode
  Spawn: ask
acceptEdits:
  Edit: allow
  Write: allow
  Bash:
    safe_patterns: allow
    mutating_patterns: ask
    destructive_patterns: deny
red:
  Edit:
    path_in_test_globs: allow
    path_in_src_globs: deny
  Write:
    path_in_test_globs: allow
    path_in_src_globs: deny
green:
  Edit:
    path_in_src_globs:
      if_recent_red_proof: allow
      else: deny
    path_in_test_globs: allow
refactor:
  Edit:
    path_in_src_globs:
      if_coverage_preserved: allow
      else: ask
```

Destructive patterns (unbypassable except in `bypass`):

```yaml
bash_destructive_patterns:
  - "rm\\s+-rf\\s+/"
  - "rm\\s+-rf\\s+\\$HOME"
  - "git\\s+push\\s+.*--force(-with-lease)?\\s+.*\\b(main|master)\\b"
  - ":(){ :|:& };:"            # fork bomb
  - "dd\\s+if=.*\\s+of=/dev/"
  - "mkfs"
```

## Risk classifier

Two-part:

1. **Rule-based** — regex + AST checks. Fast, explainable, deterministic. The source of truth for "never allow" items.
2. **ML-based** — small sklearn logistic regression on (tool name, arg shape, recent history). Outputs score ∈ [0, 1]. Retrainable from labeled traces (nightly in CI).

Features for ML include:

- Tool name one-hot.
- Arg length, arg entropy, arg token distribution.
- Current TDD phase.
- Recent tool-call sequence (trigrams).
- Recent hook block rate.
- File-path depth + globs matched.

Training data: labeled traces from internal eval set plus red-team fixtures. Training code in `scripts/train_risk_classifier.py`.

ML score **cannot override** a deterministic deny — it can only escalate allow→ask→deny.

## Policy engine

User / repo / org-level policies in YAML:

```yaml
# .lyra/policy.yaml
- name: no-edits-to-generated-protos
  when:
    tool: [Edit, Write]
    path_glob: "**/*.pb.go"
  decision: deny
  reason: generated file

- name: bash-curl-egress-allowlist
  when:
    tool: Bash
    command_regex: "\\bcurl\\b"
  require:
    hostname_in: [github.com, pypi.org, npmjs.com]
  else:
    decision: ask

- name: prod-config-requires-bypass
  when:
    tool: [Edit, Write]
    path_glob: "deploy/prod/**"
  decision: ask
  elevate_to: bypass
```

Policies are:

- Hot-reloadable (daemon watches file).
- Validated at load time (linter catches ambiguity / cycles).
- Versioned (policy version pinned per session for reproducibility).

## Approval UX

Interactive approval prompt carries context:

```
┌── Approval required ──────────────────────────────────────────────┐
│  Tool:     Edit                                                   │
│  Path:     src/auth/token.ts                                      │
│  Reason:   default mode requires approval for write               │
│  Elevate:  Switch to `acceptEdits` for this session? [y/N/always] │
│                                                                   │
│  Preview of change:                                               │
│   - const expires = 3600                                          │
│   + const expires = 86400                                         │
│                                                                   │
│  [a]pprove  [d]eny  [q]uestion  [x]cancel                         │
└───────────────────────────────────────────────────────────────────┘
```

Power features:

- `always` upgrades mode for the rest of this session.
- `question` opens a dialog to ask the agent why it wants this.
- `x` cancels the turn; trace records the cancellation.
- Web viewer mirrors this UI for browser approval.

## Park mechanism (DAG Teams)

In `dag-teams`, an `ask` decision on a node can be *parked* rather than blocking:

1. Node's task returns `parked` status to scheduler.
2. Scheduler marks the node awaiting approval; emits a `permission.park` trace event.
3. Downstream nodes that do not depend on parked run normally.
4. Web viewer shows a queue of parked items; user approves asynchronously.
5. On approval, the node resumes from park (its transcript preserved); on deny, downstream chains mark `blocked_upstream`.

## Integration with hooks

The order is: **PermissionBridge first → Hooks after**. Rationale: hooks are task-specific guardrails; permissions are the coarse authorization envelope. A `deny` at permission level prevents hooks from running (no tool execution to hook).

An exception: `PreToolUse` hooks may be declared **pre-permission** in their metadata if they must run for logging/observability regardless. These are opt-in and marked `phase=pre_permission` in the hook registry.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| LLM convinces user to switch to `bypass` under false pretenses | Mode change surfaces diff summary + "are you sure" prompt |
| Prompt injection triggers a tool call that matches `ask`; user clicks approve habitually | `always` requires typing out the word, not single-key press |
| Risk classifier drift over time | Nightly retraining + regression test against labeled fixtures |
| Policy file typo grants too much | YAML lint + policy dry-run before apply |
| Parking queue grows unbounded | Cap; older parked items auto-expire with `timeout_deny` |
| Race between async approval and DAG progression | Scheduler checks latest decision on each wave boundary |
| User overrides classifier too aggressively | Telemetry: if user approves > 90% of asks, surface a doctor warning (you've disabled the gate in practice) |

## Metrics emitted

- `permission.decisions.total` labeled by decision × tool
- `permission.mode.current` gauge
- `permission.mode.transitions.total` labeled by from/to
- `permission.approvals.latency_ms` (histogram)
- `permission.approvals.auto_rate` (approved in <2s as proxy for habit approval)
- `permission.risk.score` histogram
- `permission.policy.matches.total` labeled by policy name
- `permission.park.queue_size` gauge

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_permissions_bridge.py` | Decision order, mode transitions, destructive pattern coverage |
| Unit `test_policy_engine.py` | Policy evaluation, validation |
| Unit `test_risk_classifier.py` | Classifier determinism on fixtures |
| Integration | Full flow: agent tries mutating in plan mode → deny → agent adapts |
| Property | Monotonic: higher mode never denies more than lower mode for a given call |
| Red-team | Attempt to bypass via crafted args (smuggled rm, base64 commands) |

## Open questions

1. **Org-level policy sync.** Team mode (v2) needs centralized policy distribution; MDM-style sync or git-synced configs?
2. **Classifier features.** Current features are shallow; deep features from trace embeddings could improve precision at cost of latency.
3. **Elevation duration.** `always` elevates for the session; should it persist across sessions? We default to no (fresh session = fresh permissions).
4. **Hardware-backed approval.** For high-risk operations, couple to system-level MFA or TouchID. v2 exploration.
