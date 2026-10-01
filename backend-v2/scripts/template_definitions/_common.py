"""
Shared building blocks for archetype template definitions.

These helpers exist because Decision 7 held up: the `Vol/Pip`, `Dilution-n/
Volume-n`, `Pipette/mL` and `V.F./Dil.` column variants across all 35 workbooks
are the same algebra. Expressing that once here means a new template declares
*which* stages it uses rather than restating the arithmetic, and a fix to the
chain cannot be applied to some templates and missed in others.

Definitions are plain JSON-shaped dicts. They are built by code only to keep the
repetition out of the source files — the output is data, and it is what gets
stored, versioned and e-signed.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SeedTemplate:
    """One template to seed, plus the Test Master entry it needs."""

    code: str
    name: str
    archetype: str
    result_unit: str | None
    #  The Test this template computes. Created in the Test Master if absent —
    #  a template bound to a Test that does not exist can never be selected.
    test_code: str
    test_name: str
    test_type: str
    definition: dict[str, Any]


# ── Context blocks ───────────────────────────────────────────────────


def context_header(
    *,
    label_claim: bool = True,
    avg_weight: bool = True,
    extra: list[dict] | None = None,
) -> list[dict]:
    """
    The context fields nearly every sheet carries.

    `label_claim` is entered rather than sourced from `trf.label_claim`: that
    column is free text ("50 mg/vial") and this field is a divisor, so feeding a
    string into the arithmetic would blank the whole chain.

    Every field here either resolves from a source or is `overridable` — a
    context field with neither, and no default, would render as a permanently
    blank read-only box.
    """
    fields: list[dict] = [
        {
            "key": "generic_name",
            "kind": "context",
            "type": "text",
            "label": "Generic Name",
            "source": "product.name",
        },
        {
            "key": "batch_no",
            "kind": "context",
            "type": "text",
            "label": "Batch No.",
            "source": "trf.batch_number",
        },
    ]
    if label_claim:
        fields.append(
            {
                "key": "label_claim",
                "kind": "context",
                "type": "number",
                "label": "Label Claim",
                #  Auto-filled from the TRF only when its Label Claim is numeric;
                #  otherwise this stays blank for manual entry. It is a divisor in
                #  the assay formula, so a free-text TRF value ("LC-0072e76") must
                #  not flow in. Remains overridable either way.
                "source": "trf.label_claim_numeric",
                "overridable": True,
            }
        )
    if avg_weight:
        fields.append(
            {
                "key": "avg_weight",
                "kind": "context",
                "label": "Average Weight / Vial",
                "default": 1,
                "overridable": True,
            }
        )
    fields.extend(extra or [])
    fields.extend(
        [
            {
                "key": "method_no",
                "kind": "context",
                "type": "text",
                "label": "Method No.",
                "overridable": True,
            },
            {
                "key": "instrument_id",
                "kind": "context",
                "type": "text",
                "label": "Instrument ID",
                "overridable": True,
            },
            {
                "key": "analysed_by",
                "kind": "context",
                "type": "text",
                "label": "Analysed By",
                "source": "session.analyst",
            },
            {
                "key": "date_of_analysis",
                "kind": "context",
                "type": "date",
                "label": "Date of Analysis",
                "source": "session.date",
            },
        ]
    )
    return fields


# ── Dilution chains ─────────────────────────────────────────────────

#  Three stages cover every sheet examined. Unused stages sit at a neutral 1/1,
#  which is why the defaults are 1 rather than required.
_CHAIN_STAGES = 3


def dilution_fields(prefix: str = "", *, first_required: bool = True) -> list[dict]:
    """`vol_n` / `pip_n` input pairs for a three-stage dilution chain."""
    fields: list[dict] = []
    for stage in range(1, _CHAIN_STAGES + 1):
        fields.append(
            {
                "key": f"{prefix}vol_{stage}",
                "kind": "input",
                "label": f"Vol {stage}",
                "unit": "mL",
                **({"required": True} if stage == 1 and first_required else {"default": 1}),
            }
        )
        if stage < _CHAIN_STAGES:
            fields.append(
                {
                    "key": f"{prefix}pip_{stage}",
                    "kind": "input",
                    "label": f"Pip {stage}",
                    "unit": "mL",
                    "default": 1,
                }
            )
    return fields


def dilution_factor(prefix: str = "") -> str:
    """
    The *concentration* direction of the chain: aliquot ÷ diluted-to per stage.

    Used for a standard: `weight / vol_1 * pip_1 / vol_2 * pip_2 / vol_3`.
    """
    return (
        f"{prefix}vol_1 * {prefix}pip_1 / {prefix}vol_2 "
        f"* {prefix}pip_2 / {prefix}vol_3"
    ).replace("vol_1 *", "vol_1 *", 1)


def standard_chain_terms(group: str = "standard") -> str:
    """
    The standard's contribution to a sample result, as it appears in the sheets:
    `weight / vol_1 * pip_1 / vol_2 * pip_2 / vol_3`.
    """
    return (
        f"{group}.weight_mg / {group}.vol_1 * {group}.pip_1 / {group}.vol_2 "
        f"* {group}.pip_2 / {group}.vol_3"
    )


def sample_chain_terms(prefix: str = "s_", group: str | None = None) -> str:
    """
    The sample's contribution, which is the chain *inverted* — the sheets write
    it as `vol_2/pip_1 * vol_3/pip_2 * vol_1/weight`, i.e. multiplying back up
    from the injected concentration to the amount in the original sample.

    `group` qualifies every term when the preparation fields live in a *different*
    group from the field being calculated. Bare names only resolve within the
    current row, so an unqualified reference from another group silently evaluates
    to blank and takes the whole result with it.
    """
    q = f"{group}." if group else ""
    return (
        f"{q}{prefix}vol_2 / {q}{prefix}pip_1 * {q}{prefix}vol_3 / {q}{prefix}pip_2 "
        f"* {q}{prefix}vol_1 / {q}sample_weight"
    )


# ── Standard blocks ─────────────────────────────────────────────────


def standard_group(
    *,
    key: str = "standard",
    label: str = "Standard Details",
    with_mw: bool = True,
    conc_label: str = "Concentration",
) -> dict:
    """
    The weighed-standard block: weight, dilution chain, potency, optional
    salt/base molecular-weight correction, and the resulting concentration.
    """
    fields: list[dict] = [
        {"key": "name", "kind": "input", "type": "text", "label": "Standard Name"},
        {"key": "weight_mg", "kind": "input", "label": "Weight", "unit": "mg", "required": True},
        *dilution_fields(),
    ]
    if with_mw:
        fields.extend(
            [
                {"key": "mw_base", "kind": "input", "label": "MW — Base", "default": 1},
                {"key": "mw_salt", "kind": "input", "label": "MW — Salt", "default": 1},
            ]
        )
    fields.append(
        {"key": "potency", "kind": "input", "label": "Potency", "unit": "%", "default": 100}
    )

    mw_term = " * mw_base / mw_salt" if with_mw else ""
    fields.append(
        {
            "key": "conc_ppm",
            "kind": "calculated",
            "label": conc_label,
            "unit": "ppm",
            "expression": (
                "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3"
                f"{mw_term} * potency / 100 * 1000"
            ),
        }
    )
    return {"key": key, "kind": "singleton", "label": label, "fields": fields}


def replicate_area_group(
    *,
    key: str = "std_areas",
    label: str = "Standard Replicate Injections",
    default_rows: int = 5,
    max_rows: int = 6,
    stats_group: str | None = "stats",
) -> dict:
    """
    The replicate-injection table. When paired with `standard_statistics_group`
    (the usual case), it also carries a compact Mean/SD/%RSD footer that renders
    directly beneath the table — the same numbers as the statistics section,
    shown inline where the analyst enters the areas.

    `stats_group=None` omits the footer, for the rare template that has no
    matching statistics group.
    """
    group: dict = {
        "key": key,
        "kind": "table",
        "label": label,
        "rows": {"min": 1, "max": max_rows, "default": default_rows},
        "fields": [{"key": "area", "kind": "area", "label": "STD Area"}],
    }
    if stats_group:
        group["footer"] = [
            {"label": "Mean", "ref": f"{stats_group}.mean_std"},
            {"label": "SD", "ref": f"{stats_group}.sd_std"},
            {"label": "% RSD", "ref": f"{stats_group}.rsd_std", "unit": "%"},
        ]
    return group


def standard_statistics_group(source: str = "std_areas") -> dict:
    """Mean / SD / %RSD over the standard replicates."""
    return {
        "key": "stats",
        "kind": "singleton",
        "label": "Standard Statistics",
        "fields": [
            {
                "key": "mean_std",
                "kind": "calculated",
                "label": "Mean STD Area",
                "expression": f"mean({source}.area)",
            },
            {
                "key": "sd_std",
                "kind": "calculated",
                "label": "SD",
                "expression": f"sd({source}.area)",
            },
            {
                "key": "rsd_std",
                "kind": "calculated",
                "label": "%RSD",
                "unit": "%",
                "expression": f"rsd({source}.area)",
            },
        ],
    }


def sst_rsd_criterion(target: str = "stats.rsd_std", limit: float = 2.0) -> dict:
    return {
        "key": "sst_std_rsd",
        "label": "%RSD of standard replicate injections",
        "target": target,
        "operator": "lte",
        "limit": limit,
        "severity": "blocking",
        "limitText": f"NMT {limit} %",
    }
