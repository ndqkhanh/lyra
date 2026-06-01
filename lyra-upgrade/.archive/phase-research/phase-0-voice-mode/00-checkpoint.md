# Phase 0 Voice Mode — Research Checkpoint

**Status**: Research complete, synthesizing plan  
**Date**: 2026-05-31

## Sources Researched

### ✅ Claude Code Documentation
- Voice dictation: https://code.claude.com/docs/en/voice-dictation
- Hooks for audio playback: Warcraft peon notifications, sound-effects-via-hooks

### ✅ Voice Agent Frameworks (Cloned & Read)
- **Pipecat** (https://github.com/pipecat-ai/pipecat) — Real-time voice/multimodal framework
- **Smart Turn** (https://github.com/pipecat-ai/smart-turn) — Semantic turn detection, 23 langs (VI+EN)
- **LiveKit Agents** (https://github.com/livekit/agents) — WebRTC + telephony + MCP support
- **TEN Framework** (https://github.com/TEN-framework/TEN-Agent) — Multi-language realtime framework
- **Silero VAD** (https://github.com/snakers4/silero-vad) — De-facto open VAD

### ✅ Speech-to-Speech Models (Cloned & Read)
- **Moshi** (https://github.com/kyutai-labs/moshi) — First real-time full-duplex spoken LLM
  - Paper: https://arxiv.org/abs/2410.00037
  - Mimi codec: 24kHz → 1.1kbps, 80ms latency, streaming
  - 160ms theoretical latency (80ms frame + 80ms acoustic)
- **CSM** (https://github.com/SesameAILabs/csm) — Llama-based conversational speech, Mimi codes

### ✅ Open TTS/STT (Cloned & Read)
- **Kokoro-82M** (https://github.com/hexgrad/kokoro) — Tiny, fast, high-quality TTS (Apache)
- **Orpheus TTS** (https://github.com/canopyai/Orpheus-TTS) — Expressive, emotion tags, low latency
- **NeMo** (https://github.com/NVIDIA/NeMo) — Parakeet/Canary STT (top Open ASR Leaderboard)
  - Parakeet-unified-en-0.6b: 160ms minimum streaming latency
  - Nemotron VoiceChat: full-duplex, interruptible, low latency
  - MagpieTTS: 9 languages (En, Es, De, Fr, **Vi**, It, Zh, Hi, Ja)
- **Whisper** (https://github.com/openai/whisper) — Best multilingual open ASR (VI+EN strong)

### ✅ Voice Benchmarks (Web Search)
- **Full-Duplex-Bench v1** (https://arxiv.org/abs/2503.04721) — Turn-taking, backchannel, interruption
- **Full-Duplex-Bench v3** (https://arxiv.org/abs/2604.04847) — Disfluency + multi-step tool use
- **τ-Voice** (https://arxiv.org/abs/2603.13686) — Real-world task completion (not just conversational quality)
- **Open ASR Leaderboard** (https://arxiv.org/abs/2510.06961) — 60-86 systems, multilingual, Vietnamese support

## Key Findings

### Architecture Patterns
1. **Cascaded STT→LLM→TTS** (Pipecat, LiveKit) — Most production-ready, swappable components
2. **Full-duplex S2S** (Moshi, CSM) — Lower latency but monolithic, harder to adapt
3. **Semantic turn detection** (Smart Turn, LiveKit) — Transformer-based, reduces interruptions

### Latency Targets
- **Moshi**: 160ms theoretical (80ms codec + 80ms acoustic), 200ms practical on L4 GPU
- **NeMo Parakeet**: 160ms minimum streaming latency
- **Industry standard**: <300ms end-to-end for natural conversation

### Multilingual (VI+EN) Support
- **Whisper large-v3/turbo**: Strong VI+EN, proven multilingual baseline
- **NeMo Canary-1b-v2**: 25 European languages (no VI listed, but Parakeet supports it)
- **MagpieTTS**: Explicit Vietnamese support (9 languages)
- **Smart Turn**: 23 languages including Vietnamese + English

### Provider Abstraction Requirements
- STT/TTS providers must be swappable like LLM providers (§4.5 router)
- Support on-device (Whisper, Kokoro) vs. cloud (OpenAI Realtime, Deepgram, Cartesia)
- Graceful degradation when provider unavailable

## Next Steps
1. Synthesize into Phase 0 plan (voice-mode.md)
2. Define Lyra voice pipeline architecture
3. Specify MVP → full-duplex phasing
4. Integrate with §4.5 provider abstraction layer
5. Design personality/SFX layer (§5.3) as voice-mode component
