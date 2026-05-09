"""Stdlib HTTP shim with the duck-typed surface our providers expect.

Two providers (:mod:`~lyra_cli.providers.copilot` and any future
adapter that takes an injectable HTTP client for testability) accept
an ``http`` kwarg whose contract is::

    resp = http.request(
        method, url, headers={"name": "value"},
        json={"payload": ...} or None,
        timeout=10.0,
    )
    resp.status_code  # int
    resp.text         # str
    resp.json()       # dict (caller catches errors)

Real production deployments hand them an HTTPx / requests / urllib3
client. Tests hand them a hand-rolled spy. The CLI's middle ground
is this stdlib shim — zero new dependencies for users who only want
``--llm copilot`` to work, while keeping the same shape so callers
can swap in a fancier client when they need keep-alive or HTTP/2.

The shim is *not* a full client — no retries, no connection pooling,
no proxy support beyond what ``urllib`` ships out of the box. Anyone
hammering Copilot at production volume should bring their own
``urllib3.PoolManager`` and pass it via the constructor.
"""
from __future__ import annotations

import json as _json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass
class _StdlibResponse:
    """Shape that mimics ``requests.Response`` minimally."""

    status_code: int
    text: str

    def json(self) -> Any:
        return _json.loads(self.text)


class StdlibHTTP:
    """Minimal HTTP client backed by :mod:`urllib`.

    Method ``request`` matches the duck-typed surface in
    :mod:`~lyra_cli.providers.copilot`. Errors are *flattened* into
    response objects with a non-2xx ``status_code`` so callers can
    branch on the status field uniformly — networking exceptions
    become ``599 internal_error`` responses with the exception
    message in ``text``.
    """

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json: Optional[Any] = None,
        timeout: float = 30.0,
    ) -> _StdlibResponse:
        data: Optional[bytes] = None
        merged_headers = dict(headers or {})
        if json is not None:
            data = _json.dumps(json).encode("utf-8")
            merged_headers.setdefault("content-type", "application/json")

        req = urllib.request.Request(
            url,
            data=data,
            method=method.upper(),
            headers=merged_headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return _StdlibResponse(status_code=resp.status, text=body)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover — defensive
                pass
            return _StdlibResponse(status_code=e.code, text=body)
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            return _StdlibResponse(status_code=599, text=f"{type(e).__name__}: {e}")


__all__ = ["StdlibHTTP"]
