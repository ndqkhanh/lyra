---
title: Install
description: Install Lyra with pip or pipx, on macOS, Linux, or WSL.
---

<!-- lyra-legacy-aware: page documents the upgrade path from open-coding / open-harness, so the legacy brand names appear by design. -->


# Install Lyra <span class="lyra-badge beginner">beginner</span>

Lyra is a Python package that ships a single CLI entry point: `lyra`
(plus the short alias `ly`). It runs anywhere CPython 3.11+ runs.

## Requirements

| Requirement | Why |
|---|---|
| **Python ≥ 3.11** | New typing features, structural pattern matching |
| **Git ≥ 2.30** | Subagent worktrees and 3-way merge |
| A POSIX shell | `bash` tool falls back to `/bin/sh` if `bash` is missing |
| 200 MB free disk | The package itself is small; subagent worktrees grow on demand |

Lyra has **no required GPU**, no Docker dep, and no native compile step.
All it needs is a Python interpreter and an LLM API key.

## Recommended: pipx

[pipx](https://pipx.pypa.io/) installs CLI tools into isolated venvs and
puts a single executable on your `$PATH`. This is the cleanest install:

```bash
pipx install lyra
lyra --version
```

??? tip "Don't have pipx?"
    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    # then re-open your shell
    ```

## Alternative: pip into a venv

```bash
python3 -m venv ~/.venvs/lyra
source ~/.venvs/lyra/bin/activate
pip install lyra
```

You'll need to activate that venv whenever you run `lyra`. Most people
prefer pipx for that reason.

## Alternative: from source

```bash
git clone https://github.com/lyra-contributors/lyra.git
cd lyra
pip install -e packages/lyra-cli -e packages/lyra-core \
            -e packages/lyra-skills -e packages/lyra-mcp \
            -e packages/lyra-evals
```

Editable installs are the right choice if you're going to read the
source — and reading the source is one of Lyra's design goals.

## Configure your first provider

Lyra talks to **16 LLM providers** through a single factory. You only
need credentials for the one(s) you'll actually use. Set the env var
that matches your provider:

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY=sk-ant-…
    export LYRA_LLM_MODEL=anthropic:claude-3-5-sonnet-latest
    ```

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY=sk-…
    export LYRA_LLM_MODEL=openai:gpt-4o
    ```

=== "DeepSeek"

    ```bash
    export DEEPSEEK_API_KEY=sk-…
    export LYRA_LLM_MODEL=deepseek:deepseek-chat
    ```

=== "Local (Ollama)"

    ```bash
    # No API key — Ollama serves on localhost:11434.
    export LYRA_LLM_MODEL=ollama:llama3.1
    ```

The `LYRA_LLM_MODEL` syntax is `provider:model_id`. Run
`lyra providers` to see the full provider list and the env var each one
expects.

!!! note "Legacy env vars still work"
    If you're upgrading from `open-coding` or `open-harness`, the old
    `HARNESS_LLM_MODEL` / `OPEN_HARNESS_*` names still work. Lyra prints
    a one-shot deprecation warning the first time it reads them. See
    [Environment variables](../reference/env-vars.md) for the full
    legacy → canonical map.

## Verify

```bash
lyra --version
lyra providers
lyra doctor
```

`lyra doctor` checks Python version, git availability, current model
config, write permissions on `~/.lyra/`, and the readability of your
provider credentials. It will tell you exactly what's missing.

[← Get Started overview](index.md){ .md-button }
[Run your first session →](first-session.md){ .md-button .md-button--primary }
