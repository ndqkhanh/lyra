# S5: Supervisor Daemon + Session Lifecycle

> Plan: §4.13 (13-swarm-fleet.md) | Depends on: S1, S2

## Scope
Persistent background daemon managing agent sessions: state tracking, lifecycle, auto-stop idle, restart recovery.

## Key Design
1. **SessionState enum**: WORKING, IDLE, NEEDS_INPUT, COMPLETED, FAILED, STOPPED
2. **ProcessState enum**: ALIVE, EXITED, LOOP_SLEEPING
3. **State persistence**: SQLite-backed, survives restart
4. **Auto-stop**: idle timeout (configurable, default 1hr)
5. **Fleet view**: list all sessions with status
