# Claude Code Prompt: Build Lyra Auto-Spec-Kit

> **How to use this file**
>
> 1. Open Claude Code in the Lyra repo root.
> 2. Paste the entire contents of this file as your first message.
> 3. Claude Code will read it, ask any clarifying questions, then produce
>    a plan before writing code.
> 4. Confirm the plan; let it execute.

---

## What you are building

A subsystem inside Lyra called **Auto-Spec-Kit** that watches every user
prompt, decides whether the prompt is "build-a-thing" enough to deserve
the full spec-kit flow (constitution → spec → plan → tasks), and if so,
runs that flow *inside the conversation* — drafting the artifacts in
memory, showing them to the user, and only writing to disk after
explicit approval.

The goal: when the user says *"build me a TUI like Claude Code"* or
*"add deep-research orchestration to Lyra"*, the agent should not jump
straight to coding. It should pause, propose a constitution check,
draft the spec, draft the plan, draft tasks, get sign-off, then
implement. When the user says *"fix the typo in README"* or *"run
the tests"*, Auto-Spec-Kit must stay out of the way.

This is **Lyra's own internal version of GitHub's spec-kit**, but:
- the trigger is automatic, not a slash command;
- the artifacts live in memory first, on disk only after `Approve`;
- it is implemented as a Python module Lyra calls, not as external
  shell scripts;
- it integrates with the existing agent loop and the TUI from
  feature `001-tui-claude-code-parity`.

---

## Repository context (read this before planning)

- Lyra is a Python 3.12 agentic CLI at `src/lyra_cli/`.
- The agent loop emits structured `AgentEvent` instances on an asyncio
  queue — that contract is defined in
  `specs/001-tui-claude-code-parity/contracts/agent-events.md`
  (if that file doesn't exist yet, the canonical version is in
  `specs/001-tui-claude-code-parity/plan.md` §4.2).
- There is an existing TUI feature in flight (`specs/001-tui-claude-code-parity/`).
  Read its `spec.md`, `plan.md`, and `tasks.md` before designing this
  one — Auto-Spec-Kit emits events the TUI must render, so the two
  features share data model.
- The constitution at `.specify/memory/constitution.md` v1.0.0 already
  exists. **Auto-Spec-Kit must respect it** — non-blocking, single
  source of truth, observability, etc.
- Existing modules you will integrate with:
  - `src/lyra_cli/cli/agent_integration.py` — the agent loop entry
  - `src/lyra_cli/interactive/` — interactive subsystems (memory,
    context engineering, deep-search, skills lifecycle, model router)
  - `src/lyra_cli/tui/` — the TUI scaffolding from feature 001

---

## Your task, in three explicit phases

### Phase 1 — Read and plan (do not write code yet)

Read in this order:

1. `.specify/memory/constitution.md`
2. `specs/001-tui-claude-code-parity/spec.md`
3. `specs/001-tui-claude-code-parity/plan.md`
4. `src/lyra_cli/cli/agent_integration.py`
5. `src/lyra_cli/interactive/` — scan the directory; read any file
   whose name suggests it owns a similar lifecycle (e.g.
   `spec_driven.py` if it exists).
6. `pyproject.toml` to confirm Python version and current deps.

Then **produce a written plan** before any file write. The plan must
include:

- A one-paragraph restatement of what Auto-Spec-Kit does.
- A list of new files you will create and existing files you will modify.
- The detector design (how does it decide "spec-worthy"?).
- The state machine (what are the phases and transitions?).
- The events it emits onto the agent event bus.
- The disk schema (what gets written, where, when).
- A risks-and-tradeoffs section, including a fallback path for when
  the detector misclassifies.
- 5–10 acceptance tests it should pass before you call it done.

**Stop after the plan and ask for approval.** Do not start writing
implementation files until the user says "go".

### Phase 2 — Implement (after approval)

Once the user approves the plan, implement following the constitution:

- All long operations run in workers (the spec-drafting LLM call is
  the obvious one) — never block the event loop.
- All state lives in one place, exposed via the existing
  `SessionState` reactive object plus a new `SpecKitState` sub-object.
- All visible counters (phase name, draft progress, file write
  status) are sourced from `SpecKitState` only.
- Every long-running operation emits structured log lines via
  `structlog`.

Order of files to create:

1. `src/lyra_cli/spec_kit/__init__.py`
2. `src/lyra_cli/spec_kit/detector.py` — the "is this spec-worthy?"
   classifier
3. `src/lyra_cli/spec_kit/state.py` — `SpecKitState`, the in-memory
   draft store
4. `src/lyra_cli/spec_kit/events.py` — new `AgentEvent` variants
5. `src/lyra_cli/spec_kit/templates/` — the four Markdown templates
   (constitution-snippet, spec, plan, tasks) — copy structure from
   the existing `.specify/templates/` if present, else use the
   github/spec-kit canonical structure
6. `src/lyra_cli/spec_kit/drafter.py` — the workflow: detector → draft
   constitution-check → draft spec → review → draft plan → review →
   draft tasks → review → write
7. `src/lyra_cli/spec_kit/writer.py` — the disk-write step, gated on
   approval
8. `src/lyra_cli/spec_kit/orchestrator.py` — the public entrypoint
   the agent loop calls on each incoming user prompt
9. Integration patch in `src/lyra_cli/cli/agent_integration.py` —
   route every prompt through `Orchestrator.maybe_intercept(prompt)`
   before normal handling
10. TUI integration: a new widget `src/lyra_cli/tui/widgets/spec_drawer.py`
    that subscribes to `SpecKitState` and renders the draft inline

### Phase 3 — Test, document, and ship

- Add tests under `tests/spec_kit/`:
  - `test_detector.py` — at least 20 prompts (10 spec-worthy, 10 not),
    asserting the classifier's verdict.
  - `test_state_machine.py` — the phase transitions in isolation.
  - `test_orchestrator_e2e.py` — feed a spec-worthy prompt, walk
    through the approvals via a stub user, assert the four files land
    on disk in the right structure.
  - `test_no_disk_without_approval.py` — feed a spec-worthy prompt,
    reject at the spec-review step, assert no files on disk.
  - `test_misclassification_recovery.py` — feed a "fix typo" prompt,
    confirm the orchestrator skips the spec flow and runs the normal
    agent loop within < 100 ms.
- Update `README.md` with a "Auto-Spec-Kit" section explaining when
  it triggers and how to opt out (env var `LYRA_AUTOSPEC=off`).
- Update `.specify/memory/constitution.md` with a new principle
  (VIII. Spec Before Build, with the exemption list).
- Tag a draft release.

---

## The detector — design constraints

This is the load-bearing piece. **Get this design right or the
feature is annoying.**

The detector returns a `Verdict` with three fields:

```python
@dataclass(slots=True)
class Verdict:
    spec_worthy: bool
    confidence: float          # 0.0 to 1.0
    reasoning: str             # one-line explanation
    exemption_reason: str | None  # if not spec_worthy, why?
```

Rules of thumb (you will refine these in the planning phase):

**Spec-worthy signals** (each adds confidence):
- Imperative verbs at scale: *build*, *create*, *implement*, *design*,
  *architect*, *add a new <thing>*.
- Multi-step nouns: *system*, *module*, *subsystem*, *feature*,
  *pipeline*, *framework*, *integration*, *engine*.
- Concrete scope indicators: *whole*, *end-to-end*, *production*,
  *MVP*, *v1*.
- Length: prompts > 80 words almost always need a spec.

**Exemption signals** (each removes confidence):
- *Fix*, *patch*, *update*, *bump*, *rename*, *small*, *quick*,
  *typo*, *one-liner*.
- Direct file references with surgical scope: *fix line 42 in foo.py*.
- *Run*, *test*, *check*, *show me*.
- Length: < 15 words rarely needs a spec.
- The user is in the middle of a spec-driven flow already (the
  `SpecKitState.phase` is not `idle`).

**Threshold**: spec-worthy if `confidence ≥ 0.7`.

**Always-bypass conditions** (no LLM call, no questions, return
`(False, 1.0, "explicit bypass", reason)`):
- The prompt starts with `/` (it's a slash command).
- `LYRA_AUTOSPEC=off` is set.
- The conversation already has an active `SpecKitState`.
- The prompt matches an internal regex of exempt verbs only.

Implementation: combine a cheap rule-based pre-classifier (regex +
length) with a small LLM call ONLY when the rule-based score is in
the ambiguous band (0.4 ≤ confidence ≤ 0.8). The LLM call uses a
small model (Haiku-class) with a strict JSON-mode output schema. This
keeps the average latency under 50 ms for clearly classifiable
prompts.

---

## The state machine

```
                     ┌──────────────┐
                     │     idle     │
                     └──────┬───────┘
                            │ detector says spec-worthy
                            ▼
                  ┌──────────────────────┐
                  │   constitution_check │  ◀── if constitution exists, just verify
                  └──────────┬───────────┘
                             │ approved
                             ▼
                  ┌──────────────────────┐
                  │   drafting_spec      │  ◀── LLM call streams into SpecKitState.spec_draft
                  └──────────┬───────────┘
                             │ user approves OR edits
                             ▼
                  ┌──────────────────────┐
                  │   drafting_plan      │
                  └──────────┬───────────┘
                             │ approved
                             ▼
                  ┌──────────────────────┐
                  │   drafting_tasks     │
                  └──────────┬───────────┘
                             │ approved
                             ▼
                  ┌──────────────────────┐
                  │     writing_disk     │  ◀── only here do files land
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │      executing       │  ◀── normal agent loop, scoped to tasks.md
                  └──────────────────────┘

  Any state can transition to `cancelled` on user Esc or `/skip-spec`.
  Any state can transition to `failed` on detector error or LLM error
  → fall back to normal agent loop with a warning toast.
```

The orchestrator runs this state machine. The TUI subscribes to
`SpecKitState.phase` reactive and renders the appropriate view.

---

## Events Auto-Spec-Kit emits

Add to `events.py` (new tagged-union variants extending the existing
`AgentEvent`):

```python
class SpecDetectorRan(_Base):
    kind: Literal["spec_detector_ran"]
    verdict: dict   # serialized Verdict

class SpecPhaseChanged(_Base):
    kind: Literal["spec_phase_changed"]
    old_phase: str
    new_phase: str

class SpecDraftChunk(_Base):
    kind: Literal["spec_draft_chunk"]
    artifact: Literal["spec", "plan", "tasks", "constitution"]
    chunk: str

class SpecApprovalRequested(_Base):
    kind: Literal["spec_approval_requested"]
    artifact: Literal["spec", "plan", "tasks", "constitution"]
    full_text: str

class SpecApprovalResolved(_Base):
    kind: Literal["spec_approval_resolved"]
    artifact: str
    approved: bool
    edits: str | None

class SpecFilesWritten(_Base):
    kind: Literal["spec_files_written"]
    feature_id: str
    paths: list[str]
```

---

## Disk layout (only after approval)

```
.specify/
└── memory/
    └── constitution.md          ← updated by writer if constitution-check
                                   produced changes; otherwise untouched

specs/
└── <NNN>-<slug>/
    ├── spec.md
    ├── plan.md
    ├── tasks.md
    └── .draft-history/           ← optional: each approval round saved
        ├── spec.draft-1.md
        ├── spec.draft-2.md
        └── …
```

Feature numbering rule: scan existing `specs/` for the highest `NNN-`
prefix and use `NNN+1`. Slug comes from the user's original prompt
via a 4-word summary.

---

## Integration with the agent loop

In `src/lyra_cli/cli/agent_integration.py`, find the function that
processes a new user message. Add this guard at the top:

```python
async def handle_user_message(prompt: str, session: Session) -> None:
    # NEW: Auto-Spec-Kit intercept
    if not session.spec_kit_active:
        verdict = await spec_orchestrator.maybe_intercept(prompt, session)
        if verdict.intercepted:
            # The orchestrator now owns the conversation until it
            # transitions to `executing` or `cancelled` / `failed`.
            return
    # Existing agent-loop path …
```

The orchestrator's `maybe_intercept` returns immediately with
`intercepted=False` for non-spec-worthy prompts. For spec-worthy ones
it kicks off the state machine and returns `intercepted=True`.

---

## TUI integration (the `SpecDrawer` widget)

A new widget under `src/lyra_cli/tui/widgets/spec_drawer.py`:

- Renders nothing when `SpecKitState.phase == "idle"`.
- Otherwise opens a right-side drawer (Textual `Horizontal` split) with:
  - The current phase as a title (`Drafting spec…`, `Awaiting approval`, etc.).
  - A streaming `Markdown` view of the current draft, fed by
    `SpecDraftChunk` events via `Markdown.get_stream()`.
  - An approval bar at the bottom: `[Enter] approve · [E] edit ·
    [R] redraft · [Esc] skip spec-kit`.
- When the user presses `E`, opens an inline editor with the current
  draft loaded.
- When `phase == "writing_disk"`, shows a checklist of files about to
  be written; the user confirms or cancels before the writer fires.

---

## Acceptance criteria (the user-visible behaviour)

When the implementation is done, this conversation must work:

```
> build me a deep-research orchestrator that runs 5 sub-agents in parallel
[spec-drawer opens]
[phase: detector ran, verdict: spec-worthy, confidence 0.91]
[phase: drafting_spec]
[spec streams in...]
[phase: awaiting approval]
Approve spec? [Enter] approve · [E] edit · [R] redraft · [Esc] skip spec-kit
> [Enter]
[phase: drafting_plan]
...
[phase: writing_disk]
Write these 3 files? specs/002-deep-research-orchestrator/{spec,plan,tasks}.md
[Y/n]
> y
[files written]
[phase: executing — normal agent loop scoped to tasks.md]
```

And this conversation must *not* trigger the drawer:

```
> fix the typo in README
[detector ran, verdict: not spec-worthy, confidence 0.12, exemption: small fix]
[normal agent loop proceeds]
```

---

## Things to be careful about

- **Detector latency.** The rule-based path must return in < 5 ms.
  The LLM-assisted path must time out at 800 ms and fall through to
  "not spec-worthy" on timeout — never block the user.
- **Memory hygiene.** `SpecKitState.spec_draft`, `plan_draft`,
  `tasks_draft` are large strings. Bound each at 100 KB; truncate
  gracefully.
- **Detector misclassification recovery.** If the user types `/skip-spec`
  or presses `Esc` during any phase, drop the state machine and
  fall through to normal agent-loop with the original prompt
  preserved.
- **Idempotent disk writes.** If `specs/<NNN>-<slug>/spec.md` already
  exists, append a `.draft-N` suffix instead of overwriting. Surface
  the conflict to the user.
- **Constitution evolution.** If the user's prompt implies a
  principle update (e.g., "from now on every feature must have a
  performance budget"), the constitution-check phase MUST surface
  that as a proposed constitution amendment with a Sync Impact Report
  comment — do not silently mutate the constitution.

---

## Final instruction

Begin with **Phase 1 — Read and plan**. Do not edit any files yet.
When the plan is ready, post it as a single message and stop. Wait
for the user to type "go" before proceeding to Phase 2.

Use sub-agents in parallel where useful (e.g., one to read the
existing TUI feature, one to scan the interactive modules, one to
study the github/spec-kit upstream templates for reference).
