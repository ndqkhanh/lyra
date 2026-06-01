"""
Demo Specialist Skill - Product demonstration and presentation planning.

Given product and audience, produces:
- Demo script
- Presentation flow
- Key talking points
- Objection handling
- Follow-up strategy

Outputs structured demo plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AudienceType(StrEnum):
    """Types of demo audiences."""

    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    END_USER = "end_user"
    MIXED = "mixed"


@dataclass(frozen=True)
class DemoSegment:
    """Demo segment."""

    segment_name: str
    duration_minutes: int
    objective: str
    talking_points: tuple[str, ...]
    demo_actions: tuple[str, ...]


@dataclass(frozen=True)
class TalkingPoint:
    """Key talking point."""

    topic: str
    message: str
    supporting_data: tuple[str, ...]


@dataclass(frozen=True)
class ObjectionResponse:
    """Objection and response."""

    objection: str
    response_strategy: str
    example_response: str


@dataclass(frozen=True)
class FollowUpAction:
    """Follow-up action."""

    action: str
    timing: str
    owner: str


@dataclass(frozen=True)
class DemoPlan:
    """Complete demo plan."""

    product_name: str
    audience_type: AudienceType
    demo_segments: tuple[DemoSegment, ...]
    key_talking_points: tuple[TalkingPoint, ...]
    objection_responses: tuple[ObjectionResponse, ...]
    follow_up_actions: tuple[FollowUpAction, ...]


class DemoSpecialist:
    """Demo specialist skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run demo planning.

        Args:
            input_data: Dictionary with keys:
                - product_name: Product name
                - audience_type: Optional audience type (default "mixed")

        Returns:
            Dictionary with demo plan data.
        """
        product_name = input_data.get("product_name", "")
        if not product_name:
            return {"error": "No product name provided"}

        audience_str = input_data.get("audience_type", "mixed").lower()
        try:
            audience_type = AudienceType(audience_str)
        except ValueError:
            audience_type = AudienceType.MIXED

        segments = self._design_demo_segments(audience_type)
        talking_points = self._prepare_talking_points()
        objections = self._prepare_objection_responses()
        follow_up = self._plan_follow_up_actions()

        return DemoPlan(
            product_name=product_name,
            audience_type=audience_type,
            demo_segments=tuple(segments),
            key_talking_points=tuple(talking_points),
            objection_responses=tuple(objections),
            follow_up_actions=tuple(follow_up),
        ).__dict__ | {
            "demo_segments": [s.__dict__ for s in segments],
            "key_talking_points": [t.__dict__ for t in talking_points],
            "objection_responses": [o.__dict__ for o in objections],
            "follow_up_actions": [f.__dict__ for f in follow_up],
        }

    @staticmethod
    def _design_demo_segments(audience_type: AudienceType) -> list[DemoSegment]:
        if audience_type == AudienceType.EXECUTIVE:
            return [
                DemoSegment(
                    segment_name="Business Value Overview",
                    duration_minutes=5,
                    objective="Establish ROI and strategic value",
                    talking_points=(
                        "Market trends and business drivers",
                        "Quantified business outcomes",
                        "Customer success stories",
                    ),
                    demo_actions=(
                        "Show executive dashboard with KPIs",
                        "Highlight ROI calculator",
                    ),
                ),
                DemoSegment(
                    segment_name="High-Level Solution Overview",
                    duration_minutes=10,
                    objective="Show how solution addresses business challenges",
                    talking_points=(
                        "Key capabilities aligned to challenges",
                        "Differentiation from competitors",
                        "Implementation approach",
                    ),
                    demo_actions=(
                        "Walk through main workflow at high level",
                        "Show integration architecture diagram",
                    ),
                ),
            ]
        else:
            return [
                DemoSegment(
                    segment_name="Introduction",
                    duration_minutes=3,
                    objective="Set context and agenda",
                    talking_points=(
                        "Agenda overview",
                        "Key challenges we'll address",
                        "Demo format and Q&A approach",
                    ),
                    demo_actions=("Show agenda slide",),
                ),
                DemoSegment(
                    segment_name="Core Features Demo",
                    duration_minutes=15,
                    objective="Demonstrate key product capabilities",
                    talking_points=(
                        "Feature 1: Workflow automation",
                        "Feature 2: Real-time collaboration",
                        "Feature 3: Analytics and reporting",
                    ),
                    demo_actions=(
                        "Create and automate a workflow",
                        "Invite collaborator and show real-time updates",
                        "Generate and customize a report",
                    ),
                ),
                DemoSegment(
                    segment_name="Advanced Capabilities",
                    duration_minutes=10,
                    objective="Show differentiation and enterprise features",
                    talking_points=(
                        "API and integration capabilities",
                        "Security and compliance",
                        "Scalability and performance",
                    ),
                    demo_actions=(
                        "Show API documentation",
                        "Demonstrate SSO and RBAC",
                        "Show performance metrics",
                    ),
                ),
                DemoSegment(
                    segment_name="Q&A and Next Steps",
                    duration_minutes=7,
                    objective="Address questions and define next steps",
                    talking_points=(
                        "Answer questions",
                        "Discuss POC or trial",
                        "Outline implementation timeline",
                    ),
                    demo_actions=("Show implementation roadmap slide",),
                ),
            ]

    @staticmethod
    def _prepare_talking_points() -> list[TalkingPoint]:
        return [
            TalkingPoint(
                topic="Time to Value",
                message="Customers see ROI within 3-6 months",
                supporting_data=(
                    "Average implementation: 8 weeks",
                    "Customer case study: 40% efficiency gain in 4 months",
                    "Industry benchmark: 12-18 months for competitors",
                ),
            ),
            TalkingPoint(
                topic="Ease of Use",
                message="Intuitive interface requires minimal training",
                supporting_data=(
                    "90%+ user adoption within 30 days",
                    "Average training time: 2 hours",
                    "User satisfaction score: 4.7/5",
                ),
            ),
            TalkingPoint(
                topic="Enterprise Ready",
                message="Built for scale with enterprise-grade security",
                supporting_data=(
                    "SOC 2 Type II certified",
                    "99.9% uptime SLA",
                    "Supports 10,000+ concurrent users",
                ),
            ),
        ]

    @staticmethod
    def _prepare_objection_responses() -> list[ObjectionResponse]:
        return [
            ObjectionResponse(
                objection="This looks complicated for our users",
                response_strategy="Acknowledge, then show simplified view and training resources",
                example_response=(
                    "I understand that concern. Let me show you our simplified user mode "
                    "designed for occasional users. We also provide interactive training "
                    "modules that get users productive in under 2 hours."
                ),
            ),
            ObjectionResponse(
                objection="How is this different from [Competitor]?",
                response_strategy="Acknowledge competitor, then highlight 2-3 key differentiators",
                example_response=(
                    "[Competitor] is a solid solution. Where we differentiate is in three areas: "
                    "1) Our AI-powered automation reduces manual work by 60%, "
                    "2) Our open API enables deeper integrations, and "
                    "3) Our implementation time is 50% faster."
                ),
            ),
            ObjectionResponse(
                objection="What about pricing?",
                response_strategy="Defer to value discussion, then provide range",
                example_response=(
                    "Great question. Our pricing is based on the value you'll receive. "
                    "Based on what we've discussed, you'd see $500K in annual savings. "
                    "Our typical investment for an organization your size is $200-300K, "
                    "giving you a strong ROI. Let's schedule a follow-up to discuss a detailed proposal."
                ),
            ),
        ]

    @staticmethod
    def _plan_follow_up_actions() -> list[FollowUpAction]:
        return [
            FollowUpAction(
                action="Send demo recording and slides",
                timing="Within 24 hours",
                owner="Sales Rep",
            ),
            FollowUpAction(
                action="Schedule technical deep-dive with engineering team",
                timing="Within 1 week",
                owner="Sales Engineer",
            ),
            FollowUpAction(
                action="Provide custom ROI analysis",
                timing="Within 3 days",
                owner="Solution Consultant",
            ),
            FollowUpAction(
                action="Share customer references in similar industry",
                timing="Within 2 days",
                owner="Sales Rep",
            ),
        ]
