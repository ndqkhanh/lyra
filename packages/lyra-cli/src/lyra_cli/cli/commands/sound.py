"""Sound effects management command — pack selection, toggle, preview."""

from __future__ import annotations

import typer
from rich.console import Console

from lyra_cli.generate_sounds import generate_all_sounds
from lyra_cli.sound_effects import SoundEvent, get_sound_manager

app = typer.Typer()
console = Console()


@app.command()
def list_packs() -> None:
    """List available sound packs."""
    sm = get_sound_manager()
    packs = sm.available_packs
    active = sm.active_pack_name

    if not packs:
        console.print("[dim]No sound packs available.[/dim]")
        return

    console.print(f"[bold]Available sound packs ({len(packs)}):[/bold]")
    for name in packs:
        marker = " [green](active)[/green]" if name == active else ""
        enabled = "[green]ON[/green]" if sm.enabled else "[red]OFF[/red]"
        console.print(f"  • [cyan]{name}[/cyan]{marker} — Sound: {enabled}")


@app.command()
def select(pack_name: str) -> None:
    """Select a sound pack by name."""
    sm = get_sound_manager()
    if sm.load_pack(pack_name):
        console.print(f"[green]Sound pack '{pack_name}' selected.[/green]")
    else:
        console.print(f"[red]Unknown pack: '{pack_name}'.[/red]")
        console.print(f"Available: {', '.join(sm.available_packs)}")


@app.command()
def toggle() -> None:
    """Toggle sound effects on/off."""
    sm = get_sound_manager()
    state = sm.toggle()
    status = "[green]ON[/green]" if state else "[red]OFF[/red]"
    console.print(f"Sound effects: {status}")


@app.command()
def on() -> None:
    """Enable sound effects."""
    sm = get_sound_manager()
    sm.enable()
    console.print("[green]Sound effects enabled.[/green]")


@app.command()
def off() -> None:
    """Disable sound effects."""
    sm = get_sound_manager()
    sm.disable()
    console.print("[yellow]Sound effects disabled.[/yellow]")


@app.command()
def preview(
    event_name: str = typer.Argument("session_start", help="Sound event to preview"),
) -> None:
    """Preview a sound event. Events: session_start, user_prompt, tool_start,
    tool_success, tool_failure, stop, pre_compact, error, task_complete."""
    sm = get_sound_manager()
    sm.enable()
    try:
        event = SoundEvent(event_name)
    except ValueError:
        valid = ", ".join(e.value for e in SoundEvent)
        console.print(f"[red]Invalid event: '{event_name}'.[/red] Valid: {valid}")
        raise typer.Exit(1)

    if sm.active_pack is None:
        console.print("[yellow]No sound pack selected. Use 'sound select <pack>' first.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Preview:[/bold] {sm.active_pack_name} → {event.value}")
    sm.dispatch(event)


@app.command()
def setup() -> None:
    """Generate WAV sound files for all built-in packs (required for playback)."""
    base = generate_all_sounds()
    sm = get_sound_manager()
    console.print(f"[green]Sound files generated at: {base}[/green]")
    console.print(f"[bold]Packs:[/bold] {', '.join(sm.available_packs)}")
    console.print("[bold]Next:[/bold] 'sound select retro' then 'sound on'")
