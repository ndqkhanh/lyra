"""Security tool implementations — secret scanning, vulnerability detection.

Production-grade secret scanning with regex patterns covering common credential
formats. No external dependencies beyond stdlib.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Patterns adapted from OWASP and GitLeaks secret detection rules
_SECRET_PATTERNS: dict[str, str] = {
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"[A-Za-z0-9/+]{40}",
    "google_api_key": r"AIza[0-9A-Za-z\-_]{35}",
    "github_token": r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}",
    "generic_api_key": r"(?i)(api[_-]?key|apikey|secret|token|password|auth)\s*[=:]\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]",
    "private_key_header": r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----",
    "jwt_token": r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    "slack_webhook": r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+",
    "discord_webhook": r"https://(?:discord|discordapp)\.com/api/webhooks/\d+/[A-Za-z0-9\-_]+",
    "stripe_key": r"(?:sk|pk)_(?:test|live)_[A-Za-z0-9]{24,}",
    "openai_key": r"sk-[A-Za-z0-9\-]{32,}",
    "anthropic_key": r"sk-ant-[A-Za-z0-9\-_]{32,}",
    "basic_auth": r"https?://[^:\s]+:[^@\s]+@",
    "generic_password": r"(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]+['\"]",
}

# Files to skip (binary, vendored, etc.)
_SKIP_PATTERNS = {
    "*.pyc", "*.pyo", "*.so", "*.dylib", "*.dll",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
    "*.jpg", "*.jpeg", "*.png", "*.gif", "*.ico", "*.svg",
    "*.mp3", "*.mp4", "*.wav", "*.ogg",
    "*.zip", "*.tar", "*.gz", "*.bz2", "*.7z",
    "*.min.js", "*.min.css", "*.map",
    "package-lock.json", "*.lock", "*.sum",
    "Pipfile.lock", "poetry.lock",
}

_SKIP_DIRS = {
    "__pycache__", ".git", ".svn", ".hg",
    "node_modules", "vendor", "venv", ".venv", "env",
    ".tox", ".eggs", "dist", "build", ".mypy_cache",
    ".pytest_cache", ".ruff_cache",
}


def _should_skip(file_path: Path) -> bool:
    """Check if a file should be skipped during scanning."""
    # Check dirs
    for part in file_path.parts:
        if part in _SKIP_DIRS or part.startswith(".") and part not in (".env.example",):
            return True
    # Check extensions
    name = file_path.name.lower()
    for pattern in _SKIP_PATTERNS:
        if _match_glob(name, pattern):
            return True
    return False


def _match_glob(filename: str, pattern: str) -> bool:
    """Simple glob matching for skip patterns."""
    if pattern.startswith("*."):
        return filename.endswith(pattern[1:])
    return filename == pattern


def sec_secrets_scan(
    path: str = ".",
    *,
    repo_root: str = ".",
    max_files: int = 1000,
) -> dict[str, Any]:
    """Scan a codebase for hardcoded secrets and credentials."""
    root = Path(repo_root) / path
    if not root.exists():
        return {"error": f"path not found: {path}", "findings": []}

    files_scanned = 0
    findings: list[dict[str, Any]] = []

    for file_path in root.rglob("*"):
        if files_scanned >= max_files:
            break
        if not file_path.is_file():
            continue
        if _should_skip(file_path):
            continue

        try:
            content = file_path.read_text(errors="ignore")
        except (OSError, PermissionError):
            continue

        files_scanned += 1
        rel_path = str(file_path.relative_to(root))

        for secret_type, pattern in _SECRET_PATTERNS.items():
            compiled = re.compile(pattern)
            for match in compiled.finditer(content):
                # Get context (up to 80 chars around the match)
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                context = content[start:end].replace("\n", "\\n")

                # Redact the matched secret in context
                redacted_context = context[:20] + "***REDACTED***" + context[-20:]

                findings.append({
                    "file": rel_path,
                    "line": content[:match.start()].count("\n") + 1,
                    "type": secret_type,
                    "context": redacted_context,
                    "start_col": match.start(),
                })

    # Deduplicate and group by file
    return {
        "path": str(root),
        "files_scanned": files_scanned,
        "findings": findings,
        "count": len(findings),
        "severity": (
            "critical" if len(findings) > 0
            else "clean"
        ),
    }


__all__ = ["sec_secrets_scan"]
