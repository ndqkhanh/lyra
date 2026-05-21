import { HyperAgent } from '../hyper-agent';
import { LLMClient } from '../core/llm-client';
import { PerformanceMetrics } from '../types';

describe('HyperAgent', () => {
  let hyperAgent: HyperAgent;
  let mockLLM: jest.Mocked<LLMClient>;

  beforeEach(() => {
    mockLLM = {
      generate: jest.fn(),
      generateStructured: jest.fn(),
    } as any;

    hyperAgent = new HyperAgent(mockLLM, {
      sandboxEnabled: true,
    });
  });

  describe('analyzeBottlenecks', () => {
    it('should analyze bottlenecks successfully', async () => {
      const mockMetrics: PerformanceMetrics = {
        reasoning: { mathReasoning: 0.7, logicalReasoning: 0.6, commonSense: 0.8 },
        planning: { taskPlanning: 0.7, longHorizon: 0.6, multiStep: 0.7 },
        coding: { humanEval: 0.8, mbpp: 0.7, apps: 0.6 },
        toolUse: { apiUsage: 0.8, composition: 0.7, errorRecovery: 0.6 },
        learning: { fewShot: 0.8, zeroShot: 0.7, transfer: 0.6 },
        creativity: { novelty: 0.7, diversity: 0.8, quality: 0.7 },
      };

      mockLLM.generateStructured.mockResolvedValue({
        bottlenecks: [
          {
            type: 'reasoning',
            component: 'logical-reasoning',
            impact: 0.4,
            evidence: 'Low scores on logical tasks',
            performanceData: {},
          },
        ],
      });

      const result = await hyperAgent.analyzeBottlenecks(mockMetrics);

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
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

      await expect(hyperAgent.analyzeBottlenecks(mockMetrics)).rejects.toThrow();
    });
  });

  describe('proposeArchitecturalChange', () => {
    it('should propose architectural change successfully', async () => {
      mockLLM.generateStructured.mockResolvedValue({
        description: 'Add new reasoning module',
        reasoning: 'Improve logical reasoning',
        code: 'class NewModule {}',
        tests: ['test1', 'test2'],
        rollbackPlan: 'Remove module',
        expectedImprovement: 0.2,
      });

      const result = await hyperAgent.proposeArchitecturalChange({
        type: 'reasoning',
        component: 'logical-reasoning',
        impact: 0.4,
        evidence: 'Low scores',
        performanceData: {},
      });

      expect(result).toBeDefined();
      expect(result.description).toBeDefined();
      expect(mockLLM.generateStructured).toHaveBeenCalled();
    });
  });
});
