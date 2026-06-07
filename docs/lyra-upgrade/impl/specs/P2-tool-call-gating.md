# P2: Deterministic Tool-Call Gating (Breakthrough #3)

> Plan: §4.17 | Depends on: S2, S8 | Breakthrough #3

## Scope
Intercept all tool calls against LLM-generated least-privilege policy with deterministic enforcement. ASR reduction from 39.9% to 1.0%.

## Key Design
1. **Policy generation**: LLM generates least-privilege policy from task context
2. **Deterministic enforcement**: validate tool calls against policy (no LLM in enforcement path)
3. **Gating levels**: ALLOW, ALLOW_WITH_SANDBOX, ASK_USER, BLOCK
4. **Audit log**: every gating decision logged immutably
