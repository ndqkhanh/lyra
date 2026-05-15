"""Complete slash commands for Lyra - All 80+ commands.

Implements all Lyra-specific features:
- Research workflows
- Agent teams
- Memory systems
- Skills management
- Evolution features
- And all Claude Code commands
"""

from __future__ import annotations

# Complete command registry (80+ commands)
LYRA_COMMANDS = {
    # === CONVERSATION & NAVIGATION ===
    "/help": "List all commands",
    "/exit": "Exit REPL",
    "/quit": "Exit REPL (alias)",
    "/clear": "Clear screen",
    "/new": "Start fresh chat (Ctrl-N)",
    "/history": "Show recent inputs",
    "/compact": "Compress chat history",
    "/search": "Search sessions (FTS5)",
    "/replay": "Replay past sessions",

    # === MODELS & CONFIGURATION ===
    "/model": "Show current model + fast/smart slots",
    "/models": "List all available models",
    "/status": "Show model, mode, budget, tools",
    "/budget": "Show/set cost cap",
    "/stream": "Toggle streaming output",
    "/config": "Configuration management",
    "/credentials": "Set API credentials",

    # === MODES ===
    "/mode": "Switch mode (agent|plan|debug|ask)",

    # === PLANNING & EXECUTION ===
    "/plan": "Generate implementation plan",
    "/approve": "Approve plan and execute",
    "/reject": "Reject current plan",
    "/spawn": "Fork subagent in worktree",
    "/verify": "Replay verifier",

    # === CODE REVIEW & DIFF ===
    "/review": "Post-turn diff review",
    "/diff": "Show working tree diff",
    "/blame": "Git blame annotations",
    "/map": "ASCII tree of repo",
    "/security-review": "OWASP security review",
    "/simplify": "3-pass review (quality/reuse/efficiency)",

    # === TOOLS & SKILLS ===
    "/tools": "List registered tools",
    "/skills": "Show injected SKILL.md files",
    "/memory": "Show memory window",
    "/mcp": "Manage MCP servers",

    # === SESSIONS & HANDOFF ===
    "/session": "Session management",
    "/handoff": "Generate handoff message",
    "/retro": "Session retrospective",
    "/export": "Export transcript as markdown",
    "/copy": "Copy to clipboard",
    "/resume": "Resume session",
    "/fork": "Fork session",
    "/rename": "Rename session",

    # === TEAMS & AGENTS ===
    "/team": "Multi-agent team execution",
    "/agents": "List available agents",
    "/agentteams": "Anthropic Agent Teams runtime",

    # === RESEARCH & INVESTIGATION ===
    "/research": "Deep research workflow (10-step pipeline)",
    "/investigate": "DCI-mode investigation",
    "/deep-research": "Alias for /research",

    # === CRON & SCHEDULING ===
    "/cron": "Manage cron jobs",
    "/schedule": "Alias for /cron",
    "/loop": "Recurring prompt",

    # === MEMORY & REFLECTION ===
    "/reflect": "Add lesson to memory",
    "/btw": "Add side note to memory",

    # === CONFIGURATION & THEME ===
    "/theme": "Switch color theme",
    "/color": "Tint prompt accent",
    "/statusline": "Set toolbar format",
    "/fast": "Toggle fast posture",
    "/focus": "Hide side panels",
    "/tui": "Switch rendering mode",
    "/vim": "Toggle vim mode",
    "/sandbox": "Toggle filesystem sandbox",

    # === OBSERVABILITY & DEBUGGING ===
    "/trace": "Toggle event logging",
    "/self": "Agent introspection",
    "/context": "Context window breakdown",
    "/stats": "Session metrics",
    "/cost": "Cost breakdown",
    "/badges": "Command usage stats",
    "/debug": "Toggle debug mode",
    "/doctor": "Health check",
    "/hooks": "List active hooks",
    "/permissions": "Permission mode",
    "/usage": "Usage statistics",

    # === ADVANCED FEATURES ===
    "/autopilot": "Supervised autonomy status",
    "/ultrawork": "Enhanced work mode",
    "/ralph": "Agent contract mode",
    "/ralplan": "Strategic planning mode",
    "/continue": "Re-feed agent",
    "/sharpen": "Rewrite task as goals",
    "/directive": "Append to HUMAN_DIRECTIVE.md",
    "/contract": "AgentContract budget",
    "/batch": "Multi-unit refactor",
    "/add-dir": "Add auxiliary directory",
    "/pr-comments": "Fetch GitHub PR comments",
    "/feedback": "Print issue URL + context",
    "/release-notes": "Show CHANGELOG",
    "/logout": "Clear credentials",
    "/plugin": "Plugin management",
    "/reload-plugins": "Reload plugins",
    "/claude-api": "Claude API reference",

    # === LYRA UNIQUE FEATURES ===
    "/scaling": "Four-axis scaling laws",
    "/coverage": "Verifier coverage index",
    "/bundle": "Software 3.0 bundle pipeline",
    "/commands": "User-defined commands",
    "/keybindings": "Show keyboard shortcuts",
    "/palette": "Command palette",
    "/soul": "Show SOUL.md",
    "/policy": "Show permission policy",
    "/evals": "Run evaluations",
    "/auth": "OAuth flow",
    "/init": "Initialize project",
    "/rewind": "Undo last turn",
    "/redo": "Redo turn",
    "/toolsets": "Manage tool sets",
    "/wiki": "Wiki operations",
    "/voice": "Voice commands",
    "/split": "Split view",
    "/pair": "Pair programming mode",
    "/recap": "Terse summary",

    # === GIT OPERATIONS ===
    "/commit": "Create git commit",
    "/pr": "Create pull request",
    "/push": "Push current branch",
}


def get_command_category(command: str) -> str:
    """Get category for a command."""
    categories = {
        "conversation": ["/help", "/exit", "/quit", "/clear", "/new", "/history", "/compact", "/search", "/replay"],
        "models": ["/model", "/models", "/status", "/budget", "/stream", "/config", "/credentials"],
        "planning": ["/plan", "/approve", "/reject", "/spawn", "/verify", "/mode"],
        "review": ["/review", "/diff", "/blame", "/map", "/security-review", "/simplify"],
        "tools": ["/tools", "/skills", "/memory", "/mcp"],
        "sessions": ["/session", "/handoff", "/retro", "/export", "/copy", "/resume", "/fork", "/rename"],
        "teams": ["/team", "/agents", "/agentteams"],
        "research": ["/research", "/investigate", "/deep-research"],
        "scheduling": ["/cron", "/schedule", "/loop"],
        "memory": ["/reflect", "/btw"],
        "theme": ["/theme", "/color", "/statusline", "/fast", "/focus", "/tui", "/vim", "/sandbox"],
        "debug": ["/trace", "/self", "/context", "/stats", "/cost", "/badges", "/debug", "/doctor", "/hooks", "/permissions", "/usage"],
        "advanced": ["/autopilot", "/ultrawork", "/ralph", "/ralplan", "/continue", "/sharpen", "/directive", "/contract", "/batch", "/add-dir", "/pr-comments", "/feedback", "/release-notes", "/logout", "/plugin", "/reload-plugins", "/claude-api"],
        "unique": ["/scaling", "/coverage", "/bundle", "/commands", "/keybindings", "/palette", "/soul", "/policy", "/evals", "/auth", "/init", "/rewind", "/redo", "/toolsets", "/wiki", "/voice", "/split", "/pair", "/recap"],
        "git": ["/commit", "/pr", "/push"],
    }

    for category, commands in categories.items():
        if command in commands:
            return category
    return "other"


def format_help_by_category() -> str:
    """Format help text organized by category."""
    output = []

    categories = {
        "conversation": "Conversation & Navigation",
        "models": "Models & Configuration",
        "planning": "Planning & Execution",
        "review": "Code Review & Diff",
        "tools": "Tools & Skills",
        "sessions": "Sessions & Handoff",
        "teams": "Teams & Agents",
        "research": "Research & Investigation",
        "scheduling": "Cron & Scheduling",
        "memory": "Memory & Reflection",
        "theme": "Configuration & Theme",
        "debug": "Observability & Debugging",
        "advanced": "Advanced Features",
        "unique": "Lyra Unique Features",
        "git": "Git Operations",
    }

    for cat_key, cat_name in categories.items():
        output.append(f"\n\033[1m{cat_name}:\033[0m")
        for cmd, desc in LYRA_COMMANDS.items():
            if get_command_category(cmd) == cat_key:
                output.append(f"  \033[36m{cmd:<20}\033[0m {desc}")

    return "\n".join(output)
