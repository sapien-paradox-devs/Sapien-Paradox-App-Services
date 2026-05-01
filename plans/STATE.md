# Active planning state — backend

> Auto-loaded each session by `.claude/hooks/session-start.sh`.
> Update whenever a cross-cutting decision lands, focus shifts, or a new open question surfaces.
> Domain-specific decisions live in `components/<domain>/*.md`, NOT here. STATE.md is cross-cutting only.
>
> **Note:** This is the backend slice. The frontend repo has its own `plans/STATE.md` covering UI/UX state. Keep cross-cutting locks below in sync between the two when product-level decisions land.

**Last updated:** 2026-05-01
**Mode:** **Prototype-first.** Lock the happy flow at the basic-shape level (no concrete structure — decisions may change once the team weighs in) and build a working demo end-to-end. Detail-level grilling deferred until after the prototype lands.
**Active focus:** Happy-flow grilling **closed**. Pivoting to ticket creation in `plans/tickets/`.
**Next action:** Draft prototype tickets covering the backend slice of the happy flow (signup endpoint, Stripe checkout-session create, Stripe webhook → User+Order, cadence scheduler, WhatsApp/Twilio dispatcher, reminder job, profile data endpoint, login endpoint, token-gated PDF stream). ~5–7 backend tickets expected.

---

## Locked decisions (cross-cutting)

1. **Plans live in `plans/` as a tree.** Shape: `STATE.md`, `README.md`, `components/<domain>/*.md`, `integrations/*.md`, `tickets/*.md`, `_archive/`. No numeric prefixes. No separate architecture folder — `CLAUDE.md` files own architecture truth. Folders/files created lazily — only domains in active scope have folders.
2. **Plans = source of truth.** Edited in place. Domain decisions in `components/<domain>/*.md`. STATE.md is cross-cutting only.
3. **Existing tickets in `_archive/BACKEND_PLAN.md` (BE-1..27) are reference, not canon.** We re-cut tickets from root.
4. **Tickets are heavyweight implementation specs.** File structure, function signatures (where useful), edge cases, test plan, acceptance, out-of-scope. Implementation should be straight-forward because the planning happened upstream.
5. **Tests fold into the implementing ticket's acceptance.** One slice-closer smoke-test ticket per slice for end-to-end coverage.
6. **Ticket file naming:** flat `plans/tickets/`, files `001-<slug>.md` (3-digit padded). Lane (FE/BE) in frontmatter.
7. **BFS over DFS.** Resolve root-level questions before descending. Within a level, exhaust all questions. One question at a time during grilling, with a recommended answer.
8. **Cover and document everything that exists.** Don't dismiss code as cruft. Disposition (replace, retain, delete) is part of each component spec's "Current state" section.
9. **Two personas: Reader and Admin.** Same signed-in surface for now. Admin gets distinct features later. "Visitor" is the unauthenticated entry state of a Reader.
10. **Auth is infrastructure, not a product pivot.** Product remains cadence-paced delivery (Crawl/Steady/Soar). Cadence channel is **WhatsApp via Twilio** (not email) — each unlocked chapter is delivered as a Twilio WhatsApp message containing a token-gated link to the secure PDF stream. Auth replaces "we know you by token" with "we know you by account." Token-gated chapter links remain self-authenticating (clicking a WhatsApp link does NOT require login). The `/profile` API exposes a re-read library of **already-unlocked** chapters only — never future ones.
11. **Workflow:** plan (here) → Claude Designer designs visuals → we implement. Plans specify *contents and behavior*, not visual styling. (Frontend-side concern; backend impact is API shape stability.)
12. **Continuity / checkpoint system:** STATE.md is the resume file. Three hooks: `SessionStart` (auto-injects STATE.md, flags drift), `UserPromptSubmit` (marks turn boundary), `Stop` (per-turn nudge if plans/ touched without STATE.md sync). Model writes decisions as they land — does not accumulate across turns.
13. **Payments are real and gate signup.** One-time per-book purchase via Stripe. Recurring catalog subscription is **deferred but designed-for** — book-access checks route through a service function (`user_has_access_to(user, book)`) that a future `Subscription` mechanism can extend additively without rewiring callers. **No `User` row exists until payment clears**; signup is webhook-driven async (form → Stripe checkout → webhook → User + Order created together). Detail in `components/payments/README.md`.

## Open questions (backend-relevant)

_None currently. Cross-domain UI questions live in the frontend STATE.md._

## Working notes

- User prefers simple over fancy. Push back on overengineering by default. Add complexity only when it earns its keep.
- One question at a time during grilling. Always provide a recommended answer with reasoning.
- Token-gated email/WhatsApp links (`TemporalGrant`) remain self-authenticating; auth adds account-based access on top, doesn't replace tokens for the link flow.
- Plans → tickets flow: never create tickets until parent component spec(s) are locked.
- Audit findings about current code drift are detailed in each component's "Current state" section — don't restate them here.

## Recent thread (backend-relevant)

1. User clarified: tickets are heavyweight, plan from root to leaf, plans/ is tree, auth becomes real.
2. Reviewed plans/ tree proposal twice; landed on `components/<domain>/*.md` structure with optional domain README, separate `integrations/`, flat `tickets/`. Lazy folder creation.
3. Locked: 2 personas (Reader, Admin); same signed-in surface; basic email+password auth; cadence-paced product unchanged.
4. Set up continuity system: 3 hooks installed (`session-start.sh`, `user-prompt-submit.sh`, `stop.sh`), `.claude/.gitignore` for ephemeral markers, plans/ tree restructured. Auth domain skeleton populated in `components/auth/`.
5. User introduced payment-gated signup. Locked: one-time per-book purchase via Stripe; recurring subscription deferred but designed-for. New `components/payments/` domain scaffolded. `auth/user-model.md` flagged for revision (book/pace move from User → Order; signup becomes async/webhook-driven).
6. Mode shift: **prototype-first**. Stop deep structural planning. Lock the basic happy flow only, build a working demo, defer detailed component specs.
7. Backend-side happy flow:
   - Landing form POST (now includes **password** AND **phone**) → `POST /api/payments/create-checkout-session` → Stripe Checkout → success webhook → User + Order created together → instantly fire chapter-1 WhatsApp + return success URL → user lands on welcome screen.
   - **Cadence trigger**: chapter N unlocks at `signup_time + (N-1) × cadence_delay` — pure schedule from signup, NOT read-completion-based. Each unlock fires a WhatsApp message with the chapter link via Twilio. Cadence advances regardless of whether the user has opened previous chapters.
   - **Reminders:** if a user hasn't opened chapter N within ~24h of its unlock, a single follow-up WhatsApp reminder is sent for that chapter. One reminder per chapter, non-spammy. (Open-tracking signal source: PDF stream endpoint hit on the chapter token.)
   - Prototype uses a tiny cadence delay (e.g. 1 minute) for end-to-end demo; real values wired later.
8. Channel pivot: **WhatsApp via Twilio** (not email). Twilio sends each unlocked chapter as a WhatsApp message containing a token-gated `/r/:token` link to the secure PDF stream. Token alone authenticates that chapter (no login required). Phone field added to landing form / User model.
9. `/profile` data shape: account block (name, email, phone, current book, pace) + list of unlocked chapters (chapters 1..N where N is the highest-unlocked). Future chapters NOT exposed in the API. Single endpoint serves it.
10. Chapter 1 unlocks immediately on Stripe payment success — webhook handler fires the chapter-1 WhatsApp synchronously and creates the welcome flow.
11. **(this turn)** Grilling closed. Prototype happy flow is locked enough to ticket. Open at-ticket-time (non-blocking): end-of-book behavior (default: just stop sending; no celebration).
