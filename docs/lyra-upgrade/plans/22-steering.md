# Human Steering & Interruptibility — Plan (§4.22)

> Run 1 — June 3, 2026

## Plain-Language Summary

Lyra's steering system lets you redirect, interrupt, and correct agents mid-run without restarting. Peek at what any agent is doing from the fleet view. Inject corrections in natural language ("use async/await, not callbacks"). Undo mistakes. The agent learns your preferences over time — common corrections become defaults.

## Key Features

1. **Steer-by-Exception:** Fleet view shows state-grouped rows with cheap-model summaries. Peek (latest output + current question), reply with Tab-suggested responses, attach for full conversation. Never need to babysit.
2. **Mid-Run Interruption:** Inject a message at any time — agent processes it at next turn boundary. "Stop, that approach is wrong. Use X instead."
3. **Natural-Language Correction Loop:** Human says "No, use async/await instead of callbacks" → agent identifies the specific decision being corrected → applies correction → re-executes from that point.
4. **Undo/Rewind:** Agent actions are reversible — undo last N actions, rewind to checkpoint. Integration with §4.11 session checkpointing.
5. **Preference Learning:** Common corrections stored in semantic memory (§4.2). "You always correct me to use async/await → I'll default to that for Python tasks."
6. **Trust Calibration:** Show confidence alongside suggestions. Low confidence → explicit "I'm 60% sure — please verify." High confidence → "I'm 92% confident in this."

## Integration

- Fleet view (§4.13) is the primary steering surface
- Voice (§4.18) enables spoken corrections
- Self-knowledge (§4.19) provides the confidence signal
- Memory (§4.2) stores learned preferences

**Impact:** 4 | **Effort:** 3 | **Tier:** (A) Parity

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Agent View (§3.1) | Steer-by-exception: peek without attach, suggested reply (Tab), state-grouped rows, PR status indicators |
| Claude Code Fleet UX (§3.1) | Cheap-model row summaries (≤15s refresh) enable at-a-glance steering without opening transcripts |
| InsightAgent (2504.14822) | Interactive visualization of agent trajectories for real-time human monitoring/feedback |
| Identity Skews (2510.07517) | Anonymized steering prevents sycophancy — agent evaluates correction on content, not identity |

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| lyra-human-interaction (package) | EXTEND: natural-language correction, preference learning | Low — existing interaction patterns |
| lyra-cockpit (package) | EXTEND: fleet-view-as-steering-surface | Low — existing monitoring |
| Preference memory | ADD: store corrections → auto-apply to future similar tasks | None — new module |

## Expert Review

**Senior UX:** "The key insight from Agent View: users should steer by exception, not by watching. When a session needs input, it surfaces. Otherwise, it stays out of the way. The cheap-model row summary is the enabler — one line tells you everything."

**Skeptic:** "Preference learning from corrections sounds great but has a cold-start problem. Ship without it first; add when there are enough corrections to learn from." → ADOPTED.
