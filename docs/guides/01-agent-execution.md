# Guide: Agent Execution

> 📖 Guide — Walk through a complete agent execution from task to output. Learn how the agent loop, plan mode, and key controls work in practice.

This guide follows a single task through Lyra's execution pipeline so you understand what happens at each stage and which controls affect the outcome.

---

## The Execution Pipeline

A task flows through five stages:

**Task In -> Plan (optional) -> Dispatch Subagents -> Verify -> Consolidate -> Output**

### 1. Task Entry

You submit a task via the CLI:

```bash
lyra run "Add dark mode toggle that persists across reloads"
```

Lyra's heuristics engine evaluates the task. If it mentions multiple files, vague requirements, or architectural keywords (design, refactor, migrate), the planner activates automatically. Trivial tasks skip straight to the agent loop.

### 2. Plan Mode

When activated, the planner produces a plan artifact under `.lyra/plans/<session-id>.md`:

```markdown
# Plan: Add dark mode toggle
## Expected files
- src/settings/ThemeToggle.tsx
- src/settings/useTheme.ts
## Steps
1. Add useTheme hook with localStorage persistence
2. Create ThemeToggle component
3. Mount in App.tsx
```

You review it and type `/approve` to give the go-ahead. Plans include acceptance tests, forbidden files, and a goal hash -- all used later by the verifier. See the [Plan Mode concept](../concepts/05-plan-mode.md) for the full schema.

### 3. Dispatch & Execution

The agent loop (under 200 lines) runs the think-act-observe cycle:

```
assemble context -> model.chat() -> permission check -> hooks -> tool execution -> compression check -> repeat
```

Each step costs roughly 2s P50 (88% of time is the model call). Tools execute sequentially for determinism. For complex tasks, the loop delegates to fleet orchestration (DAG teams) at effort level `ultracode`.

### 4. Verification

After execution, the verifier checks output against the plan: acceptance tests pass, expected files exist, forbidden files untouched, steps executed in order. The Refute/Promote loop catches issues a single agent would miss.

### 5. Consolidation

Results are written to session state under `.lyra/sessions/<session-id>/`:

- `STATE.md` -- human-readable metadata (loaded by `/resume`)
- `recent.jsonl` -- last N transcript turns
- `trace.jsonl` -- full HIR event stream
- `artifacts/` -- hash-addressed immutable payloads

---

## Key Controls

| Control | What It Does |
|---|---|
| `/model <name>` | Pin model for current session (e.g., `/model claude-opus-4-7`) |
| `/effort <level>` | Override effort: low / medium / high / ultracode |
| `/plan` | Force plan mode on/off |
| `/bg` | Run session in background (unattended L3+) |
| `--auto-approve` | Bypass plan approval gate (CI use) |

---

## Autonomy Escalation Ladder

| Level | Name | Human Role |
|---|---|---|
| L0 | Hand-hold | Approves every tool call |
| L1 | Supervised | Batch-approves writes |
| L2 | Steer-by-exception | Alerts only |
| L3 | Unattended | Row summaries |
| L4 | Autonomous | Periodic briefings |

---

## Related Docs

- [Architecture: Agent Loop](../blocks/01-agent-loop.md) -- the core loop deep-dive
- [Concept: Plan Mode](../concepts/05-plan-mode.md) -- plan artifact schema and approval flow
- [Concept: Sessions and State](../concepts/08-sessions-and-state.md) -- persistence model
- [Guide: Fleet Orchestration](04-fleet-orchestration.md) -- multi-agent DAG execution
- [Guide: Research and Verification](07-research-and-verification.md) -- verification pipeline
