"""SkillNet-based auto-generator — template-driven skill generation with 5-D quality scoring and deterministic fallback."""

from __future__ import annotations

import json
import os
import random
import textwrap
from datetime import datetime
from typing import Any

from lyra.skill_generator.models import (
    GeneratedSkill,
    GeneratorConfig,
    SkillCatalog,
    SkillDomain,
    SkillQualityReport,
    SkillTemplate,
)
from lyra.skill_generator.templates import TEMPLATE_REGISTRY


class SkillGenerator:
    """Generates Lyra skills from templates using LLM calls with deterministic fallback."""

    def __init__(
        self,
        config: GeneratorConfig | None = None,
        catalog: SkillCatalog | None = None,
    ) -> None:
        self.config = config or GeneratorConfig()
        self.catalog = catalog or SkillCatalog()
        self._generated: list[GeneratedSkill] = []

        # Pre-register all built-in templates
        for template in TEMPLATE_REGISTRY.values():
            self.catalog.register(template)

    # ── Public API ──────────────────────────────────────────────────────────

    def generate(self, template_name: str, specification: str = "") -> GeneratedSkill:
        """Generate a skill from a named template and specification string."""
        template = self.catalog.get(template_name)
        if template is None:
            msg = f"Unknown template: {template_name}"
            raise ValueError(msg)

        if not specification:
            specification = f"Generate a {template.domain.display_name.lower()} skill named '{template.name}'."

        prompt = self._build_prompt(template, specification)
        content = self._generate_with_llm(prompt)
        quality = self._evaluate_quality(content)

        skill = GeneratedSkill(
            template_name=template.name,
            domain=template.domain,
            content=content,
            quality_report=quality,
            generated_at=datetime.now(),
            version="1.0.0",
        )

        self._generated.append(skill)
        self._save_skill(skill)
        return skill

    def generate_domain(self, domain: SkillDomain, specification: str = "") -> list[GeneratedSkill]:
        """Generate all skills in a given domain."""
        results: list[GeneratedSkill] = []
        templates = self.catalog.by_domain(domain)
        for template in templates:
            spec = specification or f"Generate a {domain.display_name.lower()} skill named '{template.name}'."
            skill = self.generate(template.name, spec)
            results.append(skill)
        return results

    def generate_all(self, specification: str = "") -> list[GeneratedSkill]:
        """Generate one skill for every registered template."""
        results: list[GeneratedSkill] = []
        for template_name in self.catalog.templates:
            skill = self.generate(template_name, specification)
            results.append(skill)
        return results

    @property
    def generated(self) -> list[GeneratedSkill]:
        return list(self._generated)

    @property
    def generated_count(self) -> int:
        return len(self._generated)

    # ── Internal ────────────────────────────────────────────────────────────

    def _build_prompt(self, template: SkillTemplate, specification: str) -> str:
        """Build a structured LLM prompt from the template and user specification."""
        sections_text = "\n".join(f"  - {s}" for s in template.sections)
        dependencies_text = ", ".join(template.dependencies) if template.dependencies else "none"

        return textwrap.dedent(f"""\
            You are a skill generator for the Lyra autonomous coding system.

            Generate a complete, well-structured skill definition in YAML format.

            Domain: {template.domain.display_name}
            Skill Name: {template.name}
            Description: {template.description}
            Difficulty: {template.difficulty}
            Dependencies: {dependencies_text}

            Required Sections:
            {sections_text}

            User Specification:
            {specification}

            The skill must include:
            1. A 'metadata' section with domain, name, description, version, and difficulty
            2. A 'triggers' section listing trigger keywords from the spec
            3. One subsection per required section listed above
            4. A 'quality_checks' section with automated quality criteria

            Output valid YAML or JSON only, no commentary.
        """).strip()

    def _generate_with_llm(self, prompt: str) -> str:
        """Attempt LLM generation with deterministic fallback if LLM is unavailable."""
        if self.config.enable_llm:
            try:
                import urllib.request
                import urllib.error

                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if not api_key:
                    raise RuntimeError("ANTHROPIC_API_KEY not set")

                data = json.dumps({
                    "model": self.config.model_name,
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    content_blocks = body.get("content", [])
                    text_parts = [
                        b.get("text", "")
                        for b in content_blocks
                        if b.get("type") == "text"
                    ]
                    if text_parts:
                        return text_parts[0]

            except Exception:
                pass

        # ── Deterministic fallback ───────────────────────────────────────
        return self._fallback_generate(prompt)

    def _fallback_generate(self, prompt: str) -> str:
        """Generate a deterministic skill definition from the prompt when LLM is unavailable."""
        lines = prompt.split("\n")

        domain_name = "General"
        skill_name = "generated_skill"
        description = "Auto-generated skill."
        difficulty = 0.5
        sections: list[str] = []

        for line in lines:
            low = line.lower().strip()
            if low.startswith("domain:"):
                domain_name = line.split(":", 1)[1].strip()
            elif low.startswith("skill name:"):
                skill_name = line.split(":", 1)[1].strip()
            elif low.startswith("description:"):
                description = line.split(":", 1)[1].strip()
            elif low.startswith("difficulty:"):
                try:
                    difficulty = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

        # Collect section names from the bullet list after "Required Sections:"
        in_sections = False
        for line in lines:
            low = line.strip()
            if low.startswith("Required Sections"):
                in_sections = True
                continue
            if in_sections:
                stripped = low.strip("- ").strip()
                if stripped and not stripped.startswith("User Specification"):
                    sections.append(stripped)
                if low.startswith("User Specification"):
                    break

        trigger_keywords = [
            skill_name.replace("_", " "),
            domain_name.lower(),
            "auto-generated",
        ]

        section_content = ""
        for section in sections:
            section_content += textwrap.dedent(f"""\
                {section}:
                  description: "Auto-generated {section} for {skill_name}."
                  content:
                    - step: "Analyze requirements for {section}"
                    - step: "Generate {section} content"
                    - step: "Validate {section} output"
                  status: "generated"

            """)

        return textwrap.dedent(f"""\
            ---
            metadata:
              domain: {domain_name}
              name: {skill_name}
              description: "{description}"
              version: "1.0.0"
              difficulty: {difficulty}

            triggers:
              keywords: {json.dumps(trigger_keywords)}

            sections:
            {textwrap.indent(section_content.rstrip(), "  ")}

            quality_checks:
              min_correctness: 0.7
              min_completeness: 0.6
              min_efficiency: 0.5
              min_readability: 0.6
              min_maintainability: 0.5
        """)

    def _evaluate_quality(self, content: str) -> SkillQualityReport:
        """Score generated skill content across five dimensions (0.0-1.0)."""
        if not content:
            return SkillQualityReport()

        lines = content.lower().split("\n")
        total_lines = len(lines)
        if total_lines == 0:
            return SkillQualityReport()

        has_schema = any("metadata" in l or "domain:" in l for l in lines)
        has_errors = any("error" in l for l in lines)
        has_validation = any("validat" in l for l in lines)

        # Correctness: schema presence + error handling
        correctness = 0.5
        if has_schema:
            correctness += 0.2
        if has_validation:
            correctness += 0.15
        if has_errors:
            correctness += 0.15

        # Completeness: section coverage
        section_count = sum(1 for l in lines if l.strip().endswith(":"))
        completeness = min(1.0, 0.3 + section_count * 0.05)

        # Efficiency: compactness ratio (penalize excessive verbosity)
        avg_line_len = sum(len(l) for l in lines) / total_lines if total_lines else 0
        efficiency = min(1.0, 0.7 - abs(avg_line_len - 60) / 200)

        # Readability: comment density
        comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
        readability = min(1.0, 0.5 + comment_lines / max(total_lines, 1))

        # Maintainability: structure indicators
        has_structure = sum(1 for kw in ["steps:", "plan:", "checks:", "tests:", "sections:"] if kw in content.lower())
        maintainability = min(1.0, 0.4 + has_structure * 0.12)

        return SkillQualityReport(
            correctness=round(correctness, 4),
            completeness=round(completeness, 4),
            efficiency=round(efficiency, 4),
            readability=round(readability, 4),
            maintainability=round(maintainability, 4),
        )

    def _save_skill(self, skill: GeneratedSkill) -> str:
        """Write a generated skill to disk and return the file path."""
        output_dir = os.path.join(self.config.output_dir, skill.domain.value)
        os.makedirs(output_dir, exist_ok=True)

        safe_name = skill.template_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}.yaml"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(skill.content)

        return filepath

    def __repr__(self) -> str:
        return f"SkillGenerator(catalog_size={self.catalog.count}, generated={self.generated_count})"
