# Auto-Spec-Kit Rollout Guide

**Version**: 1.0.0  
**Status**: Ready for Integration  
**Date**: 2026-05-17

## Overview

Auto-Spec-Kit is now fully implemented and ready for integration into Lyra's agent loop. This document outlines the rollout strategy and integration steps.

## Implementation Status

### ✅ Completed Phases

- **Phase 1**: Foundation & Detection System
- **Phase 2**: State Machine & Orchestration
- **Phase 3**: TUI Integration
- **Phase 4**: Templates & Constitution
- **Phase 5**: Testing & Validation
- **Phase 6**: Documentation & Polish
- **Phase 7**: Performance Optimization
- **Phase 8**: Integration & Rollout (this document)

## Feature Flag

Auto-Spec-Kit is controlled by the `LYRA_AUTOSPEC` environment variable:

```bash
export LYRA_AUTOSPEC=on   # Enable (default)
export LYRA_AUTOSPEC=off  # Disable globally
```

## Integration Points

### 1. Agent Loop Integration

Add to `agent_integration.py`:

```python
from lyra_cli.spec_kit.integration import SpecKitIntegration

spec_kit = SpecKitIntegration(llm_client)

# Before normal agent processing:
intercepted, feature_id, error = await spec_kit.intercept_prompt(prompt, session)
if intercepted:
    # Spec-kit handled the prompt
    return
```

### 2. TUI Integration

Add SpecDrawer to main TUI app:

```python
from lyra_cli.tui_v2.widgets.spec_drawer import SpecDrawer

# In app compose:
yield SpecDrawer()
```

## Rollout Strategy

### Week 1: Internal Testing
- Enable for Lyra core team
- Monitor detector accuracy
- Collect feedback on UX

### Week 2: Beta Release
- Enable for early adopters
- Track metrics (false positives, completion rates)
- Iterate on thresholds

### Week 3: General Availability
- Enable by default for all users
- Publish announcement
- Monitor adoption

## Success Metrics

Track these metrics:

- **Detector Accuracy**: >90% true positives, <5% false positives
- **User Engagement**: >70% approval rate on drafted specs
- **Feature Completion**: >80% of flows reach execution
- **Opt-out Rate**: <10% of users disable

## Monitoring

Log all detector verdicts for tuning:

```python
log.info("spec_detector_ran", 
         verdict=verdict.spec_worthy,
         confidence=verdict.confidence,
         latency_ms=verdict.latency_ms)
```

## Known Limitations

1. LLM-assisted classification not yet implemented (placeholder)
2. User approval flow needs TUI event wiring
3. Constitution check phase is pass-through

## Next Steps

1. Wire SpecDrawer events to orchestrator
2. Implement LLM-assisted classification
3. Add telemetry dashboard
4. Create user onboarding flow

## Support

- Documentation: `packages/lyra-cli/README.md` (Auto-Spec-Kit section)
- Tests: `packages/lyra-cli/tests/spec_kit/`
- Issues: GitHub issue tracker
