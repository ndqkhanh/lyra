# Third-party notices

This file records every external work whose code, text, or design we
have **vendored** into Lyra (i.e. copied into the repo, not just
referenced from documentation). Pattern-only inspirations live in
`docs/community-ecosystem.md` instead — they don't carry a license
obligation.

## Section ordering

1. **Vendored code** — per-file attributions for files copied from
   external repos. Each row lists the source repo, source path, the
   destination in this tree, the upstream license, and a one-line
   summary of what was changed during vendoring (if anything).
2. **Vendored documentation** — same shape but for prose (e.g. SKILL.md
   bodies copied or close-paraphrased).
3. **Inspirations** — short list of repos and papers whose *patterns*
   shaped Lyra without carrying a license obligation. These are
   listed for credit and reproducibility, not because we owe them
   under their license.

## 1. Vendored code

*(none yet — Phase 6a vendoring of community skill packs is planned
but not landed in v3.5. Once the first pack is vendored, add a row
per copied file here.)*

Format reminder for future entries:

```markdown
### <repo-name> (<license>)

- Source: `https://github.com/<owner>/<repo>` (commit `<sha>`)
- File(s):
  - `upstream/path/to/file.py` → `packages/lyra-X/src/lyra_X/path/to/file.py`
- Changes: <"verbatim copy" | "renamed module" | "trimmed to MIT-safe subset" | …>
- License: full text reproduced at `licenses/<repo-name>.LICENSE`
```

## 2. Vendored documentation

### Memento-Skills (MIT) — design ideas only

- Source: `https://github.com/Memento-Teams/Memento-Skills`
- File: design memo `docs/research/memento-skills.md` (Phase O design
  doc, no upstream code copied).
- Changes: written from scratch by Lyra contributors as a **rejection
  notes** memo. The Memento README is referenced for context but no
  text is reproduced verbatim.
- License: original Memento-Skills MIT license applies to the upstream
  repo only; this memo is itself MIT under Lyra's license.

## 3. Inspirations (no license obligation)

This list credits authors and works whose *ideas* we built on,
without copying any of their code or text. Listed alphabetically.

### Repositories

- **`anthropics/skills`** — first-party Anthropic skills: docx/pdf/pptx/xlsx
  (source-available; pattern-mined only, **never** vendored).
- **`ArtemKulakov/claude-code-best-practice`** (MIT) — workflow tips
  folded into `docs/research/4-mode-prompts.md` enrichment notes.
- **`chuanqi-shi/awesome-design-md`** (MIT) — design.md style guide
  influenced our SKILL.md authoring conventions.
- **`dair-ai/Prompt-Engineering-Guide`** (MIT) — Chain-of-Thought,
  ReAct, self-consistency, prompt-chaining patterns absorbed into the
  4-mode system prompts (`docs/research/4-mode-prompts.md`).
- **`hesreallyhim/awesome-claude-code`** (MIT) — used as a directory
  to find the other 12 repos in this list.
- **`jarrodwatts/claude-hud`** (MIT) — visual + UX inspiration for
  `lyra hud`. We re-implemented the pipeline natively in Python
  because the upstream couples deeply to Claude Code's stdin /
  transcript JSONL contract.
- **`obra/superpowers`** (MIT) — "force-the-AI-to-plan-first"
  workflow patterns folded into the plan-mode system prompt.
- **`thedotmack/claude-mem`** (**AGPL-3.0**) — long-term memory
  pattern. **Not vendored.** Documented as an optional companion only.
- **`VoltAgent/awesome-claude-code-subagents`** (MIT) — subagent role
  presets influenced the `subagent_type` taxonomy in
  `lyra_core/subagent/registry.py`.
- **`VonHoltenCodes/get-shit-done`** (MIT) — "stop-and-clarify"
  workflow influence on the ask-mode system prompt.
- **`yamadashy/repomix`** (MIT) — wrapped as the `lyra pack` shim;
  upstream binary required, no code copy.
- **karpathy-skills** — under license verification before any
  vendoring; currently inspiration only.

### Papers

- **CALM** (Tencent + Tsinghua, 2026; arXiv:2604.24026) — studied and
  rejected for hosted-API Lyra. See `docs/research/calm-evaluation.md`
  for the full applicability analysis (no Lyra code derives from CALM
  in v3.5.5+; the earlier `BlockStreamingProvider` and `BrierLM` shims
  were removed).
- **Agent-World** (ByteDance, 2026; arXiv:2604.18292) — inspired the
  upcoming `lyra-evals/synth/` task-generation patterns and the
  `lyra-evals/arena/` capability-gap diagnostic loop. Implementation
  scheduled for v3.6.
- **Memento / Read-Write Reflective Learning** (arXiv:2603.18743) —
  inspired Phase O's `SkillLedger` + `lyra skill reflect`. See
  `docs/research/memento-skills.md`.
- **Hermes-agent v0.12 (2026)** — inspired the ContextVars
  concurrency fix in `lyra_core/concurrency.py` and the SkillCurator
  in `lyra_skills/curator.py`. Hermes itself is internal to its
  authors; no code copy.

## 4. License-allowlist policy

For Tier-2 vendoring (see `docs/community-ecosystem.md`) the loader
enforces:

```python
LICENSE_ALLOWLIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}
```

Anything outside that set requires explicit operator opt-in
(`--accept-agpl` etc.) and a corresponding entry in this file
explaining the rationale and the user-facing label.

## Reporting a missing attribution

If you believe Lyra has vendored your code or text without proper
attribution, open an issue at
`github.com/<lyra-org>/lyra/issues/new?template=attribution.md` (or
email the maintainers). We treat attribution issues as priority and
aim to respond within 7 days.
