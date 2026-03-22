---
id: SB-035
title: Frontend scaffold + dark design system
status: draft
epic: EP-006
depends_on: []
branch:
pr:
stack: frontend-mvp
stack_index: 1
created: 2026-03-21
---

# Frontend scaffold + dark design system

## Summary

Bootstrap the React frontend with Vite, TypeScript, and Tailwind 4. Update `patterns.yaml` so `pts dev` and `pts sync` know about the frontend. Establish the dark design system tokens — colors, typography, spacing, radii — as CSS custom properties. This is the foundation every subsequent issue builds on.

## Scope

What's in:
- Vite + React 18 + TypeScript project at `app/frontend/`
- Tailwind 4 via `@tailwindcss/vite`
- `vite.config.ts` with `/api` proxy to backend
- `patterns.yaml` update (`apps.frontend.working_dir: "app/frontend"`)
- Design tokens in CSS custom properties (dark palette from v3 mockup: canvas, surface, border, accent, green, red, purple, yellow)
- Font stack (system sans + mono)
- Global styles: scrollbar, box-sizing, body reset
- `pts sync generate` run to produce `src/generated/` from backend models
- Basic `App.tsx` with hello world to verify dev server

What's out:
- Any UI components (that's SB-036+)
- Routing
- Auth

## Implementation

Key files to create or modify:

```
patterns.yaml                          # update frontend working_dir
app/frontend/
  package.json
  tsconfig.json
  vite.config.ts
  index.html
  src/
    main.tsx
    App.tsx
    index.css                          # design tokens + global styles
    generated/                         # pts sync generate output
```

## Verification

- [ ] `cd app/frontend && npm run dev` starts on configured port
- [ ] `pts sync generate` produces `src/generated/` with schemas, api, hooks, store
- [ ] Browser shows App.tsx content with dark background and correct font
- [ ] `/api/health` returns `{"status": "ok"}` through Vite proxy

## Notes

Design token palette (from v3 mockup):
- `--bg-canvas: #0d1117`, `--bg-surface: #161b22`, `--bg-inset: #010409`
- `--border: #30363d`, `--fg-default: #e6edf3`, `--fg-muted: #7d8590`
- `--accent: #58a6ff`, `--green: #3fb950`, `--red: #f85149`, `--purple: #bc8cff`, `--yellow: #d29922`
