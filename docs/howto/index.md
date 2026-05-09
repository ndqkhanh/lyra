---
title: How-To Guides
description: Recipes for the things you'll actually do in a normal week with Lyra.
---

# How-To Guides <span class="lyra-badge intermediate">intermediate</span>

Concept pages explain **how Lyra works**. How-To pages show you **how
to use it** for a specific task. Each one is a short, actionable
recipe with copy-pasteable commands and a verification step.

## Extend Lyra

| Guide | When you need it |
|---|---|
| [Add an MCP server](add-mcp-server.md) | Plug an MCP-protocol tool server into a session |
| [Write a skill](write-skill.md) | Add a reusable capability via `SKILL.md` |
| [Write a slash command](write-slash-command.md) | Add a custom `/command` to your workflow |
| [Write a hook](write-hook.md) | Run code at any lifecycle event — block, redact, or augment |
| [Write a plugin](write-plugin.md) | Bundle skills + hooks + commands into an installable package |

## Operate Lyra

| Guide | When you need it |
|---|---|
| [Configure providers](configure-providers.md) | Switch between Anthropic / OpenAI / DeepSeek / Ollama / … |
| [Set budgets and quotas](budgets-and-quotas.md) | Cap session cost, per-tool quotas, CI-wide spend |
| [Customize the HUD](customize-hud.md) | Build your own live status pane with widgets |
| [Schedule a recurring skill](cron-skill.md) | Hermes-style cron channel for repeating chores |

## Verify and debug

| Guide | When you need it |
|---|---|
| [Turn on the TDD gate](tdd-gate.md) | Enable the deterministic test gate |
| [Debug systematically](debug-mode.md) | Use `debug` mode for hypothesis-driven investigation |
| [Read and replay a trace](replay-trace.md) | Walk a session's HIR span tree, diff runs, replay against a different model |
| [Run an eval](run-eval.md) | Score Lyra against a corpus, compute pass@k, gate CI on regression |
| [Use the ReasoningBank](use-reasoning-bank.md) | Inspect, seed, and operate Lyra's lessons memory; wire MaTTS into Tournament-TTS |
| [Use prompt caching across subagents](use-prompt-cache.md) | Pre-warm provider prompt caches so `N` sibling subagents share one write — 50–90% off the prefix |

Each guide assumes you've completed [Get Started](../start/index.md)
and have a working `lyra` install with at least one provider
configured.

[Add an MCP server →](add-mcp-server.md){ .md-button .md-button--primary }
