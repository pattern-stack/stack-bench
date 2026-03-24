---
title: "SB-035: Frontend Scaffold + Dark Design System"
date: 2026-03-21
status: draft
branch: dugshub/frontend-mvp/1-ep-006-frontend-mvp-stack-review-ui
depends_on: []
adrs:
  - ADR-001
  - ADR-002
---

# SB-035: Frontend Scaffold + Dark Design System

## Goal

Bootstrap the React frontend with Vite, TypeScript, and Tailwind 4. Establish the dark design system as CSS custom properties and create the atomic directory structure that every subsequent issue (SB-036 through SB-039) builds on. After this issue, `npm run dev` serves a dark-themed shell on port 3000 with an API proxy to the backend.

## Domain Model

No domain entities in this issue. This is pure infrastructure: build tooling, design tokens, and directory scaffolding.

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Create project files (package.json, tsconfig, vite config, index.html) | -- |
| 2 | Create source files (main.tsx, App.tsx, index.css with design tokens) | Phase 1 |
| 3 | Create atomic directory structure (empty directories with .gitkeep) | Phase 1 |
| 4 | Install dependencies and verify | Phase 1-3 |

## Phase Details

### Phase 1: Project Configuration Files

All files live under `app/frontend/`.

#### `app/frontend/package.json`

```json
{
  "name": "@stack-bench/frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite --port 3000",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

#### `app/frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,

    /* Paths */
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "vite-env.d.ts"]
}
```

#### `app/frontend/vite.config.ts`

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

#### `app/frontend/vite-env.d.ts`

```ts
/// <reference types="vite/client" />
```

#### `app/frontend/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Stack Bench</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### Phase 2: Source Files

#### `app/frontend/src/main.tsx`

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

#### `app/frontend/src/App.tsx`

A minimal shell that proves the design system works. Shows the app name, a few token-colored elements, and confirms the dark theme is active.

```tsx
export function App() {
  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-6">
          <h1 className="text-3xl font-semibold tracking-tight">
            Stack Bench
          </h1>
          <p className="text-[var(--fg-muted)] text-sm">
            Frontend scaffold loaded.
          </p>
          <div className="flex gap-3 justify-center">
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--accent)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--green)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--red)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--purple)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--yellow)]" />
          </div>
          <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--fg-subtle)]">
            v0.0.1 &middot; Vite + React + Tailwind 4
          </p>
        </div>
      </div>
    </div>
  );
}
```

#### `app/frontend/src/index.css`

This is the design token foundation. Every component references these variables.

```css
@import "tailwindcss";

/*
 * Stack Bench — Dark Design System Tokens
 *
 * All colors, fonts, and semantic values are defined here as CSS custom
 * properties. Components reference these via var(--token-name). Never
 * hardcode color values in component code.
 */

:root {
  /* ── Backgrounds ─────────────────────────────────────────── */
  --bg-canvas: #0d1117;          /* Page background */
  --bg-surface: #161b22;         /* Cards, panels, headers */
  --bg-surface-hover: #1c2128;   /* Surface hover state */
  --bg-inset: #010409;           /* Inputs, recessed areas */

  /* ── Borders ─────────────────────────────────────────────── */
  --border: #30363d;             /* Default border */
  --border-muted: #21262d;       /* Subtle border */

  /* ── Foreground / Text ───────────────────────────────────── */
  --fg-default: #e6edf3;         /* Primary text */
  --fg-muted: #7d8590;           /* Secondary text */
  --fg-subtle: #484f58;          /* Tertiary text, placeholders */

  /* ── Semantic Colors ─────────────────────────────────────── */
  --accent: #58a6ff;             /* Links, primary actions */
  --green: #3fb950;              /* Success, additions */
  --red: #f85149;                /* Error, deletions */
  --purple: #bc8cff;             /* Reviews, special items */
  --yellow: #d29922;             /* Warnings, pending */

  /* ── Semantic Backgrounds ────────────────────────────────── */
  --green-bg: #12261e;           /* Diff addition background */
  --red-bg: #28171a;             /* Diff deletion background */
  --accent-muted: #1f6feb33;     /* Selected/active background */

  /* ── Typography ──────────────────────────────────────────── */
  --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
    "Liberation Mono", monospace;

  /* ── Spacing (for reference, Tailwind handles most) ──────── */
  --sidebar-width: 320px;
}

/* ── Global Reset ──────────────────────────────────────────── */

*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  background-color: var(--bg-canvas);
  color: var(--fg-default);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Scrollbar Styling ─────────────────────────────────────── */

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-canvas);
}

::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--fg-subtle);
}

/* Firefox scrollbar */
* {
  scrollbar-width: thin;
  scrollbar-color: var(--border) var(--bg-canvas);
}

/* ── Selection ─────────────────────────────────────────────── */

::selection {
  background-color: var(--accent-muted);
  color: var(--fg-default);
}
```

### Phase 3: Atomic Directory Structure

Create the following empty directories with `.gitkeep` files so the structure is tracked in git:

```
app/frontend/src/components/atoms/.gitkeep
app/frontend/src/components/molecules/.gitkeep
app/frontend/src/components/organisms/.gitkeep
app/frontend/src/hooks/.gitkeep
app/frontend/src/lib/.gitkeep
app/frontend/src/pages/.gitkeep
app/frontend/src/generated/.gitkeep
```

The `generated/` directory will hold pts codegen output in the future. Add a `.gitkeep` with a comment header:

**`app/frontend/src/generated/.gitkeep`**
```
# This directory holds auto-generated files from pts codegen.
# DO NOT manually edit files in this directory.
```

### Phase 4: Install and Verify

1. `cd app/frontend && npm install`
2. Verify `node_modules/` is created and no errors
3. Run `npm run dev` and confirm:
   - Server starts on port 3000
   - No TypeScript errors
   - No Tailwind errors

## File Inventory

| File | Purpose |
|------|---------|
| `package.json` | Dependencies, scripts |
| `tsconfig.json` | TypeScript strict config with path aliases |
| `vite.config.ts` | Vite + React + Tailwind plugins, `@/` alias, `/api` proxy |
| `vite-env.d.ts` | Vite type reference |
| `index.html` | HTML shell with `#root` mount point |
| `src/main.tsx` | React entry point |
| `src/App.tsx` | Minimal dark-themed landing proving tokens work |
| `src/index.css` | Design tokens + global styles + scrollbar + reset |
| `src/components/atoms/.gitkeep` | Atomic directory placeholder |
| `src/components/molecules/.gitkeep` | Atomic directory placeholder |
| `src/components/organisms/.gitkeep` | Atomic directory placeholder |
| `src/hooks/.gitkeep` | Hooks directory placeholder |
| `src/lib/.gitkeep` | Utilities directory placeholder |
| `src/pages/.gitkeep` | Pages directory placeholder |
| `src/generated/.gitkeep` | Codegen output placeholder (DO NOT EDIT) |

## Design Token Reference

### Backgrounds
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-canvas` | `#0d1117` | Page background |
| `--bg-surface` | `#161b22` | Cards, panels, headers |
| `--bg-surface-hover` | `#1c2128` | Hover state for surfaces |
| `--bg-inset` | `#010409` | Inputs, recessed areas |

### Borders
| Token | Value | Usage |
|-------|-------|-------|
| `--border` | `#30363d` | Default borders |
| `--border-muted` | `#21262d` | Subtle dividers |

### Text
| Token | Value | Usage |
|-------|-------|-------|
| `--fg-default` | `#e6edf3` | Primary text |
| `--fg-muted` | `#7d8590` | Secondary text |
| `--fg-subtle` | `#484f58` | Placeholders, hints |

### Semantic Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--accent` | `#58a6ff` | Links, primary actions |
| `--green` | `#3fb950` | Success, additions |
| `--red` | `#f85149` | Errors, deletions |
| `--purple` | `#bc8cff` | Reviews, special |
| `--yellow` | `#d29922` | Warnings, pending |

### Semantic Backgrounds
| Token | Value | Usage |
|-------|-------|-------|
| `--green-bg` | `#12261e` | Diff addition lines |
| `--red-bg` | `#28171a` | Diff deletion lines |
| `--accent-muted` | `#1f6feb33` | Selected/active items |

### Typography
| Token | Value |
|-------|-------|
| `--font-sans` | System sans-serif stack |
| `--font-mono` | System monospace stack |

## Verification Steps

1. **Dev server starts:**
   ```bash
   cd app/frontend && npm install && npm run dev
   ```
   Confirm output shows `Local: http://localhost:3000/`.

2. **Browser renders correctly:**
   - Navigate to `http://localhost:3000`
   - Page has dark background (`#0d1117`)
   - "Stack Bench" heading visible in light text (`#e6edf3`)
   - Five colored dots visible (accent blue, green, red, purple, yellow)
   - Version text visible in subtle color

3. **API proxy works:**
   - With backend running on port 8000
   - `curl http://localhost:3000/api/health` returns `{"status": "ok"}`

4. **TypeScript compiles cleanly:**
   ```bash
   cd app/frontend && npx tsc --noEmit
   ```
   No errors.

5. **Build succeeds:**
   ```bash
   cd app/frontend && npm run build
   ```
   Output in `dist/` directory.

## Notes for Builder

- Do NOT run `pts sync generate` or any codegen commands. Just create the `generated/` directory.
- The `@/` path alias maps to `src/` via both tsconfig paths and vite resolve alias. This lets all imports use `@/components/atoms/Badge` style paths.
- Tailwind 4 uses `@import "tailwindcss"` instead of the old `@tailwind` directives.
- CVA and clsx are installed as dependencies but not used yet. They are needed by SB-036 (atoms).
- The `--sidebar-width` token is included for SB-038 (app shell layout).

## Open Questions

None. All decisions are settled for this scaffolding issue.
