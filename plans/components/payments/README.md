# Payments domain

**Status:** drafting

## Purpose

Monetization layer. A Visitor pays before becoming a Reader. Payment success is what creates the `User` row.

## Locked decisions

1. **One-time per-book purchase** (not recurring). Each successful payment grants permanent access to one book + chosen pace. Recurring catalog-access subscription is **deferred but designed-for** — book-access checks go through a service function (`user_has_access_to(user, book)`) so a future `Subscription` mechanism can be added additively, without rewiring callers.
2. **Payment processor: Stripe.**
3. **Signup is payment-gated.** No `User` row is created until payment clears. Flow: landing form → Stripe checkout → webhook → `User` + `Order` created together. The signup endpoint shape and `auth/user-model.md` change accordingly (book_id/pace move from inline-on-User → fields on `Order`).

## Open questions

1. **Stripe Checkout (hosted page) vs Stripe Elements (embedded)?** Recommendation: **Checkout** — no card UI to design or maintain, no new canonical screen needed (just a redirect), Stripe handles 3DS / Apple Pay / Google Pay / error states. Cost: visual-continuity break on the Stripe-hosted page (mitigated by branded Checkout settings). Resolved in `stripe-integration.md` once confirmed.
2. **Where does form data live during the Stripe redirect?** Options: (a) `PendingSignup` DB row keyed by Stripe checkout-session ID; (b) Stripe `metadata` field on the checkout session. Recommendation: **(b)** — no extra table, no abandoned-row cleanup. Stripe metadata limits (50 keys, 500 chars/value) comfortably hold `email/full_name/book_id/pace/notes`.
3. **Pricing — flat per-book or variable?** Recommendation: **flat for now**, configurable later via a `Book` model field. Defer the `Book` domain until that decision matters.
4. **Refunds?** Recommendation: defer — manual via Stripe dashboard for the launch slice. No in-app refund flow.
5. **Test vs live keys?** Recommendation: standard env-var split — `STRIPE_API_KEY` from settings; dev uses test keys, prod uses live keys. Defer config detail to ticket.

## Files (populated lazily as grilling descends)

- `order-model.md` — `Order` Django model (FK to User, FK to book, pace, stripe_session_id, amount, created_at).
- `stripe-integration.md` — Stripe Checkout + webhook plumbing.
- `endpoints.md` — `POST /api/payments/create-checkout-session`, webhook handler.

## Dependencies

- Needs: `auth/user-model.md` (Order FKs to User on creation), `auth/endpoints.md` (signup endpoint shape changes — replaced by create-checkout-session + webhook).
- Used by: `reading-room/` (access check on token landing), future `subscription/` (additive access mechanism).

## Notes for designer / implementer

- The "we plan → designer designs → we implement" workflow applies. If we pick Stripe Checkout (Q1 recommendation), there is no in-app payment UI to design — only the post-success / post-failure landing pages.
- Stripe Checkout success URL → `/profile?welcome=1` (recommended). Cancel URL → `/?book_id=<slug>` (back to landing pre-filled).
