# Lyra UX Implementation Plan - Ink/React TypeScript

**Date**: 2026-05-24  
**Status**: Python TUI removed ✅ | Ink UI is primary ✅ | Ready for UX enhancements

---

## ✅ COMPLETED

### 1. Architecture Cleanup
- ✅ Removed all Python prompt_toolkit TUI code (`pt_tui/`, `tui/`)
- ✅ Updated main.py to launch Ink UI directly
- ✅ Ink/React UI is now the only UI

### 2. Already Implemented in Ink UI
- ✅ Terminal resize handling (index.tsx lines 60-64)
- ✅ Responsive separator (dynamically adjusts to terminal width)
- ✅ Global keyboard shortcuts (Ctrl+C, Ctrl+\)
- ✅ History navigation (↑/↓ arrows)
- ✅ Command autocomplete (/ commands with suggestions)
- ✅ Color enhancements (50+ semantic colors, Dracula theme)
- ✅ Syntax highlighting (SyntaxHighlight.tsx)
- ✅ Markdown rendering (Markdown.tsx)
- ✅ Streaming indicators (StreamingIndicator.tsx)

---

## 🚧 TO IMPLEMENT

### Priority 1: Enhanced Welcome Banner (1-2 days)

**Current**: Basic header in Header.tsx  
**Target**: Claude Code style with rounded borders

**Features needed**:
```
╭─── Lyra Code v1.0.0 ──────────────────────────────────────╮
│                                                             │
│                      Welcome back!                          │
│                        ╦  ╦ ╦╦═╗╔═╗                         │
│                        ║  ╚╦╝╠╦╝╠═╣                         │
│                        ╩═╝ ╩ ╩╚═╩ ╩                         │
│  Opus 4.7 (1M context) · Deep Research Mode                │
│  ~/current/directory                                        │
╰─────────────────────────────────────────────────────────────╯
```

**Responsive breakpoints**:
- Wide (>120 cols): Two-column with tips sidebar
- Standard (80-120 cols): Single column
- Narrow (<80 cols): Compact version

**Files to modify**:
- `packages/ui-terminal/src/components/Header.tsx`

---

### Priority 2: File Mentions (@ references) (2-3 days)

**Current**: Basic input in InputArea.tsx  
**Target**: File/folder autocomplete with @ prefix

**Features needed**:
- Detect `@` prefix in input
- Show file/folder suggestions from current directory
- Fuzzy matching for file names
- Visual indicators for files vs folders
- Tab/Enter to accept suggestion
- Support for relative paths (`@src/`, `@../`)

**Implementation**:
```typescript
// Add to InputArea.tsx
const [fileSuggestions, setFileSuggestions] = useState<string[]>([])

useEffect(() => {
  if (input.includes('@')) {
    const lastAtIndex = input.lastIndexOf('@')
    const query = input.slice(lastAtIndex + 1)
    
    // Get file suggestions from filesystem
    const suggestions = getFileSuggestions(query)
    setFileSuggestions(suggestions)
  }
}, [input])
```

**Files to modify**:
- `packages/ui-terminal/src/components/InputArea.tsx`
- Create `packages/ui-terminal/src/utils/fileCompletion.ts`

---

### Priority 3: Enhanced Status Bar (1 day)

**Current**: Basic status bar in StatusBar.tsx  
**Target**: Dynamic updates with real-time info

**Features needed**:
- Real-time context percentage (5% → 47% → 89%)
- Token counters (↑ 9.7k input, ↓ 12.3k output)
- Permission mode cycling (ask → bypass → auto)
- Cost tracking (optional, $0.23)
- Keyboard shortcut hints

**Current status bar**:
```
⏵⏵ bypass permissions on · (shift+tab to cycle) · esc to interrupt · ↓ to manage
```

**Enhanced status bar**:
```
⏵⏵ bypass permissions on · shift+tab to cycle · esc to interrupt     47% context · ↑ 9.7k · ↓ 12.3k · $0.23
```

**Files to modify**:
- `packages/ui-terminal/src/components/StatusBar.tsx`
- Add state management for tokens/cost in ui-core

---

### Priority 4: Progress Indicators (1 day)

**Current**: Basic streaming indicator  
**Target**: Rich progress with time/tokens/phase

**Features needed**:
- Time elapsed (5m 24s)
- Token counters during streaming
- Phase indicators (thinking → tools → response)
- Agent tree visualization (collapsed/expanded)

**Example output**:
```
⏺ Thinking... (2.3s)
⏺ Running tool: read_file (0.8s)
⏺ Streaming response... (↑ 234 · ↓ 1.2k · 5.7s)
✳ Completed (8.2s · ↑ 9.7k · ↓ 12.3k)
```

**Files to modify**:
- `packages/ui-terminal/src/components/StreamingIndicator.tsx`
- Add time tracking to ui-core state

---

### Priority 5: Agent Tree Visualization (2-3 days)

**Current**: Not implemented  
**Target**: Hierarchical agent display with expand/collapse

**Features needed**:
- Collapsed state: `⏺ Running 4 agents... (ctrl+o to expand)`
- Expanded state: Tree with ├│└ characters
- Show tool uses and token counts per agent
- Interactive expansion with Ctrl+O

**Example expanded tree**:
```
⏺ Agent Tree (4 agents)
  ├─ Planner (completed)
  │  ├─ 3 tool uses
  │  └─ 2.1k tokens
  ├─ Researcher (running)
  │  ├─ 7 tool uses
  │  └─ 5.3k tokens
  ├─ Executor (pending)
  └─ Reviewer (pending)
```

**Files to create**:
- `packages/ui-terminal/src/components/AgentTree.tsx`
- Add agent tracking to ui-core state

---

### Priority 6: Additional Keyboard Shortcuts (1 day)

**Current**: Ctrl+C, Ctrl+\  
**Target**: Full shortcut suite

**Shortcuts to add**:
- `Ctrl+O` - Toggle agent tree expansion
- `Shift+Tab` - Cycle permission modes
- `Esc` - Interrupt streaming
- `Ctrl+L` - Clear screen
- `Ctrl+R` - Search history
- `Ctrl+K` - Clear input

**Files to modify**:
- `packages/ui-terminal/src/index.tsx` (global shortcuts)
- `packages/ui-terminal/src/components/InputArea.tsx` (input shortcuts)

---

### Priority 7: Command Palette Enhancements (1 day)

**Current**: Basic / command autocomplete  
**Target**: Rich command palette with descriptions

**Commands to add**:
- `/help` - Show all commands
- `/plan` - Create implementation plan
- `/review` - Code review
- `/test-coverage` - Check test coverage
- `/clear` - Clear screen
- `/exit` - Exit Lyra
- `/init` - Initialize project
- `/release-notes` - Show what's new

**Enhanced autocomplete**:
```
Suggestions (↑/↓ to navigate, Tab to select):
  ❯ /plan          Create implementation plan
    /review        Code review current changes
    /test-coverage Check test coverage
```

**Files to modify**:
- `packages/ui-terminal/src/components/InputArea.tsx`
- Create `packages/ui-terminal/src/commands/registry.ts`

---

## 📁 File Structure

```
projects/lyra/packages/
├── ui-core/                    # Shared state and types
│   ├── src/
│   │   ├── store/             # Zustand store
│   │   ├── theme/             # Colors and symbols
│   │   └── types/             # TypeScript types
│   └── package.json
│
├── ui-transport/               # Communication layer
│   ├── src/
│   │   ├── local.ts           # Local transport
│   │   └── websocket.ts       # WebSocket transport
│   └── package.json
│
└── ui-terminal/                # Main Ink UI
    ├── src/
    │   ├── index.tsx          # Entry point ✅
    │   ├── App.tsx            # Main app component
    │   ├── components/
    │   │   ├── Header.tsx              # ⏳ Needs enhancement
    │   │   ├── StatusBar.tsx           # ⏳ Needs enhancement
    │   │   ├── InputArea.tsx           # ⏳ Needs @ mentions
    │   │   ├── StreamingIndicator.tsx  # ⏳ Needs time/tokens
    │   │   ├── ConversationView.tsx    # ✅ Complete
    │   │   ├── Markdown.tsx            # ✅ Complete
    │   │   ├── SyntaxHighlight.tsx     # ✅ Complete
    │   │   ├── Collapsible.tsx         # ✅ Complete
    │   │   └── AgentTree.tsx           # ❌ To create
    │   ├── hooks/
    │   │   ├── useHistory.ts           # ✅ Complete
    │   │   └── useTerminalSize.ts      # ❌ To create
    │   ├── utils/
    │   │   └── fileCompletion.ts       # ❌ To create
    │   └── commands/
    │       └── registry.ts             # ❌ To create
    └── package.json
```

---

## 🧪 Testing Strategy

### Unit Tests
```bash
cd packages/ui-terminal
npm test
```

Test files to create:
- `src/components/__tests__/Header.test.tsx`
- `src/components/__tests__/InputArea.test.tsx`
- `src/components/__tests__/AgentTree.test.tsx`
- `src/utils/__tests__/fileCompletion.test.ts`

### Integration Tests
- Full app flow with ink-testing-library
- Keyboard shortcut tests
- File completion tests

### Manual Testing
- Test on iTerm2, Terminal.app, Alacritty, Kitty
- Test with tmux and screen
- Test different terminal widths (narrow/standard/wide)
- Test with different color schemes

---

## 📊 Implementation Timeline

| Week | Priority | Tasks | Effort |
|------|----------|-------|--------|
| 1 | P1 | Welcome banner, Status bar | 2-3 days |
| 2 | P2-P3 | File mentions, Progress indicators | 3-4 days |
| 3 | P4-P5 | Agent tree, Keyboard shortcuts | 3-4 days |
| 4 | P6-P7 | Command palette, Polish | 2-3 days |

**Total**: 10-14 days

---

## 🎯 Success Metrics

- ✅ Python TUI completely removed
- ✅ Ink UI launches successfully
- ⏳ All 7 priorities implemented
- ⏳ Tests passing (>80% coverage)
- ⏳ Manual testing complete
- ⏳ Documentation updated

---

## 🚀 Next Steps

1. **Immediate**: Implement enhanced welcome banner
2. **This week**: Add file mentions (@ references)
3. **Next week**: Implement agent tree visualization
4. **Week 3-4**: Polish and testing

---

**Last Updated**: 2026-05-24  
**Status**: Ready to implement UX enhancements in Ink/React UI
