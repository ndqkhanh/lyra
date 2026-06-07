# Claude Code Environment Variables Reference (Anthropic / Claude Code Docs)

**URL:** https://code.claude.com/docs/en/env-vars
**Source:** Anthropic (Claude Code product documentation)
**Date:** No explicit date on page; part of live docs corpus at code.claude.com

---

## Key Technical Claims

1. **Multi-layer configuration precedence:** Environment variables override `settings.json` fields; CLI flags and in-session commands can override env vars (varies per feature). The specific rule: ENV > settings field, but `--model` and `/model` override `ANTHROPIC_MODEL`, while `CLAUDE_CODE_EFFORT_LEVEL` overrides `/effort`.

2. **Startup-only reading:** All environment variables are read at launch. Changing them mid-session requires a full `claude` relaunch. This is a deliberate architectural constraint -- it avoids mid-session state drift.

3. **Dual auth paths:** The system supports API key (`ANTHROPIC_API_KEY`), OAuth token (`CLAUDE_CODE_OAUTH_TOKEN`), subscription-based auth (Claude Pro/Max/Team/Enterprise), and provider-specific auth for AWS Bedrock, GCP Vertex AI, and Microsoft Foundry. Each auth method has its own set of env vars.

4. **Feature flag pattern:** A large family of `CLAUDE_CODE_DISABLE_*` and `CLAUDE_CODE_ENABLE_*` variables toggle experimental or optional features. Examples: `DISABLE_AGENT_VIEW`, `DISABLE_BACKGROUND_TASKS`, `DISABLE_WORKFLOWS`, `ENABLE_AUTO_MODE`, `ENABLE_TASKS`.

5. **Subprocess detection:** The `CLAUDECODE` env var is set to `1` in every subprocess (Bash, PowerShell, tmux, hooks, status line commands, stdio MCP servers). This allows child scripts to detect they are running inside Claude Code.

6. **Non-first-party detection:** When `ANTHROPIC_BASE_URL` points to a non-Anthropic host (proxy/gateway), certain features like MCP tool search are disabled by default. Explicit opt-in via `ENABLE_TOOL_SEARCH=true` is required if the proxy forwards `tool_reference` blocks.

7. **Settings file scoping:** Four layers of settings files with increasing specificity: user-global (`~/.claude/settings.json`), project-shared (`.claude/settings.json`, source-controlled), project-local (`.claude/settings.local.json`, gitignored), and managed settings (admin-deployed org-wide).

8. **Sanitized MCP server environment:** `CLAUDE_CODE_MCP_ALLOWLIST_ENV` spawns stdio MCP servers with only a safe baseline environment plus the server's configured `env`, rather than inheriting the full shell environment. This is a security hardening pattern for third-party tool plugins.

---

## Architecture/Mechanism Details

- **Auth routing:** Variables for four separate backends (Anthropic API, AWS Bedrock, GCP Vertex AI, Microsoft Foundry) each with distinct URL, project/workspace ID, and credential variables. The system selects the active backend based on which variables are set.

- **Compaction system:** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (default ~95%) controls when the context window triggers auto-compaction. Can be paired with `CLAUDE_CODE_AUTO_COMPACT_WINDOW` to set an artificial context capacity for compaction calculations (e.g., treat a 1M window as 500K). `CLAUDE_CODE_DISABLE_1M_CONTEXT` removes 1M model variants entirely. `CLAUDE_CODE_MAX_CONTEXT_TOKENS` overrides the assumed window size (only effective when compaction is also disabled).

- **Effort/thinking controls:** `CLAUDE_CODE_EFFORT_LEVEL` selects from low/medium/high/xhigh/max/auto. `CLAUDE_CODE_DISABLE_THINKING` force-disables extended thinking. `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` (relevant mainly for Opus 4.6/Sonnet 4.6) falls back to a fixed budget. `CLAUDE_CODE_MAX_OUTPUT_TOKENS` caps output length and indirectly affects compaction timing.

- **Background agents/teams:** `CLAUDE_CODE_DISABLE_AGENT_VIEW` removes all background agent functionality. `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` removes `run_in_background`, auto-backgrounding, and Ctrl+B. `CLAUDE_CODE_FORK_SUBAGENT` makes forked subagents the default (inheriting full conversation context). `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` enables multi-agent teams.

- **Plugin system:** `CLAUDE_CODE_PLUGIN_CACHE_DIR`, `CLAUDE_CODE_PLUGIN_SEED_DIR` (for read-only pre-populated plugins in containers), `CLAUDE_CODE_PLUGIN_PREFER_HTTPS` (for CI without SSH keys), and `CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE` (for offline/airgapped environments).

- **OTel telemetry:** `CLAUDE_CODE_ENABLE_TELEMETRY` enables OpenTelemetry data collection, with separate flush/shutdown timeout variables and dynamic header refresh. `CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL` routes session quality surveys to the org's own OTel collector when Anthropic-bound traffic is blocked.

- **Request customization:** `ANTHROPIC_BETAS` for opting into API betas, `ANTHROPIC_CUSTOM_HEADERS` for arbitrary headers, `CLAUDE_CODE_EXTRA_BODY` for provider-specific request body parameters, and `CLAUDE_CODE_ATTRIBUTION_HEADER` to omit the attribution block for improved prompt-cache hit rates through LLM gateways.

---

## Numbers & Benchmarks

| Variable | Default | Notes |
|---|---|---|
| `API_TIMEOUT_MS` | 600000 (10 min) | Max 2147483647; overflow causes immediate failure |
| `BASH_DEFAULT_TIMEOUT_MS` | 120000 (2 min) | Model-controlled timeout for bash |
| `BASH_MAX_TIMEOUT_MS` | 600000 (10 min) | Ceiling for model's bash timeout requests |
| `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` | 600000 (10 min) | Reset on each streaming progress event |
| `CLAUDE_CODE_GLOB_TIMEOUT_SECONDS` | 20s (most platforms), 60s (WSL) | File discovery timeout |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | 10 | Max parallel read-only tools + subagents |
| `CLAUDE_CODE_MAX_RETRIES` | 10 | API request retry count override |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | ~95% | Range 1-100; lower values compact earlier |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | Model default (200K or 1M) | Artificial cap for compaction calculations |
| `CLAUDE_CODE_OTEL_FLUSH_TIMEOUT_MS` | 5000 | OTel span flush |
| `CLAUDE_CODE_OTEL_SHUTDOWN_TIMEOUT_MS` | 2000 | OTel exporter finish; increase if metrics dropped |
| `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` | 120000 (2 min) | Git ops for plugin install/update |
| `CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS` | 1740000 (29 min) | Dynamic OTel header refresh interval |

No traditional benchmarks (latency, throughput) are present -- this is a configuration reference, not a performance evaluation.

---

## Transfer to Lyra

**One idea: Layered, scoped configuration with env-var override semantics.**

Claude Code's configuration architecture is a clean reference model for Lyra. The key patterns:

1. **Four scopes of config files** -- user-global, project-shared (source-controlled), project-private (local overrides, gitignored), and org-managed admin policy. Lyra should adopt this exact scoping: a base config in `~/.lyra/config.json`, a shared config at project root (checked in), a `.local` override (gitignored), and an admin-deployed org policy.

2. **Environment variable overrides for every setting** -- Every `settings.json` field has a corresponding env var that takes precedence. Every field name maps to `CLAUDE_CODE_UPPER_SNAKE_CASE` of the setting path. Lyra should adopt the same: every config knob (model, timeout, effort, feature toggle) should have a `LYRA_*` env var analog.

3. **Startup-only reading with explicit relaunch** -- This avoids runtime state complexity. Lyra's configuration loader should read once at startup and document that changes require restart, simplifying the state model.

4. **Feature flag DISABLE/ENABLE pairs** -- The `CLAUDE_CODE_DISABLE_*` / `CLAUDE_CODE_ENABLE_*` pattern is clean and discoverable. Lyra should standardize on `LYRA_ENABLE_*` (opt-in) for experimental features and `LYRA_DISABLE_*` (opt-out) for stable ones.

5. **Subprocess environment injection** -- Setting `LYRA=1` in all spawned subprocesses gives child processes awareness of their parent, enabling integration scripts to behave differently when run inside Lyra.

**Workstream route:** This maps to **Section 4.6 (Configuration and DevOps)** of the Lyra upgrade plan. The layered config file scoping + env var override semantics directly supports the deployment and team-scale adoption goals of §4.6. Additionally, the `MCP_ALLOWLIST_ENV` security pattern belongs in **Section 4.7 (Safety and Security)** . The subprocess detection env var (`LYRA=1`) is a small operational hygiene improvement for **Section 4.9 (Tooling and SDK/API)** .
