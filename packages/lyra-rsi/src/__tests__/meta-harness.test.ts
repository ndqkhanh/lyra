import { MetaHarness } from '../meta-harness';
import { LLMClient } from '../core/llm-client';
import { Benchmark } from '../types';

describe('MetaHarness', () => {
  let metaHarness: MetaHarness;
  let mockLLM: jest.Mocked<LLMClient>;
  let mockBenchmark: Benchmark;

  beforeEach(() => {
    mockLLM = {
      generate: jest.fn(),
      generateStructured: jest.fn(),
    } as any;

    metaHarness = new MetaHarness(mockLLM, {
      maxIterations: 3,
      searchDir: './test-data',
    });

    mockBenchmark = {
      id: 'test-benchmark',
      name: 'Test Benchmark',
      tasks: [],
      evaluator: jest.fn().mockReturnValue(0.8),
    };
  });

  describe('optimizeHarness', () => {
    it('should optimize harness successfully', async () => {
      mockLLM.generate.mockResolvedValue('function test() { return true; }');

      await metaHarness.optimizeHarness('reasoning', mockBenchmark);

      expect(mockLLM.generate).toHaveBeenCalled();
    });

    it('should handle errors gracefully', async () => {
      mockLLM.generate.mockRejectedValue(new Error('API error'));

      await expect(
        metaHarness.optimizeHarness('reasoning', mockBenchmark)
      ).resolves.not.toThrow();
    });
  });

  describe('optimizeHarness', () => {
    it('should optimize harness successfully', async () => {
      const mockBenchmark = {
        id: 'test-benchmark',
        name: 'Test Benchmark',
        tasks: [],
        evaluator: jest.fn().mockReturnValue(0.8),
      };

      const result = await metaHarness.optimizeHarness('reasoning', mockBenchmark);
      
      expect(result).toBeDefined();
      expect(result).toHaveProperty('code');
      expect(result).toHaveProperty('score');
      expect(typeof result.score).toBe('number');
    });
  });
});
