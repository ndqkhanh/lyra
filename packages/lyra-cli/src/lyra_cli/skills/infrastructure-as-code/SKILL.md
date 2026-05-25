---
name: infrastructure-as-code
description: Terraform and Pulumi patterns, drift detection, cost optimization, and CI/CD for infrastructure
origin: Plan 13
tags: [iac, terraform, pulumi, drift, infrastructure]
triggers: [infrastructure, terraform, pulumi, IaC, drift, provision]
---

# Infrastructure as Code

## Terraform Patterns

**Module Composition**: Write stateless, versioned modules with explicit inputs/outputs.

```hcl
module "networking" {
  source  = "git::ssh://git@github.com/org/tf-modules//networking?ref=v1.2"
  vpc_cidr = "10.0.0.0/16"
  env      = var.env
}
```

**State Management**: Use remote backends (S3/GCS + DynamoDB for locking). Never commit state to Git.

**Workspaces**: Isolate environments per workspace. Use `terraform.workspace` in conditionals.

## Pulumi Patterns

**Component Resources**: Encapsulate logical infrastructure in reusable components.

```typescript
const cluster = new EKSCluster("app-cluster", {
  nodeCount: 5,
  instanceType: "t3.large",
});
```

**Stack References**: Reference outputs from other stacks with `stack.getOutput()`.

## Drift Detection and Remediation

- Run `terraform plan` / `pulumi preview` on a schedule to detect drift
- `terraform refresh` updates state; reconcile with `terraform apply`
- Gate changes via CI: detect drift before deployment, alert on unexpected resource changes

## Cost Optimization

- Enforce tagging taxonomy: `Environment`, `Team`, `CostCenter`, `Owner`
- Right-size instances using utilization data (72+ hour window)
- Reserved Instances / Savings Plans for steady-state workloads
- Delete orphaned resources (unattached volumes, unused load balancers)

## Immutable Infrastructure

- Never modify servers in-place
- Bake AMIs/container images via packer or CI pipelines
- Replace instances on every deployment for deterministic state

## CI/CD for Infrastructure

**Plan Stage**: `terraform plan -out=tfplan` in PRs; review output for unexpected changes.

**Apply Stage**: `terraform apply tfplan` on merge to main; auto-approve only with strict plan validation.

## Security Scanning

- **tfsec**: Static analysis for Terraform (hardcoded secrets, open SG rules)
- **Checkov**: Policy-as-code (CIS benchmarks, custom policies)
- Gate pipelines: fail on CRITICAL/HIGH findings
