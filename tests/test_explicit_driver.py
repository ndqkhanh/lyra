#!/usr/bin/env python3
"""Test with explicit driver selection."""
import os
import sys
from pathlib import Path

# Force a specific driver
os.environ['TEXTUAL_DRIVER'] = 'linux'  # or 'windows' on Windows

print("Testing with explicit linux driver...", file=sys.stderr, flush=True)

from harness_tui import ProjectConfig
from lyra_cli.tui_v2 import lyra_theme
from lyra_cli.tui_v2.app import LyraHarnessApp
from lyra_cli.tui_v2.commands import register_lyra_commands
from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs
from lyra_cli.tui_v2.transport import LyraTransport

transport = LyraTransport(repo_root=Path.cwd(), model='claude-sonnet-4.6', max_steps=20)
cfg = ProjectConfig(
    name='lyra',
    description='Test',
    theme=lyra_theme(),
    transport=transport,
    model='claude-sonnet-4.6',
    working_dir=str(Path.cwd()),
    sidebar_tabs=build_lyra_sidebar_tabs(Path.cwd()),
    extra_commands=[register_lyra_commands],
)

app = LyraHarnessApp(cfg)

print("Launching with linux driver...", file=sys.stderr, flush=True)
print("Press Ctrl+Q to quit", file=sys.stderr, flush=True)

app.run()
print("Exited", file=sys.stderr, flush=True)
