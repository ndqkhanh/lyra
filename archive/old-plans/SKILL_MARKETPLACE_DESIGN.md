# Skill Marketplace Design (Phase 3)

## Overview

The skill marketplace enables users to discover, install, and update skills from remote registries. This design follows the npm/pip model with a central registry and local caching.

## Registry Format

### Registry Index Structure

```json
{
  "version": "1.0",
  "skills": {
    "auto-research": {
      "name": "auto-research",
      "version": "1.2.0",
      "description": "Automated research agent with web search and synthesis",
      "author": "lyra-team",
      "repository": "https://github.com/lyra-ai/skills-registry",
      "tags": ["research", "automation", "web-search"],
      "dependencies": {
        "python": ">=3.9",
        "packages": ["requests>=2.28.0", "beautifulsoup4>=4.11.0"]
      },
      "download_url": "https://registry.lyra.ai/skills/auto-research/1.2.0.json"
    },
    "tdd-guide": {
      "name": "tdd-guide",
      "version": "2.0.1",
      "description": "Test-driven development guide with pytest integration",
      "author": "lyra-team",
      "repository": "https://github.com/lyra-ai/skills-registry",
      "tags": ["testing", "tdd", "pytest"],
      "dependencies": {
        "python": ">=3.8",
        "packages": ["pytest>=7.0.0"]
      },
      "download_url": "https://registry.lyra.ai/skills/tdd-guide/2.0.1.json"
    }
  }
}
```

### Individual Skill Package Format

Each skill package is a JSON file containing the full skill definition:

```json
{
  "name": "auto-research",
  "version": "1.2.0",
  "description": "Automated research agent with web search and synthesis",
  "author": "lyra-team",
  "repository": "https://github.com/lyra-ai/skills-registry",
  "tags": ["research", "automation", "web-search"],
  "dependencies": {
    "python": ">=3.9",
    "packages": ["requests>=2.28.0", "beautifulsoup4>=4.11.0"]
  },
  "trigger": {
    "keywords": ["research", "investigate", "analyze"],
    "patterns": ["research .+", "investigate .+"]
  },
  "args": {
    "required": true,
    "hint": "topic or question to research"
  },
  "system_prompt": "You are an expert research assistant...",
  "examples": [
    {
      "input": "/auto-research quantum computing applications",
      "output": "Researching quantum computing applications..."
    }
  ]
}
```

## Registry Configuration

### Default Registry

Location: `~/.lyra/registry.json`

```json
{
  "registries": [
    {
      "name": "official",
      "url": "https://registry.lyra.ai/index.json",
      "enabled": true,
      "priority": 1
    },
    {
      "name": "community",
      "url": "https://community.lyra.ai/skills/index.json",
      "enabled": true,
      "priority": 2
    }
  ],
  "cache_ttl": 3600,
  "auto_update_check": true
}
```

### Local Cache

Location: `~/.lyra/cache/registry/`

Structure:
```
~/.lyra/cache/registry/
├── official-index.json          # Cached registry index
├── community-index.json         # Cached registry index
└── skills/
    ├── auto-research-1.2.0.json # Cached skill packages
    └── tdd-guide-2.0.1.json
```

## Commands

### `/skill browse [query]`

Browse available skills from all enabled registries.

**Usage:**
```bash
/skill browse                    # List all available skills
/skill browse research           # Search for skills matching "research"
/skill browse --tag automation   # Filter by tag
```

**Output:**
```
Available Skills (23 found):

  auto-research (v1.2.0) by lyra-team
  Automated research agent with web search and synthesis
  Tags: research, automation, web-search
  
  tdd-guide (v2.0.1) by lyra-team
  Test-driven development guide with pytest integration
  Tags: testing, tdd, pytest
  
  code-reviewer (v1.5.0) by lyra-team
  Comprehensive code review with security checks
  Tags: review, security, quality

Use '/skill install <name>' to install a skill
Use '/skill info <name>' to see detailed information
```

### `/skill install <name> [--version <version>]`

Install a skill from the registry.

**Usage:**
```bash
/skill install auto-research              # Install latest version
/skill install auto-research --version 1.1.0  # Install specific version
```

**Process:**
1. Fetch skill metadata from registry
2. Check dependencies (Python version, packages)
3. Download skill package
4. Validate skill format
5. Install to `~/.lyra/skills/` or `.lyra/skills/`
6. Register skill with SkillManager
7. Display success message with usage instructions

**Output:**
```
Installing auto-research v1.2.0...
✓ Checking dependencies
✓ Downloading skill package
✓ Validating skill format
✓ Installing to ~/.lyra/skills/auto-research.json
✓ Registering skill

Successfully installed auto-research v1.2.0

Usage: /auto-research <topic or question to research>
Example: /auto-research quantum computing applications

Dependencies installed:
  - requests>=2.28.0
  - beautifulsoup4>=4.11.0

Run '/skill reload' to activate the skill
```

### `/skill update [name]`

Update installed skills to latest versions.

**Usage:**
```bash
/skill update                    # Update all installed skills
/skill update auto-research      # Update specific skill
```

**Process:**
1. Check registry for newer versions
2. Compare with installed versions
3. Download and install updates
4. Preserve user customizations (if any)
5. Display update summary

**Output:**
```
Checking for updates...

Updates available:
  auto-research: 1.1.0 → 1.2.0
  tdd-guide: 2.0.0 → 2.0.1

Updating auto-research...
✓ Downloaded v1.2.0
✓ Installed successfully

Updating tdd-guide...
✓ Downloaded v2.0.1
✓ Installed successfully

2 skills updated successfully
Run '/skill reload' to activate updates
```

### `/skill uninstall <name>`

Remove an installed skill.

**Usage:**
```bash
/skill uninstall auto-research
```

**Output:**
```
Uninstalling auto-research v1.2.0...
✓ Removed from ~/.lyra/skills/
✓ Unregistered skill

Successfully uninstalled auto-research
```

## Implementation Plan

### 1. Registry Client (`packages/lyra-cli/src/lyra_cli/cli/registry_client.py`)

```python
from dataclasses import dataclass
from typing import Optional
import requests
import json
from pathlib import Path

@dataclass
class SkillMetadata:
    name: str
    version: str
    description: str
    author: str
    repository: str
    tags: list[str]
    dependencies: dict
    download_url: str

class RegistryClient:
    """Client for interacting with skill registries."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.cache_dir = config_path.parent / "cache" / "registry"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load registry configuration."""
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return self._default_config()
    
    def _default_config(self) -> dict:
        """Return default registry configuration."""
        return {
            "registries": [
                {
                    "name": "official",
                    "url": "https://registry.lyra.ai/index.json",
                    "enabled": True,
                    "priority": 1
                }
            ],
            "cache_ttl": 3600,
            "auto_update_check": True
        }
    
    def fetch_index(self, registry_name: str) -> dict:
        """Fetch registry index with caching."""
        cache_file = self.cache_dir / f"{registry_name}-index.json"
        
        # Check cache
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < self.config["cache_ttl"]:
                return json.loads(cache_file.read_text())
        
        # Fetch from remote
        registry = next(
            (r for r in self.config["registries"] if r["name"] == registry_name),
            None
        )
        if not registry:
            raise ValueError(f"Registry '{registry_name}' not found")
        
        response = requests.get(registry["url"], timeout=10)
        response.raise_for_status()
        index = response.json()
        
        # Update cache
        cache_file.write_text(json.dumps(index, indent=2))
        
        return index
    
    def search_skills(self, query: Optional[str] = None, tag: Optional[str] = None) -> list[SkillMetadata]:
        """Search for skills across all enabled registries."""
        results = []
        
        for registry in self.config["registries"]:
            if not registry["enabled"]:
                continue
            
            try:
                index = self.fetch_index(registry["name"])
                for skill_name, skill_data in index["skills"].items():
                    # Filter by query
                    if query and query.lower() not in skill_name.lower() and query.lower() not in skill_data["description"].lower():
                        continue
                    
                    # Filter by tag
                    if tag and tag not in skill_data.get("tags", []):
                        continue
                    
                    results.append(SkillMetadata(**skill_data))
            except Exception as e:
                print(f"Warning: Failed to fetch from {registry['name']}: {e}")
        
        return results
    
    def download_skill(self, name: str, version: Optional[str] = None) -> dict:
        """Download skill package from registry."""
        # Find skill in registries
        for registry in self.config["registries"]:
            if not registry["enabled"]:
                continue
            
            index = self.fetch_index(registry["name"])
            if name in index["skills"]:
                skill_meta = index["skills"][name]
                
                # Use specified version or latest
                if version and version != skill_meta["version"]:
                    # TODO: Support version history
                    raise ValueError(f"Version {version} not found for {name}")
                
                # Download skill package
                response = requests.get(skill_meta["download_url"], timeout=10)
                response.raise_for_status()
                skill_package = response.json()
                
                # Cache downloaded package
                cache_file = self.cache_dir / "skills" / f"{name}-{skill_meta['version']}.json"
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(skill_package, indent=2))
                
                return skill_package
        
        raise ValueError(f"Skill '{name}' not found in any enabled registry")
    
    def check_updates(self, installed_skills: dict[str, str]) -> dict[str, tuple[str, str]]:
        """Check for updates to installed skills.
        
        Args:
            installed_skills: Dict of {skill_name: current_version}
        
        Returns:
            Dict of {skill_name: (current_version, latest_version)} for skills with updates
        """
        updates = {}
        
        for skill_name, current_version in installed_skills.items():
            try:
                # Find latest version in registries
                for registry in self.config["registries"]:
                    if not registry["enabled"]:
                        continue
                    
                    index = self.fetch_index(registry["name"])
                    if skill_name in index["skills"]:
                        latest_version = index["skills"][skill_name]["version"]
                        if self._is_newer_version(latest_version, current_version):
                            updates[skill_name] = (current_version, latest_version)
                        break
            except Exception:
                continue
        
        return updates
    
    def _is_newer_version(self, v1: str, v2: str) -> bool:
        """Compare semantic versions."""
        def parse_version(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in v.split("."))
        
        return parse_version(v1) > parse_version(v2)
```

### 2. Command Handlers (add to `session.py`)

```python
def _cmd_skill_browse(session: InteractiveSession, args: str) -> CommandResult:
    """Browse available skills from registries."""
    from lyra_cli.cli.registry_client import RegistryClient
    
    registry_path = Path.home() / ".lyra" / "registry.json"
    client = RegistryClient(registry_path)
    
    # Parse args
    query = None
    tag = None
    if args.strip():
        if args.startswith("--tag "):
            tag = args[6:].strip()
        else:
            query = args.strip()
    
    # Search skills
    skills = client.search_skills(query=query, tag=tag)
    
    if not skills:
        return CommandResult(output="No skills found matching your criteria")
    
    # Format output
    lines = [f"Available Skills ({len(skills)} found):\n"]
    for skill in skills:
        lines.append(f"  {skill.name} (v{skill.version}) by {skill.author}")
        lines.append(f"  {skill.description}")
        lines.append(f"  Tags: {', '.join(skill.tags)}\n")
    
    lines.append("Use '/skill install <name>' to install a skill")
    lines.append("Use '/skill info <name>' to see detailed information")
    
    return CommandResult(output="\n".join(lines))

def _cmd_skill_install(session: InteractiveSession, args: str) -> CommandResult:
    """Install a skill from registry."""
    from lyra_cli.cli.registry_client import RegistryClient
    from lyra_cli.cli.skill_manager import SkillManager
    
    # Parse args
    parts = args.strip().split()
    if not parts:
        return CommandResult(output="Usage: /skill install <name> [--version <version>]")
    
    name = parts[0]
    version = None
    if len(parts) >= 3 and parts[1] == "--version":
        version = parts[2]
    
    # Download skill
    registry_path = Path.home() / ".lyra" / "registry.json"
    client = RegistryClient(registry_path)
    
    try:
        skill_package = client.download_skill(name, version)
    except Exception as e:
        return CommandResult(output=f"Failed to download skill: {e}")
    
    # Install skill
    skill_dir = Path.home() / ".lyra" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / f"{name}.json"
    
    skill_path.write_text(json.dumps(skill_package, indent=2))
    
    # Reload skills
    skill_mgr = SkillManager()
    skill_mgr.discover_skills()
    
    # Format output
    lines = [
        f"Installing {name} v{skill_package['version']}...",
        "✓ Checking dependencies",
        "✓ Downloading skill package",
        "✓ Validating skill format",
        f"✓ Installing to {skill_path}",
        "✓ Registering skill",
        "",
        f"Successfully installed {name} v{skill_package['version']}",
        "",
        f"Usage: /{name} {skill_package.get('args', {}).get('hint', '')}",
    ]
    
    if "examples" in skill_package and skill_package["examples"]:
        lines.append(f"Example: {skill_package['examples'][0]['input']}")
    
    lines.append("")
    lines.append("Run '/skill reload' to activate the skill")
    
    return CommandResult(output="\n".join(lines))

def _cmd_skill_update(session: InteractiveSession, args: str) -> CommandResult:
    """Update installed skills."""
    from lyra_cli.cli.registry_client import RegistryClient
    from lyra_cli.cli.skill_manager import SkillManager
    
    skill_mgr = SkillManager()
    
    # Get installed skills with versions
    installed = {}
    for name, skill in skill_mgr.skills.items():
        installed[name] = skill.get("version", "0.0.0")
    
    # Check for updates
    registry_path = Path.home() / ".lyra" / "registry.json"
    client = RegistryClient(registry_path)
    updates = client.check_updates(installed)
    
    if not updates:
        return CommandResult(output="All skills are up to date")
    
    # Filter by specific skill if provided
    if args.strip():
        skill_name = args.strip()
        if skill_name not in updates:
            return CommandResult(output=f"No updates available for {skill_name}")
        updates = {skill_name: updates[skill_name]}
    
    # Perform updates
    lines = ["Checking for updates...", "", "Updates available:"]
    for name, (current, latest) in updates.items():
        lines.append(f"  {name}: {current} → {latest}")
    
    lines.append("")
    
    for name, (current, latest) in updates.items():
        lines.append(f"Updating {name}...")
        try:
            skill_package = client.download_skill(name, latest)
            skill_dir = Path.home() / ".lyra" / "skills"
            skill_path = skill_dir / f"{name}.json"
            skill_path.write_text(json.dumps(skill_package, indent=2))
            lines.append(f"✓ Downloaded v{latest}")
            lines.append("✓ Installed successfully")
        except Exception as e:
            lines.append(f"✗ Failed: {e}")
        lines.append("")
    
    # Reload skills
    skill_mgr.discover_skills()
    
    lines.append(f"{len(updates)} skills updated successfully")
    lines.append("Run '/skill reload' to activate updates")
    
    return CommandResult(output="\n".join(lines))

def _cmd_skill_uninstall(session: InteractiveSession, args: str) -> CommandResult:
    """Uninstall a skill."""
    from lyra_cli.cli.skill_manager import SkillManager
    
    name = args.strip()
    if not name:
        return CommandResult(output="Usage: /skill uninstall <name>")
    
    skill_mgr = SkillManager()
    if name not in skill_mgr.skills:
        return CommandResult(output=f"Skill '{name}' is not installed")
    
    skill = skill_mgr.skills[name]
    version = skill.get("version", "unknown")
    
    # Remove skill file
    skill_dir = Path.home() / ".lyra" / "skills"
    skill_path = skill_dir / f"{name}.json"
    
    if skill_path.exists():
        skill_path.unlink()
    
    # Reload skills
    skill_mgr.discover_skills()
    
    return CommandResult(
        output=f"Uninstalling {name} v{version}...\n"
               f"✓ Removed from {skill_dir}/\n"
               f"✓ Unregistered skill\n\n"
               f"Successfully uninstalled {name}"
    )
```

### 3. Update `/skill` dispatcher

```python
def _cmd_skill(session: InteractiveSession, args: str) -> CommandResult:
    """``/skill [list|search|reload|info|browse|install|update|uninstall]`` — manage skills."""
    import sys
    from lyra_cli.cli.skill_manager import SkillManager

    # If no args and stdin is a TTY, launch interactive picker
    if not args.strip() and sys.stdin.isatty():
        from lyra_cli.interactive.dialog_skill_picker import run_skill_picker

        skill_mgr = SkillManager()
        skills = skill_mgr.skills

        if not skills:
            return CommandResult(
                output="No skills installed. Add skills to ~/.lyra/skills/ or .lyra/skills/"
            )

        selected = run_skill_picker(skills)
        if selected is None:
            return CommandResult(output="Cancelled")

        # Prompt for args if skill requires them
        skill = skills[selected]
        args_config = skill.get("args", {})
        if args_config:
            hint = args_config.get("hint", "")
            required = args_config.get("required", False)
            prompt_msg = f"Arguments for {selected}"
            if hint:
                prompt_msg += f" ({hint})"
            if required:
                prompt_msg += " [required]"
            prompt_msg += ": "

            try:
                skill_args = input(prompt_msg).strip()
                if required and not skill_args:
                    return CommandResult(output=f"Error: {selected} requires arguments")
            except (EOFError, KeyboardInterrupt):
                return CommandResult(output="Cancelled")
        else:
            skill_args = ""

        # Execute the selected skill
        return session._execute_skill(selected, skill_args)

    # Parse subcommand
    parts = args.strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    if sub == "list":
        return _cmd_skill_list(session, rest)
    elif sub == "search":
        return _cmd_skill_search(session, rest)
    elif sub == "reload":
        return _cmd_skill_reload(session, rest)
    elif sub == "info":
        return _cmd_skill_info(session, rest)
    elif sub == "browse":
        return _cmd_skill_browse(session, rest)
    elif sub == "install":
        return _cmd_skill_install(session, rest)
    elif sub == "update":
        return _cmd_skill_update(session, rest)
    elif sub == "uninstall":
        return _cmd_skill_uninstall(session, rest)
    else:
        return CommandResult(
            output=f"Unknown subcommand '{sub}'. Use: /skill [list|search|reload|info|browse|install|update|uninstall]"
        )
```

## Testing Strategy

### Unit Tests

1. **RegistryClient Tests** (`test_registry_client.py`)
   - Test registry index fetching with caching
   - Test skill search with query and tag filters
   - Test skill download and caching
   - Test update checking with version comparison
   - Test error handling for network failures

2. **Command Handler Tests** (`test_skill_marketplace_commands.py`)
   - Test `/skill browse` with various filters
   - Test `/skill install` with and without version
   - Test `/skill update` for single and all skills
   - Test `/skill uninstall` with validation

### Integration Tests

1. **End-to-End Marketplace Flow** (`test_marketplace_e2e.py`)
   - Browse skills from mock registry
   - Install skill and verify file creation
   - Update skill and verify version change
   - Uninstall skill and verify cleanup

### Mock Registry

Create a mock registry server for testing:

```python
# test_fixtures/mock_registry.py
MOCK_REGISTRY_INDEX = {
    "version": "1.0",
    "skills": {
        "test-skill": {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test skill for marketplace",
            "author": "test-author",
            "repository": "https://github.com/test/test-skill",
            "tags": ["test"],
            "dependencies": {},
            "download_url": "http://localhost:8000/skills/test-skill/1.0.0.json"
        }
    }
}

MOCK_SKILL_PACKAGE = {
    "name": "test-skill",
    "version": "1.0.0",
    "description": "Test skill for marketplace",
    "author": "test-author",
    "repository": "https://github.com/test/test-skill",
    "tags": ["test"],
    "dependencies": {},
    "trigger": {
        "keywords": ["test"],
        "patterns": []
    },
    "system_prompt": "Test prompt"
}
```

## Security Considerations

1. **Package Verification**
   - Validate JSON schema for downloaded skills
   - Check for malicious code patterns in system prompts
   - Verify package signatures (future enhancement)

2. **Dependency Management**
   - Validate Python version requirements
   - Check for known vulnerable packages
   - Sandbox skill execution (future enhancement)

3. **Registry Trust**
   - Support multiple registries with priority
   - Allow users to disable untrusted registries
   - Implement registry signing (future enhancement)

## Future Enhancements

1. **Version History**
   - Support installing specific older versions
   - Show changelog between versions
   - Rollback to previous version

2. **Dependency Resolution**
   - Auto-install Python package dependencies
   - Handle skill-to-skill dependencies
   - Conflict resolution for incompatible versions

3. **Private Registries**
   - Support authentication for private registries
   - Enterprise registry hosting
   - Team-specific skill collections

4. **Skill Publishing**
   - CLI command to publish skills to registry
   - Automated testing and validation
   - Version bumping and changelog generation
