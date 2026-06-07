# zjunlp/SkillNet — Deep-Read

**Repo:** https://github.com/zjunlp/SkillNet | **Paper:** arXiv 2603.04448 | **Website:** http://skillnet.openkg.cn/
**SDK version:** 0.0.18 | **Language:** Python 3.9+ | **License:** MIT

---

## 1. Headline Feature & Mechanism (how the code really works)

**Headline:** SkillNet is an open infrastructure — "npm for AI agent skills" — that lets agents search, install, create, evaluate, and cross-connect reusable skill packages via a central registry (500,000+ community skills) or local skill directories.

**How it really works — mechanical walkthrough:**

The codebase has two layers: a hosted REST API backend (not in this repo) and a Python SDK/CLI client (`skillnet-ai`) that is the user-facing entry point. The SDK is structured around five orthogonal capabilities, each backed by a dedicated module:

1. **Search** (`searcher.py`): Makes an HTTP GET to `api-skillnet.openkg.cn/v1/search` with `mode=keyword|vector`. Returns pydantic-validated results (`SkillModel`). No auth needed. The keyword mode sends string filters; vector mode sends a similarity threshold.

2. **Download** (`downloader.py`): Parses a GitHub tree/blob URL (e.g., `https://github.com/owner/repo/tree/main/path`), then walks the GitHub Contents API recursively to list files and download each via `raw.githubusercontent.com`. Supports mirror URLs for restricted networks (e.g., `ghfast.top`). No auth needed for public repos.

3. **Create** (`creator.py`): Four sub-modes, all using LLM calls (OpenAI-compatible) to generate a skill package:
   - *Trajectory*: LLM reads a user/agent log, extracts candidate skills (JSON list in `<Skill_Candidate_Metadata>` tags), then generates per-candidate file content (SKILL.md + scripts) parsed via `## FILE: path` markup.
   - *GitHub repo*: Fetches repo metadata, README, file tree, language breakdown, AST/code analysis (`_GitHubFetcher`, `_CodeAnalyzer` with recursive AST for Python and regex for 7 other languages), then feeds a large prompt to the LLM for skill generation.
   - *Office doc*: Extracts text from PDF/PPTX/DOCX with `PyPDF2`/`python-pptx`/`python-docx`, then LLM-generates a skill.
   - *Prompt*: Direct LLM generation from a user-written description.

4. **Evaluate** (`evaluator.py`): The most sophisticated module. Loads SKILL.md + scripts + references for a skill, optionally runs Python scripts in a sandboxed `ScriptRunner` (subprocess with timeout, AST-parse of docstrings to extract usage commands), then calls an LLM with a detailed structured prompt to score 5 dimensions: Safety, Completeness, Executability, Maintainability, Cost-Awareness (each Good/Average/Poor). Batch evaluation uses `ThreadPoolExecutor` with a bounded-in-flight pattern.

5. **Analyze** (`analyzer.py`): Scans a local skill directory, extracts names/descriptions from SKILL.md frontmatter, calls LLM to map 4 relationship types (`similar_to`, `belong_to`, `compose_with`, `depend_on`), saves to `relationships.json`.

The entire SDK is wrapped in a CLI (`cli.py`, via Typer+Rich) and a `SkillNetClient` facade class in `client.py` that delegates to the module classes above.

---

## 2. Architecture & Core Modules

```
skillnet-ai/
  pyproject.toml          # v0.0.18, MIT, Python >=3.9
  src/skillnet_ai/
    __init__.py           # Exports all public classes
    client.py             # SkillNetClient facade — aggregates all 5 capabilities
    cli.py                # Typer CLI (skillnet <search|download|create|evaluate|analyze>)
    searcher.py           # SkillNetSearcher — HTTP client to public REST API
    downloader.py         # SkillDownloader — GitHub Contents API + mirror fallback
    creator.py            # SkillCreator — LLM-based skill generation (4 modes)
    evaluator.py          # SkillEvaluator — 5-dim quality scoring via LLM
    analyzer.py           # SkillRelationshipAnalyzer — skill graph via LLM
    models.py             # Pydantic models: SkillModel, MetaModel, SearchResponse
    prompts.py            # All LLM prompt templates (~900 lines of detailed instructions)

skills/skillnet/          # Portable SKILL.md skill that wraps the CLI for any agent
  SKILL.md                # Search-before-build workflow, security policy
  references/             # API reference, security/privacy, workflow patterns
  scripts/                # skillnet_create.py, skillnet_validate.py

experiments/              # Evaluation against ALFWorld, ScienceWorld, WebShop
  alfworld_run.py
  scienceworld_run.py
  webshop_run.py
  src/
    skill.py              # SkillModule — loads SKILL.md metadata, retrieves skills by task
    prompt_generator.py   # Prompt templates for skill retrieval + procedure generation
    skills/               # Pre-built skills used in experiments (alfworld/, scienceworld/, webshop/)
```

**Data flow for the skill-SDK:**

```
User/Agent
  |-- pip install skillnet-ai
  |-- skillnet search "pdf" --mode keyword
  |     \-- GET api-skillnet.openkg.cn/v1/search?q=pdf&mode=keyword → [SkillModel...]
  |-- skillnet download <url>
  |     \-- GitHub Contents API → local filesystem
  |-- skillnet create trajectory.txt  [needs API_KEY]
  |     \-- LLM (trajectory → candidate metadata → skill files on disk)
  |-- skillnet evaluate ./my-skill    [needs API_KEY]
  |     \-- Load SKILL.md → optional script run → LLM → {safety, completeness, ...}
  |-- skillnet analyze ./my-skills    [needs API_KEY]
        \-- Read all SKILL.md → LLM → relationships.json
```

**Integration patterns:** SkillNet itself is packaged as a portable agent skill (`skills/skillnet/`) for Claude Code, Codex, OpenClaw, and MCP servers. It also has a first-class MCP server (community-maintained by CycleChain).

**Dependencies (runtime):** `requests`, `openai`, `pydantic`, `tqdm`, `typer`, `rich`, `PyPDF2`, `pycryptodome`, `python-docx`, `python-pptx`, `json-repair`.

---

## 3. Performance/Benchmarks (real numbers from the repo)

The repo does not publish performance benchmarks for the SDK itself (search latency, creation throughput, etc.). However, it includes a full experiment suite evaluating the **effectiveness of skill-augmented agents**. The `experiments/` directory tests against three established agent benchmarks:

- **ALFWorld** — Text-based household task completion
- **ScienceWorld** — Scientific reasoning tasks
- **WebShop** — Web shopping tasks

Running command format:
```bash
python alfworld_run.py --model o4-mini --split dev --max_workers 10 --exp_name alf_test --use_skill
python scienceworld_run.py --model o4-mini --split test --max_workers 5 --exp_name sci_test --use_skill
python webshop_run.py --model o4-mini --max_workers 3 --exp_name web_test --use_skill
```

The flag `--use_skill` toggles the SkillNet skill-augmentation module. The paper (arXiv 2603.04448) contains the actual scores. The experimental design:
1. Pre-built skills (SKILL.md files in `experiments/src/skills/`) are loaded from disk.
2. The `SkillModule` uses LLM retrieval to find relevant skills for a given task.
3. Retrieved skills' content is concatenated into an "overall procedure" prompt.
4. The agent executes with this augmented context vs. baseline (no skills).

The repo also has a GitHub Actions workflow (`.github/workflows/skill-review.yml`) that runs `tesslio/skill-review` on PRs modifying SKILL.md files, showing a commitment to quality review automation.

---

## 4. Trade-offs (wins vs. loses)

**Wins:**

- **No-auth search & download:** Search and public-repo download require zero credentials — lowers adoption friction to zero.
- **LLM-as-evaluator design:** The 5-dim evaluation prompt is extremely detailed (~400 lines), covering edge cases like instruction-only skills, script execution failures, correct vs. incorrect formulas, and health disclaimers. This allows nuanced automated QA without building a hand-crafted test harness.
- **Multi-source skill creation:** Supporting trajectories, GitHub repos, office docs, and free-text prompts makes it easy to turn anything into a skill.
- **Portable skill format:** Standardized `SKILL.md` layout with `scripts/`, `references/`, `assets/` subdirectories means skills are interoperable across agent frameworks.
- **MCP + OpenClaw integration:** The ecosystem integrations (MCP server, OpenClaw built-in, Claude Code/Codex skill install) mean the platform is reachable from multiple agent entry points.
- **Mirror support for restricted networks:** Built-in `GITHUB_MIRROR` env var and `--mirror` flag acknowledge the China/international user base.

**Loses / Drawbacks:**

- **LLM dependency for 3 of 5 operations:** `create`, `evaluate`, and `analyze` all require calling an expensive LLM (default `gpt-4o`). This means operational cost scales with usage, and quality is bounded by the LLM's capability. No offline/rule-based fallback for these operations.
- **No self-hosted backend:** The search/registry API (`api-skillnet.openkg.cn`) is a hosted service. There is no documented way to run a private registry. This limits enterprise adoption where skills must remain air-gapped.
- **Download locked to GitHub:** `skillnet download` only accepts GitHub URLs. No support for GitLab, Bitbucket, Hugging Face Hub, or S3/artifact registries.
- **No skill versioning or signing:** The downloader pulls from a GitHub tree ref (branch or commit), but there's no semantic versioning, content hashing for integrity, or cryptographic signing to verify skill provenance.
- **No sandboxed script execution:** The `ScriptRunner` in the evaluator runs Python scripts via `subprocess.run` with a simple timeout. There is no containerization, temporary filesystem isolation, or network blocking. This is labeled "optional" (default off), but the evaluator's `--run-scripts` flag could pose risk in untrusted skill evaluation.
- **Skill quality depends entirely on SKILL.md:** The evaluation prompt is sophisticated, but the skill format is essentially markdown-driven. There is no formal action schema, parameter typing, or pre/post-condition specification. Skills are unstructured text consumed by an LLM — not deterministic modules.
- **Experimental benchmarks not reproduced:** The experiment scripts clone external repos (ALFWorld, ScienceWorld, WebShop) and rely on their specific dependency setups. The README advises separate conda environments for each, indicating significant setup complexity.
- **Single-client architecture:** The `SkillNetClient` is a thin facade that delegates to module classes, but all operations are synchronous. There is no async/streaming support for LLM-heavy operations like batch evaluation.

---

## 5. Design Rationale (why this approach)

1. **"npm for AI agents" as the core abstraction:** Skills as first-class, standardized, shareable packages mirrors the package-manager pattern that made npm/PyPI successful. The key insight is that agent capabilities can be distributed as structured text (SKILL.md + scripts), not as compiled plugins. This radically lowers the barrier to contribution.

2. **LLM-native all the way down:** Rather than building rule-based parsers, static analyzers, or hand-crafted rubrics, every operation that needs understanding (creation, evaluation, relationship analysis) delegates to an LLM. This is pragmatic because the skill format is unstructured natural language. The trade-off is cost and latency, but the design accepts these because the benefit — handling arbitrary skill content without custom tooling — outweighs them.

3. **Free tier for core discovery:** Search and public download are free, no auth. This is a deliberate growth strategy: the most common friction in agent tool adoption is "finding the right skill." By making discovery zero-friction, SkillNet drives usage and then monetizes via the LLM-based creation/evaluation/analysis operations.

4. **Skill format designed for progressive disclosure:** The SKILL.md format puts concise orchestration in the main file and pushes detailed documentation to `references/`, deterministic logic to `scripts/`. This mirrors the "context-is-a-public-good" philosophy — agents should only load what they need.

5. **Agent-first rather than developer-first:** The portable skill (`skills/skillnet/`) is designed to be dropped into any agent framework's skill directory. The SKILL.md itself contains a complete workflow (search-before-build, confirm-before-download, post-task creation) that the agent reads and follows. This means the "user" of SkillNet can be an autonomous agent, not just a human developer.

6. **Evaluation as a product differentiator:** The 5-dimension evaluation rubric (Safety, Completeness, Executability, Maintainability, Cost-Awareness) with detailed per-dimension guidance creates a quality signal that the central registry can display. This differentiates SkillNet from a simple search index — it provides a trust mechanism for community-contributed skills.

7. **Ecosystem integrations multiply reach:** MCP server for desktop IDEs, OpenClaw for web agents, Claude Code/Codex skill install for code agents — each integration targets a different agent consumption mode, making SkillNet the default skill supply chain regardless of framework.

---

## 6. Transfer to Lyra

**One idea:** **Treat agent skills as a first-class supply chain with a standardized packaging format and automated quality evaluation.** Lyra currently has skills/abilities baked into the codebase as Python modules or hard-coded tool definitions. Adopting a SkillNet-like approach means:

- Skills become self-describing packages (SKILL.md-style YAML frontmatter + instructions + scripts).
- A registry/service (even a local one) indexes available skills with quality scores.
- LLM-based evaluation gates which skills get used.
- Skills can be created on-the-fly from execution traces, converting successful workflows into reusable assets.

**Workstream route:** §4.x Capability Supply Chain / Skill Marketplace

Specifically, this maps to Lyra's existing workstream §4.0 (Agent Capability) or the emerging §4.x for third-party extensions:

| Route | Mapping |
|-------|---------|
| **§4.0 — Agent Core Capabilities** | Skill format standardization, SKILL.md frontmatter for triggers/descriptions |
| **§4.x — Third-Party Skills** | A local or federated skill registry for Lyra, auto-creation from trajectories, quality gates |
| **§4.x — MCP Integration** | Leverage SkillNet's MCP server pattern for Lyra desktop/IDE integrations |

**Impact:** 6/10 — High value but not core. A standardized skill supply chain would make Lyra extensible by the community and dramatically reduce the cost of adding new capabilities. However, Lyra already has a working ability system, so this is incremental improvement rather than a missing essential.

**Effort:** 5/10 — Moderate. The core ideas (SKILL.md format, LLM-based evaluation, GitHub-based distribution) are already open-source. The main work would be: (1) adapting the skill format to Lyra's existing ability/tool schema, (2) building a Lyra-specific skill evaluator tuned to Lyra's safety and correctness requirements, and (3) creating the automatic skill-creation-from-trajectory pipeline.

**Tier:** **Tier 2 — Package & Polish** (worthy of serious consideration for the v2 capability extension milestone, not blocking the initial architecture)

**LICENSE:** MIT — fully compatible with Lyra's licensing. No restrictions on use, modification, or distribution. Credit to ZJUNLP required only for the notice text.
