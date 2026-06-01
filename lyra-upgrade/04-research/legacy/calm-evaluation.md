# CALM (Continuous Autoregressive Language Models) — Lyra design memo

> **Status:** v3.5.5 postmortem. CALM (Tencent + Tsinghua, 2026 —
> [arXiv:2604.24026](https://arxiv.org/abs/2604.24026)) proposes that
> LLMs predict **continuous vectors that decode to K tokens** rather
> than next-token distributions. We evaluated whether Lyra, a
> *harness*, has anything to import. **The answer was no.** This page
> records the analysis so a future contributor doesn't repeat the
> exercise.

## TL;DR

Lyra is a **harness**, not a model. CALM is a **modelling-side**
breakthrough. The two intersect on three small surfaces; in **none of
them** does Lyra get value today:

1. **Token-stream UI compatibility.** A `BlockStreamingProvider`
   adapter would only matter if a hosted provider ever emits K-token
   blocks. **No hosted provider does.** Anthropic, OpenAI, Google,
   xAI, Mistral, DeepSeek, Cerebras, Groq all ship token-by-token
   streaming with discrete vocabularies. Tencent + Tsinghua haven't
   released a hosted CALM endpoint either.
2. **Eval-metric extensibility.** A `BrierLM` scorer would only fire
   if a provider returns full per-token probability distributions.
   **No production provider does.** OpenAI exposes top-K `logprobs`
   only; Anthropic, DeepSeek, and Gemini expose nothing.
3. **Documentation hygiene.** This memo plus a CHANGELOG note —
   the only piece that survives.

In v3.5.0 Lyra shipped a forward-compat `BlockStreamingProvider`
Protocol (`packages/lyra-core/src/lyra_core/providers/streaming.py`)
and an experimental `BrierLM` scorer
(`packages/lyra-evals/src/lyra_evals/scorers/brierlm.py`) so that
*if* either upstream emerged, the seam would already be there. In
**v3.5.5** both were deleted: a Protocol nobody implements is
documentation overhead, not architecture. See
[CHANGELOG](https://github.com/lyra-contributors/lyra/blob/main/projects/lyra/CHANGELOG.md)
v3.5.5 "The clean cut".

## What CALM actually proposes

The paper introduces three coupled changes:

1. **Token-chunk autoencoder.** Each contiguous group of `K` tokens
   (the paper uses K = 4) is replaced by one continuous vector via a
   small autoencoder (~1 % of total parameters). The decoder is
   fixed for the rest of training.
2. **Continuous next-vector prediction.** The transformer predicts
   the next vector in continuous space using an energy-based head —
   no softmax, no vocabulary. Sampling is via Langevin dynamics.
3. **BrierLM** — replaces perplexity. Defined as the expected Brier
   score of the model's predictive distribution over a held-out
   sequence. The paper argues it's well-defined for continuous
   outputs where perplexity is not.

Headline systems wins (per paper):

- **4× fewer prediction steps** — each step emits ~K tokens.
- **44 % less training compute** at the same downstream quality.
- **No discrete vocabulary** — handles arbitrary languages /
  modalities without retokenisation.

## Why nothing in CALM reaches a harness

A coding-agent harness like Lyra:

- **Does not own training compute.** The "44 % less training
  compute" win goes to whoever trains the model.
- **Does not own the loss function.** Lyra speaks to providers via
  HTTP / JSON; the energy-based vs softmax distinction is invisible.
- **Does not own the tokenizer.** No-vocab means nothing to a
  runtime that just relays text.
- **Does own the streaming UI** and the **eval harness** — these
  are the two seams where CALM-style providers, *if they ever exist
  as a hosted API*, would touch us. They don't, so they don't.

There is no serious public discussion (as of v3.5.5) of any
commercial provider offering a CALM-class API or returning per-token
probability distributions. The paper itself notes that
productionising the energy sampler is an open challenge.

## When to revisit

Reopen this analysis if **any** of:

1. A hosted provider ({Anthropic, OpenAI, Google, xAI, Mistral,
   Cohere, OpenRouter, DeepSeek, Cerebras, Groq, Bedrock, Vertex})
   ships a public API that returns K-token blocks **and** per-token
   probabilities. Both, not one.
2. An open-weight CALM-class checkpoint becomes runnable via
   Ollama / vLLM / llama-server **and** Lyra grows a self-hosted
   profile worth wiring it into.
3. The paper's authors release a reference inference server we can
   target with the existing `LYRA_*_BASE_URL` overrides.

Until then, revisiting is wasted time. The PromptCacheCoordinator
absorption of [PolyKV](polykv-evaluation.md) shows the right shape
for a harness-side absorption when one is genuinely available;
CALM is the counter-example.

## What we shipped (and unshipped)

| Surface | v3.5.0 | v3.5.5 |
|---|---|---|
| `BlockStreamingProvider` Protocol (`lyra_core/providers/streaming.py`) | Forward-compat shim with `BlockToTokenAdapter` + `split_block_on_whitespace` helper | **Deleted** — no upstream emerged |
| `BrierLM` scorer (`lyra_evals/scorers/brierlm.py`) | Experimental — auto-skipped on every real run | **Deleted** — no provider activates it |
| `lyra_evals.scorers` package | Existed for the BrierLM re-export | **Deleted** — no other scorers used it |
| This memo (`docs/research/calm-evaluation.md`) | Live design note | **Postmortem** (this page) |

## References

- Tencent + Tsinghua (2026). *Continuous Autoregressive Language
  Models*. [arXiv:2604.24026](https://arxiv.org/abs/2604.24026).
- Companion docs: `docs/feature-parity.md` §"Wave-2 performance edges".
- Sibling postmortem-shaped memo: [PolyKV evaluation](polykv-evaluation.md)
  — the *positive* counterpart, where the architectural insight
  *did* port (as `PromptCacheCoordinator`) even though the literal
  mechanism didn't.
