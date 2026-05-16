"""Tests for Phase 6 Multimodal modules."""

import pytest

from lyra_cli.multimodal.evidence_chain import (
    MediaType,
    MediaMetadata,
    MultimodalEvidenceChain,
)
from lyra_cli.multimodal.computer_use import (
    ActionType,
    UIElement,
    ComputerUseContext,
)
from lyra_cli.multimodal.screenshot_analysis import (
    ScreenshotAnalyzer,
)


# ============================================================================
# Evidence Chain Tests
# ============================================================================

@pytest.fixture
def evidence_chain():
    """Create evidence chain."""
    return MultimodalEvidenceChain()


def test_evidence_start_chain(evidence_chain):
    """Test starting an evidence chain."""
    chain_id = evidence_chain.start_chain("Test task")

    assert chain_id is not None
    assert chain_id in evidence_chain.chains
    assert evidence_chain.stats["total_chains"] == 1


def test_evidence_add_evidence(evidence_chain):
    """Test adding evidence to a chain."""
    chain_id = evidence_chain.start_chain("Test task")

    evidence_id = evidence_chain.add_evidence(
        chain_id=chain_id,
        media_type=MediaType.IMAGE,
        content="base64_image_data",
        description="Test image",
        extracted_text="Sample text",
    )

    assert evidence_id is not None
    assert evidence_chain.stats["total_evidence"] == 1
    assert evidence_chain.stats["images_processed"] == 1


def test_evidence_complete_chain(evidence_chain):
    """Test completing a chain."""
    chain_id = evidence_chain.start_chain("Test task")
    evidence_chain.complete_chain(chain_id)

    chain = evidence_chain.get_chain(chain_id)
    assert chain.completed_at is not None


def test_evidence_search(evidence_chain):
    """Test searching evidence."""
    chain_id = evidence_chain.start_chain("Test task")

    evidence_chain.add_evidence(
        chain_id=chain_id,
        media_type=MediaType.SCREENSHOT,
        content="screenshot_data",
        description="Login screen",
        extracted_text="Username Password Login",
    )

    results = evidence_chain.search_evidence(text_query="login")

    assert len(results) > 0


def test_evidence_export_chain(evidence_chain):
    """Test exporting a chain."""
    chain_id = evidence_chain.start_chain("Test task")

    evidence_chain.add_evidence(
        chain_id=chain_id,
        media_type=MediaType.IMAGE,
        content="image_data",
        description="Test image",
    )

    exported = evidence_chain.export_chain(chain_id)

    assert exported is not None
    assert exported["chain_id"] == chain_id
    assert exported["evidence_count"] == 1


# ============================================================================
# Computer Use Tests
# ============================================================================

@pytest.fixture
def computer_use():
    """Create computer use context."""
    return ComputerUseContext()


def test_computer_use_start_session(computer_use):
    """Test starting a session."""
    session_id = computer_use.start_session("Test task")

    assert session_id is not None
    assert session_id in computer_use.sessions
    assert computer_use.stats["total_sessions"] == 1


def test_computer_use_detect_elements(computer_use):
    """Test detecting UI elements."""
    elements = computer_use.detect_ui_elements("screenshot_data")

    assert len(elements) > 0
    assert elements[0].element_type in ["button", "input", "link", "text"]


def test_computer_use_record_action(computer_use):
    """Test recording an action."""
    session_id = computer_use.start_session("Test task")

    element = UIElement(
        element_id="elem_001",
        element_type="button",
        text="Submit",
        position={"x": 100, "y": 100, "width": 80, "height": 30},
    )

    action_id = computer_use.record_action(
        session_id=session_id,
        action_type=ActionType.CLICK,
        target_element=element,
    )

    assert action_id is not None
    assert computer_use.stats["total_actions"] == 1
    assert computer_use.stats["successful_actions"] == 1


def test_computer_use_end_session(computer_use):
    """Test ending a session."""
    session_id = computer_use.start_session("Test task")
    computer_use.end_session(session_id, "success")

    session = computer_use.get_session(session_id)
    assert session.end_time is not None
    assert session.final_status == "success"


def test_computer_use_action_sequence(computer_use):
    """Test getting action sequence."""
    session_id = computer_use.start_session("Test task")

    # Record multiple actions
    for i in range(3):
        computer_use.record_action(
            session_id=session_id,
            action_type=ActionType.CLICK,
        )

    sequence = computer_use.get_action_sequence(session_id)

    assert len(sequence) == 3


def test_computer_use_export_session(computer_use):
    """Test exporting a session."""
    session_id = computer_use.start_session("Test task")

    computer_use.record_action(
        session_id=session_id,
        action_type=ActionType.CLICK,
    )

    exported = computer_use.export_session(session_id)

    assert exported is not None
    assert exported["session_id"] == session_id
    assert exported["action_count"] == 1


# ============================================================================
# Screenshot Analysis Tests
# ============================================================================

@pytest.fixture
def screenshot_analyzer():
    """Create screenshot analyzer."""
    return ScreenshotAnalyzer()


def test_screenshot_analyze(screenshot_analyzer):
    """Test analyzing a screenshot."""
    analysis_id = screenshot_analyzer.analyze_screenshot(
        screenshot_path="/path/to/screenshot.png"
    )

    assert analysis_id is not None
    assert screenshot_analyzer.stats["total_analyses"] == 1


def test_screenshot_extract_text(screenshot_analyzer):
    """Test extracting text from screenshot."""
    analysis_id = screenshot_analyzer.analyze_screenshot(
        screenshot_path="/path/to/screenshot.png",
        extract_text=True,
    )

    text = screenshot_analyzer.get_extracted_text(analysis_id)

    assert text is not None
    assert len(text) > 0


def test_screenshot_detect_objects(screenshot_analyzer):
    """Test detecting objects in screenshot."""
    analysis_id = screenshot_analyzer.analyze_screenshot(
        screenshot_path="/path/to/screenshot.png",
        detect_objects=True,
    )

    analysis = screenshot_analyzer.get_analysis(analysis_id)

    assert len(analysis.detected_objects) > 0


def test_screenshot_detect_ui(screenshot_analyzer):
    """Test detecting UI elements in screenshot."""
    analysis_id = screenshot_analyzer.analyze_screenshot(
        screenshot_path="/path/to/screenshot.png",
        detect_ui=True,
    )

    analysis = screenshot_analyzer.get_analysis(analysis_id)

    assert len(analysis.ui_elements) > 0


def test_screenshot_search_text(screenshot_analyzer):
    """Test searching for text in screenshots."""
    screenshot_analyzer.analyze_screenshot(
        screenshot_path="/path/to/screenshot.png",
        extract_text=True,
    )

    results = screenshot_analyzer.search_text("sample")

    assert len(results) > 0


def test_screenshot_export_analysis(screenshot_analyzer):
    """Test exporting an analysis."""
    analysis_id = screenshot_analyzer.analyze_screenshot(
        screenshot_path="/path/to/screenshot.png"
    )

    exported = screenshot_analyzer.export_analysis(analysis_id)

    assert exported is not None
    assert exported["analysis_id"] == analysis_id
