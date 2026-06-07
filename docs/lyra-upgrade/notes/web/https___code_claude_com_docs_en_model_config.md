# Model Configuration (Anthropic official docs -- code.claude.com)

> Fetched 2026-06-07. Source: https://code.claude.com/docs/en/model-config

## Key Technical Claims

1. **Model aliases** (`default`, `best`, `opus`, `sonnet`, `haiku`, `opus[1m]`, `sonnet[1m]`, `opusplan`) abstract provider-specific model IDs behind stable names. The same alias resolves to different concrete models depending on provider (Anthropic API, Bedrock, Vertex, Foundry, Claude Platform on AWS).

2. **`opusplan` alias** is a hybrid scheduler: uses `opus` during plan mode, then auto-switches to `sonnet` for execution/code generation. This gives Opus-level reasoning for architecture decisions and Sonnet efficiency for implementation -- all within a single session.

3. **Effort levels** (`low`, `medium`, `high`, `xhigh`, `max`) control adaptive reasoning per model. Default is `high` on Opus 4.8/4.6 and Sonnet 4.6, `xhigh` on Opus 4.7. Models that do not support a specified level fall back to the highest supported level at or below it.

4. **Extended context** (1M token window) is automatically enabled for Opus on Max/Team/Enterprise plans with no extra configuration. Sonnet 1M requires usage credits on all subscription plans. The 1M window uses standard model pricing with no premium beyond 200K.

5. **Enterprise model governance**: `availableModels` in managed/policy settings restricts which models users can select. To fully control the experience, administrators must combine `availableModels` + `model` (initial selection) + `ANTHROPIC_DEFAULT_*_MODEL` env vars (controls what `Default` resolves to).

6. **`modelOverrides`** maps Anthropic model IDs to provider-specific strings (Bedrock ARNs, Vertex versions, Foundry deployments) for governance, cost allocation, or regional routing.

7. **Custom model options**: `ANTHROPIC_CUSTOM_MODEL_OPTION` adds a single custom entry to the `/model` picker without replacing built-in aliases, useful for LLM gateway deployments or testing unreleased model IDs.

## Architecture/Mechanism Details

- **Resolution order** (highest to lowest priority): `/model` in-session switch -> `--model` startup flag -> `ANTHROPIC_MODEL` env var -> settings file `model` field.
- **Resumed sessions** keep the model from when the transcript was saved, regardless of current `model` setting.
- **`opusplan`**: Plan-mode Opus runs with the standard 200K context window (the automatic 1M upgrade does NOT extend to `opusplan`).
- **Subagent model routing**: `CLAUDE_CODE_SUBAGENT_MODEL` env var overrides all subagent and agent-team model selections. Set to `inherit` to use normal resolution.
- **Prompt caching**: Automatic. Configurable via `DISABLE_PROMPT_CACHING`, `DISABLE_PROMPT_CACHING_HAIKU`, `DISABLE_PROMPT_CACHING_SONNET`, `DISABLE_PROMPT_CACHING_OPUS`.
- **Third-party deployment pinning**: Use `_SUPPORTED_CAPABILITIES` env var suffix to declare features (effort, thinking, adaptive_thinking, interleaved_thinking, etc.) since provider-specific IDs may not match Claude Code's built-in pattern matching.

## Numbers & Benchmarks

- Opus 4.8 requires Claude Code v2.1.154+.
- `opusplan` Opus phase is capped at 200K context (not eligible for automatic 1M upgrade).
- Effort levels per model:
  - Opus 4.8, Opus 4.7: `low`, `medium`, `high`, `xhigh`, `max`
  - Opus 4.6, Sonnet 4.6: `low`, `medium`, `high`, `max`
- Default model by account type:
  - Max/Team Premium/Enterprise pay-go/API: Opus 4.8
  - Claude Platform on AWS: Opus 4.7
  - Pro/Team Standard/Enterprise subscription seats: Sonnet 4.6
  - Bedrock/Vertex/Foundry: Sonnet 4.5
- `max` effort level applies to current session only (except via `CLAUDE_CODE_EFFORT_LEVEL` env var). `ultracode` is also session-only.

## Transfer to Lyra (one idea)

**The `opusplan` hybrid scheduling pattern is the single most transferable idea.** Lyra's current architecture (as described in proposals) typically routes either to a single model or requires manual model selection per task phase. Adopting an `opusplan`-style pattern would let Lyra:

- Use a strong reasoning model (analogous to Opus) for planning, architecture analysis, and route selection.
- Auto-switch to a lighter, faster model (analogous to Sonnet) for execution -- code generation, tool calls, routine subagent delegation.
- Keep all routing decisions within a single session/agent lifecycle, eliminating cross-session coordination overhead.

**Workstream route recommendation:** This maps to a new `§4.5 Dynamic Model Router` in the Lyra architecture plan. Unlike the existing static per-workstream model assignment, the Dynamic Model Router would inspect the current phase (plan vs. execute vs. verify vs. research) and the task's complexity signal (estimated token budget, required reasoning depth) to select the right model on the fly, then cache the choice for the session.

## Concrete Suggestion

Implement a `TieredModelRouter` in Lyra's agent harness that exposes a `plan/execute/verify` mode switch (not just a static model config). On entering plan mode, route to the heavy model; on transitioning to execute, auto-drop to the fast model. This would be a small configuration-layer change (the agents and tools are already model-agnostic) with outsized cost savings -- Opus-level tokens only during planning/architecture phases, Sonnet for the bulk of code generation and iteration.
