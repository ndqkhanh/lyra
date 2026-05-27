# cmux UI/UX Enhancement Plan for Lyra
## Comprehensive Analysis and Implementation Roadmap

**Document Version:** 1.0  
**Date:** May 26, 2026  
**Target:** Lyra AI Agent System  
**Source Analysis:** cmux (GPL-3.0) - Ghostty-based macOS terminal with vertical tabs and notifications

---

## Executive Summary

This document provides a comprehensive analysis of cmux's UI/UX patterns and proposes a detailed enhancement plan for Lyra, an AI agent system aiming to become state-of-the-art AGI. The analysis covers five critical areas:

1. **Notification System** - Blue rings, tab lighting, OSC sequences, CLI integration
2. **Vertical Tabs** - Sidebar metadata (git, PR, ports, notifications)
3. **In-App Browser** - Scriptable API with accessibility tree snapshots
4. **Session Restore** - Layout, scrollback, browser state, agent resume
5. **Multi-Agent UI** - Native splits for teammates with metadata

### Key Findings

cmux demonstrates production-grade patterns for:
- **Non-intrusive notifications** with visual indicators (blue rings, tab badges)
- **Rich workspace metadata** (git branch, PR status, ports, latest notification)
- **Scriptable browser automation** via agent-browser port (WKWebView)
- **Comprehensive session persistence** with agent-aware resume
- **Multi-agent coordination** through Claude Code Teams integration

### GPL-3.0 Compliance Strategy

cmux is licensed under GPL-3.0-or-later. This plan distinguishes:
- **Conceptual patterns** (architecture, UX flows) - can be learned from
- **Implementation details** (specific code) - requires GPL compliance if copied
- **Alternative implementations** - achieve similar UX without direct copying

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [cmux UI/UX Analysis](#cmux-uiux-analysis)
3. [GPL-3.0 Compliance Strategy](#gpl-30-compliance-strategy)
4. [Notification System Design](#notification-system-design)
5. [Vertical Tabs Architecture](#vertical-tabs-architecture)
6. [In-App Browser Integration](#in-app-browser-integration)
7. [Session Restore System](#session-restore-system)
8. [Multi-Agent UI Patterns](#multi-agent-ui-patterns)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Code Examples](#code-examples)
11. [Architecture Diagrams](#architecture-diagrams)

---

## 1. cmux UI/UX Analysis

### 1.1 Core Architecture

cmux is a native macOS terminal application built with:
- **Swift/AppKit** - Native macOS UI framework
- **libghostty** - GPU-accelerated terminal rendering (Zig-based)
- **Bonsplit** - Custom split pane management
- **WKWebView** - In-app browser with scriptable API

**Key Design Principles:**
1. **Non-intrusive notifications** - Visual indicators without stealing focus
2. **Rich contextual metadata** - Git, PR, ports, notifications per workspace
3. **Scriptable everything** - CLI and socket API for automation
4. **Agent-first design** - Built for AI coding agents (Claude Code, Codex, etc.)

### 1.2 Notification System Architecture

#### Visual Indicators
- **Blue rings** around panes when agents need attention
- **Tab lighting** in sidebar for workspaces with unread notifications
- **Notification panel** (Cmd+I) with unread tracking
- **Dock badge** showing unread count

#### Terminal Sequences
cmux supports OSC (Operating System Command) sequences:
- **OSC 9** - iTerm2-compatible notifications
- **OSC 99** - Custom notification protocol
- **OSC 777** - Extended notification with metadata

#### CLI Integration
```bash
cmux notify --title "Build Complete" --body "Tests passed"
cmux notify --workspace workspace:1 --surface surface:2 --title "Agent Ready"
```

#### Notification Store Architecture

**Key Components:**
1. `TerminalNotificationStore` - @MainActor observable store
2. `TerminalNotification` - Immutable notification model
3. `NotificationIndexes` - Fast lookup structures
4. `UNUserNotificationCenter` - macOS native notifications

**State Management:**
```swift
@MainActor
final class TerminalNotificationStore: ObservableObject {
    @Published private(set) var notifications: [TerminalNotification] = []
    @Published private(set) var manualUnreadWorkspaceIds: Set<UUID> = []
    @Published private(set) var panelDerivedUnreadWorkspaceIds: Set<UUID> = []
    
    private var indexes = NotificationIndexes()
    
    func addNotification(
        tabId: UUID,
        surfaceId: UUID?,
        title: String,
        subtitle: String,
        body: String
    )
}
```

**Notification Hooks:**
- Composable JSON-based hooks in `cmux.json`
- Filter native banners, sidebar history, sounds, commands
- Project-level and global hooks with trust gates

### 1.3 Vertical Tabs (Sidebar)

#### Metadata Display
Each workspace tab shows:
- **Git branch** - Current branch name with dirty indicator
- **PR status** - Linked PR number and status (open/merged/closed)
- **Working directory** - Current directory path
- **Listening ports** - Active server ports (e.g., :3000, :8080)
- **Latest notification** - Most recent notification text

#### Implementation Details
- **FSEventStream** for git metadata watching
- **Debounced updates** (250ms) to avoid thrashing
- **Lazy evaluation** with snapshot boundaries to prevent re-render loops

// __CONTINUE_HERE__
