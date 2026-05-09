# Lyra and the broader Claude-Code ecosystem

> **Status:** v3.5 snapshot. This page is the **policy + process**
> layer for Lyra's relationship with the wider Claude-Code /
> coding-agent ecosystem — vendoring tiers, license gates, and the
> rules for adding new repos. The **data** (one row per repo with
> license, mode, and Lyra implementation file) lives at
> [Reference repositories](research/repos.md), the canonical
> absorption matrix that subsumes the 13-row Claude-Code ecosystem
> table that previously lived here, plus every paper reference impl,
> adjacent infra, model weight, and benchmark corpus Lyra cites.

If you arrived here asking *"should I use repo X with Lyra?"* —
that question is answered, per-repo, in
[`docs/research/repos.md`](research/repos.md).

If you arrived here asking *"how does Lyra decide what to vendor
vs. pattern-mine vs. reject?"* — that's this page.

## Quick links to the data

| Looking for… | → |
|---|---|
| The 13 Claude-Code ecosystem repos (`obra/superpowers`, `anthropics/skills`, `claude-mem`, `repomix`, `claude-hud`, …) | [`research/repos.md` § A](research/repos.md#a-claude-code--coding-agent-ecosystem) |
| Reference impls of papers we cite (Voyager, DSPy, MetaGPT, ChatDev, MAS_Diversity, …) | [`research/repos.md` § B](research/repos.md#b-paper-reference-implementations) |
| Adjacent infra (CubeSandbox, phantom, moraine, gnomon-hir, gbrain, hermes-agent) | [`research/repos.md` § C](research/repos.md#c-adjacent-infrastructure) |
| Skills + MCP ecosystem (anthropics/skills, skills-mcp, Memento-Skills) | [`research/repos.md` § D](research/repos.md#d-skills--mcp-ecosystem) |
| Model weights + benchmark corpora (DeepSeek-R1, EAGLE-3 weights, prm800k, τ-bench, terminal-bench-2, SWELancer) | [`research/repos.md` § E](research/repos.md#e-model-weights--benchmark-corpora) |
| Industry signals (GPT-5.5, GLM-5.1, Cline / Aider / OpenHands stars) | [`research/repos.md` § F](research/repos.md#f-industry-signals-model-releases-talks-market) |
| All 37 papers Lyra cites + how each one landed in Lyra | [`research/papers.md`](research/papers.md) |

## Star-count caveat

The user's claimed star counts are mostly **inflated by 10×–100×**
versus reality (verified via `gh api repos/<owner>/<name>`). For
example, "everything-claude-code – 153,000 ⭐" cross-referenced to a
canonical curated list with ~5k–8k stars at the time of writing (May
2026). We treat the relative ordering as a popularity signal — the
absolute numbers as marketing.

## Vendoring policy

We adopted **three tiers** of integration with community repos:

### Tier 1: pattern-mine (preferred default)

Read the upstream's docs / SKILL.md, distill the *idea*, write a
clean Lyra-native skill or doc that credits the source in a footer.
**No code copy, no SKILL.md copy.** Used for AGPL repos, mixed-license
repos, and any repo whose docs we summarised in plan-mode research.

### Tier 2: selectively vendor

For MIT / Apache-2.0 / BSD repos, copy specific files into
`packages/lyra-skills/src/lyra_skills/packs/community/<repo>/` with:

- per-file license header preserved,
- attribution footer in `THIRD_PARTY_NOTICES.md`,
- `lyra-skills/installer.py` `LICENSE_ALLOWLIST` updated,
- the SKILL.md frontmatter `id` re-namespaced to
  `community/<repo>/<skill>` to avoid collision with first-party packs.

### Tier 3: optional integration (no code copy)

For tools that are full applications (repomix, claude-mem, claude-hud)
we wrap them with a small shim and document them as **optional** —
the user installs upstream separately and Lyra calls it via subprocess.

## License gates

The skill loader (`lyra_skills/loader.py`, planned Phase 6 patch) will
enforce a `LICENSE_ALLOWLIST`:

```python
LICENSE_ALLOWLIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}
```

Skills with frontmatter `license:` outside this set fail to load
unless the operator passes `--accept-agpl` or `--accept-source-available`.
The default is conservative on purpose — Lyra is MIT and we will not
contaminate users' projects by silently mixing licenses.

## Optional companion docs

For each Tier-3 integration we ship a one-page guide at
`docs/integrations/<tool>.md`:

- `repomix.md` — how to use `lyra pack` (calls upstream `repomix`)
- `claude-mem.md` — running claude-mem as a parallel memory store
- `claude-hud.md` — superseded by native `lyra hud`; documented for
  users coming from upstream Claude Code

## How to update the matrix

When evaluating a new community repo, the per-row workflow lives at
[`docs/research/repos.md` § How to add a new repo to this matrix](research/repos.md#how-to-add-a-new-repo-to-this-matrix).
The seven-step recipe in summary:

1. Verify star count via `gh api repos/<owner>/<repo>`.
2. Check license via `gh api repos/<owner>/<repo>/license`.
3. Pick the correct section (A–F) of `repos.md` based on what the
   repo *is*.
4. If MIT/Apache/BSD: skim 5–10 SKILL.md files for quality; pick
   1–3 to vendor under `packs/community/<repo>/`.
5. If AGPL or source-available: pattern-mine only; document the
   *idea* under the relevant `docs/research/<topic>.md` design memo.
6. Add a row to `repos.md` with verdict + paragraph if the repo
   warrants explanation.
7. Append attribution to `THIRD_PARTY_NOTICES.md`.

## See also

- [Reference papers](research/papers.md) — the canonical bibliography
  with one row per paper, absorption mode, and Lyra implementation
  file.
- [Reference repositories](research/repos.md) — the canonical repo
  matrix this page used to host inline.
- `THIRD_PARTY_NOTICES.md` — per-vendored-file licenses + attribution.
- [PolyKV evaluation](research/polykv-evaluation.md) and
  [CALM evaluation](research/calm-evaluation.md) — how a *paper*
  (not a repo) is evaluated for harness applicability.
- `packages/lyra-skills/src/lyra_skills/installer.py` — the
  `LICENSE_ALLOWLIST` enforcement.
- `CONTRIBUTING.md` § "Skills (SKILL.md)" — author-facing rules.
