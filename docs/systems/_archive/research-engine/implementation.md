# Research Engine Implementation Guide

**System:** Multi-Hop Deep Research Engine  
**Version:** 2.0  
**Status:** Production  
**Last Updated:** 2026-06-02

---

## Overview

This guide provides implementation details, code examples, configuration, deployment, integration patterns, and testing strategies for the Lyra Research Engine.

---

## Installation & Setup

### Prerequisites

```bash
# Python 3.11 or higher
python --version  # Python 3.11+

# Required system packages
pip install --upgrade pip setuptools wheel
```

### Dependencies

```bash
# Install core dependencies
pip install -r requirements-research.txt
```

**requirements-research.txt:**

```text
# Core
networkx==3.2.1
chromadb==0.4.22
spacy==3.7.2
python-dotenv==1.0.0

# Data processing
pandas==2.1.4
numpy==1.26.2

# HTTP & APIs
requests==2.31.0
aiohttp==3.9.1
beautifulsoup4==4.12.2
lxml==4.9.3

# Academic sources
arxiv==2.1.0
scholarly==1.7.11
PyGithub==2.1.1

# NLP
spacy==3.7.2
sentence-transformers==2.2.2

# Storage & Cache
redis==5.0.1
sqlalchemy==2.0.23

# Utilities
tenacity==8.2.3
pydantic==2.5.2
```

### Download NLP Models

```bash
# Download spaCy model for entity extraction
python -m spacy download en_core_web_lg

# Download sentence transformer for embeddings
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

---

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Research Engine Configuration
RESEARCH_ENGINE_ENABLED=true
RESEARCH_MAX_HOPS=5
RESEARCH_MAX_SOURCES=50
RESEARCH_CREDIBILITY_THRESHOLD=0.7

# Cache Configuration
REDIS_URL=redis://localhost:6379
CACHE_TTL_HOURS=24
MEMORY_CACHE_SIZE=1000

# API Keys
ARXIV_API_KEY=your_arxiv_key
GITHUB_TOKEN=your_github_token
GOOGLE_API_KEY=your_google_key
GOOGLE_CSE_ID=your_cse_id

# LLM Configuration (for query refinement)
OPENAI_API_KEY=your_openai_key
REFINEMENT_MODEL=gpt-4o-mini

# Storage
RESEARCH_STORAGE_PATH=./.lyra/research
GRAPH_STORAGE_PATH=./.lyra/graphs

# Logging
LOG_LEVEL=INFO
```

### Configuration File

**config/research_engine.yaml:**

```yaml
research_engine:
  # Multi-hop configuration
  multi_hop:
    max_hops: 5
    min_sources_per_hop: 10
    max_sources_per_hop: 20
    convergence_threshold: 0.85
  
  # Source retrieval
  sources:
    enabled:
      - arxiv
      - github
      - web_search
      - academic_db
    
    timeout_seconds: 30
    retry_attempts: 3
    concurrent_requests: 5
  
  # Credibility scoring
  credibility:
    weights:
      authority: 0.25
      recency: 0.15
      citations: 0.20
      methodology: 0.25
      relevance: 0.15
    
    threshold: 0.7
    recency_half_life_days: 730
  
  # Knowledge graph
  knowledge_graph:
    max_nodes: 50000
    max_edges: 100000
    merge_similarity_threshold: 0.85
    prune_low_confidence_threshold: 0.3
  
  # Evidence synthesis
  synthesis:
    agreement_threshold_high: 0.8
    agreement_threshold_medium: 0.5
    max_contradictions: 10
  
  # Cache
  cache:
    enabled: true
    memory_size: 1000
    redis_ttl_hours: 24
    query_cache_enabled: true
```

---

## Core Implementation

### 1. Research Engine Entry Point

```python
from lyra_research import ResearchEngine, ResearchQuery

# Initialize engine
engine = ResearchEngine.from_config("config/research_engine.yaml")

# Execute research
result = await engine.research(
    query="Latest advances in LLM agent reasoning",
    strategy="iterative",
    max_hops=4
)

# Access results
print(f"Found {len(result.all_results)} sources")
print(f"Knowledge graph: {result.knowledge_graph.number_of_nodes()} nodes")
print(f"Report:\n{result.report}")
```

### 2. Custom Source Provider

```python
from lyra_research.sources import SourceProvider, ResearchResult

class CustomSourceProvider(SourceProvider):
    """Custom source provider implementation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.custom.com"
    
    async def retrieve(
        self,
        query: str,
        max_results: int = 20
    ) -> List[ResearchResult]:
        """Retrieve sources from custom API."""
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/search",
                params={"q": query, "limit": max_results},
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                data = await response.json()
        
        results = []
        for item in data["results"]:
            result = ResearchResult(
                result_id=generate_id(),
                query_id="",
                source_type="custom",
                title=item["title"],
                url=item["url"],
                content=item["abstract"],
                authors=item.get("authors", []),
                publication_date=parse_date(item.get("published")),
                citations=item.get("citations", 0),
                credibility_score=0.0,  # Will be scored later
                credibility_breakdown={},
                entities=[],
                claims=[],
                retrieved_at=datetime.now()
            )
            results.append(result)
        
        return results

# Register custom provider
engine.register_provider("custom", CustomSourceProvider(api_key=os.getenv("CUSTOM_API_KEY")))
```

### 3. Custom Credibility Scorer

```python
from lyra_research.evaluator import CredibilityDimension

class CustomCredibilityScorer:
    """Custom credibility scoring logic."""
    
    def score_authority(self, result: ResearchResult) -> float:
        """Custom authority scoring."""
        
        # Check if from trusted domain
        trusted_domains = [
            "arxiv.org",
            "github.com",
            "proceedings.mlr.press",
            "openreview.net"
        ]
        
        domain = urlparse(result.url).netloc
        if any(trusted in domain for trusted in trusted_domains):
            return 0.9
        
        # Check author reputation (custom logic)
        author_scores = [
            self._get_author_score(author)
            for author in result.authors
        ]
        
        if author_scores:
            return max(author_scores)
        
        return 0.5
    
    def _get_author_score(self, author: str) -> float:
        """Get author reputation score."""
        # Custom logic: check h-index, publication count, etc.
        # Simplified example:
        return 0.7

# Use custom scorer
engine.evaluator.register_dimension(
    CredibilityDimension(
        name="authority",
        weight=0.25,
        scorer=CustomCredibilityScorer().score_authority
    )
)
```

### 4. Knowledge Graph Operations

```python
from lyra_research.graph import KnowledgeGraph

# Access knowledge graph
graph = result.knowledge_graph

# Query nodes by type
concepts = graph.query_nodes(node_type="concept", limit=50)
references = graph.query_nodes(node_type="reference", limit=100)

# Find related concepts
related = graph.find_related(
    node_id="concept_123",
    edge_type="related_to",
    max_depth=2
)

# Find path between two concepts
path = graph.find_shortest_path(
    source_id="concept_123",
    target_id="concept_456"
)

# Get subgraph around a node
subgraph = graph.get_subgraph(
    center_node_id="concept_123",
    radius=2
)

# Export to various formats
graph.export_gexf("research_graph.gexf")
graph.export_graphml("research_graph.graphml")
graph.export_json("research_graph.json")

# Visualize (requires matplotlib)
graph.visualize(
    output_path="research_graph.png",
    layout="spring",
    node_size=100,
    font_size=8
)
```

### 5. Citation Management

```python
from lyra_research.citations import CitationManager

# Initialize citation manager
citations = CitationManager(result.all_results)

# Get formatted citations
bibliography = citations.format_bibliography(style="apa")
print(bibliography)

# Get citation for specific result
citation = citations.get_citation(result_id="res_123", style="bibtex")
print(citation)

# Export citations
citations.export_bibtex("references.bib")
citations.export_ris("references.ris")
citations.export_endnote("references.enw")

# Traverse citation network
network = citations.build_citation_network()
related_papers = network.find_related(result_id="res_123", max_depth=2)
```

---

## Integration Patterns

### 1. Integration with Lyra Gateway

```python
from lyra_core.gateway import Gateway
from lyra_research import ResearchEngine

class ResearchIntegration:
    """Integrate research engine with Lyra Gateway."""
    
    def __init__(self, gateway: Gateway):
        self.gateway = gateway
        self.engine = ResearchEngine.from_config()
    
    async def handle_research_command(self, session_id: str, query: str):
        """Handle /research command."""
        
        # Execute research
        result = await self.engine.research(query)
        
        # Store in session context
        await self.gateway.context_engine.add_observation(
            session_id=session_id,
            observation={
                "type": "research_result",
                "query": query,
                "result_summary": result.synthesis.to_dict(),
                "source_count": len(result.all_results),
                "knowledge_graph_size": result.knowledge_graph.number_of_nodes()
            }
        )
        
        # Persist knowledge graph to memory
        await self.gateway.memory.store_graph(
            session_id=session_id,
            graph=result.knowledge_graph
        )
        
        return result.report

# Register with gateway
gateway = Gateway()
research_integration = ResearchIntegration(gateway)
gateway.register_command("research", research_integration.handle_research_command)
```

### 2. Integration with Memory System

```python
from lyra_memory import MemoryStore
from lyra_research import ResearchEngine

class ResearchMemoryIntegration:
    """Integrate research results with memory system."""
    
    def __init__(self, memory: MemoryStore):
        self.memory = memory
        self.engine = ResearchEngine.from_config()
    
    async def research_with_memory(self, query: str) -> ResearchSession:
        """Execute research using prior memory."""
        
        # Retrieve relevant prior research from memory
        prior_research = await self.memory.semantic_search(
            query=query,
            collection="research_sessions",
            limit=5
        )
        
        # Add context from prior research
        context = {
            "prior_findings": [r["synthesis"] for r in prior_research],
            "prior_sources": [r["sources"] for r in prior_research]
        }
        
        # Execute research with context
        result = await self.engine.research(
            query=query,
            context=context
        )
        
        # Store results in memory
        await self.memory.store_embedding(
            collection="research_sessions",
            id=result.session_id,
            text=result.report,
            metadata={
                "query": query,
                "synthesis": result.synthesis.to_dict(),
                "sources": [r.url for r in result.all_results],
                "timestamp": result.completed_at.isoformat()
            }
        )
        
        # Store knowledge graph
        await self.memory.store_graph(
            graph_id=result.session_id,
            graph=result.knowledge_graph
        )
        
        return result
```

### 3. Integration with Agent Swarm

```python
from lyra_swarm import AgentSwarm
from lyra_research import ResearchEngine

class SwarmResearchCoordinator:
    """Coordinate research across multiple agents."""
    
    def __init__(self, swarm: AgentSwarm):
        self.swarm = swarm
        self.engine = ResearchEngine.from_config()
    
    async def distributed_research(
        self,
        query: str,
        subtopics: List[str]
    ) -> ResearchSession:
        """Distribute research across agents."""
        
        # Spawn agents for each subtopic
        tasks = []
        for subtopic in subtopics:
            agent_id = await self.swarm.spawn_agent(
                role="researcher",
                task=f"Research: {subtopic}"
            )
            
            task = self.engine.research(
                query=subtopic,
                max_hops=3
            )
            tasks.append((agent_id, task))
        
        # Execute in parallel
        results = await asyncio.gather(*[task for _, task in tasks])
        
        # Merge knowledge graphs
        merged_graph = self._merge_graphs([r.knowledge_graph for r in results])
        
        # Synthesize combined findings
        combined_synthesis = self._synthesize_combined(results)
        
        # Create combined session
        combined_session = ResearchSession(
            session_id=generate_id(),
            query=ResearchQuery(
                query_id=generate_id(),
                text=query,
                strategy=ResearchStrategy.distributed,
                created_at=datetime.now()
            ),
            all_results=[r for result in results for r in result.all_results],
            knowledge_graph=merged_graph,
            synthesis=combined_synthesis,
            report=self._generate_combined_report(combined_synthesis),
            started_at=min(r.started_at for r in results),
            completed_at=max(r.completed_at for r in results)
        )
        
        return combined_session
```

---

## Deployment

### Local Development

```bash
# Start Redis (for caching)
docker run -d -p 6379:6379 redis:7-alpine

# Start research engine service
python -m lyra_research.server \
    --host 0.0.0.0 \
    --port 8080 \
    --config config/research_engine.yaml

# Health check
curl http://localhost:8080/health
```

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-research.txt .
RUN pip install --no-cache-dir -r requirements-research.txt

# Download NLP models
RUN python -m spacy download en_core_web_lg

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Start service
CMD ["python", "-m", "lyra_research.server", "--host", "0.0.0.0", "--port", "8080"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  research-engine:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
      - RESEARCH_STORAGE_PATH=/data/research
      - GRAPH_STORAGE_PATH=/data/graphs
    volumes:
      - ./data:/data
      - ./config:/app/config
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
  
  research-worker:
    build: .
    command: python -m lyra_research.worker
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 3

volumes:
  redis-data:
```

### Kubernetes Deployment

**k8s/deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: research-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: research-engine
  template:
    metadata:
      labels:
        app: research-engine
    spec:
      containers:
      - name: research-engine
        image: lyra/research-engine:2.0
        ports:
        - containerPort: 8080
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: RESEARCH_MAX_HOPS
          value: "5"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: research-engine-service
spec:
  selector:
    app: research-engine
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

---

## Testing Strategies

### Unit Tests

```python
import pytest
from lyra_research import MultiHopEngine, ResearchQuery

@pytest.fixture
def engine():
    return MultiHopEngine.from_config("config/test.yaml")

def test_single_hop_research(engine):
    """Test single hop research execution."""
    query = ResearchQuery(
        query_id="test_1",
        text="Test query",
        strategy=ResearchStrategy.breadth_first,
        max_hops=1,
        created_at=datetime.now()
    )
    
    result = await engine.execute_research(query)
    
    assert result.current_hop == 1
    assert len(result.all_results) > 0
    assert result.knowledge_graph.number_of_nodes() > 0

def test_credibility_scoring():
    """Test source credibility scoring."""
    evaluator = SourceEvaluator()
    
    result = ResearchResult(
        result_id="test_1",
        source_type="arxiv",
        publication_date=datetime.now() - timedelta(days=30),
        citations=100,
        content="methodology experiment evaluation benchmark"
    )
    
    score = evaluator.score(result, query="test query")
    
    assert 0.0 <= score <= 1.0
    assert score > 0.7  # Should be high for recent arXiv with citations

def test_knowledge_graph_construction():
    """Test knowledge graph building."""
    builder = KnowledgeGraphBuilder()
    graph = KnowledgeGraph()
    
    result = ResearchResult(
        result_id="test_1",
        title="Test Paper",
        entities=[
            Entity(text="Neural Networks", type="concept", confidence=0.9),
            Entity(text="Deep Learning", type="concept", confidence=0.85)
        ]
    )
    
    builder.add_result(graph, result)
    
    assert graph.number_of_nodes() >= 3  # ref + 2 concepts
    assert graph.number_of_edges() >= 2  # ref -> concepts
```

### Integration Tests

```python
@pytest.mark.integration
async def test_end_to_end_research():
    """Test complete research flow."""
    engine = ResearchEngine.from_config()
    
    result = await engine.research(
        query="LLM reasoning techniques",
        max_hops=3
    )
    
    assert result.is_complete()
    assert len(result.all_results) > 10
    assert result.synthesis is not None
    assert result.report is not None
    assert result.knowledge_graph.number_of_nodes() > 50

@pytest.mark.integration
async def test_cache_integration():
    """Test cache hit/miss behavior."""
    engine = ResearchEngine.from_config()
    query = "Test query for caching"
    
    # First execution (cache miss)
    start1 = time.time()
    result1 = await engine.research(query)
    time1 = time.time() - start1
    
    # Second execution (cache hit)
    start2 = time.time()
    result2 = await engine.research(query)
    time2 = time.time() - start2
    
    assert time2 < time1 * 0.1  # Cache should be 10x faster
    assert result1.session_id == result2.session_id
```

### Performance Tests

```python
@pytest.mark.performance
async def test_research_latency():
    """Test research latency under load."""
    engine = ResearchEngine.from_config()
    
    queries = [
        "Query 1",
        "Query 2",
        "Query 3",
        "Query 4",
        "Query 5"
    ]
    
    start = time.time()
    results = await asyncio.gather(*[
        engine.research(q) for q in queries
    ])
    duration = time.time() - start
    
    avg_time = duration / len(queries)
    assert avg_time < 30.0  # Average should be under 30s

@pytest.mark.performance
async def test_cache_hit_rate():
    """Test cache performance."""
    engine = ResearchEngine.from_config()
    
    # Execute same queries multiple times
    queries = ["Query A", "Query B", "Query C"] * 10
    
    for query in queries:
        await engine.research(query)
    
    stats = engine.cache.get_stats()
    hit_rate = stats["hits"] / (stats["hits"] + stats["misses"])
    
    assert hit_rate > 0.6  # Should achieve >60% hit rate
```

---

## Monitoring & Observability

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
research_requests = Counter(
    'research_requests_total',
    'Total research requests',
    ['strategy']
)

research_duration = Histogram(
    'research_duration_seconds',
    'Research duration',
    buckets=[5, 10, 20, 30, 45, 60]
)

cache_hits = Counter('research_cache_hits_total', 'Cache hits')
cache_misses = Counter('research_cache_misses_total', 'Cache misses')

knowledge_graph_nodes = Gauge('knowledge_graph_nodes', 'Graph node count')
knowledge_graph_edges = Gauge('knowledge_graph_edges', 'Graph edge count')

# Instrument code
@research_duration.time()
async def research(query: str) -> ResearchSession:
    research_requests.labels(strategy='iterative').inc()
    
    result = await engine.execute_research(query)
    
    knowledge_graph_nodes.set(result.knowledge_graph.number_of_nodes())
    knowledge_graph_edges.set(result.knowledge_graph.number_of_edges())
    
    return result
```

### Logging

```python
import structlog

logger = structlog.get_logger()

# Structured logging
logger.info(
    "research_started",
    query=query.text,
    strategy=query.strategy,
    session_id=session.session_id
)

logger.info(
    "research_hop_completed",
    session_id=session.session_id,
    hop=hop_number,
    sources_found=len(results),
    credible_sources=len(credible_results)
)

logger.info(
    "research_completed",
    session_id=session.session_id,
    duration_seconds=duration,
    total_sources=len(session.all_results),
    graph_nodes=session.knowledge_graph.number_of_nodes()
)
```

---

## Troubleshooting

### Common Issues

#### Issue: High Latency

```python
# Check where time is spent
profiler = ResearchProfiler()
result = await profiler.profile(engine.research, query)

print(profiler.report())
# Output:
# - Source retrieval: 12s (48%)
# - Entity extraction: 5s (20%)
# - Query refinement: 4s (16%)
# ...

# Solution: Enable parallel source retrieval
engine.config.concurrent_requests = 10
```

#### Issue: Low Cache Hit Rate

```bash
# Check cache stats
curl http://localhost:8080/stats/cache

# Increase cache size
export MEMORY_CACHE_SIZE=2000

# Increase TTL
export CACHE_TTL_HOURS=48
```

#### Issue: Graph Too Large

```python
# Check graph size
print(f"Nodes: {graph.number_of_nodes()}")
print(f"Edges: {graph.number_of_edges()}")

# Prune low-confidence nodes
graph.prune(min_confidence=0.5)

# Or limit graph growth
engine.config.knowledge_graph.max_nodes = 10000
```

---

## Related Documentation

- [Architecture](./architecture.md) - System architecture overview
- [System Design](./system-design.md) - Detailed design and algorithms
- [Tradeoffs](./tradeoffs.md) - Design decisions and alternatives
- [Evaluation](./evaluation.md) - Performance metrics and benchmarks

---

**Research Engine Implementation Guide v2.0** | Last Updated: 2026-06-02
