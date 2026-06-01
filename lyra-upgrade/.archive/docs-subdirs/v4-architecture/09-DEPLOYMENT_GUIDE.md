# Lyra v4.0 Deployment Guide

**Version**: 1.0  
**Status**: 🚧 Draft  
**Last Updated**: 2026-05-21

---

## Overview

Complete deployment guide for Lyra v4.0 covering local development, staging, and production environments. This document provides step-by-step instructions for deploying, configuring, and maintaining Lyra.

---

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Local Development](#local-development)
3. [Staging Environment](#staging-environment)
4. [Production Deployment](#production-deployment)
5. [Configuration Management](#configuration-management)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Deployment Options

### Deployment Modes

1. **Local Development**
   - Single machine
   - Development and testing
   - Hot reload enabled

2. **Staging**
   - Pre-production testing
   - Production-like environment
   - Integration testing

3. **Production**
   - Live deployment
   - High availability
   - Full monitoring

### Architecture Options

```
┌─────────────────────────────────────┐
│         Standalone Mode             │
│  ┌──────────────────────────────┐  │
│  │      Lyra Instance           │  │
│  │  ┌────────┐  ┌────────┐     │  │
│  │  │ Memory │  │ Agents │     │  │
│  │  └────────┘  └────────┘     │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         Distributed Mode            │
│  ┌──────────┐      ┌──────────┐    │
│  │  Node 1  │◄────►│  Node 2  │    │
│  │ (Primary)│      │(Specialist)│   │
│  └──────────┘      └──────────┘    │
│       ▲                 ▲           │
│       │                 │           │
│       └────────┬────────┘           │
│                │                    │
│         ┌──────▼──────┐             │
│         │   Storage   │             │
│         └─────────────┘             │
└─────────────────────────────────────┘
```

---

## Local Development

### Prerequisites

```bash
# System requirements
- Python 3.11+
- pip 23+
- Git 2.40+
- 8GB+ RAM
- 10GB+ disk space

# Optional
- Docker 24+ (for containerized deployment)
- Node.js 18+ (for tooling)
```

### Installation

#### Step 1: Clone Repository

```bash
# Clone repository
git clone https://github.com/your-org/lyra.git
cd lyra

# Checkout v4.0 branch
git checkout v4.0
```

#### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Unix/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .
```

#### Step 4: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env
```

**File**: `.env`

```bash
# API Keys
ANTHROPIC_API_KEY=your-api-key-here

# Paths
LYRA_HOME_DIR=~/.lyra
LYRA_DATA_DIR=~/.lyra/data
LYRA_CACHE_DIR=~/.lyra/cache

# Memory
LYRA_MEMORY_MAX_SIZE_MB=500

# Agents
LYRA_MAX_CONCURRENT_AGENTS=5
LYRA_AGENT_TIMEOUT_SECONDS=300

# Budget
LYRA_DEFAULT_MAX_COST_USD=10.0
LYRA_DEFAULT_MAX_TIME_SECONDS=3600

# Safety
LYRA_REQUIRE_APPROVAL_FOR_DESTRUCTIVE=true
LYRA_ENABLE_AUDIT_LOGGING=true

# Logging
LYRA_LOG_LEVEL=INFO
LYRA_LOG_FILE=~/.lyra/logs/lyra.log
```

#### Step 5: Initialize Database

```bash
# Initialize database
lyra init

# Verify installation
lyra --version
lyra doctor
```

#### Step 6: Run Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit
pytest tests/integration

# With coverage
pytest --cov=lyra --cov-report=html
```

### Development Workflow

```bash
# Start development server
lyra serve --dev --reload

# Run in interactive mode
lyra interactive

# Run specific command
lyra execute "Create a Python function"

# View logs
tail -f ~/.lyra/logs/lyra.log
```

### Hot Reload

```bash
# Enable hot reload for development
lyra serve --dev --reload --port 8000

# Watch for file changes
watchmedo auto-restart \
  --directory=./src \
  --pattern="*.py" \
  --recursive \
  -- lyra serve
```

---

## Staging Environment

### Setup

#### Step 1: Provision Server

```bash
# Recommended specs
- 4 CPU cores
- 16GB RAM
- 50GB SSD
- Ubuntu 22.04 LTS

# SSH into server
ssh user@staging-server
```

#### Step 2: Install System Dependencies

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Git
sudo apt install -y git

# Install system libraries
sudo apt install -y \
  build-essential \
  libssl-dev \
  libffi-dev \
  python3-dev
```

#### Step 3: Create Service User

```bash
# Create lyra user
sudo useradd -m -s /bin/bash lyra
sudo usermod -aG sudo lyra

# Switch to lyra user
sudo su - lyra
```

#### Step 4: Deploy Application

```bash
# Clone repository
cd /home/lyra
git clone https://github.com/your-org/lyra.git
cd lyra
git checkout v4.0

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure environment
cp .env.example .env
nano .env
```

#### Step 5: Configure Systemd Service

**File**: `/etc/systemd/system/lyra.service`

```ini
[Unit]
Description=Lyra v4.0 AI Assistant
After=network.target

[Service]
Type=simple
User=lyra
Group=lyra
WorkingDirectory=/home/lyra/lyra
Environment="PATH=/home/lyra/lyra/venv/bin"
ExecStart=/home/lyra/lyra/venv/bin/lyra serve --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lyra

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/lyra/.lyra

[Install]
WantedBy=multi-user.target
```

#### Step 6: Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable lyra

# Start service
sudo systemctl start lyra

# Check status
sudo systemctl status lyra

# View logs
sudo journalctl -u lyra -f
```

#### Step 7: Configure Nginx Reverse Proxy

**File**: `/etc/nginx/sites-available/lyra`

```nginx
server {
    listen 80;
    server_name staging.lyra.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/lyra /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

#### Step 8: Configure SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d staging.lyra.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

---

## Production Deployment

### High Availability Setup

#### Architecture

```
                    ┌──────────────┐
                    │ Load Balancer│
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
       ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
       │ Node 1  │    │ Node 2  │   │ Node 3  │
       │(Primary)│    │(Primary)│   │(Primary)│
       └────┬────┘    └────┬────┘   └────┬────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                    ┌──────▼───────┐
                    │   Database   │
                    │  (Replicated)│
                    └──────────────┘
```

#### Step 1: Database Setup

**PostgreSQL for Production** (instead of SQLite)

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE DATABASE lyra_prod;
CREATE USER lyra WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE lyra_prod TO lyra;
\q

# Configure connection
# In .env:
LYRA_DATABASE_URL=postgresql://lyra:secure-password@localhost/lyra_prod
```

#### Step 2: Redis for Caching

```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: maxmemory 2gb
# Set: maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis

# Configure in .env:
LYRA_REDIS_URL=redis://localhost:6379/0
```

#### Step 3: Load Balancer (HAProxy)

**File**: `/etc/haproxy/haproxy.cfg`

```
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5000
    timeout client  300000
    timeout server  300000

frontend lyra_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/lyra.pem
    default_backend lyra_backend

backend lyra_backend
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    
    server node1 10.0.1.10:8000 check
    server node2 10.0.1.11:8000 check
    server node3 10.0.1.12:8000 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
```

#### Step 4: Monitoring Setup

**Prometheus Configuration**

**File**: `/etc/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'lyra'
    static_configs:
      - targets:
        - 'localhost:8000'
        - '10.0.1.10:8000'
        - '10.0.1.11:8000'
        - '10.0.1.12:8000'
    
    metrics_path: '/metrics'
```

**Grafana Dashboard**

```bash
# Install Grafana
sudo apt install -y grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Access: http://server:3000
# Default: admin/admin
```

#### Step 5: Backup Strategy

**Automated Backups**

**File**: `/usr/local/bin/lyra-backup.sh`

```bash
#!/bin/bash

# Configuration
BACKUP_DIR="/var/backups/lyra"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump lyra_prod | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Backup data directory
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" /home/lyra/.lyra/data

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" /home/lyra/lyra/.env

# Remove old backups
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete

# Upload to S3 (optional)
# aws s3 sync "$BACKUP_DIR" s3://lyra-backups/

echo "Backup completed: $DATE"
```

**Cron Job**

```bash
# Add to crontab
sudo crontab -e

# Daily backup at 2 AM
0 2 * * * /usr/local/bin/lyra-backup.sh >> /var/log/lyra-backup.log 2>&1
```

---

## Configuration Management

### Environment Variables

**Production Configuration**

```bash
# API Keys
ANTHROPIC_API_KEY=prod-api-key

# Database
LYRA_DATABASE_URL=postgresql://lyra:password@db-server/lyra_prod
LYRA_REDIS_URL=redis://redis-server:6379/0

# Paths
LYRA_HOME_DIR=/var/lib/lyra
LYRA_DATA_DIR=/var/lib/lyra/data
LYRA_CACHE_DIR=/var/cache/lyra

# Memory
LYRA_MEMORY_MAX_SIZE_MB=2000

# Agents
LYRA_MAX_CONCURRENT_AGENTS=20
LYRA_AGENT_TIMEOUT_SECONDS=600

# Budget
LYRA_DEFAULT_MAX_COST_USD=50.0
LYRA_DEFAULT_MAX_TIME_SECONDS=7200

# Safety
LYRA_REQUIRE_APPROVAL_FOR_DESTRUCTIVE=true
LYRA_ENABLE_AUDIT_LOGGING=true

# Logging
LYRA_LOG_LEVEL=WARNING
LYRA_LOG_FILE=/var/log/lyra/lyra.log

# Performance
LYRA_WORKER_PROCESSES=4
LYRA_WORKER_THREADS=2

# Security
LYRA_ENABLE_RATE_LIMITING=true
LYRA_MAX_REQUESTS_PER_MINUTE=60
```

### Secrets Management

**Using Environment Variables**

```bash
# Store secrets in secure location
sudo mkdir -p /etc/lyra/secrets
sudo chmod 700 /etc/lyra/secrets

# Create secrets file
sudo nano /etc/lyra/secrets/api_keys

# Load in systemd service
# Add to [Service] section:
EnvironmentFile=/etc/lyra/secrets/api_keys
```

**Using HashiCorp Vault** (Advanced)

```bash
# Install Vault
wget https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip
unzip vault_1.15.0_linux_amd64.zip
sudo mv vault /usr/local/bin/

# Start Vault
vault server -dev

# Store secret
vault kv put secret/lyra/api_key value="your-api-key"

# Retrieve in application
vault kv get -field=value secret/lyra/api_key
```

---

## Monitoring & Maintenance

### Health Checks

**Endpoint**: `/health`

```python
# Health check implementation
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    checks = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0",
        "components": {
            "memory": await check_memory_health(),
            "agents": await check_agents_health(),
            "database": await check_database_health()
        }
    }
    
    # Overall status
    if any(c["status"] != "healthy" for c in checks["components"].values()):
        checks["status"] = "degraded"
    
    return checks
```

### Metrics Collection

**Prometheus Metrics**

```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'lyra_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'lyra_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

# Agent metrics
active_agents = Gauge(
    'lyra_active_agents',
    'Number of active agents'
)

# Memory metrics
memory_size = Gauge(
    'lyra_memory_size_bytes',
    'Memory system size'
)
```

### Log Management

**Structured Logging**

```python
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "request_processed",
    user_id=user_id,
    request_id=request_id,
    duration=duration,
    status="success"
)
```

**Log Aggregation (ELK Stack)**

```bash
# Install Filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.10.0-amd64.deb
sudo dpkg -i filebeat-8.10.0-amd64.deb

# Configure Filebeat
sudo nano /etc/filebeat/filebeat.yml
```

**File**: `/etc/filebeat/filebeat.yml`

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/lyra/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "lyra-%{+yyyy.MM.dd}"

setup.kibana:
  host: "kibana:5601"
```

### Alerting

**Alertmanager Configuration**

**File**: `/etc/alertmanager/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-notifications'

receivers:
- name: 'team-notifications'
  email_configs:
  - to: 'team@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.example.com:587'
  
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#alerts'
    title: 'Lyra Alert'
```

**Alert Rules**

**File**: `/etc/prometheus/rules/lyra.yml`

```yaml
groups:
- name: lyra
  interval: 30s
  rules:
  
  # High error rate
  - alert: HighErrorRate
    expr: rate(lyra_requests_total{status="error"}[5m]) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors/sec"
  
  # High memory usage
  - alert: HighMemoryUsage
    expr: lyra_memory_size_bytes > 2000000000
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }} bytes"
  
  # Service down
  - alert: ServiceDown
    expr: up{job="lyra"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Lyra service is down"
      description: "Service {{ $labels.instance }} is down"
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Service Won't Start

```bash
# Check logs
sudo journalctl -u lyra -n 50

# Check configuration
lyra config validate

# Check permissions
ls -la /home/lyra/.lyra

# Test manually
sudo -u lyra /home/lyra/lyra/venv/bin/lyra serve
```

#### Issue 2: High Memory Usage

```bash
# Check memory usage
ps aux | grep lyra

# Check memory system
lyra memory stats

# Clear cache
lyra cache clear

# Restart service
sudo systemctl restart lyra
```

#### Issue 3: Database Connection Issues

```bash
# Test database connection
psql -U lyra -d lyra_prod -h localhost

# Check connection pool
lyra db pool-status

# Reset connections
lyra db reset-connections
```

#### Issue 4: Slow Performance

```bash
# Check system resources
top
htop
iotop

# Check database performance
lyra db analyze

# Check agent status
lyra agents status

# Enable profiling
lyra serve --profile
```

### Debug Mode

```bash
# Enable debug logging
export LYRA_LOG_LEVEL=DEBUG

# Run with profiling
lyra serve --debug --profile

# Interactive debugging
lyra debug --interactive
```

### Recovery Procedures

#### Database Recovery

```bash
# Stop service
sudo systemctl stop lyra

# Restore from backup
gunzip < /var/backups/lyra/db_20260521_020000.sql.gz | psql lyra_prod

# Verify data
psql lyra_prod -c "SELECT COUNT(*) FROM memories;"

# Start service
sudo systemctl start lyra
```

#### Configuration Recovery

```bash
# Restore configuration
tar -xzf /var/backups/lyra/config_20260521_020000.tar.gz -C /

# Verify configuration
lyra config validate

# Restart service
sudo systemctl restart lyra
```

---

## Summary

This deployment guide provides:
- ✅ Complete deployment instructions
- ✅ Local, staging, and production setups
- ✅ High availability configuration
- ✅ Monitoring and alerting
- ✅ Backup and recovery procedures
- ✅ Troubleshooting guide

**Key Points**:
- Start with local development
- Test thoroughly in staging
- Deploy to production with monitoring
- Maintain regular backups
- Monitor health and performance

---

**Related Documents**:
- `06-IMPLEMENTATION_GUIDE.md`: Implementation details
- `08-TESTING_STRATEGY.md`: Testing procedures
- `05-SAFETY_GOVERNANCE.md`: Safety configuration
