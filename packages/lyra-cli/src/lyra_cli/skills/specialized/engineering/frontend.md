---
name: "frontend-engineer"
description: Frontend development expertise covering React, Vue, Angular, Next.js, state management, performance optimization, accessibility, and modern UI patterns. Use when building user interfaces, optimizing frontend performance, implementing responsive designs, or debugging UI issues.
tags: ["engineering", "frontend", "react", "vue", "ui", "performance"]
triggers: ["frontend", "react", "vue", "ui component", "state management", "responsive design"]
model: "sonnet"
tools: ["Read", "Write", "Edit", "Bash", "Grep"]
---

# Frontend Engineer

Expert frontend development guidance for modern web applications.

## Core Competencies

### 1. React Development
- Component architecture (functional components, hooks)
- State management (Context, Redux, Zustand, Jotai)
- Performance optimization (memo, useMemo, useCallback)
- Server components and RSC patterns
- Testing (Jest, React Testing Library, Playwright)

### 2. Modern Frameworks
- **Next.js**: App Router, Server Actions, ISR, SSG
- **Vue 3**: Composition API, Pinia, Nuxt 3
- **Angular**: Signals, Standalone components, RxJS
- **Svelte/SvelteKit**: Reactive programming, stores

### 3. Styling Solutions
- **CSS-in-JS**: styled-components, Emotion
- **Utility-first**: Tailwind CSS, UnoCSS
- **CSS Modules**: Scoped styles, composition
- **Design Systems**: Radix UI, shadcn/ui, Chakra UI

### 4. Performance Optimization
- Code splitting and lazy loading
- Image optimization (next/image, responsive images)
- Bundle analysis and tree shaking
- Web Vitals (LCP, FID, CLS)
- Lighthouse optimization

### 5. Accessibility (WCAG 2.1 AA)
- Semantic HTML and ARIA attributes
- Keyboard navigation
- Screen reader compatibility
- Color contrast and focus management

## Common Patterns

### Component Structure
```typescript
// Atomic design pattern
components/
  atoms/       # Button, Input, Label
  molecules/   # FormField, SearchBar
  organisms/   # Header, ProductCard
  templates/   # PageLayout, DashboardLayout
  pages/       # HomePage, ProductPage
```

### State Management Decision Tree
```
Local state only? → useState
Shared across components? → Context API
Complex state logic? → useReducer
Global app state? → Redux Toolkit / Zustand
Server state? → TanStack Query / SWR
Form state? → React Hook Form / Formik
```

### Performance Checklist
- [ ] Code splitting at route level
- [ ] Lazy load below-the-fold components
- [ ] Optimize images (WebP, AVIF, responsive)
- [ ] Minimize bundle size (<200KB initial)
- [ ] Use CDN for static assets
- [ ] Implement proper caching headers
- [ ] Defer non-critical JavaScript
- [ ] Preload critical resources

## Workflows

### New Component Workflow
1. **Design**: Review design specs, identify reusable patterns
2. **Structure**: Choose atomic design level (atom/molecule/organism)
3. **Props API**: Define TypeScript interface with JSDoc
4. **Implementation**: Build with accessibility in mind
5. **Styling**: Apply design system tokens
6. **Testing**: Unit tests + accessibility tests
7. **Documentation**: Storybook story with variants

### Performance Debugging
1. **Measure**: Run Lighthouse, check Web Vitals
2. **Profile**: Use React DevTools Profiler
3. **Analyze**: Bundle analyzer for size issues
4. **Optimize**: Apply memoization, code splitting
5. **Verify**: Re-run Lighthouse, compare metrics

### Accessibility Audit
1. **Automated**: Run axe DevTools, Lighthouse
2. **Keyboard**: Tab through entire interface
3. **Screen reader**: Test with NVDA/JAWS/VoiceOver
4. **Color**: Check contrast ratios (4.5:1 minimum)
5. **Focus**: Verify visible focus indicators

## Tech Stack Recommendations

### Starter Stack (2024)
```
Framework: Next.js 14 (App Router)
Language: TypeScript
Styling: Tailwind CSS + shadcn/ui
State: Zustand + TanStack Query
Forms: React Hook Form + Zod
Testing: Vitest + Playwright
```

### Enterprise Stack
```
Framework: Next.js 14 or Remix
Language: TypeScript (strict mode)
Styling: Tailwind + Design System
State: Redux Toolkit + RTK Query
Forms: React Hook Form + Zod
Testing: Jest + React Testing Library + Playwright
Monitoring: Sentry + Vercel Analytics
```

## Common Issues & Solutions

### Issue: Unnecessary Re-renders
**Symptoms**: Slow UI, high CPU usage
**Solution**: 
- Use React DevTools Profiler
- Wrap expensive components in `memo()`
- Memoize callbacks with `useCallback`
- Memoize computed values with `useMemo`

### Issue: Large Bundle Size
**Symptoms**: Slow initial load, poor Lighthouse score
**Solution**:
- Analyze with `@next/bundle-analyzer`
- Dynamic imports for routes
- Tree-shake unused code
- Replace heavy libraries (moment → date-fns)

### Issue: Hydration Mismatch
**Symptoms**: Console warnings, UI flicker
**Solution**:
- Avoid `Date.now()` or `Math.random()` in render
- Use `useEffect` for client-only code
- Suppress hydration warning only when necessary

### Issue: Accessibility Violations
**Symptoms**: Failed axe audit, keyboard navigation broken
**Solution**:
- Add ARIA labels to interactive elements
- Ensure proper heading hierarchy (h1 → h2 → h3)
- Implement focus trap for modals
- Test with keyboard only (no mouse)

## Reference Documentation

### React Patterns
- Compound components
- Render props
- Higher-order components (HOCs)
- Custom hooks
- Controlled vs uncontrolled components

### Next.js App Router
- Server components (default)
- Client components (`'use client'`)
- Server actions
- Route handlers
- Middleware

### Testing Strategy
```typescript
// Unit test (Vitest)
describe('Button', () => {
  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Click</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })
})

// E2E test (Playwright)
test('user can submit form', async ({ page }) => {
  await page.goto('/contact')
  await page.fill('[name="email"]', 'test@example.com')
  await page.click('button[type="submit"]')
  await expect(page.locator('.success')).toBeVisible()
})
```

## Quick Commands

```bash
# Create Next.js app
npx create-next-app@latest --typescript --tailwind --app

# Analyze bundle
npm run build && npx @next/bundle-analyzer

# Run accessibility audit
npx @axe-core/cli http://localhost:3000

# Performance profiling
npm run build && npm run start
# Open Chrome DevTools → Performance → Record

# Type checking
npx tsc --noEmit

# Lint
npx eslint . --ext .ts,.tsx

# Test
npm run test
npm run test:e2e
```

## When to Escalate

- Complex animation requirements → Consider Framer Motion or GSAP
- Real-time collaboration → Consider Yjs or Liveblocks
- 3D graphics → Consider Three.js or React Three Fiber
- Video processing → Consider WebRTC or FFmpeg.wasm
- Advanced data visualization → Consider D3.js or Recharts
