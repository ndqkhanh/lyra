"""Wave-E Task 6: DingTalk channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def DingTalkAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="dingtalk", endpoint=endpoint, auth_header=auth_header, **kwargs
    )


__all__ = ["DingTalkAdapter"]
