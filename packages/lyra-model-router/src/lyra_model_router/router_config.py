"""Routing rules, policies, and configuration management.

Defines RouterConfig with routing policies, model registry with health checking,
fallback rules, and hot-reloadable configuration via JSON/YAML serialization.
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Sequence


class PolicyType(Enum):
    """Types of routing policies."""
    DOMAIN_ROUTING = "domain_routing"
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_FIRST = "performance_first"
    BALANCED = "balanced"


@dataclass(frozen=True)
class RoutingPolicy:
    """A named routing policy with its configuration."""
    name: str
    policy_type: PolicyType
    domain: str = ""
    preferred_models: tuple[str, ...] = field(default_factory=tuple)
    max_cost_per_task: float = float("inf")
    min_reasoning_score: float = 0.0
    min_coding_score: float = 0.0
    require_verification: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelRegistryEntry:
    """An entry in the model registry with health/status info."""
    model_id: str
    tier: str
    enabled: bool = True
    max_concurrency: int = 10
    rate_limit_per_minute: int = 60
    timeout_seconds: float = 60.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthStatus:
    """Health status for a registered model."""
    model_id: str
    available: bool = True
    healthy: bool = True
    last_check: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p99_ms: float = 0.0
    error_rate: float = 0.0
    consecutive_failures: int = 0


@dataclass(frozen=True)
class FallbackRule:
    """A fallback rule specifying what to do when a model fails."""
    primary_model: str
    fallback_models: tuple[str, ...] = field(default_factory=tuple)
    fallback_strategy: str = "ordered"  # ordered, random, cheapest, fastest
    max_retries: int = 2
    timeout_before_fallback: float = 30.0


DEFAULT_POLICIES: tuple[RoutingPolicy, ...] = (
    RoutingPolicy(
        name="reasoning",
        policy_type=PolicyType.DOMAIN_ROUTING,
        domain="reasoning",
        preferred_models=("claude-opus-4.7", "claude-sonnet-4.6"),
        min_reasoning_score=0.85,
        require_verification=True,
        metadata={"description": "Deep reasoning tasks require Opus or Sonnet"},
    ),
    RoutingPolicy(
        name="coding",
        policy_type=PolicyType.DOMAIN_ROUTING,
        domain="coding",
        preferred_models=("claude-sonnet-4.6", "claude-haiku-4.5"),
        min_coding_score=0.65,
        metadata={"description": "Coding tasks balanced for cost/quality"},
    ),
    RoutingPolicy(
        name="quick",
        policy_type=PolicyType.PERFORMANCE_FIRST,
        domain="quick",
        preferred_models=("claude-haiku-4.5", "deepseek-v4-pro"),
        max_cost_per_task=0.01,
        metadata={"description": "Quick tasks prefer speed and low cost"},
    ),
    RoutingPolicy(
        name="research",
        policy_type=PolicyType.BALANCED,
        domain="research",
        preferred_models=("claude-opus-4.7", "claude-sonnet-4.6"),
        min_reasoning_score=0.80,
        require_verification=True,
        metadata={"description": "Research needs deep reasoning + verification"},
    ),
    RoutingPolicy(
        name="economy",
        policy_type=PolicyType.COST_OPTIMIZED,
        domain="economy",
        preferred_models=("deepseek-v4-pro", "claude-haiku-4.5"),
        max_cost_per_task=0.005,
        metadata={"description": "Economy routing for budget-constrained tasks"},
    ),
)

DEFAULT_MODEL_REGISTRY: tuple[ModelRegistryEntry, ...] = (
    ModelRegistryEntry(model_id="claude-opus-4.7", tier="premium", max_concurrency=5, timeout_seconds=120.0),
    ModelRegistryEntry(model_id="claude-sonnet-4.6", tier="standard", max_concurrency=20, timeout_seconds=90.0),
    ModelRegistryEntry(model_id="claude-haiku-4.5", tier="economy", max_concurrency=50, timeout_seconds=30.0),
    ModelRegistryEntry(model_id="deepseek-v4-pro", tier="economy", max_concurrency=30, timeout_seconds=60.0),
)

DEFAULT_FALLBACK_RULES: tuple[FallbackRule, ...] = (
    FallbackRule(
        primary_model="claude-opus-4.7",
        fallback_models=("claude-sonnet-4.6", "deepseek-v4-pro"),
    ),
    FallbackRule(
        primary_model="claude-sonnet-4.6",
        fallback_models=("claude-haiku-4.5", "deepseek-v4-pro"),
    ),
    FallbackRule(
        primary_model="claude-haiku-4.5",
        fallback_models=("deepseek-v4-pro",),
    ),
    FallbackRule(
        primary_model="deepseek-v4-pro",
        fallback_models=("claude-haiku-4.5",),
    ),
)

_CONFIG_VERSION: str = "0.1.0"


class RouterConfig:
    """Manages routing configuration with hot-reload support.

    Stores routing policies, model registry, fallback rules, and health status.
    Supports JSON serialization/deserialization and hot-reload via file watching.
    """

    def __init__(
        self,
        policies: Sequence[RoutingPolicy] | None = None,
        model_registry: Sequence[ModelRegistryEntry] | None = None,
        fallback_rules: Sequence[FallbackRule] | None = None,
    ) -> None:
        self._version = _CONFIG_VERSION
        self._policies: dict[str, RoutingPolicy] = {}
        self._model_registry: dict[str, ModelRegistryEntry] = {}
        self._fallback_rules: dict[str, FallbackRule] = {}
        self._health: dict[str, HealthStatus] = {}
        self._load_timestamp: float = time.time()

        for policy in (policies or DEFAULT_POLICIES):
            self._policies[policy.name] = policy
        for entry in (model_registry or DEFAULT_MODEL_REGISTRY):
            self._model_registry[entry.model_id] = entry
            self._health[entry.model_id] = HealthStatus(model_id=entry.model_id, last_check=time.time())
        for rule in (fallback_rules or DEFAULT_FALLBACK_RULES):
            self._fallback_rules[rule.primary_model] = rule

    @property
    def version(self) -> str:
        return self._version

    @property
    def load_timestamp(self) -> float:
        return self._load_timestamp

    # ── Policies ──────────────────────────────────────────────────────

    @property
    def policies(self) -> dict[str, RoutingPolicy]:
        return dict(self._policies)

    def get_policy(self, name: str) -> RoutingPolicy | None:
        return self._policies.get(name)

    def add_policy(self, policy: RoutingPolicy) -> None:
        self._policies[policy.name] = policy

    def remove_policy(self, name: str) -> bool:
        return self._policies.pop(name, None) is not None

    def list_policies(self) -> list[str]:
        return list(self._policies.keys())

    def find_policies_by_domain(self, domain: str) -> list[RoutingPolicy]:
        return [p for p in self._policies.values() if p.domain == domain]

    # ── Model Registry ────────────────────────────────────────────────

    @property
    def model_registry(self) -> dict[str, ModelRegistryEntry]:
        return dict(self._model_registry)

    def get_registry_entry(self, model_id: str) -> ModelRegistryEntry | None:
        return self._model_registry.get(model_id)

    def register_model(self, entry: ModelRegistryEntry) -> None:
        self._model_registry[entry.model_id] = entry
        if entry.model_id not in self._health:
            self._health[entry.model_id] = HealthStatus(model_id=entry.model_id)

    def unregister_model(self, model_id: str) -> bool:
        self._health.pop(model_id, None)
        return self._model_registry.pop(model_id, None) is not None

    def list_registered_models(self) -> list[str]:
        return list(self._model_registry.keys())

    def set_model_enabled(self, model_id: str, enabled: bool) -> bool:
        entry = self._model_registry.get(model_id)
        if entry is None:
            return False
        self._model_registry[model_id] = ModelRegistryEntry(
            model_id=entry.model_id,
            tier=entry.tier,
            enabled=enabled,
            max_concurrency=entry.max_concurrency,
            rate_limit_per_minute=entry.rate_limit_per_minute,
            timeout_seconds=entry.timeout_seconds,
            metadata=entry.metadata,
        )
        return True

    # ── Fallback Rules ────────────────────────────────────────────────

    @property
    def fallback_rules(self) -> dict[str, FallbackRule]:
        return dict(self._fallback_rules)

    def get_fallback_rule(self, model_id: str) -> FallbackRule | None:
        return self._fallback_rules.get(model_id)

    def set_fallback_rule(self, rule: FallbackRule) -> None:
        self._fallback_rules[rule.primary_model] = rule

    def remove_fallback_rule(self, model_id: str) -> bool:
        return self._fallback_rules.pop(model_id, None) is not None

    def get_fallback_chain(self, model_id: str) -> list[str]:
        """Get the ordered fallback chain for a primary model."""
        rule = self._fallback_rules.get(model_id)
        if rule is None:
            return [model_id]
        chain: list[str] = [rule.primary_model]
        for fb in rule.fallback_models:
            chain.append(fb)
            sub_rule = self._fallback_rules.get(fb)
            if sub_rule is not None:
                chain.extend(m for m in sub_rule.fallback_models if m not in chain)
        return chain

    # ── Health ────────────────────────────────────────────────────────

    @property
    def health(self) -> dict[str, HealthStatus]:
        return dict(self._health)

    def get_health(self, model_id: str) -> HealthStatus | None:
        return self._health.get(model_id)

    def update_health(self, status: HealthStatus) -> None:
        self._health[status.model_id] = status

    def report_failure(self, model_id: str) -> None:
        current = self._health.get(model_id)
        if current is None:
            self._health[model_id] = HealthStatus(
                model_id=model_id,
                healthy=False,
                available=False,
                last_check=time.time(),
                consecutive_failures=1,
            )
        else:
            self._health[model_id] = HealthStatus(
                model_id=current.model_id,
                available=current.consecutive_failures < 3,
                healthy=False,
                last_check=time.time(),
                latency_p50_ms=current.latency_p50_ms,
                latency_p99_ms=current.latency_p99_ms,
                error_rate=(current.error_rate * current.consecutive_failures + 1.0) / (current.consecutive_failures + 1),
                consecutive_failures=current.consecutive_failures + 1,
            )

    def report_success(self, model_id: str, latency_ms: float = 0.0) -> None:
        self._health[model_id] = HealthStatus(
            model_id=model_id,
            available=True,
            healthy=True,
            last_check=time.time(),
            latency_p50_ms=latency_ms,
            latency_p99_ms=latency_ms,
            error_rate=0.0,
            consecutive_failures=0,
        )

    def get_available_models(self) -> list[str]:
        """Return list of model IDs that are enabled and healthy."""
        available: list[str] = []
        for model_id, entry in self._model_registry.items():
            health = self._health.get(model_id)
            if entry.enabled and (health is None or health.available):
                available.append(model_id)
        return available

    # ── Hot Reload ────────────────────────────────────────────────────

    def hot_reload(self, config_data: dict[str, Any]) -> list[str]:
        """Apply a new configuration, returning list of changes."""
        changes: list[str] = []
        if "policies" in config_data:
            old_policies = set(self._policies.keys())
            self._policies.clear()
            for p_data in config_data["policies"]:
                if isinstance(p_data, dict):
                    policy = RoutingPolicy(
                        name=p_data.get("name", ""),
                        policy_type=PolicyType(p_data.get("policy_type", PolicyType.BALANCED.value)),
                        domain=p_data.get("domain", ""),
                        preferred_models=tuple(p_data.get("preferred_models", [])),
                        max_cost_per_task=p_data.get("max_cost_per_task", float("inf")),
                        min_reasoning_score=p_data.get("min_reasoning_score", 0.0),
                        min_coding_score=p_data.get("min_coding_score", 0.0),
                        require_verification=p_data.get("require_verification", False),
                        metadata=p_data.get("metadata", {}),
                    )
                    self._policies[policy.name] = policy
            new_policies = set(self._policies.keys())
            changes.append(f"policies: added={new_policies - old_policies}, removed={old_policies - new_policies}")
        if "model_registry" in config_data:
            self._model_registry.clear()
            for m_data in config_data["model_registry"]:
                if isinstance(m_data, dict):
                    entry = ModelRegistryEntry(
                        model_id=m_data.get("model_id", ""),
                        tier=m_data.get("tier", ""),
                        enabled=m_data.get("enabled", True),
                        max_concurrency=m_data.get("max_concurrency", 10),
                        rate_limit_per_minute=m_data.get("rate_limit_per_minute", 60),
                        timeout_seconds=m_data.get("timeout_seconds", 60.0),
                        metadata=m_data.get("metadata", {}),
                    )
                    self._model_registry[entry.model_id] = entry
            changes.append("model_registry: reloaded")
        if "fallback_rules" in config_data:
            self._fallback_rules.clear()
            for f_data in config_data["fallback_rules"]:
                if isinstance(f_data, dict):
                    rule = FallbackRule(
                        primary_model=f_data.get("primary_model", ""),
                        fallback_models=tuple(f_data.get("fallback_models", [])),
                        fallback_strategy=f_data.get("fallback_strategy", "ordered"),
                        max_retries=f_data.get("max_retries", 2),
                        timeout_before_fallback=f_data.get("timeout_before_fallback", 30.0),
                    )
                    self._fallback_rules[rule.primary_model] = rule
            changes.append("fallback_rules: reloaded")
        self._load_timestamp = time.time()
        changes.append(f"config reloaded at {self._load_timestamp}")
        return changes

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return {
            "version": self._version,
            "policies": [
                {
                    "name": p.name,
                    "policy_type": p.policy_type.value,
                    "domain": p.domain,
                    "preferred_models": list(p.preferred_models),
                    "max_cost_per_task": p.max_cost_per_task,
                    "min_reasoning_score": p.min_reasoning_score,
                    "min_coding_score": p.min_coding_score,
                    "require_verification": p.require_verification,
                    "metadata": p.metadata,
                }
                for p in self._policies.values()
            ],
            "model_registry": [
                asdict(e)
                for e in self._model_registry.values()
            ],
            "fallback_rules": [
                asdict(r)
                for r in self._fallback_rules.values()
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RouterConfig:
        """Create a RouterConfig from a dictionary."""
        policies: list[RoutingPolicy] = []
        for p_data in data.get("policies", []):
            policies.append(RoutingPolicy(
                name=p_data.get("name", ""),
                policy_type=PolicyType(p_data.get("policy_type", PolicyType.BALANCED.value)),
                domain=p_data.get("domain", ""),
                preferred_models=tuple(p_data.get("preferred_models", [])),
                max_cost_per_task=p_data.get("max_cost_per_task", float("inf")),
                min_reasoning_score=p_data.get("min_reasoning_score", 0.0),
                min_coding_score=p_data.get("min_coding_score", 0.0),
                require_verification=p_data.get("require_verification", False),
                metadata=p_data.get("metadata", {}),
            ))
        registry: list[ModelRegistryEntry] = []
        for m_data in data.get("model_registry", []):
            registry.append(ModelRegistryEntry(
                model_id=m_data.get("model_id", ""),
                tier=m_data.get("tier", ""),
                enabled=m_data.get("enabled", True),
                max_concurrency=m_data.get("max_concurrency", 10),
                rate_limit_per_minute=m_data.get("rate_limit_per_minute", 60),
                timeout_seconds=m_data.get("timeout_seconds", 60.0),
                metadata=m_data.get("metadata", {}),
            ))
        fallback: list[FallbackRule] = []
        for f_data in data.get("fallback_rules", []):
            fallback.append(FallbackRule(
                primary_model=f_data.get("primary_model", ""),
                fallback_models=tuple(f_data.get("fallback_models", [])),
                fallback_strategy=f_data.get("fallback_strategy", "ordered"),
                max_retries=f_data.get("max_retries", 2),
                timeout_before_fallback=f_data.get("timeout_before_fallback", 30.0),
            ))
        return cls(policies=policies, model_registry=registry, fallback_rules=fallback)

    @classmethod
    def from_json(cls, json_str: str) -> RouterConfig:
        """Create a RouterConfig from a JSON string."""
        return cls.from_dict(json.loads(json_str))
