# Voice Mode (Concept)

> **What & Why:** Lyra speaks and listens. Voice Mode is a provider-swappable pipeline (capture→VAD→STT→agent→TTS→playback) with barge-in, full-duplex Inner Monologue, and bilingual VI+EN support.

## Mental Model

Voice is just another I/O channel. The same agent that reads your text and writes responses also listens to your speech and speaks back. The provider abstraction (§4.5) means you can swap Whisper for DeepSeek ASR, or ElevenLabs for Orpheus TTS, without changing the pipeline.

## Tiers

- **Tier A (Cascaded):** STT → LLM → TTS. 1.7s simple, 4.7s complex. Production-ready.
- **Tier B (Full-Duplex):** Inner Monologue at 80ms frames. Simultaneous listen+speak. Built.

## Key Concepts

- **Barge-in:** Interrupt the agent mid-speech. Semantic endpointing detects intent, not just silence.
- **Self-correction buffer:** Keyword-triggered rollback ("wait, I meant..."). Addresses cascaded STT's 0.176 Pass@1.
- **Think-before-Speak:** CoT reasoning before audio output. +113.79% task completion [VoxMind, 2604.15710v1].

## → Dive Deeper

- [Voice Architecture](../architecture/07-voice-pipeline.md)
- [Innovation Doc](../innovations/voice-mode.md)
- [Plan](../lyra-upgrade/plans/18-voice-mode.md)
