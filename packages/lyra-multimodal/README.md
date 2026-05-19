# Lyra Multimodal - Phase 6: Voice and Multimodal

## Overview

Phase 6 implements multimodal capabilities including vision analysis, speech-to-text, and text-to-speech.

## Features

### 1. Vision Analyzer (`vision.py`)

Analyze images and screenshots:

```python
from lyra_multimodal import VisionAnalyzer

analyzer = VisionAnalyzer()

# General analysis
result = analyzer.analyze_image("screenshot.png", analysis_type="general")
print(f"Type: {result.image_type.value}")
print(f"Description: {result.description}")

# Security analysis
result = analyzer.analyze_image("screenshot.png", analysis_type="security")
for finding in result.security_findings:
    print(f"⚠️  {finding}")

# UI/UX analysis
result = analyzer.analyze_image("ui.png", analysis_type="ui")
for element in result.ui_elements:
    print(f"🎨 {element}")
for rec in result.recommendations:
    print(f"💡 {rec}")

# Get image info
info = analyzer.get_image_info("image.png")
print(f"Size: {info['width']}x{info['height']}")
print(f"Format: {info['format']}")
```

**Analysis Types**:
- `general` - Basic image classification
- `security` - Security vulnerability detection
- `ui` - UI/UX analysis
- `code` - Code screenshot analysis

**Image Types**:
- Screenshot
- Diagram
- Code
- UI
- Document
- Other

### 2. Voice Interface (`voice.py`)

Speech-to-text and text-to-speech:

```python
from lyra_multimodal import VoiceInterface, VoiceEngine

voice = VoiceInterface(engine=VoiceEngine.WHISPER)

# Speech-to-text
result = voice.transcribe("audio.wav", language="en")
print(f"Text: {result.text}")
print(f"Confidence: {result.confidence:.1%}")
print(f"Duration: {result.duration_seconds}s")

# Text-to-speech
result = voice.synthesize("Hello, Lyra!", voice="default", speed=1.0)
with open("output.mp3", "wb") as f:
    f.write(result.audio_data)

# Voice command recognition
command = voice.recognize_command("command.wav")
if command:
    print(f"Command: {command}")
    
# Get supported languages
languages = voice.get_supported_languages()
print(f"Languages: {', '.join(languages)}")
```

**Voice Engines**:
- `WHISPER` - OpenAI Whisper (default)
- `GOOGLE` - Google Speech
- `AZURE` - Azure Speech

**Voice Commands**:
- `scan` - Start security scan
- `stop` - Stop operation
- `report` - Generate report
- `status` - Show status

## Architecture

```
┌─────────────────────────────────────────┐
│       Vision Analyzer                   │
│  (Image Analysis)                       │
│                                         │
│  Image → Classify → Analyze            │
│  - Security findings                   │
│  - UI elements                         │
│  - Text extraction                     │
│  - Recommendations                     │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Voice Interface                      │
│  (STT/TTS)                              │
│                                         │
│  Audio → Transcribe → Text             │
│  Text → Synthesize → Audio             │
│  - Command recognition                 │
│  - Multi-language support              │
└─────────────────────────────────────────┘
```

## Use Cases

### Security Screenshot Analysis

```python
analyzer = VisionAnalyzer()

# Analyze pentest screenshot
result = analyzer.analyze_image("pentest_results.png", analysis_type="security")

print("Security Findings:")
for finding in result.security_findings:
    print(f"  - {finding}")

print("\nRecommendations:")
for rec in result.recommendations:
    print(f"  - {rec}")
```

### Voice-Controlled Pentesting

```python
voice = VoiceInterface()

# Listen for voice command
command = voice.recognize_command("voice_input.wav")

if command == "scan":
    print("Starting security scan...")
    # Trigger scan
elif command == "report":
    print("Generating report...")
    # Generate report
elif command == "status":
    print("Checking status...")
    # Show status
```

### UI Accessibility Analysis

```python
analyzer = VisionAnalyzer()

result = analyzer.analyze_image("app_ui.png", analysis_type="ui")

print("UI Elements:")
for element in result.ui_elements:
    print(f"  - {element}")

print("\nAccessibility Recommendations:")
for rec in result.recommendations:
    print(f"  - {rec}")
```

## Testing

Run tests:
```bash
cd packages/lyra-multimodal
pip install -e .
pytest tests/ -v
```

Tests: 13 tests covering vision and voice

## Performance

- **Vision Analysis**: <100ms per image
- **Image Encoding**: <50ms
- **Voice Transcription**: Real-time (1x speed)
- **Voice Synthesis**: <500ms for short text

## Next Steps (Phase 7)

- Cyber-specific enhancements
- Red team automation
- Blue team defense
- Threat intelligence integration

## Version

Current version: **0.1.0**

## Changes

- Added `VisionAnalyzer` for image analysis
- Added `VoiceInterface` for STT/TTS
- Security-focused image analysis
- Voice command recognition
- Multi-language support
- Comprehensive tests

## References

- Claude Vision: https://docs.anthropic.com/claude/docs/vision
- Whisper API: https://openai.com/research/whisper
- Lyra Ultra Plan: `.omc/research/LYRA_ULTRA_ENHANCEMENT_PLAN.md`
