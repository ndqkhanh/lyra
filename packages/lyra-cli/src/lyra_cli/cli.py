#!/usr/bin/env python3
"""Lyra CLI - Main command-line interface"""

import argparse
import sys

from lyra_cli.commands import CommandLoader, get_registry
from lyra_cli.config import ConfigManager
from lyra_cli.loops import LoopManager
from lyra_cli.mcp import MCPManager, register_ecc_servers


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Lyra - AI-powered development harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lyra plan                    # Create implementation plan
  lyra code-review app.py      # Review code
  lyra -p "step1,step2,step3"  # Sequential pipeline
  lyra loop start my-loop      # Start autonomous loop
  lyra mcp list                # List MCP servers
  lyra config show             # Show configuration

For more information, visit: https://github.com/ndqkhanh/lyra
        """
    )

    parser.add_argument("--version", action="version", version="Lyra 0.1.0 (ECC Integration)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--config", type=str, help="Config file path")
    parser.add_argument("-p", "--pipeline", type=str, help="Sequential pipeline (comma-separated steps)")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Config commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_parser.add_argument("action", choices=["show", "set", "get"], help="Config action")
    config_parser.add_argument("key", nargs="?", help="Config key")
    config_parser.add_argument("value", nargs="?", help="Config value")

    # Loop commands
    loop_parser = subparsers.add_parser("loop", help="Loop management")
    loop_parser.add_argument("action", choices=["start", "stop", "status", "list"], help="Loop action")
    loop_parser.add_argument("name", nargs="?", help="Loop name")

    # MCP commands
    mcp_parser = subparsers.add_parser("mcp", help="MCP server management")
    mcp_parser.add_argument("action", choices=["list", "info", "config"], help="MCP action")
    mcp_parser.add_argument("server", nargs="?", help="Server name")

    # Commands list
    subparsers.add_parser("commands", help="List available commands")

    # Skills list
    subparsers.add_parser("skills", help="List available skills")

    # Agents list
    subparsers.add_parser("agents", help="List available agents")

    args = parser.parse_args()

    # Load configuration
    config_manager = ConfigManager(config_file=args.config)
    config = config_manager.load()

    # Handle pipeline mode
    if args.pipeline:
        from lyra_cli.loops import SequentialPipeline
        steps = [s.strip() for s in args.pipeline.split(",")]
        pipeline = SequentialPipeline(steps)
        success = pipeline.execute()
        sys.exit(0 if success else 1)

    # Handle commands
    if args.command == "config":
        handle_config(args, config_manager)
    elif args.command == "loop":
        handle_loop(args)
    elif args.command == "mcp":
        handle_mcp(args)
    elif args.command == "commands":
        handle_commands()
    elif args.command == "skills":
        handle_skills()
    elif args.command == "agents":
        handle_agents()
    else:
        parser.print_help()


def handle_config(args, config_manager):
    """Handle config commands"""
    if args.action == "show":
        config = config_manager.load()
        print("Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    elif args.action == "get":
        if not args.key:
            print("Error: key required")
            sys.exit(1)
        value = config_manager.get(args.key)
        print(f"{args.key}: {value}")
    elif args.action == "set":
        if not args.key or not args.value:
            print("Error: key and value required")
            sys.exit(1)
        config_manager.set(args.key, args.value)
        print(f"Set {args.key} = {args.value}")


def handle_loop(args):
    """Handle loop commands"""
    manager = LoopManager()

    if args.action == "list":
        loops = manager.list_loops()
        print(f"Loops ({len(loops)}):")
        for loop in loops:
            print(f"  {loop['id']}: {loop['status']}")
    elif args.action == "status":
        if not args.name:
            print("Error: loop name required")
            sys.exit(1)
        status = manager.get_loop_status(args.name)
        print(f"Loop: {args.name}")
        print(f"Status: {status.get('status', 'not found')}")
    elif args.action == "start":
        if not args.name:
            print("Error: loop name required")
            sys.exit(1)
        manager.start_loop(args.name)
        print(f"Started loop: {args.name}")
    elif args.action == "stop":
        if not args.name:
            print("Error: loop name required")
            sys.exit(1)
        manager.stop_loop(args.name)
        print(f"Stopped loop: {args.name}")


def handle_mcp(args):
    """Handle MCP commands"""
    manager = MCPManager()
    register_ecc_servers(manager)

    if args.action == "list":
        servers = manager.list_servers()
        print(f"MCP Servers ({len(servers)}):")
        categories = manager.list_categories()
        for category in categories:
            cat_servers = manager.list_servers(category=category)
            print(f"\n{category} ({len(cat_servers)}):")
            for server in cat_servers:
                print(f"  • {server.name}: {server.description}")
    elif args.action == "info":
        if not args.server:
            print("Error: server name required")
            sys.exit(1)
        server = manager.get_server(args.server)
        if server:
            print(f"Name: {server.name}")
            print(f"Description: {server.description}")
            print(f"Command: {server.command}")
            print(f"Args: {' '.join(server.args)}")
            print(f"Category: {server.category}")
        else:
            print(f"Server not found: {args.server}")
    elif args.action == "config":
        manager.save_config()
        print(f"Config saved to: {manager.config_dir / 'servers.json'}")


def handle_commands():
    """Handle commands list"""
    CommandLoader.register_all()
    registry = get_registry()

    commands = registry.list()
    print(f"Commands ({len(commands)}):")

    categories = registry.list_categories()
    for category in categories:
        cat_commands = registry.list(category=category)
        print(f"\n{category} ({len(cat_commands)}):")
        for cmd in cat_commands:
            aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
            print(f"  • {cmd.name}: {cmd.description}{aliases}")


def handle_skills():
    """Handle skills list"""
    from lyra_cli.skills import SkillRegistry, register_ecc_skills

    registry = SkillRegistry()
    register_ecc_skills(registry)

    skills = registry.list()
    print(f"Skills ({len(skills)}):")

    categories = registry.list_categories()
    for category in categories:
        cat_skills = registry.list(category=category)
        print(f"\n{category} ({len(cat_skills)}):")
        for skill in cat_skills:
            triggers = f" (triggers: {', '.join(skill.triggers)})" if skill.triggers else ""
            print(f"  • {skill.name}: {skill.description}{triggers}")


def handle_agents():
    """Handle agents list"""
    from lyra_cli.agents import AgentRegistry, register_ecc_agents

    registry = AgentRegistry()
    register_ecc_agents(registry)

    agents = registry.list()
    print(f"Agents ({len(agents)}):")

    categories = registry.list_categories()
    for category in categories:
        cat_agents = registry.list(category=category)
        print(f"\n{category} ({len(cat_agents)}):")
        for agent in cat_agents:
            print(f"  • {agent.name}: {agent.description} (model: {agent.model})")


if __name__ == "__main__":
    main()
