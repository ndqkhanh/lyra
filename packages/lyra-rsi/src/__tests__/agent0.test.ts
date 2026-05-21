import { Agent0 } from '../agent0';
import { LLMClient } from '../core/llm-client';

describe('Agent0', () => {
  let agent0: Agent0;
  let mockLLM: jest.Mocked<LLMClient>;

  beforeEach(() => {
    mockLLM = {
      generate: jest.fn(),
      generateStructured: jest.fn(),
    } as any;

    agent0 = new Agent0(mockLLM, {
      maxIterations: 3,
      syntheticTaskCount: 5,
    });
  });

  describe('bootstrapFromZero', () => {
    it('should bootstrap from zero data successfully', async () => {
      mockLLM.generateStructured.mockResolvedValue({
        tasks: [
          { id: '1', description: 'Test task', type: 'test' },
        ],
      });

      mockLLM.generate.mockResolvedValue('Test solution');

      await agent0.bootstrapFromZero();

      expect(mockLLM.generateStructured).toHaveBeenCalled();
      expect(mockLLM.generate).toHaveBeenCalled();
    });

    it('should handle errors gracefully', async () => {
      mockLLM.generateStructured.mockRejectedValue(new Error('API error'));

      await expect(agent0.bootstrapFromZero()).resolves.not.toThrow();
    });
  });

  describe('getExperienceCount', () => {
    it('should return initial experience count', () => {
      const count = agent0.getExperienceCount();
      expect(count).toBe(0);
    });
  });
});
