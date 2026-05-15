"""Phase N - top-level surface smoke.

Quick, dependency-free assertions that ``lyra --help`` advertises the
new Phase N commands (``setup``, ``serve``, ``skill``) and that the
canonical Phase N modules import cleanly. We intentionally avoid
exercising any real LLM provider, sandbox container, or HTTP socket
here; each subsystem owns its own deeper test file. This is the file
to break first when somebody removes a Phase N seam.
"""

from __future__ import annotations

import importlib

import pytest
from typer.testing import CliRunner

from lyra_cli import __version__
from lyra_cli.__main__ import app


def test_phase_n_version_string() -> None:
    # Bumped in v3.13 — autonomy surfaces: /directive, /contract,
    # /autopilot, /continue wire the v3.12 substrate
    # (lyra_core.contracts, lyra_core.loops.{directive,store}) into the REPL.
    assert __version__ == "3.13.0"


@pytest.mark.parametrize(
    "command",
    ["setup", "serve", "skill", "doctor"],
)
def test_root_help_advertises_phase_n_command(command: str) -> None:
    res = CliRunner().invoke(app, ["--help"])
    assert res.exit_code == 0, res.output
    assert command in res.output.lower()


def test_doctor_supports_json_flag() -> None:
    res = CliRunner().invoke(app, ["doctor", "--help"])
    assert res.exit_code == 0, res.output
    assert "--json" in res.output


def test_setup_supports_non_interactive_flag() -> None:
    res = CliRunner().invoke(app, ["setup", "--help"])
    assert res.exit_code == 0, res.output
    assert "--non-interactive" in res.output


@pytest.mark.parametrize(
    "module_path",
    [
        "lyra_cli.client",
        "lyra_cli.tracing",
        "lyra_cli.diagnostics",
        "lyra_cli.config_io",
        "lyra_cli.provider_registry",
        "lyra_cli.sandbox",
        "lyra_cli.serve",
    ],
)
def test_phase_n_modules_import(module_path: str) -> None:
    mod = importlib.import_module(module_path)
    assert mod is not None
