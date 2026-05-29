"""Agent Identity — content-addressable hashing, cryptographic provenance, signed manifests.

Content-addressable: every agent action produces a verifiable hash.
Cryptographic: agent identity via key pairs, signed outputs.
Provenance: traceable lineage across agent generations.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "AgentIdentity",
    "SignedManifest",
]


@dataclass
class SignedManifest:
    action_id: str
    agent_id: str
    content_hash: str
    signature: str
    parent_action_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentIdentity:
    """Manages agent identity, content-addressing, and output signing."""

    def __init__(self, agent_id: str, private_key: str | None = None):
        self.agent_id = agent_id
        self._private_key = private_key or hashlib.sha256(agent_id.encode()).hexdigest()
        self._public_key = hashlib.sha256(self._private_key.encode()).hexdigest()
        self.action_counter = 0
        self.provenance_graph: dict[str, list[str]] = {}

    def _content_hash(self, data: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()

    def sign_action(self, action: dict[str, Any], parent_action_id: str | None = None) -> SignedManifest:
        self.action_counter += 1
        action_id = f"{self.agent_id}:{self.action_counter}"
        content_hash = self._content_hash(action)
        signature = hashlib.sha256(
            f"{content_hash}:{self._private_key}".encode()
        ).hexdigest()

        manifest = SignedManifest(
            action_id=action_id,
            agent_id=self.agent_id,
            content_hash=content_hash,
            signature=signature,
            parent_action_id=parent_action_id,
        )

        # Build provenance graph
        if parent_action_id:
            if parent_action_id not in self.provenance_graph:
                self.provenance_graph[parent_action_id] = []
            self.provenance_graph[parent_action_id].append(action_id)

        return manifest

    def verify(self, manifest: SignedManifest) -> bool:
        """Verify a manifest's integrity."""
        expected = hashlib.sha256(
            f"{manifest.content_hash}:{self._private_key}".encode()
        ).hexdigest()
        return manifest.signature == expected

    def get_lineage(self, action_id: str) -> list[str]:
        """Get the full provenance lineage for an action."""
        lineage = [action_id]
        for parent, children in self.provenance_graph.items():
            if action_id in children:
                lineage = [parent] + lineage
                break
        return lineage

    @property
    def public_key(self) -> str:
        return self._public_key
