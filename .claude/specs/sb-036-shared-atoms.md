---
title: "SB-036: Shared Atoms (Badge, Icon, Button, Collapsible, Tab)"
date: 2026-03-21
status: draft
branch: dugshub/frontend-mvp/1-ep-006-frontend-mvp-stack-review-ui
depends_on:
  - SB-035
adrs: []
---

# SB-036: Shared Atoms (Badge, Icon, Button, Collapsible, Tab)

## Goal

Create the foundational atom components for the stack-bench frontend. These are generic, reusable visual primitives with zero domain knowledge. All styling uses the dark design system tokens established in SB-035. Every subsequent molecule and organism component will compose from these atoms.

## Domain Model

No domain entities. These are pure presentation components: Badge, Icon, Button, Collapsible, Tab, and CountBadge.

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | `cn()` utility function | -- |
| 2 | Badge component | Phase 1 |
| 3 | Icon component | -- |
| 4 | Button component | Phase 1 |
| 5 | Collapsible component | -- |
| 6 | Tab + CountBadge components | Phase 1 |
| 7 | Barrel exports + dependency install | Phase 2-6 |
| 8 | Verification | Phase 7 |

## Phase Details

### Phase 1: Utility — `cn()` function

Create `app/frontend/src/lib/utils.ts`. This replaces the `.gitkeep` in `src/lib/`.

The `cn()` function merges class names using `clsx`. In Tailwind 4, `tailwind-merge` is unnecessary because Tailwind 4 handles specificity correctly via cascade layers. We use `clsx` alone.

#### `app/frontend/src/lib/utils.ts`

```ts
import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
```

Delete `app/frontend/src/lib/.gitkeep` after creating this file.

---

### Phase 2: Badge Component

#### `app/frontend/src/components/atoms/Badge/Badge.tsx`

```tsx
import { forwardRef, type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full font-medium leading-none whitespace-nowrap",
  {
    variants: {
      size: {
        sm: "px-1.5 py-0.5 text-[10px]",
        default: "px-2 py-0.5 text-xs",
      },
      color: {
        default:
          "bg-[var(--bg-surface-hover)] text-[var(--fg-muted)] border border-[var(--border-muted)]",
        green:
          "bg-[var(--green-bg)] text-[var(--green)] border border-[var(--green)]/20",
        red:
          "bg-[var(--red-bg)] text-[var(--red)] border border-[var(--red)]/20",
        purple:
          "bg-[var(--purple)]/10 text-[var(--purple)] border border-[var(--purple)]/20",
        yellow:
          "bg-[var(--yellow)]/10 text-[var(--yellow)] border border-[var(--yellow)]/20",
        accent:
          "bg-[var(--accent-muted)] text-[var(--accent)] border border-[var(--accent)]/20",
      },
    },
    defaultVariants: {
      size: "default",
      color: "default",
    },
  }
);

type BadgeVariants = VariantProps<typeof badgeVariants>;

interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    BadgeVariants {}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, size, color, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(badgeVariants({ size, color }), className)}
      {...props}
    />
  )
);

Badge.displayName = "Badge";

export { Badge, badgeVariants };
export type { BadgeProps };
```

#### `app/frontend/src/components/atoms/Badge/index.ts`

```ts
export { Badge, badgeVariants } from "./Badge";
export type { BadgeProps } from "./Badge";
```

---

### Phase 3: Icon Component

#### `app/frontend/src/components/atoms/Icon/Icon.tsx`

```tsx
import { forwardRef, type SVGAttributes } from "react";
import { cn } from "@/lib/utils";

const iconPaths: Record<string, React.ReactNode> = {
  "chevron-right": (
    <polyline points="9 18 15 12 9 6" />
  ),
  "chevron-down": (
    <polyline points="6 9 12 15 18 9" />
  ),
  check: (
    <polyline points="20 6 9 17 4 12" />
  ),
  x: (
    <>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </>
  ),
  plus: (
    <>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </>
  ),
  file: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </>
  ),
  folder: (
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  ),
  "git-branch": (
    <>
      <line x1="6" y1="3" x2="6" y2="15" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M18 9a9 9 0 0 1-9 9" />
    </>
  ),
  "git-commit": (
    <>
      <circle cx="12" cy="12" r="4" />
      <line x1="1.05" y1="12" x2="7" y2="12" />
      <line x1="17.01" y1="12" x2="22.96" y2="12" />
    </>
  ),
  circle: (
    <circle cx="12" cy="12" r="10" />
  ),
  "message-square": (
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  ),
};

type IconName = keyof typeof iconPaths;

const sizeMap = {
  xs: 12,
  sm: 16,
  default: 20,
  lg: 24,
} as const;

type IconSize = keyof typeof sizeMap;

interface IconProps extends Omit<SVGAttributes<SVGSVGElement>, "children"> {
  name: IconName;
  size?: IconSize;
}

const Icon = forwardRef<SVGSVGElement, IconProps>(
  ({ name, size = "default", className, ...props }, ref) => {
    const px = sizeMap[size];
    const paths = iconPaths[name];

    if (!paths) {
      return null;
    }

    return (
      <svg
        ref={ref}
        xmlns="http://www.w3.org/2000/svg"
        width={px}
        height={px}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={cn("inline-block shrink-0", className)}
        {...props}
      >
        {paths}
      </svg>
    );
  }
);

Icon.displayName = "Icon";

export { Icon, iconPaths, sizeMap };
export type { IconName, IconSize, IconProps };
```

#### `app/frontend/src/components/atoms/Icon/index.ts`

```ts
export { Icon, iconPaths, sizeMap } from "./Icon";
export type { IconName, IconSize, IconProps } from "./Icon";
```

---

### Phase 4: Button Component

#### `app/frontend/src/components/atoms/Button/Button.tsx`

```tsx
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-canvas)] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-[var(--green)] text-[#0d1117] hover:bg-[var(--green)]/90",
        subtle:
          "border border-[var(--border)] bg-transparent text-[var(--fg-default)] hover:bg-[var(--bg-surface-hover)] hover:border-[var(--border)]",
      },
      size: {
        sm: "h-7 px-3 text-xs gap-1.5",
        default: "h-9 px-4 text-sm gap-2",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  }
);

type ButtonVariants = VariantProps<typeof buttonVariants>;

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    ButtonVariants {}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
);

Button.displayName = "Button";

export { Button, buttonVariants };
export type { ButtonProps };
```

#### `app/frontend/src/components/atoms/Button/index.ts`

```ts
export { Button, buttonVariants } from "./Button";
export type { ButtonProps } from "./Button";
```

---

### Phase 5: Collapsible Component

First, install the dependency:

```bash
cd app/frontend && npm install @radix-ui/react-collapsible
```

#### `app/frontend/src/components/atoms/Collapsible/Collapsible.tsx`

```tsx
import {
  Root,
  Trigger,
  Content,
} from "@radix-ui/react-collapsible";
import { forwardRef, type ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/utils";

const Collapsible = Root;

const CollapsibleTrigger = Trigger;

const CollapsibleContent = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof Content>
>(({ className, ...props }, ref) => (
  <Content
    ref={ref}
    className={cn(
      "overflow-hidden data-[state=closed]:animate-collapse-up data-[state=open]:animate-collapse-down",
      className
    )}
    {...props}
  />
));

CollapsibleContent.displayName = "CollapsibleContent";

export { Collapsible, CollapsibleTrigger, CollapsibleContent };
```

#### CSS Animations

Add the following to `app/frontend/src/index.css`, just before the `/* -- Global Reset */` comment:

```css
/* ── Animations ───────────────────────────────────────────── */

@keyframes collapse-down {
  from {
    height: 0;
    opacity: 0;
  }
  to {
    height: var(--radix-collapsible-content-height);
    opacity: 1;
  }
}

@keyframes collapse-up {
  from {
    height: var(--radix-collapsible-content-height);
    opacity: 1;
  }
  to {
    height: 0;
    opacity: 0;
  }
}

@theme {
  --animate-collapse-down: collapse-down 150ms ease-out;
  --animate-collapse-up: collapse-up 150ms ease-out;
}
```

The `@theme` block is Tailwind 4's way of defining custom theme values (replaces `tailwind.config.js extend`). This makes `animate-collapse-down` and `animate-collapse-up` available as Tailwind utility classes.

#### `app/frontend/src/components/atoms/Collapsible/index.ts`

```ts
export {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "./Collapsible";
```

---

### Phase 6: Tab + CountBadge Components

#### `app/frontend/src/components/atoms/Tab/Tab.tsx`

```tsx
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface TabProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
}

const Tab = forwardRef<HTMLButtonElement, TabProps>(
  ({ active = false, className, children, ...props }, ref) => (
    <button
      ref={ref}
      role="tab"
      aria-selected={active}
      className={cn(
        "relative inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-b-2",
        active
          ? "text-[var(--fg-default)] border-[var(--accent)]"
          : "text-[var(--fg-muted)] border-transparent hover:text-[var(--fg-default)] hover:border-[var(--border)]",
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
);

Tab.displayName = "Tab";

export { Tab };
export type { TabProps };
```

#### `app/frontend/src/components/atoms/Tab/CountBadge.tsx`

```tsx
import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface CountBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  count: number;
}

const CountBadge = forwardRef<HTMLSpanElement, CountBadgeProps>(
  ({ count, className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-medium leading-none bg-[var(--bg-surface-hover)] text-[var(--fg-muted)] border border-[var(--border-muted)]",
        className
      )}
      {...props}
    >
      {count}
    </span>
  )
);

CountBadge.displayName = "CountBadge";

export { CountBadge };
export type { CountBadgeProps };
```

#### `app/frontend/src/components/atoms/Tab/index.ts`

```ts
export { Tab } from "./Tab";
export type { TabProps } from "./Tab";
export { CountBadge } from "./CountBadge";
export type { CountBadgeProps } from "./CountBadge";
```

---

### Phase 7: Barrel Exports + Dependency Install

#### `app/frontend/src/components/atoms/index.ts`

This replaces the `.gitkeep` in `src/components/atoms/`.

```ts
export { Badge, badgeVariants } from "./Badge";
export type { BadgeProps } from "./Badge";

export { Icon, iconPaths, sizeMap } from "./Icon";
export type { IconName, IconSize, IconProps } from "./Icon";

export { Button, buttonVariants } from "./Button";
export type { ButtonProps } from "./Button";

export {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "./Collapsible";

export { Tab } from "./Tab";
export type { TabProps } from "./Tab";
export { CountBadge } from "./CountBadge";
export type { CountBadgeProps } from "./CountBadge";
```

#### Dependency install

```bash
cd app/frontend && npm install @radix-ui/react-collapsible
```

#### Cleanup

Delete these `.gitkeep` files that are replaced by real files:
- `app/frontend/src/components/atoms/.gitkeep`
- `app/frontend/src/lib/.gitkeep`

---

### Phase 8: Verification

1. **TypeScript compiles cleanly:**
   ```bash
   cd app/frontend && npx tsc --noEmit
   ```
   No errors.

2. **Dev server starts:**
   ```bash
   cd app/frontend && npm run dev
   ```
   Confirm no build errors in the terminal.

3. **Smoke-test imports (optional):** Temporarily update `App.tsx` to import and render each atom, confirming they render without runtime errors:

   ```tsx
   import { Badge } from "@/components/atoms/Badge";
   import { Icon } from "@/components/atoms/Icon";
   import { Button } from "@/components/atoms/Button";
   import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/atoms/Collapsible";
   import { Tab } from "@/components/atoms/Tab";
   import { CountBadge } from "@/components/atoms/Tab";

   // Render inside App:
   <Badge color="green">Merged</Badge>
   <Icon name="git-branch" size="sm" />
   <Button variant="primary" size="sm">Submit</Button>
   <Button variant="subtle">Cancel</Button>
   <Collapsible>
     <CollapsibleTrigger>Toggle</CollapsibleTrigger>
     <CollapsibleContent>Content here</CollapsibleContent>
   </Collapsible>
   <Tab active>Files <CountBadge count={3} /></Tab>
   <Tab>Conversations</Tab>
   ```

   Revert `App.tsx` after verification.

4. **Build succeeds:**
   ```bash
   cd app/frontend && npm run build
   ```

## File Inventory

| File | Action | Purpose |
|------|--------|---------|
| `src/lib/utils.ts` | Create | `cn()` class merging utility |
| `src/lib/.gitkeep` | Delete | Replaced by real file |
| `src/components/atoms/.gitkeep` | Delete | Replaced by barrel export |
| `src/components/atoms/index.ts` | Create | Barrel export for all atoms |
| `src/components/atoms/Badge/Badge.tsx` | Create | Badge component with CVA variants |
| `src/components/atoms/Badge/index.ts` | Create | Badge barrel |
| `src/components/atoms/Icon/Icon.tsx` | Create | Inline SVG icon component |
| `src/components/atoms/Icon/index.ts` | Create | Icon barrel |
| `src/components/atoms/Button/Button.tsx` | Create | Button with primary/subtle variants |
| `src/components/atoms/Button/index.ts` | Create | Button barrel |
| `src/components/atoms/Collapsible/Collapsible.tsx` | Create | Radix-based collapsible wrapper |
| `src/components/atoms/Collapsible/index.ts` | Create | Collapsible barrel |
| `src/components/atoms/Tab/Tab.tsx` | Create | Tab button with active indicator |
| `src/components/atoms/Tab/CountBadge.tsx` | Create | Numeric count pill |
| `src/components/atoms/Tab/index.ts` | Create | Tab + CountBadge barrel |
| `src/index.css` | Modify | Add collapse animations + @theme block |
| `package.json` | Modify | Add `@radix-ui/react-collapsible` dependency |

## Open Questions

None. All design decisions are settled.
