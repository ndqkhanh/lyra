"""
Product Manager Skill - Product strategy and roadmap planning.

Given a product vision, produces:
- Product roadmap
- Feature prioritization
- User story mapping
- Success metrics
- Go-to-market strategy

Outputs structured product plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Priority(StrEnum):
    """Feature priority levels."""

    P0_CRITICAL = "P0_critical"
    P1_HIGH = "P1_high"
    P2_MEDIUM = "P2_medium"
    P3_LOW = "P3_low"


class RoadmapPhase(StrEnum):
    """Roadmap phases."""

    NOW = "now"
    NEXT = "next"
    LATER = "later"
    FUTURE = "future"


@dataclass(frozen=True)
class Feature:
    """Product feature specification."""

    name: str
    description: str
    priority: Priority
    user_value: str
    effort_estimate: str
    success_metrics: tuple[str, ...]


@dataclass(frozen=True)
class UserStory:
    """User story specification."""

    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: tuple[str, ...]


@dataclass(frozen=True)
class RoadmapItem:
    """Roadmap item."""

    phase: RoadmapPhase
    features: tuple[str, ...]
    timeline: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class SuccessMetric:
    """Product success metric."""

    metric_name: str
    target: str
    measurement_method: str
    frequency: str


@dataclass(frozen=True)
class GTMStrategy:
    """Go-to-market strategy."""

    target_audience: str
    positioning: str
    channels: tuple[str, ...]
    launch_plan: tuple[str, ...]


@dataclass(frozen=True)
class ProductPlan:
    """Complete product plan."""

    product_name: str
    vision: str
    features: tuple[Feature, ...]
    user_stories: tuple[UserStory, ...]
    roadmap: tuple[RoadmapItem, ...]
    success_metrics: tuple[SuccessMetric, ...]
    gtm_strategy: GTMStrategy


class ProductManager:
    """Product management skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run product planning.

        Args:
            input_data: Dictionary with keys:
                - product_vision: Product vision statement
                - product_name: Optional product name (default "Product")

        Returns:
            Dictionary with product plan data.
        """
        vision = input_data.get("product_vision", "")
        if not vision:
            return {"error": "No product vision provided"}

        product_name = input_data.get("product_name", "Product")
        vision_lower = vision.lower()

        features = self._identify_features(vision_lower)
        user_stories = self._create_user_stories(features)
        roadmap = self._build_roadmap(features)
        metrics = self._define_success_metrics()
        gtm = self._design_gtm_strategy(vision_lower)

        return ProductPlan(
            product_name=product_name,
            vision=vision,
            features=tuple(features),
            user_stories=tuple(user_stories),
            roadmap=tuple(roadmap),
            success_metrics=tuple(metrics),
            gtm_strategy=gtm,
        ).__dict__ | {
            "features": [f.__dict__ for f in features],
            "user_stories": [u.__dict__ for u in user_stories],
            "roadmap": [r.__dict__ for r in roadmap],
            "success_metrics": [m.__dict__ for m in metrics],
            "gtm_strategy": gtm.__dict__,
        }

    @staticmethod
    def _identify_features(vision: str) -> list[Feature]:
        return [
            Feature(
                name="User Authentication",
                description="Secure user login and registration",
                priority=Priority.P0_CRITICAL,
                user_value="Users can securely access their accounts",
                effort_estimate="2 weeks",
                success_metrics=("Registration conversion rate > 60%", "Login success rate > 95%"),
            ),
            Feature(
                name="Core Functionality",
                description="Primary product feature set",
                priority=Priority.P0_CRITICAL,
                user_value="Users can accomplish their primary goals",
                effort_estimate="6 weeks",
                success_metrics=("Feature adoption > 70%", "Task completion rate > 80%"),
            ),
            Feature(
                name="Analytics Dashboard",
                description="User activity and insights dashboard",
                priority=Priority.P1_HIGH,
                user_value="Users can track their progress and insights",
                effort_estimate="3 weeks",
                success_metrics=("Dashboard engagement > 50%", "Daily active users +20%"),
            ),
            Feature(
                name="Mobile App",
                description="Native mobile application",
                priority=Priority.P2_MEDIUM,
                user_value="Users can access product on mobile devices",
                effort_estimate="8 weeks",
                success_metrics=("Mobile MAU > 40% of total", "App store rating > 4.5"),
            ),
        ]

    @staticmethod
    def _create_user_stories(features: list[Feature]) -> list[UserStory]:
        return [
            UserStory(
                as_a="new user",
                i_want="to create an account quickly",
                so_that="I can start using the product immediately",
                acceptance_criteria=(
                    "Registration form has < 5 fields",
                    "Email verification is optional",
                    "Social login options available",
                ),
            ),
            UserStory(
                as_a="returning user",
                i_want="to see my recent activity",
                so_that="I can pick up where I left off",
                acceptance_criteria=(
                    "Dashboard shows last 10 activities",
                    "Quick actions for common tasks",
                    "Personalized recommendations",
                ),
            ),
            UserStory(
                as_a="power user",
                i_want="to customize my workflow",
                so_that="I can work more efficiently",
                acceptance_criteria=(
                    "Customizable dashboard layout",
                    "Keyboard shortcuts available",
                    "Saved preferences persist",
                ),
            ),
        ]

    @staticmethod
    def _build_roadmap(features: list[Feature]) -> list[RoadmapItem]:
        p0_features = [f.name for f in features if f.priority == Priority.P0_CRITICAL]
        p1_features = [f.name for f in features if f.priority == Priority.P1_HIGH]
        p2_features = [f.name for f in features if f.priority == Priority.P2_MEDIUM]

        return [
            RoadmapItem(
                phase=RoadmapPhase.NOW,
                features=tuple(p0_features),
                timeline="Q1 2026 (Months 1-3)",
                dependencies=(),
            ),
            RoadmapItem(
                phase=RoadmapPhase.NEXT,
                features=tuple(p1_features),
                timeline="Q2 2026 (Months 4-6)",
                dependencies=tuple(p0_features),
            ),
            RoadmapItem(
                phase=RoadmapPhase.LATER,
                features=tuple(p2_features),
                timeline="Q3 2026 (Months 7-9)",
                dependencies=tuple(p1_features),
            ),
        ]

    @staticmethod
    def _define_success_metrics() -> list[SuccessMetric]:
        return [
            SuccessMetric(
                metric_name="Monthly Active Users (MAU)",
                target="10,000 MAU by end of Q2",
                measurement_method="Analytics platform (Mixpanel/Amplitude)",
                frequency="Weekly",
            ),
            SuccessMetric(
                metric_name="User Retention (Day 7)",
                target="> 40% Day 7 retention",
                measurement_method="Cohort analysis",
                frequency="Weekly",
            ),
            SuccessMetric(
                metric_name="Net Promoter Score (NPS)",
                target="NPS > 50",
                measurement_method="In-app survey",
                frequency="Monthly",
            ),
            SuccessMetric(
                metric_name="Feature Adoption",
                target="> 70% of users use core features",
                measurement_method="Feature usage tracking",
                frequency="Weekly",
            ),
        ]

    @staticmethod
    def _design_gtm_strategy(vision: str) -> GTMStrategy:
        return GTMStrategy(
            target_audience="Early adopters and tech-savvy users aged 25-45",
            positioning="The fastest and most intuitive solution for [problem]",
            channels=(
                "Product Hunt launch",
                "Content marketing (blog, SEO)",
                "Social media (Twitter, LinkedIn)",
                "Partnerships with complementary products",
            ),
            launch_plan=(
                "Week 1: Beta launch to 100 early access users",
                "Week 2-3: Gather feedback and iterate",
                "Week 4: Public launch on Product Hunt",
                "Week 5-8: Content marketing and SEO ramp-up",
                "Week 9-12: Partnership outreach and integrations",
            ),
        )
