"""Wave-E Task 6: Mattermost channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def MattermostAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="mattermost", endpoint=endpoint, auth_header=auth_header, **kwargs
    )


__all__ = ["MattermostAdapter"]
