"""Phase O - reflective-learning surface smoke.

Quick, dependency-free assertions that the Memento-style Read-Write
Reflective Learning loop is wired up at the CLI surface:

* the version string was bumped to ``3.5.0``,
* ``lyra skill stats`` / ``reflect`` / ``consolidate`` are advertised
  by ``lyra skill --help``,
* the new lifecycle event ``SKILLS_ACTIVATED`` is exported by
  :mod:`lyra_core.hooks.lifecycle`,
* the ledger-backed utility resolver is reachable from the live REPL
  skill-injection helper (Phase O.6 wiring).

This file is the canary that fails first when somebody removes a
Phase O seam — deeper unit tests live next to each subsystem
(``test_skill_command.py``, ``test_skill_ledger.py``,
``test_skill_activation.py``, ``test_skills_telemetry.py``).
"""

from __future__ import annotations

import importlib

import pytest
from typer.testing import CliRunner

from lyra_cli import __version__
from lyra_cli.__main__ import app


def test_phase_o_version_string() -> None:
    assert __version__ == "3.13.0"


@pytest.mark.parametrize(
    "subcommand",
    ["stats", "reflect", "consolidate"],
)
def test_skill_help_advertises_phase_o_subcommand(subcommand: str) -> None:
    res = CliRunner().invoke(app, ["skill", "--help"])
    assert res.exit_code == 0, res.output
    assert subcommand in res.output.lower()


def test_lifecycle_event_exposes_skills_activated() -> None:
    mod = importlib.import_module("lyra_core.hooks.lifecycle")
    LifecycleEvent = getattr(mod, "LifecycleEvent")
    assert hasattr(LifecycleEvent, "SKILLS_ACTIVATED")
    assert LifecycleEvent.SKILLS_ACTIVATED.value == "skills_activated"


def test_skill_inject_exposes_utility_resolver_builder() -> None:
    mod = importlib.import_module("lyra_cli.interactive.skills_inject")
    assert hasattr(mod, "_build_utility_resolver"), (
        "Phase O.6 utility-aware activation must be wired into the live "
        "REPL skill injection path."
    )


def test_skill_ledger_module_importable() -> None:
    mod = importlib.import_module("lyra_skills.ledger")
    for name in (
        "SkillLedger",
        "SkillStats",
        "SkillOutcome",
        "load_ledger",
        "utility_score",
        "top_n",
    ):
        assert hasattr(mod, name), f"lyra_skills.ledger must export {name!r}"


def test_skill_activation_accepts_utility_resolver() -> None:
    """``select_active_skills`` is the seam Phase O.6 hooks into."""
    import inspect

    from lyra_skills.activation import select_active_skills

    sig = inspect.signature(select_active_skills)
    assert "utility_resolver" in sig.parameters
