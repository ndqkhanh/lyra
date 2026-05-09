"""Wave-E Task 6: OpenWebUI channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def OpenWebUIAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="openwebui",
        endpoint=endpoint,
        auth_header=auth_header,
        **kwargs,
    )


__all__ = ["OpenWebUIAdapter"]
