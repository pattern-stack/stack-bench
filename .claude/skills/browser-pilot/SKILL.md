---
name: browser-pilot
description: Navigate, inspect, and interact with the browser — headed (user's browser) or headless (agent's own). Use when building frontend features, debugging UI issues, checking console errors, verifying visual output, running performance/accessibility audits, or when a coordinating agent needs browser verification. Triggers on words like "check the browser", "look at the app", "console errors", "screenshot", "lighthouse", "accessibility audit", "verify the UI".
allowed-tools: Bash, Read, Glob, Grep
---

# Browser Pilot

## Purpose

Gives Claude Code full browser navigation and inspection capability across two modes: connecting to the user's live browser session (headed) or driving an independent headless browser. This enables build-verify-fix loops, visual QA, console/network monitoring, performance profiling, and accessibility auditing — either for direct user interaction or as part of an orchestrated agent team.

## MCP Servers

This skill depends on three MCP servers configured in `.mcp.json`:

| Server | Package | Mode | Purpose |
|--------|---------|------|---------|
| **chrome-devtools** | `chrome-devtools-mcp` | `--autoConnect` | Connect to user's running Chrome — shared session, cookies, login state |
| **playwright** | `@playwright/mcp` | `--headless` | Agent's own browser — automated testing, screenshots, parallel verification |
| **lighthouse** | `@danielsogl/lighthouse-mcp` | on-demand | Performance, accessibility, SEO, best-practices auditing |

### Setup Requirements

1. **Chrome DevTools MCP** requires Chrome 144+ with remote debugging enabled at `chrome://inspect/#remote-debugging`
2. **Playwright MCP** is self-contained — launches its own browser instance
3. **Lighthouse MCP** runs audits against any reachable URL

## Operating Modes

### Mode 1: Connect to User's Browser (chrome-devtools)

Use when the user says "check my browser", "look at what I'm seeing", or when you need to observe the app in the user's actual session.

**Capabilities:**
- Read console logs and errors (`list_console_messages`)
- Monitor network requests (`list_network_requests`)
- Take screenshots (`take_screenshot`)
- Execute JavaScript (`evaluate_script`)
- Navigate pages (`navigate_page`)
- Click, fill forms, hover (`click`, `fill`, `fill_form`, `hover`)
- Run performance traces (`performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight`)
- Emulate CPU/network conditions (`emulate_cpu`, `emulate_network`)
- Resize viewport (`resize_page`)

**When to use:** Debugging user-reported issues, verifying changes in the user's environment, observing state that depends on login/session.

### Mode 2: Agent's Own Browser (playwright)

Use when you need to independently verify UI, run automated checks, or work without disturbing the user's browser.

**Capabilities:**
- Navigate and interact (`browser_navigate`, `browser_click`, `browser_fill_form`, `browser_type`)
- Accessibility snapshots (`browser_snapshot`) — structured page representation, token-efficient
- Screenshots (`browser_take_screenshot`)
- Console messages (`browser_console_messages`)
- Network requests (`browser_network_requests`)
- JavaScript evaluation (`browser_evaluate`)
- Multi-tab support (`browser_tabs`)

**Key advantage:** Accessibility tree snapshots provide structured, semantic page content without consuming vision tokens. Prefer `browser_snapshot` over `browser_take_screenshot` for understanding page structure.

**When to use:** Automated verification loops, testing across viewports, running checks that shouldn't interfere with the user's session.

### Mode 3: Auditing (lighthouse)

Use when checking performance, accessibility, SEO, or best practices.

**Capabilities:**
- Performance audit (Core Web Vitals, LCP, TBT, CLS)
- Accessibility audit (WCAG compliance)
- SEO audit
- Best practices audit
- Device emulation (mobile/desktop)
- Network throttling simulation

**When to use:** After implementing UI changes, before submitting PRs with frontend changes, when the user asks about performance or accessibility.

## Instructions

### For Direct User Requests

1. Determine which mode is appropriate:
   - User wants you to see what they see → **chrome-devtools** (Mode 1)
   - User wants you to check something independently → **playwright** (Mode 2)
   - User asks about performance/a11y → **lighthouse** (Mode 3)
2. Execute the relevant MCP tool calls
3. Report findings concisely — lead with issues/errors, then context

### For Build-Verify-Fix Loops

When building frontend features, use this pattern:

1. Make code changes
2. Wait for HMR/rebuild (check Vite dev server on port 3500)
3. Use **playwright** to take an accessibility snapshot of the affected page
4. Check for console errors via `browser_console_messages`
5. If issues found, fix and repeat from step 1
6. If clean, optionally run **lighthouse** audit for quality gates

### For Agent Team Coordination

When called by a coordinating agent (e.g., orchestrator or build agent):

1. Accept the verification request with specific URLs and assertions
2. Use **playwright** (headless) for automated checks
3. Return structured results:
   - **pass/fail** status
   - Console errors (if any)
   - Screenshot path (if taken)
   - Accessibility snapshot summary
   - Network errors (if any)

### Console Error Triage

When investigating console errors:

1. First use `list_console_messages` (chrome-devtools) or `browser_console_messages` (playwright)
2. Filter for errors and warnings
3. Correlate with network errors — failed API calls often produce console errors
4. Check for React-specific errors (hydration mismatches, key warnings, unhandled promise rejections)
5. Report with file:line references where available

## Stack Bench Context

The frontend runs on **port 3500** (Vite dev server) with API proxy to backend on **port 8500**.

- Frontend entry: `http://localhost:3500`
- API health check: `http://localhost:8500/health`
- Vite config: `app/frontend/vite.config.ts`

## Output

When reporting browser state, use this structure:

```
**Page:** {url}
**Status:** {pass | issues found}

**Console:** {N errors, M warnings} or "clean"
**Network:** {N failed requests} or "all OK"
**Visual:** {brief description or "matches expected"}

{Details of any issues, with actionable fix suggestions}
```

## Constraints

- Do NOT leave browser sessions open indefinitely — close when verification is complete
- Do NOT use chrome-devtools mode to modify the user's browser state without asking first
- Do NOT take screenshots of pages that may contain sensitive data without user awareness
- PREFER accessibility snapshots over screenshots for page understanding (more token-efficient)
- ALWAYS check that the dev server is running before attempting to navigate to localhost URLs
