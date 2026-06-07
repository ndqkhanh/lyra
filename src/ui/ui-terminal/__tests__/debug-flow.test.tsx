import React from 'react';
import { render } from 'ink-testing-library';
import { useUIStore } from '@lyra/ui-core';
import { ConversationView } from '../components/ConversationView';
import { InputArea } from '../components/InputArea';

// Set up store before rendering
useUIStore.getState().createSession('test');
useUIStore.getState().setTransport({
  connect: async () => {},
  disconnect: async () => {},
  sendMessage: async () => {},
  onMessage: () => () => {},
  onStreamChunk: () => () => {},
  onError: () => () => {},
  onStatusChange: () => () => {},
} as any);

function TestApp() {
  return React.createElement(
    'ink-box',
    { flexDirection: 'column' },
    React.createElement(ConversationView, { sessionId: 'test' }),
    React.createElement(InputArea, { sessionId: 'test' })
  );
}

const { lastFrame, stdin } = render(React.createElement(TestApp));

console.log('=== INITIAL FRAME ===');
console.log(lastFrame());

// Simulate typing and submitting
stdin.write('Hello world');
console.log('\n=== AFTER TYPING ===');
console.log(lastFrame());

stdin.write('\r'); // Enter key
console.log('\n=== AFTER SUBMIT ===');
console.log(lastFrame());

// Check store state
const session = useUIStore.getState().getActiveSession();
console.log('\n=== STORE STATE ===');
console.log('Messages:', session?.messages.length);
console.log('Items:', JSON.stringify(session?.messages.map((m: any) => ({role: m.role, content: m.content.slice(0, 50)}))));

const items = useUIStore.getState().getRenderItems('test');
console.log('Render items:', items.length);
items.forEach((i: any) => console.log('  -', i.kind, i.content?.slice(0, 50)));
