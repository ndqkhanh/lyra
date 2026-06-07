# @chrysb/alphaclaw — Deep-Read

**npm:** `@chrysb/alphaclaw` v0.9.18
**git:** https://github.com/chrysb/alphaclaw (MIT)
**Role:** Ops + observability wrapper around OpenClaw. Browser-based setup UI, self-healing watchdog, gateway manager, channel integrations, anti-drift prompt hardening.

---

## 1. Headline Feature & Mechanism

**Headline:** "The ultimate OpenClaw harness. Deploy in minutes. Stay running for months." — a browser-based management layer that wraps OpenClaw with a Setup UI, self-healing watchdog, Git-backed rollback, and full observability, so manual SSH rescue missions are never needed.

**How it really works:**

AlphaClaw is a Node.js/Express server that runs as the parent process. It spawns `openclaw gateway run` as a managed child process (proxied on 127.0.0.1:18789) and exposes a browser UI on port 3000. The core mechanism is a **process supervisor** pattern:

- **`lib/server/gateway.js`**: Spawns OpenClaw via `child_process.spawn`, pipes stdout/stderr to the AlphaClaw log, tracks PID and exit codes. On `"listening on"` in stdout, fires a launch handler; on exit, fires `onGatewayExit` to the watchdog. Supports graceful restart (`SIGTERM` child, `openclaw gateway --force`), cold start, and light restart (via `openclaw gateway restart` CLI).
- **`lib/server/watchdog.js`**: A state machine with lifecycle states (`stopped`, `running`, `restarting`, `crashed`, `crash_loop`) and health states (`unknown`, `healthy`, `degraded`, `unhealthy`). Runs periodic health checks via HTTP GET to `localhost:18789/health`. On failure: transitions to "degraded", schedules accelerated 5s retries, triggers `openclaw doctor --fix --yes` if `WATCHDOG_AUTO_REPAIR=true`. Crash-loop detection: >=3 crashes in 300s window. Notifications via Telegram/Discord/Slack. Uses SQLite-backed event log.
- **`lib/server.js`**: Wires everything — Express app, `http-proxy` to gateway, route registration, signal handlers, database init (auth, webhooks, watchdog, usage, doctor).
- **Setup UI**: Preact + `htm` single-page app under `lib/public/js/`, built with esbuild. Divided into tabbed panes (General, Browse, Usage, Cron, Nodes, Watchdog, Providers, Envars, Webhooks).
- **Prompt Hardening**: `lib/setup/core-prompts/AGENTS.md` + `TOOLS.md` are injected into every agent message via gateway config. These enforce "Save and Show Your Work", "No YOLO system changes", "Plan Before You Build", persistent storage rules, and commit discipline.
- **Usage Tracker Plugin**: A first-party OpenClaw plugin (`lib/plugin/usage-tracker/index.js`) that hooks into `llm_output` and `tool_result_persist` events, writing to SQLite (`usage.db`) for the Usage UI dashboard.

---

## 2. Architecture & Core Modules

**Entry points:**
- `bin/alphaclaw.js` — CLI entrypoint. Parses args, resolves root directory, loads `.env`, creates directory structure, reconciles channels, starts Express server.
- `lib/server.js` — Server bootstrap. Initializes runtime, databases, creates Express app with middleware, wires all services, sets up WebSocket bridge, starts lifecycle.

**Core modules (357 source files, 84 test files):**

| Module | File(s) | Responsibility |
|---|---|---|
| Gateway Manager | `lib/server/gateway.js` | Spawn/monitor/restart `openclaw gateway run` as child process. Signal handlers, plugin preflight, MCP config injection |
| Watchdog | `lib/server/watchdog.js` | Health check state machine, crash detection, auto-repair, notification dispatch |
| Express Server | `lib/server.js` | App bootstrap, proxy setup, route registration, database init |
| Constants | `lib/server/constants.js` | All tunables: rate limits, watchdog thresholds, model catalog, channel defs, env var schemas, OAuth endpoints, Google Workspace API scopes |
| Doctor Service | `lib/server/doctor/service.js` | Runs `openclaw doctor --fix` programmatically, manages run/card lifecycle |
| Cron Service | `lib/server/cron-service.js` | Job scheduling, calendar rendering, run-history |
| Usage Tracker Plugin | `lib/plugin/usage-tracker/index.js` | OpenClaw-side plugin capturing token/usage data to SQLite |
| Setup UI | `lib/public/js/` | Preact+htm SPA, ~40 component files, esbuild bundle |
| Auth/Throttle | `lib/server/auth-profiles.js`, `login-throttle.js` | Password auth with exponential backoff lockout, API rate limiting |
| Channel integrations | `telegram-api.js`, `discord-api.js`, `slack-api.js` | Bot token management, topic registry, workspace sync |
| Webhooks | `webhook-middleware.js`, `db/webhooks.js` | Named endpoints, transform modules, request logging, OAuth callbacks |
| Google Workspace | `gmail-watch.js`, `gmail-push.js`, `gog-skill.js` | OAuth flow, Pub/Sub push, Google Workspace skill injection |
| Onboarding | `server/onboarding/` | Setup wizard (GitHub, provider creds, model selection, channel pairing) |
| Internal Files Migration | `server/internal-files-migration.js` | Managed file paths, hourly git sync script, backward compatibility |

**Data flow:**
```
Browser  --HTTPS-->  AlphaClaw (Express :3000)
                        |
                        |-- proxy --> OpenClaw gateway (child :18789)
                        |                `-> SQLite (/data/.openclaw/*.db)
                        |
                        |-- API routes --> JSON response
                        |-- WebSocket --> xterm terminal, chat session
                        |
Watchdog: Health check GET /health -> degrade -> doctor --fix -> restart
```

**State storage:** `ALPHACLAW_ROOT_DIR` (default `/data`):
- `/data/.openclaw/openclaw.json` — OpenClaw config (git-versioned)
- `/data/.env` — Secret environment variables
- `/data/.openclaw/workspace/` — Agent workspace (git-versioned)
- `/data/db/usage.db` — Usage tracker SQLite
- `/data/.openclaw/credentials/` — Channel pairing data
- `/data/.openclaw/cron/` — Cron job definitions

**Key dependencies:** Express ^4.21, http-proxy ^1.18.1, openclaw 2026.5.28, ws ^8.19. Dev: Preact, htm, esbuild, Tailwind, Vitest, Supertest, Chart.js, xterm.

---

## 3. Performance/Benchmarks

The README provides these concrete numbers:

- **440 tests** across 84 test files (full Vitest suite)
- **First deploy to first message in under five minutes** (target UX guarantee)
- **Watchdog health check interval:** configurable, default 120s
- **Watchdog degraded retry interval:** 5s (accelerated when health is "degraded")
- **Crash-loop detection:** 3 crashes within 300s window triggers crash_loop lifecycle
- **Health check timeout:** 5s per probe
- **Startup grace period:** 30s before health failures count
- **Startup retry threshold:** 3 consecutive failures before marking degraded
- **Max repair attempts:** 2 before auto-repair pauses
- **Log retention:** 30 days (watchdog), configurable via env vars
- **Log max bytes:** 2 MB per log file
- **Webhook payload max:** 50 KB (logged), 5 MB (raw body)
- **OpenAI compat API rate limits:** 10 attempts per window per client, 100 global
- **Login rate limits:** 5 attempts per 10min per client, 25 global

No formal latency/throughput benchmarks are provided, but the architecture is single-process Express proxying to a single OpenClaw child process — throughput is bounded by the gateway, not AlphaClaw itself.

---

## 4. Trade-offs (Wins vs Loses)

**Wins:**
- **Zero-config deploy:** One-click Railway/Render templates ship a complete stack — no manual gateway setup needed.
- **Self-healing:** Watchdog with crash-loop detection, auto-repair, and multi-channel notifications.
- **Anti-drift prompt hardening:** Injected AGENTS.md/TOOLS.md enforces agent discipline on every message — commits, planning, storage rules — without user configuration.
- **Browser-based everything:** No SSH, no CLI, no config file editing after the first deploy.
- **Ejectable:** AlphaClaw simply wraps OpenClaw; remove it and the agent keeps running unchanged.
- **Git sync:** Automatic hourly commits to GitHub with configurable cron. Combined with prompt hardening, every agent action is version-controlled.
- **Multi-agent management:** Sidebar-driven agent navigation, per-agent channel bindings, URL-driven selection.
- **Usage tracking:** First-party plugin captures LLM token usage and tool events to SQLite, visualized in the Usage UI.

**Loses / Known limitations (from README and code):**
- **Security trade-offs** (explicitly documented): Single setup-password model instead of OpenClaw's pairing-code flow; one-click pairing approval; auto CLI device pairing; query-string tokens for webhooks. "If you need OpenClaw's full security posture, use OpenClaw directly."
- **Express 4 vs 5 guardrails:** Container dependency tree can accidentally resolve express@5, causing body-parsing regressions. Requires careful template version pinning.
- **macOS local development not yet supported** — Docker/Linux only for production.
- **Platform-specific ports:** Port 18789 is reserved for the OpenClaw gateway; AlphaClaw will fatal-error if started on that port.
- **Railway Trial plan memory warning:** Needs >= 8 GB RAM (Hobby plan); Trial plan OOMs during normal operation.
- **Single-process scaling:** No horizontal scaling — all requests (UI, API, proxy, WebSocket) go through one Node.js process.
- **Update persistence on ephemeral containers:** Railway/Render ephemeral filesystems lose npm install on restart; workaround uses a persistent volume marker to re-run install.
- **No formal CHANGELOG** found in the repo; relies on GitHub releases for changelogs.
- **Single commit in history** (merge commit) — repo was likely squashed when made public.
- **Watcher constraints:** `GMAIL_WATCH_RENEWAL_INTERVAL` defaults to 6 hours; push notifications require Google Pub/Sub setup.

**From code analysis:**
- Watchdog state machine is in-memory only (no persistence across AlphaClaw restarts) — crash history resets if AlphaClaw itself restarts.
- Usage tracker plugin uses `node:sqlite` (Node 22+), which is synchronous — could block the event loop under heavy write load.
- Gateway restart can take up to 120s (timeout) during which the UI shows "Gateway unavailable".
- The `http-proxy` library is unmaintained (last release 2021); no updates for HTTP/2 or advanced proxy features.

---

## 5. Design Rationale

From CONTRIBUTING.md and README:

**"UX over features."** Every interaction should feel considered. The Setup UI replaces what would otherwise be CLI commands and config-file edits. The welcome wizard guides first-time users through the entire setup without documentation.

**"Smart defaults."** AlphaClaw is opinionated — it bootstraps hooks, prompt hardening, and sensible configs so the out-of-box experience is good without manual tuning. Examples: auto-injecting `WATCHDOG_AUTO_REPAIR` channel reconciliation from env vars, auto-registering the usage tracker plugin, injecting `trustedProxies` and `allowedOrigins` into the gateway config.

**"Complement, don't replicate."** OpenClaw's native dashboard is exhaustive. AlphaClaw surfaces the most common workflows and adds net-new value (watchdog, usage tracking, git sync, prompt hardening) rather than duplicating what OpenClaw already does.

**"Always ejectable."** AlphaClaw is not a dependency. Remove it and the OpenClaw instance keeps running. Nothing proprietary, nothing to migrate. The git sync ensures every agent action is version-controlled and portable.

**"Reliability is a feature."** The watchdog, auto-repair, crash-loop recovery, and notification channels are treated as first-class features, not afterthoughts. The state machine design with graceful startup periods, crash window tracking, and exponential backoff on repair reflects production operations experience.

**"One-click deploy, browser-based ops."** The core insight is that AI agent operators want to manage their infrastructure through a dashboard, not SSH. The entire architecture — Express proxy, watchdog, SQLite-backed state, automated git sync — exists to make the operator's job zero-touch after initial deployment.

---

## 6. Transfer to Lyra

**Transferable idea: Anti-drift prompt hardening via injected system prompts.**

AlphaClaw injects AGENTS.md and TOOLS.md into every agent message at the gateway level. These files encode behavioral rules: "Save and Show Your Work", "No YOLO System Changes", "Plan Before You Build", persistent storage conventions, commit discipline, and change-summary formatting. Because they are injected on every message (not just at session start), they resist drift — agents cannot "forget" the rules as context windows roll.

**Why this maps to Lyra:** Lyra needs a mechanism for persistent agent governance across sessions and context windows. A naive system prompt at session init is sufficient for first-message behavior, but degrades as context grows. AlphaClaw's approach — injecting governance prompts into every message at the gateway/proxy layer — is a provably more robust pattern.

**Specific mechanism to adopt:** A `systemPromptOverlay` or `governanceRules` injection point in Lyra's gateway/router that prepends a managed ruleset to every LLM API call. The ruleset would be a user-editable markdown file (like AGENTS.md) that is version-controlled via Lyra's workspace git sync. The router would read this file on every request and inject it as a `system` message before the user's messages. This is semantically different from a static system prompt — it applies to every turn, not just session init.

**Workstream route:** Section 4.x — Prompt Engineering & Agent Governance

**Impact:** Medium-High (7/10) — Directly improves agent reliability and adherence to behavioral rules. Lowers the risk of costly agent mistakes.

**Effort:** Low (3/10) — Implementation is a router-level change: add a stage in the LLM request pipeline that reads a governance file and prepends a system message. No new infrastructure, no new databases.

**Tier:** Tier 1 — High-value, low-effort, immediately deployable.

**LICENSE:** MIT — fully compatible with Lyra's licensing. Attribution required per MIT terms.

**Relevant file paths from source:**
- Anti-drift prompts: `lib/setup/core-prompts/AGENTS.md` and `lib/setup/core-prompts/TOOLS.md`
- Prompt injection mechanism: `lib/server/onboarding/workspace.js` (the `syncBootstrapPromptFiles` function)
- Gateway proxy: `lib/server/gateway.js` (where env/config flows into OpenClaw)
