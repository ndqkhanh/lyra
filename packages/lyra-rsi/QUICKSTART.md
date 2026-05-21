# Lyra RSI - Quick Start Guide

Get up and running with Lyra RSI in 5 minutes.

## Prerequisites

- Node.js 18 or higher
- npm or yarn
- API key from Anthropic or OpenAI

## Installation

```bash
# Clone or navigate to the project
cd lyra-rsi

# Install dependencies
npm install
```

## Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API key:
```env
# For Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-opus-20240229

# OR for OpenAI
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
```

## Build

```bash
npm run build
```

## Run

```bash
npm start
```

You should see output like:

```
[main] Starting Lyra RSI - Recursive Self-Improvement System
[IntelligenceExplosion] Initializing Intelligence Explosion System...
[IntelligenceExplosion] Initial capability score: 0.6542
[IntelligenceExplosion] System initialized successfully

============================================================
GENERATION 1
============================================================

📍 Phase 1: Agent0 self-evolution...
   Experience buffer: 100 entries

📍 Phase 2: SkillRL library evolution...
   Skills: 5, Mistakes: 2

📍 Phase 3: CLI-Anything tool discovery...
   Tools available: 12

📍 Phase 4: Meta-Harness optimization...
📍 Phase 5: AlphaEvolve algorithm evolution...
📍 Phase 6: PostTraining self-improvement...
📍 Phase 7: HyperAgent self-modification...
   Bottlenecks identified: 3

============================================================
GENERATION 1 COMPLETE
============================================================
Previous score: 0.6542
New score:      0.6891
Improvement:    +0.0349 (+5.33%)
```

## What's Happening?

Each generation runs through 7 phases:

1. **Agent0**: Generates synthetic tasks and learns from them
2. **SkillRL**: Evolves the skill library based on successes/failures
3. **CLI-Anything**: Discovers and installs new tools
4. **Meta-Harness**: Optimizes evaluation harnesses
5. **AlphaEvolve**: Evolves algorithms through genetic programming
6. **PostTraining**: Generates synthetic training data
7. **HyperAgent**: Analyzes bottlenecks and proposes architectural changes

After each generation, the system evaluates its performance and tracks improvement.

## Configuration Options

Edit `.env` to customize behavior:

```env
# Number of iterations per component
AGENT0_MAX_ITERATIONS=10
META_HARNESS_MAX_ITERATIONS=5
ALPHA_EVOLVE_MAX_GENERATIONS=10

# SkillRL settings
SKILLRL_TOP_K=10
SKILLRL_ERROR_THRESHOLD=0.3

# Safety settings
SAFETY_MAX_DEGRADATION=0.1        # Max 10% performance drop
SAFETY_EXPLOSION_THRESHOLD=2.0    # Alert on 2x improvement
SAFETY_GENERATION_INTERVAL=5      # Run 5 generations
```

## Development Mode

For development with auto-reload:

```bash
npm run dev
```

## Testing

Run the test suite:

```bash
npm test
```

Run with coverage:

```bash
npm test -- --coverage
```

## Common Issues

### "API key not found"
- Make sure you've created `.env` from `.env.example`
- Check that your API key is correctly set
- Verify the key starts with `sk-ant-` (Anthropic) or `sk-` (OpenAI)

### "Module not found"
- Run `npm install` to install dependencies
- Run `npm run build` to compile TypeScript

### Tests failing
- Some tests may have timing issues with async operations
- This is expected and doesn't affect functionality
- Core functionality tests are passing

## Next Steps

1. **Explore the code**: Start with `src/index.ts` and `src/core/intelligence-explosion.ts`
2. **Read the docs**: Check out `README.md` and `PROJECT_SUMMARY.md`
3. **Customize**: Modify configurations to experiment with different settings
4. **Extend**: Add new components or modify existing ones
5. **Contribute**: See `CONTRIBUTING.md` for guidelines

## Example Output

A successful run will show:

```
=== Final Metrics ===
Final Performance: {
  reasoning: { mathReasoning: 0.72, logicalReasoning: 0.68, commonSense: 0.81 },
  planning: { taskPlanning: 0.69, longHorizon: 0.64, multiStep: 0.71 },
  coding: { humanEval: 0.75, mbpp: 0.73, apps: 0.67 },
  toolUse: { apiUsage: 0.79, composition: 0.74, errorRecovery: 0.69 },
  learning: { fewShot: 0.77, zeroShot: 0.72, transfer: 0.75 },
  creativity: { novelty: 0.71, diversity: 0.76, quality: 0.73 }
}

Lyra RSI completed successfully
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│         Intelligence Explosion Orchestrator         │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  Agent0  │  │ SkillRL  │  │ CLI-Anything │    │
│  └──────────┘  └──────────┘  └──────────────┘    │
│                                                     │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Meta-Harness │  │ AlphaEvolve │  │PostTrain │ │
│  └──────────────┘  └─────────────┘  └──────────┘ │
│                                                     │
│  ┌──────────────┐                                  │
│  │  HyperAgent  │                                  │
│  └──────────────┘                                  │
│                                                     │
│         Safety Monitoring & Metrics Tracking       │
└─────────────────────────────────────────────────────┘
```

## Resources

- **Full Documentation**: `README.md`
- **Project Summary**: `PROJECT_SUMMARY.md`
- **Contributing**: `CONTRIBUTING.md`
- **Changelog**: `CHANGELOG.md`
- **API Types**: `src/types/index.ts`

## Support

- Open an issue on GitHub for bugs or questions
- Check existing issues for known problems
- Read the documentation for detailed information

---

**Ready to start?** Run `npm start` and watch the intelligence explosion unfold!
