# Brainstorm: Commands & Interactive Mode (§4.9)

## Sources Reviewed

### Claude Code Commands
- Slash commands (/help, /clear, /config, etc.)
- Command discovery and help
- Command aliases and shortcuts
- Interactive mode with prompts

### Comparable Harnesses
- Kilo Code: --auto flag for full autonomy
- Goose: Recipes for recurring workflows
- Pi: Sub-1000-token prompt with lazy-loading

### Dynamic Workflows
- Code-driven workflow specs
- Interactive vs autonomous modes

---

## Cross-Source Breakthrough Ideas

### Idea 1: Natural Language Command Parser
**Sources Combined**:
- Claude Code commands (slash command system)
- Ask-before-Plan (proactive clarification)
- Dynamic Workflows (autonomous orchestration)
- Goose Recipes (recurring workflows)

**Mechanism**:
**Parse natural language into commands** without requiring slash syntax:
- User types: "show me the last 5 sessions"
- System recognizes intent: `/sessions list --limit 5`
- Confirms: "Running: /sessions list --limit 5" (with option to cancel)
- Executes command

**Intent recognition**:
- "clear screen" → `/clear`
- "save this session" → `/save-session`
- "switch to opus" → `/model opus`
- "run tests" → `/test`
- "start research mode" → `/research`

**Ambiguity handling**:
- "save" → Could be `/save-session` or `/save-file`
- System asks: "Did you mean: 1) Save session 2) Save file?"

**Learning from corrections**:
- User types: "show sessions"
- System suggests: `/sessions list`
- User corrects: "no, /sessions recent"
- System learns: "show sessions" → `/sessions recent`

**Why It Beats Individual Sources**:
- Claude Code requires slash syntax; this accepts **natural language**
- Ask-before-Plan clarifies ambiguous tasks; this clarifies **ambiguous commands**
- Dynamic Workflows are code-driven; this is **language-driven**
- Goose Recipes are predefined; this is **adaptive**

**Impact × Effort**: 5×4 = BREAKTHROUGH impact, HIGH effort

**Failure Modes**:
- Intent recognition could be wrong
- Ambiguity resolution adds friction
- Learning from corrections requires storage
- Natural language is inherently ambiguous

---

### Idea 2: Command Composition Pipelines
**Sources Combined**:
- Claude Code commands (individual commands)
- Unix pipes (command chaining)
- Dynamic Workflows (workflow composition)
- Pipecat (pipeline architecture)

**Mechanism**:
**Chain commands with pipe syntax**:
```
/research "AI agents" | /summarize | /save-file report.md
```

**Data passing**:
- Each command outputs structured data
- Next command receives it as input
- Type checking ensures compatibility

**Examples**:
```
# Research → Summarize → Present
/research "topic" | /summarize --length 500 | /present --format slides

# Search → Filter → Export
/search-code "function.*auth" | /filter --language typescript | /export --format csv

# List → Select → Execute
/sessions list | /select --interactive | /load-session

# Analyze → Visualize → Save
/analyze-codebase | /visualize --type graph | /save-file graph.svg
```

**Interactive pipes**:
```
/research "topic" | /review --interactive | /approve | /publish
                      ↑
                User reviews and approves before publishing
```

**Why It Beats Individual Sources**:
- Claude Code commands are isolated; this enables **composition**
- Unix pipes work on text; this works on **structured data**
- Dynamic Workflows are code-based; this is **command-based**
- Pipecat pipelines are for voice; this is for **commands**

**Impact × Effort**: 5×4 = BREAKTHROUGH impact, HIGH effort

**Failure Modes**:
- Type mismatches between commands
- Error handling in pipelines is complex
- Debugging multi-command pipelines is hard
- Performance overhead from data serialization

---

### Idea 3: Context-Aware Command Suggestions
**Sources Combined**:
- Claude Code commands (static command list)
- Pi (lazy-loading based on context)
- GitHub Copilot (context-aware suggestions)
- Dynamic Workflows (state-driven behavior)

**Mechanism**:
**Suggest commands based on current context**:

**File context**:
- Editing TypeScript file → suggest `/lint`, `/test`, `/format`
- Viewing error log → suggest `/debug`, `/search-error`, `/fix`
- In git repo → suggest `/commit`, `/push`, `/pr`

**Session context**:
- After research → suggest `/summarize`, `/save-report`
- After code changes → suggest `/test`, `/review`, `/commit`
- After error → suggest `/debug`, `/rollback`, `/search-docs`

**Time context**:
- Long-running task → suggest `/status`, `/cancel`, `/background`
- Idle for 5 min → suggest `/save-session`, `/exit`

**User history**:
- Frequently uses `/research` → prioritize in suggestions
- Never uses `/voice` → deprioritize

**Visual presentation**:
```
> _
Suggestions: /test (Ctrl+T) | /commit (Ctrl+C) | /review (Ctrl+R)
```

**Why It Beats Individual Sources**:
- Claude Code shows all commands; this shows **relevant commands**
- Pi lazy-loads skills; this lazy-suggests **commands**
- Copilot suggests code; this suggests **commands**
- Dynamic Workflows adapt to state; this adapts **suggestions to state**

**Impact × Effort**: 4×3 = HIGH impact, MEDIUM effort

**Failure Modes**:
- Suggestions could be wrong or annoying
- Context detection heuristics might fail
- Too many suggestions overwhelm user
- Privacy concerns with usage tracking

---

## Parked Ideas

### Idea 4: Command Macros
Record sequences of commands and replay them as macros (like Vim macros).

**Why Parked**: Goose Recipes already cover this; focus on novel ideas.

### Idea 5: Voice-Activated Commands
Say commands aloud instead of typing (integrate with §4.18 voice mode).

**Why Parked**: Voice mode is §4.18; don't duplicate work.

### Idea 6: Command Undo/Redo
Undo the last command and redo it (like Ctrl+Z for commands).

**Why Parked**: Complex to implement safely; many commands aren't reversible.
