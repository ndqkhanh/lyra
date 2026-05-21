import { LLMClient } from '../core/llm-client';
import { Algorithm, Benchmark } from '../types';
import { Logger, generateId, sleep } from '../utils/helpers';

export class AlphaEvolve {
  private llm: LLMClient;
  private logger: Logger;
  private maxGenerations: number;
  private populationSize: number;

  constructor(llm: LLMClient, config: { maxGenerations: number; populationSize: number }) {
    this.llm = llm;
    this.logger = new Logger('AlphaEvolve');
    this.maxGenerations = config.maxGenerations;
    this.populationSize = config.populationSize;
  }

  async evolveAlgorithm(objective: string, benchmark: Benchmark): Promise<Algorithm> {
    this.logger.info(`🧬 Evolving algorithm for: ${objective}`);

    // 1. Initialize population
    let population = await this.initializePopulation(objective);
    this.logger.info(`Initialized population of ${population.length}`);

    let bestAlgorithm = population[0];

    // 2. Evolutionary loop
    for (let generation = 0; generation < this.maxGenerations; generation++) {
      this.logger.info(`\n=== Generation ${generation + 1}/${this.maxGenerations} ===`);

      // 3. Evaluate fitness
      const fitness = await Promise.all(
        population.map(algo => this.evaluateFitness(algo, benchmark))
      );

      // Update fitness in population
      population.forEach((algo, i) => {
        algo.fitness = fitness[i];
      });

      // 4. Select top performers
      const selected = this.selection(population, fitness);
      this.logger.info(`Selected ${selected.length} top performers`);

      // Track best
      const currentBest = selected[0];
      if (currentBest.fitness! > (bestAlgorithm.fitness || 0)) {
        bestAlgorithm = currentBest;
        this.logger.info(`✅ New best fitness: ${bestAlgorithm.fitness?.toFixed(4)}`);
      }

      // 5. Generate offspring via mutation and crossover
      const offspring: Algorithm[] = [];

      // Mutation
      for (const parent of selected.slice(0, 3)) {
        const mutations = await this.mutate(parent, { objective, generation });
        offspring.push(...mutations);
      }

      // Crossover
      if (selected.length >= 2) {
        const child = await this.crossover(selected[0], selected[1]);
        offspring.push(child);
      }

      // 6. Update population
      population = [...selected, ...offspring].slice(0, this.populationSize);

      await sleep(500);
    }

    this.logger.info(`\n🎯 Best fitness achieved: ${bestAlgorithm.fitness?.toFixed(4)}`);
    return bestAlgorithm;
  }

  private async initializePopulation(objective: string): Promise<Algorithm[]> {
    const population: Algorithm[] = [];

    for (let i = 0; i < this.populationSize; i++) {
      const code = await this.generateInitialAlgorithm(objective);
      population.push({
        id: generateId(),
        code,
        fitness: null,
      });
    }

    return population;
  }

  private async generateInitialAlgorithm(objective: string): Promise<string> {
    const prompt = `Generate a TypeScript algorithm to ${objective}.

Requirements:
- Efficient implementation
- Clear and readable code
- Handle edge cases

Output ONLY the code, no explanations.`;

    try {
      const response = await this.llm.generate(prompt);
      
      if (typeof response === 'string') {
        const codeMatch = response.match(/```typescript\n([\s\S]*?)\n```/) || response.match(/```\n([\s\S]*?)\n```/);
        return codeMatch ? codeMatch[1] : response;
      }
      
      return '// Algorithm implementation';
    } catch (error) {
      this.logger.error('Failed to generate initial algorithm:', error);
      return '// Algorithm implementation';
    }
  }

  private async evaluateFitness(algo: Algorithm, _benchmark: Benchmark): Promise<number> {
    // Simulate fitness evaluation
    const baseScore = 0.5;
    const randomVariation = (Math.random() - 0.5) * 0.3;
    const complexityBonus = algo.code.length > 300 ? 0.1 : 0;
    
    return Math.max(0, Math.min(1, baseScore + randomVariation + complexityBonus));
  }

  private selection(population: Algorithm[], fitness: number[]): Algorithm[] {
    // Sort by fitness and select top 50%
    const sorted = population
      .map((algo, i) => ({ algo, fitness: fitness[i] }))
      .sort((a, b) => b.fitness - a.fitness);

    const selectCount = Math.ceil(population.length / 2);
    return sorted.slice(0, selectCount).map(s => s.algo);
  }

  private async mutate(algo: Algorithm, context: { objective: string; generation: number }): Promise<Algorithm[]> {
    const prompt = `You are evolving an algorithm to ${context.objective}.

# Current Algorithm (Fitness: ${algo.fitness?.toFixed(4) || 'N/A'})
\`\`\`typescript
${algo.code}
\`\`\`

# Your Task
Propose 2 semantically meaningful mutations:

1. **Optimization mutation**: Improve efficiency
2. **Exploration mutation**: Try a different approach

For each mutation, output the complete mutated code.

Output format:
{
  "mutations": [
    {
      "type": "optimization",
      "code": "..."
    },
    {
      "type": "exploration",
      "code": "..."
    }
  ]
}`;

    try {
      const response = await this.llm.generateStructured<{
        mutations: Array<{ type: string; code: string }>;
      }>(prompt);

      return response.mutations.map(m => ({
        id: generateId(),
        code: m.code,
        fitness: null,
        metadata: {
          parent: algo.id,
          mutationType: m.type,
        },
      }));
    } catch (error) {
      this.logger.error('Failed to mutate:', error);
      return [];
    }
  }

  private async crossover(parent1: Algorithm, parent2: Algorithm): Promise<Algorithm> {
    const prompt = `Combine the best aspects of these two algorithms:

# Parent 1 (Fitness: ${parent1.fitness?.toFixed(4) || 'N/A'})
\`\`\`typescript
${parent1.code}
\`\`\`

# Parent 2 (Fitness: ${parent2.fitness?.toFixed(4) || 'N/A'})
\`\`\`typescript
${parent2.code}
\`\`\`

Create a child algorithm that inherits the best patterns from both.

Output ONLY the child algorithm code.`;

    try {
      const response = await this.llm.generate(prompt);
      
      let code = '// Crossover result';
      if (typeof response === 'string') {
        const codeMatch = response.match(/```typescript\n([\s\S]*?)\n```/) || response.match(/```\n([\s\S]*?)\n```/);
        code = codeMatch ? codeMatch[1] : response;
      }

      return {
        id: generateId(),
        code,
        fitness: null,
        metadata: {
          parents: [parent1.id, parent2.id],
          type: 'crossover',
        },
      };
    } catch (error) {
      this.logger.error('Failed to crossover:', error);
      return {
        id: generateId(),
        code: parent1.code,
        fitness: null,
      };
    }
  }
}
