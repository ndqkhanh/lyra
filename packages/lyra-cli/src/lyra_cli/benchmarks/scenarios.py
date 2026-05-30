"""Predefined benchmark scenarios for Lyra subsystems.

Covers: model routing, memory operations, safety checks, skills execution,
swarm consensus, tool dispatch, and context compression.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ScenarioCategory(StrEnum):
    ROUTING = "routing"
    MEMORY = "memory"
    SAFETY = "safety"
    SKILLS = "skills"
    SWARM = "swarm"
    TOOLS = "tools"
    CONTEXT = "context"
    NETWORK = "network"


class LoadProfile(StrEnum):
    LIGHT = "light"        # 10 req/s
    MODERATE = "moderate"  # 100 req/s
    HEAVY = "heavy"        # 1000 req/s
    BURST = "burst"        # 5000 req/s spike


@dataclass(frozen=True)
class BenchmarkScenario:
    name: str
    category: ScenarioCategory
    description: str
    load_profile: LoadProfile
    duration_seconds: float
    warmup_seconds: float = 1.0
    target_p95_ms: float = 100.0
    min_throughput: float = 10.0
    tags: tuple[str, ...] = ()


# Predefined benchmark scenarios
SCENARIOS: tuple[BenchmarkScenario, ...] = (
    # ── Routing Benchmarks ──
    BenchmarkScenario(
        name="routing_policy_inference",
        category=ScenarioCategory.ROUTING,
        description="Measure RL policy network inference latency for routing decisions",
        load_profile=LoadProfile.MODERATE,
        duration_seconds=30.0,
        target_p95_ms=10.0,
        min_throughput=1000.0,
        tags=("routing", "policy", "inference"),
    ),
    BenchmarkScenario(
        name="routing_tier_selection",
        category=ScenarioCategory.ROUTING,
        description="Measure tier selection latency across 4 model tiers",
        load_profile=LoadProfile.HEAVY,
        duration_seconds=30.0,
        target_p95_ms=5.0,
        min_throughput=5000.0,
        tags=("routing", "tier", "selection"),
    ),
    BenchmarkScenario(
        name="routing_cascade_e2e",
        category=ScenarioCategory.ROUTING,
        description="End-to-end cascade routing with confidence estimation",
        load_profile=LoadProfile.MODERATE,
        duration_seconds=60.0,
        target_p95_ms=50.0,
        min_throughput=500.0,
        tags=("routing", "cascade", "e2e"),
    ),

    # ── Memory Benchmarks ──
    BenchmarkScenario(
        name="memory_read_latency",
        category=ScenarioCategory.MEMORY,
        description="Measure memory read latency across L0-L6 tiers",
        load_profile=LoadProfile.HEAVY,
        duration_seconds=30.0,
        target_p95_ms=20.0,
        min_throughput=2000.0,
        tags=("memory", "read", "latency"),
    ),
    BenchmarkScenario(
        name="memory_write_throughput",
        category=ScenarioCategory.MEMORY,
        description="Measure memory write throughput for high-throughput ingestion",
        load_profile=LoadProfile.HEAVY,
        duration_seconds=30.0,
        target_p95_ms=30.0,
        min_throughput=1000.0,
        tags=("memory", "write", "throughput"),
    ),
    BenchmarkScenario(
        name="memory_search_recall",
        category=ScenarioCategory.MEMORY,
        description="Measure memory semantic search latency and recall accuracy",
        load_profile=LoadProfile.MODERATE,
        duration_seconds=60.0,
        target_p95_ms=100.0,
        min_throughput=100.0,
        tags=("memory", "search", "recall"),
    ),
    BenchmarkScenario(
        name="memory_compaction_efficiency",
        category=ScenarioCategory.MEMORY,
        description="Measure memory compaction ratio and latency overhead",
        load_profile=LoadProfile.LIGHT,
        duration_seconds=120.0,
        target_p95_ms=500.0,
        min_throughput=5.0,
        tags=("memory", "compaction", "efficiency"),
    ),

    # ── Safety Benchmarks ──
    BenchmarkScenario(
        name="safety_four_gate_pipeline",
        category=ScenarioCategory.SAFETY,
        description="Throughput of 4-gate safety validation pipeline",
        load_profile=LoadProfile.HEAVY,
        duration_seconds=30.0,
        target_p95_ms=30.0,
        min_throughput=500.0,
        tags=("safety", "gate", "pipeline"),
    ),

    # ── Skills Benchmarks ──
    BenchmarkScenario(
        name="skills_load_latency",
        category=ScenarioCategory.SKILLS,
        description="Measure skill loading and initialization latency",
        load_profile=LoadProfile.LIGHT,
        duration_seconds=30.0,
        target_p95_ms=50.0,
        min_throughput=100.0,
        tags=("skills", "load", "latency"),
    ),
    BenchmarkScenario(
        name="skills_execution_throughput",
        category=ScenarioCategory.SKILLS,
        description="Measure skill execution throughput across 100+ skills",
        load_profile=LoadProfile.HEAVY,
        duration_seconds=60.0,
        target_p95_ms=100.0,
        min_throughput=500.0,
        tags=("skills", "execution", "throughput"),
    ),

    # ── Swarm Benchmarks ──
    BenchmarkScenario(
        name="swarm_raft_throughput",
        category=ScenarioCategory.SWARM,
        description="Raft consensus log replication throughput",
        load_profile=LoadProfile.MODERATE,
        duration_seconds=30.0,
        target_p95_ms=50.0,
        min_throughput=500.0,
        tags=("swarm", "raft", "throughput"),
    ),
    BenchmarkScenario(
        name="swarm_leader_election",
        category=ScenarioCategory.SWARM,
        description="Leader election latency during node failure",
        load_profile=LoadProfile.LIGHT,
        duration_seconds=60.0,
        target_p95_ms=200.0,
        min_throughput=1.0,
        tags=("swarm", "leader", "election"),
    ),
    BenchmarkScenario(
        name="swarm_fleet_autoscale",
        category=ScenarioCategory.SWARM,
        description="Fleet auto-scaling response time under load",
        load_profile=LoadProfile.BURST,
        duration_seconds=60.0,
        target_p95_ms=500.0,
        min_throughput=10.0,
        tags=("swarm", "fleet", "autoscale"),
    ),

    # ── Tool Benchmarks ──
    BenchmarkScenario(
        name="tools_dispatch_latency",
        category=ScenarioCategory.TOOLS,
        description="Tool dispatch latency across file/search/shell/git tools",
        load_profile=LoadProfile.MODERATE,
        duration_seconds=30.0,
        target_p95_ms=10.0,
        min_throughput=2000.0,
        tags=("tools", "dispatch", "latency"),
    ),
    BenchmarkScenario(
        name="tools_parallel_execution",
        category=ScenarioCategory.TOOLS,
        description="Parallel tool execution throughput via eager dispatch",
        load_profile=LoadProfile.HEAVY,
        duration_seconds=30.0,
        target_p95_ms=50.0,
        min_throughput=1000.0,
        tags=("tools", "parallel", "throughput"),
    ),

    # ── Context Benchmarks ──
    BenchmarkScenario(
        name="context_compression_ratio",
        category=ScenarioCategory.CONTEXT,
        description="Context compression ratio and latency for different strategies",
        load_profile=LoadProfile.LIGHT,
        duration_seconds=120.0,
        target_p95_ms=200.0,
        min_throughput=10.0,
        tags=("context", "compression", "ratio"),
    ),
    BenchmarkScenario(
        name="context_assembly_latency",
        category=ScenarioCategory.CONTEXT,
        description="Priority-based context assembly latency",
        load_profile=LoadProfile.MODERATE,
        duration_seconds=30.0,
        target_p95_ms=30.0,
        min_throughput=500.0,
        tags=("context", "assembly", "latency"),
    ),

    # ── Network Benchmarks ──
    BenchmarkScenario(
        name="network_mcp_transport",
        category=ScenarioCategory.NETWORK,
        description="MCP transport pool connection establishment and throughput",
        load_profile=LoadProfile.MODERATE,
        duration_seconds=30.0,
        target_p95_ms=100.0,
        min_throughput=100.0,
        tags=("network", "mcp", "transport"),
    ),
)


def get_scenarios_by_category(category: ScenarioCategory) -> list[BenchmarkScenario]:
    return [s for s in SCENARIOS if s.category == category]


def get_scenario_by_name(name: str) -> BenchmarkScenario | None:
    for s in SCENARIOS:
        if s.name == name:
            return s
    return None


def get_all_categories() -> list[ScenarioCategory]:
    return list(ScenarioCategory)
