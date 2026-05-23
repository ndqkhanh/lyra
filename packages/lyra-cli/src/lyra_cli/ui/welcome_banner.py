"""Welcome banner for Lyra - Claude Code style (simple print)"""

import os
import shutil


def print_welcome_banner(
    version: str = "0.1.0",
    model: str = "Opus 4.7",
    effort: str = "high",
    provider: str = "Anthropic API",
    working_dir: str = None,
    context_window: str = "1M context"
):
    """Print welcome banner - simple version without TUI"""

    if working_dir is None:
        working_dir = os.getcwd()

    # Get terminal width
    width = shutil.get_terminal_size().columns
    if width > 90:
        width = 90

    # Shorten path if needed
    path = _shorten_path(working_dir, width - 20)

    # Top border
    title = f"Lyra v{version}"
    border_content = f"─── {title} "
    remaining = width - len(border_content) - 1
    top_border = f"╭{border_content}{'─' * remaining}"

    # ASCII art lines
    art_line_1 = "  ╦  ╦ ╦ ╦═╗ ╔═╗"
    art_line_2 = "  ║  ╚╦╝ ╠╦╝ ╠═╣"
    art_line_3 = "  ╩═╝ ╩  ╩╚═ ╩ ╩"

    # Info lines
    context = f" ({context_window})" if context_window else ""
    info_1 = f"Lyra v{version}"
    info_2 = f"{model}{context} · {effort} effort · {provider}"
    info_3 = path

    # Print banner
    print(top_border)
    print(f"{art_line_1}   {info_1}")
    print(f"{art_line_2}   {info_2}")
    print(f"{art_line_3}   {info_3}")
    print()


def _shorten_path(path: str, max_length: int) -> str:
    """Shorten path to fit within max_length"""
    if len(path) <= max_length:
        return path

    # Replace home directory with ~
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]

    if len(path) <= max_length:
        return path

    # Truncate from the middle
    parts = path.split(os.sep)
    if len(parts) <= 3:
        return "..." + path[-(max_length - 3):]

    # Keep first and last parts, truncate middle
    first = parts[0] or os.sep
    last = parts[-1]
    return f"{first}{os.sep}...{os.sep}{last}"


if __name__ == "__main__":
    # Demo
    print_welcome_banner(
        version="0.1.0",
        model="Opus 4.7",
        effort="xhigh",
        provider="Anthropic API",
        working_dir="~/Downloads/MyCV/research/harness-engineering",
        context_window="1M context"
    )
