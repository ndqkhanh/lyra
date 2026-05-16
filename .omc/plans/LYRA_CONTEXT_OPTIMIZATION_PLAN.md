# LYRA Context Optimization Ultra Plan
*Solving Context Bloat & Context Rot — All Phases*

**Research base:** 4 featured repos (Caveman 60.6k★, RTK 48.4k★, code-review-graph 16.6k★, context-mode 14.8k★) + 20 additional repos + 25 academic papers (EMNLP'23, ACL'24, NeurIPS'23–'25, ICLR'24)
**Generated:** 2026-05-15

---

## The Problem: Lyra's Context Architecture Today

Lyra currently sends **single-turn messages only**:

```python
# agent_integration.py — both _run_anthropic() and _run_openai()
messages=[{"role": "user", "content": user_input}]
```

This means:
- **No conversation memory** — each turn is stateless; the model forgets everything
- **No context rot** yet — but also no continuity, no learning, no session awareness
- **O(n²) cost cliff is ahead** the moment multi-turn history is wired in naively

The goal of this plan is to wire in multi-turn memory AND prevent the O(n²) cost explosion from the start — implementing all token-reduction layers before they're needed, not after.

---

## Research Foundation: Technique Taxonomy

| Layer | Technique | Source | Reduction |
|---|---|---|---|
| Output verbosity | Terse-output system prompt | Caveman (60.6k★) | 65% output tokens |
| Tool output | Pre-ingestion filtering | RTK (48.4k★) | 60–90% per session |
| Code context | AST blast-radius scoping | code-review-graph (16.6k★) | 8–49x fewer tokens |
| Bulk data | Sandbox interception | context-mode (14.8k★) | 98% on raw data |
| Prompt compression | Perplexity-based pruning | LLMLingua (6.2k★, EMNLP'23) | up to 20x |
| KV eviction | Attention score accumulation | H2O (NeurIPS'23) | 5x cache reduction |
| KV eviction | Attention sinks + sliding window | StreamingLLM (ICLR'24) | ∞ streaming |
| Conversation history | Recursive rolling summary | MemGPT (arxiv:2310.08560) | O(1) context growth |
| Long-term memory | Salient fact extraction | Mem0 (41k★) | 93% per-turn reduction |
| RAG context | Hierarchical summary trees | RAPTOR (Stanford) | multi-hop w/o full docs |
| Soft compression | Summary vectors | AutoCompressors (EMNLP'23) | 30K→soft prompts |
| Provider caching | cache_control breakpoints | Anthropic | 90% cost on stable prefix |
| Serialization | CSV over JSON | production best practice | 40–70% |

**Key insight from "Context Rot" study (Chroma, 2025):** Every model tested degrades significantly well before hitting its context limit — at 50K tokens on a 200K window. Three compounding mechanisms: lost-in-the-middle effect, attention dilution, distractor interference. The fix is not a bigger window; it is *less context*.

---

## Phase Map

```
Phase A — Multi-turn Foundation         [prerequisite for all]
Phase B — Output Compression            [65% output savings, zero infra]
Phase C — Tool Output Filtering         [60–90% on terminal/tool results]
Phase D — Sliding Window + Summarizer   [O(1) history growth]
Phase E — Hierarchical Memory (MemGPT) [persistent across sessions]
Phase F — Prompt Compression            [20x on injected context]
Phase G — RAG-based Context Retrieval  [semantic history retrieval]
Phase H — Provider Optimizations        [90% on stable prefix]
```

---

## Phase A: Multi-turn Conversation Foundation

**What:** Wire conversation history into `TUIAgentIntegration`. Currently single-turn; add a rolling `_messages` list that persists across `run_agent()` calls.

**Why first:** All other phases depend on having accumulated context to compress.

### Files changed
- `cli/agent_integration.py` — add `_messages: list[dict]`, append user+assistant turns
- `cli/tui.py` — expose `clear_history()`, `get_history_stats()` to commands

### Implementation

```python
# agent_integration.py

class TUIAgentIntegration:
    def __init__(self, model: str, repo_root, budget_cap_usd: float | None = None):
        ...
        self._messages: list[dict] = []          # conversation history
        self._system_prompt: str = ""            # stable system prompt (cache-eligible)
        self._total_input_tokens_session = 0
        self._total_output_tokens_session = 0

    async def run_agent(self, user_input: str) -> AsyncIterator[dict]:
        self._messages.append({"role": "user", "content": user_input})
        assistant_content = ""
        async for event in self._run_provider(self._messages):
            if event["type"] == "text":
                assistant_content += event["content"]
            yield event
        if assistant_content:
            self._messages.append({"role": "assistant", "content": assistant_content})

    def clear_history(self) -> None:
        self._messages.clear()

    def history_token_estimate(self) -> int:
        # Rough estimate: 1 token ≈ 4 chars
        return sum(len(m["content"]) // 4 for m in self._messages)
```

### `/history` command in TUI

```
/history clear   — wipe conversation memory
/history show    — display turn count + estimated tokens
/history stats   — full usage breakdown
```

### Acceptance criteria
- [ ] Second turn in TUI sees output referencing first turn
- [ ] `/history stats` shows correct token counts
- [ ] `clear_history()` resets context; next turn is stateless again

---

## Phase B: Output Verbosity Reduction (Caveman-inspired)

**What:** Inject a terse-output system prompt at initialization. Configurable verbosity levels. No proxies, no extra infra — pure prompt engineering.

**Evidence:** Caveman (60.6k★) achieves 65% output token reduction (range 22–87%) with a simple skill/system-prompt injection. Best case: React explanation 1,180 → 159 tokens (87%).

### Files changed
- `cli/agent_integration.py` — `set_verbosity(level)`, prepend system prompt
- `cli/tui.py` — `/verbosity [lite|full|ultra]` command

### Verbosity levels

```python
VERBOSITY_PROMPTS = {
    "lite": (
        "Be concise. Omit filler phrases. Use short sentences. "
        "Skip pleasantries."
    ),
    "full": (  # DEFAULT
        "Respond with maximum brevity. Use fragments, not sentences, where unambiguous. "
        "No preamble, no summary, no filler. Code over prose. "
        "If asked to explain, use bullet points and minimal words."
    ),
    "ultra": (
        "ONE-WORD or ONE-LINE responses only unless code is required. "
        "Strip ALL explanatory prose. Labels only. No punctuation unless code."
    ),
    "off": "",  # full default model verbosity
}
```

### Memory file compression (Caveman's `caveman-compress`)
Apply terse rewriting to Lyra's own memory/skill files before they're injected into context:

```python
async def compress_memory_file(self, content: str) -> str:
    """Rewrite memory content in terse style — ~46% input token reduction."""
    prompt = (
        "Rewrite the following in the most compressed form possible. "
        "Keep all facts. Remove all prose. Use fragments, bullets, abbreviations. "
        "Target: maximum information density, minimum token count.\n\n"
        f"{content}"
    )
    return await self._one_shot(prompt)
```

### Acceptance criteria
- [ ] `ultra` mode: average response ≤ 35% of `off` mode token count
- [ ] `/verbosity` toggles without session restart
- [ ] Memory files re-injected after compression are verifiably shorter

---

## Phase C: Tool Output Filtering (RTK-inspired)

**What:** Intercept tool/command results before they enter context. Apply noise removal, smart truncation, deduplication. Implement as a `ToolOutputFilter` class.

**Evidence:** RTK (48.4k★) achieves 60–90% per-session reduction on terminal output. A 30-minute session: ~118K raw tokens → ~23.9K filtered tokens.

### Files changed
- `cli/tool_output_filter.py` — new file, `ToolOutputFilter` class
- `cli/agent_integration.py` — pipe tool results through filter before appending to `_messages`

### ToolOutputFilter design

```python
class ToolOutputFilter:
    """Filters tool/command output before it enters the context window."""

    MAX_FILE_LINES = 200        # hard cap on file content
    MAX_TEST_FAILURES = 10      # keep only first N failures
    MAX_GREP_RESULTS = 50       # keep only first N matches
    ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mK]')

    def filter(self, tool_name: str, output: str) -> str:
        output = self.ANSI_RE.sub('', output)           # strip ANSI
        output = self._dedup_lines(output)               # remove duplicate lines
        if tool_name in ('ls', 'find', 'tree'):
            return self._filter_listing(output)
        if tool_name in ('cat', 'read_file'):
            return self._filter_file(output)
        if tool_name in ('grep', 'rg', 'ag'):
            return self._filter_search(output)
        if tool_name in ('git_diff', 'git status'):
            return self._filter_diff(output)
        if tool_name in ('pytest', 'npm test', 'cargo test'):
            return self._filter_test(output)
        return self._generic_truncate(output)

    def _filter_test(self, output: str) -> str:
        """Keep only failures + summary line."""
        lines = output.splitlines()
        failures = [l for l in lines if 'FAIL' in l or 'ERROR' in l or 'assert' in l.lower()]
        summary = [l for l in lines if 'passed' in l or 'failed' in l or 'error' in l]
        kept = failures[:self.MAX_TEST_FAILURES] + summary[-3:]
        return '\n'.join(kept)

    def compression_ratio(self, original: str, filtered: str) -> float:
        if not original:
            return 1.0
        return len(filtered) / len(original)
```

### Metrics to track
- Per-tool compression ratio (expose via `/tools stats`)
- Session-level tool token savings vs raw

### Acceptance criteria
- [ ] `pytest` output: only failures + summary enter context
- [ ] `cat` on a 2,000-line file: ≤ 200 lines in context
- [ ] Session tool token savings ≥ 50% vs unfiltered
- [ ] All filtered output still sufficient for agent to act correctly

---

## Phase D: Sliding Window + Rolling Summarizer

**What:** Prevent unbounded history growth. Keep last N verbatim turns + a rolling summary of older turns. This is the primary defense against O(n²) cost growth.

**Evidence:**
- MemGPT (arxiv:2310.08560): recursive summary keeps O(1) context overhead while maintaining conversational continuity
- Wang et al. 2023 (Neurocomputing 2025): rolling summaries maintain consistency over long conversations
- Production data: LangChain sliding window + periodic summarization reduces history tokens 60–80%

### Files changed
- `cli/context_manager.py` — new file, `ContextManager` class
- `cli/agent_integration.py` — integrate `ContextManager` into message preparation

### ContextManager design

```python
@dataclass(frozen=True)
class ContextBudget:
    max_history_tokens: int = 6_000      # verbatim recent turns
    max_summary_tokens: int = 1_500      # compressed older turns
    verbatim_turns: int = 4              # always keep last N turns verbatim
    compression_trigger: float = 0.80   # compress when at 80% of budget

class ContextManager:
    """Manages conversation history to prevent context bloat."""

    def __init__(self, budget: ContextBudget, summarizer: Callable):
        self._budget = budget
        self._summarizer = summarizer     # async fn(messages) -> str
        self._summary: str = ""
        self._verbatim: list[dict] = []
        self._total_turns = 0

    async def add_turn(self, user_msg: str, assistant_msg: str) -> None:
        self._verbatim.append({"role": "user", "content": user_msg})
        self._verbatim.append({"role": "assistant", "content": assistant_msg})
        self._total_turns += 1
        if self._should_compress():
            await self._compress()

    def build_messages(self, system: str = "") -> list[dict]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        if self._summary:
            msgs.append({
                "role": "system",
                "content": f"[Conversation summary — {self._total_turns - len(self._verbatim) // 2} earlier turns]:\n{self._summary}"
            })
        msgs.extend(self._verbatim)
        return msgs

    def _should_compress(self) -> bool:
        estimated = sum(len(m["content"]) // 4 for m in self._verbatim)
        return estimated > self._budget.max_history_tokens * self._budget.compression_trigger

    async def _compress(self) -> None:
        # Keep last `verbatim_turns` turns verbatim; summarize the rest
        keep_count = self._budget.verbatim_turns * 2  # user+assistant pairs
        to_summarize = self._verbatim[:-keep_count]
        self._verbatim = self._verbatim[-keep_count:]

        new_summary = await self._summarizer(to_summarize, existing=self._summary)
        self._summary = new_summary
```

### Summarizer prompt

```
You are summarizing a conversation excerpt for memory compression.
Existing summary (if any): {existing}
New turns to incorporate: {turns}

Produce a single dense paragraph capturing: key decisions made,
facts established, tasks completed, open questions. Maximum 200 words.
Prioritize: technical facts > decisions > context > small talk.
```

### Acceptance criteria
- [ ] After 20+ turns, context stays ≤ 8K tokens regardless of verbosity
- [ ] Agent in turn 15 correctly references a fact from turn 3 (via summary)
- [ ] Compression trigger fires at configured threshold
- [ ] `/history stats` shows: verbatim turns, summarized turns, summary tokens

---

## Phase E: Hierarchical Persistent Memory (MemGPT-inspired)

**What:** Three-tier memory across sessions. Core memory (always in context), session memory (current session summary), archival memory (SQLite full-text search). Based on MemGPT (UC Berkeley, arxiv:2310.08560) and Mem0's approach (93% per-turn reduction, 41k★).

**Evidence:**
- Mem0 reduces per-turn tokens from 26K → 1.8K (93% reduction) with 26% accuracy improvement
- MemGPT enables "infinite" effective context via OS-style paging
- context-mode (14.8k★) uses SQLite for session continuity — session compaction to ≤2KB snapshots

### Files changed
- `cli/memory_manager.py` — extend existing file with three-tier architecture
- `cli/agent_integration.py` — inject memory tiers into system prompt
- New SQLite DB: `~/.lyra/memory.db`

### Memory architecture

```python
@dataclass(frozen=True)
class CoreMemory:
    """Always in context. ≤ 500 tokens. User facts, preferences, active tasks."""
    user_facts: tuple[str, ...]         # "user prefers Python", "working on X"
    active_tasks: tuple[str, ...]       # current in-progress items
    preferences: tuple[str, ...]        # response style, domain focus

@dataclass(frozen=True)
class SessionMemory:
    """Current session summary. ≤ 1,500 tokens. Built by ContextManager (Phase D)."""
    summary: str
    turn_count: int
    key_outcomes: tuple[str, ...]

class ArchivalMemory:
    """SQLite FTS5 store. Retrieved by semantic similarity, not loaded wholesale."""

    def __init__(self, db_path: Path):
        self._db = sqlite3.connect(db_path)
        self._init_schema()

    def store(self, session_id: str, content: str, tags: list[str]) -> None:
        ...

    def search(self, query: str, limit: int = 5) -> list[str]:
        """BM25 FTS5 search — returns top-k relevant memory chunks."""
        ...
```

### Memory injection into context

```python
def build_system_prompt(self) -> str:
    parts = [BASE_SYSTEM_PROMPT]

    # Core memory (always present, ≤500 tokens)
    if self._core.user_facts:
        parts.append("## User\n" + "\n".join(f"- {f}" for f in self._core.user_facts))

    # Archival retrieval (only if relevant, ≤800 tokens)
    relevant = self._archival.search(self._current_query, limit=3)
    if relevant:
        parts.append("## Relevant past context\n" + "\n\n".join(relevant))

    return "\n\n".join(parts)
```

### Memory update operations (tool calls)

```
core_memory_add(fact: str)           — add a user/task fact to core memory
core_memory_remove(fact_id: str)     — remove stale fact
archival_memory_store(content: str)  — archive current session
archival_memory_search(query: str)   — retrieve relevant past context
session_save()                       — snapshot current session to archival
```

### Acceptance criteria
- [ ] Second session recognizes facts established in first session
- [ ] Core memory stays ≤ 500 tokens always
- [ ] Archival search returns relevant context in < 50ms
- [ ] `/memory show` displays all three tiers

---

## Phase F: Prompt Compression Layer (LLMLingua-inspired)

**What:** Compress injected context (memory, retrieved docs, file content) before it hits the API. Apply perplexity-based token pruning or a lightweight classifier approach.

**Evidence:**
- LLMLingua (microsoft, 6.2k★, EMNLP'23): up to 20x compression, minimal performance loss, integrated in LangChain/LlamaIndex
- LLMLingua-2 (ACL'24): task-agnostic, 3–6x faster, 50–80% token removal
- Selective Context (EMNLP'23): 40% reduction, no model training, self-information scoring
- Headroom (1.7k★): agent-oriented, 60–95% fewer tokens on tool outputs + RAG chunks

### Implementation options (choose by compute budget)

| Option | Method | Cost | Reduction | Quality |
|---|---|---|---|---|
| A (zero-infra) | Simple heuristics | Free | 20–40% | Good |
| B (lightweight) | Selective Context (self-info) | Cheap | 40% | Good |
| C (best) | LLMLingua-2 API or local | Low | 50–80% | Best |

### Option A: Heuristic compression (default, zero extra cost)

```python
class HeuristicCompressor:
    """Zero-infra compression via textual heuristics."""

    def compress(self, text: str, target_ratio: float = 0.6) -> str:
        lines = text.splitlines()
        lines = self._remove_blank_runs(lines)
        lines = self._remove_boilerplate(lines)
        lines = self._truncate_repetitive_blocks(lines)
        lines = self._shorten_urls(lines)
        return '\n'.join(lines)

    def _remove_boilerplate(self, lines: list[str]) -> list[str]:
        skip_patterns = [
            r'^#\s*(Copyright|License|Author)',
            r'^\s*/\*\*?\s*$',  # javadoc openers
            r'^\s*\*\s*@(param|returns|throws)',
        ]
        ...
```

### Option B: Self-information scoring (Selective Context approach)

```python
class SelectiveContextCompressor:
    """Prune low-self-information sentences. No training required."""

    def compress(self, text: str, keep_ratio: float = 0.6) -> str:
        sentences = self._split_sentences(text)
        scores = [self._self_info_score(s) for s in sentences]
        threshold = sorted(scores)[int(len(scores) * (1 - keep_ratio))]
        return ' '.join(s for s, sc in zip(sentences, scores) if sc >= threshold)

    def _self_info_score(self, sentence: str) -> float:
        """Proxy: rare/specific words score higher than common words."""
        words = sentence.lower().split()
        return sum(math.log(1 / (COMMON_WORD_FREQ.get(w, 1e-6))) for w in words) / max(len(words), 1)
```

### Acceptance criteria
- [ ] Injected research/doc context compressed ≥ 40% before API call
- [ ] Response quality (human eval) unchanged on 10 test prompts
- [ ] Compression runs in < 200ms for typical context payloads
- [ ] Compression ratio reported in `/history stats`

---

## Phase G: RAG-based Context Retrieval

**What:** Replace "inject all history" with "retrieve only relevant history." Embed past turns; at query time, retrieve the top-k most semantically relevant past turns.

**Evidence:**
- RAG-based context management reduces tokens ~75%, response time ~62% (rag-mcp)
- RECOMP (ICLR'24): compressed retrieved docs to 6% of original size with minimal quality loss
- "A focused 300-token context frequently outperforms a 113,000-token context" (Chroma, 2025)

### Files changed
- `cli/memory_manager.py` — add `SemanticRetriever` using local embeddings
- `cli/agent_integration.py` — switch history injection from rolling-append to retrieval

### SemanticRetriever design

```python
class SemanticRetriever:
    """Embeds conversation turns; retrieves semantically relevant ones."""

    def __init__(self, embedding_fn: Callable[[str], list[float]]):
        self._embedding_fn = embedding_fn
        self._store: list[tuple[dict, list[float]]] = []  # (message, embedding)

    def index(self, message: dict) -> None:
        emb = self._embedding_fn(message["content"])
        self._store.append((message, emb))

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        if not self._store:
            return []
        query_emb = self._embedding_fn(query)
        scores = [cosine_similarity(query_emb, emb) for _, emb in self._store]
        top_indices = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
        return [self._store[i][0] for i in sorted(top_indices)]  # preserve order
```

### Embedding options (no external API required)

```python
# Option A: Use the LLM provider's embedding endpoint (Anthropic/OpenAI)
# Option B: Local sentence-transformers model (all-MiniLM-L6-v2, 22MB)
# Option C: TF-IDF cosine similarity (zero-dependency fallback)
```

### Context assembly with retrieval

```python
def build_messages_with_retrieval(self, user_input: str) -> list[dict]:
    # 1. Retrieve relevant history
    retrieved = self._retriever.retrieve(user_input, top_k=5)
    # 2. Always include last 2 turns verbatim (recency bias)
    recent = self._verbatim[-4:]  # last 2 user+assistant pairs
    # 3. Merge, deduplicate, sort by original position
    context = self._merge_unique(retrieved, recent)
    return self._build_messages(context)
```

### Acceptance criteria
- [ ] With 50+ turns of history, context ≤ 8K tokens per turn
- [ ] Agent correctly answers "what did we discuss about X?" from archival retrieval
- [ ] Local embedding (sentence-transformers) works offline, < 100ms per query
- [ ] Retrieval quality: precision@5 ≥ 0.8 on 20 test queries over saved histories

---

## Phase H: Provider-Level Optimizations

**What:** Exploit provider caching and pricing mechanics. Highest ROI changes with zero quality impact.

**Evidence:**
- Anthropic prompt caching: 90% cost reduction, 85% latency reduction on stable prefixes
- A 50K-token system prompt, 500 req/day → $75/day → $7.69/day with caching ($24,500/year savings)
- Cache read tokens do NOT count against ITPM rate limits (Claude 3.7 Sonnet)

### 1. Anthropic: Prompt Caching

```python
# agent_integration.py — _run_anthropic()

async def _run_anthropic(self, messages: list[dict]) -> AsyncIterator[dict]:
    system = [
        {
            "type": "text",
            "text": self._system_prompt,
            "cache_control": {"type": "ephemeral"}  # 5-min TTL, 90% cost on re-use
        }
    ]
    async with self._client.messages.stream(
        model=self._model_name,
        max_tokens=4096,
        system=system,
        messages=messages,
    ) as stream:
        ...
        # Track cache metrics
        usage = (await stream.get_final_message()).usage
        cache_read = getattr(usage, 'cache_read_input_tokens', 0)
        cache_write = getattr(usage, 'cache_creation_input_tokens', 0)
        yield {"type": "usage", "metadata": {
            ...,
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "cache_savings_usd": (cache_read / 1_000_000) * (3.0 * 0.9),  # 90% saved
        }}
```

### 2. Stable prefix ordering

Put content in this order to maximize cache hit rate:
1. System prompt (stable, cache-eligible)
2. Core memory (changes rarely)
3. Tool definitions (stable)
4. Conversation history summary (changes per session)
5. Recent verbatim turns (changes each turn)
6. Current user message (always last)

### 3. DeepSeek: stream_options for accurate usage

Already implemented. Ensure `stream_options={"include_usage": True}` stays in all OpenAI-compatible calls.

### 4. Context budget monitoring + alerts

```python
CONTEXT_BUDGET_WARN = 0.70   # warn at 70% of provider context limit
CONTEXT_BUDGET_CRIT = 0.85   # trigger aggressive compression at 85%

PROVIDER_CONTEXT_LIMITS = {
    "claude-sonnet-4-6": 200_000,
    "deepseek-chat": 64_000,
    "gpt-4o": 128_000,
}

def _check_context_budget(self, input_tokens: int) -> None:
    limit = PROVIDER_CONTEXT_LIMITS.get(self._model_name, 100_000)
    ratio = input_tokens / limit
    if ratio >= CONTEXT_BUDGET_CRIT:
        # Auto-trigger Phase D compression
        asyncio.create_task(self._context_manager.force_compress())
    elif ratio >= CONTEXT_BUDGET_WARN:
        self._emit_warning(f"Context at {ratio:.0%} of limit — consider /history clear")
```

### 5. Serialization optimization

```python
def serialize_for_context(self, data: Any) -> str:
    """Use compact serialization — CSV for tables, compact JSON otherwise."""
    if isinstance(data, list) and all(isinstance(r, dict) for r in data):
        # Tabular data → CSV (40–70% smaller than JSON)
        if data:
            keys = list(data[0].keys())
            rows = [[str(r.get(k, '')) for k in keys] for r in data]
            return ','.join(keys) + '\n' + '\n'.join(','.join(r) for r in rows)
    # Compact JSON: no indentation, no spaces
    return json.dumps(data, separators=(',', ':'))
```

### Acceptance criteria
- [ ] Status bar shows `Cache: Xk` tokens saved per turn when cache active
- [ ] Anthropic calls include `cache_control` on system prompt
- [ ] Context budget warnings fire before hitting provider limit
- [ ] Tabular data serialized as CSV, not JSON

---

## Implementation Sequence & Milestones

| Phase | Effort | Dependencies | Expected Reduction | Cumulative |
|---|---|---|---|---|
| A: Multi-turn Foundation | 1 day | none | baseline | baseline |
| B: Output Verbosity | 0.5 day | A | −65% output tokens | −65% output |
| C: Tool Output Filter | 1 day | A | −60–90% tool tokens | −75% total |
| D: Sliding Window+Summary | 1.5 days | A | O(1) history | stable |
| E: Hierarchical Memory | 2 days | D | −93% per-turn | very low |
| F: Prompt Compression | 1 day | E | −20–50% injected | very low |
| G: RAG Retrieval | 2 days | E | optimal only relevant | minimal |
| H: Provider Optimizations | 0.5 day | A | −90% on stable prefix | near-zero on cache |

**Total effort estimate:** ~9.5 engineering days for all phases  
**Expected steady-state cost after Phase H:** < 5% of naive multi-turn baseline

---

## Observability & Metrics

Every phase must be measurable. The TUI status bar and `/history stats` must show:

```
Context Status:
  Verbatim turns:       4  (last 4 turns in full)
  Summarized turns:    23  (compressed into 1.2K tokens)
  Core memory:        380 tokens
  Session tokens:    6,840 tokens  [34% of 20K budget]
  Cache hit rate:     87%  (Anthropic prompt cache)

Token Budget:
  Input this turn:   4,200
  Output this turn:    830
  Cache saved:       3,100  ($0.009)
  Session total:    42,100 input / 18,600 output
  Session cost:      $0.41

Tool Compression:
  pytest:           94% (12K → 720 tokens)
  git diff:         78%  (4.2K → 920 tokens)
  file reads:       72% (session avg)
```

---

## Context Rot Prevention: Key Design Invariants

Based on "Context Rot" (Chroma 2025) and "Lost in the Middle" (Stanford 2023):

1. **Never exceed 70% of context window** — degradation begins before the limit
2. **Place critical information at edges** — beginning (system prompt) or end (recent turns); middle is "lost"
3. **Fresh > compressed > absent** — a short current fact beats a long summary beats nothing
4. **Distractor pruning** — irrelevant retrieved content degrades more than adding relevant content helps; be selective
5. **Recency always verbatim** — last 2 turns must never be summarized; the model needs exact recent state
6. **One quality embedding > many cheap embeddings** — embedding model quality determines retrieval quality more than chunking strategy (Vectara 2024)

---

## File Structure After All Phases

```
src/lyra_cli/cli/
├── agent_integration.py     # Phase A, H — multi-turn, provider caching
├── context_manager.py       # Phase D — sliding window + summarizer (NEW)
├── tool_output_filter.py    # Phase C — tool output compression (NEW)
├── prompt_compressor.py     # Phase F — heuristic + selective compression (NEW)
├── semantic_retriever.py    # Phase G — embedding + retrieval (NEW)
├── memory_manager.py        # Phase E — three-tier memory (EXTEND existing)
├── tui.py                   # All phases — status bar, commands
└── ...existing files...
```

---

## Research Sources

### Repos
- **Caveman** (60.6k★): github.com/juliusbrussee/caveman — prompt-level output compression
- **RTK** (48.4k★): github.com/rtk-ai/rtk — Rust CLI tool output filtering
- **code-review-graph** (16.6k★): github.com/tirth8205/code-review-graph — AST blast-radius scoping
- **context-mode** (14.8k★): github.com/mksglu/context-mode — SQLite sandbox for bulk data
- **LLMLingua** (6.2k★): github.com/microsoft/LLMLingua — perplexity-based prompt compression
- **Mem0** (41k★): mem0.ai — salient fact extraction, 93% per-turn reduction
- **headroom** (1.7k★): github.com/chopratejas/headroom — agent-oriented context compression
- **NVIDIA/kvpress**: github.com/NVIDIA/kvpress — KV cache eviction methods

### Papers
- LLMLingua (EMNLP'23, arXiv:2310.05736) — 20x prompt compression
- LLMLingua-2 (ACL'24, arXiv:2403.12968) — task-agnostic, 50–80% token removal
- H2O (NeurIPS'23, arXiv:2306.14048) — KV cache eviction, 29x throughput
- StreamingLLM (ICLR'24, arXiv:2309.17453) — attention sinks, ∞ streaming
- MemGPT (arXiv:2310.08560) — OS-style hierarchical memory
- AutoCompressors (EMNLP'23, arXiv:2305.14788) — soft summary vectors
- RECOMP (ICLR'24) — RAG compression to 6% original size
- Lost in the Middle (Stanford, arXiv:2307.03172) — U-shaped performance curve
- Context Rot (Chroma 2025) — empirical degradation study across 18 models
- Selective Context (EMNLP'23, arXiv:2310.06201) — self-information pruning
- Prompt Compression Survey (NAACL'25 Oral, arXiv:2410.12388)
- KVzip (NeurIPS'25 Oral) — 3–4x KV cache reduction, training-free
- RocketKV (ICML'25) — 400x KV compression, 3.7x speedup
