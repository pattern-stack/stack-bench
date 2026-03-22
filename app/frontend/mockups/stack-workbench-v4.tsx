// Designer mockup — Stack Workbench v4
// Reference implementation for round-2-polish
// Key features: Agent panel, line selection, hover actions, viewed toggle, action bar

import { useState, useRef, useEffect } from "react";

const STACK = [
  { id: 1, name: "1-scaffold", status: "merged", added: 48, removed: 12, files: 2 },
  { id: 2, name: "2-shared-atoms", status: "merged", added: 156, removed: 23, files: 5 },
  { id: 3, name: "3-stack-nav", status: "open", added: 89, removed: 34, files: 3 },
  { id: 4, name: "4-app-shell", status: "local", added: 0, removed: 0, files: 0 },
];

const DIFF_FILES = [
  {
    name: "app/frontend/package.json",
    path: "app/frontend/",
    filename: "package.json",
    status: "A",
    added: 28,
    removed: 0,
    hunks: [
      {
        header: "@@ -0,0 +1,28 @@",
        lines: [
          { type: "add", num: 1, content: "+{" },
          { type: "add", num: 2, content: '+  "name": "@stack-bench/frontend",' },
          { type: "add", num: 3, content: '+  "private": true,' },
          { type: "add", num: 4, content: '+  "version": "0.0.1",' },
          { type: "add", num: 5, content: '+  "type": "module",' },
          { type: "add", num: 6, content: '+  "scripts": {' },
          { type: "add", num: 7, content: '+    "dev": "vite --port 3000",' },
          { type: "add", num: 8, content: '+    "build": "tsc -b && vite build"' },
          { type: "add", num: 9, content: "+  }," },
          { type: "add", num: 10, content: '+  "dependencies": {' },
          { type: "add", num: 11, content: '+    "react": "^18.3.0",' },
          { type: "add", num: 12, content: '+    "react-dom": "^18.3.0"' },
          { type: "add", num: 13, content: "+  }" },
          { type: "add", num: 14, content: "+}" },
        ],
      },
    ],
  },
  {
    name: "app/frontend/src/index.css",
    path: "app/frontend/src/",
    filename: "index.css",
    status: "M",
    added: 20,
    removed: 12,
    hunks: [
      {
        header: "@@ -1,15 +1,23 @@",
        lines: [
          { type: "ctx", oldNum: 1, newNum: 1, content: ' @import "tailwindcss";' },
          { type: "ctx", oldNum: 2, newNum: 2, content: "" },
          { type: "del", oldNum: 3, content: "-/* Default theme */" },
          { type: "del", oldNum: 4, content: "-:root {" },
          { type: "del", oldNum: 5, content: "-  --bg: white;" },
          { type: "del", oldNum: 6, content: "-  --fg: #111;" },
          { type: "del", oldNum: 7, content: "-}" },
          { type: "add", newNum: 3, content: "+/* Dark design system tokens */" },
          { type: "add", newNum: 4, content: "+:root {" },
          { type: "add", newNum: 5, content: "+  --bg-primary: #0a0e17;" },
          { type: "add", newNum: 6, content: "+  --bg-secondary: #111827;" },
          { type: "add", newNum: 7, content: "+  --bg-tertiary: #1e293b;" },
          { type: "add", newNum: 8, content: "+  --fg-primary: #e2e8f0;" },
          { type: "add", newNum: 9, content: "+  --fg-secondary: #94a3b8;" },
          { type: "add", newNum: 10, content: "+  --accent: #6ee7b7;" },
          { type: "add", newNum: 11, content: "+  --accent-dim: #065f46;" },
          { type: "add", newNum: 12, content: "+}" },
          { type: "ctx", oldNum: 8, newNum: 13, content: "" },
          { type: "del", oldNum: 9, content: "-body { background: var(--bg); color: var(--fg); }" },
          { type: "add", newNum: 14, content: "+body {" },
          { type: "add", newNum: 15, content: "+  background: var(--bg-primary);" },
          { type: "add", newNum: 16, content: "+  color: var(--fg-primary);" },
          { type: "add", newNum: 17, content: "+  font-family: 'IBM Plex Mono', monospace;" },
          { type: "add", newNum: 18, content: "+" },
        ],
      },
    ],
  },
];

const AGENT_MESSAGES = [
  { role: "system", content: "Watching branch 1-scaffold — 2 files changed" },
  {
    role: "assistant",
    content: "This scaffold looks clean. The dark design tokens in index.css use a solid naming convention. One thing I'd flag: you're importing tailwindcss but the custom properties duplicate what Tailwind's dark mode already provides. Want me to suggest a reconciliation?",
  },
];

const StatusBadge = ({ status }) => {
  const styles = {
    merged: { bg: "#065f46", color: "#6ee7b7", label: "Merged" },
    open: { bg: "#1e3a5f", color: "#7dd3fc", label: "Open" },
    local: { bg: "#292524", color: "#a8a29e", label: "Local" },
  };
  const s = styles[status];
  return (
    <span style={{ fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 4, background: s.bg, color: s.color, letterSpacing: "0.02em" }}>
      {s.label}
    </span>
  );
};

const FileStatusBadge = ({ status }) => {
  const map = { A: { color: "#6ee7b7", label: "A" }, M: { color: "#fbbf24", label: "M" }, D: { color: "#f87171", label: "D" } };
  const s = map[status] || map.M;
  return <span style={{ fontSize: 11, fontWeight: 600, color: s.color, width: 16, textAlign: "center", flexShrink: 0 }}>{s.label}</span>;
};

const IconSend = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

const IconChevron = ({ dir = "right" }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    style={{ transform: dir === "left" ? "rotate(180deg)" : dir === "down" ? "rotate(90deg)" : "none", transition: "transform 0.15s" }}>
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

const IconComment = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const IconAgent = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3" />
    <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
  </svg>
);

const IconRestack = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
  </svg>
);

// --- Main Components ---
// See the full source in the user's message for StackSidebar, DiffLine, DiffView, AgentPanel, StackWorkbench
