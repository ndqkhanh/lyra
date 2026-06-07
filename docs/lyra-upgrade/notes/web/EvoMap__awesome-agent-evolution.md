# EvoMap/awesome-agent-evolution -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: A curated awesome-list (registry) for the AI agent self-evolution ecosystem, maintained by EvoMap.

**How it really works**: This is NOT a runtime software project. It is a **data-driven directory** with a single source-of-truth JSON file (`data/projects.json`) that lists ~80+ curated open-source projects across 9 categories (agent evolution, memory systems, protocols, platforms, coding, prompt optimization, safety, embodied AI, community). The README.md is auto-generated from this JSON by `scripts/generate-readme.js`, which places project entries between `<!-- AUTOGEN:section -->` markers. A suite of Node.js scripts (all zero-dependency, using only built-in modules) provides automated maintenance: star-count refreshing via GitHub API, GitHub search for new candidates, link validation, and ecosystem monitoring.

## 2. Architecture & Core Modules

**Data layer**:
- `/data/projects.json` -- JSON array of objects with schema: `{name, repo, description, category, maintainer, tags, stars, paper?}`. This is the sole source of truth.
- `/data/discovered.json` -- Candidate projects found by `discover-projects.js`, tagged `pending/approved/rejected/added`.
- `/data/monitor-results.json` -- Output of ecosystem issue monitoring.

**Scripts (all Node.js, zero external dependencies)**:
- `scripts/generate-readme.js` -- Parses `projects.json`, groups by category, sorts by star count descending, injects into README.md between AUTOGEN markers. Regenerates the full listing from JSON.
- `scripts/update-stars.js` -- Uses `gh api repos/<repo>` in batches of 10 with 1s delay to fetch real-time stargazer counts and writes them back to `projects.json`.
- `scripts/discover-projects.js` -- Searches GitHub via `gh api search/repositories` with 42 pre-programmed queries across 9 categories (e.g. "self-evolving agent", "agent memory system"). Filters results by star count (>=500), deduplicates against existing + previously rejected repos, and writes candidates to `discovered.json`.
- `scripts/adopt-projects.js` -- Moves candidates with `status: "approved"` from `discovered.json` into `projects.json`. Requires human review to set the status field.
- `scripts/check-links.js` -- Validates every repo link via `gh api repos/<repo>`, reports OK/not_found/archived/disabled/redirected. Exits 1 on failures.
- `scripts/monitor-github.js` -- Searches for open GitHub issues matching ecosystem keywords (agent memory, self-evolution, A2A, MCP, etc.). Scores results by keyword relevance. Saves to `monitor-results.json`.
- `scripts/sync-link-cleanup-issue.js` -- Creates or updates a labelled GitHub issue listing broken links found by `check-links.js`, with instructions for cleanup.

**CI/CD (GitHub Actions)**:
- `.github/workflows/update-stars.yml` -- Scheduled: fetches fresh star counts weekly.
- `.github/workflows/check-links.yml` -- Scheduled: validates all links, creates cleanup issues on failure.
- `.github/workflows/monitor.yml` -- Scheduled: runs ecosystem monitoring.

**Data flow pattern**: Data-driven static generation. Single JSON file -> generate-readme.js -> README.md. Maintenance is a series of independent CRUD scripts operating on the same JSON file.

**Architecture pattern**: Registry-as-code with cron-scheduled maintenance automation.

**Production dependencies**: None (Node.js v24 built-in modules only). Runtime requires `gh` CLI (GitHub CLI) authenticated for star fetching, discovery, link checking, and monitoring.

## 3. Performance / Benchmarks

No runtime performance data (not an application). Relevant operational metrics:
- ~80+ curated projects across 9+ categories
- Star fetching: batch size 10, 1s delay between batches -- completes ~80 repos in ~8s network time
- Discovery: 42 search queries, 2s delay between queries -- ~84s for a full discovery scan
- Link checking: serial `gh api` calls, ~2-3s per repo
- README generation: sub-second (pure in-memory JSON manipulation + regex replacement)
- GitHub issue monitoring: 8 queries, returns up to 10 results each, ~65 deduplicated results per run

## 4. Trade-offs

**Wins**:
- Auto-generated README eliminates manual editing errors and stale listings.
- Single JSON data source makes the list machine-readable and portable (other tools can consume `projects.json` directly).
- Zero npm dependencies -- scripts run on Node.js built-ins only, immune to supply-chain issues.
- Automated star freshness via scheduled GitHub Actions.
- Structured discovery pipeline (keyword search -> human review -> adoption) scales curation.
- Link validation + auto-created cleanup issues keeps the list healthy.
- Mermaid taxonomy diagram in README gives quick visual orientation.

**Losses**:
- Star count is the primary sort metric, which is a vanity metric -- it reflects popularity, not quality or relevance.
- Discovery relies entirely on keyword matching against repo descriptions/topics. A relevant project that uses different terminology will be missed.
- No automated quality gating beyond minimum star threshold (500 stars for discovery). No code quality, activity recency, or license checks.
- Categorization is manual after discovery -- humans must decide which bucket a project belongs to.
- No automated detection of stale/abandoned projects (beyond link checking). A project can stop being maintained and remain listed indefinitely.
- The taxonomy is fixed at design time -- adding a new category requires code changes to scripts.
- No test framework, no type checking, no linting configured for the repo itself.

## 5. Design Rationale

The design choices reflect a trade-off between automation and human curation:

- **JSON as database** over SQL/NoSQL: Chosen for simplicity, portability, and git-friendliness. No server, no schema migrations, no connection management. The dataset is small enough (~80 objects) that JSON fits entirely in memory.
- **`gh` CLI over direct GitHub REST API**: Leverages pre-existing authentication (no API token management in scripts), handles pagination implicitly, and works in CI without secret injection.
- **AUTOGEN markers in README**: Allows the README to remain a human-readable Markdown file with hand-written preamble and taxonomy, while ensuring the project listing section is always programmatically correct. Common pattern (see also: `awesome-list` ecosystem).
- **Star count as sort key**: It is objective, universally understood, low-friction to fetch, and hard to game at scale. No other metric (commit frequency, contributor count, issue responsiveness) is as easy to obtain consistently across thousands of repos.
- **Separate discovery/discovered/adoption pipeline**: Decouples automated scraping from human curation. The bot finds candidates; humans decide what gets listed. This prevents the list from being polluted by automated additions.
- **Zero external npm dependencies**: Deliberate choice for a repository expected to have minimal churn. No lockfile to maintain, no Dependabot alerts, no `npm audit`.

## 6. Transfer to Lyra

**One idea**: Adopt the **AUTOGEN-comment marker pattern** for Lyra's documentation suite. Maintain source-of-truth data in structured JSON files (e.g., `docs/lyra-upgrade/data/`) and auto-generate cross-referenced documentation sections from them. This would ensure the "source-ledger", "findings", and "master-plan" documents stay in sync with a canonical data source rather than requiring manual edits in multiple places. Specifically:

- Create a `data/` directory under `docs/lyra-upgrade/` with JSON files tracking: plan statuses, workstream routes, assigned impact/effort scores, and architectural decisions.
- Write a lightweight Node.js/Python script that reads these JSON files and regenerates the appropriate Markdown sections in MASTER-PLAN.md and related documents using `<!-- AUTOGEN: -->` markers.
- This decouples fact authority (structured data) from document presentation (Markdown), making the documentation suite more maintainable as upgrade plans evolve.

**Workstream route**: 4.3 (Documentation & Knowledge Management)

**Impact**: 6 (Reduces documentation drift across multiple coupled documents; enables adding a rendered summary view; makes plan status self-consistent.)

**Effort**: 2 (Low -- the pattern is simple to implement; Lyra already has the data in prose form; converting to JSON and writing the generation script is a few hours of work; no external dependencies needed if using Node.js built-ins.)

**Tier**: Quick Win

**License note**: CC-BY-SA 4.0. If Lyra incorporates or adapts any scripts from this repository, it must provide attribution to EvoMap and distribute adaptations under the same CC-BY-SA 4.0 license.
