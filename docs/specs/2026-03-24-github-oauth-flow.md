---
title: GitHub App OAuth Flow (PKCE)
date: 2026-03-24
status: draft
branch: dug/infra-setup/2-oauth-flow
depends_on:
  - dug/infra-setup/1-github-app-auth
adrs: []
---

# GitHub App OAuth Flow (PKCE)

## Goal

Implement the OAuth authorization code flow with PKCE so users can connect their GitHub account to Stack Bench. The backend exchanges a temporary authorization code for a user access token, stores the tokens encrypted in the database, and exposes a status endpoint. The frontend provides a "Connect GitHub" button that initiates the flow and a status indicator showing whether GitHub is connected. This does NOT include user auth (login/register) -- the flow operates without a logged-in user (single-tenant MVP), and user association will be wired later.

## Domain Model

| Entity | Pattern | Table | Purpose |
|--------|---------|-------|---------|
| `GitHubConnection` | `BasePattern` | `github_connections` | Stores encrypted GitHub user access tokens, refresh tokens, and GitHub user metadata |

**Why BasePattern (not EventPattern)?** A GitHub connection does not have a meaningful state machine. It is either present (connected) or absent (not connected). Token refresh is a background concern, not a lifecycle transition. BasePattern gives us UUID PK, timestamps, and change tracking, which is sufficient. (Note: soft delete via `deleted_at` is an EventPattern feature, not BasePattern. If soft delete is needed later, the model can be upgraded to EventPattern.)

**Why a new table (not pattern-stack's Connection model)?** The framework's `Connection` model is designed for integration adapter connections (Linear, Jira, etc.) with webhook paths, provider config, and sync records. GitHub OAuth is a fundamentally different concern: it stores per-user access tokens for API calls, not integration adapter credentials. Using `Connection` would require shoehorning fields (webhook_path is meaningless here) and conflate two distinct concepts. A purpose-built `github_connections` table is cleaner.

## GitHub OAuth Flow (Step by Step)

```
Frontend                Backend                 GitHub
   |                       |                       |
   |  1. Click "Connect"   |                       |
   |  generate PKCE pair   |                       |
   |  store code_verifier  |                       |
   |  in sessionStorage    |                       |
   |                       |                       |
   |  2. GET /api/v1/auth/github?code_verifier=... |
   |  ──────────────────>  |                       |
   |                       |  3. Compute S256       |
   |                       |     challenge from     |
   |                       |     verifier           |
   |                       |                       |
   |  4. 302 Redirect      |                       |
   |  <──────────────────  |                       |
   |                       |                       |
   |  5. User authorizes   |                       |
   |  ────────────────────────────────────────────> |
   |                       |                       |
   |  6. Redirect to       |                       |
   |     /api/v1/auth/github/callback?code=...     |
   |  <──────────────────────────────────────────── |
   |                       |                       |
   |  ──────────────────>  |  7. POST              |
   |                       |     github.com/        |
   |                       |     login/oauth/       |
   |                       |     access_token       |
   |                       |     (code + verifier)  |
   |                       |  ──────────────────>   |
   |                       |                       |
   |                       |  8. access_token +     |
   |                       |     refresh_token      |
   |                       |  <──────────────────   |
   |                       |                       |
   |                       |  9. GET /user          |
   |                       |     (fetch github      |
   |                       |      profile)          |
   |                       |  ──────────────────>   |
   |                       |  <──────────────────   |
   |                       |                       |
   |                       | 10. Encrypt tokens     |
   |                       |     Store in DB        |
   |                       |                       |
   | 11. 302 Redirect      |                       |
   |     to frontend       |                       |
   |     /?github=connected|                       |
   |  <──────────────────  |                       |
```

### PKCE Detail

PKCE (Proof Key for Code Exchange, RFC 7636) prevents authorization code interception attacks:

1. **Frontend generates** a random `code_verifier` (43-128 chars, URL-safe) and stores it in `sessionStorage`
2. **Frontend passes** the `code_verifier` to the backend's `/auth/github` endpoint as a query parameter
3. **Backend computes** the `code_challenge` = base64url(SHA-256(code_verifier))
4. **Backend includes** `code_challenge` and `code_challenge_method=S256` in the GitHub authorize URL
5. **Backend stores** the `code_verifier` in a short-lived server-side cache (in-memory dict with TTL, keyed by `state`)
6. **On callback**, backend sends the original `code_verifier` to GitHub's token endpoint
7. **GitHub verifies** SHA-256(code_verifier) matches the original code_challenge

### Token Lifecycle

- **User access token**: 8-hour TTL, used for GitHub API calls
- **Refresh token**: 6-month TTL, used to obtain new access tokens
- Both stored encrypted in `github_connections` table
- Token refresh happens lazily on API call failure (402/401) or proactively via TTL check (future enhancement)

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Feature layer: GitHubConnection model, schemas, service | -- |
| 2 | Settings + encryption key | Phase 1 |
| 3 | Molecule layer: GitHubOAuthAPI | Phase 1, 2 |
| 4 | Organism layer: auth router | Phase 3 |
| 5 | Database migration | Phase 1 |
| 6 | Frontend: Connect button + status | Phase 4 |

## Phase Details

### Phase 1: Feature -- `github_connections`

**Files to create:**

```
app/backend/src/features/github_connections/
  __init__.py
  models.py
  schemas/
    __init__.py
    input.py
    output.py
  service.py
```

**Model: `models.py`**

```python
from datetime import datetime
from pattern_stack.atoms.patterns import BasePattern, Field

class GitHubConnection(BasePattern):
    __tablename__ = "github_connections"

    class Pattern:
        entity = "github_connection"
        reference_prefix = "GHC"
        track_changes = True

    # GitHub user identity
    github_user_id = Field(int, required=True, unique=True, index=True)
    github_login = Field(str, required=True, max_length=255)

    # Encrypted tokens (Fernet-encrypted JSON blob containing
    # access_token, refresh_token, expires_at, refresh_expires_at)
    tokens_encrypted = Field(bytes, required=True)

    # Token metadata (unencrypted for query/monitoring)
    token_expires_at = Field(datetime, nullable=True)
    refresh_token_expires_at = Field(datetime, nullable=True)

    # Future: user_id = Field(UUID, foreign_key="users.id", nullable=True, index=True)
```

Key decisions:
- `github_user_id` is `unique=True` because this is single-tenant MVP (one connection per GitHub user). Multi-user will add a `user_id` FK later.
- Tokens stored as a single encrypted blob rather than separate encrypted columns -- simpler, fewer decryption operations, and the tokens are always used together.
- `token_expires_at` stored unencrypted so we can query for expiring tokens without decrypting.

**Schemas: `input.py`**

```python
class GitHubConnectionCreate(BaseModel):
    github_user_id: int
    github_login: str
    tokens_encrypted: bytes
    token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None

class GitHubConnectionUpdate(BaseModel):
    tokens_encrypted: bytes | None = None
    github_login: str | None = None
    token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None
```

**Schemas: `output.py`**

```python
class GitHubConnectionResponse(BaseModel):
    id: UUID
    github_user_id: int
    github_login: str
    token_expires_at: datetime | None = None
    connected: bool = True  # computed: always True if record exists
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

Note: Response schema intentionally EXCLUDES `tokens_encrypted`. Tokens never leave the backend.

**Service: `service.py`**

```python
class GitHubConnectionService(BaseService[GitHubConnection, GitHubConnectionCreate, GitHubConnectionUpdate]):
    model = GitHubConnection

    async def get_by_github_user_id(self, db: AsyncSession, github_user_id: int) -> GitHubConnection | None:
        """Look up connection by GitHub user ID."""
        ...

    async def upsert(self, db: AsyncSession, data: GitHubConnectionCreate) -> GitHubConnection:
        """Create or update connection (re-authorization replaces tokens)."""
        ...
```

### Phase 2: Settings + Encryption Key

**File to modify: `app/backend/pyproject.toml`**

Add `cryptography` as a direct dependency (it is currently only a transitive dependency and the spec uses `cryptography.fernet.Fernet` directly):
```toml
dependencies = [
    # ... existing deps ...
    "cryptography",
]
```

**File to modify: `app/backend/src/config/settings.py`**

Add:
```python
# Encryption
ENCRYPTION_KEY: str = Field(default="")  # Fernet key for encrypting tokens

# OAuth
GITHUB_OAUTH_REDIRECT_URI: str = Field(default="http://localhost:8500/api/v1/auth/github/callback")
FRONTEND_URL: str = Field(default="http://localhost:3500")
```

**File to modify: `.env.example`**

Add:
```
# Encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=op://DugsApps/Stack Bench/encryption_key

# OAuth
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8500/api/v1/auth/github/callback
FRONTEND_URL=http://localhost:3500
```

### Phase 3: Molecule -- GitHubOAuthAPI

**File to create: `app/backend/src/molecules/apis/github_oauth_api.py`**

This is the business logic layer. It orchestrates the OAuth flow without any HTTP concerns.

```python
class GitHubOAuthAPI:
    """GitHub OAuth business logic.

    Responsibilities:
    - Generate authorization URL with PKCE challenge
    - Exchange authorization code for tokens
    - Encrypt and store tokens
    - Retrieve connection status
    - Refresh expired tokens
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.service = GitHubConnectionService()
        self.settings = get_settings()

    def build_authorize_url(self, code_verifier: str) -> tuple[str, str]:
        """Build GitHub authorization URL with PKCE.

        Returns (authorize_url, state) where state is a random
        CSRF token that must be verified on callback.
        """
        ...

    async def handle_callback(self, code: str, state: str, code_verifier: str) -> GitHubConnectionResponse:
        """Exchange code for tokens, fetch user profile, store connection.

        Steps:
        1. POST to GitHub token endpoint with code + code_verifier
        2. GET /user to fetch github_user_id and github_login
        3. Encrypt tokens
        4. Upsert into github_connections
        """
        ...

    async def get_connection_status(self) -> GitHubConnectionResponse | None:
        """Get current GitHub connection (if any).

        Single-tenant MVP: returns the first (and only) connection.
        Multi-user: will filter by user_id.
        """
        ...

    async def refresh_token_if_needed(self, connection: GitHubConnection) -> GitHubConnection:
        """Refresh the access token if expired or expiring soon."""
        ...
```

**PKCE state storage**: Use an in-memory dict with TTL cleanup. The `state` parameter (random string) maps to the `code_verifier`. Entries expire after 10 minutes. This is acceptable for single-instance MVP. For multi-instance, move to Redis or database.

```python
# Module-level state store (single-process MVP)
_pending_oauth: dict[str, tuple[str, float]] = {}  # state -> (code_verifier, expires_at)
```

**GitHub API calls**: Use `httpx.AsyncClient` for HTTP calls to GitHub (token exchange and user profile fetch). Do NOT use the existing `GITHUB_TOKEN`-based adapter -- that is the app installation token, not the user OAuth token.

### Phase 4: Organism -- Auth Router

**File to create: `app/backend/src/organisms/api/routers/auth.py`**

```python
router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/github")
async def github_auth_redirect(
    code_verifier: str,  # Query parameter from frontend
    db: DatabaseSession,
) -> RedirectResponse:
    """Redirect to GitHub authorization page.

    Frontend generates PKCE code_verifier, passes it here.
    Backend computes challenge and redirects to GitHub.
    """
    ...

@router.get("/github/callback")
async def github_auth_callback(
    code: str,           # Authorization code from GitHub
    state: str,          # CSRF state token
    db: DatabaseSession,
) -> RedirectResponse:
    """Handle GitHub OAuth callback.

    Exchanges code for tokens, stores connection, redirects to frontend.
    On success: redirect to FRONTEND_URL/?github=connected
    On error: redirect to FRONTEND_URL/?github=error&message=...
    """
    ...

@router.get("/github/status")
async def github_connection_status(
    db: DatabaseSession,
) -> dict:
    """Check if GitHub is connected.

    Returns { connected: bool, github_login: str | null, ... }
    """
    ...
```

**File to modify: `app/backend/src/organisms/api/app.py`**

Add the auth router:
```python
from organisms.api.routers.auth import router as auth_router
# ...
app.include_router(auth_router, prefix="/api/v1")
```

**File to modify: `app/backend/src/organisms/api/dependencies.py`**

Add dependency for GitHubOAuthAPI:
```python
def get_github_oauth_api(db: DatabaseSession) -> GitHubOAuthAPI:
    return GitHubOAuthAPI(db)

GitHubOAuthAPIDep = Annotated[GitHubOAuthAPI, Depends(get_github_oauth_api)]
```

### Phase 5: Database Migration

**File to create: `app/backend/alembic/versions/<hash>_add_github_connections.py`**

Generated via `alembic revision --autogenerate -m "add github_connections"` after adding the model.

**File to modify: `app/backend/src/features/__init__.py`**

Add model import for alembic discovery:
```python
from features.github_connections.models import GitHubConnection  # noqa: F401
```

Table schema:

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, server_default gen_random_uuid() |
| github_user_id | Integer | NOT NULL, UNIQUE, INDEX |
| github_login | VARCHAR(255) | NOT NULL |
| tokens_encrypted | LargeBinary | NOT NULL |
| token_expires_at | DateTime(tz) | NULLABLE |
| refresh_token_expires_at | DateTime(tz) | NULLABLE |
| reference_number | VARCHAR(50) | UNIQUE (from BasePattern) |
| created_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |
| updated_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |

### Phase 6: Frontend

**File to create: `app/frontend/src/hooks/useGitHubConnection.ts`**

```typescript
interface GitHubConnectionStatus {
  connected: boolean;
  github_login: string | null;
  loading: boolean;
  error: string | null;
  connect: () => void;  // Initiates OAuth flow
}

export function useGitHubConnection(): GitHubConnectionStatus { ... }
```

The `connect` function:
1. Generates a random `code_verifier` (43-128 URL-safe chars)
2. Stores `code_verifier` in `sessionStorage` (survives redirect)
3. Navigates to `/api/v1/auth/github?code_verifier=<verifier>` (backend handles redirect to GitHub)

On page load, the hook:
1. Checks URL for `?github=connected` or `?github=error` query params
2. Fetches `/api/v1/auth/github/status` to get current connection state
3. Cleans up URL query params after processing

**File to modify: `app/frontend/src/App.tsx`**

Add a connection status indicator and "Connect GitHub" button to the AppShell header area. When disconnected, show a button. When connected, show the GitHub username.

**File to create: `app/frontend/src/components/molecules/GitHubConnect/GitHubConnect.tsx`**

A small component that renders either:
- "Connect GitHub" button (when disconnected)
- "Connected as @username" badge (when connected)

**File to create: `app/frontend/src/components/molecules/GitHubConnect/index.ts`**

Barrel export.

## File Tree Summary

```
# New files
app/backend/src/features/github_connections/__init__.py        # Barrel exports
app/backend/src/features/github_connections/models.py          # GitHubConnection (BasePattern)
app/backend/src/features/github_connections/schemas/__init__.py
app/backend/src/features/github_connections/schemas/input.py   # Create/Update schemas
app/backend/src/features/github_connections/schemas/output.py  # Response schema (no tokens)
app/backend/src/features/github_connections/service.py         # CRUD + upsert + lookup
app/backend/src/molecules/apis/github_oauth_api.py             # OAuth business logic
app/backend/src/organisms/api/routers/auth.py                  # GET /auth/github, callback, status
app/backend/alembic/versions/xxxx_add_github_connections.py    # Migration (autogenerated)
app/backend/__tests__/features/test_github_connections.py      # Model + schema + service tests
app/backend/__tests__/molecules/test_github_oauth_api.py       # OAuth flow tests (mocked HTTP)
app/backend/__tests__/organisms/test_auth_router.py            # Router integration tests
app/frontend/src/hooks/useGitHubConnection.ts                  # Connection status + connect action
app/frontend/src/components/molecules/GitHubConnect/GitHubConnect.tsx
app/frontend/src/components/molecules/GitHubConnect/index.ts

# Modified files
app/backend/pyproject.toml                                     # +cryptography dependency
app/backend/src/config/settings.py                             # +ENCRYPTION_KEY, +GITHUB_OAUTH_REDIRECT_URI, +FRONTEND_URL
app/backend/src/features/__init__.py                           # +GitHubConnection import
app/backend/src/organisms/api/app.py                           # +auth_router
app/backend/src/organisms/api/dependencies.py                  # +GitHubOAuthAPIDep
app/frontend/src/App.tsx                                       # +GitHubConnect component
.env.example                                                   # +ENCRYPTION_KEY, +GITHUB_OAUTH_REDIRECT_URI, +FRONTEND_URL
```

## Key Design Decisions

1. **BasePattern over EventPattern**: No state machine needed. A connection exists or it doesn't. Token refresh is operational, not a domain state transition.

2. **Custom table over framework Connection**: The Connection model is purpose-built for integration adapters with webhook paths, provider config, and sync records. GitHub OAuth tokens are a different domain concept.

3. **Single encrypted blob for tokens**: `tokens_encrypted` contains `{access_token, refresh_token, expires_at, refresh_token_expires_at}` as one Fernet-encrypted JSON blob. Simpler than two separate encrypted columns, and the tokens are always read/written together.

4. **PKCE verifier passed from frontend**: The frontend generates the `code_verifier` because it is the party that needs to prove the authorization request originated from it. The backend computes the S256 challenge and stores the verifier temporarily (keyed by the random `state` parameter) for retrieval during callback.

5. **In-memory state store for PKCE**: A simple dict with TTL is sufficient for single-process MVP. The `state` parameter maps to `code_verifier`. This avoids adding Redis as a dependency for this feature alone.

6. **Redirect-based callback (not SPA)**: The callback is a server-side redirect flow. After token exchange, the backend redirects to the frontend with a query parameter indicating success/failure. This is the standard OAuth pattern and avoids CORS complexity.

7. **httpx for GitHub API calls**: Use `httpx.AsyncClient` rather than the existing GitHub adapter (which uses app installation tokens). User OAuth tokens are a separate concern.

8. **No user association yet**: The `GitHubConnection` model has no `user_id` FK. In the single-tenant MVP, there is at most one connection. Multi-user support will add `user_id` later.

## Testing Strategy

### Unit Tests (`@pytest.mark.unit`)

**`test_github_connections.py`** (feature layer):
- Model field presence and types
- Pattern config (entity name, reference prefix)
- Create schema validation (required fields, types)
- Update schema allows partial updates
- Response schema excludes tokens_encrypted
- Service model binding

**`test_github_oauth_api.py`** (molecule layer):
- `build_authorize_url` generates correct URL with PKCE challenge
- `build_authorize_url` returns unique state per call
- PKCE S256 challenge computation is correct (test vector from RFC 7636)
- `handle_callback` calls GitHub token endpoint with correct params
- `handle_callback` calls GitHub user endpoint to fetch profile
- `handle_callback` encrypts tokens before storage
- `handle_callback` upserts (re-auth overwrites existing connection)
- `get_connection_status` returns None when no connection
- `get_connection_status` returns response when connected
- State store cleanup removes expired entries

Mock `httpx.AsyncClient` for all external HTTP calls.

### Integration Tests (`@pytest.mark.integration`)

**`test_auth_router.py`** (organism layer):
- `GET /auth/github?code_verifier=...` returns 302 redirect to github.com
- Redirect URL contains correct client_id, redirect_uri, code_challenge, code_challenge_method=S256
- `GET /auth/github/callback` with valid code exchanges tokens (mocked)
- `GET /auth/github/callback` with invalid state returns error redirect
- `GET /auth/github/status` returns `{connected: false}` when no connection
- `GET /auth/github/status` returns connection info when connected

## Open Questions

1. **Encryption key provisioning**: Should we generate the Fernet key on first run and store it, or require it in the environment? Current plan: require it in `.env` (1Password reference). This ensures it survives container restarts.

2. **Token refresh strategy**: Lazy (refresh on 401) vs proactive (background job). Current plan: lazy refresh in the molecule layer when getting tokens. A background job can be added later using the Jobs subsystem.

3. **Multi-instance state store**: The in-memory PKCE state store doesn't work with multiple backend instances. For MVP (single instance), this is fine. For production, move to Redis or a short-lived database row.
