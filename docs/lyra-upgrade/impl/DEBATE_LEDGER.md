# DEBATE_LEDGER.md — Architecture Decision Records

> Each architecture call records: who objected, on what grounds, how resolved, steelman of rejected alternative.

## D001: Rebuild substrate from plans vs recover bytecode

- **Context:** ~50+ Python files exist only as .pyc bytecode (CLI, providers, advanced memory, routing)
- **Proposal:** Rebuild from plans + synthesis rather than decompiling bytecode
- **Objection (Skeptic):** Decompiling bytecode might recover working implementations faster than rebuilding
- **Resolution:** Plans provide complete specifications backed by 546 sources. Bytecode is of unknown quality, may not match plans, and carries licensing risk (unknown origin). Rebuilding ensures clean-room compliance and plan traceability.
- **Steelman of rejected:** Bytecode decompilation could reveal implementation patterns worth studying — do that as research, not as source of truth.
- **Verdict:** REBUILD from plans. ✅

## D002: Provider abstraction first (S1)

- **Context:** Everything depends on real LLM calls — agents, memory, tools, voice
- **Proposal:** Build provider abstraction before any other item
- **Objection (Skeptic):** Agent loop (S9) could use a hardcoded provider initially to unblock other workstreams
- **Resolution:** Hardcoded provider creates rework when abstraction is added later. The plan specifies provider-swappable design; building it first avoids migration cost. The existing `adapters/` and `routing/` bytecode proves the architecture is understood.
- **Steelman of rejected:** Start with Anthropic-only, add abstraction later when DeepSeek is needed for testing.
- **Verdict:** PROVIDER FIRST. ✅

## D003: Clean-room discipline

- **Context:** 118 cloned repos have varying licenses. Lyra is MIT.
- **Proposal:** Port ideas only from repos with compatible licenses; never copy code from GPL/incompatible sources
- **Objection (Skeptic):** Many repos are Apache 2.0 / MIT — compatible. The restriction adds process overhead.
- **Resolution:** Process overhead is acceptable for legal safety. Each port must cite the repo note's LICENSE field. GPL code is studied for ideas but reimplemented independently.
- **Steelman of rejected:** Use Apache 2.0 code freely (compatible with MIT). Only restrict GPL/AGPL.
- **Verdict:** Apache 2.0 / MIT / Unlicense = OK to port ideas. GPL/AGPL = study only, reimplement independently. ✅
