"""Instinct extractor - Extracts patterns from observations"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class Instinct:
    """An extracted instinct/pattern"""

    id: str
    trigger: str
    action: str
    confidence: float  # 0.0 to 1.0
    domain: str  # code-style, testing, git, debugging, workflow
    evidence: list[str]
    scope: str  # "project" or "global"
    project_id: str | None
    created_at: datetime


class InstinctExtractor:
    """Extracts instincts from observations"""

    def __init__(self, instincts_dir: Path | None = None):
        self.instincts_dir = instincts_dir or Path.home() / ".lyra" / "learning" / "instincts"
        self.instincts_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_observations(self, observations: list[dict]) -> list[Instinct]:
        """Extract instincts from observations (simplified)"""
        instincts = []

        # Pattern 1: User corrections
        for i, obs in enumerate(observations):
            if obs.get("user_prompt") and "no" in obs["user_prompt"].lower():
                # User corrected something
                if i > 0:
                    prev_obs = observations[i - 1]
                    instinct = Instinct(
                        id=f"correction-{obs['timestamp']}",
                        trigger=f"when {prev_obs.get('tool_name', 'unknown')}",
                        action="avoid previous approach",
                        confidence=0.7,
                        domain="workflow",
                        evidence=[obs["user_prompt"]],
                        scope="project" if obs.get("project_id") else "global",
                        project_id=obs.get("project_id"),
                        created_at=datetime.fromisoformat(obs["timestamp"]),
                    )
                    instincts.append(instinct)

        # Pattern 2: Repeated workflows
        tool_sequences = {}
        for obs in observations:
            tool = obs.get("tool_name")
            if tool:
                if tool not in tool_sequences:
                    tool_sequences[tool] = 0
                tool_sequences[tool] += 1

        for tool, count in tool_sequences.items():
            if count >= 3:  # Repeated 3+ times
                instinct = Instinct(
                    id=f"repeated-{tool}",
                    trigger="when working on similar tasks",
                    action=f"use {tool}",
                    confidence=min(0.9, 0.5 + (count * 0.1)),
                    domain="workflow",
                    evidence=[f"Used {count} times"],
                    scope="project",
                    project_id=observations[0].get("project_id") if observations else None,
                    created_at=datetime.now(),
                )
                instincts.append(instinct)

        return instincts

    def save_instinct(self, instinct: Instinct):
        """Save instinct to file"""
        if instinct.scope == "project" and instinct.project_id:
            instinct_dir = self.instincts_dir / instinct.project_id
        else:
            instinct_dir = self.instincts_dir / "global"

        instinct_dir.mkdir(parents=True, exist_ok=True)

        # Save as YAML with frontmatter
        instinct_file = instinct_dir / f"{instinct.id}.md"

        frontmatter = {
            "id": instinct.id,
            "trigger": instinct.trigger,
            "confidence": instinct.confidence,
            "domain": instinct.domain,
            "scope": instinct.scope,
            "project_id": instinct.project_id,
        }

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# {instinct.trigger.title()}

## Action
{instinct.action}

## Evidence
{chr(10).join(f"- {e}" for e in instinct.evidence)}

## Created
{instinct.created_at.isoformat()}
"""

        instinct_file.write_text(content)

    def load_instincts(self, project_id: str | None = None) -> list[Instinct]:
        """Load instincts from files"""
        if project_id:
            instinct_dir = self.instincts_dir / project_id
        else:
            instinct_dir = self.instincts_dir / "global"

        if not instinct_dir.exists():
            return []

        instincts = []
        for instinct_file in instinct_dir.glob("*.md"):
            try:
                content = instinct_file.read_text()
                # Parse YAML frontmatter
                import re

                match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
                if match:
                    frontmatter_text, body = match.groups()
                    frontmatter = yaml.safe_load(frontmatter_text)

                    instinct = Instinct(
                        id=frontmatter["id"],
                        trigger=frontmatter["trigger"],
                        action=(
                            body.split("## Action")[1].split("##")[0].strip()
                            if "## Action" in body
                            else ""
                        ),
                        confidence=frontmatter["confidence"],
                        domain=frontmatter["domain"],
                        evidence=[],
                        scope=frontmatter["scope"],
                        project_id=frontmatter.get("project_id"),
                        created_at=datetime.now(),
                    )
                    instincts.append(instinct)
            except Exception as e:
                print(f"Warning: Failed to load instinct {instinct_file}: {e}")

        return instincts


# Global instinct extractor
_instinct_extractor: InstinctExtractor | None = None


def get_instinct_extractor() -> InstinctExtractor:
    """Get or create global instinct extractor"""
    global _instinct_extractor
    if _instinct_extractor is None:
        _instinct_extractor = InstinctExtractor()
    return _instinct_extractor
