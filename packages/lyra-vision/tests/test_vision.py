"""Tests for lyra-vision."""
import pytest
from lyra_vision import VisionModule


class TestVisionModule:
    @pytest.mark.asyncio
    async def test_understand_screenshot(self):
        v = VisionModule()
        state = await v.understand_screenshot(b"fake_image")
        assert state.dimensions == (1920, 1080)
        assert len(state.elements) >= 1

    @pytest.mark.asyncio
    async def test_generate_image(self):
        v = VisionModule()
        data = await v.generate_image("A beautiful landscape")
        assert isinstance(data, bytes)
        assert v.stats["images_processed"] >= 1

    @pytest.mark.asyncio
    async def test_extract_text(self):
        v = VisionModule()
        blocks = await v.extract_text(b"fake_image")
        assert len(blocks) >= 1
        assert blocks[0].confidence > 0.9

    @pytest.mark.asyncio
    async def test_parse_diagram(self):
        v = VisionModule()
        diagram = await v.parse_diagram(b"fake_diagram")
        assert diagram.diagram_type == "flowchart"
        assert len(diagram.nodes) >= 1
