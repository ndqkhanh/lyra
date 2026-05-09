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
HERMES_ALIASES: list[tuple[str, str, str]] = [
    ("compress", "compact", "hermes `/compress` = compact context window"),
    ("usage", "cost", "hermes `/usage` = show token usage / cost (NOT /context)"),
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


def test_usage_alias_points_at_cost_not_context() -> None:
    """Regression guard for the specific bug the audit surfaced.

    Prior to v1.7.2 the ``usage`` alias was attached to the ``/context``
    spec, which is the context-window grid (a totally different
    command). Hermes' ``/usage`` shows **token spend**, which is Lyra's
    ``/cost``. If someone accidentally re-lands the old wiring this
    test fails with a pointed message.
    """
    spec = command_spec("usage")
    assert spec is not None, "/usage must resolve"
    assert spec.name != "context", (
        "/usage must NOT alias /context — that was the pre-v1.7.2 bug. "
        "/usage is hermes for /cost (token spend), not the context grid."
    )
    assert spec.name == "cost", (
        f"/usage must alias /cost (got /{spec.name})"
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
