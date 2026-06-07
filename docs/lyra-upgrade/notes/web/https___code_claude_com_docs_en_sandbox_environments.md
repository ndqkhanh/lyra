# Choose a sandbox environment (Claude Code docs, Anthropic, 2026)

## Key Technical Claims

1. **Six tiers of isolation**, from per-command sandbox to full VM: Sandboxed Bash tool, Sandbox runtime, Dev containers, Custom containers, Virtual machines, and Claude Code on the web (Anthropic-hosted VM).
2. **Isolation scope varies by approach.** The built-in Bash sandbox (Seatbelt on macOS, bubblewrap on Linux/WSL2) constrains only Bash commands and their child processes -- built-in file tools, MCP servers, and hooks remain unconstrained on the host. Every other approach puts the entire Claude Code process inside the boundary.
3. **Layer approaches for defense in depth.** The Bash sandbox inside a container gives per-command OS restrictions on top of the outer environment boundary.
4. **Isolation is not sufficient alone.** Sandbox boundaries reduce the impact of a breach but do not eliminate risk -- any approach allowing network egress can still leak data; any approach mounting the project directory writable can still modify code. The sandbox also does not change what is sent to the model (prompts and files are transmitted regardless).
5. **Permission modes and isolation are orthogonal.** Permission modes decide whether a tool call runs and whether the user is prompted; isolation restricts what a command can access once it runs. Together they form layered controls.

## Architecture/Mechanism Details

### Sandboxed Bash tool (built-in)
- **macOS:** Uses Seatbelt (the built-in macOS sandbox API) to restrict filesystem and network per command.
- **Linux/WSL2:** Uses bubblewrap (bwrap), a user-space sandbox using Linux namespaces.
- **Scope:** Bash commands and their child processes only. Read, Edit, WebFetch, MCP servers, and hooks run unconstrained outside the sandbox.
- **Default policy:** Allows writes to the working directory; prompts the first time a command needs a new network domain.
- **Enable:** `/sandbox` command.

### Sandbox runtime (`@anthropic-ai/sandbox-runtime`)
- Wraps the entire process (not just Bash) in the same Seatbelt or bubblewrap isolation.
- Covers every tool, hook, and MCP server in the session.
- Denies all write and network access by default; must configure before use.
- **Configuration:** `~/.srt-settings.json` (or pass `--settings` flag). Must allow writes to project directory + `~/.claude` and `~/.claude.json`. Must allow network domains including `api.anthropic.com` or custom provider endpoint.
- **Launch:** `npx @anthropic-ai/sandbox-runtime claude`
- **Status:** Beta research preview. Configuration format may change.

### Dev containers
- Runs Claude Code inside a Docker container managed by VS Code or compatible editor.
- Anthropic publishes an example with default-deny iptables firewall as a starting point.
- Supports `--dangerously-skip-permissions` for unattended work because firewall blocks unapproved egress.

### Custom containers
- Any Docker/OCI image with custom network policies, mounted volumes, seccomp profiles.
- Can layer built-in Bash sandbox inside container (unprivileged containers need the nested-sandbox setting).

### Virtual machines
- Strongest separation with own kernel; options include cloud instances, local hypervisors, Firecracker microVMs.
- Docker Desktop Sandboxes feature provides microVM with own Docker daemon and workspace sync.

### Claude Code on the web
- Each session in an isolated Anthropic-managed VM.
- Network proxy enforces default allowlist.
- GitHub token held outside sandbox; scoped credentials issued inside.
- Requires Claude subscription + connected GitHub account.

### Organizational enforcement
- Built-in Bash sandbox: Enforced via managed settings (MDM or server-managed settings on Claude.ai). Config keys prevent developers from widening the policy.
- Dev containers: Convention (commit to repos), not enforcement boundary.
- Custom containers/VMs: Distributed via approved image; enforced via device management or software allowlisting.

## Numbers & Benchmarks

None. This is a conceptual/architectural document -- no benchmarks, latency numbers, or resource measurements are provided.

## Transfer to Lyra

**One idea:** Ship a sandbox runtime layer that wraps the entire Lyra agent process (not just spawned commands) in an OS-level sandbox using platform-native primitives.

Lyra currently containerizes code execution but leaves the agent's own file tools, context readers, hook invocations, and plugin servers running on the host with host-level access. The Claude Code sandbox runtime pattern shows how to extend confinement to the full agent process using Seatbelt (macOS) and bubblewrap (Linux) -- no Docker required. This is especially relevant for Lyra's supervisor/orchestrator agents that (a) read arbitrary files from workspace directories, (b) invoke plugins and MCP-like servers, and (c) write back modifications.

**Concrete approach:**
1. Define a config file (analogous to `~/.srt-settings.json`) for Lyra agents that specifies allowed read/write paths and allowed network domains.
2. Wrap the agent entrypoint in a thin runtime that applies `sandbox_init` (macOS) or `bubblewrap` (Linux) before any tool or plugin code executes.
3. For the Kubernetes deployment path, expose the same sandbox as a sidecar config or `securityContext` annotation.

**Workstream route:** §4.3 (Reliability & Fault Tolerance) -- the sandbox runtime directly supports reliable agent operation by preventing an agent from accidentally (or adversarially) escaping its workspace, modifying files outside its scope, or phoning home to unauthorized endpoints. It also intersects with §4.1 (Agent Safety & Security) as a foundational control for the safety layer.

**Tier:** T1 -- Direct adoption. The pattern uses existing, battle-tested OS primitives and is a straightforward engineering effort rather than a research problem. The sandbox runtime is already published as an npm package; porting the approach to Lyra's Python/Go architecture is a matter of wrapping the same system calls.

**Impact:** 4/5 -- Significantly raises the baseline security posture of the agent runtime without requiring containerization on every workstation.
**Effort:** 3/5 -- Moderate. Requires implementing the wrapper (1-2 weeks), defining the configuration schema (few days), and testing across macOS and Linux (1 week).
