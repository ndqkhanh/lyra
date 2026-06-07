# Desktop GUI (Concept)

> **What & Why:** Lyra is not terminal-only. The Desktop GUI is an Electron + React shell that wraps the same agent core the CLI uses. Both are interchangeable clients of the same backend.

## Mental Model

The agent core exposes a local API (HTTP/SSE on 127.0.0.1:8580). The CLI talks to it. The Desktop GUI talks to it. Voice talks to it. They all drive the same agent — just different windows into the same brain.

## Built Components

- **ChatView:** Streaming markdown with syntax-highlighted code blocks
- **FleetView:** Agent View-style session rows with two-axis state badges
- **Sidebar:** Session list, provider config, skills browser
- **InputBar:** Chat input with model picker and voice toggle
- **StatusBar:** Token usage, cost, connection status

## → Dive Deeper

- [Innovation Doc](../innovations/desktop.md)
- [Plan](../lyra-upgrade/plans/28-desktop.md)
- [Source](../../src/ui/desktop/)
