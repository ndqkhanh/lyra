# Lyra Block 01 — Agent Loop

The agent loop is the kernel of Lyra. It assembles context, invokes the model, authorizes tool calls through [PermissionBridge](04-permission-bridge.md) and [Hooks](05-hooks-and-tdd-gate.md), executes tools, folds observations back into the transcript, and decides termination. It is deliberately short so that its semantics fit in a reviewer's head.

The loop builds on [`harness_core.loop.AgentLoop`](../../../orion-code/harness_core/src/harness_core/loop.py) and extends it with Lyra-specific concerns: TDD phase tracking, repeat detection, safety monitor integration, HIR-compatible tracing, cost/budget enforcement, and session persistence.

Upstream reference: [Orion-Code Block 01](../../../orion-code/docs/blocks/01-agent-loop.md). [Claude Code audit](../../../../docs/29-dive-into-claude-code.md) for loop philosophy.

## Responsibility

One function, clearly-delimited concerns:

1. Build transcript from `SOUL.md` + plan + recent context.
2. Call model with the tools allowed by the current permission mode.
3. For each tool call: `PermissionBridge.decide` → pre-hook → execute → post-hook → reduce observation → append.
4. Detect termination: model end-of-turn, budget exhausted, safety flag, user interrupt, stalemate.
5. Persist session state on every step (STATE.md, recent.jsonl, OTel spans, JSONL trace).

Everything else — planning, verification, memory writes, skill extraction — is outside the loop and runs at turn or session boundaries.

## Pseudo-code

```python
def agent_loop(
    session: Session, task: str, *, plan: Plan | None = None,
) -> LoopResult:
    transcript = context_engine.assemble(session, task, plan)
    repeat_guard = RepeatDetector(window=16, threshold=3)

    with tracer.span("agent.run", session=session.id, hir="agent_loop") as run_span:
        run_span.attrs["model.generator"] = session.model_selection.generator
        run_span.attrs["permission.mode"] = session.permission_mode.value
        run_span.attrs["tdd.enabled"] = session.config.tdd.enabled

        for step in range(session.budgets.max_steps):
            # ── Preflight ─────────────────────────────────────────────
            if transcript.tokens > session.budgets.max_tokens * 0.85:
                transcript = context_engine.compact(transcript, session)
                tracer.event("compaction", hir="compaction_event",
                             tokens_before=transcript.tokens_before_compact,
                             tokens_after=transcript.tokens)
            if session.cost_usd >= session.budgets.max_cost_usd:
                return LoopResult.cost_exhausted(session, transcript, step)
            if session.interrupted:
                return LoopResult.user_interrupt(session, transcript, step)

            # ── Think (model call) ────────────────────────────────────
            with tracer.span("agent.step", step=step, hir="agent_loop") as sp:
                resp = model.chat(
                    transcript,
                    tools=tool_layer.schemas(session.permission_mode),
                    prompt_cache=session.cache_config,
                )
                transcript.append(resp)
                session.cost_usd += resp.cost_usd
                sp.attrs["tool_calls"] = len(resp.tool_calls)
                sp.attrs["cost_usd"] = resp.cost_usd
                sp.attrs["tokens.in"] = resp.tokens_in
                sp.attrs["tokens.out"] = resp.tokens_out

            # ── Termination by model ─────────────────────────────────
            if not resp.has_tool_calls() or resp.stop_reason == StopReason.END_TURN:
                return finalize(session, transcript, step)

            # ── Act (tool calls) ──────────────────────────────────────
            for call in resp.tool_calls:
                call = repeat_guard.check(call)
                if call is None:
                    transcript.append(
                        tool_result_repeat_suppressed(call, nudge=repeat_guard.nudge())
                    )
                    continue

                decision = permission_bridge.decide(call, session)
                tracer.event("permission.decide", hir="permission_check",
                             decision=decision.decision, reason=decision.reason)

                if decision.decision == "deny":
                    transcript.append(tool_result(call, f"blocked: {decision.reason}"))
                    continue
                if decision.decision == "ask":
                    if not approval.request(call, session):
                        transcript.append(tool_result(call, "rejected by user"))
                        continue
                if decision.decision == "park":
                    session.parked_calls.append(call)
                    transcript.append(tool_result(call, "parked pending approval"))
                    continue

                pre = hooks.run(HookEvent.PRE_TOOL_USE, call, session)
                tracer.event("hook.pre", hir="hook", name=pre.name, block=pre.block)
                if pre.block:
                    transcript.append(
                        tool_result(call, critique=pre.to_critique())
                    )
                    continue

                # ── Execute ───────────────────────────────────────────
                with tracer.span(f"tool.{call.name}", hir="tool_use") as t_sp:
                    result = tool_layer.execute(call, session)
                    t_sp.attrs["is_error"] = result.is_error
                    t_sp.attrs["bytes"] = len(result.content)

                post = hooks.run(HookEvent.POST_TOOL_USE, call, result, session)
                tracer.event("hook.post", hir="hook", name=post.name,
                             annotation=bool(post.annotation))
                if post.annotation:
                    result = result.with_annotation(post.annotation)

                observation = context_engine.reduce(result, session)
                transcript.append(tool_result(call, observation))

                # ── Safety monitor check ──────────────────────────────
                if safety_monitor.should_check(step):
                    verdict = safety_monitor.check(session)
                    tracer.event("safety.check", hir="verifier_call",
                                 flag=verdict.flag)
                    if verdict.flag:
                        persist_state_for_review(session, verdict)
                        raise SafetyViolation(verdict)

            # ── Per-step persistence ──────────────────────────────────
            session.persist_recent(transcript.tail(n=8))
            state_md.update(session, transcript)

        return LoopResult.step_budget_exhausted(session, transcript)
```

## Key contracts

### Termination conditions

| Condition | Trigger | Return status |
|---|---|---|
| Model end-of-turn | `resp.stop_reason == END_TURN` or no tool calls | `completed` |
| Step budget | `step >= max_steps` | `step_budget_exhausted` |
| Token budget | unrecoverable even after compaction | `token_budget_exhausted` |
| Cost budget | `cost_usd >= max_cost_usd` | `cost_exhausted` |
| User interrupt | SIGINT / web-viewer "pause" button | `user_interrupt` |
| Safety flag | safety monitor verdict | `safety_violation` |
| Evaluator stalemate | N rounds of reject (handled by harness plugin, not loop) | `evaluator_stalemate` |
| Hard tool failure | critical exception in tool layer | `tool_failure` |

### Repeat detection

`RepeatDetector` hashes `(name, normalized_args)` into a bloom filter with recency weighting. After `threshold` repeats within a window, it:

1. Suppresses the call and injects a structured "you've tried this before and it didn't help" observation.
2. Suggests diversifying (different args, different tool, ask user, switch strategy).
3. After two consecutive suppressions, bumps the session to `human_review` state.

This catches the "hammering the same tool" pathology common in long traces.

### Observation reduction

Raw tool outputs rarely belong in the transcript verbatim. `context_engine.reduce` trims:

- **Long text** → first N lines + tail + "middle elided" marker; full content offloaded to `artifacts/<hash>` and referenced.
- **Binary / blob** → byte count + MIME guess + hash reference; never inline.
- **Error traces** → top N frames + file:line anchors; full trace offloaded.
- **Git diffs** → summary line count + file list + first-N-hunks; full diff is an artifact.
- **Test output** → pass/fail summary + first failure block; full output artifact.

A `View` tool (or the `mem` MCP retrieval) fetches the full artifact on demand.

## Integration points

- **Context Engine** ([block 06](06-context-engine.md)): `assemble`, `compact`, `reduce`.
- **Permission Bridge** ([block 04](04-permission-bridge.md)): `decide(call, session) → Decision`.
- **Hooks** ([block 05](05-hooks-and-tdd-gate.md)): `run(event, call, ...) → HookResult`.
- **Tool Layer** ([block 14](14-mcp-adapter.md) + native tools): `schemas(mode)`, `execute(call, session)`.
- **Memory** ([block 07](07-memory-three-tier.md)): read within `reduce`, write on explicit events.
- **Safety Monitor** ([block 12](12-safety-monitor.md)): `should_check`, `check`.
- **Observability** ([block 13](13-observability.md)): every decision produces a trace event with HIR tag.

## Session persistence

Every step the loop persists:

- `recent.jsonl`: last 8 turns + deltas (cheap append).
- `STATE.md`: phase, open questions, current hypothesis, cost running tally.
- Trace span flushed to JSONL and OTel exporter.

On crash, `lyra run --resume <session-id>` replays: read STATE.md, rebuild transcript from plan + recent.jsonl + memory references, resume loop from the step after the last persisted one. Session-branch git commits are atomic checkpoints a full step can safely revert to.

## Model routing

As of **v2.7.1** every model call inside (and adjacent to) the loop runs through a single resolver, `_resolve_model_for_role(session, role)`, that maps each call's role to one of two slots on the session:

| Role keyword                                                | Slot   | What invokes it                                              |
|-------------------------------------------------------------|--------|--------------------------------------------------------------|
| `chat`                                                      | fast   | inside-loop `model.chat()` calls (generator)                 |
| `plan`                                                      | smart  | planner ([block 02](02-plan-mode.md)) — runs *before* the loop |
| `spawn` / `subagent`                                        | smart  | each `/spawn` subagent's own loop ([block 10](10-subagent-worktree.md)) |
| `cron`                                                      | smart  | scheduled fan-out via the cron daemon                        |
| `review` / `verify`                                         | smart  | post-turn diff reviewer; Phase-2 LLM evaluator ([block 11](11-verifier-cross-channel.md)) |
| any unknown role                                             | falls back to `session.model` (legacy "auto" pin) | escape hatch for `--model <slug>` |

The fast slot defaults to `deepseek-v4-flash` (resolves to the DeepSeek API slug `deepseek-chat`), the smart slot defaults to `deepseek-v4-pro` (resolves to `deepseek-reasoner`). Both are re-pinnable per session via `/model fast=<slug>` / `/model smart=<slug>`, or persistently in `~/.lyra/settings.json` (`fast_model` / `smart_model`).

When the resolved alias differs from the cached provider's `model` attribute, Lyra **mutates the cached provider in place** (setting `provider.model = "<resolved-slug>"`) and stamps both `HARNESS_LLM_MODEL` (universal) and the provider-specific override (`DEEPSEEK_MODEL`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`) so a freshly built provider lands on the same slug. Chat history, MCP plumbing, and the budget meter all stay attached.

```yaml
# ~/.lyra/settings.json or config.yaml fragment
fast_model:  deepseek-v4-flash    # → deepseek-chat
smart_model: deepseek-v4-pro      # → deepseek-reasoner
default_model: auto               # legacy universal pin; "auto" defers to slot routing

# Legacy four-role layout still accepted; mapped onto fast/smart at load:
models:
  generator: anthropic/claude-sonnet-4-6   # → smart slot (review-tier)
  planner:   anthropic/claude-opus-4-7
  evaluator: openai/gpt-5
  safety:    openai/gpt-5-nano
  fallbacks:
    generator: [openai/gpt-5, google/gemini-2.5-pro]
```

On provider 5xx, the loop transparently retries three times with exponential backoff; on the fourth failure it pivots to the first configured fallback (preserving the role → slot mapping) and emits a `model.fallback` trace event.

## Cost accounting

Every `model.chat` call returns `cost_usd`. The loop accumulates into `session.cost_usd`. Tool calls may contribute cost too (MCP-called external services often bill per-call); the tool's metadata includes a cost estimator and the loop uses it to update running cost. Budget overruns raise `CostCapHit` which the CLI surfaces with friendly remediation (*extend budget? investigate what was expensive?*).

## Prompt caching

Caching layout (Anthropic-style breakpoints; analogous on OpenAI/Gemini):

- **L1 cached prefix** (rarely changes): system prompt + tool definitions.
- **L2 cached mid** (changes per-session but stable within): SOUL.md + plan summary + permission mode notes.
- **L3 dynamic suffix** (changes per-step): recent turns + tool results.

The `prompt_cache` config passed into `model.chat` describes breakpoints; on provider that supports it, 50-90% cost savings on repeated calls are typical.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Infinite tool retry | RepeatDetector + `max_steps` |
| Context explosion | Compaction trigger + offload + observation reduction |
| Runaway cost | `max_cost_usd` hard stop |
| Silent drift from task | Safety monitor + evaluator at turn boundary |
| Tool failure cascades | `ToolResult.is_error=True` becomes an observation the model can recover from |
| Transcripts non-recoverable | STATE.md + recent.jsonl + trace replay |
| Hook feedback loops (block → retry → block) | Hook cooldown; critique escalates to `human_review` after N consecutive blocks |
| Compaction introduces lossy summary | Compaction events produce a hash + reference to the pre-compaction transcript artifact for audit |

## Metrics emitted

- `agent.step.count`
- `agent.step.duration_ms` (histogram)
- `agent.step.tokens_in / tokens_out`
- `agent.tool_calls.total` labeled by tool name
- `agent.hook.blocks.total` labeled by hook name
- `agent.permission.denies.total`
- `agent.repeat.suppressions.total`
- `agent.cost.usd.total` labeled by model, feature item
- `agent.terminations.total` labeled by reason

These feed into the `lyra retro` subcommand and web viewer dashboards.

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_loop.py` | Branch coverage of each termination path with MockLLM |
| Unit `test_repeat_detector.py` | Hash collision + recency windows |
| Integration | Real filesystem + scripted MockLLM run through RED→GREEN→commit sequence |
| Property | Monotonic cost accounting; transcript is append-only |
| Replay | Pre-recorded traces regression-test new loop versions |
| Red-team | LaStraj-style forced-infinite-tool, hostile permission escalation attempts |

See [`tests/unit/test_loop.py`](../../tests/unit/test_loop.py) once scaffolded.

## Open questions

1. **Streaming tool-call execution.** Current loop is batched; streaming lets tool results inform the in-flight model response. Requires more elaborate cache invalidation. v2 exploration.
2. **Parallel tool calls.** If the model emits N independent tool calls, we could fan out. v1 runs them sequentially to simplify ordering and observation attribution.
3. **Preemption.** User editing files mid-session: currently the loop re-reads on next `Read`. Smarter file-watcher integration deferred.
4. **LLM call cancellation mid-generation.** Some providers support interruption; we do not use it in v1. User interrupt waits until the current generation returns.
