# plans/

Single source of truth for Sapien Paradox planning.

## Files and folders

- **`STATE.md`** — active planning state. Auto-injected each session by the `SessionStart` hook. Read first when resuming. Update whenever a cross-cutting decision lands, focus shifts, or a new open question surfaces.
- **`components/<domain>/`** — one folder per domain (auth, reading-room, books, etc.). Inside: optional `README.md` (domain overview), one `.md` per major sub-component (screen, model, endpoint group, service, machine). Created lazily — only domains in active scope have folders.
- **`integrations/`** — cross-domain flow specs (signup-to-first-read, delivery-loop, etc.). Created when a flow is non-trivial.
- **`tickets/`** — flat list of heavyweight implementation tickets. Naming: `001-<slug>.md`. Each ticket links to the component spec(s) it implements via frontmatter.
- **`_archive/`** — original plans (DEVELOPMENT, FRONTEND, BACKEND, READING_ROOM). Frozen reference; superseded by re-planning under `components/`.

## Conventions

- **Lazy creation.** Don't pre-stub folders. Create when entering scope.
- **Component spec sections** (every `.md` follows this): Purpose, Current state, Future plan, Dependencies, Open questions, Notes for designer/implementer.
- **No tickets until parent spec is locked.** Spec is the contract; tickets implement it.
- **Domain decisions live in `components/<domain>/*.md`.** STATE.md only carries cross-cutting locks.
- **Domain README is optional** — only created when a domain has cross-component info worth grouping (locked domain-level decisions, status, cross-domain dependencies). Single-file domains skip it.

## Continuity

- `SessionStart` hook auto-injects `STATE.md` and flags drift.
- `UserPromptSubmit` hook marks each turn boundary.
- `Stop` hook nudges if a turn modified plans/ files without updating STATE.md.

**Discipline:** write decisions as they land — do not accumulate across turns. Sessions can end abruptly; mid-session checkpoints are how we don't lose work.
