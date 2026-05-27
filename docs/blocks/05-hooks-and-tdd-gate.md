# Lyra Block 05 — Hooks and the TDD Gate

Hooks are deterministic, code-enforced guardrails that run at specific lifecycle events. The TDD gate is the flagship hook — the load-bearing feature that justifies the whole project. This block describes the hook framework and specifies every shipped hook in detail.

Workspace references: [Claude Code hooks](../../../../docs/09-hooks.md), [Four Pillars § Guardrails](../../../../docs/44-four-pillars-harness-engineering.md), [TDD discipline](../tdd-discipline.md).

## Responsibility

1. Provide a small, typed registry of lifecycle events.
2. Allow multiple hooks per event; results compose predictably.
3. Ship a small set of built-in hooks (TDD, destructive-pattern, secrets scan, loop detector, injection guard).
4. Allow user-defined hooks (Python callables or shell scripts).
5. Emit trace events for every hook invocation (HIR primitive = `hook`).

## Lifecycle events

```python
class HookEvent(StrEnum):
    SESSION_START = "session.start"
    USER_PROMPT_SUBMIT = "user.prompt.submit"
    PRE_MODEL_CALL = "pre.model.call"
    POST_MODEL_CALL = "post.model.call"
    PRE_TOOL_USE = "pre.tool.use"          # most common
    POST_TOOL_USE = "post.tool.use"        # most common
    PRE_PERMISSION = "pre.permission"      # advisory
    STOP = "stop"                           # session completion gate
    SESSION_END = "session.end"
    SUBAGENT_START = "subagent.start"
    SUBAGENT_END = "subagent.end"
    NOTIFICATION = "notification"           # surface to user
    COMPACTION = "compaction"               # observe or intervene
```

## Hook result types

```python
@dataclass
class HookDecision:
    block: bool                           # if True for PRE events, prevents action
    reason: str
    name: str                             # hook name, stable
    annotation: Optional[str] = None      # appended to tool result as critique
    suggestion: Optional[str] = None      # advice back to LLM
    severity: Literal["info","warn","error","block"] = "info"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(cls, name: str) -> "HookDecision": ...
    @classmethod
    def block_(cls, name: str, reason: str, **kw) -> "HookDecision": ...
```

Composition rule for multiple hooks on the same event: **any `block=True` wins**; annotations concatenate in declaration order.

## Hook declaration

Python decorator:

```python
from lyra import Hook, HookEvent, ToolCall, Session

@Hook.register(HookEvent.PRE_TOOL_USE, name="my-secrets-redactor", priority=10)
def redact_secrets(call: ToolCall, session: Session) -> HookDecision:
    if call.name in {"Write","Edit"} and has_secret_pattern(call.args.get("content","")):
        return HookDecision.block_(
            name="my-secrets-redactor",
            reason="content matches secret pattern",
            suggestion="Remove the secret or store it in env/.env (not tracked by git).",
        )
    return HookDecision.allow("my-secrets-redactor")
```

YAML declaration for shell hooks (`.lyra/hooks.yaml`):

```yaml
- name: format-on-edit
  event: post.tool.use
  run: scripts/format.sh
  match:
    tool: [Edit, Write]
    path_glob: "src/**/*.{ts,tsx,py,go}"
  timeout_s: 5
  non_blocking: true
```

`non_blocking: true` means failure does not block; it emits a warn annotation.

## Shipped hooks

### 5.1. `tdd-gate` (the star)

Full contract in [`tdd-discipline.md`](../tdd-discipline.md). Summary:

- `PRE_TOOL_USE(Edit|Write)` — require RED proof in recent window when editing `src/**`.
- `POST_TOOL_USE(Edit|Write)` — run focused tests in GREEN phase; emit critique on failure.
- `STOP` — full acceptance tests must pass; coverage delta ≥ 0.
- `PRE_TOOL_USE(Bash)` — block test-disabling patterns.

Implementation: `src/lyra_core/hooks/tdd.py`.

### 5.2. `destructive-pattern`

Blocks unbypassable-dangerous Bash patterns regardless of mode. See [block 04 § Destructive patterns](04-permission-bridge.md).

### 5.3. `secrets-scan`

On `PRE_TOOL_USE(Write|Edit)`, scans `content` + `new_string` for:

- High-entropy tokens (> 4.5 bits/char over 40+ chars).
- Known secret patterns (AWS keys, GitHub PAT, Slack bot, Stripe keys, generic RSA/PEM headers, JWT bodies).
- `.env`-style `KEY=value` lines with values that match the above.

Block or annotate depending on severity. Configurable allowlist via `.lyra/secrets-allow.yaml` (e.g. example keys in fixtures).

### 5.4. `loop-detector`

On `POST_TOOL_USE`, tracks a sliding window of (tool name, normalized args) hashes. If repeat count > threshold, emit `suggestion` to diversify. If hammer continues, escalate to `STOP`-blocking on next turn.

Complements the in-loop `RepeatDetector` ([block 01](01-agent-loop.md)) but runs as a hook so user-defined hooks can replace / extend.

### 5.5. `injection-guard`

On `POST_TOOL_USE(WebFetch|MCP.*|Bash.stdout)`, runs injection detection:

1. ML classifier (fast, small model).
2. If score > warn-threshold: canary token check — injected content that references system identifiers or past session state is flagged.
3. If score > block-threshold: LLM vote (a cheap model reads the output + original request, says "does this try to manipulate the agent?").

On block, truncate the injected content, emit `injection.blocked` span, and pass a sanitized observation to the transcript. On warn, annotate.

### 5.6. `format-on-edit`

On `POST_TOOL_USE(Edit|Write)` for recognized file types, run the project's formatter (`ruff format`, `prettier`, `gofmt`). Non-blocking on failure. Emits `formatted` annotation when applied.

### 5.7. `lint-on-edit`

Similar to format but blocking on egregious errors (unused imports, undefined names). The lint output is structured (`ruff --output-format=json`, `eslint --format=json`) and the annotation includes the first few errors with file:line.

### 5.8. `typecheck-incremental`

On `POST_TOOL_USE(Edit|Write)` in Python / TS projects, incrementally runs `mypy --follow-imports=silent <file>` or `tsc --noEmit --incremental`. Annotates transcript with any new type errors.

### 5.9. `stop-verifier`

The final `STOP` hook: ensures the verifier Phase 1 gate ran and passed, Phase 2 produced an accept verdict, and cross-channel agreement holds. If not, return block. See [block 11](11-verifier-cross-channel.md).

### 5.10. `skill-extractor-trigger`

On `SESSION_END` with status `completed`, triggers the skill extractor ([block 09](09-skill-engine-and-extractor.md)). Does not block; runs async on worker.

### 5.11. `state-md-persist`

On every `POST_TOOL_USE`, refreshes STATE.md with the latest plan status, open questions, last-action summary. Non-blocking.

## Hook execution order

At a given event, hooks run in **declared priority order**, lowest number first. Built-ins have reserved priorities (TDD gate = 10, secrets-scan = 20, destructive-pattern = 0, injection-guard = 30). User hooks default to 100+. Within the same priority, declaration order is stable.

## Timeout and failure

Each hook has a timeout (default 10s for Python, 30s for shell). On timeout, result = `warn` annotation "hook X timed out"; does not block (timeout of a block-style hook becomes advisory to avoid silent deadlock). Exceptions in a hook are caught; they emit `hook.error` span and do not block downstream hooks.

## Hook-on-hook composition

Careful pattern: a hook can enqueue another hook. e.g. the secrets-scan hook, on finding a secret, triggers the `NOTIFICATION` event to show user a banner. Nested hook invocations are depth-limited (2) to prevent recursion.

## Sandboxing (user hooks)

User-supplied Python hooks run in the daemon process — they can read/write everywhere. Shell hooks run as subprocesses inheriting the daemon's env (optionally `env: {}` in YAML to empty). v1 is trust-the-user; v2 will offer a restricted subinterpreter mode.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Hook hangs | Timeout enforced |
| Hook panics in loop (always blocks) | Escalation after N consecutive blocks to `human_review` |
| Hook has side effects on filesystem | Metadata `side_effects: [fs]` required; trace records; hooks without declaration warned |
| Hooks slow down every tool call | `hook.duration_ms` histogram tracked; hooks > 500ms surface in doctor |
| User hook leaks secrets to logs | Hook output is part of trace; trace redactor applies same rules |
| Hook disagrees with permission bridge | Permission bridge runs first; hook cannot undo a `deny` (it can only add further block/annotations) |
| Hook that never allows | Escalation: 3 blocks on same tool call stream → session pauses for user review |

## Metrics

- `hook.invocations.total` labeled by name, event, decision
- `hook.duration_ms` histogram labeled by name
- `hook.errors.total` labeled by name
- `hook.blocks.total` labeled by name (TDD-gate will be the leader)
- `hook.annotations.total`

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_hooks_registry.py` | Register, priority, composition |
| Unit `test_hooks_tdd.py` | Each TDD contract under multiple scenarios |
| Unit `test_secrets_scan.py` | Every known pattern; entropy thresholds |
| Unit `test_destructive.py` | All listed patterns deny; near-miss patterns allow |
| Integration | Happy path + one-of-each block path |
| Property | Hook composition is deterministic across declaration orders per same priority |
| Red-team | Pattern bypass attempts (unicode, base64, obfuscation) |

## Authoring guide (for users)

```python
# .lyra/user_hooks/no_console_log.py
from lyra import Hook, HookEvent

@Hook.register(HookEvent.PRE_TOOL_USE, name="no-console-log", priority=200)
def block_console_log(call, session):
    if call.name == "Edit" and "new_string" in call.args:
        if "console.log(" in call.args["new_string"]:
            return Hook.block(
                "no-console-log",
                reason="Direct console.log in source. Use the logger instead.",
                suggestion="import { logger } from '@/logging' and call logger.debug(...)",
            )
    return Hook.allow("no-console-log")
```

Users can also install pre-made hook packs via `lyra skills install <uri>` where a plugin bundles hooks + skills + MCP servers.

## Open questions

1. **WASI hook sandbox.** Run untrusted hooks in a WASM runtime with restricted capabilities. v2.
2. **Hook priority auto-learning.** When two hooks block frequently, should the system suggest a priority swap? Research.
3. **Cross-session hooks.** Hooks that fire on "started my Nth session today" — rhythmic rather than event-based. Maybe moves to Scheduler.
4. **Conflict resolution UX.** When two user hooks block the same call for different reasons, how to surface? v1 concatenates; v2 may offer an interactive chooser.
