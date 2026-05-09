"""Wave-E Task 6: Feishu / Lark channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def FeishuAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="feishu", endpoint=endpoint, auth_header=auth_header, **kwargs
    )


__all__ = ["FeishuAdapter"]
