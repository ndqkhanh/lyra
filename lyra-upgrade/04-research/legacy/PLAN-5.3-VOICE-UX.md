# Investigation 5.3: Voice/Sound UX Design

> **Based on:** STREAM-11 (Workflows/Swarms/Safety), CESP v1.0, Warcraft Peon, alexop.dev
> **Status:** PLAN — Ready for implementation

---

## 1. Hook Points (15 Events)

| Hook ID | Event | Trigger | CESP Category |
|---------|-------|---------|---------------|
| `session.start` | New session started | User opens Lyra | session.start |
| `session.end` | Session ending | User closes / timeout | session.end |
| `agent.spawn` | Agent spawned | New sub-agent created | agent.spawn |
| `agent.terminate` | Agent terminated | Agent killed or completed | agent.terminate |
| `agent.task_start` | Agent begins task | Task dispatched to agent | agent.task_start |
| `agent.task_complete` | Agent completes task | Task result returned | agent.task_complete |
| `agent.task_error` | Agent task fails | Unrecoverable error | agent.error |
| `agent.handoff` | Task handed between agents | Agent delegates to another | agent.handoff |
| `fleet.formed` | Fleet/swarm formed | Multiple agents organized | fleet.formed |
| `consensus.reached` | Convergence achieved | Adversarial debate converges | consensus.reached |
| `consensus.failed` | Convergence failed | Debate deadlocks, escalation | consensus.failed |
| `research.breakthrough` | Research breakthrough | Champion improved (AutoScientists) | research.breakthrough |
| `system.warning` | System warning | Approaching limits, unusual | system.warning |
| `system.error` | System error | Crash, panic, fatal | system.error |
| `alignment.check` | Safety alignment triggered | Reasoning monitor flags | safety.alignment_check |

---

## 2. Voice Pack Themes

### Pack A: Warcraft Peon (Gamer Theme)
**Inspiration:** Warcraft III peon voice notifications, CESP v1.0

| Event | Sound Description | Voice Line |
|-------|------------------|-----------|
| session.start | Peon spawning | "Work, work" / "Zug zug" |
| session.end | Peon dying | "Aaaaaargh" |
| agent.spawn | New peon created | "More work?" |
| agent.task_start | Peon begins task | "Yes me lord" |
| agent.task_complete | Peon finishes building | "Job's done!" |
| agent.task_error | Peon can't reach | "I'm not that kind of orc!" |
| fleet.formed | Army assembled | "Lok'tar ogar!" |
| consensus.reached | Alliance formed | "Well done" |
| system.error | Peon under attack | "We're under attack!" |

### Pack B: Sci-Fi (Enterprise Theme)
**Inspiration:** GLaDOS (Portal), HAL 9000

| Event | Sound Description |
|-------|------------------|
| session.start | Ascending activation chime |
| session.end | Soft power-down sequence |
| agent.spawn | Clean initialization beep |
| agent.task_start | "Processing initiated" |
| agent.task_complete | "Task completed successfully" (neutral TTS) |
| agent.task_error | Warning klaxon + "Error detected" |
| consensus.reached | Harmony chord |
| system.error | Escalating alarm |
| alignment.check | "Safety protocol activated" |

### Pack C: Minimalist (Daily Driver)
**Inspiration:** macOS system sounds, Material Design

| Event | Sound Description |
|-------|------------------|
| session.start | Soft ascending two-note chime |
| session.end | Gentle descending chime |
| agent.spawn | Subtle "pop" |
| agent.task_start | Quiet click |
| agent.task_complete | Single clear ping |
| agent.task_error | Double low tone (do-dong) |
| research.breakthrough | Triple ascending chime |
| system.warning | Single low tone |
| long_operation | Subtle heartbeat tick (every 30s) |

---

## 3. Implementation Strategy

### Phase 1: Basic Audio Engine (Week 1)
- Cross-platform playback: `afplay` (macOS), `aplay` (Linux), `paplay` (PulseAudio)
- Fallback to `lyra_audio` package (pygame/sounddevice)
- Sound file management: `.lyra/sounds/` directory
- Hook integration: PostToolUse hook triggers sound events

### Phase 2: Voice Packs (Week 1-2)
- Pack A (Warcraft Peon): 10 sounds, CESP-compliant
- Pack B (Sci-Fi): 10 sounds, generated TTS
- Pack C (Minimalist): 10 sounds, simple tones
- Theme switching: `/sound theme <name>` command

### Phase 3: Advanced (Week 3)
- Adaptive volume: quieter during focus hours
- Productivity mode: disable during meetings (calendar integration)
- Custom sound packs: user-loaded `.wav`/`.mp3` files
- CESP manifest validation

---

## 4. CESP v1.0 Compliance

All sound packs follow the Coding Event Sound Pack Specification:
```json
{
  "cesp_version": "1.0",
  "pack_name": "lyra-warcraft-peon",
  "author": "Lyra Project",
  "license": "MIT",
  "sounds": {
    "session.start": { "file": "peon_ready.wav", "volume": 0.7 },
    "agent.task_complete": { "file": "peon_jobdone.wav", "volume": 0.8 }
  }
}
```

---

## 5. References

| Source | URL | Key Insight |
|--------|-----|-------------|
| Warcraft Peon for Claude Code | freedium-mirror.cfd (Medium) | Hook-based voice notifications in coding agents |
| Sound Effects via Hooks | alexop.dev | Technical implementation of `afplay`/hook integration |
| CESP v1.0 | PeonPing/OpenPeon | Standardized sound pack specification |
| Lyra Voice System V1 | docs/architecture/voice-system.md | Existing Lyra voice design |
