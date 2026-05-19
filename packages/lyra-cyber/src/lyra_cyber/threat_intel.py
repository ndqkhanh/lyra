"""
Threat Intelligence - Threat data aggregation and analysis.

Features:
- IOC (Indicator of Compromise) management
- Threat feed integration
- Threat actor profiling
- TTPs (Tactics, Techniques, Procedures) tracking
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class IOCType(Enum):
    """Indicator of Compromise types."""

    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH = "file_hash"
    EMAIL = "email"
    CVE = "cve"


@dataclass
class IOC:
    """Indicator of Compromise."""

    ioc_id: str
    ioc_type: IOCType
    value: str
    confidence: float  # 0.0-1.0
    first_seen: datetime
    last_seen: datetime
    threat_actor: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ThreatActor:
    """Threat actor profile."""

    actor_id: str
    name: str
    aliases: List[str]
    motivation: str  # financial, espionage, hacktivism
    sophistication: str  # low, medium, high, advanced
    ttps: List[str]  # MITRE ATT&CK technique IDs
    known_iocs: List[str] = field(default_factory=list)


class ThreatIntelligence:
    """
    Threat intelligence system.

    Features:
    - IOC tracking
    - Threat actor profiling
    - Intelligence enrichment
    """

    def __init__(self):
        """Initialize threat intelligence."""
        self.iocs: Dict[str, IOC] = {}
        self.threat_actors: Dict[str, ThreatActor] = {}

    def add_ioc(self, ioc: IOC):
        """
        Add IOC to database.

        Args:
            ioc: Indicator of Compromise
        """
        self.iocs[ioc.ioc_id] = ioc

    def check_ioc(self, value: str, ioc_type: IOCType) -> Optional[IOC]:
        """
        Check if value is a known IOC.

        Args:
            value: Value to check
            ioc_type: IOC type

        Returns:
            Matching IOC or None
        """
        for ioc in self.iocs.values():
            if ioc.ioc_type == ioc_type and ioc.value == value:
                return ioc
        return None

    def enrich_ioc(self, ioc_id: str) -> Dict[str, any]:
        """
        Enrich IOC with threat intelligence.

        Args:
            ioc_id: IOC ID

        Returns:
            Enriched data
        """
        if ioc_id not in self.iocs:
            raise ValueError(f"IOC not found: {ioc_id}")

        ioc = self.iocs[ioc_id]

        # Find related threat actors
        related_actors = []
        for actor in self.threat_actors.values():
            if ioc_id in actor.known_iocs:
                related_actors.append(actor.name)

        return {
            "ioc_id": ioc_id,
            "value": ioc.value,
            "type": ioc.ioc_type.value,
            "confidence": ioc.confidence,
            "threat_actors": related_actors,
            "tags": ioc.tags,
            "first_seen": ioc.first_seen.isoformat(),
            "last_seen": ioc.last_seen.isoformat(),
        }

    def add_threat_actor(self, actor: ThreatActor):
        """
        Add threat actor profile.

        Args:
            actor: Threat actor
        """
        self.threat_actors[actor.actor_id] = actor

    def get_actor_profile(self, actor_id: str) -> Dict[str, any]:
        """
        Get threat actor profile.

        Args:
            actor_id: Actor ID

        Returns:
            Actor profile
        """
        if actor_id not in self.threat_actors:
            raise ValueError(f"Actor not found: {actor_id}")

        actor = self.threat_actors[actor_id]

        return {
            "actor_id": actor.actor_id,
            "name": actor.name,
            "aliases": actor.aliases,
            "motivation": actor.motivation,
            "sophistication": actor.sophistication,
            "ttps": actor.ttps,
            "known_iocs": len(actor.known_iocs),
        }

    def correlate_iocs(self, ioc_ids: List[str]) -> Dict[str, any]:
        """
        Correlate multiple IOCs.

        Args:
            ioc_ids: List of IOC IDs

        Returns:
            Correlation analysis
        """
        iocs = [self.iocs[iid] for iid in ioc_ids if iid in self.iocs]

        # Find common threat actors
        common_actors = set()
        for ioc in iocs:
            if ioc.threat_actor:
                common_actors.add(ioc.threat_actor)

        # Find common tags
        all_tags = []
        for ioc in iocs:
            all_tags.extend(ioc.tags)

        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "ioc_count": len(iocs),
            "common_threat_actors": list(common_actors),
            "common_tags": [tag for tag, count in tag_counts.items() if count > 1],
            "confidence_avg": sum(ioc.confidence for ioc in iocs) / len(iocs)
            if iocs
            else 0,
        }

    def get_stats(self) -> Dict[str, any]:
        """
        Get threat intelligence statistics.

        Returns:
            Statistics
        """
        return {
            "total_iocs": len(self.iocs),
            "total_threat_actors": len(self.threat_actors),
            "iocs_by_type": self._count_by_type(),
            "high_confidence_iocs": sum(
                1 for ioc in self.iocs.values() if ioc.confidence > 0.8
            ),
        }

    def _count_by_type(self) -> Dict[str, int]:
        """
        Count IOCs by type.

        Returns:
            Type counts
        """
        counts = {}
        for ioc in self.iocs.values():
            type_name = ioc.ioc_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
