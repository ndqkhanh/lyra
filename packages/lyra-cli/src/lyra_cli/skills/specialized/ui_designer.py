"""UI Designer Skill — visual design and component consistency validation.

Analyzes UI designs for:
- Design system consistency
- Color contrast and accessibility
- Typography hierarchy
- Spacing and layout grid
- Component reusability
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class UIDesignSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UIDesignCategory(StrEnum):
    ACCESSIBILITY = "accessibility"
    CONSISTENCY = "consistency"
    TYPOGRAPHY = "typography"
    LAYOUT = "layout"
    COLOR = "color"


@dataclass(frozen=True)
class UIDesignIssue:
    category: UIDesignCategory
    severity: UIDesignSeverity
    element: str
    message: str
    suggestion: str


class UIDesignerSkill:
    """Validates UI design for consistency and accessibility."""

    def __init__(self) -> None:
        self._issues: list[UIDesignIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run UI design analysis.

        Args:
            input_data: Dictionary with keys:
                - components: List of UI components with properties
                - design_system: Design system configuration
                - color_palette: Color palette definition

        Returns:
            Dictionary with analysis report data.
        """
        components = input_data.get("components", [])
        design_system = input_data.get("design_system", {})
        color_palette = input_data.get("color_palette", {})

        self._issues.clear()

        self._check_color_contrast(components, color_palette)
        self._check_typography(components, design_system)
        self._check_spacing(components, design_system)
        self._check_consistency(components, design_system)
        self._check_component_reusability(components)

        score = self._compute_score()

        return {
            "components_analyzed": len(components),
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
        }

    def _check_color_contrast(self, components: list, color_palette: dict) -> None:
        """Check color contrast for accessibility (WCAG AA)."""
        for comp in components:
            fg_color = comp.get("foreground_color")
            bg_color = comp.get("background_color")

            if fg_color and bg_color:
                # Simplified contrast check (real implementation would calculate actual ratio)
                contrast_ratio = comp.get("contrast_ratio", 0)

                if contrast_ratio < 4.5:  # WCAG AA for normal text
                    self._issues.append(
                        UIDesignIssue(
                            category=UIDesignCategory.ACCESSIBILITY,
                            severity=UIDesignSeverity.CRITICAL,
                            element=comp.get("name", "unknown"),
                            message=f"Insufficient color contrast ({contrast_ratio:.1f}:1, need 4.5:1)",
                            suggestion="Increase contrast between foreground and background colors",
                        )
                    )

        # Check for color palette consistency
        if not color_palette:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.CONSISTENCY,
                    severity=UIDesignSeverity.HIGH,
                    element="color_palette",
                    message="No color palette defined",
                    suggestion="Define a consistent color palette in design system",
                )
            )

        # Check for too many colors
        unique_colors = set()
        for comp in components:
            if "color" in comp:
                unique_colors.add(comp["color"])

        if len(unique_colors) > 12:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.CONSISTENCY,
                    severity=UIDesignSeverity.MEDIUM,
                    element="color_palette",
                    message=f"Too many unique colors ({len(unique_colors)}) - reduces consistency",
                    suggestion="Limit to 8-12 colors in design system",
                )
            )

    def _check_typography(self, components: list, design_system: dict) -> None:
        """Check typography consistency and hierarchy."""
        font_sizes = []
        font_families = set()

        for comp in components:
            if "font_size" in comp:
                font_sizes.append(comp["font_size"])
            if "font_family" in comp:
                font_families.add(comp["font_family"])

        # Check for too many font sizes
        unique_sizes = set(font_sizes)
        if len(unique_sizes) > 8:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.TYPOGRAPHY,
                    severity=UIDesignSeverity.MEDIUM,
                    element="typography",
                    message=f"Too many font sizes ({len(unique_sizes)}) - inconsistent hierarchy",
                    suggestion="Use type scale with 5-8 sizes (e.g., 12, 14, 16, 20, 24, 32, 48)",
                )
            )

        # Check for too many font families
        if len(font_families) > 3:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.TYPOGRAPHY,
                    severity=UIDesignSeverity.HIGH,
                    element="typography",
                    message=f"Too many font families ({len(font_families)}) - reduces cohesion",
                    suggestion="Limit to 2-3 font families (heading, body, monospace)",
                )
            )

        # Check for missing typography scale
        if not design_system.get("typography_scale"):
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.TYPOGRAPHY,
                    severity=UIDesignSeverity.MEDIUM,
                    element="design_system",
                    message="No typography scale defined",
                    suggestion="Define typography scale in design system",
                )
            )

    def _check_spacing(self, components: list, design_system: dict) -> None:
        """Check spacing consistency."""
        spacing_values = []

        for comp in components:
            if "padding" in comp:
                spacing_values.append(comp["padding"])
            if "margin" in comp:
                spacing_values.append(comp["margin"])
            if "gap" in comp:
                spacing_values.append(comp["gap"])

        # Check for spacing scale
        spacing_scale = design_system.get("spacing_scale", [])
        if not spacing_scale:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.LAYOUT,
                    severity=UIDesignSeverity.MEDIUM,
                    element="design_system",
                    message="No spacing scale defined",
                    suggestion="Define spacing scale (e.g., 4, 8, 12, 16, 24, 32, 48, 64)",
                )
            )

        # Check for arbitrary spacing values
        if spacing_scale:
            for value in spacing_values:
                if value not in spacing_scale and value != 0:
                    self._issues.append(
                        UIDesignIssue(
                            category=UIDesignCategory.LAYOUT,
                            severity=UIDesignSeverity.LOW,
                            element="spacing",
                            message=f"Spacing value {value} not in design system scale",
                            suggestion="Use values from spacing scale for consistency",
                        )
                    )
                    break  # Report once

    def _check_consistency(self, components: list, design_system: dict) -> None:
        """Check overall design consistency."""
        # Check for design tokens
        has_tokens = design_system.get("has_design_tokens", False)
        if not has_tokens and len(components) > 5:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.CONSISTENCY,
                    severity=UIDesignSeverity.HIGH,
                    element="design_system",
                    message="No design tokens defined",
                    suggestion="Define design tokens for colors, spacing, typography",
                )
            )

        # Check for component variants
        component_types = {}
        for comp in components:
            comp_type = comp.get("type", "unknown")
            component_types[comp_type] = component_types.get(comp_type, 0) + 1

        # Check for duplicate similar components
        for comp_type, count in component_types.items():
            if count > 5 and comp_type not in ("text", "div", "span"):
                self._issues.append(
                    UIDesignIssue(
                        category=UIDesignCategory.CONSISTENCY,
                        severity=UIDesignSeverity.MEDIUM,
                        element=comp_type,
                        message=f"Many instances of {comp_type} ({count}) - consider variants",
                        suggestion="Create component variants instead of duplicating",
                    )
                )

    def _check_component_reusability(self, components: list) -> None:
        """Check component reusability patterns."""
        # Check for atomic design principles
        atomic_levels = {"atom": 0, "molecule": 0, "organism": 0, "template": 0}

        for comp in components:
            level = comp.get("atomic_level")
            if level in atomic_levels:
                atomic_levels[level] += 1

        # Check if using atomic design
        total_categorized = sum(atomic_levels.values())
        if total_categorized == 0 and len(components) > 10:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.CONSISTENCY,
                    severity=UIDesignSeverity.LOW,
                    element="architecture",
                    message="Components not organized by atomic design principles",
                    suggestion="Consider organizing components as atoms, molecules, organisms",
                )
            )

        # Check for component documentation
        documented = sum(1 for c in components if c.get("has_documentation"))
        if documented < len(components) * 0.5:
            self._issues.append(
                UIDesignIssue(
                    category=UIDesignCategory.CONSISTENCY,
                    severity=UIDesignSeverity.MEDIUM,
                    element="documentation",
                    message=f"Only {documented}/{len(components)} components documented",
                    suggestion="Document all components with usage examples",
                )
            )

    def _compute_score(self) -> int:
        """Compute overall UI design quality score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == UIDesignSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == UIDesignSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == UIDesignSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == UIDesignSeverity.LOW]) * 3,
        )
