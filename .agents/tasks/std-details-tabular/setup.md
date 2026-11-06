# Setup — Standard-Details-to-tabular conversion

## Worktree
- Path: `d:\RD-instance\GIT\.worktrees\std-details-tabular`
- Branch: `std-details-tabular` (newly created off base `MadhuriWorktree` @ 4b43b51)

## Artifact folder
- `d:\RD-instance\GIT\.agents\tasks\std-details-tabular` (lives in MAIN checkout, not the worktree)

## SQLite DB resolution
- `lims.db` is gitignored, so it was NOT copied into the new worktree.
- `DATABASE_URL` default (src/config/settings.py) = `sqlite+aiosqlite:///./lims.db` — a RELATIVE path.
- No `.env` exists in either backend-v2 (main or worktree); the default applies.
- Seed/validate scripts run from the `backend-v2` cwd, so they open `<cwd>\lims.db`:
  - From MAIN checkout cwd → `d:\RD-instance\GIT\backend-v2\lims.db` (EXISTS, live DB, 2,547,712 bytes)
  - From WORKTREE cwd → `d:\RD-instance\GIT\.worktrees\std-details-tabular\backend-v2\lims.db` (does NOT exist yet)

## Backups created (BEFORE any DB write)
- `d:\RD-instance\GIT\backend-v2\lims.db.bak-std-details-tabular-20261103-112033` (2,547,712 bytes)
  - This is the only lims.db that currently exists and that scripts could touch.
  - The worktree backend-v2 has no lims.db yet; back it up if/when it is created before writing.
