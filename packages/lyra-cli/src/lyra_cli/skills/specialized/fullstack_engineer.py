"""Fullstack Engineer Skill — end-to-end application architecture validation.

Analyzes fullstack applications for:
- Frontend-backend API contract consistency
- State management patterns
- Authentication flow completeness
- Data flow and validation
- Deployment readiness
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FullstackSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FullstackCategory(StrEnum):
    API_CONTRACT = "api_contract"
    STATE_MANAGEMENT = "state_management"
    AUTH_FLOW = "auth_flow"
    DATA_VALIDATION = "data_validation"
    DEPLOYMENT = "deployment"


@dataclass(frozen=True)
class FullstackIssue:
    category: FullstackCategory
    severity: FullstackSeverity
    component: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class FullstackReport:
    frontend_files: int
    backend_files: int
    issues: tuple[FullstackIssue, ...]
    score: int
    integration_health: str


class FullstackEngineerSkill:
    """Validates fullstack application architecture and integration patterns."""

    def __init__(self) -> None:
        self._issues: list[FullstackIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run fullstack architecture analysis.

        Args:
            input_data: Dictionary with keys:
                - frontend_code: Frontend source code
                - backend_code: Backend source code
                - api_spec: Optional OpenAPI/Swagger spec
                - auth_config: Optional authentication configuration

        Returns:
            Dictionary with analysis report data.
        """
        frontend = input_data.get("frontend_code", "")
        backend = input_data.get("backend_code", "")
        api_spec = input_data.get("api_spec", {})
        auth_config = input_data.get("auth_config", {})

        self._issues.clear()

        # Check API contract consistency
        self._check_api_contract(frontend, backend, api_spec)

        # Check authentication flow
        self._check_auth_flow(frontend, backend, auth_config)

        # Check state management
        self._check_state_management(frontend)

        # Check data validation
        self._check_data_validation(frontend, backend)

        # Check deployment readiness
        self._check_deployment_readiness(input_data)

        score = self._compute_score()
        health = self._compute_health(score)

        return FullstackReport(
            frontend_files=len(frontend.splitlines()) if frontend else 0,
            backend_files=len(backend.splitlines()) if backend else 0,
            issues=tuple(self._issues),
            score=score,
            integration_health=health,
        ).__dict__ | {"issues": [i.__dict__ for i in self._issues]}

    def _check_api_contract(self, frontend: str, backend: str, api_spec: dict) -> None:
        """Check frontend-backend API contract consistency."""
        # Check if frontend makes API calls
        has_fetch = "fetch(" in frontend or "axios." in frontend or "http." in frontend
        has_api_routes = "@app.route" in backend or "@router." in backend or "def " in backend

        if has_fetch and not has_api_routes:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.API_CONTRACT,
                    severity=FullstackSeverity.CRITICAL,
                    component="API",
                    message="Frontend makes API calls but no backend routes defined",
                    suggestion="Define backend API endpoints matching frontend requests",
                )
            )

        if not api_spec and has_fetch and has_api_routes:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.API_CONTRACT,
                    severity=FullstackSeverity.MEDIUM,
                    component="API",
                    message="No API specification (OpenAPI/Swagger) provided",
                    suggestion="Document API contract with OpenAPI spec for consistency",
                )
            )

        # Check CORS configuration
        if has_fetch and "cors" not in backend.lower() and "CORS" not in backend:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.API_CONTRACT,
                    severity=FullstackSeverity.HIGH,
                    component="API",
                    message="No CORS configuration detected",
                    suggestion="Configure CORS to allow frontend-backend communication",
                )
            )

    def _check_auth_flow(self, frontend: str, backend: str, auth_config: dict) -> None:
        """Check authentication flow completeness."""
        has_login_ui = "login" in frontend.lower() or "signin" in frontend.lower()
        has_auth_backend = (
            "authenticate" in backend.lower()
            or "login" in backend.lower()
            or "jwt" in backend.lower()
        )

        if has_login_ui and not has_auth_backend:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.AUTH_FLOW,
                    severity=FullstackSeverity.CRITICAL,
                    component="Authentication",
                    message="Login UI exists but no backend authentication",
                    suggestion="Implement backend authentication endpoints and token management",
                )
            )

        # Check token storage
        if has_login_ui and "localStorage" in frontend and "token" in frontend.lower():
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.AUTH_FLOW,
                    severity=FullstackSeverity.HIGH,
                    component="Authentication",
                    message="Tokens stored in localStorage (XSS vulnerable)",
                    suggestion="Use httpOnly cookies or secure session storage",
                )
            )

        # Check refresh token logic
        if has_auth_backend and "refresh" not in backend.lower():
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.AUTH_FLOW,
                    severity=FullstackSeverity.MEDIUM,
                    component="Authentication",
                    message="No refresh token mechanism detected",
                    suggestion="Implement refresh token flow for better UX",
                )
            )

    def _check_state_management(self, frontend: str) -> None:
        """Check frontend state management patterns."""
        has_state = (
            "useState" in frontend
            or "useReducer" in frontend
            or "createStore" in frontend
            or "createSlice" in frontend
        )

        has_global_state = (
            "Redux" in frontend
            or "Zustand" in frontend
            or "Recoil" in frontend
            or "Context" in frontend
        )

        if not has_state and len(frontend) > 500:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.STATE_MANAGEMENT,
                    severity=FullstackSeverity.MEDIUM,
                    component="Frontend",
                    message="No state management detected in non-trivial frontend",
                    suggestion="Implement state management with useState/Redux/Zustand",
                )
            )

        if has_state and not has_global_state and len(frontend) > 2000:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.STATE_MANAGEMENT,
                    severity=FullstackSeverity.LOW,
                    component="Frontend",
                    message="Large frontend without global state management",
                    suggestion="Consider Redux/Zustand for complex state sharing",
                )
            )

    def _check_data_validation(self, frontend: str, backend: str) -> None:
        """Check data validation on both ends."""
        has_frontend_validation = (
            "validate" in frontend.lower()
            or "schema" in frontend.lower()
            or "yup" in frontend.lower()
            or "zod" in frontend.lower()
        )

        has_backend_validation = (
            "validate" in backend.lower()
            or "schema" in backend.lower()
            or "pydantic" in backend.lower()
            or "marshmallow" in backend.lower()
        )

        if not has_frontend_validation:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.DATA_VALIDATION,
                    severity=FullstackSeverity.MEDIUM,
                    component="Frontend",
                    message="No frontend validation detected",
                    suggestion="Add client-side validation with Yup/Zod for better UX",
                )
            )

        if not has_backend_validation:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.DATA_VALIDATION,
                    severity=FullstackSeverity.CRITICAL,
                    component="Backend",
                    message="No backend validation detected",
                    suggestion="Add server-side validation with Pydantic/Marshmallow",
                )
            )

    def _check_deployment_readiness(self, input_data: dict) -> None:
        """Check deployment configuration."""
        has_dockerfile = input_data.get("has_dockerfile", False)
        has_docker_compose = input_data.get("has_docker_compose", False)
        has_ci_cd = input_data.get("has_ci_cd", False)
        has_env_example = input_data.get("has_env_example", False)

        if not has_dockerfile:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.DEPLOYMENT,
                    severity=FullstackSeverity.MEDIUM,
                    component="Infrastructure",
                    message="No Dockerfile found",
                    suggestion="Add Dockerfile for containerized deployment",
                )
            )

        if not has_docker_compose and has_dockerfile:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.DEPLOYMENT,
                    severity=FullstackSeverity.LOW,
                    component="Infrastructure",
                    message="No docker-compose.yml for local development",
                    suggestion="Add docker-compose for easy local setup",
                )
            )

        if not has_env_example:
            self._issues.append(
                FullstackIssue(
                    category=FullstackCategory.DEPLOYMENT,
                    severity=FullstackSeverity.MEDIUM,
                    component="Configuration",
                    message="No .env.example file",
                    suggestion="Add .env.example documenting required environment variables",
                )
            )

    def _compute_score(self) -> int:
        """Compute overall integration score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == FullstackSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == FullstackSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == FullstackSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == FullstackSeverity.LOW]) * 3,
        )

    def _compute_health(self, score: int) -> str:
        """Compute integration health status."""
        if score >= 90:
            return "excellent"
        if score >= 75:
            return "good"
        if score >= 60:
            return "fair"
        if score >= 40:
            return "poor"
        return "critical"
