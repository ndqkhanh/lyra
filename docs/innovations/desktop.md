# Desktop GUI: Electron + React Shell over Lyra Core API (Built)
> **Status:** 🟡 Stub (Electron + React shell built with 15 source files; backend integration deferred) | [Plan](../lyra-upgrade/plans/28-desktop.md) | [Code](../../src/lyra/desktop/) | [App](../../src/ui/desktop/)

## Abstract
Lyra Desktop is an Electron + React + TypeScript GUI shell that wraps the Lyra agent core's local API. Following the hermes-desktop reference architecture (MIT, Electron 39, React 19, TS 5.9, Tailwind 4), the desktop app is a thin GUI client — agent logic stays in the Python core, CLI and GUI are interchangeable clients of the same backend. Built components: streaming ChatView, FleetView with two-axis state, Sidebar with session/provider/skills panels, InputBar with model picker, StatusBar with token/cost tracking, SSE streaming hook to localhost:8580, and dark theme. Multimodal input (drag-drop images/audio/PDFs) and output (rendered images, audio playback, Mermaid diagrams, rich diffs) are the headline differentiator — a terminal cannot render these.

## Method (Planned)
Architecture: Agent core exposes local API (HTTP/SSE on localhost) → CLI/TUI and Desktop are interchangeable clients. Desktop = Electron + React + TS shell with: streaming chat, fleet view (§4.13), session search (SQLite FTS5), provider/model config (§4.5), skills/tools/memory/persona screens, schedules (§4.14), voice surface (§4.18).

## Conclusion
Config scaffolding exists (`src/lyra/desktop/`). Full build deferred — requires §4.5 provider abstraction and §4.13 fleet core as dependencies.
