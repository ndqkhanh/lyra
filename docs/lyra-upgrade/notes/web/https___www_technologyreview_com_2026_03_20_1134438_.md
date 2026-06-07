# OpenAI is throwing everything into building a fully automated researcher (MIT Technology Review)

**Source:** https://www.technologyreview.com/2026/03/20/1134438/
**Author:** Will Douglas Heaven
**Date:** March 20, 2026

---

## Key Technical Claims

1. **OpenAI's top strategic priority** is a fully automated "AI researcher" -- an agent-based system that independently tackles large, complex problems across math, physics, biology, chemistry, and business/policy.

2. **Two-phase roadmap:**
   - **Phase 1 (Sep 2026):** "AI Research Intern" -- autonomously handles *a small number of specific research problems* at the level of tasks that would take a person a few days.
   - **Phase 2 (2028):** Fully automated multi-agent research system tackling problems "too large or complex for humans to cope with."

3. **Codex as precursor:** Codex (released Jan 2026) is described as an early version of the AI researcher. Most technical staff at OpenAI now use it. Pachocki: "I expect Codex to get fundamentally better."

4. **GPT-5 and GPT-5.4:** GPT-5 powers Codex. GPT-5.4 was released approximately early March 2026. Researchers have used GPT-5 to discover new solutions to unsolved math problems and break through dead ends in biology, chemistry, and physics puzzles.

5. **Capability driver trajectory:** GPT-3 (2020) to GPT-4 (2023) showed general capability improvements extended sustained task duration. Reasoning models (step-by-step, backtracking) provided another substantial bump.

6. **Training method:** Feed systems samples of complex tasks (hard puzzles from math/coding contests) to force learning of skills like tracking large text chunks and splitting problems into multiple managed subtasks.

---

## Architecture/Mechanism Details

- **Multi-agent orchestration:** The vision involves *multiple Codex agents working together*. Pachocki describes managing "a group of Codex agents" rather than writing code manually.

- **Scratchpad monitoring (key safety mechanism):** Reasoning models are trained to write notes on a "scratch pad" as they step through tasks. Researchers then use *other LLMs to monitor these scratch pads for misbehavior*. Pachocki: "Once we get to systems working mostly autonomously for a long time in a big data center, I think" this monitoring approach will become essential.

- **Sandboxing:** Very powerful models should be "deployed in sandboxes, cut off from anything they could break or use to cause harm."

- **Risk vectors identified:** Going off the rails, getting hacked, or misunderstanding instructions.

- **Safety publication:** On the same day, OpenAI published chain-of-thought monitoring details at openai.com/index/how-we-monitor-internal-coding-agents-misalignment/.

---

## Numbers & Benchmarks

- **No hard benchmark numbers provided** in the article.
- The article references Doug Downey (AI2) who tested top-tier LLMs on scientific tasks (arxiv.org/abs/2510.21652). GPT-5 came out on top but still "made lots of errors." Key caution: "If you have to chain tasks together, then the odds that you get several of them right in succession tend to go down."
- Downey noted he had not tested GPT-5.4, so those results "might already be stale."

---

## Perspectives on AGI / Transformative AI

- Pachocki avoided the term AGI, referring instead to "economically transformative technology."
- He stated LLMs "are not formed by evolution to be really efficient" and that even by 2028 he does not expect "systems as smart as people in all ways."
- Key insight: "you don't need to be as smart as people in all their ways in order to be very transformative."

---

## Transfer to Lyra

### One Transferable Idea: Scratchpad-Based Supervisor Monitoring for Long-Running Agent Tasks

The single most impactful and directly implementable idea from this article for Lyra is **scratchpad-based supervisor monitoring**: using one LLM agent to monitor another agent's chain-of-thought reasoning trace for misbehavior, off-track navigation, and safety violations during long-running autonomous tasks.

**How this applies to Lyra:**
- Lyra's Router (workflow orchestration layer) dispatches long-running tasks to sub-agents. During execution, a lightweight supervisor agent (or a monitoring plugin) continuously reads the sub-agent's reasoning scratchpad.
- The supervisor detects: going off-task, misinterpreting instructions, veering into unsafe operations, or cascading errors across chained subtasks.
- On detecting misbehavior, the supervisor can pause, escalate to a human, or redirect the sub-agent with corrected context.
- This is implementable as a plugin/interceptor in Lyra's agent framework without requiring model retraining.

**Why it matters:** The AI2 research cited in the article directly warns that chained tasks compound error rates -- each link in the chain multiplies failure probability. Lyra's task decomposition and delegation pipelines are exactly this: chains of subtasks. A scratchpad monitor is the countermeasure.

### Workstream Route: **§4.5 (Reliability/Safety)**

This idea maps most directly to the Reliability and Safety workstream (brainstorm/16-reliability.md, brainstorm/17-safety.md). The scratchpad monitor is fundamentally a runtime verification and guardrail mechanism. Secondary connection to **§4.2 (Router/Workflow)** for the multi-agent orchestration pattern of supervisor-worker agent topologies.

### Scoring

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Impact** | 8/10 | Directly addresses the compounding-error problem in chained agent tasks, Lyra's core execution model |
| **Effort** | 5/10 | Requires building a monitoring plugin/interceptor and scratchpad capture infrastructure; no model changes needed |
| **Tier** | T1 | Core reliability/safety improvement that unlocks longer autonomous execution |

---

*Note captured 2026-06-07 via subagent workflow.*
