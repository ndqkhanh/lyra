# Lyra — Optional TDD Plugin

> **v3.0.0 status.** As of v3.0.0 (released 2026-04-27), the TDD gate
> is an **opt-in plugin**, not a runtime invariant. Out of the box,
> `lyra` behaves like `claw-code`, `opencode`, and `hermes-agent`: a
> general coding agent that doesn't refuse Edits because no failing
> test exists yet. The state machine, hooks, validators, and slashes
> documented below all still ship — they're simply off by default.
> Flip them on per-session with `/tdd-gate on`, persist with
> `/config set tdd_gate=on`, or set
> `[plugins.tdd] enabled = true` in `~/.lyra/settings.toml`.
>
> Everything below describes what the plugin does **when enabled**.
> The contracts, state machine, and hooks are unchanged from v2.x.

When the TDD plugin is enabled, Lyra's most distinctive feature
lights up: **Test-Driven Development is enforced at the harness
kernel, not at the prompt.** This document defines the contracts,
the state machine, the hooks, and the escape hatches.

Reference pillar: [Four Pillars § Deterministic Guardrails](../../../docs/44-four-pillars-harness-engineering.md). Philosophical source: Kent Beck's *Test-Driven Development: By Example* (red → green → refactor). Adjacent influences: the four principles of [`andrej-karpathy-skills`](../../../docs/71-karpathy-skills-single-file-guardrails.md) and the Goal-Driven Execution tenet in particular.

## 1. Why a kernel-level gate (when you opt in)

A prompt-level TDD reminder works ~95% of the time. In production, 5% slip is enough to encode bad habits into every generated change over the course of a session. The only way to make TDD load-bearing is to *refuse* to run a mutation the test does not justify — and that's exactly what the v3.0.0 plugin still does, on demand.

- Prompts are advisory; hooks are mandatory.
- The gate gives the LLM a *structured reason* to write the test first, because the hook speaks back to it with a critique when it tries to skip.
- TDD compliance becomes a measurable SLO, not an aspiration.

The v3.0.0 trade-off: this discipline is no longer the default
posture. Most users — especially those coming from `claw-code`,
`opencode`, or `hermes-agent` — expect a general coding agent. So
the gate ships, but waits for an explicit `/tdd-gate on`.

## 2. The TDD state machine

Each session transitions through explicit TDD phases. The permission mode enum ([block 04](blocks/04-permission-bridge.md)) carries the phase:

```
IDLE ──task──▶ PLAN ──plan approved──▶ RED
                                        │  (write failing test)
                                        ▼
               SHIP ◀──green proof── GREEN ◀── pre-hook: test must be red first
                │                        │  (minimum code to pass)
                │                        ▼
                │                   REFACTOR
                │                        │  (keep tests green)
                │                        ▼
                └─────────── RED ◀── next plan item
                             │
                             ▼
                     COMPLETED → retro
```

Phases encode the *intent* of the current step. Hooks behave differently per phase.

## 3. Hook contracts

### 3.1. `PreToolUse(Edit | Write)` in phases RED or refactor-new

**Contract.** If the target path matches `src/**` (tunable via `.lyra/tdd.yaml` `src_globs`), a recent failing test must exist in this session. Otherwise **block** with reason `tdd: no_red_test`.

```python
def pre_tdd_gate(call: ToolCall, session: Session) -> HookDecision:
    if session.phase not in {Phase.RED, Phase.GREEN, Phase.REFACTOR}:
        return HookDecision.allow()
    if call.name not in {"Edit", "Write"}:
        return HookDecision.allow()
    path = _target_path(call)
    if not _matches_src_globs(session, path):
        return HookDecision.allow()

    # If the edit is in tests/ itself, we *encourage* it — but track.
    if _matches_test_globs(session, path):
        session.ephemeral.last_test_edit_span_id = call.span_id
        return HookDecision.allow()

    # Otherwise: require a recent failing test.
    proof = session.red_proof()
    if proof is None or proof.age_steps > 5:
        return HookDecision.block(
            reason="tdd: no_red_test",
            suggestion=(
                "Add a failing test first. Run `lyra red \"<test-name>\"` "
                "or emit a test file edit yourself. After the test fails, retry."
            ),
        )
    if proof.still_passing_when_refreshed():
        return HookDecision.block(
            reason="tdd: red_test_turned_green_without_implementation",
            suggestion=(
                "The test you wrote passes without new code. "
                "Either the test is not exercising the feature or feature already exists."
            ),
        )
    return HookDecision.allow()
```

`session.red_proof()` inspects the trace for the most recent `tool.result` matching a test-run with exit code ≠ 0 *and* the `PostToolUse` annotation attributing it to a recently edited test file.

### 3.2. `PostToolUse(Edit | Write)` in phase GREEN

**Contract.** After a mutation in `src/**`, run the **focused test subset** (tests that touched in the session plus tests that reference the touched file). If the subset fails → the hook does not *block* the tool call itself (the mutation happened), but it appends a **critique observation** to the transcript so the next step sees the failure and can adapt.

```python
def post_green_gate(call, result, session) -> HookAnnotation:
    if session.phase != Phase.GREEN:
        return HookAnnotation.noop()
    if call.name not in {"Edit","Write"}:
        return HookAnnotation.noop()
    if not _matches_src_globs(session, _target_path(call)):
        return HookAnnotation.noop()

    runner = session.test_runner   # pytest | vitest | go_test | ...
    selector = runner.focused_selector(session, call)  # closest tests
    report = runner.run(selector, timeout_s=30)

    if report.exit_code == 0:
        session.ephemeral.last_green_at = now()
        return HookAnnotation.success(f"tests pass: {report.summary_line()}")
    else:
        session.ephemeral.green_fails += 1
        return HookAnnotation.critique(
            (f"tests failing after edit.\n"
             f"{report.first_failure_snippet(lines=20)}")
        )
```

### 3.3. `Stop` hook

**Contract.** A session cannot transition to `COMPLETED` if:

1. Focused tests are not green, **or**
2. The full test suite (fast subset) has regressed, **or**
3. Lint or typecheck regressed from the plan's baseline, **or**
4. Coverage delta on touched files is negative beyond a configured tolerance (default ≥ 0).

If any fail, the Stop hook returns a critique; the harness records the critique in STATE.md and the session remains `in_progress` rather than completing.

### 3.4. `Stop` hook in phase REFACTOR

**Additional contract.** Behavior tests (integration tests marked `@behavior` or in `tests/integration/`) must all pass. Unit-test coverage on touched files cannot decrease.

Rationale: refactor is defined as "does not change observable behavior". The gate enforces the definition.

### 3.5. `PreToolUse(Bash)` detecting test-disabling patterns

**Contract.** Block commands matching `pytest\s+.*--no-cov`, `vitest\s+.*--no-coverage`, `go test\s+.*-run\s+xxxxxx`, or other patterns indicating the agent is shutting off tests. Allowlist may be extended per project, but default-on.

## 4. Escape hatches

TDD without escape hatches is a prison. Lyra ships three:

### 4.1. Per-session flag `--no-tdd`

```
lyra run --no-tdd "quick prototype: sketch a new UI in /scratch"
```

Disables the gate for this session only. Telemetry tracks usage rate as a health metric.

### 4.2. Per-directory overrides in `.lyra/tdd.yaml`

```yaml
# .lyra/tdd.yaml
enabled: true
src_globs:
  - src/**/*.{py,ts,tsx,js,go}
test_globs:
  - tests/**/*.{py,ts}
  - src/**/*.test.{ts,tsx,js}
exempt_paths:
  - scratch/
  - examples/
  - docs/
runners:
  python: pytest
  typescript: vitest
  go: go_test
focused_timeout_s: 30
coverage_tolerance: 0.0
```

### 4.3. Mode-based downgrade

```
lyra config set tdd.mode advisory   # warn but don't block (project-wide)
lyra config set tdd.mode blocking   # default
lyra config set tdd.mode off        # strongest downgrade; requires --confirm
```

## 5. Test runner adapters (v1)

Initial three runners shipped in v1:

### 5.1. Python — `pytest`

- Default selector: `-p no:cacheprovider --tb=short -q -x --disable-warnings <paths>`
- Focused subset: pytest-testmon-style — run tests that import the changed file or match the changed function name.
- Timeout per subset run: 30s default.
- Coverage: `coverage.py` hooks read `.coverage` file.

### 5.2. TypeScript / JavaScript — `vitest`

- Default selector: `vitest run --no-coverage --bail=1 <paths>`
- Focused subset: `--related <file>` flag.
- Coverage: `vitest --coverage` feeds `coverage/lcov.info`.

### 5.3. Go — `go test`

- Default selector: `go test -count=1 -timeout=30s -run <regex> <packages>`
- Focused subset: package containing changed file plus dependents (via `go list -deps -f ...`).
- Coverage: `go test -cover` + `go tool cover -func`.

Additional runners (`jest`, `unittest`, `cargo test`, `junit`) are v2 opt-in plugins.

## 6. What counts as a RED proof

A `RedProof` object is produced when, during the session:

1. A `Write` or `Edit` into a `test_globs` path occurred, *and*
2. Within the next N (default 3) agent steps, a test-runner Bash call (or the internal focused-subset call) returned exit code ≠ 0, *and*
3. The failing test identifier is present in stdout/stderr.

The proof is **session-scoped**, has an age in steps, and is consumed on use. After consumption, phases advance RED → GREEN and the gate expects mutation.

Edge cases handled explicitly:

- *Agent edits a test file then edits more tests before running* → proof accumulates; any failure within window counts.
- *Runner itself errored (syntax)* → does not count as a RED proof; specific critique returned.
- *Test was already failing before the edit* → still counts IF the edit added a new failing assertion; detected by diff analysis on the test file.
- *Flaky test* → hook detects re-runs with inconsistent exit codes; emits a warning; user can pin with `@stable`.

## 7. Critique format

When the gate blocks or annotates, it emits a structured critique rather than bare text. The transcript-visible form:

```json
{
  "kind": "tdd.critique",
  "phase": "GREEN",
  "reason": "tdd: red_test_turned_green_without_implementation",
  "evidence": [
    {"span": "tool.call:abc123", "file": "tests/test_auth.py",
     "line": 42, "excerpt": "assert login(valid) == 200"}
  ],
  "suggestion": "Write a test that fails when the feature is absent, e.g., mock the handler missing.",
  "gate_version": "tdd-hook@1.0.0"
}
```

The agent sees this as a tool-result observation; the next LLM call reads it and adapts.

## 8. Measurement: TDD health SLOs

| Metric | Target | Where surfaced |
|---|---|---|
| `--no-tdd` usage rate per week | < 5% of sessions | `lyra doctor` |
| False positives (user override justified) | < 5% labeled | internal review |
| TDD-gate block → successful retry rate | > 80% | trace analytics |
| Coverage delta per merged PR (touched files) | ≥ 0 | `lyra retro` |
| Time-to-green (median RED→GREEN duration) | < 5 agent steps | session dashboard |
| Flaky-test false-block rate | < 1% | nightly replay |

## 9. Relationship to Karpathy Skills

The [four principles](../../../docs/71-karpathy-skills-single-file-guardrails.md) each have an operational TDD translation:

| Principle | TDD Translation |
|---|---|
| Think Before Coding | Plan Mode default + `PreToolUse(Edit)` blocks without red proof |
| Simplicity First | GREEN-phase refusal of speculative abstractions; "minimum code to pass" |
| Surgical Changes | `Edit` tool's unique-match requirement + focused test subset + forbidden-file list |
| Goal-Driven Execution | Every mutation traces to a failing test; the test traces to a plan item; the plan item traces to the user's task |

In effect the TDD discipline is the way Lyra *enforces* the Karpathy principles instead of merely *stating* them.

## 10. What TDD does *not* solve

Honest limits, in plain view:

1. **Design quality.** A passing test says the code does what the test asks; it does not say the architecture is good. This is the evaluator's Phase 2 job.
2. **Exploratory / notebook work.** The gate is awkward for `scratch/` and research repos. Escape hatch exists; use it without guilt.
3. **Infrastructure / infra-as-code.** Terraform and similar often lack practical unit tests. Opt a directory out via `exempt_paths`.
4. **UI visual iteration.** Visual output is not easily test-driven. A vestigial TDD gate here would block. Use `--no-tdd` or set the directory exempt.
5. **Flaky tests.** Flake is the TDD gate's worst enemy. Identify and quarantine with `@stable`.
6. **"Test-after" in legacy.** If the repo has no tests, the gate suggests `lyra init-tests` which scaffolds a baseline; otherwise user bypasses until a test suite exists.

## 11. Meta-TDD: Lyra tests itself

The discipline applies to Lyra's own development. Every PR into `lyra_core/` must:

1. Include test(s) that fail on the base and pass on the tip (RED proof).
2. Pass the full suite on tip (GREEN proof).
3. Include coverage delta ≥ 0 on touched files.
4. Pass lint + typecheck.
5. Be routed through the same PreToolUse/PostToolUse/Stop hooks when Lyra is used to develop Lyra (dogfood).

Nightly, `scripts/dogfood.py` runs Lyra against a trivial Lyra task ("fix typo in README") and confirms the full TDD machinery executes as expected; failure raises an alert. This is the load-bearing test for the load-bearing feature.

## 12. Open questions

1. **Language coverage expansion.** Adding Rust / Java / Swift runners in v2; quality of "focused subset" heuristic varies.
2. **Behavior test tagging.** Automatic classification of "behavior" vs "unit" is heuristic (location + decorators). A proper taxonomy is a v2 research item.
3. **Property-based TDD.** Hypothesis / fast-check integration as first-class RED proof source; v2 exploration.
4. **Mutation testing as coverage-delta backstop.** Use mutmut / stryker to validate that tests actually discriminate; adds cost.
5. **Concurrency tests.** Flake-prone by nature; do we require deterministic concurrency primitives or accept flake with retry? v2.

## 13. Related reading

- [`architecture.md § 3.4`](architecture.md) — commitment
- [`architecture-tradeoff.md § A.1`](architecture-tradeoff.md) — cost of kernel-level TDD
- [`blocks/05-hooks-and-tdd-gate.md`](blocks/05-hooks-and-tdd-gate.md) — implementation depth
- [Four Pillars](../../../docs/44-four-pillars-harness-engineering.md)
- [Karpathy-skills](../../../docs/71-karpathy-skills-single-file-guardrails.md)
