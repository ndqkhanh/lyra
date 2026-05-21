import { SkillRL } from '../skillrl';
import { LLMClient } from '../core/llm-client';

describe('SkillRL', () => {
  let skillRL: SkillRL;
  let mockLLM: jest.Mocked<LLMClient>;

  beforeEach(() => {
    mockLLM = {
      generate: jest.fn(),
      generateStructured: jest.fn(),
    } as any;

    skillRL = new SkillRL(mockLLM, {
      evolutionInterval: 1000,
      topK: 3,
    });
  });

  describe('evolveSkillLibrary', () => {
    it('should evolve skill library successfully', async () => {
      mockLLM.generateStructured.mockResolvedValue({
        skills: [
          {
            id: '1',
            title: 'Test Skill',
            principle: 'Test principle',
            whenToApply: 'Always',
            examples: [],
            successRate: 0.8,
          },
        ],
      });

      await skillRL.evolveSkillLibrary();

      expect(mockLLM.generateStructured).toHaveBeenCalled();
    });

    it('should handle errors gracefully', async () => {
      mockLLM.generateStructured.mockRejectedValue(new Error('API error'));

      await expect(skillRL.evolveSkillLibrary()).resolves.not.toThrow();
    });
  });

  describe('getLibraryStats', () => {
    it('should return library statistics', () => {
      const stats = skillRL.getLibraryStats();
      expect(stats).toHaveProperty('skillCount');
      expect(stats).toHaveProperty('mistakeCount');
      expect(stats.skillCount).toBeGreaterThanOrEqual(0);
    });
  });

  describe('getLibraryStats', () => {
    it('should return library statistics', () => {
      const stats = skillRL.getLibraryStats();
      expect(stats).toHaveProperty('skillCount');
      expect(stats).toHaveProperty('mistakeCount');
      expect(typeof stats.skillCount).toBe('number');
      expect(typeof stats.mistakeCount).toBe('number');
    });
  });
});
