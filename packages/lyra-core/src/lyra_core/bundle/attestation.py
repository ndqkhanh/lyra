"""Signed attestation record for installed bundles.

The attestation is a JSON object whose canonical form is signed with
HMAC-SHA256 (default) or a caller-supplied key. We deliberately avoid a
dependency on a real PKI / Sigstore client at the MVP; the
:func:`sign_attestation` / :func:`verify_attestation` functions are
swappable seams that production callers replace with a real signer.

Why HMAC and not Ed25519? Stdlib HMAC is enough for the MVP's
"prove the bundle that produced this attestation is the bundle that
this Lyra install verified" assertion. Real cross-org attestation
deserves a real signer (Sigstore, GPG, x509); the seam is here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_DEFAULT_KEY_ENV = "LYRA_BUNDLE_ATTEST_KEY"


class AttestationError(RuntimeError):
    """Raised on signature verification failures."""


@dataclass(frozen=True)
class Attestation:
    """Signed install record. Emitted by :class:`AgentInstaller.install`."""

    bundle_name: str
    bundle_version: str
    bundle_hash: str
    target_dir: str
    installed_at: float
    smoke_eval_pass: int
    smoke_eval_fail: int
    smoke_eval_pass_rate: float
    registered_skills: tuple[str, ...]
    wired_tools: tuple[str, ...]
    verifier_domain: str
    dual_use: bool
    signature: str | None
    authorized_by: str | None = None  # LBL-BUNDLE-DUAL-USE audit trail
    _envelope_version: int = field(default=1)

    # ---- (de)serialization ---------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_version": self._envelope_version,
            "bundle_name": self.bundle_name,
            "bundle_version": self.bundle_version,
            "bundle_hash": self.bundle_hash,
            "target_dir": self.target_dir,
            "installed_at": self.installed_at,
            "smoke_eval_pass": self.smoke_eval_pass,
            "smoke_eval_fail": self.smoke_eval_fail,
            "smoke_eval_pass_rate": self.smoke_eval_pass_rate,
            "registered_skills": list(self.registered_skills),
            "wired_tools": list(self.wired_tools),
            "verifier_domain": self.verifier_domain,
            "dual_use": self.dual_use,
            "authorized_by": self.authorized_by,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Attestation":
        return cls(
            bundle_name=str(d["bundle_name"]),
            bundle_version=str(d["bundle_version"]),
            bundle_hash=str(d["bundle_hash"]),
            target_dir=str(d["target_dir"]),
            installed_at=float(d["installed_at"]),
            smoke_eval_pass=int(d["smoke_eval_pass"]),
            smoke_eval_fail=int(d["smoke_eval_fail"]),
            smoke_eval_pass_rate=float(d["smoke_eval_pass_rate"]),
            registered_skills=tuple(d.get("registered_skills") or ()),
            wired_tools=tuple(d.get("wired_tools") or ()),
            verifier_domain=str(d.get("verifier_domain") or "generic"),
            dual_use=bool(d.get("dual_use", False)),
            authorized_by=d.get("authorized_by"),
            signature=d.get("signature"),
            _envelope_version=int(d.get("envelope_version", 1)),
        )

    @classmethod
    def load(cls, path: Path) -> "Attestation":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def dump(self, path: Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )


# ---- canonical signing payload ---------------------------------------


def _canonical_payload(att: Attestation) -> bytes:
    """Stable byte-string used to compute the signature.

    Excludes the ``signature`` field itself; everything else is sorted
    by key.
    """
    d = att.to_dict()
    d.pop("signature", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def _resolve_key(explicit: bytes | None) -> bytes:
    if explicit is not None:
        return explicit
    env = os.environ.get(_DEFAULT_KEY_ENV)
    if env:
        return env.encode()
    # Fallback dev key — fine for local installs, not for real attestation.
    return b"lyra-dev-attestation-key"


def sign_attestation(att: Attestation, *, key: bytes | None = None) -> Attestation:
    """Return a copy of ``att`` with HMAC-SHA256 signature attached."""
    payload = _canonical_payload(att)
    sig = hmac.new(_resolve_key(key), payload, hashlib.sha256).hexdigest()
    return Attestation(
        bundle_name=att.bundle_name,
        bundle_version=att.bundle_version,
        bundle_hash=att.bundle_hash,
        target_dir=att.target_dir,
        installed_at=att.installed_at,
        smoke_eval_pass=att.smoke_eval_pass,
        smoke_eval_fail=att.smoke_eval_fail,
        smoke_eval_pass_rate=att.smoke_eval_pass_rate,
        registered_skills=att.registered_skills,
        wired_tools=att.wired_tools,
        verifier_domain=att.verifier_domain,
        dual_use=att.dual_use,
        authorized_by=att.authorized_by,
        signature=sig,
    )


def verify_attestation(att: Attestation, *, key: bytes | None = None) -> bool:
    """Constant-time HMAC verify. Raises :class:`AttestationError` on
    missing signature; returns ``True/False`` on present-but-(in)valid."""
    if att.signature is None:
        raise AttestationError("attestation has no signature")
    expected = hmac.new(
        _resolve_key(key), _canonical_payload(att), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(att.signature, expected)


__all__ = [
    "Attestation",
    "AttestationError",
    "sign_attestation",
    "verify_attestation",
]
