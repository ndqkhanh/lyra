"""One-shot command execution for Lyra CLI.

Provides non-interactive execution mode for scripting and automation.
Agent loop driven by the harness-core AgentLoop + lyra_cli.llm_factory.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from lyra_cli.llm_factory import build_llm

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
        model: LLM model to use (e.g. opus, sonnet, haiku, or auto)
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
    """Execute one-shot agent turn using the harness-core AgentLoop.

    Builds an LLM provider from the configured env (``build_llm``),
    runs the prompt through ``AgentLoop.run()``, and yields the
    final text as a ``StreamEvent``.

    Args:
        prompt: User prompt
        repo_root: Repository root directory
        model: LLM model to use (e.g. opus, sonnet, haiku, or auto)
        budget_cap: Optional budget cap in USD

    Yields:
        Stream events
    """
    import os

    from lyra_harness_core.loop import AgentLoop
    from lyra_harness_core.tools import ToolRegistry

    _ = repo_root  # repo_root is used indirectly via cwd for tool scoping

    # Map user-friendly model name to provider kind
    provider_kind = {"opus": "anthropic", "sonnet": "anthropic", "haiku": "anthropic"}.get(
        model.lower().strip(), "auto"
    )
    if provider_kind != "auto":
        os.environ["HARNESS_LLM_MODEL"] = model
    else:
        os.environ.pop("HARNESS_LLM_MODEL", None)

    # Build the LLM provider
    llm = build_llm(provider_kind)

    # Run via the harness AgentLoop (no tools wired by default)
    tool_registry = ToolRegistry()
    loop = AgentLoop(llm=llm, tools=tool_registry, max_steps=10)
    result = loop.run(prompt)

    yield StreamEvent(
        event_type="text_delta",
        data={"text": result.final_text},
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
