"""Wave-E Task 6: QQ Bot channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def QQBotAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="qqbot", endpoint=endpoint, auth_header=auth_header, **kwargs
    )


__all__ = ["QQBotAdapter"]
