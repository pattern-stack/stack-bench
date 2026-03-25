---
title: User Auth & Registration
date: 2026-03-24
status: draft
branch: dugshub/sb-062-st-push/1-st-push-backend-changes
depends_on: []
adrs: []
---

# User Auth & Registration

## Goal

Wire pattern-stack's built-in authentication stack (User model, AuthAPI, auth router) into Stack Bench so users can register, login, and access protected routes. The backend work is pure integration -- no new models, services, or auth logic. The frontend gets custom-designed login/register pages, an auth context provider, and protected routing.

## Domain Model

No new models. We use pattern-stack's existing `User` (ActorPattern) from `pattern_stack.features.users.models`. The table name is `users`. All auth schemas, services, and business logic come from the framework.

**Pattern-stack components consumed (do NOT rewrite):**

| Component | Import Path | Layer |
|-----------|-------------|-------|
| User model | `pattern_stack.features.users.models.User` | Feature |
| UserService | `pattern_stack.features.users.service.UserService` | Feature |
| UserCreate, UserUpdate | `pattern_stack.features.users.schemas` | Feature |
| UserResponse | `pattern_stack.features.users.schemas.UserResponse` | Feature |
| LoginRequest, RegisterRequest, RefreshRequest | `pattern_stack.features.auth.schemas` | Feature |
| TokenResponse, AuthResult, RefreshResult | `pattern_stack.features.auth.schemas` | Feature |
| AuthAPI | `pattern_stack.molecules.apis.auth.AuthAPI` | Molecule |
| create_auth_router | `pattern_stack.organisms.api.auth_router.create_auth_router` | Organism |
| create_access_token, decode_token, verify_password, get_password_hash | `pattern_stack.atoms.security` | Atom |

## Implementation Phases

| Phase | What | Depends On |
|-------|------|------------|
| 1 | Backend: settings, migration, auth router wiring, CORS | -- |
| 2 | Frontend: routing, auth context, login/register pages, protected routes | Phase 1 |
| 3 | Integration testing | Phase 1 + 2 |

## Phase Details

### Phase 1: Backend Wiring

All backend changes are integration/configuration -- zero new business logic.

#### 1a. Add `redis` dependency

**File:** `app/backend/pyproject.toml`

Add `redis` to the dependencies list. Pattern-stack's `atoms.security.utils` imports `redis` at module level, so the entire auth import chain (`create_auth_router`, `AuthAPI`) fails with `ModuleNotFoundError` without it.

Then run `uv sync` from `app/backend/`.

#### 1b. Confirm JWT_SECRET_KEY is inherited (no code change needed)

`AppSettings` extends `pattern_stack.atoms.config.settings.Settings` which already defines `JWT_SECRET_KEY` (with a random default_factory), `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_MINUTES`, `PASSWORD_MIN_LENGTH`, etc. with sensible defaults. No field additions needed in `AppSettings`.

For production, set `JWT_SECRET_KEY` in the `.env` file. The inherited `default_factory` generates a random key for development so the app starts without configuration.

#### 1b-env. Update .env.example

**File:** `app/backend/.env.example`

Add these lines:

```
# Auth (inherited from pattern-stack BaseSettings — override as needed)
JWT_SECRET_KEY=change-me-in-production
CORS_ALLOW_ORIGINS=http://localhost:3500
```

#### 1c. Register User model for Alembic discovery

**File:** `app/backend/src/features/__init__.py`

Add one import at the end of the model registry:

```python
from pattern_stack.features.users.models import User  # noqa: F401
```

This registers the `users` table with SQLAlchemy's metadata so Alembic can detect it during `autogenerate`.

#### 1d. Generate Alembic migration

**Command:** `cd app/backend && just migrate` (or `alembic revision --autogenerate -m "add users table"`)

This will generate the migration for the `users` table. The User model (ActorPattern) creates columns: `id` (UUID PK), `reference_number`, `display_name`, `actor_type`, `email`, `phone`, `first_name`, `last_name`, `password_hash`, `is_active`, `oauth_accounts`, `activity_count`, `last_activity_at`, `created_at`, `updated_at`, `deleted_at`, plus ActorPattern's standard columns.

Review the generated migration to confirm it only adds the `users` table and does not alter existing tables.

#### 1e. Wire auth router into create_app

**File:** `app/backend/src/organisms/api/app.py`

Import `create_auth_router` and the existing `get_db` dependency, then include the auth router:

```python
from pattern_stack.organisms.api.auth_router import create_auth_router
from organisms.api.dependencies import get_db

def create_app() -> FastAPI:
    # ... existing setup ...

    # Auth router (pattern-stack built-in)
    auth_router = create_auth_router(
        get_session=get_db,
        prefix="/api/v1/auth",
    )
    app.include_router(auth_router)

    # ... existing routers, error handlers ...
```

**Key detail:** The `get_db` dependency in `dependencies.py` uses `request.app.state.session_factory` which is set during `lifespan`. The `create_auth_router` function accepts any async generator yielding `AsyncSession`, so the existing `get_db` works as-is. No adapter needed.

**Endpoints created:**
- `POST /api/v1/auth/login` -- email + password, returns `TokenResponse`
- `POST /api/v1/auth/register` -- first_name, last_name, email, password, returns `TokenResponse`
- `POST /api/v1/auth/refresh` -- refresh_token, returns `RefreshResult`
- `GET /api/v1/auth/me` -- Bearer token required, returns `UserResponse`

#### 1f. Add get_current_user dependency

**File:** `app/backend/src/organisms/api/dependencies.py`

Add a reusable FastAPI dependency for protecting future routes:

```python
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pattern_stack.molecules.apis.auth import AuthAPI

bearer_scheme = HTTPBearer()
_auth_api = AuthAPI()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DatabaseSession,
) -> "User":
    """Get current authenticated user from Bearer token.

    Use as a dependency on any route that requires authentication.
    Raises 401 if token is invalid or user not found.
    """
    from pattern_stack.features.users.models import User

    user = await _auth_api.get_current_user(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

CurrentUser = Annotated["User", Depends(get_current_user)]
```

This dependency is not used by any route yet but provides the `CurrentUser` type alias for future route protection.

#### 1g. Add CORS middleware

**File:** `app/backend/src/organisms/api/app.py`

The app currently has no CORS middleware. Add it in `create_app()`:

```python
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(...)

    # CORS — allow frontend origin with credentials for auth cookies/headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_allow_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ... rest of setup ...
```

The `get_cors_allow_origins()` method is inherited from `BaseSettings` and parses the `CORS_ALLOW_ORIGINS` env var (defaults to `http://localhost:3000`). For Stack Bench, set `CORS_ALLOW_ORIGINS=http://localhost:3500` in `.env` to match the Vite dev server port.

Note: In development, the Vite proxy at `localhost:3500` forwards `/api` requests to the backend, so CORS is not strictly needed for proxied requests. However, CORS is required for production builds and for any direct frontend-to-backend requests.

#### 1h. Update Vite proxy for auth routes

**File:** `app/frontend/vite.config.ts`

The existing proxy configuration already proxies `/api` to the backend. Since we use `prefix="/api/v1/auth"`, auth routes are already covered by the existing proxy rule:

```typescript
proxy: {
  "/api": {
    target: process.env.VITE_API_BASE_URL || "http://localhost:8500",
    changeOrigin: true,
  },
},
```

No changes needed to vite.config.ts.

### Phase 2: Frontend Auth

#### 2a. Install react-router-dom

**Command:** `cd app/frontend && npm install react-router-dom`

#### 2b. Create auth types

**File:** `app/frontend/src/types/auth.ts`

Define TypeScript types matching the backend schemas:

```typescript
export interface UserInfo {
  id: string;
  reference_number: string;
  first_name: string;
  last_name: string;
  display_name: string;
  email: string;
  full_name: string;
}

export interface TokenResponse {
  user: UserInfo;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshResult {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}
```

#### 2c. Create auth context and provider

**File:** `app/frontend/src/contexts/AuthContext.tsx`

Provides authentication state to the entire app:

- Stores `access_token` and `refresh_token` in `localStorage`
- Exposes `user`, `login()`, `register()`, `logout()`, `isAuthenticated`
- On mount, checks for stored tokens and calls `GET /api/v1/auth/me` to validate
- On 401 response, attempts token refresh via `POST /api/v1/auth/refresh`
- On refresh failure, clears tokens and redirects to login
- Uses `React.createContext` + `useContext` hook pattern

Key implementation details:
- `login(email, password)` calls `POST /api/v1/auth/login`, stores tokens, sets user
- `register(first_name, last_name, email, password)` calls `POST /api/v1/auth/register`, stores tokens, sets user
- `logout()` clears localStorage tokens and user state
- Export a `useAuth()` hook for consuming components

#### 2d. Wire auth token into API client

**File:** `app/frontend/src/main.tsx`

Update the `setApiConfig` call to read the access token from localStorage:

```typescript
setApiConfig({
  baseUrl: window.location.origin,
  getAuthToken: () => localStorage.getItem("access_token"),
});
```

The existing `ApiClient` already supports `getAuthToken` and sets the `Authorization: Bearer <token>` header when a token is present. No changes to `client.ts` needed.

#### 2e. Create login page

**File:** `app/frontend/src/pages/LoginPage.tsx`

Custom-designed login page:
- Email and password fields
- Submit button
- Link to register page
- Error display for invalid credentials (401)
- Redirects to app on successful login
- Uses the `useAuth()` hook for `login()`
- Minimal, clean design matching Stack Bench's existing dark theme

#### 2f. Create register page

**File:** `app/frontend/src/pages/RegisterPage.tsx`

Custom-designed registration page:
- First name, last name, email, password fields
- Submit button
- Link to login page
- Error display for validation errors (400) and email conflicts (409)
- Redirects to app on successful registration
- Uses the `useAuth()` hook for `register()`
- Matching design with login page

#### 2g. Create ProtectedRoute wrapper

**File:** `app/frontend/src/components/ProtectedRoute.tsx`

A route wrapper that checks authentication:

```typescript
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <LoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
```

#### 2h. Add routing to the app

**File:** `app/frontend/src/main.tsx`

Wrap the app with `BrowserRouter` and `AuthProvider`:

```typescript
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <AppRouter />
        </QueryClientProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
```

**File:** `app/frontend/src/AppRouter.tsx`

Top-level router component:

```typescript
import { Routes, Route, Navigate } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { App } from "./App";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <App />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

The existing `App` component remains unchanged -- it just becomes the protected content.

### Phase 3: Integration Testing

#### 3a. Backend auth endpoint tests

**File:** `app/backend/__tests__/test_auth_endpoints.py`

Test the wired auth endpoints against the real Stack Bench app:
- `POST /api/v1/auth/register` -- creates user, returns tokens
- `POST /api/v1/auth/login` -- authenticates, returns tokens
- `POST /api/v1/auth/login` with wrong password -- returns 401
- `POST /api/v1/auth/refresh` -- refreshes access token
- `GET /api/v1/auth/me` -- returns user profile with valid token
- `GET /api/v1/auth/me` without token -- returns 401
- `POST /api/v1/auth/register` with duplicate email -- returns 409

Use `httpx.AsyncClient` with the FastAPI test client pattern. The tests exercise the full Stack Bench app (not pattern-stack in isolation).

## File Tree

```
app/backend/
  pyproject.toml                           # MODIFY: add redis dependency
  .env.example                             # MODIFY: add JWT_SECRET_KEY, CORS_ALLOW_ORIGINS
  src/
    features/
      __init__.py                          # MODIFY: add User model import for alembic
    organisms/api/
      app.py                               # MODIFY: wire auth_router + CORS middleware
      dependencies.py                      # MODIFY: add get_current_user + CurrentUser
  alembic/versions/
    xxxx_add_users_table.py                # CREATE: auto-generated migration
  __tests__/
    test_auth_endpoints.py                 # CREATE: integration tests

app/frontend/
  src/
    types/
      auth.ts                              # CREATE: auth TypeScript types
    contexts/
      AuthContext.tsx                       # CREATE: auth provider + useAuth hook
    pages/
      LoginPage.tsx                        # CREATE: login page
      RegisterPage.tsx                     # CREATE: register page
    components/
      ProtectedRoute.tsx                   # CREATE: auth gate wrapper
    AppRouter.tsx                          # CREATE: route definitions
    main.tsx                               # MODIFY: add BrowserRouter, AuthProvider, getAuthToken
    App.tsx                                # NO CHANGE (becomes child of ProtectedRoute)
  package.json                             # MODIFY: add react-router-dom dependency
```

## Implementation Order

1. Add `redis` to `pyproject.toml` and run `uv sync` (BLOCKER: auth imports fail without it)
2. Update `.env.example` with `JWT_SECRET_KEY` and `CORS_ALLOW_ORIGINS`
3. `features/__init__.py` -- add `User` model import for Alembic
4. Run `alembic revision --autogenerate -m "add users table"` then `alembic upgrade head`
5. `app.py` -- add CORS middleware + auth router wiring (depends on steps 1-4)
6. `dependencies.py` -- add `get_current_user` / `CurrentUser` (depends on step 5)
7. `test_auth_endpoints.py` -- verify backend works (depends on step 5)
8. `npm install react-router-dom` in frontend
9. `types/auth.ts` -- TypeScript types (no dependencies)
10. `contexts/AuthContext.tsx` -- auth provider (depends on step 9)
11. `main.tsx` -- wire providers + getAuthToken (depends on step 10)
12. `pages/LoginPage.tsx` + `pages/RegisterPage.tsx` (depends on step 10)
13. `components/ProtectedRoute.tsx` (depends on step 10)
14. `AppRouter.tsx` -- route definitions (depends on steps 12-13)

## Key Design Decisions

**Why not switch to pattern-stack's app factory?**
Stack Bench has a custom `create_app()` with its own lifespan management, error handlers, and router registration. Switching to the framework's factory would require reworking all of this. Instead, we import `create_auth_router` and `include_router` it -- the router is designed for exactly this use case.

**Why prefix="/api/v1/auth" instead of "/auth"?**
All existing Stack Bench routes use the `/api/v1` prefix. Keeping auth routes consistent means the Vite proxy rule (`/api` -> backend) works without modification and the URL structure is uniform.

**Why localStorage for tokens instead of httpOnly cookies?**
The existing `ApiClient` is already built around `getAuthToken()` returning a string for the `Authorization` header. localStorage is the natural fit. httpOnly cookies would require backend changes (Set-Cookie headers, CSRF protection) and a different client architecture. For a developer workbench (not a public-facing app), localStorage with short-lived access tokens and refresh rotation is appropriate.

**Why a separate AppRouter.tsx?**
Keeps routing concerns separate from the main App component. The existing `App.tsx` is large (250 lines) and handles the full workbench UI. Making it a child of `ProtectedRoute` means zero changes to that file.

**Password requirements from BaseSettings defaults:**
- Min length: 8 characters
- Requires: uppercase, lowercase, digits, symbols
- Bcrypt rounds: 12

These can be relaxed for development by setting env vars (e.g., `PASSWORD_REQUIRE_SYMBOLS=false`).

## Testing Strategy

**Backend tests** (`test_auth_endpoints.py`):
- Use `httpx.AsyncClient` with `app=create_app()` and `base_url="http://test"`
- Each test gets a fresh database transaction (rolled back after test)
- Test the happy path for each endpoint plus key error cases
- Marker: `@pytest.mark.asyncio`

**Frontend tests** (deferred):
- Auth context unit tests with mocked API calls
- Login/register page component tests
- ProtectedRoute redirect behavior
- These can be added in a follow-up once the frontend testing framework is established

## Open Questions

1. **Seed user for development?** Should we add a seed user (e.g., `dev@stackbench.dev` / `password`) to the database seeds so developers can log in immediately after setup? Likely yes -- add to `app/backend/src/seeds/`.

2. **Token refresh on 401?** The auth context should intercept 401 responses from any API call and attempt a token refresh before failing. This requires either an axios-style interceptor or wrapping the apiClient. Decide during implementation whether to add this now or defer.

3. **Logout endpoint?** Pattern-stack's auth router does not include a logout endpoint (JWT tokens are stateless). Client-side logout (clearing localStorage) is sufficient. Server-side token blacklisting can be added later if needed.
