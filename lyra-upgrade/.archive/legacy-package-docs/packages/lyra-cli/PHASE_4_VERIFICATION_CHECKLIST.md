# Phase 4 Verification Checklist

**Status**: Code-level verification complete. Manual testing required.

## Code Verification (Completed)

- ✅ All widget files exist and are syntactically correct
- ✅ Widgets exported in `__init__.py`
- ✅ App integration code is syntactically correct
- ✅ Entry point updated to use tui_v2 by default
- ✅ Documentation updated

## Manual Testing Required

### Widget Integration
- [ ] WelcomeCard displays on launch with correct model/cwd/account
- [ ] WelcomeCard collapses after first input
- [ ] CompactionBanner appears on context compaction events
- [ ] CompactionBanner auto-collapses after 30s
- [ ] CompactionBanner expands/collapses with Ctrl+O
- [ ] TodoPanel shows in sidebar with live task updates
- [ ] TodoPanel displays correct glyphs (◻ pending, ◼ done, ⚠ blocked)
- [ ] BackgroundSwitcher opens with Ctrl+B
- [ ] BackgroundSwitcher shows running background tasks

### Entry Point
- [ ] `lyra` launches tui_v2 by default
- [ ] `lyra --legacy-tui` launches old TUI
- [ ] `lyra --help` shows --legacy-tui flag

### Functional Requirements (24 FRs)
See `ui-specs/` folder for complete FR list. Key FRs to verify:
- [ ] FR-001: Welcome card (collapsible)
- [ ] FR-010: Compaction banner
- [ ] FR-012: Background task switcher
- [ ] FR-015: To-do panel

## Notes

Phase 4 verification is limited to code-level checks. Full manual testing requires:
1. Running `lyra` in a terminal
2. Triggering each widget's display conditions
3. Verifying interactive behavior (keyboard shortcuts, animations, etc.)

**Recommendation**: Deploy to staging environment for manual QA before v1.0.0 release.
