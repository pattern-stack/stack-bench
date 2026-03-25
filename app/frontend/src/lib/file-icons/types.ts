/** Semantic icon IDs — the abstraction layer between file names and visuals */
export type FileIconId =
  // Languages
  | "typescript" | "typescriptReact" | "javascript" | "javascriptReact"
  | "python" | "go" | "rust" | "ruby" | "java" | "kotlin" | "swift"
  | "c" | "cpp" | "csharp" | "php" | "lua" | "shell" | "sql" | "r" | "zig"
  // Web
  | "html" | "css" | "scss" | "less" | "svg" | "vue" | "svelte" | "astro"
  // Data / config formats
  | "json" | "yaml" | "toml" | "xml" | "csv" | "env" | "ini" | "graphql"
  | "prisma" | "protobuf" | "terraform" | "hcl"
  // Prose / docs
  | "markdown" | "mdx" | "text" | "pdf"
  // Media
  | "image" | "video" | "audio" | "favicon"
  // DevOps / dotfiles
  | "dockerfile" | "docker-compose" | "gitignore" | "makefile"
  // Config files
  | "packageJson" | "tsconfig" | "viteConfig" | "eslint" | "prettier"
  | "tailwindConfig" | "nextConfig" | "webpackConfig"
  // AI / agent files
  | "agent"
  // Derived / special file types
  | "lockfile" | "sourcemap" | "minified" | "declaration"
  // Binary
  | "binary" | "archive" | "certificate"
  // Folders
  | "folder" | "folderOpen" | "folderSrc" | "folderSrcOpen"
  | "folderComponents" | "folderComponentsOpen"
  | "folderNodeModules" | "folderNodeModulesOpen"
  | "folderTest" | "folderTestOpen"
  // Fallback
  | "default";

export interface IconPackEntry {
  svg: string;      // Raw SVG content (elements inside the <svg> tag)
  color: string;    // Hex color
  viewBox?: string; // Defaults to "0 0 24 24"
}

export type IconPack = Record<FileIconId, IconPackEntry>;
