# Skills System -- Deep Dive

## 1. Executive Summary

Lyra's skills system is the knowledge substrate of the agent harness. It implements a complete lifecycle: skills are authored as structured Markdown files (SKILL.md), discovered and parsed by a tiered loader, matched against user intents through a multi-stage cascade router, activated with progressive disclosure, tracked via an outcome ledger, graded by a deterministic curator, extracted from successful trajectories, iteratively optimized through a closed-loop scorer, and evolved across generations via Pareto-frontier search and multi-agent councils.

The system spans two core packages: `lyra-skills` (the production runtime -- loader, router, extractor, curator, compaction, state management, semantic search, provenance bridge to Argus) and `lyra-evolution` (the research-grade evolution layer -- Escher-Loop RSI, GEAR-Evolve, Council Mode, PRISM drift detection, code generation with sandboxed verification). A legacy `src/skills/` module provides the original bare-bones parser and registry used by the first-generation Lyra TUI.

Key architectural decisions:

- **Skill format is the Agent Skills open standard** (SKILL.md with YAML frontmatter), compatible with Claude Code, Cursor, and the emerging SkillOS ecosystem.
- **Routing is harness-level, not provider-API-level**. The default token-overlap router requires no embeddings or external models. The optional Argus cascade adds BM25, semantic embeddings, cross-encoders, and telemetry-driven re-ranking behind the same interface.
- **All grading and curation is deterministic**. The curator uses precomputed utility scores from the ledger and runs in under 100ms for hundreds of skills with zero LLM calls. The extractor uses a rubric-first approach with HARD/SOFT criteria and detects leaked secrets regexically.
- **Self-evolution is gated by bounded edits**. The optimizer emits one of four constrained mutation strategies (add_example, add_constraint, restructure, add_edge_case) applied as single-pass string replacements. Accept-or-revert semantics prevent regression.
- **Provider-agnostic by default, Claude-enhanced optionally**. Claude-only frontmatter fields (model, subagent, dynamic_inject) are stripped for non-Claude providers. Trigger strategies adapt per provider: auto_trigger for Anthropic, keyword_primary for DeepSeek, keyword_only for open-weight models.

### 1.1 System Boundaries

The skills system interacts with four external systems:

1. **Argus** (`harness_skill_router`): Optional external dependency providing the 5-tier cascade router, governance ledgers, drift detector, and telemetry-driven promotion. Integrated via `LyraArgusCascade` facade which indexes `SkillManifest` objects and returns `SkillManifest` results. Lyra operates fully without Argus using the default token-overlap router.
2. **Lyra CLI** (`lyra_cli`): All skill commands (`lyra skill list/add/remove/reflect/curator/optimize`) are Typer wrappers around `lyra_skills` functions. The CLI injects the LLM provider (e.g., Anthropic, OpenAI) via the `LLMRunner` protocol for optimizer rounds and the extend/reflect commands.
3. **Lyra Core** (`lyra_core`): The core package provides the auth store for path resolution (`lyra_home()`), the skill registry wrapping for Argus telemetry mirroring (`mirror_registry_into_cascade`), and the session management that feeds trajectory data to the extractor.
4. **Evolution** (`lyra_evolution`): The research-grade evolution layer is designed to be decoupled: it consumes `SkillManifest` objects and evolution configuration, runs evolution algorithms across generations, and outputs evolved candidates as `SkillProposal` objects that can be materialised through the normal installation pipeline.

### 1.2 Data Flow Summary

```
SKILL.md files on disk
    |
    v
Loader/SkillParser (frontmatter extraction + YAML parse)
    |
    v
SkillManifest[] (in-memory catalog)
    |
    v
SkillRouter.route() -- token-overlap or Argus cascade
    |
    v
SkillActivator.select_active_skills() -- keyword + explicit + force
    |
    v
ProviderBridge (strip Claude-only fields, translate triggers)
    |
    v
System prompt injection -> LLM turn
    |
    v
Outcome (success/failure/neutral) -> SkillLedger
    |
    v
Curator (utility tiers) -- keeper/write/retire/promote
    |
    v
Extractor (trajectory -> candidate) on successful turns
    |
    v
Optimizer (executor/analyst/mutator loop) on flagged skills
    |
    v
Evolver (Escher/GEAR/Council) exploring skill genome space
```

## 2. Skills Format

### 2.1 SKILL.md Frontmatter

Every skill lives in a directory containing a `SKILL.md` file. The file begins with YAML frontmatter delimited by `---` markers, followed by an optional Markdown body. The canonical schema (defined in `loader.py` SkillManifest):

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | semi | parent dir name | Stable handle for routing and ledger |
| `name` | string | no | `id` | Human display label |
| `description` | string | no | `""` | One-liner surfaced to chat mode |
| `version` | string | no | `""` | Semver string |
| `keywords` | list of strings | no | `[]` | Trigger phrases for the router |
| `applies_to` | list of glob strings | no | `[]` | File globs the skill is relevant to |
| `requires` | list of strings | no | `[]` | Python distribution names the skill body expects |
| `progressive` | boolean | no | `false` | True means description-only at injection; full body fetched on activation |
| `allowed_tools` | list of strings | no | `[]` | Tool names the skill is permitted to use (tool-approval pipeline) |

Unknown keys are stashed verbatim into `SkillManifest.extras` for forward compatibility -- authors can experiment without forcing the loader to recognise every flag.

The full frontmatter regex used by the parser (`_FM_RE`):

```python
_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
```

This matches content from the opening `---\n` through the closing `\n---\n` and captures everything after as the body. The `re.DOTALL` flag ensures the body content spanning multiple lines is captured correctly. A parse failure (no frontmatter match) raises `SkillLoaderError` with the source file path.

Minimal example (from `.lyra/skills/code-review/SKILL.md`):

```yaml
---
name: code-review
description: Review code for bugs, security issues, and maintainability concerns
version: 1.0.0
triggers:
  - review this code
  - code review
  - check for bugs
  - audit this
tags: [engineering, quality, security]
---
```

Example with progressive loading and tool restrictions:

```yaml
---
id: surgical-changes
name: Surgical Code Changes
description: Make minimal, targeted code changes with no side effects
version: 1.2.0
keywords:
  - edit this file
  - change this
  - modify function
  - surgical edit
  - minimal change
applies_to:
  - "**/*.py"
  - "**/*.ts"
  - "**/*.go"
progressive: true
allowed_tools: [Read, Edit, Glob, Grep]
requires: []
---
```

Note that the `triggers` field in the legacy example is not a recognised `_KNOWN_KEYS` field; it would be silently accepted as an `extras` key. The loader only validates known keys via `_KNOWN_KEYS` and passes everything else through to `extras`:

```python
_KNOWN_KEYS: frozenset[str] = frozenset({
    "id", "name", "description", "version", "keywords",
    "applies_to", "requires", "progressive", "allowed_tools",
})
```

### 2.2 Type Coercion with Strict Validation

The loader applies strict type coercion to prevent silent degradation. Two key helpers enforce the contract:

**`_coerce_str_list(value, field_name, source)`** accepts:
- `None` or `""` -> empty list
- A single string -> `[string]`
- A list of strings -> as-is
- Any non-string element in a list -> raises `SkillLoaderError`
- Boolean, number, or dict -> raises `SkillLoaderError`

This catch mechanism is load-bearing: if an author accidentally types `keywords: true`, the loader rejects the file loudly at startup rather than silently treating it as `["true"]` and degrading keyword matching throughout the session.

**`_coerce_bool(value, field_name, source)`** accepts:
- Native Python `bool` -> as-is
- String `"true"` / `"1"` / `"yes"` / `"on"` -> `True`
- String `"false"` / `"0"` / `"no"` / `"off"` / `""` -> `False`
- Everything else -> raises `SkillLoaderError`

This is necessary because YAML parsing varies by loader -- some versions return strings for unquoted values and others return native booleans. The coerce function normalises across parser versions.

### 2.3 Agent Skills Open Standard Compatibility

Lyra's SKILL.md format aligns with the emerging **Agent Skills open standard** adopted by Claude Code, Cursor, and the SkillOS ecosystem. The format is forward-compatible:

- Claude Code's `SKILL.md` uses the same YAML frontmatter with `id`, `name`, `description`, `keywords`.
- Argus (`harness_skill_router`) uses `Skill` objects with `name`, `description`, `body`, `when_to_use`, `paths`, `source_url`, `trust_tier`.
- The `argus_bridge.py` module provides bidirectional translation: `manifest_to_argus_skill()` projects `SkillManifest` into `Skill`, and `argus_skill_to_manifest()` reverses it. Field mapping is lossless with Lyra-specific fields (progressive, requires, version, lyra_keywords) tucked into `Skill.extra`.
- `triggers` (legacy), `tags` (legacy), and `trigger_patterns` (ECC) are all mapped into `extras` or `keywords` depending on the loader path.

The Argus bridge mapping in detail:

| Lyra `SkillManifest` | Argus `Skill` | Direction |
|----------------------|---------------|-----------|
| `id` | `name` | both |
| `name` | `extra["display_name"]` | manifest -> argus |
| `description` | `description` | both |
| `body` | `body` | both |
| `keywords` (list) | `when_to_use` (newline-joined) | manifest -> argus |
| `applies_to` | `paths` | both |
| `requires` | `extra["requires"]` | both |
| `progressive` | `extra["progressive"]` | both |
| `version` | `extra["version"]` | both |
| `path` | `source_url` | both |
| `extras` (free-form) | merged into `extra` | both |

The reverse direction (`argus_skill_to_manifest`) reconstructs keywords from `when_to_use` on splitlines when the `lyra_keywords` extra key is missing, ensuring round-trip fidelity even when the skill was introduced by a non-Lyra adapter.

### 2.4 Claude Code Extensions

Lyra adds three Claude-specific frontmatter fields that are stripped for non-Claude providers (see Section 7):

- `model`: Model pin for execution (Claude-specific model IDs). Allows a skill to request a specific model, e.g., `model: claude-sonnet-4-20250514`.
- `subagent`: Enables Claude Code subagent execution from within the skill. Instructs the harness to delegate the skill body to a subagent invocation.
- `dynamic_inject`: Triggers dynamic context injection during chat. When set, the skill body is injected mid-turn rather than at the system prompt level.

These are defined in `provider_bridge.CLAUDE_ONLY_FRONTMATTER` and stripped via `strip_claude_frontmatter()` when the target provider is not `anthropic` or `openrouter`.

The existing `.claude/skills/` and `.lyra/skills/` directories coexist with Lyra's skill roots (shipped packs, user-global, project-local). All roots are scanned by the loader and merged with later-root-wins resolution for duplicate ids.

### 2.5 Legacy ECC Format

The original ECC format (parsed by `src/skills/parser.py`) uses a different set of fields:

```yaml
---
name: skill-name
description: Skill description
category: coding-standards
trigger_patterns: [pattern1, pattern2]
tags: [tag1, tag2]
language: python
---
```

Key differences from the Agent Skills standard:
- `category` is a controlled enum (`SkillCategory` with 10 values: coding-standards, backend-patterns, frontend-patterns, tdd-testing, security-review, database, api-design, deployment, docker, framework-specific, general).
- `trigger_patterns` is functionally identical to `keywords` but operates via substring matching in `Skill.matches_trigger()`.
- `language` is a string field, not a list of `applies_to` globs.
- The ECC format has no concept of `progressive` or `allowed_tools`.

The legacy `SkillSearchResult` dataclass bridges to the new system through `score + match_reason` fields that the unified router can consume.

## 3. Skills Loader

### 3.1 Tiered Loading: Frontmatter -> Body -> References

The loader (`loader.py`, `load_skills()`) performs a three-tier parse:

**Tier 1 -- Frontmatter extraction**. The regex `\A---\s*\n(.*?)\n---\s*\n?(.*)\Z` splits the file into frontmatter YAML and body Markdown. Missing frontmatter raises `SkillLoaderError`. The YAML is parsed with `yaml.safe_load()` and type-coerced through strict helpers (`_coerce_str_list`, `_coerce_bool`):

- `_coerce_str_list` accepts both scalar strings (`keywords: foo`) and list form (`keywords: [foo, bar]`), rejecting `True`/`42`/dicts loudly so a typo does not silently degrade matching.
- `_coerce_bool` accepts native YAML booleans plus the string fallbacks `"true"`/`"false"`/`"yes"`/`"no"`/`"1"`/`"0"`/`"on"`/`"off"`.

Loading validates:
- `id` defaults to the parent directory name (legacy skills keep loading).
- Duplicate ids within a single root raise `SkillLoaderError`.
- Across roots, later root wins (the CLI shim orders: project skills, shipped packs, then user-global skills).

**Tier 2 -- Body extraction**. The Markdown body is the content after the closing `---`. It is stored verbatim in `SkillManifest.body`. The body is kept out of the default system prompt for progressive skills (see Section 3.4).

**Tier 3 -- References**. The `requires` field lists Python distribution names. The loader does not install them but `lyra doctor` and `lyra skill add` surface missing requirements from this list.

The full loading loop:

```python
def load_skills(roots: Iterable[Path]) -> list[SkillManifest]:
    by_id: dict[str, SkillManifest] = {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        local_ids: set[str] = set()
        for skill_md in sorted(root.rglob("SKILL.md")):
            manifest = _parse_skill_md(skill_md)
            if manifest.id in local_ids:
                raise SkillLoaderError(
                    f"duplicate skill id {manifest.id!r} in root {root}"
                )
            local_ids.add(manifest.id)
            by_id[manifest.id] = manifest
    return list(by_id.values())
```

Each root is walked with `rglob("SKILL.md")`, sorted for deterministic ordering. Within a root, duplicate detection is by `id`, not by filename. Across roots, the final dict overwrites earlier entries so the last-seen root wins. This gives the user-global directory priority over shipped packs on identical skill ids.

### 3.2 Trigger Matching

Three layers of trigger matching exist, ordered by increasing sophistication:

**1. Keyword substring match (activation.py)**. `match_keywords()` normalises the user prompt and skill keywords to lowercase-collapsed form, then checks substring containment. This is the cheapest and most reliable layer -- no NLP, no model calls. Also supports explicit `USE SKILL: <id>` directives detected by regex in `match_explicit_invocations()`.

```python
def match_keywords(prompt, skills):
    haystack = _norm(prompt)
    if not haystack:
        return []
    out = []
    for skill in skills:
        for kw in skill.keywords or ():
            needle = _norm(kw)
            if needle and needle in haystack:
                out.append((skill, kw))
                break
    return out
```

**2. Token overlap with synonym expansion (router.py)**. `SkillRouter._route_overlap()` tokenises the query and skill description/name using `_tokens()`, which applies:
- Stopword filtering (`_STOPWORDS`: ~25 common English words including "i", "to", "the", "a", "an", "of", "in", "on", "at", "for", "and", "or", "with", "from", "by", "is", "this", "that", "be", "need", "want", "please", "it", "into").
- Stemming (`_stem()`: removes -ing, -ed, -s suffixes).
- Synonym expansion (`_SYNONYMS`: maps "change"/"modify"/"update"/"fix"/"patch" all to "edit", "check"/"audit" to "review", "find"/"locate"/"search"/"where" to "localize", "test"/"tests" to "test-gen").

```python
_SYNONYMS = {
    "change": "edit", "changes": "edit", "modify": "edit",
    "update": "edit", "alter": "edit", "rewrite": "edit",
    "fix": "edit", "patch": "edit", "add": "edit", "remove": "edit",
    "delete": "edit", "refactor": "edit", "edits": "edit",
    "check": "review", "audit": "review", "inspect": "review",
    "find": "localize", "locate": "localize", "search": "localize",
    "where": "localize",
    "test": "test-gen", "tests": "test-gen",
}
```

The score is the number of intersecting tokens. This is the default path when no Argus cascade is wired.

**3. Argus cascade (argus_cascade.py, harness_skill_router)**. When `SkillRouter.with_argus()` is used, `route()` delegates to a five-tier cascade returning `CascadeResult` with `CascadePick` objects. The cascade modes are:
- `"auto"`: Full cascade, size-aware tier gating.
- `"keyword"`: Tier 1 BM25 only (deterministic, cheap).
- `"semantic"`: Tier 0 + Tier 2 (+ Tier 3 on ambiguity).

Results are projected back to `SkillManifest` via `CascadePick.from_ranked()`.

### 3.3 Provider-Agnostic Design

The skill loader is harness-level, not provider-API-level. There is zero coupling to specific LLM provider types in the loading process. The `SkillRouter` and `SkillActivation` modules operate on `SkillManifest` objects exclusively. Provider-specific behavior is handled by the `ProviderSkillBridge` (see Section 7), which is a shim layer that translates skill content for the target provider at injection time, not at load time.

The router's `system_prompt_index()` method renders a compact one-line-per-skill index:

```python
def system_prompt_index(self, *, limit=None):
    skills = self._skills if limit is None else self._skills[:limit]
    if not skills:
        return ""
    lines = [
        f"- {s.id}: {s.description.splitlines()[0] if s.description else s.name}"
        for s in skills
    ]
    return "Available skills:\n" + "\n".join(lines)
```

This index is what gets injected into the system prompt -- a compact, token-efficient listing of available skills the LLM can request by id.

### 3.4 Progressive Disclosure

Skills with `progressive: true` (defined in `activation.py`) keep their full body out of the default system prompt. Only the description is advertised. The full body is materialised only when the skill activates, via `select_active_skills()`:

1. **Force-activated** ids (caller-pinned via CLI flag) always win -- explicit caller intent must never be silently dropped.
2. **Explicit invocations** (`USE SKILL: <id>` in the prompt). Detected via regex: `r"USE\s+SKILL\s*:\s*([A-Za-z0-9_\-./]+)"`. Ties broken by ledger utility score (Phase O.6).
3. **Keyword matches** against `skill.keywords`. Sorted by ledger utility before the cap is applied.

Activation is capped at `max_active=6` per turn with `max_body_chars=4096` per skill to prevent prompt budget saturation. Bodies are truncated with an ellipsis character ("...") when exceeding the limit.

Non-progressive skills always inject their full body -- that is the existing behaviour for canonical packs (tdd-sprint, surgical-changes, ai-research, etc.).

The `render_active_block()` function formats activated skills for system prompt injection:

```python
def render_active_block(active):
    rows = list(active)
    if not rows:
        return ""
    parts = ["## Active skills (loaded for this turn)", ""]
    for entry in rows:
        m = entry.manifest
        parts.append(f"### {m.name} (`{m.id}`)")
        parts.append(f"_Activated because: {entry.reason}._")
        parts.append("")
        parts.append(entry.body.strip())
        parts.append("")
    return "\n".join(parts)
```

This produces headers that the LLM can parse and reference during the turn.

## 4. Skills Weaver

### 4.1 Discovery Across Skill Packs

Skills are discovered by walking `SKILL.md` under multiple roots. The shipped packs (`packs/__init__.py`) include 24 curated domains:

```python
_PACK_NAMES = [
    "ai-research", "atomic-skills", "ba", "brainstorming",
    "cloud-engineering", "data", "debugging", "design",
    "devops", "documentation", "engineering", "general",
    "karpathy", "migration", "optimization", "pm",
    "refactoring", "safety", "security", "solution-architecture",
    "sre", "tdd-sprint", "testing",
]
```

Each pack is a subdirectory of `packs/` containing a `SKILL.md` file. The pack roots are resolved relative to `packs/__init__.py` at runtime so they work regardless of the Python installation path.

User-global skills live under `~/.lyra/skills/<id>/`. Project-local skills under `./.lyra/skills/<id>/`. The Argus cascade additionally integrates with external marketplaces via `LocalDirectoryAdapter` and `PullSummary`, enabling federated skill discovery across repositories. The `import_directory()` method on `LyraArgusCascade` imports every `SKILL.md` under a root through Argus's A8 gates (content fingerprinting, signature validation, and trust-tier assignment).

### 4.2 Composition: Combining Skills for Complex Tasks

Skill composition is implicit rather than explicit -- multiple skills can be activated in a single turn. The `select_active_skills()` function deduplicates by skill id and respects the `max_active` cap, but within that boundary multiple skills coexist in the system prompt simultaneously.

The extractor (`extractor.py`) surfaces composition opportunities by recording which `skills_used` fired during a trajectory. The generated skill body includes a "Skills invoked" section:

```markdown
## Skills invoked
- tdd-discipline
- surgical-changes
```

The SLIM lifecycle manager (`lifecycle.py`) further enables composition analysis through `contexts_applied` tracking and marginal contribution estimation: `delta(s) = Perf(library) - Perf(library \ {s})`.

The compaction system (`compaction.py`) identifies merge candidates -- skills with high tag overlap (default threshold 0.6 Jaccard similarity) that could be combined into a composite pack. This is a purely tag-based heuristic; the actual merge logic is left to the caller's discretion (the compactor only reports candidates).

### 4.3 Optimization: Selecting the Best Skill for a Task

The router applies utility-aware tie-breaking via the skill ledger. The `utility_score()` function (ledger.py) computes:

```
base = (successes - failures) / (successes + failures)
total = successes + failures
if total == 0: return 0.0
```

With a recency boost: a skill used within the last 7 days gets a +10% multiplier decaying linearly over 60 days. The sign of the base score is preserved (a hot failure is not boosted into a success). The formula:

```python
age_days = max(0.0, (time.time() - stats.last_used_at) / 86400.0)
if age_days >= _RECENCY_DECAY_DAYS:   # 60 days
    return base
decay = max(0.0, 1.0 - age_days / _RECENCY_DECAY_DAYS)
if age_days < _RECENCY_FRESH_DAYS:    # 7 days
    decay = 1.0
boost = _RECENCY_BOOST * decay        # 0.10 max boost
return base + math.copysign(boost, base) if base != 0.0 else base
```

The `top_n()` function returns skills sorted by (utility, activation count, freshness) -- higher confidence beats lower confidence at equal utility.

```python
def top_n(ledger, n=10):
    items = list(ledger.skills.values())
    items.sort(
        key=lambda s: (utility_score(s), s.successes + s.failures, s.last_used_at),
        reverse=True,
    )
    return items[:max(0, n)]
```

When the Argus cascade is active, the full telemetry-driven re-ranker promotes or demotes skills based on outcome history: a skill with five successful executions in the last fortnight is auto-promoted to `T_REVIEWED`; a skill with >40% miss rate over at least three samples is demoted.

## 5. Skills Generator (SkillNet)

### 5.1 9-Domain Template System

The **AutoSkill** pipeline (`lyra_skills/autoskill.py`) extracts skill candidates from agent-environment dialogue using `SkillCandidate` objects with fields: id, name, description, code, source_dialogue (turn IDs), judge_scores, overall_score. Skills are materialised as SKILL.md files in the `~/.lyra/skills/autoskill/` directory.

The pipeline steps:
1. **Dialogue Collection**: Each `DialogueTurn` records user_input, agent_action, environment_feedback, success, timestamp.
2. **Skill Extraction**: An LLM extracts reusable patterns from the dialogue text.
3. **4-Axis Evaluation**: The `FourAxisJudge` scores each candidate (see Section 5.2).
4. **Library Update**: Skills above `acceptance_threshold` (default 0.7) are materialised as SKILL.md files.
5. **Pruning**: If the library exceeds `max_skills` (default 100), the lowest-scoring skills are removed.

The **EvoSkill** pipeline (`lyra_skills/evoskill.py`) discovers skills through evolutionary search:
- **Executor**: Runs agent programs on tasks, collects failures.
- **Proposer**: Analyses failures, proposes skills to address missing capabilities.
- **Skill-Builder**: Materialises skills as SKILL.md with implementation, keywords, confidence score.
- **Pareto frontier**: Maintains k=3 programs, evicting dominated ones via crowding-distance selection.

### 5.2 LLM-Driven Generation with Deterministic Fallback

Both generators use LLMs for the creative generation step, but validation and scoring are deterministic:

**AutoSkill 4-axis Judge**:
```python
overall = 0.4 * correctness + 0.2 * efficiency + 0.3 * generalizability + 0.1 * novelty
```
These weights prefer generalizable correctness over raw novelty. The extraction step prompts an LLM for candidate detection; the Judge step calls the LLM for per-axis scoring; the acceptance/rejection threshold (default 0.7) is deterministic. Each axis is scored 0.0-1.0 with a required JSON response format:

```json
{
  "correctness": 0.9,
  "efficiency": 0.8,
  "generalizability": 0.85,
  "novelty": 0.7,
  "reasoning": "Brief explanation for each score"
}
```

**EvoSkill**: LLMs are used for program execution and skill proposal generation. Pareto-frontier dominance is purely deterministic (all-objective strict domination with crowding-distance tie-breaking). Confidence scores from the proposer are stored verbatim in skill metadata but do not affect frontier membership. The dominance check:

```python
def _dominates(self, m1, m2):
    better_in_all = all(m1.get(k, 0) >= m2.get(k, 0) for k in m1.keys())
    better_in_some = any(m1.get(k, 0) > m2.get(k, 0) for k in m1.keys())
    return better_in_all and better_in_some
```

Failure grouping happens by `missing_capability` field, which is parsed from the executor's error output. Skills are proposed per missing capability, then evaluated on their ability to address the grouped failures.

**Hermes extractor** (`extractor.py`): The `extract_candidate()` function takes a trajectory and runs six rubric checks:
1. `min_tool_calls` (HARD): >= 4 tool calls (bumped from 3 in v3.5 based on Hermes' observation that 3-call trajectories produce too-narrow skills).
2. `distinct_tools` (HARD): >= 2 distinct tool names -- single-tool trajectories do not generalise.
3. `slug_unique` (HARD when existing ids supplied): refuses to shadow existing skills with `slug = _slug(task)` that lowercases, strips non-alphanumeric characters, and truncates to 48 chars.
4. `has_sections` (SOFT): body must contain `## When to use` and `## Tool sequence`.
5. `no_leaked_secrets` (HARD): regex scan against OpenAI (sk-...), Google (AIza...), AWS (AKIA...), GitHub (ghp_...), GitLab (glpat-...) secret patterns.
6. `body_length_bounded` (SOFT): <=200 lines.

Any HARD failure rejects the candidate entirely. The output `ExtractorOutput` always sets `requires_user_review=True` -- the extractor never writes to disk autonomously. The slug generation:

```python
def _slug(task):
    s = task.lower().strip()
    s = re.sub(r"[^a-z0-9 _-]+", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s[:48] or "unnamed"
```

### 5.3 5-D Quality Scoring

Quality is measured at multiple points across the pipeline:

**Runtime utility** (ledger.py `utility_score()`): Ranges from approximately -1.1 to +1.1. Base is `(s-f)/(s+f)` with recency boost. Used for router tie-breaking, curator grading, and lifecycle decisions.

**Curator tiers** (curator.py `_tier_for()`): Maps utility score to five quality tiers:

| Tier | Minimum Utility | Conditions | Action |
|------|----------------|------------|--------|
| Promote | >= 0.85 | >=10 activations, <=1 failure | Feature in /help and SessionStart |
| Keep | >= 0.65 | -- | No action |
| Watch | >= 0.40 | -- | Monitor |
| Rewrite | < 0.40 | <=250 lines | `lyra skill reflect <id>` |
| Retire | < 0.20 | >=5 activations, >=90 days stale | `lyra skill rm <id>` |

The tier logic is a pure function of (SkillStats, SkillManifest, size_lines, now_ts) making it trivially testable:

```python
def _tier_for(stats, *, manifest, size_lines, now_ts):
    if stats is None or activations == 0:
        return (TIER_WATCH, "never activated", "monitor")
    score = utility_score(stats)
    stale_days = _days_since(stats.last_used_at, now_ts) if stats.last_used_at else None
    # Promote check
    if score >= 0.85 and activations >= 10 and stats.failures <= 1:
        return (TIER_PROMOTE, ..., "feature in /help")
    # Retire check
    if score < 0.20 and activations >= 5 and stale_days >= 90:
        return (TIER_RETIRE, ..., f"lyra skill rm {manifest.id}")
    # Rewrite check
    if score < 0.40 and size_lines <= 250:
        return (TIER_REWRITE, ..., f"lyra skill reflect {manifest.id}")
    # Watch check
    if score < 0.65:
        return (TIER_WATCH, ..., "monitor")
    return (TIER_KEEP, ..., "no action")
```

**AutoSkill 4-axis**: Each axis scores 0.0-1.0. Acceptance threshold 0.7.

**Optimizer pass rate** (optimizer.py `_score()`): Fraction of evaluation scenarios passed, target >= 1.0 (100%). Scenarios are prompt + eval-criterion pairs scored by an LLM executor.

**SkillOS curator** (`skilloscurator.py`): Computes a composite reward from:
- Task outcome weight (0.50): downstream task success rate.
- Operation validity weight (0.20): fraction of valid curator operations.
- Content quality weight (0.20): external judge score [0,1].
- Compression weight (0.10): penalty for storing raw trajectories.

This is the only learned curator in the system -- designed to be trained via RL rather than hand-tuned. The total reward formula:

```python
def total(self, config=None):
    cfg = config or CurationRewardConfig()
    return (
        cfg.task_outcome_weight * self.task_outcome
        + cfg.operation_validity_weight * self.operation_validity
        + cfg.content_quality_weight * self.content_quality
        + cfg.compression_weight * min(self.compression_ratio, 1.0)
    )
```

### 5.4 Quality Threshold Gating with Retry

The optimizer (`optimize_skill()`) implements iterative quality gating:

1. Score current skill body against all scenarios.
2. If `pass_rate >= target` (default 1.0), terminate.
3. Otherwise: analyst diagnoses failure, mutator proposes edit, applier applies it, executor re-scores.
4. Accept only if `new_score > pre_score`. Revert otherwise.
5. Loop up to `max_rounds` (default 20, max 50).

Each round costs `len(scenarios) + 2` LLM calls (executor for each scenario + analyst + mutator). The default of 20 rounds with 5 scenarios = ~110 LLM calls per full optimization run. The mutation log (`skill_mutations.jsonl`) records every round, accepted or rejected, so users can audit SKILL.md drift over time.

The optimizer's JSON parsing (`_parse_json_obj`) handles common model output quirks:
- Strips triple-backtick `json` fences.
- Falls back to extracting the first `{...}` substring if the whole body is not valid JSON.
- Returns `{}` if nothing parses -- the caller (analyst raises ValueError, executor treats as `passed=False`).

```python
def _parse_json_obj(raw):
    text = (raw or "").strip()
    fence = _FENCE_RE.match(text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}
```

## 6. Self-Evolution Pipeline

Lyra's self-evolution is a multi-algorithm framework spanning three packages and seven distinct mechanisms. They are ordered here from most conservative (bounded edits) to most exploratory (open-ended search).

### 6.1 Darwin Archive-Based Evolution

The Darwin archive (`lyra-evolution/.lyra/evolution/archive/`) stores candidate configurations as JSON, keyed by candidate id. Each candidate includes skills list, memory configuration, generation number, parent id, and creation timestamp. This provides a versioned, queryable ancestry for all evolved configurations. The archive is consumed by the Escher-Loop and GEAR-Evolve mechanisms.

Archive structure:
```
.lyra/evolution/archive/
  candidates/
    c000_5fc04e7f.json     # Baseline configuration
    c001_abc12345.json     # First evolved candidate
    c002_def67890.json     # Second evolved candidate (may fork from c000 or c001)
    ...
  scores/
    c000_5fc04e7f.json     # Evaluation results for candidate c000
    ...
```

Each candidate JSON:
```json
{
  "id": "c000_5fc04e7f",
  "generation": 0,
  "parent_id": null,
  "config": {
    "skills": ["skill1", "skill2"],
    "memory_config": {"type": "memtier"}
  },
  "created_at": "2026-05-17T14:23:33.346826",
  "metadata": {
    "description": "Baseline configuration"
  }
}
```

The generation counter tracks ancestry depth. `parent_id` is `null` only for the root (generation 0) candidate. This forms a directed acyclic graph of evolution history, enabling traceability and selective rollback.

### 6.2 SkillOpt Bounded Edits (<=50 tokens)

The optimizer (`optimizer.py`) constrains mutations to four strategies from a small enum:

| Strategy | Purpose | Example |
|----------|---------|---------|
| `add_example` | Add a worked example that generalises the skill | Insert a new code block in the examples section |
| `add_constraint` | Add a guardrail the model must follow | Add a precondition or postcondition |
| `restructure` | Reorganise sections for clarity | Reorder steps, regroup related content |
| `add_edge_case` | Cover a failure mode the skill missed | Add a note about null inputs, empty results |

Each mutation is a single `(old_text, new_text)` pair applied via `str.replace()` with the strict requirement that `old_text` appears exactly once. A mutation that fails application (zero or multiple matches) is treated as a no-op revert. This keeps edits auditable and prevents unbounded drift.

```python
def _apply_mutation(skill_body, mutation):
    if not mutation.old_text:
        return skill_body, False
    count = skill_body.count(mutation.old_text)
    if count != 1:
        return skill_body, False
    return skill_body.replace(mutation.old_text, mutation.new_text), True
```

The full optimizer loop:

```python
def optimize_skill(skill_id, *, current_md, scenarios, llm, max_rounds=20, target_pass_rate=1.0):
    best_md = current_md
    best_score, _ = _score(best_md, scenarios, llm)
    result = OptimizeResult(skill_id, initial_score=best_score, ...)

    for round_no in range(1, max_rounds + 1):
        failures = [r for r in pre_results if not r.passed]
        if not failures:
            break

        analysis = _analyse(best_md, failures, llm)
        mutation = _mutate(best_md, analysis, llm)
        new_md, applied = _apply_mutation(best_md, mutation)
        if not applied:
            continue

        new_score, _ = _score(new_md, scenarios, llm)
        if new_score > pre_score:
            best_md = new_md
            best_score = new_score
            if new_score >= target_pass_rate:
                break

    result.final_md = best_md
    result.final_score = best_score
    return result
```

The mutation log (`skill_mutations.jsonl`, managed in `ledger.py`) persists every round as a `MutationRecord` with ts, skill_id, strategy, pre_score, post_score, accepted bit, reasoning, target_section, and error. This provides a full audit trail for every change to every skill.

### 6.3 FORGE Population Generation

The **Escher-Loop** (`escher.py`) implements a two-population architecture:

**Solver population**: Generates candidate solutions. Default size 50, configurable. Each solver's `generate_solutions()` produces one candidate per solver per generation.

**Critic population**: Evaluates solutions via a fitness function and selects top-k survivors (default 10). Survivors reproduce through crossover (midpoint content merge, rate 0.5) and mutation (random content perturbation, rate 0.1).

The loop:
```
for gen in 0..generations:
    solutions = generate_solutions(population, problem)
    scores = evaluate_solutions(solutions, evaluator)
    survivors = select_top(solutions, top_k, scores)
    population = reproduce(survivors)  # crossover + mutation
```

Diversity is tracked as `(unique_contents - 1) / (population_size - 1)`. The loop records generation snapshots (`EscherGeneration`) with full solution/score vectors. The crossover operator uses a simple midpoint merge:

```python
def crossover(self, parent_a, parent_b):
    midpoint = (len(parent_a.content) + len(parent_b.content)) // 2
    child_content = parent_a.content[:midpoint] + " | " + parent_b.content[midpoint:]
    return EscherSolver(content=child_content, parent_ids=(parent_a.solution_id, parent_b.solution_id))
```

### 6.4 CODESKILL Quality Feedback

The `CodeGenerator` (`generation/generator.py`) provides the quality feedback loop for code-level skill optimization:

- Detects recursive functions and proposes memoization patches (using `functools.lru_cache`).
- Detects inefficient loops and proposes list comprehension refactoring.
- Generates type hints for untyped code.
- Validates all patches via `ast.parse()` syntactic validation before application.
- Confidence scoring: memoization patches get 0.9 confidence, iterative conversion 0.8, type hints 0.7, generic optimizations 0.5.

The memoization patch generator:

```python
def generate_memoization_patch(self, function_name, original_code):
    new_code = f"""from functools import lru_cache

@lru_cache(maxsize=None)
{original_code.strip()}"""
    return GeneratedPatch(
        target_function=function_name,
        original_code=original_code,
        new_code=new_code,
        description=f"Add memoization to {function_name} using lru_cache",
        confidence=0.9,
        patch_type="optimization",
    )
```

The `SelfImprovement` engine (`improvement.py`) provides the closed-loop wrapper:
1. `record_episode()`: Logs task outcomes with scores and metadata.
2. `analyze_failures()`: Groups failures by task_id, returns patterns with >=3 occurrences.
3. `generate_improvements()`: Proposes fixes for each pattern (with optional callable generator for custom logic).
4. `validate_improvement()`: Tests against a callable test suite before deployment.
5. `apply_improvement()` / `rollback_if_degraded()`: Active deployment with automatic rollback if performance drops more than 5% from baseline.

The `compute_improvement_rate()` function tracks long-term improvement via linear regression over a sliding window:

```python
def compute_improvement_rate(self, window=20):
    recent = self._episodes[-window:]
    n = len(recent)
    xs = list(range(n))
    ys = [e["score"] for e in recent]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return 0.0
    slope = num / den
    normalised = slope / max(abs(mean_y), 0.001)
    return round(normalised, 6)
```

This provides a single scalar that answers "is the system getting better over time?" Positive values indicate improvement, negative values indicate degradation. The denominator normalisation makes the rate comparable across tasks with different score ranges.

### 6.5 Auto-Rollback on Regression (EvolveMem)

The `GEAR-Evolve` controller (`gear.py`) implements self-modifying search with automatic rollback through two mechanisms:

**Strategy performance update**: Each strategy maintains an exponential moving average success rate (`alpha = 0.1`). Underperforming strategies (success rate < 0.1 after >=5 uses) are pruned automatically. The EMA update:

```python
def update_strategy_performance(self, strategy, outcome):
    alpha = 0.1  # EMA smoothing factor
    new_rate = alpha * outcome + (1 - alpha) * strategy.success_rate
    updated = GEARStrategy(
        strategy_id=strategy.strategy_id,
        success_rate=round(new_rate, 4),
        total_uses=strategy.total_uses,
        ...
    )
    self._strategies[strategy.strategy_id] = updated
```

**Exploration/exploitation adaptation**: The global exploration weight decays by `decay_factor=0.95` each step, favouring exploitation as strategies mature. If recent performance drops below 0.3 on a 3-outcome window, exploration is boosted by 0.15 to escape local optima:

```python
def adapt_exploration(self, performance_history=None):
    self._global_exploration *= self._decay_factor  # 0.95 per step
    if performance_history and len(performance_history) >= 3:
        recent = list(performance_history)[-3:]
        if sum(recent) / len(recent) < 0.3:
            boost = 0.15
            self._global_exploration = min(0.8, self._global_exploration + boost)
    self._global_exploration = max(self._min_exploration, self._global_exploration)
    return self._global_exploration
```

Strategy selection uses epsilon-greedy: with probability `exploration_weight`, pick a random strategy biased toward under-used ones (inverse-weighted by `total_uses`). Otherwise, pick the best-performing strategy:

```python
def select_strategy(self, problem=None, problem_features=None):
    if self._rng.random() < self._global_exploration:
        return self._explore()  # biased toward under-used
    else:
        return self._exploit(features=problem_features)  # best success rate
```

**Council Mode** (`council.py`) provides STORM conflict resolution for evolution decisions: when council members disagree, the system iterates through up to 5 resolution rounds, narrowing options each round, and escalates to weighted-majority tie-breaking on deadlock. Consensus >= 0.66 is required for early termination. The resolution loop:

```python
def resolve_conflict(self, disagreement, max_iterations=5):
    options = list(set(disagreement.values()))
    if len(options) <= 1:
        return CouncilDecision(final_decision=options[0], consensus_level=1.0)
    participants = [self._members[uid] for uid in disagreement if uid in self._members]
    for iteration in range(max_iterations):
        decision = self.vote(participants, options)
        if decision.consensus_level >= 0.66:
            return decision
        # Narrow options to top contenders
        tally = decision.metadata.get("tally", {})
        top_options = sorted(tally, key=lambda k: tally.get(k, 0.0), reverse=True)
        options = top_options[:max(2, len(top_options) // 2)]
    # Tie-breaker: weighted majority
    winner, score = self.weighted_majority(list(decision.votes), ...)
    return CouncilDecision(final_decision=winner, consensus_level=score, ...)
```

Each council member has a weight derived from historical performance and votes with a confidence score. The weighted majority function multiplies member weight by confidence:

```python
def weighted_majority(votes, weights):
    tally = Counter()
    total_weight = 0.0
    for v in votes:
        w = weights.get(v.member_id, 1.0) * v.confidence
        tally[v.decision] += w
        total_weight += w
    if not tally:
        return ("", 0.0)
    winner = tally.most_common(1)[0][0]
    score = tally[winner] / total_weight if total_weight > 0 else 0.0
    return winner, score
```

Hallucination detection across council members uses Jaccard overlap against a reference text:

```python
def detect_hallucination(claims, reference):
    ref_tokens = set(reference.lower().split())
    risks = {}
    for member_id, claim in claims.items():
        claim_tokens = set(claim.lower().split())
        overlap = claim_tokens & ref_tokens
        jaccard = len(overlap) / len(claim_tokens | ref_tokens) if claim_tokens else 0.0
        risk = 1.0 - jaccard
        risks[member_id] = round(risk, 4)
    return risks
```

**PRISM drift detection** (`drift_detector.py`) provides the watchtower: daily comparison of recent performance signals against a rolling baseline. Alert levels:

| Level | Degradation | Action |
|-------|-------------|--------|
| NONE | < 5% drop | No action |
| WARNING | 5-15% drop | Schedule GEPA optimization |
| DEGRADATION | significant | Trigger re-optimisation now |
| CRITICAL | >15% drop | Rollback + alert on-call |

The current vs baseline comparison splits signals into baseline (older than `baseline_window_days//2`) and recent (newer) signals:

```python
def check_drift(self, prompt_name):
    signals = self._signals.get(prompt_name)
    baseline_cutoff = time.time() - (self._baseline_window_days * 86_400)
    recent_cutoff = time.time() - (self._baseline_window_days * 86_400 // 2)
    baseline = [s for s in signals if s.timestamp <= baseline_cutoff]
    recent = [s for s in signals if baseline_cutoff < s.timestamp <= recent_cutoff]
    # Fallback: oldest half as baseline, newest half as recent
    if not baseline or not recent:
        mid = len(signals) // 2
        baseline = signals[:mid]; recent = signals[mid:]
    baseline_rate = sum(s.success_rate for s in baseline) / len(baseline)
    current_rate = sum(s.success_rate for s in recent) / len(recent)
    degradation_pct = (current_rate - baseline_rate) / baseline_rate * 100
    alert_level = self._classify_drift(degradation_pct)
    return DriftReport(prompt_name=prompt_name, alert_level=alert_level, ...)
```

The **SLIM lifecycle manager** (`lifecycle.py`) provides marginal-contribution-based retirement: skills whose `delta(s) ~= 0` (the policy has internalised them) are retired, preventing library signal-to-noise degradation. SLIM thresholds:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_uses_before_evaluation` | 5 | Skip decision until sufficiently exercised |
| `retire_marginal_threshold` | 0.02 | `delta(s)` below this -> retire |
| `retire_success_rate_floor` | 0.20 | Retire if success rate too low |
| `expand_failure_streak` | 3 | N consecutive failures -> expand (add new skill) |
| `retain_min_success_rate` | 0.50 | Must exceed this to retain confidently |

The evaluation function implements the three-way decision:

```python
def evaluate(self, skill_id):
    f = self._fitness.get(skill_id)
    if f.use_count < cfg.min_uses_before_evaluation:
        return LifecycleEvaluation(RETAIN, "not enough data", ...)
    streak = self._failure_streaks.get(skill_id, 0)
    if streak >= cfg.expand_failure_streak:
        return LifecycleEvaluation(EXPAND, "coverage gap", ...)
    if f.marginal_contribution < cfg.retire_marginal_threshold or f.success_rate < cfg.retire_success_rate_floor:
        return LifecycleEvaluation(RETIRE, "marginal contribution near zero", ...)
    return LifecycleEvaluation(RETAIN, "healthy", ...)
```

This is grounded in the paper finding that monotonic accumulation degrades library signal-to-noise over time. SLIM achieves +12.5pp over monotonic accumulation on ALFWorld (87.5% vs 75.0%).

### 6.6 Compaction: Trim, Merge, Archive

The compactor (`compaction.py`) provides four operations to maintain library health:

**Trim**: Removes unreferenced sections from active skills. Uses `SectionUsageTracker` which tracks per-section reference counts. Sections with zero references are candidates for trimming.

**Merge**: Identifies skill pairs with high Jaccard similarity on their tag sets (threshold 0.6). The similarity formula:

```
similarity = |tags_a & tags_b| / |tags_a | tags_b|
```

**Archive**: Finds skills unused for >= 90 days (`STALE_THRESHOLD_DAYS`).

**Delete**: Finds cold skills -- fewer than `MIN_USES_TO_KEEP` (3) invocations AND unused for >30 days.

The overall compression target is 60% context reduction (`COMPRESSION_TARGET = 0.60`). The compactor's `stats()` method reports tracked skills, total characters, active characters, and the current compression ratio.

### 6.7 Skill State Management

The `SkillsState` module (`state.py`) provides per-skill enable/disable overrides driven by the `/skills` picker UI. Persistence mirrors the ledger: tempfile + `os.replace` for crash-safe atomic writes.

State semantics:
- `enabled`: Forward-compat slot for when default-off skills ship.
- `disabled`: The meaningful set -- skills in this set are filtered out of the system-prompt block.
- `locked`: Shipped packs are always active regardless of state.

The `is_active()` function implements the three-rule policy:

```python
def is_active(skill_id, *, locked, state):
    if locked:
        return True
    if skill_id in state.disabled:
        return False
    return True
```

## 7. Provider x Skill Compatibility

### 7.1 Per-Provider Trigger Strategy

The `ProviderSkillBridge.get_trigger_strategy()` returns the recommended trigger strategy per provider:

| Provider | Strategy | Rationale |
|----------|----------|-----------|
| `anthropic` | `auto_trigger` | Strong instruction following; model auto-trigger is reliable |
| `openrouter` | `auto_trigger` | Claude models available via OpenRouter |
| `deepseek` | `keyword_primary` | Deterministic keyword matching recommended as primary |
| `openai` | `keyword_and_auto` | Mixed strategy |
| `google` | `keyword_primary` | Keyword matching recommended |
| `openweights` | `keyword_only` | No auto-trigger reliability for open-weight models |

Skills lacking `keywords` or `triggers` frontmatter produce a validation warning on DeepSeek, OpenAI, and Google providers, noting that auto-trigger may be unreliable.

The strategy mapping is simple and extensible:

```python
strategies = {
    "anthropic": "auto_trigger",
    "openrouter": "auto_trigger",
    "deepseek": "keyword_primary",
    "openai": "keyword_and_auto",
    "google": "keyword_primary",
    "openweights": "keyword_only",
}
```

### 7.2 Claude-Only Frontmatter Handling

Three frontmatter fields are recognised as Claude-only:

```python
CLAUDE_ONLY_FRONTMATTER = frozenset({
    "model",           # Model pin (Claude-specific model IDs)
    "subagent",        # Claude Code subagent execution
    "dynamic_inject",  # Claude Code dynamic context injection
})
```

`strip_claude_frontmatter()` removes these fields for non-Claude, non-OpenRouter providers to prevent confusion. The check is line-level (`stripped.startswith(f"{field}:")`) so even malformed frontmatter with incorrect casing is handled.

```python
def strip_claude_frontmatter(skill_content, provider):
    if provider in ("anthropic", "openrouter"):
        return skill_content
    lines = skill_content.split("\n")
    result = []
    for line in lines:
        stripped = line.strip().lower()
        should_skip = any(stripped.startswith(f"{field}:") for field in CLAUDE_ONLY_FRONTMATTER)
        if not should_skip:
            result.append(line)
    return "\n".join(result)
```

### 7.3 Degradation on Weaker Providers

The compatibility check in `validate_for_provider()` returns two values: `(is_compatible, warnings)`. The logic for `is_compatible` is deliberately lenient -- it only returns `False` when a warning cannot be resolved by stripping Claude-only fields. In practice, all skills are considered compatible because Claude-only fields are stripped; the warnings serve as advisory rather than blocking.

The degradation path is:
1. **On Claude**: Full SKILL.md with all frontmatter preserved; model auto-trigger is the primary route.
2. **On non-Claude providers with auto-trigger** (OpenAI, OpenRouter): frontmatter stripped, model auto-trigger attempted but keyword matching is the reliable fallback.
3. **On deterministic-only providers** (DeepSeek, Google, open-weight): frontmatter stripped, keyword matching is the only path. Skills without explicit keywords silently under-activate.

The Argus cascade supports all providers uniformly because it runs at the harness level, not the provider level. The cascade produces ranked results as `SkillManifest` objects regardless of which LLM provider will eventually execute the turn.

### 7.4 Telemetry Bridge for Registry Events

The Argus telemetry bridge (`argus_telemetry_bridge.py`) provides monkey-patching of the old-style `SkillRegistry` so that success/miss events also reach Argus's ledger. This is needed for the migration period where both the old `src/skills/registry.py` and the new `lyra_skills` system coexist:

```python
def mirror_registry_into_cascade(registry, cascade):
    original_success = registry.record_success
    original_miss = registry.record_miss

    def record_success(skill_id):
        skill = original_success(skill_id)
        cascade.record_outcome(skill_id, success=True, ...)
        return skill

    def record_miss(skill_id):
        skill = original_miss(skill_id)
        cascade.record_outcome(skill_id, success=False, ...)
        return skill

    registry.record_success = record_success
    registry.record_miss = record_miss
    return restore  # callable to detach the bridge
```

The bridge is idempotent (calling restore twice is harmless) and reversible (returns a `Restore` callable).

## 8. Architecture Diagram

```
+------------------------------------------------------------------+
|                     SKILL ECOSYSTEM                               |
+------------------------------------------------------------------+
                                                                    
  AUTHORING                    DISCOVERY & LOADING                  
  +-----------+                +---------------------+              
  | SKILL.md  |---.           | Skill Roots          |              
  | (yaml+md) |   |           | - project .lyra      |              
  +-----------+   |           | - user ~/.lyra       |              
                  |           | - shipped packs      |              
  +-----------+   |           | - marketplace repos  |              
  | ECC       |   '--------->| - argus catalog       |              
  | format    |---.           +---------------------+              
  +-----------+   |              |                                  
                  |              v                                  
  +-----------+   |           +---------+                           
  | AutoSkill |---'           | Loader  |-----> SkillManifest[]     
  | EvoSkill  |---.           | Parser  |  (frontmatter + body)    
  +-----------+   |           +---------+                           
                  |              |                                  
  +-----------+   |              v                                  
  | trajectory|   |           +----------------------------------+  
  | extractor |---'           |      ROUTING                      |  
  +-----------+               |  +-----------------------------+  |  
                              |  | Token Overlap (default)     |  |  
  RUNTIME                     |  | - stemmer + synonyms        |  |  
  +----------+                |  +-----------------------------+  |  
  | Ledger   |<-- outcomes    |  | Argus Cascade (optional)    |  |  
  | JSON     |                |  | BM25 -> Embed -> Cross-enc  |  |  
  +----------+                |  | Telemetry re-rank           |  |  
       |                     |  +-----------------------------+  |  
       v                     +----------------------------------+  
  +-----------+                       |                            
  | Curator   |                 activation                         
  | 5 tiers   |<-- SkillReport[]  |                              
  +-----------+              +-----------+                         
       |                     | Activator |---system prompt         
       v                     | progressive|                        
  +-----------+              +-----------+                         
  | Compactor |                    |                               
  | trim/merge|              +-----------+                         
  | archive   |              | Provider  |---translated prompt     
  +-----------+              | Bridge    |                         
                             +-----------+                         
                                                                    
  EVOLUTION                                                         
  +-----------------------------+                                  
  | Optimizer (closed-loop)     |                                  
  | Executor -> Analyst ->      |                                  
  | Mutator -> Apply -> Revert  |                                  
  +-----------------------------+                                  
  | Escher-Loop RSI             |                                  
  | Solver-pop -> Critic-pop    |                                  
  +-----------------------------+                                  
  | GEAR-Evolve                 |                                  
  | Self-modifying search       |                                  
  +-----------------------------+                                  
  | Council Mode + STORM        |                                  
  | Multi-agent debate + voting |                                  
  +-----------------------------+                                  
  | PRISM Drift Detection       |                                  
  | Baseline vs recent signals  |                                  
  +-----------------------------+                                  
  | SLIM Lifecycle              |                                  
  | Marginal contribution ->    |                                  
  | Retain/Retire/Expand        |                                  
  +-----------------------------+                                  
  | SkillOS Curator (RL)        |                                  
  | Learnable INSERT/UPDATE/    |                                  
  | DELETE from task outcomes   |                                  
  +-----------------------------+                                  
  | Skill Vetter (Proteus)      |                                  
  | 5-axis, multi-round audit   |                                  
  +-----------------------------+                                  
                                                                    
  PERSISTENCE                                                      
  +----------+  +----------+  +----------+                         
  |skill_    |  |skill_    |  |skill_    |                         
  |ledger    |  |mutations |  |state     |                         
  |.json     |  |.jsonl    |  |.json     |                         
  +----------+  +----------+  +----------+                         
  +----------+  +----------+  +----------+                         
  |skill_    |  |darwin    |  |benchmark_|                         
  |embeddings|  |archive/  |  |results   |                         
  |.json     |  |candidates|  |.json     |                         
  +----------+  +----------+  +----------+                         
```

The data flow proceeds from bottom-left to top-right: skills are authored or downloaded into skill roots, loaded and parsed into `SkillManifest` objects, routed against user queries, activated into the system prompt, translated through the provider bridge, and executed. Outcomes flow back into the ledger. The curator and compactor run periodic health checks. The evolution layer operates in its own feedback loop, consuming ledger data and proposing new/updated skills.

### 8.1 Data Flow Detail: A Complete Turn

1. **Session start**: `load_skills()` discovers all SKILL.md files across all roots. `SkillRouter.system_prompt_index()` renders a compact index. Non-progressive skill bodies are injected into the system prompt.
2. **User prompt arrives**: `SkillRouter.route()` runs query against the catalog (token-overlap or Argus cascade).
3. **Activation**: `select_active_skills()` matches prompt against skill keywords, explicit `USE SKILL` directives, and force-pinned ids. Progressive skills have their bodies fetched. `render_active_block()` formats the activation block.
4. **Provider translation**: `ProviderSkillBridge.strip_claude_frontmatter()` and `validate_for_provider()` adapt skill content for the target LLM provider.
5. **LLM turn**: The combined system prompt (index + active block + non-progressive bodies) is sent to the provider.
6. **Outcome recording**: The harness calls `record_outcome()` on the ledger with SUCCESS/FAILURE/NEUTRAL and optional error_kind.
7. **Post-turn**: The curator (if invoked) reads the ledger and recomputes utility tiers. The extractor (if recording is enabled) checks whether the trajectory qualifies for skill extraction.

## 9. Trade-Off Analysis

### 9.1 Deterministic Curator vs LLM-Graded Review

**Choice**: The curator uses pure-function heuristics (utility score + activation count + staleness) with zero LLM calls.

**Trade-off**: The curator runs in <100ms over hundreds of skills, is reproducible across runs (hash-deterministic), and can run in CI/pre-commit/SessionStart without quota concern. However, it cannot detect semantic quality issues that an LLM would catch (e.g., "this skill body is misleading despite having high utility"). The `lyra skill reflect` command fills this gap by using an LLM for the actual rewrite step. The curator's role is purely triage -- surface candidates for human or LLM review, not judge them.

The separation of concerns is deliberate: the curator answers "which skills need attention?" while `lyra skill reflect` answers "what should the improved version look like?" The first question is a sorting problem best solved with cheap heuristics; the second is a generation problem that benefits from an LLM.

### 9.2 Progressive Loading vs Always-Inject

**Choice**: Skills can be `progressive: true` (description-only at injection, full body on activation) or non-progressive (always inject full body).

**Trade-off**: Progressive skills save prompt budget (potentially thousands of tokens across dozens of skills) and reduce noise in the context window. But they add latency -- the model must make an additional tool call to Read the body on activation. Non-progressive skills are faster at execution time but consume prompt budget unconditionally. The hybrid approach (shipped packs are non-progressive, user-generated skills are progressive) gives a sensible default: well-tested canonical skills are always available, while experimental or niche skills activate only when relevant.

Empirical observation: with 24 shipped packs (each averaging ~200 tokens of body) plus ~50 user skills (each ~300 tokens of body), the always-inject approach would consume ~20K tokens just for skill bodies. Progressive loading reduces this to the description-only index (~500 tokens) plus activated bodies (~2-6 * 300 = 600-1800 tokens), a 5-10x savings.

### 9.3 Token-Overlap Router vs Argus Cascade

**Choice**: Default router is pure Python (re + set intersection) with zero dependencies. Argus cascade adds BM25, sentence-transformers embeddings, cross-encoders.

**Trade-off**: Token overlap requires no models, no network calls, no GPU, and runs in microseconds. It works on air-gapped systems and has predictable behaviour. But it misses semantic relationships ("change" and "refactor" are distinct tokens unless the synonym list is manually extended). The Argus cascade improves recall through embeddings and improves precision through cross-encoder re-ranking, at the cost of ~50MB model loading (all-MiniLM-L6-v2), ~10-50ms per inference, and the `sentence-transformers` dependency. The design allows graceful degradation: Argus is an optional enhancement, not a requirement.

The synonym list partially bridges the gap: "change", "modify", "update", "alter", "rewrite", "fix", "patch", "add", "remove", "delete", "refactor" all map to "edit". This covers common use cases without requiring embeddings.

### 9.4 Bounded Mutations vs Free-Text Rewrites

**Choice**: The optimizer emits one of four constrained mutation strategies applied as single-pass string replacements.

**Trade-off**: Bounded mutations are auditable (every change is a `(old_text, new_text)` pair), debuggable (per-round mutation log), and revertable (single unconditional revert). Free-text rewrites (what `lyra skill reflect` does) would converge faster but drift unpredictably -- the same skill would evolve differently on different runs, and intermediate states would be hard to review. The bounded edit constraint prevents runaway prompt growth. The trade-off is slower convergence: the optimizer may take 20 rounds to achieve what a free-text rewrite could do in one shot. The upstream awesome-llm-apps project confirmed this trade-off and chose the same constrained approach.

### 9.5 JSON Ledger vs SQLite

**Choice**: The skill ledger is a plain JSON file at `$LYRA_HOME/skill_ledger.json`.

**Trade-off**: JSON is inspectable (`cat` to see the ledger), has zero deployment complexity (no DB driver), and suits the data volume (one row per skill, 50 history entries each -> ~100KB for 200 skills). SQLite would offer proper transactions, concurrent read/write handling, and faster queries on large datasets. The trade-off is acceptable because: (a) the data is analytics-grade (losing one outcome across concurrent sessions is acceptable), (b) writes are bounded (one per turn per activated skill), and (c) `os.replace()` provides crash-safe atomic writes. The ledger would only need SQLite if multi-process write contention became a problem or if the history grew past ~10K entries.

### 9.6 Multi-Round Vetting vs Single-Pass Filtering

**Choice**: The vetter runs multi-round adversarial audits (default 5 rounds) with attack surface expansion between rounds.

**Trade-off**: Single-round audits miss >93% of adaptive attacks per Proteus findings. Multi-round iteration with path expansion (finding alternative bypass implementations) and surface expansion (transferring patterns to new attack objectives) catches substantially more threats. The cost is time: a full 5-round vet of a single skill may take minutes. The `quick_vet()` single-round function exists for rapid screening of many skills, and the `is_safe()` boolean gate provides a fast reject-or-escalate path.

### 9.7 Self-Improvement Rollback Threshold

**Choice**: Default rollback threshold is 5% degradation from baseline, with GEAR-Evolve pruning strategies below 10% success rate.

**Trade-off**: 5% is conservative enough to prevent most regressions from reaching production, but lenient enough that noise-induced false positives do not roll back legitimate improvements. The 5% threshold is tunable via `rollback_threshold` on `SelfImprovement.__init__()` for deployments that prefer stricter (1%) or more lenient (10%) policies.

### 9.8 Shipped Packs vs Community Marketplace

**Choice**: 24 domains of skills ship with Lyra. Additional skills can be installed from git or local paths. Marketplace integration is via Argus.

**Trade-off**: Shipped packs guarantee quality and availability but limit diversity. Community marketplaces (SkillOS, Claude Code skills directory) offer breadth but require vetting. The Argus catalog integration provides content fingerprinting, signature validation, and trust-tier assignment to bridge this gap -- marketplace skills go through A8 gates before they are loadable.

### 9.9 Deterministic vs Learned Curation

**Choice**: The primary curator (`curator.py`) is deterministic. The SkillOS curator (`skilloscurator.py`) is an optional learned alternative designed for RL training.

**Trade-off**: The deterministic curator is predictable, testable, and zero-cost. The learned curator (8B parameter model) outperforms both human curation and using Gemini-2.5-Pro directly (+9.8% improvement, 6% fewer interaction steps per arXiv:2605.06614). The trade-off is infrastructure cost: the RL training loop requires compute, and the learned curator weights need periodic retraining to avoid distribution shift. Lyra defaults to the deterministic curator and documents the SkillOS curator as a production upgrade path.

## 10. (B) Breakthrough: Self-Evolving Skills

The breakthrough insight behind Lyra's skills system is that skill evolution should be **marginal, not wholesale**; **telemetry-gated, not arbitrary**; and **reversible, not committing**.

### 10.1 The Self-Evolution Loop in Practice

The full self-evolution loop connects seven stages end-to-end:

```
1. TRAJECTORY CAPTURE
   Agent completes a turn. Router logs which skills were activated.
   Harness records outcome (success/failure/neutral) in ledger.

2. UTILITY SCORING
   After N turns, utility_score() computes per-skill (s-f)/(s+f)
   with recency boost. Top-n skills are surfaced.

3. CURATION
   curate() maps utility scores to tiers. Skills in "rewrite" or
   "retire" tier are flagged for action. Skills in "promote" tier
   are featured in SessionStart.

4. EXTRACTION
   Successful trajectories with >=4 tool calls and >=2 distinct tools
   pass the Hermes rubric. extract_candidate() produces a proposed
   SkillManifest. User review is always required.

5. OPTIMIZATION
   Flagged skills enter the optimizer loop. Each round scores the
   skill against evaluation scenarios. Analyst diagnoses failures.
   Mutator proposes a bounded edit. Accept-or-revert gates keep
   quality monotonic.

6. EVOLUTION
   In parallel or sequence, Escher-Loop and GEAR-Evolve explore the
   skill genome space. Council Mode provides conflict resolution
   for evolution decisions. PRISM monitors for drift.

7. LIFECYCLE MANAGEMENT
   SLIM evaluates marginal contribution. Skills with delta(s) approx 0
   are retired. Skills with persistent failures trigger EXPAND.
   Darwin archive stores the ancestry for traceability.
```

### 10.2 Guarantees the Pipeline Provides

1. **Monotonic quality by construction**: Every optimizer round must increase the pass rate. No regression is committed. The ledger utility score is monotonic with per-outcome recording.

2. **Human-in-the-loop at the creation boundary**: The extractor never writes to disk without review. The curator recommends actions but does not execute them. The optimizer writes to disk only on explicit `--apply`.

3. **Bounded cost per evolution cycle**: Each optimizer round costs `N+2` LLM calls (N scenarios + 1 analyst + 1 mutator). The round cap (20) bounds the maximum cost. The GEAR-Evolve exploration weight decays, naturally reducing exploration cost over time.

4. **Auditable ancestry**: Mutation log, ledger history, darwin archive, and drift reports together provide full traceability: what changed, when, why, and what the effect was.

5. **Graceful degradation on rollback**: If an optimizer round fails to apply or degrades performance, the previous state is restored. If gear strategies underperform, they are pruned. If drift exceeds critical threshold, the system recommends rollback to last known good.

### 10.3 Open Challenges

Self-evolving skills in production face three open challenges that Lyra's design acknowledges but does not fully solve:

**Reward hacking**: An optimizer could learn to "game" the evaluation scenarios by inflating scores on seen prompts while degrading on unseen ones. Mitigation: held-out evaluation scenarios not used during the optimizer loop. This is not yet implemented.

**Cross-skill interference**: Optimizing skill A for higher pass rates could degrade skill B if they share context. Mitigation: the SLIM marginal contribution metric is one approach but requires leave-one-skill-out validation, which is O(N^2) in the number of skills.

**Catastrophic forgetting**: An evolved skill that specialises to recent failure patterns could lose general-purpose knowledge. Mitigation: the bounded edit strategy constrains drift per round, and the darwin archive preserves the full ancestry for manual rollback. The question is whether, after 1000 evolution cycles across 100 skills, the archive can still be searched efficiently.

## 11. Key Sources

### Source Code

- `packages/lyra-skills/src/lyra_skills/loader.py` -- Skill frontmatter loader and SkillManifest dataclass with strict type coercion.
- `packages/lyra-skills/src/lyra_skills/router.py` -- Default token-overlap router with synonym expansion and Argus cascade integration.
- `packages/lyra-skills/src/lyra_skills/activation.py` -- Progressive skill activation with keyword matching, explicit invocations, and utility-aware ranking.
- `packages/lyra-skills/src/lyra_skills/curator.py` -- Hermes-inspired deterministic curator with 5-tier grading system.
- `packages/lyra-skills/src/lyra_skills/optimizer.py` -- Executor/Analyst/Mutator closed-loop optimizer with bounded mutations and accept-or-revert.
- `packages/lyra-skills/src/lyra_skills/extractor.py` -- Rubric-first skill extractor with HARD/SOFT criteria and secret scanning.
- `packages/lyra-skills/src/lyra_skills/ledger.py` -- Persistent outcome ledger with recency-boosted utility scoring, mutation log.
- `packages/lyra-skills/src/lyra_skills/compaction.py` -- Per-section usage tracking, stale skill archiving, compression planning.
- `packages/lyra-skills/src/lyra_skills/vetter.py` -- Proteus-inspired multi-round adversarial security vetting (5-axis).
- `packages/lyra-skills/src/lyra_skills/lifecycle.py` -- SLIM-based lifecycle management with marginal contribution estimation.
- `packages/lyra-skills/src/lyra_skills/argus_cascade.py` -- Lyra facade over harness_skill_router Argus cascade.
- `packages/lyra-skills/src/lyra_skills/argus_bridge.py` -- Bidirectional SkillManifest <-> Argus Skill translation.
- `packages/lyra-skills/src/lyra_skills/argus_telemetry_bridge.py` -- Mirror Lyra registry events into Argus telemetry ledger.
- `packages/lyra-skills/src/lyra_skills/semantic_search.py` -- Sentence-embedding-based semantic search with hybrid scoring.
- `packages/lyra-skills/src/lyra_skills/retrieval.py` -- BM25 + DCI + hybrid retrieval (Phase J).
- `packages/lyra-skills/src/lyra_skills/provider_bridge.py` -- Provider-agnostic validation and Claude-only frontmatter stripping.
- `packages/lyra-skills/src/lyra_skills/state.py` -- Per-skill enable/disable overrides with atomic persistence.
- `packages/lyra-skills/src/lyra_skills/packs/__init__.py` -- 24 shipped skill pack roots.
- `packages/lyra-skills/src/lyra_skills/installer.py` -- Skill installation from local path or git repo.
- `packages/lyra-skills/src/lyra_skills/compiler.py` -- DSPy-style SkillCompiler for typed Python function compilation.
- `packages/lyra-skills/src/lyra_skills/skilloscurator.py` -- SkillOS trainable curator with RL-compatible interface.
- `packages/lyra-skills/lyra_skills/autoskill.py` -- AutoSkill lifelong learning with 4-axis Judge.
- `packages/lyra-skills/lyra_skills/evoskill.py` -- EvoSkill failure-driven discovery with Pareto frontier.
- `packages/lyra-skills/lyra_skills/ctx2skill.py` -- Context-to-skill extraction.
- `packages/lyra-skills/lyra_skills/versioning.py` -- Skill version management.

- `packages/lyra-evolution/src/lyra_evolution/escher.py` -- Escher-Loop RSI (solver/critic populations).
- `packages/lyra-evolution/src/lyra_evolution/gear.py` -- GEAR-Evolve self-modifying search controller.
- `packages/lyra-evolution/src/lyra_evolution/council.py` -- Council Mode with STORM conflict resolution.
- `packages/lyra-evolution/src/lyra_evolution/improvement.py` -- Closed-loop self-improvement with rollback.
- `packages/lyra-evolution/src/lyra_evolution/drift_detector.py` -- PRISM prompt drift detection.
- `packages/lyra-evolution/src/lyra_evolution/generation/generator.py` -- Code generation for optimization patches.
- `packages/lyra-evolution/src/lyra_evolution/models.py` -- Evolution data models (CouncilMember, EscherSolver, GEARStrategy, etc.).
- `packages/lyra-evolution/src/lyra_evolution/sandbox/executor.py` -- Sandboxed code execution with rollback.
- `packages/lyra-evolution/src/lyra_evolution/gepa_v2.py` -- GEPA v2 prompt evolution.

- `src/skills/skill.py` -- Legacy Skill dataclass (original system).
- `src/skills/parser.py` -- Legacy ECC skill file parser.
- `src/skills/registry.py` -- Legacy skill registry with multi-index search.
- `src/skills/importer.py` -- Legacy ECC importer.

- `.lyra/skills/code-review/SKILL.md` -- Installed skill example with frontmatter, checklist, and output format.

### Research Papers Referenced

- Zhou et al., "Proteus: Multi-Round Adversarial Skill Vetting" (arXiv 2026). -- Cited in `vetter.py` for the finding that single-round audits miss >93% of adaptive attacks.
- "SLIM: Dynamic Skill Lifecycle Management" (arXiv:2605.10923). -- Cited in `lifecycle.py` for the +12.5pp over monotonic accumulation on ALFWorld.
- "Beyond Semantic Similarity: DCI for Agentic Retrieval" (arXiv:2605.05242). -- Cited in `retrieval.py` for the DCI grep-based search paradigm.
- "Group of Skills (GoSkills)" (arXiv:2605.06978). -- Cited in `retrieval.py` for multi-hop hypothesis refinement.
- "SkillOS: Trainable Skill Curation" (arXiv:2605.06614). -- Cited in `skilloscurator.py` for the 8B curator outperforming Gemini-2.5-Pro directly (+9.8%).
- "AutoSkill: Experience-Driven Lifelong Learning" -- +35-44pp cross-model transfer, cited in `autoskill.py`.
- "EvoSkill: Failure-Driven Skill Discovery for Coding Agents" -- +7.3pp OfficeQA, +12.1pp SealQA, cited in `evoskill.py`.
- "Self-Improving Agent Skills" (awesome-llm-apps). -- Executor/Analyst/Mutator pattern borrowed by `optimizer.py`.
- "Memento-Skills: Memento-style Read-Write Reflective Learning" -- Phase O ledger design influencing `ledger.py`.
- "Hermes-agent v0.12" -- Continuous-running skill tier convention adopted by `curator.py`.
- "STORM: Structured Debate for Hallucination Reduction" -- 35.9% hallucination reduction, cited in `council.py`.
