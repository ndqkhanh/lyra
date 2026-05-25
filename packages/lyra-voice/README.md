# Lyra Voice

Voice interface layer for Lyra — wake word detection, voice commands, VAD, and session management.

## Features

- **Wake Word Detection**: Detect trigger phrases from audio streams
- **Voice Activity Detection (VAD)**: Energy-threshold based speech detection
- **Command Parsing**: Natural language voice command to structured actions
- **Command Routing**: Parse and route commands to appropriate handlers
- **Session Management**: Start, track, and end voice interaction sessions
- **Audio Stream Processing**: Full pipeline (wake word -> VAD -> transcription -> parse -> execute)

## Installation

```bash
pip install lyra-voice
```

## Quick Start

```python
from lyra_voice import VoiceInterface, VoiceConfig

# Initialize voice interface
vi = VoiceInterface()
session = vi.start_session()

# Process audio and get commands
chunks = [...]  # raw PCM audio chunks
commands = vi.process_audio_stream(chunks)

# Parse a command directly
parsed = vi.parse_command("search for quarterly reports")
result = vi.execute_command(parsed)

# End session
vi.end_session()
```

## Testing

```bash
pytest tests/ -v
```

## Status

**Phase**: Development (Plan 8 — Voice/Audio System)
