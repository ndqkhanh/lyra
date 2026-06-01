# LYRA ULTRA PLAN 11: Autonomous Systems — Complete Blueprint

**Version:** 1.0.0 | **Status:** In Progress | **Created:** 2026-05-25
**Parent Plan:** [LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md](LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md)

---

## Overview

Transform Lyra from an interactive agent into a fully autonomous AI system capable of self-directed work across days, weeks, or indefinitely. Goals, schedules, hooks, continuous mode, and self-monitoring combine into a "set and forget" architecture inspired by Continuous-Claude, Claude Code Goals, and autonomous agent research.

---

## Part 1: Goal System

### 1.1 Goal Architecture

```
Goal
├── id: "goal_abc123"
├── title: "Migrate user service to async Python"
├── description: "Refactor all sync endpoints to async/await, add connection pooling"
├── criteria: [Acceptance criteria as checkable items]
├── status: active | paused | completed | failed | blocked
├── priority: P0 | P1 | P2 | P3
├── created_at: 2026-05-25T10:00:00Z
├── deadline: 2026-05-28T18:00:00Z (optional)
├── parent_goal: "goal_xyz789" (optional, for goal trees)
├── sub_goals: ["goal_def456", "goal_ghi012"]
├── agent_type: code | research | design | sre | auto
├── auto_approve: true | false
├── max_budget_usd: 5.00
├── max_turns: 100
├── check_interval_minutes: 30
├── metrics:
│   ├── turns_completed: 42
│   ├── tokens_used: 85000
│   ├── cost_usd: 1.23
│   ├── files_changed: 12
│   ├── tests_passing: 47
│   └── completion_pct: 65
└── history: [GoalEvent, ...]
```

### 1.2 CLI Commands

```bash
# Goal management
lyra goal "Migrate user service to async Python"   # Create goal
lyra goal list                                      # List active goals
lyra goal list --all                                # All goals (including completed)
lyra goal show <id>                                 # Show goal details + progress
lyra goal pause <id>                                # Pause active goal
lyra goal resume <id>                               # Resume paused goal
lyra goal cancel <id>                               # Cancel goal
lyra goal retry <id>                                # Retry failed goal

# Goal monitoring
lyra goal status                                     # All goals status overview
lyra goal log <id>                                   # Goal execution log
lyra goal metrics <id>                               # Goal performance metrics

# Background mode
lyra goal start <id> --background                    # Start goal in background
lyra goal stop <id>                                  # Stop background goal
```

### 1.3 Goal Templates

```json
{
  "templates": {
    "migrate": {
      "agent_type": "code",
      "auto_approve": false,
      "check_interval_minutes": 30,
      "criteria": [
        "All tests pass",
        "No breaking API changes",
        "Performance within 10% of baseline",
        "Documentation updated"
      ]
    },
    "research": {
      "agent_type": "research",
      "auto_approve": true,
      "check_interval_minutes": 120,
      "criteria": [
        "At least 10 papers reviewed",
        "Synthesis report with citations",
        "Gap analysis completed",
        "Recommendations documented"
      ]
    },
    "investigate": {
      "agent_type": "code",
      "auto_approve": false,
      "check_interval_minutes": 15,
      "criteria": [
        "Root cause identified",
        "Reproduction steps documented",
        "Fix proposed with risk assessment",
        "Regression test added"
      ]
    }
  }
}
```

---

## Part 2: Continuous Autonomous Mode

### 2.1 Architecture

Inspired by [Continuous-Claude](https://github.com/AnandChowdhary/continuous-claude):

```
┌─────────────────────────────────────────┐
│         Continuous Loop                  │
│                                          │
│  ┌──────────┐    ┌──────────────┐       │
│  │ WAKE UP  │ →  │ CHECK GOALS  │       │
│  └──────────┘    └──────────────┘       │
│       ↑                  ↓               │
│       │           ┌──────────────┐       │
│       │           │ PRIORITIZE   │       │
│       │           └──────────────┘       │
│       │                  ↓               │
│       │           ┌──────────────┐       │
│       │           │ EXECUTE TASK │       │
│       │           └──────────────┘       │
│       │                  ↓               │
│       │           ┌──────────────┐       │
│       │           │ VERIFY        │       │
│       │           └──────────────┘       │
│       │                  ↓               │
│       │           ┌──────────────┐       │
│       └───────────│ LOG & LEARN  │       │
│                   └──────────────┘       │
│                                          │
│  Auto-wake triggers:                     │
│  - Goal check_interval reached           │
│  - External event (webhook, file change) │
│  - Scheduled time (cron)                 │
│  - Manual trigger                        │
└─────────────────────────────────────────┘
```

### 2.2 Continuous Mode CLI

```bash
# Start continuous mode
lyra continuous                  # Start autonomous loop
lyra continuous --interval 300   # Check every 5 minutes
lyra continuous --until "2026-05-28T18:00:00"  # Run until deadline
lyra continuous --goal <id>      # Work on specific goal
lyra continuous --background     # Run as daemon

# Monitor
lyra continuous status           # Show current state
lyra continuous log              # Show recent activity
lyra continuous stop             # Stop continuous mode
lyra continuous pause            # Pause (resume later)
```

### 2.3 Self-Monitoring & Safety

```python
class ContinuousGuard:
    """Safety rails for autonomous operation."""
    
    MAX_CONSECUTIVE_FAILURES = 5
    MAX_COST_PER_HOUR_USD = 2.00
    MAX_FILES_PER_HOUR = 50
    DESTRUCTIVE_OPERATIONS_BLOCKED = ["rm -rf", "DROP TABLE", "DELETE FROM", "git push --force"]
    
    def check_safety(self, action: AgentAction) -> bool:
        # Block destructive operations
        if any(op in str(action) for op in self.DESTRUCTIVE_OPERATIONS_BLOCKED):
            self.escalate("Destructive operation blocked", action)
            return False
        
        # Check rate limits
        if self.cost_last_hour() > self.MAX_COST_PER_HOUR_USD:
            self.pause("Hourly cost limit exceeded")
            return False
        
        # Check consecutive failures
        if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            self.pause("Too many consecutive failures — needs human review")
            return False
        
        return True
```

---

## Part 3: Scheduling System

### 3.1 Cron-Based Task Scheduling

```json
// ~/.lyra/schedule.json
{
  "tasks": [
    {
      "id": "daily_dependency_check",
      "cron": "0 9 * * 1-5",
      "task": "Check for outdated dependencies and create upgrade PRs",
      "agent_type": "code",
      "auto_approve": true,
      "max_budget_usd": 1.00,
      "notify": ["slack#eng-team"]
    },
    {
      "id": "weekly_code_review",
      "cron": "0 10 * * 1",
      "task": "Review all PRs from last week. Summarize patterns and flag risks.",
      "agent_type": "code",
      "auto_approve": false,
      "max_budget_usd": 3.00,
      "notify": ["email:tech-lead@company.com"]
    },
    {
      "id": "daily_trending_papers",
      "cron": "0 8 * * *",
      "task": "Scan arXiv and AI twitter for trending papers. Summarize top 3.",
      "agent_type": "research",
      "auto_approve": true,
      "max_budget_usd": 0.50,
      "notify": ["slack#ai-research"]
    },
    {
      "id": "security_scan",
      "cron": "0 2 * * 0",
      "task": "Run full security scan. Report vulnerabilities with severity.",
      "agent_type": "code",
      "auto_approve": true,
      "max_budget_usd": 2.00,
      "notify": ["slack#security"]
    }
  ]
}
```

### 3.2 Event-Driven Triggers

```json
{
  "webhooks": [
    {
      "id": "github_pr_opened",
      "event": "github.pull_request.opened",
      "repo": "org/repo",
      "task": "Review this PR for security issues and code quality",
      "agent_type": "code",
      "auto_approve": false
    },
    {
      "id": "sentry_new_error",
      "event": "sentry.error.new",
      "project": "production-api",
      "task": "Investigate this error. Check logs, find root cause, propose fix.",
      "agent_type": "code",
      "auto_approve": false
    },
    {
      "id": "file_watch_config",
      "event": "file.change",
      "pattern": "config/**/*.yaml",
      "task": "Validate config change. Check syntax and consistency.",
      "agent_type": "code",
      "auto_approve": true
    }
  ]
}
```

---

## Part 4: Hooks System v2

### 4.1 Hook Events (27+)

| Category | Events |
|----------|--------|
| **Session** | `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreCompact`, `PostCompact` |
| **Tools** | `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PreToolPermission` |
| **Agent** | `SubagentStart`, `SubagentStop`, `AgentHandoff`, `AgentSpawn` |
| **Notifications** | `Notification`, `IdlePrompt`, `PermissionRequest` |
| **Lifecycle** | `Stop`, `PreCompaction`, `GoalCreated`, `GoalCompleted`, `GoalFailed` |
| **System** | `Checkpoint`, `ModelSwitch`, `Error`, `RateLimit` |

### 4.2 Hook Handler Types

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "type": "command",
        "command": "lyra-voice session.start &",
        "description": "Play session start sound"
      },
      {
        "matcher": "",
        "type": "agent",
        "agent": "session-initializer",
        "description": "Load context from last session"
      }
    ],
    "PreToolUse": [
      {
        "matcher": "shell_run",
        "type": "prompt",
        "prompt": "Review this shell command for safety. If it's destructive, warn the user.",
        "description": "Safety check before shell execution"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "file_write|file_edit",
        "type": "command",
        "command": "prettier --write ${LYRA_FILE_PATH}",
        "description": "Auto-format edited files"
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "type": "command",
        "command": "lyra-voice task.complete &",
        "description": "Play completion sound"
      }
    ]
  }
}
```

### 4.3 Hook Scope Hierarchy (7 Levels)

| Level | Path | Scope |
|-------|------|-------|
| 1 | `~/.lyra/settings.json` | All projects, local machine |
| 2 | `.lyra/settings.json` | Single project, can be committed |
| 3 | `.lyra/settings.local.json` | Single project, gitignored |
| 4 | Organization policy | Managed org-wide settings |
| 5 | Plugin `hooks/hooks.json` | When plugin is enabled |
| 6 | Skill YAML frontmatter | While skill is active |
| 7 | CLI `--hook` override | Per-session override |

---

## Part 5: Implementation Roadmap

### Phase 11.1: Goals System (Weeks 1-3)
- [ ] Goal data model + CRUD operations
- [ ] Goal templates (migrate, research, investigate)
- [ ] Goal CLI commands
- [ ] Goal progress tracking + metrics
- [ ] Sub-goal decomposition

### Phase 11.2: Continuous Mode (Weeks 4-6)
- [ ] Continuous loop engine
- [ ] Self-monitoring guardrails
- [ ] Background daemon mode
- [ ] Pause/resume/stop controls
- [ ] Cost/budget enforcement

### Phase 11.3: Scheduling (Weeks 7-9)
- [ ] Cron-based scheduler
- [ ] Event-driven triggers (webhook, file watch)
- [ ] Notification integrations (Slack, email, Discord)
- [ ] Schedule management CLI

### Phase 11.4: Hooks v2 (Weeks 10-12)
- [ ] All 27+ hook events
- [ ] 5 handler types (command, http, mcp_tool, prompt, agent)
- [ ] 7-level scope hierarchy
- [ ] Hook debugging + testing tools

---

## Part 6: Reference & Inspiration

| Source | Key Ideas |
|--------|-----------|
| [Continuous-Claude](https://github.com/AnandChowdhary/continuous-claude) | Continuous autonomous loop pattern, sleep/wake cycle |
| [Claude Code Goals](https://code.claude.com/docs/en/goal) | Goal data model, progress tracking, criteria |
| [Claude Code Hooks](https://code.claude.com/docs/en/hooks) | 27+ events, 5 handler types, scope hierarchy |
| [Claude Code Checkpointing](https://code.claude.com/docs/en/checkpointing) | Session checkpoints, fork/merge |
| [Hermes-agent](https://github.com/nousresearch/hermes-agent) | Learning loop, progressive disclosure |
| [AutoResearchClaw](https://arxiv.org/abs/2605.20025) | Self-healing executors, debate-based verification |
