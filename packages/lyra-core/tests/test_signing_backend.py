"""Tests for the pluggable signing backends."""
from __future__ import annotations

import pytest

from lyra_core.bundle import (
    Ed25519Backend,
    HmacBackend,
    SigstoreBackend,
    default_signing_backend,
    set_default_signing_backend,
)


# ---- HMAC backend ----------------------------------------------------


def test_hmac_round_trip():
    backend = HmacBackend(key=b"test-key")
    payload = b"hello world"
    sig = backend.sign(payload)
    assert backend.verify(payload, sig) is True


def test_hmac_verify_rejects_tampered():
    backend = HmacBackend(key=b"test-key")
    sig = backend.sign(b"original")
    assert backend.verify(b"tampered", sig) is False


def test_hmac_resolves_env_key(monkeypatch):
    monkeypatch.setenv("LYRA_BUNDLE_ATTEST_KEY", "env-secret")
    backend = HmacBackend()
    sig = backend.sign(b"x")
    # Different backend (with no key, no env) — different sig.
    monkeypatch.delenv("LYRA_BUNDLE_ATTEST_KEY")
    other = HmacBackend()
    assert backend.sign(b"x") != other.sign(b"x") or sig != other.sign(b"x")


def test_hmac_dev_fallback_when_unset(monkeypatch):
    monkeypatch.delenv("LYRA_BUNDLE_ATTEST_KEY", raising=False)
    backend = HmacBackend()
    # Always works — falls back to the documented dev key.
    sig = backend.sign(b"x")
    assert backend.verify(b"x", sig) is True


def test_hmac_constant_time_compare():
    backend = HmacBackend(key=b"k")
    sig = backend.sign(b"payload")
    # Wrong-length signature still returns False, no exception.
    assert backend.verify(b"payload", "deadbeef") is False
    assert backend.verify(b"payload", "") is False


# ---- Sigstore placeholder --------------------------------------------


def test_sigstore_sign_raises_not_implemented():
    backend = SigstoreBackend()
    with pytest.raises(NotImplementedError):
        backend.sign(b"x")


def test_sigstore_verify_raises_not_implemented():
    backend = SigstoreBackend()
    with pytest.raises(NotImplementedError):
        backend.verify(b"x", "y")


def test_sigstore_name_attribute():
    backend = SigstoreBackend()
    assert backend.name == "sigstore"


# ---- Ed25519 backend (depends on cryptography availability) ---------


def _has_cryptography() -> bool:
    try:
        import cryptography  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_cryptography(), reason="cryptography not installed")
def test_ed25519_round_trip():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    priv = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    backend = Ed25519Backend(private_key_pem=priv_pem, public_key_pem=pub_pem)
    payload = b"signed by ed25519"
    sig = backend.sign(payload)
    assert backend.verify(payload, sig) is True


@pytest.mark.skipif(not _has_cryptography(), reason="cryptography not installed")
def test_ed25519_verify_rejects_tampered():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    priv = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    backend = Ed25519Backend(private_key_pem=priv_pem, public_key_pem=pub_pem)
    sig = backend.sign(b"original")
    assert backend.verify(b"tampered", sig) is False


def test_ed25519_sign_without_priv_raises():
    backend = Ed25519Backend(public_key_pem=b"x")
    with pytest.raises(RuntimeError, match="private_key_pem"):
        backend.sign(b"x")


def test_ed25519_verify_without_pub_raises():
    backend = Ed25519Backend(private_key_pem=b"x")
    with pytest.raises(RuntimeError, match="public_key_pem"):
        backend.verify(b"x", "y")


# ---- default-backend swap --------------------------------------------


def test_default_starts_as_hmac():
    set_default_signing_backend(None)  # reset
    assert isinstance(default_signing_backend(), HmacBackend)


def test_default_swappable():
    backend = HmacBackend(key=b"swap-test")
    set_default_signing_backend(backend)
    try:
        assert default_signing_backend() is backend
    finally:
        set_default_signing_backend(None)


def test_default_reset_via_none():
    backend = HmacBackend(key=b"swap-test")
    set_default_signing_backend(backend)
    set_default_signing_backend(None)
    assert default_signing_backend() is not backend
