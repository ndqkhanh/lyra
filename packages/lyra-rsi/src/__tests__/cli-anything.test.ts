import { CLIAnything } from '../cli-anything';
import { LLMClient } from '../core/llm-client';

describe('CLIAnything', () => {
  let cliAnything: CLIAnything;
  let mockLLM: jest.Mocked<LLMClient>;

  beforeEach(() => {
    mockLLM = {
      generate: jest.fn(),
      generateStructured: jest.fn(),
    } as any;

    cliAnything = new CLIAnything(mockLLM);
  });

  describe('discoverAndInstallTools', () => {
    it('should discover and install tools successfully', async () => {
      mockLLM.generateStructured.mockResolvedValue({
        tools: [
          {
            id: '1',
            name: 'test-tool',
            description: 'Test tool',
            usage: 'test-tool --help',
          },
        ],
      });

      await cliAnything.discoverAndInstallTools();

      expect(mockLLM.generateStructured).toHaveBeenCalled();
    });

    it('should handle errors gracefully', async () => {
      mockLLM.generateStructured.mockRejectedValue(new Error('API error'));

      await expect(cliAnything.discoverAndInstallTools()).resolves.not.toThrow();
    });
  });

  describe('getInstalledTools', () => {
    it('should return installed tools', () => {
      const tools = cliAnything.getInstalledTools();
      expect(Array.isArray(tools)).toBe(true);
    });
  });
});
