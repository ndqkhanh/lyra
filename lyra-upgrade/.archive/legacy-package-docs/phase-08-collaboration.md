# Phase 8 — Sessions, Teams & Integrations

Modules: `session.py`, `team.py`, `integration.py`

## Session Management (`session.py`)

Session export / import and replay.

```python
from lyra_ui import SessionManager, SessionEventType, SessionReplay

manager = SessionManager()

session = manager.create_session(
    session_id="research-session",
    author="user@example.com",
    title="AI Research Session",
    description="Researching AI agent frameworks",
    tags=["ai", "research"],
)

manager.add_event(
    event_id="e1",
    event_type=SessionEventType.MESSAGE,
    data={"role": "user", "content": "What are the best AI frameworks?"},
)
manager.add_event(
    event_id="e2",
    event_type=SessionEventType.TOOL_CALL,
    data={"tool": "search", "query": "AI frameworks"},
)

manager.add_annotation(
    annotation_id="a1",
    event_id="e1",
    author="reviewer",
    text="Good question",
)

manager.save_session()

exported = manager.export_session()
manager.import_session(exported)

results = manager.search_sessions(query="AI", tags=["research"])

analytics = manager.get_analytics()
print(f"Total events: {analytics['total_events']}")

# Replay
replay = SessionReplay(manager)
replay.start()
while True:
    event = replay.next_event()
    if event is None:
        break
    print(f"Event: {event.type.value}")
```

**Features**

- Session export / import to JSON
- Event types: MESSAGE, TOOL_CALL, TOOL_RESULT, ERROR, ANNOTATION
- Session annotations for collaboration
- Session search by query, author, tags
- Analytics (events, tokens, cost)
- Replay with next / previous / goto controls

## Team Collaboration (`team.py`)

Team management with role-based access control.

```python
from lyra_ui import TeamManager, UserRole

manager = TeamManager()

team = manager.create_team(
    team_id="engineering",
    team_name="Engineering Team",
    settings={"theme": "dark", "notifications": True},
)

manager.add_member("alice", "Alice", "alice@example.com", role=UserRole.ADMIN)
manager.add_member("bob", "Bob", "bob@example.com", role=UserRole.MEMBER)
manager.update_member_role("bob", UserRole.ADMIN)

# Quotas
manager.set_quota("alice", tokens_limit=200000, cost_limit=20.0)
manager.update_usage("alice", tokens=50000, cost=5.0)
if manager.check_quota("alice"):
    print("Within quota")

# Shared templates
manager.add_template(
    template_id="code-review",
    name="Code Review",
    description="Template for code reviews",
    template="Review the following code:\n{code}",
    variables=["code"],
    created_by="alice",
)
template = manager.get_template("code-review")

manager.save_team()

analytics = manager.get_team_analytics()
print(f"Total members: {analytics['total_members']}")
```

**Features**

- Team configuration and settings
- RBAC: `ADMIN`, `MEMBER`, `VIEWER`
- Usage quotas (token and cost limits)
- Shared prompt templates with variables
- Analytics (members, usage, cost)
- Storage in `~/.lyra/teams/`

## Integration System (`integration.py`)

External tool integrations.

```python
from lyra_ui import (
    IntegrationManager,
    IntegrationType,
    Plugin,
)

manager = IntegrationManager()

# Configure
manager.configure_integration(
    IntegrationType.GIT,
    enabled=True,
    settings={"repo_path": "/path/to/repo"},
)
manager.configure_integration(
    IntegrationType.GITHUB,
    enabled=True,
    settings={"token": "ghp_xxx"},
)

# Git
git = manager.git
git.commit("feat: add new feature", files=["src/main.py"])
git.push(branch="main")
git.create_branch("feature/new-feature")

# GitHub
github = manager.github
pr_url = github.create_pull_request(
    repo="owner/repo",
    title="Add new feature",
    body="This PR adds...",
    head="feature/new-feature",
    base="main",
)

# Slack
manager.slack.send_notification(
    title="Build Complete",
    message="Build #123 completed successfully",
    level="success",
)

# Webhook
webhook = manager.webhook
webhook.register_webhook("task.completed", "https://example.com/webhook")
webhook.trigger_webhook("task.completed", {"task_id": "123", "status": "done"})

# Plugins
plugins = manager.plugins
plugins.register_plugin(Plugin(
    id="custom-plugin",
    name="Custom Plugin",
    version="1.0.0",
    description="A custom plugin",
))

def on_task_complete(task_id):
    print(f"Task {task_id} completed")

plugins.register_hook("task.complete", on_task_complete)
plugins.trigger_hook("task.complete", "task-123")

manager.save_config()
```

**Features**

- Git integration (commit, push, branch)
- GitHub / GitLab integration (PRs, issues)
- Slack notifications
- Webhook support
- Plugin system with hooks
- Integration configuration management
- Enable / disable per integration

## Components

- `SessionManager`, `SessionReplay`
- `TeamManager` (with `UserRole`, `UsageQuota`, `PromptTemplate`)
- `IntegrationManager` (with `GitIntegration`, `GitHubIntegration`, `SlackIntegration`, `WebhookIntegration`)
- `PluginSystem`, `Plugin`
