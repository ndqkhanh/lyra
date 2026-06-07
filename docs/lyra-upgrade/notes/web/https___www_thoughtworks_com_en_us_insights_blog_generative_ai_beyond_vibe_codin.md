# Beyond vibe coding: The five building blocks of AI-native engineering (Thoughtworks)

**Source:** https://www.thoughtworks.com/en-us/insights/blog/generative-ai/beyond-vibe-coding-the-five-building-blocks-of-aI-native-engineering
**Author:** Sunit Parekh (Thoughtworks)
**Published:** March 18, 2026
**Tags:** ai-native-engineering, vibe-coding, agent-building-blocks, spec-to-code, context-engineering, model-specialization, methodology, BMAD

---

## Key Technical Claims

1. **Five-building-block stack for AI-native engineering:** Agent (execution), Model (knowledge), Methodology (process discipline), Spec (requirements articulation), Context (guardrails/institutional knowledge). Enterprise development must orchestrate all five deliberately -- not just prompt at a chat interface.

2. **Agent thrashing is the central process risk:** AI agents become trapped in infinite/lengthy self-correction loops, fixing one error only to introduce another. Countermeasures include structured prompts, CI/CD integration, test-driven AI (TDA), audit trails, and mandatory human review gates.

3. **Model market bifurcation:** The industry is moving away from single general-purpose models toward specialized models for distinct cognitive tasks -- code generation, architectural reasoning, test/QA, documentation synthesis, and security analysis. Each specialization has a recommended frontier model (Claude 4.6 Sonnet for planning/migration, Gemini 3.1 Pro for 2M+ token analysis, GPT 5.3 Codex for hard algorithmic problems, GLM 5 for cost-efficient boilerplate).

4. **Effectiveness proportional to spec quality:** The "spec to code" pipeline is the critical bridge between human intent and autonomous execution. Tools like SpecKit (constitution -> specify -> plan -> tasks -> implement) and OpenSpec (proposal -> apply -> archive) demonstrate that structured spec ingestion directly determines agent output quality.

5. **Context is institutional knowledge, not just a prompt prefix:** Context engineering involves strategic curation of design principles, security policies, architecture guidelines, and domain-specific logic embedded into the agent's workspace -- not ad-hoc system prompts.

---

## Architecture/Mechanism Details

- **Agent capabilities taxonomy:** file system navigation/analysis, terminal command execution, automated testing/verification, autonomous multi-file editing/refactoring, supervised autonomy (human review via PR).

- **Named agent frameworks:** Claude Code (Anthropic, Claude-only), OpenCode (open-source, privacy-first, any model), Cline (VS Code, granular tool permissions), Antigravity/Cursor/Windsurf (IDE-native agents).

- **BMAD Method (multi-role orchestration):** Simulates a full software team through role-based agent orchestration using a "plan-analysis-design-architect-dev-test" loop. Cross-agent consensus on design is required before implementation proceeds, reducing hallucination drift.

- **Thoughtworks AI/works 3-3-3 delivery model:** concept in 3 days, functional prototype in 3 weeks, production-ready MVP in 3 months. Supports legacy modernization from reverse engineering through spec-to-code generation.

- **SpecKit pipeline (5 steps):** constitution -> specify -> plan -> tasks -> implement. OpenSpec workflow (3 steps for brownfield): proposal -> apply -> archive.

- **Context engineering mechanisms (4):** agent skills (domain-specific), rules files (AGENTS.md/.cursorrules), security guardrails (never-allow rules), design system guidelines.

---

## Numbers & Benchmarks

- **Gemini 3.1 Pro context window:** 2M+ tokens for large-scale codebase analysis.
- **3-3-3 delivery model:** Concept in 3 days, functional prototype in 3 weeks, production-ready MVP in 3 months.
- **OWASP Top 10:** referenced as baseline for security vulnerability analysis models.
- **GLM 5 positioning:** cost-efficiency for high-volume boilerplate generation and unit testing (no explicit token/cost numbers given).

---

## Transfer to Lyra (one idea + workstream route)

**Idea:** Adopt a **spec-to-code five-step pipeline** as the ingestion frontend for Lyra's agent execution engine. Currently Lyra's agent intake is unstructured -- the User sends a prompt and Lyra figures it out. By layering a SpecKit-like pipeline (constitution -> specify -> plan -> tasks -> implement) upstream of agent execution, Lyra would force structured intent articulation before any code is written. This directly addresses the "agent thrashing" risk by constraining the solution space before execution begins, and provides an audit trail (constitution+spec) that can be versioned and reviewed independently of generated code.

**Workstream route:** SS 4.2 (Agent Framework & Execution) -- specifically augmenting the Agent Scheduler/Dispatcher with a structured spec ingestion stage that normalizes user requests into constitution-spec-plan-task layers before routing to execution agents. The spec layer would also be exposed as a new top-level Lyra command (`/lyra spec`) for brownfield modification workflows (borrowing OpenSpec's proposal-apply-archive pattern).

---

## Related Lyra Plans

- `docs/lyra-upgrade/plans/02-memory.md` -- context engineering overlaps
- `docs/lyra-upgrade/plans/05-router.md` -- agent routing overlaps with spec-to-code dispatch
- `docs/lyra-upgrade/plans/07-plugins.md` -- agent skill definitions for domain context injection
- `docs/lyra-upgrade/brainstorm/15-research.md` -- BMAD multi-role orchestration
