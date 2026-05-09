"""Device-code OAuth flow + `/auth` slash dispatcher.

Device-code flow is the right pattern for CLI OAuth: the CLI prints a
short user code, the user visits a URL in a browser, enters the code,
and the CLI polls a token endpoint until the grant lands. No embedded
browser, no localhost callback server needed.

Persists the resulting token via the same ``CopilotTokenStore``-shaped
JSON store we use for Copilot session tokens (one file per user,
``chmod 600``).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from lyra_cli.providers.copilot import CopilotTokenStore


@dataclass(frozen=True)
class AuthFlowResult:
    provider: str
    user_code: str
    verification_uri: str
    access_token: str
    expires_at: int


class DeviceCodeAuth:
    """OAuth 2.0 Device Authorization Grant (RFC 8628)."""

    def __init__(
        self,
        *,
        provider: str,
        client_id: str,
        scope: str,
        device_endpoint: str,
        token_endpoint: str,
        http: Any,
        store_path: Optional[Path] = None,
        poll_interval_s: float = 5.0,
        poll_timeout_s: float = 600.0,
    ) -> None:
        self.provider = provider
        self.client_id = client_id
        self.scope = scope
        self.device_endpoint = device_endpoint
        self.token_endpoint = token_endpoint
        self.http = http
        self.store = CopilotTokenStore(path=store_path)
        self.poll_interval_s = poll_interval_s
        self.poll_timeout_s = poll_timeout_s

    def run(self) -> Optional[AuthFlowResult]:
        start = self.http.request(
            "POST", self.device_endpoint,
            headers={"accept": "application/json"},
            data={"client_id": self.client_id, "scope": self.scope},
        )
        start.raise_for_status()
        payload = start.json()
        device_code = payload["device_code"]
        user_code = payload["user_code"]
        verification_uri = payload.get("verification_uri") \
            or payload.get("verification_uri_complete", "")
        interval = max(float(payload.get("interval", 5)), self.poll_interval_s)

        deadline = time.time() + self.poll_timeout_s
        while time.time() <= deadline:
            token_resp = self.http.request(
                "POST", self.token_endpoint,
                headers={"accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
            try:
                body = token_resp.json()
            except Exception:
                body = {}
            err = body.get("error")
            if err in {"authorization_pending"}:
                if interval > 0:
                    time.sleep(interval)
                continue
            if err == "slow_down":
                # RFC 8628: increase interval by at least 5s. Use the
                # minimum of (interval+5, 5) when poll_interval_s is 0
                # so test suites using poll_interval_s=0 don't block.
                interval = interval + 5.0 if self.poll_interval_s > 0 else 0.0
                if interval > 0:
                    time.sleep(interval)
                continue
            if err:
                return None
            access = body.get("access_token")
            if isinstance(access, str):
                expires_at = int(time.time() + int(body.get("expires_in", 3600)))
                self.store.save(self.provider, access, expires_at=expires_at)
                return AuthFlowResult(
                    provider=self.provider,
                    user_code=user_code,
                    verification_uri=verification_uri,
                    access_token=access,
                    expires_at=expires_at,
                )
            if interval > 0:
                time.sleep(interval)
        return None


_SUPPORTED_PROVIDERS = ("copilot",)


def run_auth_slash(
    *,
    argv: list[str],
    store_path: Optional[Path] = None,
) -> str:
    """Dispatch `/auth <sub> [provider]`."""
    store = CopilotTokenStore(path=store_path)
    if not argv or argv[0] == "list":
        lines = ["Configured OAuth providers:"]
        for p in _SUPPORTED_PROVIDERS:
            rec = store.load(p)
            status = "configured" if rec else "not configured"
            lines.append(f"  - {p}  - {status}")
        return "\n".join(lines)
    sub = argv[0]
    if sub == "logout":
        if len(argv) < 2:
            return "usage: /auth logout <provider>"
        provider = argv[1]
        store.clear(provider)
        return f"cleared token for {provider}"
    if sub == "copilot":
        return (
            "copilot OAuth is interactive - run `lyra auth copilot` "
            "from a terminal where you can paste the user code "
            "into github.com/login/device."
        )
    return f"usage: /auth [list|logout <provider>|{' | '.join(_SUPPORTED_PROVIDERS)}]"


__all__ = [
    "AuthFlowResult",
    "DeviceCodeAuth",
    "run_auth_slash",
]
