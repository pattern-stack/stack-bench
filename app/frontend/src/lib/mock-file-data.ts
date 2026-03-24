import type { FileTreeNode, FileContent } from "@/types/file-tree";

export const mockFileTree: FileTreeNode = {
  name: ".",
  path: "",
  type: "dir",
  size: null,
  children: [
    {
      name: "src",
      path: "src",
      type: "dir",
      size: null,
      children: [
        {
          name: "components",
          path: "src/components",
          type: "dir",
          size: null,
          children: [
            {
              name: "Button.tsx",
              path: "src/components/Button.tsx",
              type: "file",
              size: 1240,
              children: null,
            },
            {
              name: "Header.tsx",
              path: "src/components/Header.tsx",
              type: "file",
              size: 890,
              children: null,
            },
            {
              name: "Sidebar.tsx",
              path: "src/components/Sidebar.tsx",
              type: "file",
              size: 1560,
              children: null,
            },
          ],
        },
        {
          name: "hooks",
          path: "src/hooks",
          type: "dir",
          size: null,
          children: [
            {
              name: "useAuth.ts",
              path: "src/hooks/useAuth.ts",
              type: "file",
              size: 720,
              children: null,
            },
            {
              name: "useTheme.ts",
              path: "src/hooks/useTheme.ts",
              type: "file",
              size: 340,
              children: null,
            },
          ],
        },
        {
          name: "lib",
          path: "src/lib",
          type: "dir",
          size: null,
          children: [
            {
              name: "utils.ts",
              path: "src/lib/utils.ts",
              type: "file",
              size: 480,
              children: null,
            },
          ],
        },
        {
          name: "App.tsx",
          path: "src/App.tsx",
          type: "file",
          size: 2048,
          children: null,
        },
        {
          name: "index.css",
          path: "src/index.css",
          type: "file",
          size: 1200,
          children: null,
        },
        {
          name: "main.ts",
          path: "src/main.ts",
          type: "file",
          size: 180,
          children: null,
        },
      ],
    },
    {
      name: "public",
      path: "public",
      type: "dir",
      size: null,
      children: [
        {
          name: "favicon.svg",
          path: "public/favicon.svg",
          type: "file",
          size: 1520,
          children: null,
        },
      ],
    },
    {
      name: "package.json",
      path: "package.json",
      type: "file",
      size: 640,
      children: null,
    },
    {
      name: "tsconfig.json",
      path: "tsconfig.json",
      type: "file",
      size: 420,
      children: null,
    },
  ],
};

const mockFiles: Record<string, FileContent> = {
  "src/App.tsx": {
    path: "src/App.tsx",
    content: `import { useState } from "react";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";

export function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="app">
      <Header title="My App" />
      <div className="layout">
        <Sidebar />
        <main>
          <h1>Welcome</h1>
          <button onClick={() => setCount((c) => c + 1)}>
            Count: {count}
          </button>
        </main>
      </div>
    </div>
  );
}`,
    size: 2048,
    language: "tsx",
    lines: 22,
    truncated: false,
  },

  "src/components/Button.tsx": {
    path: "src/components/Button.tsx",
    content: `import { type ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        outline: "border border-input bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}`,
    size: 1240,
    language: "tsx",
    lines: 38,
    truncated: false,
  },

  "src/components/Header.tsx": {
    path: "src/components/Header.tsx",
    content: `interface HeaderProps {
  title: string;
}

export function Header({ title }: HeaderProps) {
  return (
    <header className="border-b border-border bg-surface px-4 py-3">
      <h1 className="text-lg font-semibold">{title}</h1>
    </header>
  );
}`,
    size: 890,
    language: "tsx",
    lines: 11,
    truncated: false,
  },

  "src/components/Sidebar.tsx": {
    path: "src/components/Sidebar.tsx",
    content: `import { useState } from "react";

const navItems = [
  { label: "Dashboard", href: "/" },
  { label: "Projects", href: "/projects" },
  { label: "Settings", href: "/settings" },
];

export function Sidebar() {
  const [active, setActive] = useState("/");

  return (
    <nav className="w-64 border-r border-border bg-surface p-4">
      <ul className="space-y-1">
        {navItems.map((item) => (
          <li key={item.href}>
            <a
              href={item.href}
              onClick={(e) => {
                e.preventDefault();
                setActive(item.href);
              }}
              className={
                active === item.href
                  ? "block rounded px-3 py-2 text-sm font-medium bg-accent/10 text-accent"
                  : "block rounded px-3 py-2 text-sm text-muted hover:bg-surface-hover"
              }
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}`,
    size: 1560,
    language: "tsx",
    lines: 36,
    truncated: false,
  },

  "src/hooks/useAuth.ts": {
    path: "src/hooks/useAuth.ts",
    content: `import { useState, useCallback } from "react";

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: false,
  });

  const login = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, loading: true }));
    // Simulated login
    await new Promise((r) => setTimeout(r, 1000));
    setState({
      user: { id: "1", name: "Test User", email },
      loading: false,
    });
  }, []);

  const logout = useCallback(() => {
    setState({ user: null, loading: false });
  }, []);

  return { ...state, login, logout };
}`,
    size: 720,
    language: "typescript",
    lines: 34,
    truncated: false,
  },

  "src/hooks/useTheme.ts": {
    path: "src/hooks/useTheme.ts",
    content: `import { useState } from "react";

type Theme = "light" | "dark";

export function useTheme(initial: Theme = "dark") {
  const [theme, setTheme] = useState<Theme>(initial);
  const toggle = () => setTheme((t) => (t === "light" ? "dark" : "light"));
  return { theme, toggle };
}`,
    size: 340,
    language: "typescript",
    lines: 9,
    truncated: false,
  },

  "src/lib/utils.ts": {
    path: "src/lib/utils.ts",
    content: `import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}`,
    size: 480,
    language: "typescript",
    lines: 13,
    truncated: false,
  },

  "src/index.css": {
    path: "src/index.css",
    content: `@import "tailwindcss";

:root {
  --bg-canvas: #0d1117;
  --bg-surface: #161b22;
  --bg-surface-hover: #1c2128;
  --border: #30363d;
  --border-muted: #21262d;
  --fg-default: #e6edf3;
  --fg-muted: #7d8590;
  --fg-subtle: #484f58;
  --accent: #58a6ff;
  --green: #3fb950;
  --red: #f85149;
}

body {
  margin: 0;
  background-color: var(--bg-canvas);
  color: var(--fg-default);
  font-family: system-ui, sans-serif;
}`,
    size: 1200,
    language: "css",
    lines: 22,
    truncated: false,
  },

  "src/main.ts": {
    path: "src/main.ts",
    content: `import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(<App />);`,
    size: 180,
    language: "typescript",
    lines: 5,
    truncated: false,
  },

  "package.json": {
    path: "package.json",
    content: `{
  "name": "my-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0"
  }
}`,
    size: 640,
    language: "json",
    lines: 22,
    truncated: false,
  },

  "tsconfig.json": {
    path: "tsconfig.json",
    content: `{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}`,
    size: 420,
    language: "json",
    lines: 17,
    truncated: false,
  },
};

export function getMockFileContent(path: string): FileContent | null {
  return mockFiles[path] ?? null;
}
