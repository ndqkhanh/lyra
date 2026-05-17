# Research Pipeline Enhancement Plan

## Goal
Enhance Lyra's `/research` command to show detailed progress information matching Claude Code's transparency, including model names, timing, token usage, expandable output, and parallel sub-agent execution.

## Current State vs Desired State

### Current Output
```
⏺ Decompose  Breaking topic into sub-questions  ░░░░░░░░░░░░░░░░░░░░ 0%
  ⎿  Decomposing: '"transformer architecture"'
  ✔ Decompose (8%)
```

### Desired Output
```
⏺ Decompose [deepseek-reasoner] · 2.3s · ↑1.2K ↓0.8K tokens
  ⎿  Decomposing: '"transformer architecture"' (ctrl+o to expand)
  ⎿  Running 5 parallel agents for sub-questions…
     ├ Agent 1: What is transformer architecture? · 12 tool uses · 5.2K tokens
     ├ Agent 2: How does attention work? · 18 tool uses · 7.1K tokens
     ├ Agent 3: Major transformer variants? · 15 tool uses · 6.3K tokens
     ├ Agent 4: Influential research teams? · 11 tool uses · 4.8K tokens
     └ Agent 5: Applications and limitations? · 14 tool uses · 5.9K tokens
  ✔ Decompose (8%) · Total: 2.3s · 29.3K tokens
```

## Implementation Tasks

### Task 1: Add Model, Time, and Token Tracking ✅

**Files to modify:**
- `packages/lyra-cli/src/lyra_cli/cli/research_pipeline.py`

**Changes:**
1. Track start time for each phase
2. Track token usage (input/output) for each LLM call
3. Display model name in progress indicator
4. Show elapsed time and tokens when phase completes

**Example code:**
```python
import time

class ResearchPhase:
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.start_time = time.time()
        self.tokens_in = 0
        self.tokens_out = 0
    
    def complete(self):
        elapsed = time.time() - self.start_time
        return f"✔ {self.name} [{self.model}] · {elapsed:.1f}s · ↑{self.tokens_in} ↓{self.tokens_out} tokens"
```

### Task 2: Implement Ctrl+O Expand/Collapse ✅

**Files to modify:**
- `packages/lyra-cli/src/lyra_cli/tui_v2/app.py` (add keybinding)
- `packages/lyra-cli/src/lyra_cli/cli/research_pipeline.py` (add collapse markers)

**Changes:**
1. Add `Ctrl+O` keybinding to LyraHarnessApp
2. Track collapsed/expanded state for each output block
3. Show "(ctrl+o to expand)" hint for collapsed content
4. Toggle visibility when Ctrl+O is pressed

**Example code:**
```python
# In app.py
BINDINGS = [
    # ... existing bindings ...
    Binding("ctrl+o", "toggle_expand", "Expand", show=False),
]

async def action_toggle_expand(self) -> None:
    """Toggle expand/collapse for tool output (Ctrl+O)."""
    # Find the most recent collapsible block
    # Toggle its visibility
    # Re-render the chat log
```

### Task 3: Auto-Spawn Sub-Agents for Parallel Research ✅

**Files to modify:**
- `packages/lyra-cli/src/lyra_cli/cli/research_pipeline.py`
- `packages/lyra-cli/src/lyra_cli/commands/research.py`

**Changes:**
1. After decomposition, spawn one agent per sub-question
2. Use the Task tool to create parallel agents
3. Track each agent's progress (tool uses, tokens)
4. Display tree-style progress for all agents
5. Aggregate results when all agents complete

**Example code:**
```python
async def research_with_agents(topic: str, sub_questions: list[str]):
    """Research using parallel agents for each sub-question."""
    
    # Spawn agents in parallel
    agents = []
    for i, question in enumerate(sub_questions):
        agent = spawn_agent(
            name=f"research-{i+1}",
            task=f"Research: {question}",
            tools=["web_search", "scrape", "extract"],
        )
        agents.append(agent)
    
    # Track progress
    while any(agent.is_running() for agent in agents):
        display_agent_tree(agents)
        await asyncio.sleep(0.5)
    
    # Aggregate results
    return synthesize_results([agent.result for agent in agents])
```

### Task 4: Enhanced Progress Display Format ✅

**Format specification:**

```
Phase Header:
⏺ {phase_name} [{model}] · {elapsed}s · ↑{tokens_in} ↓{tokens_out} tokens

Sub-items (collapsed):
  ⎿  {description}… (ctrl+o to expand)

Sub-items (expanded):
  ⎿  {description}
     {detailed_output_line_1}
     {detailed_output_line_2}
     ...

Agent tree:
  ⎿  Running {n} parallel agents…
     ├ Agent {i}: {task} · {tool_uses} tool uses · {tokens} tokens
     │ ⎿  Current: {current_operation}
     ├ Agent {i+1}: {task} · {tool_uses} tool uses · {tokens} tokens
     │ ⎿  Current: {current_operation}
     └ Agent {n}: {task} · {tool_uses} tool uses · {tokens} tokens
       ⎿  Done

Phase completion:
  ✔ {phase_name} ({progress}%) · Total: {elapsed}s · {total_tokens} tokens
```

## Implementation Priority

1. **Phase 1** (2-3 hours): Add model, time, and token tracking
   - Easiest to implement
   - High visibility impact
   - Foundation for other features

2. **Phase 2** (3-4 hours): Auto-spawn sub-agents
   - Most valuable feature
   - Enables true parallel research
   - Matches Claude Code's agent spawning

3. **Phase 3** (2-3 hours): Implement Ctrl+O expand/collapse
   - Improves readability
   - Reduces clutter
   - Professional polish

4. **Phase 4** (1-2 hours): Enhanced progress display format
   - Visual polish
   - Consistent formatting
   - Tree-style agent display

**Total Estimated Time:** 8-12 hours

## Testing Plan

### Manual Tests

```bash
# Test 1: Basic research with progress tracking
lyra --tui
> /research "Python async patterns"
# Verify: Model name, time, tokens shown for each phase

# Test 2: Parallel agent spawning
lyra --tui
> /research "transformer architecture"
# Verify: Multiple agents spawn, tree display shows progress

# Test 3: Ctrl+O expand/collapse
lyra --tui
> /research "machine learning"
# Verify: Press Ctrl+O to expand/collapse output

# Test 4: Long research with many sub-questions
lyra --tui
> /research "comprehensive guide to neural networks"
# Verify: All features work together
```

### Automated Tests

```python
# Test token tracking
def test_research_phase_tracks_tokens():
    phase = ResearchPhase("Decompose", "deepseek-reasoner")
    phase.tokens_in = 1200
    phase.tokens_out = 800
    result = phase.complete()
    assert "↑1200" in result
    assert "↓800" in result

# Test agent spawning
def test_research_spawns_parallel_agents():
    sub_questions = ["Q1", "Q2", "Q3"]
    agents = spawn_research_agents(sub_questions)
    assert len(agents) == 3
    assert all(agent.is_running() for agent in agents)
```

## Success Criteria

✅ Each research phase shows model name, elapsed time, and token usage  
✅ Sub-agents spawn automatically for each sub-question  
✅ Tree-style progress display shows all agents  
✅ Ctrl+O expands/collapses detailed output  
✅ Total time and tokens shown at phase completion  
✅ All features work in TUI v2 mode  
✅ No regressions in existing functionality  

## Notes

- All enhancements are additive - no breaking changes
- Features are opt-in via TUI v2 mode (`lyra --tui`)
- Token tracking requires LLM response metadata
- Agent spawning uses existing Task tool infrastructure
- Ctrl+O follows Claude Code's UX pattern

## Next Steps

1. Implement Phase 1 (tracking) first - foundation for everything else
2. Test with real research queries
3. Iterate based on user feedback
4. Document new features in README
