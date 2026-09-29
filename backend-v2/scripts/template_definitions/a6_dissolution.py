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
#  A6b — with replacement: volume constant, carry-over still applies
# ─────────────────────────────────────────────────────────────────────

A6B_DEFINITION = {
    "resultRef": "timepoints.mean_released",
    "context": _dissolution_context(750),
    "groups": [
        *_standard_groups(),
        _timepoint_group(
            #  Replacement restores the withdrawn volume, so the series is flat.
            #  Written as an expression rather than a constant so the derivation
            #  stays visible and an unequal replacement volume is a one-field edit.
            volume_expression="initial_volume",
            #  The correction is still needed: replacing the medium removes
            #  dissolved drug along with the aliquot.
            with_carryover=True,
        ),
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
