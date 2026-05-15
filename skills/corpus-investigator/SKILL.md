---
name: 'corpus-investigator'
description: 'When the user wants to find evidence in a corpus, skip semantic retrieval — grep the raw files directly, then read and cite.'
version: '0.1.0'
triggers: ['corpus-search', 'multi-hop-qa', 'investigate', 'find-evidence']
tags: ['retrieval', 'dci', 'agentic-search']
---

# Goal

When the question is "find me X in this corpus / on these docs / across
these files", interact with the raw files directly using `codesearch`,
`read_file`, and a bounded shell — not a semantic retriever.

Cite: arXiv:2605.05242 — *Beyond Semantic Similarity: Rethinking
Retrieval for Agentic Search via Direct Corpus Interaction*. The paper
shows this approach beats SOTA sparse/dense/reranker pipelines by
+11.0% on BrowseComp-Plus, +30.7% on multi-hop QA, and +21.5% on IR
ranking. The headline 62.9% BCP run uses `gpt-5.4-nano` with extended
thinking and context-management level 3.

# Constraints & Style

- Start with a **broad** pattern from the question, not a narrow one.
- Read **top hits with surrounding lines** before adding a second clue.
- Conjunct two clues only after each one independently returns hits.
- Never paraphrase the corpus — every claim ends with `path:line`.
- If three broad patterns return zero hits, the corpus probably does
  not contain the answer; say so instead of hallucinating.

# Workflow

1. `codesearch(<broad_pattern>)` — locate candidate files.
2. `read_file(<top_hit>, start_line=…, end_line=…)` — verify in context.
3. `codesearch(<narrower_pattern>)` — add a second clue.
4. `execute_code("find . -name '*<topic>*'")` — broaden when sparse.
5. `codesearch("<entity1>.*<entity2>")` — multi-entity conjunction,
   the move dense retrievers cannot replicate.
6. `execute_code("sed -n 'A,Bp' <file>")` — pin exact lines.
7. Final answer cites `path:line` for each claim, no narration.

# When to engage

Argus auto-routes here when the user query contains:

- "search through this / these files / corpus"
- "find evidence in" / "look up in"
- "what does <doc> say about" with a concrete corpus mount
- multi-hop questions over a known corpus

When in doubt, the `lyra investigate` CLI surface explicitly opts in.

# Budgets

The investigate runner enforces:

- `max_turns=300` (DCI-Agent-Lite default)
- `max_bash_calls=200`
- `max_bytes_read=100_000_000`
- `wall_clock_s=1800`

Stop early when the answer is cited. Do not pad the trajectory.

# Composes with

- `lyra ralph` — wrap long investigations in fresh-context iterations.
- Context level 3 (`--context-level 3`) — truncation + relevance
  filter + NGC running summary; the paper's headline configuration.
- `--thinking high` on supported providers — defer reasoning to native
  extended thinking instead of ReAct scaffolds in the prompt.
