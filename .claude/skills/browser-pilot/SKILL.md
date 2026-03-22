---
name: browser-pilot
description: Browser navigation and inspection knowledge. Loaded into the browser-pilot agent as context. Also auto-invoked when the main conversation discusses browser verification, console errors, screenshots, lighthouse audits, or visual QA — to recommend spawning the browser-pilot teammate.
allowed-tools: Bash, Read, Glob, Grep
---

# Browser Pilot

## Purpose

Knowledge base for browser navigation, inspection, and interaction. This skill is preloaded into the `browser-pilot` agent (`.claude/agents/browser-pilot.md`) which owns the MCP server connections.

## When to Spawn a Browser Pilot Teammate

If you are in the main conversation (not already a browser-pilot agent), spawn a browser-pilot teammate when:

- The user asks to "check the browser", "look at the app", "verify the UI"
- You need to verify frontend changes visually
- Console errors or network failures need investigation
- Performance or accessibility auditing is requested
- A build-verify-fix loop is needed during frontend development

**How to spawn:**
```
Use the Agent tool with subagent_type="browser-pilot", team_name=<current-team>, name="browser-pilot"
```

## Three Browser Modes

| Mode | MCP Server | When to Use |
|------|-----------|-------------|
| **User's browser** | `chrome-devtools` | See what the user sees, use their session/cookies |
| **Own browser** | `playwright` | Independent headless verification, automated checks |
| **Auditing** | `lighthouse` | Performance, accessibility, SEO, best practices |

## Key Tool Preferences

- **PREFER** `browser_snapshot` (accessibility tree) over `browser_take_screenshot` — structured, token-efficient, no vision model needed
- **USE** `chrome-devtools` when you need the user's session state (login, cookies)
- **USE** `playwright` when you need independent verification without disturbing the user
- **USE** `lighthouse` for quality gates on performance/a11y

## Stack Bench URLs

| Endpoint | URL |
|----------|-----|
| Frontend | `http://localhost:3500` |
| Backend API | `http://localhost:8500` |
| Health check | `http://localhost:8500/health` |
