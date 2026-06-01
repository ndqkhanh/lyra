# PolyKV (Shared Asymmetrically-Compressed KV Cache) — Lyra design memo

> **Status:** v3.5.5 evaluation note. PolyKV (Patel & Joshi, April
> 2026 — [arXiv:2604.24971](https://arxiv.org/abs/2604.24971))
> demonstrates that `N` agents reading the same shared document can
> share a single, lossy-compressed KV cache pool — saving 19.3 GB of
> RAM on Llama-3-8B/15-agents/4K-tokens for only +0.57% perplexity
> degradation. We evaluated whether Lyra, a *harness*, has anything
> to import. This memo records the verdict and what we shipped (a
> production hosted-API coordinator + an integrated subagent prewarm
> helper) versus what we deliberately did not (and, in v3.5.5, what
> we *unshipped* — the `SharedKVPoolProvider` Protocol stub).

## TL;DR

Lyra is a **harness** that talks to **hosted LLM APIs** (Anthropic,
OpenAI, DeepSeek, Gemini, xAI, Mistral, Bedrock, Vertex,
OpenAI-compatible — 16 providers total). PolyKV is a **self-hosted
inference-runtime breakthrough**. The two intersect on two small
surfaces:

1. **Hosted-API equivalent — production.** PolyKV's literal
   mechanism (HuggingFace `DynamicCache` injection with q8_0 keys
   and TurboQuant 3-bit values) requires direct transformer access.
   Hosted providers don't expose KV cache, but they *do* ship
   prompt-cache mechanisms (Anthropic `cache_control`, OpenAI
   automatic prefix cache, DeepSeek context cache, Gemini
   `CachedContent`). We built `PromptCacheCoordinator` —
   provider-aware, sibling-subagent-aware — to give Lyra the same
   "O(1) cost in the shared prefix regardless of `N`" shape that
   PolyKV gives self-hosted runtimes for memory.
   ([`packages/lyra-core/src/lyra_core/providers/prompt_cache.py`](https://github.com/lyra-contributors/lyra/tree/main/projects/lyra/packages/lyra-core/src/lyra_core/providers/prompt_cache.py))

2. **Subagent-orchestrator integration — production.** A thin
   `prewarm_for_specs` helper lets the parent thread pre-warm the
   cache before sibling subagents fan out — guaranteeing exactly
   one cache *write* (paid up front) and `N − 1` *hits* (paid at the
   discount), matching PolyKV's "one prefill, many reads"
   guarantee.
   ([`packages/lyra-core/src/lyra_core/subagent/cache_prewarm.py`](https://github.com/lyra-contributors/lyra/tree/main/projects/lyra/packages/lyra-core/src/lyra_core/subagent/cache_prewarm.py))

Everything else in PolyKV (Walsh-Hadamard transform rotation,
Lloyd-Max scalar codebook, q8_0 per-tensor quantization, in-place
`DynamicCache` mutation) is **structurally inapplicable** to a hosted
LLM harness. We do not host the model; we never touch the KV tensors.

In **v3.5.0** Lyra additionally shipped a `SharedKVPoolProvider`
Protocol (`packages/lyra-core/src/lyra_core/providers/shared_kv.py`)
as a forward-compat shim, on the theory that a future self-hosted
Lyra profile might want to plug a real PolyKV implementation behind
it. In **v3.5.5** that shim was deleted. The reasoning is in
[*What we deliberately did not ship*](#what-we-deliberately-did-not-ship)
and the [CHANGELOG](https://github.com/lyra-contributors/lyra/blob/main/projects/lyra/CHANGELOG.md)
under v3.5.5 "The clean cut": a Protocol with zero implementations
is documentation, not architecture, and self-hosted Lyra is not on
the v3.5 / v3.6 roadmap.

## What PolyKV actually proposes

The paper ships two abstractions:

1. **`SharedKVPool`** — receives a shared document and a model
   reference. Runs a single forward prefill pass to compute the full
   KV state, then compresses asymmetrically:
    - **Keys** at `q8_0` (per-tensor int8, scale = `max(|K|) / 127`),
      preserving softmax stability.
    - **Values** via **TurboQuant MSE**: a normalized Fast
      Walsh-Hadamard Transform (FWHT) rotation followed by 3-bit
      Lloyd-Max scalar quantization with eight optimal centroids on
      `N(0, 1)`: `[−2.152, −1.344, −0.756, −0.245, 0.245, 0.756, 1.344, 2.152]`.

   Compression ratio: `16 / ((8 + 3) / 2) = 16 / 5.5 ≈ 2.91x` —
   stable across all tested models, context lengths, and agent
   counts.

2. **`PooledAgent`** — represents one inference agent. At decode
   time, materialises a fresh `transformers.cache_utils.DynamicCache`
   shell whose layers hold *references* to the shared pool's
   compressed K/V tensors (no per-agent copy of the bulk data), then
   runs that agent's autoregressive generate independently.

The empirical wins (Llama-3-8B, Tests 5–9):

- **15 agents x 4K tokens:** KV cache RAM drops from 19.8 GB →
  0.45 GB (**−97.7%**), perplexity delta only +0.57%.
- **Pool memory is `O(1)` in `N`:** 0.116 GB whether 3 or 10 agents
  read 2K tokens.
- **PPL delta invariant to `N`:** +1.59% at 3, 5, and 10 agents on
  the same 1,837-token context — the pool itself is stable.
- **PPL improves with longer context:** drops from +1.59% at 2K to
  +0.57% at 4K. Inverts to **−0.26%** (compressed *beats* baseline)
  at 1,851 tokens of coherent SmolLM2-1.7B context — confirmed at
  both 3 and 5 agents, eliminating reader count as a confound.
- **BERTScore F1 mean:** 0.928–0.970 across all configurations —
  semantic equivalence preserved.

The paper hypothesises that FWHT rotation noise acts as **implicit
regularization** on coherent mid-document attention sinks (similar in
spirit to dropout but at inference time). Needs ablation to confirm
causality.

## Why most of PolyKV doesn't reach a harness

A coding-agent harness like Lyra:

- **Does not own the KV cache.** Lyra speaks to providers via
  HTTP/JSON; the entire `DynamicCache` lifecycle is invisible.
- **Does not control transformer internals.** Per-tensor
  quantization, FWHT rotation, codebook lookup all happen inside
  the inference engine — Lyra just sends prompt text and receives
  completion text.
- **Does not run the prefill itself.** The "single shared prefill"
  trick PolyKV exploits is owned by the inference runtime; the
  hosted providers Lyra targets run prefill once per request inside
  their datacentre.
- **Does own the prompt assembly.** This is the seam — when `N`
  Lyra subagents are about to send the *same* shared document
  prefix to the *same* provider, Lyra can mark it cacheable and let
  the provider's cache do the equivalent work.

There is no public API today (April 2026) where any hosted provider
exposes KV cache injection. Anthropic, OpenAI, Google, DeepSeek,
xAI, Mistral, Bedrock, and Vertex all ship token-by-token completion
APIs with internal caching. The paper itself notes that
productionising the FWHT rotation requires direct transformer
access; vLLM has prefix caching but no shared compressed pool;
llama.cpp shares prompt prefixes via `mmap` but uses full precision.

## What we shipped

### 1. `PromptCacheCoordinator` (`lyra_core/providers/prompt_cache.py`)

The production module — works with the four providers that ship
prompt caching today:

| Provider | Mechanism | Discount on cache hit |
|---|---|---|
| Anthropic | `cache_control: {"type": "ephemeral"}` block | ~90% read, +25% write |
| OpenAI | Automatic for prefixes ≥ 1024 tokens | ~50% on prefix |
| DeepSeek | Automatic identical-prefix matching | ~90% on hit |
| Gemini | Explicit `CachedContent` resource | ~75% on cached tokens |

Other providers fall back to a `NoopAdapter` that records "skipped
chars" telemetry so an operator can see "your shared prefix on
provider X is leaving money on the table."

Internally:
- One `PromptCacheAnchor` per `(provider, sha256(shared_text))`
  pair, TTL-bounded (default 5 min, matching most providers'
  ephemeral defaults).
- Thread-safe under `concurrent.futures` fan-out (the dominant
  subagent execution shape in Lyra).
- 4 KB character floor — below that, the per-request cache-write
  overhead beats the save.
- Process-global `default_coordinator()` so sibling subagents share
  anchors transparently.

### 2. `prewarm_for_specs` helper (`lyra_core/subagent/cache_prewarm.py`)

A thin opt-in helper the subagent spawn site calls right before
`SubagentOrchestrator.run_parallel` fans out. Takes a
`SharedPromptDescriptor(shared_text, provider, scope_ids)`, asks the
coordinator to write the anchor once on the parent thread, returns a
`PrewarmResult` for HIR + `/cache stats` reporting.

Workers inside the fan-out call `hit_for_sibling(descriptor)` to
retrieve the same anchor and splice the provider directive into
their own request payload. The result: **exactly one cache write,
`N − 1` cache hits**, deterministic across thread races.

This is the morally-equivalent guarantee to PolyKV's
"one prefill, many reads" — but expressed in token-cost rather than
RAM. Where PolyKV makes the per-agent KV memory `O(1)` in `N`,
`prewarm_for_specs` makes the **per-sibling cost of the shared
prefix `O(1)` in `N`**.

### 3. Docs

- This file (`docs/research/polykv-evaluation.md`).
- Concept page: [Prompt-cache coordination](../concepts/prompt-cache-coordination.md).
- How-to recipe: [Use prompt caching across subagents](../howto/use-prompt-cache.md).
- `CHANGELOG.md` v3.5.2 entry summarising the verdict; v3.5.5 entry
  recording the shim removal.
- Bibliography entry: [`docs/research/papers.md`](papers.md) Wave 4.

## What we deliberately did not ship

- **No vendoring of TurboQuant.** Lyra never sees raw K/V tensors.
  The Walsh-Hadamard transform, Lloyd-Max codebook lookup, and
  per-tensor `q8_0` quantization belong inside the inference
  engine. If they ever ship as a Python library, a self-hosted
  adapter under `lyra_core/providers/self_hosted/` will pull them in
  *at the time the self-hosted profile materialises* — not behind a
  speculative Protocol.

- **No `transformers.cache_utils.DynamicCache` import.** Lyra has
  zero `transformers` dependency today and we don't intend to take
  one. Adding it for a forward-compat stub would slow imports for
  every user who never runs a self-hosted profile.

- **No `SharedKVPoolProvider` Protocol shim (removed in v3.5.5).**
  v3.5.0 shipped a `SharedKVPoolProvider` Protocol +
  `_NotWiredProvider` stub that raised `NotImplementedError`,
  intended as a slot for a future self-hosted adapter to plug
  into. Six months later, no self-hosted profile is on the
  roadmap, no hosted provider exposes KV-cache injection, and the
  Protocol had zero callers — making it documentation overhead
  pretending to be architecture. It was deleted in v3.5.5
  ("The clean cut") along with the parallel `BlockStreamingProvider`
  shim from CALM. If a self-hosted profile ever ships, the
  Protocol can be reintroduced *with* a real implementation behind
  it on the same commit; we lose nothing by waiting.

- **No automatic cache marking.** The `PromptCacheCoordinator` is
  opt-in: callers explicitly identify which prefix is shared. Magic
  detection of "this looks like the same plan blob" is a class of
  silently-wrong behaviour we don't want — a cache miss caused by
  one whitespace difference is a miss the operator deserves to see.

- **No global "always cache" hook on the agent loop.** The agent
  loop's first message changes every turn (it carries the latest
  user query); only the *system prompt + plan + L2 context* is
  shareable, and only across explicitly-related subagents. The
  spawn site is the only place that knows that.

- **No multi-provider cross-anchor sharing.** Anthropic and OpenAI
  cache the same text under different formats and TTLs; pretending
  one anchor covers both would lie about telemetry. The coordinator
  keys `(provider, digest)` exactly to keep the accounting honest.

## When to revisit

We will revisit PolyKV in Lyra if and only if **at least one** of:

1. A hosted provider exposes a KV-cache injection API (none does
   today; this would be a strict superset of current prompt
   caching). The coordinator has the seam to slot it in behind the
   existing adapter pattern.
2. A self-hosted Lyra profile ships (vLLM/llama.cpp adapter). At
   that point we (re)introduce the `SharedKVPoolProvider` Protocol
   *together with* a working implementation, on the same commit.
3. An open-source PolyKV reference implementation lands as a
   pip-installable library with a stable API. The same commit can
   add the Protocol + an adapter wrapping that library.

Until then, the production hosted-API coordinator is the
appropriate — and complete — level of investment.

## References

- Patel, I. & Joshi, I. (April 2026). *PolyKV: A Shared
  Asymmetrically-Compressed KV Cache Pool for Multi-Agent LLM
  Inference*. [arXiv:2604.24971](https://arxiv.org/abs/2604.24971).
  DOI: [10.5281/zenodo.19686729](https://doi.org/10.5281/zenodo.19686729).
- Reference Python package:
  [`polykv-llm` on PyPI](https://pypi.org/project/polykv-llm/) (v0.1.0).
- Companion compression-side prior art (cited in PolyKV §2):
    - Liu et al. (2024) — KIVI: asymmetric K/V quantization, per-request.
    - Hooper et al. (2024) — KVQuant: ditto.
    - Zhang et al. (2024) — AsymKV.
    - Google Research (2026) — TurboQuant: the value-side codebook
      PolyKV adopts.
- Companion sharing-side prior art (cited in PolyKV §2):
    - Pan et al. (2025) — KVFlow: full-precision shared prefix cache.
    - Ye et al. (2025) — KVCOMM: ditto.
    - Kim et al. (2026) — LRAgent: shared base cache + per-agent LoRA.
    - Anonymous (2026) — Agent Memory: per-agent isolated Q4 cache,
      reports +2.8–3.0% PPL (PolyKV achieves +0.57% with the shared
      pool).
- Companion Lyra docs:
    - [Concept: Prompt-cache coordination](../concepts/prompt-cache-coordination.md)
    - [How-to: Use prompt caching across subagents](../howto/use-prompt-cache.md)
    - [Reference papers — Wave 4](papers.md#wave-4--multi-agent-cache-sharing--long-horizon-eval)
- Companion CALM evaluation memo (the *negative* counterpart, where
  *no* surface ports cleanly): [`docs/research/calm-evaluation.md`](calm-evaluation.md).
