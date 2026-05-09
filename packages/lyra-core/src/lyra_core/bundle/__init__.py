"""L311-4 / L311-5 — Software 3.0 SourceBundle + agent-installer.

A :class:`SourceBundle` is the canonical six-part Software 3.0 source
artefact ([`docs/239-software-3-0-paradigm.md`](../../../../../../docs/239-software-3-0-paradigm.md)
§(b)): persona + skills + tools + memory + evals + verifier. The
bundle is the *unit of deploy* — installed as a whole or not at all.

The :class:`AgentInstaller` is the agent-as-installer primitive
([`docs/239`](../../../../../../docs/239-software-3-0-paradigm.md) §(d)):
provision runtime → register skills → wire tools → run smoke evals
→ emit signed attestation. Install fails closed if smoke-eval pass-rate
falls below the bundle's threshold (default 95%, ``LBL-AI-EVAL``).

Every install emits an :class:`Attestation` (``LBL-AI-ATTEST``) — a
signed JSON record of what was installed, with what versions, against
what evals.

Usage::

    from lyra_core.bundle import SourceBundle, AgentInstaller

    bundle = SourceBundle.load("./orion-code-bundle/")
    bundle.validate()  # raises BundleValidationError on missing parts

    installer = AgentInstaller(bundle)
    attestation = installer.install(target_dir="./.lyra/installed/")
    assert attestation.smoke_eval_pass_rate >= 0.95
"""
from __future__ import annotations

from .attestation import Attestation, AttestationError, sign_attestation, verify_attestation
from .signing_backend import (
    Ed25519Backend,
    HmacBackend,
    SigningBackend,
    SigstoreBackend,
    default_signing_backend,
    set_default_signing_backend,
)
from .agent_installer import (
    AgentInstaller,
    DualUseAuthorizationError,
    InstallError,
    InstallStep,
    SmokeEvalReport,
    SmokeEvalRunner,
)
from .source_bundle import (
    BundleManifest,
    BundleValidationError,
    EvalSpec,
    MemorySpec,
    PersonaSpec,
    RoutineSpec,
    SkillRef,
    SourceBundle,
    ToolSpec,
    VerifierSpec,
)
from .verifier_coverage import (
    VerifierCoverage,
    VerifierCoverageIndex,
    global_index,
    reset_global_index,
)
from .marketplace import (
    FetchSpec,
    FetchScopeError,
    FetchedBundle,
    MarketplaceError,
    MarketplaceFetcher,
    MarketplaceKey,
    MarketplaceRegistry,
    SBOMEntry,
    SignatureMismatchError,
    sign_archive,
)
from .installed_registry import (
    InstalledRecord,
    InstalledRegistry,
    UninstallError,
    global_installed_registry,
    reset_global_installed_registry,
    uninstall_bundle,
)
from .exporters import (
    ClaudeCodeExporter,
    CodexExporter,
    CursorExporter,
    ExportError,
    ExportManifest,
    ExportTarget,
    Exporter,
    GeminiCLIExporter,
    list_exporters,
    resolve_exporter,
)

__all__ = [
    "ClaudeCodeExporter",
    "CodexExporter",
    "CursorExporter",
    "ExportError",
    "ExportManifest",
    "ExportTarget",
    "Exporter",
    "FetchScopeError",
    "FetchSpec",
    "FetchedBundle",
    "GeminiCLIExporter",
    "InstalledRecord",
    "InstalledRegistry",
    "MarketplaceError",
    "MarketplaceFetcher",
    "MarketplaceKey",
    "MarketplaceRegistry",
    "SBOMEntry",
    "SignatureMismatchError",
    "UninstallError",
    "global_installed_registry",
    "list_exporters",
    "reset_global_installed_registry",
    "resolve_exporter",
    "sign_archive",
    "uninstall_bundle",
    "AgentInstaller",
    "Attestation",
    "AttestationError",
    "BundleManifest",
    "BundleValidationError",
    "Ed25519Backend",
    "HmacBackend",
    "SigningBackend",
    "SigstoreBackend",
    "default_signing_backend",
    "set_default_signing_backend",
    "DualUseAuthorizationError",
    "EvalSpec",
    "InstallError",
    "InstallStep",
    "MemorySpec",
    "PersonaSpec",
    "RoutineSpec",
    "SkillRef",
    "SmokeEvalReport",
    "SmokeEvalRunner",
    "SourceBundle",
    "ToolSpec",
    "VerifierCoverage",
    "VerifierCoverageIndex",
    "VerifierSpec",
    "global_index",
    "reset_global_index",
    "sign_attestation",
    "verify_attestation",
]
