# Brainstorm Enhancement Plan - Run 2

**Purpose**: Ensure every workstream has ≥3 cross-source breakthrough ideas before finalizing plans.

---

## Current Brainstorm Files Status

| File | Exists | Ideas Count | Status | Action Needed |
|------|--------|-------------|--------|---------------|
| 00-voice-mode.md | ✅ | TBD | CHECK | Verify ≥3 ideas, enhance with new voice research |
| 02-memory-architecture.md | ✅ | TBD | CHECK | Verify ≥3 ideas, enhance with MemAgent papers |
| 03-context-optimization.md | ✅ | TBD | CHECK | Verify ≥3 ideas |
| 04-skills-system.md | ✅ | TBD | CHECK | Verify ≥3 ideas, enhance with new skills research |
| 05-model-router.md | ✅ | TBD | CHECK | Verify ≥3 ideas, enhance with routing research |
| 13-swarm-fleet-channels.md | ✅ | TBD | CHECK | Verify ≥3 ideas |
| 15-deep-research.md | ✅ | TBD | CHECK | Verify ≥3 ideas |
| 16-reliability-verification.md | ✅ | TBD | CHECK | Verify ≥3 ideas |
| 17-safety-alignment.md | ✅ | TBD | CHECK | Verify ≥3 ideas |

**Missing brainstorm files** (need creation):
- 01-ui-ux.md (§4.1)
- 06-plugins.md (§4.7)
- 07-mcp.md (§4.8)
- 08-commands-interactive.md (§4.9)
- 09-hooks-automation.md (§4.10)
- 10-sessions-checkpointing.md (§4.11)
- 11-permissions-credentials.md (§4.12)
- 12-full-autonomy.md (§4.14)
- 18-rmux-rebuild.md (§5.1)
- 19-multi-tenancy.md (§5.2)
- 20-voice-sound-sfx.md (§5.3 - fold into 00-voice-mode)

---

## Brainstorm Quality Criteria

Each brainstorm file MUST contain:

1. **≥3 distinct cross-source ideas**
   - Each idea combines techniques from ≥2 different sources
   - Each idea goes BEYOND what any single source does
   - Each idea names the sources fused

2. **For each idea**:
   - **Mechanism**: How the combination works
   - **Why it wins**: Argument for why fusion > individual sources
   - **Impact × Effort**: Rough ratings (1-5 scale)
   - **Failure modes**: What could go wrong

3. **Stress-testing**:
   - Note why ideas might NOT work
   - Identify dependencies and prerequisites
   - Flag research gaps

4. **Promotion path**:
   - Pick strongest 1-2 ideas for plan's (B) breakthrough tier
   - Keep rest as "parked ideas" for future runs

---

## Enhancement Workflow

**Phase 1**: Audit existing brainstorm files
- Read each file
- Count cross-source ideas
- Verify each idea combines ≥2 sources
- Check for failure mode analysis

**Phase 2**: Enhance weak files
- Add missing cross-source ideas
- Strengthen existing ideas with new research
- Add failure mode analysis where missing

**Phase 3**: Create missing files
- Generate ≥3 cross-source ideas per workstream
- Use findings.md as source material
- Follow quality criteria above

**Phase 4**: Link to plans
- Ensure each plan references its brainstorm file
- Promote strongest ideas to plan's (B) breakthrough tier
- Document parked ideas for future consideration

---

## Cross-Source Fusion Examples

**Good cross-source idea**:
> **Idea**: Fuse SkillNet's 5-D quality evaluation (§3.7) with Darwin Gödel Machine's empirical validation (§3.18) and A-MAC's admission control (§3.4) into a **self-improving skill curator** that:
> - Auto-generates skills from execution traces (DGM)
> - Scores them on 5 dimensions (SkillNet)
> - Admits only high-quality skills to the library (A-MAC)
> - Empirically validates improvements on benchmarks (DGM)
>
> **Why it wins**: No single source does all four. SkillNet creates but doesn't validate empirically. DGM validates but doesn't score quality dimensions. A-MAC filters but doesn't generate.
>
> **Sources fused**: SkillNet (§3.7), Darwin Gödel Machine (§3.18), A-MAC (§3.4)

**Bad (not cross-source)**:
> **Idea**: Use SkillNet's skill marketplace.
> 
> **Why bad**: This is just porting SkillNet, not combining sources.

---

## Priority Order

1. **Voice Mode** (00-voice-mode.md) - Flagship, enhance first
2. **Memory** (02-memory-architecture.md) - Core capability
3. **Skills** (04-skills-system.md) - Self-improvement foundation
4. **Model Router** (05-model-router.md) - Cost optimization
5. **Safety** (17-safety-alignment.md) - Critical for production
6. **Reliability** (16-reliability-verification.md) - Production readiness
7. **Deep Research** (15-deep-research.md) - Differentiator
8. **Swarm** (13-swarm-fleet-channels.md) - Scalability
9. **Context** (03-context-optimization.md) - Performance
10. **All others** - Feature parity

---

## Next Steps

After research agents complete:
1. Read all findings.md sections
2. Audit existing brainstorm files
3. Enhance weak files with new research
4. Create missing brainstorm files
5. Link brainstorms to plans
6. Verify every plan has (B) breakthrough tier

---

**Status**: FRAMEWORK READY  
**Trigger**: After Batch 1 research agents complete
