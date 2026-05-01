# Sapien Paradox — Development Plan (Root)

> **Audience:** Engineering leads + project owner. This is the planning meta-document. Detailed UI and backend specs live in `/plans/FRONTEND_PLAN.md` and `/plans/BACKEND_PLAN.md`. The Reading Room has its own deep-dive in `/READING_ROOM_PLAN.md`.
>
> **Last updated:** 2026-04-27

---

## 1. Where we are

### What works today
- **Landing page** — hero, books showcase, modular engine, pace selector, lead-capture form. Driven by an XState machine. Hardcoded book list in machine context.
- **Backend lead intake** — `POST /api/leads/` stores name, email, book selection (as free strings), pace, notes.
- **Backend models** — `Lead`, `Shard`, `TemporalGrant` (token-based PDF access).
- **Backend admin** — Django admin for managing Shards, Leads, and issuing Grants manually.
- **Reading Room** — designed and locked (`/READING_ROOM_PLAN.md`), not yet built.

### What's missing or stubbed
- **No real "book" concept on backend.** Books exist only as hardcoded objects in the frontend machine; backend stores them as free-text strings on `Lead`. There is no `Book` model and no link from `Book` to its `Shard`s.
- **No automated email delivery.** Pace selection (Crawl/Steady/Soar) drives nothing. The whole "cadence engine" — the product's central premise — doesn't exist server-side.
- **No frontend route for the Reading Room.** `ShardView.tsx` is a dev-mock overlay rendered from the landing-page machine; this will be retired when `/r/:token` ships.
- **No user accounts, no library view, no payments.** Token-gated email links are the only access primitive.
- **No telemetry.** We can't tell whether anyone reads a Shard.

---

## 2. North-star principles (senior-dev convention)

These are non-negotiable across slices. Re-read before any architectural decision.

1. **Vertical slices over horizontal layers.** Every milestone produces something a real user can do end-to-end. We don't build the data model in month 1, the API in month 2, and the UI in month 3.
2. **Manual before automated.** The first version of every workflow is a human in the admin (or a script). Automation comes after the manual loop runs cleanly. This catches false-premise features before they're built.
3. **Boring tooling.** Django + Django Ninja, React Router, XState, react-pdf. No new frameworks per slice. No premature microservices. No GraphQL. SQLite in dev, Postgres in prod.
4. **One way to do one thing.** Two paths into the Reading Room? No. One. Two ways to issue a grant? No. One. The cost of duplicate paths is paid forever in confusion and drift.
5. **Token = access, not identity.** The `TemporalGrant` model is the security primitive. We do not bolt user accounts on top until there is a clear product reason.
6. **No premature abstraction.** Three similar lines is better than the wrong base class. Build the concrete thing, refactor when the third copy appears.
7. **Apple-clean over fancy.** UI bias: subtract. If a control could be removed without harming the user, remove it.
8. **Mandates from `/CLAUDE.md` are load-bearing.** Zero hardcoded strings, machine-first logic, temporal security, variable-velocity animations. Don't drift.

---

## 3. Slice plan (milestones)

Each slice is shippable on its own and unblocks the next. Estimates are dev-days for a single full-stack engineer; parallelize where the FE↔BE contract is locked.

### Slice 1 — Reading Room MVP *(in progress)*
**Goal:** A user with a token can read a Shard.

**Includes:**
- `react-router-dom` integration, route at `/r/:token`.
- `react-pdf` swap-in, retire iframe.
- Reading Room XState machine + components (per `/READING_ROOM_PLAN.md`).
- Backend: `validate_shard` returns unified `{status:"expired"}` for any failure mode.
- Retire the landing-page `ShardView` overlay path.

**Out of scope:** email delivery, book model, multiple shards per lead.

**Demo:** Admin issues a `TemporalGrant` manually in Django admin → copies the `/r/:token` URL → emails it manually → user reads.

**Est:** ~5–7 dev-days. See FRONTEND/BACKEND plans for ticket breakdowns.

---

### Slice 2 — `Book` model + landing alignment
**Goal:** Books become a real backend concept; the landing page is the source of truth no longer.

**Includes:**
- Backend: introduce `Book` model with `title`, `slug`, `tagline`, `cover_image`, etc. `Shard` gets a `book = ForeignKey(Book)` and an `order` field (chapter/sequence).
- Backend: `GET /api/books/` returns the public book catalog. `Lead.book_id` becomes a real FK.
- Frontend: landing's `BooksShowcase` consumes `/api/books/` instead of hardcoded array. Pre-select via `?book_id=<slug>` (deep-link from expired Reading Room).
- Admin: book + chapter management UI.

**Why this slice now:** without it, no further automation works. The cadence engine needs to know "for this user, which book are they on, and which chapter is next."

**Est:** ~4–5 dev-days.

---

### Slice 3 — Email delivery (manual trigger)
**Goal:** When admin issues a `TemporalGrant`, the user automatically receives a styled email with the link. No scheduling yet.

**Includes:**
- Backend: email service abstraction (`core/services/email.py`) — Django's `send_mail` to start, swap to Postmark/Resend later.
- Backend: a single email template (`templates/emails/shard_delivered.html`) — "Your next chapter has arrived" + link to `/r/:token`.
- Backend: post-save signal on `TemporalGrant` triggers email send (idempotent — guarded by a `delivered_at` field).
- Admin: a "Re-send email" action on the grant.

**Why before scheduling:** validates the email pipeline (deliverability, spam, template rendering) before any cron is involved. If emails don't land, schedules are useless.

**Est:** ~3 dev-days.

---

### Slice 4 — Cadence engine (the actual product)
**Goal:** A user with `pace=steady` and an active subscription to a book receives the next chapter automatically at the right cadence.

**Includes:**
- Backend: `Subscription` model — links a `Lead` to a `Book`, tracks `pace`, `current_chapter`, `next_send_at`, `paused`, `completed_at`.
- Backend: scheduled job (Django + `django-q2` or `celery-beat`) that runs hourly, finds subscriptions with `next_send_at <= now`, creates a new `TemporalGrant` for the next `Shard` in order, fires the email (Slice 3 pipeline), advances `current_chapter` and `next_send_at`.
- Backend: when a `Lead` is created, auto-create a `Subscription` (paced from form input). Or: admin gates this manually for early users.
- Operational: a clear "pause" mechanism in admin so a user's cadence can be halted.

**Out of scope:** payments, self-serve pause, email preference center.

**Est:** ~6–8 dev-days.

---

### Slice 5 — Telemetry minimum
**Goal:** We can answer "did the user open this Shard, and roughly how long did they spend?"

**Includes:**
- Backend: `ShardEvent` model (`grant`, `event_type`, `meta JSON`, `created_at`). Event types: `validated`, `streamed`, `closed`.
- Backend: validate/stream endpoints emit these events.
- Frontend: room emits `closed` when the user exits. No client-side identifiers — events are tied to grant.
- Admin: a basic dashboard view showing per-grant event log.

**Est:** ~2–3 dev-days.

---

### Future shelf (post-MVP, do not build now)

| # | Feature | Notes |
|---|---|---|
| F1 | Read-aloud (TTS) | react-pdf text extraction → browser speechSynthesis or backend TTS. |
| F2 | AI chat panel (desktop) | Right-gutter of the Reading Room. Uses page context. |
| F3 | Communal Reading Rooms | Multi-user synced session. New `ReadingSession` model + WebSockets. |
| F4 | User accounts + library | When users want to see all their Shards in one place. Tokens-only model breaks down here. |
| F5 | Payments | Stripe checkout pre-grant. Consider one-time vs subscription. |
| F6 | Pathfinder Engine | AI-driven content assembly per BUSINESS.md. |
| F7 | Telemetry-based adaptation | Adjust cadence based on Slice 5 data. |

---

## 4. FE ↔ BE contract (the seams)

These are the API contracts that unblock parallel FE/BE work. Locked.

| Endpoint | Method | Slice | Request | Response |
|---|---|---|---|---|
| `/api/leads/` | POST | 1 *(exists)* | `LeadIn` | `LeadOut` |
| `/api/shards/validate/` | GET | 1 *(tweak)* | `?token=<t>` | `{status:"valid", shard_id, title, expires_at}` or `{status:"expired"}` |
| `/api/shards/stream/` | GET | 1 *(exists)* | `?token=<t>` | `application/pdf` stream |
| `/api/books/` | GET | 2 *(new)* | — | `[{slug, title, tagline, cover_url, chapter_count}]` |
| `/api/books/<slug>/` | GET | 2 *(new)* | — | full book detail |

Frontend never touches: `Subscription`, `ShardEvent`, raw `Shard` URLs. These are backend-only concerns.

---

## 5. Open questions / risks (named, not avoided)

1. **What is `book_id` today?** The landing page hardcodes books in the machine. Each "book" the user picks is a string we store on `Lead.book_id`. Until Slice 2, this is just metadata — it doesn't link to any `Shard`s.
2. **`max_views` accounting.** With `react-pdf`, every page reload triggers a fresh fetch of the PDF binary, incrementing `current_views`. With `max_views=5` (default), users get 5 sessions max. We may need to either (a) raise the default, or (b) move `current_views` increment from the binary fetch to the validate call. **Decision needed before Slice 1 ships.** Recommend (a) — raise to 50, simpler, doesn't change logic.
3. **No auth means no "library view"** is possible. If a Sapien wants to see all the Shards they've received, they need to keep the emails. Acceptable trade-off until F4 is funded.
4. **Email deliverability.** Using `send_mail` against a single SMTP server will land us in spam. Slice 3 should start there but plan to move to a transactional provider (Postmark, Resend, SES) before Slice 4 launch.
5. **Pace = delivery cadence is immutable post-signup today.** When users want to change pace ("I picked Soar but it's too fast"), there's no mechanism. Add a "change pace" admin action in Slice 4 minimum; self-serve in F4.

---

## 6. Plan-doc index

| File | What's in it |
|---|---|
| `/DEVELOPMENT_PLAN.md` *(this)* | Slice plan, FE↔BE contract, risks. Read first. |
| `/plans/FRONTEND_PLAN.md` | Component inventory, route map, machine specs, styling, ticket-ready breakdown. |
| `/plans/BACKEND_PLAN.md` | Data model evolution, API specs, delivery engine, admin ops, ticket-ready breakdown. |
| `/READING_ROOM_PLAN.md` | Locked design for the Reading Room (Slice 1 deliverable). |
| `/CLAUDE.md` | Architecture map + engineering mandates. Always-on. |
| `/BUSINESS.md` | Product vision, audience, visual language. |

---

## 7. How tickets get cut

Each slice in §3 maps to a milestone in your tracker. Tickets within a slice come from §3 of the slice's detail file (`FRONTEND_PLAN.md` or `BACKEND_PLAN.md`), which lists ticket-sized units of work with explicit acceptance criteria.

A ticket is well-formed if:
- It has a single owner (FE or BE, not both).
- It can be reviewed in one PR.
- Its acceptance criteria are observable (you can demo it).
- It does not block the next ticket in its lane (or the block is explicit).

When in doubt: **smaller tickets**. A 3-day ticket is two 1-day tickets that haven't been factored yet.
