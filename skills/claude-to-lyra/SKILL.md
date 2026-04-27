---
id: claude-to-lyra
name: Lyra Bridge
description: Delegate to Lyra (any LLM provider, any session) over HTTP. Use when you want a second-opinion model, want to switch providers mid-conversation, or want to run a sandboxed shell command without touching the host.
version: "1.0.0"
keywords:
  - lyra
  - delegate
  - second-opinion
  - bridge
  - sandbox
applies_to:
  - claude-code
  - codex
  - cursor
requires:
  - "lyra-cli >= 3.4.0"
progressive: true
---

# Lyra Bridge — invoke Lyra from Claude Code (or any other agent)

This skill turns the locally-running `lyra serve` instance into a
callable tool. You hand Lyra a prompt, it routes the request to
whichever provider the user has configured (DeepSeek, Anthropic,
OpenAI, Gemini, xAI, Groq, Cerebras, Mistral, DashScope, OpenRouter),
and you get the answer back as plain text.

## When to use this skill

Reach for the bridge when you want to:

1. **Get a second opinion** on a tricky design choice — ask Lyra
   to weigh in with a different model and compare the two replies.
2. **Cost-shift** a long, mechanical sub-task (refactor 80 files,
   summarise a transcript) onto a cheaper model without leaving
   the current session.
3. **Run untrusted code** safely — `POST /v1/run` spins up an
   ephemeral sandbox, executes the command, and tears it down.

Never use it as a "do my whole task for me" passthrough. Lyra is
a peer, not a sub-agent — keep the conversation in *this* harness
and use Lyra for focused side-quests.

## Pre-flight

1. The user must have run `lyra setup` so `~/.lyra/settings.json`
   has a default provider + model.
2. Start the server: `lyra serve` (defaults to
   `http://127.0.0.1:9099`).
3. If `LYRA_API_TOKEN` is set, include it as
   `Authorization: Bearer <token>` on every request.

## Calling the API

### Synchronous chat

```bash
curl -s http://127.0.0.1:9099/v1/chat \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $LYRA_API_TOKEN" \
  -d '{
    "prompt": "Write a Python function that detects palindromes ignoring punctuation.",
    "model": "deepseek-flash",
    "session_id": "from-claude-code"
  }'
```

Response shape:

```json
{
  "text": "...",
  "session_id": "from-claude-code",
  "model": "deepseek-flash",
  "usage": {"input_tokens": 42, "output_tokens": 88},
  "error": null
}
```

### Streaming chat (SSE)

```
POST /v1/stream
```

Each event is a `data: {...}` line containing `{"kind": "delta",
"payload": "..."}`. Terminator is `data: [DONE]`.

### Sandbox runner

```json
POST /v1/run
{
  "argv": ["python", "-c", "print(1 + 1)"],
  "files": {"hello.py": "print('hi')\n"},
  "timeout": 10
}
```

Response is the :class:`CommandResult` dict — `stdout`, `stderr`,
`exit_code`, `duration_ms`, `timed_out`.

## Error handling

- `400` — payload was malformed (missing `prompt`, oversized body).
- `401` — bearer token mismatch.
- `404` — endpoint typo. `GET /v1/models` is the introspection
  hatch when you don't know which aliases the user has wired up.
- `500` — Lyra crashed; surface the error verbatim, do not retry.

## Output etiquette

When you forward Lyra's reply, label it explicitly so the user
knows where the answer came from. Never paraphrase Lyra's output
silently — they may be paying per-token on a different provider
and want to audit the bill.
