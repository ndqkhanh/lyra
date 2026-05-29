"""Abduction step — infer posterior over exogenous variables given evidence."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from lyra_causal_graph.scm import StructuralCausalModel
from scipy import optimize

from .errors import AbductionError

logger = logging.getLogger(__name__)

__all__ = [
    "AbductionConfig",
    "AbductionResult",
    "AbductionEngine",
    "AbductionStrategy",
]


# ── Configuration ─────────────────────────────────────────────────────────────


@dataclass
class AbductionConfig:
    """Configuration for the abduction step.

    Attributes:
        strategy: Abduction strategy to use ("inversion", "mcmc", "optimization").
        n_posterior_samples: Number of samples for posterior approximation.
        mcmc_burnin: Burn-in iterations for MCMC strategy.
        optimization_lr: Learning rate for optimization-based inversion.
        noise_tolerance: Tolerance for noise estimation convergence.
        max_iterations: Maximum iterations for iterative inversion.
        random_seed: Seed for reproducibility.
    """

    strategy: str = "inversion"
    n_posterior_samples: int = 5000
    mcmc_burnin: int = 1000
    optimization_lr: float = 0.01
    noise_tolerance: float = 1e-6
    max_iterations: int = 100
    random_seed: int | None = None


@dataclass
class AbductionResult:
    """Result of the abduction step.

    Attributes:
        noise_posterior: Dict mapping exogenous variable names to
                         sample arrays representing the posterior.
        evidence_log_prob: Log-probability of the evidence under the posterior.
        converged: Whether the inversion converged.
        iterations: Number of iterations used.
        diagnostics: Additional diagnostic information.
    """

    noise_posterior: dict[str, np.ndarray]
    evidence_log_prob: float
    converged: bool = True
    iterations: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"AbductionResult(exo_vars={len(self.noise_posterior)}, "
            f"log_prob={self.evidence_log_prob:.2f}, converged={self.converged})"
        )


# ── Abduction Strategy Enum ──────────────────────────────────────────────────


class AbductionStrategy:
    """Enumeration of available abduction strategies."""

    INVERSION = "inversion"
    MCMC = "mcmc"
    OPTIMIZATION = "optimization"
    REJECTION = "rejection"
    VARIATIONAL = "variational"

    @classmethod
    def all_strategies(cls) -> list[str]:
        return [cls.INVERSION, cls.MCMC, cls.OPTIMIZATION, cls.REJECTION, cls.VARIATIONAL]


# ── Abduction Engine ─────────────────────────────────────────────────────────


class AbductionEngine:
    """Core abduction engine: infers noise posterior from observed evidence.

    Implements multiple strategies for computing the posterior distribution
    of exogenous (noise) variables conditioned on observed evidence.

    **Strategy details:**

    - ``inversion``: Direct algebraic inversion of structural equations.
      Fastest, but assumes linearity and no missing evidence.
    - ``mcmc``: Metropolis-Hastings sampling from the noise posterior.
      Handles nonlinear equations and partial evidence.
    - ``optimization``: Gradient-based minimization of the discrepancy
      between observed and predicted values.
    - ``rejection``: Rejection sampling from prior, accepting when
      predictions match evidence.
    - ``variational``: Variational inference with Gaussian approximation.

    Typical usage::

        engine = AbductionEngine(scm)
        result = engine.abduce({"X": 1.2, "Y": 3.4})
        posterior = result.noise_posterior
    """

    def __init__(
        self,
        scm: StructuralCausalModel,
        config: AbductionConfig | None = None,
    ) -> None:
        if scm is None:
            raise AbductionError("SCM must not be None.")
        self._scm = scm
        self._config = config or AbductionConfig()
        self._rng = np.random.default_rng(self._config.random_seed)

    @property
    def config(self) -> AbductionConfig:
        return self._config

    @property
    def scm(self) -> StructuralCausalModel:
        return self._scm

    # ── Public API ──────────────────────────────────────────────────────

    def abduce(
        self,
        evidence: dict[str, float],
        strategy: str | None = None,
    ) -> AbductionResult:
        """Infer noise posterior given observed evidence.

        Args:
            evidence: Dict mapping variable names to observed values.
            strategy: Override abduction strategy from config.

        Returns:
            ``AbductionResult`` with noise posterior samples.

        Raises:
            AbductionError: If evidence variables are not in the SCM or
                            if no strategy succeeds.
        """
        self._validate_evidence(evidence)
        strat = strategy or self._config.strategy

        if strat == AbductionStrategy.INVERSION:
            return self._inversion_abduction(evidence)
        elif strat == AbductionStrategy.OPTIMIZATION:
            return self._optimization_abduction(evidence)
        elif strat == AbductionStrategy.REJECTION:
            return self._rejection_abduction(evidence)
        elif strat == AbductionStrategy.MCMC:
            return self._mcmc_abduction(evidence)
        elif strat == AbductionStrategy.VARIATIONAL:
            return self._variational_abduction(evidence)
        else:
            raise AbductionError(f"Unknown abduction strategy: {strat}")

    async def abduce_async(
        self,
        evidence: dict[str, float],
        strategy: str | None = None,
    ) -> AbductionResult:
        """Async version for long-running MCMC or variational abduction."""
        return self.abduce(evidence, strategy)

    def batch_abduce(
        self,
        evidence_list: list[dict[str, float]],
        strategy: str | None = None,
    ) -> list[AbductionResult]:
        """Abduce noise posteriors for multiple evidence sets.

        Args:
            evidence_list: List of evidence dicts.
            strategy: Override abduction strategy.

        Returns:
            List of ``AbductionResult`` objects.
        """
        return [self.abduce(ev, strategy) for ev in evidence_list]

    # ── Strategy: Inversion ─────────────────────────────────────────────

    def _inversion_abduction(self, evidence: dict[str, float]) -> AbductionResult:
        """Direct algebraic inversion of structural equations.

        Works by solving ``evidence = f(parents) + noise`` for noise.
        Requires evidence for every endogenous variable.
        """
        n = self._config.n_posterior_samples
        noise_posterior: dict[str, np.ndarray] = {}

        # Initialize noise from prior
        for exo_name, exo_var in self._scm.exogenous_vars.items():
            noise_posterior[exo_name] = exo_var.sample_noise(n)

        # Invert equations in topological order
        order = self._scm.evaluation_order

        for var_name in order:
            eq = self._scm.equations.get(var_name)
            if eq is None:
                continue

            var_info = self._scm.endogenous_vars[var_name]

            # Build parent values
            parent_values: dict[str, np.ndarray] = {}
            for p in var_info.parents:
                if p in evidence:
                    parent_values[p] = np.full(n, evidence[p])
                elif p in self._scm.endogenous_vars:
                    parent_values[p] = self._evaluate_recursive(p, evidence, noise_posterior)
                elif p in self._scm.exogenous_vars:
                    parent_values[p] = noise_posterior.get(p, np.zeros(n))
                else:
                    parent_values[p] = np.zeros(n)

            if var_name in evidence:
                expected = eq.function(parent_values)
                observed = np.full(n, evidence[var_name])
                noise_posterior[eq.noise_var] = observed - expected

        # Compute log-probability of evidence
        log_prob = self._compute_evidence_log_prob(evidence, noise_posterior)

        return AbductionResult(
            noise_posterior=noise_posterior,
            evidence_log_prob=log_prob,
            converged=True,
            iterations=1,
            diagnostics={"strategy": "inversion", "n_samples": n},
        )

    def _evaluate_recursive(
        self,
        var_name: str,
        evidence: dict[str, float],
        noise: dict[str, np.ndarray],
    ) -> np.ndarray:
        """Recursively evaluate an endogenous variable."""
        if var_name in evidence:
            return np.full(self._config.n_posterior_samples, evidence[var_name])

        eq = self._scm.equations.get(var_name)
        if eq is None:
            return np.zeros(self._config.n_posterior_samples)

        var_info = self._scm.endogenous_vars[var_name]
        parent_vals: dict[str, np.ndarray] = {}
        for p in var_info.parents:
            if p in evidence:
                parent_vals[p] = np.full(self._config.n_posterior_samples, evidence[p])
            elif p in noise:
                parent_vals[p] = noise[p]
            else:
                parent_vals[p] = self._evaluate_recursive(p, evidence, noise)

        return eq.function(parent_vals) + noise.get(eq.noise_var, np.zeros(self._config.n_posterior_samples))

    # ── Strategy: Optimization ──────────────────────────────────────────

    def _optimization_abduction(self, evidence: dict[str, float]) -> AbductionResult:
        """Gradient-free optimization to find maximum a-posteriori noise values."""
        exo_names = sorted(self._scm.exogenous_vars.keys())
        n_exo = len(exo_names)

        def loss(noise_vals: np.ndarray) -> float:
            """Negative log-posterior: -log p(noise) - log p(evidence | noise)."""
            noise_dict = {name: np.array([noise_vals[i]]) for i, name in enumerate(exo_names)}
            # Prior log-prob
            prior_lp = 0.0
            for name, val in noise_dict.items():
                exo = self._scm.exogenous_vars[name]
                prior_lp += float(np.sum(exo.noise.log_prob(val)))
            # Likelihood
            try:
                predicted = self._predict_from_noise(noise_dict)
                likelihood_lp = 0.0
                for var_name, obs_val in evidence.items():
                    if var_name in predicted:
                        diff = obs_val - float(predicted[var_name][0])
                        likelihood_lp += -0.5 * diff**2  # Gaussian likelihood
                return float(-prior_lp - likelihood_lp)
            except Exception:
                return 1e10

        # Initial guess
        x0 = np.zeros(n_exo)
        try:
            result = optimize.minimize(
                loss, x0,
                method="Nelder-Mead",
                options={"maxiter": self._config.max_iterations, "xatol": self._config.noise_tolerance},
            )
        except Exception:
            raise AbductionError("Optimization abduction failed to converge.")

        # Create posterior samples as small perturbations around MAP
        n = self._config.n_posterior_samples
        noise_posterior: dict[str, np.ndarray] = {}
        for i, name in enumerate(exo_names):
            exo = self._scm.exogenous_vars[name]
            map_val = result.x[i]
            # Add small Gaussian noise around MAP for posterior approximation
            noise_posterior[name] = np.random.normal(map_val, max(exo.noise.std if hasattr(exo.noise, 'std') else 0.1, 0.01), n)

        log_prob = self._compute_evidence_log_prob(evidence, noise_posterior)

        return AbductionResult(
            noise_posterior=noise_posterior,
            evidence_log_prob=log_prob,
            converged=result.success,
            iterations=result.nit,
            diagnostics={
                "strategy": "optimization",
                "final_loss": float(result.fun),
                "success": result.success,
            },
        )

    def _predict_from_noise(self, noise_dict: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """Evaluate the SCM given noise values."""
        values: dict[str, np.ndarray] = dict(noise_dict)
        for var_name in self._scm.evaluation_order:
            eq = self._scm.equations.get(var_name)
            if eq is None:
                continue
            var_info = self._scm.endogenous_vars[var_name]
            parent_vals = {}
            for p in var_info.parents:
                if p in values:
                    parent_vals[p] = values[p]
                else:
                    parent_vals[p] = np.zeros_like(next(iter(values.values())))
            values[var_name] = eq.evaluate(parent_vals, noise_dict.get(eq.noise_var, np.zeros_like(next(iter(values.values())))))
        return {k: v for k, v in values.items() if k in self._scm.endogenous_vars}

    # ── Strategy: Rejection Sampling ────────────────────────────────────

    def _rejection_abduction(self, evidence: dict[str, float]) -> AbductionResult:
        """Rejection sampling: draw from prior, accept when predictions match evidence."""
        exo_names = sorted(self._scm.exogenous_vars.keys())
        n_attempts = 0
        accepted: dict[str, list[float]] = {name: [] for name in exo_names}
        target = self._config.n_posterior_samples
        max_attempts = target * 100

        while len(next(iter(accepted.values()))) < target and n_attempts < max_attempts:
            n_attempts += 1
            # Draw noise from prior
            noise_candidate = {name: self._scm.exogenous_vars[name].sample_noise(1) for name in exo_names}
            # Predict
            predicted = self._predict_from_noise(noise_candidate)
            # Accept
            if self._matches_evidence(predicted, evidence):
                for name in exo_names:
                    accepted[name].append(float(noise_candidate[name][0]))

        accepted_count = len(next(iter(accepted.values())))
        converged = accepted_count >= target

        if accepted_count == 0:
            raise AbductionError(
                "Rejection sampling failed: no samples matched evidence. "
                "Try a different strategy or relax tolerance."
            )

        noise_posterior = {name: np.array(vals) for name, vals in accepted.items()}
        log_prob = self._compute_evidence_log_prob(evidence, noise_posterior)

        return AbductionResult(
            noise_posterior=noise_posterior,
            evidence_log_prob=log_prob,
            converged=converged,
            iterations=n_attempts,
            diagnostics={
                "strategy": "rejection",
                "acceptance_rate": accepted_count / n_attempts if n_attempts > 0 else 0,
            },
        )

    def _matches_evidence(
        self,
        predicted: dict[str, np.ndarray],
        evidence: dict[str, float],
        tolerance: float = 0.5,
    ) -> bool:
        """Check if predicted values match evidence within tolerance."""
        for var_name, obs_val in evidence.items():
            if var_name not in predicted:
                return False
            pred_val = float(predicted[var_name][0])
            if abs(pred_val - obs_val) > tolerance:
                return False
        return True

    # ── Strategy: MCMC ──────────────────────────────────────────────────

    def _mcmc_abduction(self, evidence: dict[str, float]) -> AbductionResult:
        """Metropolis-Hastings MCMC for noise posterior sampling."""
        exo_names = sorted(self._scm.exogenous_vars.keys())
        n_exo = len(exo_names)
        n_total = self._config.n_posterior_samples + self._config.mcmc_burnin

        # Initialize
        current = np.zeros(n_exo)
        samples = np.zeros((n_total, n_exo))

        current_log_post = -self._log_posterior(current, exo_names, evidence)

        accepted = 0
        proposal_std = 0.1

        for i in range(n_total):
            # Propose
            proposal = current + np.random.normal(0, proposal_std, n_exo)
            proposal_log_post = -self._log_posterior(proposal, exo_names, evidence)

            # Accept/reject
            log_alpha = proposal_log_post - current_log_post
            if np.log(np.random.random()) < log_alpha:
                current = proposal
                current_log_post = proposal_log_post
                accepted += 1

            samples[i] = current

            # Adapt proposal std every 100 iterations
            if i > 0 and i % 100 == 0:
                accept_rate = accepted / i
                if accept_rate > 0.5:
                    proposal_std *= 1.1
                else:
                    proposal_std *= 0.9

        # Discard burn-in
        posterior_samples = samples[self._config.mcmc_burnin:]

        noise_posterior = {
            name: posterior_samples[:, i]
            for i, name in enumerate(exo_names)
        }

        log_prob = self._compute_evidence_log_prob(evidence, noise_posterior)

        return AbductionResult(
            noise_posterior=noise_posterior,
            evidence_log_prob=log_prob,
            converged=True,
            iterations=n_total,
            diagnostics={
                "strategy": "mcmc",
                "acceptance_rate": accepted / n_total,
            },
        )

    def _log_posterior(
        self, noise_vals: np.ndarray, exo_names: list[str], evidence: dict[str, float]
    ) -> float:
        """Compute log-posterior for MCMC."""
        noise_dict = {name: np.array([noise_vals[i]]) for i, name in enumerate(exo_names)}
        # Prior
        prior_lp = 0.0
        for name, val in noise_dict.items():
            exo = self._scm.exogenous_vars[name]
            prior_lp += float(np.sum(exo.noise.log_prob(val)))
        # Likelihood
        try:
            predicted = self._predict_from_noise(noise_dict)
            likelihood_lp = 0.0
            for var_name, obs_val in evidence.items():
                if var_name in predicted:
                    diff = obs_val - float(predicted[var_name][0])
                    likelihood_lp += -0.5 * diff**2
            return float(prior_lp + likelihood_lp)
        except Exception:
            return -1e10

    # ── Strategy: Variational ───────────────────────────────────────────

    def _variational_abduction(self, evidence: dict[str, float]) -> AbductionResult:
        """Variational inference with Gaussian mean-field approximation.

        Minimizes KL divergence between a Gaussian posterior and the
        true noise posterior via coordinate ascent.
        """
        exo_names = sorted(self._scm.exogenous_vars.keys())
        n_exo = len(exo_names)
        n = self._config.n_posterior_samples

        # Initialize variational parameters (Gaussian mean-field)
        mu = np.zeros(n_exo)
        sigma = np.ones(n_exo) * 0.5

        lr = self._config.optimization_lr

        for _iteration in range(self._config.max_iterations):
            # Sample from current variational distribution
            eps = np.random.normal(0, 1, (100, n_exo))
            samples = mu + sigma * eps

            # Compute gradients via REINFORCE / score function estimator
            grad_mu = np.zeros(n_exo)
            grad_sigma = np.zeros(n_exo)

            log_posts = np.array([
                self._log_posterior(s, exo_names, evidence)
                for s in samples
            ])

            # Normalize for stability
            log_posts = log_posts - np.max(log_posts)

            for i, s in enumerate(samples):
                weight = np.exp(log_posts[i])
                grad_mu += weight * (s - mu) / (sigma**2)
                grad_sigma += weight * ((s - mu)**2 / sigma**3 - 1.0 / sigma)

            grad_mu /= len(samples)
            grad_sigma /= len(samples)

            # Update
            mu += lr * grad_mu
            sigma += lr * grad_sigma
            sigma = np.clip(sigma, 0.01, 10.0)

            # Check convergence
            if np.max(np.abs(grad_mu)) < self._config.noise_tolerance:
                break

        # Sample final posterior
        posterior_samples = np.random.normal(mu, sigma, (n, n_exo))
        noise_posterior = {
            name: posterior_samples[:, i]
            for i, name in enumerate(exo_names)
        }

        log_prob = self._compute_evidence_log_prob(evidence, noise_posterior)

        return AbductionResult(
            noise_posterior=noise_posterior,
            evidence_log_prob=log_prob,
            converged=True,
            iterations=self._config.max_iterations,
            diagnostics={
                "strategy": "variational",
                "variational_mu": mu.tolist(),
                "variational_sigma": sigma.tolist(),
            },
        )

    # ── Helpers ─────────────────────────────────────────────────────────

    def _validate_evidence(self, evidence: dict[str, float]) -> None:
        """Validate that evidence variables exist in the SCM."""
        if not evidence:
            raise AbductionError("At least one piece of evidence is required.")

        for var_name in evidence:
            if var_name not in self._scm.endogenous_vars:
                raise AbductionError(
                    f"Variable '{var_name}' not found in SCM. "
                    f"Available: {sorted(self._scm.endogenous_vars.keys())}"
                )

    def _compute_evidence_log_prob(
        self,
        evidence: dict[str, float],
        noise_posterior: dict[str, np.ndarray],
    ) -> float:
        """Compute log-probability of evidence under the noise posterior.

        Uses Monte Carlo estimation: average of log-likelihoods.
        """
        n = min(len(next(iter(noise_posterior.values()))), 500)  # subsample
        idx = np.random.choice(len(next(iter(noise_posterior.values()))), n, replace=False)

        log_probs = []
        for i in idx:
            noise_i = {name: np.array([vals[i]]) for name, vals in noise_posterior.items()}
            try:
                predicted = self._predict_from_noise(noise_i)
                lp = 0.0
                for var_name, obs_val in evidence.items():
                    if var_name in predicted:
                        diff = obs_val - float(predicted[var_name][0])
                        lp += -0.5 * diff**2 - 0.5 * np.log(2 * np.pi)
                log_probs.append(lp)
            except Exception:
                continue

        if not log_probs:
            return -np.inf

        return float(np.mean(log_probs))

    def __repr__(self) -> str:
        return f"AbductionEngine(scm={self._scm}, strategy={self._config.strategy})"
