# Netflix, Meta, IBM speakers discuss AI and their workdays (The Register)

**Source:** The Register -- coverage of the All Things AI conference, Durham, North Carolina  
**Date:** April 4, 2026  
**Speakers:** Ben Ilegbodu (Netflix, UI architect), Justin Jeffress (Meta, developer advocate), Luis Lastras (IBM, director of language & multimodal technologies), Justin Chau (Intuit)

---

## Key Technical Claims

1. **Netflix -- Adversarial Multi-Agent Code Review.** Ben Ilegbodu described a workflow where three AI agents collaborate: one implements a feature, a second evaluates the output adversarially (finding flaws), and a third orchestrates the back-and-forth. The human acts as the final authority/decision-maker. Ilegbodu noted that this pattern lets him productively work in languages he does not natively know (Python, Bash, Groovy), but reported fatigue from "spending the whole day talking to something."

2. **Meta -- Context Rot and Prompt Chaining.** Justin Jeffress characterized LLMs as an "insatiable intern" that, unlike a human, never gets overwhelmed but suffers from "context rot" (degrading performance as conversation length grows). His fix: "context engineering" and "prompt chaining" -- decomposing a task into discrete steps each with its own prompt and fresh context window. He also described a fractal Pareto principle: AI automates 80% of a job, the human finishes the remaining 20%, but 80% of that 20% can itself be further automated, implying a nested hierarchy of automation.

3. **IBM -- Against Wishful Prompting; Decomposition via Mellea.** Luis Lastras warned that developers commonly resort to "wishful prompting" -- e.g., begging the model "please do not hallucinate" -- which has no effect. Instead, the skill needed is "decomposition": breaking complex systems into smaller, modular tasks that can be handled independently by LLM calls. IBM's open-source library **mellea.ai** was presented as providing canonical patterns for structuring those calls.

4. **Intuit -- Constraints, Not Instructions.** Justin Chau argued that LLMs may silently disregard instructions if they find what they judge to be a "better" path, so developers should give agents *constraints* rather than *instructions* (or at minimum, impose hard permission boundaries such as revoking GitHub write access).

5. **Jevons Paradox of AI Work.** The article framed the overall dynamic as a Jevons Paradox: making AI more efficient creates *more* work for developers, who now spend their days preparing context, reviewing agent output, and orchestrating multi-agent systems rather than writing code directly.

---

## Architecture / Mechanism Details

- **Adversarial agent loop:** Implementer agent -> Reviewer agent -> Orchestrator agent -> human gate. The reviewer's system prompt is explicitly set to be adversarial/critical, not collaborative.
- **Prompt chaining (Meta):** Each step in a task gets its own prompt invocation with a clean context window, avoiding the decay of long single-turn conversations.
- **Mellea.ai (IBM):** Open-source library providing reusable patterns (likely chain, map, reduce, parallel, etc.) for composing LLM calls into larger programs.
- **Permission gating (Intuit):** Hard sandboxing of agent capabilities at the API/role level rather than relying on instruction-following.

---

## Numbers and Benchmarks

- **Fractal Pareto principle (Meta):** Claimed 80% automation on first pass, then 80% of the remainder (96% total), implying nested tiers of automation rather than a one-shot 80% ceiling.
- No concrete latency, accuracy, or throughput benchmarks were reported in this coverage. The article is qualitative.

---

## Transfer to Lyra

**One idea:** Netflix's **adversarial multi-agent code review** -- having a dedicated "reviewer" agent that is explicitly prompted to be adversarial and find flaws, separate from the "implementer" agent, with a human or a lightweight orchestrator agent mediating the loop.

**Route:** This maps cleanly onto Lyra's Quality/Verification workstream ($\S 4.3$). Lyra already has a `verification-loop` skill; extending it to support an adversarial reviewer persona (rather than a single-model self-verify) would directly implement this pattern. The fractally nested Pareto from Meta also suggests that Lyra's verification pipeline should be recursively applied: verify the output, then verify the verification, etc., stopping when the cost of the next tier exceeds the expected value of the defects it would catch.

**Secondary idea (Intuit):** "Constraints, not instructions" should inform Lyra's Safety workstream ($\S 4.4$), where permission boundaries (e.g., filesystem ACLs, network blacklists) replace prompting-based safety.
