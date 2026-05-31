# lyra-effort — Six-Item Effort Scale

Per-provider reasoning-budget control for Lyra. Implements the `/effort` menu:
low → medium → high → xhigh → max → ultracode

**Key invariant**: Ultracode = xhigh budget + orchestration toggle (NOT a 6th API tier).

| Provider | Mechanism |
|----------|-----------|
| Anthropic | `budget_tokens` API |
| DeepSeek | Prompt-level thinking instruction |
| OpenAI | `reasoning_effort` API |
| Google | Prompt-level thinking instruction |

[Plan: plans/19-ultracode-replication.md](../../lyra-upgrade/plans/19-ultracode-replication.md)
