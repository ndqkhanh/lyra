"""`lyra init` — scaffold ``SOUL.md`` and ``.lyra/`` in a repo.

If the repo still carries a legacy ``.open-harness/`` (v1.7) or
``.opencoding/`` (v1.6) state directory, the migration orchestrator
copies the newer one into ``.lyra/`` on first init and leaves the
legacy directory untouched for safety. A notification line is printed
so the user knows what happened.

lyra-legacy-aware: this module references the legacy directory names
by design — they are the migration sources surfaced to the user.
"""
from __future__ import annotations

from importlib import resources
from pathlib import Path

import typer
from lyra_core.migrations import migrate_legacy_state
from rich.console import Console

from ..paths import RepoLayout

_console = Console()


def init_command(
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        "-C",
        help="Repo to initialise (defaults to cwd).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing SOUL.md / policy.yaml.",
    ),
) -> None:
    """Initialise Lyra scaffolding in a repo: SOUL.md + .lyra/."""
    repo_root = repo_root.resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    layout = RepoLayout(repo_root=repo_root)

    # Auto-migrate legacy state before scaffolding; idempotent after
    # first run thanks to the marker file written into .lyra/.
    performed, source = migrate_legacy_state(layout)
    if performed and source is not None:
        _console.print(
            f"[yellow]Migrated state:[/yellow] "
            f"{source.name} → {layout.state_dir.name} "
            f"(original preserved at {source})"
        )

    layout.ensure()

    _write_from_template(
        template_name="SOUL.md.tmpl",
        target=layout.soul_md,
        force=force,
    )
    _write_from_template(
        template_name="policy.yaml.tmpl",
        target=layout.policy_yaml,
        force=force,
    )

    _console.print(f"[green]Lyra initialised[/green] at {repo_root}")


def _write_from_template(*, template_name: str, target: Path, force: bool) -> None:
    """Write a packaged template to ``target`` unless it exists and ``force`` is False."""
    if target.exists() and not force:
        return
    source_text = _read_template(template_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source_text)


def _read_template(name: str) -> str:
    path = resources.files("lyra_cli").joinpath("templates").joinpath(name)
    return path.read_text(encoding="utf-8")
