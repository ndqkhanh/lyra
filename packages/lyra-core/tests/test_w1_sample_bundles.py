"""End-to-end smoke test — load each W1 sample bundle (argus, gnomon,
vertex-eval), install it, and export to all four cross-harness targets.

This proves the cross-project plan's claim that *every* sample bundle
in the portfolio loads under the v3.11 pipeline without modification."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.bundle import (
    AgentInstaller,
    SourceBundle,
    list_exporters,
    resolve_exporter,
    verify_attestation,
)


# Each W1 project lives under projects/<name>/bundle/ relative to this test.
# The test discovers them by walking up from this file.
_REPO_ROOT = Path(__file__).resolve().parents[5]   # research/harness-engineering


# W1 + W2 + W3 + W4 sample bundles.
#  W1 = argus / gnomon / vertex-eval                          (foundation)
#  W2 = orion-code / atlas-research / open-fang / polaris     (high-leverage agents)
#  W3 = helix-bio / cipher-sec / aegis-ops                    (dual-use)
#       syndicate / harmony-voice / quanta-proof              (non-dual-use)
#  W4 = mentat-learn                                          (personal-assistant)
_W1_BUNDLES = ("argus", "gnomon", "vertex-eval")
_W2_BUNDLES = ("orion-code", "atlas-research", "open-fang", "polaris")
_W3_DUAL_USE_BUNDLES = ("helix-bio", "cipher-sec", "aegis-ops")
_W3_NON_DUAL_USE_BUNDLES = ("syndicate", "harmony-voice", "quanta-proof")
_W3_BUNDLES = _W3_DUAL_USE_BUNDLES + _W3_NON_DUAL_USE_BUNDLES
_W4_BUNDLES = ("mentat-learn",)
_ALL_BUNDLES = _W1_BUNDLES + _W2_BUNDLES + _W3_BUNDLES + _W4_BUNDLES


def _install_kwargs_for(project_name: str) -> dict:
    """Per-bundle install kwargs — dual-use bundles need authorization."""
    if project_name in _W3_DUAL_USE_BUNDLES:
        return {
            "allow_dual_use": True,
            "authorized_by": f"test:{project_name}",
        }
    return {}


@pytest.mark.parametrize("project_name", _ALL_BUNDLES)
def test_w1w2w3_bundle_loads_and_validates(project_name: str):
    bundle_dir = _REPO_ROOT / "projects" / project_name / "bundle"
    assert bundle_dir.is_dir(), f"missing bundle at {bundle_dir}"
    b = SourceBundle.load(bundle_dir)
    b.validate()
    s = b.summary()
    assert s["skills"] >= 4
    assert s["evals"] >= 10


@pytest.mark.parametrize("project_name", _ALL_BUNDLES)
def test_w1w2w3_bundle_installs(project_name: str, tmp_path):
    bundle_dir = _REPO_ROOT / "projects" / project_name / "bundle"
    b = SourceBundle.load(bundle_dir)
    inst = AgentInstaller(bundle=b)
    att = inst.install(
        target_dir=tmp_path / project_name,
        **_install_kwargs_for(project_name),
    )
    assert att.smoke_eval_pass_rate >= 0.95
    assert verify_attestation(att) is True
    # Dual-use bundles have authorized_by set in attestation.
    if project_name in _W3_DUAL_USE_BUNDLES:
        assert att.dual_use is True
        assert att.authorized_by == f"test:{project_name}"


@pytest.mark.parametrize("project_name", _ALL_BUNDLES)
def test_w1w2w3_bundle_exports_to_every_target(project_name: str, tmp_path):
    bundle_dir = _REPO_ROOT / "projects" / project_name / "bundle"
    b = SourceBundle.load(bundle_dir)
    for target in list_exporters():
        out = tmp_path / project_name / target
        manifest = resolve_exporter(target).export(b, target=out)
        assert manifest.files, f"{project_name} -> {target} produced no files"
        # Each export must have an MCP-server descriptor referenced
        # somewhere in the emitted file set, since every bundle
        # publishes an MCP server.
        out_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                             for p in manifest.files
                             if p.suffix in (".md", ".json", ".txt") and p.exists())
        assert "mcp_server.py" in out_text or "mcp" in out_text.lower(), \
            f"{project_name} -> {target}: MCP descriptor missing in export"


@pytest.mark.parametrize("project_name", _W3_DUAL_USE_BUNDLES)
def test_w3_dual_use_bundle_blocks_unauthorized_install(
    project_name: str, tmp_path
):
    """Dual-use bundles must refuse install without explicit authorization
    (LBL-BUNDLE-DUAL-USE)."""
    from lyra_core.bundle import DualUseAuthorizationError

    bundle_dir = _REPO_ROOT / "projects" / project_name / "bundle"
    b = SourceBundle.load(bundle_dir)
    inst = AgentInstaller(bundle=b)
    with pytest.raises(DualUseAuthorizationError):
        inst.install(target_dir=tmp_path / project_name)
