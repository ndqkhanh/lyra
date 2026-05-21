# Lyra RSI - Recursive Self-Improvement System

A comprehensive implementation of the Lyra Recursive Self-Improvement Ultra Plan, featuring an intelligence explosion architecture with multiple self-improvement mechanisms.

## Features

- **Agent0**: Bootstrap learning from zero data using synthetic task generation
- **SkillRL**: Reinforcement learning for skill library evolution
- **CLI-Anything**: Automatic tool discovery and installation
- **Meta-Harness**: Self-optimizing evaluation harness
- **AlphaEvolve**: Evolutionary algorithm optimization
- **Post-Training**: Synthetic data generation and training strategy selection
- **HyperAgent**: Architectural bottleneck analysis and self-modification
- **Intelligence Explosion Orchestrator**: Coordinates all components with safety monitoring

## Installation

```bash
npm install
```

## Configuration

Copy `.env.example` to `.env` and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
ANTHROPIC_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here

LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-opus-20240229
```

## Usage

### Development

```bash
npm run dev
```

### Production

```bash
npm run build
npm start
```

### Testing

```bash
npm test
```

### Linting

```bash
npm run lint
```

### Formatting

```bash
npm run format
```

## Architecture

### Core Components

1. **Agent0** - Bootstraps from zero data
   - Generates synthetic tasks
   - Self-trains on generated data
   - Builds initial experience buffer

2. **SkillRL** - Evolves skill library
   - Tracks skill performance
   - Learns from mistakes
   - Evolves successful patterns

3. **CLI-Anything** - Tool ecosystem
   - Discovers available tools
   - Installs and configures tools
   - Maintains tool registry

4. **Meta-Harness** - Self-optimizing evaluation
   - Optimizes evaluation harnesses
   - Tracks harness performance
   - Evolves evaluation strategies

5. **AlphaEvolve** - Algorithm evolution
   - Generates algorithm variants
   - Evaluates on benchmarks
   - Selects best performers

6. **Post-Training** - Continuous improvement
   - Generates synthetic training data
   - Selects training strategies
   - Targets weak areas

7. **HyperAgent** - Self-modification
   - Analyzes performance bottlenecks
   - Proposes architectural changes
   - Implements and validates changes

8. **Intelligence Explosion** - Orchestration
   - Coordinates all components
   - Monitors safety metrics
   - Manages generation cycles

## Safety Features

- Maximum degradation threshold
- Explosion detection and throttling
- Generation interval controls
- Rollback capabilities
- Comprehensive logging

## Project Structure

```
lyra-rsi/
├── src/
│   ├── agent0/           # Bootstrap learning
│   ├── skillrl/          # Skill evolution
│   ├── cli-anything/     # Tool management
│   ├── meta-harness/     # Evaluation optimization
│   ├── alpha-evolve/     # Algorithm evolution
│   ├── post-training/    # Training optimization
│   ├── hyper-agent/      # Self-modification
│   ├── core/             # Core components
│   │   ├── llm-client.ts
│   │   └── intelligence-explosion.ts
│   ├── utils/            # Utilities
│   ├── types/            # TypeScript types
│   ├── __tests__/        # Test suite
│   ├── config.ts         # Configuration
│   └── index.ts          # Entry point
├── dist/                 # Compiled output
├── coverage/             # Test coverage
├── logs/                 # Application logs
├── benchmarks/           # Benchmark data
├── .env.example          # Example environment
├── jest.config.js        # Jest configuration
├── tsconfig.json         # TypeScript config
└── package.json          # Dependencies
```

## Development

### Adding New Components

1. Create component directory in `src/`
2. Implement component interface
3. Add tests in `src/__tests__/`
4. Register in `intelligence-explosion.ts`
5. Update configuration types

### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test
npm test -- agent0.test.ts

# Watch mode
npm test -- --watch
```

## Performance Metrics

The system tracks comprehensive metrics across:

- **Reasoning**: Math, logical, common sense
- **Planning**: Task planning, long-horizon, multi-step
- **Coding**: HumanEval, MBPP, APPS
- **Tool Use**: API usage, composition, error recovery
- **Learning**: Few-shot, zero-shot, transfer
- **Creativity**: Novelty, diversity, quality

## License

MIT

## Author

Khanh Nguyen

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.

## Citation

If you use this work in your research, please cite:

```bibtex
@software{lyra_rsi_2024,
  title={Lyra RSI: Recursive Self-Improvement System},
  author={Nguyen, Khanh},
  year={2024},
  url={https://github.com/yourusername/lyra-rsi}
}
```
