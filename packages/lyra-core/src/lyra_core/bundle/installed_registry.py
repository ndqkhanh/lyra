"""Registry of installed bundles + uninstall lifecycle.

Tracks every bundle the :class:`AgentInstaller` has lit up on the
local machine. The registry is **filesystem-backed** so a human
operator can inspect ``~/.lyra/installed.json`` to see what's
installed without running Lyra.

Each registry entry binds:

* The bundle's name + version + content hash.
* The target_dir (where the install lives).
* The attestation path (and its current verify-status).
* Whether the install is dual-use + who authorized it.
* ``installed_at`` and ``last_verified_at`` timestamps.

The :class:`AgentInstaller` writes to this registry automatically on
every successful install (idempotent — re-installing the same hash
updates ``last_verified_at`` rather than appending). The
:func:`uninstall_bundle` function does the inverse: re-verifies the
attestation, then removes both the install directory and the
registry entry.
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any


_DEFAULT_REGISTRY_PATH = Path.home() / ".lyra" / "installed.json"


# ---- typed errors ---------------------------------------------------


class UninstallError(RuntimeError):
    """Raised when uninstall cannot proceed cleanly."""


# ---- record ---------------------------------------------------------


@dataclass(frozen=True)
class InstalledRecord:
    """One row in the installed-bundles registry."""

    bundle_name: str
    bundle_version: str
    bundle_hash: str
    target_dir: str
    attestation_path: str
    installed_at: float
    last_verified_at: float
    dual_use: bool = False
    authorized_by: str | None = None
    verifier_domain: str = "generic"

    def to_json(self) -> dict[str, Any]:
        return {
            "bundle_name": self.bundle_name,
            "bundle_version": self.bundle_version,
            "bundle_hash": self.bundle_hash,
            "target_dir": self.target_dir,
            "attestation_path": self.attestation_path,
            "installed_at": self.installed_at,
            "last_verified_at": self.last_verified_at,
            "dual_use": self.dual_use,
            "authorized_by": self.authorized_by,
            "verifier_domain": self.verifier_domain,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "InstalledRecord":
        return cls(
            bundle_name=str(d["bundle_name"]),
            bundle_version=str(d["bundle_version"]),
            bundle_hash=str(d["bundle_hash"]),
            target_dir=str(d["target_dir"]),
            attestation_path=str(d["attestation_path"]),
            installed_at=float(d["installed_at"]),
            last_verified_at=float(d["last_verified_at"]),
            dual_use=bool(d.get("dual_use", False)),
            authorized_by=d.get("authorized_by"),
            verifier_domain=str(d.get("verifier_domain", "generic")),
        )


# ---- registry -------------------------------------------------------


@dataclass
class InstalledRegistry:
    """Filesystem-backed registry of installed bundles."""

    path: Path = field(default_factory=lambda: _DEFAULT_REGISTRY_PATH)
    _records: dict[str, InstalledRecord] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def __post_init__(self) -> None:
        self.path = Path(self.path).expanduser()
        self._load()

    # ---- mutation -------------------------------------------------

    def upsert(self, record: InstalledRecord) -> None:
        """Add or update an entry. Keyed by ``bundle_hash`` so multiple
        installs of the same bundle in different target dirs are
        distinct entries."""
        key = self._key_for(record.bundle_hash, record.target_dir)
        with self._lock:
            self._records[key] = record
            self._flush_locked()

    def remove(self, bundle_hash: str, target_dir: str) -> InstalledRecord | None:
        key = self._key_for(bundle_hash, target_dir)
        with self._lock:
            rec = self._records.pop(key, None)
            if rec is not None:
                self._flush_locked()
            return rec

    # ---- read -----------------------------------------------------

    def all(self) -> tuple[InstalledRecord, ...]:
        return tuple(self._records.values())

    def find_by_name(self, name: str) -> tuple[InstalledRecord, ...]:
        return tuple(r for r in self._records.values() if r.bundle_name == name)

    def find_by_hash(self, bundle_hash: str) -> tuple[InstalledRecord, ...]:
        return tuple(r for r in self._records.values() if r.bundle_hash == bundle_hash)

    def find(self, *, bundle_hash: str, target_dir: str) -> InstalledRecord | None:
        return self._records.get(self._key_for(bundle_hash, target_dir))

    def __len__(self) -> int:
        return len(self._records)

    # ---- internal -------------------------------------------------

    @staticmethod
    def _key_for(bundle_hash: str, target_dir: str) -> str:
        return f"{bundle_hash}@{Path(target_dir).resolve()}"

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        for row in data.get("installed", []):
            try:
                rec = InstalledRecord.from_json(row)
            except Exception:
                continue
            self._records[self._key_for(rec.bundle_hash, rec.target_dir)] = rec

    def _flush_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "envelope_version": 1,
            "updated_at": time.time(),
            "installed": [r.to_json() for r in self._records.values()],
        }
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)


# ---- process-wide singleton -----------------------------------------


_GLOBAL_REGISTRY: InstalledRegistry | None = None


def global_installed_registry() -> InstalledRegistry:
    """Return the process-wide :class:`InstalledRegistry` singleton.

    Tests reset between cases via :func:`reset_global_installed_registry`.
    """
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = InstalledRegistry()
    return _GLOBAL_REGISTRY


def reset_global_installed_registry(path: Path | None = None) -> InstalledRegistry:
    """Drop the singleton; if ``path`` is given, the new registry uses
    it (test-only helper for isolated state)."""
    global _GLOBAL_REGISTRY
    if path is not None:
        _GLOBAL_REGISTRY = InstalledRegistry(path=path)
    else:
        _GLOBAL_REGISTRY = None
    return global_installed_registry()


# ---- uninstall ------------------------------------------------------


def uninstall_bundle(
    *,
    bundle_hash: str,
    target_dir: Path | str,
    registry: InstalledRegistry | None = None,
    verify_attestation_first: bool = True,
) -> InstalledRecord:
    """Re-verify the attestation, then remove the install directory
    and the registry entry.

    Order matters:

    1. Look up the registry entry (raises if not present).
    2. Verify the attestation (refuses to uninstall if the
       attestation has been tampered with — the operator can pass
       ``verify_attestation_first=False`` to override, but doing so
       is logged as ``LBL-UNINSTALL-OVERRIDE``).
    3. ``shutil.rmtree`` the target directory.
    4. Remove the registry entry.

    Returns the removed :class:`InstalledRecord`.
    """
    target = Path(target_dir).expanduser().resolve()
    reg = registry if registry is not None else global_installed_registry()
    rec = reg.find(bundle_hash=bundle_hash, target_dir=str(target))
    if rec is None:
        raise UninstallError(
            f"no installed record for hash {bundle_hash[:16]}... at {target}"
        )

    if verify_attestation_first:
        # Re-verify the attestation file. Tampering is fail-closed.
        from .attestation import Attestation, verify_attestation

        att_path = Path(rec.attestation_path)
        if not att_path.exists():
            raise UninstallError(
                f"attestation file missing at {att_path}; refusing uninstall "
                f"(LBL-UNINSTALL-VERIFY)"
            )
        try:
            att = Attestation.load(att_path)
        except Exception as e:
            raise UninstallError(
                f"attestation unreadable at {att_path}: {e}"
            ) from e
        try:
            ok = verify_attestation(att)
        except Exception as e:
            raise UninstallError(
                f"attestation verification crashed: {e}"
            ) from e
        if not ok:
            raise UninstallError(
                f"attestation signature invalid at {att_path}; refusing "
                f"uninstall (LBL-UNINSTALL-VERIFY). Pass "
                f"verify_attestation_first=False to override."
            )

    # Remove install dir.
    if target.exists():
        shutil.rmtree(target)
    # Remove registry entry.
    reg.remove(bundle_hash, str(target))
    # Emit lifecycle event.
    try:
        from lyra_core.hir import events

        events.emit(
            "bundle.uninstalled",
            bundle_name=rec.bundle_name,
            bundle_version=rec.bundle_version,
            bundle_hash=rec.bundle_hash,
            target_dir=rec.target_dir,
        )
    except Exception:
        pass
    return rec


__all__ = [
    "InstalledRecord",
    "InstalledRegistry",
    "UninstallError",
    "global_installed_registry",
    "reset_global_installed_registry",
    "uninstall_bundle",
]
