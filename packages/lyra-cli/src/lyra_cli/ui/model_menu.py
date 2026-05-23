"""Simple model selection menu - raw terminal control"""

import sys
import tty
import termios
from typing import Optional
from lyra_cli.cli.models import get_registry


def show_model_menu_simple(current_model: str) -> Optional[str]:
    """
    Show simple model selection menu

    Returns:
        Selected model ID or None if cancelled
    """
    registry = get_registry()
    models = registry.get_all_models()
    selected = 0

    # Find current model index
    for i, model in enumerate(models):
        if model.id == current_model:
            selected = i
            break

    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)

        # Print menu
        _render_menu(models, selected, current_model)

        # Input loop
        while True:
            # Read key
            char = sys.stdin.read(1)

            # Handle escape sequences (arrow keys)
            if char == '\x1b':
                next1 = sys.stdin.read(1)
                if next1 == '[':
                    next2 = sys.stdin.read(1)
                    if next2 == 'A':  # Up arrow
                        selected = max(0, selected - 1)
                    elif next2 == 'B':  # Down arrow
                        selected = min(len(models) - 1, selected + 1)

                    # Re-render
                    _clear_menu(len(models) + 5)
                    _render_menu(models, selected, current_model)
                else:
                    # Esc pressed
                    _clear_menu(len(models) + 5)
                    return None

            elif char == '\r':  # Enter
                _clear_menu(len(models) + 5)
                return models[selected].id

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _render_menu(models, selected, current_model):
    """Render the menu"""
    print("\n" + "─" * 80)
    print("  \x1b[36mSelect model\x1b[0m")
    print("  \x1b[2mSwitch between models from multiple providers.\x1b[0m\n")

    for i, model in enumerate(models):
        cursor = "\x1b[33m❯\x1b[0m " if i == selected else "  "
        checkmark = " \x1b[32m✔\x1b[0m" if model.id == current_model else ""

        # Format line
        name = f"{model.name}{checkmark}"
        desc = model.description
        provider = model.provider
        pricing = f"${model.input_price}/${model.output_price} per Mtok"

        line = f"{cursor}{i+1}. {name:30} {desc} · {provider} · {pricing}"

        if i == selected:
            print(line)
        else:
            print(f"\x1b[2m{line}\x1b[0m")

    print("\n  \x1b[2mEnter to confirm · Esc to cancel\x1b[0m")
    print("─" * 80)


def _clear_menu(lines: int):
    """Clear menu lines"""
    for _ in range(lines):
        sys.stdout.write('\x1b[1A')  # Move up
        sys.stdout.write('\x1b[2K')  # Clear line
    sys.stdout.flush()
