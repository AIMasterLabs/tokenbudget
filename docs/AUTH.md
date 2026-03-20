# TokenBudget — Authentication & Access Control

TokenBudget is completely free and open source. Authentication is used to
identify users, scope data by project, and control access — not for billing.

---

## Auth Modes

Set `AUTH_MODE` in your `.env` file to choose how users log in:

```env
AUTH_MODE=local    # default
```

| Mode | How Users Log In | Best For |
|------|-----------------|----------|
| `local` | Email + password, JWT tokens | Teams, self-hosted deployments |
| `clerk` | Google OAuth, magic link via Clerk | SaaS / hosted deployment |
| `none` | No login, auto-provisions API key | Single user, personal, development |

The frontend automatically adapts — it checks `GET /api/auth/config` on load to determine which auth flow to show.

---

## Local Auth (default)

### First-time setup

1. Start the app and go to `/register`
2. Create your account (email + password)
3. **The first user registered automatically becomes admin**
4. Admin can add more users at Dashboard > Users

### How it works

1. User submits email + password to `POST /api/auth/register` or `POST /api/auth/login`
2. Server verifies credentials, returns a JWT token (30-day expiry)
3. Frontend stores JWT as `tb_token` in localStorage
4. All API calls include `Authorization: Bearer <jwt>`
5. Server decodes JWT, loads user, checks role and project access

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | None | Create account `{ email, password, name }` |
| `/api/auth/login` | POST | None | Login `{ email, password }` → `{ token, user }` |
| `/api/auth/me` | GET | JWT | Get current user info |
| `/api/auth/change-password` | POST | JWT | Change password `{ old_password, new_password }` |
| `/api/auth/config` | GET | None | Returns `{ auth_mode, clerk_publishable_key }` |

### JWT token format

```json
{
  "sub": "user-uuid",
  "role": "admin",
  "iat": 1234567890,
  "exp": 1237159890,
  "iss": "tokenbudget"
}
```

Signed with `SECRET_KEY` from your `.env`. Use a strong random key in production.

---

## User Roles

| Role | Dashboard | Create Events | Create Projects | Manage Users | See All Projects |
|------|-----------|--------------|----------------|-------------|-----------------|
| Admin | Full access | Yes | Yes | Yes | Yes |
| Member | Assigned projects only | Yes | No | No | No |
| Viewer | Assigned projects only (read-only) | No | No | No | No |

### How project access works

- **Admins** see all projects and all data across the organization
- **Members** only see projects they've been added to by an admin
- **Viewers** can read dashboards for assigned projects but can't create events or modify anything

This keeps costs private between departments. A marketing team can't see R&D's AI spend on a confidential project.

### Admin panel

Admins manage users at `/dashboard/admin/users`:
- Add new users (email, password, name, role, department)
- Deactivate users
- View all users and their roles

### Project membership

Admins assign users to projects in the Project Detail page:
- Add members with a role (member or viewer)
- Remove members
- Each project can have different members

---

## API Key Auth (for SDK and proxy)

Used by the Python SDK, JavaScript SDK, proxy, and any programmatic integration.
API keys work independently of the dashboard auth mode.

| Detail | Value |
|--------|-------|
| Header | `Authorization: Bearer tb_ak_<key>` |
| Key prefix | `tb_ak_` |
| Implementation | `api/app/middleware/api_key_auth.py` |

### Create an API key

**Via dashboard:** Go to Dashboard > API Keys > Create Key

**Via API:**
```bash
curl -X POST http://localhost:2727/api/keys \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'
```

**Via setup endpoint (no auth, for bootstrapping):**
```bash
curl -X POST http://localhost:2727/api/setup \
  -H "Content-Type: application/json" \
  -d '{"name": "default"}'
```

### How API key auth works

1. Client sends `Authorization: Bearer tb_ak_<raw-key>`
2. Server hashes the key (SHA-256) and looks it up in the `api_keys` table
3. Returns `(ApiKey, User)` on success, raises `401` on failure
4. `last_used_at` is updated on each use

---

## Clerk Auth (optional)

For SaaS deployments where you want Google OAuth and magic link email login.

### Setup

1. Create account at https://clerk.com
2. Create application, enable Google + Email sign-in
3. Set in `.env`:

```env
AUTH_MODE=clerk
CLERK_SECRET_KEY=sk_live_YOUR_KEY
CLERK_PUBLISHABLE_KEY=pk_live_YOUR_KEY
```

4. Set in `frontend/.env.local`:

```env
VITE_CLERK_PUBLISHABLE_KEY=pk_live_YOUR_KEY
```

### How it works

- Frontend wraps app with `<ClerkProvider>`
- Login page shows Google OAuth + magic link options
- Clerk JWT is verified server-side via JWKS endpoint
- Users are auto-provisioned in the local DB on first login

---

## No Auth Mode

For single-user personal deployments or development.

```env
AUTH_MODE=none
```

- No login page shown
- API key auto-provisioned on first dashboard visit
- All data accessible without authentication
- Good for local development and personal tracking

---

## Multi-auth middleware

The `require_clerk_or_api_key` dependency accepts all auth methods:

```python
from app.middleware.clerk_auth import require_clerk_or_api_key

@router.get("/endpoint")
async def my_route(auth=Depends(require_clerk_or_api_key)):
    api_key_or_none, user = auth
    # user is always a User object regardless of auth method
```

Auth resolution order:
1. `tb_ak_` prefix → API key auth
2. Valid local JWT → local auth
3. Valid Clerk JWT → Clerk auth (when configured)
4. None matched → `401 Unauthorized`

---

## Security notes

- Passwords hashed with bcrypt
- JWT signed with HMAC-SHA256 using `SECRET_KEY`
- Use a strong random `SECRET_KEY` in production (32+ characters)
- API keys hashed with SHA-256 (never stored in plain text)
- JWKS cache for Clerk has 1-hour TTL with auto-refresh on key rotation
- CORS origins configurable via `CORS_ORIGINS` env var
