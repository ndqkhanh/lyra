---
title: Schedule a recurring skill
description: Run a skill on a cron schedule via the Lyra cron daemon — for digest emails, repo health checks, dependency-bump PRs, and other repeating chores.
---

# Schedule a recurring skill <span class="lyra-badge intermediate">intermediate</span>

The cron subsystem lets a skill run on a schedule (every hour,
weekday morning, monthly, …) without you starting Lyra by hand.
This is the Hermes-style automation channel: agentic chores that
should happen *to* the repo even when no human is at the keyboard.

Source: [`lyra_core/cron/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/cron).

## Two pieces

| Piece | What it does |
|---|---|
| **Schedule** | What to run, when, with what budget |
| **Daemon** | Process that wakes on time and dispatches |

Schedules are declarative YAML; the daemon is one process per host.

## Recipe: dependency-bump PR every Monday

Step 1 — write the skill (or use an existing one).

```markdown title="~/.lyra/skills/deps-monday-bump/SKILL.md"
---
name: deps-monday-bump
description: Bump non-major dependencies, run tests, open a PR if green.
allowed_tools: [view, write, bash, mcp__github__create_pr]
---

# Procedure

1. Run `pip-tools compile --upgrade requirements.in -o requirements.txt`.
2. Run pytest. If anything fails, abort and STOP.
3. Stage the requirements file. Run `git diff --stat`.
4. Open a PR titled `chore(deps): weekly bump` with the diff stat in the body.
```

Step 2 — schedule it.

```yaml title=".lyra/cron/deps-bump.yaml"
schedule: "0 9 * * MON"          # cron expression: Mondays 09:00 local
skill: deps-monday-bump
budget_usd: 1.50
quotas:
  bash: 30
  write: 10
permission_mode: acceptEdits
notify:
  on_success: slack:#dev
  on_failure: slack:#alerts
timeout: 30m
```

Step 3 — start the daemon (one per host).

```bash
lyra cron daemon &        # foreground; or systemd / launchd unit
```

The daemon polls schedules every 30 s and dispatches due jobs. Each
dispatch is a fully isolated Lyra session in a worktree, with the
schedule's budget and quotas applied.

## Cron expression reference

Standard 5-field cron with two extensions:

| Field | Range | Notes |
|---|---|---|
| Minute | 0–59 | |
| Hour | 0–23 | |
| Day of month | 1–31 | |
| Month | 1–12 or `JAN..DEC` | |
| Day of week | 0–6 or `SUN..SAT` | 0 = Sunday |

Plus:

```yaml
schedule: "@daily 09:00"          # named with time
schedule: "every 4h"              # interval
schedule: "after sess-X"          # event-driven; runs N min after a session ends
```

## What runs in a cron-spawned session

The dispatched session:

- Starts in a fresh git worktree (one cron run can't dirty the repo
  for the next).
- Has the cron schedule's `budget_usd` and `quotas` applied as hard
  limits.
- Runs in `permission_mode` (defaults to `acceptEdits` for cron).
- Cannot spawn subagents (cron runs are leaf-only by default — set
  `allow_subagents: true` in the schedule to override).
- Writes its trace to `.lyra/cron/runs/<schedule>/<ts>/trace.jsonl`.
- Posts to `notify` channels on terminal status.

## Inspecting and managing

```bash
lyra cron list                            # all schedules
lyra cron show deps-bump                  # one schedule
lyra cron runs deps-bump --last 10        # recent runs
lyra cron run deps-bump --now             # run immediately, off-schedule
lyra cron pause deps-bump
lyra cron resume deps-bump
lyra cron logs deps-bump --tail
```

Each run has its own session id; trace and metrics flow through the
normal observability pipeline.

## Notifications

```yaml
notify:
  on_success:
    - slack:#dev
    - email:team@example.com
  on_failure:
    - slack:#alerts
    - pagerduty:lyra-cron
  on_budget_exhausted:
    - slack:#alerts
```

The notifier is a [hook](write-hook.md) registered on the
`PreSessionEnd` event, so the same channel set works for any
session, not just cron-dispatched ones.

## Budget and safety for unattended runs

Defaults that work:

```yaml
budget_usd: 2.0                   # tight; cron jobs should be cheap
permission_mode: acceptEdits      # not bypass — let writes through, gate bash
quotas:                           # cap the obvious risks
  bash: 30
  subagent_spawn: 0               # leaf-only by default
timeout: 30m                      # hard wall-clock cap
allow_network: true
allow_destructive: false          # blocks rm -rf, db drop, etc.
```

The `allow_destructive: false` flag enables an extra hook that
denies tool calls matching destructive patterns (`rm -rf`,
`DROP TABLE`, `git reset --hard origin/*`, etc). This is in addition
to the permission bridge and is **on by default for cron schedules**.

## Patterns that work

**Daily digest.** A skill that scans yesterday's PRs and posts a
summary to Slack. `schedule: "0 9 * * MON-FRI"`, budget $0.20.

**Weekly dep bump.** As above. Budget $1.50, opens at most one PR.

**Repo health check.** Run linters, count TODOs, check for stale
branches. Posts to a dashboard channel. `schedule: "@daily"`.

**Eval drift watcher.** Run a small eval suite nightly against the
fast slot; alert if `pass@1` regresses against the baseline.
`schedule: "0 2 * * *"`, budget $5.

## Where to look

| File | What lives there |
|---|---|
| `lyra_core/cron/daemon.py` | The polling daemon |
| `lyra_core/cron/schedule.py` | Schedule parsing + matching |
| `lyra_core/cron/store.py` | Schedule + run history persistence |
| `lyra_cli/commands/cron.py` | The `lyra cron …` CLI |

[← How-to: run an eval](run-eval.md){ .md-button }
[Continue: write a plugin →](write-plugin.md){ .md-button .md-button--primary }
