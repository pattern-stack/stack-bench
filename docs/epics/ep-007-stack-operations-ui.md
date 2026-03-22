---
id: EP-007
title: Stack Operations UI — Health, Merge Flow, and Activity
status: planning
created: 2026-03-22
target: 2026-03-29
---

# Stack Operations UI — Health, Merge Flow, and Activity

## Objective

Surface the full stack lifecycle in the UI — branch health states, merge readiness, restack needs, conflict detection, and an activity log. This closes the gap between our CLI's stack management capabilities and the frontend, bringing feature parity with Graphite's stack-aware UX.

## Design Reference

- Design agent mockup (screenshot in conversation + `app/frontend/mockups/`)
- Graphite's stack sidebar, merge queue, and CI propagation UX
- Stack CLI v0.6.2 capabilities (`st status`, `st restack`, `st merge`, `st sync`, `st stack check`)

## Issues

| ID | Title | Status | Branch |
|----|-------|--------|--------|
| SB-045 | Branch status enrichment — CI, reviews, restack indicators | draft | -- |
| SB-046 | Merge flow panel — cascade merge with readiness checks | draft | -- |
| SB-047 | Stack operations toolbar — restack, sync, activity log | draft | -- |

## Architecture Notes

- All three issues start with mock data, then wire to real stack CLI / GitHub API
- The stack CLI daemon (`st daemon`) can feed real-time events for the activity log
- Branch health is multi-signal: CI + reviews + conflicts + restack state
- Merge flow maps to `st stack merge` — bottom-up cascade with CI checks between
- Graphite comparison is required during architect phase for each issue

## Acceptance Criteria

- [ ] Each branch shows health state (CI, reviews, conflicts, restack) in the sidebar
- [ ] Stack header shows aggregate health summary ("2 merged, 3 open, 2 need restack")
- [ ] Merge queue view shows readiness per branch with "Merge up to here" action
- [ ] Operations toolbar provides Sync, Restack, Merge with progress feedback
- [ ] Activity log shows recent stack operations with timestamps
- [ ] Upstack PRs show "blocked by #N" when downstack CI fails
- [ ] All features map cleanly to stack CLI commands for future backend wiring

## Dependencies

- Depends on EP-006 (Frontend MVP) and file-viewer stack being merged
- Stack CLI daemon for real-time events (optional for v0, mock first)

## Notes

- Conflict resolution UI (per-file strategies, agent auto-resolve) is captured in SB-047 but deferred to v2
- Speculative CI (Graphite's optimization) is out of scope
- PR inbox / triage view is a separate epic
