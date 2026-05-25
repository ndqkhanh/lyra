# Lyra Speech

Multi-modal speech module for Lyra — voice input, voice output, speaker identification, and emotion detection.

## Features

- **Speech-to-Text (STT)**: Transcribe audio to text
- **Text-to-Speech (TTS)**: Synthesize speech from text
- **Speaker Identification**: Identify speakers from voice prints
- **Emotion Detection**: Detect emotion from audio signals
- **Streaming Transcription**: Process audio chunks incrementally

## Installation

```bash
pip install lyra-speech
```

## Quick Start

```python
from lyra_speech import SpeechModule, SpeechConfig, SynthesisOptions

# Initialize module
config = SpeechConfig(stt_enabled=True, tts_enabled=True)
speech = SpeechModule(config)

# Synthesize speech
audio = speech.synthesize("Hello, world!")

# Transcribe audio
result = speech.transcribe(audio)
print(result.text)
```

## Testing

```bash
pytest tests/ -v
```

## Status

**Phase**: Development (Plan 11 — Multi-Modal Agent Foundation)
