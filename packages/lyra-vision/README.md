# Lyra Vision - Multi-Modal Agent Foundation

## Overview

Multi-modal vision module for Lyra providing screenshot understanding, image generation, OCR, diagram parsing, and visual QA capabilities.

## Installation

```bash
pip install lyra-vision
```

## Quick Start

```python
from lyra_vision import VisionModule, VisionConfig

# Initialize with default config
module = VisionModule()

# Analyze a screenshot
with open("screenshot.png", "rb") as f:
    image_data = f.read()
state = module.understand_screenshot(image_data, "PNG")
print(f"Dimensions: {state.dimensions}")

# Extract text (OCR)
blocks = module.extract_text(image_data)
for block in blocks:
    print(f"Text: {block.text} (confidence: {block.confidence})")

# Parse a diagram
diagram = module.parse_diagram(image_data)
print(f"Nodes: {diagram.nodes}")

# Answer a question about an image
qa = module.answer_question(image_data, "What is shown?")
print(f"Answer: {qa.answer}")
```

## Features

### 1. Screenshot Understanding
- UI element detection and classification
- Screen state extraction
- Multi-format support (PNG, JPEG, WEBP, SVG, BMP)

### 2. Image Generation
- Text-to-image stub (production: DALL-E, Stable Diffusion)
- Configurable output format

### 3. OCR Text Extraction
- Text block detection with bounding boxes
- Confidence scoring
- Production-ready with Tesseract/vision API

### 4. Diagram Parsing
- Flowchart and diagram structure detection
- Node/edge graph extraction
- Mermaid/DOT structured representation

### 5. Visual QA
- Natural language question answering about images
- Evidence region identification
- Confidence scoring

## Testing

```bash
pytest tests/ -v
```

## Configuration

```python
config = VisionConfig(
    ocr_enabled=True,
    diagram_parsing_enabled=True,
    visual_qa_enabled=True,
    image_generation_enabled=True,
    max_image_size=4096,
    default_format="PNG",
)
module = VisionModule(config=config)
```

## Version

Current version: **0.1.0**

## License

MIT License
