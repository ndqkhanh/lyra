"""Model selection menu - Claude Code style"""

from typing import Optional, List
from dataclasses import dataclass
from lyra_cli.cli.models import ModelInfo, ModelRegistry, EFFORT_LEVELS, get_registry
from lyra_cli.ui.colors import ColorEngine
from lyra_cli.ui.symbols import SymbolRegistry


@dataclass
class MenuAction:
    """Action from menu interaction"""
    action: str  # "confirm", "cancel", "set_default"
    model_id: Optional[str] = None
    effort: Optional[str] = None


class ModelSelectionMenu:
    """Interactive model selection menu"""

    def __init__(self, current_model_id: str, current_effort: str = "high", width: int = 80):
        self.registry = get_registry()
        self.models = self.registry.get_all_models()
        self.current_model_id = current_model_id
        self.selected_index = self._find_model_index(current_model_id)
        self.effort_index = EFFORT_LEVELS.index(current_effort) if current_effort in EFFORT_LEVELS else 2
        self.width = width
        self.colors = ColorEngine()
        self.symbols = SymbolRegistry()

    def _find_model_index(self, model_id: str) -> int:
        """Find index of model in list"""
        for i, model in enumerate(self.models):
            if model.id == model_id:
                return i
        return 0

    def render(self) -> str:
        """Render the menu"""
        lines = []

        # Top divider
        lines.append(self._render_divider())

        # Title
        lines.append(f"  {self.colors.cyan('Select model')}")

        # Description
        desc = "Switch between models from multiple providers. Applies to this session only."
        lines.append(f"  {self.colors.dim(desc)}")
        lines.append("")

        # Options
        for i, model in enumerate(self.models):
            line = self._render_option(i, model)
            lines.append(line)

        lines.append("")

        # Effort selector
        lines.append(self._render_effort_selector())

        lines.append("")

        # Footer
        footer = "Enter to confirm · d to set as default · Esc to cancel"
        lines.append(f"  {self.colors.dim(footer)}")

        # Bottom divider
        lines.append(self._render_divider())

        return "\n".join(lines)

    def _render_divider(self) -> str:
        """Render full-width divider"""
        return self.colors.dim("─" * self.width)

    def _render_option(self, index: int, model: ModelInfo) -> str:
        """Render a single option line"""
        is_selected = (index == self.selected_index)
        is_current = (model.id == self.current_model_id)

        # Prefix: cursor or spaces
        cursor = self.symbols.get("❯")
        prefix = f"  {self.colors.yellow(cursor)} " if is_selected else "    "

        # Number
        number = f"{index + 1}. "

        # Name with checkmark
        checkmark = f" {self.colors.green('✔')}" if is_current else ""
        name = f"{model.name}{checkmark}"

        # Pad name to align descriptions (30 chars)
        name_width = 30
        padded_name = name.ljust(name_width)

        # Description
        desc = model.description

        # Provider
        provider = model.provider

        # Pricing
        pricing = f"${model.input_price}/${model.output_price} per Mtok"

        # Combine
        line = f"{prefix}{number}{padded_name}{desc} · {provider} · {pricing}"

        # Apply dim to non-selected items
        if not is_selected:
            line = self.colors.dim(line)

        return line

    def _render_effort_selector(self) -> str:
        """Render effort level selector"""
        symbol = self.symbols.get("◉")
        current_effort = EFFORT_LEVELS[self.effort_index]
        effort_display = current_effort.capitalize() if current_effort != "xhigh" else "xHigh"

        line = f"  {symbol} {effort_display} effort (default) ←/→ to adjust"
        return self.colors.dim(line)

    def move_up(self):
        """Move selection up"""
        if self.selected_index > 0:
            self.selected_index -= 1

    def move_down(self):
        """Move selection down"""
        if self.selected_index < len(self.models) - 1:
            self.selected_index += 1

    def decrease_effort(self):
        """Decrease effort level"""
        if self.effort_index > 0:
            self.effort_index -= 1

    def increase_effort(self):
        """Increase effort level"""
        if self.effort_index < len(EFFORT_LEVELS) - 1:
            self.effort_index += 1

    def get_selected_model(self) -> ModelInfo:
        """Get currently selected model"""
        return self.models[self.selected_index]

    def get_selected_effort(self) -> str:
        """Get currently selected effort"""
        return EFFORT_LEVELS[self.effort_index]

    def handle_key(self, key: str) -> Optional[MenuAction]:
        """
        Handle keyboard input

        Returns:
            MenuAction if action should be taken, None to continue
        """
        # Navigation
        if key in ['↑', 'k', '\x1b[A']:  # Up arrow
            self.move_up()
            return None
        elif key in ['↓', 'j', '\x1b[B']:  # Down arrow
            self.move_down()
            return None
        elif key in ['←', 'h', '\x1b[D']:  # Left arrow
            self.decrease_effort()
            return None
        elif key in ['→', 'l', '\x1b[C']:  # Right arrow
            self.increase_effort()
            return None

        # Actions
        elif key == '\r':  # Enter
            return MenuAction(
                action="confirm",
                model_id=self.get_selected_model().id,
                effort=self.get_selected_effort()
            )
        elif key == 'd':  # Set as default
            return MenuAction(
                action="set_default",
                model_id=self.get_selected_model().id,
                effort=self.get_selected_effort()
            )
        elif key in ['\x1b', 'q']:  # Esc
            return MenuAction(action="cancel")

        return None


def show_model_menu(current_model_id: str, current_effort: str = "high") -> Optional[MenuAction]:
    """
    Show interactive model selection menu

    Args:
        current_model_id: Currently active model ID
        current_effort: Current effort level

    Returns:
        MenuAction with user's selection, or None if cancelled
    """
    import sys
    import tty
    import termios

    menu = ModelSelectionMenu(current_model_id, current_effort)

    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        # Set terminal to raw mode
        tty.setraw(fd)

        # Initial render
        print("\n" + menu.render())

        # Input loop
        while True:
            # Read single character
            char = sys.stdin.read(1)

            # Handle escape sequences (arrow keys)
            if char == '\x1b':
                next1 = sys.stdin.read(1)
                if next1 == '[':
                    next2 = sys.stdin.read(1)
                    char = '\x1b[' + next2

            # Handle key
            action = menu.handle_key(char)

            if action:
                # Clear menu
                lines_to_clear = menu.render().count('\n') + 2
                for _ in range(lines_to_clear):
                    print('\x1b[1A\x1b[2K', end='')  # Move up and clear line
                return action

            # Re-render
            lines_to_clear = menu.render().count('\n') + 1
            for _ in range(lines_to_clear):
                print('\x1b[1A\x1b[2K', end='')  # Move up and clear line
            print(menu.render())

    finally:
        # Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    # Demo
    print("Model Selection Menu Demo")
    print("=" * 80)
    print()

    # Static render
    menu = ModelSelectionMenu("claude-opus-4-20250514", "xhigh")
    print(menu.render())
    print()

    # Test navigation
    print("Testing navigation:")
    menu.move_down()
    menu.move_down()
    print(f"Selected: {menu.get_selected_model().name}")
    print()

    menu.increase_effort()
    print(f"Effort: {menu.get_selected_effort()}")
