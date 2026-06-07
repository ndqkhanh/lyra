# Configure the sandboxed Bash tool (code.claude.com/docs — Claude Code by Anthropic)

Source: https://code.claude.com/docs/en/sandboxing
Fetched: 2026-06-07

---

## Key Technical Claims

1. **Built-in OS-level sandbox for Bash subprocess isolation.** Every Bash command and its transitive child processes run inside an OS-enforced boundary. This is distinct from tool-level permission rules — sandboxing restricts what a process *can do once running*, not whether it runs at all.

2. **Filesystem isolation by default.** Write access is granted only to the current working directory and its subdirectories. Read access defaults to "the entire computer" (except certain denied directories), which notably *includes credential files* like `~/.aws/credentials` and `~/.ssh/`. These must be explicitly added to `denyRead` to block them.

3. **Network isolation via an outbound proxy.** No domains are pre-allowed. The first time a command needs a new domain, Claude Code prompts for approval. Domains can be pre-allowed via `allowedDomains` in settings. A managed lockdown (`allowManagedDomainsOnly`) makes unknown domains a hard block instead of a prompt.

4. **Two orthogonal layers: permission rules + sandbox + permission modes.** These are complementary, not redundant:
   - Permission rules control *which tools* Claude Code can invoke (Bash, Read, Edit, WebFetch, MCP).
   - Sandboxing controls *what Bash subprocesses can access* once running (OS-enforced, holds regardless of model behavior).
   - Permission modes control *whether tool calls run and whether you are prompted*.
   - The sandbox's "auto-allow mode" is separate from the general "auto mode" classifier.

5. **Managed settings can lock down the sandbox org-wide.** `failIfUnavailable` blocks startup if deps are missing; `allowUnsandboxedCommands: false` disables the escape hatch; `allowManagedDomainsOnly` / `allowManagedReadPathsOnly` prevent developers from widening the policy.

## Architecture/Mechanism Details

### OS enforcement primitives
| Platform | Mechanism |
|---|---|
| macOS | Seatbelt (built-in, no install) |
| Linux | bubblewrap + socat (must install) |
| WSL2 | bubblewrap (same as Linux) |
| Native Windows | Not supported |

### How filesystem isolation works
- **Default write:** only the CWD and its subdirectories.
- **Default read:** entire filesystem except certain denied paths. Credential dirs READABLE by default.
- **Git worktrees:** write access extended to the shared `.git/` directory of the main repo (except `hooks/` and `config`).
- **Configurable:** `allowWrite`, `denyWrite`, `denyRead`, `allowRead` in settings.
- **Scope merging:** arrays from user + project + local settings are concatenated (not replaced).
- **Path prefix conventions:** `/` = absolute, `~/` = home, `./` or bare = project-relative (in project settings) or `~/.claude/`-relative (in user settings). This differs from Read/Edit permission rules which use `//path` for absolute.

### How network isolation works
- A proxy server runs *outside* the sandbox boundary.
- The proxy enforces the allowlist based on the *requested hostname* (SNI / CONNECT host).
- The built-in proxy does **not** terminate or inspect TLS traffic. This means domain fronting attacks are possible if broad domains like `github.com` are allowed.
- Custom proxy configuration: `httpProxyPort`, `socksProxyPort` settings let you point at a corporate MITM proxy that terminates TLS.

### The escape hatch
When a command fails inside the sandbox, Claude Code may retry it with `dangerouslyDisableSandbox=true`. The retried command runs unsandboxed and goes through the regular permission flow (user must approve). This can be disabled by setting `"allowUnsandboxedCommands": false`.

### Managed settings lockdowns
- `failIfUnavailable`: hard block if deps missing (instead of warning+fallback)
- `allowUnsandboxedCommands: false`: ignore `dangerouslyDisableSandbox` entirely
- `allowManagedDomainsOnly`: only managed `allowedDomains` honored; user settings ignored
- `allowManagedReadPathsOnly`: only managed `allowRead` honored; user settings ignored
- `excludedCommands` has **no** managed-only lockdown — developers can always append

### Known incompatibilities
- `watchman` (jest), `docker`, Go-based CLIs (`gh`, `gcloud`, `terraform`) on macOS may fail under sandbox.
- On Ubuntu 24.04+: default AppArmor policy blocks bubblewrap userns creation; requires a custom AppArmor profile.
- On WSL2: Windows binaries (`cmd.exe`, `powershell.exe`, `/mnt/c/`) cannot run inside sandbox.
- Inside unprivileged containers: bubblewrap cannot mount fresh `/proc`; requires `enableWeakerNestedSandbox`.

## Numbers & Benchmarks

No concrete benchmarks were provided. Performance overhead is described only as "minimal" with the caveat that "some filesystem operations may be slightly slower." This page is a configuration guide, not a performance evaluation.

## Transfer to Lyra

### One transferable idea: OS-level subprocess sandboxing as a complement to tool-level permission rules

Lyra's current architecture relies entirely on tool-level permission rules (which tools the model can invoke, what paths file tools can touch). There is no OS-level enforcement boundary — once a plugin or agent loop gains Bash access, it inherits the full process environment and filesystem of the Lyra host process. A compromised subprocess (e.g., a `npm install` script, a Python plugin with malicious dependencies, or an autonomous agent that writes a cron job) has no second line of defense.

The Claude Code sandbox demonstrates a **dual-layer model**:
- **Layer 1 (tool-level permissions):** controls whether the model can invoke Bash at all, what path arguments are allowed, etc.
- **Layer 2 (OS-level sandbox):** controls what a running Bash subprocess can actually access, enforced by the OS kernel itself, regardless of what the model decides to do.

For Lyra, implementing an analogous Layer 2 would mean:
- Wrapping Bash subprocess calls in bubblewrap (Linux) or Seatbelt (macOS) profiles.
- Restricting write access to only the project working directory by default, requiring explicit `allowWrite` for any other path (e.g., `~/.kube`, `/tmp/build`).
- Running a small local proxy for network egress control, allowing only explicitly listed domains.
- Providing an escape hatch analogous to `dangerouslyDisableSandbox` for commands that genuinely need wider access, with a managed-setting kill switch for hardened deployments.

This would significantly raise the cost of exploitation in Lyra's plugin and autonomous-agent workstreams. Even if an attacker crafts a prompt that tricks the model into calling Bash, the subprocess would have no write access outside the project directory and no network access to unapproved hosts.

### Workstream route
The most natural landing spot is the **Safety** workstream ($\S 4.3$). Sandboxing is fundamentally a safety and security boundary — it prevents both accidental damage (model writes to wrong path) and malicious exploitation (injected plugin exfiltrates data). If a dedicated Infrastructure workstream is spun out, this also fits there. In the current MASTER-PLAN.md structure, I would suggest placing it as a new subsection $\S 4.3.x$ under Safety, titled "Process-level sandboxing for Bash subprocess isolation."

### Impact assessment
- **Impact:** 8/10. Would be the single largest security improvement Lyra could make. Addresses the gap where a compromised plugin or jailbroken autonomous loop can trivially read SSH keys and write to anywhere on the filesystem. Also improves reliability (prevents accidental filesystem stomping).
- **Effort:** 6/10. Wrapping subprocess execution in bubblewrap is straightforward (a few hundred lines of Rust/Python/Shell wrapper). The network proxy is the harder part (running a local SOCKS proxy, managing the domain allowlist, handling the TLS termination policy). Integration with Lyra's existing permission model requires design work but is not fundamentally difficult.
- **Tier:** Tier 1 (essential for production safety). Should be part of the v1.0 safety baseline, not deferred to a v2 hardening pass.

### Estimate
- Basic filesystem-only sandbox (bubblewrap wrapper for all Bash calls): ~2-3 days of engineering.
- Full sandbox with network proxy and managed settings: ~2-3 weeks of engineering.
- Production hardening, escape-hatch UX, cross-platform testing: ~4-6 weeks total.
