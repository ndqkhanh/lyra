"""
Integration System - External tool integrations.

Features:
- Git integration (commit, push, PR)
- GitHub/GitLab integration
- Slack notifications
- Webhook support
- API for external tools
- Plugin system
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class IntegrationType(Enum):
    """Integration type."""

    GIT = "git"
    GITHUB = "github"
    GITLAB = "gitlab"
    SLACK = "slack"
    WEBHOOK = "webhook"
    API = "api"
    PLUGIN = "plugin"


@dataclass
class IntegrationConfig:
    """Integration configuration."""

    type: IntegrationType
    enabled: bool
    settings: Dict[str, Any] = field(default_factory=dict)


class GitIntegration:
    """
    Git integration.

    Features:
    - Commit changes
    - Push to remote
    - Create branches
    - Create pull requests
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize Git integration.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = repo_path or Path.cwd()

    def commit(self, message: str, files: Optional[List[str]] = None) -> bool:
        """
        Commit changes.

        Args:
            message: Commit message
            files: Files to commit (None = all)

        Returns:
            True if successful
        """
        try:
            if files:
                for file in files:
                    subprocess.run(
                        ["git", "add", file],
                        cwd=self.repo_path,
                        check=True,
                        capture_output=True,
                    )
            else:
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True,
                )

            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def push(self, branch: Optional[str] = None, remote: str = "origin") -> bool:
        """
        Push to remote.

        Args:
            branch: Branch name (None = current)
            remote: Remote name

        Returns:
            True if successful
        """
        try:
            cmd = ["git", "push", remote]
            if branch:
                cmd.append(branch)

            subprocess.run(
                cmd,
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def create_branch(self, branch_name: str) -> bool:
        """
        Create new branch.

        Args:
            branch_name: Branch name

        Returns:
            True if successful
        """
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_current_branch(self) -> Optional[str]:
        """
        Get current branch name.

        Returns:
            Branch name or None
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None


class GitHubIntegration:
    """
    GitHub integration.

    Features:
    - Create pull requests
    - Create issues
    - Add comments
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub integration.

        Args:
            token: GitHub API token
        """
        self.token = token

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> Optional[str]:
        """
        Create pull request.

        Args:
            repo: Repository (owner/name)
            title: PR title
            body: PR body
            head: Head branch
            base: Base branch

        Returns:
            PR URL or None
        """
        try:
            cmd = [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body",
                body,
                "--head",
                head,
                "--base",
                base,
            ]

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Create issue.

        Args:
            repo: Repository (owner/name)
            title: Issue title
            body: Issue body
            labels: Issue labels

        Returns:
            Issue URL or None
        """
        try:
            cmd = [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body",
                body,
            ]

            if labels:
                cmd.extend(["--label", ",".join(labels)])

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None


class SlackIntegration:
    """
    Slack integration.

    Features:
    - Send messages
    - Send notifications
    - Post to channels
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack integration.

        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url

    def send_message(self, text: str, channel: Optional[str] = None) -> bool:
        """
        Send message to Slack.

        Args:
            text: Message text
            channel: Channel name

        Returns:
            True if successful
        """
        if not self.webhook_url:
            return False

        payload = {"text": text}
        if channel:
            payload["channel"] = channel

        try:
            import requests

            response = requests.post(self.webhook_url, json=payload)
            return response.status_code == 200
        except Exception:
            return False

    def send_notification(
        self,
        title: str,
        message: str,
        level: str = "info",
    ) -> bool:
        """
        Send notification to Slack.

        Args:
            title: Notification title
            message: Notification message
            level: Notification level (info/success/warning/error)

        Returns:
            True if successful
        """
        colors = {
            "info": "#36a64f",
            "success": "#2eb886",
            "warning": "#daa038",
            "error": "#a30200",
        }

        attachment = {
            "color": colors.get(level, colors["info"]),
            "title": title,
            "text": message,
            "ts": int(datetime.now().timestamp()),
        }

        if not self.webhook_url:
            return False

        try:
            import requests

            response = requests.post(
                self.webhook_url,
                json={"attachments": [attachment]},
            )
            return response.status_code == 200
        except Exception:
            return False


class WebhookIntegration:
    """
    Webhook integration.

    Features:
    - Register webhooks
    - Trigger webhooks
    - Handle webhook events
    """

    def __init__(self):
        """Initialize webhook integration."""
        self.webhooks: Dict[str, str] = {}

    def register_webhook(self, event: str, url: str):
        """
        Register webhook for event.

        Args:
            event: Event name
            url: Webhook URL
        """
        self.webhooks[event] = url

    def trigger_webhook(self, event: str, data: Dict[str, Any]) -> bool:
        """
        Trigger webhook.

        Args:
            event: Event name
            data: Event data

        Returns:
            True if successful
        """
        if event not in self.webhooks:
            return False

        url = self.webhooks[event]

        try:
            import requests

            response = requests.post(url, json=data)
            return response.status_code == 200
        except Exception:
            return False

    def list_webhooks(self) -> Dict[str, str]:
        """
        List registered webhooks.

        Returns:
            Dictionary of event -> URL
        """
        return self.webhooks.copy()


@dataclass
class Plugin:
    """Plugin definition."""

    id: str
    name: str
    version: str
    description: str
    enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)


class PluginSystem:
    """
    Plugin system.

    Features:
    - Load plugins
    - Enable/disable plugins
    - Plugin hooks
    - Plugin settings
    """

    def __init__(self, plugin_dir: Optional[Path] = None):
        """
        Initialize plugin system.

        Args:
            plugin_dir: Plugin directory
        """
        self.plugin_dir = plugin_dir or Path.home() / ".lyra" / "plugins"
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[Callable]] = {}

    def register_plugin(self, plugin: Plugin):
        """
        Register plugin.

        Args:
            plugin: Plugin to register
        """
        self.plugins[plugin.id] = plugin

    def enable_plugin(self, plugin_id: str):
        """
        Enable plugin.

        Args:
            plugin_id: Plugin ID
        """
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = True

    def disable_plugin(self, plugin_id: str):
        """
        Disable plugin.

        Args:
            plugin_id: Plugin ID
        """
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = False

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get plugin by ID.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin or None
        """
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[Plugin]:
        """
        List all plugins.

        Returns:
            List of plugins
        """
        return list(self.plugins.values())

    def register_hook(self, event: str, callback: Callable):
        """
        Register hook callback.

        Args:
            event: Event name
            callback: Callback function
        """
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)

    def trigger_hook(self, event: str, *args, **kwargs):
        """
        Trigger hook callbacks.

        Args:
            event: Event name
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        if event in self.hooks:
            for callback in self.hooks[event]:
                callback(*args, **kwargs)


class IntegrationManager:
    """
    Integration manager.

    Features:
    - Manage integrations
    - Configure integrations
    - Integration status
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize integration manager.

        Args:
            config_path: Path to config file
        """
        self.config_path = config_path or Path.home() / ".lyra" / "integrations.json"
        self.integrations: Dict[str, IntegrationConfig] = {}
        self.git = GitIntegration()
        self.github = GitHubIntegration()
        self.slack = SlackIntegration()
        self.webhook = WebhookIntegration()
        self.plugins = PluginSystem()

    def configure_integration(
        self,
        integration_type: IntegrationType,
        enabled: bool,
        settings: Optional[Dict[str, Any]] = None,
    ):
        """
        Configure integration.

        Args:
            integration_type: Integration type
            enabled: Enable/disable
            settings: Integration settings
        """
        config = IntegrationConfig(
            type=integration_type,
            enabled=enabled,
            settings=settings or {},
        )
        self.integrations[integration_type.value] = config

    def get_integration(
        self,
        integration_type: IntegrationType,
    ) -> Optional[IntegrationConfig]:
        """
        Get integration config.

        Args:
            integration_type: Integration type

        Returns:
            Integration config or None
        """
        return self.integrations.get(integration_type.value)

    def is_enabled(self, integration_type: IntegrationType) -> bool:
        """
        Check if integration is enabled.

        Args:
            integration_type: Integration type

        Returns:
            True if enabled
        """
        config = self.get_integration(integration_type)
        return config.enabled if config else False

    def save_config(self):
        """Save integration config to file."""
        config_data = {
            key: {
                "type": config.type.value,
                "enabled": config.enabled,
                "settings": config.settings,
            }
            for key, config in self.integrations.items()
        }

        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=2)

    def load_config(self):
        """Load integration config from file."""
        if not self.config_path.exists():
            return

        with open(self.config_path, "r") as f:
            config_data = json.load(f)

        for key, data in config_data.items():
            config = IntegrationConfig(
                type=IntegrationType(data["type"]),
                enabled=data["enabled"],
                settings=data["settings"],
            )
            self.integrations[key] = config
