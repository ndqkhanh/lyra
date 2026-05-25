# lyra-arena

Agent Arena — competitive tournaments, Elo ratings, match-running, and leaderboards for the Lyra agent platform.

## Features

- **Agent Registration**: Register agents with customizable initial Elo ratings
- **Match Recording**: Record match outcomes and automatically update Elo ratings
- **Elo Computation**: Standard Elo rating system with configurable K-factors
- **Domain-Specific Ratings**: Track agent performance across different domains
- **Tournament Formats**:
  - Round Robin: Every agent plays every other agent
  - Single Elimination: Bracket-based knockout tournament
  - Swiss: Pairing agents with similar records
  - Double Elimination: Winners and losers brackets
- **Leaderboards**: Global and domain-specific leaderboards
- **Head-to-Head Records**: Compare performance between two agents
- **Match History**: Full history of matches for any agent

## Usage

```python
from lyra_arena import AgentArena, TournamentConfig, TournamentFormat

arena = AgentArena()

# Register agents
agent_a = arena.register_agent("agent-1", name="Alpha", version="1.0")
agent_b = arena.register_agent("agent-2", name="Beta", version="2.0")

# Run a tournament
config = TournamentConfig(
    tournament_id="t1",
    name="Test Tournament",
    format=TournamentFormat.ROUND_ROBIN,
    domains=("GENERAL",),
    agents=(agent_a, agent_b),
)
result = arena.run_tournament(config)

# View leaderboard
leaderboard = arena.get_leaderboard()
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
