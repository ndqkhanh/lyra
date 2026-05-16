#!/usr/bin/env python3
"""Test all 7 research sources to verify they work correctly."""

import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-research/src"))
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-core/src"))

def test_all_sources():
    """Test all 7 research sources."""
    print("=" * 80)
    print("TESTING ALL 7 RESEARCH SOURCES")
    print("=" * 80)

    try:
        from lyra_research.discovery import MultiSourceDiscovery
        import os

        # Get API keys from environment
        semantic_scholar_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        github_token = os.environ.get("GITHUB_TOKEN")

        print("\n📋 API Keys Status:")
        print(f"  SEMANTIC_SCHOLAR_API_KEY: {'✓ Set' if semantic_scholar_key else '✗ Not set'}")
        print(f"  GITHUB_TOKEN: {'✓ Set' if github_token else '✗ Not set'}")

        discovery = MultiSourceDiscovery(
            semantic_scholar_key=semantic_scholar_key,
            github_token=github_token,
        )

        # Test query
        query = "large language models"
        max_results = 5

        print(f"\n🔍 Testing with query: '{query}'")
        print(f"📊 Max results per source: {max_results}")
        print("\n" + "=" * 80)

        # Test each source individually
        sources_to_test = [
            ("arxiv", "ArXiv"),
            ("semantic_scholar", "Semantic Scholar"),
            ("github", "GitHub"),
            ("huggingface", "HuggingFace Papers"),
            ("openreview", "OpenReview"),
            ("papers_with_code", "Papers with Code"),
            ("acl", "ACL Anthology"),
        ]

        results_summary = {}
        total_sources = 0

        for source_key, source_name in sources_to_test:
            print(f"\n{source_name}:")
            print("-" * 40)

            try:
                result = discovery.discover(
                    query,
                    sources=[source_key],
                    max_per_source=max_results,
                )

                count = len(result.get(source_key, []))
                results_summary[source_name] = count

                if count > 0:
                    total_sources += count
                    print(f"✓ {source_name} working! Found {count} results")

                    # Show first result
                    first = result[source_key][0]
                    print(f"  Sample: {first.title[:80]}...")
                    print(f"  URL: {first.url}")
                else:
                    print(f"⚠ {source_name} returned no results")

            except Exception as e:
                print(f"✗ {source_name} error: {e}")
                results_summary[source_name] = 0

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        working_sources = sum(1 for count in results_summary.values() if count > 0)
        total_count = sum(results_summary.values())

        print(f"\n📊 Sources Status:")
        for source_name, count in results_summary.items():
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {source_name}: {count} results")

        print(f"\n📈 Overall Statistics:")
        print(f"  Working sources: {working_sources}/7 ({working_sources/7*100:.0f}%)")
        print(f"  Total results: {total_count}")
        print(f"  Average per source: {total_count/7:.1f}")

        # Recommendations
        print(f"\n💡 Recommendations:")
        if semantic_scholar_key:
            print("  ✓ Semantic Scholar API key configured")
        else:
            print("  ⚠ Set SEMANTIC_SCHOLAR_API_KEY for higher rate limits")
            print("    Get free key: https://www.semanticscholar.org/product/api")

        if github_token:
            print("  ✓ GitHub token configured")
        else:
            print("  ⚠ Set GITHUB_TOKEN for higher rate limits")

        # Test full discovery with all sources
        print("\n" + "=" * 80)
        print("TESTING FULL DISCOVERY (ALL SOURCES)")
        print("=" * 80)

        print(f"\nRunning full discovery with all 7 sources...")
        full_results = discovery.discover(query, max_per_source=10)

        total_full = sum(len(sources) for sources in full_results.values())
        print(f"\n✓ Full discovery completed!")
        print(f"  Total sources found: {total_full}")
        print(f"  Breakdown: {dict((k, len(v)) for k, v in full_results.items())}")

        return working_sources >= 5  # Success if at least 5/7 sources work

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_all_sources()
    sys.exit(0 if success else 1)
