"""Phase M.8 - version + help-text smoke."""
from __future__ import annotations

from typer.testing import CliRunner

from lyra_cli import __version__
from lyra_cli.__main__ import app


def test_version_is_3_5_0():
    assert __version__ == "3.5.0"


def test_root_help_mentions_burn():
    res = CliRunner().invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "burn" in res.output.lower()


def test_burn_help_lists_subcommands():
    res = CliRunner().invoke(app, ["burn", "--help"])
    assert res.exit_code == 0
    out = res.output.lower()
    for sub in ("compare", "optimize", "yield"):
        assert sub in out
