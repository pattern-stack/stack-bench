---
name: CLI is a thin client
description: The CLI/TUI is purely a view/controller — no business logic, just renders UI and calls the backend agent API
type: feedback
---

The CLI must contain zero business logic. It is a window/controller only — it renders the UI and interacts with the backend agent API. All logic lives in the backend.

**Why:** Clean separation of concerns. The CLI is a presentation layer over the agent API, not a standalone app.

**How to apply:** When adding CLI features, never put domain logic, decision-making, or data transformation in the Go code. If something requires logic, it belongs in the backend API. The CLI should only handle: rendering, user input, API calls, and streaming responses.
