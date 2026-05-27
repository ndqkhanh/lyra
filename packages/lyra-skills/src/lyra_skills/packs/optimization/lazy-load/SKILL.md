---
id: lazy-load
name: Lazy Load
description: Implement lazy loading for modules, images, and data to improve perceived performance.
keywords:
  - lazy
  - lazy load
  - defer
  - dynamic import
  - suspense
  - intersection observer
---

1. Identify above-the-fold vs below-the-fold content.
2. Convert static imports to dynamic imports for below-the-fold modules.
3. Add loading states (skeletons, spinners) for lazy-loaded content.
4. Use Intersection Observer for deferred image/data loading.
5. Measure Largest Contentful Paint (LCP) before and after.
