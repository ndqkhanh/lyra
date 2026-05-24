# Lyra LLM Integration - Complete

Successfully integrated LLM API calls into Lyra's TUI. The TypeScript UI now communicates with Python's LLM providers via a lightweight HTTP server.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Lyra TUI (TypeScript/Ink)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Header     │  │ Conversation │  │  InputArea   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           │                                   │
│                           ▼                                   │
│                  ┌─────────────────┐                         │
│                  │ LocalTransport  │                         │
│                  └─────────────────┘                         │
└────────────────────────│─────────────────────────────────────┘
                         │ HTTP (localhost:3737)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Lyra UI Server (Python)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  HTTP Handler (POST /chat, GET /health)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│                  ┌─────────────────┐                         │
│                  │  LyraClient     │                         │
│                  └─────────────────┘                         │
│                           │                                   │
│                           ▼                                   │
│                  ┌─────────────────┐                         │
│                  │  LLM Factory    │                         │
│                  └─────────────────┘                         │
│                           │                                   │
│          ┌────────────────┼────────────────┐                 │
│          ▼                ▼                ▼                 │
│    ┌─────────┐     ┌──────────┐     ┌─────────┐            │
│    │Anthropic│     │  OpenAI  │     │DeepSeek │            │
│    └─────────┘     └──────────┘     └─────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. UI Server (`packages/lyra-cli/src/lyra_cli/ui_server.py`)

Lightweight HTTP server that bridges TypeScript UI with Python LLM providers:

- **Port**: `localhost:3737`
- **Endpoints**:
  - `POST /chat` - Send message and stream response
  - `GET /health` - Health check
- **Features**:
  - Server-Sent Events (SSE) for streaming
  - Automatic session management
  - Error handling with proper HTTP status codes

### 2. LocalTransport (`packages/ui-transport/src/local.ts`)

TypeScript client that connects to the Python server:

- **Connection**: HTTP fetch API
- **Streaming**: SSE parsing with ReadableStream
- **Events**:
  - `message` - Complete assistant response
  - `stream-chunk` - Streaming chunks
  - `error` - Error handling
  - `status` - Connection status

### 3. TUI Launcher (`packages/lyra-cli/src/lyra_cli/tui_launcher.py`)

Updated to start the HTTP server before launching the UI:

- Starts server as background subprocess
- Automatic cleanup on exit
- Graceful error handling if server fails

## How It Works

### Message Flow

1. **User types message** in InputArea component
2. **InputArea calls** `transport.sendMessage(message)`
3. **LocalTransport sends** HTTP POST to `localhost:3737/chat`
4. **UI Server receives** request and creates ChatRequest
5. **LyraClient processes** request through LLM provider
6. **Provider streams** response back via SSE
7. **LocalTransport parses** SSE events and emits chunks
8. **UI Store updates** with new messages
9. **ConversationView renders** the response

### Streaming

The integration supports real-time streaming:

```typescript
// LocalTransport emits chunks as they arrive
this.emit('stream-chunk', {
  content: data.payload,
  done: false,
})

// Final complete event
this.emit('stream-chunk', {
  content: fullText,
  done: true,
})
```

## Features Implemented

✅ **Full LLM Integration**
- Connects to all Lyra-supported providers (Anthropic, OpenAI, DeepSeek, etc.)
- Automatic provider selection via `llm_factory.py`
- Environment variable configuration

✅ **Streaming Support**
- Real-time response streaming via SSE
- Progressive UI updates as tokens arrive

✅ **Session Management**
- Persistent session IDs
- Conversation history maintained
- Multi-turn conversations

✅ **Error Handling**
- Connection errors displayed in UI
- Provider errors shown as system messages
- Graceful degradation

✅ **Beautiful UI**
- LYRA ASCII art logo
- Responsive separator lines
- Multi-line input (Shift+Enter)
- Vibrant Dracula-inspired colors

## Usage

### Running Lyra

```bash
# From project root
lyra

# Or with specific model
ANTHROPIC_API_KEY=your_key lyra
```

The launcher will:
1. Start the HTTP server on port 3737
2. Launch the TypeScript TUI
3. Connect to the server automatically
4. Clean up on exit

### Sending Messages

1. Type your message in the input box
2. Press **Enter** to send
3. Press **Shift+Enter** for new lines
4. Watch the response stream in real-time

### Keyboard Shortcuts

- **Enter** - Send message
- **Shift+Enter** - New line in input
- **↑/↓** - Navigate history
- **Ctrl+\\** - Cycle display mode
- **Ctrl+C** - Exit

## Configuration

### Provider Selection

Set environment variables to configure your LLM provider:

```bash
# Anthropic (Claude)
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
export OPENAI_API_KEY=sk-...

# DeepSeek
export DEEPSEEK_API_KEY=sk-...

# Auto-select (tries providers in order)
# No configuration needed - uses first available
```

### Server Port

Default port is 3737. To change:

```python
# In ui_server.py
start_server(port=8080)
```

## Testing

### Test Server Standalone

```bash
cd packages/lyra-cli
python -m lyra_cli.ui_server
```

### Test Health Endpoint

```bash
curl http://localhost:3737/health
# {"status": "ok"}
```

### Test Chat Endpoint

```bash
curl -X POST http://localhost:3737/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

## Files Modified

1. **packages/lyra-cli/src/lyra_cli/ui_server.py** (NEW)
   - HTTP server implementation
   - SSE streaming support

2. **packages/ui-transport/src/local.ts**
   - Replaced stub with HTTP client
   - SSE parsing and event emission

3. **packages/lyra-cli/src/lyra_cli/tui_launcher.py**
   - Added server startup logic
   - Automatic cleanup on exit

4. **packages/ui-terminal/src/index.tsx**
   - Added transport event listeners
   - Message and error handling

5. **packages/ui-core/src/theme/symbols.ts**
   - Updated logo to LYRA ASCII art

6. **packages/ui-terminal/src/components/InputArea.tsx**
   - Added Shift+Enter for multi-line input

7. **packages/ui-terminal/src/components/StatusBar.tsx**
   - Single-line responsive layout

## Next Steps

### Potential Enhancements

1. **WebSocket Support**
   - Replace HTTP with WebSocket for lower latency
   - Bidirectional communication

2. **Tool Execution Display**
   - Show tool calls in conversation
   - Collapsible tool output

3. **Agent Status Indicators**
   - Show thinking/composing states
   - Progress indicators

4. **Multi-Session Support**
   - Switch between sessions
   - Session history browser

5. **Settings UI**
   - Model selection in UI
   - Provider configuration
   - Display preferences

## Troubleshooting

### Server Won't Start

```bash
# Check if port 3737 is in use
lsof -i :3737

# Kill existing process
kill -9 <PID>
```

### Connection Errors

- Ensure server is running: `curl http://localhost:3737/health`
- Check firewall settings
- Verify Python dependencies installed

### No Response from LLM

- Check API key is set: `echo $ANTHROPIC_API_KEY`
- Verify provider is configured: `lyra doctor`
- Check server logs for errors

## Success Criteria

✅ Server starts automatically with TUI
✅ UI connects to server on launch
✅ Messages send successfully
✅ Responses stream in real-time
✅ Errors display gracefully
✅ Multi-turn conversations work
✅ All keyboard shortcuts functional
✅ UI is responsive and beautiful

## Conclusion

Lyra now has a fully functional LLM integration! The TypeScript UI communicates seamlessly with Python's powerful LLM provider ecosystem through a lightweight HTTP bridge. Users can chat with any supported LLM provider with a beautiful, responsive terminal interface.
