# DCI-Agent-Lite -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: Direct Corpus Interaction (DCI) -- zero-index, zero-embedding agentic search by searching the raw corpus directly with terminal tools (`rg`, `find`, `sed`) instead of a semantic retriever or vector database.

**How it actually works**: DCI-Agent-Lite wraps the Pi coding agent harness (a Node.js CLI, external dependency) in RPC mode. The Python launcher (`pi_rpc_runner.py`) spawns Pi as a subprocess, connects over JSON-line stdin/stdout, and sends a question. The Pi agent has only two tools: `read` and `bash`. It uses `ripgrep` (`rg`) to search for keywords across flat text files, then `read` to inspect relevant documents. The agent freely composes these primitives -- run multiple searches in parallel, chain searches to narrow down, cross-check results -- across as many turns as needed (default 300 max). There is no retrieval stage separate from the reasoning loop: the LLM decides on each turn which terminal commands to run and how to interpret results.

The Python side manages the full lifecycle: RPC client startup, event recording (every tool call, LLM response, turn boundary), conversation artifact serialization (state.json, conversation.json, events.jsonl, final.txt), and optional auto-evaluation via an OpenAI judge model.

## 2. Architecture & Core Modules

**Entry point** (`dci-agent-lite` CLI):
- `src/dci/benchmark/pi_rpc_runner.py` -- Contains `main()`, CLI arg parsing, `PiRpcClient` class (RPC subprocess management, JSON-line protocol), `RunRecorder` class (event logging, conversation serialization, tool timing), and `judge_answer_sync()` (OpenAI judge for auto-grading).

**Core data flow**:
1. `dci-agent-lite` parses CLI args (provider, model, question, corpus cwd, max turns, context management level).
2. `PiRpcClient` spawns `node pi-mono/packages/coding-agent/dist/cli.js --mode rpc` as a subprocess.
3. Sends `{"id": "py-1", "type": "prompt", "message": "..."}` via stdin.
4. Reads JSON-line events from stdout: `turn_start`, `tool_execution_start`, `tool_execution_end`, `message_update` (text deltas), `agent_end`.
5. `RunRecorder` logs every event to `events.jsonl`, tracks tool timing, serializes the evolving conversation to `conversation_full.json` and `conversation.json`, and saves the final answer to `final.txt`.
6. Optionally grades the answer via OpenAI judge (`judge_answer_sync`) and writes `eval_result.json`.

**Key modules**:

| File | Role |
|------|------|
| `src/dci/benchmark/pi_rpc_runner.py` | Main entry point, RPC client, run recorder, judge |
| `src/dci/benchmark/pi_system_prompt.py` | Prints Pi's dynamically-generated system prompt for debugging |
| `src/dci/benchmark/export_bc_plus_docs.py` | Exports BrowseComp-Plus parquet corpus to domain-folder text files |
| `src/dci/benchmark/export_bright_docs.py` | Exports BRIGHT parquet corpora to text files |
| `prompts/system_prompt.txt` | Minimal system prompt (2 tools: read, bash; guidelines for rg/find usage) |
| `scripts/bcplus_eval/run_bcplus_eval.py` | Full benchmark harness: concurrent question running via asyncio, per-question RPC launcher, OpenAI judge, aggregate analysis with matplotlib plots |
| `pyproject.toml` | Hatchling build, dependencies (anthropic, datasets, httpx, huggingface-hub, matplotlib, numpy, pyarrow, scipy, tqdm) |
| `setup.sh` | One-click setup: installs uv+ripgrep, syncs Python deps, clones+builds pi-mono, downloads corpora from HuggingFace |
| `.env.template` | Optional: ANTHROPIC_API_KEY, OPENAI_API_KEY, VLLM_API_KEY |

**External dependency**: Pi coding agent (`pi-mono`, specifically branch `codex/context-management-ablation`) -- a Node.js coding agent harness that provides the LLM loop, tool execution environment, and context management. DCI-Agent-Lite does not implement its own agent loop; it delegates to Pi entirely and focuses on the corpus-side orchestration and evaluation.

**Context management (5 levels)**:
- level0: No context management
- level1: Light truncation of large tool results
- level2: Stronger truncation
- level3: Truncation + compaction (replace older tool results with placeholders)
- level4: Truncation + compaction + summarization (summarize older history)

**Architecture pattern**: RPC-driven agent harness -- a minimal Python control plane wraps a richer (external) agent runtime. The Python side handles the experiment pipeline (question loading, concurrent execution, result aggregation, plotting); the Node.js side handles the agent loop and tool sandbox. This split keeps the DCI-specific code (`src/dci/`) very small (6 files, ~2000 lines total).

## 3. Performance / Benchmarks

**Core result** (from README, verified at arXiv 2605.05242): DCI-Agent-Lite with `GPT-5.4-nano` achieves **62.9% accuracy on BrowseComp-Plus**, surpassing agentic search agents powered by `GPT-5.2`, `Claude-Sonnet-4.6`, `Qwen3.5-122B`, and `GLM-4.7`.

**Benchmark coverage**: 13 benchmarks across three categories:
- **Agentic Search**: BrowseComp-Plus (830 questions, 100,195-doc corpus)
- **Knowledge-Intensive QA**: NQ, TriviaQA, Bamboogle, HotpotQA, 2WikiMultiHopQA, MuSiQue (50 each / 300 total, Wikipedia-18 corpus of 21M docs)
- **IR Ranking**: BRIGHT (4 subsets: Biology 103 Qs / 57K docs, Earth Science 116 Qs / 121K docs, Economics 103 Qs / 50K docs, Robotics 101 Qs / 62K docs)

**Run-time configuration**: 300 max turns, context management level3, `--thinking high`.

**Cost modelling**: Built-in per-query cost accounting at OpenAI API rates ($0.20/1M input, $0.02/1M cached input, $1.25/1M output tokens). The eval pipeline generates matplotlib figures (scatter plots of cost vs latency, tool breakdowns, box plots of correct vs incorrect query metrics).

**Tool usage pattern**: The eval pipeline tracks per-tool call counts, durations, error counts, and produces detailed "tool_summary" analysis showing which tools correlate with correct vs incorrect answers.

## 4. Trade-offs

**Wins**:
- Zero indexing: No embeddings, no vector DB, no chunking decisions. The corpus is just flat text files. Start immediately after download.
- High-resolution search: Regex-level control over retrieval. Can search for variable names, code snippets, line-level patterns that semantic retrieval would miss.
- Extreme simplicity: Core Python code is ~2000 lines across 6 files. No API servers, no database, no index build pipeline.
- Composability: The agent can chain multiple searches, cross-reference results, and iteratively narrow down -- same freedom as a human using a terminal.
- Privacy: All corpus data stays local; only LLM API calls leave the machine.

**Losses**:
- No semantic understanding: Pure keyword/regex search. Misses semantically relevant documents that use different vocabulary. No synonym expansion, no query rewriting.
- Text-only corpora: Cannot directly search images, PDFs, or structured data.
- Performance on large corpora: `ripgrep` is fast, but brute-force regex scanning of 21M Wikipedia articles (100 words each) is slower than ANN index lookup.
- External Pi dependency: Requires cloning and building a separate Node.js monorepo. Pi's branch `codex/context-management-ablation` is specific and may diverge from upstream.
- No web search: Deliberately excluded (by system prompt). For questions requiring current web information, this is a hard limitation.
- LLM API cost: Long-horizon runs (up to 300 turns) can accumulate significant token usage. The cost modelling exists but is post-hoc, not preventive.

**Known limitations (from repo)**:
- The context management system (level0-level4) is described as "ablation" -- it ships in the Pi fork but is not yet well-characterized for all run lengths.
- The BRIGHT export script has a `.dci_export_complete` marker file pattern that could conflict with re-exports.
- The `--resume` flag validates all run parameters match exactly; mismatch is a hard error, not a merge.

## 5. Design Rationale

The core insight (from the paper "Beyond Semantic Similarity: Rethinking Retrieval for Agentic Search via Direct Corpus Interaction", arXiv 2605.05242) is that **semantic similarity is insufficient for agentic search**. An agent performing multi-step research needs:

1. **Precision**: Exact-match retrieval for names, numbers, identifiers that semantic search blurs.
2. **Composability**: Chain grep | awk | sort to filter on multiple criteria -- impossible with a single embedding query.
3. **Visibility**: The agent sees raw file contents (not chunked snippets) and can judge context directly.
4. **Simplicity**: A complete retrieval system with embeddings + vector DB + chunking + reranking is complex and fragile. Terminal tools are decades-proven.

The design mirrors how a human researcher would search a codebase or document corpus: start with `grep -r` for a keyword, read promising files, refine the search, cross-reference. The agent does the same at machine speed, guided by LLM reasoning.

The Pi coding agent was chosen as the harness because it already provides code-execution tool support, RPC mode, and a context management system optimized for long coding sessions -- the same patterns needed for long-horizon deep research.

## 6. Transfer to Lyra

**One transferable idea**: **Replace/supplement Lyra's semantic RAG tool with a Direct Corpus Interaction tool that uses `ripgrep` (or equivalent) to search local source files with regex patterns**. Lyra's current agent tool-use architecture (§4.x / tool-use workstream) could add a `corpus_search` primitive: `rg -n "pattern" --include "*.py" --include "*.ts"` that the agent invokes to find relevant code, then `read` to inspect. This would be particularly valuable for:

- **Codebase QA**: Finding variable definitions, function calls, import paths via exact regex match.
- **Configuration search**: Grepping for specific settings across YAML/TOML/JSON files.
- **Cross-referencing**: Chaining multiple searches to trace data flow across modules.
- **Low-latency retrieval**: For well-defined lookups (a known function name, a specific error string), regex search is faster and more reliable than embedding search.

This is complementary to semantic RAG, not a replacement. The DCI tool handles high-precision lookups; the semantic retriever handles broad-concept queries.

**Workstream route**: §4.x (Agent Toolbox / Tool-Use Architecture) -- add a `bash_corpus_search` or `rg_search` tool alongside Lyra's existing tools. The key implementation challenge is sandboxing (limiting the agent's bash execution to the corpus directory) and output truncation (large result sets).

**Impact**: 7/10 -- Enables a fundamentally new retrieval primitive for Lyra's agent that the current semantic-only pipeline cannot replicate. Eliminates the cold-start problem (no index build needed for a new codebase).

**Effort**: 5/10 -- Straightforward tool addition, but requires careful sandboxing of the bash subprocess and integration with Lyra's existing tool-use protocol (function calling, output format). The DCI context management levels (truncation/compaction/summarization) are a secondary concern.

**Tier**: Core -- This changes how Lyra retrieves information at the fundamental tool level, affecting every agentic workflow.

**LICENSE**: MIT (Copyright 2026 Dongfu Jiang). Compatible with Lyra's licensing. Full permissive reuse allowed.
