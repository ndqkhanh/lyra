"""
Bypass Mode - Bypass mode implementation with audit logging.

Features:
- Bypass mode toggle
- Audit trail logging
- Visual indicators
- Safety guardrails
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from lyra_permissions.types import PermissionDecision, PermissionLevel


class BypassMode:
    """
    Bypass mode controller.

    Features:
    - Enable/disable bypass mode
    - Multiple toggle methods
    - Visual indicators
    """

    def __init__(self):
        """Initialize bypass mode."""
        self.enabled = self._load_bypass_state()

    def _load_bypass_state(self) -> bool:
        """Load bypass state from multiple sources."""
        # Check environment variable
        if os.getenv("LYRA_BYPASS_PERMISSIONS", "").lower() == "true":
            return True

        # Check config file
        config_path = Path("~/.lyra/config.json").expanduser()
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    return config.get("bypassPermissions", False)
            except (OSError, json.JSONDecodeError):
                pass

        return False

    def enable(self):
        """Enable bypass mode."""
        self.enabled = True
        self._save_state()

    def disable(self):
        """Disable bypass mode."""
        self.enabled = False
        self._save_state()

    def toggle(self) -> bool:
        """Toggle bypass mode."""
        self.enabled = not self.enabled
        self._save_state()
        return self.enabled

    def is_enabled(self) -> bool:
        """Check if bypass mode is enabled."""
        return self.enabled

    def _save_state(self):
        """Save bypass state to config."""
        config_path = Path("~/.lyra/config.json").expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        config["bypassPermissions"] = self.enabled

        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        except OSError:
            pass

    def get_status_indicator(self) -> str:
        """Get visual status indicator."""
        if self.enabled:
            return "[BYPASS MODE]"
        return ""


class AuditLogger:
    """
    Audit trail logger for bypass mode.

    Features:
    - Log all auto-accepted permissions
    - Exportable audit reports
    - Retention policy
    """

    def __init__(self, log_path: str | None = None):
        """Initialize audit logger."""
        if log_path:
            self.log_path = Path(log_path).expanduser()
        else:
            self.log_path = Path("~/.lyra/audit.log").expanduser()

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        tool: str,
        operation: str,
        decision: PermissionDecision,
        level: PermissionLevel,
        context: dict[str, Any] | None = None,
    ):
        """
        Log permission decision.

        Args:
            tool: Tool name
            operation: Operation name
            decision: Permission decision
            level: Permission level
            context: Operation context
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "operation": operation,
            "decision": decision.value,
            "level": level.value,
            "context": context or {},
        }

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # Fail silently

    def get_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get recent audit entries.

        Args:
            limit: Maximum number of entries

        Returns:
            List of audit entries
        """
        if not self.log_path.exists():
            return []

        entries = []
        try:
            with open(self.log_path) as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []

        return entries[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """
        Get audit statistics.

        Returns:
            Audit statistics
        """
        entries = self.get_recent(limit=1000)

        if not entries:
            return {
                "total_entries": 0,
                "auto_accepted": 0,
                "prompted": 0,
                "denied": 0,
            }

        auto_accepted = sum(1 for e in entries if e["decision"] == "allow")
        prompted = sum(1 for e in entries if e["decision"] == "prompt")
        denied = sum(1 for e in entries if e["decision"] == "deny")

        return {
            "total_entries": len(entries),
            "auto_accepted": auto_accepted,
            "prompted": prompted,
            "denied": denied,
            "first_entry": entries[0]["timestamp"] if entries else None,
            "last_entry": entries[-1]["timestamp"] if entries else None,
        }

    def clear(self):
        """Clear audit log."""
        if self.log_path.exists():
            try:
                self.log_path.unlink()
            except OSError:
                pass

    def export(self, output_path: str, format: str = "json") -> bool:
        """
        Export audit log.

        Args:
            output_path: Output file path
            format: Export format (json or csv)

        Returns:
            True if successful
        """
        entries = self.get_recent(limit=10000)

        if not entries:
            return False

        output = Path(output_path).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            if format == "json":
                with open(output, "w") as f:
                    json.dump(entries, f, indent=2)
            elif format == "csv":
                import csv

                with open(output, "w", newline="") as f:
                    if entries:
                        writer = csv.DictWriter(f, fieldnames=entries[0].keys())
                        writer.writeheader()
                        writer.writerows(entries)
            return True
        except (OSError, ImportError):
            return False


class SafetyGuardrails:
    """
    Safety guardrails for bypass mode.

    Features:
    - Critical operation protection
    - Rollback capability
    - Emergency stop
    """

    CRITICAL_OPERATIONS = [
        "drop",
        "truncate",
        "force_push",
        "delete_all",
        "destroy",
        "rm_rf",
    ]

    SENSITIVE_PATHS = [
        "/etc",
        "/var",
        "/sys",
        "/usr",
        "~/.ssh",
        "~/.aws",
        "~/.config",
    ]

    @staticmethod
    def requires_confirmation(
        tool: str, operation: str, context: dict[str, Any] | None = None
    ) -> bool:
        """
        Check if operation requires confirmation even in bypass mode.

        Args:
            tool: Tool name
            operation: Operation name
            context: Operation context

        Returns:
            True if confirmation required
        """
        context = context or {}

        # Check for critical operations
        if operation in SafetyGuardrails.CRITICAL_OPERATIONS:
            return True

        # Check for sensitive paths
        if "path" in context:
            path = str(context["path"])
            for sensitive in SafetyGuardrails.SENSITIVE_PATHS:
                if path.startswith(sensitive):
                    return True

        # Check for force operations
        if context.get("force", False):
            return True

        # Check for bulk operations
        if context.get("count", 0) > 10:
            return True

        return False

    @staticmethod
    def get_warning_message(
        tool: str, operation: str, context: dict[str, Any] | None = None
    ) -> str:
        """
        Get warning message for critical operation.

        Args:
            tool: Tool name
            operation: Operation name
            context: Operation context

        Returns:
            Warning message
        """
        context = context or {}

        if operation in SafetyGuardrails.CRITICAL_OPERATIONS:
            return f"⚠️  CRITICAL: {tool}.{operation} is a destructive operation!"

        if "path" in context:
            path = context["path"]
            return f"⚠️  WARNING: Operating on sensitive path: {path}"

        if context.get("force", False):
            return f"⚠️  WARNING: Force operation requested for {tool}.{operation}"

        if context.get("count", 0) > 10:
            count = context["count"]
            return f"⚠️  WARNING: Bulk operation affecting {count} items"

        return f"⚠️  WARNING: {tool}.{operation} requires confirmation"
