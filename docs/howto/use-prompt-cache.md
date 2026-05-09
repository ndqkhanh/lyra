---
title: Use prompt caching across subagents
description: Recipes for opting subagent fan-outs into the prompt-cache coordinator so N readers of the same prefix cost the same as one.
---

# Use prompt caching across subagents <span class="lyra-badge howto">how-to</span>

The **prompt-cache coordinator** ships Lyra's hosted-API absorption
of [PolyKV](../research/polykv-evaluation.md) — one cache write paid
by the parent, `N − 1` hits paid by sibling subagents at the
provider's discount (50–90% off). This page is the hands-on
recipe.

For the *what* and the *why*, read
[Concept: prompt-cache coordination](../concepts/prompt-cache-coordination.md)
first.

## Recipe 1 — Pre-warm before fanning out subagents

The most common shape: a parent has assembled the shared context
(SOUL.md + plan summary + pinned files) and is about to spawn `N`
subagents that will all read it.

```python
from lyra_core.subagent.orchestrator import SubagentOrchestrator, SubagentSpec
from lyra_core.subagent.cache_prewarm import (
    SharedPromptDescriptor,
    prewarm_for_specs,
    hit_for_sibling,
)


# 1. Assemble the byte-identical shared prefix every sibling will see.
shared = system_prompt + soul_md + plan_artifact + l2_context

# 2. Describe it.
desc = SharedPromptDescriptor(
    shared_text=shared,
    provider="anthropic",
    scope_ids=("sub-a", "sub-b", "sub-c"),  # optional, for /cache stats
)

# 3. Pre-warm on the parent thread BEFORE the fan-out.
result = prewarm_for_specs(desc, sibling_count=3)
# result.status is CacheStatus.WRITE the first time, HIT thereafter.

# 4. Fan out as usual; workers look up the same anchor.
def worker(workdir, spec):
    status, anchor = hit_for_sibling(desc)
    request_payload = build_request(
        prefix=shared,
        tail=spec_specific_tail(spec),
        cache_directive=anchor.provider_directive if anchor else None,
    )
    return llm_client.send(request_payload)

orchestrator = SubagentOrchestrator(repo_root=Path.cwd())
results = orchestrator.run_parallel(
    [SubagentSpec(id=sid, scope_globs=["src/*"]) for sid in desc.scope_ids],
    worker=worker,
)
```

**What you get:** exactly one cache *write* (the parent's
`prewarm_for_specs` call) and three *hits* (one per worker). On
Anthropic with a 6 000-character shared prefix, that's the
prefix billed once at +25% (write) and then three times at −90%
(reads) — a net ≈ 70% saving on the prefix portion of the
fan-out.

## Recipe 2 — Tournament-TTS attempts

Tournament-TTS already runs `K` attempts of the *same* task
description; that's a textbook cache target.

```python
from lyra_core.subagent.cache_prewarm import (
    SharedPromptDescriptor,
    prewarm_for_specs,
)
from lyra_core.tts.tournament import TournamentTts, TtsBudget

desc = SharedPromptDescriptor(shared_text=task_description, provider="anthropic")
prewarm_for_specs(desc, sibling_count=budget.max_attempts)

tts = TournamentTts(
    generator=my_generator,        # generator splices anchor.provider_directive
    discriminator=my_discriminator,
    budget=TtsBudget(max_attempts=8, max_total_tokens=200_000, max_wall_clock_s=120),
)
result = tts.run(task_description)
```

The generator's `generate(task_description, attempt_index)` call
passes through `task_description` unchanged; the cache hit happens
because every attempt's request prefix is byte-identical.

If you've also wired
[ReasoningBank's MaTTS prefix](../concepts/reasoning-bank.md), each
attempt's *prefix* differs by design — that's a deliberate
diversification trade. Don't pre-warm those; the prefixes won't
match.

## Recipe 3 — Inspect coordinator state

```python
from lyra_core.providers.prompt_cache import default_coordinator

coord = default_coordinator()
snap = coord.snapshot()
print(f"writes={snap.writes} hits={snap.hits} skips={snap.skips}")
print(f"chars cached: {snap.chars_cached:,}")
print(f"active anchors: {coord.active_anchors()}")
```

In a long-running REPL session, periodically printing this surfaces
"are we actually getting cache hits, or is every fan-out paying full
price?" — the most common silent failure mode is one whitespace
difference between the prewarm and the worker calls.

## Recipe 4 — Reset between sessions

```python
from lyra_core.providers.prompt_cache import reset_default_coordinator

# At session boundary, or in a test teardown:
reset_default_coordinator()
```

Tests should always reset between cases; otherwise the
process-global default leaks anchors across runs.

## Recipe 5 — Register a custom adapter

Got a provider not in the built-in set? Implement the adapter
contract and register it once at startup:

```python
from lyra_core.providers.prompt_cache import (
    PromptCacheAdapter,
    register_adapter,
)


class GroqAdapter:
    @property
    def provider_name(self) -> str:
        return "groq"

    def make_directive(self, *, digest, chars, ttl_seconds, is_write):
        # Groq doesn't ship prompt caching today; return None to
        # join the no-op family. If they ship it tomorrow, swap in
        # their actual directive shape here.
        return None


register_adapter(GroqAdapter())
```

The coordinator immediately picks up the adapter on next
`coordinate()` call for `provider="groq"`.

## Recipe 6 — Skip coordination explicitly

For prefixes you *want* to bypass (e.g. tiny one-shot calls, or
cases where you're already routing through a per-request token
budget), don't call the coordinator at all. The default behaviour
is "no cache directive → provider treats every request as
independent." Coordination is opt-in.

## Failure modes & how to debug them

| Symptom | Likely cause | Fix |
|---|---|---|
| Every call returns `CacheStatus.WRITE`, never `HIT` | Shared text differs between calls (whitespace, ordering, dict-iteration order) | Hash-print the prefix before pre-warming and inside the worker; they must match |
| `CacheStatus.SKIP` for a clearly-large prefix | Below the 4 000-char floor for the configured coordinator | Lower `cache_floor_chars` (only if your provider supports it) or accept the skip |
| Anchor expires mid-fan-out | TTL too short for slow workers | Pass `ttl_seconds=900` (15 min) to your coordinator constructor |
| Anthropic returns "cache_control invalid" | The directive was placed on the wrong content block | Splice `cache_control` onto the *last* block of the cacheable prefix |

## When **not** to use this

- **Per-turn user messages.** They change every turn; caching them
  wastes the write overhead.
- **Tool-result heavy turns.** Tool results vary per call; only the
  static prefix above them is cacheable.
- **Cross-provider sibling fan-outs.** Anchors are keyed
  `(provider, digest)`; siblings on different providers each pay
  their own write. Use the coordinator anyway — telemetry will
  surface this honestly — but don't expect cross-provider sharing.
- **One-shot subagents.** If `N == 1`, there's nothing to share;
  skip the prewarm.

## Continue to

→ [How-to: use the ReasoningBank](use-reasoning-bank.md)

→ [Reference: subsystem map](../reference/subsystem-map.md) to find
where the coordinator lives in the source tree.
