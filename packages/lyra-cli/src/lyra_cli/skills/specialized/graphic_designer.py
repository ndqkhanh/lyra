"""Graphic Designer Skill — visual design and brand consistency validation.

Analyzes graphic designs for:
- Brand guideline compliance
- Visual hierarchy and composition
- Color theory application
- Typography and readability
- File format and technical specifications
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GraphicDesignSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GraphicDesignCategory(StrEnum):
    BRAND = "brand"
    COMPOSITION = "composition"
    COLOR = "color"
    TYPOGRAPHY = "typography"
    TECHNICAL = "technical"


@dataclass(frozen=True)
class GraphicDesignIssue:
    category: GraphicDesignCategory
    severity: GraphicDesignSeverity
    element: str
    message: str
    suggestion: str


class GraphicDesignerSkill:
    """Validates graphic design for brand consistency and technical quality."""

    def __init__(self) -> None:
        self._issues: list[GraphicDesignIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run graphic design analysis.

        Args:
            input_data: Dictionary with keys:
                - design_type: Type of design (logo, poster, social, web, print)
                - brand_guidelines: Brand guideline configuration
                - colors: List of colors used
                - fonts: List of fonts used
                - dimensions: Design dimensions
                - file_format: Output file format

        Returns:
            Dictionary with analysis report data.
        """
        design_type = input_data.get("design_type", "unknown")
        brand_guidelines = input_data.get("brand_guidelines", {})
        colors = input_data.get("colors", [])
        fonts = input_data.get("fonts", [])
        dimensions = input_data.get("dimensions", {})
        file_format = input_data.get("file_format", "")

        self._issues.clear()

        self._check_brand_compliance(colors, fonts, brand_guidelines, input_data)
        self._check_composition(input_data)
        self._check_color_usage(colors, design_type, input_data)
        self._check_typography(fonts, design_type, input_data)
        self._check_technical_specs(dimensions, file_format, design_type, input_data)

        score = self._compute_score()

        return {
            "design_type": design_type,
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
        }

    def _check_brand_compliance(
        self, colors: list, fonts: list, brand_guidelines: dict, input_data: dict
    ) -> None:
        """Check compliance with brand guidelines."""
        if not brand_guidelines:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.BRAND,
                    severity=GraphicDesignSeverity.HIGH,
                    element="brand_guidelines",
                    message="No brand guidelines provided",
                    suggestion="Reference brand guidelines for consistency",
                )
            )
            return

        # Check brand colors
        brand_colors = brand_guidelines.get("colors", [])
        if brand_colors:
            off_brand_colors = [c for c in colors if c not in brand_colors]
            if off_brand_colors and len(off_brand_colors) > 2:
                self._issues.append(
                    GraphicDesignIssue(
                        category=GraphicDesignCategory.BRAND,
                        severity=GraphicDesignSeverity.HIGH,
                        element="colors",
                        message=f"{len(off_brand_colors)} colors not in brand palette",
                        suggestion="Use colors from brand palette for consistency",
                    )
                )

        # Check brand fonts
        brand_fonts = brand_guidelines.get("fonts", [])
        if brand_fonts:
            off_brand_fonts = [f for f in fonts if f not in brand_fonts]
            if off_brand_fonts:
                self._issues.append(
                    GraphicDesignIssue(
                        category=GraphicDesignCategory.BRAND,
                        severity=GraphicDesignSeverity.CRITICAL,
                        element="typography",
                        message=f"Using non-brand fonts: {', '.join(off_brand_fonts)}",
                        suggestion="Use only brand-approved fonts",
                    )
                )

        # Check logo usage
        has_logo = input_data.get("has_logo", False)
        logo_placement = input_data.get("logo_placement", "")
        if has_logo and not logo_placement:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.BRAND,
                    severity=GraphicDesignSeverity.MEDIUM,
                    element="logo",
                    message="Logo placement not specified",
                    suggestion="Follow brand guidelines for logo placement and clear space",
                )
            )

    def _check_composition(self, input_data: dict) -> None:
        """Check visual composition and hierarchy."""
        has_focal_point = input_data.get("has_focal_point", False)
        if not has_focal_point:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COMPOSITION,
                    severity=GraphicDesignSeverity.HIGH,
                    element="layout",
                    message="No clear focal point defined",
                    suggestion="Establish clear visual hierarchy with a focal point",
                )
            )

        # Check rule of thirds
        uses_grid = input_data.get("uses_grid", False)
        if not uses_grid:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COMPOSITION,
                    severity=GraphicDesignSeverity.MEDIUM,
                    element="layout",
                    message="No grid system used",
                    suggestion="Use grid system or rule of thirds for balanced composition",
                )
            )

        # Check whitespace
        whitespace_ratio = input_data.get("whitespace_ratio", 0)
        if whitespace_ratio < 0.2:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COMPOSITION,
                    severity=GraphicDesignSeverity.MEDIUM,
                    element="layout",
                    message=f"Insufficient whitespace ({whitespace_ratio:.0%})",
                    suggestion="Increase whitespace to 20-30% for better readability",
                )
            )
        elif whitespace_ratio > 0.6:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COMPOSITION,
                    severity=GraphicDesignSeverity.LOW,
                    element="layout",
                    message=f"Excessive whitespace ({whitespace_ratio:.0%})",
                    suggestion="Consider adding more content or reducing canvas size",
                )
            )

        # Check alignment
        has_alignment = input_data.get("has_alignment", False)
        if not has_alignment:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COMPOSITION,
                    severity=GraphicDesignSeverity.MEDIUM,
                    element="layout",
                    message="Elements not properly aligned",
                    suggestion="Align elements to grid for professional appearance",
                )
            )

    def _check_color_usage(self, colors: list, design_type: str, input_data: dict) -> None:
        """Check color theory and usage."""
        if not colors:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COLOR,
                    severity=GraphicDesignSeverity.CRITICAL,
                    element="colors",
                    message="No colors defined",
                    suggestion="Define color palette for the design",
                )
            )
            return

        # Check color count
        if len(colors) > 5:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COLOR,
                    severity=GraphicDesignSeverity.MEDIUM,
                    element="colors",
                    message=f"Too many colors ({len(colors)}) - reduces cohesion",
                    suggestion="Limit to 3-5 colors for better harmony",
                )
            )

        # Check for color accessibility
        has_high_contrast = input_data.get("has_high_contrast", False)
        if not has_high_contrast:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.COLOR,
                    severity=GraphicDesignSeverity.HIGH,
                    element="colors",
                    message="Insufficient color contrast for accessibility",
                    suggestion="Ensure 4.5:1 contrast ratio for text (WCAG AA)",
                )
            )

        # Check for print vs digital color mode
        if design_type == "print":
            color_mode = input_data.get("color_mode", "")
            if color_mode != "CMYK":
                self._issues.append(
                    GraphicDesignIssue(
                        category=GraphicDesignCategory.TECHNICAL,
                        severity=GraphicDesignSeverity.CRITICAL,
                        element="color_mode",
                        message=f"Print design should use CMYK, not {color_mode}",
                        suggestion="Convert to CMYK color mode for print",
                    )
                )

    def _check_typography(self, fonts: list, design_type: str, input_data: dict) -> None:
        """Check typography usage."""
        if not fonts:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TYPOGRAPHY,
                    severity=GraphicDesignSeverity.CRITICAL,
                    element="typography",
                    message="No fonts specified",
                    suggestion="Define typography for the design",
                )
            )
            return

        # Check font count
        if len(fonts) > 3:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TYPOGRAPHY,
                    severity=GraphicDesignSeverity.HIGH,
                    element="typography",
                    message=f"Too many fonts ({len(fonts)}) - reduces consistency",
                    suggestion="Limit to 2-3 font families",
                )
            )

        # Check readability
        min_font_size = input_data.get("min_font_size", 0)
        if design_type in ("web", "mobile") and min_font_size < 14:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TYPOGRAPHY,
                    severity=GraphicDesignSeverity.HIGH,
                    element="typography",
                    message=f"Body text too small ({min_font_size}px) for digital",
                    suggestion="Use minimum 14-16px for body text on screens",
                )
            )
        elif design_type == "print" and min_font_size < 9:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TYPOGRAPHY,
                    severity=GraphicDesignSeverity.HIGH,
                    element="typography",
                    message=f"Body text too small ({min_font_size}pt) for print",
                    suggestion="Use minimum 9-10pt for print body text",
                )
            )

        # Check line height
        line_height = input_data.get("line_height", 0)
        if line_height < 1.2:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TYPOGRAPHY,
                    severity=GraphicDesignSeverity.MEDIUM,
                    element="typography",
                    message=f"Line height too tight ({line_height})",
                    suggestion="Use 1.4-1.6 line height for body text",
                )
            )

    def _check_technical_specs(
        self, dimensions: dict, file_format: str, design_type: str, input_data: dict
    ) -> None:
        """Check technical specifications."""
        # Check dimensions
        width = dimensions.get("width", 0)
        height = dimensions.get("height", 0)

        if not width or not height:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TECHNICAL,
                    severity=GraphicDesignSeverity.CRITICAL,
                    element="dimensions",
                    message="Dimensions not specified",
                    suggestion="Define width and height for the design",
                )
            )

        # Check resolution
        dpi = input_data.get("dpi", 0)
        if design_type == "print" and dpi < 300:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TECHNICAL,
                    severity=GraphicDesignSeverity.CRITICAL,
                    element="resolution",
                    message=f"Print design at {dpi} DPI - too low",
                    suggestion="Use 300 DPI minimum for print",
                )
            )
        elif design_type in ("web", "mobile") and dpi > 150:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TECHNICAL,
                    severity=GraphicDesignSeverity.LOW,
                    element="resolution",
                    message=f"Web design at {dpi} DPI - unnecessarily high",
                    suggestion="72-96 DPI is sufficient for web/mobile",
                )
            )

        # Check file format
        if not file_format:
            self._issues.append(
                GraphicDesignIssue(
                    category=GraphicDesignCategory.TECHNICAL,
                    severity=GraphicDesignSeverity.HIGH,
                    element="file_format",
                    message="Output file format not specified",
                    suggestion="Define appropriate file format for use case",
                )
            )
        else:
            recommended_formats = {
                "logo": ["svg", "eps", "ai"],
                "web": ["svg", "png", "webp"],
                "print": ["pdf", "eps", "tiff"],
                "social": ["png", "jpg"],
            }
            recommended = recommended_formats.get(design_type, [])
            if recommended and file_format.lower() not in recommended:
                self._issues.append(
                    GraphicDesignIssue(
                        category=GraphicDesignCategory.TECHNICAL,
                        severity=GraphicDesignSeverity.MEDIUM,
                        element="file_format",
                        message=f"{file_format} not ideal for {design_type}",
                        suggestion=f"Consider {', '.join(recommended)} for {design_type}",
                    )
                )

        # Check bleed for print
        if design_type == "print":
            has_bleed = input_data.get("has_bleed", False)
            if not has_bleed:
                self._issues.append(
                    GraphicDesignIssue(
                        category=GraphicDesignCategory.TECHNICAL,
                        severity=GraphicDesignSeverity.HIGH,
                        element="bleed",
                        message="No bleed defined for print design",
                        suggestion="Add 3mm bleed on all sides for print",
                    )
                )

    def _compute_score(self) -> int:
        """Compute overall graphic design quality score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == GraphicDesignSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == GraphicDesignSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == GraphicDesignSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == GraphicDesignSeverity.LOW]) * 3,
        )
