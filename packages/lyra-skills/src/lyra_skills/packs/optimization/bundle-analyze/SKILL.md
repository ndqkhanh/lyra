---
id: bundle-analyze
name: Bundle Analyze
description: Analyse JavaScript/TypeScript bundles to reduce size and improve load time.
keywords:
  - bundle
  - webpack
  - vite
  - esbuild
  - tree shaking
  - code splitting
  - chunk
---

1. Generate a bundle analysis report (webpack-bundle-analyzer, rollup-plugin-visualizer).
2. Identify the largest chunks and their constituent modules.
3. Check for: duplicate dependencies, un-tree-shaken exports, moment.js locales, polyfill bloat.
4. Apply code splitting for routes and lazy-loaded components.
5. Verify bundle size reduction and time-to-interactive improvement.
