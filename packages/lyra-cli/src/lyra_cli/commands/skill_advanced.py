"""Advanced skill commands for Phase 4.

Provides commands for:
- Skill analytics and statistics
- Skill composition
- Skill configuration
- Skill templates
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lyra_cli.commands.registry import CommandSpec

if TYPE_CHECKING:
    from lyra_cli.interactive.session import InteractiveSession


def skill_stats_command(session: InteractiveSession, args: str) -> str:
    """Show usage statistics for skills.

    Usage:
        /skill stats              # All skills
        /skill stats <name>       # Specific skill
        /skill stats --top 10     # Top 10 skills
    """
    skill_manager = session.skill_manager

    # Parse arguments
    parts = args.strip().split()
    if not parts:
        # Show all skills stats
        stats = skill_manager.get_skill_stats()
        if not stats:
            return "No skill usage data available yet."

        output = ["Skill Usage Statistics\n"]
        output.append(f"Total skills tracked: {len(stats)}\n")

        # Show top 5 by invocations
        top_skills = skill_manager.get_top_skills(limit=5, sort_by="invocations")
        output.append("\nTop Skills by Invocations:")
        for i, skill in enumerate(top_skills, 1):
            output.append(
                f"  {i}. {skill['skill_name']:<20} "
                f"{skill['total_invocations']:>4} invocations  "
                f"({skill['success_rate']:.1f}% success)  "
                f"avg {skill['avg_duration_ms']/1000:.1f}s"
            )

        return "\n".join(output)

    elif parts[0] == "--top":
        # Show top N skills
        limit = int(parts[1]) if len(parts) > 1 else 10
        sort_by = parts[2] if len(parts) > 2 else "invocations"

        top_skills = skill_manager.get_top_skills(limit=limit, sort_by=sort_by)
        if not top_skills:
            return "No skill usage data available yet."

        output = [f"Top {limit} Skills by {sort_by}:\n"]
        for i, skill in enumerate(top_skills, 1):
            output.append(
                f"  {i}. {skill['skill_name']:<20} "
                f"{skill['total_invocations']:>4} invocations  "
                f"({skill['success_rate']:.1f}% success)  "
                f"avg {skill['avg_duration_ms']/1000:.1f}s"
            )

        return "\n".join(output)

    else:
        # Show specific skill stats
        skill_name = parts[0]
        stats = skill_manager.get_skill_stats(skill_name)

        if not stats:
            return f"No usage data for skill '{skill_name}'"

        skill_stats = stats[skill_name]
        output = [f"Statistics for {skill_name}\n"]
        output.append("Usage:")
        output.append(f"  Total invocations: {skill_stats['total_invocations']}")
        output.append(
            f"  Successful: {skill_stats['successful_invocations']} "
            f"({skill_stats['success_rate']:.1f}%)"
        )
        output.append(f"  Failed: {skill_stats['failed_invocations']}")
        output.append("\nPerformance:")
        output.append(
            f"  Average duration: {skill_stats['avg_duration_ms']/1000:.1f}s"
        )
        output.append("\nTimeline:")
        output.append(f"  First used: {skill_stats['first_used']}")
        output.append(f"  Last used: {skill_stats['last_used']}")

        return "\n".join(output)


def skill_compose_command(session: InteractiveSession, args: str) -> str:
    """Create a composition skill interactively.

    Usage:
        /skill compose <name>
    """
    if not args.strip():
        return "Usage: /skill compose <name>"

    skill_name = args.strip()

    # Interactive composition creation
    output = [f"Creating composition skill: {skill_name}\n"]
    output.append("This feature requires interactive input.")
    output.append("Use the skill template system instead:")
    output.append(f"  /skill new composition-skill")

    return "\n".join(output)


def skill_config_command(session: InteractiveSession, args: str) -> str:
    """Configure a skill.

    Usage:
        /skill config <name>           # Show current config
        /skill config <name> <key> <value>  # Set config value
        /skill config list             # List all configured skills
    """
    skill_manager = session.skill_manager
    parts = args.strip().split(maxsplit=2)

    if not parts:
        return "Usage: /skill config <name> [<key> <value>]"

    if parts[0] == "list":
        # List all configured skills
        config = skill_manager.config_manager.config
        skills_config = config.get("skills", {})

        if not skills_config:
            return "No skills configured yet."

        output = ["Configured Skills:\n"]
        for skill_name, skill_config in skills_config.items():
            output.append(f"  {skill_name}:")
            for key, value in skill_config.items():
                output.append(f"    {key}: {value}")
            output.append("")

        return "\n".join(output)

    skill_name = parts[0]

    if len(parts) == 1:
        # Show current config
        config = skill_manager.get_skill_config(skill_name)
        if not config:
            return f"No configuration for skill '{skill_name}'"

        output = [f"Configuration for {skill_name}:\n"]
        for key, value in config.items():
            output.append(f"  {key}: {value}")

        return "\n".join(output)

    elif len(parts) == 3:
        # Set config value
        key = parts[1]
        value = parts[2]

        # Try to parse value as JSON
        import json

        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass  # Keep as string

        # Get current config and update
        config = skill_manager.get_skill_config(skill_name)
        config[key] = value
        skill_manager.set_skill_config(skill_name, config)

        return f"✓ Set {skill_name}.{key} = {value}"

    else:
        return "Usage: /skill config <name> [<key> <value>]"


def skill_new_command(session: InteractiveSession, args: str) -> str:
    """Create a new skill from a template.

    Usage:
        /skill new [template]
    """
    skill_manager = session.skill_manager

    if not args.strip():
        # Show available templates
        templates = skill_manager.list_templates()
        output = ["Available Skill Templates:\n"]
        for template in templates:
            output.append(f"  {template['name']}")
            output.append(f"  {template['description']}")
            output.append("")

        output.append("Use '/skill new <template>' to create a skill from template")
        return "\n".join(output)

    template_name = args.strip()

    # For now, show a message about interactive creation
    output = [f"Creating skill from template: {template_name}\n"]
    output.append("This feature requires interactive input.")
    output.append("Template system is available via API:")
    output.append("  skill_manager.create_from_template(template_name, variables)")

    return "\n".join(output)


def skill_template_command(session: InteractiveSession, args: str) -> str:
    """Manage skill templates.

    Usage:
        /skill template list
    """
    skill_manager = session.skill_manager

    if args.strip() == "list":
        templates = skill_manager.list_templates()
        output = ["Available Skill Templates:\n"]
        for template in templates:
            output.append(f"  {template['name']}")
            output.append(f"  {template['description']}")
            output.append(f"  Category: {template['category']}")
            output.append("")

        return "\n".join(output)

    return "Usage: /skill template list"


# Command specifications
SKILL_ADVANCED_COMMANDS = [
    CommandSpec(
        name="skill-stats",
        handler=skill_stats_command,
        description="Show skill usage statistics",
        category="skill",
        args_hint="[name|--top N]",
    ),
    CommandSpec(
        name="skill-compose",
        handler=skill_compose_command,
        description="Create a composition skill",
        category="skill",
        args_hint="<name>",
    ),
    CommandSpec(
        name="skill-config",
        handler=skill_config_command,
        description="Configure a skill",
        category="skill",
        args_hint="<name> [<key> <value>]",
    ),
    CommandSpec(
        name="skill-new",
        handler=skill_new_command,
        description="Create a skill from template",
        category="skill",
        args_hint="[template]",
    ),
    CommandSpec(
        name="skill-template",
        handler=skill_template_command,
        description="Manage skill templates",
        category="skill",
        args_hint="list",
    ),
]
