# Model Configuration & Effort Levels (code.claude.com/docs)

Source: Claude Code official documentation (Anthropic). No explicit date on the page, but references Claude Code v2.1.154 for Opus 4.8, so content is current as of mid-2026.

## Key Technical Claims

1. **Model aliases provide abstraction over versioned models.** Alias resolution is provider-aware (Anthropic API, Bedrock, Vertex, Foundry all resolve differently). Aliases can be overridden via three environment variables: `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`.

2. **`opusplan` is a dual-phase hybrid.** Plan mode uses Opus (200K context only); execution mode auto-switches to Sonnet. This is a *model alias* not a separate binary -- the switch is transparent to the user.

3. **Five effort levels: low, medium, high, xhigh, max** -- new adaptive-reasoning mechanism distinct from old fixed thinking budget. Effort controls how much thinking happens on each turn, dynamically. "The effort scale is calibrated per model, so the same level name does not represent the same underlying value across models."

4. **Ultracode is not an effort level.** It is a Claude Code setting that sends `xhigh` effort to the model AND additionally has Claude orchestrate dynamic workflows for substantive tasks.

5. **Enterprise model governance uses a three-setting lock**: `availableModels` (restrict picker), `model` (initial selection), `ANTHROPIC_DEFAULT_*_MODEL` (pin what Default resolves to). All three must be set for full control.

6. **`modelOverrides` maps Anthropic model IDs to provider-specific strings** (Bedrock ARNs, Vertex names, etc.) for enterprise routing without changing alias logic.

7. **Prompt caching is automatic** per model tier, with disable kill-switches at global and per-tier level.

## Architecture/Mechanism Details

**Model resolution priority** (highest to lowest):
1. `/model` during session (v2.1.153+ also saves as default)
2. `claude --model <alias|name>` at startup
3. `ANTHROPIC_MODEL` environment variable
4. Settings file `model` field

**Effort level resolution**:
- Env var `CLAUDE_CODE_EFFORT_LEVEL` > frontmatter > session setting > model default
- Invalid effort falls back to highest supported level at or below requested level
- `low`/`medium`/`high`/`xhigh` persist across sessions; `max` is session-only (except via env var)
- `ultracode` is session-only, not settable in settings or via `--effort` flag

**Adaptive reasoning**:
- Opus 4.7+ always use adaptive reasoning (no fixed budget mode available)
- Opus 4.6 and Sonnet 4.6 can revert to fixed budget via `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`
- Adaptive thinking uses the effort level as the primary control

**Extended context (1M tokens)**:
- Opus 1M is auto-included on Max/Team/Enterprise plans
- Sonnet 1M always requires usage credits
- API/pay-as-you-go has full access to 1M
- 1M can be enabled per-alias via `[1m]` suffix on model env vars
- 1M is NOT applied to the plan-mode Opus phase of `opusplan` (capped at 200K)

## Numbers & Benchmarks

| Feature | Models | Levels |
|---------|--------|--------|
| Opus 4.8 / 4.7 | effort levels | low, medium, high, xhigh, max |
| Opus 4.6 / Sonnet 4.6 | effort levels | low, medium, high, max |
| Default effort | Opus 4.8/4.6, Sonnet 4.6 | **high** |
| Default effort | Opus 4.7 | **xhigh** |
| Context | `opusplan` plan phase | 200K (no 1M upgrade) |
| Context | `opus[1m]` / `sonnet[1m]` | 1M tokens |
| Min version | Opus 4.8 support | Claude Code v2.1.154 |

**Fallback rule**: Unsupported effort falls to highest supported below it. Example: `xhigh` runs as `high` on Opus 4.6.

**Key design decision**: Effort is per-model calibrated, not absolute. Same label across models = different underlying behavior.

## Transfer to Lyra

**One idea**: Adopt the `opusplan` dual-phase routing pattern + effort-level adaptive reasoning for Lyra's agent orchestration.

**How it maps**:
- Lyra already has a plan/strategy phase and an execution phase in its agent loop. Route the plan phase to the highest-capability model available (Opus-tier) and execution to a cost-efficient model (Sonnet/Haiku-tier). This directly parallels `opusplan`.
- Implement effort-level-like tiers for Lyra's sub-agent calls (not just model selection but thinking budget allocation). Low-effort tasks get fast path with minimal orchestration; high-effort tasks get multi-step reasoning with verification.
- Use the fallback pattern: if a model or capacity is unavailable, fall to the next available tier rather than failing.
- The dual-phase separation (200K context for planning, potentially 1M for execution) maps well to Lyra's need to maintain separate reasoning and execution contexts.

**Workstream route**: **Section 4.3 -- Route Planner** (Model routing tier / adaptive think budget per agent phase).

**Impact**: High. This is a concrete, tested pattern from a production system that directly addresses Lyra's model-cost-vs-quality tension.

**Effort**: Medium. The `opusplan` pattern is architectural (agent dispatch) rather than requiring deep research, but integrating effort-level adaptation into Lyra's planner requires careful instrumentation of thinking budgets.
