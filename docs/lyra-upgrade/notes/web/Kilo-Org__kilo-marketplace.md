# Kilo-Org/kilo-marketplace -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline feature:** A community-curated, YAML-driven registry of Skills, MCP Servers, Modes, and Agents for the Kilo Code ecosystem (VS Code AI extension, CLI, and compatible agents). The repo does NOT host skill source code directly; it serves as a federated index that maps skill names to externally-hosted GitHub repositories, with metadata cached locally via sparse git checkout.

**How it actually works:**

The repo is 100% configuration/codegen infrastructure -- no runtime server, no database, no end-user application. Four script-generated `marketplace.yaml` files (one per resource type: skills, mcps, modes, agents) serve as the canonical discovery layer consumed by Kilo Code clients. Each script reads resource-specific metadata files from subdirectories and emits a unified YAML manifest:

- **Skills** (`skills/marketplace.yaml`, 364 lines): Reads YAML frontmatter from each `skills/<name>/SKILL.md` via `gray-matter`, emits a sorted YAML list with `id`, `description` (folded block scalar), `category`, `githubUrl`, `rawUrl`, and a tarball download URL.
- **MCP Servers** (`mcps/marketplace.yaml`, 3032 lines): Reads `mcps/<name>/MCP.yaml` directly via `yaml.parse`, merges into a flat list sorted by `id`. Each entry specifies installation configs (NPX command, Docker args, SSE endpoint, env vars, parameters).
- **Modes** (`modes/marketplace.yaml`, 307 lines): Same pattern as MCPs, reading `modes/<name>/MODE.yaml` files that define agent role definitions, tool group permissions, and file restrictions.
- **Agents** (`agents/marketplace.yaml`, 434 lines): Reads `agents/<name>/AGENT_DEFINITION.md` with YAML frontmatter (via `gray-matter`), extracting structured agent config (mode, model, temperature, permission, color, steps, hidden) plus the Markdown body as the agent prompt.

**Skill lifecycle -- the key innovation:**

1. **Add**: `bin/add-remote-skill.ts` takes a GitHub URL, does a sparse git checkout of only the skill directory from the external repo, copies it locally, and injects `metadata.source` (repository + path) into the SKILL.md frontmatter. Source code stays in the author's repo.
2. **Sync**: `bin/update-skills.ts` groups all skills by upstream repo, does a single sparse checkout per repo, replaces local content with upstream, re-applies source metadata, copies LICENSE files, and re-applies any `local.patch` files.
3. **Local mods**: `bin/generate-patches.ts` diffs the locally normalized upstream against the current local state, saving any differences as `skills/<name>/local.patch`. These patches survive upstream syncs via `patch -p2 --forward`.
4. **Serve**: Marketplace YAMLs are committed to git; Kilo Code clients fetch them directly from `raw.githubusercontent.com` or as release tarballs.

Dependencies (from `bin/package.json`): `gray-matter` (YAML frontmatter parsing), `tsx` (TypeScript execution), `yaml` (YAML serialization).

## 2. Architecture & Core Modules (entry points, data flow, patterns)

```
bin/
├── package.json              # Dependencies: gray-matter, tsx, yaml
├── add-remote-skill.ts       # Single-skill import from GitHub (sparse checkout)
├── update-skills.ts          # Bulk sync all skills from upstream repos
├── generate-patches.ts       # Generate local.patch for diverged skills
├── generate-skill-marketplace.ts  # Build skills/marketplace.yaml
├── generate-mcps-marketplace.ts   # Build mcps/marketplace.yaml
├── generate-modes-marketplace.ts  # Build modes/marketplace.yaml
└── generate-agents-marketplace.ts # Build agents/marketplace.yaml

.kilocode/skills/add-remote-skill/SKILL.md  # Agent-facing skill to invoke add-remote-skill.ts
.kilo/kilo.json                            # Schema marker for Kilo Code
```

**Data flow for a new skill:**
```
User provides GitHub URL
  -> add-remote-skill.ts (sparse checkout, copy, inject metadata)
  -> generate-skill-marketplace.ts (rebuild index)
  -> commit marketplace.yaml
  -> Kilo Code clients fetch via raw.githubusercontent.com
```

**Key design patterns:**
- **Index-as-config**: Marketplaces are static YAML files, not a live service. Zero operational cost.
- **Sparse checkout for sync**: Uses `git init; git remote add; git config core.sparseCheckout true; git fetch --depth 1; git checkout FETCH_HEAD` -- clones only the needed paths, not the full upstream repo.
- **Patch-based local customization**: `local.patch` files let the marketplace maintainer apply site-local fixes that survive upstream syncs. Patch preservation across syncs is explicitly handled.
- **Folded-block YAML scalars**: Description fields use `>-` chomping (strip trailing newline, fold internal newlines) for readable YAML output at `lineWidth: 120`.
- **Frontmatter-driven metadata**: SKILL.md, AGENT_DEFINITION.md, MODE.yaml, MCP.yaml all use YAML frontmatter as the structured data carrier. The Markdown body is the execution instructions.

## 3. Performance/Benchmarks

No benchmark data exists in the repo. This is a metadata-index repository, not a runtime system. The relevant metric is the size of the marketplace: the repo curates approximately 39 skills, 60+ MCP servers, 8 modes, and 8 agents. The combined `marketplace.yaml` files total ~4137 lines. The `update-skills.ts` sync uses `--depth 1` shallow fetches, so per-skill sync cost is bounded.

## 4. Trade-offs (wins vs loses)

**Wins:**
- **Zero operational overhead**: No server, database, API, or authentication infrastructure. The entire marketplace is flat files on GitHub and raw.githubusercontent.com.
- **Federated ownership**: Skill authors own their repos. They push updates independently; the marketplace syncs them. No bottleneck on the marketplace maintainer for content updates.
- **Patch survival**: `local.patch` files let the marketplace maintainer apply customizations that persist across upstream syncs. This is critical for a curated index that sources from many independent repos.
- **Sparse checkout efficiency**: Only the specific skill path is cloned, not the upstream repo. For a skill directory that is typically <100KB, this is extremely fast.
- **Simple contribution model**: External authors submit a single PR via `add-remote-skill.ts`, no need to understand the full toolchain.

**Loses:**
- **No versioning or dependency management**: Skills are pinned to `HEAD` of the upstream branch. There is no semantic versioning, no lockfile, no deprecation mechanism. An upstream breaking change immediately breaks the marketplace until the next sync.
- **No discovery beyond YAML**: No search, no filtering, no rating, no usage analytics. Clients must parse the full YAML and filter client-side.
- **Single-commit linear history**: The entire repo has exactly 1 commit (a squash merge). No issue/PR trail, no changelog, no design rationale in commit messages.
- **No testing or validation**: The codegen scripts have no tests, no schema validation, no CI pipeline. A malformed SKILL.md frontmatter silently produces a broken marketplace.yaml.
- **No security model**: MCP configurations embed raw JSON with env-var placeholders (`{{API_KEY}}`). There is no validation that keys referenced in `parameters` match `env` keys, and no guidance on secret storage.
- **Tarball drift risk**: The `content` links point to release tarballs at `releases/download/skills-latest/`, but there is no CI workflow generating these releases. The tarball URLs would 404 on first commit without external infrastructure.

**From open issues:**
- Issue #79: JSONC comments/trailing commas in global config cause hangs during MCP install -- the install flow uses strict JSON.parse, not a JSON5/tolerant parser.
- Issue #83: Subagent issue (non-English title suggests internationalization gap).
- Several "add skill" enhancement requests (issues #57, #56, #11, #10) tagged with `kilo-triaged` and `kilo-auto-fix`, suggesting an automated triage pipeline exists but is not visible in the repo itself.

## 5. Design Rationale (why this approach)

The repository is explicitly a fork of `ComposioHQ/awesome-claude-skills` (per NOTICE). The design choices reflect a philosophy of **maximum simplicity**: the marketplace is just files on GitHub, the authority is the local `git checkout + patch`, and the primary operation is `cpSync` + frontmatter injection.

The external-hosting requirement (CONTRIBUTING.md: "Kilo Marketplace does not host the source code for contributed skills directly") is a deliberate architectural choice to avoid becoming a bottleneck for skill authors. This mirrors the npm/PyPI registry model -- separate registry from package hosting -- but at a much lighter weight (no database, no authentication, no API).

The `local.patch` system is the most interesting architectural decision. Rather than forking every upstream skill (which would lose the connection to the original), the marketplace tracks the delta via unified diff and re-applies it after each sync. This is a pragmatic middle ground between "always use upstream HEAD" and "fork everything."

The sparse checkout technique (`git init + git fetch --depth 1 + git checkout FETCH_HEAD`) is notable for its minimal dependency footprint -- no GitHub API calls, no `gh` CLI, no tokens needed for public repos. It works with raw git plumbing, which is universally available.

## 6. Transfer to Lyra (one idea + route + Impact/Effort/Tier + LICENSE)

**Idea: Federated plugin index with patch-based customization.**

Lyra already has a plugin architecture. Kilo Marketplace's sparse-index pattern -- where the registry stores only metadata and the real code lives in distributed repos -- is directly applicable to Lyra's plugin system. The key transferable mechanism is:

1. **Plugin registry as static YAML**: Lyra could maintain a `plugins/marketplace.yaml` that indexes externally-hosted plugin repos. The Lyra client fetches this YAML, presents options to the user, and installs plugins directly from their source repos. No server, no database.
2. **Patch-based local overrides**: When a user or Lyra maintainer needs to customize a plugin (e.g., add a model provider shim, fix a compatibility issue), the difference is saved as a `local.patch` that survives `plugin update`. This avoids forking the plugin and losing upstream updates.
3. **Sparse checkout installer**: The `git init; git sparse-checkout; git fetch --depth 1` pattern is the most portable, dependency-free way to install plugins from git repos. No npm, no pip, no Docker needed at the registry level.

**Workstream Route:** Section 4.x (Plugins/Extensions) -- specifically a new subsection under plugin lifecycle management.

- **Impact:** 7/10 -- Solves the discoverability and maintenance tension for Lyra's plugin ecosystem. Currently, if Lyra has a plugin system, each plugin must be individually found, evaluated, and updated. A federated index with automated sync would dramatically lower the friction for both plugin authors and users. The `local.patch` mechanism is especially valuable for enterprise deployments that need to apply site-specific patches without losing the upstream update stream.
- **Effort:** 3/10 -- The entire Kilo Marketplace infrastructure is ~500 lines of TypeScript, three npm dependencies, and zero runtime infrastructure. A Lyra plugin registry would be roughly the same scale: a codegen script for the index, a sparse-checkout installer, and a patch manager. No database, no server, no auth system.
- **Tier:** Tier 2 (Medium-term, `§4.x-plugins`). This is not a core architectural change -- it is a quality-of-life improvement for the plugin ecosystem. It should be planned after the base plugin architecture is stabilized.

**LICENSE:** Apache 2.0 (same as Kilo Marketplace). Compatible with any permissive or weak-copyleft license Lyra might use.
