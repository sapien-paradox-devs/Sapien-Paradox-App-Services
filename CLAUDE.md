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

- `sapien_backend/settings.py`: Core config (CORS, Media, Security, Custom User).
- `sapien_backend/urls.py`: Main router mapping `/api/` to Ninja.
- `core/models.py`:
    - `User`: Custom user model (email-based auth).
    - `Shard`: Metadata for modular PDF content.
    - `TemporalGrant`: Logic for expiring access tokens (`shortuuid`).
- `core/api/`: Package containing Ninja API logic.
    - `__init__.py`: API instance and router registration.
    - `auth.py`: Login/logout endpoints.
- `core/schemas/`: Pydantic schemas for type-safe API.
- `core/admin.py`: Operational dashboard for managing Shards/Users.

## Key documents
- `plans/STATE.md`: **Active planning state.**
- `plans/README.md`: Folder map and conventions.
- `BUSINESS.md`: Product vision, audience, visual language.

## Development Commands
- **Run server**: `python3 manage.py runserver` (Port 8000).
- **Migrations**: `python3 manage.py makemigrations core && python3 manage.py migrate`.
- **Tests**: `python3 manage.py test core`.

## Engineering Mandates
1. **Temporal Security**: Never expose raw Google Drive/S3 links; always proxy via `/api/shards/stream/`.
2. **Type-safe API**: Use Django Ninja schemas for all request/response bodies — no untyped dicts crossing the API boundary.
