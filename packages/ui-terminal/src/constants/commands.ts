export interface Command {
  name: string
  description: string
  category: string
}

export const COMMANDS: Command[] = [
  // Conversation & Navigation
  { name: '/help', description: 'List all commands', category: 'Conversation & Navigation' },
  { name: '/exit', description: 'Exit REPL', category: 'Conversation & Navigation' },
  { name: '/quit', description: 'Exit REPL (alias)', category: 'Conversation & Navigation' },
  { name: '/clear', description: 'Clear screen', category: 'Conversation & Navigation' },
  { name: '/new', description: 'Start fresh chat (Ctrl-N)', category: 'Conversation & Navigation' },
  { name: '/history', description: 'Show recent inputs', category: 'Conversation & Navigation' },
  { name: '/compact', description: 'Compress chat history', category: 'Conversation & Navigation' },
  { name: '/search', description: 'Search sessions (FTS5)', category: 'Conversation & Navigation' },
  { name: '/replay', description: 'Replay past sessions', category: 'Conversation & Navigation' },

  // Models & Configuration
  { name: '/model', description: 'Show current model + fast/smart slots', category: 'Models & Configuration' },
  { name: '/models', description: 'List all available models', category: 'Models & Configuration' },
  { name: '/status', description: 'Show model, mode, budget, tools', category: 'Models & Configuration' },
  { name: '/budget', description: 'Show/set cost cap', category: 'Models & Configuration' },
  { name: '/stream', description: 'Toggle streaming output', category: 'Models & Configuration' },
  { name: '/config', description: 'Configuration management', category: 'Models & Configuration' },
  { name: '/credentials', description: 'Set API credentials', category: 'Models & Configuration' },

  // Planning & Execution
  { name: '/plan', description: 'Generate implementation plan', category: 'Planning & Execution' },
  { name: '/approve', description: 'Approve plan and execute', category: 'Planning & Execution' },
  { name: '/reject', description: 'Reject current plan', category: 'Planning & Execution' },
  { name: '/spawn', description: 'Fork subagent in worktree', category: 'Planning & Execution' },
  { name: '/verify', description: 'Replay verifier', category: 'Planning & Execution' },
  { name: '/mode', description: 'Switch mode (agent|plan|debug|ask)', category: 'Planning & Execution' },

  // Code Review & Diff
  { name: '/review', description: 'Post-turn diff review', category: 'Code Review & Diff' },
  { name: '/diff', description: 'Show working tree diff', category: 'Code Review & Diff' },
  { name: '/blame', description: 'Git blame annotations', category: 'Code Review & Diff' },
  { name: '/map', description: 'ASCII tree of repo', category: 'Code Review & Diff' },
  { name: '/security-review', description: 'OWASP security review', category: 'Code Review & Diff' },
  { name: '/simplify', description: '3-pass review (quality/reuse/efficiency)', category: 'Code Review & Diff' },

  // Tools & Skills
  { name: '/tools', description: 'List registered tools', category: 'Tools & Skills' },
  { name: '/skills', description: 'Show injected SKILL.md files', category: 'Tools & Skills' },
  { name: '/memory', description: 'Show memory window', category: 'Tools & Skills' },
  { name: '/mcp', description: 'Manage MCP servers', category: 'Tools & Skills' },

  // Sessions & Handoff
  { name: '/session', description: 'Session management', category: 'Sessions & Handoff' },
  { name: '/handoff', description: 'Generate PR summary', category: 'Sessions & Handoff' },
  { name: '/retro', description: 'Session retrospective', category: 'Sessions & Handoff' },
  { name: '/export', description: 'Export transcript', category: 'Sessions & Handoff' },
  { name: '/copy', description: 'Copy last response to clipboard', category: 'Sessions & Handoff' },
  { name: '/resume', description: 'Resume saved session', category: 'Sessions & Handoff' },
  { name: '/fork', description: 'Branch session', category: 'Sessions & Handoff' },
  { name: '/rename', description: 'Rename session', category: 'Sessions & Handoff' },

  // Teams & Agents
  { name: '/team', description: 'Multi-agent team orchestration', category: 'Teams & Agents' },
  { name: '/agents', description: 'Live subagent registry', category: 'Teams & Agents' },
  { name: '/agentteams', description: 'Anthropic Agent Teams', category: 'Teams & Agents' },

  // Research & Investigation
  { name: '/research', description: 'Deep research pipeline', category: 'Research & Investigation' },
  { name: '/investigate', description: 'Multi-hop investigation', category: 'Research & Investigation' },
  { name: '/deep-research', description: 'Full-depth academic research', category: 'Research & Investigation' },

  // Cron & Scheduling
  { name: '/cron', description: 'Manage scheduled tasks', category: 'Cron & Scheduling' },
  { name: '/schedule', description: 'Schedule recurring prompts', category: 'Cron & Scheduling' },
  { name: '/loop', description: 'Run prompt on interval', category: 'Cron & Scheduling' },

  // Memory & Reflection
  { name: '/reflect', description: 'Reflection on recent work', category: 'Memory & Reflection' },
  { name: '/btw', description: 'Side question (ephemeral)', category: 'Memory & Reflection' },

  // Configuration & Theme
  { name: '/theme', description: 'Change color theme', category: 'Configuration & Theme' },
  { name: '/color', description: 'Set accent color', category: 'Configuration & Theme' },
  { name: '/statusline', description: 'Customize status bar', category: 'Configuration & Theme' },
  { name: '/fast', description: 'Toggle fast mode', category: 'Configuration & Theme' },
  { name: '/focus', description: 'Toggle focus mode', category: 'Configuration & Theme' },
  { name: '/tui', description: 'Switch renderer mode', category: 'Configuration & Theme' },
  { name: '/vim', description: 'Toggle vim editing', category: 'Configuration & Theme' },
  { name: '/sandbox', description: 'Toggle filesystem sandbox', category: 'Configuration & Theme' },
  { name: '/keybindings', description: 'Show keybinding cheatsheet', category: 'Configuration & Theme' },
  { name: '/palette', description: 'Show command palette', category: 'Configuration & Theme' },

  // Observability & Debugging
  { name: '/trace', description: 'Toggle HIR event log', category: 'Observability & Debugging' },
  { name: '/self', description: 'Agent introspection', category: 'Observability & Debugging' },
  { name: '/context', description: 'Context window breakdown', category: 'Observability & Debugging' },
  { name: '/stats', description: 'Session performance metrics', category: 'Observability & Debugging' },
  { name: '/cost', description: 'Cost/token usage', category: 'Observability & Debugging' },
  { name: '/badges', description: 'Command usage stats', category: 'Observability & Debugging' },
  { name: '/debug', description: 'Toggle debug mode', category: 'Observability & Debugging' },
  { name: '/doctor', description: 'Health check', category: 'Observability & Debugging' },
  { name: '/hooks', description: 'View configured hooks', category: 'Observability & Debugging' },
  { name: '/permissions', description: 'Manage tool permissions', category: 'Observability & Debugging' },
  { name: '/usage', description: 'Session cost + usage stats', category: 'Observability & Debugging' },

  // Advanced Features
  { name: '/autopilot', description: 'Supervised autonomy loops', category: 'Advanced Features' },
  { name: '/ultrawork', description: 'Ultra-work orchestration', category: 'Advanced Features' },
  { name: '/ralph', description: 'Loop-until-done execution', category: 'Advanced Features' },
  { name: '/ralplan', description: 'Ralph planning mode', category: 'Advanced Features' },
  { name: '/continue', description: 'Re-feed agent with follow-up', category: 'Advanced Features' },
  { name: '/sharpen', description: 'Rewrite task as verifiable goals', category: 'Advanced Features' },
  { name: '/directive', description: 'Append to HUMAN_DIRECTIVE.md', category: 'Advanced Features' },
  { name: '/contract', description: 'Agent contract budget envelope', category: 'Advanced Features' },
  { name: '/batch', description: 'Multi-unit refactor delegation', category: 'Advanced Features' },
  { name: '/add-dir', description: 'Add working directory', category: 'Advanced Features' },
  { name: '/pr-comments', description: 'Fetch GitHub PR comments', category: 'Advanced Features' },
  { name: '/feedback', description: 'Submit bug report with context', category: 'Advanced Features' },
  { name: '/release-notes', description: 'Show changelog', category: 'Advanced Features' },
  { name: '/logout', description: 'Clear stored credentials', category: 'Advanced Features' },
  { name: '/plugin', description: 'Manage plugins', category: 'Advanced Features' },
  { name: '/reload-plugins', description: 'Reload plugin discovery', category: 'Advanced Features' },
  { name: '/claude-api', description: 'Claude API quick reference', category: 'Advanced Features' },

  // Lyra Unique Features
  { name: '/scaling', description: 'Scaling-laws aggregator', category: 'Lyra Unique' },
  { name: '/coverage', description: 'Verifier coverage index', category: 'Lyra Unique' },
  { name: '/bundle', description: 'Software 3.0 bundle ops', category: 'Lyra Unique' },
  { name: '/meta-evolve', description: 'GEPA meta-evolution', category: 'Lyra Unique' },
  { name: '/commands', description: 'List user commands', category: 'Lyra Unique' },
  { name: '/soul', description: 'Print SOUL.md', category: 'Lyra Unique' },
  { name: '/policy', description: 'Print policy.yaml', category: 'Lyra Unique' },
  { name: '/evals', description: 'Run evals harness', category: 'Lyra Unique' },
  { name: '/auth', description: 'Manage OAuth tokens', category: 'Lyra Unique' },
  { name: '/init', description: 'Scaffold SOUL.md + .lyra/', category: 'Lyra Unique' },
  { name: '/rewind', description: 'Undo most recent turn', category: 'Lyra Unique' },
  { name: '/redo', description: 'Re-apply rewound turn', category: 'Lyra Unique' },
  { name: '/toolsets', description: 'Named tool bundles', category: 'Lyra Unique' },
  { name: '/wiki', description: 'Generate repo wiki', category: 'Lyra Unique' },
  { name: '/voice', description: 'Toggle voice mode', category: 'Lyra Unique' },
  { name: '/split', description: 'Queue task on split_queue', category: 'Lyra Unique' },
  { name: '/pair', description: 'Pair-programming stream', category: 'Lyra Unique' },
  { name: '/recap', description: 'Terse turn summary', category: 'Lyra Unique' },

  // Git Operations
  { name: '/commit', description: 'Stage and commit', category: 'Git Operations' },
  { name: '/pr', description: 'Create pull request', category: 'Git Operations' },
  { name: '/push', description: 'Push to remote', category: 'Git Operations' },
]

/** Returns flat list of command names for autocomplete. */
export function getCommandNames(): string[] {
  return COMMANDS.map(c => c.name.slice(1)) // strip leading '/'
}
