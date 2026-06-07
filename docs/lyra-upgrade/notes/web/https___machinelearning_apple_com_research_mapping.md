# Mapping the Design Space of User Experience for Computer Use Agents (Apple ML Research)

**Source:** https://machinelearning.apple.com/research/mapping  
**arXiv:** https://arxiv.org/abs/2602.07283  
**Authors:** Ruijia Cheng, Jenny T. Liang (CMU), Eldon Schoop, Jeffrey Nichols  
**Date:** February 2026 | **Venue:** IUI 2026 (ACM, 17 pages)

---

## Key Technical Claims

1. **UX for computer-use agents is under-explored.** Despite the proliferation of LLM-based agents that manipulate UI elements (web navigation, desktop automation), there is no systematic map of UX design considerations for this new interaction paradigm.

2. **Four-pillar taxonomy of UX considerations.** Through literature review + practitioner interviews (N=8), the authors derive a taxonomy with four top-level categories:
   - **User prompts** -- how users specify commands, express intent, provide feedback to the agent
   - **Explainability** -- what the agent reveals about its reasoning, plan, or next steps
   - **User control** -- ability to interrupt, correct, approve/reject, or steer agent actions
   - **Users' mental models** -- how accurately users understand the agent's capabilities, limitations, and failure modes

   Each category has subcategories and concrete example design features (detailed in the full PDF).

3. **Wizard-of-Oz study validates and extends the taxonomy.** With 20 participants, a human operator simulated a web-based computer-use agent across three execution modes:
   - **Normal** -- agent performs expected actions without incident
   - **Error-prone** -- agent makes mistakes, misclicks, misreads UI
   - **Risky** -- agent attempts actions with potentially irreversible consequences (e.g., submitting a purchase, deleting a file)

4. **Divergence in user needs.** Not all users want the same UX. The study found systematic variation in preferences for level of control, amount of explanation, and tolerance for autonomous action -- depending on task criticality, user expertise, and trust.

5. **Design space map.** The paper's main artifact is a map that connects design areas (prompts, explainability, control, mental models) to each other and to user scenarios, helping developers reason about trade-offs.

---

## Architecture / Mechanism Details

This is a **human-computer interaction (HCI) paper**, not a systems paper. There is no agent architecture, no training pipeline, no inference stack. The method is:

- **Phase 1 -- Taxonomy construction:**
  - Survey of existing computer-use agent systems (web agents, desktop agents, GUI agents) drawn from literature (2018-2025)
  - Semi-structured interviews with 8 practitioners (UX designers and AI/ML engineers) who had built or evaluated computer-use agents
  - Iterative card-sorting and affinity diagramming to cluster design features into categories

- **Phase 2 -- Wizard-of-Oz (WOz) study:**
  - 20 participants (mix of technical and non-technical backgrounds)
  - Task: participants asked a "computer-use agent" (actually a researcher behind the scenes) to perform web-based tasks (booking, research, form-filling)
  - Three conditions within-subjects: normal, error-prone, risky
  - Measures: qualitative feedback, think-aloud protocols, post-task interviews
  - Analysis: thematic coding against the Phase 1 taxonomy; identification of new themes and cross-category connections

---

## Numbers & Benchmarks

| Metric | Value |
|---|---|
| Practitioner interviews (Phase 1) | N = 8 |
| WOz study participants (Phase 2) | N = 20 |
| Execution modes tested | 3 (normal, error-prone, risky) |
| Paper length | 17 pages (ACM format) |
| Conference | IUI 2026, Paphos, Cyprus |
| License | CC BY-NC-ND 4.0 |

No quantitative benchmarks, accuracy numbers, or performance metrics are reported. The paper is qualitative/empirical.

---

## Transfer to Lyra

### One transferable idea

Lyra, as an autonomous agent performing computer-use tasks (web search, file manipulation, browser automation), faces the same UX design challenges this paper catalogues. **The paper's key insight for Lyra is the taxonomy of Explainability + User Control trade-offs across execution modes.**

Currently, Lyra's user interface is primarily the chat terminal -- the user types a command, Lyra executes it, and output appears. There is minimal structured affordance for:
- Previewing what Lyra intends to do before it acts
- Interrupting or correcting an in-progress action
- Understanding why Lyra chose one action over another
- Calibrating user trust (knowing when Lyra is uncertain vs. confident)

### Concrete recommendations for Lyra

1. **Mode-aware explainability.** The paper shows that users want MORE explanation in error-prone/risky contexts and LESS explanation in routine contexts. Lyra could implement a "confidence signal" -- when the model's confidence in its planned action is below a threshold, it could pause and surface its plan for user approval before proceeding.

2. **Steerable execution.** The "user control" category suggests Lyra should support interrupt/hold/correct/rollback gestures. For example, during a multi-step file operation, Lyra could emit a preview diff and wait for user confirmation before applying changes that are irreversible.

3. **Mental model calibration.** New users overestimate and experienced users underestimate Lyra's capabilities. A brief onboarding or contextual hint that communicates Lyra's actual scope (what it can and cannot do, where it tends to fail) would align user expectations and reduce frustration.

### Workstream route

The most natural home for this transfer is **SS4.3 (Human-Agent Interaction)** since the paper is fundamentally about UX design for agent interaction. However, the error-mode and risky-execution findings also inform **SS4.6 (Safety & Reliability)** by providing a framework for when and how agents should escalate to the user.

**Recommended approach:** Use this taxonomy as a checklist during Lyra's UI/UX redesign. For each of the four pillars (prompts, explainability, control, mental models), conduct a gap analysis against Lyra's current interface. The error-prone and risky mode findings should feed directly into safety protocol design for SS4.6.
