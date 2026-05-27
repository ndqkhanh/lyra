---
id: dependency-scan
name: Dependency Scan
description: Scan project dependencies for known vulnerabilities and outdated packages.
keywords:
  - dependency
  - vulnerability
  - cve
  - npm audit
  - pip audit
  - supply chain
  - snyk
---

1. Run the project's dependency scanner (npm audit, pip-audit, cargo audit, etc.).
2. Triage findings by severity; focus on Critical and High first.
3. For each finding: check if the vulnerable code path is reachable in this project.
4. Upgrade to the patched version or apply the recommended workaround.
5. Add dependency scanning to CI; fail the build on Critical CVEs.
