# Browser Skill

Interact with your browser directly from Claude Code — see what's on screen, click buttons, fill forms, run visual QA, and audit performance.

## Quick Start

### 1. Launch your browser with remote debugging

Quit your browser first, then relaunch from terminal:

| Browser | Command |
|---------|---------|
| **Arc** | `open -a "Arc" --args --remote-debugging-port=9222` |
| **Chrome** | `open -a "Google Chrome" --args --remote-debugging-port=9222` |
| **Brave** | `open -a "Brave Browser" --args --remote-debugging-port=9222` |
| **Edge** | `open -a "Microsoft Edge" --args --remote-debugging-port=9222` |
| **Chromium** | `open -a "Chromium" --args --remote-debugging-port=9222` |
| **Vivaldi** | `open -a "Vivaldi" --args --remote-debugging-port=9222` |
| **Opera** | `open -a "Opera" --args --remote-debugging-port=9222` |

> Firefox and Safari are **not supported** (they don't use Chrome DevTools Protocol).

### 2. Set your browser preference (one-time)

Claude will ask and set this for you automatically on first use. Or set it yourself in `.claude/settings.local.json` (gitignored):

```json
{
  "env": {
    "BROWSER_PREFERENCE": "arc"
  }
}
```

### 3. Use

**Visual QA** — run a structured check on any URL:
```
/verify                          # check localhost:3500
/verify http://localhost:8500    # check a specific URL
/verify --perf                   # include performance metrics
```

**Open-ended interaction** — tell Claude what to do in your browser:
```
/browse go to localhost:3500 and click the settings button
/browse fill out the login form with test@example.com
/browse take a screenshot of what's on my screen
/browse run a lighthouse accessibility audit
```

Or just talk naturally — the skill auto-invokes when you mention browsers, screenshots, console errors, or visual QA.

## What It Can Do

- **See** your browser — screenshots, accessibility tree snapshots, page content
- **Interact** — click, type, fill forms, hover, drag, press keys, upload files
- **Inspect** — console logs, network requests, run JavaScript in page context
- **Audit** — Lighthouse performance, accessibility, SEO, best practices scores
- **Trace** — Core Web Vitals (LCP, CLS, TTFB), network dependency trees

## Three Modes

| Mode | When to use |
|------|-------------|
| **Your browser** (chrome-devtools) | See what you see, use your login session |
| **Headless** (playwright) | Independent checks without disturbing your browser |
| **Audit** (lighthouse) | Performance and accessibility scoring |

## How It Fits Into Development

During frontend work, the typical loop is:

1. Make code changes
2. `/verify` to check the result visually + console + network
3. Fix issues, repeat

The `browser-pilot` agent (runs on Haiku) can also be spawned as a teammate during `/develop` loops for automated build-verify-fix cycles.
