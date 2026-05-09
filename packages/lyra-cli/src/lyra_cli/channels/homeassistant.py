"""Wave-E Task 6: Home Assistant channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def HomeAssistantAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="homeassistant",
        endpoint=endpoint,
        auth_header=auth_header,
        **kwargs,
    )


__all__ = ["HomeAssistantAdapter"]
