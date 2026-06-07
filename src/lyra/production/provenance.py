"""
AIBOM (AI Bill of Materials) cryptographic provenance tracking.

Provides tamper-evident provenance chains using Merkle trees,
linking agent outputs to their generating models, prompts,
tool calls, and data sources with cryptographic integrity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from lyra.production.models import (
    AIBOMEntry,
    ProvenanceChain,
    ProvenanceStatus,
    compute_entry_hash,
    compute_merkle_root,
)

logger = logging.getLogger(__name__)


class ProvenanceError(RuntimeError):
    """Raised when a provenance operation fails."""


class EntryNotFoundError(KeyError):
    """Raised when a requested provenance entry does not exist."""


class ProvenanceTracker:
    """Tracks and verifies AI Bill of Materials provenance chains.

    Each agent output is recorded as an AIBOMEntry containing
    metadata about the model, prompt, tools, and data sources
    used. Entries are linked into Merkle-tree chains for
    tamper-evident verification.
    """

    def __init__(self) -> None:
        self._entries: dict[str, AIBOMEntry] = {}
        self._chains: dict[str, ProvenanceChain] = {}
        self._lock = Lock()

    def _sha256(self, data: str) -> str:
        """Compute SHA-256 hex digest."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def record_output(
        self,
        output: str,
        model_info: dict[str, Any],
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        data_sources: list[dict[str, Any]] | None = None,
        parent_entry: str | None = None,
    ) -> AIBOMEntry:
        """Record an agent output with full provenance metadata.

        Args:
            output: The agent's output text.
            model_info: Model metadata (name, version, provider).
            prompt: The prompt that generated this output.
            tools: Tool calls made during generation.
            data_sources: Data sources used.
            parent_entry: Optional parent entry ID for chaining.

        Returns:
            The created AIBOMEntry.
        """
        entry_id = f"bom-{uuid.uuid4().hex[:12]}"
        output_hash = self._sha256(output)
        prompt_hash = self._sha256(prompt)

        entry = AIBOMEntry(
            entry_id=entry_id,
            output_hash=output_hash,
            model_info=model_info,
            prompt_hash=prompt_hash,
            tool_calls=tuple(tools or []),
            data_sources=tuple(data_sources or []),
            parent_entry=parent_entry,
            timestamp=datetime.now(timezone.utc),
        )

        with self._lock:
            self._entries[entry_id] = entry

        logger.info(
            "Recorded AIBOM entry %s (output hash: %s...)",
            entry_id,
            output_hash[:12],
        )
        return entry

    def build_chain(
        self,
        entry_ids: list[str] | None = None,
        filter_output_hash: str | None = None,
    ) -> ProvenanceChain:
        """Build a provenance chain from entries.

        Constructs a Merkle tree from the specified entries and
        computes the root hash for tamper-evident verification.

        Args:
            entry_ids: Specific entries to include (defaults to all).
            filter_output_hash: If provided, only include entries
                matching this output hash.

        Returns:
            A ProvenanceChain with Merkle root hash.

        Raises:
            ProvenanceError: If no entries are available.
        """
        with self._lock:
            all_entries = list(self._entries.values())

        if entry_ids is not None:
            entries = [
                e for e in all_entries if e.entry_id in entry_ids
            ]
        elif filter_output_hash is not None:
            entries = [
                e
                for e in all_entries
                if e.output_hash == filter_output_hash
            ]
        else:
            entries = all_entries

        if not entries:
            raise ProvenanceError(
                "Cannot build chain: no entries found"
            )

        # Sort by timestamp for deterministic ordering
        entries.sort(key=lambda e: e.timestamp)

        entries_tuple = tuple(entries)
        root_hash = compute_merkle_root(entries_tuple)

        chain_id = f"chain-{uuid.uuid4().hex[:12]}"
        chain = ProvenanceChain(
            chain_id=chain_id,
            entries=entries_tuple,
            root_hash=root_hash,
            verification_status=ProvenanceStatus.VERIFIED,
            created_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._chains[chain_id] = chain

        logger.info(
            "Built provenance chain %s with %d entries",
            chain_id,
            len(entries),
        )
        return chain

    def verify_chain(self, chain: ProvenanceChain) -> bool:
        """Verify a provenance chain for tamper evidence.

        Recomputes the Merkle root and compares it to the stored
        root. Also verifies each entry's hash is consistent with
        its data.

        Args:
            chain: The provenance chain to verify.

        Returns:
            True if the chain is intact, False if tampered.
        """
        # Verify each entry's hash matches its data
        for entry in chain.entries:
            expected_hash = compute_entry_hash(entry)
            actual_hash = self._sha256(
                json.dumps(
                    {
                        "entry_id": entry.entry_id,
                        "output_hash": entry.output_hash,
                        "model_info": entry.model_info,
                        "prompt_hash": entry.prompt_hash,
                        "tool_calls": list(entry.tool_calls),
                        "data_sources": list(entry.data_sources),
                        "parent_entry": entry.parent_entry,
                        "timestamp": entry.timestamp.isoformat(),
                    },
                    sort_keys=True,
                    default=str,
                )
            )
            if expected_hash != actual_hash:
                logger.warning(
                    "Entry %s hash mismatch in chain %s",
                    entry.entry_id,
                    chain.chain_id,
                )
                self._update_chain_status(chain.chain_id, ProvenanceStatus.TAMPERED)
                return False

        # Verify Merkle root
        expected_root = compute_merkle_root(chain.entries)
        if expected_root != chain.root_hash:
            logger.warning(
                "Merkle root mismatch in chain %s", chain.chain_id
            )
            self._update_chain_status(chain.chain_id, ProvenanceStatus.TAMPERED)
            return False

        self._update_chain_status(chain.chain_id, ProvenanceStatus.VERIFIED)
        logger.info("Chain %s verified successfully", chain.chain_id)
        return True

    def _update_chain_status(
        self, chain_id: str, status: ProvenanceStatus
    ) -> None:
        """Update the verification status of a stored chain."""
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return

            updated = ProvenanceChain(
                chain_id=chain.chain_id,
                entries=chain.entries,
                root_hash=chain.root_hash,
                verification_status=status,
                created_at=chain.created_at,
            )
            self._chains[chain_id] = updated

    def export_bom(self, chain: ProvenanceChain) -> dict[str, Any]:
        """Export a machine-readable AI Bill of Materials.

        Args:
            chain: The provenance chain to export.

        Returns:
            A serializable dictionary representing the AIBOM.
        """
        bom: dict[str, Any] = {
            "bom_specification": "aibom-1.0",
            "chain_id": chain.chain_id,
            "root_hash": chain.root_hash,
            "verification_status": chain.verification_status.name,
            "created_at": chain.created_at.isoformat(),
            "total_entries": len(chain.entries),
            "entries": [],
        }

        for entry in chain.entries:
            bom["entries"].append(
                {
                    "entry_id": entry.entry_id,
                    "output_hash": entry.output_hash,
                    "model_info": entry.model_info,
                    "prompt_hash": entry.prompt_hash,
                    "tool_calls": list(entry.tool_calls),
                    "data_sources": list(entry.data_sources),
                    "parent_entry": entry.parent_entry,
                    "timestamp": entry.timestamp.isoformat(),
                }
            )

        return bom

    def audit_trail(self, output_hash: str) -> list[AIBOMEntry]:
        """Get the full provenance trail for a specific output hash.

        Traces all entries related to the given output hash,
        including parent entries for chained outputs.

        Args:
            output_hash: The output hash to trace.

        Returns:
            A list of AIBOM entries in chronological order.
        """
        with self._lock:
            matching = [
                e
                for e in self._entries.values()
                if e.output_hash == output_hash
            ]

        if not matching:
            return []

        # Collect parent chain
        result: list[AIBOMEntry] = []
        seen: set[str] = set()

        def _collect_parent(entry: AIBOMEntry) -> None:
            if entry.entry_id in seen:
                return
            seen.add(entry.entry_id)
            result.append(entry)
            if entry.parent_entry:
                parent = self._entries.get(entry.parent_entry)
                if parent:
                    _collect_parent(parent)

        for entry in matching:
            _collect_parent(entry)

        result.sort(key=lambda e: e.timestamp)
        return result

    def detect_tampering(self, chain: ProvenanceChain) -> list[str]:
        """Identify modified entries in a provenance chain.

        Args:
            chain: The provenance chain to inspect.

        Returns:
            A list of descriptions of tampered or modified entries.
        """
        issues: list[str] = []

        # Check for missing entries
        with self._lock:
            for entry in chain.entries:
                stored = self._entries.get(entry.entry_id)
                if stored is None:
                    issues.append(
                        f"Entry {entry.entry_id} not found in storage"
                    )

        # Check Merkle root
        expected_root = compute_merkle_root(chain.entries)
        if expected_root != chain.root_hash:
            issues.append(
                f"Merkle root mismatch: expected {expected_root}, "
                f"got {chain.root_hash}"
            )

        # Check for orphaned parent references
        for entry in chain.entries:
            if entry.parent_entry:
                parent = self._entries.get(entry.parent_entry)
                if parent is None:
                    issues.append(
                        f"Entry {entry.entry_id} references missing "
                        f"parent {entry.parent_entry}"
                    )

        # Check chronological ordering
        for i in range(1, len(chain.entries)):
            if chain.entries[i].timestamp < chain.entries[i - 1].timestamp:
                issues.append(
                    f"Entry {chain.entries[i].entry_id} has timestamp "
                    f"before entry {chain.entries[i - 1].entry_id}"
                )

        if issues:
            self._update_chain_status(chain.chain_id, ProvenanceStatus.TAMPERED)
        else:
            self._update_chain_status(chain.chain_id, ProvenanceStatus.VERIFIED)

        return issues

    def get_entry(self, entry_id: str) -> AIBOMEntry:
        """Get an AIBOM entry by ID.

        Args:
            entry_id: The entry identifier.

        Returns:
            The AIBOMEntry.

        Raises:
            EntryNotFoundError: If the entry does not exist.
        """
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                raise EntryNotFoundError(f"Entry not found: {entry_id}")
            return entry

    def list_entries(self) -> list[AIBOMEntry]:
        """List all recorded provenance entries."""
        with self._lock:
            return list(self._entries.values())

    def list_chains(self) -> list[ProvenanceChain]:
        """List all built provenance chains."""
        with self._lock:
            return list(self._chains.values())


__all__ = [
    "ProvenanceError",
    "EntryNotFoundError",
    "ProvenanceTracker",
]
