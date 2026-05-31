# Implementation Backlog

**Purpose**: Track work discovered during implementation that the plans missed,
or non-blocking improvements deferred from reviews. Ranked by impact × effort.

---

## Deferred from Plans (known scope gaps)

| # | Item | Impact | Effort | Priority | Plan Ref |
|---|------|--------|--------|----------|----------|
| 1 | Wire lyra_provider into all capability packages (tools, MCP, skills, voice, permissions) | HIGH | LARGE | P0 | §4.5-§4.12 |
| 2 | GoogleProvider full adapter implementation | MEDIUM | MEDIUM | P1 | §4.5 |
| 3 | OpenWeightsProvider adapter | LOW | SMALL | P2 | §4.5 |
| 4 | Plugin system package (lyra-plugins) | MEDIUM | MEDIUM | P1 | §4.7 |
| 5 | Mermaid architecture diagrams in README | MEDIUM | SMALL | P1 | §6 |

## Discovered During Implementation

| # | Item | Discovered In | Impact | Effort | Priority |
|---|------|--------------|--------|--------|----------|
| 1 | Zero capability packages import from lyra_provider — provider abstraction is an island | Tier 4 scout audit | HIGH | LARGE | P0 |
| 2 | lyra-tools model_routing.py hardcodes Claude-only model IDs | Tier 4 scout audit | HIGH | MEDIUM | P0 |
| 3 | toolspec.py produces Anthropic-style schemas, not lyra_provider ToolSchema | Tier 4 scout audit | HIGH | MEDIUM | P0 |
| 4 | AVP middleware built but not universally wired into tool execution path | Tier 3 build | HIGH | LARGE | P0 |
| 5 | TKG write-path not universally enforced — memory as central nervous system is partial | Architecture audit | HIGH | LARGE | P0 |
| 6 | Per-tier review gate not executed (expert panel review) | Per-tier gate | HIGH | LARGE | P0 |
| 7 | End-to-end test-plan.md flow not executed | Final pass | HIGH | LARGE | P0 |
| 8 | Existing router test test_get_fallback_model is flaky (passes in isolation) | Tier 1 testing | LOW | SMALL | P2 |

## Review Deferrals (non-blocking nits)

| # | Item | Review | Impact | Effort | Priority |
|---|------|--------|--------|--------|----------|
| — | None yet (review gate not executed) | — | — | — | — |

---
