# SWE-bench Verified (SWE-bench Team / ICLR 2024)

Source: https://www.swebench.com/verified.html

## Key Technical Claims

- SWE-bench Verified is a **human-validated subset of 500 SWE-bench instances**. Human annotators verified problem description clarity, test patch correctness, and task solvability given available information. The goal is more reliable evaluation than the full SWE-bench set.
- Supports comparison across "a wide variety of AI coding systems, from simple LM agent loops to RAG systems to multi-rollout and review type systems."
- Published at ICLR 2024; arXiv:2310.06770. Built in collaboration with OpenAI.

## Architecture / Mechanism Details

**Bash-Only Evaluation Setup (mini-SWE-agent):**
- Purpose: Isolate language model capability from scaffolding complexity. "No tools, no special scaffold structure; just a simple ReAct agent loop."
- Uses a specific YAML config (on GitHub) shared across all models.
- **Release 1.x vs 2.x divergence**: Release 2.x uses tool calling to invoke actions; 1.x parses actions from output strings. Results across major versions are NOT comparable.
- **Temperature**: For release 1.x and earlier, LM temperature = 0.0 (if supported). For release 2.x+, temperature parameter is not set.
- **Versioning policy**: Versions correspond to tags in mini-SWE-agent repo. Minor/patch = minor fixes and prompt clarifications only. Team states: "We do *not* aim to tune the configuration and setup to reach higher and higher scores."
- **ReAct loop** (arXiv:2210.03629) as the underlying agent paradigm.

**Leaderboard Structure:**
- Two views: (a) mini-SWE-agent "bash-only" results for apples-to-apples LM comparison, (b) full leaderboard for arbitrary agent systems.

## Numbers & Benchmarks (if any)

No concrete benchmark scores, resolution rates, or model rankings are present on this page. The actual leaderboard data is dynamically loaded client-side. The page is primarily an explanation / methodology reference.

## Transfer to Lyra

**One idea**: Adopt the "bash-only evaluation" isolation strategy. Evaluate Lyra's core code-generation capability using a minimal ReAct agent loop with no tools, no special scaffolding — just raw model + bash. This separates model quality from orchestration complexity, giving a clean signal on where to invest: model improvement vs. agent scaffolding.

**Route to §4.x**: This maps to §4 (Verification & Evaluation). Build a dedicated minimal-evaluation harness (analogous to mini-SWE-agent) that tests Lyra against a curated set of coding tasks using the simplest possible agent loop. Results feed directly into model selection (§2) and scaffolding design (§3).
