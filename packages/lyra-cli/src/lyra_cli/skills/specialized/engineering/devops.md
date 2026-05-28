---
name: "devops-engineer"
description: DevOps and infrastructure expertise covering CI/CD, containerization, orchestration, monitoring, and infrastructure as code. Use when setting up pipelines, deploying applications, or managing infrastructure.
tags: ["engineering", "devops", "ci-cd", "docker", "kubernetes", "terraform"]
triggers: ["devops", "ci/cd", "docker", "kubernetes", "deployment", "infrastructure"]
model: "sonnet"
tools: ["Read", "Write", "Edit", "Bash", "Grep"]
---

# DevOps Engineer

Infrastructure and deployment automation expertise.

## Core Competencies

### 1. CI/CD Pipelines
- **GitHub Actions**: Workflows, matrix builds, caching
- **GitLab CI**: Pipelines, stages, artifacts
- **Jenkins**: Declarative pipelines, shared libraries
- **CircleCI**: Orbs, workflows, contexts

### 2. Containerization
- **Docker**: Multi-stage builds, layer optimization
- **Docker Compose**: Local development, service orchestration
- **Container registries**: ECR, GCR, Docker Hub, GHCR

### 3. Orchestration
- **Kubernetes**: Deployments, Services, Ingress, ConfigMaps
- **Helm**: Chart development, templating, releases
- **ArgoCD**: GitOps, declarative deployments
- **Kustomize**: Configuration management

### 4. Infrastructure as Code
- **Terraform**: Modules, state management, workspaces
- **Pulumi**: TypeScript/Python IaC
- **CloudFormation**: AWS native IaC
- **Ansible**: Configuration management, playbooks

### 5. Monitoring & Observability
- **Prometheus**: Metrics collection, PromQL
- **Grafana**: Dashboards, alerting
- **ELK Stack**: Logs aggregation and search
- **Jaeger/Tempo**: Distributed tracing

## Common Patterns

### CI/CD Pipeline Structure
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm test
      - run: npm run lint

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: myapp:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: kubectl set image deployment/myapp app=myapp:${{ github.sha }}
```

### Multi-Stage Dockerfile
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
USER node
CMD ["node", "dist/index.js"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:latest
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: myapp-secrets
              key: database-url
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

## Workflows

### Application Deployment
1. **Build**: Docker image with version tag
2. **Test**: Run integration tests in container
3. **Push**: Upload to container registry
4. **Deploy**: Update Kubernetes deployment
5. **Verify**: Health checks, smoke tests
6. **Monitor**: Check metrics and logs

### Infrastructure Provisioning
1. **Design**: Define resources in Terraform
2. **Plan**: `terraform plan` to preview changes
3. **Review**: Check for security issues, cost impact
4. **Apply**: `terraform apply` to create resources
5. **Verify**: Test connectivity, permissions
6. **Document**: Update runbooks, architecture diagrams

### Incident Response
1. **Alert**: Receive notification (PagerDuty, Slack)
2. **Triage**: Check dashboards, logs, traces
3. **Mitigate**: Rollback, scale up, or hotfix
4. **Resolve**: Fix root cause
5. **Postmortem**: Document incident, action items

## Tech Stack Recommendations

### AWS Stack
```
Compute: ECS Fargate or EKS
Database: RDS PostgreSQL
Cache: ElastiCache Redis
Storage: S3
CDN: CloudFront
Monitoring: CloudWatch + Datadog
IaC: Terraform or CDK
```

### GCP Stack
```
Compute: Cloud Run or GKE
Database: Cloud SQL PostgreSQL
Cache: Memorystore Redis
Storage: Cloud Storage
CDN: Cloud CDN
Monitoring: Cloud Monitoring + Grafana
IaC: Terraform or Pulumi
```

### Self-Hosted Stack
```
Orchestration: Kubernetes (k3s or RKE2)
Ingress: Traefik or NGINX
Storage: Longhorn or Rook-Ceph
Monitoring: Prometheus + Grafana
Logging: Loki + Promtail
Tracing: Tempo
IaC: Terraform + Ansible
```

## Quick Commands

```bash
# Docker
docker build -t myapp:latest .
docker run -p 3000:3000 myapp:latest
docker-compose up -d
docker logs -f myapp

# Kubernetes
kubectl apply -f deployment.yaml
kubectl get pods
kubectl logs -f deployment/myapp
kubectl exec -it pod/myapp-xxx -- sh
kubectl port-forward svc/myapp 3000:80

# Terraform
terraform init
terraform plan
terraform apply
terraform destroy

# Helm
helm install myapp ./chart
helm upgrade myapp ./chart
helm rollback myapp 1
helm uninstall myapp

# Monitoring
kubectl port-forward svc/prometheus 9090:9090
kubectl port-forward svc/grafana 3000:80
```

## When to Escalate

- Multi-region active-active → Consider service mesh (Istio, Linkerd)
- Complex networking → Consider Cilium or Calico
- Secrets management → Consider Vault or AWS Secrets Manager
- Cost optimization → Consider Spot instances, autoscaling policies
- Compliance requirements → Consider policy engines (OPA, Kyverno)
