"""Doctor command for diagnostics (OpenClaw pattern)"""

import os
import sys
from pathlib import Path

from rich.console import Console


class DoctorCommand:
    """Diagnostic tool to check Lyra setup"""

    def __init__(self, console: Console):
        self.console = console
        self.issues = []
        self.warnings = []

    def run(self):
        """Run diagnostics"""
        self.console.print("\n[bold cyan]Lyra Doctor[/bold cyan]")
        self.console.print("[dim]Checking your setup...[/dim]\n")

        # Run checks
        self._check_python()
        self._check_workspace()
        self._check_api_key()
        self._check_dependencies()
        self._check_permissions()

        # Show results
        self._show_results()

    def _check_python(self):
        """Check Python version"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 11:
            self._ok("Python", f"{version.major}.{version.minor}.{version.micro}")
        else:
            self._error("Python", f"Version {version.major}.{version.minor} (need 3.11+)")

    def _check_workspace(self):
        """Check workspace setup"""
        workspace = Path.home() / ".lyra"

        if workspace.exists():
            self._ok("Workspace", str(workspace))

            # Check subdirectories
            required = ["sessions", "skills", "memory"]
            for subdir in required:
                path = workspace / subdir
                if not path.exists():
                    self._warning(f"  {subdir}/", "Missing (will be created)")
        else:
            self._error("Workspace", "Not found (run: lyra onboard)")

    def _check_api_key(self):
        """Check API key"""
        if os.getenv("ANTHROPIC_API_KEY"):
            self._ok("API Key", "Set in environment")
        else:
            config_file = Path.home() / ".lyra" / "config.toml"
            if config_file.exists():
                content = config_file.read_text()
                if "api_key" in content:
                    self._ok("API Key", "Set in config")
                else:
                    self._error("API Key", "Not configured (run: lyra onboard)")
            else:
                self._error("API Key", "Not configured (run: lyra onboard)")

    def _check_dependencies(self):
        """Check required dependencies"""
        deps = {
            "rich": "Terminal formatting",
            "typer": "CLI framework",
            "anthropic": "Claude API",
            "prompt_toolkit": "Interactive prompts",
        }

        for module, desc in deps.items():
            try:
                __import__(module)
                self._ok(f"  {module}", desc)
            except ImportError:
                self._error(f"  {module}", f"Missing (pip install {module})")

    def _check_permissions(self):
        """Check file permissions"""
        workspace = Path.home() / ".lyra"

        if workspace.exists():
            if os.access(workspace, os.W_OK):
                self._ok("Permissions", "Workspace writable")
            else:
                self._error("Permissions", "Workspace not writable")

    def _ok(self, check: str, message: str):
        """Record successful check"""
        self.console.print(f"[green]✓[/green] {check:20} {message}")

    def _warning(self, check: str, message: str):
        """Record warning"""
        self.console.print(f"[yellow]⚠[/yellow] {check:20} {message}")
        self.warnings.append((check, message))

    def _error(self, check: str, message: str):
        """Record error"""
        self.console.print(f"[red]✗[/red] {check:20} {message}")
        self.issues.append((check, message))

    def _show_results(self):
        """Show diagnostic results"""
        self.console.print()

        if not self.issues and not self.warnings:
            self.console.print("[bold green]✓ All checks passed![/bold green]")
            self.console.print("[dim]Your Lyra setup is healthy.[/dim]\n")
        else:
            if self.issues:
                self.console.print(f"[bold red]Found {len(self.issues)} issue(s)[/bold red]")
                for check, msg in self.issues:
                    self.console.print(f"  • {check}: {msg}")
                self.console.print()

            if self.warnings:
                self.console.print(
                    f"[bold yellow]Found {len(self.warnings)} warning(s)[/bold yellow]"
                )
                for check, msg in self.warnings:
                    self.console.print(f"  • {check}: {msg}")
                self.console.print()

            # Suggest fixes
            if self.issues:
                self.console.print("[bold]Suggested fixes:[/bold]")
                self.console.print("  1. Run [cyan]lyra onboard[/cyan] to complete setup")
                self.console.print("  2. Check [cyan]https://docs.lyra.ai/troubleshooting[/cyan]")
                self.console.print()


def run_doctor():
    """Run the doctor command"""
    console = Console()
    doctor = DoctorCommand(console)
    doctor.run()
