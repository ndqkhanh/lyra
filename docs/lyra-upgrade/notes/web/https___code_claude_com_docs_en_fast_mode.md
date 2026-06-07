# Fast Mode (Claude Code Docs, Anthropic)

## Key Technical Claims

- Fast mode is a high-speed configuration for Claude Opus, not a different model -- same quality (identical responses), lower latency, higher per-token cost.
- Up to **2.5x faster** response speed when enabled.
- Supported on Opus 4.8, Opus 4.7, and Opus 4.6. Not available on Sonnet or Haiku.
- Available to all subscription plan users (Pro/Max/Team/Enterprise) and Claude Console API, but **not** on Bedrock, Vertex AI, Azure Foundry, or CLAude Platform on AWS.
- In research preview -- pricing, availability, and API configuration may change.
- Opus 4.8 is the fast mode default in Claude Code v2.1.154+; on v2.1.142-v2.1.153 it defaults to Opus 4.7.

## Architecture/Mechanism Details

- Uses a different API configuration (likely reduced thinking budget, higher-priority inference scheduling, or speculative decoding) that prioritizes speed over cost efficiency.
- Toggled via `/fast` CLI command or `"fastMode": true` in user settings.
- Persists across sessions by default; admins can force per-session opt-in with `fastModePerSessionOptIn: true`.
- When fast mode is enabled, Claude Code auto-switches to Opus regardless of prior model.
- Separate rate-limit pool from standard Opus. All Opus fast mode models share the same rate-limit pool.
- On rate limit hit or credit exhaustion: automatic fallback to standard speed (grayed-out icon), auto-re-enables after cooldown.
- The first enable in a conversation incurs the full uncached input token price for the entire conversation context. Subsequent toggles do not repeat this cost. This is the key mechanism detail: the cost hit is front-loaded on first activation.

## Numbers & Benchmarks

| Metric | Value |
|--------|-------|
| Speedup | Up to 2.5x vs standard Opus |
| Opus 4.8 fast pricing | $10/MTok input, $50/MTok output |
| Opus 4.7/4.6 fast pricing | $30/MTok input, $150/MTok output |
| Pricing model | Flat across full 1M context window |
| Minimum CLI version | v2.1.36 |
| Opus 4.6 fast deprecation | ~30 days after Opus 4.8 launch |

## Transfer to Lyra

**One idea:** Offer a "fast-path" inference mode that trades per-token cost for lower latency on time-sensitive subtasks. The mechanism is analogous: a separate configuration of the same backend model (not a different model) that front-loads a context-read cost once per conversation, then delivers up to 2.5x faster responses.

**Workstream route:** This maps to **Section 4.1 -- API / Model Router** architecture. Lyra should expose a `fast_mode` flag or a `/fast` equivalent that is wired into the model router. When enabled, the router selects a different API parameter set (shorter thinking budget, reduced max_tokens, speculative decoding on the provider side) for the same underlying model. This avoids creating a separate "fast model" -- it keeps the routing logic uniform and only varies the configuration profile. The cost model (front-loaded context read, higher per-token rate) must be surfaced to the user so they can make informed tradeoffs. If Lyra is composable (routable to multiple providers), this pattern should be provider-agnostic: define a "fast profile" per provider, and let the router match the active model's fast profile.

**Next step:** Add a `FastModeProfile` interface to the model router (Section 4.1), with fields for `max_tokens`, `thinking_budget`, `pricing_multiplier`, and `context_read_policy`. Wire it to the session state so it toggles at conversation boundaries, not mid-stream.
