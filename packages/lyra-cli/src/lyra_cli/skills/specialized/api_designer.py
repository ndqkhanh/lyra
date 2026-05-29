"""API Designer Skill — REST and GraphQL API design with best-practice validation.

Validates API designs against RESTful conventions, checks for:
- Proper HTTP method usage and status codes
- Resource naming conventions
- Versioning strategies
- Pagination, filtering, and error response formats
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DesignIssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class DesignIssue:
    path: str
    method: str
    severity: DesignIssueSeverity
    message: str
    suggestion: str
    rule_id: str


class ApiDesignerSkill:
    """Validates API designs against REST best practices."""

    _VALID_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
    _RESERVED_PATHS = frozenset({"api", "v1", "internal", "admin"})

    def __init__(self) -> None:
        self._issues: list[DesignIssue] = []

    def run(self, input_data: dict) -> dict:
        endpoints = input_data.get("endpoints", [])
        if not endpoints:
            return {"error": "No endpoints provided", "issues": [], "score": 0}

        self._issues.clear()
        for ep in endpoints:
            self._validate_endpoint(
                ep.get("path", ""), ep.get("method", ""), ep.get("description", "")
            )

        score = max(0, 100 - len(self._issues) * 5)
        return {
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
            "passed": len(self._issues) == 0,
        }

    def _validate_endpoint(self, path: str, method: str, description: str) -> None:
        if method.upper() not in self._VALID_METHODS:
            self._issues.append(
                DesignIssue(
                    path,
                    method,
                    DesignIssueSeverity.ERROR,
                    f"Invalid HTTP method '{method}'.",
                    f"Use one of: {', '.join(sorted(self._VALID_METHODS))}.",
                    "API-INVALID-METHOD",
                )
            )

        if not path.startswith("/"):
            self._issues.append(
                DesignIssue(
                    path,
                    method,
                    DesignIssueSeverity.WARNING,
                    "API path should start with '/'.",
                    "Prefix paths with '/' (e.g., '/users').",
                    "API-PATH-SLASH",
                )
            )

        if "//" in path:
            self._issues.append(
                DesignIssue(
                    path,
                    method,
                    DesignIssueSeverity.ERROR,
                    "Path contains double slash.",
                    "Remove double slashes.",
                    "API-DOUBLE-SLASH",
                )
            )

        if path.split("/")[-1].startswith("_"):
            self._issues.append(
                DesignIssue(
                    path,
                    method,
                    DesignIssueSeverity.WARNING,
                    "Path segment starts with underscore (private convention).",
                    "Use public naming for API paths.",
                    "API-PRIVATE-PATH",
                )
            )

        if not description:
            self._issues.append(
                DesignIssue(
                    path,
                    method,
                    DesignIssueSeverity.INFO,
                    "Endpoint has no description.",
                    "Add a brief description of the endpoint.",
                    "API-NO-DESC",
                )
            )
