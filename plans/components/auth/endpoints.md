# Auth endpoints

**Domain:** auth
**Type:** Django Ninja API endpoints (backend)
**Status:** drafting

## Purpose

HTTP surface for sign-up, sign-in, sign-out. Three endpoints under `/api/auth/`.

## Current state

- `core/api.py` has `POST /api/leads/` (creates a `Lead`; no auth).
- No `/api/auth/*` endpoints.

## Future plan

### `POST /api/auth/signup`

- Request body: `{email, password, full_name, book_id, pace, notes?}`.
- Behavior:
  - Validate input. Reject if email already used.
  - Create `User` row (with password hashed via Django manager).
  - **(Future, when `subscription/` ships)** create Subscription row, first TemporalGrant, trigger welcome email + first chapter email. Coordinated in `integrations/signup-to-first-read.md`.
  - For the auth-only slice: store `book_id`/`pace`/`notes` inline on User (per `user-model.md`); no Subscription, no email.
  - Establish session (Django session cookie set on response).
  - Return 201 with `{user: {id, email, full_name, role}}`.
- Errors: 409 (email exists), 400 (validation), 5xx (server).

### `POST /api/auth/login`

- Request body: `{email, password}`.
- Behavior:
  - Authenticate user via `django.contrib.auth.authenticate(...)`.
  - Success → establish session; return 200 with `{user: {id, email, full_name, role}}`.
  - Failure → return 401 with `{detail: "invalid credentials"}` (generic, no email-enumeration leak).
- Errors: 401 (invalid creds), 400 (validation).

### `POST /api/auth/logout`

- Empty body.
- Behavior: clear session via `django.contrib.auth.logout(request)`.
- Returns 204.

## Dependencies

- Needs: `user-model.md` (User must exist).
- Used by: `signup-form.md`, `login-screen.md`, `profile/` (sign-out button).

## Open questions

1. **Session vs token (JWT)?** Recommendation: **Django session cookies**. Simplest; works with Ninja; no separate token storage. Frontend uses `credentials: "include"` on fetch. CORS is already configured for the dev origin in `sapien_backend/settings.py`.
2. **CSRF protection?** Recommendation: **yes** — Django CSRF middleware applies; frontend sends `X-CSRFToken` header on auth-mutating endpoints. Defer config detail to ticket.
3. **Email-enumeration prevention on login error?** Recommendation: **yes** — generic "invalid credentials" rather than "no such user" / "wrong password." Cheap, harmless.
4. **Rate limiting?** Recommendation: **not in this slice.** Defer to strict-auth.

## Notes for designer / implementer

- Endpoints in `core/api.py` (or extracted to `core/api/auth.py` if `api.py` outgrows readability).
- Pydantic schemas in `core/schemas.py` (split from `api.py` per archived plan's clean-up).
- Tests: happy + sad path per endpoint, using Ninja's test client.
