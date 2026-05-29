"""Tests for lyra-vision module."""
import pytest
from lyra_vision import (
    Diagram,
    ImageFormat,
    ScreenState,
    TextBlock,
    UIElement,
    VisionConfig,
    VisionModule,
    VisualQA,
)

# ---------------------------------------------------------------------------
# Data class instantiation tests
# ---------------------------------------------------------------------------


def test_image_format_values() -> None:
    """Test ImageFormat enum values."""
    assert ImageFormat.PNG.value == "PNG"
    assert ImageFormat.JPEG.value == "JPEG"
    assert ImageFormat.WEBP.value == "WEBP"
    assert ImageFormat.SVG.value == "SVG"
    assert ImageFormat.BMP.value == "BMP"


def test_text_block_creation() -> None:
    """Test TextBlock dataclass instantiation."""
    block = TextBlock(text="hello", bounds=(10, 20, 100, 30), confidence=0.95)
    assert block.text == "hello"
    assert block.bounds == (10, 20, 100, 30)
    assert block.confidence == 0.95


def test_text_block_immutable() -> None:
    """Test TextBlock is frozen (immutable)."""
    block = TextBlock(text="test", bounds=(0, 0, 0, 0), confidence=0.0)
    with pytest.raises(AttributeError):
        block.text = "changed"  # type: ignore[misc]


def test_ui_element_creation() -> None:
    """Test UIElement dataclass instantiation."""
    elem = UIElement(
        element_type="button",
        label="Submit",
        bounds=(100, 200, 50, 20),
        attributes=(("role", "button"), ("enabled", "true")),
    )
    assert elem.element_type == "button"
    assert elem.label == "Submit"
    assert elem.bounds == (100, 200, 50, 20)
    assert elem.attributes == (("role", "button"), ("enabled", "true"))


def test_screen_state_creation() -> None:
    """Test ScreenState dataclass instantiation."""
    state = ScreenState(
        elements=(),
        raw_text="Hello World",
        dimensions=(1920, 1080),
    )
    assert state.elements == ()
    assert state.raw_text == "Hello World"
    assert state.dimensions == (1920, 1080)


def test_diagram_creation() -> None:
    """Test Diagram dataclass instantiation."""
    diagram = Diagram(
        diagram_type="flowchart",
        nodes=("Start", "End"),
        edges=(("Start", "End"),),
        structured_representation="flowchart LR\n    Start --> End\n",
    )
    assert diagram.diagram_type == "flowchart"
    assert diagram.nodes == ("Start", "End")
    assert diagram.edges == (("Start", "End"),)
    assert "flowchart" in diagram.structured_representation


def test_visual_qa_creation() -> None:
    """Test VisualQA dataclass instantiation."""
    qa = VisualQA(
        question="What color is the sky?",
        answer="Blue",
        confidence=0.95,
        evidence_regions=("top_half",),
    )
    assert qa.question == "What color is the sky?"
    assert qa.answer == "Blue"
    assert qa.confidence == 0.95
    assert qa.evidence_regions == ("top_half",)


def test_vision_config_defaults() -> None:
    """Test VisionConfig default values."""
    config = VisionConfig()
    assert config.ocr_enabled is True
    assert config.diagram_parsing_enabled is True
    assert config.visual_qa_enabled is True
    assert config.image_generation_enabled is True
    assert config.max_image_size == 4096
    assert config.default_format == "PNG"


def test_vision_config_custom() -> None:
    """Test VisionConfig with custom values."""
    config = VisionConfig(
        ocr_enabled=False,
        diagram_parsing_enabled=False,
        visual_qa_enabled=False,
        image_generation_enabled=False,
        max_image_size=1024,
        default_format="JPEG",
    )
    assert config.ocr_enabled is False
    assert config.diagram_parsing_enabled is False
    assert config.visual_qa_enabled is False
    assert config.image_generation_enabled is False
    assert config.max_image_size == 1024
    assert config.default_format == "JPEG"


# ---------------------------------------------------------------------------
# VisionModule tests
# ---------------------------------------------------------------------------


def test_vision_module_init() -> None:
    """Test VisionModule initialization."""
    module = VisionModule()
    assert module._config is not None
    assert isinstance(module._config, VisionConfig)
    assert module._config.ocr_enabled is True


def test_vision_module_init_with_config() -> None:
    """Test VisionModule initialization with custom config."""
    config = VisionConfig(ocr_enabled=False)
    module = VisionModule(config=config)
    assert module._config.ocr_enabled is False


def test_understand_screenshot() -> None:
    """Test screenshot understanding with a minimal PNG."""
    module = VisionModule()
    png_data = VisionModule._make_minimal_png(width=64, height=32)
    result = module.understand_screenshot(png_data, "PNG")
    assert isinstance(result, ScreenState)
    assert result.dimensions == (64, 32)
    assert isinstance(result.elements, tuple)
    assert len(result.elements) == 0
    assert result.raw_text == ""


def test_understand_screenshot_invalid_data() -> None:
    """Test screenshot understanding with non-PNG input."""
    module = VisionModule()
    result = module.understand_screenshot(b"not a real image", "JPEG")
    assert result.dimensions == (0, 0)


def test_generate_image() -> None:
    """Test image generation stub."""
    module = VisionModule()
    result = module.generate_image("a beautiful sunset")
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Validate PNG signature
    assert result[:8] == b'\x89PNG\r\n\x1a\n'


def test_extract_text() -> None:
    """Test OCR text extraction stub."""
    module = VisionModule()
    result = module.extract_text(b"fake image data")
    assert isinstance(result, list)
    assert len(result) >= 1
    assert isinstance(result[0], TextBlock)
    assert "OCR stub" in result[0].text
    assert result[0].bounds == (0, 0, 0, 0)
    assert result[0].confidence == 0.0


def test_parse_diagram() -> None:
    """Test diagram parsing stub."""
    module = VisionModule()
    result = module.parse_diagram(b"fake diagram data")
    assert isinstance(result, Diagram)
    assert result.diagram_type == "flowchart"
    assert len(result.nodes) >= 2
    assert len(result.edges) >= 1
    assert "flowchart" in result.structured_representation


def test_parse_diagram_empty_data() -> None:
    """Test diagram parsing with empty data."""
    module = VisionModule()
    result = module.parse_diagram(b"")
    assert isinstance(result, Diagram)
    assert result.diagram_type == "flowchart"


def test_answer_question() -> None:
    """Test visual QA stub."""
    module = VisionModule()
    result = module.answer_question(b"fake image", "What is shown in this image?")
    assert isinstance(result, VisualQA)
    assert result.question == "What is shown in this image?"
    assert "Stub answer" in result.answer
    assert result.confidence == 0.5
    assert "full_image" in result.evidence_regions


def test_get_stats_initial() -> None:
    """Test get_stats returns initial zeros."""
    module = VisionModule()
    stats = module.get_stats()
    assert stats["total_screenshots"] == 0
    assert stats["total_ocr_calls"] == 0
    assert stats["total_questions"] == 0
    assert stats["avg_confidence"] == 0.0


def test_get_stats_after_operations() -> None:
    """Test get_stats after performing multiple operations."""
    module = VisionModule()
    png_data = VisionModule._make_minimal_png()

    module.understand_screenshot(png_data, "PNG")
    module.extract_text(png_data)
    module.answer_question(png_data, "Test question 1?")
    module.answer_question(png_data, "Test question 2?")

    stats = module.get_stats()
    assert stats["total_screenshots"] == 1
    assert stats["total_ocr_calls"] == 1
    assert stats["total_questions"] == 2
    # avg = (0.0 + 0.5 + 0.5) / 4 = 0.25
    assert stats["avg_confidence"] == 0.25
