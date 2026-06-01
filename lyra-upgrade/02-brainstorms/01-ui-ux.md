# Brainstorm: UI/UX Enhancements (§4.1)

## Sources Reviewed

### Claude Code UI/UX
- Keybindings (30+ shortcuts, chord support, custom JSON config)
- Statusline (model, tokens, cost, mode indicators)
- Output styles (compact/standard/verbose)
- Fullscreen mode
- Fast mode toggle

### Hermes Agent
- Rich terminal colors (ANSI 256)
- Spinners, tables, syntax highlighting
- Progress bars, bordered boxes

### Comparable Harnesses
- Kilo Code: VS Code/JetBrains/CLI modes, Memory Bank UI
- OpenCode: Desktop + terminal, 75+ providers
- Pi: Sub-1000-token prompt with lazy-loading skills
- Goose: Desktop app with MCP-native UI

### Dynamic Workflows (Claude Code)
- Code-driven workflow specs (workflow.js)
- Fan-out + adversarial verification + convergence
- Resumable long-run UI

---

## Cross-Source Breakthrough Ideas

### Idea 1: Adaptive Context-Aware Theming
**Sources Combined**: 
- Claude Code statusline (dynamic indicators)
- Hermes Agent (rich ANSI colors)
- Pi (lazy-loading pattern)
- Dynamic Workflows (state-driven UI)

**Mechanism**: 
Theme system that adapts not just to user preference but to **current agent state and context budget**:
- **Color intensity** scales with context usage (0-50% = cool colors, 50-80% = warm, 80-100% = hot)
- **Statusline elements** lazy-load based on active features (only show "Swarm: 3 agents" when swarm is active)
- **Syntax highlighting** adjusts based on file type being edited
- **Progress indicators** morph based on operation type (spinner for research, progress bar for file ops, pulse for thinking)

**Why It Beats Individual Sources**:
- Claude Code has static themes; this makes them **context-reactive**
- Hermes has rich colors but no semantic mapping; this **encodes meaning in color**
- Pi's lazy-loading is for prompts; this applies it to **UI elements**
- Dynamic Workflows show state; this **visualizes state through theme**

**Impact × Effort**: 5×3 = HIGH impact, MEDIUM effort

**Failure Modes**:
- Color changes could be distracting if too frequent
- Context-to-color mapping might not be intuitive
- Accessibility concerns (colorblind users need non-color indicators too)

---

### Idea 2: Chord-Based Agent Orchestration
**Sources Combined**:
- Claude Code keybindings (chord support: ctrl+k ctrl+s)
- Dynamic Workflows (fan-out orchestration)
- Kilo Code (Architect/Coder/Debugger/Analyst modes)

**Mechanism**:
Multi-key chord sequences that **spawn and coordinate agents**:
- `ctrl+a ctrl+r` = spawn research agent
- `ctrl+a ctrl+c` = spawn code-review agent
- `ctrl+a ctrl+a` = spawn architect agent
- `ctrl+a ctrl+s` = spawn swarm (3 parallel agents)
- `ctrl+a ctrl+k` = kill all background agents
- `ctrl+a ctrl+l` = list active agents with status

Each chord opens a **mini-TUI overlay** showing agent status, allowing user to:
- Select which agent to focus
- Send messages to specific agents
- Merge agent outputs
- Cancel/restart agents

**Why It Beats Individual Sources**:
- Claude Code chords are for simple actions; this makes them **orchestration primitives**
- Dynamic Workflows require code; this gives **keyboard-driven orchestration**
- Kilo modes are mutually exclusive; this enables **concurrent multi-mode**

**Impact × Effort**: 5×4 = HIGH impact, HIGH effort

**Failure Modes**:
- Chord sequences hard to remember (need visual cheatsheet)
- Overlay TUI adds complexity
- Agent coordination state could get confusing

---

### Idea 3: Progressive Disclosure Statusline
**Sources Combined**:
- Claude Code statusline (fixed elements)
- Pi (lazy-loading skills)
- Dynamic Workflows (resumable state)
- Hermes Agent (rich formatting)

**Mechanism**:
Statusline that **expands/contracts based on relevance and available space**:

**Minimal mode** (narrow terminal, <80 cols):
```
[opus] [45K/200K] [$2.34]
```

**Standard mode** (80-120 cols):
```
[Model: opus-4.7] [Tokens: 45K/200K] [Cost: $2.34] [Thinking: ON]
```

**Expanded mode** (>120 cols, or when relevant):
```
[Model: opus-4.7] [Tokens: 45K/200K (22%)] [Cost: $2.34] [Thinking: ON] [Swarm: 3 agents] [Memory: 12 items] [Skills: 5 loaded]
```

**Contextual expansion**:
- Show "Swarm: N agents" only when swarm is active
- Show "Memory: N items" only after memory operations
- Show "Skills: N loaded" only when skills are in use
- Show "Research: 45/100 sources" during research mode

**Interactive statusline**:
- Click elements to expand details
- Hover for tooltips
- Right-click for quick actions

**Why It Beats Individual Sources**:
- Claude Code statusline is static; this makes it **adaptive**
- Pi lazy-loads prompts; this lazy-loads **UI elements**
- Dynamic Workflows show state; this shows **only relevant state**
- Hermes has rich formatting; this adds **interactivity**

**Impact × Effort**: 4×3 = HIGH impact, MEDIUM effort

**Failure Modes**:
- Statusline jumping around could be jarring
- Click/hover requires mouse (breaks keyboard-only workflow)
- Determining "relevance" requires heuristics that might be wrong

---

## Parked Ideas

### Idea 4: Voice-Driven Theme Switching
Combine voice mode (§4.18) with theming: say "dark mode" or "light mode" to switch themes hands-free during voice sessions.

**Why Parked**: Voice mode is §4.18 flagship; don't overload it with UI concerns in first iteration.

### Idea 5: Collaborative Cursor Sharing
Multi-user Lyra sessions where multiple users see each other's cursors and can collaborate in real-time (like VS Code Live Share).

**Why Parked**: Requires networking layer and conflict resolution; too complex for initial UI/UX work.

### Idea 6: Terminal Recording with Replay
Built-in asciinema-style recording that captures full session and allows replay with speed control.

**Why Parked**: Nice-to-have but not core to UI/UX polish; can be external tool.
