# Standard Details to tabular: roster

Mode: verify, 2026-11-05 18:05:12 UTC. Database: `d:\RD-instance\GIT\backend-v2\lims.db`. Pre-state backup: `d:\RD-instance\GIT\backend-v2\lims.db.bak-std-rollout-20261105-180445`.
Verify: all checks passed.

Rows to convert: 25 of 25; groups converted: 28; reference-audit violations: 0; equivalence diffs: 0; problems: 0.

| Code | Id | Ver | Status | Groups | Source | Module | Action | Drift | Equivalence variants | Non-blank calculated |
|---|---|---|---|---|---|---|---|---|---|---|
| TPL-A1-0001 | 1 | 1 | Active | standard | helper | equal | convert | - | empty 1, synth 1, ws 4, pad3 1 | 19 |
| TPL-A1-0002 | 15 | 1 | Active | standard | db | none | convert | - | empty 1, synth 1, pad3 1 | 19 |
| TPL-A1-0003 | 39 | 1 | Active | standard | inline | equal | convert | - | empty 1, synth 1, ws 1, pad3 1 | 22 |
| TPL-A2-0001 | 2 | 1 | Active | standard | helper | drifted | convert | context | empty 1, synth 1, ws 1, pad3 1 | 17 |
| TPL-A2-0003 | 33 | 1 | Active | standard | inline | drifted | convert | groups.std_injections, groups.bkt_injections | empty 1, synth 1, ws 1, pad3 1 | 56 |
| TPL-A2-0006 | 54 | 1 | Active | standard | inline | equal | convert | - | empty 1, synth 1, ws 1, pad3 1 | 41 |
| TPL-A3-0001 | 3 | 1 | Active | standard | helper | drifted | convert | criteria, resultRef, groups.media_names, groups.std_areas, groups.media_solution_1, groups.media_sets_1, groups.media_solution_2, groups.media_sets_2, groups.media_solution_3, groups.media_sets_3, groups.media_solution_4, groups.media_sets_4, groups.media_solution_5, groups.media_sets_5, groups.media_solution_6, groups.media_sets_6, groups.media_solution_7, groups.media_sets_7, groups.media_solution_8, groups.media_sets_8, groups.media_solution_9, groups.media_sets_9, groups.media_solution_10, groups.media_sets_10, groups.stats, groups.samples | empty 1, synth 1, ws 1, pad3 1 | 135 |
| TPL-A4-0001 | 4 | 1 | Active | standard, standard_2 | helper | equal | convert | - | empty 1, synth 1, ws 1, pad3 1 | 40 |
| TPL-A4-0004 | 52 | 1 | Active | standard | helper | drifted | convert | groups.unknowns_header, groups.unknowns | empty 1, synth 1, ws 1, pad3 1 | 11 |
| TPL-A6A-0001 | 6 | 1 | Active | standard | helper | drifted | convert | context, resultRef, groups.additional_info, groups.standard, groups.corel_weights, groups.corel_areas, groups.stats, groups.bkt_1, groups.sst, groups.test_prep, groups.sample_weight, groups.sw_stats, groups.ti_header, groups.time_intervals, groups.tpc_header, groups.timepoints_pct, groups.tpr_header, groups.timepoints_release, groups.remarks, groups.timepoints | empty 1, synth 1, ws 3, pad3 1 | 435 |
| TPL-A6A-0002 | 22 | 1 | Active | standard | db | none | convert | - | empty 1, synth 1, ws 1, pad3 1 | 228 |
| TPL-A6A-0003 | 23 | 1 | Active | standard | db | none | convert | - | empty 1, synth 1, pad3 1 | 435 |
| TPL-A6A-0004 | 34 | 1 | Active | standard | db | none | convert | - | empty 1, synth 1, ws 1, pad3 1 | 510 |
| TPL-A6A-0005 | 44 | 3 | Active | standard | inline | equal | convert | - | empty 1, synth 1, pad3 1 | 165 |
| TPL-A6B-0001 | 7 | 1 | Active | standard | inline | equal | convert | - | empty 1, synth 1, ws 3, pad3 1 | 255 |
| TPL-A6B-0002 | 37 | 1 | Active | standard | inline | equal | convert | - | empty 1, synth 1, ws 1, pad3 1 | 76 |
| TPL-A6C-0001 | 8 | 1 | Active | standard | helper | drifted | convert | context | empty 1, synth 1, ws 1, pad3 1 | 22 |
| TPL-A8-0001 | 24 | 2 | Active | standard | helper | drifted | convert | context, criteria, groups.additional_info, groups.standard, groups.std_prep_procedure, groups.sample_dil, groups.test_prep_procedure, groups.std_areas, groups.stats, groups.units, groups.summary | empty 1, synth 1, ws 1, pad3 1 | 46 |
| TPL-A8-0003 | 21 | 1 | Draft | standard | db | none | convert | - | empty 1, synth 1, pad3 1 | 21 |
| TPL-A8-0004 | 38 | 1 | Active | standard | helper | equal | convert | - | empty 1, synth 1, ws 1, pad3 1 | 48 |
| TPL-A12-0001 | 30 | 1 | Active | standard | helper | drifted | convert | context, groups.bkt_1_header, groups.bkt_1, groups.bkt_2_header, groups.bkt_2, groups.stats, groups.preps | empty 1, synth 1, ws 1, pad3 1 | 43 |
| TPL-A13-0001 | 14 | 1 | Active | standard | helper | drifted | convert | context | empty 1, synth 1, ws 1, pad3 1 | 11 |
| TPL-H1-0001 | 16 | 1 | Active | standard, standard_2 | db | none | convert | - | empty 1, synth 1, ws 1, pad3 1 | 40 |
| TPL-H1-0002 | 20 | 1 | Active | standard, standard_2 | db | none | convert | - | empty 1, synth 1, ws 1, pad3 1 | 62 |
| TPL-NITRO-0001 | 51 | 1 | Active | standard | inline | equal | convert | - | empty 1, synth 1, ws 1, pad3 1 | 53 |

## Final live-DB outcome (after `--apply`, 2026-11-05 18:04:45 UTC, worktree HEAD 20e7da5a364917f119f42e41b66dde73acc04edd)

Every row below was updated in place: `definition`, `modified_by` (`std-details-rollout`) and `modified_date` changed; id, code, name, archetype, test_id, version, status, result_unit, approval and supersession columns are identical to the backup. Each listed group is now `kind: table`, `rows {min 1, max 10, default 1}`, `rowLabel {format "STD - {n}"}`. Outside the listed groups every definition key and group is identical to the backup (A4-0004 `standard` additionally lost the dead `renderAsTable` key).

| Template | Ver / status (unchanged) | Live outcome | Stored definition vs module |
|---|---|---|---|
| TPL-A1-0001 | 1 Active | converted: standard | byte-equal to module |
| TPL-A1-0002 | 1 Active | converted (DB-only): standard | no module |
| TPL-A1-0003 | 1 Active | converted: standard | byte-equal |
| TPL-A2-0001 | 1 Active | converted: standard | drifted elsewhere (context); standard matches module |
| TPL-A2-0003 | 1 Active | converted: standard | drifted elsewhere (std_injections, bkt_injections); standard matches |
| TPL-A2-0006 | 1 Active | converted: standard | byte-equal |
| TPL-A3-0001 | 1 Active | converted: standard | drifted elsewhere; standard matches |
| TPL-A4-0001 | 1 Active | converted: standard and standard_2 | byte-equal |
| TPL-A4-0004 | 1 Active | converted: standard (renderAsTable dropped) | drifted elsewhere (unknowns_header, unknowns); standard matches |
| TPL-A6A-0001 | 1 Active | converted: standard | drifted elsewhere (incl. standard field labels / rounding kept as in live DB); kind/rows/rowLabel match |
| TPL-A6A-0002 | 1 Active | converted (DB-only): standard | no module |
| TPL-A6A-0003 | 1 Active | converted (DB-only): standard | no module |
| TPL-A6A-0004 | 1 Active | converted (DB-only): standard | no module |
| TPL-A6A-0005 | 3 Active | converted: standard | byte-equal |
| TPL-A6B-0001 | 1 Active | converted: standard | byte-equal |
| TPL-A6B-0002 | 1 Active | converted: standard | byte-equal |
| TPL-A6C-0001 | 1 Active | converted: standard | drifted elsewhere (context); standard matches |
| TPL-A8-0001 | 2 Active | converted: standard | drifted elsewhere; kind/rows/rowLabel match |
| TPL-A8-0003 | 1 Draft | converted (DB-only, still Draft): standard | no module |
| TPL-A8-0004 | 1 Active | converted: standard | byte-equal |
| TPL-A12-0001 | 1 Active | converted: standard | drifted elsewhere; standard matches |
| TPL-A13-0001 | 1 Active | converted: standard | drifted elsewhere (context); standard matches |
| TPL-H1-0001 | 1 Active | converted (DB-only): standard and standard_2 | no module |
| TPL-H1-0002 | 1 Active | converted (DB-only): standard and standard_2 | no module |
| TPL-NITRO-0001 | 1 Active | converted: standard | byte-equal |

Totals: 25 rows, 28 groups (25 `standard` + 3 `standard_2`); 9 byte-equal to module, 9 drifted elsewhere (drift reported, not fixed), 7 DB-only.

### Not changed in the live DB (32 rows, all column-identical to the backup)

| Template | Reason |
|---|---|
| TPL-A2-0002 | already tabular (converted earlier by the reference work; re-verified: `standard` is a table) |
| TPL-A2-0004, TPL-A2-0005, TPL-A11-0001, TPL-A11-0002 | already tabular `standard` |
| TPL-A4-0002 v3, TPL-A4-0003 | already tabular (`standards` / `std_preps`) |
| TPL-A11-0001 v2, A11-0002 v2, A11-0003 v2 (Draft) | no singleton `standard` / `standard_2` |
| TPL-A4-0002 v1/v2 (Superseded), TPL-A6A-0005 v1/v2 (Inactive), TPL-A8-0001 v1 (Inactive) | superseded history, worksheets still bound; not touched |
| TPL-A5-0001..0004, A6D-0001, A6D-0002, A7-0001, A7-0002, A8-0002, A9-0001, A9-0002, A10-0001, A10-0002, A11-0003, A12-0002, A12-0003 | no standard section |
| TPL-A14-0001 | only a `std` Linearity Standard Stock Solution (stock, not a weighed-standard section); possible follow-up |

