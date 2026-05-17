# Auto-Spec-Kit: Design Note

> Lyra's mechanism for automatically routing build-a-thing prompts
> through a constitution → spec → plan → tasks flow before any code
> is written.

## Why

Big asks deserve big plans. When a user says *"build me a deep-research
orchestrator"* the worst outcome is an agent that starts editing files
immediately. The best outcome is a paused, structured conversation
that produces a spec, a plan, a task list, an explicit approval, and
only then code — exactly the GitHub spec-kit flow, but run by the
agent itself instead of by the human.

## What it is

A Python subsystem at `src/lyra_cli/spec_kit/` that the agent loop
calls on every incoming user prompt. Most prompts pass through
untouched (microseconds of overhead). Spec-worthy prompts trigger an
in-conversation state machine that drafts artifacts in memory, shows
them to the user inside the TUI's `SpecDrawer` widget, takes
approvals, and writes to disk only after the final sign-off.

## Trigger

Automatic, based on a two-stage detector:

1. **Rule-based pre-classifier** (< 5 ms): regex over verbs, length
   heuristics, exemption keywords, slash-command bypass.
2. **LLM-assisted classifier** (≤ 800 ms, only in the ambiguous band
   0.4 – 0.8): small model, JSON-mode output, strict schema.

Verdict threshold: `confidence ≥ 0.7` ⇒ intercept. Below ⇒ fall
through to normal agent loop.

Opt out globally with `LYRA_AUTOSPEC=off`.

## The state machine

```
idle → constitution_check → drafting_spec → drafting_plan
     → drafting_tasks → writing_disk → executing
```

Any state can branch to `cancelled` (user `Esc` or `/skip-spec`) or
`failed` (detector / LLM error). Both fall back to the normal agent
loop with the original prompt preserved.

## Public API

```python
# src/lyra_cli/spec_kit/orchestrator.py
class Orchestrator:
    async def maybe_intercept(
        self, prompt: str, session: Session
    ) -> InterceptResult:
        """
        Return InterceptResult(intercepted=False) for non-spec-worthy
        prompts. For spec-worthy prompts, take ownership of the
        conversation until the state machine completes, then return
        InterceptResult(intercepted=True, feature_id=...).
        """
```

The agent loop calls `maybe_intercept` once per incoming user
message; if `intercepted`, it does not run its normal pipeline.

## Disk layout (only after approval)

```
.specify/memory/constitution.md       ← amended only on constitution-check
specs/<NNN>-<slug>/
├── spec.md
├── plan.md
├── tasks.md
└── .draft-history/                   ← every approval round
```

Feature number is `max(existing NNN) + 1`. Slug is a 4-word summary
of the original prompt.

## TUI integration

The TUI subscribes to `SpecKitState.phase` reactive. When `phase !=
"idle"`, the `SpecDrawer` widget renders a right-side drawer
streaming the current draft via `Markdown.get_stream()`, with an
approval bar:

```
[Enter] approve · [E] edit · [R] redraft · [Esc] skip spec-kit
```

## Events on the bus

| Event | Fields |
|---|---|
| `spec_detector_ran` | verdict |
| `spec_phase_changed` | old_phase, new_phase |
| `spec_draft_chunk` | artifact, chunk |
| `spec_approval_requested` | artifact, full_text |
| `spec_approval_resolved` | artifact, approved, edits |
| `spec_files_written` | feature_id, paths |

These extend the existing `AgentEvent` union defined in
`specs/001-tui-claude-code-parity/plan.md` §4.2.

## Non-goals

- A separate spec-kit CLI binary (no `lyra specify` command —
  Auto-Spec-Kit triggers automatically).
- Cross-session memory of past specs (one feature = one session for
  v1; revisiting an existing feature is a v2 concern).
- Multi-language project support beyond Python (templates assume
  Python conventions; plan templates can be extended later).

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Detector false positives (annoying) | Threshold 0.7, easy `/skip-spec`, opt-out env var, log every verdict for tuning |
| Detector false negatives (missed value) | Toast-level hint "this looked spec-worthy — invoke `/spec` to retry" when retrospective signals appear |
| LLM drafting takes too long | Stream in chunks; user can `[E]` edit at any point; `[Esc]` skips |
| Constitution drift across features | Every constitution amendment surfaces a Sync Impact Report; never silently mutates |
| Disk-write conflicts | Idempotent: existing file ⇒ `.draft-N` suffix, surface conflict |

## Acceptance tests

Stored under `tests/spec_kit/`:

- 20-prompt classifier accuracy test
- State-machine transitions in isolation
- End-to-end happy path: prompt → 4 approvals → 3 files on disk
- Rejection path: reject at spec step → zero files on disk
- Misclassification recovery: 100 ms budget on "fix typo" prompt
- Constitution amendment path: principle change ⇒ Sync Impact Report
  proposed (not silently applied)

## How to opt out

- Globally: `export LYRA_AUTOSPEC=off`
- Per prompt: type `/skip-spec` before submitting
- Per phase: press `Esc` during any drafting state

## How to extend

- Add a new artifact type (e.g. `architecture.md`): add a template
  under `src/lyra_cli/spec_kit/templates/`, add a new phase to the
  state machine, add an event variant, register a TUI render in
  `SpecDrawer`.
- Tune the detector: edit the rule weights in `detector.py` and re-run
  the 20-prompt accuracy test.
- Add a new agent-loop hook (e.g. post-write linting): subscribe to
  `spec_files_written` events on the bus.
