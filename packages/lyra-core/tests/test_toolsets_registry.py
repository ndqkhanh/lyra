"""Contract tests for the toolsets registry (hermes-agent parity).

Locked surface:

* Built-in bundles ``default``, ``safe``, ``research``, ``coding``,
  ``ops`` are present.
* ``safe`` excludes destructive tools (``Bash``, ``ExecuteCode``,
  ``Write``, ``Edit``, ``Patch``, ``apply_patch``, ``Browser``,
  ``send_message``).
* ``research`` is ``safe`` ∪ {``pdf_extract``, ``image_describe``,
  ``image_ocr``}.
* ``register_toolset`` accepts iterables, deduplicates, rejects
  empty.
* ``apply_toolset`` returns ``ToolsetApplication`` with
  ``applied`` ⊆ ``available`` and ``skipped`` for missing tools.
* Built-ins cannot be removed.
"""
from __future__ import annotations

import pytest

from lyra_core.tools import (
    ToolsetRegistry,
    apply_toolset,
    default_toolsets,
    get_registry,
    get_toolset,
    list_toolsets,
    register_toolset,
)


def test_builtin_bundles_present():
    names = list_toolsets()
    for expected in ("default", "safe", "research", "coding", "ops"):
        assert expected in names


def test_safe_excludes_destructive_tools():
    safe = set(get_toolset("safe"))
    for forbidden in (
        "Bash",
        "ExecuteCode",
        "Write",
        "Edit",
        "Patch",
        "apply_patch",
        "Browser",
        "send_message",
    ):
        assert forbidden not in safe, f"safe must not contain {forbidden}"


def test_research_extends_safe():
    safe = set(get_toolset("safe"))
    research = set(get_toolset("research"))
    assert safe.issubset(research)
    assert {"pdf_extract", "image_describe", "image_ocr"}.issubset(research)


def test_default_toolsets_returns_copy():
    snapshot = default_toolsets()
    snapshot["__bogus__"] = ("X",)
    assert "__bogus__" not in default_toolsets()


def test_register_toolset_dedupes():
    reg = ToolsetRegistry()
    reg.register("custom", ["A", "B", "A", "C", "B"])
    assert reg.get("custom") == ("A", "B", "C")


def test_register_toolset_rejects_empty():
    reg = ToolsetRegistry()
    with pytest.raises(ValueError):
        reg.register("nope", [])


def test_register_toolset_rejects_blank_name():
    reg = ToolsetRegistry()
    with pytest.raises(ValueError):
        reg.register("   ", ["A"])


def test_remove_built_in_rejected():
    reg = ToolsetRegistry()
    with pytest.raises(ValueError):
        reg.remove("default")


def test_remove_custom_works():
    reg = ToolsetRegistry()
    reg.register("custom", ["A"])
    reg.remove("custom")
    assert "custom" not in reg.names()


def test_apply_toolset_filters_available():
    reg = ToolsetRegistry()
    reg.register("triple", ["A", "B", "C"])
    out = reg.apply("triple", available=["A", "C", "Z"])
    assert out.name == "triple"
    assert out.applied == ("A", "C")
    assert out.skipped == ("B",)
    assert out.enabled_now == ("A", "C")


def test_apply_toolset_unknown_raises():
    reg = ToolsetRegistry()
    with pytest.raises(KeyError):
        reg.apply("ghost", available=["A"])


def test_module_level_apply_toolset_safe():
    reg = get_registry()
    available = list(reg.get("default"))
    out = apply_toolset("safe", available=available)
    assert "Read" in out.applied
    assert "Bash" not in out.applied
    assert out.as_dict()["name"] == "safe"


def test_register_toolset_module_level():
    reg = get_registry()
    register_toolset("__test_bundle__", ["Read", "Glob"])
    try:
        assert get_toolset("__test_bundle__") == ("Read", "Glob")
    finally:
        reg.remove("__test_bundle__")
