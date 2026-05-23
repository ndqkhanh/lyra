#!/usr/bin/env python3
"""Lyra main CLI entry point"""

import argparse
import sys
from pathlib import Path

from lyra_cli.commands import get_registry, CommandLoader
from lyra_cli.config import ConfigManager
from lyra_cli.loops import LoopManager, SequentialPipeline
from lyra_cli.mcp import MCPManager, register_ecc_servers
from lyra_cli.skills import SkillRegistry, register_ecc_skills
from lyra_cli.agents import AgentRegistry, register_ecc_agents


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Lyra - AI-powered development harness with ECC integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lyra commands                # List all commands
  lyra skills                  # List all skills
  lyra agents                  # List all agents
  lyra mcp list                # List MCP servers
  lyra config show             # Show configuration
  lyra -p "step1,step2,step3"  # Sequential pipeline

For more information, visit: https://github.com/ndqkhanh/lyra
        """
    )

    parser.add_argument("--version", action="version", version="Lyra 0.1.0 (ECC Integration)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-p", "--pipeline", type=str, help="Sequential pipeline (comma-separated steps)")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Config commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_parser.add_argument("action", choices=["show", "set", "get"], help="Config action")
    config_parser.add_argument("key", nargs="?", help="Config key")
    config_parser.add_argument("value", nargs="?", help="Config value")

    # MCP commands
    mcp_parser = subparsers.add_parser("mcp", help="MCP server management")
    mcp_parser.add_argument("action", choices=["list", "info"], help="MCP action")
    mcp_parser.add_argument("server", nargs="?", help="Server name")

    # List commands
    subparsers.add_parser("commands", help="List available commands")
    subparsers.add_parser("skills", help="List available skills")
    subparsers.add_parser("agents", help="List available agents")

    args = parser.parse_args()

    # Handle pipeline mode
    if args.pipeline:
        steps = [s.strip() for s in args.pipeline.split(",")]
        pipeline = SequentialPipeline(steps)
        success = pipeline.execute()
        sys.exit(0 if success else 1)

    # Handle commands
    if args.command == "config":
        handle_config(args)
    elif args.command == "mcp":
        handle_mcp(args)
    elif args.command == "commands":
        list_commands()
    elif args.command == "skills":
        list_skills()
    elif args.command == "agents":
        list_agents()
    else:
        parser.print_help()


def handle_config(args):
    """Handle config commands"""
    config_manager = ConfigManager()

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


def list_commands():
    """List all commands"""
    CommandLoader.register_all()
    registry = get_registry()

    commands = registry.list()
    print(f"Commands ({len(commands)}):")

    categories = registry.list_categories()
    for category in categories:
        cat_commands = registry.list(category=category)
        print(f"\n{category} ({len(cat_commands)}):")
        for cmd in cat_commands[:3]:  # Show first 3
            print(f"  • {cmd.name}: {cmd.description}")
        if len(cat_commands) > 3:
            print(f"  ... and {len(cat_commands) - 3} more")


def list_skills():
    """List all skills"""
    registry = SkillRegistry()
    register_ecc_skills(registry)

    skills = registry.list()
    print(f"Skills ({len(skills)}):")

    categories = registry.list_categories()
    for category in categories:
        cat_skills = registry.list(category=category)
        print(f"\n{category} ({len(cat_skills)}):")
        for skill in cat_skills:
            print(f"  • {skill.name}: {skill.description}")


def list_agents():
    """List all agents"""
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
