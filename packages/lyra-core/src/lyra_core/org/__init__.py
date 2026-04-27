"""Software Org Mode — multi-persona, multi-topology agent orchestration.

This module is the v1.9 Phase 1 entry point for Lyra's *Software Org Mode*:
a collection of named personas (Vertical = top-down expert chain,
Horizontal = peers, Subgroups = competing duos, NGT = blind ideation,
Standard = single agent) that the agent loop can spin up in response to
a hard task.

The full role/persona machinery (``OrgPersona``, ``Topology``,
``OrgRunner``) ships alongside the v1.9 plugin loader. This Phase-0
module establishes the **defaults** that Lyra commits to *now*, on the
basis of Chen et al., 2026 — *Diversity Collapse in Multi-Agent LLM
Systems* (`arXiv:2604.18005 <https://arxiv.org/abs/2604.18005>`_), which
identifies two persona mixes (``leader_led``, ``interdisciplinary``) and
one topology (``standard``) as **collapse-prone** and one Pareto-optimal
combination (``vertical`` x ``subgroups``) and one max-diversity escape
hatch (``horizontal`` x ``ngt``).

Concrete contracts (the analysis doc
[`docs/research/diversity-collapse-analysis.md`](../../../../docs/research/diversity-collapse-analysis.md)
codifies these):

- :data:`DEFAULT_PERSONA_MIX` is locked to one of the two Pareto-safe
  values (``"vertical"`` or ``"horizontal"``); shipping the default as
  one of the collapse-prone mixes is a CI-failing regression.
- :data:`DEFAULT_TOPOLOGY` is locked to one of the two diversity-safe
  topologies (``"subgroups"`` or ``"ngt"``); the ``"standard"``
  topology is permitted as an opt-in for benchmark replication, never
  as a default.
- :data:`COLLAPSE_PRONE_PERSONA_MIXES` and
  :data:`COLLAPSE_PRONE_TOPOLOGIES` enumerate the modes the v1.9 runner
  must refuse to use *as a default*; passing them via explicit
  ``--persona-mix`` / ``--topology`` overrides is allowed for ablation
  but emits a loud warning.

The constants are intentionally plain strings (not Enums) at this Phase
so the v1.9 config schema can validate them cheaply against the
upstream paper's nomenclature.
"""
from __future__ import annotations

from typing import Final

DEFAULT_PERSONA_MIX: Final[str] = "vertical"
"""Pareto-frontier persona mix per arXiv:2604.18005 §4 Figure 3.

A *vertical* mix is a top-down expert chain (senior → mid → junior);
the paper finds it scores Vendi ≈ 6.08 with Overall Quality ≈ 8.32 — the
strict Pareto-optimum across the four mixes the paper tested. The
alternative diversity-safe choice is ``"horizontal"`` (max diversity but
slightly lower quality). The two excluded mixes (``"leader_led"`` and
``"interdisciplinary"``) are the documented collapse modes.
"""


DEFAULT_TOPOLOGY: Final[str] = "subgroups"
"""Diversity-safe topology per arXiv:2604.18005 §5.2 Figure 10.

*Subgroups* (two competing duos arguing before reconciliation) maximises
*sustained* constructive disagreement across the dialogue — the Lyra
default for any tournament that runs longer than two rounds. The
alternative diversity-safe choice is ``"ngt"`` (Nominal Group Technique:
blind silent ideation in round 0, then debate); pick that when the
priority is *initial* diversity rather than sustained one. The
``"standard"`` topology — fully connected debate from round 0 —
is the Lyra-forbidden default because the paper shows it accelerates
premature convergence.
"""


COLLAPSE_PRONE_PERSONA_MIXES: Final[frozenset[str]] = frozenset(
    {"leader_led", "interdisciplinary"}
)
"""The two persona mixes the v1.9 runner refuses as a default.

``leader_led`` collapses because authority dynamics suppress dissent;
``interdisciplinary`` collapses because the cross-domain framing
pressures every agent to rebrand the same idea (see paper §4 Figure 3).
"""


COLLAPSE_PRONE_TOPOLOGIES: Final[frozenset[str]] = frozenset({"standard"})
"""The single topology the v1.9 runner refuses as a default.

``standard`` (fully-connected dialogue from round 0) is the topology the
paper explicitly identifies as the principal driver of the diversity-
collapse regime in §5.2.
"""


_VALID_DEFAULT_PERSONA_MIXES: Final[frozenset[str]] = frozenset(
    {"vertical", "horizontal"}
)
_VALID_DEFAULT_TOPOLOGIES: Final[frozenset[str]] = frozenset({"subgroups", "ngt"})

assert DEFAULT_PERSONA_MIX in _VALID_DEFAULT_PERSONA_MIXES, (
    "DEFAULT_PERSONA_MIX must stay on the Pareto frontier "
    "(arXiv:2604.18005 §4 Figure 3)."
)
assert DEFAULT_TOPOLOGY in _VALID_DEFAULT_TOPOLOGIES, (
    "DEFAULT_TOPOLOGY must stay diversity-safe "
    "(arXiv:2604.18005 §5.2 Figure 10)."
)
assert (
    DEFAULT_PERSONA_MIX not in COLLAPSE_PRONE_PERSONA_MIXES
    and DEFAULT_TOPOLOGY not in COLLAPSE_PRONE_TOPOLOGIES
), "Lyra defaults must never sit on a documented collapse mode."


__all__ = [
    "COLLAPSE_PRONE_PERSONA_MIXES",
    "COLLAPSE_PRONE_TOPOLOGIES",
    "DEFAULT_PERSONA_MIX",
    "DEFAULT_TOPOLOGY",
]
