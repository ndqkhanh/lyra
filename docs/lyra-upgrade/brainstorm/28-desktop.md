# Brainstorm — Lyra Desktop GUI + Multimodal (§4.28)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Source Techniques Gathered

| Technique | Source | Core Idea |
|-----------|--------|-----------|
| hermes-desktop | fathah (MIT) | Electron + React + TS, thin GUI over agent core local API, SSE streaming, multimodal |
| Claude Code Desktop | Anthropic | Desktop companion for CLI agent |
| OpenCode | SST | Terminal + desktop + IDE, 75+ providers |
| Electron vs Tauri | — | Footprint trade-off: Electron (~150MB) vs Tauri (~10MB) |

---

## Breakthrough Idea #1: Agent-Core-Local-API Split — CLI and Desktop as Interchangeable Clients

**Sources Fused:** hermes-desktop architecture + Lyra's existing agent core

**Core Mechanism:**
- Lyra agent core exposes a local HTTP/SSE API on `127.0.0.1:<port>`
- CLI/TUI and lyra-desktop are interchangeable clients of the SAME backend
- API endpoints: `/chat` (SSE stream), `/sessions` (CRUD), `/fleet` (supervisor), `/config` (settings), `/memory` (search), `/skills` (list/load)
- Desktop adds: multimodal input handling, rich output rendering, voice surface, fleet view
- Both clients share: auth, sessions, memory, skills, tools — single source of truth

**Breakthrough:** No other open-source agent harness has the clean local-API split that makes CLI and GUI true peers. Claude Code desktop is proprietary; hermes-desktop is the closest analog.

**Impact:** 5 | **Effort:** 5 | **Risk:** Medium

---

## Breakthrough Idea #2: Multimodal Input Router with Graceful Degradation

**Sources Fused:** §4.5 provider capability map + hermes-desktop multimodal handling

**Core Mechanism:**
- Drag-drop/paste an image → Lyra checks provider capability map (§4.5): can the active provider do vision?
- YES → send image to vision-capable provider, receive analysis
- NO → local OCR/description pipeline: extract text via OCR, describe via image metadata, route text description to text-only provider
- Same pattern for audio (transcribe locally → route text), PDFs (extract text + images), video (extract keyframes + audio)
- The degradation is automatic and transparent — the user doesn't need to know provider capabilities

**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: Tauri-Based Lightweight Desktop with Rust Performance

**Sources Fused:** Tauri evaluation + hermes-desktop feature set

**Core Mechanism:**
- Evaluate Tauri (Rust backend, ~10MB binary) vs Electron (Chromium, ~150MB)
- Tauri advantages: smaller, faster, more secure (no full Chromium), Rust backend for performance-critical paths
- Electron advantages: larger ecosystem, easier React integration, more npm packages
- Decision: START with Electron (faster to ship, proven pattern from hermes-desktop), PLAN Tauri migration for v2 (when bundle size matters)
- Keep the agent-core-local-API split — Tauri desktop is just another client

**Impact:** 3 | **Effort:** 3 | **Risk:** Low

---

## Expert Check

**Senior UX Designer:** "Idea #1 is architecture, not UX — but it's the right architecture. The local API split means Lyra can have a web UI, a mobile app, or an IDE plugin later without touching the agent core. This is future-proofing."

**Senior Backend Engineer:** "SSE streaming over localhost is simple and reliable. Don't over-engineer the API — REST + SSE covers everything. Add WebSocket only if full-duplex voice requires it."

**Adversarial Skeptic:** "A desktop app for a terminal-native agent — is this solving a real problem or adding complexity? The multimodal argument is valid (terminals can't show images), but the desktop adds an entirely new frontend to maintain. Prove demand with a minimal multimodal CLI extension first."

**Resolution:** Idea #1 (agent-core-local-API) is the architecture. Idea #2 (multimodal routing) is the killer feature that justifies the desktop. Ship a minimal multimodal chat first (images + PDFs), add voice + fleet later. The Skeptic's concern is valid — gate the full desktop behind multimodal CLI usage data.
