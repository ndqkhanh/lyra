# Skills System — Plan (§4.4)

> Run 3, 2026-06-03

## Plain-Language Summary

Lyra's skills system loads markdown skill files from the filesystem using progressive disclosure (metadata first, body on selection, resources on demand). It auto-generates skill packages from GitHub repos, PDFs, and conversation logs, organizes them into a similarity/composition/dependency graph, rates them on 5 quality dimensions, and optimizes them via gradient-free prompt evolution. Works across ALL providers — the loader is harness-level, not API-level.

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Skills docs (§3.1) | 3-level progressive disclosure, dynamic context injection (!`cmd`), 4-state visibility model |
| Agent Skills open standard | SKILL.md + YAML frontmatter, works across Claude Code/Codex/Gemini CLI/Cursor/Hermes |
| SkillNet (2603.04448) | Auto-generates skill packages, 5-dimension quality scoring, skill graph (similarity/composition/dependency) |
| GEPA (ICLR 2026 Oral) | Gradient-free prompt evolution, outperforms GRPO, works on any provider |
| TF-TTCL (2604.13552) | Explore-Reflect-Steer loop, training-free, works on closed-model providers |
| alirezarezvani/claude-skills (§3.7) | 330+ skills, 30+ agents, 70+ commands — bootstrap Lyra's skill library |

## Proposed Lyra Design

### (A) Parity — Harness-Level Skills Loader

1. **Progressive disclosure loader:**
   - Level 1: frontmatter (name + description) → pre-loaded at session start
   - Level 2: SKILL.md body → loaded on invocation
   - Level 3: referenced files (scripts, references, assets) → loaded on demand

2. **Provider-agnostic injection:** Read SKILL.md from filesystem, inject into messages array. Never depend on provider-specific "skills" endpoint. Strip/translate Claude-only frontmatter fields for non-Claude providers.

3. **Skill selection:** Deterministic keyword/embedding match as fallback for providers with unreliable auto-trigger. Per-provider trigger strategy (Claude: auto, DeepSeek: keyword-based).

4. **Bundled starter skills:** Port from superpowers/oh-my-claude/claude-skills: code-review, debug, tdd, plan, verify, loop, brainstorm, deep-research.

### (B) Breakthrough — SkillNet Graph + GEPA Evolution

5. **SkillNet graph:** Similarity/composition/dependency edges between skills. "Install skill X and get Y, Z recommended." Auto-generated from GitHub/PDFs/trajectories.
6. **GEPA prompt evolution:** Generate skill variants → evaluate on task → keep winners → mutate → repeat. Gradient-free, works on any provider.
7. **5-dimension quality scoring:** Correctness, completeness, clarity, efficiency, safety.

## Build Outline

1. SKILL.md parser + frontmatter extractor (week 1)
2. Progressive disclosure loader + provider-agnostic injection (week 1)
3. Deterministic skill matching + per-provider trigger config (week 2)
4. Bundled starter skills (port 8-10 skills) (week 2)
5. SkillNet graph builder + quality scorer (week 3-4)
6. GEPA prompt evolution loop (week 4-5)

## Multi-Provider Note

Skill loading is harness-level (filesystem → messages array). On DeepSeek: deterministic matching preferred (keyword/embedding) over auto-trigger. Claude-only frontmatter (model: pin, dynamic-injection extensions) stripped/translated for non-Claude providers. Provider × skill compatibility matrix documented.

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| skill_format.py (421L) | KEEP — already solid | None |
| lyra-skills (package) | EXTEND: progressive disclosure, SkillNet graph, GEPA | Medium |
| lyra-skill-loader | EXTEND: per-provider trigger config | Low |
| lyra-skill-evolution | EXTEND: GEPA gradient-free evolution | Medium |

## Expert Review

**Adversarial Skeptic:** "330+ skills from claude-skills is a bootstrap goldmine but also a quality risk. Ship with 8-10 vetted skills; let users install more from the graph." → ADOPTED.

**Senior AI Engineer:** "GEPA works on any provider because it's prompt-level — generate variants, test them, keep winners. No gradient access needed. This is the right evolution approach for multi-provider Lyra."

**Impact:** 5 | **Effort:** 4 | **Tier:** (A) Parity + (B) Breakthrough
