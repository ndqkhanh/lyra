"""Wave-E Task 5a: Email channel adapter (IMAP + SMTP).

Lyra treats email as a polled, async channel: ``iter_inbound`` walks
``fetch_unseen`` once, ``send`` posts replies via SMTP. The wire
client is injectable so unit tests don't pull in :mod:`aioimaplib` /
:mod:`aiosmtplib` (opt-in via ``pip install lyra[email]``).

Threading model
---------------

We treat the IMAP ``Message-ID`` header as the thread id; outbound
``send`` sets ``In-Reply-To`` so providers thread the reply
correctly. Bare new-thread sends pass ``thread_id=""`` (empty).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

from ._errors import (
    AdapterAuthError as EmailAuthError,
    FeatureUnavailable,
)


__all__ = [
    "EmailAdapter",
    "EmailAuthError",
    "FeatureUnavailable",
]


def _default_client_factory(**_: Any) -> Any:  # pragma: no cover — smoke
    try:
        import aioimaplib  # type: ignore  # noqa: F401
        import aiosmtplib  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise FeatureUnavailable(
            "email channel requires the optional dep; "
            "install with `pip install lyra[email]`"
        ) from exc
    raise FeatureUnavailable(
        "email adapter ships its production IMAP+SMTP wrapper in v1.9.1; "
        "for now, inject your own via client_factory=…"
    )


@dataclass
class EmailAdapter:
    user: str
    password: str
    imap_host: str = "imap.gmail.com"
    smtp_host: str = "smtp.gmail.com"
    default_recipient: str = ""
    client_factory: Callable[..., Any] = _default_client_factory
    name: str = "email"

    def __post_init__(self) -> None:
        if not self.user or not self.password:
            raise FeatureUnavailable(
                "email adapter requires user + password; "
                "set $LYRA_EMAIL_USER / $LYRA_EMAIL_PASS or pass them"
            )
        self._client: Any | None = None
        self._reply_routes: dict[str, str] = {}

    async def start(self) -> None:
        if self._client is None:
            self._client = self.client_factory(
                user=self.user,
                password=self.password,
                imap_host=self.imap_host,
                smtp_host=self.smtp_host,
            )
        await self._client.login()

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.logout()

    async def send(self, *, thread_id: str, text: str) -> str:
        assert self._client is not None, "call start() first"
        recipient = self._reply_routes.get(thread_id) or self.default_recipient
        if not recipient:
            raise FeatureUnavailable(
                "email send: no recipient resolved for thread "
                f"{thread_id!r}; set default_recipient= or seed via inbound"
            )
        msg_id = await self._client.send_mail(
            to=recipient,
            subject=self._reply_subject(thread_id),
            body=text,
            in_reply_to=thread_id or None,
        )
        return f"email:{recipient}:{msg_id}"

    async def iter_inbound(self) -> AsyncIterator:
        from .base import Inbound

        assert self._client is not None, "call start() first"
        gen = await self._client.fetch_unseen()
        async for msg in gen:
            sender = str(msg.get("from") or "")
            mid = str(msg.get("message_id") or "")
            if mid and sender:
                self._reply_routes[mid] = sender
            yield Inbound(
                channel="email",
                thread_id=mid or sender,
                user_id=sender,
                text=str(msg.get("body") or ""),
                attachments=tuple(msg.get("attachments") or ()),
                received_at=float(msg.get("received_at") or 0.0)
                if isinstance(msg.get("received_at"), (int, float))
                else 0.0,
            )

    @staticmethod
    def _reply_subject(thread_id: str) -> str:
        return f"Re: {thread_id}" if thread_id else "lyra reply"
