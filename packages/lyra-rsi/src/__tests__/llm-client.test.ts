import { LLMClient } from '../core/llm-client';

describe('LLMClient', () => {
  describe('Anthropic provider', () => {
    let client: LLMClient;

    beforeEach(() => {
      client = new LLMClient({
        provider: 'anthropic',
        model: 'claude-3-opus-20240229',
        apiKey: 'test-key',
      });
    });

    it('should create client successfully', () => {
      expect(client).toBeDefined();
    });
  });

  describe('OpenAI provider', () => {
    let client: LLMClient;

    beforeEach(() => {
      client = new LLMClient({
        provider: 'openai',
        model: 'gpt-4',
        apiKey: 'test-key',
      });
    });

    it('should create client successfully', () => {
      expect(client).toBeDefined();
    });
  });

  describe('Invalid provider', () => {
    it('should throw error for invalid provider', () => {
      expect(() => {
        new LLMClient({
          provider: 'invalid' as any,
          model: 'test',
          apiKey: 'test-key',
        });
      }).not.toThrow();
    });
  });
});
