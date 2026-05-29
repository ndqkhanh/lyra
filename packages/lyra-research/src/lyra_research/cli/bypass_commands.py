"""
Bypass CLI Commands

Command-line interface for bypass permissions management.
"""

import click

from ..permissions.audit_logger import AuditLogger
from ..permissions.bypass_manager import BypassManager


@click.group()
def bypass():
    """Bypass permissions management"""
    pass


@bypass.command()
def enable():
    """Enable bypass mode"""
    manager = BypassManager()
    manager.enable_bypass()
    click.echo("✓ Bypass mode ENABLED")
    click.echo("  All standard operations will proceed without confirmation")
    click.echo("  Use 'lyra bypass disable' to turn off")


@bypass.command()
def disable():
    """Disable bypass mode"""
    manager = BypassManager()
    manager.disable_bypass()
    click.echo("✓ Bypass mode disabled")


@bypass.command()
def toggle():
    """Toggle bypass mode on/off"""
    manager = BypassManager()
    enabled = manager.toggle_bypass()
    if enabled:
        click.echo("✓ Bypass mode ENABLED")
    else:
        click.echo("✓ Bypass mode disabled")


@bypass.command()
def status():
    """Show bypass mode status"""
    manager = BypassManager()
    enabled = manager.is_bypass_enabled()

    click.echo(f"Bypass mode: {'ENABLED' if enabled else 'disabled'}")

    if enabled and manager.enabled_at:
        click.echo(f"Enabled at: {manager.enabled_at.isoformat()}")

    if manager.config.auto_disable_after_minutes:
        click.echo(f"Auto-disable: {manager.config.auto_disable_after_minutes} minutes")


@bypass.command()
@click.option('--limit', default=20, help='Number of entries to show')
def audit(limit):
    """Show recent bypassed operations"""
    logger = AuditLogger()
    entries = logger.get_recent_bypasses(limit)

    if not entries:
        click.echo("No bypassed operations logged")
        return

    click.echo(f"\nRecent bypassed operations ({len(entries)}):\n")
    for entry in entries:
        click.echo(f"  [{entry.timestamp}] {entry.operation}")
        click.echo(f"    Level: {entry.level}")
        click.echo(f"    {entry.description}\n")
