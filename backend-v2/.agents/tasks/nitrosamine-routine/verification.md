# Verification — Nitrosamine Routine analysis sheet (TPL-NITRO-0001)

Addresses review finding **B1** (CHANGES_REQUESTED): the required verification
evidence had not been run/recorded. All correctness findings in `review.md`
already passed; this note supplies the missing run record. No formula or test
changes were required — the three commands below are the evidence.

Working directory: `d:/RD-instance/GIT/backend-v2`. Runner: `pytest` (per
`pyproject.toml`), Python 3.13.

## 1. New parity test

Command:

```
python -m pytest tests/calculation/test_nitrosamine_routine_parity.py -q
```

Result: **7 passed in 0.24s** (exit 0).

Covers: O11 standard conc = 1.0416537600000002; left-block stats D23=76406,
D24=479.69365224067747, D25=0.6278219671762394; right-block BKT stats
G23=81345.75, G24=4455.392341496613, G25=5.477105247043163 (pooled
blank-chromatogram quirk); all 16 Sample Solution PPM golds (0.0611 … 1.8798);
reportable result = first sample PPM (0.0611); SST blocking on `std_stats.rsd_area`
only; BKT %RSD not a criterion.

## 2. Broader template suites

Command:

```
python -m pytest tests/calculation/test_seeded_template_parity.py tests/calculation/test_workbook_parity.py -q
```

Result: **3 failed, 338 passed in 2.39s** (exit 1).

The 3 failures are all in `TestA6BDissolutionWithReplacement`
(`test_unit1_release_carryover`, `test_per_timepoint_summary`,
`test_amount_remaining`) — the A6B dissolution-with-replacement template, which
has no relationship to the nitrosamine module (its `release`/`amount` groups
return EMPTY; a pre-existing issue in that separate template).

**Proof the failures are pre-existing and NOT caused by registering
`TPL-NITRO-0001`:** with `*_NITRO` temporarily removed from
`scripts/template_definitions/__init__.py`, the same A6B class still fails
identically:

```
python -m pytest tests/calculation/test_seeded_template_parity.py::TestA6BDissolutionWithReplacement -q
-> 3 failed, 1 passed in 1.88s
```

The same three A6B tests fail with the module unregistered, so adding
`TPL-NITRO-0001` to `SEED_TEMPLATES` did not perturb any cross-template suite.
The registry edit was restored to its registered state after this check (34
templates, `TPL-NITRO-0001` present — see step 3).

## 3. Registry import smoke

Command:

```
python -c "from scripts.template_definitions import SEED_TEMPLATES; print(len(SEED_TEMPLATES))"
```

Result: **34** (exit 0). A follow-up check confirmed `TPL-NITRO-0001` is present
in `SEED_TEMPLATES` and the import resolves cleanly with the module registered.

## Summary

| Command | Result |
| --- | --- |
| parity test (`test_nitrosamine_routine_parity.py`) | 7 passed |
| broader suites (seeded + workbook parity) | 338 passed, 3 failed (pre-existing A6B, unrelated) |
| registry import smoke | 34 templates, `TPL-NITRO-0001` present |

No changes were made to `nitrosamine_routine.py`,
`test_nitrosamine_routine_parity.py`, or the `__init__.py` registry edit (the
temporary removal in step 2 was reverted). Per task constraints, no git commit
was created and `lims.db` was not touched.
