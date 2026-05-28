"""Onboarding wizard for Lyra CLI (OpenClaw-inspired)"""

import os
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt


class OnboardingWizard:
    """Step-by-step setup wizard (OpenClaw pattern)"""

    def __init__(self, console: Console):
        self.console = console
        self.workspace = Path.home() / ".lyra"

    def run(self):
        """Run the onboarding wizard"""
        self.console.print("\n[bold cyan]Welcome to Lyra![/bold cyan]\n")
        self.console.print("Let's get you set up. This will take about 2 minutes.\n")

        # Step 1: Workspace
        if not self._setup_workspace():
            return False

        # Step 2: API Key
        if not self._setup_api_key():
            return False

        # Step 3: Model Selection
        if not self._setup_model():
            return False

        # Step 4: Optional Features
        self._setup_optional_features()

        # Done
        self.console.print("\n[bold green]✓ Setup complete![/bold green]\n")
        self.console.print("Run [cyan]lyra[/cyan] to start chatting.\n")
        return True

    def _setup_workspace(self) -> bool:
        """Setup workspace directory"""
        self.console.print("[bold]Step 1/4: Workspace[/bold]")

        if self.workspace.exists():
            self.console.print(f"[dim]Found existing workspace at {self.workspace}[/dim]")
            if not Confirm.ask("Use this workspace?", default=True):
                custom_path = Prompt.ask("Enter workspace path")
                self.workspace = Path(custom_path).expanduser()
        else:
            self.console.print(f"[dim]Creating workspace at {self.workspace}[/dim]")

        # Create workspace structure
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Creating directories...", total=None)

            dirs = [
                self.workspace,
                self.workspace / "sessions",
                self.workspace / "skills",
                self.workspace / "memory",
            ]

            for dir_path in dirs:
                dir_path.mkdir(parents=True, exist_ok=True)

            progress.update(task, completed=True)

        self.console.print("[green]✓[/green] Workspace ready\n")
        return True

    def _setup_api_key(self) -> bool:
        """Setup API key"""
        self.console.print("[bold]Step 2/4: API Key[/bold]")

        # Check if already set
        if os.getenv("ANTHROPIC_API_KEY"):
            self.console.print("[green]✓[/green] API key already set")
            if not Confirm.ask("Update it?", default=False):
                self.console.print()
                return True

        self.console.print("[dim]Get your API key from: https://console.anthropic.com/[/dim]")
        api_key = Prompt.ask("Enter your Anthropic API key", password=True)

        if not api_key:
            self.console.print("[red]✗[/red] API key required")
            return False

        # Save to config
        config_file = self.workspace / "config.toml"
        with open(config_file, "w") as f:
            f.write(f'[auth]\napi_key = "{api_key}"\n')

        self.console.print("[green]✓[/green] API key saved\n")
        return True

    def _setup_model(self) -> bool:
        """Setup default model"""
        self.console.print("[bold]Step 3/4: Model Selection[/bold]")

        models = {
            "1": ("Opus 4.7", "Most capable, best for complex tasks"),
            "2": ("Sonnet 4.6", "Balanced, good for daily use"),
            "3": ("Haiku 4.5", "Fast, good for simple tasks"),
        }

        self.console.print()
        for key, (name, desc) in models.items():
            self.console.print(f"  [cyan]{key}[/cyan]. {name} - [dim]{desc}[/dim]")

        choice = Prompt.ask("\nChoose default model", choices=["1", "2", "3"], default="2")

        model_map = {"1": "opus", "2": "sonnet", "3": "haiku"}
        selected = model_map[choice]

        # Save to config
        config_file = self.workspace / "config.toml"
        with open(config_file, "a") as f:
            f.write(f'\n[general]\nmodel = "{selected}"\n')

        self.console.print(f"[green]✓[/green] Default model: {models[choice][0]}\n")
        return True

    def _setup_optional_features(self):
        """Setup optional features"""
        self.console.print("[bold]Step 4/4: Optional Features[/bold]\n")

        # Skills
        if Confirm.ask("Enable skills? (Reusable workflows)", default=True):
            (self.workspace / "skills").mkdir(exist_ok=True)
            self.console.print("[green]✓[/green] Skills enabled")

        # Memory
        if Confirm.ask("Enable memory? (Persistent context)", default=True):
            (self.workspace / "memory").mkdir(exist_ok=True)
            self.console.print("[green]✓[/green] Memory enabled")

        # Session history
        if Confirm.ask("Save session history?", default=True):
            (self.workspace / "sessions").mkdir(exist_ok=True)
            self.console.print("[green]✓[/green] Session history enabled")

        self.console.print()


def run_onboarding():
    """Run the onboarding wizard"""
    console = Console()
    wizard = OnboardingWizard(console)
    return wizard.run()
