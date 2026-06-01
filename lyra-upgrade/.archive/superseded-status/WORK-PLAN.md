# Lyra Upgrade — Remaining Work Plan

**Created**: 2026-05-31  
**Agent**: general-purpose (a2bf804f670163cdb)

---

## Mission Summary

Complete all remaining research, brainstorms, and plans for the Lyra upgrade project as specified in the master prompt.

---

## Current State

**Completed:**
- ✅ Plans 00-11 (Voice, UI/UX, Memory, Context, Skills, Tools, Plugins, MCP, Commands, Hooks, Sessions, Permissions)
- ✅ Brainstorms: 00, 02-05, 13, 15-17
- ✅ 204/286 sources researched (70.6%)

**Remaining:**
- ⏳ 84 URLs to research
- ⏳ 9 brainstorms to create
- ⏳ 5 plans to create

---

## Task Breakdown

### Task 1: Continue §3.1 Research (17 Claude Code docs)

**Priority**: HIGH (feeds into multiple workstreams)

URLs to fetch:
1. https://code.claude.com/docs/en/skills
2. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
3. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
4. https://platform.claude.com/docs/en/agent-sdk/skills
5. https://code.claude.com/docs/en/plugins-reference
6. https://code.claude.com/docs/en/tools-reference
7. https://code.claude.com/docs/en/goal
8. https://code.claude.com/docs/en/hooks-guide
9. https://code.claude.com/docs/en/hooks
10. https://code.claude.com/docs/en/mcp
11. https://code.claude.com/docs/en/interactive-mode
12. https://code.claude.com/docs/en/commands
13. https://code.claude.com/docs/en/checkpointing
14. https://code.claude.com/docs/en/permissions
15. https://code.claude.com/docs/en/agent-teams
16. https://code.claude.com/docs/en/channels-reference
17. https://code.claude.com/docs/en/env-vars

**Deliverable**: Update findings.md with extracted mechanisms, update source-ledger.md status to "read"

---

### Task 2: Continue §3.2 Research (7 comparable harnesses)

**Priority**: HIGH (feeds into feature parity)

Repos to clone/analyze:
1. https://github.com/nousresearch/hermes-agent
2. https://github.com/Kilo-Org/kilocode
3. https://github.com/Kilo-Org/kilo-marketplace
4. https://github.com/SamurAIGPT/awesome-openclaw
5. https://github.com/anomalyco/opencode (duplicate of #45, verify)
6. https://github.com/bytedance/deer-flow

**Deliverable**: Feature-parity matrix, findings.md updates

---

### Task 3: Create Missing Brainstorms (9 files)

**Priority**: MEDIUM (prerequisite for plans)

Files to create in `brainstorm/`:
1. 01-ui-ux.md (§4.1)
2. 06-tools.md (§4.6)
3. 07-plugins.md (§4.7)
4. 08-mcp.md (§4.8)
5. 09-commands.md (§4.9)
6. 10-hooks.md (§4.10)
7. 11-sessions.md (§4.11)
8. 12-permissions.md (§4.12)
9. 14-full-autonomy.md (§4.14)

**Requirements per brainstorm:**
- ≥3 cross-source ideas
- Reference specific papers/repos
- Identify breakthrough opportunities
- Link to relevant findings

---

### Task 4: Create Missing Plans (5 files)

**Priority**: HIGH (core deliverables)

Files to create in `plans/`:
1. 12-swarm-fleet-channels.md (§4.13) — use brainstorm/13-swarm-fleet-channels.md
2. 13-full-autonomy.md (§4.14) — create brainstorm/14-full-autonomy.md first
3. 14-deep-research.md (§4.15) — use brainstorm/15-deep-research.md
4. 15-reliability-verification.md (§4.16) — use brainstorm/16-reliability-verification.md
5. 16-safety-alignment.md (§4.17) — use brainstorm/17-safety-alignment.md

**Requirements per plan:**
1. Problem statement
2. Evidence synthesis (links to findings)
3. Proposed Lyra design (specific, not generic)
4. Architecture + data model (Mermaid diagrams)
5. Build outline (ordered tasks + dependencies)
6. Multi-provider note (DeepSeek vs Anthropic + fallback)
7. Risks & open questions
8. (A) Parity tier + (B) Breakthrough tier with impact×effort
9. References
10. Changelog

**BREAKTHROUGH REQUIREMENT**: Every plan needs a (B) breakthrough tier that COMBINES techniques from multiple sources. No single-source ports.

---

### Task 5: Research Remaining §3.5 arXiv Papers (67 papers)

**Priority**: MEDIUM (can be done in parallel with other tasks)

**Strategy**: Batch fetch, auto-categorize by workstream (memory→§4.2, context→§4.3, voice→§4.18, routing→§4.5, etc.)

**Deliverable**: Update findings.md with categorized insights

---

### Task 6: Research Remaining §3.7 Skills Systems (9 repos)

**Priority**: MEDIUM (feeds into §4.4 skills plan, which already exists)

Repos:
1. https://github.com/MontrealAI/skillos
2. https://github.com/kepano/obsidian-skills
3. https://github.com/multica-ai/andrej-karpathy-skills
4. https://github.com/forrestchang/andrej-karpathy-skills
5. https://github.com/obra/superpowers
6. https://github.com/microsoft/SkillOpt
7. https://github.com/Imbad0202/academic-research-skills
8. https://github.com/SafeRL-Lab/cheetahclaws
9. https://github.com/HKUDS/CLI-Anything
10. https://github.com/code-yeongyu/oh-my-openagent

**Deliverable**: Update findings.md with skill patterns

---

## Execution Order

**Phase 1: Critical Research** (feeds into brainstorms/plans)
1. Task 1: §3.1 Claude Code docs (17 URLs) — 2-3 hours
2. Task 2: §3.2 Comparable harnesses (7 repos) — 3-4 hours

**Phase 2: Brainstorm Generation** (prerequisite for plans)
3. Task 3: Create 9 missing brainstorms — 3-4 hours

**Phase 3: Plan Generation** (core deliverables)
4. Task 4: Create 5 missing plans — 5-6 hours

**Phase 4: Supplementary Research** (parallel, lower priority)
5. Task 5: §3.5 arXiv papers (67 papers) — 4-5 hours
6. Task 6: §3.7 Skills systems (10 repos) — 2-3 hours

**Total Estimated Time**: 19-25 hours

---

## Success Criteria

- [ ] All 286 sources in source-ledger.md marked as `read`, `failed`, or `unresolved`
- [ ] All 18 brainstorms exist (00-17, excluding 01 which is voice mode)
- [ ] All 17 plans exist (00-16)
- [ ] findings.md contains entries for all researched sources
- [ ] Every plan has both (A) Parity and (B) Breakthrough tiers
- [ ] Every breakthrough combines ≥2 sources
- [ ] PROGRESS.md updated with completion status

---

## Notes

- Work systematically through each phase
- Update source-ledger.md and PROGRESS.md as I go
- If a URL fails, log it and continue (don't block)
- For repos, focus on architecture, unique features, and transferable patterns
- For papers, extract: mechanism, result, limitation, transferable idea, impact, effort, tier

---

**END OF WORK PLAN**
