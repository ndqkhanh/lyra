# Effort (Anthropic Claude Platform Docs)

**Source:** `https://platform.claude.com/docs/en/build-with-claude/effort` -- Official Anthropic documentation, no author/date listed.

---

## Key Technical Claims

1. The `effort` parameter (passed inside `output_config`) controls how many tokens Claude spends on a response, enabling a single-model trade-off between thoroughness and token efficiency.
2. Five effort levels exist: `low`, `medium`, `high` (default), `xhigh`, `max`. Model support varies: `xhigh` is available only on Opus 4.8 and Opus 4.7; `max` is available on Opus 4.8, Mythos, Opus 4.7, Opus 4.6, and Sonnet 4.6.
3. Effort affects **all tokens** in the response -- text, tool calls, and extended thinking. This is a critical architectural difference from the deprecated `budget_tokens` parameter (which only constrained thinking tokens).
4. Setting `effort: "high"` is equivalent to omitting the parameter entirely.
5. Effort is a **behavioral signal**, not a strict token budget. At lower levels, Claude still thinks on sufficiently difficult problems, just less than it would at higher levels for the same problem.
6. On modern models (Opus 4.8, Opus 4.7, Sonnet 4.6), effort replaces `budget_tokens` as the recommended control. Adaptive thinking (`thinking: {type: "adaptive"}`) + effort is the recommended combination.

---

## Architecture / Mechanism Details

- **New API field**: `output_config: { effort: "medium" }` in the Messages API request body. Available on all supported models with no beta header.
- **ZDR eligible**: Data sent through this feature is not stored after the API response is returned for organizations with Zero Data Retention arrangements.
- **Relationship to Claude Code's ultracode**: Ultracode is NOT a separate API effort level. It pairs `xhigh` with standing permission for multi-agent workflows via mid-conversation system messages. The API's complete effort set is `low`, `medium`, `high`, `xhigh`, `max`.
- **Effort + Extended Thinking**:
  - Opus 4.8: Uses adaptive thinking by recommendation. Manual `thinking: {type: "enabled", budget_tokens: N}` returns a 400 error. Set `thinking: {type: "adaptive"}` to enable thinking alongside effort.
  - Opus 4.7: Same as Opus 4.8 -- adaptive thinking + effort replaces manual budget_tokens.
  - Sonnet 4.6: Adaptive thinking recommended; interleaved mode still functional but deprecated.
  - Opus 4.5: Still uses manual thinking (`thinking: {type: "enabled", budget_tokens: N}`); effort works alongside the thinking token budget.
- **Effort + Tool Use**:
  - Low effort: combines operations into fewer calls, makes fewer total calls, proceeds directly, terse confirmations.
  - High effort: makes more calls, explains plans before actions, detailed summaries, comprehensive comments.
- **Recommended `max_tokens`**: At `xhigh`/`max` on Opus 4.7/4.8, start at 64k tokens and tune from there.

---

## Numbers & Benchmarks

- **`xhigh` target use case**: Long-running agentic and coding tasks **over 30 minutes** with token budgets in the **millions**.
- **`max_tokens` starting point**: 64k for Opus 4.7/4.8 at xhigh/max effort.
- **Opus 4.7 guidance**: Start with `xhigh` for coding/agentic; reserve `max` only when evals show headroom above `xhigh`. On most workloads `max` adds significant cost for small quality gains, and on structured-output tasks can lead to overthinking.
- **Sonnet 4.6 guidance**: `medium` is recommended default for most applications (agentic coding, tool-heavy workflows). `low` for high-volume/latency-sensitive workloads.
- **Effort respects levels more strictly on Opus 4.7**: At `low`/`medium` the model scopes work to exactly what was asked rather than going above and beyond.

---

## Transfer to Lyra

**One transferable idea**: Implement **dynamic effort tiering** across Lyra's subagent architecture. Currently Lyra (like most harnesses) likely uses a single effort level for all calls. Route each subagent invocation to an effort level based on task classification:

| Tier | Effort | max_tokens | Example subagent tasks |
|------|--------|------------|------------------------|
| T1 (lookup) | `low` | 4k | classification, simple extraction, keyword search |
| T2 (standard) | `medium` | 16k | code generation, tool-calling, summarization |
| T3 (deep) | `high` | 32k | multi-step reasoning, debugging, PR review |
| T4 (frontier) | `xhigh`/`max` | 64k | architecture debate, adversarial verification, breakthrough synthesis |

This mirrors Opus 4.7's recommended pattern and aligns with Sonnet 4.6's cost-efficiency profile. The key insight is that effort affects **tool call quantity** not just thinking depth -- so low-effort agents will naturally make fewer tool calls, reducing both latency and cost on simple operations. For Lyra's high-volume subagent workflows (research, verification, code review), this could yield 2-5x cost reduction on the majority of calls without meaningful quality degradation.

**Route**: Section 4.x -- fits naturally under §4.3 (Agent Orchestration and Routing) or as a new §4.x on Cost-Efficient Agent Tiering. The brainstorming document at `docs/lyra-upgrade/brainstorm/05-router.md` is the natural home for this design.
