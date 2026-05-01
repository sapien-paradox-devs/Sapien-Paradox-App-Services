# Domain: auth

**Status:** drafting

## Components in this domain

- `login-screen.md` — `/login` page (email + password sign-in)
- `signup-form.md` — extended landing SignUp dialog (creates a real `User` on submit)
- `user-model.md` — Django `User` model (email, password, role, etc.)
- `endpoints.md` — `POST /api/auth/{signup,login,logout}`

## Locked decisions (domain-level)

1. **Email + password ("basic auth").** No magic links, OAuth, 2FA, or email verification gating in this scope. Strict-auth concerns (rules, lockouts, verification) deferred.
2. **Real, not mock.** The current `AppShell.tsx` + `LoginPage.tsx` + `components/app/user/*` + `machines/app/` are mocks. They are superseded by this domain's real implementation. Disposition (delete vs preserve as design reference) is captured per-component.
3. **Tokens (`TemporalGrant`) remain self-authenticating** for the email-link Reading Room. Auth adds account-based access on top of tokens; it does not replace tokens for the email-link flow.

## Open questions (domain-level)

1. **Form-to-User integration.** Does the landing SignUp dialog create a User directly (single step, password field added) or does Lead persist as a separate intake stage? See `signup-form.md` and `user-model.md`.
2. **Session mechanism.** Django session cookies (default), or token-based (JWT)? Affects frontend handling. See `endpoints.md`.
3. **Where do successful sign-in / sign-up land?** Profile? Last-attempted page? See `login-screen.md` and `signup-form.md`.
4. **Existing Lead model fate.** Drop, migrate to User, or coexist? See `user-model.md`.

## Cross-domain dependencies

- **`subscription/`** — signup likely creates a Subscription (links User → Book at chosen pace). Coordinated via `integrations/signup-to-first-read.md` (to be drafted when `subscription/` is in scope).
- **`reading-room/`** — Sanctuary's "renew" CTA may require sign-in for non-token-bearing users. Coordinated when Sanctuary is specced.
- **`profile/`** — sign-in lands on `/profile`. Profile content is its own domain.
