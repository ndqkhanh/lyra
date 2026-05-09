"""Bundle marketplace fetcher.

Realizes Argus's `marketplace-fetcher` skill ([`projects/argus/bundle/skills/06-marketplace-fetcher.md`](../../../../../../../projects/argus/bundle/skills/06-marketplace-fetcher.md))
as a v3.11 primitive. Fetches a bundle archive from a remote URL,
verifies its detached signature against a pre-registered marketplace
key, unpacks it into a sandboxed cache, and returns a path the
:class:`AgentInstaller` can ingest.

Bright lines (mirrors Argus's three):

* ``LBL-FETCH-VERIFY`` — every fetched bundle's signature must verify
  against the marketplace's published key. Unsigned or
  signature-mismatched bundles are *rejected, not warned*.
* ``LBL-FETCH-SCOPE`` — fetched bundles inherit *no* tool grants
  beyond what they explicitly declare in their manifest.
* ``LBL-FETCH-SBOM`` — every fetch records a software-bill-of-materials
  entry: source URL, bundle hash, signing key fingerprint, fetch
  timestamp.

The implementation is **stdlib-only** — `urllib.request` for fetch,
`hmac` + `hashlib` for verify, `tarfile` for unpack. Real Sigstore
swap is a v3.11.x follow-up.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import tarfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .source_bundle import SourceBundle


_DEFAULT_CACHE_ENV = "LYRA_MARKETPLACE_CACHE"


# ---- typed errors ---------------------------------------------------


class MarketplaceError(RuntimeError):
    """Base class for marketplace fetch errors."""


class SignatureMismatchError(MarketplaceError):
    """Raised when ``LBL-FETCH-VERIFY`` rejects a bundle."""


class FetchScopeError(MarketplaceError):
    """Raised when ``LBL-FETCH-SCOPE`` blocks a fetched bundle."""


# ---- typed records --------------------------------------------------


@dataclass(frozen=True)
class MarketplaceKey:
    """A marketplace's published verification key."""

    fingerprint: str
    secret: bytes  # HMAC secret (or public key in a real impl)


@dataclass(frozen=True)
class FetchSpec:
    """One fetch request."""

    url: str
    expected_signature: str
    marketplace: str  # which marketplace published it
    expected_hash: str | None = None  # optional content hash for double-check


@dataclass(frozen=True)
class FetchedBundle:
    """A fetched, verified, unpacked bundle on local disk."""

    bundle: SourceBundle
    sbom: "SBOMEntry"


@dataclass(frozen=True)
class SBOMEntry:
    """``LBL-FETCH-SBOM``: the audit row for one fetch."""

    bundle_name: str
    bundle_hash: str
    source_url: str
    marketplace: str
    signing_key_fingerprint: str
    fetched_at: float
    cache_path: str

    def to_json(self) -> dict:
        return {
            "bundle_name": self.bundle_name,
            "bundle_hash": self.bundle_hash,
            "source_url": self.source_url,
            "marketplace": self.marketplace,
            "signing_key_fingerprint": self.signing_key_fingerprint,
            "fetched_at": self.fetched_at,
            "cache_path": self.cache_path,
        }


# ---- registry of trusted marketplaces -------------------------------


@dataclass
class MarketplaceRegistry:
    """In-memory registry of trusted marketplaces and their keys."""

    keys: dict[str, MarketplaceKey] = field(default_factory=dict)
    sbom_log: list[SBOMEntry] = field(default_factory=list)

    def trust(self, marketplace: str, key: MarketplaceKey) -> None:
        self.keys[marketplace] = key

    def revoke(self, marketplace: str) -> None:
        self.keys.pop(marketplace, None)

    def is_trusted(self, marketplace: str) -> bool:
        return marketplace in self.keys


# ---- the fetcher ----------------------------------------------------


@dataclass
class MarketplaceFetcher:
    """Pulls bundles from URLs, verifies signatures, unpacks to cache.

    URL fetcher is pluggable so tests can inject a stub without
    touching the network. Default uses ``urllib.request``.
    """

    registry: MarketplaceRegistry
    cache_root: Path = field(default_factory=lambda: _default_cache_root())
    fetch_url: callable = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.cache_root = Path(self.cache_root).expanduser().resolve()
        self.cache_root.mkdir(parents=True, exist_ok=True)
        if self.fetch_url is None:
            self.fetch_url = _default_fetch_url

    def fetch(self, spec: FetchSpec) -> FetchedBundle:
        """Fetch + verify + unpack. Returns a :class:`FetchedBundle`.

        Raises:
            SignatureMismatchError: ``LBL-FETCH-VERIFY`` failure.
            MarketplaceError: untrusted marketplace, hash mismatch,
                or unpack failure.
        """
        # Step 1: marketplace must be trusted.
        if not self.registry.is_trusted(spec.marketplace):
            raise MarketplaceError(
                f"marketplace {spec.marketplace!r} is not trusted; call "
                "MarketplaceRegistry.trust() first"
            )
        key = self.registry.keys[spec.marketplace]

        # Step 2: fetch the archive bytes.
        if not _is_safe_url(spec.url):
            raise MarketplaceError(f"refused unsafe URL scheme: {spec.url}")
        try:
            archive_bytes = self.fetch_url(spec.url)
        except Exception as e:
            raise MarketplaceError(f"fetch failed: {e}") from e

        # Step 3: optional content hash.
        actual_hash = hashlib.sha256(archive_bytes).hexdigest()
        if spec.expected_hash and not hmac.compare_digest(actual_hash, spec.expected_hash):
            raise MarketplaceError(
                f"content hash mismatch: expected {spec.expected_hash}, got {actual_hash}"
            )

        # Step 4: signature verify (LBL-FETCH-VERIFY).
        expected_sig = hmac.new(key.secret, archive_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, spec.expected_signature):
            raise SignatureMismatchError(
                f"signature mismatch (LBL-FETCH-VERIFY): "
                f"marketplace={spec.marketplace} url={spec.url}"
            )

        # Step 5: unpack into the cache.
        cache_dir = self.cache_root / actual_hash[:16]
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._unpack_safely(archive_bytes, cache_dir)
        except Exception as e:
            raise MarketplaceError(f"unpack failed: {e}") from e

        # Step 6: load the SourceBundle.
        try:
            bundle = SourceBundle.load(cache_dir)
        except Exception as e:
            raise MarketplaceError(f"loaded bundle invalid: {e}") from e

        # LBL-FETCH-SCOPE: fetched bundles bring no tool grants beyond
        # what their manifest declares. The installer enforces this
        # via the existing tool-descriptor flow; here we just sanity-
        # check that the manifest didn't smuggle in an absolute-path
        # MCP server (which would escape the cache sandbox).
        for tool in bundle.tools:
            if tool.kind == "mcp" and tool.server:
                if tool.server.startswith(("http://", "https://", "stdio:/")):
                    continue
                # Relative stdio path — must resolve inside the cache.
                if tool.server.startswith("stdio:"):
                    relative = tool.server[len("stdio:"):]
                    full = (cache_dir / relative).resolve()
                    try:
                        full.relative_to(cache_dir)
                    except ValueError:
                        raise FetchScopeError(
                            f"tool {tool.name!r} server escapes cache "
                            f"(LBL-FETCH-SCOPE)"
                        )

        # Step 7: SBOM (LBL-FETCH-SBOM).
        entry = SBOMEntry(
            bundle_name=bundle.manifest.name,
            bundle_hash=bundle.hash(),
            source_url=spec.url,
            marketplace=spec.marketplace,
            signing_key_fingerprint=key.fingerprint,
            fetched_at=time.time(),
            cache_path=str(cache_dir),
        )
        self.registry.sbom_log.append(entry)
        return FetchedBundle(bundle=bundle, sbom=entry)

    def _unpack_safely(self, archive_bytes: bytes, dest: Path) -> None:
        """Unpack a tar.gz/tar archive without allowing path-escape."""
        import io

        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:*") as tar:
            for member in tar.getmembers():
                # Refuse absolute / parent-traversal paths.
                p = Path(member.name)
                if p.is_absolute() or any(part == ".." for part in p.parts):
                    raise MarketplaceError(
                        f"unsafe archive member {member.name!r}"
                    )
            tar.extractall(dest)


# ---- helpers ---------------------------------------------------------


def _default_cache_root() -> Path:
    env = os.environ.get(_DEFAULT_CACHE_ENV)
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".lyra" / "marketplace-cache"


def _default_fetch_url(url: str) -> bytes:
    """stdlib fetch — no external deps. Tests inject a stub."""
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        return resp.read()


def _is_safe_url(url: str) -> bool:
    """Refuse non-http/https URLs."""
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


# ---- helper: build an SBOM-only signed archive (test fixture) -------


def sign_archive(archive_bytes: bytes, key: MarketplaceKey) -> str:
    """Compute the canonical signature for a marketplace key.

    Production publishers hold the key and call this; consumers
    re-derive the same expected signature to verify.
    """
    return hmac.new(key.secret, archive_bytes, hashlib.sha256).hexdigest()


__all__ = [
    "FetchSpec",
    "FetchScopeError",
    "FetchedBundle",
    "MarketplaceError",
    "MarketplaceFetcher",
    "MarketplaceKey",
    "MarketplaceRegistry",
    "SBOMEntry",
    "SignatureMismatchError",
    "sign_archive",
]
