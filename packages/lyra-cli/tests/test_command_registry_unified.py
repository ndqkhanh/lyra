"""Phase 0 — RED for the unified slash command registry.

Contract (plan Phase 5):

- ``lyra_cli.commands.registry`` exposes ``COMMAND_REGISTRY``:
  a list of ``CommandSpec`` dataclasses with fields
  ``name``, ``description``, ``category``, ``aliases``, ``handler``,
  ``args_hint``, ``interactive_only``.
- ``resolve_command(line)`` parses a user line like ``"/status foo"``
  and returns the matched spec (or alias) plus the argument string.
- ``COMMAND_REGISTRY`` is the single source of truth used by the REPL
  completer, ``/help`` renderer, and dispatcher.
- Well-known entries: ``help``, ``status``, ``mode``, ``model``, ``diff``,
  ``clear``, ``exit``.
"""
from __future__ import annotations

import pytest


def _import_registry():
    try:
        from lyra_cli.commands.registry import (
            COMMAND_REGISTRY,
            CommandSpec,
            resolve_command,
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_cli.commands.registry must exist ({exc})")
    return COMMAND_REGISTRY, CommandSpec, resolve_command


def test_registry_is_list_of_specs():
    COMMAND_REGISTRY, CommandSpec, _ = _import_registry()
    assert isinstance(COMMAND_REGISTRY, list)
    assert COMMAND_REGISTRY, "registry must not be empty"
    for entry in COMMAND_REGISTRY:
        assert isinstance(entry, CommandSpec)


def test_well_known_commands_present():
    COMMAND_REGISTRY, _, _ = _import_registry()
    names = {spec.name for spec in COMMAND_REGISTRY}
    for required in ("help", "status", "mode", "model", "diff", "clear", "exit"):
        assert required in names, f"missing built-in `/{required}` in registry"


def test_resolve_command_returns_spec_and_argstr():
    _, _, resolve_command = _import_registry()
    spec, args = resolve_command("/status")
    assert spec is not None
    assert spec.name == "status"
    assert args == ""

    spec, args = resolve_command("/mode plan")
    assert spec is not None
    assert spec.name == "mode"
    assert args == "plan"


def test_resolve_command_follows_aliases():
    COMMAND_REGISTRY, _, resolve_command = _import_registry()
    # `/q` or `/quit` should resolve to the `exit` command via aliases.
    exit_spec = next(s for s in COMMAND_REGISTRY if s.name == "exit")
    assert exit_spec.aliases, "exit must have aliases (at least 'quit' or 'q')"
    for alias in exit_spec.aliases:
        spec, _ = resolve_command(f"/{alias}")
        assert spec is not None
        assert spec.name == "exit"


def test_resolve_command_returns_none_for_unknown():
    _, _, resolve_command = _import_registry()
    spec, _ = resolve_command("/definitely-not-a-command")
    assert spec is None


def test_registry_names_are_unique():
    COMMAND_REGISTRY, _, _ = _import_registry()
    names = [spec.name for spec in COMMAND_REGISTRY]
    assert len(names) == len(set(names)), "duplicate names in COMMAND_REGISTRY"


def test_aliases_do_not_collide_with_names_or_other_aliases():
    COMMAND_REGISTRY, _, _ = _import_registry()
    names = {spec.name for spec in COMMAND_REGISTRY}
    all_aliases: list[str] = []
    for spec in COMMAND_REGISTRY:
        all_aliases.extend(spec.aliases)
    assert len(all_aliases) == len(set(all_aliases)), "duplicate alias across registry"
    assert names.isdisjoint(set(all_aliases)), "alias collides with command name"
