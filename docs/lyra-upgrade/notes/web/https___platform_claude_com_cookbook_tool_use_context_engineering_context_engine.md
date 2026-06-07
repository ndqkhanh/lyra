# Context Engineering: Memory, Compaction, and Tool Clearing (Claude Cookbook / Anthropic)

**Source:** https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools
**Author:** Isabella He (@isabella-anthropic)
**Published:** March 20, 2026
**Model used:** `claude-sonnet-4-6` (1M-token context window)
**Category:** Tools / Agent Patterns
**Repository:** `anthropics/claude-cookbooks/blob/main/tool_use/context_engineering/context_engineering_tools.ipynb`

---

## Key Technical Claims

1. **Context is a finite resource with diminishing marginal returns.** The term "context rot" describes degraded recall as token count increases. Core discipline: find the smallest set of high-signal tokens that maximize outcome likelihood.

2. **Three first-party API strategies, each with its own primitive and trigger mechanism:**

   | Strategy | API Identifier | Beta Header | Scope |
   |----------|---------------|-------------|-------|
   | Compaction | `compact_20260112` | `compact-2026-01-12` | Whole transcript |
   | Tool-Result Clearing | `clear_tool_uses_20250919` | `context-management-2025-06-27` | Tool results only |
   | Memory | `memory_20250818` | none (standalone) | Cross-session |

3. **Without context management, agents hit hard walls.** On a 200K-token model, a research agent hard-stops at turn 3 (168,242 tokens) despite needing to read 8 documents and write a synthesis.

4. **Clearing invalidates cached prompt prefixes.** This is the critical trade-off: the `clear_at_least` parameter ensures enough tokens are freed to justify the cache invalidation cost.

5. **Memory tool protocol auto-injects system prompt** so the model knows to always view `/memories` before starting work -- the model drives save/load decisions within its tool-use reasoning loop.

6. **Compaction `instructions` completely replaces the default prompt** (does not supplement it). Custom instructions can bias toward preserving quantitative data.

7. **Combined strategies are production-viable.** Claude Code itself uses compaction + two memory systems in production.

---

## Architecture / Mechanism Details

### Compaction (`compact_20260112`)
- Takes the full conversation transcript and asks a model to summarize it.
- Replaces all prior turns (user messages, assistant messages, tool calls, tool results, prior compaction blocks) with a compressed version.
- Whole-transcript operation -- flattens everything.
- **Default trigger:** 150K input tokens (minimum: 50K).
- **Configurable knobs:** `trigger`, `instructions`, `pause_after_compaction`.

### Tool-Result Clearing (`clear_tool_uses_20250919`)
- Walks the message list and replaces old `tool_result` content blocks with `"[cleared to save context]"` placeholders.
- Keeps the `tool_use` record (function name, input) intact.
- Sub-transcript operation -- leaves user messages, assistant reasoning, and tool-call records untouched.
- **Default trigger:** 100K input tokens.
- **Default keep:** 3 most recent tool uses.
- **Additional:** `clear_thinking_20251015` for extended-thinking blocks (must be first in `edits` array if combined).
- Other knobs: `clear_at_least`, `exclude_tools`, `clear_tool_inputs`.

### Memory (`memory_20250818`)
- Client-side tool where the model decides what/when to save.
- API provides: tool protocol + auto-injected system prompt establishing memory-checking behavior.
- Client implements six commands: `view`, `create`, `str_replace`, `insert`, `delete`, `rename`.
- Cross-session persistence example: Session 1 writes research notes to `/memories`, Session 2 reads them instead of re-researching.

### Diagnostic Framework (from the cookbook)
- Dialogue/reasoning accumulation -> Compaction
- Tool result bloat (re-fetchable) -> Clearing
- Cross-session knowledge -> Memory
- Multiple problems -> Combine them

---

## Numbers & Benchmarks

### Test Corpus
- 8 synthetic review documents comparing model organisms for aging research
- Each document ~40K tokens; total corpus ~328,955 tokens
- Task: read 2 batches, take notes, write comparative synthesis

### Baseline (No Context Management)
- **1M-token window:** Peak 335,279 tokens across 5 turns. Context breakdown: 96.3% file-read results, 1.9% tool-call records, 1.7% agent reasoning, 0.1% user prompts.
- **200K-token window:** Hard stop at turn 3 (last successful context: 168,242 tokens). 8 file reads attempted, 2 notes taken.

### Compaction Results
- Trigger: 180,000 tokens (above batch-1's ~165K)
- **Peak:** 169,164 tokens (vs. baseline 335,279)
- **Final after summary:** 5,829 tokens
- **Summary size:** ~2,783 tokens
- **Compaction events:** 1

### Compaction Fidelity
| Category | Result |
|----------|--------|
| High-level facts (3 tested) | 3/3 preserved |
| Obscure specifics (3 tested) | 0/3 preserved |
| Examples lost: appendix heterogeneity I² values, specific effect magnitudes, epigenetic clock acceleration ratios |

### Tool-Result Clearing Results
- Trigger: 30,000 tokens; keep: 4; clear_at_least: 10,000
- **Peak:** 173,137 tokens (vs. baseline 335,279)
- **4 clearing events**, each freeing ~163,000 tokens
- At session end (keep=4): 7 of 8 file reads cleared; only most recent survived
- Demo effect: 3 file reads, clear 2 (keep=1): ~128,740 -> ~43,060 tokens (67% reduction)

### Memory Results
- Session 1: 4 organisms read, memory file written (~2,999 tokens), 8 turns, peak 171,935 tokens
- Session 2: Reads previous session's saved file instead of re-researching

---

## Transfer to Lyra

### One Idea: Layered Context Management Triage

Lyra should adopt Anthropic's diagnostic framework as its §4 context management strategy, implementing **all three primitives** in a layered pipeline:

1. **Clearing** (lowest overhead) for bloat from intermediate tool results -- file reads, search results, git diffs, code listings. These are re-fetchable. Configure `keep` to preserve the last N tool uses with critical content, `clear_at_least` to amortize cache invalidation cost.

2. **Compaction** for periodic summarization of the full conversation history after major phase transitions (e.g., after a planner/architect pass before executor handoff). Preserve quantitative decisions, file paths, and next-step state in the custom `instructions`. Accept that obscure specifics will be lost at the compaction boundary.

3. **Memory** for cross-workstream and cross-session persistence. Lyra's existing memory system should align with the `memory_20250818` six-command protocol, with auto-injected system prompt to load relevant memories on session start.

The specific transfer surface: Lyra's `§4.1.x` should define trigger thresholds (e.g., compact when reasoning turns exceed 150K, clear when tool results exceed 50K) based on Lyra's observed token budgets per phase, rather than Anthropic's defaults. The clearing trade-off (cache invalidation vs. token bloat) is especially relevant for Lyra's multi-agent loops where the same context is incrementally extended across agent handoffs.

### Workstream Route: §4 (Context Management)
- **§4.1.x** -- Configure compaction trigger and custom instructions for Lyra phase transitions
- **§4.1.y** -- Implement tool-result clearing with Lyra-specific `keep` and `clear_at_least` values
- **§4.1.z** -- Align Lyra memory protocol with `memory_20250818` six-command interface
- **Cross-cutting:** Add the diagnostic framework decision tree to Lyra's context management documentation so each agent role (planner, executor, verifier) applies the right strategy
