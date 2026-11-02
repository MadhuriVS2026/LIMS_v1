# Setup Notes — a6d-linearity-seed-v2

Workspace preparation for the LIMS template engine change. Setup only; no design or implementation performed here.

## Fresh artifact folder (this run's output)

- `D:\RD-instance\GIT\backend-v2\.agents\tasks\a6d-linearity-seed-v2\`

## Confirmed reference inputs (REFERENCE ONLY — do not modify)

### Prior task artifacts (from a6d-linearity-addlinfo)
- `D:\RD-instance\GIT\backend-v2\.agents\tasks\a6d-linearity-addlinfo\design.md`
- `D:\RD-instance\GIT\backend-v2\.agents\tasks\a6d-linearity-addlinfo\design-review.md`
- `D:\RD-instance\GIT\backend-v2\.agents\tasks\a6d-linearity-addlinfo\design-review.json`
- `D:\RD-instance\GIT\backend-v2\.agents\tasks\a6d-linearity-addlinfo\plan.md`

### LIMS database
- `D:\RD-instance\GIT\backend-v2\lims.db`

### Precedent author scripts (located via search)
- `D:\RD-instance\GIT\backend-v2\_apply_a6d_sampling_details.py`
- `D:\RD-instance\GIT\backend-v2\_apply_cu30_kedit.py`

### Schema parser
- `D:\RD-instance\GIT\backend-v2\src\domain\services\calculation\template_schema.py`

### Worksheet service (WorksheetService.create_worksheet)
- `D:\RD-instance\GIT\backend-v2\src\application\services\worksheet_service.py` (method `create_worksheet` at line 116)

### Frontend component (located via search)
- `D:\RD-instance\GIT\frontend-react\src\features\test-templates\components\WorksheetForm.tsx`
  - Note: a mirror copy exists at `D:\RD-instance\GIT\.worktrees\f1f2-mirror-template\frontend-react\...`; the main-tree path above is canonical.

### Parity test
- `D:\RD-instance\GIT\backend-v2\tests\calculation\test_seeded_template_parity.py`

### App launcher
- `D:\RD-instance\GIT\start-lims.bat`

## Mandatory DB backup (created BEFORE any write)

- Source: `D:\RD-instance\GIT\backend-v2\lims.db`
- Backup: `D:\RD-instance\GIT\backend-v2\lims.db.bak-a6dlinearity2-20261027-122834`
- Verified: source and backup both 1,593,344 bytes.
- Note: the stray older backup `lims.db.bak-a6dlinearity-20261027-110803` (byte-identical, from an aborted attempt) was intentionally ignored; this is a fresh `a6dlinearity2`-prefixed backup.
- `lims.db` and all backups are NOT committed to git.
