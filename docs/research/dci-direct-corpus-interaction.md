# DCI — Direct Corpus Interaction (paper + repo deep-dive, with Lyra steal-list)

> **One-line summary.** A May-2026 paper from a TIGER-Lab–led
> 80-author consortium argues that **the best retriever for agentic
> search is no retriever**: replace the embedding model + vector index +
> top-k API with `grep` / `find` / `sed` / `bash` and let the LLM
> investigate the raw corpus directly. The reference implementation
> ([DCI-Agent-Lite](https://github.com/DCI-Agent/DCI-Agent-Lite))
> beats strong sparse/dense/reranker baselines on **13 benchmarks**:
> **+11.0 %** BrowseComp-Plus, **+30.7 %** multi-hop QA, **+21.5 %** IR
> ranking. This document is Lyra's reading note + a concrete plan for
> what Lyra v3.13 should steal.
>
> Sources:
> - Paper: [arXiv 2605.05242 — *Beyond Semantic Similarity: Rethinking
>   Retrieval for Agentic Search via Direct Corpus Interaction*](https://arxiv.org/abs/2605.05242)
> - HF paper page: [huggingface.co/papers/2605.05242](https://huggingface.co/papers/2605.05242)
> - Reference impl: [github.com/DCI-Agent/DCI-Agent-Lite](https://github.com/DCI-Agent/DCI-Agent-Lite)
> - Demo / eval logs: `huggingface.co/spaces/DCI-Agent/demo`,
>   `huggingface.co/datasets/DCI-Agent/eval-logs`

---

## 1. The thesis in one paragraph

Today's retrieval-augmented generation pipelines compress the corpus
through a single bottleneck: an embedding model maps every chunk to a
fixed vector, an index returns the top-k most similar to the query,
and the agent only ever sees those k chunks. That bottleneck **destroys
evidence before the model gets to reason about it**. DCI removes the
bottleneck entirely. The agent — which is already capable of writing
shell commands for a coding task — is handed the same raw corpus the
indexer would have read, plus `rg`, `find`, `sed`, `cat`, and pipes,
and asked to investigate. No offline indexing step, no vector store,
no rerankers; the "interface" between the agent and the corpus is just
a sandboxed shell with a budget.

The surprising empirical finding is that this beats SOTA semantic
pipelines on three independent task families — and the gap *grows* on
multi-hop questions where evidence is scattered, where dense retrievers
fail to surface obscure intermediate clues, and where exact-string
matching (which embeddings deliberately blur) actually matters.

The deeper claim, in the authors' phrasing: **"retrieval quality
depends not only on reasoning ability but also on the resolution of
the interface through which the model interacts with the corpus."**
Embeddings are a low-resolution interface. A shell is a high-resolution
interface. As the model gets stronger, the interface bottleneck — not
the model — becomes the bound.

---

## 2. What the paper actually shows

### 2.1 Benchmarks and numbers

| Task family | Datasets used | Average DCI gain over SOTA |
|---|---|---|
| Agentic search | BrowseComp-Plus (830 tasks, 100 K docs, 5 179 avg words/doc) | **+11.0 %** |
| Multi-hop QA | HotpotQA, MuSiQue, 2WikiMultiHopQA, NQ, TriviaQA, Bamboogle (300 questions total over 21 M-doc Wikipedia-18 corpus) | **+30.7 %** |
| IR ranking | BRIGHT (Biology / Earth Science / Economics / Robotics, 50 K–121 K docs), BEIR | **+21.5 %** |

The headline number cited in the README: **62.9 %** accuracy on
BrowseComp-Plus with `gpt-5.4-nano` plus `--thinking high` and context
management level 3.

### 2.2 Baselines beaten

DCI is benchmarked against, and beats:

- **Sparse retrievers** — BM25 (the only baseline that DCI's primary
  tool, `rg`, structurally resembles, but DCI wins by composing
  searches reactively).
- **Dense retrievers** — modern embedding models with vector indices.
- **Reranker pipelines** — two-stage retrieve-then-rerank baselines.
- **Agentic-search SOTA** — Search-o1 and comparable systems that
  themselves use semantic retrieval under the hood.

### 2.3 Ablations the paper runs

Sections 4.2–4.6 ask the obvious questions:

- **RQ2 — trajectory patterns.** What does the agent's tool call
  sequence actually look like? (Answer: it iterates — broad pattern →
  narrow pattern → file read → cross-check — like a programmer
  greppping a codebase.)
- **RQ3 — evidence utilization.** Does the agent recover evidence that
  semantic retrievers would have discarded? (Yes; this is where the
  multi-hop +30 % comes from.)
- **RQ4 — corpus scale.** Does the approach hold up at 21 M docs? (Yes,
  with the help of context management.)
- **RQ5 — context management.** How aggressive does the truncation /
  compaction / summarization need to be to keep the agent productive
  past hundreds of tool calls? (See §3.2 below.)
- **RQ6 — tool usage patterns.** Which tools dominate? (`rg` / `grep`
  is the workhorse; `sed` and pipes appear when the agent is
  cross-cutting fields; `find` opens the search; `cat` / `head` /
  `wc` close the loop.)

### 2.4 The philosophical contribution

The paper's framing — "the interface between AI and information is as
important as the AI itself" — is the same framing that underlies the
recent push in 2026 toward **operator-style** agents (Claude Computer
Use, OpenAI Operator, Anthropic Computer Use ALPHA): give the model the
same surface a human investigator would use, then trust the model to
investigate.

DCI specializes that thesis to *search*, but the lesson generalises:
**stop pre-digesting the world for the agent**.

---

## 3. The reference implementation (DCI-Agent-Lite)

### 3.1 Stack & layout

```
DCI-Agent-Lite/
├── src/dci/             # ~87 % of code — Python
├── prompts/
│   └── system_prompt.txt   # short, terse: "use bash for ls/rg/find"
├── scripts/
│   ├── bcplus_eval/     # BrowseComp-Plus harness
│   ├── bright/          # BRIGHT harness
│   └── qa/              # NQ / TriviaQA / HotpotQA / MuSiQue / 2Wiki / Bamboogle
├── assets/              # banner, paper figures
├── pyproject.toml       # uv-managed
├── uv.lock
├── setup.sh             # clones pi-mono at codex/context-management-ablation
└── .env.template        # OPENAI_API_KEY, ANTHROPIC_API_KEY
```

Outputs land at `outputs/runs/<timestamp>/{final.txt,
conversation_full.json, question.txt}` — i.e. the eval harness is
**append-only and ledger-shaped**, which matches how Lyra already
captures session-search trajectories.

### 3.2 Agent architecture

The agent loop is built on the **Pi framework** (`jdf-prog/pi-mono` at
the `codex/context-management-ablation` branch). Pi is a minimal
TypeScript/Node tool-use harness that exposes:

- A **`bash` tool** with the host's `rg`, `find`, `sed`, `cat`, `wc`,
  `head`, `tail`, `awk`, `sort`, `uniq`, `xargs`, and shell pipes.
- A **`read` tool** for explicit file reads.
- A **context-management pipeline** with four levels (described below).
- An **optional thinking budget** (`--thinking high|low`) that toggles
  extended reasoning per turn.
- A **turn budget** (max 300) before the run is forcibly stopped.

The Python wrapper `dci-agent-lite` is essentially:

```text
parse flags  →  build system prompt  →  spawn pi  →
  for turn in 1..300:
    LLM thinks (optionally with --thinking high) and emits a tool call
    pi executes the bash / read
    output is piped back as the next user message
    context_manager.apply(level)
  →  write final.txt, conversation_full.json, question.txt
```

There is **no retriever, no embedding model, no vector index**.

### 3.3 The four context-management levels

Past ~30 tool calls a raw transcript blows the model's context. DCI-Agent-Lite
ships a four-step ladder:

| Level | Strategy |
|---|---|
| `level0` | No management. Whole transcript stays. |
| `level1` | Light truncation — drop the oldest tool outputs first. |
| `level2` | Stronger truncation — drop more aggressively, keep recent N. |
| `level3` | Truncation + compaction — collapse a sliding window of older turns into one compressed message. |
| `level4` | Truncation + compaction + summarization — also produce a running "what I've learned so far" digest. |

The published 62.9 % BrowseComp-Plus number uses **level 3**. Level 4
helps on the longest trajectories; level 0–1 only work on small
corpora.

### 3.4 Supported LLMs

- OpenAI: `gpt-5.4-nano`, `gpt-5.2`
- Anthropic: `claude-sonnet-4.6`
- vLLM-served local models (Qwen / GLM variants benchmarked)

The fact that a *nano-class* model carries the headline result is the
detail to underline: DCI is not "throw a bigger model at retrieval",
it is "give a small model a better interface".

### 3.5 The system prompt

The actual prompt is short. Stripped to its load-bearing rules
(paraphrased — the file is `prompts/system_prompt.txt` and tells the
agent *what tools it has* rather than *how to think*):

- Available tools are `read` (file content) and `bash` (`ls`, `rg`,
  `find`, etc.).
- Use bash for file operations.
- Be brief, show file paths.
- Documentation files exist and should be consulted when the user
  asks about Pi itself, otherwise stay out of them.

There is **no chain-of-thought scaffolding, no ReAct template, no
"think step by step"** in the system prompt — the `--thinking high`
flag delegates that to the model's own extended-thinking mechanism.

This is the part that should be most counter-intuitive to anyone who
has spent the last two years prompt-engineering retrieval agents: the
prompt is *less* structured than a typical RAG prompt, not more. The
authors' bet is that the model already knows how to grep a codebase,
because it has done so in training a million times.

### 3.6 What `rg` looks like in the trajectory

A typical run on BrowseComp-Plus produces a tool-call shape like:

1. `rg -l -i "<entity from question>" .` — locate candidate files.
2. `head -200 <file>` — sample top of each candidate.
3. `rg -n -C 3 "<sharper pattern>" <file>` — extract surrounding
   context.
4. `find . -type f -name "*<topic>*"` — broaden when the first pattern
   has zero hits.
5. `rg -n "<entity1>.*<entity2>"` — multi-entity conjunction (the
   thing dense retrievers cannot do).
6. `sed -n '40,80p' <file>` — pin exact lines for the final answer.
7. `cat <file>` — final verification on a small file.

This shape is **functionally identical to how a Claude Code or
Lyra `agent` mode would explore a codebase** — which is precisely
the point.

---

## 4. Where this lands in the wider 2026 picture

DCI is not isolated. Three concurrent strands are converging on the
same idea:

- **"Grep is All You Need: Zero-Preprocessing Knowledge Retrieval for
  LLM Agents"** — earlier 2026 paper, same intuition, smaller scale.
- **Interact-RAG (arXiv 2510.27566)** — argues for *reasoning + interacting*
  with the corpus past black-box retrieval, a half-step before DCI.
- **Anthropic / OpenAI computer-use agents** — generalises the
  "operator interface" thesis to the entire desktop, of which a shell
  is the most precise subset.

The trend that connects them: **as models get stronger, the
information-loss step in the pipeline migrates from the model to the
interface around the model**. Indices are the most lossy interface in
modern RAG, so they go first.

---

## 5. What Lyra already has that overlaps

| DCI primitive | Lyra surface today | Status |
|---|---|---|
| Bash + `rg` over corpus | `lyra_core/tools/codesearch.py` — auto-detects `rg`, falls back to a pure-Python regex walker; returns structured `{path,line,column,text}` hits | ✅ shipped |
| Generic shell | `lyra_core/tools/execute_code.py` (sandbox-gated bash); `lyra_core/permissions/` grammar gates exact commands | ✅ shipped |
| File read tool | `read_file` in `lyra_core/tools/builtin.py` | ✅ shipped |
| Lexical retrieval over skills | `lyra_core/skills/bm25_tier.py` — the "tier 2" in Argus' 5-stage skill cascade | ✅ shipped (skills only, not arbitrary corpora) |
| Session memory / trajectory | `lyra_core/sessions/store.py`, `memory/reasoning_bank.py`, `memory/procedural.py` | ✅ shipped |
| Context compaction | `lyra_core/context/{compactor,compact_router,compact_validate,ngc,grid}.py` — the 5-layer + NGC stack | ✅ shipped, **richer than DCI level0-4** |
| Turn budget / loop | `AgentLoop` in `lyra_core/agent/loop.py`; cron-as-loop in `cron/daemon.py`; v3.12 plan adds `/loop`, ralph, Stop hooks | 🟡 partial (loop exists; budget enforcement weaker) |
| Extended thinking toggle | provider plugins expose `thinking` on Anthropic / OpenAI o-series | ✅ shipped |

**The honest read:** Lyra already has the *atoms* — bash, codesearch,
read, context compaction, persistence. What it is missing is a
**packaged investigative mode** that composes them, plus eval harnesses
that prove the composition matches the paper's gains.

---

## 6. What Lyra should steal — the v3.13 plan

The integration target is a new optional **`investigate` mode** for
the 4-mode router (today: `agent · plan · debug · ask` → tomorrow:
`agent · plan · debug · ask · investigate`), plus three supporting
primitives. Everything below is shaped to honour Lyra's contracts:
each bundle ships as one `lyra_core/<module>/` directory, offline-
testable, opt-in, and with a public-paper citation chain.

### 6.1 Bundle DCI-1 — `investigate` mode + system prompt

**New surface.**
- `lyra investigate <question>` CLI subcommand.
- `/investigate` slash command in the REPL.
- `4-mode router` upgraded to 5-mode; selection routes to a new
  system prompt at `lyra_core/prompts/investigate.md`.

**System prompt principles** (cite DCI §3.5):
- Two-paragraph prompt, not a 600-line scaffold.
- Tools advertised: `codesearch`, `read_file`, `execute_code` (with
  bash subset), `web_search` (gated), `pdf_extract` (already shipped).
- *No* ReAct template. *No* "think step by step". Defer thinking to
  the model's native extended-thinking mechanism via a provider hint.
- Output protocol: structured final answer with file/line citations
  (Lyra already enforces this in `codesearch.py`'s return shape; just
  carry it through).

**Why first.** Zero new code — it's a prompt and a wire-up. Gives
Lyra immediate parity with the DCI-Agent-Lite agent loop on
arbitrary user-provided corpora.

### 6.2 Bundle DCI-2 — Corpus mount + sandboxed shell budget

**Problem.** Today `codesearch` searches the current working tree.
DCI-Agent-Lite takes `--cwd <corpus_root>` and confines bash to that
root. We need the same: a way to point Lyra at an *external* corpus
and bound the shell.

**Design.**
- New `lyra_core/investigate/corpus.py` — `CorpusMount` dataclass
  (frozen) with `root: Path`, `read_only: bool = True`,
  `max_file_bytes: int = 10_000_000`, `excluded_globs: tuple[str, ...]`.
- New `lyra_core/investigate/budget.py` — `InvestigationBudget`
  with `max_turns: int = 300`, `max_bash_calls: int = 200`,
  `max_bytes_read: int = 100_000_000`, `wall_clock_s: float = 1800.0`.
  Mirrors DCI-Agent-Lite's 300-turn cap but adds the bytes/wall-clock
  guards Lyra's tool-permissions grammar can enforce today.
- Permissions wire-up: `lyra_core/permissions/` grammar gets two
  named profiles, `investigate-readonly` (no writes, no network,
  bash limited to `rg find sed cat head tail wc awk sort uniq xargs`)
  and `investigate-rw` (same plus `mkdir` and writes inside the
  mount). The grammar already supports this — we're just adding two
  preset bundles.

**Why second.** Without this you can't run DCI on someone else's
laptop without giving the agent root over the filesystem. The grammar
already exists; this is composition.

### 6.3 Bundle DCI-3 — Context-management level ladder (level0–4 parity)

**Problem.** Lyra's NGC compactor and grid compactor are
*sophisticated* — they do hierarchical compaction with relevance-based
eviction. But there's no single **level dial** that ops can turn from
0 → 4 the way DCI-Agent-Lite exposes. We have the engine; we don't
have the simple thermostat.

**Design.**
- New `lyra_core/context/levels.py` — `ContextLevel(Enum)` with
  `OFF = 0`, `TRUNCATE_LIGHT = 1`, `TRUNCATE_HARD = 2`,
  `TRUNCATE_PLUS_COMPACT = 3`, `FULL = 4`.
- Maps each level to an existing pipeline:
  - level0 → no-op
  - level1 → drop-oldest-tool-output (existing `compactor.py`)
  - level2 → drop-oldest plus `relevance.py` filter on tool outputs
  - level3 → level2 + NGC running summary (existing `ngc.py`)
  - level4 → level3 + per-window summarizer pass
- CLI flag: `lyra investigate --context-level 3 ...`.
- Telemetry: each level emits the bytes-saved figure so we can
  reproduce DCI's RQ5 ablation on Lyra's own benchmarks.

**Why third.** This is the cheapest big-impact knob in the paper —
their headline number uses level 3, and the level 4 helped tail
trajectories. Lyra has all the building blocks; we are wrapping a
dial around them.

### 6.4 Bundle DCI-4 — Eval harness on three datasets

**Problem.** Lyra ships `lyra-evals` but does not yet have a
zero-retrieval baseline on the DCI benchmarks. Without numbers we
can't claim parity.

**Design.** Add to `packages/lyra-evals/`:
- `adapters/browsecomp_plus.py` — 830-task harness, 100 K-doc corpus.
- `adapters/multihop_qa.py` — HotpotQA / MuSiQue / 2WikiMultiHopQA
  subset (start with 50 each — cheap signal first).
- `adapters/bright.py` — BRIGHT-Biology + BRIGHT-Robotics (the two
  smallest splits; the others can wait).
- Each adapter takes `--mode investigate --context-level 3 --thinking
  high` and emits a `pass@1` accuracy plus a trajectory ledger that
  mirrors DCI's `conversation_full.json`.
- Comparison-mode flag: `--against bm25` runs Lyra's existing
  `bm25_tier.py` against the same questions so we can plot the
  *Lyra-specific* gain instead of just citing the paper.

**Why fourth.** This is the only way to know whether bundles DCI-1
through DCI-3 actually work. Lyra's contract is "every borrowed idea
has a visible citation chain" — the ledger from these adapters is
the citation.

### 6.5 Bundle DCI-5 — Argus skill: `corpus-investigator.md`

**Problem.** Argus' 5-tier router cascade now has discovery, dedup,
and rate limiting (from the just-shipped Argus iteration), but no
skill teaches the agent the *trajectory shape* (broad-grep →
narrow-grep → read → cross-cut) that DCI-Agent-Lite relies on.

**Design.**
- Add `skills/corpus-investigator/SKILL.md` to Lyra's bundled
  skill library. Trust tier: `T_TRUSTED` (we authored it).
- Body teaches the seven-step trajectory from §3.6, with one
  worked example on a Wikipedia subset.
- Registered with Argus so any user query that scores high on
  intent embeddings like "search through this corpus / find
  evidence / multi-hop" auto-loads the skill into the system
  prompt before the agent starts.

**Why fifth.** Argus is Lyra's "what skill should I use right now"
brain. Without an entry in Argus, the `investigate` mode is just a
flag the user has to remember. With an entry, Lyra auto-promotes
into DCI mode when the question shape calls for it.

### 6.6 Bundle DCI-6 — Composing DCI with the v3.12 autonomy loop

**The compound bet.** v3.12 adds Ralph-style fresh-context loops,
`Stop` / `SubagentStop` hooks, `/loop`, and an iteration cap. DCI is
fundamentally **a single long trajectory** today. Composed with v3.12:

- A long investigation becomes a `lyra ralph <investigation.json>`
  run — fresh context each iteration, `progress.txt` carries
  hypotheses from the previous one, `<promise>COMPLETE</promise>`
  parses out when the agent thinks it's found the answer.
- The Stop hook fires when the model emits its final answer; a
  *verifier* sub-agent (already shipped) re-reads the cited file
  ranges and answers `FULFILLED` / `VIOLATED` / `EXPIRED`.
- On `VIOLATED`, the loop re-feeds the verifier's complaint as the
  next user message — the same `Decision.deny` semantics the v3.12
  plan installs.

This is the difference between a 300-turn investigation that runs
once and a 24/7 investigation that runs all night against a freshly
cloned corpus, like Karpathy's autoresearch sketch but for the
search axis. **No new code in DCI-6 — it is purely the composition
contract.**

### 6.7 What we are explicitly NOT stealing

- The Pi framework. Lyra's `AgentLoop` is already a more mature
  version of the same abstraction; porting Pi would be reverse
  engineering effort with no payoff. We are stealing the *prompt
  shape, the budget shape, and the context-level ladder*, not the
  runtime.
- The `--thinking high|low` toggle as a Lyra flag. Lyra already
  supports per-provider thinking budgets through the provider-plugin
  surface (v3.10); we just route the existing knob.
- DCI-Agent-Lite's `setup.sh` cloning a specific pi-mono commit.
  Lyra is install-and-go; we are not requiring a side-clone.

---

## 7. Sequencing — order of attack

| Bundle | LOC est. | Tests | Depends on | Ship gate |
|---|---|---|---|---|
| DCI-1 (`investigate` mode + prompt) | ~250 | prompt-snapshot + router test | none | system prompt reviewed |
| DCI-2 (corpus mount + budget) | ~400 | mount-permission + budget-cap tests | DCI-1 | grammar profile lands |
| DCI-3 (level0–4 ladder) | ~350 | one test per level | DCI-1 | bytes-saved telemetry visible |
| DCI-4 (eval harness, 3 datasets) | ~600 | smoke pass on 5-task subset | DCI-1, 2, 3 | one full BCP-100 run green |
| DCI-5 (Argus skill) | ~150 | argus-cascade test | DCI-1 | skill loaded on synthetic query |
| DCI-6 (ralph compose) | 0 (docs only) | scenario test | v3.12 + DCI-1..3 | one all-night run logged |

Recommended order: **DCI-1 → DCI-2 → DCI-3 → DCI-4 (smoke) → DCI-5 →
DCI-4 (full) → DCI-6**. Bundles 1–3 are the spine, 4 is the proof, 5
makes it auto-engage, 6 is the autonomy compose.

---

## 8. Risks and known unknowns

- **Subprocess-availability bias.** DCI-Agent-Lite assumes `rg`,
  `sed`, `find` exist on the host. Lyra's `codesearch.py` already
  has the pure-Python fallback; we'll need to extend the same posture
  to `sed` and `find` (or document the host requirement).
- **Multi-process safety.** If two Lyra investigations run against
  the same corpus mount, the read-only constraint protects us; if
  someone wires up `investigate-rw`, the v3.10 sandbox isolation
  needs to gate writes.
- **Context-level 4 cost.** Per-window summarisation costs an extra
  model call per window. The level-3 sweet spot is real; level 4 is
  for long tails only.
- **Benchmark licensing.** BrowseComp-Plus and BRIGHT are public;
  the 21 M-doc Wikipedia corpus is reproducible from a dump. None
  block us from publishing Lyra-side numbers.
- **The paper might not reproduce on smaller models.** All headline
  numbers use frontier-class models with extended thinking. On
  `qwen-2.5-7b` the lift is smaller; the harness should expose that
  honestly rather than gate the feature on a big model.

---

## 9. Citation chain (for `CHANGELOG.md`)

Whatever ships as v3.13 should carry, in module docstrings:

```text
DCI: Direct Corpus Interaction.
Cite: Li, Zhang, Wei, et al. "Beyond Semantic Similarity: Rethinking
Retrieval for Agentic Search via Direct Corpus Interaction."
arXiv:2605.05242 (May 2026).
Reference impl: github.com/DCI-Agent/DCI-Agent-Lite.
```

This honours Lyra's "every borrowed idea has a visible citation chain"
contract from the v3.1.0 research-synthesis precedent.

---

## 10. Bottom line

The DCI thesis is the kind of finding that retroactively explains a
lot of 2024–2025 RAG frustration: we were optimising the wrong axis.
The model wasn't the bottleneck; the embedding-then-top-k interface
was. Lyra is unusually well-positioned to steal this — `codesearch.py`,
the sandboxed shell, the context compaction stack, the permissions
grammar, Argus' skill cascade, the upcoming Ralph loop — every
ingredient is already in the kitchen. The work in v3.13 is **wiring,
not invention**.

If we ship DCI-1 through DCI-3 alone, Lyra gets a credible
`investigate` mode for any local corpus, with the level-3 context
strategy that gave DCI-Agent-Lite its 62.9 % BCP. If we ship DCI-4
and DCI-5 we close the *proof* and the *auto-engagement*. If we ship
DCI-6, Lyra gets the combination the paper does not yet demonstrate:
**fresh-context Ralph loops wrapping DCI trajectories**, which is
where the long-tail multi-hop wins should compound.
