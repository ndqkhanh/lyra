# sambuild04/screen-voice-agent (Samuel) -- Deep-Read

## 1. Headline Feature & Mechanism

**Voice-first AI desktop companion for macOS** with sub-500ms wake-word voice loop, ambient screen+audio context, real computer use via the macOS Accessibility framework, and self-modifying tools that write, test, and auto-repair their own plugins at runtime using GPT-5.5 reasoning.

### Core mechanism

The system runs a realtime bidirectional voice loop over the OpenAI Realtime API (WebRTC transport, model `gpt-realtime-2`). A wake-word detector ("Hey Samuel", implemented in `src/hooks/useWakeWord.ts`) triggers the Electron app to connect an ephemeral API key and start a `RealtimeSession` via the `@openai/agents` SDK. From that point, the loop is:

1. The server runs Voice Activity Detection (VAD) with `threshold=0.6`, `silence_duration=700ms`, and `create_response=true`.
2. When the user stops speaking, the server auto-creates a model response.
3. Before responding, Samuel may call 1+ tools (screen capture, AX tree read, browser automation, plugin execution, etc.) to gather context.
4. The model speaks back over WebRTC audio as voice "Ash".

**Three critical latency optimizations** set Samuel apart from naive agents:

- **(a) Smart context decision** (`classifyTranscript` in `useRealtime.ts`): Before every turn, Samuel classifies the user's transcript into categories (ACK, META, SERVICE, COMMAND, REFERENTIAL, AMBIGUOUS). Turns that clearly don't need the screen (acknowledgments, meta-questions like "what can you do", service-mentions destined for Playwright) entirely skip the AX-tree read + screenshot that would otherwise cost ~1.3s of latency and ~150 KB of tokens.

- **(b) Ambient audio buffer (pull-model)**: A Swift helper (`helpers/record-audio.swift`) uses ScreenCaptureKit to continuously record system audio into a rolling local-only `.m4a` file. Zero transcription cost while idle. When the user asks "translate the last 30 seconds" or "what did they just say?", the model calls `recall_audio(last_seconds=N)`, which ffmpeg-trims the buffer tail and transcribes via `gpt-4o-transcribe`. The user's question IS the boundary -- no fragile semantic-VAD cadence, no auto-pause/resume keystroke fights, no mic-bleed cancellation.

- **(c) Per-display JPEG encoding cache** (`capture.ts`): Screenshots are adaptively compressed (quality step-down + width step-down) to fit within a 140KB (full-display) or 190KB (focused window) cap, matching the WebRTC SCTP message limit. The converged `(quality, widthIdx)` pair is cached per-display and per-app so subsequent captures converge in 1 `sips` call instead of 6-7.

### Two-loop architecture

The system operates two independent loops:

| Loop | Trigger | Cadence | Purpose |
|---|---|---|---|
| **Conversation loop** (`useRealtime.ts`) | User speech | Per-turn | Reactive: listen -> transcribe -> think -> speak + tools |
| **Watcher loop** (`useWatcherLoop.ts`) | Timer | 20s interval | Proactive: evaluate registered triggers against screen+audio content |

The watcher loop evaluates two tiers of triggers stored in `~/.samuel/memory.json`:
- **Keyword triggers**: deterministic string matching, zero cost, exact-match-only
- **Classifier triggers**: GPT-4o-mini evaluates each event (~$0.0001/call), e.g. "alert me when the speaker sounds frustrated"

Triggers are first-class objects with cooldown, debounce, digest mode (accumulate matches and deliver one summary per window), and per-watch suppression lists. They fire synthetic conversation turns via `sendTextAndRespond("TRIGGER ALERT: ...")`.

### Self-modifying tool system

The plugin system in `src/lib/plugin-loader.ts` uses `new Function("secrets", "invoke", "sleep", "ui", code)` to dynamically load JavaScript plugins from `~/.samuel/plugins/*.js`. Plugins declare a `validates()` function and an optional `wraps` field (middleware over existing tools). The auto-repair pipeline:

```
execution fails -> loadPlugin() validates
  -> diagnoseFailure (GPT-5.5 with reasoning tokens)
    -> category: syntax_logic / wrong_assumption / external_change / etc.
    -> next_step: patch / rewrite / ask_user / give_up
  -> generate_plugin_code (GPT-5.5)
  -> loadPlugin() verifies the new code parses
  -> write_plugin() saves to disk
  -> max 2 attempts, then honest escalation
```

## 2. Architecture & Core Modules

### Entry points

| File | Role | Lines |
|---|---|---|
| `src/main.tsx` | React DOM mount, minimal entry | 11 |
| `src/App.tsx` | Root component -- orchestrates all hooks, wake word, recording, settings | 432 |
| `electron/main.ts` | Electron main process, BrowserWindow creation, IPC bridge routing | 118 |
| `electron/preload.ts` | Context bridge (`__electronInvoke`, `__electronWindow`) | 13 |

### Core library (renderer process)

| File | Purpose | Lines |
|---|---|---|
| `src/lib/samuel.ts` | 30+ tool definitions, control mode logic, rate limiting, structured error types | 3404 |
| `src/hooks/useRealtime.ts` | Main RealtimeSession lifecycle, VAD, transit handling, echo guard, say-do guard, continuous screen, guardrails | 2590 |
| `src/lib/session-bridge.ts` | Cross-module communication -- 15+ register/set function pairs, runtime state snapshot | 447 |
| `src/lib/plugin-loader.ts` | Dynamic plugin loading via new Function, validate, wraps, auto-repair pipeline | 443 |
| `src/lib/samuel-privacy.ts` | Privacy gate helpers -- localStorage read of 6 privacy toggles | 111 |
| `src/lib/watcher-eval.ts` | Three-tier watcher evaluation: keyword -> classifier -> digest flush | 158 |
| `src/lib/invoke-bridge.ts` | IPC bridge from renderer to Electron main process | (trivial) |

### Electron handlers (main process)

| File | Purpose |
|---|---|
| `electron/handlers/index.ts` | Central router -- dispatches ~70 commands to handler modules |
| `electron/handlers/capture.ts` | Screenshot pipeline: Peekaboo, screencapture, sips compression, display detection, selected text |
| `electron/handlers/memory.ts` | Persistent memory: facts, corrections, vocabulary, watcher system (52 exported functions) |
| `electron/handlers/plugins.ts` | Plugin CRUD, code generation via GPT-5.5, code review via GPT-4o-mini, diagnose failure |
| `electron/handlers/learning.ts` | Audio capture lifecycle, web search, web read, language learning hooks |
| `electron/handlers/oauth.ts` | PKCE OAuth for Google/GitHub/Spotify |
| `electron/handlers/browser.ts` | Playwright browser automation |
| `electron/handlers/cua.ts` | Computer Use Agent running GPT-5.5 visual desktop control |
| `electron/handlers/misc.ts` | Desktop interaction: click/type/key/scroll/focus via CGEvent, AX tree reading, AppleScript |
| `electron/handlers/config.ts` | Realtime API ephemeral key creation, config reading |

### Native helpers (Swift)

| File | Purpose |
|---|---|
| `helpers/record-audio.swift` | ScreenCaptureKit system audio capture, rolling buffer |
| `helpers/read-ax-tree.swift` | Accessibility tree reader for any macOS app |
| `helpers/desktop-action.swift` | CGEvent-based mouse click/type/scroll |
| `helpers/native-input.swift` | Native input event generation |
| `helpers/ax-observer.swift` | Accessibility event observer for content-change detection |

### React hooks

| File | Purpose |
|---|---|
| `src/hooks/useRealtime.ts` | Session lifecycle, VAD, guardrails, say-do guard, media noise filter, continuous screen |
| `src/hooks/useWakeWord.ts` | Local wake-word detection via Web Audio API |
| `src/hooks/useWatcherLoop.ts` | 20s-interval trigger evaluation (Loop 2) |
| `src/hooks/useLearningMode.ts` | Ambient language learning loop |
| `src/hooks/useAudioBuffer.ts` | Ambient audio buffer lifecycle |
| `src/hooks/useRecordMode.ts` | Recording mode for meeting capture |
| `src/hooks/useUIPreferences.ts` | localStorage UI preferences (privacy toggles, volume, window size) |

### Data flow (typical interaction)

```
1. "Hey Samuel" -> useWakeWord.ts detects -> App.tsx:handleWakeDetected()
2. Connect RealtimeSession via ephemeral API key (electron/handlers/config.ts)
3. User says "what does this error mean?"
4. gpt-realtime-2 receives audio, transcribes via gpt-4o-transcribe
5. useRealtime.ts transcript handler -> echo/medianoise/bias-guard checks
6. VAD speech_stopped -> server auto-creates response
7. Model decides turn needs screen -> calls read_app() tool
8. read_app tool -> IPC invoke("read_app_content") -> misc.ts AX tree read
9. If AX tree thin (<5 elements) -> fallback to capture.ts peekaboo/screencapture
10. sendImageToSession() -> session.transport.sendEvent({type: "conversation.item.create"})
11. Model receives screen context, generates spoken answer
12. Audio plays, bubble text revealed at 16 chars/sec via pacer timer
```

## 3. Performance/Benchmarks

All numbers are from the README and code comments (no independent benchmark):

| Metric | Value | Source |
|---|---|---|
| Voice loop latency (wake word -> first audio) | ~500ms | README |
| Per-turn smart context savings | ~1.3s latency, ~150 KB tokens | README |
| Continuous screen poll cadence | 15s | `CONTINUOUS_POLL_MS` constant |
| Screen push hard throttle | 10s min gap | `CONTINUOUS_MIN_PUSH_GAP_MS` |
| Screen push delta threshold | 200 bytes | `CONTINUOUS_DELTA_BYTES` |
| JPEG hard cap (full display) | 140 KB | `SIZE_CAP` in capture.ts |
| JPEG hard cap (focused window) | 190 KB | `SIZE_CAP` in capture.ts |
| Wake word always-listening cost | ~$0.006/min | README |
| Ambient mode (screen + audio) cost | ~$0.02-0.05/min | README |
| Plugin generation (GPT-5.5) | ~3-8s, ~$0.005/plugin | README |
| Plugin diagnosis (GPT-5.5) | ~$0.003/diagnosis | README |
| Plugin review (GPT-4o-mini) | ~$0.001/review | README |
| Trigger evaluation (GPT-4o-mini) | ~$0.0001/event | README |
| Session rotation | 25 min (before 60-min hard cap) | `SESSION_ROTATION_MS` constant |
| Heartbeat keepalive | 30s | `HEARTBEAT_INTERVAL_MS` constant |
| Auto-passive idle timeout | 30s | `AUTO_PASSIVE_TIMEOUT_MS` constant |
| Media-noise passive threshold | 4 consecutive drops | `MEDIA_NOISE_PASSIVE_THRESHOLD` |
| Bubble text reveal rate | 16 chars/sec | `REVEAL_CHARS_PER_SEC` constant |
| AJAX continuous budget | 16 KB per push | `CONTINUOUS_AX_BUDGET` constant |
| VAD threshold | 0.6 | turnDetection config |
| VAD silence duration | 700ms | turnDetection config |
| Say-do guard max nudges | 1 per turn | `saydoRetriedRef` flag |
| Tool rate limit | varies per tool | `rateLimitGuard()` in samuel.ts |
| Plugin max auto-repair attempts | 2 | `MAX_REPAIR_ATTEMPTS` |
| Auto-Reflexion lesson cap | 5 per session | `AUTO_LESSON_CAP` |

## 4. Trade-offs

### Wins

- **Sub-500ms voice loop** feels natural and conversational. The OpenAI Realtime API's WebRTC transport with server VAD and barge-in is the best available latency profile for voice agents.

- **Smart context decisions** avoid screen capture on ~50% of turns (acknowledgments, meta-questions, service mentions). This saves ~1.3s of latency per skipped turn and keeps conversation tokens lean.

- **Pull-model audio buffer** is architecturally superior to push: zero idle transcription cost, user's question defines the window, no fragile semantic-VAD cadence to tune.

- **Self-modifying tools** with auto-repair mean the toolset grows organically with usage. Plugin generation is tested, validated, and can self-heal against external API changes.

- **Privacy-first architecture**: toggles for every sensory capability, consent popups (no auto-approve) for sensitive surfaces, all memory stored locally.

- **Two-loop design** cleanly separates reactive conversation from proactive monitoring. The watcher loop's trigger system (keyword + classifier, with cooldowns, debounce, digest, and suppression lists) is sophisticated and well-considered.

- **Per-app permission cache** avoids re-prompting for app access during a session, while initial access still requires user approval.

- **Structured tool errors** (`{ok: false, error_type: "focus_lost" | "permission" | ..., try_instead: "..."}`) let the model reason about failures rather than seeing raw error strings.

### Losses

- **macOS only** -- depends entirely on ScreenCaptureKit, Peekaboo, and macOS Accessibility APIs. No Windows/Linux port.

- **Plugins execute via `new Function()`** with no sandboxing. The approval flow is the only security boundary. An approved malicious plugin has full JS access to secrets, IPC, and the DOM.

- **Cannot modify compiled code** -- plugins can only extend and wrap, never patch the core agent. True self-improvement is limited.

- **Browser sessions don't persist** -- each Playwright launch starts fresh, requiring re-login to every site.

- **Single-file plugins only** -- no multi-file architecture, no npm imports. Plugin complexity is constrained.

- **Always-on API costs** -- no local-first fallback. Ambient mode at $0.02-0.05/min would cost $29-72/month at 24h/day.

- **OpenAI single-vendor lock** -- Realtime API, GPT-5.5, GPT-4o, gpt-4o-transcribe, all from one provider. No Anthropic, no local models.

- **Transcription bias prompt regurgitation** -- a persistent bug where `gpt-4o-transcribe` hallucinates its own bias prompt on unclear audio, producing fake "Samuel" user turns. Multiple rounds of hardening (sentence-form -> keyword-bag -> minimal wake-words-only) show this is a recurring cat-and-mouse problem with the Whisper-family architecture.

- **Say-do guard complexity** -- the regex-based `looksLikeUnactedCommitment()` guard has accumulated 6 exclusion patterns over multiple postmortems (memory acks, self-recap, conditionals, etc.). Each new pattern addresses a specific loop but the surface is growing unsustainably.

- **No LICENSE file in repository** -- the README states MIT, but no LICENSE file is present in the cloned repo. This is a distribution hygiene issue.

## 5. Design Rationale

The codebase reveals a pragmatic, battle-tested design philosophy shaped by postmortems of real failures. Key decisions:

- **"Takeover" as default control mode**: The README and code note that each spoken command IS the user's explicit consent. Asking for confirmation in a voice loop would be double-confirmation friction. Only destructive actions (close window, quit app, send email) still gate. The user can voice-downshift to `ask_before_action` or `observe_only`.

- **Pull-model for audio over push**: Historically Samuel had a "Companion mode" with semantic VAD pushing audio context. The current pull-model replaces it because the user's question is the ideal boundary -- no fragile cadence tuning, no mic-bleed cancellation, no idle transcription cost.

- **Smart context over always-on capture**: Earlier versions injected AX+screenshot on every turn. The current architecture classifies first, captures only when relevant, and de-dupes by AX-tree hash + 5s cooldown. Saves 1.3s per turn on ~50% of turns.

- **Per-display JPEG cache**: The comment trail in `capture.ts` documents a postmortem where per-display cache convergence was needed because a 4K Studio Display and HD external monitor needed wildly different quality settings. Without per-display caching, switching displays would burn 6-7 `sips` re-encodes (~700ms) per capture.

- **Session rotation at 25 minutes**: The OpenAI Realtime API has a 60-minute hard cap. Samuel reconnects proactively at 25 minutes to avoid mid-conversation teardown. Context window of 6 turns is carried across reconnections.

- **new Function() over worker isolation for plugins**: The simplest possible plugin runtime. The trade-off is explicit: ease of self-modification over security. A Web Worker sandbox is on the roadmap.

- **Auto-Reflexion for tool failures**: Structural tool errors (permission, focus_lost, ax_error) are automatically persisted as corrections, so future sessions learn from them. The cap of 5 lessons per session prevents noise. This is a lightweight implementation of the Reflexion pattern.

- **Post-session feedback extraction**: After idle timeout, the session transcript is sent to GPT-4o-mini to extract implicit corrections. This closes the loop: even if the user doesn't explicitly say "remember this", behavioral lessons can be learned from conversation patterns.

## 6. Transfer to Lyra

### Transferable idea: Two-Loop Architecture with Pull-Model Context Injection

Samuel's clean separation of (1) a reactive conversation loop and (2) an event-driven proactive watcher loop is directly applicable to Lyra's memory and context system (§4.x: Memory/Context). 

**The pattern**: Instead of Lyra continuously polling for context (expensive, noisy, token-wasteful), adopt a pull-model where:
- The conversation loop decides per-turn whether context is needed, based on semantic classification of the user's intent
- A separate watcher loop evaluates user-registrable triggers against ambient signals on a tunable cadence
- User questions are the boundary for context injection -- no ambient data enters context without a user question to ground it

**Specific transfer**:
- Lyra's `decide_and_respond` or equivalent turn handler should classify user intent before fetching memory/screen/audio context
- Lyra's continuous observation mode should use a poll pump with change-detection hashing (djb2 hash on AX text) and a minimum delta threshold before pushing
- The watcher trigger system (keyword + classifier, cooldowns, debounce, digest, suppression lists, expiry) is a well-architected pattern for Lyra's "tell me when you see/hear X" feature

**Plugin auto-repair** is a secondary transfer: validated output contracts (`validates()` function) with automatic GPT-5.5 diagnosis and repair (max 2 attempts, clean escalation) would strengthen Lyra's plugin/tool extensibility layer.

### Workstream route: §4.x Memory & Context

The section most relevant to the two-loop pull-model architecture is the Memory/Context workstream. The pull-model audio buffer pattern also applies to Lyra's ambient listening mode in the Voice workstream.

### Impact, Effort, Tier

| Dimension | Score | Rationale |
|---|---|---|
| **Impact** | 8/10 | Core memory+context loop improvement; eliminates wasteful continuous polling; adds proactive watcher triggers |
| **Effort** | 6/10 | Significant integration work to refactor Lyra's context injection pipeline, but the patterns are well-proven and the code is MIT-licensed |
| **Tier** | Silver | High-value architectural pattern that improves both latency and cost, but requires non-trivial refactoring |

### License

MIT (stated in README; no LICENSE file present in clone). Compatible with Lyra's licensing.
