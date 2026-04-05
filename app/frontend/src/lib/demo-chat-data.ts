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
        timestamp: t(15),
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
        timestamp: t(14),
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
        timestamp: t(13),
        parts: [
          {
            type: "text",
            content:
              "I've analyzed the current OAuth 2.0 implementation. Here's what needs to change for 2.1 compliance:\n\n## Findings\n\n1. **PKCE not enforced** — `codeChallengeMethod` is `undefined` in `oauth_config.ts`. OAuth 2.1 requires PKCE for all clients.\n2. **Implicit flow still supported** — `legacy_flow.ts` uses `response_type: 'token'`. OAuth 2.1 removes the implicit grant entirely.\n3. **No code_verifier in token exchange** — `token_exchange.ts` sends `authorization_code` without PKCE verification.\n\n## Plan\n\n- **Step 1**: Add PKCE support to `oauth_config.ts` — enforce `S256` challenge method\n- **Step 2**: Update `token_exchange.ts` to include `code_verifier`\n- **Step 3**: Remove `legacy_flow.ts` and all implicit grant references\n- **Step 4**: Update session middleware to reject non-PKCE flows\n\nHanding off to Builder.",
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
        timestamp: t(12),
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
        timestamp: t(11),
        parts: [
          {
            type: "text",
            content:
              "Implementing PKCE validation in the token exchange pipeline. Modification of `auth-service/internal/token.go` is in progress.",
          },
          {
            type: "toolCall",
            toolCallId: "tc4",
            toolName: "Edit",
            state: "complete",
            displayType: "diff",
            input: "src/auth/oauth_config.ts",
            output:
              '  export const oauthConfig = {\n    authorizationEndpoint: "/oauth/authorize",\n    tokenEndpoint: "/oauth/token",\n    clientId: process.env.OAUTH_CLIENT_ID,\n    responseType: "code",\n-   codeChallengeMethod: undefined,\n+   codeChallengeMethod: "S256",\n+   requirePKCE: true,\n  };',
          },
        ],
      },
      {
        id: "b3",
        role: "assistant",
        timestamp: t(10),
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
        id: "b4",
        role: "assistant",
        timestamp: t(9),
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
              "Removed implicit grant flow. Updated 3 files, created 1 new file (`pkce.ts`). All changes enforce PKCE with backward compatibility — the `codeVerifier` parameter is optional during the migration window but will be required once `requirePKCE` is flipped to strict mode.\n\nHanding off to Validator.",
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
        timestamp: t(7),
        parts: [
          {
            type: "toolCall",
            toolCallId: "tc8",
            toolName: "Bash",
            state: "complete",
            displayType: "bash",
            input: "npm run test -- --run src/auth/",
            output:
              " PASS  src/auth/pkce.test.ts\n  ✓ generates valid code verifier (2ms)\n  ✓ generates valid S256 challenge (1ms)\n  ✓ validates correct verifier (1ms)\n  ✓ rejects incorrect verifier (1ms)\n\n PASS  src/auth/token_exchange.test.ts\n  ✓ exchanges code with PKCE verifier (3ms)\n  ✓ throws when PKCE required but missing (1ms)\n  ✓ allows missing verifier in compat mode (2ms)\n\n PASS  src/auth/oauth_config.test.ts\n  ✓ enforces S256 challenge method (1ms)\n\nTest Suites: 3 passed, 3 total\nTests:       8 passed, 8 total\nTime:        1.24s",
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
        id: "v2",
        role: "assistant",
        timestamp: t(6),
        parts: [
          {
            type: "text",
            content:
              "All quality gates passed:\n\n- **Tests**: 8/8 passing across 3 suites (PKCE, token exchange, config)\n- **Lint**: Clean\n- **TypeCheck**: 0 errors\n\nThe migration is safe. PKCE is enforced for new clients, backward-compatible for existing mobile clients via optional `codeVerifier`. Implicit grant flow has been fully removed.",
          },
        ],
      },
    ],
  },
];
