---
title: The agent loop
description: The kernel of Lyra — how a turn is assembled, sent, observed, and terminated.
---

# The agent loop <span class="lyra-badge intermediate">intermediate</span>

The agent loop is Lyra's **kernel**. It's deliberately small — under
200 lines in `lyra_core.loop` — so its semantics fit in a reviewer's
head. If you understand this page, you understand 80% of Lyra.

Source: [`lyra_core/loop/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/loop) ·
canonical spec: [`docs/blocks/01-agent-loop.md`](../blocks/01-agent-loop.md).

## What it does

1. **Assemble** the transcript from `SOUL.md` + plan + recent context.
2. **Call** the model with the tools allowed by the current permission mode.
3. For each tool call: **decide** (PermissionBridge) → **pre-hook** →
   **execute** → **post-hook** → **reduce** the observation → **append**.
4. **Detect termination**: end-of-turn, budget exhausted, safety flag,
   user interrupt, or stalemate.
5. **Persist** session state on every step (STATE.md, recent.jsonl, OTel
   spans, JSONL trace).

Everything else — planning, verification, memory writes, skill
extraction — runs **outside** the loop, at turn or session boundaries.

## One picture

```mermaid
sequenceDiagram
    autonumber
    participant U as User / Plan
    participant CE as Context Engine
    participant LP as Agent Loop
    participant LLM as LLM
    participant PB as Permission Bridge
    participant H as Hooks
    participant T as Tool
    participant ST as State

    U->>CE: task
    CE->>LP: assembled transcript
    loop until end-of-turn / budget / interrupt
        LP->>LLM: chat(transcript, allowed_tools)
        LLM-->>LP: text + tool_calls
        loop per tool call
            LP->>PB: decide(call, session)
            PB-->>LP: allow / ask / deny / park
            LP->>H: PreToolUse(call)
            H-->>LP: allow / block + critique
            LP->>T: execute
            T-->>LP: observation
            LP->>H: PostToolUse(observation)
            LP->>ST: persist
            LP->>CE: reduce + append
        end
    end
```

## The pseudo-code

This is a faithful sketch of `lyra_core.loop.AgentLoop.run`:

```python title="agent_loop.py"
def agent_loop(session: Session, task: str, *, plan: Plan | None = None) -> LoopResult:
    transcript = context_engine.assemble(session, task, plan)
    repeat_guard = RepeatDetector(window=16, threshold=3)

    with tracer.span("agent.run", session=session.id) as run_span:
        for step in range(session.budgets.max_steps):

            # ── Preflight (compaction, budget, interrupt) ────────────
            if transcript.tokens > session.budgets.max_tokens * 0.85:
                transcript = context_engine.compact(transcript, session)  # (1)
            if session.cost_usd >= session.budgets.max_cost_usd:
                return LoopResult.cost_exhausted(session, transcript, step)
            if session.interrupted:
                return LoopResult.user_interrupt(session, transcript, step)

            # ── Think (model call) ───────────────────────────────────
            resp = model.chat(transcript, tools=session.allowed_tools)
            transcript.append_assistant(resp)

            # ── Act (tool calls) ─────────────────────────────────────
            for call in resp.tool_calls:
                decision = permission_bridge.decide(call, session)        # (2)
                if decision.is_block:
                    transcript.append_tool_block(call, decision.reason)
                    continue

                pre = hooks.dispatch(HookEvent.PRE_TOOL_USE, call, session) # (3)
                if pre.block:
                    transcript.append_tool_block(call, pre.reason)
                    continue

                obs = tool_pool.invoke(call)                              # (4)

                post = hooks.dispatch(HookEvent.POST_TOOL_USE, obs, session)
                obs = obs.with_critique(post.annotation)

                transcript.append_tool_observation(call, obs)             # (5)
                state_store.persist(session, transcript)

            # ── Termination check ────────────────────────────────────
            if resp.is_end_of_turn:
                hooks.dispatch(HookEvent.STOP, session)                   # (6)
                return LoopResult.complete(session, transcript, step)

            if repeat_guard.is_stalemate(transcript):
                return LoopResult.stalemate(session, transcript, step)

        return LoopResult.steps_exhausted(session, transcript, step)
```

1. **Compaction** lives in the [Context Engine](context-engine.md) and
   replaces older turns with a summary while preserving SOUL, plan,
   and the keep-window.
2. **Permission Bridge** is the [runtime authorization
   primitive](permission-bridge.md). It returns one of `allow`, `ask`,
   `deny`, or `park`. The LLM never holds the keys.
3. **Pre-hooks** are deterministic Python that can block before
   execution — secret scanner, TDD gate, destructive-pattern check.
4. The **tool pool** is just a registered catalogue; built-ins
   (`read`, `write`, `bash`, `grep`, …) and MCP-provided tools are
   indistinguishable to the loop.
5. The observation is **reduced** to fit the transcript. Big payloads
   (`Read` of a 500-line file) are stored as artifacts and the
   observation carries the reference, not the bytes.
6. The **`STOP` hook** is your last chance — that's where the TDD gate
   blocks session completion if the test gate is on and tests are red.

## Termination conditions

There are five ways a turn ends. All of them are deterministic:

| Reason | Trigger |
|---|---|
| `complete` | Model emits `is_end_of_turn=True` and `STOP` hook didn't block |
| `cost_exhausted` | `session.cost_usd >= max_cost_usd` |
| `steps_exhausted` | `step >= max_steps` |
| `user_interrupt` | `Ctrl-C` set `session.interrupted` |
| `stalemate` | RepeatDetector saw the same tool-call signature 3 times in a 16-call window |

`stalemate` is the most surprising one — it exists because LLMs
sometimes fall into a "read-the-same-file-forever" loop. The detector
hashes `(tool_name, args_normalized)` and bails when it sees the same
signature too often.

## What runs *outside* the loop

These deliberately don't live in the kernel — they run at boundaries
so the loop stays small:

| Concern | When |
|---|---|
| Planning | Before first turn, in [`plan_mode`](../start/four-modes.md#plan_mode-design-before-code) |
| Verification (test runs) | Driven by the TDD gate hook on `POST_TOOL_USE` and `STOP` |
| Memory writes (observations, summaries) | On compaction and on `SESSION_END` |
| Skill extraction | After `SESSION_END`, in a background process |
| Trace export (HIR / OTel) | Streamed during the loop, finalized on `SESSION_END` |

This is the **load-bearing design choice** of Lyra: keep the kernel
small, push everything else to hooks and boundaries.

## Where to look in the source

| File | What lives there |
|---|---|
| `lyra_core/loop/agent_loop.py` | `AgentLoop.run` — the function above |
| `lyra_core/loop/repeat_detector.py` | Stalemate detection |
| `lyra_core/loop/result.py` | `LoopResult` dataclass and termination classifiers |
| `lyra_core/state/store.py` | Per-step persistence to disk |

[← Concepts overview](index.md){ .md-button }
[Continue to Tools and hooks →](tools-and-hooks.md){ .md-button .md-button--primary }
