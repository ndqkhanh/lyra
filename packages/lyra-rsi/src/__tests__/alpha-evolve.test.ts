import { AlphaEvolve } from '../alpha-evolve';
import { LLMClient } from '../core/llm-client';
import { Benchmark } from '../types';

describe('AlphaEvolve', () => {
  let alphaEvolve: AlphaEvolve;
  let mockLLM: jest.Mocked<LLMClient>;
  let mockBenchmark: Benchmark;

  beforeEach(() => {
    mockLLM = {
      generate: jest.fn(),
      generateStructured: jest.fn(),
    } as any;

    alphaEvolve = new AlphaEvolve(mockLLM, {
      maxGenerations: 2,
      populationSize: 3,
    });

    mockBenchmark = {
      id: 'test-benchmark',
      name: 'Test Benchmark',
      tasks: [],
      evaluator: jest.fn().mockReturnValue(0.8),
    };
  });

  describe('evolveAlgorithm', () => {
    it('should evolve algorithm successfully', async () => {
      mockLLM.generate.mockResolvedValue('function search() { return []; }');
      mockLLM.generateStructured.mockResolvedValue({
        mutations: [
          { type: 'optimization', code: 'function search() { return []; }' },
          { type: 'exploration', code: 'function search() { return []; }' },
        ],
      });

      const result = await alphaEvolve.evolveAlgorithm('Improve search', mockBenchmark);

      expect(result).toBeDefined();
      expect(result.code).toBeDefined();
      expect(mockLLM.generate).toHaveBeenCalled();
    });

    it('should handle errors gracefully', async () => {
      mockLLM.generate.mockRejectedValue(new Error('API error'));

      await expect(
        alphaEvolve.evolveAlgorithm('Improve search', mockBenchmark)
      ).rejects.toThrow();
    });
  });
});
