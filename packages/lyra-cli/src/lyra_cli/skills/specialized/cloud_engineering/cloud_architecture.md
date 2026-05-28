---
name: "cloud-architect"
description: Cloud architecture expertise covering AWS, GCP, Azure, Kubernetes, Terraform, and cloud-native patterns. Use when designing cloud infrastructure, migrating to cloud, or optimizing cloud costs.
tags: ["cloud", "aws", "gcp", "azure", "kubernetes", "terraform"]
triggers: ["cloud", "aws", "gcp", "azure", "kubernetes", "terraform", "cloud architecture"]
model: "sonnet"
tools: ["Read", "Write", "Edit", "Bash"]
---

# Cloud Architect

Cloud infrastructure design and implementation across AWS, GCP, and Azure.

## Core Competencies

### 1. Cloud Platforms
- **AWS**: EC2, ECS, EKS, Lambda, RDS, S3, CloudFront
- **GCP**: Compute Engine, GKE, Cloud Run, Cloud SQL, Cloud Storage
- **Azure**: VMs, AKS, Functions, SQL Database, Blob Storage

### 2. Infrastructure as Code
- **Terraform**: Modules, state management, workspaces
- **Pulumi**: TypeScript/Python IaC
- **CloudFormation**: AWS native
- **ARM Templates**: Azure native

### 3. Container Orchestration
- **Kubernetes**: Deployments, Services, Ingress, StatefulSets
- **Helm**: Chart development and management
- **ArgoCD**: GitOps deployments
- **Service Mesh**: Istio, Linkerd

### 4. Networking
- **VPC**: Subnets, routing, NAT gateways
- **Load Balancing**: ALB, NLB, Cloud Load Balancer
- **DNS**: Route 53, Cloud DNS, Azure DNS
- **CDN**: CloudFront, Cloud CDN, Azure CDN

### 5. Security
- **IAM**: Roles, policies, service accounts
- **Secrets Management**: AWS Secrets Manager, GCP Secret Manager, Vault
- **Network Security**: Security groups, NACLs, firewall rules
- **Compliance**: SOC 2, HIPAA, PCI-DSS

## Cloud Architecture Patterns

### Multi-Tier Architecture
```
Internet
    ↓
CloudFront (CDN)
    ↓
Application Load Balancer
    ↓
┌─────────────────────────────┐
│  Auto Scaling Group (EC2)   │
│  Web/App Tier               │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│  RDS (Primary + Replica)    │
│  Database Tier              │
└─────────────────────────────┘
    ↓
S3 (Static Assets)
```

### Serverless Architecture
```
API Gateway
    ↓
Lambda Functions
    ↓
┌──────────┬──────────┬──────────┐
│ DynamoDB │   S3     │   SQS    │
└──────────┴──────────┴──────────┘
```

### Microservices on Kubernetes
```
Ingress Controller
    ↓
┌─────────┬─────────┬─────────┐
│ Service │ Service │ Service │
│    A    │    B    │    C    │
└─────────┴─────────┴─────────┘
    ↓         ↓         ↓
┌─────────┬─────────┬─────────┐
│  DB A   │  DB B   │  DB C   │
└─────────┴─────────┴─────────┘
```

## AWS Reference Architecture

### Highly Available Web Application
```hcl
# Terraform configuration

# VPC with public and private subnets
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "production-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
}

# Application Load Balancer
resource "aws_lb" "app" {
  name               = "app-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets
}

# Auto Scaling Group
resource "aws_autoscaling_group" "app" {
  name                = "app-asg"
  vpc_zone_identifier = module.vpc.private_subnets
  target_group_arns   = [aws_lb_target_group.app.arn]
  health_check_type   = "ELB"
  
  min_size         = 2
  max_size         = 10
  desired_capacity = 3
  
  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}

# RDS Database
resource "aws_db_instance" "main" {
  identifier           = "production-db"
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  storage_encrypted    = true
  
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  multi_az               = true
  backup_retention_period = 7
  skip_final_snapshot    = false
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "production-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
}

# S3 Bucket for static assets
resource "aws_s3_bucket" "assets" {
  bucket = "production-assets"
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "cdn" {
  origin {
    domain_name = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_id   = "S3-assets"
    
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main.cloudfront_access_identity_path
    }
  }
  
  enabled             = true
  default_root_object = "index.html"
  
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-assets"
    
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
```

## Kubernetes Deployment

### Production-Ready Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
        version: v1.2.3
    spec:
      serviceAccountName: api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: api
        image: myregistry/api:v1.2.3
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: api-config
              key: redis-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: production
spec:
  type: ClusterIP
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8080
    name: http
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Cost Optimization

### Strategies
```
1. Right-sizing:
   - Analyze utilization metrics
   - Downsize over-provisioned instances
   - Use burstable instances (t3, t4g)

2. Reserved Instances / Savings Plans:
   - 1-year or 3-year commitment
   - 30-70% savings
   - Use for baseline capacity

3. Spot Instances:
   - 70-90% discount
   - Use for batch jobs, stateless workloads
   - Combine with on-demand for reliability

4. Auto-scaling:
   - Scale down during off-peak hours
   - Use predictive scaling
   - Set appropriate min/max limits

5. Storage Optimization:
   - Use lifecycle policies (S3 → Glacier)
   - Delete unused snapshots
   - Compress data
   - Use appropriate storage class

6. Network Optimization:
   - Use VPC endpoints (avoid NAT gateway costs)
   - Minimize cross-region traffic
   - Use CloudFront for static assets
```

### Cost Monitoring
```bash
# AWS Cost Explorer CLI
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Set budget alerts
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

## Security Best Practices

### IAM Policies
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
    }
  ]
}
```

### Secrets Management
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name production/database/password \
  --secret-string "super-secret-password"

# Retrieve in application
aws secretsmanager get-secret-value \
  --secret-id production/database/password \
  --query SecretString \
  --output text
```

### Network Security
```
VPC Security:
- Private subnets for application and database
- Public subnets only for load balancers
- NAT gateway for outbound internet access
- VPC endpoints for AWS services

Security Groups:
- Least privilege (only required ports)
- Source IP restrictions
- Separate groups per tier

NACLs:
- Stateless firewall rules
- Deny rules for known bad IPs
- Allow rules for required traffic
```

## Migration Strategies

### Lift and Shift (Rehost)
```
1. Assess current infrastructure
2. Provision equivalent cloud resources
3. Migrate data and applications
4. Test and validate
5. Cutover to cloud

Pros: Fast, low risk
Cons: No cloud optimization
```

### Replatform
```
1. Identify optimization opportunities
2. Migrate to managed services (RDS, ElastiCache)
3. Containerize applications
4. Implement auto-scaling
5. Optimize costs

Pros: Some optimization, moderate effort
Cons: Requires refactoring
```

### Refactor (Cloud-Native)
```
1. Redesign for cloud-native patterns
2. Microservices architecture
3. Serverless where appropriate
4. Event-driven architecture
5. Full automation

Pros: Maximum cloud benefits
Cons: High effort, high risk
```

## Quick Commands

```bash
# AWS CLI
aws ec2 describe-instances
aws s3 ls s3://my-bucket
aws rds describe-db-instances
aws eks update-kubeconfig --name my-cluster

# Terraform
terraform init
terraform plan
terraform apply
terraform destroy

# Kubernetes
kubectl get pods -n production
kubectl logs -f deployment/api
kubectl exec -it pod/api-xxx -- sh
kubectl port-forward svc/api 8080:80

# Helm
helm install myapp ./chart
helm upgrade myapp ./chart
helm rollback myapp 1
```

## When to Escalate

- Multi-cloud strategy → Consider cloud-agnostic tools (Terraform, Kubernetes)
- Hybrid cloud → Consider VPN, Direct Connect, ExpressRoute
- Compliance requirements → Engage security and compliance teams
- Large-scale migration → Consider AWS Migration Hub, Azure Migrate
- Cost optimization at scale → Consider FinOps practices and tools
