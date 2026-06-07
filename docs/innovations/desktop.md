# Desktop GUI: Electron + React Shell over Lyra Core API (Built)
> **Status:** 🟡 Stub (Electron + React shell built with 15 source files; backend integration deferred) | [Plan](../lyra-upgrade/plans/28-desktop.md) | [Code](../../src/lyra/desktop/) | [App](../../src/ui/desktop/)

## Abstract
Lyra Desktop is an Electron + React + TypeScript GUI shell that wraps the Lyra agent core's local API. Following the hermes-desktop reference architecture (MIT, Electron 39, React 19, TS 5.9, Tailwind 4), the desktop app is a thin GUI client — agent logic stays in the Python core, CLI and GUI are interchangeable clients of the same backend. Built components: streaming ChatView, FleetView with two-axis state, Sidebar with session/provider/skills panels, InputBar with model picker, StatusBar with token/cost tracking, SSE streaming hook to localhost:8580, and dark theme. Multimodal input (drag-drop images/audio/PDFs) and output (rendered images, audio playback, Mermaid diagrams, rich diffs) are the headline differentiator — a terminal cannot render these.

## Method (Planned)
Architecture: Agent core exposes local API (HTTP/SSE on localhost) → CLI/TUI and Desktop are interchangeable clients. Desktop = Electron + React + TS shell with: streaming chat, fleet view (§4.13), session search (SQLite FTS5), provider/model config (§4.5), skills/tools/memory/persona screens, schedules (§4.14), voice surface (§4.18).

## Working Flow

You install the Lyra desktop app and launch it. Behind the scenes, Electron wakes up and starts a local HTTP/SSE server inside the Lyra Python core on `localhost:8580` — think of it as Lyra's API engine running in the background. The React frontend connects to that server via Server-Sent Events, which is just a fancy way of saying "the server pushes real-time messages to your chat window as they happen."

**Example:** You want to upload a diagram image and ask Lyra to explain it.

1. You drag-drop a PNG diagram onto the ChatView area in the desktop app.
2. The React UI sends the file to the backend at `http://localhost:8580/chat/stream` as a multipart request.
3. Lyra's core processes the image, generates a response, and streams tokens back over SSE.
4. The ChatView renders each token as it arrives — no waiting for the full reply.
5. If Lyra generates a Mermaid diagram or rich diff in its answer, the desktop renders it visually inline (something a terminal cannot do).

## Conclusion
Config scaffolding exists (`src/lyra/desktop/`). Full build deferred — requires §4.5 provider abstraction and §4.13 fleet core as dependencies.
