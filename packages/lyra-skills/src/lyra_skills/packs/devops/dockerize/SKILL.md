---
id: dockerize
name: Dockerize
description: Containerize an application with a production-ready Dockerfile and compose setup.
keywords:
  - docker
  - container
  - dockerfile
  - docker-compose
  - containerize
  - image
---

1. Choose the appropriate base image (alpine for Go/Rust, slim for Python/Node).
2. Multi-stage build: build deps in stage 1, copy artifacts to stage 2.
3. Run as non-root user; expose only necessary ports.
4. Add healthcheck; use .dockerignore to exclude node_modules, .git, etc.
5. Provide a docker-compose.yml for local dev with dependent services.
