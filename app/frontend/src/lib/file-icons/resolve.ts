import type { FileIconId } from "./types";

/** Exact filename → icon ID (checked first) */
const fileNameMap: Record<string, FileIconId> = {
  "Dockerfile":       "dockerfile",
  "dockerfile":       "dockerfile",
  "docker-compose.yml": "docker-compose",
  "docker-compose.yaml": "docker-compose",
  "compose.yml":      "docker-compose",
  "compose.yaml":     "docker-compose",
  ".gitignore":       "gitignore",
  ".gitattributes":   "gitignore",
  ".gitmodules":      "gitignore",
  "Makefile":         "makefile",
  "makefile":         "makefile",
  "Justfile":         "makefile",
  "justfile":         "makefile",
  "package.json":     "packageJson",
  "tsconfig.json":    "tsconfig",
  "tsconfig.node.json": "tsconfig",
  "tsconfig.app.json": "tsconfig",
  "vite.config.ts":   "viteConfig",
  "vite.config.js":   "viteConfig",
  "vite.config.mts":  "viteConfig",
  ".eslintrc":        "eslint",
  ".eslintrc.js":     "eslint",
  ".eslintrc.cjs":    "eslint",
  ".eslintrc.json":   "eslint",
  "eslint.config.js": "eslint",
  "eslint.config.mjs": "eslint",
  "eslint.config.ts": "eslint",
  ".prettierrc":      "prettier",
  ".prettierrc.js":   "prettier",
  ".prettierrc.json": "prettier",
  "prettier.config.js": "prettier",
  "tailwind.config.js": "tailwindConfig",
  "tailwind.config.ts": "tailwindConfig",
  "tailwind.config.cjs": "tailwindConfig",
  "next.config.js":   "nextConfig",
  "next.config.mjs":  "nextConfig",
  "next.config.ts":   "nextConfig",
  "webpack.config.js": "webpackConfig",
  "webpack.config.ts": "webpackConfig",
  ".env":             "env",
  ".env.local":       "env",
  ".env.development": "env",
  ".env.production":  "env",
  ".env.test":        "env",
  ".env.example":     "env",
  ".env.sample":      "env",
  "favicon.ico":      "favicon",
  "favicon.svg":      "favicon",
  // AI / agent files
  "CLAUDE.md":        "agent",
  "claude.md":        "agent",
  "AGENTS.md":        "agent",
  "agents.md":        "agent",
};

/** Extension → icon ID */
const extensionMap: Record<string, FileIconId> = {
  // TypeScript / JavaScript
  ts:    "typescript",
  tsx:   "typescriptReact",
  mts:   "typescript",
  cts:   "typescript",
  js:    "javascript",
  jsx:   "javascriptReact",
  mjs:   "javascript",
  cjs:   "javascript",
  // Python
  py:    "python",
  pyi:   "python",
  pyw:   "python",
  // Systems
  go:    "go",
  rs:    "rust",
  rb:    "ruby",
  java:  "java",
  kt:    "kotlin",
  kts:   "kotlin",
  swift: "swift",
  c:     "c",
  h:     "c",
  cpp:   "cpp",
  cxx:   "cpp",
  cc:    "cpp",
  hpp:   "cpp",
  cs:    "csharp",
  php:   "php",
  lua:   "lua",
  sh:    "shell",
  bash:  "shell",
  zsh:   "shell",
  fish:  "shell",
  sql:   "sql",
  r:     "r",
  zig:   "zig",
  // Web
  html:  "html",
  htm:   "html",
  css:   "css",
  scss:  "scss",
  sass:  "scss",
  less:  "less",
  svg:   "svg",
  vue:   "vue",
  svelte: "svelte",
  astro: "astro",
  // Data / config
  json:  "json",
  jsonc: "json",
  json5: "json",
  yml:   "yaml",
  yaml:  "yaml",
  toml:  "toml",
  xml:   "xml",
  csv:   "csv",
  ini:   "ini",
  cfg:   "ini",
  graphql: "graphql",
  gql:   "graphql",
  prisma: "prisma",
  proto: "protobuf",
  tf:    "terraform",
  hcl:   "hcl",
  // Prose
  md:    "markdown",
  mdx:   "mdx",
  txt:   "text",
  pdf:   "pdf",
  // Media
  png:   "image",
  jpg:   "image",
  jpeg:  "image",
  gif:   "image",
  webp:  "image",
  avif:  "image",
  ico:   "image",
  bmp:   "image",
  mp4:   "video",
  webm:  "video",
  mov:   "video",
  avi:   "video",
  mp3:   "audio",
  wav:   "audio",
  ogg:   "audio",
  flac:  "audio",
  // Special derived types
  "d.ts": "declaration",
  "d.mts": "declaration",
  "d.cts": "declaration",
  map:   "sourcemap",
  lock:  "lockfile",
  // Binary / archive
  wasm:  "binary",
  exe:   "binary",
  dll:   "binary",
  so:    "binary",
  dylib: "binary",
  zip:   "archive",
  tar:   "archive",
  gz:    "archive",
  bz2:   "archive",
  "7z":  "archive",
  rar:   "archive",
  // Certificates
  pem:   "certificate",
  crt:   "certificate",
  key:   "certificate",
  cert:  "certificate",
};

/** Folder name → base icon ID (without Open suffix) */
const folderNameMap: Record<string, FileIconId> = {
  src:          "folderSrc",
  lib:          "folderSrc",
  source:       "folderSrc",
  components:   "folderComponents",
  node_modules: "folderNodeModules",
  test:         "folderTest",
  tests:        "folderTest",
  __tests__:    "folderTest",
  __test__:     "folderTest",
  spec:         "folderTest",
  specs:        "folderTest",
};

/** Map a base folder icon to its open variant */
const folderOpenMap: Record<string, FileIconId> = {
  folder:               "folderOpen",
  folderSrc:            "folderSrcOpen",
  folderComponents:     "folderComponentsOpen",
  folderNodeModules:    "folderNodeModulesOpen",
  folderTest:           "folderTestOpen",
};

/**
 * Resolve a file/folder name to a semantic icon ID.
 *
 * Priority: exact filename → compound extension → simple extension → default
 */
export function resolveFileIcon(
  fileName: string,
  type: "file" | "dir",
  isOpen = false,
): FileIconId {
  if (type === "dir") {
    const lower = fileName.toLowerCase();
    const base = folderNameMap[lower] ?? "folder";
    if (isOpen) return folderOpenMap[base as string] ?? "folderOpen";
    return base;
  }

  // Exact filename match
  const byName = fileNameMap[fileName];
  if (byName) return byName;

  // Agent files — any .md with "agent" in the name, or SKILL.md
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".md") && (lower.includes("agent") || lower === "skill.md")) return "agent";

  // Compound extensions (e.g. "d.ts", "min.js")
  const parts = fileName.split(".");
  if (parts.length >= 3) {
    const compound = parts.slice(-2).join(".");
    if (compound === "min.js" || compound === "min.css") return "minified";
    const byCompound = extensionMap[compound];
    if (byCompound) return byCompound;
  }

  // Simple extension
  const ext = parts.pop()?.toLowerCase();
  if (ext) {
    // Special: lockfiles
    if (fileName === "package-lock.json" || fileName === "pnpm-lock.yaml" ||
        fileName === "yarn.lock" || fileName === "bun.lockb" ||
        fileName === "Gemfile.lock" || fileName === "poetry.lock" ||
        fileName === "Cargo.lock") {
      return "lockfile";
    }
    const byExt = extensionMap[ext];
    if (byExt) return byExt;
  }

  return "default";
}
