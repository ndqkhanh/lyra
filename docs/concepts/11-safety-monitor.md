# Safety Monitor

> **A continuous, cheap nano-model observer that watches the trajectory and votes alongside hooks.** | **Phase:** 2
> **Jargon:** *nano-model* = a tiny on-device classifier (e.g., Llama Guard 3 1B) running at ~50 ms/inference; *hooks* = deterministic lifecycle gates that run before/after every tool call; *soft-stop* = let the in-flight call finish, then interrupt at the next turn boundary rather than aborting mid-call; *trajectory* = the accumulated sequence of turns, tool calls, and outputs the agent has produced so far.

##  Architecture

The safety monitor runs in parallel to the [agent loop](01-agent-loop.md). It samples every Nth step, asks a **nano-model** "is this agent still doing what it was asked to do?", and votes alongside [hooks](02-tools-and-hooks.md) on whether to interrupt. Where hooks are synchronous gates at lifecycle boundaries, the safety monitor is an asynchronous observer that watches the trajectory as it accumulates. The monitor and hooks are independent voters -- either can interrupt, and together they vote on borderline cases.

```mermaid
sequenceDiagram
    participant Agent
    participant Loop as Agent Loop
    participant Monitor as Safety Monitor
    participant PB as Permission Bridge
    participant User

    Loop->>Agent: turn N: "edit src/foo.py"
    Agent->>Loop: tool call: Write("foo.py")
    Loop->>PB: decide → ALLOW
    Loop->>Monitor: sample? (N % 4 == 0)
    Monitor->>Monitor: classify <br/>5 signal categories
    alt signal exceeds threshold
        Monitor-->>Loop: vote INTERRUPT
        Note over Loop,User: soft-stop: let in-flight call finish
        Loop->>User: verdict + critique
        User-->>User: /approve-continue or /abort
    else all signals clean
        Monitor-->>Loop: vote CONTINUE
        Loop->>Agent: turn N+1
    end
```

The monitor uses its own model client, configured separately from the **fast** and **smart** slots (see [Two-Tier Routing](10-two-tier-routing.md)), so the same provider does not see both the generator's context and the monitor's prompt. This provides a small but real defence against *adversarial steering* -- the generator inferring the monitor's existence and tailoring its output to hide from it.

##  Signal Categories

The monitor runs every N steps (default 4) and classifies the current trajectory against five signals:

| Signal | Detection Method | What It Catches |
|--------|-----------------|-----------------|
| Out-of-scope | nano-model checks whether edited files are outside the plan's expected file set | Agent silently expands blast radius |
| Loop/repetition | Rule: same tool+args digest appears 3+ times in a 16-call window | Runaway agent stuck on the same action |
| Cost burn | Rule: cost-per-step exceeds rolling 95th percentile by 3x | Budget bomb or infinite loop with expensive calls |
| Hypothesis drift | nano-model checks whether agent investigates something unrelated to the original task | Agent chases a tangent and never returns |
| Adversarial injection | Rules + nano-model jointly check for known prompt-injection patterns; strips content and annotates critique | Attacker input hijacks agent instructions |

##  Soft-Stop Semantics

When the monitor votes interrupt, the loop does not abort mid-tool-call. It finishes the in-flight call first (so the filesystem is never left in a half-edited state), then at the next turn boundary surfaces the verdict to the user and waits for `/approve-continue` or `/abort`. The verdict is appended to the transcript as a **critique** (an annotated note visible to the model) so the generator knows why it was interrupted. Hard-aborting in the middle of a destructive tool call is more dangerous than letting it finish with a flag set -- the [Permission Bridge](09-permission-bridge.md) already blocked the dangerous part at the tool level.

##  Configuration

```toml
# ~/.lyra/config.toml
[safety_monitor]
enabled = true
model = "llama-guard-3-1b"            # nano-model for classification
monitor_every_n_steps = 4             # sample every Nth turn (1 = synchronous & expensive; 16 = cheap but lags ~half a turn)
out_of_scope_threshold = 0.7          # confidence threshold for scope-flag
hypothesis_drift_threshold = 0.6      # confidence threshold for drift-flag
```

##  Real Numbers (target estimates)

| Metric | Value | Notes |
|--------|-------|-------|
| Nano-model inference latency | ~50 ms / call | Llama Guard 3 1B on GPU |
| Token overhead per sample | ~150 tokens | prompt + compact trajectory summary |
| False-positive rate (target) | < 5 % | Measured against `lyra safety redteam --suite default` |
| Red-team suite pass rate (target) | > 95 % | Adversarial injection, scope violation, loop-inducement, cost bomb |

##  When to Use / When NOT to Use

The safety monitor runs by default every 4 steps. Bump cadence to 1 (synchronous) for high-risk sessions involving writes or bypass mode. Run `lyra safety redteam --suite default` periodically to verify the monitor still catches known attack patterns -- a regression shows up in CI as a falling pass rate on the suite.

**Disable the monitor** only in deterministic CI runs with short, well-understood tasks. The monitor can produce false positives on unusual workflows -- review and dismiss with `/approve-continue`. It is an additional observer, not the primary safety layer (hooks, [Permission Bridge](09-permission-bridge.md), and worktree isolation are the main surface).

##  Why This Design

Deterministic hooks alone cannot catch every failure mode. An agent can stay strictly within its allowed tool set while drifting far from the original task -- editing files outside the plan's scope, chasing unrelated hypotheses, or burning budget on loops. The nano-model adds a **semantic layer** that detects these drifts where no tool-level rule would trigger. The soft-stop semantics ensure the filesystem is never left in a half-edited state.

##  Where Next

- **Implementation block:** [docs/blocks/12-safety-monitor.md](../blocks/12-safety-monitor.md)
- **Build plan:** [docs/lyra-upgrade/plans/17-safety.md](../lyra-upgrade/plans/17-safety.md)
- **Related concepts:** [Agent Loop](01-agent-loop.md), [Tools & Hooks](02-tools-and-hooks.md), [Permission Bridge](09-permission-bridge.md), [Two-Tier Routing](10-two-tier-routing.md)
- **Red-teaming command:** `lyra safety redteam --suite default`
- **Research papers:** *Llama Guard: LLM-based Input-Output Safety Filter* (Inan et al., 2024); *Constitutional AI: Harmlessness from AI Feedback* (Bai et al., 2022)
