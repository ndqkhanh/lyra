"""Wave-E Task 6: WhatsApp (Twilio relay) channel adapter."""
from __future__ import annotations

from ._http_base import HttpChannelAdapter


def WhatsAppAdapter(*, endpoint: str, auth_header: str = "", **kwargs):  # noqa: N802
    return HttpChannelAdapter(
        name="whatsapp", endpoint=endpoint, auth_header=auth_header, **kwargs
    )


__all__ = ["WhatsAppAdapter"]
