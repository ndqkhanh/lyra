"""Wave-E Task 6: BlueBubbles iMessage relay channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def BlueBubblesAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="bluebubbles",
        endpoint=endpoint,
        auth_header=auth_header,
        **kwargs,
    )


__all__ = ["BlueBubblesAdapter"]
