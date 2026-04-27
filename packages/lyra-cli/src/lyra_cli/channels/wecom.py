"""Wave-E Task 6: WeCom (WeChat Work) channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def WeComAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="wecom", endpoint=endpoint, auth_header=auth_header, **kwargs
    )


__all__ = ["WeComAdapter"]
