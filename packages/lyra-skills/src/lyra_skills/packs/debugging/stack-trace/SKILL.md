---
id: stack-trace
name: Stack Trace
description: Decode and interpret native stack traces from crashes or core dumps.
keywords:
  - stack trace
  - core dump
  - segfault
  - native crash
  - addr2line
  - lldb
---

1. Confirm symbols are available (debug info, dSYM, .sym).
2. Resolve addresses to function names and source lines.
3. Walk the call stack from top (crash site) to bottom.
4. Identify the crashing instruction and the register/memory state.
5. Map the crash to source code; explain why the state was invalid.
