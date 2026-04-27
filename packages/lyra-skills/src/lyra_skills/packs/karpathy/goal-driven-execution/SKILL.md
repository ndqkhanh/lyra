---
id: goal-driven-execution
name: Goal-Driven Execution
description: Every tool call advances the acceptance tests; if not, stop and replan.
---

At every step, answer: "Which acceptance test does this move closer to green?"
If you cannot, do not proceed with the action — call `ReplanTool` or ask the user.
