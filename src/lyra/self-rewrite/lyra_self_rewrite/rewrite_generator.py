"""Generate code rewrites from agent genomes using template-based transformation."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from .hyper_agent import HyperAgent


@dataclass(frozen=True)
class RewriteTemplate:
    """A template describing a code rewrite transformation."""

    template_id: str
    pattern: str
    replacement: str
    applicable_genes: tuple[str, ...]


@dataclass(frozen=True)
class GeneratedRewrite:
    """A generated code rewrite produced from a template and agent genome."""

    rewrite_id: str
    agent_id: str
    template: RewriteTemplate
    generated_code: str
    confidence: float


@dataclass(frozen=True)
class RewriteLibrary:
    """A library of rewrite templates organised by category."""

    templates: tuple[RewriteTemplate, ...]
    total_templates: int
    categories: tuple[str, ...]


_DEFAULT_TEMPLATES: tuple[RewriteTemplate, ...] = (
    RewriteTemplate(
        template_id="opt-loop",
        pattern="for $idx in range($n):",
        replacement="for $item in $collection:",
        applicable_genes=("speed", "efficiency"),
    ),
    RewriteTemplate(
        template_id="async-convert",
        pattern="def $name($args):",
        replacement="async def $name($args):",
        applicable_genes=("thoroughness",),
    ),
    RewriteTemplate(
        template_id="type-annotate",
        pattern="def $name($args)",
        replacement="def $name($args) -> $rtype:",
        applicable_genes=("thoroughness", "conservatism"),
    ),
    RewriteTemplate(
        template_id="extract-method",
        pattern="# TODO",
        replacement="# TODO: refactor into smaller functions",
        applicable_genes=("creativity", "exploration"),
    ),
    RewriteTemplate(
        template_id="add-logging",
        pattern="raise $exc($msg)",
        replacement="logger.error($msg)\n    raise $exc($msg)",
        applicable_genes=("thoroughness", "conservatism"),
    ),
)


class RewriteGenerator:
    """Generates code rewrite candidates from agent genomes and templates."""

    def __init__(self) -> None:
        self._random = secrets.SystemRandom()

    async def load_templates(self) -> RewriteLibrary:
        """Load the built-in rewrite template library."""
        return RewriteLibrary(
            templates=_DEFAULT_TEMPLATES,
            total_templates=len(_DEFAULT_TEMPLATES),
            categories=("optimisation", "async", "types", "refactor", "logging"),
        )

    async def generate_rewrites(
        self,
        agent: HyperAgent,
        library: RewriteLibrary,
    ) -> tuple[GeneratedRewrite, ...]:
        """Generate rewrites for an agent using applicable templates."""
        if not agent.genome:
            return ()

        gene_traits = {g.trait for g in agent.genome}
        rewrites: list[GeneratedRewrite] = []

        for template in library.templates:
            if not template.applicable_genes:
                continue

            # Check if any applicable gene matches the agent's traits
            if not gene_traits.intersection(template.applicable_genes):
                continue

            # Compute confidence based on matching gene values
            confidence = _compute_confidence(agent, template)
            if confidence <= 0.0:
                continue

            rewrite_id = f"rw-{self._random.randint(100000, 999999)}"
            generated_code = _apply_template(agent, template)

            rewrites.append(GeneratedRewrite(
                rewrite_id=rewrite_id,
                agent_id=agent.agent_id,
                template=template,
                generated_code=generated_code,
                confidence=confidence,
            ))

        return tuple(rewrites)

    async def validate_rewrite(self, rewrite: GeneratedRewrite) -> bool:
        """Validate a generated rewrite (basic structural check)."""
        if not rewrite.generated_code or not rewrite.generated_code.strip():
            return False
        if rewrite.confidence < 0.0 or rewrite.confidence > 1.0:
            return False
        required_fields = (
            rewrite.rewrite_id,
            rewrite.agent_id,
            rewrite.template.template_id,
        )
        if not all(required_fields):
            return False
        return True

    async def apply_best_rewrite(
        self,
        rewrites: tuple[GeneratedRewrite, ...],
        threshold: float = 0.8,
    ) -> GeneratedRewrite | None:
        """Select the highest-confidence rewrite above threshold."""
        if not rewrites:
            return None

        valid = [rw for rw in rewrites if rw.confidence >= threshold]
        if not valid:
            return None

        valid.sort(key=lambda r: r.confidence, reverse=True)
        return valid[0]


def _compute_confidence(
    agent: HyperAgent, template: RewriteTemplate
) -> float:
    """Compute confidence score for a template applied to an agent."""
    if not agent.genome:
        return 0.0

    total_value = 0.0
    match_count = 0
    for gene in agent.genome:
        if gene.trait in template.applicable_genes:
            total_value += gene.value
            match_count += 1

    if match_count == 0:
        return 0.0

    base_confidence = total_value / match_count
    # Scale by agent fitness
    return base_confidence * (0.5 + 0.5 * agent.fitness)


def _apply_template(
    agent: HyperAgent, template: RewriteTemplate
) -> str:
    """Generate code from a template based on agent genome values.

    Produces a descriptive comment showing the intended rewrite rather than
    actually performing AST-level code transformation.
    """
    trait_values = {g.trait: g.value for g in agent.genome}
    gene_summary = ", ".join(
        f"{t}={v:.3f}" for t, v in trait_values.items()
    )

    return (
        f"# Rewrite generated from template '{template.template_id}'\n"
        f"# Agent: {agent.agent_id} (fitness={agent.fitness:.4f})\n"
        f"# Gene values: {gene_summary}\n"
        f"# Pattern: {template.pattern}\n"
        f"# Replacement: {template.replacement}\n"
    )
