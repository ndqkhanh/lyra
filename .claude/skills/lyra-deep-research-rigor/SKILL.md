---
name: lyra-deep-research-rigor
description: >
  Enforces deep-research rigor and source-integrity standards for the Lyra upgrade
  research-and-planning work. This skill should be used whenever the agent is researching a
  paper PDF, book, GitHub repo, doc page, or any external source and writing it into findings,
  a synthesis, or a plan under /docs/lyra-upgrade/ — i.e. any time the task involves reading a
  source and turning it into a research note or design proposal. Triggers include "deep
  research", "deep dive", "research this paper/repo/book", "add to findings", "write the plan",
  "synthesize the sources", reading from the local paper library
  (/Users/khanhnguyen/Downloads/MyCV/research_papers) or books library
  (/Users/khanhnguyen/Downloads/MyCV/AI-Agent-Books), or working in the /docs/lyra-upgrade
  directory. It defines what a complete, deep, non-shallow source read must contain
  (step-by-step mechanism, real benchmark numbers, explicit trade-offs, limitation,
  transferable idea, reverse prompt for repos) and the honesty rules (never fabricate a
  description, verify before labeling, log failures). Apply it to every source, not a sample.
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, Bash
version: 2.0.0
license: MIT
compatible-with: claude-code, openclaw, codex
---

# Lyra Deep-Research Rigor

You are doing research-and-planning for Lyra (an MIT, terminal-based, multi-provider, multi-agent
omni-agent harness). This skill defines the _standard of depth and honesty_ every source read and
every plan must meet. It does not change scope — it raises quality. Apply it to **every** source,
not a representative sample.

The governing document is the master prompt at
`/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/docs/lyra-upgrade-master-prompt.md`
— read it END TO END (§0–§9; the whole document is binding) before any research pass. Where this
skill and the master prompt differ in detail, the master prompt wins.

## Where sources live (read locally first)

- **Papers** = the PDF files in `/Users/khanhnguyen/Downloads/MyCV/research_papers`. That directory
  IS the paper corpus — paper links were intentionally removed from the master prompt. Identify
  each paper from the PDF itself (title/authors/ID on the first page or metadata); cite by title +
  arXiv/OpenReview ID, **never** by local file path. Web access for papers is fallback-only
  (unreadable/corrupted file → recover by ID once, log it).
- **Books** = `/Users/khanhnguyen/Downloads/MyCV/AI-Agent-Books` (master prompt §3.30) — the
  best-practice layer. Books are not web-recoverable: an unreadable book is logged `failed` and
  flagged for manual re-download.
- **Repos / docs / blogs** = web, as linked in the master prompt §3. Clone repos to
  `/docs/lyra-upgrade/repos/<owner>__<name>/` (shallow is fine).

## The depth bar — a source isn't "read" until you can answer all of these

Reading an abstract or a README is **not** research. For each source, go deep enough to redesign
the technique for Lyra. A complete read produces, in your own words:

1. **Mechanism, step by step** — how it actually works: the algorithm, data structures, equations,
   control flow. Not "it uses memory" but _how_ the memory is written, indexed, retrieved, evicted.
   If a repo: what the core modules are and how the headline feature is actually implemented.
2. **Results with real numbers** — the specific benchmark, dataset, and figures (deltas, latencies,
   token counts). "Improves accuracy" is shallow; "+7.8% over ReAct on Gaia2" is a read.
3. **Explicit trade-offs** — what it gains vs. what it costs (latency, memory, tokens, accuracy,
   complexity, failure modes), and the conditions under which it wins vs. loses. Every technique
   trades something; name it.
4. **Limitation / failure mode** — where it breaks, what it assumes, what it can't do.
5. **Transferable idea for Lyra** — the one concrete thing Lyra should borrow, and which §4
   workstream it feeds (the routing the orchestrator writes back into the master prompt).
6. **Provider behavior** (where relevant) — does it depend on a specific model/API, and how does it
   degrade on a weaker/non-Anthropic provider (e.g. DeepSeek)? What's the fallback?
7. **Reverse prompt** (repos only — master prompt §3.31) — 1–3 paragraphs written as a user
   instructing an agent to build this product: capabilities, UX flows, integrations, deployment
   shape, in plain language. Faithful to what the CODE actually does, not the README. This becomes
   the product-spec baseline the implementation run builds from.

**Self-check:** if your note is missing the mechanism, the numbers, the trade-off — or, for a repo,
the reverse prompt — the read was too shallow; go back one level deeper before moving on.

## How to go deep, by source type

- **Papers (local PDFs)** — read the full PDF: method/architecture section, figures and algorithm
  boxes, experimental setup, results tables, ablations, and limitations/future-work. If official
  code exists, open it and confirm how the method is really implemented. Follow one hop into the
  paper's _key_ cited works when the technique depends on them (check the local library first; the
  top-venue quality bar in master prompt §3 governs any corpus expansion).
- **Books (local, §3.30)** — deep but structured, not page-by-page like a paper: TOC + preface to
  map the territory, then chapter-by-chapter notes for every Lyra-relevant chapter (out-of-scope
  chapters skim-logged with a one-line reason). Per book, produce the best-practices note: core
  thesis + mental models; every concrete practice/anti-pattern routed (→ §4.x); agreements AND
  conflicts with the paper corpus (conflicts are signal — surface them to the §1.5 panel debate);
  "what Lyra should do differently". Cite as Title (author, year, chapter).
- **GitHub repos** — clone and read the real source, not just the README. Map entry points, core
  modules, and data structures; read the code implementing the headline feature; skim
  issues/CHANGELOG for design rationale and known limits. Always record the **license** verbatim
  (it gates clean-room reuse into Lyra's MIT codebase). Write the reverse prompt (depth-bar #7);
  `https://www.gitreverse.com/<owner>/<repo>` may be fetched as a pre-dive hint but is never
  evidence — verify everything against the code. For awesome-/paper-lists, enumerate entries and
  expand one hop on Lyra-relevant items; log what you skip and why.
- **Official docs** — read the full page and adjacent linked pages; extract the exact mechanism,
  config/flags, and version/plan constraints.
- **OpenReview (web fallback only)** — papers should come from the local library; if you must fetch
  the web (missing/corrupt file, review-thread context), verify the fetched content's destination
  matches the requested id before trusting it — these endpoints sometimes serve a cached different
  paper. If it collides, try the alternate URL form; if it still collides, mark unresolved rather
  than mislabel.
- **Blogs / reports** — read fully; keep the defensible technical claims and the evidence; discard
  marketing language.

## Honesty rules (non-negotiable)

- **Never fabricate.** If you cannot actually read a source, do not invent a description. Mark it
  `unresolved` with the reason.
- **Verify before labeling.** Confirm a fetched/opened document is the one you intend before
  attributing its content to a given link/id/filename.
- **Dead/blocked sources never stall the run.** Mark `failed`, log it, find the nearest equivalent
  (mirror, abstract, related work — for web sources; manual re-download flag for books), continue.
- **Retry on resume.** Sources previously marked `failed`/`unresolved` may have recovered — retry
  them once before re-failing.
- **Flag uncertainty.** Approximate or unverified figures (star counts, second-hand claims,
  not-yet-indexed arXiv IDs) are labeled as such, not stated as fact.
- **Single-writer write-back.** Only the orchestrator edits the master prompt (the Phase-1
  write-back of resolved titles + routings), only within §3, append/replace-minimal so each batch's
  git diff is small and reviewable. Subagents never edit the master prompt.

## From sources to plans

- **Synthesize before designing.** Don't jump from per-source notes to a feature list. First compare
  techniques head-to-head across sources — frontier, convergences, contradictions, open problems —
  then design.
- **Breakthrough = combination.** A strong proposal fuses techniques from multiple sources into
  something no single source does. Name the sources combined and argue _why_ the combination wins,
  with the same trade-off depth as a source read.
- **Breakthroughs everywhere.** EVERY §4 workstream plan — memory, context, skills, router, tools,
  reliability, safety, RAG, desktop, all of them, not only the four primary directions — must
  contain at least one breakthrough-tier proposal argued against that area's current SOTA, with the
  Skeptic's strongest objection recorded and answered (master prompt §0/§1.6). An incremental-only
  plan is incomplete. The §5 investigations get plans too (plans/5.x-\*.md).
- **Book practices are binding.** The cross-book playbook (synthesis/best-practices.md) feeds every
  plan; plans cite book practices alongside papers with the same citation discipline.
- **Specific, not generic.** Every design must be specific to Lyra's architecture. If a sentence
  would be true of any agent, it's too generic — replace it with the Lyra-specific mechanism.
- **Cite everything.** Every proposed technique carries a reference (paper title + ID, repo link,
  or book chapter), ideally to the section or figure it came from.

## Integrity of the work itself

Keep `/docs/lyra-upgrade/PROGRESS.md` (the coverage manifest: every paper, book, repo, doc, blog —
status pending|read|failed|unresolved) and `/docs/lyra-upgrade/RESEARCH_LOG.md` (append-only
failures, collisions, retries, phase checkpoints) current. Don't claim coverage you don't have: the
run is honest only if every source is genuinely `read` (to the depth bar), `failed`, or
`unresolved` with a logged reason. Expect a fresh-context audit at the end to verify coverage,
rigor sampling, citation tracing, and write-back completeness — a confidently-wrong label is worse
than an admitted gap.
