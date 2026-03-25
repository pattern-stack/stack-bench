---
title: "SB-117: GitHub App OAuth + User Auth (Phases 1-2)"
date: 2026-03-24
status: draft
branch: ""
depends_on: []
adrs: []
---

# SB-117: GitHub App OAuth Integration (Phases 1-2)

## Goal

Add user authentication to Stack Bench using pattern-stack's blessed User model and AuthAPI molecule, then implement GitHub App OAuth so each user can connect their GitHub account. This replaces the global `GITHUB_TOKEN` env var with per-user tokens stored encrypted in the database via pattern-stack's Connection model.

This spec covers Phase 1 (user auth) and Phase 2 (GitHub OAuth flow) only. Phase 3 (per-user GitHubAdapter refactor) and Phase 4 (GitHub App features like webhooks, check reporting) are follow-up issues.

## Domain Model

```
User (from pattern_stack.features.users)
  - ActorPattern with first_name, last_name, email, password_hash, oauth_accounts
  - Already exists in pattern-stack; we import it, not re-create it

Connection (from pattern_stack.atoms.integrations.models)
  - BasePattern with provider, name, config_encrypted, enabled, status
  - Stores GitHub OAuth tokens encrypted via Fernet
  - One Connection per user-GitHub link (provider="github", team_id=user.id)

AuthAPI (from pattern_stack.molecules.apis.auth)
  - Login, register, refresh, get_current_user
  - Already exists in pattern-stack; we wrap it in our router
```

### Token Types Stored in Connection.config_encrypted

```python
{
    "access_token": "ghu_xxxx",          # GitHub user access token (8hr TTL)
    "refresh_token": "ghr_xxxx",         # GitHub refresh token (6mo TTL)
    "token_type": "bearer",
    "expires_at": 1711234567,            # Unix timestamp
    "refresh_token_expires_at": 1726786567,
    "github_user_id": 12345,
    "github_login": "dug",
    "scope": "repo,read:org",
}
```

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | User auth: migration, auth router, frontend login | -- |
| 2 | GitHub OAuth: env vars, redirect, callback, Connection storage | Phase 1 |

## File Tree

Files to create or modify, organized by phase:

### Phase 1: User Auth

```
app/backend/
  src/
    features/__init__.py                         # MODIFY - add User, Connection imports
    config/settings.py                           # MODIFY - add JWT_SECRET, ENCRYPTION_KEY
    organisms/api/
      app.py                                     # MODIFY - add auth router, CORS, auth config
      dependencies.py                            # MODIFY - add CurrentUser dependency
      routers/auth.py                            # CREATE - login/register/refresh/me endpoints
      error_handlers.py                          # MODIFY - add auth exception mapping
  alembic/versions/xxxx_add_users_connections.py # CREATE - migration for users + connections tables

app/frontend/
  src/
    lib/auth.ts                                  # CREATE - token storage, auth helpers
    hooks/useAuth.ts                             # CREATE - login/register/refresh hooks
    components/organisms/LoginPage.tsx           # CREATE - login/register form
    App.tsx                                      # MODIFY - wrap with auth gate
    main.tsx                                     # MODIFY - configure apiClient with token getter
```

### Phase 2: GitHub OAuth Flow

```
app/backend/
  src/
    config/settings.py                           # MODIFY - add GitHub App OAuth settings
    molecules/
      apis/github_oauth_api.py                   # CREATE - OAuth business logic molecule
    organisms/api/
      routers/auth.py                            # MODIFY - add /auth/github, /auth/github/callback
      dependencies.py                            # MODIFY - add get_user_github_token helper

app/frontend/
  src/
    hooks/useGitHubConnection.ts                 # CREATE - connection status, connect/disconnect
    components/organisms/GitHubConnectButton.tsx  # CREATE - "Connect GitHub" UI
    components/organisms/LoginPage.tsx           # MODIFY - add "Sign in with GitHub" button
```

## Phase 1 Details: User Auth

### 1.1 Settings Updates

**File**: `app/backend/src/config/settings.py`

Add to `AppSettings`:

```python
# Auth
JWT_SECRET: str = Field(default="change-me-in-production")
ENCRYPTION_KEY: str = Field(default="")  # Fernet key for Connection config encryption

# Frontend URL (for OAuth redirects)
FRONTEND_URL: str = Field(default="http://localhost:5173")
```

The `JWT_SECRET` feeds into pattern-stack's auth config. The `ENCRYPTION_KEY` is a Fernet key generated once via `pattern_stack.atoms.integrations.encryption.generate_key()`.

### 1.2 Auth Config Bridge

In `app.py` lifespan, configure pattern-stack's auth system before yield:

```python
from pattern_stack.atoms.config.auth import configure_auth
configure_auth(jwt_secret_key=settings.JWT_SECRET)
```

This wires our `JWT_SECRET` setting into pattern-stack's JWT module so `create_access_token()` / `decode_token()` use the right key.

### 1.3 Database Migration

**File**: `alembic/versions/xxxx_add_users_connections.py`

Creates both tables from pattern-stack models:

**users table** (from `User(ActorPattern)`):
- `id` UUID PK
- `reference_number` varchar unique
- `display_name` varchar
- `actor_type` varchar default "user"
- `email` varchar unique (from ActorPattern)
- `phone` varchar nullable
- `first_name` varchar
- `last_name` varchar
- `password_hash` varchar nullable (allows OAuth-only users)
- `is_active` bool default true
- `oauth_accounts` jsonb default {}
- `activity_count` int default 0
- `last_activity_at` timestamp nullable
- `created_at`, `updated_at`, `deleted_at` timestamps

**connections table** (from `Connection(BasePattern)`):
- `id` UUID PK
- `reference_number` varchar unique
- `provider` varchar indexed
- `name` varchar
- `webhook_path` varchar unique
- `config_encrypted` bytea
- `enabled` bool default true
- `team_id` UUID nullable indexed (stores owning user_id)
- `status` varchar default "pending"
- `webhook_secret` varchar nullable
- `last_sync_at` timestamp nullable
- `last_error` varchar nullable
- `created_by`, `updated_by` UUID nullable
- `created_at`, `updated_at`, `deleted_at` timestamps

Both models come from pattern-stack. Register them in `features/__init__.py` and generate with `alembic revision --autogenerate`.

### 1.4 Model Registration

**File**: `app/backend/src/features/__init__.py`

Add at the end:

```python
from pattern_stack.features.users.models import User  # noqa: F401
from pattern_stack.atoms.integrations.models import Connection  # noqa: F401
```

### 1.5 Auth Router

**File**: `app/backend/src/organisms/api/routers/auth.py` (CREATE)

Thin router delegating to pattern-stack's `AuthAPI`:

```python
from fastapi import APIRouter, HTTPException
from pattern_stack.molecules.apis.auth import AuthAPI
from pattern_stack.features.auth.schemas import (
    LoginRequest, RegisterRequest, RefreshRequest,
)
from pattern_stack.features.auth.schemas.output import TokenResponse, RefreshResult, UserInfo
from pattern_stack.features.auth.exceptions import (
    EmailAlreadyRegisteredError, WeakPasswordError, InvalidRefreshTokenError,
)
from pattern_stack.features.users.schemas.output import UserResponse
from organisms.api.dependencies import DatabaseSession, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])
auth_api = AuthAPI()

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DatabaseSession):
    result = await auth_api.login(db, data)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await db.commit()
    return result.to_token_response()

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: DatabaseSession):
    try:
        result = await auth_api.register(db, data)
        await db.commit()
        return result.to_token_response()
    except EmailAlreadyRegisteredError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except WeakPasswordError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post("/refresh", response_model=RefreshResult)
async def refresh(data: RefreshRequest, db: DatabaseSession):
    try:
        return await auth_api.refresh_tokens(db, data.refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return user
```

### 1.6 Dependencies Update

**File**: `app/backend/src/organisms/api/dependencies.py` (MODIFY)

Add `CurrentUser` and `OptionalUser` dependencies:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pattern_stack.molecules.apis.auth import AuthAPI
from pattern_stack.features.users.models import User

_bearer_scheme = HTTPBearer(auto_error=False)
_auth_api = AuthAPI()

async def get_current_user(
    db: DatabaseSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await _auth_api.get_current_user(db, credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

async def get_optional_user(
    db: DatabaseSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User | None:
    if not credentials:
        return None
    return await _auth_api.get_current_user(db, credentials.credentials)

OptionalUser = Annotated[User | None, Depends(get_optional_user)]
```

### 1.7 App Setup Updates

**File**: `app/backend/src/organisms/api/app.py` (MODIFY)

Three changes:

1. Import and register auth router:
```python
from organisms.api.routers.auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1")
```

2. Add CORS middleware:
```python
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. Configure pattern-stack auth in lifespan (before yield):
```python
from pattern_stack.atoms.config.auth import configure_auth
configure_auth(jwt_secret_key=settings.JWT_SECRET)
```

### 1.8 Error Handler Updates

**File**: `app/backend/src/organisms/api/error_handlers.py` (MODIFY)

Add auth exception handler:

```python
from pattern_stack.features.auth.exceptions import AuthError

async def auth_exception_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})
```

Register in `app.py`: `app.add_exception_handler(AuthError, auth_exception_handler)`

### 1.9 Frontend: Auth Module

**File**: `app/frontend/src/lib/auth.ts` (CREATE)

```typescript
const ACCESS_TOKEN_KEY = "sb_access_token";
const REFRESH_TOKEN_KEY = "sb_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}
```

### 1.10 Frontend: main.tsx Update

**File**: `app/frontend/src/main.tsx` (MODIFY)

Wire token getter into API client:

```typescript
import { getAccessToken } from "@/lib/auth";

setApiConfig({
  baseUrl: window.location.origin,
  getAuthToken: getAccessToken,
});
```

The generated `ApiClient` already supports `getAuthToken` -- it just needs to be wired up.

### 1.11 Frontend: Auth Hook

**File**: `app/frontend/src/hooks/useAuth.ts` (CREATE)

Provides: `login()`, `register()`, `logout()`, `user`, `isAuthenticated`, `isLoading`.

Uses react-query for `GET /api/v1/auth/me` on mount (when token exists). Handles token refresh on 401 responses. Calls `setTokens()` / `clearTokens()` from `auth.ts`.

### 1.12 Frontend: Login Page

**File**: `app/frontend/src/components/organisms/LoginPage.tsx` (CREATE)

Email/password form with login + register tabs. Follows existing component patterns (functional component, Tailwind, design tokens from `index.css`).

### 1.13 Frontend: App.tsx Auth Gate

**File**: `app/frontend/src/App.tsx` (MODIFY)

Wrap main app in auth check:
- If no token / user not loaded: show `<LoginPage />`
- If authenticated: show current `<AppShell />` content
- On 401 from any API call: clear tokens, show login

## Phase 2 Details: GitHub OAuth Flow

### 2.1 Settings Updates

**File**: `app/backend/src/config/settings.py` (MODIFY)

Add GitHub App OAuth settings:

```python
# GitHub App OAuth
GITHUB_APP_ID: str = Field(default="3169724")
GITHUB_CLIENT_ID: str = Field(default="Iv23lixxrPIqZQvr3BlX")
GITHUB_CLIENT_SECRET: str = Field(default="")  # Required for OAuth
GITHUB_APP_PRIVATE_KEY: str = Field(default="")  # For installation tokens (Phase 4)
```

### 2.2 GitHub OAuth Molecule

**File**: `app/backend/src/molecules/apis/github_oauth_api.py` (CREATE)

Business logic molecule -- no HTTP concerns. Responsibilities:

1. **`get_authorize_url(state)`** -- Generate GitHub OAuth URL with client_id, redirect_uri, scope, state
2. **`exchange_code(code)`** -- POST to `github.com/login/oauth/access_token` with client_id + client_secret
3. **`get_github_user(access_token)`** -- GET `api.github.com/user`
4. **`get_github_emails(access_token)`** -- GET `api.github.com/user/emails` for primary verified email
5. **`find_or_create_user_from_github(db, github_user, emails)`** -- Find by GitHub ID in `oauth_accounts`, then by email, or create new OAuth-only user. Returns `(User, is_new)`.
6. **`store_github_connection(db, user_id, token_data, github_user)`** -- Create or update Connection with encrypted token config. Uses `team_id=user_id` for ownership. Provider="github".
7. **`get_user_github_token(db, user_id)`** -- Decrypt Connection config, check expiry, auto-refresh if expired (with 5-min buffer), return access_token or None.
8. **`_refresh_github_token(config)`** -- POST refresh_token grant to GitHub token endpoint.
9. **`_get_user_connection(db, user_id)`** -- Query Connection where provider="github" and team_id=user_id.

Key constants:
- `AUTHORIZE_URL = "https://github.com/login/oauth/authorize"`
- `TOKEN_URL = "https://github.com/login/oauth/access_token"`
- `USER_URL = "https://api.github.com/user"`
- `USER_EMAILS_URL = "https://api.github.com/user/emails"`
- OAuth scope: `"repo read:org read:user user:email"`

### 2.3 Auth Router OAuth Endpoints

**File**: `app/backend/src/organisms/api/routers/auth.py` (MODIFY)

Add to the existing auth router:

```python
@router.get("/github")
async def github_login():
    """Return GitHub OAuth authorization URL."""
    # Generate state as short-lived signed JWT for CSRF protection
    state = secrets.token_urlsafe(32)
    url = await github_oauth.get_authorize_url(state)
    return {"authorize_url": url, "state": state}

@router.post("/github/callback")
async def github_callback(code: str, state: str, db: DatabaseSession):
    """Exchange GitHub auth code for tokens, create/link user, return JWT."""
    # 1. Exchange code for GitHub tokens
    # 2. Fetch GitHub user profile + emails
    # 3. Find or create user
    # 4. Store GitHub tokens as encrypted Connection
    # 5. Generate Stack Bench JWT tokens
    # 6. Return TokenResponse

@router.get("/github/status")
async def github_connection_status(user: CurrentUser, db: DatabaseSession):
    """Check if current user has connected GitHub account."""
    # Returns: {connected: bool, github_login?: str}

@router.delete("/github")
async def disconnect_github(user: CurrentUser, db: DatabaseSession):
    """Disconnect GitHub account (soft-delete Connection)."""
```

### 2.4 Dependencies: Per-User GitHub Token

**File**: `app/backend/src/organisms/api/dependencies.py` (MODIFY)

Add `UserGitHubToken` dependency for Phase 3 adapter refactoring:

```python
async def get_user_github_token(user: CurrentUser, db: DatabaseSession) -> str:
    token = await _github_oauth.get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(403, detail="GitHub account not connected")
    return token

UserGitHubToken = Annotated[str, Depends(get_user_github_token)]
```

### 2.5 Frontend: GitHub Connection Hook

**File**: `app/frontend/src/hooks/useGitHubConnection.ts` (CREATE)

Provides: `connectionStatus`, `connect()`, `disconnect()`, `isLoading`.

The `connect()` function:
1. Calls `GET /api/v1/auth/github` to get `authorize_url`
2. Opens a popup window to GitHub
3. Popup redirects back to `/auth/github/callback` in the frontend
4. Frontend callback page extracts `code` + `state` from URL
5. POSTs to `POST /api/v1/auth/github/callback`
6. Stores returned JWT tokens, closes popup

### 2.6 Frontend: Connect Button

**File**: `app/frontend/src/components/organisms/GitHubConnectButton.tsx` (CREATE)

Shows connection state:
- Disconnected: "Connect GitHub" button
- Connected: "Connected as @login" with disconnect option
- Loading: spinner

### 2.7 Frontend: Login Page Update

**File**: `app/frontend/src/components/organisms/LoginPage.tsx` (MODIFY)

Add "Sign in with GitHub" button above email/password form. This triggers the same OAuth flow but also logs the user in (returns Stack Bench JWT).

## Environment Variables

### Required (add to `.env`)

```bash
# Phase 1
JWT_SECRET=<random-256-bit-string>
ENCRYPTION_KEY=<fernet-key-from-generate_key()>

# Phase 2
GITHUB_CLIENT_SECRET=<from-github-app-settings>
```

### Optional (have defaults)

```bash
GITHUB_APP_ID=3169724
GITHUB_CLIENT_ID=Iv23lixxrPIqZQvr3BlX
FRONTEND_URL=http://localhost:5173
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/login` | No | Email/password login |
| POST | `/api/v1/auth/register` | No | Create account |
| POST | `/api/v1/auth/refresh` | No | Refresh access token |
| GET | `/api/v1/auth/me` | Yes | Get current user |
| GET | `/api/v1/auth/github` | No | Get GitHub OAuth URL |
| POST | `/api/v1/auth/github/callback` | No | Exchange code for tokens |
| GET | `/api/v1/auth/github/status` | Yes | Check GitHub connection |
| DELETE | `/api/v1/auth/github` | Yes | Disconnect GitHub |

## Pattern-Stack Patterns Used

| What | Pattern-Stack Component | Import Path |
|------|------------------------|-------------|
| User model | `User(ActorPattern)` | `pattern_stack.features.users.models` |
| User service | `UserService(BaseService)` | `pattern_stack.features.users` |
| Auth molecule | `AuthAPI` | `pattern_stack.molecules.apis.auth` |
| Auth schemas | `LoginRequest`, `TokenResponse`, etc. | `pattern_stack.features.auth.schemas` |
| Auth exceptions | `EmailAlreadyRegisteredError`, etc. | `pattern_stack.features.auth.exceptions` |
| JWT tokens | `create_access_token`, `decode_token` | `pattern_stack.atoms.security` |
| Connection model | `Connection(BasePattern)` | `pattern_stack.atoms.integrations.models` |
| Encryption | `encrypt_config`, `decrypt_config` | `pattern_stack.atoms.integrations.encryption` |

## Test Strategy

### Phase 1 Tests

**File**: `app/backend/__tests__/test_auth_router.py`

1. Register new user -- 201, returns access + refresh tokens
2. Register duplicate email -- 409
3. Register weak password -- 422
4. Login valid credentials -- 200, returns tokens
5. Login wrong password -- 401
6. Login nonexistent email -- 401
7. Refresh with valid token -- 200, returns new access token
8. Refresh with invalid token -- 401
9. GET /me with valid token -- 200, returns UserResponse
10. GET /me without token -- 401
11. GET /me with expired token -- 401

### Phase 2 Tests

**File**: `app/backend/__tests__/test_github_oauth.py`

Unit tests for `GitHubOAuthAPI` (mock httpx):
1. `test_get_authorize_url` -- correct URL with all params
2. `test_exchange_code_success` -- mock token response
3. `test_exchange_code_error` -- handle GitHub error response
4. `test_store_github_connection_creates_new` -- Connection created with encrypted config
5. `test_store_github_connection_updates_existing` -- existing Connection updated, not duplicated
6. `test_get_user_github_token_valid` -- returns decrypted token
7. `test_get_user_github_token_expired_refreshes` -- auto-refresh, returns new token
8. `test_get_user_github_token_no_connection` -- returns None
9. `test_find_or_create_user_new` -- creates user with oauth_accounts
10. `test_find_or_create_user_existing_by_github_id` -- finds and returns existing
11. `test_find_or_create_user_existing_by_email` -- links GitHub to existing account

**File**: `app/backend/__tests__/test_github_oauth_router.py`

API-level tests:
1. GET /auth/github -- returns authorize_url with correct params
2. POST /auth/github/callback valid code -- returns TokenResponse
3. POST /auth/github/callback invalid code -- 400
4. GET /auth/github/status connected -- returns connected=true, github_login
5. GET /auth/github/status not connected -- returns connected=false
6. DELETE /auth/github -- soft-deletes Connection

### Frontend

Manual testing via `/verify` -- screenshot login page, test OAuth popup flow, verify token persistence across reload.

## Dependencies

**No new Python packages required.** Everything comes from:
- `pattern-stack` (installed) -- User, AuthAPI, Connection, encryption, JWT
- `httpx` (installed) -- GitHub API calls
- `cryptography` (transitive via pattern-stack) -- Fernet

**No new frontend packages.** Uses existing `@tanstack/react-query` and fetch-based API client.

The generated `ApiClient` already has `getAuthToken` support -- it just needs wiring.

## Migration Safety

- `users` and `connections` tables are new -- zero risk to existing data
- Existing endpoints remain unauthenticated until Phase 3 adds requirements
- `GITHUB_TOKEN` env var continues working for all existing functionality
- Frontend auth gate can be disabled for dev by always returning a mock user

## Open Questions

1. **CSRF state validation**: The OAuth state parameter needs server-side validation. Recommendation: store state in pattern-stack's cache subsystem with 10-minute TTL, validate on callback.

2. **Existing endpoint auth**: Should Phase 1 require auth on existing endpoints or leave them open? Recommendation: leave open, use `OptionalUser` where useful, enforce auth in Phase 3.

3. **Dev user seeding**: Should seeds create a default development user? Recommendation: yes, add a dev user (`dev@stackbench.dev` / `devpassword`) to the seed system.
