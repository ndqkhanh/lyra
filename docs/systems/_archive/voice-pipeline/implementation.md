# Voice Pipeline Implementation Guide

**System**: Voice Pipeline  
**Version**: 1.0.0  
**Date**: 2026-06-02  
**Status**: Implementation Guide

---

## Executive Summary

This guide provides step-by-step instructions for implementing and integrating the Voice Pipeline into Lyra. Includes code examples, configuration, deployment strategies, and testing approaches.

---

## Quick Start

### Installation

```bash
# Install core voice packages
cd packages/lyra-voice
pip install -e .

# Install dependencies
pip install faster-whisper torch portaudio sounddevice

# Optional: GPU acceleration
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify installation
python -c "from lyra_voice import VoicePipeline; print('✓ Voice pipeline installed')"
```

### Basic Usage

```python
import asyncio
from lyra_voice import VoicePipeline, VoiceProviderRegistry

async def main():
    # Create pipeline with default providers
    registry = VoiceProviderRegistry()
    pipeline = VoicePipeline(registry)
    
    # Load test audio
    with open("test_audio.wav", "rb") as f:
        audio_data = f.read()
    
    # Process audio
    result = await pipeline.process_audio(audio_data)
    
    print(f"User said: {result.user_text}")
    print(f"Latency: {result.total_latency_ms:.0f}ms")

---

## Provider Configuration

### Configuring STT Providers

#### Whisper (Default)

```python
from lyra_voice.providers import WhisperSTT, STTConfig

# Basic configuration
stt = WhisperSTT()
config = STTConfig(
    language="en",
    model_size="turbo",  # tiny/base/small/medium/large/turbo
    sample_rate=16000,
)

# Transcribe
result = await stt.transcribe(audio_bytes, config)
print(f"Text: {result.text}, Confidence: {result.confidence}")
```

#### Custom STT Provider

```python
from lyra_voice.providers import STTProvider, STTResult

class CustomSTT(STTProvider):
    kind = "custom"
    
    async def transcribe(self, audio: bytes, config: STTConfig | None = None) -> STTResult:
        # Your implementation
        text = await your_stt_engine(audio)
        return STTResult(
            text=text,
            confidence=0.95,
            language="en",
            is_final=True,
        )

# Register custom provider
registry.register_stt("custom", CustomSTT())
```

### Configuring TTS Providers

#### Kokoro (Default)

```python
from lyra_voice.providers import KokoroTTS, TTSConfig

tts = KokoroTTS()
config = TTSConfig(
    voice_id="default",
    language="en",
    speed=1.0,
    pitch=1.0,
    sample_rate=24000,
)

audio = await tts.synthesize("Hello world", config)
```

#### Multiple Voice Profiles

```python
# Create voice profiles
profiles = {
    "assistant": TTSConfig(voice_id="friendly", speed=1.1, emotion="cheerful"),
    "error": TTSConfig(voice_id="serious", speed=0.9, emotion="concerned"),
    "code": TTSConfig(voice_id="technical", speed=1.0, emotion="neutral"),
}

# Use context-appropriate voice
if context == "error":
    audio = await tts.synthesize(message, profiles["error"])
```

### Configuring VAD

```python
from lyra_voice.providers import SileroVAD, VADConfig

vad = SileroVAD()
config = VADConfig(
    threshold=0.5,  # 0.0-1.0, higher = more sensitive
    min_speech_duration_ms=250,
    min_silence_duration_ms=500,
)

segment = await vad.detect(audio_chunk, config)
---

## Integration Patterns

### Pattern 1: Push-to-Talk Mode

```python
import asyncio
from lyra_voice import VoicePipeline
from lyra_audio import AudioCapture

async def push_to_talk_session():
    pipeline = VoicePipeline()
    capture = AudioCapture(sample_rate=16000, channels=1)
    
    print("Hold SPACE to speak, release to send")
    
    while True:
        # Wait for key press
        if keyboard.is_pressed('space'):
            # Start recording
            audio_chunks = []
            while keyboard.is_pressed('space'):
                chunk = await capture.read_chunk(duration_ms=30)
                audio_chunks.append(chunk)
            
            # Process complete recording
            audio = b"".join(audio_chunks)
            result = await pipeline.push_to_talk(audio, agent_handler)
            
            print(f"User: {result.user_text}")
            print(f"Agent: {result.agent_text}")

asyncio.run(push_to_talk_session())
```

### Pattern 2: Wake Word Activation

```python
async def wake_word_session():
    pipeline = VoicePipeline()
    capture = AudioCapture(sample_rate=16000, channels=1)
    
    # Create audio stream
    async def audio_stream():
        while True:
            chunk = await capture.read_chunk(duration_ms=30)
            yield chunk
    
    # Listen for wake word
    async for turn in pipeline.listen_for_wake_word(
        audio_stream(),
        wake_words=("hey lyra", "ok lyra"),
        agent_handler=agent_handler,
    ):
        print(f"Wake word detected!")
        print(f"User: {turn.user_text}")
        print(f"Agent: {turn.agent_text}")
```

### Pattern 3: Streaming with Barge-in

```python
async def streaming_session():
    pipeline = VoicePipeline()
    capture = AudioCapture(sample_rate=16000, channels=1)
    
    # Register barge-in handler
    pipeline.on(PipelineEvent.BARGE_IN, lambda: print("User interrupted!"))
    
    # Stream processing
    async for turn in pipeline.process_stream(
        audio_stream(),
        agent_handler=agent_handler,
    ):
        if turn.was_interrupted:
            print("Turn was interrupted")
        print(f"Completed turn: {turn.turn_id}")
```

### Pattern 4: Integration with LLM Router

```python
from lyra.router import route_request

async def agent_handler(user_text: str) -> str:
    """Integrate with Lyra's LLM router."""
    response = await route_request(
        prompt=user_text,
        context={
            "source": "voice",
            "interaction_mode": "conversational",
        },
    )
    return response.text

---

## Event Handling

### Registering Event Handlers

```python
from lyra_voice import PipelineEvent

# Sync handler
def on_speech_started(event_data):
    print("User started speaking")

# Async handler
async def on_stt_completed(result):
    print(f"Transcription: {result.text}")
    await log_to_database(result)

# Register handlers
pipeline.on(PipelineEvent.SPEECH_STARTED, on_speech_started)
pipeline.on(PipelineEvent.STT_COMPLETED, on_stt_completed)
pipeline.on(PipelineEvent.ERROR, lambda e: print(f"Error: {e}"))
```

### Event-Driven SFX Integration

```python
from lyra_voice.sfx import SFXManager, SFXCategory
from lyra_voice.voice_hooks import VoiceHookManager

# Create SFX manager
sfx = SFXManager(volume=0.7, enabled=True)
sfx.set_pack("minimal")  # or "scifi", "warcraft_peon"

# Integrate with pipeline events
hook_manager = VoiceHookManager(sfx, pipeline)
hook_manager.register_default_mappings()

# Pipeline events now trigger SFX automatically
```

---

## Configuration Files

### YAML Configuration

```yaml
# voice_config.yaml
pipeline:
  interaction_mode: push_to_talk
  enable_barge_in: true
  enable_streaming: true
  max_turn_duration_s: 30.0

providers:
  stt:
    name: whisper
    config:
      language: en
      model_size: turbo
      sample_rate: 16000
      vad_filter: true
  
  tts:
    name: kokoro
    config:
      voice_id: default
      speed: 1.0
      emotion: neutral
      sample_rate: 24000
  
  vad:
    name: silero
    config:
      threshold: 0.5
      min_speech_duration_ms: 250
  
  turn:
    name: smart
    config:
      language: en
      endpoint_threshold_ms: 500

sfx:
  enabled: true
  volume: 0.7
  pack: minimal
```

### Loading Configuration

```python
import yaml
from lyra_voice import VoiceConfiguration

# Load from file
with open("voice_config.yaml") as f:
    config_data = yaml.safe_load(f)

config = VoiceConfiguration.from_dict(config_data)

---

## Deployment Strategies

### Development Deployment

```python
# Simple local setup for development
from lyra_voice import VoicePipeline

pipeline = VoicePipeline()  # Uses default providers
# Start coding with voice mode immediately
```

### Production Deployment (Single Node)

```bash
# Install production dependencies
pip install -r requirements-voice-prod.txt

# Download models ahead of time
python -m lyra_voice.download_models --stt whisper-turbo --tts kokoro

# Run with systemd service
sudo systemctl start lyra-voice
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY packages/lyra-voice /app/lyra-voice
WORKDIR /app

# Download models at build time (optional)
RUN python -m lyra_voice.download_models --all

EXPOSE 8080
CMD ["python", "-m", "lyra_voice.server"]
```

### Kubernetes Deployment

```yaml
# voice-pipeline-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lyra-voice
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lyra-voice
  template:
    metadata:
      labels:
        app: lyra-voice
    spec:
      containers:
      - name: voice-pipeline
        image: lyra/voice-pipeline:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        env:
        - name: STT_PROVIDER
          value: "whisper"
        - name: TTS_PROVIDER
          value: "kokoro"
```

---

## Testing Strategies

### Unit Testing

```python
import unittest
from lyra_voice import VoicePipeline, VoiceProviderRegistry
from lyra_voice.providers import MockSTT, MockTTS

class TestVoicePipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test registry with mock providers."""
        self.registry = VoiceProviderRegistry()
        self.registry.register_stt("test", MockSTT())
        self.registry.register_tts("test", MockTTS())
        self.pipeline = VoicePipeline(self.registry)
    
    async def test_process_audio_success(self):
        """Test successful audio processing."""
        audio = self.generate_test_audio(duration_s=2.0)
        result = await self.pipeline.process_audio(audio)
        
        self.assertIsNotNone(result)
        self.assertTrue(len(result.user_text) > 0)
        self.assertGreater(result.stt_latency_ms, 0)
    
    async def test_barge_in_handling(self):
        """Test barge-in interruption."""
        barge_in_triggered = False
        
        def on_barge_in():
            nonlocal barge_in_triggered
            barge_in_triggered = True
        
        self.pipeline.on(PipelineEvent.BARGE_IN, on_barge_in)
        
        # Simulate barge-in scenario
        # ... test implementation
        
        self.assertTrue(barge_in_triggered)
```

### Integration Testing

```python
async def test_full_pipeline_integration():
    """Test with real providers (requires models)."""
    pipeline = VoicePipeline()  # Real providers
    
    # Load real audio sample
    audio = load_test_audio("samples/hello_world.wav")
    
    # Process through full pipeline
    result = await pipeline.process_audio(audio)
    
    # Verify transcription
    assert "hello" in result.user_text.lower()
    
    # Verify latency budget
    assert result.total_latency_ms < 1000  # P50 target
```

### Performance Testing

```python
import time
import statistics

async def benchmark_pipeline(num_samples=100):
    """Benchmark pipeline latency."""
    pipeline = VoicePipeline()
    latencies = []
    
    for i in range(num_samples):
        audio = generate_test_audio()
        start = time.time()
        result = await pipeline.process_audio(audio)
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)
    
    print(f"P50: {statistics.median(latencies):.0f}ms")
    print(f"P95: {statistics.quantiles(latencies, n=20)[18]:.0f}ms")
    print(f"P99: {statistics.quantiles(latencies, n=100)[98]:.0f}ms")
```

---

## Error Handling & Recovery

### Handling Provider Failures

```python
from lyra_voice import VoicePipeline, STTError, TTSError

async def resilient_process(audio: bytes):
    pipeline = VoicePipeline()
    
    try:
        result = await pipeline.process_audio(audio)
        return result
    
    except STTError as e:
        print(f"STT failed: {e}")
        # Retry with simpler model
        registry.register_stt("default", WhisperSTT(model_size="tiny"))
        return await pipeline.process_audio(audio)
    
    except TTSError as e:
        print(f"TTS failed: {e}")
        # Return text-only response
        return {"text": result.agent_text, "audio": None}
    
    except Exception as e:
        print(f"Pipeline failed: {e}")
        # Fallback to text mode
        return {"error": str(e), "mode": "text_only"}
```

### Timeout Management

```python
import asyncio

async def process_with_timeout(audio: bytes, timeout_s: float = 5.0):
    """Process audio with timeout."""
    try:
        result = await asyncio.wait_for(
            pipeline.process_audio(audio),
            timeout=timeout_s
        )
        return result
    except asyncio.TimeoutError:
        print("Processing timed out")
        return None
```

---

## Monitoring & Observability

### Pipeline Statistics

```python
# Get pipeline statistics
stats = pipeline.stats

print(f"Total turns: {stats.total_turns}")
print(f"Interruptions: {stats.total_interruptions}")
print(f"Avg STT latency: {stats.avg_stt_latency_ms:.0f}ms")
print(f"Avg TTS latency: {stats.avg_tts_latency_ms:.0f}ms")
print(f"Error count: {stats.error_count}")
```

### Logging Integration

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lyra_voice")

# Log pipeline events
pipeline.on(PipelineEvent.STT_COMPLETED, lambda r: logger.info(
    f"STT: text='{r.text}', confidence={r.confidence:.2f}, latency={r.duration_ms:.0f}ms"
))

pipeline.on(PipelineEvent.ERROR, lambda e: logger.error(f"Pipeline error: {e}"))
```

### Metrics Export (Prometheus)

```python
from prometheus_client import Counter, Histogram

# Define metrics
turns_total = Counter('voice_turns_total', 'Total voice turns processed')
latency_hist = Histogram('voice_latency_seconds', 'Voice pipeline latency')
errors_total = Counter('voice_errors_total', 'Total voice pipeline errors')

# Update metrics on events
pipeline.on(PipelineEvent.STT_COMPLETED, lambda _: turns_total.inc())
pipeline.on(PipelineEvent.ERROR, lambda _: errors_total.inc())

async def monitored_process(audio: bytes):
    with latency_hist.time():
        result = await pipeline.process_audio(audio)
    return result
```

---

## Best Practices

### 1. Model Loading

```python
# ✅ Good: Lazy loading
class OptimizedPipeline:
    def __init__(self):
        self._pipeline = None
    
    async def get_pipeline(self):
        if self._pipeline is None:
            self._pipeline = VoicePipeline()
        return self._pipeline

# ❌ Bad: Eager loading on import
pipeline = VoicePipeline()  # Loads 800MB immediately
```

### 2. Audio Buffer Management

```python
# ✅ Good: Ring buffer with fixed size
buffer = AudioRingBuffer(capacity_seconds=2.0)

# ❌ Bad: Unbounded list
audio_chunks = []  # Can grow indefinitely
```

### 3. Event Handler Cleanup

```python
# ✅ Good: Unregister handlers
handler_id = pipeline.on(PipelineEvent.STT_COMPLETED, my_handler)
# ... later
pipeline.off(PipelineEvent.STT_COMPLETED, handler_id)

# ❌ Bad: Handlers persist forever
pipeline.on(PipelineEvent.STT_COMPLETED, lambda: print("done"))  # Leaks memory
```

### 4. Provider Configuration

```python
# ✅ Good: Immutable config objects
config = STTConfig(language="en", model_size="turbo")
result = await stt.transcribe(audio, config)

# ❌ Bad: Mutable global config
STT_CONFIG["language"] = "en"  # Race conditions in concurrent use
```

---

## Troubleshooting

### Common Issues

#### Issue: STT produces gibberish
**Cause**: Wrong sample rate or corrupted audio  
**Fix**: Verify audio is 16kHz mono PCM
```python
# Check audio format
import wave
with wave.open("audio.wav", "rb") as f:
    print(f"Channels: {f.getnchannels()}")  # Should be 1
    print(f"Sample rate: {f.getframerate()}")  # Should be 16000
```

#### Issue: High latency (>1s)
**Cause**: Model not GPU-accelerated or large model  
**Fix**: Use smaller model or enable GPU
```python
# Check if GPU available
import torch
print(f"GPU available: {torch.cuda.is_available()}")

# Use smaller model
config = STTConfig(model_size="tiny")  # Instead of "turbo"
```

#### Issue: False wake word activations
**Cause**: Wake word threshold too low  
**Fix**: Increase sensitivity threshold
```python
wake_config = WakeWordConfig(sensitivity=0.7)  # Higher = less sensitive
```

---

## Code Examples Repository

Complete working examples are available in:
- `/packages/lyra-voice/examples/` - Example scripts
- `/packages/lyra-voice/tests/` - Test cases showing usage patterns

---

## References

- `/packages/lyra-voice/src/lyra_voice/` - Source code
- `/packages/lyra-voice/README.md` - Package documentation
- `/lyra-upgrade/00-architecture/voice-mode.md` - Architecture specification
- `/docs/systems/voice-pipeline/architecture.md` - System architecture
- `/docs/systems/voice-pipeline/system-design.md` - Detailed design

