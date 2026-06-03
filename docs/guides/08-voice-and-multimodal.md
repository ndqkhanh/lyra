# Guide: Voice and Multimodal

> 📖 Guide — Walk through Lyra's voice pipeline from microphone input to spoken response. Learn the push-to-talk cascade, multimodal desktop integration, and how to configure voice packs.

Voice mode lets you speak to Lyra and receive spoken responses with real-time streaming and natural interrupt handling. The multimodal layer adds vision capabilities and desktop integration.

---

## Push-to-Talk Cascade

When you press the push-to-talk key (default: Ctrl+Space), the voice pipeline activates through five stages:

### Stage 1: Microphone -> VAD

Voice Activity Detection (Silero VAD, 10ms frame inference) detects when speech starts and stops. The VAD tolerates ambient noise (configurable noise gate at -30dB default) and avoids triggering on non-speech sounds. Wake word detection ("hey lyra") runs on-device via Porcupine (<100ms detection latency).

### Stage 2: VAD -> ASR (Speech-to-Text)

Audio is streamed to the ASR engine. Two options:

| Engine | Latency | WER | Cost | Privacy |
|---|---|---|---|---|
| Whisper large-v3 (local) | ~400ms | 3.9% | Free | Full |
| Deepgram Nova-2 (cloud) | ~300ms | 3.2% | $0.0043/min | Shared |

Streaming ASR returns partial transcriptions as words are recognized, so the pipeline can begin processing before the user finishes speaking.

### Stage 3: ASR -> Agent (LLM Processing)

The transcribed text enters the agent loop as a normal text input. The model processes it with full context from the session (SOUL, plan, recent turns, memory). The model generates a response with streaming tokens.

### Stage 4: Agent -> TTS (Text-to-Speech)

Response tokens are streamed to the TTS engine. Two options:

| Engine | Latency | Quality | Privacy |
|---|---|---|---|
| Kokoro (local) | ~150ms first chunk | Good | Full |
| ElevenLabs Turbo (cloud) | ~200ms first chunk | Excellent (voice cloning) | Shared |

The TTS engine begins synthesizing audio as soon as the first complete sentence is available, streaming audio chunks back to the speaker.

### Stage 5: TTS -> Speaker

Audio plays through the output device. The end-to-end latency target is <500ms from speech end to first audio heard.

### State Machine

````
IDLE -> LISTENING (wake word / push-to-talk)
     -> PROCESSING (VAD detects speech end)
     -> SPEAKING (response ready)
     -> IDLE (speech complete) or LISTENING (barge-in)
```

Barge-in: you can speak while Lyra is responding. ASR detects voice activity, TTS playback stops within 50ms, and the interrupted context is preserved for potential continuation. Echo cancellation prevents Lyra from responding to its own speech.

---

## Full-Duplex S2S Future

The roadmap includes full-duplex speech-to-speech (S2S) where models process audio directly without separate ASR/TTS. This would eliminate the text intermediate step, reducing latency and preserving prosody, tone, and emotion. This is a Phase 3 item on the [MASTER PLAN](../lyra-upgrade/MASTER-PLAN.md).

---

## Multimodal Desktop

### Drag-Drop Input

You can drag and drop files directly into Lyra's desktop interface:
- Images: analyzed via vision-capable providers (Claude, GPT-4o, Gemini)
- Documents: text extracted and processed
- Code files: opened for editing

### Rich Output Rendering

Lyra renders responses with rich formatting:
- Code blocks with syntax highlighting
- File diffs
- Tables
- Mentioned file links (clickable)

### Desktop Integration

| Feature | How |
|---|---|
| System tray | Quick access to voice mode, session management |
| Global hotkeys | Push-to-talk, mute/unmute, interrupt |
| Notifications | Session completion, needs-input alerts |
| Sleep/wake | Pause/resume sessions on system sleep |

---

## Voice Packs

Voice packs are configurable profiles that set:
- ASR engine + model
- TTS engine + voice (speed, pitch, model)
- Wake word sensitivity
- Ambient noise baseline

Create a voice pack in `~/.lyra/voice-profiles/`:

```toml
[asr]
engine = "whisper"
model = "large-v3-turbo"

[tts]
engine = "kokoro"
voice_id = "default"
speed = 1.0

[interrupt]
barge_in = true
echo_cancellation = true
```

Swap with `lyra voice --profile quick`.

---

## Related Docs

- [Architecture: Voice Pipeline](../architecture/07-voice-pipeline.md) -- full pipeline, data model, performance targets
- [Guide: Agent Execution](01-agent-execution.md) -- how voice feeds into the agent loop
- [Guide: Memory and Context](02-memory-and-context.md) -- voice context preservation in episodic memory
- [Guide: Tools and Integrations](09-tools-and-integrations.md) -- desktop integration details
- [MASTER PLAN](../lyra-upgrade/MASTER-PLAN.md) -- full 4-phase, 9-month voice roadmap (Phase 3)
