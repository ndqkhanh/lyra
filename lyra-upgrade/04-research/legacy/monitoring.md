# Monitoring, Tracing, and Reliability Guide

This guide covers Lyra's infrastructure for monitoring, distributed tracing, and reliability patterns.

## Table of Contents

- [Overview](#overview)
- [Monitoring](#monitoring)
- [Distributed Tracing](#distributed-tracing)
- [Reliability Patterns](#reliability-patterns)
- [Health Checks](#health-checks)
- [Performance Profiling](#performance-profiling)
- [Integration Guide](#integration-guide)
- [Best Practices](#best-practices)

## Overview

Lyra's infrastructure module provides production-grade observability and reliability:

- **Monitoring**: Metrics collection, dashboards, and alerting
- **Tracing**: Distributed tracing across agents and tools
- **Reliability**: Circuit breakers, retries, and fallbacks
- **Health**: Health checks and diagnostics
- **Profiling**: Performance analysis and optimization

## Monitoring

### Metrics Collection

The monitoring system supports multiple metric types:

```python
from lyra_cli.infrastructure import MonitoringService, MetricType

# Initialize monitoring service
monitoring = MonitoringService()

# Record metrics
monitoring.metrics.increment("agent.tasks.completed", 1.0)
monitoring.metrics.set_gauge("system.active_agents", 5.0)
monitoring.metrics.observe("agent.response_time", 250.0)

# Get metric summary
summary = monitoring.metrics.get_metric_summary("agent.response_time")
print(f"Average response time: {summary['average']:.2f}ms")
print(f"P95: {summary['p95']:.2f}ms")
```

### Metric Types

1. **Counter**: Monotonically increasing values (tasks completed, requests)
2. **Gauge**: Point-in-time values (active agents, memory usage)
3. **Histogram**: Distribution of values (response times, payload sizes)
4. **Summary**: Statistical summaries (percentiles, averages)

### Custom Metrics

Register custom metrics for your application:

```python
from lyra_cli.infrastructure import MetricsCollector, MetricType

collector = MetricsCollector()

# Register custom metric
collector.register_metric(
    name="custom.api.requests",
    metric_type=MetricType.COUNTER,
    description="Number of API requests",
    unit="count",
    labels={"service": "api", "env": "production"},
)

# Record with additional labels
collector.record(
    "custom.api.requests",
    1.0,
    labels={"endpoint": "/users", "status": "200"},
)
```

### Alerting

Configure alerts based on metric thresholds:

```python
from lyra_cli.infrastructure import AlertSeverity

# Add threshold-based alert
monitoring.alerts.add_threshold_rule(
    name="high_error_rate",
    metric_name="system.error_rate",
    threshold=10.0,
    operator=">",
    severity=AlertSeverity.WARNING,
    message="Error rate exceeded 10%",
)

# Register callback for alert notifications
def alert_callback(alert):
    print(f"ALERT: {alert.name} - {alert.message}")
    # Send to Slack, PagerDuty, etc.

monitoring.alerts.register_callback(alert_callback)

# Check alerts periodically
active_alerts = monitoring.alerts.check_rules()
```

### Dashboard Data

Get comprehensive dashboard data:

```python
dashboard = monitoring.get_dashboard_data()

print(f"System Status: {dashboard['metrics']['system.error_rate']['latest']}")
print(f"Active Alerts: {len(dashboard['alerts'])}")

for alert in dashboard['alerts']:
    print(f"  - {alert['name']}: {alert['message']}")
```

## Distributed Tracing

### Basic Tracing

Track operations across agents and tools:

```python
from lyra_cli.infrastructure import DistributedTracer, SpanKind

tracer = DistributedTracer()

# Start a trace
trace_id = tracer.start_trace()

# Create spans
span = tracer.start_span(
    name="process_request",
    kind=SpanKind.SERVER,
    trace_id=trace_id,
)

# Add attributes
span.set_attribute("user_id", "user123")
span.set_attribute("request_size", 1024)

# Add events
span.add_event("validation_complete", {"valid": True})

# End span
tracer.end_span(span)
```

### Context Manager

Use context managers for automatic span lifecycle:

```python
with tracer.trace_span("agent_execution") as span:
    span.set_attribute("agent_type", "executor")
    
    # Nested spans automatically track parent-child relationships
    with tracer.trace_span("llm_call") as llm_span:
        llm_span.set_attribute("model", "claude-sonnet-4")
        # LLM call here
```

### Error Tracking

Spans automatically capture errors:

```python
try:
    with tracer.trace_span("risky_operation") as span:
        raise ValueError("Something went wrong")
except ValueError:
    # Span status is automatically set to ERROR
    # Error details are captured in attributes
    pass
```

### Exporting Traces

Export traces for analysis:

```python
from lyra_cli.infrastructure import TraceExporter

exporter = TraceExporter(tracer)

# Export to JSON
trace_data = exporter.export_to_json(trace_id)

# Export to OpenTelemetry format
otel_data = exporter.export_to_opentelemetry(trace_id)

# Export all traces
all_traces = exporter.export_all_traces()
```

### Integration with Existing Tracing

Integrate with Lyra's existing tracing callbacks:

```python
from lyra_cli.tracing.base import TracingHub, TurnTrace

# Create custom callback
class InfrastructureTracingCallback:
    def __init__(self, tracer):
        self.tracer = tracer
    
    def on_turn_start(self, trace: TurnTrace):
        self.tracer.start_span(
            name=f"turn_{trace.trace_id}",
            attributes={
                "session_id": trace.session_id,
                "model": trace.model,
            },
        )
    
    def on_turn_end(self, trace: TurnTrace):
        # End span and record metrics
        pass

# Register with tracing hub
hub = TracingHub()
hub.add(InfrastructureTracingCallback(tracer))
```

## Reliability Patterns

### Circuit Breaker

Prevent cascading failures:

```python
from lyra_cli.infrastructure import CircuitBreaker, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 failures
    success_threshold=2,      # Close after 2 successes
    timeout_seconds=60.0,     # Try recovery after 60s
)

cb = CircuitBreaker("external_api", config)

# Use circuit breaker
try:
    result = cb.call(external_api_call, arg1, arg2)
except CircuitBreakerOpenError:
    # Circuit is open, use fallback
    result = fallback_response()
```

### Retry Policy

Automatic retries with exponential backoff:

```python
from lyra_cli.infrastructure import RetryPolicy, RetryConfig

# Configure retry policy
config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,        # Start with 1s delay
    max_delay=60.0,           # Cap at 60s
    exponential_base=2.0,     # Double delay each time
    jitter=True,              # Add randomness
)

policy = RetryPolicy(config)

# Execute with retries
result = policy.execute(flaky_function, arg1, arg2)

# Async support
result = await policy.execute_async(async_flaky_function, arg1, arg2)
```

### Fallback

Graceful degradation:

```python
from lyra_cli.infrastructure import Fallback

def primary_service():
    # Try primary service
    return call_primary_api()

def fallback_service():
    # Use cached data or alternative service
    return get_cached_data()

fallback = Fallback(primary_service, fallback_service, name="api_fallback")
result = fallback.execute()
```

### Combined Reliability

Use all patterns together:

```python
from lyra_cli.infrastructure import ReliabilityManager

manager = ReliabilityManager()

# Configure components
cb_config = CircuitBreakerConfig(failure_threshold=3)
retry_config = RetryConfig(max_attempts=3)

manager.get_circuit_breaker("api", cb_config)
manager.get_retry_policy("api", retry_config)

# Execute with all patterns
result = manager.execute_with_reliability(
    api_call,
    circuit_breaker_name="api",
    retry_policy_name="api",
    fallback_func=fallback_func,
    arg1, arg2,
)

# Check status
status = manager.get_status()
print(f"Circuit breaker state: {status['circuit_breakers']['api']['state']}")
```

## Health Checks

### Basic Health Checks

Monitor service health:

```python
from lyra_cli.infrastructure import HealthCheckRegistry, HealthStatus

registry = HealthCheckRegistry()

# Register simple boolean check
registry.register_simple(
    "database",
    lambda: check_database_connection(),
    critical=True,
)

# Register custom check
def check_api_health():
    from lyra_cli.infrastructure.health import HealthCheckResult
    
    try:
        response = ping_api()
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="API responding",
            details={"latency_ms": response.latency},
        )
    except Exception as e:
        return HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message=f"API unreachable: {e}",
        )

from lyra_cli.infrastructure.health import HealthCheck
registry.register(HealthCheck("api", check_api_health))
```

### Readiness and Liveness

Separate readiness and liveness checks:

```python
# Readiness: Can the service accept traffic?
registry.register_simple(
    "database_ready",
    lambda: database.is_connected(),
    readiness=True,
    liveness=False,
)

# Liveness: Is the service alive?
registry.register_simple(
    "heartbeat",
    lambda: True,  # Simple heartbeat
    readiness=False,
    liveness=True,
)

# Check readiness
readiness = registry.get_readiness_report()
if readiness["ready"]:
    print("Service ready to accept traffic")

# Check liveness
liveness = registry.get_liveness_report()
if not liveness["alive"]:
    print("Service needs restart")
```

### Health Reports

Get comprehensive health reports:

```python
report = registry.get_health_report()

print(f"Overall Status: {report['status']}")
print(f"Healthy: {report['summary']['healthy']}")
print(f"Unhealthy: {report['summary']['unhealthy']}")

for name, check in report['checks'].items():
    print(f"{name}: {check['status']} - {check['message']}")
```

### Default Health Checks

Use built-in system health checks:

```python
from lyra_cli.infrastructure.health import create_default_health_checks

registry = create_default_health_checks()

# Includes:
# - System health (CPU, memory)
# - Disk space
# - More...

report = registry.get_health_report()
```

## Performance Profiling

### Basic Profiling

Profile code execution:

```python
from lyra_cli.infrastructure import PerformanceProfiler

profiler = PerformanceProfiler(enable_memory_profiling=True)

# Context manager
with profiler.profile("expensive_operation"):
    # Code to profile
    process_large_dataset()

# Decorator
@profiler.profile_function("data_processing")
def process_data(data):
    # Processing logic
    return result

# Manual start/stop
profiler.start_profiling("manual_profile")
# ... work ...
profiler.stop_profiling("manual_profile")
```

### Profile Reports

Generate profiling reports:

```python
# Get specific profile
profile = profiler.get_profile("expensive_operation")
print(f"Duration: {profile.duration_ms:.2f}ms")
print(f"Calls: {profile.call_count}")
print(f"Memory Peak: {profile.memory_peak_mb:.2f}MB")

# Generate comprehensive report
report = profiler.generate_report(bottleneck_threshold_ms=100.0)

print(f"Total Duration: {report.total_duration_ms:.2f}ms")
print("\nBottlenecks:")
for bottleneck in report.bottlenecks:
    print(f"  {bottleneck['name']}: {bottleneck['duration_ms']:.2f}ms "
          f"({bottleneck['percentage']:.1f}%)")

# Print detailed stats
profiler.print_stats("expensive_operation", sort_by="cumulative", limit=20)
```

### System Profiling

Profile system resources:

```python
from lyra_cli.infrastructure.profiler import profile_memory_usage, profile_cpu_usage

# Memory usage
memory = profile_memory_usage()
print(f"RSS: {memory['rss_mb']:.2f}MB")
print(f"Memory %: {memory['percent']:.1f}%")

# CPU usage
cpu = profile_cpu_usage()
print(f"CPU %: {cpu['percent']:.1f}%")
print(f"Threads: {cpu['num_threads']}")
```

## Integration Guide

### Complete Integration Example

```python
from lyra_cli.infrastructure import (
    MonitoringService,
    DistributedTracer,
    ReliabilityManager,
    HealthCheckRegistry,
    PerformanceProfiler,
)

class InfrastructureManager:
    """Unified infrastructure management."""
    
    def __init__(self):
        self.monitoring = MonitoringService()
        self.tracer = DistributedTracer()
        self.reliability = ReliabilityManager()
        self.health = HealthCheckRegistry()
        self.profiler = PerformanceProfiler()
        
        self._setup_health_checks()
    
    def _setup_health_checks(self):
        """Setup health checks."""
        self.health.register_simple(
            "monitoring",
            lambda: True,
            critical=True,
        )
    
    def execute_agent_task(self, task_name, task_func, *args, **kwargs):
        """Execute agent task with full observability."""
        # Start trace
        with self.tracer.trace_span(f"agent_task_{task_name}") as span:
            span.set_attribute("task_name", task_name)
            
            # Profile execution
            with self.profiler.profile(task_name):
                try:
                    # Execute with reliability
                    result = self.reliability.execute_with_reliability(
                        task_func,
                        circuit_breaker_name=f"agent_{task_name}",
                        retry_policy_name="default",
                        *args,
                        **kwargs,
                    )
                    
                    # Record success metrics
                    self.monitoring.metrics.increment("agent.tasks.completed")
                    span.set_attribute("status", "success")
                    
                    return result
                    
                except Exception as e:
                    # Record failure metrics
                    self.monitoring.metrics.increment("agent.tasks.failed")
                    span.set_attribute("status", "error")
                    span.set_attribute("error", str(e))
                    raise

# Usage
infra = InfrastructureManager()

def my_agent_task(data):
    # Agent logic
    return process(data)

result = infra.execute_agent_task("process_data", my_agent_task, data)
```

### Integration with Existing Logging

```python
from lyra_cli.logging_config import get_logger
from lyra_cli.infrastructure import MonitoringService

logger = get_logger(__name__)
monitoring = MonitoringService()

def monitored_operation():
    logger.info("Starting operation")
    monitoring.metrics.increment("operations.started")
    
    try:
        # Operation logic
        result = perform_operation()
        
        logger.info("Operation completed")
        monitoring.metrics.increment("operations.completed")
        
        return result
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        monitoring.metrics.increment("operations.failed")
        raise
```

## Best Practices

### Monitoring

1. **Use appropriate metric types**: Counters for cumulative values, gauges for snapshots, histograms for distributions
2. **Add meaningful labels**: Use labels for dimensions (service, endpoint, status)
3. **Set alert thresholds carefully**: Avoid alert fatigue with appropriate thresholds
4. **Monitor what matters**: Focus on user-facing metrics and SLIs

### Tracing

1. **Trace critical paths**: Focus on user-facing operations and cross-service calls
2. **Add context**: Use attributes to add relevant context to spans
3. **Keep spans focused**: Each span should represent a single logical operation
4. **Propagate context**: Ensure trace context flows across async boundaries

### Reliability

1. **Use circuit breakers for external services**: Protect against cascading failures
2. **Configure retries appropriately**: Use exponential backoff with jitter
3. **Implement fallbacks**: Always have a degraded mode
4. **Monitor reliability patterns**: Track circuit breaker states and retry counts

### Health Checks

1. **Keep checks fast**: Health checks should complete in <100ms
2. **Separate readiness and liveness**: Different concerns require different checks
3. **Mark critical checks**: Distinguish between critical and non-critical checks
4. **Include dependencies**: Check external dependencies (database, APIs)

### Profiling

1. **Profile in production**: Use sampling to minimize overhead
2. **Focus on bottlenecks**: Identify and optimize the slowest operations
3. **Monitor memory**: Track memory usage to prevent leaks
4. **Profile regularly**: Make profiling part of your development workflow

## Troubleshooting

### High Memory Usage

```python
from lyra_cli.infrastructure.profiler import profile_memory_usage

memory = profile_memory_usage()
if memory['percent'] > 80:
    print("High memory usage detected")
    # Investigate with profiler
    profiler.print_stats(sort_by="cumulative")
```

### Circuit Breaker Stuck Open

```python
# Check circuit breaker status
status = reliability.get_status()
cb_status = status['circuit_breakers']['api']

if cb_status['state'] == 'open':
    print(f"Circuit open with {cb_status['failure_count']} failures")
    # Manually reset if needed
    reliability.get_circuit_breaker('api').reset()
```

### Missing Traces

```python
# Verify trace context propagation
context = tracer.get_current_context()
if context is None:
    print("No active trace context")
    # Start new trace
    trace_id = tracer.start_trace()
```

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Health Check API](https://microservices.io/patterns/observability/health-check-api.html)
