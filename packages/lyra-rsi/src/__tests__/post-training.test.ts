import { PostTraining } from '../post-training';
import { LLMClient } from '../core/llm-client';
import { PerformanceMetrics } from '../types';

describe('PostTraining', () => {
  let postTraining: PostTraining;
  let mockLLM: jest.Mocked<LLMClient>;

  beforeEach(() => {
    mockLLM = {
      generate: jest.fn(),
      generateStructured: jest.fn(),
    } as any;

    postTraining = new PostTraining(mockLLM, {
      computeBudgetPerGeneration: 1000,
    });
  });

  describe('generateSyntheticData', () => {
    it('should generate synthetic data successfully', async () => {
      const mockMetrics: PerformanceMetrics = {
        reasoning: { mathReasoning: 0.7, logicalReasoning: 0.6, commonSense: 0.8 },
        planning: { taskPlanning: 0.7, longHorizon: 0.6, multiStep: 0.7 },
        coding: { humanEval: 0.8, mbpp: 0.7, apps: 0.6 },
        toolUse: { apiUsage: 0.8, composition: 0.7, errorRecovery: 0.6 },
        learning: { fewShot: 0.8, zeroShot: 0.7, transfer: 0.6 },
        creativity: { novelty: 0.7, diversity: 0.8, quality: 0.7 },
      };

      mockLLM.generateStructured.mockResolvedValue({
        examples: [
          { input: 'test input', output: 'test output' },
        ],
        metadata: {
          source: 'synthetic',
          targetWeaknesses: ['reasoning'],
          generatedAt: Date.now(),
        },
      });

      const result = await postTraining.generateSyntheticData(mockMetrics);

      expect(result).toBeDefined();
      expect(result.examples).toBeDefined();
      expect(mockLLM.generateStructured).toHaveBeenCalled();
    });

    it('should handle errors gracefully', async () => {
      const mockMetrics: PerformanceMetrics = {
        reasoning: { mathReasoning: 0.7, logicalReasoning: 0.6, commonSense: 0.8 },
        planning: { taskPlanning: 0.7, longHorizon: 0.6, multiStep: 0.7 },
        coding: { humanEval: 0.8, mbpp: 0.7, apps: 0.6 },
        toolUse: { apiUsage: 0.8, composition: 0.7, errorRecovery: 0.6 },
        learning: { fewShot: 0.8, zeroShot: 0.7, transfer: 0.6 },
        creativity: { novelty: 0.7, diversity: 0.8, quality: 0.7 },
      };

      mockLLM.generateStructured.mockRejectedValue(new Error('API error'));

      await expect(postTraining.generateSyntheticData(mockMetrics)).rejects.toThrow();
    });
  });

  describe('selectTrainingStrategy', () => {
    it('should select training strategy successfully', async () => {
      const mockMetrics: PerformanceMetrics = {
        reasoning: { mathReasoning: 0.7, logicalReasoning: 0.6, commonSense: 0.8 },
        planning: { taskPlanning: 0.7, longHorizon: 0.6, multiStep: 0.7 },
        coding: { humanEval: 0.8, mbpp: 0.7, apps: 0.6 },
        toolUse: { apiUsage: 0.8, composition: 0.7, errorRecovery: 0.6 },
        learning: { fewShot: 0.8, zeroShot: 0.7, transfer: 0.6 },
        creativity: { novelty: 0.7, diversity: 0.8, quality: 0.7 },
      };

      mockLLM.generateStructured.mockResolvedValue({
        strategy: 'fine-tuning',
        reasoning: 'Target weak areas',
        expectedImprovement: 0.15,
        estimatedCost: 500,
      });

      const result = await postTraining.selectTrainingStrategy(mockMetrics);

      expect(result).toBeDefined();
      expect(result.strategy).toBeDefined();
      expect(mockLLM.generateStructured).toHaveBeenCalled();
    });
  });
});
