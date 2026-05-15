"""One-shot command execution for Lyra CLI.

Provides non-interactive execution mode for scripting and automation.
"""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

from .formatter import CLIFormatter, get_formatter
from .messages import StreamEvent


async def execute_oneshot(
    prompt: str,
    repo_root: Path,
    model: str,
    budget_cap_usd: float | None = None,
    output_format: str = "text",
) -> int:
    """Execute a single prompt and exit.

    Args:
        prompt: User prompt to execute
        repo_root: Repository root directory
        model: LLM model to use
        budget_cap_usd: Optional budget cap in USD
        output_format: Output format (text, json, markdown)

    Returns:
        Exit code (0 for success)
    """
    formatter = get_formatter()

    try:
        # Execute agent turn with streaming
        async for event in run_oneshot_turn(
            prompt=prompt,
            repo_root=repo_root,
            model=model,
            budget_cap=budget_cap_usd,
        ):
            await handle_stream_event(event, formatter, output_format)

        return 0

    except Exception as exc:
        formatter.print_error(str(exc))
        return 1


async def run_oneshot_turn(
    prompt: str,
    repo_root: Path,
    model: str,
    budget_cap: float | None = None,
) -> AsyncIterator[StreamEvent]:
    """Execute one-shot agent turn.

    Args:
        prompt: User prompt
        repo_root: Repository root directory
        model: LLM model to use
        budget_cap: Optional budget cap in USD

    Yields:
        Stream events
    """
    # TODO: Implement actual agent loop integration
    _ = repo_root, model, budget_cap  # Suppress unused warnings

    yield StreamEvent(
        event_type="text_delta",
        data={"text": f"One-shot execution: {prompt}\n\n"},
    )
    yield StreamEvent(
        event_type="text_delta",
        data={"text": "Agent loop integration coming soon."},
    )


async def handle_stream_event(
    event: StreamEvent, formatter: CLIFormatter, output_format: str
) -> None:
    """Handle streaming event for one-shot execution.

    Args:
        event: Stream event
        formatter: Output formatter
        output_format: Output format (text, json, markdown)
    """
    if output_format == "json":
        # JSON output mode - print raw event
        import json

        formatter.print(json.dumps(event.data))
    else:
        # Text/markdown output mode
        if event.event_type == "text_delta":
            formatter.print(event.data["text"], end="", flush=True)
        elif event.event_type == "tool_call":
            formatter.print_tool_start(event.data["name"])
        elif event.event_type == "tool_end":
            success = event.data.get("success", True)
            formatter.print_tool_end(success)
