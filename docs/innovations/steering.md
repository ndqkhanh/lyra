# Human Steering: Steer-by-Exception Panel with Proactive Preference Elicitation
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/22-steering.md) | [Code](../../src/lyra/steering/)

## Abstract
Lyra's steering module lets humans oversee running agents without babysitting: peek at state, reply to questions, approve/reject sensitive actions, redirect task direction — all from a lightweight panel. The design inverts the usual "human catches mistakes" paradigm to "agent surfaces uncertainty at decision boundaries." When confidence is below threshold, the agent generates 2-3 candidate approaches with trade-off summaries and proactively interrupts itself, presenting a multiple-choice query that produces high-quality preference pairs with full decision context.

## Method
`SteerPanel` (`src/lyra/steering/panel.py`): peek, update_state, redirect, request_decision, remove_session. `ApprovalGate`: ALLOW/ASK/DENY with pattern-based auto-approval. `InterruptHandler` (`src/lyra/steering/interrupt.py`): PAUSE/RESUME/ABORT/ROLLBACK/BARGE_IN signals with checkpoint save/restore.

## Working Flow

You are watching a Lyra agent research a coding problem, but you notice it's going down a rabbit hole — it keeps fetching docs about an old deprecated library when it should be looking at the newer one. You don't need to kill the session and restart. You open the SteerPanel (`src/lyra/steering/panel.py`) which shows the agent's current task and recent tool calls.

**Example:** Redirecting a wandering agent mid-session.

1. The agent calls `web_search` to look up "React state management" — you see it in the SteerPanel log.
2. It picks a dated library (Flux) instead of modern options (Zustand, Jotai). You click the session in SteerPanel and call `redirect("Focus on Zustand vs Jotai comparison instead")`.
3. The InterruptHandler sends a PAUSE signal, saves a checkpoint of the agent's current state, injects your redirect message, then issues RESUME.
4. The agent picks up from the checkpoint but now targets the correct libraries.
5. Two steps later, the agent wants to install a package — the ApprovalGate intercepts it with ASK status. You get a popup: "Allow `npm install jotai`?" You click Approve and the agent continues.

## Conclusion
Implemented: SteerPanel, ApprovalGate, InterruptHandler with barge-in detection. Future: preference-learning from steering decisions.
