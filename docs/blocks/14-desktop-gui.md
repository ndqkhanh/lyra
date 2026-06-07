# Desktop GUI — Block Spec

> Electron + React + TypeScript shell wrapping the Lyra agent core's local API. Thin GUI client — agent logic stays in Python. CLI and GUI are interchangeable clients of the same backend.

## Architecture

```
┌──────────────────────────────────────────────┐
│  Electron Main Process                        │
│  electron/main.ts                             │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │ IPC Bridge   │  │ BrowserWindow        │   │
│  │ preload.ts   │  │ (1280×860, dark)     │   │
│  └──────┬───────┘  └──────────┬───────────┘   │
├─────────┼─────────────────────┼───────────────┤
│  Renderer│                     │               │
│  React App                      │               │
│  ┌──────┴──────────────────────┴───────────┐  │
│  │ ChatView · FleetView · Sidebar          │  │
│  │ InputBar · StatusBar                    │  │
│  │ useLyraAPI (SSE) · useSessions (SQLite) │  │
│  └──────────────────┬──────────────────────┘  │
└─────────────────────┼─────────────────────────┘
                      │ HTTP/SSE
              ┌───────┴────────┐
              │ Lyra Core      │
              │ 127.0.0.1:8580 │
              └────────────────┘
```

## Components

| Component | File | Role |
|-----------|------|------|
| `App` | `src/ui/desktop/src/App.tsx` | Root: SSE streaming, message state, health checks |
| `ChatView` | `src/ui/desktop/src/components/ChatView.tsx` | Markdown rendering, code blocks, auto-scroll |
| `FleetView` | `src/ui/desktop/src/components/FleetView.tsx` | Session rows, two-axis state badges |
| `Sidebar` | `src/ui/desktop/src/components/Sidebar.tsx` | Sessions, providers, skills |
| `InputBar` | `src/ui/desktop/src/components/InputBar.tsx` | Chat input, model picker, voice toggle |
| `StatusBar` | `src/ui/desktop/src/components/StatusBar.tsx` | Tokens, cost, connection |
| `useLyraAPI` | `src/ui/desktop/src/hooks/useLyraAPI.ts` | SSE streaming hook |
| `useSessions` | `src/ui/desktop/src/hooks/useSessions.ts` | Session CRUD, polling |

## → Dive Deeper

- [Desktop Innovation Doc](../innovations/desktop.md)
- [Desktop Plan](../lyra-upgrade/plans/28-desktop.md)
