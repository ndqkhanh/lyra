"""ECC commands - 75 commands from Everything Claude Code"""

from .command_registry import Command, CommandRegistry


def register_ecc_commands(registry: CommandRegistry):
    """Register all ECC commands"""

    # Planning & Project Management (10 commands)
    planning_commands = [
        Command("plan", "Implementation planning with phased breakdown", lambda: print("Planning..."), category="planning", source="ecc"),
        Command("plan-prd", "PRD generation", lambda: print("Generating PRD..."), category="planning", source="ecc"),
        Command("prp-plan", "Plan-Review-Push: Plan phase", lambda: print("PRP Plan..."), category="planning", source="ecc"),
        Command("prp-prd", "Plan-Review-Push: PRD phase", lambda: print("PRP PRD..."), category="planning", source="ecc"),
        Command("prp-implement", "Plan-Review-Push: Implementation", lambda: print("PRP Implement..."), category="planning", source="ecc"),
        Command("prp-commit", "Plan-Review-Push: Commit", lambda: print("PRP Commit..."), category="planning", source="ecc"),
        Command("prp-pr", "Plan-Review-Push: PR creation", lambda: print("PRP PR..."), category="planning", source="ecc"),
        Command("feature-dev", "Feature development orchestration", lambda: print("Feature dev..."), category="planning", source="ecc"),
        Command("project-init", "Project initialization", lambda: print("Init project..."), category="planning", source="ecc"),
        Command("projects", "Project management", lambda: print("Managing projects..."), category="planning", source="ecc"),
    ]

    # Code Review & Quality (15 commands)
    review_commands = [
        Command("code-review", "General code review", lambda: print("Reviewing..."), category="review", source="ecc"),
        Command("review-pr", "Pull request review", lambda: print("Reviewing PR..."), category="review", source="ecc"),
        Command("quality-gate", "Quality gate checks", lambda: print("Quality gate..."), category="review", source="ecc"),
        Command("harness-audit", "Harness configuration auditing", lambda: print("Auditing..."), category="review", source="ecc"),
        Command("cpp-review", "C++ code review", lambda: print("C++ review..."), category="review", source="ecc"),
        Command("flutter-review", "Flutter code review", lambda: print("Flutter review..."), category="review", source="ecc"),
        Command("go-review", "Go code review", lambda: print("Go review..."), category="review", source="ecc"),
        Command("kotlin-review", "Kotlin code review", lambda: print("Kotlin review..."), category="review", source="ecc"),
        Command("python-review", "Python code review", lambda: print("Python review..."), category="review", source="ecc"),
        Command("rust-review", "Rust code review", lambda: print("Rust review..."), category="review", source="ecc"),
        Command("fastapi-review", "FastAPI code review", lambda: print("FastAPI review..."), category="review", source="ecc"),
        Command("django-review", "Django code review", lambda: print("Django review..."), category="review", source="ecc"),
        Command("typescript-review", "TypeScript code review", lambda: print("TS review..."), category="review", source="ecc"),
        Command("java-review", "Java code review", lambda: print("Java review..."), category="review", source="ecc"),
        Command("database-review", "Database optimization review", lambda: print("DB review..."), category="review", source="ecc"),
    ]

    # Build & Test (15 commands)
    build_test_commands = [
        Command("cpp-build", "C++ build", lambda: print("Building C++..."), category="build", source="ecc"),
        Command("flutter-build", "Flutter build", lambda: print("Building Flutter..."), category="build", source="ecc"),
        Command("go-build", "Go build", lambda: print("Building Go..."), category="build", source="ecc"),
        Command("kotlin-build", "Kotlin build", lambda: print("Building Kotlin..."), category="build", source="ecc"),
        Command("rust-build", "Rust build", lambda: print("Building Rust..."), category="build", source="ecc"),
        Command("gradle-build", "Gradle build", lambda: print("Building Gradle..."), category="build", source="ecc"),
        Command("cpp-test", "C++ tests", lambda: print("Testing C++..."), category="test", source="ecc"),
        Command("flutter-test", "Flutter tests", lambda: print("Testing Flutter..."), category="test", source="ecc"),
        Command("go-test", "Go tests", lambda: print("Testing Go..."), category="test", source="ecc"),
        Command("kotlin-test", "Kotlin tests", lambda: print("Testing Kotlin..."), category="test", source="ecc"),
        Command("rust-test", "Rust tests", lambda: print("Testing Rust..."), category="test", source="ecc"),
        Command("test-coverage", "Coverage analysis", lambda: print("Coverage..."), category="test", source="ecc"),
        Command("build-fix", "Build error resolution", lambda: print("Fixing build..."), category="build", source="ecc"),
        Command("e2e", "E2E testing", lambda: print("E2E tests..."), category="test", source="ecc"),
        Command("verify", "Verification", lambda: print("Verifying..."), category="test", source="ecc"),
    ]

    # Git & Deployment (5 commands)
    git_commands = [
        Command("pr", "Pull request creation", lambda: print("Creating PR..."), category="git", source="ecc"),
        Command("checkpoint", "Checkpointing", lambda: print("Checkpoint..."), category="git", source="ecc"),
        Command("promote", "Promotion workflows", lambda: print("Promoting..."), category="git", source="ecc"),
        Command("hookify", "Git hooks setup", lambda: print("Setting up hooks..."), category="git", source="ecc"),
        Command("hookify-configure", "Configure git hooks", lambda: print("Configuring hooks..."), category="git", source="ecc"),
    ]

    # Multi-Agent Workflows (5 commands)
    multi_agent_commands = [
        Command("multi-plan", "Multi-agent planning", lambda: print("Multi-agent plan..."), category="multi-agent", source="ecc"),
        Command("multi-execute", "Multi-agent execution", lambda: print("Multi-agent execute..."), category="multi-agent", source="ecc"),
        Command("multi-workflow", "Multi-agent workflow", lambda: print("Multi-agent workflow..."), category="multi-agent", source="ecc"),
        Command("multi-backend", "Multi-agent backend", lambda: print("Multi-agent backend..."), category="multi-agent", source="ecc"),
        Command("multi-frontend", "Multi-agent frontend", lambda: print("Multi-agent frontend..."), category="multi-agent", source="ecc"),
    ]

    # Learning & Evolution (10 commands)
    learning_commands = [
        Command("learn", "Learning capabilities", lambda: print("Learning..."), category="learning", source="ecc"),
        Command("learn-eval", "Learning evaluation", lambda: print("Evaluating learning..."), category="learning", source="ecc"),
        Command("evolve", "Evolution features", lambda: print("Evolving..."), category="learning", source="ecc"),
        Command("instinct-import", "Import instincts", lambda: print("Importing instincts..."), category="learning", source="ecc"),
        Command("instinct-export", "Export instincts", lambda: print("Exporting instincts..."), category="learning", source="ecc"),
        Command("instinct-status", "Instinct status", lambda: print("Instinct status..."), category="learning", source="ecc"),
        Command("skill-create", "Create skill", lambda: print("Creating skill..."), category="learning", source="ecc"),
        Command("skill-health", "Skill health check", lambda: print("Checking skills..."), category="learning", source="ecc"),
        Command("rules-distill", "Distill rules", lambda: print("Distilling rules..."), category="learning", source="ecc"),
        Command("context-budget", "Context budget management", lambda: print("Managing context..."), category="learning", source="ecc"),
    ]

    # Session Management (5 commands)
    session_commands = [
        Command("save-session", "Save session", lambda: print("Saving session..."), category="session", source="ecc"),
        Command("resume-session", "Resume session", lambda: print("Resuming session..."), category="session", source="ecc"),
        Command("sessions", "List sessions", lambda: print("Listing sessions..."), category="session", source="ecc"),
        Command("aside", "Aside functionality", lambda: print("Aside..."), category="session", source="ecc"),
        Command("prune", "Pruning operations", lambda: print("Pruning..."), category="session", source="ecc"),
    ]

    # Automation & Loops (5 commands)
    loop_commands = [
        Command("loop-start", "Start loop", lambda: print("Starting loop..."), category="loops", source="ecc"),
        Command("loop-status", "Loop status", lambda: print("Loop status..."), category="loops", source="ecc"),
        Command("santa-loop", "Santa loop automation", lambda: print("Santa loop..."), category="loops", source="ecc"),
        Command("auto-update", "Auto-updates", lambda: print("Auto-updating..."), category="loops", source="ecc"),
        Command("orchestrate", "Orchestration", lambda: print("Orchestrating..."), category="loops", source="ecc"),
    ]

    # Utilities (5 commands)
    utility_commands = [
        Command("update-codemaps", "Update code maps", lambda: print("Updating codemaps..."), category="utility", source="ecc"),
        Command("update-docs", "Update documentation", lambda: print("Updating docs..."), category="utility", source="ecc"),
        Command("refactor-clean", "Code refactoring", lambda: print("Refactoring..."), category="utility", source="ecc"),
        Command("security-scan", "Security scanning", lambda: print("Scanning security..."), category="utility", source="ecc"),
        Command("cost-report", "Cost reporting", lambda: print("Cost report..."), category="utility", source="ecc"),
    ]

    # Register all commands
    all_commands = (
        planning_commands +
        review_commands +
        build_test_commands +
        git_commands +
        multi_agent_commands +
        learning_commands +
        session_commands +
        loop_commands +
        utility_commands
    )

    for cmd in all_commands:
        # Check for duplicates and merge
        if not registry.merge_duplicate(cmd):
            registry.register(cmd)

    print(f"✓ Registered {len(all_commands)} ECC commands")
