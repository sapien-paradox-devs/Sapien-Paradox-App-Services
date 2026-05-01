# Backend Development Plan

> **Audience:** Backend engineers picking up tickets from this plan.
> **Scope:** All backend work across Slices 1–5 from `/DEVELOPMENT_PLAN.md`.
> **Conventions:** Django app structure stays flat. Django Ninja for the API. SQLite in dev, Postgres in prod. No microservices.

---

## 1. Architectural overview

### 1.1 Stack (locked)
- **Django 6.0+** — single project, single app (`core`) for now. Split when `core` exceeds ~15 models, not before.
- **Django Ninja** — typed API layer. Pydantic schemas for I/O. No DRF.
- **SQLite** for development; **Postgres** for production. Same ORM, no code change.
- **`shortuuid`** — token generation (already in use).
- **`django-q2`** — background jobs (Slice 4). Lighter than Celery; matches our scale. Decision in Slice 4 §6.
- **Email:** Django's `send_mail` (Slice 3) → Postmark/Resend transactional provider (Slice 4).

### 1.2 Folder structure (target)

```
backend/
├── manage.py
├── requirements.txt
├── sapien_backend/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── core/
    ├── __init__.py
    ├── admin.py                      # Django admin registrations
    ├── apps.py
    ├── models.py                     # Stays flat until ~15 models
    ├── api.py                        # Ninja API entry: `api = NinjaAPI()`
    ├── schemas.py                    # Pydantic schemas (split from api.py in Slice 2)
    ├── services/                     # Business logic, not glued to HTTP
    │   ├── __init__.py
    │   ├── grants.py                 # Grant issuance + validation logic (Slice 1)
    │   ├── email.py                  # Email sending (Slice 3)
    │   └── delivery.py               # Cadence engine (Slice 4)
    ├── jobs/                         # Background jobs (Slice 4)
    │   ├── __init__.py
    │   └── deliver_next_chapter.py
    ├── migrations/
    └── tests/
        ├── test_models.py
        ├── test_api.py
        └── test_services.py
```

> **Rule:** API endpoints are thin. They parse request, call a service function, return a schema. Business logic does not live in `api.py`.

### 1.3 Models map (target after Slice 4)

```
Book ─────────────┐
  ├─ slug         │  has_many
  ├─ title        ├─→ Shard
  ├─ tagline      │     ├─ order
  ├─ cover_url    │     ├─ title
  └─ ...          │     └─ file (PDF)
                  │
Lead ─────────────┤
  ├─ full_name    │
  ├─ email        │
  ├─ pace         │
  └─ ...          │
       │
       │ has_many                       has_many
       ▼                                   ▲
   Subscription ──────────────────────────┐│
       ├─ book = FK(Book)                 ││
       ├─ lead = FK(Lead)                 ││
       ├─ pace                            ││
       ├─ current_chapter (int)           ││
       ├─ next_send_at                    ││
       ├─ paused (bool)                   ││
       └─ completed_at                    ││
                                          ▼│
                                      TemporalGrant
                                         ├─ shard = FK(Shard)
                                         ├─ subscription = FK(Subscription, nullable)
                                         ├─ lead = FK(Lead, nullable)        ← Slice 3 (for email watermarking — but we said no watermark; nullable still useful for audit)
                                         ├─ token (shortuuid)
                                         ├─ expires_at
                                         ├─ max_views
                                         ├─ current_views
                                         ├─ delivered_at (Slice 3)
                                         └─ ...

ShardEvent (Slice 5)
  ├─ grant = FK(TemporalGrant)
  ├─ event_type ("validated" | "streamed" | "closed")
  ├─ meta (JSONField)
  └─ created_at
```

### 1.4 API map (target after Slice 5)

| Method | Path | Purpose | Slice |
|---|---|---|---|
| `POST` | `/api/leads/` | Create a lead. *(exists)* | 1 |
| `GET` | `/api/shards/validate/` | Validate token, return shard meta or `{status:"expired"}`. *(tweak)* | 1 |
| `GET` | `/api/shards/stream/` | Stream PDF for a valid token. *(exists)* | 1 |
| `GET` | `/api/books/` | Public catalog. Slug-based. | 2 |
| `GET` | `/api/books/<slug>/` | Single book detail. | 2 |
| `POST` | `/api/events/closed/` | Reading Room emits when user closes. *(optional)* | 5 |

> The frontend touches **only** these endpoints. `Subscription` and admin operations are not exposed publicly.

---

## 2. Slice-by-slice work

### Slice 1 — Reading Room MVP

**Goal:** the existing token-gated PDF flow works, with a single backend tweak to unify error responses.

#### Changes
1. **`core/api.py` — `validate_shard`**
   - Today: `get_object_or_404(TemporalGrant, token=token)` returns 404 for unknown tokens.
   - Change: catch `TemporalGrant.DoesNotExist` and return `{"status": "expired"}`. Same shape as time-expired/views-exhausted. Frontend has one error state to handle.
   - Code shape:
     ```python
     @api.get("/shards/validate/")
     def validate_shard(request, token: str):
         try:
             grant = TemporalGrant.objects.get(token=token)
         except TemporalGrant.DoesNotExist:
             return {"status": "expired"}
         if not grant.is_valid():
             return {"status": "expired"}
         return {
             "status": "valid",
             "shard_id": grant.shard.slug,
             "expires_at": grant.expires_at,
             "title": grant.shard.title,
         }
     ```

2. **`core/api.py` — `stream_shard`**
   - No code change in Slice 1. Already correct.
   - **Operational note:** raise the default `max_views` on the `TemporalGrant` model from `5` to `50`. Every page reload of the Reading Room re-fetches the binary (one request per `<Document>` mount), so 5 is too low. This is a one-line model change + a migration.

3. **Tests**
   - Add `tests/test_api.py` covering: valid token returns `valid`, time-expired returns `expired`, views-exhausted returns `expired`, unknown token returns `expired` (the new branch).

---

### Slice 2 — `Book` model + landing alignment

**Goal:** introduce a real `Book` concept; `Shard`s become chapters of a `Book`; landing page reads from API.

#### Changes
1. **New model: `Book`**
   ```python
   class Book(models.Model):
       slug = models.SlugField(unique=True)
       title = models.CharField(max_length=255)
       tagline = models.CharField(max_length=512, blank=True)
       cover_image = models.ImageField(upload_to="book_covers/", blank=True, null=True)
       is_published = models.BooleanField(default=False)
       created_at = models.DateTimeField(auto_now_add=True)
   ```

2. **Update `Shard`**
   - Add `book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="shards")`.
   - Add `order = models.PositiveIntegerField()` for sequencing within a book.
   - Add `Meta: ordering = ["order"], unique_together = [["book", "order"]]`.

3. **Update `Lead`**
   - Replace `book_id = CharField` and `book_title = CharField` with `book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True)`.
   - **Migration nuance:** existing leads have free-text strings. Write a data migration that maps `book_id` (current slug-ish string) to `Book` rows. Pre-populate `Book` rows for the books currently hardcoded on the frontend before the migration runs. Document the manual step.

4. **New endpoints**
   ```python
   class BookOut(Schema):
       slug: str
       title: str
       tagline: str
       cover_url: str | None
       chapter_count: int

   @api.get("/books/", response=List[BookOut])
   def list_books(request):
       return [
           {
               "slug": b.slug,
               "title": b.title,
               "tagline": b.tagline,
               "cover_url": b.cover_image.url if b.cover_image else None,
               "chapter_count": b.shards.count(),
           }
           for b in Book.objects.filter(is_published=True)
       ]

   @api.get("/books/{slug}/", response=BookOut)
   def get_book(request, slug: str):
       book = get_object_or_404(Book, slug=slug, is_published=True)
       return ...
   ```

5. **Admin updates**
   - Register `Book` with inline `Shard` admin (chapters edited from the book detail page).
   - Existing `Lead` admin gets a `book` foreign-key dropdown.

6. **Schemas split**
   - Move all Pydantic schemas to `core/schemas.py`. `api.py` becomes endpoints-only. This is a one-shot refactor done in this slice while we're already touching the file.

#### Tickets
| # | Ticket | Acceptance |
|---|---|---|
| BE-1 | Slice 1: tweak `validate_shard` to return `{status:"expired"}` for unknown tokens. | Endpoint test asserts unknown token → expired. |
| BE-2 | Slice 1: bump `max_views` default to 50; create + run migration. | Migration applied; new grants get 50 by default. |
| BE-3 | Slice 1: add `tests/test_api.py` covering all four validate paths. | All tests green. |
| BE-4 | Slice 2: create `Book` model + migration. | Admin shows Book CRUD. |
| BE-5 | Slice 2: add `book` FK + `order` to `Shard`; migrate. | Existing shards get a book + order via data migration. |
| BE-6 | Slice 2: replace `Lead.book_id`/`book_title` with `Lead.book` FK; data migration. | Old leads remain queryable; new leads use FK. |
| BE-7 | Slice 2: implement `GET /api/books/` and `GET /api/books/<slug>/`. | Returns published books only; unpublished hidden. |
| BE-8 | Slice 2: split schemas to `core/schemas.py`. | `core/api.py` contains no `class ... Schema` definitions. |
| BE-9 | Slice 2: admin inline for chapters. | Book detail page lets admin reorder Shards via drag (or `order` field). |

---

### Slice 3 — Email delivery (manual trigger)

**Goal:** when a `TemporalGrant` is created, the corresponding `Lead` gets an email with the link.

#### Changes
1. **New service: `core/services/email.py`**
   - Single function `send_shard_email(grant: TemporalGrant) -> None`.
   - Renders an HTML template + plain-text fallback.
   - Uses Django's `send_mail` for now. The function signature is the seam; provider swap (Postmark/Resend) is hidden inside.

2. **Email template**
   - `core/templates/emails/shard_delivered.html`
   - Subject: `"<Shard title> — your next chapter awaits."` (i18n later; English-only for now.)
   - Body: greeting (uses `lead.full_name`), one CTA button linking to `{{ frontend_base_url }}/r/{{ grant.token }}`, expiry note ("This link expires on <date>").
   - Plain-text version for spam-score sanity.

3. **Trigger**
   - Two options:
     - **A. Django signal** on `TemporalGrant.post_save(created=True)` calls `send_shard_email`. Pro: automatic. Con: signals are spooky-action-at-a-distance.
     - **B. Explicit call** in admin save action / management command. Pro: explicit. Con: easy to forget.
   - **Pick: A**, but add a `delivered_at` field on `TemporalGrant` (nullable datetime). The signal sets it after a successful send; if it's already set, it's a no-op. This makes re-sends explicit (admin nulls the field to re-send).

4. **`TemporalGrant.delivered_at`** field added.

5. **Admin action: "Re-send email"**
   - Sets `delivered_at = None` and re-saves the row, which re-fires the signal.

6. **Settings**
   - `FRONTEND_BASE_URL` env var (e.g. `https://sapien.example.com`). Email links use this.
   - `DEFAULT_FROM_EMAIL` env var. Reasonable default in dev.

7. **Tests**
   - Use Django's `mail.outbox` to assert one email is sent on grant creation.
   - Assert `delivered_at` is set after send.
   - Assert idempotency: re-saving a delivered grant does not send twice.

#### Tickets
| # | Ticket | Acceptance |
|---|---|---|
| BE-10 | Add `delivered_at` to `TemporalGrant`. | Migration applied; field nullable; defaults to `None`. |
| BE-11 | Implement `core/services/email.py` with `send_shard_email`. | Calling the function with a fresh grant sends one email; mock SMTP in tests. |
| BE-12 | HTML + plaintext email templates. | Templates render with grant context; QA on Litmus or similar (manual). |
| BE-13 | post_save signal on `TemporalGrant`. | Creating a grant in admin sends an email and sets `delivered_at`. |
| BE-14 | Admin action: "Re-send email". | Admin can trigger a re-send without creating a new grant. |
| BE-15 | Email config docs in `/backend/CLAUDE.md`. | Lists required env vars and the dev setup. |

---

### Slice 4 — Cadence engine

**Goal:** real automated delivery on Crawl/Steady/Soar pace.

#### Changes
1. **New model: `Subscription`**
   ```python
   PACE_INTERVAL = {
       "crawl":  timedelta(weeks=1),
       "steady": timedelta(days=3),   # ~2/week
       "soar":   timedelta(days=1),
   }

   class Subscription(models.Model):
       lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="subscriptions")
       book = models.ForeignKey(Book, on_delete=models.CASCADE)
       pace = models.CharField(max_length=20)           # crawl/steady/soar
       current_chapter = models.PositiveIntegerField(default=0)  # number of shards already sent
       next_send_at = models.DateTimeField()
       paused = models.BooleanField(default=False)
       completed_at = models.DateTimeField(null=True, blank=True)
       created_at = models.DateTimeField(auto_now_add=True)
   ```

2. **Subscription auto-creation**
   - When a `Lead` is created via `POST /api/leads/`, also create a `Subscription` (`lead`, `book`, `pace`, `next_send_at = now()` for immediate first delivery).
   - Add idempotency: don't create duplicate subscriptions if the lead exists for the same book.
   - **Decision flag:** in early days we may want admin approval before auto-subscription. Add a Django setting `AUTO_SUBSCRIBE_ON_LEAD = False` so we can flip the behavior without code change. Default `False`; admin manually creates subscriptions until we trust the loop.

3. **Cadence service: `core/services/delivery.py`**
   - Function `deliver_due_subscriptions() -> int`. Returns number of sends.
   - Algorithm (simple, idempotent):
     ```
     for sub in Subscription.objects.filter(
         paused=False, completed_at__isnull=True, next_send_at__lte=now
     ):
         next_chapter = sub.book.shards.filter(order=sub.current_chapter + 1).first()
         if next_chapter is None:
             sub.completed_at = now
             sub.save()
             continue

         grant = TemporalGrant.objects.create(
             shard=next_chapter,
             lead=sub.lead,
             subscription=sub,
             expires_at=now + timedelta(days=14),
             max_views=50,
         )
         # email is sent by the post_save signal from Slice 3

         sub.current_chapter += 1
         sub.next_send_at = now + PACE_INTERVAL[sub.pace]
         sub.save()
     ```
   - All inside a single `transaction.atomic()` per subscription. Failures roll back that subscription only; others keep going.

4. **Background job: `core/jobs/deliver_next_chapter.py`**
   - Wraps `deliver_due_subscriptions()`.
   - Scheduled via `django-q2` (or `celery-beat` if the team prefers; same outcome). Runs every hour.
   - Add a Django management command equivalent for manual runs / cron fallback: `python manage.py deliver_due_chapters`.

5. **Update `TemporalGrant`**
   - Add nullable FK fields:
     - `lead = ForeignKey(Lead, null=True, blank=True)`
     - `subscription = ForeignKey(Subscription, null=True, blank=True)`
   - For grants created by Slice 4, both are set. For Slice 1–3 admin-issued grants, both can be null. Code that uses these fields handles None gracefully.

6. **Admin tooling**
   - `Subscription` admin with bulk actions: "Pause", "Resume", "Skip next chapter", "Reset to chapter 0".
   - List view shows: lead, book, pace, current chapter / total, next send time, paused state.

7. **Operational**
   - Add a `/health/` endpoint (Slice 4 if not earlier) so the scheduler's host can be monitored.
   - Logging: every cadence run logs a one-liner summary. `INFO`-level enough.

8. **Failure modes (named, not avoided)**
   - Email service down → `send_mail` raises → grant rolled back via the atomic block → next cron run retries.
   - Lead has no email → log + skip the subscription, mark a flag (defer to admin attention).
   - Book runs out of chapters mid-subscription → `completed_at` set; user gets no further emails. Consider: send a "you've finished" email? Defer.

#### Tickets
| # | Ticket | Acceptance |
|---|---|---|
| BE-16 | Create `Subscription` model + migration. | Admin shows Subscription CRUD. |
| BE-17 | Add `lead`, `subscription` nullable FKs to `TemporalGrant`. | Migration applied; existing grants unchanged. |
| BE-18 | Implement `core/services/delivery.py::deliver_due_subscriptions`. | Unit test: one due subscription → one new grant → `current_chapter` incremented → `next_send_at` advanced by pace interval. |
| BE-19 | Auto-create `Subscription` on `Lead` creation, gated by `AUTO_SUBSCRIBE_ON_LEAD`. | Setting flipped on → new lead gets a subscription. Off → no auto-create. |
| BE-20 | Add `core/jobs/deliver_next_chapter.py` + `django-q2` config. | Scheduled job runs hourly; logs a summary line. |
| BE-21 | Management command `deliver_due_chapters`. | `python manage.py deliver_due_chapters` runs the same code path. |
| BE-22 | Admin actions: pause, resume, skip, reset on Subscription. | All four work end-to-end and persist. |
| BE-23 | `/health/` endpoint. | Returns 200 with DB connectivity check. |

---

### Slice 5 — Telemetry minimum

**Goal:** answer "did the user open this Shard, and roughly how long did they spend?"

#### Changes
1. **New model: `ShardEvent`**
   ```python
   class ShardEvent(models.Model):
       grant = models.ForeignKey(TemporalGrant, on_delete=models.CASCADE, related_name="events")
       event_type = models.CharField(max_length=32)   # validated | streamed | closed
       meta = models.JSONField(default=dict)
       created_at = models.DateTimeField(auto_now_add=True)
   ```

2. **Emission**
   - `validate_shard` emits `validated` (every call).
   - `stream_shard` emits `streamed` (every call). De-dup at admin-view level, not here.
   - New endpoint `POST /api/events/closed/` accepts `{token, duration_ms}`; emits `closed`. Frontend calls this on close (best-effort, `navigator.sendBeacon`).

3. **Admin view**
   - Read-only `ShardEvent` admin with filters by grant + event_type + date.
   - On `TemporalGrant` admin, show inline event log.

#### Tickets
| # | Ticket | Acceptance |
|---|---|---|
| BE-24 | Create `ShardEvent` model + migration. | Admin renders the model. |
| BE-25 | Emit `validated` and `streamed` events from existing endpoints. | Each call adds one row; verified by integration test. |
| BE-26 | New `POST /api/events/closed/` endpoint. | Accepts token + duration; emits one row; rejects unknown token quietly with 204. |
| BE-27 | Inline events on `TemporalGrant` admin. | Admin sees event log per grant. |

---

## 3. Cross-slice operational concerns

### 3.1 Migrations
- One migration per ticket where possible — easier to revert.
- Data migrations (Slice 2 leads → book FK) live in their own migration files with explicit forward + reverse functions.
- Run migrations in CI against a copy of production data (when prod exists).

### 3.2 Testing
- **Models:** light tests; mostly `is_valid()` on `TemporalGrant` and any new method.
- **API:** every endpoint gets at least one happy + one sad path test using Ninja's test client.
- **Services:** business logic (delivery cadence, email) gets focused unit tests with mocked external deps.
- **No 100% coverage gating.** Don't write tests for trivial getters.

### 3.3 Environment + secrets
- `DJANGO_SECRET_KEY`, `DATABASE_URL`, `FRONTEND_BASE_URL`, `DEFAULT_FROM_EMAIL`, `EMAIL_BACKEND_*` — env vars, not in repo.
- `.env.example` checked in; `.env` ignored.

### 3.4 Deployment notes (forward-looking, not in scope)
- Single Django process behind nginx is fine through Slice 4.
- Background worker (django-q2) runs as a separate process — needs supervisor/systemd config. Add to deploy docs when Slice 4 ships.
- Postgres for prod from day one — no SQLite in production.

---

## 4. Anti-patterns (don't do)

- ❌ Don't put business logic in `api.py`. It's the HTTP edge — keep it thin. Logic → `services/`.
- ❌ Don't write Django signals for anything other than the email-on-grant-creation case (and even that is borderline). Signals make codebases hard to trace.
- ❌ Don't introduce DRF. Ninja is the convention. One way to do one thing.
- ❌ Don't add a Redis dependency until you genuinely need it (rate limiting, distributed locks, websockets). `django-q2` works against Postgres for our scale.
- ❌ Don't expose internal models (`Subscription`, `ShardEvent`) over the public API. Admin-only.
- ❌ Don't skip `transaction.atomic()` in `delivery.py`. A half-sent grant is the worst kind of bug.
- ❌ Don't pre-create `Subscription` rows for old `Lead`s "to be safe." Backfill explicitly with a one-off management command if needed.
- ❌ Don't add a `User` model "for the future." Tokens are the access primitive. When we need accounts (F4), we add them deliberately.

---

## 5. Out-of-scope (named so it doesn't sneak in)

- ❌ Auth / user accounts.
- ❌ Payments.
- ❌ Self-serve subscription management (pause, change pace) — admin only until F4.
- ❌ i18n / multi-language emails.
- ❌ A/B testing infrastructure.
- ❌ GraphQL.
- ❌ WebSockets.
- ❌ Redis.
- ❌ Microservices.

If a ticket starts implying any of these, push back and re-scope.
