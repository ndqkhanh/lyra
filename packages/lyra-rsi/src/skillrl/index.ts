import { LLMClient } from '../core/llm-client';
import { Skill, Experience, Example } from '../types';
import { Logger, generateId } from '../utils/helpers';
import * as fs from 'fs';
import * as path from 'path';

export class SkillRL {
  private llm: LLMClient;
  private logger: Logger;
  private library: SkillLibrary;
  private evolutionInterval: number;
  private topK: number;
  private storageDir: string;

  constructor(
    llm: LLMClient,
    config: { evolutionInterval: number; topK: number },
    storageDir: string = './data/skills'
  ) {
    this.llm = llm;
    this.logger = new Logger('SkillRL');
    this.evolutionInterval = config.evolutionInterval;
    this.topK = config.topK;
    this.storageDir = storageDir;
    this.library = {
      generalSkills: [],
      taskSpecificSkills: new Map(),
      commonMistakes: [],
    };
    this.loadLibrary();
  }

  async evolveSkillLibrary(): Promise<void> {
    this.logger.info('🧬 Starting SkillRL library evolution...');

    // 1. Collect experiences (simulated for now)
    const experiences = await this.collectExperiences();
    this.logger.info(`Collected ${experiences.length} experiences`);

    // 2. Discover new skills from successful trajectories
    const successfulExperiences = experiences.filter(e => e.success);
    if (successfulExperiences.length > 0) {
      const newSkills = await this.discoverSkills(successfulExperiences);
      this.logger.info(`Discovered ${newSkills.length} new skills`);
      this.library.generalSkills.push(...newSkills);
    }

    // 3. Refine existing skills based on failures
    const failedExperiences = experiences.filter(e => !e.success);
    if (failedExperiences.length > 0 && this.library.generalSkills.length > 0) {
      const refinedSkills = await this.refineSkills(this.library.generalSkills, failedExperiences);
      this.library.generalSkills = refinedSkills;
      this.logger.info(`Refined ${refinedSkills.length} skills`);
    }

    // 4. Identify common mistakes
    if (failedExperiences.length > 0) {
      const mistakes = await this.identifyMistakes(failedExperiences);
      this.library.commonMistakes.push(...mistakes);
      this.logger.info(`Identified ${mistakes.length} common mistakes`);
    }

    // 5. Save library
    this.saveLibrary();

    this.logger.info(`✅ Skill library now has ${this.library.generalSkills.length} general skills`);
  }

  private async collectExperiences(): Promise<Experience[]> {
    // Simulate collecting experiences
    const experiences: Experience[] = [];
    
    for (let i = 0; i < 20; i++) {
      experiences.push({
        id: generateId(),
        task: {
          id: generateId(),
          description: `Task ${i}`,
          type: 'general',
        },
        actions: [],
        outcome: {
          success: Math.random() > 0.3,
        },
        success: Math.random() > 0.3,
        timestamp: Date.now(),
        duration: Math.random() * 5000,
      });
    }

    return experiences;
  }

  private async discoverSkills(successfulExperiences: Experience[]): Promise<Skill[]> {
    this.logger.info('Discovering skills from successful experiences...');

    const prompt = `Analyze these successful task executions and extract reusable skills:

${successfulExperiences.slice(0, 5).map((exp, i) => `
Experience ${i + 1}:
- Task: ${exp.task.description}
- Actions: ${exp.actions.length} steps
- Duration: ${exp.duration}ms
`).join('\n')}

Extract 3-5 general skills that could be reused across different tasks.

Output format:
{
  "skills": [
    {
      "title": "Skill name",
      "principle": "What to do",
      "whenToApply": "When to use this skill",
      "examples": [
        {
          "input": "Example input",
          "output": "Example output"
        }
      ]
    }
  ]
}`;

    try {
      const response = await this.llm.generateStructured<{
        skills: Array<{
          title: string;
          principle: string;
          whenToApply: string;
          examples: Example[];
        }>;
      }>(prompt);

      return response.skills.map(s => ({
        id: generateId(),
        title: s.title,
        principle: s.principle,
        whenToApply: s.whenToApply,
        examples: s.examples || [],
        successRate: 1.0,
        executionCount: 1,
        lastUsed: Date.now(),
      }));
    } catch (error) {
      this.logger.error('Failed to discover skills:', error);
      return [];
    }
  }

  private async refineSkills(skills: Skill[], _failures: Experience[]): Promise<Skill[]> {
    this.logger.info('Refining skills based on failures...');

    const refinedSkills: Skill[] = [];

    for (const skill of skills) {
      // Check if skill needs refinement
      if (skill.successRate < 0.7) {
        try {
          const prompt = `This skill has a low success rate (${skill.successRate}):

Skill: ${skill.title}
Principle: ${skill.principle}
When to apply: ${skill.whenToApply}

Recent failures suggest it needs improvement. Refine this skill to be more effective.

Output format:
{
  "principle": "Improved principle",
  "whenToApply": "Improved conditions"
}`;

          const response = await this.llm.generateStructured<{
            principle: string;
            whenToApply: string;
          }>(prompt);

          refinedSkills.push({
            ...skill,
            principle: response.principle,
            whenToApply: response.whenToApply,
          });
        } catch (error) {
          this.logger.error(`Failed to refine skill ${skill.id}:`, error);
          refinedSkills.push(skill);
        }
      } else {
        refinedSkills.push(skill);
      }
    }

    return refinedSkills;
  }

  private async identifyMistakes(failures: Experience[]): Promise<Mistake[]> {
    this.logger.info('Identifying common mistakes...');

    const prompt = `Analyze these failed task executions and identify common mistakes:

${failures.slice(0, 5).map((exp, i) => `
Failure ${i + 1}:
- Task: ${exp.task.description}
- Error: ${exp.outcome.error || 'Unknown error'}
`).join('\n')}

Identify 2-3 common mistakes to avoid.

Output format:
{
  "mistakes": [
    {
      "pattern": "What went wrong",
      "avoidance": "How to avoid it"
    }
  ]
}`;

    try {
      const response = await this.llm.generateStructured<{
        mistakes: Array<{
          pattern: string;
          avoidance: string;
        }>;
      }>(prompt);

      return response.mistakes.map(m => ({
        id: generateId(),
        pattern: m.pattern,
        avoidance: m.avoidance,
        frequency: 1,
      }));
    } catch (error) {
      this.logger.error('Failed to identify mistakes:', error);
      return [];
    }
  }

  async retrieveRelevantSkills(taskDescription: string): Promise<Skill[]> {
    if (this.library.generalSkills.length === 0) {
      return [];
    }

    // Simple relevance scoring based on keyword matching
    const skills = this.library.generalSkills.map(skill => {
      const relevance = this.calculateRelevance(taskDescription, skill);
      return { skill, relevance };
    });

    // Sort by relevance and return top K
    skills.sort((a, b) => b.relevance - a.relevance);
    return skills.slice(0, this.topK).map(s => s.skill);
  }

  private calculateRelevance(taskDescription: string, skill: Skill): number {
    const taskWords = taskDescription.toLowerCase().split(/\s+/);
    const skillWords = (skill.principle + ' ' + skill.whenToApply).toLowerCase().split(/\s+/);
    
    let matches = 0;
    for (const word of taskWords) {
      if (skillWords.includes(word)) {
        matches++;
      }
    }

    return matches / taskWords.length;
  }

  private loadLibrary(): void {
    const libraryPath = path.join(this.storageDir, 'library.json');
    if (fs.existsSync(libraryPath)) {
      try {
        const data = fs.readFileSync(libraryPath, 'utf-8');
        const parsed = JSON.parse(data);
        this.library.generalSkills = parsed.generalSkills || [];
        this.library.commonMistakes = parsed.commonMistakes || [];
        this.logger.info(`Loaded ${this.library.generalSkills.length} skills from storage`);
      } catch (error) {
        this.logger.error('Failed to load library:', error);
      }
    }
  }

  private saveLibrary(): void {
    const libraryPath = path.join(this.storageDir, 'library.json');
    const dir = path.dirname(libraryPath);
    
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    try {
      fs.writeFileSync(
        libraryPath,
        JSON.stringify(
          {
            generalSkills: this.library.generalSkills,
            commonMistakes: this.library.commonMistakes,
          },
          null,
          2
        ),
        'utf-8'
      );
      this.logger.debug('Saved library to storage');
    } catch (error) {
      this.logger.error('Failed to save library:', error);
    }
  }

  getLibraryStats(): { skillCount: number; mistakeCount: number } {
    return {
      skillCount: this.library.generalSkills.length,
      mistakeCount: this.library.commonMistakes.length,
    };
  }
}

interface SkillLibrary {
  generalSkills: Skill[];
  taskSpecificSkills: Map<string, Skill[]>;
  commonMistakes: Mistake[];
}

interface Mistake {
  id: string;
  pattern: string;
  avoidance: string;
  frequency: number;
}
