"""Structural Causal Models — specification, evaluation, and exogenous variable handling."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

import numpy as np

from .errors import SCMError

logger = logging.getLogger(__name__)

__all__ = [
    "NoiseModel",
    "GaussianNoise",
    "UniformNoise",
    "LaplaceNoise",
    "ExogenousVariable",
    "EndogenousVariable",
    "SCMEquation",
    "StructuralCausalModel",
    "SCMConfig",
]


# ── Noise Models ──────────────────────────────────────────────────────────────


class NoiseModel(ABC):
    """Abstract base for noise distributions used in SCM equations."""

    @abstractmethod
    def sample(self, size: int = 1) -> np.ndarray:
        """Draw `size` independent noise samples.

        Args:
            size: Number of samples to draw.

        Returns:
            1D numpy array of shape ``(size,)``.
        """

    @abstractmethod
    def log_prob(self, x: np.ndarray) -> np.ndarray:
        """Compute log-probability density for the given values.

        Args:
            x: Array of values.

        Returns:
            Log-probability density per element.
        """

    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        """Return a serialisable configuration dict."""

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict[str, Any]) -> NoiseModel:
        """Reconstruct a noise model from a config dict."""


@dataclass
class GaussianNoise(NoiseModel):
    """Zero-mean Gaussian noise with configurable standard deviation."""

    std: float = 1.0

    def sample(self, size: int = 1) -> np.ndarray:
        return np.random.normal(loc=0.0, scale=self.std, size=size)

    def log_prob(self, x: np.ndarray) -> np.ndarray:
        var = self.std**2
        return -0.5 * (np.log(2 * np.pi * var) + (x**2) / var)

    def get_config(self) -> dict[str, Any]:
        return {"type": "gaussian", "std": self.std}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> GaussianNoise:
        return cls(std=config.get("std", 1.0))


@dataclass
class UniformNoise(NoiseModel):
    """Uniform noise on ``[-half_range, half_range]``."""

    half_range: float = 1.0

    def sample(self, size: int = 1) -> np.ndarray:
        return np.random.uniform(low=-self.half_range, high=self.half_range, size=size)

    def log_prob(self, x: np.ndarray) -> np.ndarray:
        in_bounds = (x >= -self.half_range) & (x <= self.half_range)
        log_p = np.full_like(x, -np.inf, dtype=float)
        log_p[in_bounds] = -np.log(2 * self.half_range)
        return log_p

    def get_config(self) -> dict[str, Any]:
        return {"type": "uniform", "half_range": self.half_range}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> UniformNoise:
        return cls(half_range=config.get("half_range", 1.0))


@dataclass
class LaplaceNoise(NoiseModel):
    """Zero-mean Laplace noise with configurable scale parameter."""

    scale: float = 1.0

    def sample(self, size: int = 1) -> np.ndarray:
        return np.random.laplace(loc=0.0, scale=self.scale, size=size)

    def log_prob(self, x: np.ndarray) -> np.ndarray:
        return -np.log(2 * self.scale) - np.abs(x) / self.scale

    def get_config(self) -> dict[str, Any]:
        return {"type": "laplace", "scale": self.scale}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> LaplaceNoise:
        return cls(scale=config.get("scale", 1.0))


_NOISE_REGISTRY: dict[str, type[NoiseModel]] = {
    "gaussian": GaussianNoise,
    "uniform": UniformNoise,
    "laplace": LaplaceNoise,
}


def _noise_from_config(config: dict[str, Any]) -> NoiseModel:
    noise_type = config.get("type", "gaussian")
    cls = _NOISE_REGISTRY.get(noise_type)
    if cls is None:
        raise SCMError(f"Unknown noise model type: {noise_type}")
    return cls.from_config(config)


# ── Variable Definitions ─────────────────────────────────────────────────────


@dataclass
class ExogenousVariable:
    """An unobserved external variable (U) with an associated noise distribution."""

    name: str
    noise: NoiseModel = field(default_factory=GaussianNoise)

    def sample_noise(self, size: int = 1) -> np.ndarray:
        return self.noise.sample(size)

    def get_config(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "noise": self.noise.get_config(),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ExogenousVariable:
        return cls(
            name=config["name"],
            noise=_noise_from_config(config.get("noise", {})),
        )


@dataclass
class EndogenousVariable:
    """An observed variable (V) whose value is determined by an SCM equation."""

    name: str
    parents: list[str] = field(default_factory=list)
    description: str = ""


# ── SCM Equation ──────────────────────────────────────────────────────────────


@dataclass
class SCMEquation:
    """A single structural equation: ``X = f(parents) + noise``.

    Attributes:
        variable: The endogenous variable this equation defines.
        function: A callable ``f(parent_values: dict) -> float`` or ``None``
                  for linear default.
        noise_var: The exogenous noise variable name.
        metadata: Arbitrary key-value metadata.
    """

    variable: str
    function: Callable[[dict[str, np.ndarray]], np.ndarray]
    noise_var: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def evaluate(
        self,
        parent_values: dict[str, np.ndarray],
        noise_values: np.ndarray,
    ) -> np.ndarray:
        """Compute the equation output for given parents and noise.

        Args:
            parent_values: Dict mapping parent variable names to value arrays.
            noise_values: The exogenous noise array.

        Returns:
            Computed endogenous value array.
        """
        return self.function(parent_values) + noise_values


# ── SCM Configuration ────────────────────────────────────────────────────────


@dataclass
class SCMConfig:
    """Configuration for a Structural Causal Model.

    Attributes:
        noise_scale: Default noise scale applied to new exogenous variables.
        default_noise_type: Default noise distribution type.
        enable_cache: Cache equation evaluations for repeated queries.
        random_seed: Seed for reproducible noise generation.
    """

    noise_scale: float = 1.0
    default_noise_type: str = "gaussian"
    enable_cache: bool = True
    random_seed: Optional[int] = None


# ── Structural Causal Model ──────────────────────────────────────────────────


class StructuralCausalModel:
    """A full Structural Causal Model with multi-equation support.

    An SCM is a triple ``<U, V, F>`` where:
    - ``U`` are exogenous (unobserved) variables driven by noise distributions.
    - ``V`` are endogenous (observed) variables determined by structural equations.
    - ``F`` is a set of structural equations, one per endogenous variable.

    Typical usage::

        scm = StructuralCausalModel()
        scm.add_exogenous("U_X", GaussianNoise(std=0.5))
        scm.add_endogenous("X", parents=[], description="Treatment")
        scm.add_equation("X", lambda pv: 0.0 * pv.get("U_X", np.zeros(1)), "U_X")
        scm.add_endogenous("Y", parents=["X"], description="Outcome")
        scm.add_equation("Y", lambda pv: 2.0 * pv["X"], "U_Y")

        sample = scm.sample(n=1000)
        intervention = scm.intervene({"X": 1.0}).sample(n=1000)
    """

    def __init__(self, config: Optional[SCMConfig] = None) -> None:
        self._config = config or SCMConfig()
        self._exogenous: dict[str, ExogenousVariable] = {}
        self._endogenous: dict[str, EndogenousVariable] = {}
        self._equations: dict[str, SCMEquation] = {}
        self._eval_order: Optional[list[str]] = None
        self._rng: np.random.Generator = np.random.default_rng(self._config.random_seed)

        if self._config.random_seed is not None:
            np.random.seed(self._config.random_seed)

    # ── Build API ─────────────────────────────────────────────────────────

    @property
    def config(self) -> SCMConfig:
        return self._config

    @property
    def exogenous_vars(self) -> dict[str, ExogenousVariable]:
        return dict(self._exogenous)

    @property
    def endogenous_vars(self) -> dict[str, EndogenousVariable]:
        return dict(self._endogenous)

    @property
    def equations(self) -> dict[str, SCMEquation]:
        return dict(self._equations)

    def add_exogenous(self, name: str, noise: Optional[NoiseModel] = None) -> ExogenousVariable:
        """Register an exogenous variable.

        Args:
            name: Variable name.
            noise: Noise model; uses config default if omitted.

        Returns:
            The created ``ExogenousVariable``.
        """
        if noise is None:
            noise = _noise_from_config({"type": self._config.default_noise_type, "std": self._config.noise_scale})
        var = ExogenousVariable(name=name, noise=noise)
        self._exogenous[name] = var
        self._invalidate_order()
        return var

    def add_endogenous(self, name: str, parents: Optional[list[str]] = None, description: str = "") -> EndogenousVariable:
        """Register an endogenous variable.

        Args:
            name: Variable name.
            parents: List of parent variable names (endogenous or exogenous).
            description: Human-readable description.

        Returns:
            The created ``EndogenousVariable``.
        """
        var = EndogenousVariable(name=name, parents=parents or [], description=description)
        self._endogenous[name] = var
        self._invalidate_order()
        return var

    def add_equation(
        self,
        variable: str,
        function: Callable[[dict[str, np.ndarray]], np.ndarray],
        noise_var: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SCMEquation:
        """Attach a structural equation to an endogenous variable.

        Args:
            variable: Name of the endogenous variable this equation defines.
            function: ``f(parent_values) -> array``. The array computation
                      without noise; noise is added by the framework.
            noise_var: Name of the exogenous noise variable.
            metadata: Optional metadata dict.

        Returns:
            The created ``SCMEquation``.

        Raises:
            SCMError: If the variable or noise variable has not been registered.
        """
        if variable not in self._endogenous:
            raise SCMError(f"Endogenous variable '{variable}' not registered. Call add_endogenous first.")
        if noise_var not in self._exogenous:
            raise SCMError(f"Exogenous variable '{noise_var}' not registered. Call add_exogenous first.")
        eq = SCMEquation(
            variable=variable,
            function=function,
            noise_var=noise_var,
            metadata=metadata or {},
        )
        self._equations[variable] = eq
        self._invalidate_order()
        return eq

    # ── Topological Order ─────────────────────────────────────────────────

    def _invalidate_order(self) -> None:
        self._eval_order = None

    def _topological_sort(self) -> list[str]:
        """Return variables in topological order (parents before children)."""
        from collections import deque

        in_degree: dict[str, int] = {}
        children: dict[str, list[str]] = {}

        for name in self._endogenous:
            in_degree[name] = 0
            children[name] = []

        for name, var in self._endogenous.items():
            for parent in var.parents:
                if parent in self._endogenous:
                    in_degree[name] = in_degree.get(name, 0) + 1
                    children.setdefault(parent, []).append(name)

        queue: deque[str] = deque(n for n, d in in_degree.items() if d == 0)
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for child in children.get(node, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(self._endogenous):
            raise SCMError(
                "SCM contains a cycle in the endogenous variable graph. "
                "Causal models must be acyclic."
            )

        return order

    @property
    def evaluation_order(self) -> list[str]:
        """Return variables in topological evaluation order."""
        if self._eval_order is None:
            self._eval_order = self._topological_sort()
        return self._eval_order

    # ── Sampling ──────────────────────────────────────────────────────────

    def _sample_noise(self, n: int) -> dict[str, np.ndarray]:
        """Draw noise for every exogenous variable."""
        return {name: var.sample_noise(n) for name, var in self._exogenous.items()}

    def _evaluate(self, noise: dict[str, np.ndarray], interventions: Optional[dict[str, np.ndarray]] = None) -> dict[str, np.ndarray]:
        """Evaluate all equations given noise and optional interventions."""
        interventions = interventions or {}
        values: dict[str, np.ndarray] = dict(noise)

        for var_name in self.evaluation_order:
            if var_name in interventions:
                values[var_name] = interventions[var_name]
                continue

            eq = self._equations.get(var_name)
            if eq is None:
                raise SCMError(f"No equation defined for endogenous variable '{var_name}'.")

            var = self._endogenous[var_name]
            parent_values = {p: values[p] for p in var.parents}
            n_var = noise[eq.noise_var]
            values[var_name] = eq.evaluate(parent_values, n_var)

        return {k: v for k, v in values.items() if k in self._endogenous}

    def sample(self, n: int = 1) -> dict[str, np.ndarray]:
        """Draw ``n`` samples from the joint distribution.

        Args:
            n: Number of samples.

        Returns:
            Dict mapping endogenous variable names to 1D numpy arrays of length ``n``.
        """
        noise = self._sample_noise(n)
        return self._evaluate(noise)

    def intervene(self, interventions: dict[str, float]) -> _InterventionalSCM:
        """Return an interventional view of this SCM.

        This implements the ``do``-operator: variables listed in
        ``interventions`` are clamped to the given values, severing
        edges from their original parents.

        Args:
            interventions: Dict mapping variable names to fixed values.

        Returns:
            An ``_InterventionalSCM`` that can be sampled.
        """
        return _InterventionalSCM(self, interventions)

    # ── Serialisation ─────────────────────────────────────────────────────

    def get_config(self) -> dict[str, Any]:
        return {
            "exogenous": [v.get_config() for v in self._exogenous.values()],
            "endogenous": [
                {"name": v.name, "parents": v.parents, "description": v.description}
                for v in self._endogenous.values()
            ],
            "equations": [
                {
                    "variable": e.variable,
                    "noise_var": e.noise_var,
                    "metadata": e.metadata,
                }
                for e in self._equations.values()
            ],
            "config": {
                "noise_scale": self._config.noise_scale,
                "default_noise_type": self._config.default_noise_type,
                "random_seed": self._config.random_seed,
            },
        }

    def validate(self) -> list[str]:
        """Validate the SCM and return a list of issues.

        Returns:
            List of validation warnings/errors (empty if valid).
        """
        issues: list[str] = []

        for name, var in self._endogenous.items():
            if name not in self._equations:
                issues.append(f"Endogenous variable '{name}' has no equation.")

        for name, eq in self._equations.items():
            if eq.noise_var not in self._exogenous:
                issues.append(f"Equation for '{name}' references unknown noise var '{eq.noise_var}'.")

        for name, var in self._endogenous.items():
            for parent in var.parents:
                if parent not in self._endogenous and parent not in self._exogenous:
                    issues.append(f"Variable '{name}' references unknown parent '{parent}'.")

        try:
            self._topological_sort()
        except SCMError as exc:
            issues.append(str(exc))

        return issues

    def __repr__(self) -> str:
        return (
            f"StructuralCausalModel(endo={len(self._endogenous)}, "
            f"exo={len(self._exogenous)}, eqs={len(self._equations)})"
        )


class _InterventionalSCM:
    """A lightweight wrapper that applies interventions during sampling.

    Created via ``scm.intervene(...)``; not instantiated directly.
    """

    def __init__(self, scm: StructuralCausalModel, interventions: dict[str, float]) -> None:
        self._scm = scm
        # Expand scalar interventions to arrays during sampling
        self._interventions_raw = interventions

    def _make_interventions(self, n: int) -> dict[str, np.ndarray]:
        return {k: np.full(n, v) for k, v in self._interventions_raw.items()}

    def sample(self, n: int = 1) -> dict[str, np.ndarray]:
        noise = self._scm._sample_noise(n)
        return self._scm._evaluate(noise, interventions=self._make_interventions(n))

    def __repr__(self) -> str:
        interventions = ", ".join(f"{k}={v}" for k, v in self._interventions_raw.items())
        return f"InterventionalSCM(do({interventions}))"


# ── Factory helpers ───────────────────────────────────────────────────────────


def make_chain_scm(
    noise_std: float = 0.1,
    coef: float = 1.0,
    n_vars: int = 3,
    seed: Optional[int] = None,
) -> StructuralCausalModel:
    """Create a simple chain SCM: ``X0 → X1 → X2 → ...``

    Args:
        noise_std: Standard deviation of Gaussian noise.
        coef: Coefficient on each parent-child edge.
        n_vars: Number of endogenous variables in the chain.
        seed: Random seed.

    Returns:
        A configured ``StructuralCausalModel``.
    """
    config = SCMConfig(noise_scale=noise_std, random_seed=seed)
    scm = StructuralCausalModel(config)

    for i in range(n_vars):
        name = f"X{i}"
        parents = [f"X{i - 1}"] if i > 0 else []
        u_name = f"U_{name}"
        scm.add_exogenous(u_name, GaussianNoise(std=noise_std))
        scm.add_endogenous(name, parents=parents)

        if i == 0:
            scm.add_equation(name, lambda pv: np.zeros_like(pv.get("_n", np.zeros(1))), u_name)
        else:
            parent_name = parents[0]
            eq = _make_chain_equation(coef, parent_name)
            scm.add_equation(name, eq, u_name)

    return scm


def _make_chain_equation(coef: float, parent_name: str) -> Callable:
    def eq(pv: dict[str, np.ndarray]) -> np.ndarray:
        return coef * pv.get(parent_name, np.zeros(1))
    return eq


def make_collider_scm(
    noise_std: float = 0.1,
    seed: Optional[int] = None,
) -> StructuralCausalModel:
    """Create a collider SCM: ``X → Z ← Y``

    Useful for demonstrating that conditioning on a collider (Z)
    induces spurious correlation between X and Y.

    Args:
        noise_std: Standard deviation of Gaussian noise.
        seed: Random seed.

    Returns:
        A configured ``StructuralCausalModel``.
    """
    config = SCMConfig(noise_scale=noise_std, random_seed=seed)
    scm = StructuralCausalModel(config)

    for var in ("X", "Y", "Z"):
        scm.add_exogenous(f"U_{var}", GaussianNoise(std=noise_std))

    scm.add_endogenous("X", parents=[])
    scm.add_equation("X", lambda pv: np.zeros_like(pv.get("_n", np.zeros(1))), "U_X")

    scm.add_endogenous("Y", parents=[])
    scm.add_equation("Y", lambda pv: np.zeros_like(pv.get("_n", np.zeros(1))), "U_Y")

    scm.add_endogenous("Z", parents=["X", "Y"])
    scm.add_equation(
        "Z",
        lambda pv: pv.get("X", np.zeros(1)) + pv.get("Y", np.zeros(1)),
        "U_Z",
    )

    return scm
