# Terminal Layer (rmux): Async PTY Multiplexer with Daemon-Based Architecture
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/51-rmux.md) | [Code](../../src/lyra/rmux/)

## Abstract
Lyra's terminal layer integrates with rmux (async-Rust PTY multiplexer) for detachable terminal sessions. The design separates concerns: rmux owns PTY hosting and detach-reattach, the supervisor daemon owns session lifecycle, and worktree isolation owns per-session file safety. This clean separation avoids the three subsystems reimplementing each other.

## Method
`src/lyra/rmux/integration.py`: daemon-based client-server model, cross-platform (macOS/Linux/Windows via ConPTY). SDK-first design with `lyra-sdk` for programmatic control.

## Conclusion
Implemented: rmux integration with supervisor + worktree. Future: post-quantum E2EE for remote session sharing.
