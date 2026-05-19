"""
Obsidian Wiki Integration - Karpathy-style knowledge base.

Exports memory as Markdown files with:
- Bidirectional links between findings
- Graph view of attack paths and vulnerabilities
- Hierarchical organization
- Auto-generated index
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import re


@dataclass
class WikiPage:
    """A page in the Obsidian wiki."""

    title: str
    content: str
    tags: List[str]
    links: List[str]  # Links to other pages
    backlinks: List[str]  # Pages that link to this one
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, str]


class ObsidianWiki:
    """
    Obsidian-compatible wiki for Lyra memory.

    Features:
    - Markdown export with frontmatter
    - Bidirectional links [[page-name]]
    - Tags #tag
    - Graph view support
    - Daily notes
    """

    def __init__(self, vault_path: Path):
        """
        Initialize Obsidian wiki.

        Args:
            vault_path: Path to Obsidian vault directory
        """
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)

        # Create standard directories
        (self.vault_path / "daily").mkdir(exist_ok=True)
        (self.vault_path / "findings").mkdir(exist_ok=True)
        (self.vault_path / "targets").mkdir(exist_ok=True)
        (self.vault_path / "exploits").mkdir(exist_ok=True)
        (self.vault_path / "reports").mkdir(exist_ok=True)

        self.pages: Dict[str, WikiPage] = {}
        self._load_existing_pages()

    def _load_existing_pages(self):
        """Load existing pages from vault."""
        for md_file in self.vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                title = md_file.stem
                self.pages[title] = self._parse_page(title, content)
            except Exception as e:
                print(f"Error loading {md_file}: {e}")

    def _parse_page(self, title: str, content: str) -> WikiPage:
        """Parse a markdown page."""
        # Extract frontmatter
        metadata = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                content = parts[2].strip()
                for line in frontmatter.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()

        # Extract links [[page-name]]
        links = re.findall(r"\[\[([^\]]+)\]\]", content)

        # Extract tags #tag
        tags = re.findall(r"#(\w+)", content)

        return WikiPage(
            title=title,
            content=content,
            tags=tags,
            links=links,
            backlinks=[],
            created_at=datetime.fromisoformat(metadata.get("created", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(metadata.get("updated", datetime.now().isoformat())),
            metadata=metadata,
        )

    def create_page(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        category: str = "findings",
        metadata: Optional[Dict[str, str]] = None,
    ) -> WikiPage:
        """
        Create a new wiki page.

        Args:
            title: Page title
            content: Page content (markdown)
            tags: List of tags
            category: Category (findings, targets, exploits, reports)
            metadata: Additional metadata

        Returns:
            Created WikiPage
        """
        # Sanitize title for filename
        filename = self._sanitize_filename(title)

        # Extract links from content
        links = re.findall(r"\[\[([^\]]+)\]\]", content)

        # Create page object
        page = WikiPage(
            title=title,
            content=content,
            tags=tags or [],
            links=links,
            backlinks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {},
        )

        # Generate markdown with frontmatter
        md_content = self._generate_markdown(page)

        # Write to file
        category_path = self.vault_path / category
        category_path.mkdir(exist_ok=True)
        file_path = category_path / f"{filename}.md"
        file_path.write_text(md_content, encoding="utf-8")

        # Update index
        self.pages[title] = page
        self._update_backlinks(page)

        return page

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename."""
        # Replace spaces with hyphens, remove special chars
        filename = re.sub(r"[^\w\s-]", "", title.lower())
        filename = re.sub(r"[-\s]+", "-", filename)
        return filename.strip("-")

    def _generate_markdown(self, page: WikiPage) -> str:
        """Generate markdown with frontmatter."""
        frontmatter = [
            "---",
            f"title: {page.title}",
            f"created: {page.created_at.isoformat()}",
            f"updated: {page.updated_at.isoformat()}",
        ]

        if page.tags:
            frontmatter.append(f"tags: [{', '.join(page.tags)}]")

        for key, value in page.metadata.items():
            frontmatter.append(f"{key}: {value}")

        frontmatter.append("---")
        frontmatter.append("")

        return "\n".join(frontmatter) + page.content

    def _update_backlinks(self, page: WikiPage):
        """Update backlinks for linked pages."""
        for link in page.links:
            if link in self.pages:
                if page.title not in self.pages[link].backlinks:
                    self.pages[link].backlinks.append(page.title)

    def link_pages(self, from_title: str, to_title: str):
        """Create a link between two pages."""
        if from_title not in self.pages or to_title not in self.pages:
            return

        from_page = self.pages[from_title]
        if to_title not in from_page.links:
            from_page.links.append(to_title)

        to_page = self.pages[to_title]
        if from_title not in to_page.backlinks:
            to_page.backlinks.append(from_title)

    def create_attack_graph(
        self,
        target: str,
        vulnerabilities: List[Dict],
        exploits: List[Dict],
    ) -> str:
        """
        Create an attack graph visualization.

        Args:
            target: Target identifier
            vulnerabilities: List of vulnerabilities
            exploits: List of exploits

        Returns:
            Page title
        """
        title = f"Attack Graph - {target}"
        content = [f"# Attack Graph: {target}\n"]

        # Target info
        content.append(f"**Target**: [[{target}]]\n")
        content.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        # Vulnerabilities section
        content.append("\n## Vulnerabilities\n")
        for vuln in vulnerabilities:
            vuln_title = vuln.get("id", "Unknown")
            content.append(f"- [[{vuln_title}]] - {vuln.get('severity', 'UNKNOWN')}")
            if vuln.get("exploitable"):
                content.append(" ⚠️ **Exploitable**")
            content.append("\n")

        # Exploits section
        content.append("\n## Exploits\n")
        for exploit in exploits:
            exploit_title = exploit.get("name", "Unknown")
            content.append(f"- [[{exploit_title}]]")
            if exploit.get("success"):
                content.append(" ✅ **Successful**")
            content.append("\n")

        # Mermaid graph
        content.append("\n## Attack Path\n")
        content.append("```mermaid\n")
        content.append("graph TD\n")
        content.append(f"    A[{target}]\n")

        for i, vuln in enumerate(vulnerabilities):
            vuln_id = f"V{i}"
            content.append(f"    {vuln_id}[{vuln.get('id', 'Unknown')}]\n")
            content.append(f"    A --> {vuln_id}\n")

            # Link exploits
            for j, exploit in enumerate(exploits):
                if exploit.get("vuln_id") == vuln.get("id"):
                    exploit_id = f"E{j}"
                    content.append(f"    {exploit_id}[{exploit.get('name', 'Unknown')}]\n")
                    content.append(f"    {vuln_id} --> {exploit_id}\n")

        content.append("```\n")

        # Create page
        self.create_page(
            title=title,
            content="".join(content),
            tags=["attack-graph", "visualization", target],
            category="reports",
            metadata={"target": target, "type": "attack-graph"},
        )

        return title

    def create_daily_note(self, findings: List[str]) -> str:
        """
        Create a daily note with findings.

        Args:
            findings: List of finding titles

        Returns:
            Page title
        """
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"Daily Note - {today}"

        content = [f"# {today}\n"]
        content.append("\n## Findings\n")

        for finding in findings:
            content.append(f"- [[{finding}]]\n")

        content.append("\n## Summary\n")
        content.append(f"Total findings: {len(findings)}\n")

        self.create_page(
            title=title,
            content="".join(content),
            tags=["daily-note"],
            category="daily",
            metadata={"date": today},
        )

        return title

    def generate_index(self) -> str:
        """Generate an index page of all content."""
        content = ["# Lyra Memory Index\n"]
        content.append(f"\n**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        content.append(f"\n**Total Pages**: {len(self.pages)}\n")

        # Group by category
        categories = {}
        for page in self.pages.values():
            # Determine category from metadata or tags
            category = page.metadata.get("category", "Other")
            if category not in categories:
                categories[category] = []
            categories[category].append(page)

        # Write categories
        for category, pages in sorted(categories.items()):
            content.append(f"\n## {category}\n")
            for page in sorted(pages, key=lambda p: p.title):
                content.append(f"- [[{page.title}]]")
                if page.tags:
                    content.append(f" #{' #'.join(page.tags)}")
                content.append("\n")

        # Write to index
        index_path = self.vault_path / "INDEX.md"
        index_path.write_text("".join(content), encoding="utf-8")

        return "INDEX"

    def search(self, query: str, tags: Optional[List[str]] = None) -> List[WikiPage]:
        """
        Search wiki pages.

        Args:
            query: Search query
            tags: Filter by tags

        Returns:
            List of matching pages
        """
        results = []
        query_lower = query.lower()

        for page in self.pages.values():
            # Check tags filter
            if tags and not any(tag in page.tags for tag in tags):
                continue

            # Check content match
            if query_lower in page.title.lower() or query_lower in page.content.lower():
                results.append(page)

        return results
