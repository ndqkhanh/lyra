# Human Steering: Steer-by-Exception Panel with Proactive Preference Elicitation
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/22-steering.md) | [Code](../../src/lyra/steering/)

## Abstract
Lyra's steering module lets humans oversee running agents without babysitting: peek at state, reply to questions, approve/reject sensitive actions, redirect task direction — all from a lightweight panel. The design inverts the usual "human catches mistakes" paradigm to "agent surfaces uncertainty at decision boundaries." When confidence is below threshold, the agent generates 2-3 candidate approaches with trade-off summaries and proactively interrupts itself, presenting a multiple-choice query that produces high-quality preference pairs with full decision context.

## Method
`SteerPanel` (`src/lyra/steering/panel.py`): peek, update_state, redirect, request_decision, remove_session. `ApprovalGate`: ALLOW/ASK/DENY with pattern-based auto-approval. `InterruptHandler` (`src/lyra/steering/interrupt.py`): PAUSE/RESUME/ABORT/ROLLBACK/BARGE_IN signals with checkpoint save/restore.

## Conclusion
Implemented: SteerPanel, ApprovalGate, InterruptHandler with barge-in detection. Future: preference-learning from steering decisions.
