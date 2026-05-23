"""Welcome banner for Lyra - Claude Code style with responsive layouts"""

import os
import shutil
from typing import Optional


def print_welcome_banner(
    version: str = "0.1.0",
    model: str = "Opus 4.7",
    effort: str = "high",
    provider: str = "Anthropic API",
    working_dir: Optional[str] = None,
    context_window: Optional[str] = "1M context",
    user_name: Optional[str] = None
):
    """Print welcome banner with responsive layout

    Args:
        version: Lyra version
        model: Model name
        effort: Effort level
        provider: Provider name
        working_dir: Working directory
        context_window: Context window size
        user_name: User name for greeting
    """
    if working_dir is None:
        working_dir = os.getcwd()

    # Get terminal width
    width = shutil.get_terminal_size().columns

    # Choose layout based on width
    if width >= 120:
        _print_wide_banner(version, model, effort, provider, working_dir, context_window, user_name)
    elif width >= 80:
        _print_standard_banner(version, model, effort, provider, working_dir, context_window, user_name)
    else:
        _print_narrow_banner(version, model, working_dir)


def _print_wide_banner(
    version: str,
    model: str,
    effort: str,
    provider: str,
    working_dir: str,
    context_window: Optional[str],
    user_name: Optional[str]
):
    """Print two-column wide banner (>120 cols)"""
    width = min(shutil.get_terminal_size().columns, 120)
    path = _shorten_path(working_dir, 50)

    # Top border
    title = f"Lyra v{version}"
    border_content = f"─── {title} "
    remaining = width - len(border_content) - 1
    top_border = f"╭{border_content}{'─' * remaining}╮"

    # Left column content
    greeting = f"Welcome back {user_name}!" if user_name else "Welcome to Lyra!"
    art_line_1 = "  ╦  ╦ ╦ ╦═╗ ╔═╗"
    art_line_2 = "  ║  ╚╦╝ ╠╦╝ ╠═╣"
    art_line_3 = "  ╩═╝ ╩  ╩╚═ ╩ ╩"

    context = f" ({context_window})" if context_window else ""
    info_line = f"{model}{context} · {effort} effort · {provider}"

    # Right column content
    tips_title = "Tips for getting started"
    tips_1 = "Run /help for commands"
    tips_2 = "Use /model to switch models"
    tips_divider = "─" * 25
    news_title = "What's new"
    news_1 = "Beautiful responsive UI"
    news_2 = "Claude Code-style patterns"
    news_3 = "/release-notes for more"

    # Print banner
    print(top_border)
    print(f"│ {greeting:<50} │ {tips_title:<25} │")
    print(f"│ {'':<50} │ {tips_1:<25} │")
    print(f"│ {art_line_1:<50} │ {tips_2:<25} │")
    print(f"│ {art_line_2:<50} │ {tips_divider:<25} │")
    print(f"│ {art_line_3:<50} │ {news_title:<25} │")
    print(f"│ {'':<50} │ {news_1:<25} │")
    print(f"│ {info_line:<50} │ {news_2:<25} │")
    print(f"│ {path:<50} │ {news_3:<25} │")
    print(f"╰{'─' * (width - 2)}╯")
    print()


def _print_standard_banner(
    version: str,
    model: str,
    effort: str,
    provider: str,
    working_dir: str,
    context_window: Optional[str],
    user_name: Optional[str]
):
    """Print standard single-column banner (80-120 cols)"""
    width = min(shutil.get_terminal_size().columns, 90)
    path = _shorten_path(working_dir, width - 10)

    # Top border
    title = f"Lyra v{version}"
    border_content = f"─── {title} "
    remaining = width - len(border_content) - 1
    top_border = f"╭{border_content}{'─' * remaining}╮"

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
    print(f"│ {art_line_1:<{width-4}} │")
    print(f"│ {art_line_2:<{width-4}} │")
    print(f"│ {art_line_3:<{width-4}} │")
    print(f"│ {'':<{width-4}} │")
    print(f"│ {info_1:<{width-4}} │")
    print(f"│ {info_2:<{width-4}} │")
    print(f"│ {info_3:<{width-4}} │")
    print(f"╰{'─' * (width - 2)}╯")
    print()


def _print_narrow_banner(version: str, model: str, working_dir: str):
    """Print compact narrow banner (<80 cols)"""
    width = shutil.get_terminal_size().columns
    path = _shorten_path(working_dir, width - 10)

    print(f"╭─── Lyra v{version} ───╮")
    print(f"│ {model:<{width-4}} │")
    print(f"│ {path:<{width-4}} │")
    print(f"╰{'─' * (width - 2)}╯")
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
    # Demo all layouts
    print("Wide layout (>120 cols):")
    _print_wide_banner(
        "0.1.0", "Opus 4.7", "xhigh", "Anthropic API",
        "~/Downloads/MyCV/research/harness-engineering",
        "1M context", "Khanh"
    )

    print("\nStandard layout (80-120 cols):")
    _print_standard_banner(
        "0.1.0", "Opus 4.7", "xhigh", "Anthropic API",
        "~/Downloads/MyCV/research/harness-engineering",
        "1M context", "Khanh"
    )

    print("\nNarrow layout (<80 cols):")
    _print_narrow_banner(
        "0.1.0", "Opus 4.7",
        "~/Downloads/MyCV/research/harness-engineering"
    )

