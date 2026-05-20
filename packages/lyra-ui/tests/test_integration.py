"""Tests for integration system."""

from pathlib import Path

from lyra_ui import (
    GitHubIntegration,
    GitIntegration,
    IntegrationManager,
    IntegrationType,
    Plugin,
    PluginSystem,
    SlackIntegration,
    WebhookIntegration,
)


# GitIntegration Tests


def test_git_integration_init():
    """Test git integration initialization."""
    git = GitIntegration()
    assert git.repo_path == Path.cwd()


def test_git_integration_custom_path(tmp_path):
    """Test git integration with custom path."""
    git = GitIntegration(repo_path=tmp_path)
    assert git.repo_path == tmp_path


# GitHubIntegration Tests


def test_github_integration_init():
    """Test GitHub integration initialization."""
    github = GitHubIntegration()
    assert github.token is None


def test_github_integration_with_token():
    """Test GitHub integration with token."""
    github = GitHubIntegration(token="test-token")
    assert github.token == "test-token"


# SlackIntegration Tests


def test_slack_integration_init():
    """Test Slack integration initialization."""
    slack = SlackIntegration()
    assert slack.webhook_url is None


def test_slack_integration_with_webhook():
    """Test Slack integration with webhook."""
    slack = SlackIntegration(webhook_url="https://hooks.slack.com/test")
    assert slack.webhook_url == "https://hooks.slack.com/test"


def test_slack_send_message_no_webhook():
    """Test sending message without webhook."""
    slack = SlackIntegration()
    result = slack.send_message("Test message")
    assert result is False


def test_slack_send_notification_no_webhook():
    """Test sending notification without webhook."""
    slack = SlackIntegration()
    result = slack.send_notification("Title", "Message")
    assert result is False


# WebhookIntegration Tests


def test_webhook_integration_init():
    """Test webhook integration initialization."""
    webhook = WebhookIntegration()
    assert len(webhook.webhooks) == 0


def test_register_webhook():
    """Test registering webhook."""
    webhook = WebhookIntegration()
    webhook.register_webhook("task.completed", "https://example.com/webhook")
    assert "task.completed" in webhook.webhooks
    assert webhook.webhooks["task.completed"] == "https://example.com/webhook"


def test_list_webhooks():
    """Test listing webhooks."""
    webhook = WebhookIntegration()
    webhook.register_webhook("event1", "https://example.com/1")
    webhook.register_webhook("event2", "https://example.com/2")

    webhooks = webhook.list_webhooks()
    assert len(webhooks) == 2
    assert "event1" in webhooks
    assert "event2" in webhooks


def test_trigger_webhook_not_registered():
    """Test triggering unregistered webhook."""
    webhook = WebhookIntegration()
    result = webhook.trigger_webhook("nonexistent", {"data": "test"})
    assert result is False


# PluginSystem Tests


def test_plugin_system_init(tmp_path):
    """Test plugin system initialization."""
    system = PluginSystem(plugin_dir=tmp_path)
    assert system.plugin_dir == tmp_path
    assert len(system.plugins) == 0
    assert len(system.hooks) == 0


def test_register_plugin(tmp_path):
    """Test registering plugin."""
    system = PluginSystem(plugin_dir=tmp_path)
    plugin = Plugin(
        id="test-plugin",
        name="Test Plugin",
        version="1.0.0",
        description="A test plugin",
    )
    system.register_plugin(plugin)
    assert "test-plugin" in system.plugins


def test_enable_plugin(tmp_path):
    """Test enabling plugin."""
    system = PluginSystem(plugin_dir=tmp_path)
    plugin = Plugin("test", "Test", "1.0.0", "Test", enabled=False)
    system.register_plugin(plugin)

    system.enable_plugin("test")
    assert system.plugins["test"].enabled is True


def test_disable_plugin(tmp_path):
    """Test disabling plugin."""
    system = PluginSystem(plugin_dir=tmp_path)
    plugin = Plugin("test", "Test", "1.0.0", "Test", enabled=True)
    system.register_plugin(plugin)

    system.disable_plugin("test")
    assert system.plugins["test"].enabled is False


def test_get_plugin(tmp_path):
    """Test getting plugin."""
    system = PluginSystem(plugin_dir=tmp_path)
    plugin = Plugin("test", "Test", "1.0.0", "Test")
    system.register_plugin(plugin)

    retrieved = system.get_plugin("test")
    assert retrieved is not None
    assert retrieved.id == "test"

    retrieved = system.get_plugin("nonexistent")
    assert retrieved is None


def test_list_plugins(tmp_path):
    """Test listing plugins."""
    system = PluginSystem(plugin_dir=tmp_path)
    plugin1 = Plugin("p1", "Plugin 1", "1.0.0", "First")
    plugin2 = Plugin("p2", "Plugin 2", "1.0.0", "Second")
    system.register_plugin(plugin1)
    system.register_plugin(plugin2)

    plugins = system.list_plugins()
    assert len(plugins) == 2


def test_register_hook(tmp_path):
    """Test registering hook."""
    system = PluginSystem(plugin_dir=tmp_path)

    def callback():
        pass

    system.register_hook("before_task", callback)
    assert "before_task" in system.hooks
    assert len(system.hooks["before_task"]) == 1


def test_trigger_hook(tmp_path):
    """Test triggering hook."""
    system = PluginSystem(plugin_dir=tmp_path)
    called = []

    def callback(value):
        called.append(value)

    system.register_hook("test_event", callback)
    system.trigger_hook("test_event", "test_value")
    assert called == ["test_value"]


def test_trigger_hook_multiple_callbacks(tmp_path):
    """Test triggering hook with multiple callbacks."""
    system = PluginSystem(plugin_dir=tmp_path)
    results = []

    def callback1(value):
        results.append(f"cb1:{value}")

    def callback2(value):
        results.append(f"cb2:{value}")

    system.register_hook("event", callback1)
    system.register_hook("event", callback2)
    system.trigger_hook("event", "test")
    assert len(results) == 2


# IntegrationManager Tests


def test_integration_manager_init(tmp_path):
    """Test integration manager initialization."""
    manager = IntegrationManager(config_path=tmp_path / "config.json")
    assert manager.config_path == tmp_path / "config.json"
    assert len(manager.integrations) == 0


def test_configure_integration(tmp_path):
    """Test configuring integration."""
    manager = IntegrationManager(config_path=tmp_path / "config.json")
    manager.configure_integration(
        IntegrationType.GIT,
        enabled=True,
        settings={"repo_path": "/path/to/repo"},
    )
    assert "git" in manager.integrations
    config = manager.integrations["git"]
    assert config.enabled is True
    assert config.settings["repo_path"] == "/path/to/repo"


def test_get_integration(tmp_path):
    """Test getting integration."""
    manager = IntegrationManager(config_path=tmp_path / "config.json")
    manager.configure_integration(IntegrationType.GITHUB, True)

    config = manager.get_integration(IntegrationType.GITHUB)
    assert config is not None
    assert config.type == IntegrationType.GITHUB

    config = manager.get_integration(IntegrationType.SLACK)
    assert config is None


def test_is_enabled(tmp_path):
    """Test checking if integration is enabled."""
    manager = IntegrationManager(config_path=tmp_path / "config.json")
    manager.configure_integration(IntegrationType.GIT, True)
    manager.configure_integration(IntegrationType.GITHUB, False)

    assert manager.is_enabled(IntegrationType.GIT) is True
    assert manager.is_enabled(IntegrationType.GITHUB) is False
    assert manager.is_enabled(IntegrationType.SLACK) is False


def test_save_and_load_config(tmp_path):
    """Test saving and loading config."""
    config_path = tmp_path / "config.json"
    manager = IntegrationManager(config_path=config_path)
    manager.configure_integration(
        IntegrationType.GIT,
        True,
        {"repo_path": "/test"},
    )
    manager.save_config()
    assert config_path.exists()

    manager2 = IntegrationManager(config_path=config_path)
    manager2.load_config()
    assert "git" in manager2.integrations
    config = manager2.integrations["git"]
    assert config.enabled is True
    assert config.settings["repo_path"] == "/test"


# Integration Tests


def test_complete_integration_workflow(tmp_path):
    """Test complete integration workflow."""
    manager = IntegrationManager(config_path=tmp_path / "config.json")

    # Configure integrations
    manager.configure_integration(IntegrationType.GIT, True, {"repo": "/repo"})
    manager.configure_integration(IntegrationType.GITHUB, True, {"token": "xxx"})
    manager.configure_integration(IntegrationType.SLACK, True, {"webhook": "url"})

    # Save config
    manager.save_config()

    # Load in new manager
    manager2 = IntegrationManager(config_path=tmp_path / "config.json")
    manager2.load_config()

    # Verify
    assert manager2.is_enabled(IntegrationType.GIT)
    assert manager2.is_enabled(IntegrationType.GITHUB)
    assert manager2.is_enabled(IntegrationType.SLACK)


def test_plugin_lifecycle(tmp_path):
    """Test plugin lifecycle."""
    system = PluginSystem(plugin_dir=tmp_path)

    # Register plugin
    plugin = Plugin("test", "Test Plugin", "1.0.0", "Description")
    system.register_plugin(plugin)
    assert system.get_plugin("test") is not None

    # Disable plugin
    system.disable_plugin("test")
    assert system.get_plugin("test").enabled is False

    # Enable plugin
    system.enable_plugin("test")
    assert system.get_plugin("test").enabled is True


def test_webhook_workflow():
    """Test webhook workflow."""
    webhook = WebhookIntegration()

    # Register webhooks
    webhook.register_webhook("task.start", "https://example.com/start")
    webhook.register_webhook("task.complete", "https://example.com/complete")

    # List webhooks
    webhooks = webhook.list_webhooks()
    assert len(webhooks) == 2
    assert "task.start" in webhooks
    assert "task.complete" in webhooks


def test_plugin_hooks_workflow(tmp_path):
    """Test plugin hooks workflow."""
    system = PluginSystem(plugin_dir=tmp_path)
    events = []

    # Register hooks
    def on_start(task_id):
        events.append(f"start:{task_id}")

    def on_complete(task_id):
        events.append(f"complete:{task_id}")

    system.register_hook("task.start", on_start)
    system.register_hook("task.complete", on_complete)

    # Trigger hooks
    system.trigger_hook("task.start", "task1")
    system.trigger_hook("task.complete", "task1")

    assert events == ["start:task1", "complete:task1"]
