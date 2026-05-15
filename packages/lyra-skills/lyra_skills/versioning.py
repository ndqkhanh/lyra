"""
Skill Versioning and Git Lineage

Tracks skill evolution through git commits, enabling:
- Version history
- Rollback to previous versions
- Diff between versions
- Lineage tracking

Based on research: Best practices for skill management
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import subprocess
import json
import hashlib


@dataclass
class SkillVersion:
    """Single version of a skill."""
    version: str
    commit_hash: str
    timestamp: datetime
    author: str
    message: str
    file_path: Path


class SkillVersionManager:
    """
    Manages skill versions using git.

    Provides:
    - Automatic versioning on skill changes
    - Version history
    - Rollback capability
    - Diff between versions
    """

    def __init__(self, skills_dir: Path):
        """
        Initialize skill version manager.

        Args:
            skills_dir: Directory containing skills (must be in git repo)
        """
        self.skills_dir = Path(skills_dir)
        self._ensure_git_repo()

    def _ensure_git_repo(self) -> None:
        """Ensure skills directory is in a git repository."""
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.skills_dir,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            # Initialize git repo
            subprocess.run(
                ["git", "init"],
                cwd=self.skills_dir,
                check=True
            )
            print(f"Initialized git repository in {self.skills_dir}")

    def commit_skill(
        self,
        skill_file: Path,
        message: str,
        author: str = "Lyra Skills System"
    ) -> str:
        """
        Commit a skill file to git.

        Args:
            skill_file: Path to skill file
            message: Commit message
            author: Author name

        Returns:
            Commit hash
        """
        # Stage file
        subprocess.run(
            ["git", "add", str(skill_file)],
            cwd=self.skills_dir,
            check=True
        )

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message, f"--author={author} <noreply@lyra.ai>"],
            cwd=self.skills_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # No changes to commit
            return self._get_latest_commit_hash(skill_file)

        # Get commit hash
        return self._get_latest_commit_hash(skill_file)

    def _get_latest_commit_hash(self, skill_file: Path) -> str:
        """Get latest commit hash for a file."""
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", str(skill_file)],
            cwd=self.skills_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    def get_version_history(self, skill_file: Path) -> List[SkillVersion]:
        """
        Get version history for a skill.

        Args:
            skill_file: Path to skill file

        Returns:
            List of SkillVersion objects, newest first
        """
        result = subprocess.run(
            ["git", "log", "--format=%H|%at|%an|%s", str(skill_file)],
            cwd=self.skills_dir,
            capture_output=True,
            text=True,
            check=True
        )

        versions = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            commit_hash, timestamp, author, message = line.split('|', 3)

            # Extract version from commit message or generate
            version = self._extract_version_from_message(message)

            versions.append(SkillVersion(
                version=version,
                commit_hash=commit_hash,
                timestamp=datetime.fromtimestamp(int(timestamp)),
                author=author,
                message=message,
                file_path=skill_file
            ))

        return versions

    def _extract_version_from_message(self, message: str) -> str:
        """Extract version from commit message."""
        # Look for version pattern like "v1.2.3" or "version 1.2.3"
        import re
        match = re.search(r'v?(\d+\.\d+\.\d+)', message)
        if match:
            return match.group(1)

        # Generate version from timestamp
        return f"auto-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def get_skill_at_version(
        self,
        skill_file: Path,
        commit_hash: str
    ) -> str:
        """
        Get skill content at a specific version.

        Args:
            skill_file: Path to skill file
            commit_hash: Commit hash

        Returns:
            Skill file content at that version
        """
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{skill_file}"],
            cwd=self.skills_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def diff_versions(
        self,
        skill_file: Path,
        version1: str,
        version2: str
    ) -> str:
        """
        Get diff between two versions.

        Args:
            skill_file: Path to skill file
            version1: First commit hash
            version2: Second commit hash

        Returns:
            Diff output
        """
        result = subprocess.run(
            ["git", "diff", version1, version2, "--", str(skill_file)],
            cwd=self.skills_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def rollback_to_version(
        self,
        skill_file: Path,
        commit_hash: str
    ) -> None:
        """
        Rollback skill to a previous version.

        Args:
            skill_file: Path to skill file
            commit_hash: Commit hash to rollback to
        """
        # Get content at that version
        content = self.get_skill_at_version(skill_file, commit_hash)

        # Write to file
        with open(self.skills_dir / skill_file, 'w') as f:
            f.write(content)

        # Commit rollback
        self.commit_skill(
            skill_file,
            f"Rollback to version {commit_hash[:8]}",
            author="Lyra Skills System"
        )

    def get_lineage(self, skill_file: Path) -> Dict[str, Any]:
        """
        Get complete lineage of a skill.

        Args:
            skill_file: Path to skill file

        Returns:
            Lineage information
        """
        versions = self.get_version_history(skill_file)

        return {
            'skill_file': str(skill_file),
            'total_versions': len(versions),
            'current_version': versions[0] if versions else None,
            'created_at': versions[-1].timestamp if versions else None,
            'last_modified': versions[0].timestamp if versions else None,
            'versions': [
                {
                    'version': v.version,
                    'commit_hash': v.commit_hash[:8],
                    'timestamp': v.timestamp.isoformat(),
                    'author': v.author,
                    'message': v.message
                }
                for v in versions
            ]
        }

    def tag_version(
        self,
        skill_file: Path,
        tag: str,
        message: str = ""
    ) -> None:
        """
        Tag a specific version.

        Args:
            skill_file: Path to skill file
            tag: Tag name (e.g., "v1.0.0", "stable")
            message: Tag message
        """
        commit_hash = self._get_latest_commit_hash(skill_file)

        subprocess.run(
            ["git", "tag", "-a", tag, commit_hash, "-m", message or tag],
            cwd=self.skills_dir,
            check=True
        )

    def list_tags(self, skill_file: Path) -> List[str]:
        """List all tags for a skill."""
        result = subprocess.run(
            ["git", "tag", "--contains", self._get_latest_commit_hash(skill_file)],
            cwd=self.skills_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return [tag for tag in result.stdout.strip().split('\n') if tag]


# Integration with skill generation
def create_versioned_skill(
    skills_dir: Path,
    skill_content: str,
    skill_name: str,
    version: str = "1.0.0",
    commit_message: Optional[str] = None
) -> Path:
    """
    Create a new skill with automatic versioning.

    Args:
        skills_dir: Skills directory
        skill_content: Skill file content
        skill_name: Skill name
        version: Version number
        commit_message: Optional commit message

    Returns:
        Path to created skill file
    """
    # Create skill file
    skill_id = f"{skill_name.lower().replace(' ', '-')}_{hashlib.md5(skill_name.encode()).hexdigest()[:8]}"
    skill_file = skills_dir / f"{skill_id}.md"

    with open(skill_file, 'w') as f:
        f.write(skill_content)

    # Version it
    version_manager = SkillVersionManager(skills_dir)
    version_manager.commit_skill(
        skill_file,
        commit_message or f"Create {skill_name} v{version}",
        author="Lyra Skills System"
    )

    # Tag version
    version_manager.tag_version(skill_file, f"v{version}", f"Release {version}")

    return skill_file


# Usage example
"""
from lyra_skills.versioning import SkillVersionManager, create_versioned_skill
from pathlib import Path

# Initialize version manager
skills_dir = Path("~/.lyra/skills").expanduser()
version_manager = SkillVersionManager(skills_dir)

# Create versioned skill
skill_file = create_versioned_skill(
    skills_dir,
    skill_content="# My Skill\\n...",
    skill_name="My Skill",
    version="1.0.0"
)

# Get version history
history = version_manager.get_version_history(skill_file)
print(f"Skill has {len(history)} versions")

# Get lineage
lineage = version_manager.get_lineage(skill_file)
print(f"Created: {lineage['created_at']}")
print(f"Last modified: {lineage['last_modified']}")

# Diff between versions
if len(history) >= 2:
    diff = version_manager.diff_versions(
        skill_file,
        history[1].commit_hash,
        history[0].commit_hash
    )
    print(f"Changes:\\n{diff}")

# Rollback to previous version
if len(history) >= 2:
    version_manager.rollback_to_version(skill_file, history[1].commit_hash)
"""
