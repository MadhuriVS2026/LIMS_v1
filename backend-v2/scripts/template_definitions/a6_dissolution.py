"""
A6 — dissolution, three variants.

The structural problem here: release has to be tracked **per unit across
timepoints**, because each vessel must independently meet Q. That makes it a
2-D grid, and the schema has only 1-D groups. Timepoints must be the row axis,
because the carry-over correction is recursive over *earlier timepoints* — so
units become columns, generated per vessel.

Hence the field lists below are built by a loop. The output is still plain data;
the loop only keeps 6 near-identical column definitions out of the source.

Two things the source sheets get right and a naive implementation gets wrong:

* **The media volume series is derived, not stored.** The sheets hard-code
  `500/495/490/485…`. Here the template declares
  `{initial_volume, withdrawal_volume}` and the series comes from `rowno`, so
  changing the withdrawal volume cannot leave a stale constant behind.
* **Release is cumulative.** `release[t] = uncorrected[t] + Σ corrections[1..t-1]`,
  which is what `sum(prior.correction_n)` expresses. Sequence groups exist for
  precisely this.

Source-sync note (TPL-A6A-0004 / "Dissolution_12units"):
    The active 12-unit template TPL-A6A-0004 (test_templates.id=34) is NOT produced
    by this module. It uses a different 12-unit structure and field names
    (`unit_1..12`, `uncorrected_N`, `correction_N`, group key `timepoints_release`),
    and lives DB-only. Its corrected `timepoints_release` formulas — reproducing the
    Bupivacaine sheet — are the authoritative reference and are pinned by
    `tests/calculation/test_dissolution_a6a_release.py`. Regenerating the -0001/-A6B/
    -A6C variants below does NOT touch -0004; do not retrofit -0004 here (that would be
    a new template version and could overwrite the live row on reseed).
"""
from scripts.template_definitions._common import (
    SeedTemplate,
    context_header,
    dilution_fields,
    replicate_area_group,
    standard_chain_terms,
    standard_group,
    standard_statistics_group,
    sst_rsd_criterion,
)

#  Six vessels — the USP default apparatus size. A 12-unit study is a new
#  template version, which is the right GxP outcome.
_UNITS = 6
_UNIT_RANGE = range(1, _UNITS + 1)


def _released_keys() -> list[str]:
    return [f"released_{n}" for n in _UNIT_RANGE]


def _unit_area_fields() -> list[dict]:
    return [
        {
            "key": f"area_{n}",
            "kind": "area",
            "label": f"Unit {n} Area",
            "unit": "µV·s",
        }
        for n in _UNIT_RANGE
    ]


def _uncorrected_expression(volume_ref: str) -> str:
    """
    Amount released at this timepoint, ignoring what was withdrawn earlier.

    The standard chain converts area to concentration; multiplying by the media
    volume gives the mass in the vessel, and dividing by label claim gives a
    percentage.
    """
    return (
        "area_{n} / stats.mean_std "
        f"* {standard_chain_terms()} "
        "* standard.potency / 100 "
        f"* {volume_ref} / label_claim * 100"
    )


def _unit_calculated_fields(*, volume_ref: str, with_carryover: bool) -> list[dict]:
    """Per-unit uncorrected value, carry-over correction, and cumulative release."""
    fields: list[dict] = []
    template = _uncorrected_expression(volume_ref)

    for n in _UNIT_RANGE:
        fields.append(
            {
                "key": f"uncorrected_{n}",
                "kind": "calculated",
                "label": f"Unit {n} (uncorrected)",
                "unit": "%",
                "expression": template.format(n=n),
            }
        )

    if with_carryover:
        for n in _UNIT_RANGE:
            fields.append(
                {
                    "key": f"correction_{n}",
                    "kind": "calculated",
                    "label": f"Unit {n} carry-over",
                    "unit": "%",
                    #  Sheet C73: TRUNC(withdrawal / volume * uncorrected, 3).
                    #  Truncated, not rounded — the sheets use TRUNC here.
                    "expression": (
                        f"trunc(withdrawal_volume / {volume_ref} * uncorrected_{n}, 3)"
                    ),
                }
            )
        for n in _UNIT_RANGE:
            fields.append(
                {
                    "key": f"released_{n}",
                    "kind": "calculated",
                    "label": f"Unit {n} Released",
                    "unit": "%",
                    #  `prior` is the sequence-group window over earlier rows, so
                    #  this replaces the sheets' hard-coded `C73+D73+E73+…`.
                    "expression": f"uncorrected_{n} + sum(prior.correction_{n})",
                    "rounding": {"mode": "round", "digits": 1},
                }
            )
    else:
        for n in _UNIT_RANGE:
            fields.append(
                {
                    "key": f"released_{n}",
                    "kind": "calculated",
                    "label": f"Unit {n} Released",
                    "unit": "%",
                    "expression": f"uncorrected_{n}",
                    "rounding": {"mode": "round", "digits": 1},
                }
            )

    return fields


def _statistics_fields() -> list[dict]:
    released = "[" + ", ".join(_released_keys()) + "]"
    return [
        {
            "key": "mean_released",
            "kind": "calculated",
            "label": "Mean Released",
            "unit": "%",
            "expression": f"mean({released})",
            "rounding": {"mode": "round", "digits": 1},
        },
        {
            "key": "min_released",
            "kind": "calculated",
            "label": "Min",
            "unit": "%",
            "expression": f"min({released})",
        },
        {
            "key": "max_released",
            "kind": "calculated",
            "label": "Max",
            "unit": "%",
            "expression": f"max({released})",
        },
        {
            "key": "rsd_released",
            "kind": "calculated",
            "label": "%RSD",
            "unit": "%",
            "expression": f"rsd({released})",
            "rounding": {"mode": "round", "digits": 1},
        },
    ]


def _timepoint_group(*, volume_expression: str, with_carryover: bool) -> dict:
    return {
        "key": "timepoints",
        "kind": "sequence",
        "label": "Timepoints",
        "rows": {"min": 1, "max": 12, "default": 4, "labelFrom": "minutes"},
        "fields": [
            {
                "key": "minutes",
                "kind": "input",
                "type": "text",
                "label": "Timepoint",
                "required": True,
            },
            *_unit_area_fields(),
            {
                "key": "media_volume",
                "kind": "calculated",
                "label": "Media Volume",
                "unit": "mL",
                #  Derived from the row's position, so the series can never drift
                #  from the declared withdrawal volume.
                "expression": volume_expression,
            },
            *_unit_calculated_fields(volume_ref="media_volume", with_carryover=with_carryover),
            *_statistics_fields(),
        ],
    }


def _dissolution_context(initial_volume: float) -> list[dict]:
    return context_header(
        extra=[
            {
                "key": "medium",
                "kind": "context",
                "type": "text",
                "label": "Medium",
                "overridable": True,
            },
            {
                "key": "apparatus",
                "kind": "context",
                "type": "text",
                "label": "Apparatus",
                "overridable": True,
            },
            {
                "key": "rpm",
                "kind": "context",
                "label": "Speed",
                "unit": "rpm",
                "overridable": True,
            },
            {
                "key": "initial_volume",
                "kind": "context",
                "label": "Initial Media Volume",
                "unit": "mL",
                "default": initial_volume,
                "overridable": True,
            },
            {
                "key": "withdrawal_volume",
                "kind": "context",
                "label": "Withdrawal Volume",
                "unit": "mL",
                "default": 5,
                "overridable": True,
            },
        ]
    )


def _standard_groups() -> list[dict]:
    return [
        standard_group(conc_label="Standard Concentration"),
        replicate_area_group(default_rows=5),
        standard_statistics_group(),
    ]


# ─────────────────────────────────────────────────────────────────────
#  A6a — without replacement: volume shrinks, carry-over accumulates
# ─────────────────────────────────────────────────────────────────────

A6A_DEFINITION = {
    "resultRef": "timepoints.mean_released",
    "context": _dissolution_context(500),
    "groups": [
        *_standard_groups(),
        _timepoint_group(
            #  V[t] = V0 - (t-1) * withdrawal. Reproduces 500/495/490/485…
            volume_expression="initial_volume - (rowno - 1) * withdrawal_volume",
            with_carryover=True,
        ),
    ],
    "criteria": [sst_rsd_criterion()],
}

A6A = SeedTemplate(
    code="TPL-A6A-0001",
    name="Dissolution (without replacement)",
    archetype="A6a",
    result_unit="%",
    test_code="TST-DISS",
    test_name="Dissolution",
    test_type="Quantitative",
    definition=A6A_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A6b — with replacement, whole-vial, 12-unit QC release (Doxorubicin)
# ─────────────────────────────────────────────────────────────────────
#
#  Formula-exact rebuild of the workbook
#  `Test types/Dissolution sheet_with replacement_whole vial_ QC release_12
#  units_Doxo.xlsx`. This replaces the earlier generic 6-unit A6b skeleton — the
#  live template TPL-A6B-0001 must reproduce the Doxorubicin sheet exactly.
#
#  Carry-over (WITH replacement). The sheet's `% Content` table (rows 59-63)
#  computes each unit column cumulatively:
#      row 1 (B59):  base_n
#      row k (B60+): base_n + prev_content_n * M35/F35   (withdrawal / total vol)
#  where base_n is the full area-to-percent chain
#      B47/$H$16 * C13/E13 * G13/I13 * K13/M13 * F35/B43 * J35/H35
#            * P13/100 / B4 * F10 * 100
#  (no ROUND/TRUNC — content/release carry full precision on the sheet).
#  In the sequence engine the carry term MUST be coalesce(prev.content_n, 0): on
#  row 1 `prev` is empty and a bare prev.content_n would be EMPTY, propagating
#  through the multiply and blanking the whole column. coalesce(...,0) makes row 1
#  equal base_n, matching the sheet.
#
#  Naming reconciliation: the user brief calls rows 59-63 the "%RELEASE table" and
#  rows 67-71 the "AMOUNT-REMAINING table"; the SHEET's own titles are the reverse
#  ("% Content" for 59-63, "% Release" for 67-71). The gold values disambiguate —
#  Unit-1 0.5hr = 83.2069 is the row-59 value (brief "release"); 16.3931 = 99.6 -
#  83.2069 is the row-67 value (brief "amount remaining"). We use the brief's
#  semantics for group keys/labels: group `release` = the computed content
#  (83.2069…), group `amount` = %Assay minus release (16.3931…).

_A6B_UNITS = 12
_A6B_UNIT_RANGE = range(1, _A6B_UNITS + 1)

#  base_n — the uncorrected area-to-percent chain for unit n at the current row.
#  `sample_area.unit_{n}[rowno - 1]` reads this row's raw area from the sample-area
#  table (0-based index). Qualified refs reach the other singleton groups.
_A6B_BASE = (
    "sample_area.unit_{n}[rowno - 1] / stats.mean_std"
    " * standard.weight_mg / standard.vol_1"
    " * standard.pip_1 / standard.vol_2"
    " * standard.pip_2 / standard.vol_3"
    " * test_prep.total_volume / gravimetric.net_{n}"
    " * test_prep.dilution_volume / test_prep.aliquot_volume"
    " * standard.potency / 100 / number(label_claim)"
    " * wt_per_ml * 100"
)

#  content_n — cumulative with-replacement value (sheet B59..B63).
_A6B_CONTENT = (
    "base_{n} + coalesce(prev.content_{n}, 0)"
    " * test_prep.withdrawal_volume / test_prep.total_volume"
)


def _a6b_units_list(field: str) -> str:
    return "[" + ", ".join(f"{field}_{n}" for n in _A6B_UNIT_RANGE) + "]"


def _a6b_summary_fields(field: str) -> list[dict]:
    """Per-timepoint Mean/SD/%RSD/Min/Max over the 12 visible unit columns."""
    units = _a6b_units_list(field)
    return [
        {"key": "mean", "kind": "calculated", "label": "Mean", "unit": "%",
         "expression": f"mean({units})"},
        {"key": "sd", "kind": "calculated", "label": "SD", "unit": "%",
         "expression": f"sd({units})"},
        {"key": "rsd", "kind": "calculated", "label": "%RSD", "unit": "%",
         "expression": f"rsd({units})"},
        {"key": "min_val", "kind": "calculated", "label": "Min.", "unit": "%",
         "expression": f"min({units})"},
        {"key": "max_val", "kind": "calculated", "label": "Max.", "unit": "%",
         "expression": f"max({units})"},
    ]


def _a6b_context() -> list[dict]:
    return [
        {"key": "generic_name", "kind": "context", "type": "text",
         "label": "Product", "source": "product.name"},
        {"key": "batch_no", "kind": "context", "type": "text",
         "label": "Batch No.", "source": "trf.batch_number"},
        #  label_claim (B4) is a divisor; source from the TRF only when numeric,
        #  default to the sheet's 2 mg/mL, and keep overridable. number(label_claim)
        #  guards the free-text case in the chain.
        {"key": "label_claim", "kind": "context", "type": "number",
         "label": "Label Claim", "unit": "mg/mL", "source": "trf.label_claim_numeric",
         "default": 2, "overridable": True},
        {"key": "pct_assay", "kind": "context", "label": "% Assay",
         "unit": "%", "default": 99.6, "overridable": True},
        {"key": "wt_per_ml", "kind": "context", "label": "Wt./mL",
         "default": 1.0313, "overridable": True},
        {"key": "trf_no", "kind": "context", "type": "text",
         "label": "TRF No.", "source": "trf.trf_number", "overridable": True},
        {"key": "ar_no", "kind": "context", "type": "text",
         "label": "A.R. No.", "source": "trf.ar_number", "overridable": True},
        {"key": "date_of_analysis", "kind": "context", "type": "date",
         "label": "Date of Analysis", "source": "session.date", "overridable": True},
        #  Display-only header text (not in any formula); overridable so each is
        #  fillable and passes test_no_context_field_is_unfillable.
        {"key": "strength", "kind": "context", "type": "text",
         "label": "Strength", "overridable": True},
        {"key": "test_performed", "kind": "context", "type": "text",
         "label": "Test Performed", "overridable": True},
        {"key": "media", "kind": "context", "type": "text",
         "label": "Disso Media", "overridable": True},
        {"key": "apparatus", "kind": "context", "type": "text",
         "label": "Apparatus", "overridable": True},
        {"key": "rpm", "kind": "context", "label": "RPM", "unit": "rpm",
         "overridable": True},
        {"key": "temperature", "kind": "context", "type": "text",
         "label": "Temperature (°C)", "overridable": True},
        {"key": "lnb_no", "kind": "context", "type": "text",
         "label": "LNB No.", "overridable": True},
        {"key": "disso_id", "kind": "context", "type": "text",
         "label": "DISSO ID", "overridable": True},
        {"key": "hplc_id", "kind": "context", "type": "text",
         "label": "HPLC ID", "overridable": True},
        {"key": "column_id", "kind": "context", "type": "text",
         "label": "Column ID", "overridable": True},
    ]


def _a6b_standard_group() -> dict:
    #  Standard prep — chain 100/5/50/5/10, potency 100 (sheet C13..P13).
    #  R13 Std Conc (ppm) = ROUND(C13/E13*G13/I13*K13/M13*P13/100*1000, 3).
    return {
        "key": "standard", "kind": "singleton", "label": "Standard Preparation",
        "fields": [
            {"key": "name", "kind": "input", "type": "text", "label": "Standard Name",
             "default": "Doxorubicin HCl WS"},
            {"key": "weight_mg", "kind": "input", "label": "Wt. in mg", "unit": "mg",
             "required": True, "default": 30.11},
            {"key": "vol_1", "kind": "input", "label": "Vol 1 (Water)", "unit": "mL",
             "default": 100},
            {"key": "pip_1", "kind": "input", "label": "Pip 1", "unit": "mL", "default": 5},
            {"key": "vol_2", "kind": "input", "label": "Vol 2 (Media)", "unit": "mL",
             "default": 50},
            {"key": "pip_2", "kind": "input", "label": "Pip 2", "unit": "mL", "default": 5},
            {"key": "vol_3", "kind": "input", "label": "Vol 3 (MeOH)", "unit": "mL",
             "default": 10},
            {"key": "potency", "kind": "input", "label": "%Potency", "unit": "%",
             "default": 100},
            {"key": "conc_ppm", "kind": "calculated", "label": "Concen. (ppm)",
             "unit": "ppm",
             "expression": "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3"
                           " * potency / 100 * 1000",
             "rounding": {"mode": "round", "digits": 3}},
        ],
    }


def _a6b_corel_group() -> dict:
    #  STD-1 / STD-2 co-relation block (sheet L19/L20, O19..O24, P19..P25).
    #  STD Co-Relation = O24/P24 * L20/L19.
    return {
        "key": "corel", "kind": "singleton", "label": "STD-1 / STD-2 Co-Relation",
        "fields": [
            {"key": "std1_weight", "kind": "input", "label": "STD-1 Weight", "unit": "mg",
             "default": 30.11},
            {"key": "std2_weight", "kind": "input", "label": "STD-2 Weight", "unit": "mg",
             "default": 30.02},
            {"key": "std1_mean", "kind": "calculated", "label": "STD-1 Mean Area",
             "expression": "mean(corel_std1.area)"},
            {"key": "std2_mean", "kind": "calculated", "label": "STD-2 Mean Area",
             "expression": "mean(corel_std2.area)"},
            {"key": "co_relation", "kind": "calculated", "label": "STD Co-Relation",
             "expression": "std1_mean / std2_mean * std2_weight / std1_weight"},
        ],
    }


def _a6b_gravimetric_group() -> dict:
    #  Sample weights, units-as-columns (sheet rows 41-43). Net = Filled - Empty.
    #  Summary over the 12 net weights.
    fields: list[dict] = []
    for n in _A6B_UNIT_RANGE:
        fields.append({"key": f"filled_{n}", "kind": "input",
                       "label": f"Filled Wt. Unite-{n}", "unit": "g"})
    for n in _A6B_UNIT_RANGE:
        fields.append({"key": f"empty_{n}", "kind": "input",
                       "label": f"Empty Wt. Unite-{n}", "unit": "g"})
    for n in _A6B_UNIT_RANGE:
        fields.append({"key": f"net_{n}", "kind": "calculated",
                       "label": f"Net Wt. Unite-{n}", "unit": "g",
                       "expression": f"filled_{n} - empty_{n}"})
    nets = "[" + ", ".join(f"net_{n}" for n in _A6B_UNIT_RANGE) + "]"
    fields.extend([
        {"key": "net_mean", "kind": "calculated", "label": "Mean", "unit": "g",
         "expression": f"mean({nets})"},
        {"key": "net_min", "kind": "calculated", "label": "Min", "unit": "g",
         "expression": f"min({nets})"},
        {"key": "net_max", "kind": "calculated", "label": "Max", "unit": "g",
         "expression": f"max({nets})"},
    ])
    return {"key": "gravimetric", "kind": "singleton", "label": "Sample Weight",
            "fields": fields}


def _a6b_sample_area_group() -> dict:
    #  Raw sample areas: time as rows, 12 units as area columns (sheet rows 46-51).
    fields: list[dict] = [
        {"key": "time_hr", "kind": "input", "label": "Time Interval (Hours)",
         "required": True},
    ]
    for n in _A6B_UNIT_RANGE:
        fields.append({"key": f"unit_{n}", "kind": "area", "label": f"Unite-{n}",
                       "unit": "µV·s"})
    return {"key": "sample_area", "kind": "table", "label": "Sample Area",
            "rows": {"min": 1, "max": 20, "default": 5, "labelFrom": "time_hr"},
            "fields": fields}


def _a6b_release_group() -> dict:
    #  % Content table (brief "% Release"): cumulative with-replacement carry-over.
    fields: list[dict] = [
        {"key": "time_hr", "kind": "input", "label": "Time Interval (Hours)"},
    ]
    #  Hidden uncorrected base columns.
    for n in _A6B_UNIT_RANGE:
        fields.append({"key": f"base_{n}", "kind": "calculated", "hidden": True,
                       "expression": _A6B_BASE.format(n=n)})
    #  Visible cumulative content columns.
    for n in _A6B_UNIT_RANGE:
        fields.append({"key": f"content_{n}", "kind": "calculated",
                       "label": f"Unite-{n}", "unit": "%",
                       "expression": _A6B_CONTENT.format(n=n)})
    fields.extend(_a6b_summary_fields("content"))
    return {"key": "release", "kind": "sequence",
            "label": "% Content of Doxorubicin Hydrochloride",
            "rows": {"min": 1, "max": 20, "default": 5, "labelFrom": "time_hr"},
            "fields": fields}


def _a6b_amount_group() -> dict:
    #  % Release table (brief "amount remaining"): %Assay - release.content_n.
    fields: list[dict] = [
        {"key": "time_hr", "kind": "input", "label": "Time Interval (Hours)"},
    ]
    for n in _A6B_UNIT_RANGE:
        fields.append({"key": f"remain_{n}", "kind": "calculated",
                       "label": f"Unite-{n}", "unit": "%",
                       "expression": f"number(pct_assay) - release.content_{n}[rowno - 1]"})
    fields.extend(_a6b_summary_fields("remain"))
    return {"key": "amount", "kind": "table",
            "label": "% Release of Doxorubicin Hydrochloride",
            "rows": {"min": 1, "max": 20, "default": 5, "labelFrom": "time_hr"},
            "fields": fields}


def _a6b_chart_group() -> dict:
    series = [{"key": f"content_{n}", "label": f"Unit {n}"} for n in _A6B_UNIT_RANGE]
    series.append({"key": "mean", "label": "Mean"})
    return {
        "key": "release_chart", "kind": "singleton", "label": "Graphical data",
        "fields": [
            {"key": "note", "kind": "input", "type": "text", "label": "Note",
             "default": ""},
        ],
        "chart": {
            "title": "% Release vs Time",
            "sourceGroup": "release",
            "xField": "time_hr",
            "xLabel": "Time Interval (Hours)",
            "yLabel": "% Release",
            "series": series,
            "defaultSeries": ["mean"],
        },
    }


A6B_DEFINITION = {
    "resultRef": "release.mean",
    "context": _a6b_context(),
    "groups": [
        _a6b_standard_group(),
        #  5-replicate standard area table + Mean/%RSD (sheet C16..I16).
        {"key": "std_areas", "kind": "table", "label": "Area of Standard Injections",
         "rows": {"min": 1, "max": 6, "default": 5},
         "fields": [{"key": "area", "kind": "area", "label": "STD Area"}]},
        #  Up-to-24 bracketing standards (sheet rows 18-25). Pooled with the 5
        #  replicates for the bracketing mean/%RSD.
        {"key": "bkt", "kind": "table", "label": "Bracketing Std (Area)",
         "rows": {"min": 0, "max": 24, "default": 2},
         "fields": [{"key": "area", "kind": "area", "label": "BKT Area"}]},
        #  Co-relation STD-1 (3 injections) and STD-2 (2 injections).
        {"key": "corel_std1", "kind": "table", "label": "STD-1 Injections",
         "rows": {"min": 1, "max": 6, "default": 3},
         "fields": [{"key": "area", "kind": "area", "label": "STD-1 Area"}]},
        {"key": "corel_std2", "kind": "table", "label": "STD-2 Injections",
         "rows": {"min": 1, "max": 6, "default": 2},
         "fields": [{"key": "area", "kind": "area", "label": "STD-2 Area"}]},
        _a6b_corel_group(),
        #  Statistics: replicate Mean=AVERAGE, %RSD=TRUNC5; pooled bracketing
        #  Mean=TRUNC1, %RSD=TRUNC5 (sheet H16/I16, H19/I19).
        {"key": "stats", "kind": "singleton", "label": "Standard Statistics",
         "fields": [
             {"key": "mean_std", "kind": "calculated", "label": "Mean",
              "expression": "mean(std_areas.area)"},
             {"key": "rsd_std", "kind": "calculated", "label": "%RSD", "unit": "%",
              "expression": "sd(std_areas.area) / mean_std * 100",
              "rounding": {"mode": "trunc", "digits": 5}},
             {"key": "mean_bkt", "kind": "calculated", "label": "Bracketing Mean",
              "expression": "mean(pool(std_areas.area, bkt.area))",
              "rounding": {"mode": "trunc", "digits": 1}},
             {"key": "rsd_bkt", "kind": "calculated", "label": "Bracketing %RSD",
              "unit": "%",
              "expression": "sd(pool(std_areas.area, bkt.area)) / mean_bkt * 100",
              "rounding": {"mode": "trunc", "digits": 5}},
         ]},
        #  System Suitability: items 1-3 text, item 4 = replicate %RSD, item 5 =
        #  pooled %RSD (sheet rows 27-32).
        {"key": "sst", "kind": "singleton", "label": "System Suitability Criteria",
         "fields": [
             {"key": "item_1", "kind": "input", "type": "text",
              "label": "1. No interference peak from the Blank solution",
              "default": "Complies"},
             {"key": "item_2", "kind": "input", "type": "text",
              "label": "2. Tailing factor NMT 2.0", "default": "Complies"},
             {"key": "item_3", "kind": "input", "type": "text",
              "label": "3. Theoretical plates NLT 2000", "default": "Complies"},
             {"key": "item_4", "kind": "calculated", "unit": "%",
              "label": "4. %RSD of five replicate injections (NMT 2.0)",
              "expression": "stats.rsd_std"},
             {"key": "item_5", "kind": "calculated", "unit": "%",
              "label": "5. %RSD of bracketing + replicate injections (NMT 2.0)",
              "expression": "stats.rsd_bkt"},
         ]},
        #  Test preparation volumes (sheet row 35).
        {"key": "test_prep", "kind": "singleton", "label": "Test Preparation",
         "fields": [
             {"key": "sample_volume", "kind": "input", "label": "Sample Volume",
              "unit": "mL", "default": 1},
             {"key": "medium_volume", "kind": "input", "label": "Medium Volume",
              "unit": "mL", "default": 600},
             {"key": "total_volume", "kind": "input", "label": "Total Volume",
              "unit": "mL", "default": 610},
             {"key": "aliquot_volume", "kind": "input", "label": "Aliquot Volume",
              "unit": "mL", "default": 3},
             {"key": "dilution_volume", "kind": "input", "label": "Dilution Volume",
              "unit": "mL", "default": 6},
             {"key": "withdrawal_volume", "kind": "input", "label": "Withdrawal Volume",
              "unit": "mL", "default": 10},
             {"key": "replenishment_volume", "kind": "input",
              "label": "Replenishment Volume", "unit": "mL", "default": 10},
         ]},
        _a6b_gravimetric_group(),
        _a6b_sample_area_group(),
        _a6b_release_group(),
        _a6b_amount_group(),
        _a6b_chart_group(),
    ],
    "criteria": [sst_rsd_criterion()],
}

A6B = SeedTemplate(
    code="TPL-A6B-0001",
    name="Dissolution (with replacement)",
    archetype="A6b",
    result_unit="%",
    test_code="TST-DISSR",
    test_name="Dissolution (with media replacement)",
    test_type="Quantitative",
    definition=A6B_DEFINITION,
)


# ─────────────────────────────────────────────────────────────────────
#  A6c — whole-vial / residual: release inferred from what is left behind
# ─────────────────────────────────────────────────────────────────────

A6C_DEFINITION = {
    "resultRef": "units.mean_released",
    "context": context_header(
        extra=[
            {
                "key": "batch_assay",
                "kind": "context",
                "label": "Batch Assay",
                "unit": "%",
                "default": 100,
                "overridable": True,
            },
            {
                "key": "medium",
                "kind": "context",
                "type": "text",
                "label": "Medium",
                "overridable": True,
            },
        ]
    ),
    "groups": [
        *_standard_groups(),
        {
            "key": "units",
            "kind": "table",
            "label": "Units (bottle-rotating, per-unit weight)",
            "rows": {"min": 1, "max": 12, "default": 6},
            "fields": [
                {"key": "unit_ref", "kind": "input", "type": "text", "label": "Unit"},
                #  Each vial is weighed individually — the whole point of this
                #  variant is that a shared average weight would not be valid.
                {
                    "key": "unit_weight",
                    "kind": "input",
                    "label": "Unit Wt.",
                    "unit": "mg",
                    "required": True,
                },
                *dilution_fields("s_"),
                {"key": "area", "kind": "area", "label": "Residue Area", "unit": "µV·s"},
                {
                    "key": "residue_pct",
                    "kind": "calculated",
                    "label": "Residual Content",
                    "unit": "%",
                    "expression": (
                        f"area / stats.mean_std * {standard_chain_terms()} "
                        "* standard.potency / 100 "
                        "* s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 "
                        "* s_vol_1 / unit_weight "
                        "* avg_weight / label_claim * 100"
                    ),
                    "rounding": {"mode": "round", "digits": 1},
                },
                {
                    "key": "released",
                    "kind": "calculated",
                    "label": "Released",
                    "unit": "%",
                    #  Release is what is NOT left in the vial, expressed against
                    #  the batch's own assay rather than nominal label claim.
                    "expression": "(batch_assay - residue_pct) / batch_assay * 100",
                    "rounding": {"mode": "round", "digits": 1},
                },
                {
                    "key": "mean_released",
                    "kind": "calculated",
                    "label": "Mean Released",
                    "unit": "%",
                    "expression": "mean(units.released)",
                    "rounding": {"mode": "round", "digits": 1},
                },
            ],
        },
    ],
    "criteria": [
        sst_rsd_criterion(),
        {
            "key": "unit_spread",
            "label": "%RSD across units",
            "target": "rsd(units.released)",
            "operator": "lte",
            "limit": 10.0,
            "severity": "advisory",
            "limitText": "NMT 10.0 %",
        },
    ],
}

A6C = SeedTemplate(
    code="TPL-A6C-0001",
    name="Dissolution (whole vial, residual content)",
    archetype="A6c",
    result_unit="%",
    test_code="TST-DISSV",
    test_name="Dissolution (whole vial residual)",
    test_type="Quantitative",
    definition=A6C_DEFINITION,
)

TEMPLATES = [A6A, A6B, A6C]
