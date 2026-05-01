# CLAUDE.md — Sapien Paradox Backend

## Project Overview
A high-end, modular learning platform for "Intellectual Explorers." Focused on depth over velocity, digital monasticism, and temporal content delivery.

This repo is the **backend**. The frontend lives in a separate repo (`../frontend`) with its own `plans/` and `.claude/`.

## Tech Stack
- **Django 6.0+**
- **Django Ninja** (FastAPI-style API)
- **SQLite** (dev)
- Serves API at `http://localhost:8000/api`.

## Technical Architecture Map (Living Document)
*Update this map when files are added or significantly refactored. Detailed deep-dive in `TECHNICAL_SUMMARY.md`.*

- `sapien_backend/settings.py`: Core config (CORS, Media, Security).
- `sapien_backend/urls.py`: Main router mapping `/api/` to Ninja.
- `core/models.py`:
    - `Lead`: Captures user signup intent.
    - `Shard`: Metadata for modular PDF content.
    - `TemporalGrant`: Logic for expiring access tokens (`shortuuid`).
- `core/api.py`: Ninja API endpoints. Handles type-safe intake and secure PDF streaming.
- `core/admin.py`: Operational dashboard for managing Shards/Leads.

## Key documents
- `plans/STATE.md`: **Active planning state. Auto-injected each session by the SessionStart hook. Read first when resuming planning or design work.**
- `plans/README.md`: Folder map and conventions.
- `plans/components/<domain>/*.md`: Per-component specs (models, endpoints, services). Loaded on demand when working on that domain.
- `plans/_archive/`: Original plans (DEVELOPMENT_PLAN, BACKEND_PLAN). Frozen reference; superseded by re-planning under `components/`.
- `BUSINESS.md`: Product vision, audience, visual language.

## Active planning — Claude as owner

`plans/` is the source of truth. Three hooks make Claude an autonomous owner across sessions:

- **`SessionStart`** auto-injects `plans/STATE.md` into context and flags any `plans/**` files newer than `STATE.md` (a leftover from a prior session that ended abruptly — reconcile early).
- **`UserPromptSubmit`** marks each turn boundary so the Stop hook knows what was touched THIS turn.
- **`Stop`** soft-blocks at end of turn if any `plans/**` file was modified but `STATE.md` was not — interpret as a checkpoint prompt: either update `STATE.md` (cross-cutting decisions, focus shift, open questions) or reply acknowledging no STATE.md change is needed.

**Discipline (the checkpoint contract):**

- When a decision lands in conversation, write it to the relevant `components/<domain>/*.md` AND update `STATE.md` if cross-cutting — *immediately*, not at end of turn. Sessions can end abruptly; do not accumulate decisions across turns.
- When focus shifts, update `STATE.md` "Active focus" and "Next action" before continuing.
- Domain-specific decisions live in `components/<domain>/*.md`. STATE.md only carries cross-cutting locks.
- **Cross-repo sync:** when a cross-cutting product decision lands here, mirror the lock list in the frontend repo's `plans/STATE.md` so both sides stay aligned.

**Style:** BFS grilling — root before leaves, exhaust a level before descending. One question at a time, with a recommended answer. Plans → tickets only after the parent component spec(s) are locked.

**Workflow:** plan (here) → Claude Designer (visuals, frontend repo) → implement.

## Development Commands
- **Run server**: `python3 manage.py runserver` (Port 8000).
- **Migrations**: `python3 manage.py makemigrations core && python3 manage.py migrate`.

## Engineering Mandates
1. **Temporal Security**: Never expose raw Google Drive/S3 links; always proxy via `/api/shards/stream/`.
2. **Type-safe API**: Use Django Ninja schemas for all request/response bodies — no untyped dicts crossing the API boundary.
