---
name: lyra-deep-research-rigor
description: >
  Enforces deep-research rigor and source-integrity standards for the Lyra upgrade
  research-and-planning work. This skill should be used whenever the agent is researching a
  paper, GitHub repo, doc page, or any external source and writing it into findings, a
  synthesis, or a plan under ./lyra-upgrade/ — i.e. any time the task involves reading a link
  and turning it into a research note or design proposal. Triggers include "deep research",
  "deep dive", "research this paper/repo", "add to findings", "write the plan", "synthesize the
  sources", or working in the lyra-upgrade directory. It defines what a complete, deep,
  non-shallow source read must contain (step-by-step mechanism, real benchmark numbers, explicit
  trade-offs, limitation, transferable idea) and the honesty rules (never fabricate a
  description, verify before labeling, log failures). Apply it to every source, not a sample.
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, Bash
version: 1.0.0
license: MIT
compatible-with: claude-code, openclaw, codex
---

# Lyra Deep-Research Rigor

You are doing research-and-planning for Lyra (an MIT, terminal-based, multi-provider, multi-agent
omni-agent harness). This skill defines the *standard of depth and honesty* every source read and
every plan must meet. It does not change scope — it raises quality. Apply it to **every** source,
not a representative sample.

## The depth bar — a source isn't "read" until you can answer all of these

Fetching a landing page or reading an abstract is **not** research. For each source, go deep enough
to redesign the technique for Lyra. A complete read produces, in your own words:

1. **Mechanism, step by step** — how it actually works: the algorithm, data structures, equations,
   control flow. Not "it uses memory" but *how* the memory is written, indexed, retrieved, evicted.
   If a repo: what the core modules are and how the headline feature is actually implemented.
2. **Results with real numbers** — the specific benchmark, dataset, and figures (deltas, latencies,
   token counts). "Improves accuracy" is shallow; "+7.8% over ReAct on Gaia2" is a read.
3. **Explicit trade-offs** — what it gains vs. what it costs (latency, memory, tokens, accuracy,
   complexity, failure modes), and the conditions under which it wins vs. loses. Every technique
   trades something; name it.
4. **Limitation / failure mode** — where it breaks, what it assumes, what it can't do.
5. **Transferable idea for Lyra** — the one concrete thing Lyra should borrow, and where it fits.
6. **Provider behavior** (where relevant) — does it depend on a specific model/API, and how does it
   degrade on a weaker/non-Anthropic provider (e.g. DeepSeek)? What's the fallback?

**Self-check:** if your note is missing the mechanism, the numbers, or the trade-off, the read was
too shallow — go back one level deeper before moving on. If a point could be stated more precisely
or one level deeper, do that.

## How to go deep, by source type

- **arXiv / PDF papers** — read the full paper: method/architecture section, figures and algorithm
  boxes, experimental setup, results tables, ablations, and limitations/future-work. If official
  code exists, open it and confirm how the method is really implemented. Follow one hop into the
  paper's *key* cited works when the technique depends on them.
- **GitHub repos** — clone and read the real source, not just the README. Map entry points, core
  modules, and data structures; read the code implementing the headline feature; skim
  issues/CHANGELOG for design rationale and known limits. Always note the **license** (it matters
  for any clean-room rebuild). For awesome-/paper-lists, enumerate entries and expand one hop on
  Lyra-relevant items; log what you skip and why.
- **Official docs** — read the full page and adjacent linked pages; extract the exact mechanism,
  config/flags, and version/plan constraints.
- **OpenReview** — open each URL directly (`pdf?id=` / `attachment?id=…&name=pdf` forms). Verify the
  fetched content's destination matches the requested id before trusting it — these endpoints
  sometimes serve a cached different paper. If it collides, try the alternate URL form; if it still
  collides, mark unresolved rather than mislabel.
- **Blogs / reports** — read fully; keep the defensible technical claims and the evidence; discard
  marketing language.

## Honesty rules (non-negotiable)

- **Never fabricate.** If you cannot actually read a source, do not invent a description. Mark it
  `unresolved` with the reason.
- **Verify before labeling.** Confirm a fetched document is the one you requested before attributing
  its content to a given link/id.
- **Dead/blocked links never stall the run.** Mark `failed`, log it, find the nearest equivalent
  (mirror, abstract, related work), and continue.
- **Retry on resume.** Sources previously marked `failed`/`unresolved` may have recovered — retry
  them before re-failing.
- **Flag uncertainty.** Approximate or unverified figures (star counts, second-hand claims,
  not-yet-indexed arXiv IDs) are labeled as such, not stated as fact.

## From sources to plans

- **Synthesize before designing.** Don't jump from per-source notes to a feature list. First compare
  techniques head-to-head across sources — frontier, convergences, contradictions, open problems —
  then design.
- **Breakthrough = combination.** A strong proposal fuses techniques from multiple sources into
  something no single source does. Name the sources combined and argue *why* the combination wins,
  with the same trade-off depth as a source read.
- **Specific, not generic.** Every design must be specific to Lyra's architecture. If a sentence
  would be true of any agent, it's too generic — replace it with the Lyra-specific mechanism.
- **Cite everything.** Every proposed technique carries a reference link, ideally to the section or
  figure it came from.

## Integrity of the work itself

Keep a `./lyra-upgrade/PROGRESS.md` checklist current. Don't claim coverage you don't have: the run
is honest only if every source is genuinely `read` (to the depth bar), `failed`, or `unresolved`
with a logged reason. A confidently-wrong label is worse than an admitted gap.
