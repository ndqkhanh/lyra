# Monitoring System Architecture

## Executive Summary

Modern LLM agent systems require specialized observability infrastructure that goes beyond traditional APM. This architecture provides comprehensive monitoring for multi-agent systems, addressing the unique challenges of non-deterministic AI workloads.

## 1. Core Components

### 1.1 Observability Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Agent 1 │  │  Agent 2 │  │  Agent N │  │   Tools  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  OpenTelemetry Collector  │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │    Trace Processing       │
        │  - Sampling               │
        │  - Enrichment             │
        │  - Aggregation            │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │      Storage Layer        │
        │  - Traces (Tempo/Jaeger)  │
        │  - Metrics (Prometheus)   │
        │  - Logs (Loki/ES)         │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │   Visualization Layer     │
        │  - Grafana Dashboards     │
        │  - Alerting               │
        │  - Analytics              │
        └───────────────────────────┘
```

### 1.2 Key Differences from Traditional Monitoring

| Aspect | Traditional APM | LLM Agent Monitoring |
|--------|----------------|---------------------|
| **Failure Mode** | 500 errors, timeouts | Confident but wrong answers |
| **Span Count** | 5-10 per request | 100+ per request |
| **Determinism** | Same input → same output | Same input → different outputs |
| **Latency** | Milliseconds | Seconds to minutes |
| **Cost Tracking** | Infrastructure only | Tokens + infrastructure |
| **Quality Metrics** | Error rate | Accuracy, coherence, safety |

## 2. Distributed Tracing Architecture

### 2.1 OpenTelemetry Integration

#### Span Hierarchy for Agent Systems

```python
# Root span: User request
with tracer.start_as_current_span("user_request") as root_span:
    root_span.set_attribute("user_id", user_id)
    root_span.set_attribute("request_type", "agent_task")
    
    # Agent orchestration span
    with tracer.start_as_current_span("agent_orchestration") as orch_span:
        orch_span.set_attribute("agent_count", 3)
        
        # Individual agent spans
        with tracer.start_as_current_span("agent_1_execution") as agent_span:
            agent_span.set_attribute("agent_role", "planner")
            
            # LLM call span
            with tracer.start_as_current_span("llm_call") as llm_span:
                llm_span.set_attribute("model", "claude-opus-4")
                llm_span.set_attribute("input_tokens", 1500)
                llm_span.set_attribute("output_tokens", 800)
                llm_span.set_attribute("cached_tokens", 1200)
                llm_span.set_attribute("cost_usd", 0.045)
                
                response = call_llm(prompt)
                
                llm_span.set_attribute("latency_ms", 2300)
                llm_span.set_attribute("ttft_ms", 450)
            
            # Tool execution spans
            with tracer.start_as_current_span("tool_search") as tool_span:
                tool_span.set_attribute("tool_name", "web_search")
                tool_span.set_attribute("query", search_query)
                results = execute_tool(search_query)
                tool_span.set_attribute("result_count", len(results))
```

#### Critical Span Attributes

**LLM Call Spans:**
```python
span_attributes = {
    # Model info
    "llm.model": "claude-opus-4",
    "llm.provider": "anthropic",
    "llm.temperature": 0.7,
    
    # Token usage
    "llm.input_tokens": 1500,
    "llm.output_tokens": 800,
    "llm.cached_tokens": 1200,
    
    # Cost
    "llm.cost_usd": 0.045,
    "llm.cache_hit_rate": 0.8,
    
    # Performance
    "llm.latency_ms": 2300,
    "llm.ttft_ms": 450,
    
    # Quality
    "llm.finish_reason": "stop",
    "llm.safety_score": 0.95,
}
```

**Agent Spans:**
```python
agent_attributes = {
    # Agent identity
    "agent.id": "planner-001",
    "agent.role": "planner",
    "agent.version": "v2.3.1",
    
    # Execution
    "agent.iteration": 3,
    "agent.max_iterations": 10,
    "agent.status": "success",
    
    # Context
    "agent.context_tokens": 15000,
    "agent.context_utilization": 0.75,
    
    # Quality
    "agent.task_success": True,
    "agent.confidence": 0.92,
}
```

**Tool Spans:**
```python
tool_attributes = {
    # Tool info
    "tool.name": "web_search",
    "tool.version": "1.2.0",
    
    # Execution
    "tool.input_size_bytes": 256,
    "tool.output_size_bytes": 4096,
    "tool.latency_ms": 850,
    
    # Results
    "tool.success": True,
    "tool.result_count": 10,
    "tool.error": None,
}
```

### 2.2 Cardinality Management

#### The Cardinality Explosion Problem

**Challenge**: LLM agent systems generate 100+ spans per request, causing:
- Storage explosion (10x traditional systems)
- Query performance degradation
- Orphaned spans (head-based sampling drops parents)

**Solution: Tail-Based Sampling**

```python
# Tail-based sampling configuration
sampling_config = {
    # Always sample errors
    "error_rate": 1.0,
    
    # Sample slow requests
    "latency_threshold_ms": 5000,
    "latency_sample_rate": 1.0,
    
    # Sample high-cost requests
    "cost_threshold_usd": 0.50,
    "cost_sample_rate": 1.0,
    
    # Sample low-quality responses
    "quality_threshold": 0.7,
    "quality_sample_rate": 1.0,
    
    # Sample normal requests
    "baseline_sample_rate": 0.1,  # 10% of normal traffic
}
```

#### Span Aggregation Strategy

```python
# Aggregate similar spans to reduce cardinality
def aggregate_llm_spans(spans):
    """Aggregate multiple LLM calls into summary metrics"""
    return {
        "llm.call_count": len(spans),
        "llm.total_input_tokens": sum(s.input_tokens for s in spans),
        "llm.total_output_tokens": sum(s.output_tokens for s in spans),
        "llm.total_cost_usd": sum(s.cost for s in spans),
        "llm.avg_latency_ms": mean(s.latency for s in spans),
        "llm.p95_latency_ms": percentile(s.latency for s in spans, 95),
        "llm.error_count": sum(1 for s in spans if s.error),
    }
```

### 2.3 Trace Context Propagation

#### W3C Trace Context Headers

```python
# Automatic propagation via OpenTelemetry
from opentelemetry import trace
from opentelemetry.propagate import inject, extract

# Outgoing request: inject trace context
headers = {}
inject(headers)
response = requests.post(url, headers=headers, json=data)

# Incoming request: extract trace context
context = extract(request.headers)
with tracer.start_as_current_span("handler", context=context):
    # Process request with inherited trace context
    pass
```

## 3. Metrics Collection

### 3.1 Core Metrics

#### System Metrics

```yaml
# Prometheus metrics configuration
metrics:
  # Request metrics
  - name: agent_requests_total
    type: counter
    labels: [agent_role, status, model]
    
  - name: agent_request_duration_seconds
    type: histogram
    buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60]
    labels: [agent_role, model]
  
  # Token metrics
  - name: llm_tokens_total
    type: counter
    labels: [model, token_type]  # token_type: input, output, cached
    
  - name: llm_tokens_per_request
    type: histogram
    buckets: [100, 500, 1000, 5000, 10000, 50000, 100000]
    labels: [model]
  
  # Cost metrics
  - name: llm_cost_usd_total
    type: counter
    labels: [model, provider]
    
  - name: llm_cost_per_request_usd
    type: histogram
    buckets: [0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
    labels: [model]
  
  # Quality metrics
  - name: agent_task_success_rate
    type: gauge
    labels: [agent_role, task_type]
    
  - name: agent_quality_score
    type: histogram
    buckets: [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
    labels: [agent_role, metric_type]
  
  # Cache metrics
  - name: llm_cache_hit_rate
    type: gauge
    labels: [model]
    
  - name: llm_cache_hits_total
    type: counter
    labels: [model]
```

#### Agent-Specific Metrics

```python
# Custom metrics for agent behavior
from prometheus_client import Counter, Histogram, Gauge

# Agent iterations
agent_iterations = Histogram(
    'agent_iterations_total',
    'Number of iterations per agent task',
    ['agent_role', 'task_type'],
    buckets=[1, 2, 3, 5, 10, 20, 50]
)

# Tool usage
tool_calls = Counter(
    'agent_tool_calls_total',
    'Number of tool calls',
    ['agent_role', 'tool_name', 'status']
)

# Context utilization
context_utilization = Histogram(
    'agent_context_utilization_ratio',
    'Context window utilization',
    ['agent_role'],
    buckets=[0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]
)

# Error recovery
error_recovery = Counter(
    'agent_error_recovery_total',
    'Error recovery attempts',
    ['agent_role', 'error_type', 'recovery_strategy', 'success']
)
```

### 3.2 Quality Metrics

#### Task Success Tracking

```python
class QualityMetrics:
    def __init__(self):
        self.success_rate = Gauge(
            'agent_task_success_rate',
            'Task success rate',
            ['agent_role', 'task_type']
        )
        
        self.quality_score = Histogram(
            'agent_quality_score',
            'Quality score distribution',
            ['agent_role', 'metric_type'],
            buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
        )
    
    def record_task_result(self, agent_role, task_type, success, quality_scores):
        # Update success rate
        self.success_rate.labels(
            agent_role=agent_role,
            task_type=task_type
        ).set(success)
        
        # Record quality scores
        for metric_type, score in quality_scores.items():
            self.quality_score.labels(
                agent_role=agent_role,
                metric_type=metric_type
            ).observe(score)
```

#### Multi-Dimensional Quality

```python
quality_dimensions = {
    "accuracy": 0.95,        # Correctness of output
    "coherence": 0.92,       # Logical consistency
    "relevance": 0.88,       # Alignment with task
    "safety": 0.98,          # Absence of harmful content
    "efficiency": 0.85,      # Token/time efficiency
    "completeness": 0.90,    # Task coverage
}
```

## 4. Cost Analytics

### 4.1 Cost Tracking Architecture

```python
class CostTracker:
    def __init__(self):
        self.cost_total = Counter(
            'llm_cost_usd_total',
            'Total LLM cost in USD',
            ['model', 'provider', 'cost_type']
        )
        
        self.cost_per_request = Histogram(
            'llm_cost_per_request_usd',
            'Cost per request in USD',
            ['model', 'task_type'],
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
    
    def track_llm_call(self, model, input_tokens, output_tokens, cached_tokens):
        # Calculate costs
        input_cost = input_tokens * PRICING[model]['input']
        output_cost = output_tokens * PRICING[model]['output']
        cache_cost = cached_tokens * PRICING[model]['cache_read']
        total_cost = input_cost + output_cost + cache_cost
        
        # Record metrics
        self.cost_total.labels(
            model=model,
            provider='anthropic',
            cost_type='input'
        ).inc(input_cost)
        
        self.cost_total.labels(
            model=model,
            provider='anthropic',
            cost_type='output'
        ).inc(output_cost)
        
        self.cost_total.labels(
            model=model,
            provider='anthropic',
            cost_type='cache'
        ).inc(cache_cost)
        
        return total_cost
```

### 4.2 Cost Attribution

```python
# Cost attribution by dimension
cost_breakdown = {
    "by_agent": {
        "planner": 0.45,
        "executor": 1.23,
        "reviewer": 0.67,
    },
    "by_task": {
        "code_generation": 2.15,
        "code_review": 0.20,
    },
    "by_user": {
        "user_123": 5.67,
        "user_456": 3.21,
    },
    "by_model": {
        "claude-opus-4": 8.12,
        "claude-sonnet-4": 0.76,
    }
}
```

### 4.3 Budget Alerts

```yaml
# Alert rules for cost management
alerts:
  - name: HighCostPerRequest
    expr: |
      histogram_quantile(0.95, 
        rate(llm_cost_per_request_usd_bucket[5m])
      ) > 1.0
    severity: warning
    annotations:
      summary: "High cost per request detected"
      description: "P95 cost per request exceeds $1.00"
  
  - name: DailyCostBudgetExceeded
    expr: |
      sum(increase(llm_cost_usd_total[24h])) > 1000
    severity: critical
    annotations:
      summary: "Daily cost budget exceeded"
      description: "Total daily cost exceeds $1000"
  
  - name: LowCacheHitRate
    expr: |
      llm_cache_hit_rate < 0.6
    severity: warning
    annotations:
      summary: "Low cache hit rate"
      description: "Cache hit rate below 60%, optimization needed"
```

## 5. Alerting and Dashboards

### 5.1 Alert Rules

```yaml
# Prometheus alert rules
groups:
  - name: agent_performance
    interval: 30s
    rules:
      # Latency alerts
      - alert: HighP95Latency
        expr: |
          histogram_quantile(0.95,
            rate(agent_request_duration_seconds_bucket[5m])
          ) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency detected"
          description: "P95 latency exceeds 10 seconds"
      
      # Quality alerts
      - alert: LowTaskSuccessRate
        expr: |
          avg_over_time(agent_task_success_rate[15m]) < 0.85
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Low task success rate"
          description: "Task success rate below 85%"
      
      # Error alerts
      - alert: HighErrorRate
        expr: |
          rate(agent_requests_total{status="error"}[5m]) /
          rate(agent_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate exceeds 5%"
```

### 5.2 Grafana Dashboards

#### Dashboard 1: Agent Performance Overview

```json
{
  "dashboard": {
    "title": "Agent Performance Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(agent_requests_total[5m])",
            "legendFormat": "{{agent_role}}"
          }
        ]
      },
      {
        "title": "Latency Distribution",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(agent_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(agent_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P99"
          }
        ]
      },
      {
        "title": "Task Success Rate",
        "targets": [
          {
            "expr": "avg_over_time(agent_task_success_rate[15m])",
            "legendFormat": "{{agent_role}}"
          }
        ]
      }
    ]
  }
}
```

#### Dashboard 2: Cost Analytics

```json
{
  "dashboard": {
    "title": "Cost Analytics",
    "panels": [
      {
        "title": "Total Cost (24h)",
        "targets": [
          {
            "expr": "sum(increase(llm_cost_usd_total[24h]))",
            "legendFormat": "Total"
          }
        ]
      },
      {
        "title": "Cost by Model",
        "targets": [
          {
            "expr": "sum by (model) (rate(llm_cost_usd_total[5m]))",
            "legendFormat": "{{model}}"
          }
        ]
      },
      {
        "title": "Token Usage",
        "targets": [
          {
            "expr": "sum by (token_type) (rate(llm_tokens_total[5m]))",
            "legendFormat": "{{token_type}}"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "llm_cache_hit_rate",
            "legendFormat": "{{model}}"
          }
        ]
      }
    ]
  }
}
```

## 6. Implementation Guide

### 6.1 Quick Start

```python
# Step 1: Initialize OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Set up tracer provider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Step 2: Initialize Prometheus
from prometheus_client import start_http_server, Counter, Histogram

# Start metrics server
start_http_server(8000)

# Define metrics
request_counter = Counter(
    'agent_requests_total',
    'Total agent requests',
    ['agent_role', 'status']
)

request_duration = Histogram(
    'agent_request_duration_seconds',
    'Agent request duration',
    ['agent_role']
)

# Step 3: Instrument your agent
@request_duration.labels(agent_role='planner').time()
def execute_agent_task(task):
    with tracer.start_as_current_span("agent_task") as span:
        span.set_attribute("task_type", task.type)
        
        try:
            result = agent.execute(task)
            request_counter.labels(
                agent_role='planner',
                status='success'
            ).inc()
            return result
        except Exception as e:
            request_counter.labels(
                agent_role='planner',
                status='error'
            ).inc()
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            raise
```

### 6.2 Production Deployment

```yaml
# docker-compose.yml for monitoring stack
version: '3.8'

services:
  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
  
  # Tempo (traces)
  tempo:
    image: grafana/tempo:latest
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "3200:3200"
  
  # Prometheus (metrics)
  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
  
  # Grafana (visualization)
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"

volumes:
  tempo-data:
  prometheus-data:
  grafana-data:
```

## References

- [AI Agent Distributed Tracing Guide](https://fast.io/resources/ai-agent-distributed-tracing/)
- [OpenTelemetry for AI Systems](http://uptrace.dev/blog/opentelemetry-ai-systems)
- [Agent Observability: Cardinality Explosion](https://tianpan.co/blog/2026-04-16-agent-observability-cardinality-explosion)
- [LLM Observability in Production](https://tianpan.co/blog/2025-11-12-llm-observability-tracing-production)
- [AI Agent Observability Tools 2026](https://latitude.so/blog/ai-agent-observability-tools-2026-comparison)
