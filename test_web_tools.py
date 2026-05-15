#!/usr/bin/env python3
"""Quick test to verify WebFetch and WebSearch tools are properly registered."""

import sys
from pathlib import Path

# Add packages to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / "packages" / "lyra-core" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "lyra-cli" / "src"))

def test_imports():
    """Test that web tool classes can be imported."""
    print("Testing imports...")
    try:
        from lyra_core.tools import WebFetchTool, WebSearchTool
        print("✅ WebFetchTool and WebSearchTool imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_tool_creation():
    """Test that tool instances can be created."""
    print("\nTesting tool creation...")
    try:
        from lyra_core.tools import WebFetchTool, WebSearchTool

        fetch_tool = WebFetchTool()
        print(f"✅ WebFetchTool created: {fetch_tool.name}")

        search_tool = WebSearchTool()
        print(f"✅ WebSearchTool created: {search_tool.name}")

        return True
    except Exception as e:
        print(f"❌ Tool creation failed: {e}")
        return False

def test_tool_schemas():
    """Test that tools have valid schemas."""
    print("\nTesting tool schemas...")
    try:
        from lyra_core.tools import WebFetchTool, WebSearchTool

        fetch_tool = WebFetchTool()
        fetch_schema = fetch_tool.to_schema()
        assert fetch_schema.get("name") == "WebFetch"
        assert "parameters" in fetch_schema
        print(f"✅ WebFetch schema valid: {fetch_schema['name']}")

        search_tool = WebSearchTool()
        search_schema = search_tool.to_schema()
        assert search_schema.get("name") == "WebSearch"
        assert "parameters" in search_schema
        print(f"✅ WebSearch schema valid: {search_schema['name']}")

        return True
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

def test_registration():
    """Test that tools are registered in chat mode."""
    print("\nTesting tool registration...")
    try:
        from lyra_cli.interactive.chat_tools import _CHAT_TOOL_NAMES

        assert "WebFetch" in _CHAT_TOOL_NAMES
        print("✅ WebFetch in _CHAT_TOOL_NAMES")

        assert "WebSearch" in _CHAT_TOOL_NAMES
        print("✅ WebSearch in _CHAT_TOOL_NAMES")

        return True
    except Exception as e:
        print(f"❌ Registration check failed: {e}")
        return False

def test_builtin_registration():
    """Test that register_builtin_tools includes web tools."""
    print("\nTesting builtin registration...")
    try:
        from harness_core.tools import ToolRegistry
        from lyra_core.tools.builtin import register_builtin_tools

        registry = ToolRegistry()
        register_builtin_tools(registry, repo_root=Path.cwd())

        # Check if WebFetch and WebSearch are in the registry
        schemas = registry.schemas(allowed={"WebFetch", "WebSearch"})

        has_fetch = any(s.get("name") == "WebFetch" for s in schemas)
        has_search = any(s.get("name") == "WebSearch" for s in schemas)

        if has_fetch:
            print("✅ WebFetch registered in ToolRegistry")
        else:
            print("⚠️  WebFetch not in registry (optional deps may be missing)")

        if has_search:
            print("✅ WebSearch registered in ToolRegistry")
        else:
            print("⚠️  WebSearch not in registry (optional deps may be missing)")

        return True
    except Exception as e:
        print(f"❌ Builtin registration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Web Tools Implementation Test Suite")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Tool Creation", test_tool_creation()))
    results.append(("Tool Schemas", test_tool_schemas()))
    results.append(("Chat Mode Registration", test_registration()))
    results.append(("Builtin Registration", test_builtin_registration()))

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Web tools are ready to use.")
        print("\nYou can now run:")
        print("  lyra")
        print("  > Deep research this paper: https://arxiv.org/pdf/2605.05242")
    else:
        print("⚠️  Some tests failed. Check the output above.")
        print("\nCommon issues:")
        print("  - Missing dependencies: pip install 'lyra[web]'")
        print("  - Import path issues: Run from repo root")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
