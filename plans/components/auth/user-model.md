# User model

**Domain:** auth
**Type:** Django model (backend)
**Status:** drafting

## Purpose

The persisted record of an authenticated person. Replaces the role of `Lead` for accounts.

## Current state

- No `User` model exists.
- `core/models.py` has `Lead` (full_name, email, book_id, book_title, pace, notes, created_at). Created on landing form submit.
- Django's built-in `auth.User` is not customized; `AUTH_USER_MODEL` defaults.

## Future plan

- Use Django's `AbstractUser` as the base for a custom `core.User` model.
- Set `AUTH_USER_MODEL = "core.User"` in `sapien_backend/settings.py` BEFORE the first migration touches User.
- Fields:
  - `email` — unique; used as username (`USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`).
  - `full_name` — CharField, max 255.
  - `role` — CharField with choices `("reader", "admin")`, default `"reader"`.
  - `password` — Django default (PBKDF2 hash).
  - `is_staff`, `is_active`, `is_superuser` — Django built-ins.
  - `created_at` — DateTimeField, `auto_now_add=True`.
  - **Temporary inline fields** (until `subscription/` domain ships): `book_id` (CharField), `pace` (CharField with `crawl/steady/soar` choices). Migrated out into Subscription when that domain is in scope.
- Migration:
  - Drop `Lead` model (no production data; dev environment only).
  - Create initial migration with the new User model.
- Admin: register `User` in Django admin with the standard `UserAdmin` config (or a thin custom subclass to surface `role`, `book_id`, `pace`).
- `objects = CustomUserManager()` to handle email-as-username (Django needs `create_user`/`create_superuser` adjusted).

## Dependencies

- Needs: nothing.
- Used by: `endpoints.md` (signup, login), eventually `subscription/model.md` (FK to User), `grants/model.md` (FK to User).

## Open questions

1. **Drop `Lead` entirely or merge into User?** Recommendation: **drop**. No production data; dev `Lead` rows are non-critical. Simpler migration, no dual lifecycle.
2. **Inline `book_id`/`pace` on User vs deferred to Subscription?** Recommendation: **(a) inline temporarily**, migrated out when `subscription/` ships. Documented as known temporary shape. The alternative (build Subscription in this slice) couples two domains and slows auth delivery.
3. **`AbstractUser` vs `AbstractBaseUser`?** Recommendation: **`AbstractUser`**. Free groups/permissions; useful when admin distinction grows.
4. **Manager-method patterns** — `create_user(email, password, ...)` and `create_superuser(...)`. Standard Django override.

## Notes for designer / implementer

- Customizing User AFTER initial migrations is painful. Doing it now (no production migrations applied) is the right time.
- Set `AUTH_USER_MODEL` in `settings.py` before running `makemigrations`.
- Password storage uses Django default hasher — adequate for this scope.
