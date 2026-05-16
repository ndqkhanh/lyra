#!/usr/bin/env python3
"""Test improved ArXiv and Semantic Scholar discovery with retry logic."""

import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-research/src"))
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-core/src"))

def test_improved_discovery():
    """Test ArXiv and Semantic Scholar with improvements."""
    print("=" * 80)
    print("IMPROVED DISCOVERY TEST")
    print("=" * 80)

    try:
        from lyra_research.discovery import MultiSourceDiscovery
        import os

        # Get API keys from environment
        semantic_scholar_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        github_token = os.environ.get("GITHUB_TOKEN")

        print("\n1. Testing ArXiv (with installed module)...")
        discovery = MultiSourceDiscovery(
            semantic_scholar_key=semantic_scholar_key,
            github_token=github_token,
        )

        # Test ArXiv
        print("\nSearching ArXiv for 'transformer attention mechanisms'...")
        arxiv_results = discovery.arxiv.search("transformer attention mechanisms", max_results=5)

        if arxiv_results:
            print(f"✓ ArXiv working! Found {len(arxiv_results)} papers")
            print(f"  Sample: {arxiv_results[0].title[:80]}...")
        else:
            print("✗ ArXiv returned no results")

        # Test Semantic Scholar with retry logic
        print("\n2. Testing Semantic Scholar (with exponential backoff)...")
        print("Searching Semantic Scholar for 'large language models'...")
        ss_results = discovery.semantic_scholar.search("large language models", max_results=5)

        if ss_results:
            print(f"✓ Semantic Scholar working! Found {len(ss_results)} papers")
            print(f"  Sample: {ss_results[0].title[:80]}...")
        else:
            print("⚠ Semantic Scholar returned no results (may still be rate limited)")

        # Test GitHub (should still work)
        print("\n3. Testing GitHub (baseline)...")
        print("Searching GitHub for 'llm reasoning'...")
        github_results = discovery.github.search("llm reasoning", max_results=5)

        if github_results:
            print(f"✓ GitHub working! Found {len(github_results)} repos")
            print(f"  Sample: {github_results[0].title}")
        else:
            print("✗ GitHub returned no results")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        sources_working = []
        if arxiv_results:
            sources_working.append("ArXiv ✅")
        else:
            sources_working.append("ArXiv ❌")

        if ss_results:
            sources_working.append("Semantic Scholar ✅")
        else:
            sources_working.append("Semantic Scholar ⚠️")

        if github_results:
            sources_working.append("GitHub ✅")
        else:
            sources_working.append("GitHub ❌")

        print("Sources status:")
        for status in sources_working:
            print(f"  {status}")

        # Check if improvements worked
        improvements = []
        if arxiv_results:
            improvements.append("✓ ArXiv module installed and working")
        if ss_results:
            improvements.append("✓ Semantic Scholar retry logic successful")
        elif "rate limited" not in str(ss_results).lower():
            improvements.append("⚠ Semantic Scholar may need API key for higher rate limits")

        if improvements:
            print("\nImprovements:")
            for imp in improvements:
                print(f"  {imp}")

        return len(arxiv_results) > 0 or len(ss_results) > 0

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_improved_discovery()
    sys.exit(0 if success else 1)
