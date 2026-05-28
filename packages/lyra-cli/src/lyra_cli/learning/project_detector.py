"""Project detector - Detects project context"""

import hashlib
import subprocess
from pathlib import Path


class ProjectDetector:
    """Detects project ID from git repository"""

    @staticmethod
    def detect_project_id(cwd: Path | None = None) -> str | None:
        """Detect project ID from git remote or path"""
        if cwd is None:
            cwd = Path.cwd()

        # Try git remote
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                # Hash the remote URL for portable project ID
                return hashlib.sha256(remote_url.encode()).hexdigest()[:16]
        except Exception:
            pass

        # Try git root path
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                git_root = result.stdout.strip()
                # Hash the git root path
                return hashlib.sha256(git_root.encode()).hexdigest()[:16]
        except Exception:
            pass

        # No git repository
        return None

    @staticmethod
    def get_project_name(cwd: Path | None = None) -> str | None:
        """Get human-readable project name"""
        if cwd is None:
            cwd = Path.cwd()

        # Try git remote
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                # Extract repo name from URL
                if "/" in remote_url:
                    return remote_url.split("/")[-1].replace(".git", "")
        except Exception:
            pass

        # Fallback to directory name
        return cwd.name


class EvolutionPipeline:
    """Evolves instincts into skills/commands/agents"""

    def __init__(self):
        self.evolved_dir = Path.home() / ".lyra" / "learning" / "evolved"
        self.evolved_dir.mkdir(parents=True, exist_ok=True)

    def evolve_to_skill(self, instinct, skill_name: str) -> Path:
        """Evolve instinct into a skill"""

        skill_file = self.evolved_dir / "skills" / f"{skill_name}.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)

        # Create skill from instinct
        content = f"""---
name: {skill_name}
description: {instinct.action}
triggers: ["{instinct.trigger}"]
tags: ["{instinct.domain}"]
model: sonnet
confidence: {instinct.confidence}
---

# {skill_name.replace('-', ' ').title()}

{instinct.action}

## When to Use

{instinct.trigger}

## Evidence

{chr(10).join(f"- {e}" for e in instinct.evidence)}

## Confidence

{instinct.confidence:.1%} confidence based on {len(instinct.evidence)} observation(s)
"""

        skill_file.write_text(content)
        return skill_file

    def evolve_to_command(self, instinct, command_name: str) -> Path:
        """Evolve instinct into a command"""
        command_file = self.evolved_dir / "commands" / f"{command_name}.py"
        command_file.parent.mkdir(parents=True, exist_ok=True)

        # Create command from instinct
        content = f'''"""
{command_name.replace('-', ' ').title()} command

Evolved from instinct: {instinct.id}
Confidence: {instinct.confidence:.1%}
"""

def execute():
    """Execute {command_name} command"""
    print("Executing {command_name}...")
    # TODO: Implement command logic
    # Action: {instinct.action}
    pass
'''

        command_file.write_text(content)
        return command_file

    def cluster_instincts(self, instincts: list) -> dict:
        """Cluster similar instincts"""
        clusters = {}

        for instinct in instincts:
            domain = instinct.domain
            if domain not in clusters:
                clusters[domain] = []
            clusters[domain].append(instinct)

        return clusters

    def promote_to_global(self, instinct) -> bool:
        """Promote project instinct to global"""
        if instinct.scope != "project":
            return False

        # Move instinct file from project to global
        from lyra_cli.learning.instinct_extractor import get_instinct_extractor
        extractor = get_instinct_extractor()

        # Update scope
        instinct.scope = "global"
        instinct.project_id = None

        # Save to global
        extractor.save_instinct(instinct)

        return True


# Global evolution pipeline
_evolution_pipeline: EvolutionPipeline | None = None


def get_evolution_pipeline() -> EvolutionPipeline:
    """Get or create global evolution pipeline"""
    global _evolution_pipeline
    if _evolution_pipeline is None:
        _evolution_pipeline = EvolutionPipeline()
    return _evolution_pipeline
