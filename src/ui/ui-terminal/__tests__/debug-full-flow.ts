import { useUIStore } from '@lyra/ui-core';
import { LocalTransport } from '@lyra/ui-transport';

class MockTransport extends LocalTransport {
  async connect(): Promise<void> {}
  
  async sendMessage(content: string, attachments?: any[], model?: string): Promise<void> {
    console.log('sendMessage called with:', content.slice(0, 50));
    setTimeout(() => {
      this.emit('stream-chunk', { content: 'Hello! ', done: false });
    }, 50);
    setTimeout(() => {
      this.emit('stream-chunk', { content: 'How can I help?', done: false });
    }, 100);
    setTimeout(() => {
      this.emit('stream-chunk', { content: '', done: true });
    }, 150);
  }
}

async function test() {
  const transport = new MockTransport();
  useUIStore.getState().setTransport(transport as any);
  useUIStore.getState().createSession('default');
  
  transport.onStreamChunk((chunk: any) => {
    console.log('onStreamChunk:', chunk.done ? 'DONE' : 'DELTA: ' + chunk.content.slice(0, 40));
    if (chunk.done) {
      useUIStore.getState().commitStreamingMessage('default');
    } else {
      useUIStore.getState().updateStreamingMessage('default', chunk.content);
    }
  });
  
  const userContent = 'Deep research about LLM memory';
  
  console.log('1. Adding user message...');
  useUIStore.getState().addMessage('default', {
    id: 'msg-test', role: 'user', content: userContent, timestamp: Date.now()
  });
  console.log('   Msgs:', useUIStore.getState().getActiveSession()?.messages.length);
  console.log('   Items:', useUIStore.getState().getRenderItems('default').length);
  
  console.log('2. Sending via transport...');
  await transport.sendMessage(userContent);
  
  await new Promise(r => setTimeout(r, 80));
  console.log('3. Mid-stream - items:', useUIStore.getState().getRenderItems('default').length);
  console.log('   isStreaming:', useUIStore.getState().getActiveSession()?.isStreaming);
  
  await new Promise(r => setTimeout(r, 100));
  console.log('4. After done - msgs:', useUIStore.getState().getActiveSession()?.messages.length);
  console.log('   isStreaming:', useUIStore.getState().getActiveSession()?.isStreaming);
  const items = useUIStore.getState().getRenderItems('default');
  console.log('   Items:', items.length);
  items.forEach((i: any) => console.log('     -', i.kind, 'committed:', i.committed, i.content?.slice(0, 40)));
  
  console.log('\nPASSED');
  process.exit(0);
}

test().catch(err => { console.error('FAILED:', err); process.exit(1); });
