"""Slash-alias contract — hermes-agent muscle-memory compatibility.

Users coming from hermes-agent type ``/compress`` / ``/usage`` /
``/insights`` / ``/skin`` by reflex. Lyra keeps the canonical Claude-Code
/ opencode name on each command, but wires the hermes form as an
**alias** that resolves to the same handler so the muscle memory
translates.

This RED test locks the mapping so any future registry refactor that
drops an alias (or worse — re-binds it to the wrong canonical name,
as ``/context → usage`` used to do) fails at CI time before it ships.

The audit that produced this file found one real bug: ``/usage`` was
previously aliased to ``/context`` (the context-window grid), not to
``/cost`` (token spend). The test enforces the correct mapping.
"""
from __future__ import annotations

import pytest

from lyra_cli.interactive.session import (
    COMMAND_REGISTRY,
    SLASH_COMMANDS,
    command_spec,
)

# (hermes_name, lyra_canonical_name, human_explanation)
#
# ``hermes_name`` is what hermes-agent users type; ``lyra_canonical_name``
# is the handler the alias must resolve to. The third column is the
# single-line "why" so CI failures explain themselves.
#
# v3.10 note: ``usage`` was promoted from an alias of ``/cost`` to a
# canonical command of its own (the consolidated cost+stats panel,
# matching Claude Code's v2.1.x merge). Hermes muscle-memory still
# works because typing ``/usage`` lands on the new handler — which
# *includes* the cost numbers — so it's removed from this alias map
# but still tested below by ``test_usage_is_canonical_consolidator``.
HERMES_ALIASES: list[tuple[str, str, str]] = [
    ("compress", "compact", "hermes `/compress` = compact context window"),
    ("insights", "stats", "hermes `/insights` = session analytics"),
    ("skin", "theme", "hermes `/skin` = switch colour theme"),
]


@pytest.mark.parametrize(
    "hermes_name,lyra_name,why",
    HERMES_ALIASES,
    ids=[f"{h}->{l}" for h, l, _ in HERMES_ALIASES],
)
def test_hermes_alias_resolves_to_canonical_lyra_command(
    hermes_name: str, lyra_name: str, why: str
) -> None:
    spec = command_spec(hermes_name)
    assert spec is not None, (
        f"/{hermes_name} must resolve to a CommandSpec ({why})"
    )
    assert spec.name == lyra_name, (
        f"/{hermes_name} must resolve to /{lyra_name} — "
        f"currently resolves to /{spec.name}. {why}"
    )


@pytest.mark.parametrize(
    "hermes_name,lyra_name,_why",
    HERMES_ALIASES,
    ids=[h for h, _, _ in HERMES_ALIASES],
)
def test_hermes_alias_is_in_slash_commands_lookup(
    hermes_name: str, lyra_name: str, _why: str
) -> None:
    assert hermes_name in SLASH_COMMANDS, (
        f"/{hermes_name} must be dispatchable via SLASH_COMMANDS "
        f"(alias of /{lyra_name})"
    )


def test_usage_is_canonical_consolidator() -> None:
    """v3.10 contract: ``/usage`` resolves to its own consolidator command.

    History:
      * pre-v1.7.2 — ``/usage`` was an alias of ``/context`` (wrong).
      * v1.7.2     — fixed to alias ``/cost`` (token spend).
      * v3.10      — promoted to a *canonical* command that combines
        cost numbers and session-shape metrics in one panel, matching
        Claude Code's v2.1.x merge of ``/cost`` + ``/stats``.

    Hermes muscle memory still works: typing ``/usage`` lands on the
    consolidator, which *includes* the cost output. The regression
    we're guarding against is anyone re-aliasing ``/usage`` back to
    ``/context`` (the original bug) — that would lose the cost
    numbers entirely.
    """
    spec = command_spec("usage")
    assert spec is not None, "/usage must resolve"
    assert spec.name == "usage", (
        f"/usage must be its own canonical command (got /{spec.name}) — "
        "v3.10 promoted it from a /cost alias to the consolidated "
        "cost+stats panel."
    )
    assert spec.name != "context", (
        "/usage must NOT alias /context — that was the pre-v1.7.2 bug."
    )


def test_every_hermes_alias_is_declared_on_the_canonical_spec() -> None:
    """Cross-check: each alias must appear in the canonical spec's ``aliases`` tuple.

    Catches the case where an alias lands in SLASH_COMMANDS through a
    side-door but never gets recorded on the CommandSpec — which breaks
    /help alias display, the completer's meta column, and anything else
    that reads from the registry.
    """
    for hermes_name, lyra_name, why in HERMES_ALIASES:
        spec = next((s for s in COMMAND_REGISTRY if s.name == lyra_name), None)
        assert spec is not None, f"no canonical /{lyra_name} in registry"
        assert hermes_name in spec.aliases, (
            f"/{lyra_name} must declare '{hermes_name}' in its "
            f"CommandSpec.aliases tuple. {why}"
        )
