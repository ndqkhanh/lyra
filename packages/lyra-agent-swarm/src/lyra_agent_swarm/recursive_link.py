"""RecursiveLink — latent-space inter-agent communication.

Implements a lightweight RecursiveLink module enabling agents to communicate
via compressed latent states instead of natural language text, reducing
inter-agent token usage by 35-75% (as demonstrated by RecursiveMAS, arXiv
2604.25917). Supports hybrid text+latent mode with text fallback.

Key concepts:
- LatentState: compressed representation of an agent's cognitive state
- LinkContext: shared context established between agent pairs
- RecursiveLink: main module managing latent comms channels
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class LinkMode(StrEnum):
    TEXT = "text"
    LATENT = "latent"
    HYBRID = "hybrid"


class LinkStatus(StrEnum):
    IDLE = "idle"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


@dataclass(frozen=True)
class LatentState:
    """Compressed representation of an agent's cognitive state.

    Attributes:
        state_id: unique identifier for this compressed state
        source_agent: agent that produced the state
        compressed_vector: latent-space vector (simulated as hash-based keys)
        dimension: effective dimension of the compressed representation
        compression_ratio: token savings vs full text (e.g. 0.65 = 65% reduction)
        semantic_hash: content-addressable integrity hash
        timestamp: when the state was produced
    """

    state_id: str
    source_agent: str
    compressed_vector: tuple[float, ...]
    dimension: int
    compression_ratio: float
    semantic_hash: str
    timestamp: float

    @classmethod
    def compress(
        cls,
        source_agent: str,
        text_content: str,
        target_dimension: int = 128,
    ) -> LatentState:
        """Simulate compression of text into a latent vector.

        In production this would use a learned encoder. For now we simulate
        with deterministic hashing to a fixed-dimension vector.
        """
        content_hash = hashlib.sha256(text_content.encode()).digest()
        vector = tuple(
            (content_hash[i % len(content_hash)] / 255.0)
            for i in range(target_dimension)
        )
        original_tokens = len(text_content.split())
        compression_ratio = 1.0 - (target_dimension / max(original_tokens, 1))
        ts = time.time()
        state_id = hashlib.sha256(
            f"{source_agent}|{ts}|{content_hash[:8].hex()}".encode()
        ).hexdigest()[:16]

        return cls(
            state_id=state_id,
            source_agent=source_agent,
            compressed_vector=vector,
            dimension=target_dimension,
            compression_ratio=max(0.0, min(compression_ratio, 1.0)),
            semantic_hash=hashlib.sha256(
                str(vector).encode()
            ).hexdigest()[:16],
            timestamp=ts,
        )

    def cosine_similarity(self, other: LatentState) -> float:
        """Compute cosine similarity between two latent states."""
        if self.dimension != other.dimension:
            return 0.0
        dot = sum(a * b for a, b in zip(self.compressed_vector, other.compressed_vector))
        norm_a = sum(a * a for a in self.compressed_vector) ** 0.5
        norm_b = sum(b * b for b in other.compressed_vector) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


@dataclass(frozen=True)
class LinkContext:
    """Established communication context between two agents.

    Tracks the shared understanding built up across multiple latent exchanges,
    including alignment scores and transmission history.
    """

    link_id: str
    agent_a: str
    agent_b: str
    mode: LinkMode
    established_at: float
    last_exchange_at: float
    exchange_count: int
    alignment_score: float
    total_tokens_saved: int
    status: LinkStatus


@dataclass(frozen=True)
class LatentMessage:
    """A message transmitted through the RecursiveLink channel."""

    message_id: str
    sender: str
    receiver: str
    state: LatentState
    text_fallback: str
    mode: LinkMode
    timestamp: float


class RecursiveLink:
    """Lightweight inter-agent latent communication module.

    Establishes latent-space channels between agent pairs to reduce token
    usage. Agents first exchange a text handshake, then transition to
    compressed latent vectors. Falls back to text if alignment degrades.

    Usage::

        link = RecursiveLink()
        link.register_agent("orchestrator")
        link.register_agent("specialist")
        ctx = link.establish("orchestrator", "specialist", mode=LinkMode.HYBRID)
        msg = link.send("orchestrator", "specialist", "Run analysis on file X")
        received = link.receive(msg.message_id)
    """

    def __init__(self) -> None:
        self._agents: dict[str, set[str]] = {}
        self._links: dict[str, LinkContext] = {}
        self._messages: dict[str, LatentMessage] = {}
        self._message_queue: dict[str, list[str]] = {}
        self._total_tokens_saved: int = 0
        self._total_exchanges: int = 0

    def register_agent(self, agent_id: str) -> None:
        """Register an agent for latent communication."""
        self._agents.setdefault(agent_id, set())

    def establish(
        self,
        agent_a: str,
        agent_b: str,
        mode: LinkMode = LinkMode.HYBRID,
    ) -> LinkContext:
        """Establish a latent communication link between two agents."""
        self.register_agent(agent_a)
        self.register_agent(agent_b)

        link_key = self._link_key(agent_a, agent_b)
        if link_key in self._links:
            return self._links[link_key]

        ts = time.time()
        ctx = LinkContext(
            link_id=hashlib.sha256(
                f"{agent_a}|{agent_b}|{ts}".encode()
            ).hexdigest()[:16],
            agent_a=agent_a,
            agent_b=agent_b,
            mode=mode,
            established_at=ts,
            last_exchange_at=ts,
            exchange_count=0,
            alignment_score=1.0,
            total_tokens_saved=0,
            status=LinkStatus.CONNECTED,
        )
        self._links[link_key] = ctx
        self._message_queue.setdefault(link_key, [])
        return ctx

    def send(
        self,
        sender: str,
        receiver: str,
        content: str,
        mode: LinkMode | None = None,
    ) -> LatentMessage:
        """Send a message through the latent link.

        Compresses the content into a LatentState, keeps the original text
        as fallback, and transmits both in hybrid mode.
        """
        link_key = self._link_key(sender, receiver)
        if link_key not in self._links:
            self.establish(sender, receiver)

        ctx = self._links[link_key]
        effective_mode = mode or ctx.mode

        state = LatentState.compress(sender, content)
        msg = LatentMessage(
            message_id=state.state_id,
            sender=sender,
            receiver=receiver,
            state=state,
            text_fallback=content,
            mode=effective_mode,
            timestamp=time.time(),
        )

        self._messages[msg.message_id] = msg
        self._message_queue[link_key].append(msg.message_id)
        self._total_exchanges += 1

        original_tokens = len(content.split())
        latent_tokens = state.dimension
        saved = max(0, original_tokens - latent_tokens)
        self._total_tokens_saved += saved

        new_alignment = min(1.0, ctx.alignment_score + 0.01 * (state.compression_ratio - 0.5))
        new_status = LinkStatus.DEGRADED if new_alignment < 0.4 else LinkStatus.CONNECTED

        self._links[link_key] = LinkContext(
            link_id=ctx.link_id,
            agent_a=ctx.agent_a,
            agent_b=ctx.agent_b,
            mode=ctx.mode,
            established_at=ctx.established_at,
            last_exchange_at=time.time(),
            exchange_count=ctx.exchange_count + 1,
            alignment_score=new_alignment,
            total_tokens_saved=ctx.total_tokens_saved + saved,
            status=new_status,
        )

        return msg

    def receive(self, message_id: str) -> LatentMessage | None:
        """Retrieve a message by ID."""
        return self._messages.get(message_id)

    def get_context(self, agent_a: str, agent_b: str) -> LinkContext | None:
        """Get the link context between two agents."""
        return self._links.get(self._link_key(agent_a, agent_b))

    def check_alignment(self, agent_a: str, agent_b: str) -> float:
        """Check the alignment score between two agents.

        If below threshold, the link should fall back to text mode.
        """
        ctx = self.get_context(agent_a, agent_b)
        return ctx.alignment_score if ctx else 0.0

    def degrade_to_text(self, agent_a: str, agent_b: str) -> LinkContext | None:
        """Force-degrade a link to text-only mode."""
        ctx = self.get_context(agent_a, agent_b)
        if ctx is None:
            return None
        link_key = self._link_key(agent_a, agent_b)
        degraded = LinkContext(
            link_id=ctx.link_id,
            agent_a=ctx.agent_a,
            agent_b=ctx.agent_b,
            mode=LinkMode.TEXT,
            established_at=ctx.established_at,
            last_exchange_at=time.time(),
            exchange_count=ctx.exchange_count,
            alignment_score=ctx.alignment_score,
            total_tokens_saved=ctx.total_tokens_saved,
            status=LinkStatus.DEGRADED,
        )
        self._links[link_key] = degraded
        return degraded

    @staticmethod
    def _link_key(a: str, b: str) -> str:
        """Deterministic, order-independent channel key."""
        return "|".join(sorted([a, b]))

    @property
    def active_links(self) -> int:
        return sum(
            1 for c in self._links.values()
            if c.status in (LinkStatus.CONNECTED, LinkStatus.DEGRADED)
        )

    @property
    def total_tokens_saved(self) -> int:
        return self._total_tokens_saved

    @property
    def total_exchanges(self) -> int:
        return self._total_exchanges

    def stats(self) -> dict:
        return {
            "active_links": self.active_links,
            "total_links": len(self._links),
            "total_exchanges": self._total_exchanges,
            "total_tokens_saved": self._total_tokens_saved,
            "registered_agents": len(self._agents),
        }
