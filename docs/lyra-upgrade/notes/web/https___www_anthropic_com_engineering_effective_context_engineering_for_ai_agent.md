# Effective Context Engineering for AI Agents (Anthropic)

> **Source:** https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
> **Author:** Anthropic Applied AI team (Prithvi Rajasekaran, Ethan Dixon, Carly Ryan, Jeremy Hadfield; contributors Rafi Ayub, Hannah Moran, Cal Rueb, Connor Jennings)
> **Published:** September 29, 2025
> **Filed under:** Lyra Upgrade -- Context Engineering / Memory / Sub-Agent Architecture

---

## Key Technical Claims

1. **Context engineering is the evolution of prompt engineering.** Prompt engineering focuses on writing/structuring instructions; context engineering broadens to curating *every token entering the model during inference* -- system prompts, tools, MCP data, external data, message history. The mindset shift is "thinking in context" -- holistically considering what the model sees at any moment.

2. **Attention Budget and Context Rot.** LLMs have an "attention budget" analogous to human working memory. As token count increases, recall accuracy degrades -- a "performance gradient rather than a hard cliff." Root causes:
   - Transformer self-attention creates n^2 pairwise relationships; these "get stretched thin" at length.
   - Training data is dominated by shorter sequences, so models have fewer specialized long-range parameters.
   - Position encoding interpolation (arXiv 2306.15595) degrades token position understanding at lengths beyond training distribution.

3. **System Prompt "Right Altitude" Principle.** Prompts must avoid two failure modes: too prescriptive (hardcoded brittle if-else logic) vs. too vague (no concrete signals). Optimal altitude is "specific enough to guide behavior, flexible enough to provide strong heuristics."

4. **Just-in-Time Dynamic Retrieval (agentic) vs. Traditional Pre-Inference Embedding Retrieval.** Agents maintain lightweight identifiers (file paths, stored queries, web links) and dynamically load data using tools at runtime. This mirrors human cognition -- we don't memorize entire corpuses; we use external systems on demand.

5. **Progressive Disclosure.** Agents incrementally discover context through exploration. File sizes suggest complexity, naming conventions hint at purpose, timestamps proxy relevance. Agents "assemble understanding layer by layer, maintaining only what is necessary in working memory."

6. **Metadata as Behavioral Signal.** Folder hierarchies, naming conventions, timestamps provide implicit signals. Example: `test_utils.py` in `tests/` implies different purpose than same filename in `src/core_logic/`.

7. **Sub-Agent Architectures for Clean Context Separation.** Specialized sub-agents handle focused tasks with clean context windows. Main agent coordinates at high level; sub-agents return condensed summaries (~1,000-2,000 tokens) after exploring extensively (tens of thousands of tokens). Referenced their prior post "How we built our multi-agent research system" showing "substantial improvement over single-agent systems on complex research tasks."

8. **Compaction as First Lever for Long-Horizon Coherence.** Distilling conversation nearing context limit into a summary, then reinitiating a new window with that summary. Claude Code implementation: pass message history to model which summarizes, preserving architectural decisions, unresolved bugs, implementation details, discarding redundant tool outputs. Combined with the five most recently accessed files.

9. **"Start simple, iterate based on failures"** -- deploy minimal prompts with best models first, then add instructions/examples only from observed failure modes.

10. **Smarter models = less prescriptive engineering needed.** Autonomy scales with model capability.

---

## Architecture / Mechanism Details

### Compaction Mechanics (Claude Code reference implementation)
- Pass message history to model for summarization
- Preserve: architectural decisions, unresolved bugs, implementation details
- Discard: redundant tool outputs, repetitive messages
- Combine compressed summary with N most recently accessed files (N=5 in Claude Code)
- **Tuning advice:** First maximize recall (capture every relevant detail), then improve precision (eliminate superfluous content).
- **"One of the safest lightest touch forms of compaction is tool result clearing"** -- now a feature on the Claude Developer Platform.

### Structured Note-Taking (Agentic Memory)
- Agent writes notes persisted outside the context window, pulled back in later
- Example: Claude Code creating a to-do list, custom agent maintaining a `NOTES.md` file
- **Claude Plays Pokemon case study:**
  - Maintained precise tallies across thousands of game steps (e.g., training Pikachu for 1,234 steps, gaining 8 levels toward target of 10)
  - Developed maps of explored regions, remembered unlocked achievements, maintained combat strategy notes
  - After context resets, agent reads its own notes and continues multi-hour sequences
  - Achieved coherence across summarization steps *without* any prompting about memory structure

### Tool Design Principles (cross-referenced from prior post)
- Tools must be self-contained, robust to error, extremely clear about intended use
- Input parameters: descriptive, unambiguous, play to model strengths
- Minimal functional overlap (analogous to well-designed codebase functions)
- Goal: "minimal viable set of tools" aids both reliability and context maintenance

### Hybrid Strategy Recommendation
- Some data loaded upfront (e.g., CLAUDE.md files dropped naively into context)
- Plus primitives (glob, grep) for runtime exploration
- Bypasses stale indexing and complex syntax tree issues
- Best suited for less dynamic content domains (legal, finance)
- Guiding principle: "do the simplest thing that works"

---

## Numbers & Benchmarks

| Metric | Value |
|---|---|
| Sub-agent condensed summary size | ~1,000-2,000 tokens (from tens of thousands explored) |
| Claude Code "recent files" retained after compaction | 5 most recently accessed files |
| Claude Plays Pokemon: Pikachu training steps | 1,234 steps tracked across resets |
| Claude Plays Pokemon: level tracking | 8 levels gained toward target of 10 |
| n^2 penalty of Transformer self-attention | Quadratic in context length |
| Position encoding paper reference | arXiv 2306.15595 |

**Key performance insight (qualitative):** Multi-agent architectures showed "substantial improvement over single-agent systems on complex research tasks." No hard percentages provided.

---

## Transfer to Lyra

### The One Idea: Just-in-Time Context Retrieval + Progressive Disclosure

Lyra's research pipeline currently pre-loads large context (full paper PDFs, deep prompts, reference docs) upfront into a single agent window. This guarantees context rot: the agent drowns in tokens and attention budget is depleted before the hard reasoning begins.

Instead, Lyra should adopt a **just-in-time retrieval architecture** modeled on the article's pattern:

1. **Lightweight identifiers as the first-class primitive.** The orchestrator/main agent carries only file paths, paper slugs, tool signatures -- not the full content. For example, instead of loading a 50-page PDF into context, the agent holds a reference like `paper:2405.02957.pdf` and retrieves specific sections via tool calls (`grep`, `head`, or a dedicated `read_paper_section` tool).

2. **Progressive disclosure for research papers.** Rather than dumping a paper's full text upfront, the orchestrator first reads the abstract and section headings, decides which sections are relevant, then reads them on demand. This mirrors the "file sizes suggest complexity, naming conventions hint at purpose" pattern.

3. **Sub-agent clean context isolation.** Move Lyra's deep-technical work (e.g., full corpus analysis, benchmark extraction) to sub-agents that return only condensed findings (~1,000-2,000 tokens). The orchestrator never sees the raw exploration. This directly references their multi-agent research system result.

4. **Tool result clearing as lightweight compaction.** After each research phase (e.g., after fetching paper details), clear tool call outputs from context to free attention budget for the next phase -- "one of the safest lightest touch forms of compaction."

### Workstream Route

Primary: **§4.3 -- Context Management** (the just-in-time retrieval architecture, progressive disclosure, and compaction strategy are all context management concerns).

Secondary: **§4.1 -- Memory** (structured note-taking pattern from the article maps directly to Lyra's research memory/knowledge base; the article shows that structured notes persisted outside context window and re-read after resets achieve coherence without explicit memory prompting).

Tertiary: **§4.5 -- Orchestration** (sub-agent architecture for clean context windows maps to Lyra's research pipeline orchestration).

### Implementation Sketch

```
Phase 1: Add lightweight retrieval tools
  - read_paper_abstract(paper_id) -> returns abstract + section headings
  - read_paper_section(paper_id, section) -> returns section text
  - research_find(query) -> runs grep/vector search, returns condensed results
  Impact: Eliminates full-paper pre-loading, saves ~20K+ tokens per paper

Phase 2: Implement compaction at phase boundaries
  - After each research phase (fetch, extract, analyze), clear tool call results
  - Use summarization compaction before starting synthesis phase
  Impact: Prevents context rot across multi-phase research runs

Phase 3: Sub-agent isolation for deep work
  - Move full-corpus analysis, benchmark extraction to dedicated sub-agents
  - Each sub-agent returns a condensed ~1,500 token report
  - Orchestrator never sees raw exploration context
  Impact: Clean separation of concerns, preserves orchestrator attention budget
```
