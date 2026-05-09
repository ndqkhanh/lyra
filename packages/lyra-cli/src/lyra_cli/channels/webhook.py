"""Wave-E Task 6: generic webhook channel adapter (no extra dep).

Useful for hitting custom internal endpoints, Zapier hooks, IFTTT,
or local listeners that mimic any of the long-tail providers.
"""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def WebhookAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="webhook", endpoint=endpoint, auth_header=auth_header, **kwargs
    )


__all__ = ["WebhookAdapter"]
