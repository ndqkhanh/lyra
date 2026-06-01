# Phase 0: Voice Mode — Executive Summary

**Status**: ✅ Research complete, plan delivered  
**Date**: 2026-05-31  
**Next**: Awaiting user approval before Phase 1

---

## What Was Delivered

### 1. Comprehensive Voice Mode Plan (431 lines)
**Location**: `lyra-upgrade/plans/00-voice-mode.md`

**Contents**:
- Problem statement & evidence synthesis
- Component landscape (VAD, STT, TTS) with provider comparison tables
- Proposed Lyra architecture (Mermaid diagram + data models)
- 5-phase implementation roadmap (MVP → full-duplex → evaluation)
- Multi-provider behavior specification (DeepSeek, Claude, OpenAI, open-weights)
- Risk analysis & open questions
- 19 cited references

**Key Recommendations**:
- **Architecture**: Cascaded STT→LLM→TTS pipeline (not monolithic S2S)
- **MVP Stack**: Silero VAD + Whisper turbo (EN) + Kokoro/MagpieTTS (VI)
- **Production Stack**: Smart Turn + Deepgram + Cartesia (cloud, <300ms)
- **Phasing**: 5 phases from push-to-talk MVP → full-duplex with barge-in
- **Evaluation**: Open ASR Leaderboard + Full-Duplex-Bench v1 + τ-Voice

### 2. Research Checkpoint (2.5KB)
**Location**: `lyra-upgrade/phase-0-voice-mode/00-checkpoint.md`

Tracks all 19 sources researched, key findings, and next steps.

### 3. Progress Tracker (4.9KB)
**Location**: `lyra-upgrade/PROGRESS.md`

Live checklist for all 5 phases:
- Phase 0: ✅ Complete
- Phases 1-5: ⏳ TODO (detailed breakdown per workstream)

### 4. Research Log (5.3KB)
**Location**: `lyra-upgrade/research-log.md`

Detailed log of every source consulted:
- 19 sources successfully researched (100% success rate)
- 0 failed/unreachable links
- 1 deferred (OpenAI Realtime API — covered conceptually)

### 5. Findings Summary (5.0KB)
**Location**: `lyra-upgrade/findings.md`

Structured table of 19 findings:
- Source | Technique | Why it matters | How to adopt | Impact | Effort | Tier
- Categorized by tier: BREAKTHROUGH (1), CORE (6), HIGH (7), MEDIUM (5)

---

## Research Scope

### Sources Researched (19 total)

**Frameworks** (5):
- Pipecat, Smart Turn, LiveKit Agents, TEN Framework, Silero VAD

**Speech Models** (2):
- Moshi (full-duplex S2S), CSM (Llama-based)

**STT/TTS Providers** (4):
- Kokoro-82M, Orpheus TTS, NeMo (Parakeet/Canary/MagpieTTS), Whisper

**Benchmarks** (4):
- Full-Duplex-Bench v1 & v3, τ-Voice, Open ASR Leaderboard

**Documentation** (4):
- Claude Code voice dictation, hooks, Warcraft peon notifications, sound effects

---

## Key Insights

### 1. Architecture Decision
**Cascaded pipeline wins over end-to-end S2S** for Lyra:
- ✅ Modular (swappable STT/TTS providers)
- ✅ Aligns with Lyra's multi-provider philosophy (§4.5)
- ✅ Production-proven (Pipecat, LiveKit)
- ⚠️ Higher latency than Moshi (240ms vs 160ms), but <300ms achievable

### 2. Multilingual (VI+EN) Support
**Strong ecosystem for Vietnamese**:
- STT: Whisper (proven), NeMo Canary (top leaderboard)
- TTS: MagpieTTS (only open TTS with VI support)
- VAD: Smart Turn (23 langs including VI)

### 3. Latency Budget
**Target: <300ms end-to-end**
- Naive pipeline: 400ms (too slow)
- Streaming optimization: 240ms (achievable)
- Cloud providers: 150ms (Deepgram + Cartesia)

### 4. Provider Abstraction
**Voice providers must be swappable like LLM providers**:
- STTProvider interface (transcribe, transcribeStream)
- TTSProvider interface (synthesize, synthesizeStream)
- Multi-provider config (on-device vs cloud, fallback chains)

### 5. Phased Rollout
**5 phases minimize risk**:
- 0.1: Push-to-talk MVP (on-device)
- 0.2: Streaming + cloud providers (<300ms)
- 0.3: Full-duplex + barge-in
- 0.4: Personality/SFX layer (§5.3)
- 0.5: Evaluation & benchmarking

---

## Impact Assessment

**Impact**: 5/5 (FLAGSHIP)
- Major UX improvement (hands-free operation)
- Accessibility win
- Competitive differentiation (first multi-agent harness with full voice)
- Enables new workflows (voice-driven coding/research)

**Effort**: 4/5 (Moderate)
- Well-researched domain (many reference implementations)
- Phased rollout reduces risk
- Estimated: 6-8 weeks MVP, 12-16 weeks full-duplex

**Tier**: BREAKTHROUGH
- Provider-agnostic voice (unique in space)
- Multilingual (VI+EN) from day one
- Designed for future S2S integration

---

## Next Steps

1. **User approval** of Phase 0 plan
2. **Proceed to Phase 1**: Feature parity (§4.6-§4.12)
   - Tools, Plugins, MCP, Commands, Hooks, Sessions, Permissions
   - Research Claude Code docs + comparable harnesses
   - Build feature-parity matrix
3. **Revisit voice mode** during implementation phases

---

## Deliverables Checklist

- ✅ `plans/00-voice-mode.md` — Complete plan (431 lines)
- ✅ `phase-0-voice-mode/00-checkpoint.md` — Research checkpoint
- ✅ `PROGRESS.md` — Live tracker for all phases
- ✅ `research-log.md` — Detailed source log
- ✅ `findings.md` — Structured findings table
- ✅ This executive summary

**Total**: 886 lines of research documentation + 11 cloned repositories

---

**Phase 0 is COMPLETE. Ready for user approval.**
