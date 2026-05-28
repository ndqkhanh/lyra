"""
Memory Ingestion Pipeline - Auto-ingest from pentest results.

Features:
- Auto-ingest from pentest results
- Extract entities (IPs, domains, CVEs, exploits)
- Extract relations (host→service, vuln→exploit)
- Background processing queue
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class EntityType(Enum):
    """Types of entities to extract."""

    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    CVE = "cve"
    EXPLOIT = "exploit"
    SERVICE = "service"
    PORT = "port"
    CREDENTIAL = "credential"
    HASH = "hash"
    URL = "url"


class RelationType(Enum):
    """Types of relations between entities."""

    HOST_HAS_SERVICE = "host_has_service"
    SERVICE_HAS_VULNERABILITY = "service_has_vulnerability"
    VULNERABILITY_HAS_EXPLOIT = "vulnerability_has_exploit"
    EXPLOIT_YIELDS_CREDENTIAL = "exploit_yields_credential"
    HOST_CONNECTS_TO = "host_connects_to"


@dataclass
class Entity:
    """An extracted entity."""

    id: str = field(default_factory=lambda: str(uuid4()))
    type: EntityType = EntityType.IP_ADDRESS
    value: str = ""
    confidence: float = 1.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Relation:
    """A relation between entities."""

    id: str = field(default_factory=lambda: str(uuid4()))
    type: RelationType = RelationType.HOST_HAS_SERVICE
    source_id: str = ""
    target_id: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class IngestionJob:
    """A job in the ingestion queue."""

    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    source_type: str = "scan_result"  # scan_result, log, report, etc.
    priority: int = 5  # 1-10, higher = more urgent
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: datetime | None = None
    error: str | None = None


class EntityExtractor:
    """Extract entities from text."""

    # Regex patterns for entity extraction
    PATTERNS = {
        EntityType.IP_ADDRESS: r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        EntityType.DOMAIN: r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b",
        EntityType.CVE: r"CVE-\d{4}-\d{4,}",
        EntityType.PORT: r"\b(?:port|:\s*)(\d{1,5})\b",
        EntityType.HASH: r"\b[a-f0-9]{32,64}\b",  # MD5, SHA1, SHA256
        EntityType.URL: r"https?://[^\s]+",
    }

    def extract(self, text: str, source: str = "unknown") -> list[Entity]:
        """
        Extract entities from text.

        Args:
            text: Text to extract from
            source: Source identifier

        Returns:
            List of extracted entities
        """
        entities = []
        seen = set()

        for entity_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(0).lower()

                # Deduplicate
                key = f"{entity_type.value}:{value}"
                if key in seen:
                    continue
                seen.add(key)

                # Validate
                if not self._validate_entity(entity_type, value):
                    continue

                entities.append(
                    Entity(
                        type=entity_type,
                        value=value,
                        source=source,
                        confidence=self._calculate_confidence(entity_type, text, value),
                    )
                )

        return entities

    def _validate_entity(self, entity_type: EntityType, value: str) -> bool:
        """Validate extracted entity."""
        if entity_type == EntityType.IP_ADDRESS:
            # Check valid IP range
            parts = value.split(".")
            return all(0 <= int(p) <= 255 for p in parts)

        elif entity_type == EntityType.PORT:
            # Check valid port range
            try:
                port = int(value)
                return 1 <= port <= 65535
            except ValueError:
                return False

        return True

    def _calculate_confidence(self, entity_type: EntityType, text: str, value: str) -> float:
        """Calculate confidence score for entity."""
        confidence = 1.0

        # Lower confidence for common false positives
        if entity_type == EntityType.IP_ADDRESS:
            if value.startswith("0.") or value.startswith("255."):
                confidence *= 0.5

        elif entity_type == EntityType.DOMAIN:
            # Lower confidence for localhost, example domains
            if any(x in value for x in ["localhost", "example.com", "test.com"]):
                confidence *= 0.3

        return confidence


class RelationExtractor:
    """Extract relations between entities."""

    def extract(
        self,
        text: str,
        entities: list[Entity],
    ) -> list[Relation]:
        """
        Extract relations from text and entities.

        Args:
            text: Source text
            entities: Extracted entities

        Returns:
            List of relations
        """
        relations = []

        # Build entity index
        entity_by_value = {e.value: e for e in entities}

        # Extract host→service relations
        # Pattern: "192.168.1.1:80" or "192.168.1.1 port 80"
        for ip_entity in [e for e in entities if e.type == EntityType.IP_ADDRESS]:
            # Find nearby ports
            ip_pos = text.find(ip_entity.value)
            if ip_pos == -1:
                continue

            # Look for port in next 50 chars
            context = text[ip_pos : ip_pos + 50]
            port_match = re.search(r":(\d{1,5})|port\s+(\d{1,5})", context, re.IGNORECASE)

            if port_match:
                port = port_match.group(1) or port_match.group(2)
                relations.append(
                    Relation(
                        type=RelationType.HOST_HAS_SERVICE,
                        source_id=ip_entity.id,
                        target_id=port,  # Will be resolved later
                        confidence=0.9,
                        metadata={"port": port},
                    )
                )

        # Extract vuln→exploit relations
        # Pattern: CVE mentioned near "exploit" keyword
        for cve_entity in [e for e in entities if e.type == EntityType.CVE]:
            cve_pos = text.find(cve_entity.value)
            if cve_pos == -1:
                continue

            # Look for exploit mention in nearby text
            context_start = max(0, cve_pos - 100)
            context_end = min(len(text), cve_pos + 100)
            context = text[context_start:context_end]

            if re.search(r"exploit|metasploit|poc", context, re.IGNORECASE):
                relations.append(
                    Relation(
                        type=RelationType.VULNERABILITY_HAS_EXPLOIT,
                        source_id=cve_entity.id,
                        target_id="",  # Will be filled when exploit entity is found
                        confidence=0.7,
                    )
                )

        return relations


class IngestionQueue:
    """Background processing queue for ingestion jobs."""

    def __init__(self, max_workers: int = 4):
        """
        Initialize ingestion queue.

        Args:
            max_workers: Maximum concurrent workers
        """
        self.max_workers = max_workers
        self.jobs: dict[str, IngestionJob] = {}
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self._running = False

    async def add_job(
        self,
        content: str,
        source_type: str = "scan_result",
        priority: int = 5,
    ) -> IngestionJob:
        """
        Add a job to the queue.

        Args:
            content: Content to ingest
            source_type: Type of source
            priority: Priority (1-10)

        Returns:
            Created job
        """
        job = IngestionJob(
            content=content,
            source_type=source_type,
            priority=priority,
        )
        self.jobs[job.id] = job
        return job

    async def process_job(self, job: IngestionJob) -> dict[str, Any]:
        """
        Process a single job.

        Args:
            job: Job to process

        Returns:
            Processing results
        """
        job.status = "processing"

        try:
            # Extract entities
            entities = self.entity_extractor.extract(job.content, source=job.source_type)

            # Extract relations
            relations = self.relation_extractor.extract(job.content, entities)

            job.status = "completed"
            job.processed_at = datetime.now()

            return {
                "job_id": job.id,
                "entities": entities,
                "relations": relations,
                "entity_count": len(entities),
                "relation_count": len(relations),
            }

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.processed_at = datetime.now()
            raise

    async def start(self):
        """Start processing queue."""
        self._running = True

        while self._running:
            # Get pending jobs sorted by priority
            pending = [j for j in self.jobs.values() if j.status == "pending"]
            pending.sort(key=lambda j: j.priority, reverse=True)

            if not pending:
                await asyncio.sleep(1)
                continue

            # Process jobs in parallel
            tasks = []
            for job in pending[: self.max_workers]:
                tasks.append(self.process_job(job))

            await asyncio.gather(*tasks, return_exceptions=True)

    def stop(self):
        """Stop processing queue."""
        self._running = False

    def get_stats(self) -> dict[str, int]:
        """Get queue statistics."""
        return {
            "total": len(self.jobs),
            "pending": sum(1 for j in self.jobs.values() if j.status == "pending"),
            "processing": sum(1 for j in self.jobs.values() if j.status == "processing"),
            "completed": sum(1 for j in self.jobs.values() if j.status == "completed"),
            "failed": sum(1 for j in self.jobs.values() if j.status == "failed"),
        }
