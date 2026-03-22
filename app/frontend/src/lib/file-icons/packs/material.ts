import type { IconPack, IconPackEntry } from "../types";

// ---------------------------------------------------------------------------
// Base shapes — reusable SVG fragments
// ---------------------------------------------------------------------------

/** Document with folded corner */
const docBase = `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="currentColor" opacity="0.15"/><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="none" stroke="currentColor" stroke-width="1.5"/><polyline points="14 2 14 8 20 8" fill="none" stroke="currentColor" stroke-width="1.5"/>`;

/** Document with label text — helper */
function docWithLabel(label: string, labelColor: string): string {
  return `${docBase}<text x="12" y="17" text-anchor="middle" font-size="6" font-weight="700" font-family="monospace" fill="${labelColor}">${label}</text>`;
}

/** Document with a small colored circle badge */
function docWithDot(dotColor: string): string {
  return `${docBase}<circle cx="12" cy="15" r="3" fill="${dotColor}"/>`;
}

/** Gear/config base */
const gearBase = `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="currentColor" opacity="0.1"/><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="none" stroke="currentColor" stroke-width="1.5"/><polyline points="14 2 14 8 20 8" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="15" r="2.5" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M12 11.5v1m0 5v1m-3-3.5h1m5 0h1m-6.2-2.5.7.7m4.3 4.3.7.7m0-5.7-.7.7m-4.3 4.3-.7.7" stroke="currentColor" stroke-width="0.8"/>`;

function gearWithLabel(label: string, labelColor: string): string {
  return `${gearBase}<text x="12" y="21.5" text-anchor="middle" font-size="4" font-weight="700" font-family="monospace" fill="${labelColor}">${label}</text>`;
}

/** Closed folder */
const folderClosed = `<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" fill="currentColor" opacity="0.2"/><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" fill="none" stroke="currentColor" stroke-width="1.5"/>`;

/** Open folder */
const folderOpenSvg = `<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" fill="currentColor" opacity="0.2"/><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 10h20" stroke="currentColor" stroke-width="1" opacity="0.4"/>`;

function folderWithLabel(label: string, open: boolean): string {
  const base = open ? folderOpenSvg : folderClosed;
  return `${base}<text x="12" y="17" text-anchor="middle" font-size="5" font-weight="700" font-family="monospace" fill="currentColor" opacity="0.7">${label}</text>`;
}

/** Media shapes */
const imageSvg = `<rect x="3" y="3" width="18" height="18" rx="2" fill="currentColor" opacity="0.15" stroke="currentColor" stroke-width="1.5"/><circle cx="8.5" cy="8.5" r="1.5" fill="currentColor"/><path d="M21 15l-5-5L5 21" stroke="currentColor" stroke-width="1.5" fill="none"/>`;
const videoSvg = `<rect x="2" y="4" width="20" height="16" rx="2" fill="currentColor" opacity="0.15" stroke="currentColor" stroke-width="1.5"/><polygon points="10,8 16,12 10,16" fill="currentColor"/>`;
const audioSvg = `<path d="M9 18V5l12-2v13" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="18" r="3" fill="currentColor" opacity="0.3" stroke="currentColor" stroke-width="1.5"/><circle cx="18" cy="16" r="3" fill="currentColor" opacity="0.3" stroke="currentColor" stroke-width="1.5"/>`;

/** Lock/shield for lockfiles */
const lockSvg = `${docBase}<rect x="8" y="13" width="8" height="6" rx="1" fill="currentColor" opacity="0.3" stroke="currentColor" stroke-width="1"/><path d="M10 13v-2a2 2 0 0 1 4 0v2" fill="none" stroke="currentColor" stroke-width="1"/>`;

/** Archive/zip */
const archiveSvg = `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="currentColor" opacity="0.15"/><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="none" stroke="currentColor" stroke-width="1.5"/><polyline points="14 2 14 8 20 8" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="10" y="11" width="4" height="2" fill="currentColor" opacity="0.5"/><rect x="10" y="14" width="4" height="2" fill="currentColor" opacity="0.3"/><rect x="10" y="17" width="4" height="2" fill="currentColor" opacity="0.2"/>`;

/** Certificate / key */
const certSvg = `${docBase}<circle cx="12" cy="13" r="2" fill="none" stroke="currentColor" stroke-width="1"/><line x1="12" y1="15" x2="12" y2="19" stroke="currentColor" stroke-width="1"/><line x1="10.5" y1="17.5" x2="13.5" y2="17.5" stroke="currentColor" stroke-width="1"/>`;

// ---------------------------------------------------------------------------
// Iconic SVG shapes — recognizable logo-style icons
// ---------------------------------------------------------------------------

/** React atom/orbital symbol */
const reactSvg = `<ellipse cx="12" cy="12" rx="10" ry="4" fill="none" stroke="#61DAFB" stroke-width="1.5"/><ellipse cx="12" cy="12" rx="10" ry="4" fill="none" stroke="#61DAFB" stroke-width="1.5" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4" fill="none" stroke="#61DAFB" stroke-width="1.5" transform="rotate(120 12 12)"/><circle cx="12" cy="12" r="2" fill="#61DAFB"/>`;

/** TypeScript — "TS" in blue rounded square */
const typescriptSvg = `<rect x="2" y="2" width="20" height="20" rx="3" fill="#3178C6"/><text x="12" y="16.5" text-anchor="middle" font-size="10" font-weight="700" font-family="sans-serif" fill="#fff">TS</text>`;

/** JavaScript — "JS" in yellow square */
const javascriptSvg = `<rect x="2" y="2" width="20" height="20" rx="1" fill="#F7DF1E"/><text x="12" y="16.5" text-anchor="middle" font-size="10" font-weight="700" font-family="sans-serif" fill="#333">JS</text>`;

/** CSS — # hash symbol */
const cssSvg = `<rect x="2" y="2" width="20" height="20" rx="3" fill="#663399"/><text x="12" y="17" text-anchor="middle" font-size="14" font-weight="700" font-family="sans-serif" fill="#fff">#</text>`;

/** HTML — angle brackets <> */
const htmlSvg = `<rect x="2" y="2" width="20" height="20" rx="3" fill="#E34C26"/><text x="12" y="17" text-anchor="middle" font-size="12" font-weight="700" font-family="monospace" fill="#fff">&lt;/&gt;</text>`;

/** JSON — curly braces {} */
const jsonSvg = `<rect x="2" y="2" width="20" height="20" rx="3" fill="#F5A623" opacity="0.15"/><text x="12" y="17.5" text-anchor="middle" font-size="14" font-weight="700" font-family="monospace" fill="#F5A623">{}</text>`;

/** Python — two intertwined arcs */
const pythonSvg = `<path d="M11.9 2C7.4 2 7.8 4 7.8 4l0 3.1h4.3v.9H5.5S2 7.5 2 12.1s3 4.4 3 4.4h1.8v-2.1s-.1-3 3-3h4.2s2.8 0 2.8-2.7V5.3S17.2 2 11.9 2zm-2.4 1.9a.9.9 0 1 1 0 1.8.9.9 0 0 1 0-1.8z" fill="#3572A5"/><path d="M12.1 22c4.5 0 4.1-2 4.1-2l0-3.1h-4.3v-.9h6.6s3.5.5 3.5-4.1-3-4.4-3-4.4h-1.8v2.1s.1 3-3 3H9.9s-2.8 0-2.8 2.7v3.4S6.8 22 12.1 22zm2.4-1.9a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8z" fill="#FFD43B"/>`;

/** Go — "Go" text */
const goSvg = `<rect x="2" y="4" width="20" height="16" rx="3" fill="#00ADD8" opacity="0.15"/><text x="12" y="16" text-anchor="middle" font-size="11" font-weight="700" font-family="sans-serif" fill="#00ADD8">Go</text>`;

/** Rust — gear/cog shape */
const rustSvg = `<circle cx="12" cy="12" r="8" fill="none" stroke="#CE422B" stroke-width="2"/><circle cx="12" cy="12" r="3.5" fill="none" stroke="#CE422B" stroke-width="1.5"/><line x1="12" y1="2" x2="12" y2="5" stroke="#CE422B" stroke-width="2"/><line x1="12" y1="19" x2="12" y2="22" stroke="#CE422B" stroke-width="2"/><line x1="2" y1="12" x2="5" y2="12" stroke="#CE422B" stroke-width="2"/><line x1="19" y1="12" x2="22" y2="12" stroke="#CE422B" stroke-width="2"/><line x1="4.9" y1="4.9" x2="7" y2="7" stroke="#CE422B" stroke-width="2"/><line x1="17" y1="17" x2="19.1" y2="19.1" stroke="#CE422B" stroke-width="2"/><line x1="4.9" y1="19.1" x2="7" y2="17" stroke="#CE422B" stroke-width="2"/><line x1="17" y1="7" x2="19.1" y2="4.9" stroke="#CE422B" stroke-width="2"/>`;

/** Vue — V shield shape */
const vueSvg = `<polygon points="12,3 2,3 12,21" fill="#41B883" opacity="0.7"/><polygon points="12,3 22,3 12,21" fill="#41B883"/><polygon points="12,7 6,3 12,17" fill="#35495E" opacity="0.7"/><polygon points="12,7 18,3 12,17" fill="#35495E"/>`;

/** Svelte — S flame shape */
const svelteSvg = `<path d="M18.2 3.8c-2.3-3-6.5-3.6-9.5-1.6L4.5 5.1C3.2 6 2.3 7.3 2 8.8c-.3 1.2-.1 2.4.3 3.5-.5.8-.7 1.7-.8 2.6-.2 1.6.3 3.2 1.3 4.5 2.3 3 6.5 3.6 9.5 1.6l4.2-2.9c1.3-.9 2.2-2.2 2.5-3.7.3-1.2.1-2.4-.3-3.5.5-.8.7-1.7.8-2.6.2-1.6-.3-3.2-1.3-4.5z" fill="#FF3E00"/><path d="M9.2 19.8c-1.8-.5-3-2-3.2-3.8 0-.4.1-.9.2-1.3l.3-.7.7.5c.7.5 1.4.8 2.2 1l.2 0 0 .3c0 .5.2.9.5 1.2.6.5 1.5.5 2.1.1l4.2-2.9c.3-.2.5-.6.6-1 .1-.4 0-.8-.2-1.2-.6-.5-1.5-.5-2.1-.1l-1.6 1.1c-1.7 1.2-4 .8-5.3-.8-.7-.8-1-1.8-.8-2.9.1-.9.6-1.7 1.3-2.2l4.2-2.9c.6-.4 1.3-.6 2-.7 1.8.5 3 2 3.2 3.8 0 .4-.1.9-.2 1.3l-.3.7-.7-.5c-.7-.5-1.4-.8-2.2-1l-.2 0 0-.3c0-.5-.2-.9-.5-1.2-.6-.5-1.5-.5-2.1.1L7.6 9.3c-.3.2-.5.6-.6 1-.1.4 0 .8.2 1.2.6.5 1.5.5 2.1-.1l1.6-1.1c1.7-1.2 4-.8 5.3.8.7.8 1 1.8.8 2.9-.1.9-.6 1.7-1.3 2.2l-4.2 2.9c-.6.4-1.3.6-2 .7z" fill="#fff"/>`;

/** Markdown — simple blue M */
const markdownSvg = `<path d="M5 18V6l5 6.5L15 6v12" fill="none" stroke="#519ABA" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M19 11v7m0 0l2.5-3m-2.5 3l-2.5-3" fill="none" stroke="#519ABA" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`;

/** Env — key icon */
const envSvg = `<path d="M20 2H4a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z" fill="#ECD53F" opacity="0.15"/><path d="M20 2H4a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z" fill="none" stroke="#ECD53F" stroke-width="1.5"/><circle cx="9" cy="12" r="3" fill="none" stroke="#ECD53F" stroke-width="1.5"/><path d="M12 12h6m-2-2v4m-2-4v4" fill="none" stroke="#ECD53F" stroke-width="1.5" stroke-linecap="round"/>`;

/** Makefile / Justfile — terminal/list icon */
const makefileSvg = `<rect x="3" y="3" width="18" height="18" rx="2" fill="#6D8086" opacity="0.15"/><rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="#6D8086" stroke-width="1.5"/><path d="M7 8l3 2-3 2" fill="none" stroke="#6D8086" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="16" x2="17" y2="16" stroke="#6D8086" stroke-width="1.5" stroke-linecap="round"/>`;

/** Git — branch/merge icon */
const gitSvg = `<circle cx="12" cy="5" r="2" fill="none" stroke="#F05032" stroke-width="1.5"/><circle cx="7" cy="19" r="2" fill="none" stroke="#F05032" stroke-width="1.5"/><circle cx="17" cy="19" r="2" fill="none" stroke="#F05032" stroke-width="1.5"/><line x1="12" y1="7" x2="12" y2="13" stroke="#F05032" stroke-width="1.5"/><path d="M12 13c0 3-5 4-5 6" fill="none" stroke="#F05032" stroke-width="1.5"/><path d="M12 13c0 3 5 4 5 6" fill="none" stroke="#F05032" stroke-width="1.5"/>`;

/** SCSS/Sass — S in rounded rectangle */
const scssSvg = `<rect x="2" y="2" width="20" height="20" rx="3" fill="#CC6699"/><text x="12" y="17" text-anchor="middle" font-size="14" font-weight="700" font-family="sans-serif" fill="#fff">S</text>`;

/** Docker — whale with containers */
const dockerSvg = `<path d="M21 10.5c-.4-.3-1.3-.5-2-.4-.2-1-.7-1.8-1.4-2.4l-.3-.2-.2.3c-.3.4-.5 1-.5 1.5 0 .6.1 1.1.4 1.6-.6.3-1.5.5-2.3.5H2.3l-.1.4c-.1.8 0 1.7.3 2.5.4 1 1 1.8 1.9 2.3 1 .6 2.3.9 3.8.9 3.6 0 6.3-1.7 7.6-4.6.9 0 1.8-.1 2.4-.7.5-.4.7-1 .8-1.7zm-15.5-.7h2v2h-2zm2.8 0h2v2h-2zm2.7 0h2v2h-2zm2.8 0h2v2h-2zm-2.8-2.7h2v2h-2zm2.8 0h2v2h-2zm2.7 0h2v2h-2zm0-2.7h2v2h-2z" fill="#2496ED"/>`;

/** YAML — data/config lines icon */
const yamlSvg = `<rect x="3" y="3" width="18" height="18" rx="2" fill="#CB171E" opacity="0.15"/><line x1="7" y1="8" x2="17" y2="8" stroke="#CB171E" stroke-width="1.5" stroke-linecap="round"/><line x1="9" y1="12" x2="17" y2="12" stroke="#CB171E" stroke-width="1.5" stroke-linecap="round"/><line x1="9" y1="16" x2="15" y2="16" stroke="#CB171E" stroke-width="1.5" stroke-linecap="round"/><circle cx="5.5" cy="12" r="1" fill="#CB171E"/><circle cx="5.5" cy="16" r="1" fill="#CB171E"/>`;

/** SVG — diamond/star shape */
const svgIconSvg = `<polygon points="12,2 22,12 12,22 2,12" fill="#FFB13B" opacity="0.2" stroke="#FFB13B" stroke-width="1.5"/><polygon points="12,6 18,12 12,18 6,12" fill="#FFB13B" opacity="0.4"/>`;

/** Shell/Bash — terminal prompt */
const shellSvg = `<rect x="2" y="3" width="20" height="18" rx="2" fill="#89E051" opacity="0.15" stroke="#89E051" stroke-width="1.5"/><path d="M6 9l4 3-4 3" fill="none" stroke="#89E051" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="16" x2="18" y2="16" stroke="#89E051" stroke-width="2" stroke-linecap="round"/>`;

// ---------------------------------------------------------------------------
// Color palette (Material Icon Theme inspired)
// ---------------------------------------------------------------------------
const colors = {
  typescript:  "#3178c6",
  javascript:  "#f7df1e",
  python:      "#3572A5",
  go:          "#00ADD8",
  rust:        "#CE422B",
  ruby:        "#CC342D",
  java:        "#E76F00",
  kotlin:      "#7F52FF",
  swift:       "#F05138",
  c:           "#A8B9CC",
  cpp:         "#00599C",
  csharp:      "#68217A",
  php:         "#777BB4",
  lua:         "#000080",
  shell:       "#89E051",
  sql:         "#E38C00",
  r:           "#276DC3",
  zig:         "#F7A41D",
  html:        "#E34C26",
  css:         "#663399",
  scss:        "#CD6799",
  less:        "#1D365D",
  svg:         "#FFB13B",
  vue:         "#42b883",
  svelte:      "#FF3E00",
  astro:       "#BC52EE",
  json:        "#F5A623",
  yaml:        "#CB171E",
  toml:        "#9C4121",
  xml:         "#E37933",
  csv:         "#4CAF50",
  env:         "#ECD53F",
  ini:         "#8E8E8E",
  graphql:     "#E10098",
  prisma:      "#2D3748",
  protobuf:    "#4285F4",
  terraform:   "#7B42BC",
  hcl:         "#7B42BC",
  markdown:    "#808080",
  mdx:         "#FCB32C",
  text:        "#8E8E8E",
  pdf:         "#EC1C24",
  image:       "#26A69A",
  video:       "#EF5350",
  audio:       "#FF9800",
  favicon:     "#FFB300",
  dockerfile:  "#2496ED",
  dockerCompose: "#2496ED",
  gitignore:   "#F05033",
  makefile:    "#6D8086",
  packageJson: "#8BC34A",
  tsconfig:    "#3178c6",
  viteConfig:  "#646CFF",
  eslint:      "#4B32C3",
  prettier:    "#F7B93E",
  tailwind:    "#06B6D4",
  nextConfig:  "#000000",
  webpack:     "#8DD6F9",
  lockfile:    "#8E8E8E",
  sourcemap:   "#F5A623",
  minified:    "#8E8E8E",
  declaration: "#3178c6",
  binary:      "#607D8B",
  archive:     "#8D6E63",
  certificate: "#FF7043",
  folder:      "#90A4AE",
  folderSrc:   "#42A5F5",
  folderComp:  "#AB47BC",
  folderNM:    "#8D6E63",
  folderTest:  "#66BB6A",
  agent:       "#DA7756",
  default:     "#90A4AE",
};

// ---------------------------------------------------------------------------
// Pack entries
// ---------------------------------------------------------------------------

function e(svg: string, color: string): IconPackEntry {
  return { svg, color };
}

export const materialPack: IconPack = {
  // --- Languages (iconic) ---
  typescript:       e(typescriptSvg, colors.typescript),
  typescriptReact:  e(reactSvg, colors.typescript),
  javascript:       e(javascriptSvg, colors.javascript),
  javascriptReact:  e(reactSvg, colors.javascript),
  python:           e(pythonSvg, colors.python),
  go:               e(goSvg, colors.go),
  rust:             e(rustSvg, colors.rust),
  ruby:             e(docWithLabel("RB", colors.ruby), colors.ruby),
  java:             e(docWithLabel("JV", colors.java), colors.java),
  kotlin:           e(docWithLabel("KT", colors.kotlin), colors.kotlin),
  swift:            e(docWithLabel("SW", colors.swift), colors.swift),
  c:                e(docWithLabel("C", colors.c), colors.c),
  cpp:              e(docWithLabel("C+", colors.cpp), colors.cpp),
  csharp:           e(docWithLabel("C#", colors.csharp), colors.csharp),
  php:              e(docWithLabel("PHP", colors.php), colors.php),
  lua:              e(docWithLabel("LU", colors.lua), colors.lua),
  shell:            e(shellSvg, colors.shell),
  sql:              e(docWithLabel("SQL", colors.sql), colors.sql),
  r:                e(docWithLabel("R", colors.r), colors.r),
  zig:              e(docWithLabel("ZG", colors.zig), colors.zig),

  // --- Web (iconic) ---
  html:             e(htmlSvg, colors.html),
  css:              e(cssSvg, colors.css),
  scss:             e(scssSvg, colors.scss),
  less:             e(docWithLabel("LE", colors.less), colors.less),
  svg:              e(svgIconSvg, colors.svg),
  vue:              e(vueSvg, colors.vue),
  svelte:           e(svelteSvg, colors.svelte),
  astro:            e(docWithLabel("AS", colors.astro), colors.astro),

  // --- Data / config formats ---
  json:             e(jsonSvg, colors.json),
  yaml:             e(yamlSvg, colors.yaml),
  toml:             e(docWithLabel("TM", colors.toml), colors.toml),
  xml:              e(docWithLabel("XML", colors.xml), colors.xml),
  csv:              e(docWithLabel("CSV", colors.csv), colors.csv),
  env:              e(envSvg, colors.env),
  ini:              e(docWithLabel("INI", colors.ini), colors.ini),
  graphql:          e(docWithLabel("GQL", colors.graphql), colors.graphql),
  prisma:           e(docWithDot(colors.prisma), colors.prisma),
  protobuf:         e(docWithLabel("PB", colors.protobuf), colors.protobuf),
  terraform:        e(docWithLabel("TF", colors.terraform), colors.terraform),
  hcl:              e(docWithLabel("HCL", colors.hcl), colors.hcl),

  // --- Prose / docs ---
  markdown:         { svg: markdownSvg, color: colors.markdown },
  mdx:              e(docWithLabel("MDX", colors.mdx), colors.mdx),
  text:             e(docWithLabel("TXT", colors.text), colors.text),
  pdf:              e(docWithLabel("PDF", colors.pdf), colors.pdf),

  // --- Media ---
  image:            e(imageSvg, colors.image),
  video:            e(videoSvg, colors.video),
  audio:            e(audioSvg, colors.audio),
  favicon:          e(docWithDot(colors.favicon), colors.favicon),

  // --- DevOps / dotfiles (iconic) ---
  dockerfile:       e(dockerSvg, colors.dockerfile),
  "docker-compose": e(dockerSvg, colors.dockerCompose),
  gitignore:        e(gitSvg, colors.gitignore),
  makefile:         e(makefileSvg, colors.makefile),

  // --- Config files ---
  packageJson:      e(gearWithLabel("PKG", colors.packageJson), colors.packageJson),
  tsconfig:         e(gearWithLabel("TS", colors.tsconfig), colors.tsconfig),
  viteConfig:       e(gearWithLabel("VT", colors.viteConfig), colors.viteConfig),
  eslint:           e(gearWithLabel("ESL", colors.eslint), colors.eslint),
  prettier:         e(gearWithLabel("FMT", colors.prettier), colors.prettier),
  tailwindConfig:   e(gearWithLabel("TW", colors.tailwind), colors.tailwind),
  nextConfig:       e(gearWithLabel("NX", colors.nextConfig), colors.nextConfig),
  webpackConfig:    e(gearWithLabel("WP", colors.webpack), colors.webpack),

  // --- Special derived types ---
  lockfile:         e(lockSvg, colors.lockfile),
  sourcemap:        e(docWithLabel("MAP", colors.sourcemap), colors.sourcemap),
  minified:         e(docWithLabel("MIN", colors.minified), colors.minified),
  declaration:      e(docWithLabel("DTS", colors.declaration), colors.declaration),

  // --- Binary ---
  binary:           e(docWithDot(colors.binary), colors.binary),
  archive:          e(archiveSvg, colors.archive),
  certificate:      e(certSvg, colors.certificate),

  // --- Folders ---
  folder:                  e(folderClosed, colors.folder),
  folderOpen:              e(folderOpenSvg, colors.folder),
  folderSrc:               e(folderWithLabel("src", false), colors.folderSrc),
  folderSrcOpen:           e(folderWithLabel("src", true), colors.folderSrc),
  folderComponents:        e(folderWithLabel("◇", false), colors.folderComp),
  folderComponentsOpen:    e(folderWithLabel("◇", true), colors.folderComp),
  folderNodeModules:       e(folderWithLabel("nm", false), colors.folderNM),
  folderNodeModulesOpen:   e(folderWithLabel("nm", true), colors.folderNM),
  folderTest:              e(folderWithLabel("✓", false), colors.folderTest),
  folderTestOpen:          e(folderWithLabel("✓", true), colors.folderTest),

  // --- AI / Agent ---
  agent:            { svg: `<line x1="12" y1="2" x2="12" y2="22" stroke="#DA7756" stroke-width="2" stroke-linecap="round"/><line x1="2" y1="12" x2="22" y2="12" stroke="#DA7756" stroke-width="2" stroke-linecap="round"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07" stroke="#DA7756" stroke-width="2" stroke-linecap="round"/><line x1="19.07" y1="4.93" x2="4.93" y2="19.07" stroke="#DA7756" stroke-width="2" stroke-linecap="round"/>`, color: colors.agent },

  // --- Fallback ---
  default:          e(docBase, colors.default),
};
