---
id: infra-as-code
name: Infrastructure as Code
description: Provision and manage infrastructure declaratively with Terraform, Pulumi, or CDK.
keywords:
  - IaC
  - terraform
  - infrastructure
  - provisioning
  - cloud
  - deploy
---

1. Define infrastructure declaratively — never click in a console. Everything in version control.
2. Structure by environment (dev/staging/prod) with shared modules. Keep environments identical except for scale.
3. Use remote state with locking (S3 + DynamoDB, Terraform Cloud). Never use local state for shared infra.
4. Pin provider versions. Test infrastructure changes in dev before applying to prod.
5. Plan before apply. Review the plan diff. If the plan shows unexpected destruction, STOP and investigate.
6. Tag everything: owner, environment, cost center, compliance level. Untagged resources are technical debt.
7. Implement least-privilege IAM: each service gets exactly the permissions it needs, reviewed quarterly.
