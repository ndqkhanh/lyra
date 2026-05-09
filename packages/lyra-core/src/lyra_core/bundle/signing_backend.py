"""Pluggable signing backends for bundle attestations.

The HMAC-SHA256 default in :mod:`lyra_core.bundle.attestation` is fine
for local-machine "this is the bundle that produced this attestation"
assertions. Real cross-org attestation deserves real PKI — Sigstore,
Ed25519, or x509 chains. This module defines the
:class:`SigningBackend` Protocol so callers can swap the default
without touching the rest of the codebase.

Three backends ship:

* :class:`HmacBackend` — the existing HMAC-SHA256 default. No deps.
* :class:`Ed25519Backend` — Ed25519 detached signatures via Python's
  ``cryptography`` package. Falls back to a clean error when the
  package is not installed.
* :class:`SigstoreBackend` — placeholder shim documenting the
  Sigstore integration shape; raises ``NotImplementedError`` if used
  without the ``sigstore`` package wired.

Usage::

    from lyra_core.bundle import HmacBackend, set_default_signing_backend

    set_default_signing_backend(HmacBackend(key=b"prod-secret-from-vault"))
    # ...subsequent installs sign with this backend instead of the dev fallback.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Protocol


_DEFAULT_KEY_ENV = "LYRA_BUNDLE_ATTEST_KEY"


# ---- Protocol -------------------------------------------------------


class SigningBackend(Protocol):
    """Sign + verify a canonical payload byte-string.

    Two methods. Backends MUST be deterministic for HMAC-style schemes
    (same input → same signature) and tolerate non-determinism for
    Ed25519/Sigstore (signing creates a fresh signature every time;
    verify still passes for any valid signature over the same payload).
    """

    name: str

    def sign(self, payload: bytes) -> str:
        ...

    def verify(self, payload: bytes, signature: str) -> bool:
        ...


# ---- HMAC default ---------------------------------------------------


@dataclass
class HmacBackend:
    """HMAC-SHA256 backend. Stdlib only."""

    key: bytes | None = None
    name: str = "hmac-sha256"

    def _resolve_key(self) -> bytes:
        if self.key is not None:
            return self.key
        env = os.environ.get(_DEFAULT_KEY_ENV)
        if env:
            return env.encode()
        return b"lyra-dev-attestation-key"

    def sign(self, payload: bytes) -> str:
        return hmac.new(self._resolve_key(), payload, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)


# ---- Ed25519 (cryptography) -----------------------------------------


@dataclass
class Ed25519Backend:
    """Ed25519 detached signatures.

    Requires the ``cryptography`` package. Holds a private key for
    signing + a public key for verify; production callers split the
    two so signing happens with a vault-held private key and verify
    happens against published pubkeys.
    """

    private_key_pem: bytes | None = None
    public_key_pem: bytes | None = None
    name: str = "ed25519"

    def _import(self):
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ed25519
            return serialization, ed25519
        except ImportError as e:
            raise RuntimeError(
                "Ed25519Backend requires the 'cryptography' package; "
                "pip install cryptography"
            ) from e

    def sign(self, payload: bytes) -> str:
        if self.private_key_pem is None:
            raise RuntimeError(
                "Ed25519Backend.sign requires private_key_pem"
            )
        serialization, _ = self._import()
        priv = serialization.load_pem_private_key(self.private_key_pem, password=None)
        return priv.sign(payload).hex()  # type: ignore[union-attr]

    def verify(self, payload: bytes, signature: str) -> bool:
        if self.public_key_pem is None:
            raise RuntimeError(
                "Ed25519Backend.verify requires public_key_pem"
            )
        serialization, _ = self._import()
        pub = serialization.load_pem_public_key(self.public_key_pem)
        try:
            pub.verify(bytes.fromhex(signature), payload)  # type: ignore[union-attr]
            return True
        except Exception:
            return False


# ---- Sigstore placeholder -------------------------------------------


@dataclass
class SigstoreBackend:
    """Sigstore (cosign) keyless signing — placeholder.

    A real implementation calls into the ``sigstore`` Python package
    to mint an OIDC-bound short-lived certificate, sign with it, and
    bundle the chain. For now this backend documents the seam — calls
    raise ``NotImplementedError`` so production callers swap in a real
    impl when they need cross-org attestation.
    """

    oidc_token: str | None = None
    name: str = "sigstore"

    def sign(self, payload: bytes) -> str:
        raise NotImplementedError(
            "SigstoreBackend.sign is a placeholder; install + wire "
            "the 'sigstore' package and replace this method"
        )

    def verify(self, payload: bytes, signature: str) -> bool:
        raise NotImplementedError(
            "SigstoreBackend.verify is a placeholder; install + wire "
            "the 'sigstore' package and replace this method"
        )


# ---- process-wide default ------------------------------------------


_DEFAULT_BACKEND: SigningBackend | None = None


def default_signing_backend() -> SigningBackend:
    """Return the process-wide default. Defaults to :class:`HmacBackend`
    (the legacy behavior)."""
    global _DEFAULT_BACKEND
    if _DEFAULT_BACKEND is None:
        _DEFAULT_BACKEND = HmacBackend()
    return _DEFAULT_BACKEND


def set_default_signing_backend(backend: SigningBackend | None) -> None:
    """Install a new default. Pass ``None`` to reset to HMAC."""
    global _DEFAULT_BACKEND
    _DEFAULT_BACKEND = backend


__all__ = [
    "Ed25519Backend",
    "HmacBackend",
    "SigningBackend",
    "SigstoreBackend",
    "default_signing_backend",
    "set_default_signing_backend",
]
