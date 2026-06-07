# Channels Reference (code.claude.com - Anthropic/Claude Code Team)

> URL: https://code.claude.com/docs/en/channels-reference
> Status: Official documentation (research preview, Claude Code v2.1.80+)

---

## Key Technical Claims

1. **Channel = MCP server pushing events into a Claude Code session.** Channels let external systems (webhooks, CI alerts, chat platforms) push events into a running Claude Code session so Claude can react to things outside the terminal. They are declared as MCP capabilities via `experimental: { 'claude/channel': {} }` in the MCP `Server` constructor.

2. **Two channel modes: one-way and two-way.** One-way channels forward alerts/monitoring events for Claude to act on (no reply path). Two-way channels additionally expose a standard MCP reply tool (`ListToolsRequestSchema` / `CallToolRequestSchema`) so Claude can send messages back through the channel.

3. **Permission relay for remote tool approval (v2.1.81+).** A two-way channel can opt into receiving tool-approval prompts (Bash, Write, Edit) and forwarding them to a remote device. The remote user replies `yes <5-char-ID>` or `no <5-char-ID>`, and the verdict is applied. The local terminal dialog stays open simultaneously -- whichever answer arrives first (local or remote) wins.

4. **Sender gating is mandatory to prevent prompt injection.** An ungated channel is an injection vector. Gate on the sender's identity (not the chat/room), using an allowlist. The official Telegram and Discord channels bootstrap the allowlist via a pairing-code flow.

5. **Channels can be packaged as plugins** and published to a marketplace for installation via `/plugin install`. During the research preview, custom channels require `--dangerously-load-development-channels` since only Anthropic-curated channels are on the allowlist.

---

## Architecture / Mechanism Details

### MCP Transport Layer
- Claude Code spawns the channel server as a subprocess over stdio transport (standard MCP pattern).
- The channel server runs on the same machine as Claude Code. No URL needs to be exposed for chat-platform channels (they poll the platform API locally).
- Webhook channels listen on a local HTTP port for external POSTs.

### Capability Declaration
```ts
const mcp = new Server(
  { name: 'webhook', version: '0.0.1' },
  {
    capabilities: {
      experimental: {
        'claude/channel': {},          // registers notification listener (required)
        'claude/channel/permission': {}, // opts into permission relay (optional)
      },
      tools: {},                        // enables MCP tool discovery (two-way only)
    },
    instructions: 'Messages arrive as <channel source="webhook" ...>. Reply with reply tool.',
  },
)
```

### Notification Format
- Method: `notifications/claude/channel`
- Params: `content` (string, becomes body of `<channel>` tag) + `meta` (Record<string, string>, each entry becomes a tag attribute)
- Events arrive in Claude's context as: `<channel source="channel-name" key1="val1">content body</channel>`
- Notifications are NOT acknowledged -- `await mcp.notification()` resolves when written to transport, not when Claude has processed it.
- Events queue and process in order. If multiple arrive while Claude is busy, they are delivered together on the next turn.

### Permission Relay Sequence
1. Claude Code generates a 5-letter request ID (a-z sans 'l') and sends `notifications/claude/channel/permission_request` to the channel server with: `request_id`, `tool_name`, `description`, `input_preview` (truncated to ~200 chars).
2. Channel server formats the prompt and sends it out through the platform.
3. Remote user replies with `yes <id>` or `no <id>`.
4. Channel server sends `notifications/claude/channel/permission` back with `request_id` (lowercased) and `behavior: 'allow' | 'deny'`.
5. If the ID doesn't match an open request, Claude Code drops it silently.
6. Wrong format (no ID, `approve it`, etc.) falls through as a normal chat message.

### Sender Gating Pattern
```ts
const allowed = new Set(loadAllowlist())
if (!allowed.has(message.from.id)) return   // gate on sender, not room
await mcp.notification({ ... })
```

### Plugin Packaging
- Channels are wrapped as plugins and published to a marketplace.
- Users install: `/plugin install <name>`, then enable: `--channels plugin:<name>@<marketplace>`.
- On Team/Enterprise plans, admins set `allowedChannelPlugins` in org policy to replace the default Anthropic allowlist.

---

## Numbers & Benchmarks

| Metric | Value |
|--------|-------|
| Min Claude Code version | v2.1.80 |
| Min version for permission relay | v2.1.81 |
| Request ID format | 5 lowercase letters, alphabet a-z without 'l' (regex: `[a-km-z]{5}`) |
| `input_preview` truncation | ~200 characters |
| Example HTTP port | 8788 |
| Runtime options | Bun, Node.js, Deno (any Node.js-compatible runtime) |
| Status | Research preview (Anthropic-curated allowlist) |

---

## Transfer to Lyra

### One Idea: Permission Relay Pattern for Remote Safety Approval

The single most transferable idea is the **permission relay** mechanism. When Lyra operates in headless, daemon, or continuous-mode scenarios (autonomous execution, long-running research loops), it will inevitably encounter operations that require human approval (e.g., executing risky bash commands, writing files, editing code). Currently Lyra blocks on a terminal prompt, which breaks automation.

The channel permission relay pattern solves this precisely:
1. Lyra generates a short request ID (borrow the 5-char no-'l' alphabet to minimize typos on mobile).
2. The safety prompt is pushed via an out-of-band channel (SSE stream, notification service, webhook, or even a simple file-based signal).
3. The human approves/denies remotely with a minimal token (`yes <id>` / `no <id>`).
4. Both local and remote channels stay live -- whichever arrives first wins, preserving responsiveness.
5. Malformed replies (missing ID, bad format) fall through as normal input rather than blocking.

Crucially, the `input_preview` field -- truncated to ~200 chars -- means the human gets enough context to decide without the full payload being transmitted. This keeps the approval UX fast and mobile-friendly.

### Where it Fits in the Architecture

**Route: SS4.6 (Safety & Autonomy Workstream)**

Permission relay is a safety mechanism, not a communication protocol. It belongs in the safety/autonomy workstream alongside Lyra's existing §17 work (safety brainstorming) because it solves the fundamental tension between automation and human oversight: how does an autonomous agent get timely approval without blocking on a terminal prompt?

The channel pattern itself (MCP server as event bridge) could also inform SS4.5 (Agent Communication), but the specific transfer is the permission relay UX pattern.

### Implementation Sketch for Lyra
- Minimal V1: Write a `safety-channel` MCP server that listens on a local port. Lyra's safety gate pushes permission requests to it. The human curl-POSTs verdicts.
- V2: Integrate with a push notification service (e.g., ntfy.sh, Pushover) to deliver prompts to a phone.
- V3: Full bidirectional channel with reply tool, pairing-based sender allowlist (mirroring the Telegram plugin pattern).

### Impact & Effort
- **Impact**: 8/10 -- Solves a critical blocker for autonomous/headless Lyra modes. Without it, any risky operation forces the user back to the terminal.
- **Effort**: 6/10 -- The MCP SDK is lightweight (~50 lines for a minimal channel server). The hard part is the UX design (how to format prompts for mobile, how to recover from timeouts) and integrating with Lyra's existing safety dispatch loop.
- **Tier**: Tier 1 -- Important for Lyra's autonomous execution story.
