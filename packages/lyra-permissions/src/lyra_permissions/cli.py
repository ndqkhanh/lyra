"""
CLI Integration - Command-line interface for permission management.

Features:
- Permission commands
- Profile management
- Audit log viewing
- Configuration management
"""

import argparse
import sys
from typing import List, Optional

from lyra_permissions.bypass_mode import AuditLogger, BypassMode
from lyra_permissions.granular_control import GranularController
from lyra_permissions.permission_manager import PermissionManager
from lyra_permissions.permission_store import PermissionStore


class PermissionCLI:
    """Command-line interface for permission management."""

    def __init__(self):
        """Initialize CLI."""
        self.manager = PermissionManager()
        self.bypass_mode = self.manager.bypass_mode
        self.granular = self.manager.granular_controller
        self.audit_logger = self.manager.audit_logger
        self.store = self.manager.store

    def run(self, args: Optional[List[str]] = None):
        """Run CLI with arguments."""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        if hasattr(parsed_args, "func"):
            parsed_args.func(parsed_args)
        else:
            parser.print_help()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="lyra permissions",
            description="Lyra Permission Management",
        )

        subparsers = parser.add_subparsers(title="commands", dest="command")

        # Bypass mode commands
        self._add_bypass_commands(subparsers)

        # Profile commands
        self._add_profile_commands(subparsers)

        # Audit commands
        self._add_audit_commands(subparsers)

        # Permission commands
        self._add_permission_commands(subparsers)

        # Status command
        self._add_status_command(subparsers)

        return parser

    def _add_bypass_commands(self, subparsers):
        """Add bypass mode commands."""
        # Bypass on
        bypass_on = subparsers.add_parser("bypass-on", help="Enable bypass mode")
        bypass_on.set_defaults(func=self.cmd_bypass_on)

        # Bypass off
        bypass_off = subparsers.add_parser("bypass-off", help="Disable bypass mode")
        bypass_off.set_defaults(func=self.cmd_bypass_off)

        # Bypass toggle
        bypass_toggle = subparsers.add_parser("bypass-toggle", help="Toggle bypass mode")
        bypass_toggle.set_defaults(func=self.cmd_bypass_toggle)

        # Bypass status
        bypass_status = subparsers.add_parser("bypass-status", help="Show bypass mode status")
        bypass_status.set_defaults(func=self.cmd_bypass_status)

    def _add_profile_commands(self, subparsers):
        """Add profile commands."""
        # List profiles
        profile_list = subparsers.add_parser("profile-list", help="List available profiles")
        profile_list.set_defaults(func=self.cmd_profile_list)

        # Set profile
        profile_set = subparsers.add_parser("profile-set", help="Set current profile")
        profile_set.add_argument("profile", help="Profile name")
        profile_set.set_defaults(func=self.cmd_profile_set)

        # Show profile
        profile_show = subparsers.add_parser("profile-show", help="Show current profile")
        profile_show.set_defaults(func=self.cmd_profile_show)

    def _add_audit_commands(self, subparsers):
        """Add audit commands."""
        # Audit log
        audit_log = subparsers.add_parser("audit-log", help="Show audit log")
        audit_log.add_argument("--limit", type=int, default=20, help="Number of entries")
        audit_log.set_defaults(func=self.cmd_audit_log)

        # Audit stats
        audit_stats = subparsers.add_parser("audit-stats", help="Show audit statistics")
        audit_stats.set_defaults(func=self.cmd_audit_stats)

        # Audit export
        audit_export = subparsers.add_parser("audit-export", help="Export audit log")
        audit_export.add_argument("output", help="Output file path")
        audit_export.add_argument("--format", choices=["json", "csv"], default="json")
        audit_export.set_defaults(func=self.cmd_audit_export)

        # Audit clear
        audit_clear = subparsers.add_parser("audit-clear", help="Clear audit log")
        audit_clear.add_argument("--confirm", action="store_true", help="Confirm deletion")
        audit_clear.set_defaults(func=self.cmd_audit_clear)

    def _add_permission_commands(self, subparsers):
        """Add permission commands."""
        # Allow
        allow = subparsers.add_parser("allow", help="Allow tool operation")
        allow.add_argument("tool", help="Tool name")
        allow.add_argument("operation", help="Operation name")
        allow.set_defaults(func=self.cmd_allow)

        # Deny
        deny = subparsers.add_parser("deny", help="Deny tool operation")
        deny.add_argument("tool", help="Tool name")
        deny.add_argument("operation", help="Operation name")
        deny.set_defaults(func=self.cmd_deny)

        # Remove
        remove = subparsers.add_parser("remove", help="Remove permission preference")
        remove.add_argument("tool", help="Tool name")
        remove.add_argument("operation", help="Operation name")
        remove.set_defaults(func=self.cmd_remove)

        # List
        list_perms = subparsers.add_parser("list", help="List permission preferences")
        list_perms.set_defaults(func=self.cmd_list)

    def _add_status_command(self, subparsers):
        """Add status command."""
        status = subparsers.add_parser("status", help="Show permission system status")
        status.set_defaults(func=self.cmd_status)

    # Command implementations

    def cmd_bypass_on(self, args):
        """Enable bypass mode."""
        self.bypass_mode.enable()
        print("✓ Bypass mode enabled")
        print(f"  Status: {self.bypass_mode.get_status_indicator()}")

    def cmd_bypass_off(self, args):
        """Disable bypass mode."""
        self.bypass_mode.disable()
        print("✓ Bypass mode disabled")

    def cmd_bypass_toggle(self, args):
        """Toggle bypass mode."""
        enabled = self.bypass_mode.toggle()
        status = "enabled" if enabled else "disabled"
        print(f"✓ Bypass mode {status}")
        if enabled:
            print(f"  Status: {self.bypass_mode.get_status_indicator()}")

    def cmd_bypass_status(self, args):
        """Show bypass mode status."""
        if self.bypass_mode.is_enabled():
            print("Bypass mode: ENABLED")
            print(f"Status: {self.bypass_mode.get_status_indicator()}")
        else:
            print("Bypass mode: DISABLED")

    def cmd_profile_list(self, args):
        """List available profiles."""
        profiles = self.granular.list_profiles()
        current = self.granular.current_profile

        print("Available profiles:")
        for profile in profiles:
            marker = "→" if profile == current else " "
            print(f"  {marker} {profile}")

    def cmd_profile_set(self, args):
        """Set current profile."""
        try:
            self.granular.set_profile(args.profile)
            print(f"✓ Profile set to: {args.profile}")
        except KeyError:
            print(f"✗ Profile not found: {args.profile}", file=sys.stderr)
            sys.exit(1)

    def cmd_profile_show(self, args):
        """Show current profile."""
        profile = self.granular.get_profile()
        print(f"Current profile: {profile.name}")
        print(f"\nTool permissions:")
        for key, value in profile.config.get("toolPermissions", {}).items():
            print(f"  {key}: {value}")
        print(f"\nContext rules:")
        for rule in profile.config.get("contextRules", []):
            print(f"  {rule['name']} (priority: {rule.get('priority', 0)})")

    def cmd_audit_log(self, args):
        """Show audit log."""
        entries = self.audit_logger.get_recent(limit=args.limit)

        if not entries:
            print("No audit entries found")
            return

        print(f"Recent audit entries (last {len(entries)}):\n")
        for entry in entries:
            timestamp = entry["timestamp"]
            tool = entry["tool"]
            operation = entry["operation"]
            decision = entry["decision"]
            level = entry["level"]

            print(f"{timestamp}")
            print(f"  {tool}.{operation} → {decision} ({level})")
            print()

    def cmd_audit_stats(self, args):
        """Show audit statistics."""
        stats = self.audit_logger.get_stats()

        print("Audit Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Auto-accepted: {stats['auto_accepted']}")
        print(f"  Prompted: {stats['prompted']}")
        print(f"  Denied: {stats['denied']}")

        if stats.get("first_entry"):
            print(f"\n  First entry: {stats['first_entry']}")
        if stats.get("last_entry"):
            print(f"  Last entry: {stats['last_entry']}")

    def cmd_audit_export(self, args):
        """Export audit log."""
        success = self.audit_logger.export(args.output, format=args.format)

        if success:
            print(f"✓ Audit log exported to: {args.output}")
        else:
            print(f"✗ Failed to export audit log", file=sys.stderr)
            sys.exit(1)

    def cmd_audit_clear(self, args):
        """Clear audit log."""
        if not args.confirm:
            print("⚠️  This will delete all audit entries!")
            print("   Use --confirm to proceed")
            sys.exit(1)

        self.audit_logger.clear()
        print("✓ Audit log cleared")

    def cmd_allow(self, args):
        """Allow tool operation."""
        self.store.allow(args.tool, args.operation)
        print(f"✓ Allowed: {args.tool}.{args.operation}")

    def cmd_deny(self, args):
        """Deny tool operation."""
        self.store.deny(args.tool, args.operation)
        print(f"✓ Denied: {args.tool}.{args.operation}")

    def cmd_remove(self, args):
        """Remove permission preference."""
        self.store.remove(args.tool, args.operation)
        print(f"✓ Removed: {args.tool}.{args.operation}")

    def cmd_list(self, args):
        """List permission preferences."""
        allow_list = self.store.get_allow_list()
        deny_list = self.store.get_deny_list()

        if allow_list:
            print("Allowed:")
            for item in allow_list:
                print(f"  ✓ {item}")

        if deny_list:
            print("\nDenied:")
            for item in deny_list:
                print(f"  ✗ {item}")

        if not allow_list and not deny_list:
            print("No permission preferences set")

    def cmd_status(self, args):
        """Show permission system status."""
        print("Permission System Status\n")

        # Bypass mode
        bypass_status = "ENABLED" if self.bypass_mode.is_enabled() else "DISABLED"
        print(f"Bypass mode: {bypass_status}")
        if self.bypass_mode.is_enabled():
            print(f"  {self.bypass_mode.get_status_indicator()}")

        # Current profile
        profile = self.granular.get_profile()
        print(f"\nCurrent profile: {profile.name}")

        # Policy
        policy = self.manager.get_policy()
        print(f"Policy: {policy.value}")

        # Audit stats
        stats = self.audit_logger.get_stats()
        print(f"\nAudit log:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Auto-accepted: {stats['auto_accepted']}")
        print(f"  Prompted: {stats['prompted']}")
        print(f"  Denied: {stats['denied']}")

        # Preferences
        allow_list = self.store.get_allow_list()
        deny_list = self.store.get_deny_list()
        print(f"\nPreferences:")
        print(f"  Allowed: {len(allow_list)}")
        print(f"  Denied: {len(deny_list)}")


def main():
    """Main entry point."""
    cli = PermissionCLI()
    cli.run()


if __name__ == "__main__":
    main()
