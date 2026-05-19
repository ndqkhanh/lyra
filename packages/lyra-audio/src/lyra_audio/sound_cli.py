"""
Sound Pack CLI - Command-line interface for sound pack management.

Features:
- Sound pack installation
- Sound pack creation
- Sound pack testing
- Sound pack listing
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from lyra_audio.sound_manager import SoundManager
from lyra_audio.sound_pack import SoundPackLoader


class SoundPackCLI:
    """Command-line interface for sound pack management."""

    def __init__(self):
        """Initialize sound pack CLI."""
        self.manager = SoundManager()
        self.loader = SoundPackLoader()

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
            prog="lyra sounds",
            description="Lyra Sound Pack Management",
        )

        subparsers = parser.add_subparsers(title="commands", dest="command")

        # On/Off commands
        self._add_toggle_commands(subparsers)

        # Theme commands
        self._add_theme_commands(subparsers)

        # Pack management
        self._add_pack_commands(subparsers)

        # Testing
        self._add_test_commands(subparsers)

        # Status
        self._add_status_command(subparsers)

        return parser

    def _add_toggle_commands(self, subparsers):
        """Add on/off commands."""
        on_cmd = subparsers.add_parser("on", help="Enable sound effects")
        on_cmd.set_defaults(func=self.cmd_on)

        off_cmd = subparsers.add_parser("off", help="Disable sound effects")
        off_cmd.set_defaults(func=self.cmd_off)

    def _add_theme_commands(self, subparsers):
        """Add theme commands."""
        theme_cmd = subparsers.add_parser("theme", help="Set current theme")
        theme_cmd.add_argument("name", help="Theme name")
        theme_cmd.set_defaults(func=self.cmd_theme)

        list_cmd = subparsers.add_parser("list", help="List available themes")
        list_cmd.set_defaults(func=self.cmd_list)

    def _add_pack_commands(self, subparsers):
        """Add pack management commands."""
        create_cmd = subparsers.add_parser("create", help="Create new sound pack")
        create_cmd.add_argument("name", help="Pack name")
        create_cmd.set_defaults(func=self.cmd_create)

        validate_cmd = subparsers.add_parser("validate", help="Validate sound pack")
        validate_cmd.add_argument("name", help="Pack name")
        validate_cmd.set_defaults(func=self.cmd_validate)

        info_cmd = subparsers.add_parser("info", help="Show pack information")
        info_cmd.add_argument("name", help="Pack name")
        info_cmd.set_defaults(func=self.cmd_info)

    def _add_test_commands(self, subparsers):
        """Add test commands."""
        test_cmd = subparsers.add_parser("test", help="Test sound playback")
        test_cmd.add_argument("event", nargs="?", default="task_complete", help="Event to test")
        test_cmd.set_defaults(func=self.cmd_test)

    def _add_status_command(self, subparsers):
        """Add status command."""
        status_cmd = subparsers.add_parser("status", help="Show sound system status")
        status_cmd.set_defaults(func=self.cmd_status)

    # Command implementations

    def cmd_on(self, args):
        """Enable sound effects."""
        self.manager.enable()
        print("✓ Sound effects enabled")

    def cmd_off(self, args):
        """Disable sound effects."""
        self.manager.disable()
        print("✓ Sound effects disabled")

    def cmd_theme(self, args):
        """Set current theme."""
        themes = self.manager.list_themes()
        if args.name not in themes:
            print(f"✗ Theme not found: {args.name}", file=sys.stderr)
            print(f"Available themes: {', '.join(themes)}")
            sys.exit(1)

        self.manager.set_theme(args.name)
        print(f"✓ Theme set to: {args.name}")

    def cmd_list(self, args):
        """List available themes."""
        themes = self.manager.list_themes()
        current = self.manager.get_theme()

        if not themes:
            print("No themes found")
            return

        print("Available themes:")
        for theme in themes:
            marker = "→" if theme == current else " "
            print(f"  {marker} {theme}")

    def cmd_create(self, args):
        """Create new sound pack."""
        pack_dir = self.loader.create_pack_template(args.name)
        print(f"✓ Created sound pack template: {pack_dir}")
        print(f"  Edit {pack_dir}/manifest.json to configure")
        print(f"  Add sound files to {pack_dir}/")

    def cmd_validate(self, args):
        """Validate sound pack."""
        is_valid, errors = self.loader.validate_pack(args.name)

        if is_valid:
            print(f"✓ Sound pack '{args.name}' is valid")
        else:
            print(f"✗ Sound pack '{args.name}' has errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)

    def cmd_info(self, args):
        """Show pack information."""
        pack = self.loader.load_pack(args.name)

        if not pack:
            print(f"✗ Pack not found: {args.name}", file=sys.stderr)
            sys.exit(1)

        print(f"Name: {pack.name}")
        print(f"Version: {pack.version}")
        print(f"Author: {pack.author}")
        print(f"Description: {pack.description}")

        if pack.metadata.game:
            print(f"Game: {pack.metadata.game}")
        if pack.metadata.character:
            print(f"Character: {pack.metadata.character}")
        if pack.metadata.tags:
            print(f"Tags: {', '.join(pack.metadata.tags)}")

        print(f"\nEvents ({len(pack.sounds)}):")
        for event in pack.list_events():
            print(f"  - {event}")

    def cmd_test(self, args):
        """Test sound playback."""
        print(f"Testing sound: {args.event}")
        self.manager.play_event(args.event)
        print("✓ Sound played (if available)")

    def cmd_status(self, args):
        """Show sound system status."""
        print("Sound System Status\n")

        # Enabled status
        status = "ENABLED" if self.manager.is_enabled() else "DISABLED"
        print(f"Status: {status}")

        # Current theme
        theme = self.manager.get_theme()
        print(f"Theme: {theme}")

        # Volume
        volume = self.manager.get_volume()
        print(f"Volume: {volume:.1%}")

        # Available themes
        themes = self.manager.list_themes()
        print(f"\nAvailable themes: {len(themes)}")
        for t in themes:
            marker = "→" if t == theme else " "
            print(f"  {marker} {t}")


def main():
    """Main entry point."""
    cli = SoundPackCLI()
    cli.run()


if __name__ == "__main__":
    main()
