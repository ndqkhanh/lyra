"""Contract tests for the 6 new OpenAI-compatible presets.

DashScope (Alibaba's cloud, hosts Qwen + Kimi),
plus five local OpenAI-compatible servers:
- vllm
- llama-server (llama.cpp's HTTP mode)
- tgi (HuggingFace Text Generation Inference)
- llamafile (single-file Mozilla distribution)
- mlx (Apple Silicon MLX-LM server)
"""
from __future__ import annotations

import pytest

from lyra_cli.providers.openai_compatible import PRESETS, preset_by_name


def _preset(name: str):
    p = preset_by_name(name)
    assert p is not None, f"missing preset: {name}"
    return p


def test_dashscope_preset_uses_dashscope_env() -> None:
    p = _preset("dashscope")
    assert "DASHSCOPE_API_KEY" in p.env_keys
    assert p.auth_scheme == "bearer"
    # DashScope is cloud — no reachability probe needed.
    assert p.probe_reachable is False


def test_dashscope_default_model_is_qwen_or_kimi() -> None:
    p = _preset("dashscope")
    assert p.default_model.startswith("qwen") or p.default_model.startswith("kimi")


def test_vllm_local_preset_no_auth() -> None:
    p = _preset("vllm")
    assert p.auth_scheme == "none"
    assert p.probe_reachable is True
    assert "127.0.0.1" in p.base_url or "localhost" in p.base_url


def test_llama_server_local_preset_no_auth() -> None:
    p = _preset("llama-server")
    assert p.auth_scheme == "none"
    assert p.probe_reachable is True


def test_tgi_local_preset_no_auth() -> None:
    p = _preset("tgi")
    assert p.auth_scheme == "none"
    assert p.probe_reachable is True


def test_llamafile_local_preset_no_auth() -> None:
    p = _preset("llamafile")
    assert p.auth_scheme == "none"
    assert p.probe_reachable is True


def test_mlx_local_preset_no_auth() -> None:
    p = _preset("mlx")
    assert p.auth_scheme == "none"
    assert p.probe_reachable is True


def test_all_new_preset_names_are_unique() -> None:
    new = {"dashscope", "vllm", "llama-server", "tgi", "llamafile", "mlx"}
    seen = [p.name for p in PRESETS if p.name in new]
    assert sorted(seen) == sorted(new)
    assert len(seen) == len(set(seen)), "duplicate names detected"


def test_local_presets_have_distinct_default_ports() -> None:
    """Each local preset should listen on a different default port to
    avoid colliding with peers on the same machine."""
    locals_ = ["vllm", "llama-server", "tgi", "llamafile", "mlx"]
    ports = []
    for name in locals_:
        p = _preset(name)
        port = p.base_url.rsplit(":", 1)[-1].split("/", 1)[0]
        ports.append(port)
    assert len(set(ports)) == len(ports), f"port collision: {ports}"
