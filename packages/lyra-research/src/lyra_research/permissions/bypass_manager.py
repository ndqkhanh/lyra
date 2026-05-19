"""
Bypass Manager

Manages bypass permissions mode with configuration and audit logging.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import json
from pathlib import Path


@dataclass
class BypassConfig:
    """Configuration for bypass mode"""
    enabled: bool = False
    auto_disable_after_minutes: Optional[int] = 30  # Auto-disable after 30 min
    allowed_operations: Optional[List[str]] = None  # None = all, or specific list

    def __post_init__(self):
        if self.allowed_operations is None:
            self.allowed_operations = []


class BypassManager:
    """
    Manages bypass permissions mode

    Features:
    - Toggle bypass on/off
    - Auto-disable after timeout
    - Whitelist specific operations
    - Audit logging
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".lyra" / "bypass_config.json"
        self.config = self._load_config()
        self.enabled_at: Optional[datetime] = None

    def _load_config(self) -> BypassConfig:
        """Load bypass configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                data = json.load(f)
                return BypassConfig(**data)
        return BypassConfig()

    def _save_config(self):
        """Save bypass configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({
                'enabled': self.config.enabled,
                'auto_disable_after_minutes': self.config.auto_disable_after_minutes,
                'allowed_operations': self.config.allowed_operations
            }, f, indent=2)

    def enable_bypass(self):
        """Enable bypass mode"""
        self.config.enabled = True
        self.enabled_at = datetime.now()
        self._save_config()

    def disable_bypass(self):
        """Disable bypass mode"""
        self.config.enabled = False
        self.enabled_at = None
        self._save_config()

    def toggle_bypass(self) -> bool:
        """
        Toggle bypass mode on/off

        Returns:
            New bypass state (True = enabled)
        """
        if self.config.enabled:
            self.disable_bypass()
        else:
            self.enable_bypass()
        return self.config.enabled

    def is_bypass_enabled(self) -> bool:
        """Check if bypass mode is currently enabled"""
        if not self.config.enabled:
            return False

        # Check auto-disable timeout
        if self.config.auto_disable_after_minutes and self.enabled_at:
            elapsed = (datetime.now() - self.enabled_at).total_seconds() / 60
            if elapsed > self.config.auto_disable_after_minutes:
                self.disable_bypass()
                return False

        return True

    def is_operation_allowed(self, operation: str) -> bool:
        """Check if specific operation is allowed in bypass mode"""
        if not self.config.allowed_operations:
            return True  # Empty list = all operations allowed
        return operation in self.config.allowed_operations

    def log_bypass(self, request):
        """Log bypassed operation for audit trail"""
        # Delegate to audit logger
        from .audit_logger import AuditLogger
        logger = AuditLogger()
        logger.log_bypass(request)
