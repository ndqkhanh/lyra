# Terminal Layer (rmux): Async PTY Multiplexer with Daemon-Based Architecture
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/51-rmux.md) | [Code](../../src/lyra/rmux/)

## Abstract
Lyra's terminal layer integrates with rmux (async-Rust PTY multiplexer) for detachable terminal sessions. The design separates concerns: rmux owns PTY hosting and detach-reattach, the supervisor daemon owns session lifecycle, and worktree isolation owns per-session file safety. This clean separation avoids the three subsystems reimplementing each other.

## Method
`src/lyra/rmux/integration.py`: daemon-based client-server model, cross-platform (macOS/Linux/Windows via ConPTY). SDK-first design with `lyra-sdk` for programmatic control.

## Conclusion
Implemented: rmux integration with supervisor + worktree. Future: post-quantum E2EE for remote session sharing.

## Working Flow

rmux lets Lyra sessions survive terminal disconnection. Here's how detach-and-reattach works.

The `rmux` integration in `src/lyra/rmux/integration.py` wraps the async-Rust PTY multiplexer. When you start a session with `lyra --detach`, the supervisor daemon (`src/lyra/supervisor/daemon.py`) spawns the agent process inside an rmux session. The PTY captures all stdin/stdout. When you close your terminal, the PTY stays alive — the agent keeps running. When you reconnect with `lyra attach <session-id>`, rmux replays the buffered output and reconnects your keyboard to the agent's stdin. The worktree isolation (`src/lyra/worktree/manager.py`) ensures each detached session has its own git checkout, so parallel sessions never collide on file edits.

**Example:** You start a long-running research task and close your laptop:
1. `lyra research --detach "Analyze 100 papers on multi-agent memory"` starts
2. The supervisor spawns an rmux session with ID `research-2026-001`
3. You close your terminal. The PTY stays alive. The agent keeps reading papers
4. 3 hours later, you `ssh` back in and run `lyra attach research-2026-001`
5. rmux replays the agent's progress — 78/100 papers analyzed, 12 findings written to `knowledge_base/`
6. The agent continues from where it was. Zero progress lost.
