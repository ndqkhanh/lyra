# Voice Dictation (Claude Code Documentation)

**Source:** https://code.claude.com/docs/en/voice-dictation
**Author/Org:** Anthropic / Claude Code team
**Date:** No explicit date; references v2.1.69+ (hold mode) and v2.1.116+ (tap mode).

## Key Technical Claims

1. **Voice dictation enables hybrid voice+keyboard input in Claude Code CLI.** Developers can speak prompts interleaved with typing in a single message. Speech is transcribed live, dimmed until finalized, then inserted at cursor position.

2. **Two interaction modes: hold-to-record and tap-to-record.** Hold mode is push-to-talk (Space held while speaking); tap mode toggles recording with a single keypress and auto-submits when stopped (minimum 3 words).

3. **Coding-specific transcription tuning.** Common dev terms (regex, OAuth, JSON, localhost) are recognized out of the box. The current project name and git branch name are injected as automatic recognition hints.

4. **Cloud-based transcription with no token cost.** Audio streams to Anthropic servers for transcription. It does NOT consume Claude messages or tokens, does not count toward `/usage` limits, and is not available with HIPAA compliance enabled.

5. **Not available with API keys or third-party providers.** Requires a Claude.ai account. Not available on Bedrock, Vertex AI, Foundry, or with HIPAA enabled.

## Architecture / Mechanism Details

- **Activation:** `/voice`, `/voice hold`, `/voice tap`, `/voice off`. Settings persist across sessions. Can be set directly in user settings JSON (`voice.enabled`, `voice.mode`).
- **Hold mode:** Watches for rapid key-repeat events from the terminal. Brief warmup during which key-repeat characters are typed and then auto-removed. Modifier combos (e.g., `meta+k`) skip warmup by starting recording on first keypress.
- **Tap mode:** First tap starts recording ONLY when prompt is empty (spaces still type normally while composing). Second tap stops and submits. Auto-stops after 15 seconds of silence or 2 minutes total.
- **Transcript insertion:** Inserted dimmed, finalized on stop. Cursor stays at end of inserted text. Multiple dictation segments can be interleaved with typing by moving the cursor.
- **Audio stack:** Built-in native module on macOS, Linux, Windows. Linux fallback chain: native -> `arecord` (ALSA) -> `rec` (SoX). WSL requires WSLg + SoX with PulseAudio backend (`libsox-fmt-pulse`).
- **Language:** Controlled by `language` setting; defaults to English. 20 supported languages (BCP 47 codes). VS Code extension also checks `accessibility.voice.speechLanguage`.
- **Keybinding:** `voice:pushToTalk` in `Chat` context, defaults to Space. Rebindable in `~/.claude/keybindings.json`. Single-key binding (replaces default, does not add secondary).
- **autoSubmit (hold mode):** When `voice.autoSubmit` is true, releasing the key auto-sends the prompt if transcript >= 3 words.
- **VS Code extension:** Supported but not in Remote sessions (SSH, Dev Containers, Codespaces) due to local microphone requirement.

## Numbers & Benchmarks

- Minimum version: v2.1.69 (hold), v2.1.116 (tap).
- autoSubmit / tap-submit threshold: 3 words minimum.
- Tap mode auto-stop: 15 seconds silence, 2 minutes total max.
- 20 supported dictation languages.
- Zero token/message consumption for transcription.
- Hold warmup: brief (key-repeat events detected from terminal).
- Not supported in web, SSH, Codespaces, Dev Containers environments.

## Transfer to Lyra

### One Transferable Idea: Hybrid voice-keyboard input channel for Lyra's agent interaction loop

Claude Code's voice dictation system proves that **low-friction voice input integrated into a CLI coding agent is practical and ergonomic.** The key architectural patterns worth adopting in Lyra are:

1. **Hold-to-record for short utterances, tap-to-record for longer dictation.** This dual-mode approach maps naturally to different interaction styles in an agent loop (quick commands vs. complex multi-sentence prompts).

2. **Auto-submit on release (hold mode)** and **auto-submit on stop (tap mode)** eliminate keystrokes for the common case, creating a near-instant voice-to-action pipeline.

3. **Coding vocabulary tuning + project-aware recognition hints.** Injecting the project name and git branch name as speech recognition hints is a trivial but high-impact optimization for transcription accuracy in context.

4. **Warmup bypass with modifier combos.** The key-repeat detection approach is a pragmatic solution for terminal environments that do not natively support key-down events.

5. **Settings persistence and session restart.** Voice dictation state survives across sessions, which is the right model for a modality preference.

### Workstream Route

Route: This maps most naturally to **Lyra's agent CLI / interactive mode workstream** -- not yet a numbered section in the upgrade plans, but a natural addition as a new §4.x subsection under "Agent Interface" or "Input Modalities." Alternatively, if Lyra has a `/commands` or `/plugins` workstream, voice dictation could be routed there as an optional plugin.

- **impact: 5** (transformative modality shift for developer interaction speed)
- **effort: 6** (requires audio capture, streaming transcription integration, coding vocabulary tuning, and terminal key-event handling; moderate complexity)
- **tier: Future / Innovation** (not a core reliability or safety concern, but a significant UX differentiator)
