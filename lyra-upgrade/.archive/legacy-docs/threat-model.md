# Lyra — Threat Model

Scope: Lyra deployed in **local-only** and **local + cloud runner** modes. Team mode (v2) has its own threat model appended once designed.

Threat modeling approach: STRIDE over the component set in [`architecture.md § 4`](architecture.md), plus AI-specific threats (prompt injection, data exfiltration via LLM, sabotage via tool misuse). Defense-in-depth mapped back to harness primitives.

## 1. Assets

| Asset | Classification | Location |
|---|---|---|
| Source code | Confidential (per-repo) | Working tree / git |
| Secrets (API keys, tokens, credentials) | High sensitivity | `~/.lyra/config.yaml`, environment, `.env` files |
| Generated traces | Sensitive (may contain prompts + code snippets) | `.lyra/traces/` |
| SOUL.md persona | User-identifying | `.lyra/memory/SOUL.md` |
| Memory store (Chroma + SQLite) | Sensitive (observations, decisions) | `.lyra/memory/` |
| Skill library | Mostly public, user-written skills private | `.lyra/skills/`, `~/.lyra/skills/` |
| LLM API budget | Financial | Provider billing |
| User's machine | Everything | Host OS |

## 2. Trust boundaries

```
┌────── User (trusted) ──────┐
│                            │
│ lyra CLI ──stdio──┬──┤────stdin──▶ daemon (trusted, local)
│                         │                     │
│                         │                     ↓
│                         │              local fs + git (trusted within repo root)
│                         │                     │
│                         │                     ↓
│                         │              SQLite + Chroma (trusted)
│                         │                     │
│                         │                     ↓
└─────────────────────────┼────────────────────────────────────
                          │              LLM API (Anthropic/OpenAI/Gemini)
                          │              — Outbound over TLS; API key auth
                          │              — Partially trusted: receives prompts,
                          │                returns content that may contain
                          │                adversarial content
                          │
                          │              MCP servers (untrusted by default)
                          │              — May be hostile; tool outputs
                          │                pass through injection guard
                          │
                          │              Web (WebFetch) — untrusted
                          │              Cloud runners — semi-trusted
                          │              (rented infra; isolated per-session)
```

## 3. STRIDE analysis

### 3.1. Spoofing

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Malicious skill published to community registry masquerading as trusted | Medium | High | `lyra skills install` checks registry signature (v2 Sigstore); v1 warns + shows content diff |
| Compromised MCP server returning fake tool results | Medium | High | Tool outputs run through injection guard; PermissionBridge still gates any mutation |
| Model-in-the-middle (MITM) on LLM API | Low | High | HTTPS + certificate pinning in httpx client; API key secrets |
| Session ID collision / forgery | Low | Medium | ULIDs (128-bit); session dir isolation |

### 3.2. Tampering

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Adversarial content in fetched docs / repos inserts hostile instructions | High | High | Injection guard (ML + LLM + canary) on all `WebFetch`, `Read` of untrusted paths, MCP tool outputs |
| Prompt injection via tool output poisoning | High | High | As above. Canary token mismatch → tool result is truncated + flagged |
| Log tampering to hide malicious actions | Low | High | JSONL trace is append-only; daemon refuses to rotate before a configured retention period |
| Git index corruption via `Bash` | Low | Medium | `Bash` destructive pattern detector; worktree isolation; `bypass` mode required for `git reset --hard` |
| STATE.md manipulated externally to mislead resume | Low | Medium | Session resume reads STATE.md + cross-checks against recent.jsonl hashes |

### 3.3. Repudiation

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| "I didn't make this change" — user denies their own agent did it | Medium | Medium | Trace is append-only; commits tagged with `session-id`; HIR-compatible trace is replayable |
| Agent fabricates success (trace says pass; diff shows no change) | Medium | High | Cross-channel verification (trace ↔ diff ↔ env snapshot) |
| Model provider denies API request happened | Low | Low | Keep response headers + request IDs in trace |

### 3.4. Information Disclosure

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Secrets in code + committed to PR | High | High | Secrets detection on every `Write`/`Edit` (entropy + detect-secrets patterns); PreCommit hook blocks |
| LLM prompt inadvertently includes secrets | High | Very High | Prompt pre-submission filter redacts known secret patterns; `.env` files excluded from context by default |
| Memory store contains exfiltrable sensitive observations | Medium | High | `<private>` tag convention (from [claude-mem](../../../docs/72-claude-mem-persistent-memory-compression.md)); `mem` subcommand has `wipe`, `export --redact` |
| Traces sent to trace collectors leak content | Medium | High | OTel exporter defaults to localhost; external collector opt-in; redactor hook layer |
| LLM provider logs prompts (policy dependent) | Low-Med (provider-dep) | High | Prompt caching uses provider cache but actual content is governed by provider policy; document per-provider guidance; `config.yaml` opt out of logging where API supports |
| Skill body leaks proprietary info when shared | Medium | High | `lyra skills publish` review flow; skill bodies diff-scanned for secrets |

### 3.5. Denial of Service

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Runaway loop burns cost cap | Medium | Medium | `max_steps`, `max_tokens`, `max_cost_usd` budgets; repeat-call detector; Stop hook |
| Compaction failure → context explodes | Low | High | Compaction budget; hard cap at 95% of `max_tokens` forces summarization regardless |
| Disk fill from worktrees | Low | Medium | Preflight disk check; `lyra doctor` warns |
| Daemon hang blocks user shell | Low | Low | Daemon uses systemd/launchd auto-restart; CLI has `--foreground` fallback |
| Rate limit from LLM provider | Medium | Low | Exponential backoff + fallback model in multi-family setup |
| Flaky test infinite retry | Low | Medium | Flaky detection marks test `@quarantine`; gate stops retrying on flag |

### 3.6. Elevation of Privilege

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM convinces user to switch to `bypass` mode under false pretenses | Medium | High | `bypass` mode surfaces a friction prompt + diff summary of what the session wants to do |
| Prompt injection triggers `bypass` mode change | Medium | Very High | Mode change requires user interactive confirmation; injection guard on the same turn flags the induced request |
| `Bash` escapes sandbox via known CVE | Low | High | Rootless container for `--sandbox`; dependency pinning; CVE scanner in CI |
| Skill with `allowed-tools: [*]` given too much authority | Medium | High | Linter for skills: `allowed-tools: [*]` is forbidden; narrow allowlists required |
| User installs hostile plugin | Low | Very High | Plugin registry signatures (v2); in v1, plugins run with narrower default permissions than native |

### 3.7. AI-specific threats

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Prompt injection (direct, via user) | Low | Medium | User is trusted; separate concern |
| Prompt injection (indirect, via fetched content) | High | High | Injection guard ML+LLM+canary |
| Model jailbreak → agent ignores safety rules | Medium | High | PermissionBridge is code, not prompt; jailbreak does not bypass it |
| Model hallucinates a file / function / API that does not exist | High | Medium | Typed tools + Evaluator Phase 1 catches missing files; Phase 2 catches semantic hallucination |
| Generator-evaluator collusion (shared blind spots) | Medium | High | Different-family default |
| Sabotage: agent deliberately leaves a backdoor | Low | Very High | Cross-channel verification + safety monitor + secrets scan |
| Agent exfiltrates code via `WebFetch` POST | Low | High | `WebFetch` is GET-only; `Bash curl --data` blocked by injection guard pattern if it touches sensitive paths; allowlist for POST |

## 4. Defense-in-depth map

Ordered from outer to inner:

1. **User intent + Plan Mode.** User writes task; plan surfaces before execution. Misunderstanding caught here.
2. **Permission mode.** Ladder of privilege; high modes require explicit upgrade.
3. **PermissionBridge.** Runtime primitive decides every tool call; LLM cannot bypass.
4. **Hooks.** Deterministic code on pre/post/stop events. TDD gate, secrets scanner, destructive-pattern detector.
5. **Injection guard.** Sanitizes fetched / imported content.
6. **Risk classifier.** ML + rule-based scoring on each tool call's arg shape.
7. **Worktree isolation.** Subagents cannot stomp the parent's fs.
8. **Verifier (two-phase).** Objective then subjective gate on completion.
9. **Cross-channel verification.** Trace ↔ diff ↔ env agreement.
10. **Safety monitor.** Continuous background check every N steps.
11. **Observability.** Tracing + nightly replay + cost alert.

If attackers bypass layers 1-10, layer 11 catches anomalies retrospectively and informs the next model of hooks.

## 5. Residual risks (honest)

1. **Coordinated channel attack.** If trace, diff, and environment are all attacker-controlled (e.g. malicious fs in a cloud runner), cross-channel agreement can be faked. Mitigation relies on safety monitor + user-initiated audits.
2. **Supply chain (dependencies).** A compromised Python package in the runtime undermines everything. Mitigation: `pip-audit`, hash pinning, release signing.
3. **Zero-day in containerization (sandbox mode).** Rootless container breakout is rare but possible. Mitigation: defence-in-depth with `Bash` allowlist even inside sandbox.
4. **LLM provider outage / model deprecation.** Operational risk, not security per se. Mitigation: model router with fallbacks; emit warning tags.
5. **User-written skill with eval()**. v1 linter can detect obvious patterns; obfuscated cases slip through. Mitigation: skill provenance + dry-run sandbox (v2).
6. **Privacy leaks via LLM provider logs.** Depends entirely on provider policy; we document per-provider guidance but cannot enforce upstream.
7. **Insider threat.** Malicious user of shared team account. Out of scope for v1 (local-only). Team mode (v2) will require OIDC + audit log.

## 6. Controls inventory

| Control | Status v1 | Implementation |
|---|---|---|
| Permission modes (plan/default/acceptEdits/bypass/red/green/refactor/triage) | Ship | `lyra_core/permissions/modes.py` |
| PermissionBridge runtime primitive | Ship | `permissions/bridge.py` |
| Hook registry + TDD gate + secrets scanner + destructive-pattern | Ship | `hooks/*.py` |
| Injection guard (ML + LLM + canary) | Ship | `hooks/injection_guard.py` |
| Risk classifier (rules + ML) | Ship | `permissions/classifier.py` |
| Worktree isolation for subagents | Ship | `orchestrator.py` |
| Two-phase verifier | Ship | `evaluator.py` |
| Cross-channel verification | Ship | `evaluator.py` + env snapshot |
| Safety monitor (continuous) | Ship | `safety_monitor.py` |
| Bash sandbox (rootless container) | Opt-in | `tools/bash.py` with `--sandbox` |
| Sigstore signature verification on skills/plugins | Defer v2 | — |
| OIDC + audit log (team mode) | Defer v2 | — |
| Dependency CVE scanner in CI | Ship | `pip-audit` + `safety` in CI |
| Secrets commit prevention | Ship | PreToolUse hook + git pre-commit sample |
| Redaction of SOUL + memory on `mem export` | Ship | `mem` subcommand |
| `<private>` tag convention in memory | Ship | `memory/store.py` |
| LLM provider logging opt-out where supported | Partial | Documented per provider |

## 7. Incident response runbook

When a safety flag or suspected compromise occurs:

1. **Freeze.** `lyra daemon stop` halts further work.
2. **Isolate.** `lyra snapshot <session-id>` produces a sealed archive of trace + state + diffs.
3. **Audit.** Open web viewer offline; inspect spans flagged `safety.flag`, `permission.deny`, `hook.pre.block`.
4. **Revert.** Session branch is abandonable with `git reset` on your main branch; session fs is confined to the worktree.
5. **Retain trace.** For post-mortem / external audit. Do not auto-delete.
6. **Report.** If the skill or plugin was community-distributed, open an issue upstream with the sealed snapshot (redacted as needed).
7. **Harden.** Add regression test under `tests/red-team/` reproducing the attack.

## 8. Privacy posture

- **SOUL.md and MEMORY.md** are user-owned files. They never leave the machine unless the user exports or a trace collector is configured.
- **`<private>` tag** in observations excludes them from memory retrieval by default; they remain in the trace for audit.
- **Prompt filtering** redacts a default set of secret patterns before every model call; additional regex patterns in config.
- **`lyra mem wipe --confirm`** deletes memory stores; trace retention is separate (trace is the audit log).
- **No telemetry by default.** Opt-in anonymous metrics for health SLOs only; no task content ever.

## 9. Comparable threat models

- [Orion-Code threat model](../../orion-code/docs/) (sibling) — similar surface; we extend with skill marketplace + team-mode risks.
- [Claude Code](../../../docs/29-dive-into-claude-code.md) — proprietary; our model mirrors where inference from audits is possible.
- [gstack browser defender](../../../docs/75-gstack-garry-tan-claude-code-setup.md) — injection guard design reference.

## 10. Review cadence

Threat model is reviewed:

- Whenever a new extensibility surface is added (new tool, new hook event, new protocol).
- Nightly CI runs the red-team suite + fuzz tests against permission rules.
- Quarterly review with attention to new classes of attacks reported in industry.
- Before every minor release (`0.x`); major releases (`1.x+`) include a public threat-model changelog.
