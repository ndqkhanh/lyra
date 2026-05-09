"""v3.11 slash commands — ``/team``, ``/scaling``, ``/coverage``, ``/bundle``.

These four commands surface the v3.11 capabilities (Anthropic Agent
Teams runtime, four-axis scaling aggregator, verifier-coverage index,
Software 3.0 bundle install + export) as user-facing REPL operations.

Pattern: every handler matches the existing ``SlashHandler`` contract
``(InteractiveSession, args: str) -> CommandResult`` so they slot into
``COMMAND_REGISTRY`` next to ``/skills``, ``/cron``, etc.

The handlers stay deliberately thin — heavy lifting lives in
:mod:`lyra_core.teams`, :mod:`lyra_core.bundle`, and
:mod:`lyra_core.meta`. The CLI surface is *display + dispatch*, not
business logic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---- result type proxy -----------------------------------------------
#
# We deliberately import lazily (and accept Any) so this module can be
# unit-tested in isolation without dragging in the full session.py
# import chain.


@dataclass
class _StubResult:
    """Test-only stub mirroring ``CommandResult``'s public attribute set."""

    output: str = ""
    renderable: Any | None = None
    should_exit: bool = False
    clear_screen: bool = False
    new_mode: str | None = None


def _result_class() -> type:
    try:
        from .session import CommandResult  # type: ignore
        return CommandResult
    except Exception:
        return _StubResult


def _ok(text: str) -> Any:
    return _result_class()(output=text)


# ---- /team -----------------------------------------------------------
#
# Subcommands:
#   /team list          — show registered teams (and per-team summary)
#   /team spawn <name>  — spawn a teammate into the current team
#   /team mailbox [name] — show messages addressed to <name> or 'lead'
#   /team report        — current team's TeamReport snapshot
#   /team help          — usage


_TEAM_HELP = """\
/team — Anthropic Agent Teams runtime (v3.11 L311-1).

  /team list                     show registered teams
  /team status                   current team summary (spawned, tasks, mailbox)
  /team spawn <name> [model]     spawn a teammate into the current team
  /team add-task <title>         add a task to the shared list
  /team mailbox [recipient]      read mailbox (default: lead)
  /team report                   final TeamReport snapshot
  /team help                     this message

Teams coordinate through a filesystem-backed shared task list and
per-recipient mailboxes under ~/.lyra/teams/{name}/. Three new hook
events fire: team.task_created, team.task_completed, team.teammate_idle.
"""


def cmd_team(session: Any, args: str) -> Any:
    raw = (args or "").strip()
    if not raw or raw == "help":
        return _ok(_TEAM_HELP)
    parts = raw.split(maxsplit=1)
    sub = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    lead = _resolve_lead(session)

    if sub == "list":
        if lead is None:
            return _ok("No team registered for this session. Use /team spawn to create one.")
        names = ", ".join(lead.teammates) or "—"
        return _ok(
            f"team={lead.team_name} mode={lead.mode} "
            f"teammates=[{names}]"
        )

    if sub == "status":
        if lead is None:
            return _ok("No team registered. /team spawn <name> to create one.")
        snap = lead.tasks.summary()
        msgs = lead.mailbox.message_count()
        return _ok(
            f"team={lead.team_name}\n"
            f"  spawned: {', '.join(lead.teammates) or '—'}\n"
            f"  tasks:   pending={snap.pending} in_progress={snap.in_progress} "
            f"completed={snap.completed} blocked={snap.blocked}\n"
            f"  mailbox: {msgs} messages\n"
            f"  warn_cost: {lead.warn_cost}"
        )

    if sub == "spawn":
        if not rest:
            return _ok("Usage: /team spawn <name> [model]")
        spawn_parts = rest.split()
        name = spawn_parts[0]
        model = spawn_parts[1] if len(spawn_parts) > 1 else "smart"
        if lead is None:
            lead = _create_default_lead(session)
        from lyra_core.teams import TeammateSpec
        try:
            lead.spawn(TeammateSpec(name=name, model=model))
        except Exception as e:
            return _ok(f"spawn failed: {e}")
        return _ok(f"spawned teammate={name} model={model}")

    if sub == "add-task":
        if lead is None:
            return _ok("No team registered. /team spawn first.")
        if not rest:
            return _ok("Usage: /team add-task <title>")
        try:
            tid = lead.add_task(rest)
        except Exception as e:
            return _ok(f"add-task failed: {e}")
        return _ok(f"task added: {tid}")

    if sub == "mailbox":
        if lead is None:
            return _ok("No team registered.")
        recipient = rest.strip() or "lead"
        msgs = lead.mailbox.read(recipient)
        if not msgs:
            return _ok(f"mailbox[{recipient}] empty")
        lines = [f"mailbox[{recipient}] ({len(msgs)} messages):"]
        for m in msgs[-10:]:
            lines.append(f"  [{m.kind}] from={m.sender}: {m.body[:80]}")
        return _ok("\n".join(lines))

    if sub == "report":
        if lead is None:
            return _ok("No team registered.")
        report = lead.shutdown()
        return _ok(json.dumps(report.as_dict(), indent=2))

    return _ok(f"unknown /team subcommand {sub!r}; try /team help")


# ---- /scaling --------------------------------------------------------


_SCALING_HELP = """\
/scaling — Four-axis scaling-laws aggregator (v3.11 L311-7).

  /scaling                show position on every axis + best-lever pick
  /scaling axis <name>    detail for one axis (pretrain|ttc|memory|tool_use)
  /scaling help           this message

Operationalizes Karpathy's verifier-density framing: the aggregator
ranks the four scaling axes by cost/benefit so the operator can
choose the next investment grounded in evidence, not vibes.
"""


def cmd_scaling(session: Any, args: str) -> Any:
    raw = (args or "").strip()
    if raw == "help":
        return _ok(_SCALING_HELP)
    sa = _resolve_scaling_axes(session)
    if not raw:
        from lyra_core.meta import render_scaling_table
        snap = sa.snapshot()
        best = sa.best_lever()
        return _ok(
            render_scaling_table(snap)
            + f"\n\nbest lever: {best.axis} — {best.next_lever}"
        )
    parts = raw.split(maxsplit=1)
    if parts[0] == "axis" and len(parts) > 1:
        target = parts[1].strip()
        for p in sa.snapshot():
            if p.axis == target:
                return _ok(
                    f"axis={p.axis}\n"
                    f"  score={p.score:.2f}\n"
                    f"  current={p.current}\n"
                    f"  next_lever={p.next_lever}\n"
                    f"  cost={p.cost_hint:.2f} benefit={p.benefit_hint:.2f} "
                    f"cost_benefit={p.cost_benefit:.2f}"
                )
        return _ok(
            f"unknown axis {target!r}; one of: pretrain, ttc, memory, tool_use"
        )
    return _ok(_SCALING_HELP)


# ---- /coverage -------------------------------------------------------


_COVERAGE_HELP = """\
/coverage — Verifier-coverage index per task domain (v3.11 L311-6).

  /coverage              snapshot of every domain registered
  /coverage <domain>     detail for one domain
  /coverage help         this message

Operationalizes the verifier-density framing as an admit signal —
domains with score ≥0.7 default to edit_automatically, 0.4-0.7 to
ask_before_edits, <0.4 to plan_mode.
"""


def cmd_coverage(session: Any, args: str) -> Any:
    raw = (args or "").strip()
    if raw == "help":
        return _ok(_COVERAGE_HELP)
    idx = _resolve_coverage_index(session)
    if not raw:
        rows = idx.all()
        if not rows:
            return _ok("No domains registered. Coverage index is empty.")
        lines = ["domain               | verifs | evals | pass30 | score | admit"]
        lines.append("---------------------|--------|-------|--------|-------|------")
        for c in rows:
            lines.append(
                f"{c.domain[:20]:<20} | {c.verifier_count:>6} "
                f"| {c.eval_count:>5} | {c.pass_rate_30d:>5.2f} "
                f"| {c.coverage_score:>5.2f} | {c.admit_recommendation}"
            )
        return _ok("\n".join(lines))
    cov = idx.get(raw)
    return _ok(
        f"domain={cov.domain}\n"
        f"  verifiers: {cov.verifier_count} ({list(cov.verifier_ids)})\n"
        f"  evals:     {cov.eval_count}\n"
        f"  pass30d:   {cov.pass_rate_30d:.2f}\n"
        f"  score:     {cov.coverage_score:.2f}\n"
        f"  admit:     {cov.admit_recommendation}"
    )


# ---- /bundle ---------------------------------------------------------


_BUNDLE_HELP = """\
/bundle — Software 3.0 bundle pipeline (v3.11 L311-4/5/9).

  /bundle info <path>                load + validate a bundle
  /bundle install <path> [target]    install with smoke-eval gate
  /bundle export <path> <target>     emit cross-harness view
  /bundle list                       show every installed bundle
  /bundle uninstall <hash> <target>  remove + verify-attestation
  /bundle help                       this message

Targets for export: claude-code, cursor, codex, gemini-cli.
Bundles ship under projects/<name>/bundle/ in this repo; install
fails closed if smoke-eval falls below the bundle's threshold
(default 0.95, LBL-AI-EVAL).
"""


def cmd_bundle(session: Any, args: str) -> Any:
    raw = (args or "").strip()
    if not raw or raw == "help":
        return _ok(_BUNDLE_HELP)
    parts = raw.split(maxsplit=2)
    sub = parts[0]
    if sub == "info":
        if len(parts) < 2:
            return _ok("Usage: /bundle info <path>")
        path = Path(parts[1])
        try:
            from lyra_core.bundle import SourceBundle
            b = SourceBundle.load(path)
            b.validate()
        except Exception as e:
            return _ok(f"info failed: {e}")
        return _ok(json.dumps(b.summary(), indent=2))

    if sub == "install":
        if len(parts) < 2:
            return _ok("Usage: /bundle install <path> [target_dir]")
        bundle_path = Path(parts[1])
        target_dir = (
            Path(parts[2])
            if len(parts) > 2
            else Path.home() / ".lyra" / "bundles"
                 / bundle_path.parent.name
        )
        try:
            from lyra_core.bundle import AgentInstaller, SourceBundle

            b = SourceBundle.load(bundle_path)
            inst = AgentInstaller(bundle=b)
            att = inst.install(target_dir=target_dir)
        except Exception as e:
            return _ok(f"install failed: {e}")
        return _ok(
            f"installed: name={att.bundle_name} version={att.bundle_version}\n"
            f"  hash={att.bundle_hash[:16]}\n"
            f"  smoke_eval: pass={att.smoke_eval_pass} fail={att.smoke_eval_fail} "
            f"rate={att.smoke_eval_pass_rate:.2f}\n"
            f"  target_dir={att.target_dir}"
        )

    if sub == "export":
        if len(parts) < 3:
            return _ok(
                "Usage: /bundle export <path> <claude-code|cursor|codex|gemini-cli>"
            )
        bundle_path = Path(parts[1])
        target = parts[2].strip()
        try:
            from lyra_core.bundle import SourceBundle, resolve_exporter
            b = SourceBundle.load(bundle_path)
            exporter = resolve_exporter(target)  # type: ignore[arg-type]
            target_dir = Path.home() / f".lyra-export-{target}"
            manifest = exporter.export(b, target=target_dir)
        except Exception as e:
            return _ok(f"export failed: {e}")
        return _ok(
            f"exported: target={target}\n"
            f"  files emitted: {len(manifest.files)}\n"
            f"  target_dir: {target_dir}"
        )

    if sub == "list":
        try:
            from lyra_core.bundle import global_installed_registry

            reg = global_installed_registry()
            rows = reg.all()
        except Exception as e:
            return _ok(f"list failed: {e}")
        if not rows:
            return _ok("No bundles installed. /bundle install <path> to install one.")
        lines = ["installed bundles:"]
        lines.append("name                  | version  | domain        | dual | hash             | target_dir")
        lines.append("----------------------|----------|---------------|------|------------------|----------")
        for r in rows:
            dual = "yes" if r.dual_use else "no"
            short_hash = r.bundle_hash[:16]
            lines.append(
                f"{r.bundle_name[:21]:<21} | {r.bundle_version[:8]:<8} "
                f"| {r.verifier_domain[:13]:<13} | {dual:<4} "
                f"| {short_hash} | {r.target_dir}"
            )
        return _ok("\n".join(lines))

    if sub == "fetch":
        # parts is split with maxsplit=2: [sub, arg1, "rest"].
        # Need to re-split rest manually.
        if len(parts) < 3:
            return _ok(
                "Usage: /bundle fetch <url> <signature_hex> <marketplace>\n"
                "  Use /bundle trust <marketplace> <fingerprint> <secret_hex> first."
            )
        rest_parts = (parts[1] + " " + parts[2]).split()
        if len(rest_parts) < 3:
            return _ok(
                "Usage: /bundle fetch <url> <signature_hex> <marketplace>"
            )
        url, signature, marketplace = rest_parts[0], rest_parts[1], rest_parts[2]
        try:
            from lyra_core.bundle import FetchSpec, MarketplaceFetcher

            registry = _resolve_marketplace_registry(session)
            fetcher = MarketplaceFetcher(registry=registry)
            fetched = fetcher.fetch(
                FetchSpec(
                    url=url, expected_signature=signature, marketplace=marketplace
                )
            )
        except Exception as e:
            return _ok(f"fetch failed: {e}")
        return _ok(
            f"fetched: name={fetched.bundle.manifest.name} "
            f"version={fetched.bundle.manifest.version}\n"
            f"  marketplace={marketplace}\n"
            f"  cache_path={fetched.sbom.cache_path}\n"
            f"  next: /bundle install {fetched.sbom.cache_path}"
        )

    if sub == "trust":
        if len(parts) < 3:
            return _ok(
                "Usage: /bundle trust <marketplace> <fingerprint> <secret_hex>"
            )
        rest_parts = (parts[1] + " " + parts[2]).split()
        if len(rest_parts) < 3:
            return _ok(
                "Usage: /bundle trust <marketplace> <fingerprint> <secret_hex>"
            )
        marketplace, fingerprint, secret_hex = (
            rest_parts[0], rest_parts[1], rest_parts[2]
        )
        try:
            from lyra_core.bundle import MarketplaceKey

            registry = _resolve_marketplace_registry(session)
            registry.trust(
                marketplace,
                MarketplaceKey(
                    fingerprint=fingerprint,
                    secret=bytes.fromhex(secret_hex),
                ),
            )
        except Exception as e:
            return _ok(f"trust failed: {e}")
        return _ok(
            f"trusted marketplace={marketplace} fingerprint={fingerprint}"
        )

    if sub == "uninstall":
        if len(parts) < 3:
            return _ok("Usage: /bundle uninstall <hash> <target_dir>")
        bundle_hash = parts[1].strip()
        target = Path(parts[2])
        try:
            from lyra_core.bundle import (
                global_installed_registry,
                uninstall_bundle,
            )
            # If the user supplied a short hash prefix, expand it.
            reg = global_installed_registry()
            if len(bundle_hash) < 64:
                matches = [
                    r for r in reg.all()
                    if r.bundle_hash.startswith(bundle_hash)
                ]
                if len(matches) == 0:
                    return _ok(f"no installed bundle matches hash prefix {bundle_hash!r}")
                if len(matches) > 1:
                    return _ok(
                        f"hash prefix {bundle_hash!r} matches {len(matches)} bundles; "
                        "supply more characters"
                    )
                bundle_hash = matches[0].bundle_hash
            removed = uninstall_bundle(bundle_hash=bundle_hash, target_dir=target)
        except Exception as e:
            return _ok(f"uninstall failed: {e}")
        return _ok(
            f"uninstalled: name={removed.bundle_name} version={removed.bundle_version}\n"
            f"  removed_dir={removed.target_dir}"
        )

    return _ok(f"unknown /bundle subcommand {sub!r}; try /bundle help")


# ---- session-state resolvers -----------------------------------------


def _resolve_lead(session: Any):
    return getattr(session, "_v311_lead", None)


def _create_default_lead(session: Any):
    """Create a default :class:`LeadSession` for the REPL.

    Tries to wire a real LLM-backed executor first via
    :func:`_resolve_real_executor`. If that fails (no LLM connected,
    no AgentLoop available, mock mode, etc.), falls back to a
    deterministic stub so the runtime still works in `--llm mock` and
    test environments.
    """
    from lyra_core.teams import LeadSession

    executor = _resolve_real_executor(session) or _default_stub_executor

    team_dir = Path.home() / ".lyra" / "teams" / "session"
    team_dir.mkdir(parents=True, exist_ok=True)
    lead = LeadSession.create(
        team_name="session",
        team_dir=team_dir,
        executor=executor,
    )
    setattr(session, "_v311_lead", lead)
    return lead


def _default_stub_executor(spec, body):
    """Deterministic fallback when no LLM is wired."""
    return f"<{spec.name}>{body[:80]}</{spec.name}>"


def _resolve_real_executor(session: Any) -> Any:
    """Best-effort: build an :class:`AgentLoopExecutor` over the
    session's actual LLM. Returns ``None`` on any failure (no
    connected LLM, no factory, mock mode) so callers can fall back to
    the stub without raising.

    The factory pattern: every spawned teammate gets a *fresh*
    :class:`AgentLoop` so contexts stay isolated. Each loop binds to
    the LLM the session is currently configured with — same provider,
    same model slot the user already chose.
    """
    try:
        from lyra_core.agent.loop import AgentLoop, IterationBudget
        from lyra_core.teams import AgentLoopExecutor
    except Exception:
        return None

    llm = getattr(session, "llm", None) or getattr(session, "_llm", None)
    tools = (
        getattr(session, "tools", None)
        or getattr(session, "_tools", None)
        or {}
    )
    store = (
        getattr(session, "store", None)
        or getattr(session, "_store", None)
    )
    if llm is None or store is None:
        return None

    def loop_factory(spec):
        return AgentLoop(
            llm=llm,
            tools=tools,
            store=store,
            plugins=[],
            budget=IterationBudget(max=8),
        )

    return AgentLoopExecutor(loop_factory=loop_factory)


def _resolve_scaling_axes(session: Any):
    sa = getattr(session, "_v311_scaling", None)
    if sa is None:
        from lyra_core.meta import ScalingAxes

        sa = ScalingAxes()
        # Reasonable defaults for a fresh session — caller can override.
        sa.record_pretrain(model="auto", param_b=70.0, quality=0.85)
        sa.record_ttc(max_samples=1, verifier_count=2, avg_pass_rate=0.7)
        sa.record_memory(context_tokens=200_000, tier_count=2, retrieval_score=0.7)
        sa.record_tool_use(
            native_count=10, mcp_server_count=3, avg_success_rate=0.85
        )
        setattr(session, "_v311_scaling", sa)
    return sa


def _resolve_marketplace_registry(session: Any):
    """Per-session marketplace registry. Defaults to a fresh empty one
    so callers must explicitly trust a marketplace before fetching —
    matches `LBL-FETCH-VERIFY` discipline."""
    reg = getattr(session, "_v311_marketplace", None)
    if reg is None:
        from lyra_core.bundle import MarketplaceRegistry

        reg = MarketplaceRegistry()
        setattr(session, "_v311_marketplace", reg)
    return reg


def _resolve_coverage_index(session: Any):
    """Resolve the coverage index for the session.

    Default to the process-wide :func:`lyra_core.bundle.global_index`
    singleton so installed bundles surface automatically. Tests can
    override by setting ``session._v311_coverage`` to a fresh
    :class:`VerifierCoverageIndex` instance before calling the slash.
    """
    idx = getattr(session, "_v311_coverage", None)
    if idx is None:
        try:
            from lyra_core.bundle import global_index

            idx = global_index()
        except Exception:
            from lyra_core.bundle import VerifierCoverageIndex
            idx = VerifierCoverageIndex()
        setattr(session, "_v311_coverage", idx)
    return idx


__all__ = [
    "cmd_bundle",
    "cmd_coverage",
    "cmd_scaling",
    "cmd_team",
]
