# Terminal Layer (rmux): Async PTY Multiplexer with Daemon-Based Architecture
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/51-rmux.md) | [Code](../../src/lyra/rmux/)

## Abstract
Lyra's terminal layer integrates with rmux (async-Rust PTY multiplexer) for detachable terminal sessions. The design separates concerns: rmux owns PTY hosting and detach-reattach, the supervisor daemon owns session lifecycle, and worktree isolation owns per-session file safety. This clean separation avoids the three subsystems reimplementing each other.

## Method
`src/lyra/rmux/integration.py`: daemon-based client-server model, cross-platform (macOS/Linux/Windows via ConPTY). SDK-first design with `lyra-sdk` for programmatic control.

## Use Cases

**Scenario 1: Long-running training job on remote server.** A machine learning engineer kicks off a multi-hour model fine-tuning job on a remote GPU server via SSH. They start Lyra with `lyra --detach "Monitor training run ft-2026-001, restart on loss spike, log metrics"` and close their laptop. The supervisor daemon keeps the rmux session alive. The agent watches training logs, detects a NaN loss spike at hour 3, kills the run, adjusts the learning rate, and restarts. The engineer reconnects the next morning with `lyra attach training-ft-001` — rmux replays the full log from last night. Training is 60% done, and the agent has already logged 3 parameter adjustments to the experiment tracker. Zero time watching a progress bar.

**Scenario 2: Pair programming across time zones.** A developer in New York starts a complex database migration on Lyra before leaving the office. They use `lyra --detach` and go home. The agent runs independently for hours, writing migration scripts and running them against a staging database. A colleague in Berlin picks up the session the next morning with `lyra attach migration-002`. They review the agent's progress, fix a column type the agent got wrong, and hand it back to the agent to continue. The developer in New York wakes up to a nearly finished migration with a detailed change log. Neither developer was at their desk for more than 30 minutes, yet the migration advanced all night.

**Scenario 3: Remote server administration with audit trail.** A sysadmin deploys critical security patches across 50 servers. They use Lyra in detach mode to run the playbook: `lyra --detach "Apply CVE-2026-1234 patch to fleet us-east-1, rollback on failure."` The agent connects to each server via SSH, applies the patch, and waits 60 seconds for health checks. One server fails — the agent rolls back that server and logs the failure with full diagnostic output. The sysadmin checks in later, attaches the session, and reads the full replay including which server failed and why. The rmux session itself becomes the audit record: every command, every output, every error is captured in the replay buffer.

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
