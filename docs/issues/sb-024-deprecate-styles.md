---
id: SB-024
title: Deprecate ui/styles.go
status: ready
epic: EP-006
depends_on: [SB-016]
branch:
pr:
stack: cli-components
stack_index: 11
created: 2026-03-22
---

# Deprecate ui/styles.go

## Summary

Remove the legacy `ui.Dim`, `ui.Fg`, `ui.Bold`, `ui.Green`, `ui.Red`, `ui.Accent` convenience vars and `RefreshStyles()`. All callers should use components or direct `theme.Resolve()` by this point.

## Scope

What's in:
- Delete `app/cli/internal/ui/styles.go`
- Find and migrate any remaining callers to theme tokens or atoms
- Verify no imports of the old style vars remain

What's out:
- Nothing — this is pure cleanup

## Implementation

```
app/cli/internal/ui/styles.go (DELETE)
```

## Verification

- [ ] `styles.go` deleted
- [ ] `go build ./...` succeeds with no references to old vars
- [ ] `go vet ./...` clean
