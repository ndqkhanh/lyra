"""
Prompt Optimizer - Optimize prompts for better results.

Features:
- Template-based prompts
- Variable substitution
- Prompt compression
- Best practice enforcement
"""

from typing import Dict, List, Optional

from jinja2 import Template


class PromptOptimizer:
    """
    Optimize prompts for better results.

    Features:
    - Template management
    - Variable substitution
    - Compression
    """

    def __init__(self):
        """Initialize prompt optimizer."""
        self.templates: Dict[str, str] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default prompt templates."""
        self.templates = {
            "code_review": """Review the following code for:
- Security vulnerabilities
- Performance issues
- Best practices
- Code quality

Code:
```{{ language }}
{{ code }}
```

Provide specific, actionable feedback.""",
            "vulnerability_analysis": """Analyze this vulnerability:

CVE: {{ cve }}
Severity: {{ severity }}
Affected: {{ affected_system }}

Provide:
1. Exploitability assessment
2. Impact analysis
3. Remediation steps
4. Detection methods""",
            "exploit_development": """Develop exploit for:

Target: {{ target }}
Vulnerability: {{ vulnerability }}
Constraints: {{ constraints }}

Requirements:
- Safe execution
- Rollback capability
- Evidence collection
- User approval for unsafe operations""",
            "incident_response": """Respond to security incident:

Type: {{ incident_type }}
Severity: {{ severity }}
Affected Systems: {{ affected_systems }}

Provide:
1. Immediate containment steps
2. Investigation plan
3. Recovery procedures
4. Post-incident analysis""",
        }

    def register_template(self, name: str, template: str):
        """
        Register custom template.

        Args:
            name: Template name
            template: Template string (Jinja2 format)
        """
        self.templates[name] = template

    def render(self, template_name: str, **variables) -> str:
        """
        Render template with variables.

        Args:
            template_name: Template name
            **variables: Template variables

        Returns:
            Rendered prompt
        """
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")

        template = Template(self.templates[template_name])
        return template.render(**variables)

    def optimize(self, prompt: str) -> str:
        """
        Optimize prompt for better results.

        Args:
            prompt: Original prompt

        Returns:
            Optimized prompt
        """
        optimized = prompt

        # Remove excessive whitespace
        optimized = " ".join(optimized.split())

        # Add structure if missing
        if not any(marker in optimized for marker in ["1.", "2.", "-", "*"]):
            # Add numbered structure
            optimized = f"Task: {optimized}\n\nProvide:\n1. Analysis\n2. Recommendations\n3. Next steps"

        # Add specificity
        if len(optimized) < 50:
            optimized = f"{optimized}\n\nBe specific and provide actionable details."

        return optimized

    def compress(self, prompt: str, max_length: int = 1000) -> str:
        """
        Compress prompt while preserving meaning.

        Args:
            prompt: Original prompt
            max_length: Maximum character length

        Returns:
            Compressed prompt
        """
        if len(prompt) <= max_length:
            return prompt

        # Simple compression: keep first and last parts
        keep_length = max_length // 2
        compressed = prompt[:keep_length] + "\n...\n" + prompt[-keep_length:]

        return compressed

    def get_template_list(self) -> List[str]:
        """
        Get list of available templates.

        Returns:
            Template names
        """
        return list(self.templates.keys())
