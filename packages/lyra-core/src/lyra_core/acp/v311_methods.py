"""v3.11 ACP method pack.

Exposes Lyra v3.11 capabilities (Agent Teams runtime, Software 3.0
bundle pipeline, scaling axes, verifier coverage) over JSON-RPC so
non-CLI clients (web UI, IDE extensions, Slack bots, ACP-compatible
tools) can drive them.

Methods registered (all under the ``v311.`` namespace):

* ``v311.agentteams.spawn(team, name, model?)`` — spawn a teammate
  into the named team. Creates the team on first use.
* ``v311.agentteams.add_task(team, title, assign?, depends_on?)`` —
  add a task to the shared list.
* ``v311.agentteams.run(team, timeout_s?)`` — drive the team to idle.
* ``v311.agentteams.report(team)`` — TeamReport snapshot.
* ``v311.agentteams.mailbox(team, recipient)`` — mailbox contents.
* ``v311.bundle.info(path)`` — load + summary.
* ``v311.bundle.install(path, target_dir, allow_dual_use?, authorized_by?)``
  — full install pipeline.
* ``v311.bundle.export(path, target, target_dir?)`` — cross-harness
  export to one of {claude-code, cursor, codex, gemini-cli}.
* ``v311.scaling.snapshot()`` — four-axis position + best lever.
* ``v311.coverage.snapshot()`` — verifier-coverage index by domain.

Bind into an existing :class:`AcpServer` with::

    server = AcpServer()
    register_v311_methods(server)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .server import AcpError, AcpServer


# ---- registry --------------------------------------------------------


def register_v311_methods(server: AcpServer, *, team_dir_root: Path | str | None = None) -> AcpServer:
    """Register every v3.11 method on the supplied ``server``.

    The ``team_dir_root`` controls where ``LeadSession`` instances
    materialize their shared task lists and mailboxes; defaults to
    ``~/.lyra/teams/``.
    """
    state = _V311State(team_dir_root=Path(team_dir_root or Path.home() / ".lyra" / "teams"))
    server.register("v311.agentteams.spawn", state.spawn)
    server.register("v311.agentteams.add_task", state.add_task)
    server.register("v311.agentteams.run", state.run_until_idle)
    server.register("v311.agentteams.report", state.report)
    server.register("v311.agentteams.mailbox", state.mailbox)
    server.register("v311.bundle.info", state.bundle_info)
    server.register("v311.bundle.install", state.bundle_install)
    server.register("v311.bundle.export", state.bundle_export)
    server.register("v311.bundle.fetch", state.bundle_fetch)
    server.register("v311.bundle.trust", state.bundle_trust)
    server.register("v311.bundle.list", state.bundle_list)
    server.register("v311.bundle.uninstall", state.bundle_uninstall)
    server.register("v311.scaling.snapshot", state.scaling_snapshot)
    server.register("v311.coverage.snapshot", state.coverage_snapshot)
    return server


# ---- state container ------------------------------------------------


class _V311State:
    """Per-server shared state for v3.11 methods."""

    def __init__(self, *, team_dir_root: Path) -> None:
        self.team_dir_root = team_dir_root
        self.team_dir_root.mkdir(parents=True, exist_ok=True)
        self._teams: dict[str, Any] = {}
        self._marketplace_registry: Any = None  # lazy

    def _marketplace(self):
        from lyra_core.bundle import MarketplaceRegistry
        if self._marketplace_registry is None:
            self._marketplace_registry = MarketplaceRegistry()
        return self._marketplace_registry

    # ---- /agentteams ---------------------------------------------

    def _resolve_team(self, name: str):
        from lyra_core.teams import LeadSession

        if not name:
            raise AcpError(-32602, "missing required param: team")
        existing = self._teams.get(name)
        if existing is not None:
            return existing
        # Default executor — deterministic stub. Real-LLM wiring is
        # the CLI's job; ACP clients can override by setting their
        # own executor before the first spawn (post-MVP feature).
        def _default_exec(spec, body):
            return f"<{spec.name}>{body[:80]}</{spec.name}>"

        team_dir = self.team_dir_root / name
        lead = LeadSession.create(
            team_name=name,
            team_dir=team_dir,
            executor=_default_exec,
        )
        self._teams[name] = lead
        return lead

    def spawn(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.teams import TeammateSpec

        team = str(params.get("team", "")).strip()
        name = str(params.get("name", "")).strip()
        model = str(params.get("model", "smart")).strip() or "smart"
        if not team or not name:
            raise AcpError(-32602, "spawn requires team + name")
        lead = self._resolve_team(team)
        try:
            lead.spawn(TeammateSpec(name=name, model=model))
        except Exception as e:  # noqa: BLE001
            raise AcpError(-32602, f"spawn failed: {e}")
        return {"team": team, "spawned": list(lead.teammates)}

    def add_task(self, params: Mapping[str, Any]) -> dict[str, Any]:
        team = str(params.get("team", "")).strip()
        title = str(params.get("title", "")).strip()
        assign = params.get("assign")
        depends_on = params.get("depends_on") or []
        body = str(params.get("body", ""))
        if not team or not title:
            raise AcpError(-32602, "add_task requires team + title")
        lead = self._resolve_team(team)
        try:
            tid = lead.add_task(
                title,
                assign=assign,
                depends_on=depends_on,
                body=body,
            )
        except Exception as e:  # noqa: BLE001
            raise AcpError(-32602, f"add_task failed: {e}")
        return {"team": team, "task_id": tid}

    def run_until_idle(self, params: Mapping[str, Any]) -> dict[str, Any]:
        team = str(params.get("team", "")).strip()
        timeout_s = float(params.get("timeout_s") or 60.0)
        if not team:
            raise AcpError(-32602, "run requires team")
        lead = self._resolve_team(team)
        completed = lead.run_until_idle(timeout_s=timeout_s)
        return {"team": team, "completed": completed}

    def report(self, params: Mapping[str, Any]) -> dict[str, Any]:
        team = str(params.get("team", "")).strip()
        if not team:
            raise AcpError(-32602, "report requires team")
        lead = self._resolve_team(team)
        return lead.shutdown().as_dict()

    def mailbox(self, params: Mapping[str, Any]) -> dict[str, Any]:
        team = str(params.get("team", "")).strip()
        recipient = str(params.get("recipient", "lead")).strip() or "lead"
        if not team:
            raise AcpError(-32602, "mailbox requires team")
        lead = self._resolve_team(team)
        msgs = lead.mailbox.read(recipient)
        return {
            "team": team,
            "recipient": recipient,
            "count": len(msgs),
            "messages": [
                {
                    "from": m.sender,
                    "kind": m.kind,
                    "body": m.body,
                    "created_at": m.created_at,
                }
                for m in msgs[-50:]  # cap
            ],
        }

    # ---- /bundle ------------------------------------------------

    def bundle_info(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import SourceBundle

        path = self._require_path(params, "path")
        try:
            b = SourceBundle.load(path)
            b.validate()
        except Exception as e:  # noqa: BLE001
            raise AcpError(-32602, f"bundle.info failed: {e}")
        return b.summary()

    def bundle_install(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import AgentInstaller, SourceBundle

        path = self._require_path(params, "path")
        target_dir = params.get("target_dir") or str(
            Path.home() / ".lyra" / "bundles" / Path(path).parent.name
        )
        allow_dual_use = bool(params.get("allow_dual_use", False))
        authorized_by = params.get("authorized_by")
        try:
            b = SourceBundle.load(path)
            inst = AgentInstaller(bundle=b)
            att = inst.install(
                target_dir=target_dir,
                allow_dual_use=allow_dual_use,
                authorized_by=authorized_by,
            )
        except Exception as e:  # noqa: BLE001
            raise AcpError(-32602, f"bundle.install failed: {e}")
        return {
            "name": att.bundle_name,
            "version": att.bundle_version,
            "hash": att.bundle_hash,
            "smoke_eval_pass_rate": att.smoke_eval_pass_rate,
            "target_dir": att.target_dir,
            "dual_use": att.dual_use,
            "authorized_by": att.authorized_by,
        }

    def bundle_trust(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import MarketplaceKey

        marketplace = str(params.get("marketplace") or "").strip()
        fingerprint = str(params.get("fingerprint") or "").strip()
        secret_hex = str(params.get("secret_hex") or "").strip()
        if not marketplace or not fingerprint or not secret_hex:
            raise AcpError(
                -32602, "trust requires marketplace + fingerprint + secret_hex"
            )
        try:
            secret = bytes.fromhex(secret_hex)
        except ValueError as e:
            raise AcpError(-32602, f"secret_hex invalid: {e}")
        self._marketplace().trust(
            marketplace, MarketplaceKey(fingerprint=fingerprint, secret=secret)
        )
        return {"trusted": marketplace, "fingerprint": fingerprint}

    def bundle_fetch(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import FetchSpec, MarketplaceFetcher

        url = str(params.get("url") or "").strip()
        signature = str(params.get("signature") or "").strip()
        marketplace = str(params.get("marketplace") or "").strip()
        expected_hash = params.get("expected_hash")
        if not url or not signature or not marketplace:
            raise AcpError(-32602, "fetch requires url + signature + marketplace")
        fetcher = MarketplaceFetcher(registry=self._marketplace())
        try:
            fetched = fetcher.fetch(
                FetchSpec(
                    url=url, expected_signature=signature,
                    marketplace=marketplace, expected_hash=expected_hash,
                )
            )
        except Exception as e:
            raise AcpError(-32602, f"fetch failed: {e}")
        return {
            "bundle_name": fetched.bundle.manifest.name,
            "bundle_version": fetched.bundle.manifest.version,
            "cache_path": fetched.sbom.cache_path,
            "signing_key_fingerprint": fetched.sbom.signing_key_fingerprint,
        }

    def bundle_list(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import global_installed_registry

        rows = global_installed_registry().all()
        return {
            "installed": [
                {
                    "bundle_name": r.bundle_name,
                    "bundle_version": r.bundle_version,
                    "bundle_hash": r.bundle_hash,
                    "target_dir": r.target_dir,
                    "verifier_domain": r.verifier_domain,
                    "dual_use": r.dual_use,
                    "authorized_by": r.authorized_by,
                    "installed_at": r.installed_at,
                    "last_verified_at": r.last_verified_at,
                }
                for r in rows
            ]
        }

    def bundle_uninstall(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import uninstall_bundle

        bundle_hash = str(params.get("bundle_hash") or "").strip()
        target_dir = str(params.get("target_dir") or "").strip()
        verify = bool(params.get("verify_attestation_first", True))
        if not bundle_hash or not target_dir:
            raise AcpError(-32602, "uninstall requires bundle_hash + target_dir")
        try:
            removed = uninstall_bundle(
                bundle_hash=bundle_hash,
                target_dir=target_dir,
                verify_attestation_first=verify,
            )
        except Exception as e:
            raise AcpError(-32602, f"uninstall failed: {e}")
        return {
            "removed_name": removed.bundle_name,
            "removed_version": removed.bundle_version,
            "removed_target_dir": removed.target_dir,
        }

    def bundle_export(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import SourceBundle, list_exporters, resolve_exporter

        path = self._require_path(params, "path")
        target = str(params.get("target", "")).strip()
        target_dir = params.get("target_dir") or str(
            Path.home() / f".lyra-export-{target}"
        )
        if target not in list_exporters():
            raise AcpError(
                -32602, f"unknown target {target!r}; one of {sorted(list_exporters())}"
            )
        try:
            b = SourceBundle.load(path)
            exporter = resolve_exporter(target)  # type: ignore[arg-type]
            manifest = exporter.export(b, target=Path(target_dir))
        except Exception as e:  # noqa: BLE001
            raise AcpError(-32602, f"bundle.export failed: {e}")
        return {
            "target": target,
            "target_dir": str(manifest.target_root),
            "files_emitted": len(manifest.files),
        }

    # ---- /scaling + /coverage -----------------------------------

    def scaling_snapshot(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.meta import ScalingAxes

        sa = ScalingAxes()
        # Apply caller-supplied overrides if present.
        if (p := params.get("pretrain")) is not None:
            sa.record_pretrain(
                model=str(p.get("model", "auto")),
                param_b=float(p.get("param_b", 0.0)),
                quality=p.get("quality"),
            )
        if (t := params.get("ttc")) is not None:
            sa.record_ttc(
                max_samples=int(t.get("max_samples", 1)),
                verifier_count=int(t.get("verifier_count", 0)),
                avg_pass_rate=float(t.get("avg_pass_rate", 0.0)),
            )
        if (m := params.get("memory")) is not None:
            sa.record_memory(
                context_tokens=int(m.get("context_tokens", 0)),
                tier_count=int(m.get("tier_count", 1)),
                retrieval_score=float(m.get("retrieval_score", 0.0)),
            )
        if (u := params.get("tool_use")) is not None:
            sa.record_tool_use(
                native_count=int(u.get("native_count", 0)),
                mcp_server_count=int(u.get("mcp_server_count", 0)),
                avg_success_rate=float(u.get("avg_success_rate", 0.0)),
            )
        snap = sa.snapshot()
        best = sa.best_lever()
        return {
            "axes": [
                {
                    "axis": p.axis,
                    "score": p.score,
                    "current": p.current,
                    "next_lever": p.next_lever,
                    "cost_hint": p.cost_hint,
                    "benefit_hint": p.benefit_hint,
                    "cost_benefit": p.cost_benefit,
                }
                for p in snap
            ],
            "best_lever": best.axis,
        }

    def coverage_snapshot(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from lyra_core.bundle import global_index

        idx = global_index()
        rows = []
        for c in idx.all():
            rows.append({
                "domain": c.domain,
                "verifier_count": c.verifier_count,
                "verifier_ids": list(c.verifier_ids),
                "eval_count": c.eval_count,
                "pass_rate_30d": c.pass_rate_30d,
                "coverage_score": c.coverage_score,
                "admit_recommendation": c.admit_recommendation,
            })
        return {"domains": rows}

    # ---- helpers ------------------------------------------------

    @staticmethod
    def _require_path(params: Mapping[str, Any], key: str) -> str:
        v = params.get(key)
        if not v:
            raise AcpError(-32602, f"missing required param: {key}")
        return str(v)


__all__ = ["register_v311_methods"]
