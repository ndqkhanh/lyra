"""
SkillNet — auto-creation of skills from code repositories, PDFs, and
agent trajectories, plus skill graph linking (dependency, similarity,
prerequisite) and validation via the quality rubric.

The SkillNetAutoCreator analyses source material and distills it into a
structured Skill object with appropriate category, triggers, tags, and
dependencies.
"""

from __future__ import annotations

import hashlib
import os
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections import Counter

from .skill import Skill, SkillCategory

# ---------------------------------------------------------------------------
# Skill graph link types
# ---------------------------------------------------------------------------


class LinkType(str):
    """Named link type for skill graph edges."""


DEPENDENCY = LinkType("dependency")
"""skill_a depends on skill_b (skill_b must be loaded first)."""

SIMILARITY = LinkType("similarity")
"""skill_a and skill_b are similar in purpose or content."""

PREREQUISITE = LinkType("prerequisite")
"""skill_a requires conceptual knowledge of skill_b."""

CONFLICT = LinkType("conflict")
"""skill_a and skill_b conflict (should not be used together)."""


# ---------------------------------------------------------------------------
# Graph link record
# ---------------------------------------------------------------------------


@dataclass
class SkillGraphLink:
    """A directed edge in the skill graph.

    Attributes:
        source: Name of the source skill.
        target: Name of the target skill.
        link_type: Type of relationship.
        weight: Confidence / strength of the link (0.0 — 1.0).
        metadata: Arbitrary additional data.
    """

    source: str
    target: str
    link_type: str = DEPENDENCY
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "link_type": self.link_type,
            "weight": self.weight,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillGraphLink:
        return cls(
            source=data["source"],
            target=data["target"],
            link_type=data.get("link_type", DEPENDENCY),
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SkillNet:
    """A network of skills connected by typed, weighted links.

    Attributes:
        skills: Mapping of skill name to Skill object.
        links: List of graph edges between skills.
        metadata: Arbitrary metadata about the network itself.
    """

    skills: dict[str, Skill] = field(default_factory=dict)
    links: list[SkillGraphLink] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_skill(self, skill: Skill) -> None:
        """Add a skill to the network."""
        self.skills[skill.name] = skill

    def get_skill(self, name: str) -> Skill | None:
        """Look up a skill by name."""
        return self.skills.get(name)

    def add_link(self, link: SkillGraphLink) -> None:
        """Add a directed edge between two skills."""
        self.links.append(link)

    def links_from(self, skill_name: str) -> list[SkillGraphLink]:
        """Return all links where *skill_name* is the source."""
        return [l for l in self.links if l.source == skill_name]

    def links_to(self, skill_name: str) -> list[SkillGraphLink]:
        """Return all links where *skill_name* is the target."""
        return [l for l in self.links if l.target == skill_name]

    def prune_isolated(self) -> list[Skill]:
        """Remove skills with no links; return the removed skills."""
        linked_names: set[str] = set()
        for link in self.links:
            linked_names.add(link.source)
            linked_names.add(link.target)
        isolated = [s for name, s in self.skills.items() if name not in linked_names]
        for s in isolated:
            del self.skills[s.name]
        return isolated

    def to_dict(self) -> dict[str, Any]:
        return {
            "skills": {n: s.to_dict() for n, s in self.skills.items()},
            "links": [l.to_dict() for l in self.links],
            "metadata": self.metadata,
            "skill_count": len(self.skills),
            "link_count": len(self.links),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillNet:
        net = cls(metadata=data.get("metadata", {}))
        for name, skill_data in data.get("skills", {}).items():
            net.skills[name] = Skill.from_dict(skill_data)
        for link_data in data.get("links", []):
            net.links.append(SkillGraphLink.from_dict(link_data))
        return net

    # ------------------------------------------------------------------
    # Graph traversal
    # ------------------------------------------------------------------

    def neighbors(
        self, skill_name: str, link_type: str | None = None
    ) -> list[SkillGraphLink]:
        """Return all adjacent edges (both incoming and outgoing).

        Args:
            skill_name: Name of the skill.
            link_type: Optional filter by link type.

        Returns:
            List of linked SkillGraphLink edges.
        """
        result = self.links_from(skill_name) + self.links_to(skill_name)
        if link_type:
            result = [l for l in result if l.link_type == link_type]
        return result

    def bfs(self, start: str, max_depth: int = 3) -> dict[str, int]:
        """Breadth-first traversal from *start* skill.

        Args:
            start: Starting skill name.
            max_depth: Maximum traversal depth.

        Returns:
            Dict mapping visited skill name to depth level.
        """
        if start not in self.skills:
            return {}
        visited: dict[str, int] = {start: 0}
        queue: list[tuple[str, int]] = [(start, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for link in self.neighbors(current):
                neighbor = link.target if link.source == current else link.source
                if neighbor not in visited:
                    visited[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))
        return visited

    def find_path(
        self,
        source: str,
        target: str,
        link_type: str | None = None,
    ) -> list[SkillGraphLink]:
        """Find a path between two skills via BFS.

        Args:
            source: Starting skill name.
            target: Target skill name.
            link_type: Restrict to a specific link type.

        Returns:
            List of SkillGraphLink forming the path, or empty list if
            no path exists.
        """
        if source not in self.skills or target not in self.skills:
            return []
        if source == target:
            return []

        from collections import deque

        visited: set[str] = {source}
        parent: dict[str, tuple[str, SkillGraphLink | None]] = {source: (source, None)}
        queue: deque[str] = deque([source])

        while queue:
            current = queue.popleft()
            for link in self.neighbors(current):
                neighbor = link.target if link.source == current else link.source
                if link_type and link.link_type != link_type:
                    continue
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = (current, link)
                    if neighbor == target:
                        # Reconstruct path
                        path: list[SkillGraphLink] = []
                        node = target
                        while node != source:
                            _parent, edge = parent[node]
                            if edge:
                                path.insert(0, edge)
                            node = _parent
                        return path
                    queue.append(neighbor)
        return []

    def find_shortest_path_by_type(
        self,
        source: str,
        target: str,
    ) -> list[SkillGraphLink] | None:
        """Find the shortest path trying dependency links first, then all.

        Args:
            source: Starting skill name.
            target: Target skill name.

        Returns:
            Path if found, else None.
        """
        # First try dependency-only
        dep_path = self.find_path(source, target, link_type=DEPENDENCY)
        if dep_path:
            return dep_path
        # Then try prerequisite-only
        prereq_path = self.find_path(source, target, link_type=PREREQUISITE)
        if prereq_path:
            return prereq_path
        # Finally any link type
        any_path = self.find_path(source, target)
        return any_path if any_path else None


# ---------------------------------------------------------------------------
# GraphTraversal — high-level path finding and navigation
# ---------------------------------------------------------------------------


class GraphTraversal:
    """Skill graph traversal utilities.

    Provides path finding from a current skill set to a target capability
    using the skill graph's typed edges.
    """

    def __init__(self, skill_net: SkillNet):
        self.net = skill_net

    def find_skill_path(
        self,
        current_skills: list[str],
        target_capability: str,
    ) -> list[SkillGraphLink]:
        """Find a learning path from current skills to a target capability.

        Tries each current skill as a starting point and returns the
        shortest valid path.

        Args:
            current_skills: Skills the agent already possesses.
            target_capability: The desired target skill.

        Returns:
            Shortest SkillGraphLink path, or empty list if unreachable.
        """
        if target_capability not in self.net.skills:
            return []

        best_path: list[SkillGraphLink] = []
        for start in current_skills:
            if start not in self.net.skills:
                continue
            path = self.net.find_shortest_path_by_type(start, target_capability)
            if path and (not best_path or len(path) < len(best_path)):
                best_path = path
        return best_path

    def missing_prerequisites(
        self,
        skill_name: str,
        owned: set[str],
    ) -> list[str]:
        """Return prerequisite skills that are not yet owned.

        Args:
            skill_name: The target skill to check.
            owned: Set of skill names already possessed.

        Returns:
            List of missing prerequisite skill names.
        """
        missing: list[str] = []
        for link in self.net.links_from(skill_name):
            if link.link_type in (DEPENDENCY, PREREQUISITE):
                if link.target not in owned:
                    missing.append(link.target)
        return missing

    def downstream_skills(
        self, skill_name: str, max_depth: int = 2
    ) -> list[str]:
        """Return skills that depend on *skill_name* (direct or transitive).

        Args:
            skill_name: The skill to check downstream of.
            max_depth: Maximum traversal depth.

        Returns:
            List of downstream skill names.
        """
        visited = self.net.bfs(skill_name, max_depth=max_depth)
        # Exclude the start node
        return [name for name in visited if name != skill_name]

    def topological_sort(self) -> list[str]:
        """Return skills in dependency order (prerequisites first).

        Uses Kahn's algorithm. Skills with no dependencies come first.

        In the skill graph, a DEPENDENCY edge ``A -> B`` means A depends on
        B.  The topological order therefore places B before A.

        Returns:
            Topologically sorted list of skill names.
        """
        in_degree: dict[str, int] = {
            name: 0 for name in self.net.skills
        }
        # Count prerequisites: each DEPENDENCY/PREREQUISITE edge adds one
        # to the *source* (the skill that depends on something else).
        for link in self.net.links:
            if link.link_type in (DEPENDENCY, PREREQUISITE):
                in_degree[link.source] = in_degree.get(link.source, 0) + 1

        queue: list[str] = [
            name for name, deg in in_degree.items() if deg == 0
        ]
        sorted_order: list[str] = []

        while queue:
            node = queue.pop(0)
            sorted_order.append(node)
            # Find skills that depend on this node (edges where node is the target)
            for link in self.net.links:
                if link.link_type in (DEPENDENCY, PREREQUISITE) and link.target == node:
                    in_degree[link.source] -= 1
                    if in_degree[link.source] == 0:
                        queue.append(link.source)

        # Remaining skills (if any) have circular dependencies
        remaining = [n for n in self.net.skills if n not in sorted_order]
        sorted_order.extend(remaining)
        return sorted_order


# ---------------------------------------------------------------------------
# SkillRecommender — suggest next skills to learn
# ---------------------------------------------------------------------------


class SkillRecommender:
    """Recommend next skills to learn given an agent's current skill set.

    Recommendations are scored on three criteria:
      1. **Prerequisite completeness**: how many missing prerequisites.
      2. **Downstream potential**: how many future skills this unlocks.
      3. **Similarity gap**: how related the skill is to current ones.
    """

    def __init__(self, skill_net: SkillNet):
        self.net = skill_net
        self._traversal = GraphTraversal(skill_net)

    def recommend(
        self,
        current_skills: list[str],
        top_k: int = 5,
        diversity_boost: float = 0.2,
    ) -> list[tuple[str, float, str]]:
        """Recommend next skills to learn.

        Args:
            current_skills: Skill names the agent already possesses.
            top_k: Maximum number of recommendations.
            diversity_boost: Bonus for recommendations from different
                categories than the user's current skill set (0-1).

        Returns:
            List of (skill_name, score, reason) tuples, sorted by
            descending score.
        """
        owned = set(current_skills)
        candidates: list[tuple[str, float, str]] = []

        # Owned categories for diversity
        owned_categories = set()
        for name in owned:
            skill = self.net.skills.get(name)
            if skill:
                owned_categories.add(skill.category.value)

        for name, skill in self.net.skills.items():
            if name in owned:
                continue

            # 1. Prerequisite completeness score
            missing = self._traversal.missing_prerequisites(name, owned)
            prereq_score = 1.0 - (len(missing) / max(len(missing) + 1, 1))
            # Lower score if too many missing prerequisites
            if len(missing) > 3:
                prereq_score *= 0.3

            # 2. Downstream potential
            downstream = self._traversal.downstream_skills(name, max_depth=2)
            downstream_score = min(1.0, len(downstream) / 10.0)

            # 3. Similarity to current skills
            similarity_score = 0.0
            for owned_name in owned:
                for link in self.net.neighbors(owned_name):
                    neighbor = link.target if link.source == owned_name else link.source
                    if neighbor == name:
                        if link.link_type == SIMILARITY:
                            similarity_score = max(similarity_score, link.weight)
                        elif link.link_type == DEPENDENCY:
                            similarity_score = max(similarity_score, link.weight * 0.8)

            # 4. Diversity bonus
            diversity_score = 0.0
            if skill and skill.category.value not in owned_categories:
                diversity_score = diversity_boost

            # Composite score
            score = (
                0.35 * prereq_score
                + 0.25 * downstream_score
                + 0.25 * similarity_score
                + 0.15 * diversity_score
            )

            # Build reason
            reason_parts = []
            if prereq_score > 0.7:
                reason_parts.append("few missing prerequisites")
            elif prereq_score < 0.3:
                reason_parts.append(f"needs {len(missing)} prerequisites")
            if downstream_score > 0.5:
                reason_parts.append("unlocks many downstream skills")
            if similarity_score > 0.5:
                reason_parts.append("similar to current skills")
            if diversity_score > 0:
                reason_parts.append("adds category diversity")
            reason = "; ".join(reason_parts) if reason_parts else "general recommendation"

            candidates.append((name, score, reason))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def recommend_to_fill_gap(
        self,
        current_skills: list[str],
        target_skill: str,
        top_k: int = 3,
    ) -> list[tuple[str, float, str]]:
        """Recommend skills that bridge from current to a target.

        Args:
            current_skills: Currently owned skills.
            target_skill: The target capability to reach.
            top_k: Maximum recommendations.

        Returns:
            List of (skill_name, score, reason).
        """
        path = self._traversal.find_skill_path(current_skills, target_skill)
        if not path:
            return []

        # Extract intermediate skills from the path
        intermediates: list[str] = []
        for link in path:
            if link.source not in current_skills and link.source not in intermediates:
                intermediates.append(link.source)
            if link.target not in current_skills and link.target not in intermediates:
                intermediates.append(link.target)

        if target_skill in intermediates:
            intermediates.remove(target_skill)

        result: list[tuple[str, float, str]] = []
        for i, name in enumerate(intermediates):
            priority = max(0.0, 1.0 - (i * 0.2))
            result.append((
                name,
                priority,
                f"on path to {target_skill} (step {i + 1})",
            ))

        return result[:top_k]


# ---------------------------------------------------------------------------
# Graph Visualization — export to Mermaid / Markdown
# ---------------------------------------------------------------------------


class GraphVisualization:
    """Export a SkillNet to Mermaid flowchart markdown.

    Usage::

        viz = GraphVisualization(skill_net)
        mermaid_code = viz.to_mermaid()
        md = viz.to_markdown_report()
    """

    def __init__(self, skill_net: SkillNet):
        self.net = skill_net

    def to_mermaid(self, show_legend: bool = True) -> str:
        """Export the skill graph as a Mermaid flowchart.

        Args:
            show_legend: If True, include a legend subgraph.

        Returns:
            Mermaid flowchart markdown string.
        """
        lines: list[str] = ["```mermaid", "flowchart LR"]

        # Define node styles per category
        category_styles: dict[str, str] = {
            "coding-standards": "fill:#e1d5e7,stroke:#9673a6",
            "backend-patterns": "fill:#d4e6f1,stroke:#2980b9",
            "frontend-patterns": "fill:#fdebd0,stroke:#e67e22",
            "tdd-testing": "fill:#d5f5e3,stroke:#27ae60",
            "security-review": "fill:#fadbd8,stroke:#c0392b",
            "database": "fill:#ebdef0,stroke:#8e44ad",
            "api-design": "fill:#d6eaf8,stroke:#2471a3",
            "deployment": "fill:#fae5d3,stroke:#ca6f1e",
            "docker": "fill:#d4efdf,stroke:#1e8449",
            "framework-specific": "fill:#f9e79f,stroke:#b7950b",
            "general": "fill:#f0f3f4,stroke:#85929e",
        }

        # Add nodes with styling
        for name, skill in self.net.skills.items():
            safe_id = self._safe_mermaid_id(name)
            style = category_styles.get(
                skill.category.value if skill else "general",
                category_styles["general"],
            )
            label = name.replace('"', "'")
            lines.append(f'    {safe_id}["{label}"]')
            lines.append(f"    style {safe_id} {style}")

        # Add edges
        edge_style: dict[str, str] = {
            DEPENDENCY: "-->|depends on|",
            PREREQUISITE: "-.->|prerequisite|",
            SIMILARITY: "---|similar|",
            CONFLICT: "x--x|conflicts|",
        }

        for link in self.net.links:
            src = self._safe_mermaid_id(link.source)
            tgt = self._safe_mermaid_id(link.target)
            arrow = edge_style.get(link.link_type, "-->")
            lines.append(f"    {src} {arrow} {tgt}")

        # Legend
        if show_legend:
            lines.extend([
                "",
                "    subgraph Legend",
                '        direction LR',
                '        L_dep["Dependency"] -->|depends on| L_dep2[" "]',
                '        L_prereq["Prerequisite"] -.->|prerequisite| L_prereq2[" "]',
                '        L_sim["Similarity"] ---|similar| L_sim2[" "]',
                '        L_conf["Conflict"] x--x|conflicts| L_conf2[" "]',
                "    end",
            ])

        lines.append("```")
        return "\n".join(lines)

    def to_markdown_report(self) -> str:
        """Generate a full skill graph report in Markdown.

        Returns:
            Markdown string with summary, stats, and Mermaid diagram.
        """
        parts: list[str] = [
            "# Skill Graph Report",
            "",
            f"**Total skills:** {len(self.net.skills)}",
            f"**Total links:** {len(self.net.links)}",
            "",
            "## Link Distribution",
            "",
        ]

        # Count by type
        from collections import Counter
        type_counts: Counter[str] = Counter(l.link_type for l in self.net.links)
        for link_type, count in type_counts.most_common():
            parts.append(f"- **{link_type}**: {count}")

        parts.append("")
        parts.append("## Skill Categories")
        parts.append("")

        # Group by category
        cat_counts: Counter[str] = Counter()
        for skill in self.net.skills.values():
            cat_counts[skill.category.value if skill else "general"] += 1
        for cat, count in cat_counts.most_common():
            parts.append(f"- **{cat}**: {count} skills")

        parts.append("")
        parts.append("## Dependency Graph")
        parts.append("")
        parts.append(self.to_mermaid(show_legend=True))
        parts.append("")

        return "\n".join(parts)

    @staticmethod
    def _safe_mermaid_id(name: str) -> str:
        """Convert a skill name to a safe Mermaid node ID."""
        safe = "".join(c if c.isalnum() else "_" for c in name)
        if safe and safe[0].isdigit():
            safe = "n_" + safe
        return safe or "unknown"


# ---------------------------------------------------------------------------
# SkillNetAutoCreator
# ---------------------------------------------------------------------------


class SkillNetAutoCreator:
    """Automatically create skills from various source materials.

    Supports creation from:
    - Code repository (analyses file structure, language, conventions)
    - PDF document (extracts conceptual patterns)
    - Agent trajectory (distills skill from session transcript)
    """

    # Category detection: file extensions → SkillCategory
    EXTENSION_CATEGORY_MAP: dict[str, SkillCategory] = {
        # Coding standards
        ".editorconfig": SkillCategory.CODING_STANDARDS,
        ".prettierrc": SkillCategory.CODING_STANDARDS,
        ".eslintrc*": SkillCategory.CODING_STANDARDS,
        "pyproject.toml": SkillCategory.CODING_STANDARDS,
        # Backend
        "*.py": SkillCategory.BACKEND_PATTERNS,
        "*.js": SkillCategory.BACKEND_PATTERNS,
        "*.ts": SkillCategory.BACKEND_PATTERNS,
        "*.java": SkillCategory.BACKEND_PATTERNS,
        "*.go": SkillCategory.BACKEND_PATTERNS,
        "*.rb": SkillCategory.BACKEND_PATTERNS,
        "*.php": SkillCategory.BACKEND_PATTERNS,
        # Frontend
        "*.jsx": SkillCategory.FRONTEND_PATTERNS,
        "*.tsx": SkillCategory.FRONTEND_PATTERNS,
        "*.vue": SkillCategory.FRONTEND_PATTERNS,
        "*.css": SkillCategory.FRONTEND_PATTERNS,
        "*.scss": SkillCategory.FRONTEND_PATTERNS,
        # Testing
        "*test*": SkillCategory.TDD_TESTING,
        "*spec*": SkillCategory.TDD_TESTING,
        # Security
        "SECURITY*": SkillCategory.SECURITY_REVIEW,
        # Database
        "*.sql": SkillCategory.DATABASE,
        "migrations/": SkillCategory.DATABASE,
        # Deployment
        "Dockerfile*": SkillCategory.DEPLOYMENT,
        "docker-compose*": SkillCategory.DEPLOYMENT,
        ".github/": SkillCategory.DEPLOYMENT,
        # API design
        "*.graphql": SkillCategory.API_DESIGN,
        "openapi*": SkillCategory.API_DESIGN,
        "swagger*": SkillCategory.API_DESIGN,
        "proto/": SkillCategory.API_DESIGN,
    }

    # Language detection: file extensions → language name
    EXTENSION_LANGUAGE_MAP: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "bash",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".vue": "vue",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".md": "markdown",
        ".r": "r",
        ".m": "matlab",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
    }

    # ------------------------------------------------------------------
    # Public creation methods
    # ------------------------------------------------------------------

    def create_from_repo(
        self,
        repo_path: str | Path,
        name: str | None = None,
    ) -> Skill:
        """Scan a code repository and generate a skill representing its
        primary patterns, language, and conventions.

        The method analyses:
        - File extensions and directory structure (language detection)
        - Configuration files (framework detection)
        - README / documentation (topic extraction)
        - Test patterns (testing conventions)

        Args:
            repo_path: Root path of the repository to analyse.
            name: Optional name for the generated skill. If omitted, one
                is generated from the repo directory name.

        Returns:
            A Skill object capturing the repo's patterns.
        """
        root = Path(repo_path).resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")

        repo_name = name or root.name
        description = self._build_repo_description(root)
        category = self._detect_category(root)
        language = self._detect_language(root)
        tags = self._collect_tags(root)
        trigger_patterns = self._generate_triggers(repo_name, description, tags)
        dependencies = self._detect_dependencies(root)
        content = self._build_repo_content(root, repo_name)

        return Skill(
            name=repo_name,
            description=description,
            content=content,
            category=category,
            trigger_patterns=trigger_patterns,
            tags=tags,
            language=language,
            source="lyra",
            metadata={
                "source_type": "repository",
                "source_path": str(root),
                "file_count": self._count_files(root),
            },
        )

    def create_from_pdf(
        self,
        pdf_path: str | Path,
        name: str | None = None,
    ) -> Skill:
        """Extract patterns from a PDF document (research paper, spec, etc.).

        The method reads PDF metadata, attempts to extract text content,
        and distills conceptual patterns into a skill.

        Args:
            pdf_path: Path to the PDF file.
            name: Optional name for the generated skill.

        Returns:
            A Skill object capturing the document's patterns.
        """
        path = Path(pdf_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {path}")

        doc_name = name or path.stem
        description = f"Patterns and knowledge extracted from {doc_name}"
        content_text = self._extract_pdf_text(path)

        return Skill(
            name=doc_name,
            description=description,
            content=content_text,
            category=SkillCategory.GENERAL,
            trigger_patterns=[doc_name.lower(), *doc_name.lower().split("_")],
            tags=self._extract_pdf_tags(doc_name),
            source="lyra",
            metadata={
                "source_type": "pdf",
                "source_path": str(path),
                "file_size_bytes": path.stat().st_size,
            },
        )

    def create_from_trajectory(
        self,
        trajectory: dict[str, Any],
        name: str | None = None,
    ) -> Skill:
        """Distil a skill from an agent session trajectory.

        The trajectory is expected to be a dict with keys such as:
        - ``"session_id"``: unique session identifier.
        - ``"phases"``: list of phase dicts, each with ``"name"``,
          ``"actions"``, and ``"outcome"``.
        - ``"tools_used"``: list of tools invoked.
        - ``"artifacts"``: files or outputs created.
        - ``"summary"``: human-readable session summary.

        Args:
            trajectory: Session trajectory data.
            name: Optional name for the generated skill.

        Returns:
            A Skill object distilled from the trajectory.
        """
        session_id = trajectory.get("session_id", "unknown")
        summary = trajectory.get("summary", "")
        phases = trajectory.get("phases", [])
        tools_used = trajectory.get("tools_used", [])
        artifacts = trajectory.get("artifacts", [])

        skill_name = name or f"trajectory-{session_id[:8]}"
        description = summary[:200] if summary else f"Skill distilled from session {session_id}"

        tags: list[str] = []
        for tool in tools_used:
            if isinstance(tool, str):
                tags.append(tool)
        for phase in phases:
            if isinstance(phase, dict):
                pname = phase.get("name", "")
                if pname:
                    tags.append(pname.lower().replace(" ", "-"))

        # Build content from phases
        content_parts = [f"# {skill_name}\n\n", f"**Summary:** {summary}\n\n"]
        if phases:
            content_parts.append("## Phases\n\n")
            for phase in phases:
                if isinstance(phase, dict):
                    name = phase.get("name", "unnamed")
                    outcome = phase.get("outcome", "unknown")
                    content_parts.append(f"- **{name}**: {outcome}\n")
            content_parts.append("\n")
        if artifacts:
            content_parts.append("## Artifacts\n\n")
            for art in artifacts:
                if isinstance(art, str):
                    content_parts.append(f"- {art}\n")
                elif isinstance(art, dict):
                    content_parts.append(f"- {art.get('path', art.get('name', 'unknown'))}\n")
        content_parts.append("\n*Auto-generated from agent trajectory.*\n")

        return Skill(
            name=skill_name,
            description=description,
            content="".join(content_parts),
            category=SkillCategory.GENERAL,
            trigger_patterns=list(set(tags[:10])),
            tags=tags[:20],
            source="lyra",
            metadata={
                "source_type": "trajectory",
                "session_id": session_id,
                "phase_count": len(phases),
                "tool_count": len(tools_used),
            },
        )

    # ------------------------------------------------------------------
    # Skill graph
    # ------------------------------------------------------------------

    def build_skill_graph(
        self,
        skills: list[Skill],
        similarity_threshold: float = 0.3,
    ) -> SkillNet:
        """Build a network of skills linked by dependency, similarity, and
        prerequisite relationships.

        Args:
            skills: The skills to include in the network.
            similarity_threshold: Minimum Jaccard similarity (0-1) for a
                similarity link to be created.

        Returns:
            A SkillNet with typed, weighted links.
        """
        net = SkillNet()
        for s in skills:
            net.add_skill(s)

        # Dependency links (from skill.dependencies)
        for s in skills:
            for dep_name in s.dependencies:
                if dep_name in net.skills:
                    net.add_link(SkillGraphLink(
                        source=s.name,
                        target=dep_name,
                        link_type=DEPENDENCY,
                        weight=1.0,
                    ))

        # Similarity links (Jaccard on tags + content overlap)
        for i, a in enumerate(skills):
            for b in skills[i + 1:]:
                sim = self._jaccard_similarity(a, b)
                if sim >= similarity_threshold:
                    net.add_link(SkillGraphLink(
                        source=a.name,
                        target=b.name,
                        link_type=SIMILARITY,
                        weight=round(sim, 3),
                        metadata={"jaccard": sim},
                    ))
                    net.add_link(SkillGraphLink(
                        source=b.name,
                        target=a.name,
                        link_type=SIMILARITY,
                        weight=round(sim, 3),
                        metadata={"jaccard": sim},
                    ))

        # Prerequisite links: if a's tags overlap with b's description
        for a in skills:
            for b in skills:
                if a.name == b.name:
                    continue
                prereq_score = self._prerequisite_score(a, b)
                if prereq_score > similarity_threshold:
                    net.add_link(SkillGraphLink(
                        source=a.name,
                        target=b.name,
                        link_type=PREREQUISITE,
                        weight=round(prereq_score, 3),
                    ))

        return net

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_skill(skill: Skill) -> bool:
        """Run the quality rubric against a skill and return True if it
        meets minimum thresholds.

        Checks:
        1. Name and description are non-empty.
        2. Content is at least 50 characters.
        3. At least one trigger pattern is defined.
        4. At least one tag is present.
        5. No obviously dangerous patterns in content.

        Args:
            skill: The skill to validate.

        Returns:
            True if the skill passes all validation checks.
        """
        checks = [
            bool(skill.name and skill.name.strip()),
            bool(skill.description and skill.description.strip()),
            len(skill.content.strip()) >= 50,
            len(skill.trigger_patterns) > 0,
            len(skill.tags) > 0,
        ]

        # Safety: reject known-dangerous patterns
        danger_signals = [
            "exec(", "eval(", "__import__(",
            "subprocess.call(", "subprocess.Popen(",
            "os.system(", "os.popen(",
        ]
        safety_ok = not any(signal in skill.content for signal in danger_signals)
        checks.append(safety_ok)

        return all(checks)

    @staticmethod
    def validate_skill_with_report(skill: Skill) -> dict[str, Any]:
        """Run validation and return a detailed report.

        Returns:
            A dict with ``"passed"`` (bool), ``"checks"`` (list of per-check
            results), and ``"score"`` (fraction of checks passed).
        """
        checks: list[dict[str, Any]] = [
            {"name": "name_nonempty", "passed": bool(skill.name and skill.name.strip())},
            {"name": "description_nonempty", "passed": bool(skill.description and skill.description.strip())},
            {"name": "content_min_length", "passed": len(skill.content.strip()) >= 50},
            {"name": "has_triggers", "passed": len(skill.trigger_patterns) > 0},
            {"name": "has_tags", "passed": len(skill.tags) > 0},
            {"name": "safety_check", "passed": not any(
                s in skill.content for s in [
                    "exec(", "eval(", "__import__(",
                    "subprocess.call(", "subprocess.Popen(",
                    "os.system(", "os.popen(",
                ]
            )},
        ]
        passed = all(c["passed"] for c in checks)
        score = sum(1 for c in checks if c["passed"]) / len(checks)
        return {
            "passed": passed,
            "checks": checks,
            "score": score,
        }

    # ------------------------------------------------------------------
    # Internal: repo analysis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_files(root: Path) -> int:
        """Count source files in a repository."""
        return sum(1 for _ in root.rglob("*") if _.is_file() and not _.name.startswith("."))

    @staticmethod
    def _build_repo_description(root: Path) -> str:
        """Build a description from the repo's README or directory name."""
        # Try README first
        for readme_name in ("README.md", "README.rst", "README.txt", "README"):
            readme = root / readme_name
            if readme.exists():
                try:
                    text = readme.read_text(encoding="utf-8", errors="ignore")[:300]
                    # Use the first non-empty line
                    for line in text.split("\n"):
                        stripped = line.strip().strip("#* \t")
                        if stripped:
                            return stripped[:200]
                except Exception:
                    continue
        # Fallback: directory name
        return f"Repository skill for {root.name}"

    @staticmethod
    def _detect_category(root: Path) -> SkillCategory:
        """Detect the most-likely skill category from file patterns."""
        files = list(root.rglob("*"))
        # Prefer explicit markers
        if root.joinpath("Dockerfile").exists() or list(root.rglob("Dockerfile*")):
            return SkillCategory.DEPLOYMENT
        if root.joinpath(".github").exists():
            return SkillCategory.DEPLOYMENT
        if root.joinpath("SECURITY.md").exists():
            return SkillCategory.SECURITY_REVIEW
        if list(root.rglob("migrations")):
            return SkillCategory.DATABASE
        if list(root.rglob("*.test.*")) or list(root.rglob("*_test.*")) or list(root.rglob("test_*.*")):
            return SkillCategory.TDD_TESTING
        if list(root.rglob("openapi*")) or list(root.rglob("swagger*")):
            return SkillCategory.API_DESIGN
        if list(root.rglob("docker-compose*")):
            return SkillCategory.DEPLOYMENT
        # Fallback based on dominant extension
        extension_counts = Counter(
            f.suffix for f in files if f.suffix
        )
        if not extension_counts:
            return SkillCategory.GENERAL
        top_ext = extension_counts.most_common(1)[0][0]
        _map = {
            ".py": SkillCategory.BACKEND_PATTERNS,
            ".js": SkillCategory.BACKEND_PATTERNS,
            ".ts": SkillCategory.BACKEND_PATTERNS,
            ".jsx": SkillCategory.FRONTEND_PATTERNS,
            ".tsx": SkillCategory.FRONTEND_PATTERNS,
            ".css": SkillCategory.FRONTEND_PATTERNS,
            ".sql": SkillCategory.DATABASE,
            ".java": SkillCategory.BACKEND_PATTERNS,
            ".go": SkillCategory.BACKEND_PATTERNS,
        }
        return _map.get(top_ext, SkillCategory.GENERAL)

    @staticmethod
    def _detect_language(root: Path) -> str | None:
        """Detect the dominant programming language in the repo."""
        extensions = [
            f.suffix for f in root.rglob("*")
            if f.is_file() and f.suffix and not f.name.startswith(".")
        ]
        if not extensions:
            return None
        ext_counts = Counter(extensions)
        top_ext = ext_counts.most_common(1)[0][0]
        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".java": "java", ".go": "go", ".rb": "ruby", ".rs": "rust",
            ".swift": "swift", ".kt": "kotlin", ".php": "php",
            ".scala": "scala", ".c": "c", ".cpp": "cpp",
        }
        return lang_map.get(top_ext)

    @staticmethod
    def _collect_tags(root: Path) -> list[str]:
        """Collect descriptive tags from the repository."""
        tags: list[str] = [root.name]
        # Check for configuration files
        markers = [
            ("python", "setup.py", "Pipfile", "poetry.lock", "requirements.txt"),
            ("javascript", "package.json"),
            ("typescript", "tsconfig.json"),
            ("docker", "Dockerfile", "docker-compose.yml"),
            ("testing", "pytest.ini", "jest.config.*", "jest.config.js"),
            ("documentation", "docs", "mkdocs.yml"),
            ("ci-cd", ".github"),
        ]
        for tag, *markers_list in markers:
            for marker in markers_list:
                resolved = root / marker
                if resolved.exists() or list(root.rglob(marker)):
                    tags.append(tag)
                    break
        return list(set(tags))

    @staticmethod
    def _generate_triggers(
        name: str,
        description: str,
        tags: list[str],
    ) -> list[str]:
        """Generate trigger patterns from name, description, and tags."""
        triggers: set[str] = set()
        # From name (split on common separators)
        for part in re.split(r"[-_/\s]+", name):
            if part and len(part) > 2:
                triggers.add(part.lower())
        # From description (first few significant words)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", description.lower())
        triggers.update(words[:5])
        # From tags
        triggers.update(t.lower() for t in tags if len(t) > 2)
        return list(triggers)[:10]

    @staticmethod
    def _detect_dependencies(root: Path) -> list[str]:
        """Detect skill-level dependencies from the repository."""
        deps: list[str] = []
        # Requirement / package files hint at upstream skills
        if root.joinpath("requirements.txt").exists():
            deps.append("python-package-management")
        if root.joinpath("package.json").exists():
            deps.append("javascript-package-management")
        if root.joinpath("Dockerfile").exists():
            deps.append("docker-basics")
        return deps

    @staticmethod
    def _build_repo_content(root: Path, repo_name: str) -> str:
        """Build the skill markdown content from repo analysis."""
        lines: list[str] = [
            f"# {repo_name}\n",
            f"\nAuto-generated skill from repository at `{root}`.\n",
        ]

        # Basic structure
        try:
            items = list(root.iterdir())
        except PermissionError:
            items = []
        top_level = [str(p.name) for p in items if not p.name.startswith(".")]
        if top_level:
            lines.append("\n## Structure\n")
            lines.append("```\n")
            lines.extend(f"{p}/\n" if root.joinpath(p).is_dir() else f"{p}\n" for p in sorted(top_level)[:20])
            lines.append("```\n")

        # README content snippet
        readme_path = root / "README.md"
        if readme_path.exists():
            try:
                readme_text = readme_path.read_text(encoding="utf-8", errors="ignore")[:800]
                lines.append("\n## README\n\n")
                lines.append(readme_text)
                lines.append("\n")
            except Exception:
                pass

        lines.append("\n---\n*Created by SkillNetAutoCreator.*\n")
        return "".join(lines)

    # ------------------------------------------------------------------
    # Internal: PDF analysis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_pdf_text(path: Path) -> str:
        """Extract text from a PDF file.

        Uses PyMuPDF (fitz) if available, otherwise attempts a basic
        extraction from raw PDF content.
        """
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            lines: list[str] = []
            for page in doc:
                lines.append(page.get_text())
            doc.close()
            text = "\n".join(lines)
            if text.strip():
                return text[:5000]  # Cap at 5k chars
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: basic raw PDF text extraction
        try:
            raw = path.read_bytes()
            text_parts: list[str] = []
            for match in re.finditer(rb"\((.*?)\)", raw):
                decoded = match.group(1).decode("latin-1", errors="ignore")
                if len(decoded) > 3 and all(c.isprintable() or c in "\n\r\t " for c in decoded):
                    text_parts.append(decoded)
            fallback = " ".join(text_parts)[:2000]
            if fallback.strip():
                return f"# Extracted PDF Content\n\n{fallback}"
        except Exception:
            pass

        return "# PDF Content\n\n*Unable to extract text from this PDF.*\n"

    @staticmethod
    def _extract_pdf_tags(doc_name: str) -> list[str]:
        """Extract tags from a document name."""
        parts = re.split(r"[-_\s]+", doc_name)
        return [p.lower() for p in parts if len(p) > 2][:10]

    # ------------------------------------------------------------------
    # Internal: graph similarity helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _jaccard_similarity(a: Skill, b: Skill) -> float:
        """Jaccard similarity between two skills based on tags and
        content word overlap.
        """
        set_a = set(t.lower() for t in a.tags) | set(
            w.lower() for w in re.findall(r"\b[a-z]{4,}\b", a.content.lower())
        )
        set_b = set(t.lower() for t in b.tags) | set(
            w.lower() for w in re.findall(r"\b[a-z]{4,}\b", b.content.lower())
        )
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    @staticmethod
    def _prerequisite_score(a: Skill, b: Skill) -> float:
        """Estimate whether *a* is a prerequisite of *b* based on
        tag-to-description content overlap.
        """
        a_tags = set(t.lower() for t in a.tags)
        b_desc_words = set(
            w.lower() for w in re.findall(r"\b[a-z]{3,}\b", b.description.lower())
        )
        if not a_tags:
            return 0.0
        overlap = a_tags & b_desc_words
        return len(overlap) / len(a_tags)
