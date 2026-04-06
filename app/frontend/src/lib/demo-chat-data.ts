import type { ChatMessage } from "@/types/chat";

/**
 * Demo conversation data for the workspace detail view.
 * Simulates a multi-agent pipeline: Architect → Builder → Validator
 * working on an OAuth 2.1 migration task.
 */

const t = (minutesAgo: number) =>
  new Date(Date.now() - minutesAgo * 60_000).toISOString();

export interface DemoPhase {
  role: string;
  color: string;
  messages: ChatMessage[];
}

export const demoPhases: DemoPhase[] = [
  // ─── PHASE: ARCHITECT ───
  {
    role: "Architect",
    color: "var(--accent)",
    messages: [
      {
        id: "a1",
        role: "assistant",
        timestamp: t(30),
        parts: [
          {
            type: "thinking",
            content:
              "The task is to migrate from OAuth 2.0 to 2.1. I need to understand the current auth implementation — which files handle token exchange, session management, and PKCE. Let me read the existing code first.",
          },
        ],
      },
      {
        id: "a2",
        role: "assistant",
        timestamp: t(29),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc1",
            toolName: "Read",
            state: "complete",
            displayType: "code",
            input: "src/auth/oauth_config.ts",
            output:
              'export const oauthConfig = {\n  authorizationEndpoint: "/oauth/authorize",\n  tokenEndpoint: "/oauth/token",\n  clientId: process.env.OAUTH_CLIENT_ID,\n  responseType: "code",\n  // NOTE: PKCE not enforced — implicit flow still allowed\n  codeChallengeMethod: undefined,\n};',
          },
          {
            type: "toolCall",
            toolCallId: "tc2",
            toolName: "Read",
            state: "complete",
            displayType: "code",
            input: "src/auth/token_exchange.ts",
            output:
              'export async function exchangeCode(code: string): Promise<TokenResponse> {\n  const res = await fetch(config.tokenEndpoint, {\n    method: "POST",\n    body: new URLSearchParams({\n      grant_type: "authorization_code",\n      code,\n      client_id: config.clientId,\n      // No code_verifier — PKCE not implemented\n    }),\n  });\n  return res.json();\n}',
          },
          {
            type: "toolCall",
            toolCallId: "tc3",
            toolName: "Grep",
            state: "complete",
            displayType: "bash",
            input: 'pattern: "implicit|response_type.*token"',
            output:
              "src/auth/oauth_config.ts:8:  // implicit flow still allowed\nsrc/auth/legacy_flow.ts:12:  responseType: 'token',\nsrc/middleware/session.ts:45:  // TODO: remove implicit grant support",
          },
        ],
      },
      {
        id: "a3",
        role: "assistant",
        timestamp: t(28),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc3b",
            toolName: "Read",
            state: "complete",
            displayType: "code",
            input: "src/middleware/session.ts",
            output:
              'import { verifyToken } from "../auth/token_exchange";\nimport type { Request, Response, NextFunction } from "express";\n\ninterface SessionOptions {\n  allowImplicit: boolean;\n  tokenHeader: string;\n}\n\nconst defaults: SessionOptions = {\n  allowImplicit: true,  // DEPRECATED — remove for OAuth 2.1\n  tokenHeader: "Authorization",\n};\n\nexport function sessionMiddleware(opts: Partial<SessionOptions> = {}) {\n  const config = { ...defaults, ...opts };\n\n  return async (req: Request, res: Response, next: NextFunction) => {\n    const header = req.headers[config.tokenHeader.toLowerCase()];\n    if (!header || typeof header !== "string") {\n      return res.status(401).json({ error: "Missing token" });\n    }\n\n    const [scheme, token] = header.split(" ");\n    if (scheme !== "Bearer" || !token) {\n      return res.status(401).json({ error: "Invalid authorization header" });\n    }\n\n    try {\n      const payload = await verifyToken(token);\n      // TODO: remove implicit grant support\n      if (!config.allowImplicit && payload.grant_type === "implicit") {\n        return res.status(403).json({ error: "Implicit grant not allowed" });\n      }\n      req.session = payload;\n      next();\n    } catch (err) {\n      return res.status(401).json({ error: "Token verification failed" });\n    }\n  };\n}',
          },
        ],
      },
      {
        id: "a4",
        role: "assistant",
        timestamp: t(27),
        parts: [
          {
            type: "thinking",
            content:
              "Now I have the full picture. The session middleware has `allowImplicit: true` as a default, meaning all existing deployments silently accept implicit grant tokens. There are two migration strategies here:\n\n1. **Hard cutover** — flip `allowImplicit` to `false` and `requirePKCE` to `true` simultaneously. Simplest code change but breaks any mobile client that hasn't updated. Risky for the v2.3 clients still in the App Store review pipeline.\n\n2. **Gradual migration with feature flag** — add a `OAUTH_MIGRATION_PHASE` env var that controls behavior: `phase1` = PKCE optional (log warnings), `phase2` = PKCE required for web but optional for mobile, `phase3` = PKCE required everywhere + implicit rejected. This is more code but lets us ship without a coordinated deploy.\n\nGiven that the mobile team said their v3.0 release is 2 weeks out, option 2 is safer. I'll recommend the phased approach with explicit migration deadlines.\n\nI also need to flag that `session.ts` line 31 checks `payload.grant_type === \"implicit\"` — but that string comparison will break if any token was issued without a `grant_type` claim. We should treat missing `grant_type` as implicit too, for safety.",
          },
        ],
      },
      {
        id: "a5",
        role: "assistant",
        timestamp: t(26),
        parts: [
          {
            type: "text",
            content:
              "I've analyzed the current OAuth 2.0 implementation across four files. Here's the full assessment:\n\n## Findings\n\n1. **PKCE not enforced** — `codeChallengeMethod` is `undefined` in `oauth_config.ts`. OAuth 2.1 requires PKCE for all public and confidential clients.\n2. **Implicit flow still supported** — `legacy_flow.ts` uses `response_type: 'token'`, and the session middleware defaults to `allowImplicit: true`.\n3. **No `code_verifier` in token exchange** — `token_exchange.ts` sends `authorization_code` without PKCE verification.\n4. **Session middleware has a bug** — `session.ts` line 31 checks `payload.grant_type === \"implicit\"` but tokens issued without a `grant_type` claim slip through. We need to treat missing `grant_type` as implicit for safety.\n\n> **Warning**: A hard cutover will break mobile clients on v2.3 and below. The mobile team's v3.0 release (with PKCE support) is ~2 weeks out. We need a phased approach.\n\n## Recommended Migration Strategy\n\n1. Add a `OAUTH_MIGRATION_PHASE` environment variable with three phases:\n   - `phase1` — PKCE accepted but optional; log warnings for non-PKCE flows\n   - `phase2` — PKCE required for web clients; optional for mobile (user-agent detection)\n   - `phase3` — PKCE required everywhere; implicit grant fully rejected\n2. Update `oauth_config.ts` — set `codeChallengeMethod: \"S256\"` and add the `migrationPhase` config field\n3. Update `token_exchange.ts` — require `code_verifier` based on migration phase\n4. Patch `session.ts` — fix the `grant_type` null check, wire in phase-aware rejection\n5. Delete `legacy_flow.ts` — but only gate its removal behind `phase3`\n\nThe config flag approach means we can ship the code now and flip phases via env var as mobile clients update. No coordinated deploy needed.\n\nHanding off to Builder.",
          },
        ],
      },
    ],
  },

  // ─── PHASE: BUILDER ───
  {
    role: "Builder",
    color: "var(--green)",
    messages: [
      {
        id: "b1",
        role: "user",
        timestamp: t(25),
        parts: [
          {
            type: "text",
            content:
              "Sounds good. Ensure we maintain backward compatibility for existing mobile clients during the migration window.",
          },
        ],
      },
      {
        id: "b2",
        role: "assistant",
        timestamp: t(24),
        parts: [
          {
            type: "text",
            content:
              "Implementing PKCE validation in the token exchange pipeline. I'll start with the config changes, then wire PKCE through the exchange and session middleware.",
          },
          {
            type: "toolCall",
            toolCallId: "tc4",
            toolName: "Edit",
            state: "complete",
            displayType: "diff",
            input: "src/auth/oauth_config.ts",
            output:
              '  export const oauthConfig = {\n    authorizationEndpoint: "/oauth/authorize",\n    tokenEndpoint: "/oauth/token",\n    clientId: process.env.OAUTH_CLIENT_ID,\n    responseType: "code",\n-   codeChallengeMethod: undefined,\n+   codeChallengeMethod: "S256",\n+   requirePKCE: true,\n+   migrationPhase: (process.env.OAUTH_MIGRATION_PHASE ?? "phase1") as\n+     | "phase1"\n+     | "phase2"\n+     | "phase3",\n  };',
          },
        ],
      },
      {
        id: "b3",
        role: "assistant",
        timestamp: t(23),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc5",
            toolName: "Write",
            state: "complete",
            displayType: "code",
            input: "src/auth/pkce.ts",
            output:
              'import { createHash, randomBytes } from "crypto";\n\nexport function generateCodeVerifier(): string {\n  return randomBytes(32).toString("base64url");\n}\n\nexport function generateCodeChallenge(verifier: string): string {\n  const hash = createHash("sha256").update(verifier).digest();\n  return hash.toString("base64url");\n}\n\nexport function validatePKCE(\n  codeChallenge: string,\n  codeVerifier: string\n): boolean {\n  const expected = generateCodeChallenge(codeVerifier);\n  return codeChallenge === expected;\n}',
          },
          {
            type: "toolCall",
            toolCallId: "tc6",
            toolName: "Edit",
            state: "complete",
            displayType: "diff",
            input: "src/auth/token_exchange.ts",
            output:
              '+ import { validatePKCE } from "./pkce";\n\n  export async function exchangeCode(\n    code: string,\n+   codeVerifier?: string\n  ): Promise<TokenResponse> {\n+   // OAuth 2.1: PKCE required for all clients\n+   if (config.requirePKCE && !codeVerifier) {\n+     throw new AuthError("PKCE code_verifier required");\n+   }\n    const res = await fetch(config.tokenEndpoint, {\n      method: "POST",\n      body: new URLSearchParams({\n        grant_type: "authorization_code",\n        code,\n        client_id: config.clientId,\n+       ...(codeVerifier && { code_verifier: codeVerifier }),\n      }),\n    });\n    return res.json();\n  }',
          },
        ],
      },
      {
        id: "b3b",
        role: "assistant",
        timestamp: t(22),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc6b",
            toolName: "Bash",
            state: "complete",
            displayType: "bash",
            input: "npm run test -- --watch src/auth/pkce.test.ts",
            output:
              " PASS  src/auth/pkce.test.ts\n  ✓ generates valid code verifier (2ms)\n  ✓ generates valid S256 challenge (1ms)\n  ✓ validates correct verifier/challenge pair (1ms)\n  ✓ rejects incorrect verifier (1ms)\n  ✓ verifier is URL-safe base64 (0ms)\n  ✓ challenge is deterministic for same verifier (0ms)\n\nTest Suites: 1 passed, 1 total\nTests:       6 passed, 6 total\nTime:        0.42s\n\nWaiting for file changes...",
          },
        ],
      },
      {
        id: "b3c",
        role: "assistant",
        timestamp: t(21),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc6c",
            toolName: "Edit",
            state: "complete",
            displayType: "diff",
            input: "src/middleware/session.ts",
            output:
              '  import { verifyToken } from "../auth/token_exchange";\n+ import { oauthConfig } from "../auth/oauth_config";\n  import type { Request, Response, NextFunction } from "express";\n\n  interface SessionOptions {\n-   allowImplicit: boolean;\n+   allowImplicit?: boolean;\n    tokenHeader: string;\n  }\n\n  const defaults: SessionOptions = {\n-   allowImplicit: true,  // DEPRECATED — remove for OAuth 2.1\n+   allowImplicit: oauthConfig.migrationPhase !== "phase3",\n    tokenHeader: "Authorization",\n  };\n\n  // ... (middleware function unchanged until line 31)\n\n-     if (!config.allowImplicit && payload.grant_type === "implicit") {\n+     const isImplicit = !payload.grant_type || payload.grant_type === "implicit";\n+     if (!config.allowImplicit && isImplicit) {\n+       console.warn(`[oauth-migration] Rejected implicit token: sub=${payload.sub}`);\n        return res.status(403).json({ error: "Implicit grant not allowed" });\n      }',
          },
        ],
      },
      {
        id: "b4",
        role: "assistant",
        timestamp: t(20),
        parts: [
          {
            type: "text",
            content:
              "The backward compatibility approach uses the `OAUTH_MIGRATION_PHASE` env var to control strictness. Here's how it works at the config level:\n\n```typescript\n// In oauth_config.ts — controls PKCE enforcement\nmigrationPhase: (process.env.OAUTH_MIGRATION_PHASE ?? \"phase1\") as\n  | \"phase1\"   // PKCE optional, log warnings\n  | \"phase2\"   // PKCE required for web, optional for mobile\n  | \"phase3\"   // PKCE required everywhere, implicit rejected\n```\n\nThe session middleware now reads this flag to decide whether to allow implicit grant tokens. In `phase1` and `phase2`, existing mobile tokens still work. In `phase3`, they're rejected with a `403` and a warning log so we can track stragglers.\n\nThis means deployments can ship the code today on `phase1`, then flip to `phase2` once web clients are updated, and finally `phase3` after the mobile v3.0 rollout.",
          },
        ],
      },
      {
        id: "b4b",
        role: "user",
        timestamp: t(19),
        parts: [
          {
            type: "text",
            content:
              "Can you also add rate limiting to the token endpoint?",
          },
        ],
      },
      {
        id: "b4c",
        role: "assistant",
        timestamp: t(18),
        parts: [
          {
            type: "text",
            content:
              "Good call — I'll note that as a follow-up task. Keeping this PR focused on PKCE migration. Rate limiting on `/oauth/token` should be its own PR since it'll need its own Redis dependency and config surface. I've added a `TODO` comment at the endpoint for visibility.",
          },
        ],
      },
      {
        id: "b5",
        role: "assistant",
        timestamp: t(17),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc7",
            toolName: "Bash",
            state: "complete",
            displayType: "bash",
            input: "rm src/auth/legacy_flow.ts",
            output: "",
          },
          {
            type: "text",
            content:
              "Removed implicit grant flow. Updated 4 files, created 1 new file (`pkce.ts`). Summary of changes:\n\n- `oauth_config.ts` — enforces `S256`, adds `migrationPhase` flag\n- `token_exchange.ts` — requires `code_verifier` (phase-dependent)\n- `session.ts` — fixed null `grant_type` bug, wired phase-aware implicit rejection\n- `pkce.ts` — new PKCE utility (generate verifier/challenge, validate pair)\n- `legacy_flow.ts` — deleted\n\nHanding off to Validator.",
          },
        ],
      },
    ],
  },

  // ─── PHASE: VALIDATOR ───
  {
    role: "Validator",
    color: "var(--purple)",
    messages: [
      {
        id: "v1",
        role: "assistant",
        timestamp: t(15),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc8",
            toolName: "Bash",
            state: "complete",
            displayType: "bash",
            input: "npm run test -- --run src/auth/",
            output:
              " PASS  src/auth/pkce.test.ts\n  ✓ generates valid code verifier (2ms)\n  ✓ generates valid S256 challenge (1ms)\n  ✓ validates correct verifier (1ms)\n  ✓ rejects incorrect verifier (1ms)\n\n PASS  src/auth/token_exchange.test.ts\n  ✓ exchanges code with PKCE verifier (3ms)\n  ✓ throws when PKCE required but missing (1ms)\n  ✓ allows missing verifier in phase1 compat mode (2ms)\n  ✓ requires verifier in phase3 strict mode (1ms)\n\n PASS  src/auth/oauth_config.test.ts\n  ✓ enforces S256 challenge method (1ms)\n  ✓ defaults to phase1 migration (1ms)\n  ✓ reads OAUTH_MIGRATION_PHASE from env (1ms)\n\nTest Suites: 3 passed, 3 total\nTests:       11 passed, 11 total\nTime:        1.31s",
          },
          {
            type: "toolCall",
            toolCallId: "tc9",
            toolName: "Bash",
            state: "complete",
            displayType: "bash",
            input: "npm run lint && npm run typecheck",
            output:
              "✨ No lint errors found.\n✨ TypeScript: 0 errors in 142 files.",
          },
        ],
      },
      {
        id: "v1b",
        role: "assistant",
        timestamp: t(14),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc9b",
            toolName: "Bash",
            state: "complete",
            displayType: "bash",
            input: "npm run test:integration -- --run src/auth/ src/middleware/",
            output:
              " PASS  src/auth/integration/oauth_flow.test.ts\n  ✓ full PKCE flow: authorize → exchange → session (48ms)\n  ✓ rejects token exchange without code_verifier in phase3 (12ms)\n  ✓ accepts token exchange without code_verifier in phase1 (15ms)\n  ✓ session middleware rejects implicit tokens in phase3 (8ms)\n  ✓ session middleware allows implicit tokens in phase1 (9ms)\n  ✓ session middleware rejects tokens with missing grant_type in phase3 (7ms)\n\n PASS  src/middleware/integration/session_compat.test.ts\n  ✓ existing mobile tokens work in phase1 (11ms)\n  ✓ existing mobile tokens work in phase2 (10ms)\n  ✓ existing mobile tokens rejected in phase3 with 403 (9ms)\n  ✓ web client PKCE tokens work across all phases (22ms)\n\nTest Suites: 2 passed, 2 total\nTests:       10 passed, 10 total\nTime:        3.87s",
          },
        ],
      },
      {
        id: "v2",
        role: "assistant",
        timestamp: t(13),
        parts: [
          {
            type: "text",
            content:
              "All quality gates passed. Here's the full test coverage breakdown:\n\n## Test Results\n\n| Suite | File | Tests | Status |\n|-------|------|------:|--------|\n| Unit | `pkce.test.ts` | 4 | Pass |\n| Unit | `token_exchange.test.ts` | 4 | Pass |\n| Unit | `oauth_config.test.ts` | 3 | Pass |\n| Integration | `oauth_flow.test.ts` | 6 | Pass |\n| Integration | `session_compat.test.ts` | 4 | Pass |\n| **Total** | | **21** | **Pass** |\n\n**Lint**: Clean | **TypeCheck**: 0 errors in 142 files",
          },
        ],
      },
      {
        id: "v3",
        role: "assistant",
        timestamp: t(12),
        parts: [
          {
            type: "text",
            content:
              "## Final Summary\n\nOAuth 2.1 PKCE migration is complete and validated. The implementation uses a phased rollout controlled by `OAUTH_MIGRATION_PHASE`.\n\n### Checklist\n\n- [x] PKCE (`S256`) enforced in `oauth_config.ts`\n- [x] `code_verifier` wired into `token_exchange.ts`\n- [x] Session middleware patched — fixed null `grant_type` bug, phase-aware rejection\n- [x] `legacy_flow.ts` removed (implicit grant eliminated)\n- [x] Backward compatibility confirmed — mobile clients work in `phase1` and `phase2`\n- [x] 21 tests passing (11 unit + 10 integration)\n- [x] Lint and typecheck clean\n- [ ] Follow-up: Rate limiting on `/oauth/token` (separate PR)\n- [ ] Follow-up: Flip to `phase3` after mobile v3.0 rollout (~2 weeks)\n\nReady to merge.",
          },
        ],
      },
    ],
  },
];
