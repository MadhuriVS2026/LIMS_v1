"""
A7 (mirrored) — dissolution profile comparison (f1 / f2) laid out as two
side-by-side mirrored tables (Reference | Test).

This is TPL-A7-0002. It is a structural clone of TPL-A7-0001
(`a7_profile_comparison.py`): the f1/f2 arithmetic and the five validity criteria
are reused *verbatim* by importing and deep-copying the A7 building blocks, so the
numbers can never drift from the proven original. Read that module's docstring for
the derivation of f1/f2, the swapped R(t)/T(t) headings in the source sheet, and
why the similarity verdict is advisory while the four validity rules are blocking.

The mirrored timepoint presentation is intentionally limited to the comparison
data: timepoints are rendered by the frontend as two side-by-side tables (a
Reference table and a Test table) instead of one wide table. That layout is a
frontend custom render gated on `template_code === 'TPL-A7-0002'`; the backing
data model stays A7's single `timepoints` sequence group, so:

  * the f1/f2 + validity arithmetic is byte-for-byte identical (one row carries
    both products' means, so `abs(ref_mean - test_mean)` and `prior.`-based RSD
    logic keep working),
  * "same time-points for both products" stays structurally guaranteed (one
    `time`/`unit` per row — the two tables are two views of the SAME rows), and
  * mirroring the timepoint label + unit between the two tables is inherent, not
    bolted on — both tables read/write the same shared backing cell.

The mirrored timepoint group has one additive per-row `unit` text input (default
"Hr"), so the time unit can live per-timepoint-row and mirror together with the
label. It is display metadata only — no expression references it — so no
calculated field changes and parity with A7 on identical mean/RSD inputs is
exact. A separate dynamic `test_product` header is also present as Section 1;
its independently entered values never copy from the TRF, product context, or
mirrored timepoint data.
"""
import copy

from scripts.template_definitions import a7_profile_comparison as a7
from scripts.template_definitions._common import SeedTemplate

_MAX_TIMEPOINTS = a7._MAX_TIMEPOINTS


def _timepoint_fields_mirrored() -> list[dict]:
    """A7's timepoint fields verbatim, plus one per-row `unit` text input.

    Deep-copied from `a7._timepoint_fields()` so every calculated expression
    (`abs_diff`, `sq_diff`, `ref_in_scope`, `ref_over_85`, `test_over_85`,
    `worst_rsd`, `has_rsd`, `rsd_limit`, `rsd_breach`) and every input (`time`,
    `included`, `ref_mean`, `ref_rsd`, `test_mean`, `test_rsd`) is the literal
    same string. The new `unit` input is inserted right after `time` so the two
    mirror-together inputs are adjacent; it is NOT referenced by any expression.
    """
    fields = copy.deepcopy(a7._timepoint_fields())
    unit_field = {
        "key": "unit",
        "kind": "input",
        "type": "text",
        "label": "Unit",
        #  Sourced from the profile-level `time_unit` context default.
        "default": "Hr",
    }
    #  Insert immediately after `time` (index 0) so label + unit sit together.
    time_index = next((i for i, f in enumerate(fields) if f["key"] == "time"), 0)
    fields.insert(time_index + 1, unit_field)
    return fields


_TIMEPOINTS_GROUP_MIRRORED = copy.deepcopy(a7._TIMEPOINTS_GROUP)
_TIMEPOINTS_GROUP_MIRRORED["label"] = (
    "Mean % Dissolved by Time Point (Reference | Test)"
)
_TIMEPOINTS_GROUP_MIRRORED["fields"] = _timepoint_fields_mirrored()


#  This is a worksheet-specific header, not the TRF/product-backed context.
#  Every value starts blank and remains independently editable for each created
#  worksheet. In particular, do not add `source`, `mirrorFrom`, or `default`
#  metadata here: the section must never copy values from a TRF or the mirrored
#  Reference/Test timepoint data.
_TEST_PRODUCT_GROUP = {
    "key": "test_product",
    "kind": "singleton",
    "label": "Section 1: Test Product",
    "fields": [
        {
            "key": "product_name",
            "kind": "input",
            "type": "text",
            "label": "Product Name",
        },
        {
            "key": "batch_no",
            "kind": "input",
            "type": "text",
            "label": "Batch No.",
        },
        {
            "key": "date_of_analysis",
            "kind": "input",
            "type": "date",
            "label": "Date of Analysis",
        },
        {
            "key": "media",
            "kind": "input",
            "type": "text",
            "label": "Media",
        },
        {
            "key": "rpm",
            "kind": "input",
            "type": "number",
            "label": "RPM",
        },
        {
            "key": "volume",
            "kind": "input",
            "type": "number",
            "label": "Volume",
        },
    ],
}


A7M_DEFINITION = copy.deepcopy(a7.A7_DEFINITION)
#  The Test Product header is entered independently for each worksheet. Keep
#  this Context field separate from both the Test Product singleton and the TRF
#  so creating a worksheet never copies a batch number into it.
A7M_DEFINITION["context"].append(
    {
        "key": "test_product_batch",
        "kind": "context",
        "type": "text",
        "label": "Test Product Batch No.",
        "overridable": True,
    }
)
#  resultRef unchanged: f2 is still the number the comparison turns on.
A7M_DEFINITION["groups"] = [
    _TEST_PRODUCT_GROUP,
    _TIMEPOINTS_GROUP_MIRRORED,
    copy.deepcopy(a7._COMPARISON_GROUP),
]
#  Context + criteria are inherited verbatim via the deepcopy above.


A7M = SeedTemplate(
    code="TPL-A7-0002",
    name="Dissolution Profile Comparison (f1 / f2) — Mirrored",
    archetype="A7",
    #  Dimensionless, like A7: f2 is a similarity factor on a 0–100 scale.
    result_unit=None,
    test_code="TST-F1F2M",
    test_name="Dissolution Profile Comparison (f1 / f2) — Mirrored",
    test_type="Quantitative",
    definition=A7M_DEFINITION,
)

TEMPLATES = [A7M]
