# Hermes Agent TUI Architecture Analysis

**Date:** 2026-05-27  
**Repository:** hermes-agent/ui-tui  
**Purpose:** Deep analysis for Lyra TUI upgrade

---

## Executive Summary

Hermes Agent represents a production-grade TUI implementation with sophisticated patterns that Lyra should adopt. Key strengths:

1. **Custom Ink Fork (@hermes/ink)** - Full control over rendering, mouse tracking, and performance
2. **Nanostores State Management** - Lightweight, reactive, with computed stores
3. **Virtual Scrolling** - Efficient rendering of large transcripts
4. **Fast Echo Input** - Direct stdout bypass for ASCII typing (sub-frame latency)
5. **Gateway Architecture** - Clean separation between TUI and Python backend
6. **Theme System** - Comprehensive with light/dark detection and ANSI normalization

---

## 1. Architecture Overview

### Directory Structure

```
ui-tui/
├── src/
│   ├── app/                    # Core application logic
│   │   ├── uiStore.ts         # Global UI state (nanostores)
│   │   ├── turnStore.ts       # Turn-specific state
│   │   ├── overlayStore.ts    # Modal/overlay state
│   │   ├── scroll.ts          # Scroll with selection
│   │   ├── turnController.ts  # Turn lifecycle
│   │   └── useMainApp.ts      # Main app hook (1040 lines!)
│   ├── components/            # React/Ink components
│   │   ├── appLayout.tsx      # Main layout
│   │   ├── textInput.tsx      # Custom input (1313 lines)
│   │   ├── markdown.tsx       # MD renderer (1120 lines)
│   │   └── streamingAssistant.tsx
│   ├── lib/                   # Utilities
│   ├── theme.ts              # Theme system (590 lines)
│   ├── gatewayClient.ts      # Backend communication (731 lines)
│   └── app.tsx               # Root component
├── packages/
│   └── hermes-ink/           # Custom Ink fork
│       └── src/
│           ├── ink/          # Core Ink modifications
│           └── hooks/        # Custom hooks
└── package.json
```

### Key Dependencies

```json
{
  "dependencies": {
    "@hermes/ink": "file:./packages/hermes-ink",  // Custom fork
    "@nanostores/react": "^1.1.0",                 // State management
    "ink": "^6.8.0",                               // Base (re-exported)
    "nanostores": "^1.2.0",                        // Core stores
    "react": "^19.2.4"                             // Latest React
  }
}
```

---

## 2. State Management (Nanostores)

### Why Nanostores Over Zustand/Redux

**Hermes chose nanostores for:**
- **Tiny bundle size** (334 bytes vs 3.5KB for Zustand)
- **Framework agnostic** (works outside React)
- **Computed stores** (derived state without selectors)
- **No Provider needed** (module-level stores)
- **Atomic updates** (fine-grained reactivity)

### Store Architecture

**Three main stores:**

1. **`$uiState`** - Global UI state (theme, busy, session info)
2. **`$turnState`** - Turn-specific (streaming, tools, todos)
3. **`$overlayState`** - Modals (approval, sudo, clarify)

### uiStore.ts Pattern

```typescript
// /ui-tui/src/app/uiStore.ts
import { atom, computed } from 'nanostores'

const buildUiState = (): UiState => ({
  bgTasks: new Set(),
  busy: false,
  theme: DEFAULT_THEME,
  sid: null,
  status: 'summoning hermes…',
  // ... 20+ fields
})

export const $uiState = atom<UiState>(buildUiState())

// Computed stores (derived state)
export const $uiTheme = computed($uiState, state => state.theme)
export const $uiSessionId = computed($uiState, state => state.sid)

// Patch helper (immutable updates)
export const patchUiState = (next: Partial<UiState>) =>
  $uiState.set({ ...$uiState.get(), ...next })
```

**Usage in components:**

```typescript
import { useStore } from '@nanostores/react'
import { $uiState } from './uiStore'

function MyComponent() {
  const ui = useStore($uiState)  // Auto-subscribes
  return <Text>{ui.status}</Text>
}
```

### turnStore.ts - Selector Pattern

```typescript
// /ui-tui/src/app/turnStore.ts
import { useSyncExternalStore } from 'react'

export const $turnState = atom<TurnState>(buildTurnState())

const subscribeTurn = (cb: () => void) => $turnState.listen(() => cb())

// Custom selector hook (fine-grained subscriptions)
export const useTurnSelector = <T>(selector: (state: TurnState) => T): T =>
  useSyncExternalStore(
    subscribeTurn,
    () => selector($turnState.get()),
    () => selector($turnState.get())
  )

// Usage: Only re-renders when streaming changes
const streaming = useTurnSelector(state => state.streaming)
```

**Key insight:** `useTurnSelector` prevents unnecessary re-renders by subscribing only to selected fields.

---

## 3. Theme System

### Comprehensive Color Palette

```typescript
// /ui-tui/src/theme.ts (590 lines)
export interface ThemeColors {
  primary: string
  accent: string
  border: string
  text: string
  muted: string
  
  // Completion menu
  completionBg: string
  completionCurrentBg: string
  
  // Status indicators
  ok: string
  error: string
  warn: string
  
  // Diff colors
  diffAdded: string
  diffRemoved: string
  diffAddedWord: string
  diffRemovedWord: string
  
  // Shell prompt
  shellDollar: string
}
```

### Light/Dark Detection

```typescript
// Ordered signal priority:
// 1. HERMES_TUI_LIGHT (1/true/yes → light, 0/false/no → dark)
// 2. HERMES_TUI_THEME (light/dark)
// 3. HERMES_TUI_BACKGROUND (hex → luminance check)
// 4. COLORFGBG (7 or 15 → light)
// 5. TERM_PROGRAM (Apple_Terminal → light default)

export function detectLightMode(env = process.env): boolean {
  const lightFlag = (env.HERMES_TUI_LIGHT ?? '').trim().toLowerCase()
  if (/^(1|true|yes|on)$/.test(lightFlag)) return true
  if (/^(0|false|no|off)$/.test(lightFlag)) return false
  
  const themeFlag = (env.HERMES_TUI_THEME ?? '').trim().toLowerCase()
  if (themeFlag === 'light') return true
  if (themeFlag === 'dark') return false
  
  // ... more checks
  return false  // Default to dark
}
```

### ANSI Normalization for Light Terminals

**Problem:** Light themes on 8-bit terminals (Apple Terminal) render bright colors as invisible.

**Solution:** Convert hex colors to ANSI 256 palette with luminance constraints.

```typescript
function normalizeAnsiForeground(color: string): string {
  const rgb = parseHex(color)
  const ansi = bestReadableAnsiColor(rgb[0], rgb[1], rgb[2])
  return `ansi256(${ansi})`
}

// Applied to light theme on Apple Terminal without truecolor
export function normalizeThemeForAnsiLightTerminal(theme: Theme): Theme {
  if (!shouldNormalize()) return theme
  
  const color = { ...theme.color }
  for (const key of ANSI_NORMALIZED_FOREGROUNDS) {
    color[key] = normalizeAnsiForeground(color[key])
  }
  return { ...theme, color }
}
```

---

## 4. Custom TextInput Component

**File:** `/ui-tui/src/components/textInput.tsx` (1313 lines)

### Fast Echo Optimization

**Problem:** Ink's render loop adds 16ms latency per keystroke.

**Solution:** Direct stdout bypass for ASCII-only typing.

```typescript
// Fast append path
if (canFastAppend(v, c, text)) {
  stdout!.write(text)
  noteCursorAdvance(text.length)  // Sync Ink's cursor model
  commit(v, c, true, false, false, lineWidth + stringWidth(text))
  return
}

// Fast backspace path
if (canFastBackspace(v, c)) {
  stdout!.write('\b \b')
  noteCursorAdvance(-1)
  commit(v, c, true, false, false, lineWidth - 1)
  return
}
```

**Safety checks:**

```typescript
export function canFastAppendShape(
  current: string,
  cursor: number,
  text: string,
  columns: number,
  currentLineWidth: number
): boolean {
  if (cursor !== current.length) return false  // Not at end
  if (current.includes('\n')) return false     // Multi-line
  if (!ASCII_PRINTABLE_RE.test(text)) return false  // Non-ASCII
  return currentLineWidth + text.length < columns   // No wrap
}
```

**Why ASCII-only?** IME compositions, Vietnamese Telex, combining marks would desync cursor.

### Grapheme-Aware Cursor Movement

```typescript
// Uses Intl.Segmenter for proper grapheme boundaries
const seg = () => (_seg ??= new Intl.Segmenter(undefined, { granularity: 'grapheme' }))

function graphemeStops(s: string) {
  const stops = [0]
  for (const { index } of seg().segment(s)) {
    if (index > 0) stops.push(index)
  }
  if (stops.at(-1) !== s.length) stops.push(s.length)
  return stops
}

function nextPos(s: string, p: number) {
  const pos = snapPos(s, p)
  for (const stop of graphemeStops(s)) {
    if (stop > pos) return stop
  }
  return s.length
}
```

**Handles:** Emoji (👨‍👩‍👧‍👦), combining marks (é = e + ́), CJK characters.

### Mouse Selection

```typescript
const startMouseSelection = (offset: number) => {
  const c = snapPos(vRef.current, offset)
  mouseAnchorRef.current = c
  selRef.current = { end: c, start: c }
  setCur(c)
}

const dragMouseSelection = (offset: number) => {
  if (mouseAnchorRef.current === null) return
  const c = snapPos(vRef.current, offset)
  const range = { end: c, start: mouseAnchorRef.current }
  selRef.current = range
  setSel(range.start === range.end ? null : range)
}

// macOS: Copy-on-select (iTerm style)
const endMouseSelection = () => {
  const normalized = selRange()
  if (isMac && normalized) {
    void writeClipboardText(vRef.current.slice(normalized.start, normalized.end))
  }
}
```

---

## 5. Gateway Architecture

**File:** `/ui-tui/src/gatewayClient.ts` (731 lines)

### Dual Transport: Spawn vs Attach

```typescript
class GatewayClient extends EventEmitter {
  private proc: ChildProcess | null = null  // Spawned Python
  private ws: WebSocket | null = null       // Attached WebSocket
  
  start() {
    const attachUrl = resolveGatewayAttachUrl()
    
    if (attachUrl) {
      this.startAttachedGateway(attachUrl)  // WebSocket mode
    } else {
      this.startSpawnedGateway(root)        // Spawn Python
    }
  }
}
```

**Spawned mode:**
- Spawns `python -m tui_gateway.entry`
- JSON-RPC over stdin/stdout
- stderr captured for logs

**Attached mode:**
- Connects to existing WebSocket server
- Binary frames supported (tool deltas, reasoning streams)
- Sidecar mirror for debugging

### Event-Driven Communication

```typescript
// Gateway publishes events
private publish(ev: GatewayEvent) {
  if (ev.type === 'gateway.ready') {
    this.ready = true
    clearTimeout(this.readyTimer)
  }
  
  if (this.subscribed) {
    this.emit('event', ev)
  } else {
    this.bufferedEvents.push(ev)  // Buffer until UI subscribes
  }
}

// RPC with timeout
request<T>(method: string, params = {}): Promise<T> {
  const id = `r${++this.reqId}`
  
  return new Promise<T>((resolve, reject) => {
    const timeout = setTimeout(this.onTimeout, REQUEST_TIMEOUT_MS, id)
    this.pending.set(id, { id, method, resolve, reject, timeout })
    
    this.proc!.stdin!.write(JSON.stringify({ id, jsonrpc: '2.0', method, params }) + '\n')
  })
}
```

**Circular buffer for logs:**

```typescript
private logs = new CircularBuffer<string>(MAX_GATEWAY_LOG_LINES)

getLogTail(limit = 20): string {
  return this.logs.tail(limit).join('\n')
}
```

---

## 6. Virtual Scrolling

**Hook:** `/ui-tui/src/hooks/useVirtualHistory.ts`

### Height Estimation

```typescript
const estimateRowHeight = useCallback(
  (index: number) =>
    estimatedMsgHeight(virtualRows[index]!.msg, cols, {
      compact: ui.compact,
      details: detailsVisible,
      thinkingVisible: thinkingDetailsVisible,
      toolsVisible: toolsDetailsVisible,
      userPrompt: ui.theme.brand.prompt,
      withSeparator: index > firstUserIdx
    }),
  [cols, detailsVisible, /* ... */]
)
```

**Measurement caching:**

```typescript
const heightCache = useMemo(() => {
  const key = `${ui.sid}:${cols}:${promptWidth}:${compact}:${detailsLayout}`
  let cache = heightCachesRef.current.get(key)
  
  if (!cache) {
    cache = new Map()
    heightCachesRef.current.set(key, cache)
    
    // LRU eviction
    if (heightCachesRef.current.size > MAX_HEIGHT_CACHE_BUCKETS) {
      heightCachesRef.current.delete(heightCachesRef.current.keys().next().value!)
    }
  }
  
  return cache
}, [heightCacheKey])
```

**Sticky scroll:**

```typescript
<ScrollBox
  ref={scrollRef}
  stickyScroll  // Auto-scroll to bottom when new content arrives
  onClick={(e) => { if (e.cellIsBlank) actions.clearSelection() }}
>
  {/* Virtual rows */}
</ScrollBox>
```

// __CONTINUE_HERE__
