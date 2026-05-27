# Provider Routing Refactor - Executive Summary

## Problem Statement

Lyra currently uses **multi-provider fallback** where it automatically cascades through providers:
```
claude → deepseek → gemini → openai → bedrock → ollama
```

This creates **unpredictable behavior**:
- User selects `claude-opus-4.7` but gets DeepSeek for coding tasks
- Silent provider switching hides errors
- Mixed provider responses in same session
- Difficult to predict costs and quality

## Proposed Solution

**Single-Provider Model Routing**: When user selects a provider, route ONLY within that provider's model family.

### Example

**User selects Anthropic:**
- Reasoning tasks → `claude-opus-4.7`
- Coding tasks → `claude-sonnet-4.6`
- Quick tasks → `claude-haiku-4.5`

**User selects DeepSeek:**
- Reasoning tasks → `deepseek-v4-pro`
- Coding tasks → `deepseek-v4-flash`
- Quick tasks → `deepseek-chat`

## Key Changes

### 1. Refactor Task Router (`llm_router.py`)
**Before:**
```python
TASK_PROFILES = (
    reasoning: ["claude-opus-4.7", "deepseek-v4-pro", "o3", "gemini-2.5-pro"]
    # Mixes providers! ❌
)
```

**After:**
```python
PROVIDER_FAMILIES = {
    "anthropic": {
        "reasoning": "claude-opus-4.7",
        "coding": "claude-sonnet-4.6",
        "quick": "claude-haiku-4.5"
    },
    "deepseek": {
        "reasoning": "deepseek-v4-pro",
        "coding": "deepseek-v4-flash",
        "quick": "deepseek-chat"
    }
}
```

### 2. Remove Multi-Provider Fallback (`llm_fallback.py`)
- Delete `FallbackExecutor` class
- Remove cross-provider cascade logic
- Surface errors clearly instead of silent switching

### 3. Simplify Auto Mode (`llm_factory.py`)
- Pick ONE provider at session start
- Stick with that provider for entire session
- Store active provider in session context

### 4. Track Active Provider (`session.py`)
```python
class LyraSession:
    active_provider: str  # "anthropic", "deepseek", etc.
    
    def route_for_task(self, prompt: str) -> str:
        # Route within active provider only
        return route_model_for_task(prompt, self.active_provider)
```

## Benefits

### For Users
✅ **Predictable** - Always know which provider you're using
✅ **Cost-aware** - Choose provider based on pricing
✅ **Quality-aware** - Choose provider based on model quality
✅ **Transparent** - Clear errors instead of silent fallbacks

### For Developers
✅ **Simpler** - Remove complex fallback logic
✅ **Testable** - Easier to test single-provider behavior
✅ **Maintainable** - Less code, clearer intent
✅ **Extensible** - Easy to add new providers

## Implementation Phases

### Phase 1: Core Refactor
1. Refactor `llm_router.py` with provider families
2. Update `llm_factory.py` to track active provider
3. Add provider tracking to `session.py`

### Phase 2: Remove Fallback
1. Deprecate `llm_fallback.py`
2. Remove `DEFAULT_FALLBACK_CHAIN` from config
3. Update error handling to surface issues

### Phase 3: Testing
1. Unit tests for provider routing
2. Integration tests for each provider
3. Migration tests for old configs

### Phase 4: Documentation
1. Update README with new behavior
2. Write migration guide
3. Update CLI help text

## Breaking Changes

⚠️ **This is a breaking change** (v6.0.0)

1. **Removed**: `fallback_chain` config option
2. **Removed**: `FallbackExecutor` class
3. **Changed**: Task routing stays within provider

### Migration Path
```python
# Old config
{
  "fallback_chain": ["anthropic", "deepseek", "openai"]
}

# New config
{
  "primary_provider": "anthropic"  # Uses first from old chain
}
```

## Files to Modify

### Core (5 files)
1. `llm_router.py` - Provider-based routing
2. `llm_factory.py` - Simplified auto mode
3. `llm_fallback.py` - Deprecate/delete
4. `config_io.py` - Update schema
5. `interactive/session.py` - Track provider

### Documentation (3 files)
6. `README.md` - Update docs
7. `CHANGELOG.md` - Breaking changes
8. `MIGRATION.md` - User guide

## Timeline

- **Week 1**: Implementation + Testing
- **Week 2**: Documentation + Release

## Open Questions

1. **Keep optional fallback?**
   - Proposal: `lyra --llm anthropic --fallback deepseek`
   - For users who want explicit backup

2. **Handle provider outages?**
   - Proposal: Clear error + suggest alternative
   - Example: "Anthropic unavailable. Try: lyra --llm deepseek"

3. **Remember last provider?**
   - Proposal: Cache in `~/.lyra/cache`
   - Faster startup, consistent experience

## Next Steps

1. **Review this plan** - Get feedback on approach
2. **Approve breaking changes** - Confirm v6.0.0 release
3. **Start Phase 1** - Begin core refactor
4. **Write tests** - Ensure no regressions

## Full Plan

See `PROVIDER_ROUTING_REFACTOR_PLAN.md` for complete details including:
- Detailed code examples
- Test cases
- Migration strategy
- Success metrics

