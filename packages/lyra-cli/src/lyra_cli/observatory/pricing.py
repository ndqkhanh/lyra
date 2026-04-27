"""LiteLLM-backed pricing engine with on-disk cache + hardcoded fallback.

Why these design choices:

* **stdlib only**: ``urllib.request`` for the fetch so airgapped users
  don't hit a missing-``httpx`` ImportError. Lyra already ships Rich;
  we don't want to grow the wheel further for one HTTP GET.

* **ETag-aware**: LiteLLM's pricing JSON is a stable URL. Sending
  ``If-None-Match: <etag>`` makes refresh free 99% of the time and
  gives us instant 304 short-circuits.

* **Decimal not float**: per-token prices are 1e-7 to 1e-5; floats
  round-off bites once you sum ~10k turns. Decimal also makes our
  ``cost_for_turn`` byte-identical between runs (test stability).

* **Hardcoded fallback**: the top 20 models cover ~95% of Lyra users
  per Phase L telemetry. Falling back to a known-good price means
  ``lyra burn`` never returns ``$?.??`` on a fresh airgapped checkout.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Mapping
from urllib import request as _urlreq
from urllib.error import URLError


_CACHE_ROOT: Path = Path.home() / ".cache" / "lyra" / "pricing"
_LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "litellm/model_prices_and_context_window_backup.json"
)
_TTL_SECONDS = 7 * 24 * 3600


_FALLBACK: dict[str, dict[str, float]] = {
    "deepseek-v4-pro":   {"input_cost_per_token": 1.0e-6,  "output_cost_per_token": 4.0e-6},
    "deepseek-v4-flash": {"input_cost_per_token": 0.3e-6,  "output_cost_per_token": 1.0e-6},
    "deepseek-v3":       {"input_cost_per_token": 0.27e-6, "output_cost_per_token": 1.10e-6},
    "claude-opus-4":     {"input_cost_per_token": 15e-6,   "output_cost_per_token": 75e-6},
    "claude-sonnet-4":   {"input_cost_per_token": 3e-6,    "output_cost_per_token": 15e-6},
    "claude-haiku-4":    {"input_cost_per_token": 0.8e-6,  "output_cost_per_token": 4e-6},
    "gpt-5":             {"input_cost_per_token": 5e-6,    "output_cost_per_token": 15e-6},
    "gpt-5-mini":        {"input_cost_per_token": 0.15e-6, "output_cost_per_token": 0.6e-6},
    "gpt-5-nano":        {"input_cost_per_token": 0.05e-6, "output_cost_per_token": 0.2e-6},
    "gpt-4o":            {"input_cost_per_token": 2.5e-6,  "output_cost_per_token": 10e-6},
    "gpt-4o-mini":       {"input_cost_per_token": 0.15e-6, "output_cost_per_token": 0.6e-6},
    "gemini-3-pro":      {"input_cost_per_token": 1.25e-6, "output_cost_per_token": 5e-6},
    "gemini-3-flash":    {"input_cost_per_token": 0.075e-6,"output_cost_per_token": 0.3e-6},
    "gemini-2.5-pro":    {"input_cost_per_token": 1.25e-6, "output_cost_per_token": 5e-6},
    "gemini-2.5-flash":  {"input_cost_per_token": 0.075e-6,"output_cost_per_token": 0.3e-6},
    "qwen-3-coder":      {"input_cost_per_token": 0.4e-6,  "output_cost_per_token": 1.6e-6},
    "qwen-3-max":        {"input_cost_per_token": 1.5e-6,  "output_cost_per_token": 6e-6},
    "qwen3-coder":       {"input_cost_per_token": 0.4e-6,  "output_cost_per_token": 1.6e-6},
    "grok-4":            {"input_cost_per_token": 5e-6,    "output_cost_per_token": 15e-6},
    "kimi-k2":           {"input_cost_per_token": 0.6e-6,  "output_cost_per_token": 2.5e-6},
    "mock":              {"input_cost_per_token": 0.0,     "output_cost_per_token": 0.0},
}

# Pricing-specific short-name map. Distinct from
# ``lyra_core.providers.aliases`` (which routes API slugs); here we
# normalise *user-facing* names to the keys used in ``_FALLBACK`` /
# LiteLLM JSON (which both index by the human-readable model name).
_PRICING_ALIASES: dict[str, str] = {
    "v4-pro":   "deepseek-v4-pro",
    "v4-flash": "deepseek-v4-flash",
    "v4":       "deepseek-v4-pro",
    "opus":     "claude-opus-4",
    "sonnet":   "claude-sonnet-4",
    "haiku":    "claude-haiku-4",
    # API-slug-back -> user-facing for cases where the agent persists
    # the underlying provider slug (e.g. ``deepseek-reasoner``).
    "deepseek-reasoner": "deepseek-v4-pro",
    "deepseek-chat":     "deepseek-v4-flash",
}


@dataclass(frozen=True)
class PriceQuote:
    model: str
    input_per_mtoken_usd: Decimal | None
    output_per_mtoken_usd: Decimal | None
    source: Literal["upstream", "cache", "fallback", "unknown"]


def quote(model: str, *, refresh: bool = False) -> PriceQuote:
    canonical = _resolve_alias(model)

    if refresh or not _cache_fresh():
        upstream = _fetch_upstream(_LITELLM_URL)
        if upstream is not None:
            _write_cache(upstream)

    cache = _read_cache()
    if cache and canonical in cache:
        return _coerce(canonical, cache[canonical], "cache")
    if canonical in _FALLBACK:
        return _coerce(canonical, _FALLBACK[canonical], "fallback")
    return PriceQuote(canonical, None, None, "unknown")


def cost_for_turn(row: Mapping[str, Any], *, refresh: bool = False) -> Decimal | None:
    model = row.get("model")
    tin = row.get("tokens_in")
    tout = row.get("tokens_out")
    if not model or tin is None or tout is None:
        return None
    q = quote(str(model), refresh=refresh)
    if q.input_per_mtoken_usd is None or q.output_per_mtoken_usd is None:
        return None
    cost = (
        Decimal(int(tin))  / Decimal(1_000_000) * q.input_per_mtoken_usd
        + Decimal(int(tout)) / Decimal(1_000_000) * q.output_per_mtoken_usd
    )
    return cost.quantize(Decimal("0.000001"))


# ---- private helpers ------------------------------------------------------

def _resolve_alias(model: str) -> str:
    norm = (model or "").lower().strip()
    return _PRICING_ALIASES.get(norm, model)


def _cache_fresh() -> bool:
    fa = _CACHE_ROOT / "litellm.fetched_at"
    if not fa.exists():
        return False
    try:
        ts = _dt.datetime.fromisoformat(fa.read_text().strip())
        age = (_dt.datetime.now() - ts).total_seconds()
        return age < _TTL_SECONDS
    except (ValueError, OSError):
        return False


def _read_cache() -> dict[str, dict[str, float]] | None:
    p = _CACHE_ROOT / "litellm.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(payload: dict[str, dict[str, float]]) -> None:
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    (_CACHE_ROOT / "litellm.json").write_text(json.dumps(payload))
    (_CACHE_ROOT / "litellm.fetched_at").write_text(
        _dt.datetime.now().isoformat(timespec="seconds")
    )


def _fetch_upstream(url: str) -> dict[str, dict[str, float]] | None:
    """Returns parsed JSON or None on any failure (including network)."""
    try:
        req = _urlreq.Request(url, headers={"User-Agent": "lyra-burn/3.3"})
        etag_path = _CACHE_ROOT / "litellm.etag"
        if etag_path.exists():
            req.add_header("If-None-Match", etag_path.read_text().strip())
        with _urlreq.urlopen(req, timeout=4.0) as resp:
            if resp.status == 304:
                return None
            data = json.loads(resp.read().decode())
            etag = resp.headers.get("ETag")
            if etag:
                _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
                etag_path.write_text(etag)
            return data
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


def _coerce(model: str, raw: Mapping[str, Any], source: str) -> PriceQuote:
    inp = raw.get("input_cost_per_token")
    outp = raw.get("output_cost_per_token")
    return PriceQuote(
        model=model,
        input_per_mtoken_usd=Decimal(str(inp)) * Decimal(1_000_000) if inp is not None else None,
        output_per_mtoken_usd=Decimal(str(outp)) * Decimal(1_000_000) if outp is not None else None,
        source=source,  # type: ignore[arg-type]
    )
