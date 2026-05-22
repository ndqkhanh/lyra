"""Research Agent implementation."""

from __future__ import annotations

import uuid
from typing import Any

from lyra_core.orchestration.agent_base import AgentStatus, BaseAgent
from lyra_core.orchestration.models.research import (
    Paper,
    PaperSource,
    ProjectEvaluation,
    ProjectQuality,
    RepoAnalysis,
    ResearchReport,
)
from lyra_core.orchestration.protocol import Message, MessageType


class ResearchAgent(BaseAgent):
    """Research agent responsible for research and analysis.

    Responsibilities:
    - Search academic papers (arXiv, Semantic Scholar)
    - Analyze GitHub repositories
    - Evaluate open source projects
    - Synthesize research findings
    - Generate research reports
    """

    async def on_start(self) -> None:
        """Initialize Research agent."""
        self._set_status(AgentStatus.IDLE)

    async def on_stop(self) -> None:
        """Cleanup Research agent."""
        pass

    async def on_message(self, message: Message) -> None:
        """Handle incoming messages.

        Args:
            message: Received message
        """
        action = message.payload.get("action")

        if action == "search_papers":
            await self._handle_search_papers(message)
        elif action == "analyze_github_repos":
            await self._handle_analyze_github_repos(message)
        elif action == "evaluate_projects":
            await self._handle_evaluate_projects(message)
        elif action == "synthesize_findings":
            await self._handle_synthesize_findings(message)
        else:
            await self.send_response(
                message,
                {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                },
            )

    async def _handle_search_papers(self, message: Message) -> None:
        """Handle paper search request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            query = message.payload.get("query", "")

            papers = await self.search_papers(query)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "papers": [
                        {
                            "id": paper.id,
                            "title": paper.title,
                            "authors": list(paper.authors),
                            "abstract": paper.abstract,
                            "url": paper.url,
                            "source": paper.source.value,
                            "published_date": paper.published_date,
                            "citations": paper.citations,
                            "relevance_score": paper.relevance_score,
                            "created_at": paper.created_at,
                        }
                        for paper in papers
                    ],
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_analyze_github_repos(self, message: Message) -> None:
        """Handle GitHub repository analysis request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            query = message.payload.get("query", "")

            repos = await self.analyze_github_repos(query)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "repositories": [
                        {
                            "id": repo.id,
                            "repo_url": repo.repo_url,
                            "name": repo.name,
                            "description": repo.description,
                            "stars": repo.stars,
                            "forks": repo.forks,
                            "language": repo.language,
                            "topics": list(repo.topics),
                            "last_updated": repo.last_updated,
                            "license": repo.license,
                            "relevance_score": repo.relevance_score,
                            "created_at": repo.created_at,
                        }
                        for repo in repos
                    ],
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_evaluate_projects(self, message: Message) -> None:
        """Handle project evaluation request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            projects_data = message.payload.get("projects", [])

            evaluations = await self.evaluate_projects(projects_data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "evaluations": [
                        {
                            "id": eval.id,
                            "project_name": eval.project_name,
                            "project_url": eval.project_url,
                            "quality": eval.quality.value,
                            "strengths": list(eval.strengths),
                            "weaknesses": list(eval.weaknesses),
                            "use_cases": list(eval.use_cases),
                            "recommendation": eval.recommendation,
                            "score": eval.score,
                            "created_at": eval.created_at,
                        }
                        for eval in evaluations
                    ],
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_synthesize_findings(self, message: Message) -> None:
        """Handle research synthesis request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            data = message.payload.get("research_data", {})

            report = await self.synthesize_findings(data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "research_report": {
                        "id": report.id,
                        "title": report.title,
                        "query": report.query,
                        "summary": report.summary,
                        "key_findings": list(report.key_findings),
                        "recommendations": list(report.recommendations),
                        "created_at": report.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def search_papers(self, query: str) -> list[Paper]:
        """Search academic papers.

        Args:
            query: Search query

        Returns:
            List of Paper objects
        """
        # In production, this would call arXiv, Semantic Scholar APIs
        papers = []

        # Simulate paper search results
        for i in range(3):
            paper = Paper.create(
                id=str(uuid.uuid4()),
                title=f"Research Paper {i + 1}: {query}",
                authors=["Author A", "Author B", "Author C"],
                abstract=f"This paper explores {query} and presents novel findings...",
                url=f"https://arxiv.org/abs/2024.{i + 1:05d}",
                source=PaperSource.ARXIV,
                published_date="2024-01-15",
                citations=100 - (i * 20),
                relevance_score=0.9 - (i * 0.1),
            )
            papers.append(paper)

        return papers

    async def analyze_github_repos(self, query: str) -> list[RepoAnalysis]:
        """Analyze GitHub repositories.

        Args:
            query: Search query

        Returns:
            List of RepoAnalysis objects
        """
        # In production, this would call GitHub API
        repos = []

        # Simulate repository analysis
        for i in range(3):
            repo = RepoAnalysis.create(
                id=str(uuid.uuid4()),
                repo_url=f"https://github.com/example/repo-{i + 1}",
                name=f"repo-{i + 1}",
                description=f"Repository for {query}",
                stars=1000 - (i * 200),
                forks=100 - (i * 20),
                language="Python",
                topics=["machine-learning", "ai", query.lower()],
                last_updated="2024-05-01",
                license="MIT",
                relevance_score=0.85 - (i * 0.1),
            )
            repos.append(repo)

        return repos

    async def evaluate_projects(
        self, projects: list[dict[str, Any]]
    ) -> list[ProjectEvaluation]:
        """Evaluate open source projects.

        Args:
            projects: List of projects to evaluate

        Returns:
            List of ProjectEvaluation objects
        """
        evaluations = []

        for project in projects:
            # Analyze project quality
            quality = ProjectQuality.GOOD
            score = 75

            evaluation = ProjectEvaluation.create(
                id=str(uuid.uuid4()),
                project_name=project.get("name", "Unknown"),
                project_url=project.get("url", ""),
                quality=quality,
                strengths=[
                    "Active development",
                    "Good documentation",
                    "Strong community",
                ],
                weaknesses=[
                    "Limited test coverage",
                    "Some outdated dependencies",
                ],
                use_cases=[
                    "Production applications",
                    "Research projects",
                    "Educational purposes",
                ],
                recommendation="Recommended for production use with proper testing",
                score=score,
            )
            evaluations.append(evaluation)

        return evaluations

    async def synthesize_findings(self, data: dict[str, Any]) -> ResearchReport:
        """Synthesize research findings into a report.

        Args:
            data: Research data containing papers, repos, evaluations

        Returns:
            ResearchReport object
        """
        query = data.get("query", "research topic")

        # Reconstruct papers
        papers_data = data.get("papers", [])
        papers = [
            Paper(
                id=p["id"],
                title=p["title"],
                authors=tuple(p["authors"]),
                abstract=p["abstract"],
                url=p["url"],
                source=PaperSource(p["source"]),
                published_date=p["published_date"],
                citations=p["citations"],
                relevance_score=p["relevance_score"],
                created_at=p["created_at"],
            )
            for p in papers_data
        ]

        # Reconstruct repos
        repos_data = data.get("repositories", [])
        repos = [
            RepoAnalysis(
                id=r["id"],
                repo_url=r["repo_url"],
                name=r["name"],
                description=r["description"],
                stars=r["stars"],
                forks=r["forks"],
                language=r["language"],
                topics=tuple(r["topics"]),
                last_updated=r["last_updated"],
                license=r["license"],
                relevance_score=r["relevance_score"],
                created_at=r["created_at"],
            )
            for r in repos_data
        ]

        # Reconstruct evaluations
        evals_data = data.get("evaluations", [])
        evaluations = [
            ProjectEvaluation(
                id=e["id"],
                project_name=e["project_name"],
                project_url=e["project_url"],
                quality=ProjectQuality(e["quality"]),
                strengths=tuple(e["strengths"]),
                weaknesses=tuple(e["weaknesses"]),
                use_cases=tuple(e["use_cases"]),
                recommendation=e["recommendation"],
                score=e["score"],
                created_at=e["created_at"],
            )
            for e in evals_data
        ]

        # Generate report
        report = ResearchReport.create(
            id=str(uuid.uuid4()),
            title=f"Research Report: {query}",
            query=query,
            papers=papers,
            repos=repos,
            evaluations=evaluations,
            summary=f"Comprehensive research on {query} reveals significant progress in the field",
            key_findings=[
                f"Found {len(papers)} relevant academic papers",
                f"Identified {len(repos)} active open source projects",
                f"Evaluated {len(evaluations)} projects for production readiness",
            ],
            recommendations=[
                "Consider adopting proven open source solutions",
                "Stay updated with latest research developments",
                "Contribute back to open source community",
            ],
        )

        return report


__all__ = ["ResearchAgent"]
