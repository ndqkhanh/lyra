# Lyra Context Optimization Plan

**Goal**: Reduce redundant context-window cost in Lyra's agent loop — cutting O(n²) token growth, preserving decision rationale across compactions, and maximising prompt-cache hit ratio.

**Research grounding**: "Reducing Redundant Context-Window Cost in LLM Coding Agents: A Deep Technical Survey" (`references/Reducing Redundant Context-Window Cost...md`)

---

## What the research says (ranked by production ROI)

| # | Technique | Research source | Gain |
|---|-----------|-----------------|------|
| 1 | **Cache-prefix byte stability** | §5.1, Anthropic April 2026 postmortem | ~10× cost reduction on cache hits |
| 2 | **Early compaction at 60 %** (not 95 %) with decision-preserving prompt | §13 #3, MindStudio, okhlopkov.com | Stops reasoning degradation from context rot |
| 3 | **Sub-agent context isolation** | §13 #2, §6.1 | Most effective single technique; already partially in Lyra |
| 4 | **Repo-map code context** (Aider-style) | §6.2, §11 step 2c | Eliminates whole-file-dump waste |
| 5 | **Tiered memory** (core / recall / archival) | §3.5 CoALA, §4 Letta/Mem0, §9 | Preserves decisions across compactions |
| 6 | **Token compression on tool outputs** | §3.1 LLMLingua-2, §3.4 AgentDiet | 2–5× compression on logs/traces |
| 7 | **Post-compaction essentials injection** | §6.1, §7 Nick Porter pattern | Recovers what summarisation always loses |
| 8 | **ACON-style compression guidelines** | §3.4 ACON arXiv:2510.00615 | Learns what to keep from failure trajectories |

---

## Current Lyra context system (existing modules)

```
lyra-core/src/lyra_core/
  context/
    compactor.py          ← NGC compaction logic
    compact_router.py     ← when/how to compact
    compact_validate.py   ← compaction output validation
    eternal_autocompact.py← auto-compaction trigger
    ngc.py                ← NGC compactor engine
    altitude.py           ← context utilisation %
    profile.py            ← what's using tokens
    relevance.py          ← relevance scoring
    working_context.py    ← working context assembly
    pipeline.py           ← context pipeline
    provider_layouts.py   ← provider cache layouts
    suggest.py            ← context suggestions
  memory/
    auto_memory.py / backend.py / consolidator.py
    distillers.py / decay.py / fusion.py
    mid_session.py / procedural.py / progressive.py
    reasoning_bank.py / session_index.py
```

**Key gaps** (what the research says is needed but not yet present):
- No per-turn cache hit/miss telemetry or prefix-stability checker
- Compaction threshold likely too late (95 %+ vs recommended 60 %)
- No decision/rationale extractor that *pins* across compactions
- No temporal fact invalidation (Zep-style `valid_from`/`invalid_at`)
- No repo-map (tree-sitter / AST-based symbol ranking)
- No token compression on tool outputs
- No post-compaction essentials re-injection hook
- No failure-driven compression guideline learning

---

## 7 Phases

---

### Phase 1 — Cache Telemetry & Prefix Stability
**New modules**: `context/cache_telemetry.py`, `context/prefix_stability.py`

What to build:
- `CacheTelemetry` — log per-turn `cache_read_input_tokens`, `cache_creation_input_tokens`, `input_tokens`, `output_tokens`; compute hit ratio; persist to JSON for trend analysis
- `CacheHitRateAlert` — alert (log + optionally surface in status bar) when hit ratio drops below configurable threshold (default 0.70)
- `PrefixStabilityChecker` — scan the outgoing message list for known cache-busters: timestamps/request-IDs above the breakpoint, thinking-block toggling per turn, `cache_control` placed inconsistently
- `StabilityReport` — dataclass: `is_stable: bool`, `busters: list[str]`, `recommended_breakpoint: int`

Why: The Anthropic April 2026 postmortem documented a cache-busting bug (thinking blocks toggled per turn) that caused every turn to be a cache miss for weeks. Even Anthropic's own team missed it without telemetry. Cache reads cost ~10 % of base input; a stable prefix is a ~10× cost reduction.

Research: §5.1 (Anthropic prompt caching mechanics), §11 step 4 (cache-aware request builder), April 2026 postmortem

---

### Phase 2 — Proactive Compaction Controller
**New module**: `context/compaction_controller.py`

What to build:
- `CompactionController` — replaces the 95 % threshold with a configurable trigger (default 60 %). Exposes `should_compact(utilisation: float) → bool`
- `DecisionPreservingPrompt` — compaction prompt template that explicitly instructs the summariser to preserve: (a) decisions made and their rationale, (b) project conventions, (c) access-control / security rules, (d) current task state and next steps. Replaces the Anthropic default ("what to do next" only)
- `CheaperSummariser` — when a `fast_model` slot is configured, use it for the compaction summary (research: "doing your own compaction with Haiku for a Sonnet session can be 5–10× cheaper for the same summary quality" — §11 design choices)
- `EssentialsInjector` — after compaction fires, inject a pinned 10–50-line "Context Essentials" block (rules, decisions, active conventions) before resuming

Why: Community consensus (okhlopkov.com, MindStudio) is that compacting at 95 % means you've already crossed the 70 % degradation threshold. The research shows decision rationale is "the first casualty" of standard compaction prompts.

Research: §13 #3, §6.1 (Claude Code auto-compaction), §7 (okhlopkov.com, MindStudio, Nick Porter)

---

### Phase 3 — Decision & Temporal Fact Memory
**New modules**: `memory/pinned_decisions.py`, `memory/temporal_fact_store.py`

What to build:

**`pinned_decisions.py`**
- `DecisionExtractor` — pattern-based extractor that scans assistant turns for decision markers (`"we decided"`, `"going with"`, `"the convention is"`, `"do not"`, `"always"`, `"never"`, etc.) and emits `PinnedDecision(text, source_turn, confidence, tags)`
- `PinnedDecisionStore` — JSON-backed store; decisions survive compaction because they are in the "core" memory tier, not the message history
- `DecisionRetrieved` — on each turn, pull top-k decisions by tag overlap with the current user message and inject into the stable prefix

**`temporal_fact_store.py`**
- `TemporalFact` — dataclass: `fact: str`, `valid_from: datetime`, `invalid_at: datetime | None`, `superseded_by: str | None`
- `TemporalFactStore` — Zep/Graphiti-style: when a file moves, a function is renamed, or a convention changes, `invalidate(fact_id)` marks `invalid_at = now()` rather than deleting — so you never surface stale advice
- `FactRecall` — returns only facts where `invalid_at is None` (currently valid)

Why: "Every community report agrees [decision/rationale preservation] is where summarisation fails hardest; no automatic technique solves it yet" (§10). The Zep temporal model is specifically designed for facts that change (file moves, refactors) where vector-only memory would surface the stale version.

Research: §3.5 (CoALA memory taxonomy), §4 (Mem0/Zep), §9 (temporal invalidation), §13 #5

---

### Phase 4 — Differential Tool-Output Retention
**New module**: `context/tool_output_policy.py`

What to build:
- `ToolOutputPolicy` — type-based forgetting (drop tool output before prose; tool outputs are reproducible, user intent is not), with three retention levels: `KEEP`, `SUMMARISE`, `DROP`
- `RetentionDecider` — given a tool output and recency, decide its level:
  - Referenced in last 3 turns → `KEEP`
  - Older but type is `bash`/`read` → `SUMMARISE` (keep first 5 + last 5 lines, discard middle)
  - Older + unreferenced + reproducible → `DROP`
- `OutputDeduplicator` — strip ANSI escape codes, collapse repeated stack frame lines (`N more lines`), detect byte-identical file content repeated across turns and replace with `[same as turn N]`
- `ReproducibilityClassifier` — classify tool outputs: `reproducible` (file reads, bash outputs) vs `irreproducible` (user confirmations, external API responses)

Why: AgentDiet (§3.4) categorises the three main waste classes in SWE-bench trajectories; type-based retention is the highest-ROI coarse filter. ACON and Focus Agent both confirm that unreferenced tool outputs are the dominant bloat source.

Research: §9 (forgetting mechanisms), §3.4 (AgentDiet waste taxonomy), §11 step 3, §6.1 ("clears older tool outputs first")

---

### Phase 5 — Repo-Map Code Context
**New module**: `context/repo_map.py`

What to build:
- `SymbolExtractor` — extract function/class definitions and call references from source files:
  - Python: stdlib `ast` module → `(name, kind, file, line)` tuples
  - Other languages: regex-based tags (function/class patterns for JS/TS/Go/Rust/Java)
- `RepoMapRanker` — PageRank-style: build a file × file reference graph; personalise scores toward the files currently mentioned in the conversation; binary-search to fit top symbols into a token budget (default 1024 tokens)
- `FunctionWindowRetriever` — given a symbol name, return only the function/method body (not the whole file), with configurable max-line window
- `RepoMapCache` — keyed by `{file_path: mtime}`; invalidate only changed files. The map is stable between turns → it lands in the cached prefix

Why: "Carrying the whole file across 30 turns is the largest single waste class" (§11). Aider's repo-map is the most mature production pattern and is documented as replaceable with the RepoMapper MCP. The cache-stability of a repo-map (same content between turns) is a direct prompt-cache multiplier.

Research: §6.2 (Aider repo-map), §11 step 2c ("RAG-replace file contents"), Bottom Line #4

---

### Phase 6 — Token Compression Pipeline
**New module**: `context/token_compressor.py`

What to build:
- `ToolOutputCompressor` — rule-based compression of tool output text (no ML model required):
  - Strip ANSI escape sequences (regex)
  - Collapse repeated blank lines → single blank
  - Truncate stack traces: keep first 3 frames + last 3 frames + `[... N frames omitted ...]`
  - Truncate bash outputs longer than `max_lines` (default 50): keep head 20 + tail 20
  - Deduplicate consecutive identical lines (`repeated N times`)
- `CompressionPolicy` — protect-list (never compress): code identifiers `[A-Za-z_]\w*`, diff lines (`+`/`-` prefix), error message lines (`Error:`, `Exception:`), file paths. Compress: prose paragraphs, blank padding, progress-bar animations
- `CompressionGuideline` — ACON-inspired: per-session store of `(content_pattern, kept: bool, reason: str)`; updated when the agent requests content it previously had (miss signal → that pattern should have been kept); used to adjust future compression decisions
- `CompressionStats` — track ratio achieved per turn; alert if a turn expands (compressor made things worse)

Why: LLMLingua-2 achieves 2–5× compression at 1.6–2.9× speedup on tool outputs (§3.1). The rule-based subset described here captures the highest-value patterns (ANSI stripping, stack-trace truncation) without requiring a local ML model — making it compatible with any deployment. The CompressionGuideline is the ACON insight applied without fine-tuning.

Research: §3.1 (LLMLingua-2), §3.4 (ACON arXiv:2510.00615, AgentDiet), §11 step 3, Bottom Line #6

---

### Phase 7 — Context Optimisation Dashboard & Evaluation
**New modules**: `commands/context_opt.py`, `context/context_evaluator.py`

What to build:

**`context_evaluator.py`**
- `ContextOptEvaluator` — 5-axis metric: `cache_hit_ratio`, `tokens_saved_by_compression`, `decisions_preserved` (cross-compaction recall %), `compaction_count`, `estimated_cost_usd`
- `SessionCostTracker` — running cumulative cost with per-section breakdown: stable prefix / recall memory / repo-map / recent turns / tool outputs
- `OptimisationTrendTracker` — JSON persistence of per-session metrics; detect if a change regressed any axis

**`commands/context_opt.py`**  
- `/context-opt status` — Rich table showing: utilisation %, cache hit ratio, compression ratio, active decisions count, compaction count this session, estimated cost saved
- `/context-opt tune compaction=60 cache_alert=0.7 compress_threshold=50` — adjust thresholds live
- `/context-opt decisions` — list pinned decisions with source turn and confidence
- `/context-opt facts` — show temporal facts, flagging any recently invalidated

Why: "Borrow the schema from `alexgreensh/token-optimizer`: log per-turn cache tokens, hit ratio. Alert when hit ratio drops — that's almost always a bug, not a content change." (§11). Evaluation closes the feedback loop so Phase 8 (learning) has data to work with.

Research: §11 ("Telemetry first"), Bottom Line #1–8, alexgreensh/token-optimizer schema

---

## Implementation constraints
- All rule-based: no LLM calls inside any new module (same rule as lyra-research)
- Stdlib + already-present project deps only; no new mandatory dependencies
- `tree-sitter` is optional for Phase 5 (fall back to regex if not installed)
- Each phase: new module(s) + tests → commit → push

## Sequencing rationale
Phases 1 and 2 deliver the largest immediate ROI (cache + compaction threshold) and add zero complexity to later phases. Phase 3 (decision pinning) is a prerequisite for Phase 7 evaluation (`decisions_preserved` metric). Phases 4–6 can run in parallel after Phase 2. Phase 7 depends on all prior phases producing metrics.

---

## Phase summary

| Phase | Module(s) | Core classes | Research grounding |
|-------|-----------|--------------|-------------------|
| 1 | `cache_telemetry.py`, `prefix_stability.py` | CacheTelemetry, PrefixStabilityChecker, CacheHitRateAlert | §5.1, April 2026 postmortem |
| 2 | `compaction_controller.py` | CompactionController, DecisionPreservingPrompt, CheaperSummariser, EssentialsInjector | §13 #3, §6.1, §7 |
| 3 | `pinned_decisions.py`, `temporal_fact_store.py` | DecisionExtractor, PinnedDecisionStore, TemporalFactStore, FactRecall | §3.5, §4, §9, §13 #5 |
| 4 | `tool_output_policy.py` | ToolOutputPolicy, RetentionDecider, OutputDeduplicator, ReproducibilityClassifier | §9, §3.4, §11 step 3 |
| 5 | `repo_map.py` | SymbolExtractor, RepoMapRanker, FunctionWindowRetriever, RepoMapCache | §6.2, §11 step 2c, Bottom Line #4 |
| 6 | `token_compressor.py` | ToolOutputCompressor, CompressionPolicy, CompressionGuideline, CompressionStats | §3.1, §3.4, Bottom Line #6 |
| 7 | `context_opt.py`, `context_evaluator.py` | ContextOptEvaluator, SessionCostTracker, OptimisationTrendTracker + CLI | §11, Bottom Line #1–8 |
