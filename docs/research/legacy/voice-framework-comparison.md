# Voice Agent Framework Comparison for Lyra Voice Mode

**Research Date:** 2026-05-30  
**Target:** §4.18 Voice Mode Implementation

## Executive Summary

Three frameworks evaluated for Lyra's real-time voice agent capabilities:
- **Pipecat**: Voice-first framework with extensive service integrations (12.6k ⭐)
- **LiveKit Agents**: WebRTC-native with telephony and multimodal support (10.7k ⭐)
- **TEN Framework**: Multi-language extensible architecture (10.6k ⭐)

**Recommendation:** **Pipecat** for initial implementation, with LiveKit as a strong alternative for WebRTC-heavy deployments.

---

## Framework Comparison

### 1. Pipecat

**Repository:** https://github.com/pipecat-ai/pipecat  
**License:** BSD-2-Clause (permissive, commercial-friendly)  
**Maturity:** 12,553 stars, 2,131 forks, 166 open issues, last push: 2026-05-29

#### Architecture

**Pipeline Structure:**
```python
Pipeline([
    transport.input(),           # Audio input (Daily, LiveKit, Vonage)
    VADProcessor(SileroVAD),     # Voice Activity Detection
    DeepgramSTT(),               # Speech-to-Text
    LLMContextAggregator(),      # Context management
    OpenAILLM(),                 # Language Model
    CartesiaTTS(),               # Text-to-Speech
    transport.output()           # Audio output
])
```

**Key Architectural Features:**
- **Modular processors**: Composable pipeline components
- **Frame-based processing**: Audio/video/text frames flow through pipeline
- **Multi-agent orchestration**: Agents can hand off, fan out in parallel, or run as sidecars
- **Transport abstraction**: WebRTC (Daily, LiveKit, Vonage), WebSocket, FastAPI

**Code Reference:** https://github.com/pipecat-ai/pipecat-examples/blob/main/daily-multi-translation/bot.py

#### Latency & Real-time Capabilities

- **Target latency:** "Typically completing the full round-trip in under one second"
- **Streaming support:** Full streaming for STT, LLM, and TTS
- **VAD integration:** Silero VAD for interruption detection
- **Barge-in handling:** VAD-based interruption detection (implementation details in examples)

**Performance monitoring:**
```python
PipelineWorker(
    enable_metrics=True,
    enable_usage_metrics=True
)
```

#### Multilingual & Vietnamese Support

**Vietnamese Support:** ✅ Available through multiple providers
- **STT:** Deepgram, Azure, Google, AWS support Vietnamese
- **TTS:** Google, Azure, ElevenLabs support Vietnamese voices
- **Multi-translation example:** https://github.com/pipecat-ai/pipecat-examples/tree/main/daily-multi-translation

**Language handling pattern:**
```python
# Parallel translation pipelines
ParallelPipeline(
    [spanish_pipeline],
    [french_pipeline],
    [german_pipeline]  # Vietnamese can be added similarly
)
```

#### Deployment

**Self-hosted:**
```bash
# Local development
python bot.py

# Production deployment to Pipecat Cloud
pipecat cloud deploy
```

**Resource Requirements:**
- Lightweight: Runs on standard Python environments
- Docker support: Available in examples
- Cloud-native: Compatible with any container platform

**Deployment docs:** https://docs.pipecat.ai/pipecat-cloud/introduction

#### Integration with Lyra

**Strengths:**
- Clean provider abstraction matches Lyra's architecture
- Easy to swap STT/LLM/TTS providers
- Extensive service integrations (80+ AI services)
- Python-native (matches Lyra's stack)

**Integration pattern:**
```python
# Lyra provider abstraction maps cleanly
stt = DeepgramSTTService(api_key=lyra_config.stt.api_key)
llm = OpenAILLMService(model=lyra_config.llm.model)
tts = CartesiaTTSService(voice=lyra_config.tts.voice)
```

#### Unique Features

1. **Pipecat Flows**: Structured conversation management
2. **Client SDKs**: JavaScript, React, React Native, Swift, Kotlin, C++, ESP32
3. **Whisker debugging tool**: Real-time pipeline visualization
4. **Audio processing**: VAD, noise reduction (Krisp, Koala, RNNoise)
5. **Multimodal**: Voice, video, images simultaneously
6. **30+ production examples**: https://github.com/pipecat-ai/pipecat-examples

---

### 2. LiveKit Agents

**Repository:** https://github.com/livekit/agents  
**License:** Apache-2.0 (permissive, commercial-friendly)  
**Maturity:** 10,749 stars, 3,177 forks, 561 open issues, last push: 2026-05-29

#### Architecture

**Session-based Structure:**
```python
session = AgentSession(
    vad=silero.VAD.load(),
    stt=inference.STT("deepgram/nova-3", language="multi"),
    llm=inference.LLM("openai/gpt-4.1-mini"),
    tts=inference.TTS("cartesia/sonic-3")
)
```

**Key Architectural Features:**
- **AgentSession**: Container managing user interactions
- **WebRTC-native**: Built on LiveKit's media server infrastructure
- **Agent orchestration**: Built-in load balancing and Kubernetes compatibility
- **Job-based dispatch**: Agents spawn as job subprocesses

**Code Reference:** https://github.com/livekit/agents/blob/main/examples/voice_agents/basic_agent.py

#### Latency & Real-time Capabilities

- **Turn detection:** "State-of-the-art turn detection model for lifelike conversation flow"
- **Semantic turn detection:** Transformer-based models to detect when users finish speaking
- **Interruption handling:** "Reduce interruptions" through advanced turn detection
- **Barge-in:** VAD integration (Silero) for interruption detection

**Turn detection reference:**
```python
from livekit.plugins.turn_detector.multilingual import MultilingualModel

turn_handling=TurnHandlingOptions(
    # VAD and turn detection determine when user is speaking
    # and when agent should respond
)
```

**Docs:** https://docs.livekit.io/agents/build/turns

#### Multilingual & Vietnamese Support

**Vietnamese Support:** ✅ Available through Deepgram Nova-3
```python
stt=inference.STT("deepgram/nova-3", language="multi")
```

**Language handling:**
- Multilingual STT through `language="multi"` parameter
- Provider-dependent language support (Deepgram Nova-3 supports Vietnamese)
- No explicit Vietnamese examples found, but multilingual capability confirmed

#### Deployment

**Development modes:**
```bash
# Development with hot reloading
python myagent.py dev

# Production mode
python myagent.py start

# Local testing
python myagent.py console
```

**Infrastructure:**
- Requires LiveKit server (self-hosted or cloud)
- Environment: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- Built-in orchestration, load balancing, Kubernetes support

**Deployment docs:** https://docs.livekit.io/agents/ops/deployment

#### Integration with Lyra

**Strengths:**
- Clean inference API: `inference.STT()`, `inference.LLM()`, `inference.TTS()`
- WebRTC infrastructure for low-latency streaming
- Production-ready orchestration and scaling
- MCP (Model Context Protocol) support for tool integration

**Integration pattern:**
```python
# Lyra could wrap LiveKit's inference API
session = AgentSession(
    stt=inference.STT(lyra_config.stt.provider),
    llm=inference.LLM(lyra_config.llm.model),
    tts=inference.TTS(lyra_config.tts.provider)
)
```

#### Unique Features

1. **Telephony integration**: Make/receive phone calls
2. **MCP support**: "Native support for MCP. Integrate tools provided by MCP servers with one line of code"
3. **Multi-agent handoff**: Transfer conversations to specialized agents
4. **Video avatars**: Integration with Tavus, Bithuman, LemonSlice
5. **Built-in test framework**: Write tests with judges to validate agent performance
6. **Gemini Live vision**: Full multimodal support including vision
7. **Dynamic tool creation**: Function tools created at runtime

**Examples:** https://github.com/livekit/agents/tree/main/examples/voice_agents

---

### 3. TEN Framework

**Repository:** https://github.com/TEN-framework/TEN-Agent  
**License:** Apache-2.0 with additional restrictions (core framework), standard Apache-2.0 (packages)  
**Maturity:** 10,621 stars, 1,283 forks, 208 open issues, last push: 2026-05-27

#### Architecture

**Extension-based Structure:**
- **Multi-language support**: Python, C/C++, TypeScript, Rust, Go
- **Plugin system**: STT, LLM, TTS extensions configurable via TMAN Designer
- **Extension interoperability**: Mix components written in different languages

**Configuration:**
```
Right-click STT, LLM, TTS extensions → 
Open properties → Enter API keys
```

**TMAN Designer:** localhost:49483

#### Latency & Real-time Capabilities

- **Low-latency focus**: "Low-latency, high-quality real-time assistant"
- **Full-duplex dialogue**: TEN Turn Detection enables full-duplex communication
- **VAD component**: TEN VAD - "Low-latency, lightweight and high-performance streaming voice activity detector"
- **Transport options**: RTC and WebSocket connections

**Specialized components:**
- **TEN VAD**: https://github.com/TEN-framework/TEN-VAD
- **TEN Turn Detection**: https://github.com/TEN-framework/TEN-Turn-Detection

#### Multilingual & Vietnamese Support

**Vietnamese Support:** ⚠️ Unclear
- README available in Vietnamese (README-VN.md)
- Multi-language documentation support
- No explicit Vietnamese voice examples found
- Language support depends on chosen STT/TTS extensions

#### Deployment

**Docker-first:**
```bash
docker compose up -d
docker build -f agents/examples/<example-name>/Dockerfile
```

**Deployment options:**
- Any container-friendly platform (VM with Docker, Fly.io, Render, ECS, Cloud Run)
- Frontend: Vercel or Netlify
- GitHub Codespaces support (no Docker required)

**Docs:** https://theten.ai/docs/ten_framework/getting-started/quick-start

#### Integration with Lyra

**Strengths:**
- Multi-language architecture (if Lyra needs non-Python components)
- Extension-based plugin system
- Full-duplex dialogue capabilities

**Challenges:**
- More complex architecture than Pipecat/LiveKit
- Additional restrictions in core framework license
- Less clear provider abstraction
- Smaller community compared to Pipecat/LiveKit

#### Unique Features

1. **Multi-language runtime**: Write extensions in Python, C/C++, TypeScript, Rust, Go
2. **TMAN Designer**: Visual configuration tool at localhost:49483
3. **Extension marketplace**: Ecosystem of pre-built extensions
4. **Full-duplex dialogue**: Advanced turn detection for natural conversation
5. **116 releases**: Rapid iteration and active development

**Docs:** https://theten.ai/docs

---

## Recommendation Matrix

| Feature | Pipecat | LiveKit Agents | TEN Framework |
|---------|---------|----------------|---------------|
| **Latency** | <1s round-trip | State-of-art turn detection | Low-latency VAD |
| **Vietnamese STT** | ✅ Deepgram, Azure, Google, AWS | ✅ Deepgram Nova-3 multi | ⚠️ Extension-dependent |
| **Vietnamese TTS** | ✅ Google, Azure, ElevenLabs | ⚠️ Provider-dependent | ⚠️ Extension-dependent |
| **License** | BSD-2-Clause ✅ | Apache-2.0 ✅ | Apache-2.0 + restrictions ⚠️ |
| **Self-host** | ✅ Easy | ✅ Requires LiveKit server | ✅ Docker-first |
| **Integration Ease** | ⭐⭐⭐⭐⭐ Clean pipeline | ⭐⭐⭐⭐ Session-based | ⭐⭐⭐ Extension-based |
| **GitHub Stars** | 12,553 | 10,749 | 10,621 |
| **Community** | 2,131 forks, 166 issues | 3,177 forks, 561 issues | 1,283 forks, 208 issues |
| **Last Update** | 2026-05-29 | 2026-05-29 | 2026-05-27 |
| **Python-native** | ✅ | ✅ | ⚠️ Multi-language |
| **Provider Abstraction** | ⭐⭐⭐⭐⭐ 80+ services | ⭐⭐⭐⭐ Inference API | ⭐⭐⭐ Extension system |
| **Barge-in/Interruption** | ✅ VAD-based | ✅ Semantic turn detection | ✅ Full-duplex turn detection |
| **Multimodal** | ✅ Voice, video, images | ✅ Voice, video, vision | ✅ Multi-modal extensions |
| **Telephony** | ⚠️ Via transports | ✅ Native telephony stack | ⚠️ Extension-dependent |
| **Production Examples** | ⭐⭐⭐⭐⭐ 30+ examples | ⭐⭐⭐⭐ 40+ examples | ⭐⭐⭐ Examples available |
| **Deployment Complexity** | ⭐⭐⭐⭐⭐ Simple | ⭐⭐⭐ Requires LiveKit infra | ⭐⭐⭐ Docker-first |
| **MCP Support** | ❌ | ✅ Native | ❌ |

**Legend:**
- ✅ Fully supported
- ⚠️ Partial/unclear support
- ❌ Not supported
- ⭐ Rating (1-5 stars)

---

## Lyra Integration Strategy

### Recommended Approach: Pipecat

**Rationale:**
1. **Best fit for Lyra's architecture**: Clean provider abstraction matches Lyra's existing design
2. **Python-native**: Seamless integration with Lyra's Python codebase
3. **Extensive provider support**: 80+ AI services, easy to swap providers
4. **Vietnamese support**: Confirmed support through multiple STT/TTS providers
5. **Simplest deployment**: No additional infrastructure required
6. **Active community**: Largest star count, active development, 30+ production examples
7. **Permissive license**: BSD-2-Clause allows commercial use without restrictions

### Integration Architecture

```python
# Lyra Voice Mode using Pipecat

from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.audio.vad_processor import VADProcessor

class LyraVoiceAgent:
    def __init__(self, config: LyraConfig):
        # Use Lyra's provider abstraction
        self.stt = self._create_stt(config.stt)
        self.llm = self._create_llm(config.llm)
        self.tts = self._create_tts(config.tts)
        
        # Pipecat components
        self.vad = VADProcessor(vad_analyzer=SileroVADAnalyzer())
        self.context = LLMContext()
        
    def _create_stt(self, stt_config):
        """Map Lyra STT config to Pipecat STT service"""
        if stt_config.provider == "deepgram":
            return DeepgramSTTService(
                api_key=stt_config.api_key,
                language="vi"  # Vietnamese
            )
        elif stt_config.provider == "azure":
            return AzureSTTService(...)
        # ... other providers
        
    def _create_llm(self, llm_config):
        """Map Lyra LLM config to Pipecat LLM service"""
        if llm_config.provider == "openai":
            return OpenAILLMService(
                api_key=llm_config.api_key,
                model=llm_config.model
            )
        # ... other providers
        
    def _create_tts(self, tts_config):
        """Map Lyra TTS config to Pipecat TTS service"""
        if tts_config.provider == "elevenlabs":
            return ElevenLabsTTSService(
                api_key=tts_config.api_key,
                voice_id=tts_config.voice_id
            )
        # ... other providers
        
    async def create_pipeline(self, transport):
        """Create Pipecat pipeline with Lyra providers"""
        return Pipeline([
            transport.input(),
            self.vad,
            self.stt,
            LLMContextAggregator(self.context),
            self.llm,
            self.tts,
            transport.output()
        ])
```

### Implementation Phases

**Phase 1: Core Integration (Week 1-2)**
- Integrate Pipecat as dependency
- Map Lyra's STT/LLM/TTS providers to Pipecat services
- Implement basic voice pipeline
- Add Vietnamese language support

**Phase 2: Advanced Features (Week 3-4)**
- Implement barge-in/interruption handling
- Add multi-agent orchestration
- Integrate with Lyra's personality system
- Add metrics and monitoring

**Phase 3: Production Hardening (Week 5-6)**
- Deploy to Pipecat Cloud or self-hosted
- Add error handling and fallbacks
- Performance optimization
- Load testing and scaling

### Alternative: LiveKit Agents

**When to choose LiveKit:**
- Need native telephony integration
- Require WebRTC infrastructure
- Want built-in load balancing and Kubernetes support
- Need MCP (Model Context Protocol) support
- Building video avatar features

**Trade-offs:**
- Requires LiveKit server infrastructure
- More complex deployment
- Larger operational footprint

### Not Recommended: TEN Framework

**Reasons:**
- License restrictions in core framework
- More complex multi-language architecture
- Less clear Vietnamese support
- Smaller community and fewer examples
- Overkill for Lyra's Python-centric architecture

**When TEN might be suitable:**
- Need to integrate non-Python components (C++, Rust, Go)
- Require full-duplex dialogue with advanced turn detection
- Building multi-language extension ecosystem

---

## Next Steps

1. **Prototype with Pipecat** (1-2 days)
   - Install Pipecat: `pip install pipecat-ai`
   - Build basic voice pipeline with Vietnamese STT/TTS
   - Test latency and quality

2. **Provider Testing** (2-3 days)
   - Test Deepgram Vietnamese STT accuracy
   - Test ElevenLabs/Azure Vietnamese TTS quality
   - Benchmark latency for each provider combination

3. **Integration Design** (2-3 days)
   - Design Lyra-Pipecat adapter layer
   - Map Lyra's provider abstraction to Pipecat services
   - Plan personality system integration

4. **Implementation** (2-3 weeks)
   - Follow 3-phase implementation plan above
   - Iterate based on testing feedback

---

## References

### Pipecat
- **GitHub:** https://github.com/pipecat-ai/pipecat
- **Docs:** https://docs.pipecat.ai
- **Examples:** https://github.com/pipecat-ai/pipecat-examples
- **Multi-translation example:** https://github.com/pipecat-ai/pipecat-examples/tree/main/daily-multi-translation

### LiveKit Agents
- **GitHub:** https://github.com/livekit/agents
- **Docs:** https://docs.livekit.io/agents
- **Examples:** https://github.com/livekit/agents/tree/main/examples/voice_agents
- **Basic agent:** https://github.com/livekit/agents/blob/main/examples/voice_agents/basic_agent.py

### TEN Framework
- **GitHub:** https://github.com/TEN-framework/TEN-Agent
- **Docs:** https://theten.ai/docs
- **Quick start:** https://theten.ai/docs/ten_framework/getting-started/quick-start

### Provider Documentation
- **Deepgram Nova-3:** https://developers.deepgram.com/docs/nova-3
- **ElevenLabs:** https://elevenlabs.io/docs
- **Azure Speech:** https://learn.microsoft.com/en-us/azure/ai-services/speech-service/
- **Cartesia:** https://docs.cartesia.ai

---

**Research completed:** 2026-05-30  
**Researcher:** Claude Opus 4.8 (general-purpose agent)  
**Status:** Ready for implementation decision
