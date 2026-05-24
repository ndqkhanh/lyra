# UI Implementation Research Report

## Executive Summary

This report documents the UI architecture and design patterns discovered in a reference implementation featuring dual rendering surfaces: a terminal-based TUI (Terminal User Interface) built with Ink (React for terminals) and a web-based PWA built with React. The implementation demonstrates sophisticated patterns for real-time streaming, state management, and cross-platform UI consistency.

**Key Architectural Decisions:**
- **Dual-surface rendering**: Terminal (Ink/React) + Web (React/Vite PWA)
- **Shared presentation layer**: Common components and state management
- **Real-time streaming**: WebSocket-based event streaming with optimistic updates
- **Zero-migration model updates**: Tier-based routing instead of hardcoded model names
- **Display density modes**: Minimal/Standard/Debug with runtime toggling

---

## 1. Architecture Overview

### 1.1 Package Structure

The UI is organized into a monorepo with clear separation of concerns:

```
packages/
├── cli/              # Terminal UI (Ink-based REPL)
│   └── src/ui/       # 249 .tsx files, ~9,852 lines
├── web/              # Web UI (React PWA)
│   └── src/          # 17 components
├── presentation/     # Shared UI primitives & state
├── protocol/         # Transport layer contracts
└── server/           # WebSocket/HTTP API
```

**Design Philosophy:**
- CLI and Web share the same protocol and state management
- Presentation layer provides cross-platform primitives
- Protocol defines transport-agnostic contracts

### 1.2 Technology Stack

**Terminal UI (CLI):**
- **Framework**: Ink 6.4.11 (React for terminals)
- **Runtime**: Bun 1.3.11+
- **State Management**: React hooks + custom observability context
- **Styling**: ANSI color codes + gradient-string for animations
- **Key Libraries**:
  - `ink-spinner` - Loading indicators
  - `marked-terminal` - Markdown rendering
  - `katex` - Math rendering (MathML-to-terminal fallback)
  - `cli-highlight` - Syntax highlighting
  - `chalk` - Terminal colors

**Web UI:**
- **Framework**: React 19.2.0
- **Build Tool**: Vite 7.2.4
- **PWA**: vite-plugin-pwa with workbox-window
- **Markdown**: react-markdown 10.1.0 + remark-gfm
- **Syntax Highlighting**: Shiki 4.0.2
- **Styling**: CSS-in-JS with CSS custom properties

**Shared Infrastructure:**
- **Transport**: WebSocket (Fastify) + HTTP fallback
- **Protocol**: Custom JSON-RPC-like event streaming
- **State Sync**: Optimistic updates with server reconciliation

---

## 2. Component Architecture

### 2.1 Terminal UI (Ink) Components

The CLI uses a sophisticated component hierarchy with ~249 .tsx files totaling ~9,852 lines:

**Core Layout Components:**
```typescript
<App>                          // Root container
  <Static>                     // Committed history (scrollback)
    {staticEntries}
  </Static>
  <Box>                        // Live zone (dynamic updates)
    {liveRenderItems}          // Current turn preview
    {queuedMessage}            // Queued user input
    {StreamingIndicator}       // Animated progress
    {TraceWaterfall}           // Debug spans
    {PipelineTimingPanel}      // TTFT breakdown
  </Box>
  <StatusBar />                // Bottom status line
  <InputArea />                // User input with autocomplete
</App>
```

**Key Architectural Patterns:**

1. **Static/Live Split**: Committed messages render once to terminal scrollback via `<Static>`, while streaming content lives in dynamic `<Box>` components. This prevents full-transcript re-renders on every keystroke.

2. **Resume History Boundary**: Pre-resume messages are filtered out of Ink's layout tree entirely, making session restoration O(0) instead of O(n).

3. **Display Policy Pipeline**:
   ```
   ConversationMessage[] 
     → toRenderItems() 
     → applyDisplayPolicy() 
     → RenderItemView
   ```

4. **Indicator State Machine**: Explicit state transitions (idle → thinking → tool_running → composing) driven by ObservabilityContext events, replacing data-derived verb/state logic.
