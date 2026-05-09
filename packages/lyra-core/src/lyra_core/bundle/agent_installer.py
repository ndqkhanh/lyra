"""L311-5 — Agent-as-installer pipeline.

The installer runs the five-step bring-up from
[`docs/239-software-3-0-paradigm.md`](../../../../../../docs/239-software-3-0-paradigm.md) §(d):

1. **provision** — create target dir, materialize persona/memory/seed.
2. **register skills** — copy each skill file into a flat skills/ dir
   under the target.
3. **wire tools** — record the tool descriptor file (real MCP spawn is
   delegated to the runtime; the installer only ensures descriptors
   are well-formed).
4. **smoke-eval** — run the bundle's smoke evals through a pluggable
   ``SmokeEvalRunner``. The default runner reads the JSONL and counts
   how many entries have ``"expected_pass": true``; this is a stub
   that callers replace in production with a real eval harness.
5. **attest** — emit a signed :class:`Attestation` recording bundle
   hash, install timestamp, eval pass rate, and target-dir hash.

If smoke-eval pass-rate falls below ``manifest.smoke_eval_threshold``
(default 0.95) the install fails closed (``LBL-AI-EVAL``).

Idempotency (``LBL-AI-IDEMPOTENT``) is enforced by checking for an
existing attestation file with the same bundle hash — running install
twice with the same bundle is a no-op.
"""
from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .attestation import Attestation, sign_attestation
from .source_bundle import BundleValidationError, SourceBundle


InstallStep = Literal[
    "provision", "register_skills", "wire_tools", "smoke_eval", "attest"
]


class InstallError(RuntimeError):
    """Raised when an installer step fails (closed-failure mode)."""


class DualUseAuthorizationError(InstallError):
    """Raised when a dual-use bundle is installed without explicit authorization.

    Enforces ``LBL-BUNDLE-DUAL-USE``: bundles whose manifest declares
    ``dual_use: true`` (helix-bio, cipher-sec, aegis-ops) require the
    caller to pass both ``allow_dual_use=True`` *and* a non-empty
    ``authorized_by`` identifier (operator name, ticket, attestation
    fingerprint) that survives into the resulting attestation.
    """


@dataclass(frozen=True)
class SmokeEvalReport:
    """Output of a :class:`SmokeEvalRunner`."""

    pass_count: int
    fail_count: int
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.pass_count + self.fail_count + self.skipped

    @property
    def pass_rate(self) -> float:
        attempted = self.pass_count + self.fail_count
        if attempted == 0:
            return 0.0
        return self.pass_count / attempted


# A SmokeEvalRunner takes the bundle and returns a SmokeEvalReport.
# The default implementation is a stub that reads `expected_pass`
# from each JSONL line — production callers swap in a real runner.
SmokeEvalRunner = Callable[[SourceBundle], SmokeEvalReport]


def default_smoke_eval_runner(bundle: SourceBundle) -> SmokeEvalReport:
    """Stub runner: counts ``expected_pass`` flags in evals.golden JSONL.

    Real implementations call into Lyra's eval harness with the bundle's
    persona/skills loaded; this stub keeps the install pipeline testable
    without an LLM.
    """
    p = (bundle.root / bundle.evals.golden_path).resolve()
    pass_n = 0
    fail_n = 0
    skipped = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if obj.get("expected_pass") is True:
            pass_n += 1
        elif obj.get("expected_pass") is False:
            fail_n += 1
        else:
            skipped += 1
    return SmokeEvalReport(pass_count=pass_n, fail_count=fail_n, skipped=skipped)


@dataclass
class AgentInstaller:
    """Five-step bring-up of a :class:`SourceBundle` into a target dir.

    Composition: ``installer.install(target_dir)`` runs the pipeline and
    returns an :class:`Attestation`. Steps can be observed via the
    optional ``on_step`` callback for tracing / progress reporting.

    When ``routine_registry`` is set to a
    :class:`~lyra_core.cron.routines.RoutineRegistry`, the installer
    auto-registers every routine declared in the bundle's manifest at
    install time. When ``None`` (default) routines are loaded into
    ``bundle.routines`` but not wired — callers can register them
    later by hand.
    """

    bundle: SourceBundle
    smoke_eval_runner: SmokeEvalRunner = field(default=default_smoke_eval_runner)
    on_step: Callable[[InstallStep, dict[str, Any]], None] | None = None
    routine_registry: Any = None  # Optional[RoutineRegistry]; lazy import
    installed_registry: Any = None  # Optional[InstalledRegistry]; lazy import
    last_registered_routines: tuple[str, ...] = field(default=(), init=False)

    def install(
        self,
        *,
        target_dir: Path | str,
        signing_key: bytes | None = None,
        allow_dual_use: bool = False,
        authorized_by: str | None = None,
    ) -> Attestation:
        target = Path(target_dir).resolve()
        target.mkdir(parents=True, exist_ok=True)

        # LBL-BUNDLE-DUAL-USE gate. Dual-use bundles require explicit
        # authorization at install time. We require BOTH the
        # ``allow_dual_use=True`` flag AND a non-empty ``authorized_by``
        # so a single ``--yes`` reflex isn't enough — the operator
        # must name the authorizing entity (operator / ticket /
        # attestation fingerprint). The identifier is folded into the
        # attestation so an audit trail survives.
        if self.bundle.manifest.dual_use:
            if not allow_dual_use or not (authorized_by and authorized_by.strip()):
                raise DualUseAuthorizationError(
                    f"bundle {self.bundle.manifest.name!r} declares dual_use=true; "
                    "install requires allow_dual_use=True AND a non-empty "
                    "authorized_by identifier (LBL-BUNDLE-DUAL-USE)."
                )

        bundle_hash = self.bundle.hash()
        attestation_path = target / "attestation.json"

        # Idempotency check (LBL-AI-IDEMPOTENT).
        if attestation_path.exists():
            try:
                existing = Attestation.load(attestation_path)
                if existing.bundle_hash == bundle_hash:
                    self._notify("attest", {"idempotent": True})
                    return existing
            except Exception:
                # Corrupt or unreadable attestation — fall through and
                # reinstall.
                pass

        # Step 1: provision.
        self._notify("provision", {"target": str(target)})
        self._provision(target)

        # Step 2: register skills.
        self._notify("register_skills", {"count": len(self.bundle.skills)})
        registered = self._register_skills(target)

        # Step 3: wire tools (descriptor only; live MCP spawn is the
        # runtime's job).
        self._notify("wire_tools", {"count": len(self.bundle.tools)})
        wired = self._wire_tools(target)

        # Step 4: smoke eval (LBL-AI-EVAL).
        self._notify("smoke_eval", {"runner": self.smoke_eval_runner.__name__})
        try:
            report = self.smoke_eval_runner(self.bundle)
        except Exception as e:
            raise InstallError(f"smoke eval runner crashed: {e}") from e

        threshold = self.bundle.manifest.smoke_eval_threshold
        if report.pass_rate < threshold:
            raise InstallError(
                f"smoke eval pass-rate {report.pass_rate:.3f} below "
                f"threshold {threshold:.3f} (LBL-AI-EVAL)"
            )

        # Step 5: attest (LBL-AI-ATTEST).
        attestation = Attestation(
            bundle_name=self.bundle.manifest.name,
            bundle_version=self.bundle.manifest.version,
            bundle_hash=bundle_hash,
            target_dir=str(target),
            installed_at=time.time(),
            smoke_eval_pass=report.pass_count,
            smoke_eval_fail=report.fail_count,
            smoke_eval_pass_rate=report.pass_rate,
            registered_skills=tuple(registered),
            wired_tools=tuple(wired),
            verifier_domain=self.bundle.verifier.domain,
            dual_use=self.bundle.manifest.dual_use,
            authorized_by=authorized_by if self.bundle.manifest.dual_use else None,
            signature=None,
        )
        signed = sign_attestation(attestation, key=signing_key)
        signed.dump(attestation_path)
        self._notify(
            "attest",
            {
                "pass_rate": report.pass_rate,
                "skills": len(registered),
                "tools": len(wired),
            },
        )

        # L311-6 bundle → coverage auto-populate. Every successful
        # install contributes to the process-wide
        # :class:`VerifierCoverageIndex`. The verifier_id is the
        # bundle's name + version; eval_count is the count of golden
        # traces; pass rate is what the smoke-eval reported. Callers
        # that want isolation can pass `auto_populate_coverage=False`
        # via setting the attribute on the installer instance.
        if getattr(self, "auto_populate_coverage", True):
            try:
                from .verifier_coverage import global_index

                idx = global_index()
                verifier_id = f"{self.bundle.manifest.name}@{self.bundle.manifest.version}"
                idx.record_verifier(
                    domain=self.bundle.verifier.domain,
                    verifier_id=verifier_id,
                )
                idx.record_evals(
                    domain=self.bundle.verifier.domain,
                    count=self.bundle.evals.eval_count,
                )
                idx.record_pass_rate(
                    domain=self.bundle.verifier.domain,
                    rate=report.pass_rate,
                )
            except Exception:
                # Coverage update is best-effort; a misbehaving index
                # cannot break a successful install.
                pass

        # L311-5 + L37-8 bundle → routines integration. Bundles that
        # declare a ``routines:`` section get registered into Lyra's
        # cron RoutineRegistry. The integration is *additive* — if no
        # registry is wired, nothing happens. Bundles without a
        # routines section are unaffected.
        registered_routines: list[str] = []
        if getattr(self, "routine_registry", None) is not None and self.bundle.routines:
            try:
                registered_routines = self._register_routines(target)
            except Exception as e:
                # Routine registration failure is treated as a warning,
                # not a fatal install error — the rest of the bundle is
                # already installed and useful. Caller can re-trigger
                # registration manually.
                self._notify(
                    "register_routines_failed",
                    {"error": f"{type(e).__name__}: {e}"},
                )

        # Persist registered_routines onto the installer instance for
        # callers that want to inspect what got wired (the
        # attestation already records skills+tools+verifier_domain;
        # routines are post-attestation because they touch external
        # cron state).
        self.last_registered_routines = tuple(registered_routines)

        # Installed-registry upsert. Tracks what's installed where so
        # `/bundle list` and `/bundle uninstall` work. Best-effort —
        # a registry write failure does not break a successful install.
        if getattr(self, "auto_register_install", True):
            try:
                self._upsert_installed_record(target=target, attestation=signed)
            except Exception as e:
                self._notify(
                    "installed_registry_failed",
                    {"error": f"{type(e).__name__}: {e}"},
                )

        return signed

    def _upsert_installed_record(self, *, target: Path, attestation: Attestation) -> None:
        """Append or update the installed-bundles registry entry."""
        from .installed_registry import (
            InstalledRecord,
            global_installed_registry,
        )

        reg = self.installed_registry or global_installed_registry()
        att_path = target / "attestation.json"
        now = time.time()
        existing = reg.find(
            bundle_hash=attestation.bundle_hash, target_dir=str(target)
        )
        record = InstalledRecord(
            bundle_name=attestation.bundle_name,
            bundle_version=attestation.bundle_version,
            bundle_hash=attestation.bundle_hash,
            target_dir=str(target),
            attestation_path=str(att_path),
            installed_at=existing.installed_at if existing else attestation.installed_at,
            last_verified_at=now,
            dual_use=attestation.dual_use,
            authorized_by=attestation.authorized_by,
            verifier_domain=attestation.verifier_domain,
        )
        reg.upsert(record)

    # ---- internal steps ------------------------------------------

    def _provision(self, target: Path) -> None:
        # Validate first; cheap and avoids leaving partial provisions on
        # broken bundles.
        try:
            self.bundle.validate()
        except BundleValidationError as e:
            raise InstallError(f"bundle invalid: {e}") from e
        # Persona and memory seed go into the target so the runtime
        # can read them without touching the original bundle dir.
        (target / "persona.md").write_text(
            self.bundle.persona.text, encoding="utf-8"
        )
        (target / "memory_seed.md").write_text(
            self.bundle.memory.seed_text, encoding="utf-8"
        )
        # Manifest copy for traceability.
        meta = {
            "apiVersion": self.bundle.manifest.api_version,
            "kind": self.bundle.manifest.kind,
            "name": self.bundle.manifest.name,
            "version": self.bundle.manifest.version,
            "dual_use": self.bundle.manifest.dual_use,
        }
        (target / "manifest.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    def _register_skills(self, target: Path) -> list[str]:
        skills_dir = target / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        registered: list[str] = []
        for s in self.bundle.skills:
            src = (self.bundle.root / s.path).resolve()
            dst = skills_dir / Path(s.path).name
            shutil.copyfile(src, dst)
            registered.append(s.name)
        return registered

    def _register_routines(self, target: Path) -> list[str]:
        """Register every bundle routine into ``self.routine_registry``.

        The workflow callable wraps the bundle's MCP tool surface so
        a fired routine dispatches into the installed bundle. Naming
        convention: ``"<bundle_name>.<routine_name>"`` for the workflow
        id, prefixed-by-bundle so multiple bundles don't collide.
        """
        from lyra_core.cron.routines import (
            CronTrigger,
            GitHubWebhookTrigger,
            HttpApiTrigger,
            Routine,
        )

        registered: list[str] = []
        bundle_slug = self.bundle.manifest.name.replace(" ", "-").lower()
        for spec in self.bundle.routines:
            workflow_id = f"{bundle_slug}.{spec.name}"
            # Stub workflow — production callers register their own
            # via routine_registry.register_workflow before install.
            if workflow_id not in self.routine_registry.workflows:
                self.routine_registry.register_workflow(
                    workflow_id,
                    self._make_workflow_for(spec, target),
                )
            if spec.kind == "cron":
                trigger = CronTrigger(expression=spec.schedule or "0 */1 * * *", timezone=spec.timezone)
            elif spec.kind == "webhook":
                trigger = GitHubWebhookTrigger(repo=spec.repo, events=spec.events or ("push",))
            else:  # api
                trigger = HttpApiTrigger(path=spec.path or f"/routines/{workflow_id}")
            routine = Routine(
                name=f"{bundle_slug}.{spec.name}",
                trigger=trigger,
                workflow=workflow_id,
            )
            try:
                self.routine_registry.register_routine(routine)
            except ValueError:
                # Already registered (idempotent install) — skip.
                continue
            registered.append(routine.name)
        return registered

    def _make_workflow_for(self, spec: Any, target: Path):
        """Default stub workflow — emits a HIR event and returns the
        handler reference. Production callers replace this by
        registering their own workflow at the same id before install.
        """
        bundle_slug = self.bundle.manifest.name.replace(" ", "-").lower()

        def _stub_workflow(routine_name: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                from lyra_core.hir import events

                events.emit(
                    "bundle.routine.fired",
                    bundle=bundle_slug,
                    routine=routine_name,
                    handler=spec.handler,
                )
            except Exception:
                pass
            return {
                "ok": True,
                "bundle": bundle_slug,
                "routine": routine_name,
                "handler": spec.handler,
                "payload": payload,
            }

        return _stub_workflow

    def _wire_tools(self, target: Path) -> list[str]:
        # Just dump a JSON list — the runtime spawns MCP servers / wires
        # native tools at session start, not here.
        wired = []
        descriptors: list[dict[str, Any]] = []
        for t in self.bundle.tools:
            descriptors.append(
                {
                    "kind": t.kind,
                    "name": t.name,
                    "server": t.server,
                    "metadata": dict(t.metadata),
                }
            )
            wired.append(f"{t.kind}:{t.name}")
        (target / "tools.json").write_text(
            json.dumps(descriptors, indent=2), encoding="utf-8"
        )
        return wired

    def _notify(self, step: InstallStep, payload: dict[str, Any]) -> None:
        if self.on_step is not None:
            try:
                self.on_step(step, payload)
            except Exception:
                pass
        # Fire HIR event too so existing trace subscribers light up.
        try:
            from lyra_core.hir import events

            events.emit(f"bundle.{step}", **payload)
        except Exception:
            pass


__all__ = [
    "AgentInstaller",
    "InstallError",
    "InstallStep",
    "SmokeEvalReport",
    "SmokeEvalRunner",
    "default_smoke_eval_runner",
]
