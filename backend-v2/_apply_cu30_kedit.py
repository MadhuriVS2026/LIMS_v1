"""Validate K is an editable Additional Info input driving the AV; sync DB row."""
import asyncio
import json
import statistics

from sqlalchemy import select

from scripts.template_definitions.a8_cu_tablets_30units import TEMPLATES
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition
from src.infrastructure.database.models.test_template_model import TestTemplateModel
from src.infrastructure.database.session import async_session_factory

CODE = "TPL-A8-0004"


async def main() -> None:
    seed = next(t for t in TEMPLATES if t.code == CODE)
    d = seed.definition
    parsed = TemplateDefinition.parse(d)
    WorksheetEvaluator(parsed).evaluate({}, {})

    # No context k_value; Additional Info has editable k_value input (default 2.4).
    assert not any(c["key"] == "k_value" for c in d["context"])
    ai = next(g for g in d["groups"] if g["key"] == "additional_info")
    k = next(f for f in ai["fields"] if f["key"] == "k_value")
    assert k["kind"] == "input" and k["default"] == 2.4, k
    # AV expression now references additional_info.k_value.
    summary = next(g for g in d["groups"] if g["key"] == "summary")
    av = next(f for f in summary["fields"] if f["key"] == "acceptance_value")
    assert "additional_info.k_value" in av["expression"], av["expression"]
    print("module OK: editable Additional Info K drives AV; no context k_value")

    # Prove editing K changes AV. User values, mean 102.4 (>101.5): AV=(102.4-101.5)+k*s.
    CU = [102.8, 99.5, 104.8]
    STD = {"weight_mg": 1, "vol_1": 1, "pip_1": 1, "vol_2": 1, "pip_2": 1,
           "vol_3": 1, "mw_base": 1, "mw_salt": 1, "potency": 100}
    SD = {"sample_unit": "1 Tablet", "sample_dilution": 1, "s_vol_1": 1,
          "s_pip_1": 1, "s_vol_2": 1, "s_pip_2": 1, "s_vol_3": 1}
    X = round(statistics.mean(CU), 1)
    s = round(statistics.stdev(CU), 4)
    for k in (2.0, 2.4):
        res = WorksheetEvaluator(parsed).evaluate(
            {"avg_weight": 1, "label_claim": 1},
            {"additional_info": [{"lc_description": "1000 mg", "cu_of": "X",
                                  "n_units": 10, "k_value": k}],
             "standard": [STD], "sample_dilution": [SD],
             "std_areas": [{"area": 100.0} for _ in range(5)],
             "units": [{"unit_ref": "u", "unit_weight": 1, "area": v} for v in CU]},
        )
        hand = round((X - 101.5) + k * s, 1)
        got = res.values["summary.acceptance_value"]
        print(f"k={k}: hand AV={hand}  engine AV={got}")
        assert abs(float(got) - hand) < 0.05

    async with async_session_factory() as sess:
        r = (await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))).scalar_one()
        r.definition = d
        await sess.commit()
    async with async_session_factory() as sess:
        r = (await sess.execute(select(TestTemplateModel).where(TestTemplateModel.code == CODE))).scalar_one()
        assert json.dumps(r.definition, sort_keys=True) == json.dumps(d, sort_keys=True)
    print(f"db row id={r.id} byte-equal to module OK")


if __name__ == "__main__":
    asyncio.run(main())
