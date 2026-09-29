"""
Seed template definitions, one module per archetype family.

All fourteen archetypes are now covered. The last two — f1/f2 profile comparison
(A7) and the cross-test roll-ups (A12) — had been held back pending lab
confirmation; both questions turned out to be answerable from the workbooks
themselves:

* A7's arithmetic **is** in its sheet, spelled out one step per cell off to the
  right of the printed area, and it is the FDA/EMA convention. What the sheet gets
  wrong is its `R(t)`/`T(t)` column headings, which are swapped relative to the
  data feeding them — the numbers are right.
* A12's "double normalisation" is a one-column reference slip in two entrapment
  cells, which substitute an already-normalised quantity for its measured partner.
  Correcting it makes both cells reconcile with `free + entrapped = whole`.

Each module's docstring carries the reasoning and what was deliberately not
reproduced. Two items still need a lab decision rather than blocking anything:
f1/f2 rounding, and A12's carried-over results, which are transcribed inputs today
because the engine cannot yet reference another test's released result.

Each entry is a `SeedTemplate`: the template plus the Test Master entry it needs,
so seeding is self-contained rather than depending on a particular Test already
existing.
"""
from scripts.template_definitions._common import SeedTemplate
from scripts.template_definitions.a1_assay import TEMPLATES as _A1
from scripts.template_definitions.a2_a3_content import TEMPLATES as _A2_A3
from scripts.template_definitions.a4_a5_related_substances import TEMPLATES as _A4_A5
from scripts.template_definitions.a6_dissolution import TEMPLATES as _A6
from scripts.template_definitions.a6d_franz_ivrt import TEMPLATES as _A6D
from scripts.template_definitions.a7_profile_comparison import TEMPLATES as _A7
from scripts.template_definitions.a8_content_uniformity import TEMPLATES as _A8
from scripts.template_definitions.a9_a10_a13_classical import TEMPLATES as _A9_A10_A13
from scripts.template_definitions.a11_microbial_bioassay import TEMPLATES as _A11
from scripts.template_definitions.a12_derived_rollups import TEMPLATES as _A12
from scripts.template_definitions.a14_linearity import TEMPLATES as _A14

#  Ordered by archetype so the seed log reads predictably.
SEED_TEMPLATES: list[SeedTemplate] = [
    *_A1,
    *_A2_A3,
    *_A4_A5,
    *_A6,
    *_A6D,
    *_A7,
    *_A8,
    *_A9_A10_A13,
    *_A11,
    *_A12,
    *_A14,
]

__all__ = ["SEED_TEMPLATES", "SeedTemplate"]
