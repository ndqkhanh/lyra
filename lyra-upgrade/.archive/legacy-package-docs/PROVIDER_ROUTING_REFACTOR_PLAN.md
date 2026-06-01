# Provider Routing Refactor Plan

## Current Architecture Analysis

### Multi-Provider Fallback Chain (Current)
```
auto mode cascade:
1. DeepSeek (if DEEPSEEK_API_KEY)
2. Anthropic (if ANTHROPIC_API_KEY)
3. OpenAI (if OPENAI_API_KEY)
4. Gemini (if GEMINI_API_KEY)
5. xAI, Groq, Cerebras, Mistral, Qwen, OpenRouter (via preset registry)
6. Ollama (local)
```

**Files Involved:**
- `llm_factory.py` (lines 746-843) - Auto cascade logic
- `llm_fallback.py` - FallbackExecutor class
- `llm_router.py` - Task-based model routing
- `config_io.py` - DEFAULT_FALLBACK_CHAIN config

### Task-Based Model Routing (Current)
```python
TASK_PROFILES = (
    reasoning: ["claude-opus-4.7", "deepseek-v4-pro", "o3", "gemini-2.5-pro-preview"]
    coding: ["claude-sonnet-4.6", "deepseek-v4-flash", "gpt-4o", "codestral-latest"]
    quick: ["claude-haiku-4.5", "deepseek-chat", "gpt-3.5-turbo", "gemini-2.5-flash"]
    creative: ["claude-opus-4.7", "gpt-4o", "gemini-2.5-pro-preview", "qwen-3.7-max"]
    planning: ["claude-opus-4.7", "deepseek-v4-pro", "o3", "gemini-2.5-pro-preview"]
)
```

**Problem**: Task profiles mix models from different providers!

---

## Proposed Architecture: Single-Provider Model Routing

### Design Principle
**When user selects a model, only route within that provider's model family.**

### Provider Model Families

```python
PROVIDER_MODEL_FAMILIES = {
    "anthropic": {
        "reasoning": "claude-opus-4.7",
        "coding": "claude-sonnet-4.6", 
        "quick": "claude-haiku-4.5",
        "creative": "claude-opus-4.7",
        "planning": "claude-opus-4.7"
    },
    "deepseek": {
        "reasoning": "deepseek-v4-pro",
        "coding": "deepseek-v4-flash",
        "quick": "deepseek-chat",
        "creative": "deepseek-v4-pro",
        "planning": "deepseek-v4-pro"
    },
    "openai": {
        "reasoning": "o3",
        "coding": "gpt-4o",
        "quick": "gpt-3.5-turbo",
        "creative": "gpt-4o",
        "planning": "o3"
    },
    "gemini": {
        "reasoning": "gemini-2.5-pro-preview",
        "coding": "gemini-2.5-pro-preview",
        "quick": "gemini-2.5-flash",
        "creative": "gemini-2.5-pro-preview",
        "planning": "gemini-2.5-pro-preview"
    }
}
```

### User Experience

**Before (Multi-Provider Fallback):**
```bash
$ lyra --llm auto
# Uses: DeepSeek → Anthropic → OpenAI → Gemini → ...
# Task routing mixes providers: opus for reasoning, deepseek for coding

$ lyra
User: "Explain quantum computing"
# Could use claude-opus-4.7 OR deepseek-v4-pro (whichever is first in cascade)
```

**After (Single-Provider Routing):**
```bash
$ lyra --llm anthropic
# Uses: ONLY Anthropic models
# Task routing: opus (reasoning), sonnet (coding), haiku (quick)

$ lyra --llm deepseek
# Uses: ONLY DeepSeek models
# Task routing: v4-pro (reasoning), v4-flash (coding), chat (quick)

$ lyra --llm auto
# Picks ONE provider based on availability
# Then routes within that provider's family
```

---

## Implementation Plan

### Phase 1: Refactor Task Router (llm_router.py)

**Current:**
```python
TASK_PROFILES = (
    TaskProfile(
        name="reasoning",
        models=("claude-opus-4.7", "deepseek-v4-pro", "o3", "gemini-2.5-pro-preview"),
    ),
    # ...
)
```

**New:**
```python
@dataclass(frozen=True)
class ProviderModelFamily:
    provider: str
    reasoning: str
    coding: str
    quick: str
    creative: str
    planning: str

PROVIDER_FAMILIES = {
    "anthropic": ProviderModelFamily(
        provider="anthropic",
        reasoning="claude-opus-4.7",
        coding="claude-sonnet-4.6",
        quick="claude-haiku-4.5",
        creative="claude-opus-4.7",
        planning="claude-opus-4.7"
    ),
    "deepseek": ProviderModelFamily(
        provider="deepseek",
        reasoning="deepseek-v4-pro",
        coding="deepseek-v4-flash",
        quick="deepseek-chat",
        creative="deepseek-v4-pro",
        planning="deepseek-v4-pro"
    ),
    # ... other providers
}

def route_model_for_task(prompt: str, provider: str) -> str:
    """Route to appropriate model within provider's family."""
    task_type = detect_task_type(prompt)  # returns "reasoning", "coding", etc.
    family = PROVIDER_FAMILIES.get(provider)
    if not family:
        return None  # Use provider's default
    return getattr(family, task_type)
```

---

### Phase 2: Remove Multi-Provider Fallback (llm_fallback.py)

**Action**: Delete or deprecate `FallbackExecutor` class

**Rationale**: 
- Cross-provider fallback creates unpredictable behavior
- Users should explicitly choose their provider
- Errors should surface clearly, not silently switch providers

**Migration Path**:
```python
# OLD: Silent fallback across providers
executor = FallbackExecutor(chain=["anthropic", "deepseek", "openai"])
result = executor.execute(messages)

# NEW: Explicit provider with clear errors
provider = build_llm("anthropic")
try:
    result = provider.generate(messages)
except ProviderError as e:
    # Surface error to user, don't silently switch
    raise
```

---

### Phase 3: Simplify Auto Mode (llm_factory.py)

**Current Auto Cascade** (lines 746-843):
```python
# Try DeepSeek
if deepseek_preset.configured():
    return deepseek_preset.build()

# Try Anthropic
if _anthropic_available():
    return AnthropicLLM()

# Try OpenAI, Gemini, xAI, Groq, etc.
for p in configured_presets():
    return p.build()
```

**New Auto Mode**:
```python
def build_llm_auto() -> tuple[LLMProvider, str]:
    """Pick ONE provider, return (provider, provider_key)."""
    
    # Priority order (same as before)
    if deepseek_preset.configured():
        return deepseek_preset.build(), "deepseek"
    
    if _anthropic_available():
        return AnthropicLLM(), "anthropic"
    
    for p in configured_presets():
        return p.build(), p.name
    
    raise NoProviderConfigured()

# Store selected provider for session
def build_llm(kind: str) -> LLMProvider:
    if kind == "auto":
        provider, provider_key = build_llm_auto()
        # Store provider_key in session context
        os.environ["LYRA_ACTIVE_PROVIDER"] = provider_key
        return provider
    else:
        # Explicit provider
        os.environ["LYRA_ACTIVE_PROVIDER"] = kind
        return build_explicit_provider(kind)
```

---

### Phase 4: Update Session to Track Active Provider

**File**: `interactive/session.py`

**Add**:
```python
class LyraSession:
    def __init__(self):
        self.active_provider: str | None = None
        self.provider_llm: LLMProvider | None = None
    
    def initialize_provider(self, kind: str):
        """Initialize provider and store for session."""
        self.provider_llm = build_llm(kind)
        self.active_provider = os.environ.get("LYRA_ACTIVE_PROVIDER", kind)
    
    def route_for_task(self, prompt: str) -> str:
        """Get appropriate model for task within active provider."""
        if not self.active_provider:
            return None
        return route_model_for_task(prompt, self.active_provider)
```

---

### Phase 5: Update Config Schema

**File**: `config_io.py`

**Remove**:
```python
fallback_chain: list[str] = field(default_factory=lambda: list(DEFAULT_FALLBACK_CHAIN))
```

**Add**:
```python
primary_provider: str = "auto"  # User's preferred provider
enable_task_routing: bool = True  # Enable smart model routing within provider
```

---

## Migration Strategy

### Breaking Changes
1. **Remove**: `fallback_chain` config option
2. **Remove**: `FallbackExecutor` class
3. **Change**: Task profiles no longer mix providers

### Backward Compatibility
```python
# If user has old config with fallback_chain
if "fallback_chain" in config:
    # Use first provider in chain as primary_provider
    config.primary_provider = config.fallback_chain[0]
    # Warn user
    logger.warning(
        "fallback_chain is deprecated. Using first provider (%s) as primary. "
        "Update config with: lyra config set primary_provider %s",
        config.primary_provider, config.primary_provider
    )
```

---

## Testing Plan

### Test Cases

1. **Single Provider Routing**
   ```python
   # User selects Anthropic
   session = LyraSession(provider="anthropic")
   
   # Reasoning task → opus
   assert session.route("Explain quantum") == "claude-opus-4.7"
   
   # Coding task → sonnet
   assert session.route("Write a function") == "claude-sonnet-4.6"
   
   # Quick task → haiku
   assert session.route("What is 2+2") == "claude-haiku-4.5"
   ```

2. **No Cross-Provider Fallback**
   ```python
   # Anthropic fails → should raise, not switch to DeepSeek
   session = LyraSession(provider="anthropic")
   with pytest.raises(ProviderError):
       session.generate("test")
   ```

3. **Auto Mode Picks One Provider**
   ```python
   # Auto mode should pick ONE provider and stick with it
   session = LyraSession(provider="auto")
   provider1 = session.active_provider
   
   # Multiple requests should use same provider
   session.generate("task 1")
   session.generate("task 2")
   assert session.active_provider == provider1
   ```

---

## Files to Modify

### Core Changes
1. ✅ `llm_router.py` - Refactor to provider-based routing
2. ✅ `llm_factory.py` - Simplify auto mode, remove cascade
3. ✅ `llm_fallback.py` - Deprecate or delete
4. ✅ `config_io.py` - Update config schema
5. ✅ `interactive/session.py` - Track active provider

### Documentation
6. ✅ `README.md` - Update provider selection docs
7. ✅ `CHANGELOG.md` - Document breaking changes
8. ✅ Migration guide for users

---

## Benefits

### For Users
1. **Predictable**: Always know which provider you're using
2. **Cost-aware**: Choose provider based on pricing
3. **Quality-aware**: Choose provider based on model quality
4. **Transparent**: Clear errors instead of silent fallbacks

### For Developers
1. **Simpler**: Remove complex fallback logic
2. **Testable**: Easier to test single-provider behavior
3. **Maintainable**: Less code, clearer intent
4. **Extensible**: Easy to add new providers

---

## Rollout Plan

### Phase 1: Implement (Week 1)
- Refactor llm_router.py
- Update llm_factory.py
- Add provider tracking to session

### Phase 2: Test (Week 1)
- Unit tests for new routing
- Integration tests for each provider
- Migration tests for old configs

### Phase 3: Document (Week 1)
- Update README
- Write migration guide
- Update CLI help text

### Phase 4: Release (Week 2)
- Release as v6.0.0 (breaking change)
- Announce in changelog
- Provide migration script

---

## Open Questions

1. **Should we keep a "fallback" option for users who want it?**
   - Proposal: Add `--fallback` flag for explicit fallback
   - Example: `lyra --llm anthropic --fallback deepseek`

2. **How to handle provider outages?**
   - Proposal: Surface clear error, suggest alternative
   - Example: "Anthropic API unavailable. Try: lyra --llm deepseek"

3. **Should auto mode remember last successful provider?**
   - Proposal: Cache last working provider in ~/.lyra/cache
   - Benefit: Faster startup, consistent experience

---

## Success Metrics

- ✅ Zero cross-provider fallbacks in logs
- ✅ 100% of task routes stay within provider
- ✅ Clear error messages when provider fails
- ✅ User can predict which model will be used
- ✅ Config migration succeeds for all users

