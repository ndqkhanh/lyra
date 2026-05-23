# Lyra UI System

A modern, modular terminal UI system built with React, Ink, and TypeScript.

## Architecture

The Lyra UI system is built on three core packages:

### 📦 Packages

#### `@lyra/ui-core`
Core state management, types, and utilities.

- **State Management**: Zustand + Immer for immutable state
- **Type System**: Comprehensive TypeScript types
- **Utilities**: Formatting, validation, helpers

#### `@lyra/ui-terminal`
Terminal UI components built with Ink.

- **Components**: Message, StatusBar, InputArea, ConversationView
- **Advanced Features**: Streaming indicators, syntax highlighting, collapsible sections
- **Interactions**: Command history, keyboard navigation

#### `@lyra/ui-transport`
WebSocket-based transport layer for real-time communication.

- **Client**: Event-driven transport client
- **Server**: WebSocket server implementation
- **Protocol**: Structured message protocol with streaming support

## Features

### ✨ Core Features

- **Real-time Streaming**: Live response streaming with visual indicators
- **Syntax Highlighting**: Automatic language detection and highlighting
- **Command History**: Navigate previous commands with arrow keys
- **Collapsible Sections**: Expand/collapse long content
- **Status Indicators**: Real-time status updates (idle, thinking, streaming, error)
- **Token Tracking**: Monitor token usage and context window

### 🎨 UI Components

- **Message**: Display user/assistant/system messages with timestamps
- **StatusBar**: Show current status, model, and token usage
- **InputArea**: Text input with history navigation
- **ConversationView**: Scrollable conversation display
- **StreamingIndicator**: Animated streaming indicator
- **SyntaxHighlight**: Code syntax highlighting
- **Collapsible**: Expandable/collapsible content sections

### 🔌 Transport Layer

- **WebSocket**: Real-time bidirectional communication
- **Event-Driven**: EventEmitter-based architecture
- **Message Queue**: Automatic message queuing when disconnected
- **Reconnection**: Automatic reconnection handling
- **Error Recovery**: Graceful error handling and recovery

## Installation

```bash
# Install all packages
npm install

# Build all packages
npm run build

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

## Usage

### Basic Example

```typescript
import { TerminalUI } from '@lyra/ui-terminal'
import { TransportClient } from '@lyra/ui-transport'
import { render } from 'ink'

// Create transport client
const transport = new TransportClient()
await transport.connect()

// Render UI
render(<TerminalUI transport={transport} />)
```

### Custom Configuration

```typescript
import { TerminalUI } from '@lyra/ui-terminal'
import { TransportClient } from '@lyra/ui-transport'

const transport = new TransportClient({
  url: 'ws://localhost:8080',
  reconnect: true,
  reconnectInterval: 5000
})

const ui = (
  <TerminalUI
    transport={transport}
    theme={{
      primary: '#00ff00',
      secondary: '#0088ff',
      error: '#ff0000'
    }}
  />
)
```

## Development

### Project Structure

```
packages/
├── ui-core/           # Core state and types
│   ├── src/
│   │   ├── state/     # Zustand stores
│   │   ├── types/     # TypeScript types
│   │   └── utils/     # Utility functions
│   └── __tests__/     # Unit tests
├── ui-terminal/       # Terminal UI components
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom hooks
│   │   └── items/       # Message item components
│   └── __tests__/       # Component tests
└── ui-transport/      # Transport layer
    ├── src/
    │   ├── client.ts    # Transport client
    │   ├── server.ts    # Transport server
    │   └── protocol.ts  # Message protocol
    └── __tests__/       # Transport tests
```

### Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific package tests
npm test --workspace=@lyra/ui-core
npm test --workspace=@lyra/ui-terminal
npm test --workspace=@lyra/ui-transport
```

### Building

```bash
# Build all packages
npm run build

# Build specific package
npm run build --workspace=@lyra/ui-core

# Watch mode for development
npm run dev --workspace=@lyra/ui-terminal
```

## Testing Strategy

### Unit Tests (80%+ coverage)
- Component rendering
- State management
- Utility functions
- Type validation

### Integration Tests
- Component + Transport integration
- State + UI synchronization
- Event flow testing

### E2E Tests
- Complete user flows
- Real-world scenarios
- Performance testing
- Error recovery

## Performance

- **Immutable State**: Zero unnecessary re-renders
- **Efficient Updates**: Zustand + Immer for optimal performance
- **Lazy Loading**: Components loaded on demand
- **Streaming**: Incremental rendering for large responses

## Architecture Decisions

### Why Zustand + Immer?
- **Zustand**: Minimal boilerplate, excellent TypeScript support
- **Immer**: Immutable updates with mutable syntax
- **Performance**: No unnecessary re-renders

### Why Ink?
- **React-based**: Familiar component model
- **Declarative**: Easy to reason about
- **Flexible**: Full control over terminal rendering

### Why WebSocket?
- **Real-time**: Bidirectional communication
- **Efficient**: Low latency, minimal overhead
- **Standard**: Well-supported protocol

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT
