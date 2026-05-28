"""Tests for Multimodal Memory Integration."""

import pytest
from lyra_cli.multimodal.memory_integration import (
    CompressionLevel,
    MultimodalMemoryIntegrator,
)


@pytest.fixture
def integrator():
    """Create integrator with aggressive compression."""
    return MultimodalMemoryIntegrator(
        compression_level=CompressionLevel.AGGRESSIVE
    )


@pytest.fixture
def integrator_no_compression():
    """Create integrator with no compression."""
    return MultimodalMemoryIntegrator(
        compression_level=CompressionLevel.NONE
    )


# ============================================================================
# Screenshot Storage Tests
# ============================================================================

def test_store_screenshot(integrator):
    """Test storing a screenshot."""
    ref_id = integrator.store_screenshot(
        screenshot_data="base64_screenshot_data",
        description="Login page",
        extracted_text="Username Password Login",
        detected_objects=["button", "input"],
        context={"task": "login", "step": 1},
    )

    assert ref_id is not None
    assert ref_id.startswith("screenshot_")
    assert integrator.stats["screenshots_stored"] == 1
    assert integrator.stats["total_stored"] == 1


def test_store_screenshot_with_chain(integrator):
    """Test storing screenshot in evidence chain."""
    chain_id = integrator.evidence_chain.start_chain("Test task")

    ref_id = integrator.store_screenshot(
        screenshot_data="base64_screenshot_data",
        description="Login page",
        extracted_text="Username Password Login",
        chain_id=chain_id,
    )

    assert ref_id is not None

    # Check evidence chain
    chain = integrator.evidence_chain.get_chain(chain_id)
    assert len(chain.evidence_items) == 1


def test_screenshot_compression_aggressive(integrator):
    """Test aggressive compression."""
    ref_id = integrator.store_screenshot(
        screenshot_data="x" * 10_000_000,  # 10MB
        description="Large screenshot",
    )

    ref = integrator.get_reference(ref_id)
    assert ref is not None
    assert ref.thumbnail is not None
    assert integrator.stats["bytes_saved"] > 0


def test_screenshot_compression_none(integrator_no_compression):
    """Test no compression."""
    ref_id = integrator_no_compression.store_screenshot(
        screenshot_data="base64_screenshot_data",
        description="Screenshot",
    )

    ref = integrator_no_compression.get_reference(ref_id)
    assert ref is not None
    assert ref.storage_path is not None

    # Full content should be stored
    content = integrator_no_compression.get_full_content(ref_id)
    assert content is not None


# ============================================================================
# DOM Storage Tests
# ============================================================================

def test_store_dom_snapshot(integrator):
    """Test storing a DOM snapshot."""
    dom_html = "<html><body><button>Click me</button></body></html>"

    ref_id = integrator.store_dom_snapshot(
        dom_data=dom_html,
        description="Login page DOM",
        relevant_elements=[{"tag": "button", "text": "Click me"}],
        context={"url": "https://example.com/login"},
    )

    assert ref_id is not None
    assert ref_id.startswith("dom_")
    assert integrator.stats["dom_snapshots_stored"] == 1


def test_dom_filtering(integrator):
    """Test DOM filtering reduces size."""
    large_dom = "<html>" + "<div>content</div>" * 1000 + "</html>"

    ref_id = integrator.store_dom_snapshot(
        dom_data=large_dom,
        description="Large DOM",
    )

    ref = integrator.get_reference(ref_id)
    assert ref is not None
    assert ref.metadata["filtered_size"] < ref.metadata["original_size"]
    assert integrator.stats["bytes_saved"] > 0


# ============================================================================
# Terminal Output Storage Tests
# ============================================================================

def test_store_terminal_output(integrator):
    """Test storing terminal output."""
    ref_id = integrator.store_terminal_output(
        command="ls -la",
        output="total 48\ndrwxr-xr-x  12 user  staff  384 May 20 10:00 .",
        exit_code=0,
        description="List directory",
        context={"cwd": "/home/user"},
    )

    assert ref_id is not None
    assert ref_id.startswith("terminal_")
    assert integrator.stats["terminal_outputs_stored"] == 1


def test_terminal_output_truncation(integrator):
    """Test long output is truncated."""
    long_output = "x" * 20_000

    ref_id = integrator.store_terminal_output(
        command="cat large_file.txt",
        output=long_output,
        exit_code=0,
        description="Large output",
    )

    ref = integrator.get_reference(ref_id)
    assert ref is not None
    assert "truncated" in ref.extracted_text


# ============================================================================
# Search Tests
# ============================================================================

def test_search_multimodal(integrator):
    """Test searching multimodal content."""
    # Store multiple items
    integrator.store_screenshot(
        screenshot_data="data1",
        description="Login page",
        extracted_text="Username Password",
    )

    integrator.store_screenshot(
        screenshot_data="data2",
        description="Dashboard",
        extracted_text="Welcome User",
    )

    integrator.store_dom_snapshot(
        dom_data="<html>Login</html>",
        description="Login DOM",
    )

    # Search for "login"
    results = integrator.search_multimodal("login")

    assert len(results) >= 2  # Screenshot + DOM


def test_search_by_media_type(integrator):
    """Test filtering search by media type."""
    integrator.store_screenshot(
        screenshot_data="data1",
        description="Screenshot",
    )

    integrator.store_dom_snapshot(
        dom_data="<html></html>",
        description="DOM",
    )

    # Search only screenshots
    results = integrator.search_multimodal("", media_type="screenshot")

    assert len(results) == 1
    assert results[0].media_type == "screenshot"


def test_search_limit(integrator):
    """Test search result limit."""
    # Store many items
    for i in range(20):
        integrator.store_screenshot(
            screenshot_data=f"data{i}",
            description="Test screenshot",
        )

    results = integrator.search_multimodal("test", limit=5)

    assert len(results) == 5


# ============================================================================
# Reference Management Tests
# ============================================================================

def test_get_reference(integrator):
    """Test getting a reference by ID."""
    ref_id = integrator.store_screenshot(
        screenshot_data="data",
        description="Test",
    )

    ref = integrator.get_reference(ref_id)

    assert ref is not None
    assert ref.ref_id == ref_id
    assert ref.description == "Test"


def test_get_full_content(integrator_no_compression):
    """Test getting full content."""
    ref_id = integrator_no_compression.store_screenshot(
        screenshot_data="full_content_data",
        description="Test",
    )

    content = integrator_no_compression.get_full_content(ref_id)

    assert content is not None
    assert b"full_content_data" in content


def test_get_full_content_not_stored(integrator):
    """Test getting full content when not stored (aggressive compression)."""
    ref_id = integrator.store_screenshot(
        screenshot_data="data",
        description="Test",
    )

    content = integrator.get_full_content(ref_id)

    # With aggressive compression, full content is not stored
    assert content is None


def test_export_reference(integrator):
    """Test exporting a reference."""
    ref_id = integrator.store_screenshot(
        screenshot_data="data",
        description="Test screenshot",
        extracted_text="Sample text",
    )

    exported = integrator.export_reference(ref_id)

    assert exported is not None
    assert exported["ref_id"] == ref_id
    assert exported["media_type"] == "screenshot"
    assert exported["description"] == "Test screenshot"
    assert exported["extracted_text"] == "Sample text"


# ============================================================================
# Statistics Tests
# ============================================================================

def test_get_stats(integrator):
    """Test getting statistics."""
    # Store various items
    integrator.store_screenshot(
        screenshot_data="data1",
        description="Screenshot 1",
    )

    integrator.store_screenshot(
        screenshot_data="data2",
        description="Screenshot 2",
    )

    integrator.store_dom_snapshot(
        dom_data="<html></html>",
        description="DOM",
    )

    integrator.store_terminal_output(
        command="ls",
        output="file1 file2",
        exit_code=0,
        description="Terminal",
    )

    stats = integrator.get_stats()

    assert stats["total_stored"] == 4
    assert stats["screenshots_stored"] == 2
    assert stats["dom_snapshots_stored"] == 1
    assert stats["terminal_outputs_stored"] == 1
    assert stats["num_references"] == 4


def test_compression_stats(integrator):
    """Test compression statistics."""
    # Store large screenshot
    integrator.store_screenshot(
        screenshot_data="x" * 10_000_000,
        description="Large screenshot",
    )

    stats = integrator.get_stats()

    assert stats["total_compressed"] > 0
    assert stats["bytes_saved"] > 0


# ============================================================================
# Content Hash Tests
# ============================================================================

def test_content_hash_deduplication(integrator_no_compression):
    """Test that identical content shares the same hash."""
    ref_id1 = integrator_no_compression.store_screenshot(
        screenshot_data="identical_data",
        description="Screenshot 1",
    )

    ref_id2 = integrator_no_compression.store_screenshot(
        screenshot_data="identical_data",
        description="Screenshot 2",
    )

    ref1 = integrator_no_compression.get_reference(ref_id1)
    ref2 = integrator_no_compression.get_reference(ref_id2)

    # Same content hash
    assert ref1.content_hash == ref2.content_hash

    # But different reference IDs
    assert ref1.ref_id != ref2.ref_id


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow(integrator):
    """Test complete workflow: store, search, retrieve."""
    # Start evidence chain
    chain_id = integrator.evidence_chain.start_chain("Login workflow")

    # Store screenshot
    screenshot_ref = integrator.store_screenshot(
        screenshot_data="screenshot_data",
        description="Login page",
        extracted_text="Username Password Login",
        chain_id=chain_id,
    )

    # Store DOM
    dom_ref = integrator.store_dom_snapshot(
        dom_data="<html><form>Login form</form></html>",
        description="Login form DOM",
        chain_id=chain_id,
    )

    # Store terminal output
    terminal_ref = integrator.store_terminal_output(
        command="curl https://example.com/login",
        output="200 OK",
        exit_code=0,
        description="Login API call",
        chain_id=chain_id,
    )

    # Complete chain
    integrator.evidence_chain.complete_chain(chain_id)

    # Search
    results = integrator.search_multimodal("login")
    assert len(results) >= 2

    # Retrieve references
    screenshot = integrator.get_reference(screenshot_ref)
    dom = integrator.get_reference(dom_ref)
    terminal = integrator.get_reference(terminal_ref)

    assert screenshot is not None
    assert dom is not None
    assert terminal is not None

    # Export
    exported_screenshot = integrator.export_reference(screenshot_ref)
    assert exported_screenshot is not None

    # Check stats
    stats = integrator.get_stats()
    assert stats["total_stored"] == 3
