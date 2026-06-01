# Hermes Agent - Comprehensive Analysis

**Analysis Date:** 2026-05-27  
**Repository:** https://github.com/NousResearch/hermes-agent  
**Version Analyzed:** 0.14.0  
**Analyst:** Research Agent

---

## Executive Summary

Hermes Agent is a production-grade, self-improving AI agent built by Nous Research. It features a sophisticated TUI built with React + Ink, a Python backend with extensive tool support, and a unique learning loop that creates and improves skills from experience. The project demonstrates exceptional engineering quality with 188 TypeScript/TSX files in the TUI alone, comprehensive testing, and multi-platform support (Linux, macOS, Windows, Termux).

**Key Strengths:**
- World-class TUI implementation with custom Ink extensions
- Sophisticated theme system with light/dark mode auto-detection
- Advanced streaming text handling with virtual scrolling
- Production-ready state management using nanostores
- Comprehensive input handling with fast-echo optimization
- Multi-platform gateway architecture (Telegram, Discord, Slack, etc.)

---

## 1. Architecture Analysis

### 1.1 Overall Project Structure

```
hermes-agent/
├── ui-tui/                    # React + Ink TUI (188 TS/TSX files)
│   ├── src/
│   │   ├── app/              # Core application logic
│   │   ├── components/       # UI components
│   │   ├── hooks/            # React hooks
│   │   ├── lib/              # Utilities
│   │   └── packages/
│   │       └── hermes-ink/   # Custom Ink extensions
├── hermes_cli/               # Python CLI commands
├── agent/                    # Core agent logic
├── tools/                    # Tool implementations
├── gateway/                  # Messaging gateway
├── tui_gateway/             # TUI-gateway bridge
├── providers/               # LLM provider adapters
├── plugins/                 # Plugin system
└── skills/                  # Skill library
```

### 1.2 Core Components

**TUI Layer (TypeScript/React):**
- **Entry Point:** `ui-tui/src/entry.tsx` - Bootstraps the Ink app
- **Main App:** `ui-tui/src/app.tsx` - Root component
- **State Management:** nanostores for reactive state
- **Gateway Client:** WebSocket/RPC bridge to Python backend

**Backend Layer (Python):**
- **CLI Entry:** `hermes_cli/main.py` - Fire-based CLI
- **Agent Core:** `agent/` - Chat completion, tool calling
- **Gateway:** `gateway/` - Multi-platform messaging
- **Tools:** `tools/` - 80+ tool implementations

### 1.3 Design Patterns

1. **Gateway Pattern:** TUI communicates with Python backend via RPC
2. **Store Pattern:** Centralized state with nanostores (`$uiState`, `$turnState`, `$overlayState`)
3. **Virtual Scrolling:** Efficient rendering of large transcripts
4. **Fast Echo:** Direct stdout writes for low-latency typing
5. **Lazy Loading:** Provider-specific deps loaded on demand
6. **Hook System:** Pre/post tool execution hooks

---

## 2. TUI Implementation Deep Dive

### 2.1 UI Framework

**Technology Stack:**
- **Framework:** Ink 6.8.0 (React for CLIs)
- **React:** 19.2.4 (latest)
- **State Management:** nanostores 1.2.0 + @nanostores/react
- **Build:** esbuild for fast compilation
- **TypeScript:** 5.7.0 with strict mode

**Custom Ink Extensions (@hermes/ink):**
Hermes maintains a forked/extended version of Ink with custom components:
- `ScrollBox` - Virtual scrolling container
- `AlternateScreen` - Full-screen mode
- `NoSelect` - Disable text selection
- `useDeclaredCursor` - Custom cursor positioning
- `useCursorAdvance` - Direct cursor manipulation
- `useTerminalFocus` - Focus detection

### 2.2 Component Architecture

**Key Components:**

1. **AppLayout** (`components/appLayout.tsx`)
   - Main layout container
   - Three panes: Transcript, Prompt, Composer
   - Conditional rendering based on overlay state
   - Mouse tracking integration

2. **TranscriptPane**
   - Virtual scrolling with `ScrollBox`
   - Message rendering with `MessageLine`
   - Sticky scroll behavior
   - Selection support

3. **ComposerPane**
   - Multi-line input with `TextInput`
   - Prompt prefix rendering
   - Queued messages display
   - Status bar integration

4. **TextInput** (`components/textInput.tsx`)
   - 1,313 lines of sophisticated input handling
   - Fast-echo optimization for low-latency typing
   - Grapheme-aware cursor movement
   - Mouse selection support
   - Undo/redo stack
   - Clipboard integration

5. **StreamingAssistant** (`components/streamingAssistant.tsx`)
   - Real-time streaming text display
   - Tool execution visualization
   - Grouped message segments

### 2.3 Theme System Implementation

**Theme Structure** (`theme.ts` - 590 lines):

```typescript
interface ThemeColors {
  primary: string
  accent: string
  border: string
  text: string
  muted: string
  completionBg: string
  completionCurrentBg: string
  // ... 28 total color properties
}

interface ThemeBrand {
  name: string
  icon: string
  prompt: string
  welcome: string
  goodbye: string
  tool: string
  helpHeader: string
}
```

**Key Features:**

1. **Auto Light/Dark Detection:**
   - Checks `HERMES_TUI_LIGHT` env var
   - Checks `HERMES_TUI_THEME` env var
   - Checks `HERMES_TUI_BACKGROUND` hex value
   - Checks `COLORFGBG` terminal hint
   - Checks `TERM_PROGRAM` for known terminals
   - Falls back to dark theme

2. **ANSI Color Normalization:**
   - Converts hex colors to ANSI 256-color palette
   - Ensures readability on light terminals
   - Special handling for Apple Terminal
   - Luminance-based color selection

3. **Color Math:**
   - `parseHex()` - Parse hex colors
   - `mix()` - Blend two colors
   - `relativeLuminance()` - Calculate brightness
   - `rgbToHsl()` - Color space conversion
   - `bestReadableAnsiColor()` - Find readable ANSI equivalent

4. **Skinning Support:**
   - `fromSkin()` function for custom themes
   - Fallback to default colors
   - Banner customization
   - Brand customization

---

