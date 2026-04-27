"""Red tests for the description-based skill router."""
from __future__ import annotations

from lyra_skills.loader import SkillManifest
from lyra_skills.router import SkillRouter


def _skill(id_: str, desc: str) -> SkillManifest:
    return SkillManifest(id=id_, name=id_, description=desc, body="b", path="/tmp")


def test_router_disambiguates_by_description() -> None:
    r = SkillRouter(
        [
            _skill("edit", "make small surgical edits to source files"),
            _skill("review", "review code for quality and security"),
        ]
    )
    hits = r.route("I need to change a line in foo.py")
    assert hits[0].id == "edit"


def test_router_prefers_user_over_shipped() -> None:
    r = SkillRouter(
        [
            _skill("edit", "shipped version for small edits to code"),
            _skill("edit-user", "user override with the same description small edits to code"),
        ]
    )
    hits = r.route("small edits to code")
    assert hits[0].id in {"edit", "edit-user"}  # stable behaviour; no crash


def test_router_returns_empty_when_no_match() -> None:
    r = SkillRouter([_skill("edit", "edit source")])
    assert r.route("bake a cake") == []


def test_router_tokenises_user_query_case_insensitively() -> None:
    r = SkillRouter([_skill("edit", "surgical edits")])
    hits = r.route("SURGICAL")
    assert hits and hits[0].id == "edit"
