"""
Sound CLI Commands

Command-line interface for sound system management.
"""

import click

from ..sounds.sound_manager import SoundManager
from ..sounds.theme_manager import ThemeManager


@click.group()
def sounds():
    """Sound system management"""
    pass


@sounds.command()
def enable():
    """Enable sounds"""
    manager = SoundManager()
    manager.config.enabled = True
    manager.config.save()
    click.echo("✓ Sounds enabled")


@sounds.command()
def disable():
    """Disable sounds"""
    manager = SoundManager()
    manager.config.enabled = False
    manager.config.save()
    click.echo("✓ Sounds disabled")


@sounds.command()
def mute():
    """Mute sounds temporarily"""
    manager = SoundManager()
    manager.mute()
    click.echo("✓ Sounds muted (temporary)")


@sounds.command()
def unmute():
    """Unmute sounds"""
    manager = SoundManager()
    manager.unmute()
    click.echo("✓ Sounds unmuted")


@sounds.command()
@click.argument('theme_name')
def theme(theme_name):
    """Set sound theme"""
    manager = SoundManager()
    theme_mgr = ThemeManager()

    if theme_name not in theme_mgr.list_themes():
        click.echo(f"❌ Unknown theme: {theme_name}")
        click.echo(f"Available themes: {', '.join(theme_mgr.list_themes())}")
        return

    manager.set_theme(theme_name)
    click.echo(f"✓ Theme set to: {theme_name}")


@sounds.command()
def themes():
    """List available themes"""
    theme_mgr = ThemeManager()
    click.echo("\nAvailable sound themes:\n")
    for name in theme_mgr.list_themes():
        theme = theme_mgr.get_theme(name)
        click.echo(f"  {name}: {theme.description}")


@sounds.command()
@click.argument('volume', type=float)
def volume(volume):
    """Set volume (0.0 to 1.0)"""
    if not 0.0 <= volume <= 1.0:
        click.echo("❌ Volume must be between 0.0 and 1.0")
        return

    manager = SoundManager()
    manager.set_volume(volume)
    click.echo(f"✓ Volume set to: {volume:.1f}")


@sounds.command()
@click.argument('event')
def test(event):
    """Test play a sound event"""
    manager = SoundManager()
    manager.play_event(event)
    click.echo(f"✓ Playing: {event}")


@sounds.command()
def status():
    """Show sound system status"""
    manager = SoundManager()

    click.echo(f"Sounds: {'enabled' if manager.config.enabled else 'disabled'}")
    click.echo(f"Theme: {manager.config.theme}")
    click.echo(f"Volume: {manager.config.volume:.1f}")
    click.echo(f"Muted: {'yes' if manager.muted else 'no'}")
