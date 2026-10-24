"""
Parity test for TPL-A6B-0002 — Dissolution (Octreotide Acetate, pH 10, with
replacement).

Source workbook: `Test types/Dissolution sheet_Octreotide_PH 10.xlsx`
(sheet `42_2-8°C_`), authoritative formula dump
`_dumps/Dissolution sheet_Octreotide_PH 10.txt`. Every expected number below is
derived by hand from the sheet formula named in the comment above it and was
independently confirmed against the xlsx cached values (design "Full gold-value
set"), so this is a true oracle, not a snapshot of current code.

The fixture is the dump's entered values: standard inputs, the 5 standard-area
replicates + 2 bracketing areas, the first two units' weights (units 3-6 blank,
exactly as the sheet), the prep volumes, the first two units' sample areas per
%Residue timepoint, and the first two entered %Residue values per %Release
timepoint.
"""
import pytest

from scripts.template_definitions import SEED_TEMPLATES
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.expression import EMPTY
from src.domain.services.calculation.template_schema import TemplateDefinition

CODE = "TPL-A6B-0002"
BY_CODE = {item.code: item for item in SEED_TEMPLATES}


def _parsed() -> TemplateDefinition:
    return TemplateDefinition.parse(BY_CODE[CODE].definition)


class TestA6B0002OctreotidePh10Parity:
    GROUPS = {
        # Standard detail (row 19): potency 89.41, mw 1/1, weight 25.65,
        # dilution_1 25, volume_1 5, dilution_2 50.
        "standard": [{
            "potency": 89.41, "mw_base": 1, "mw_salt": 1, "weight_mg": 25.65,
            "dilution_1": 25, "volume_1": 5, "dilution_2": 50,
        }],
        # B22:B26 standard replicate areas.
        "std_areas": [{"area": a} for a in
                      (3025190, 3032957, 3039697, 3038818, 3038602)],
        # D22:D23 bracketing standard areas (BKT-1, BKT-2).
        "bkt": [{"area": 3037074}, {"area": 3035247}],
        # Sample weights F/G/H: only units 1-2 entered, 3-6 blank.
        "weights": [
            {"w_1hr": 23.59, "w_4hr": 25.13, "w_24hr": 25.34},
            {"w_1hr": 23.9, "w_4hr": 24.84, "w_24hr": 23.61},
            {}, {}, {}, {},
        ],
        # Prep (rows 32-37): A32 4.12, A35 10, B35 1, C35 1, A37 1.
        "prep": [{"pct_assay": 4.12, "media_vol": 10, "pipette_vol": 1,
                  "vf_vol": 1, "withdraw_replace": 1}],
        # %Residue sample areas B40/B41, B46/B47, B52/B53 (units 1-2 only).
        "residue_1hr": [{"area": 3152088}, {"area": 3270742}, {}, {}, {}, {}],
        "residue_4hr": [{"area": 2351327}, {"area": 2326691}, {}, {}, {}, {}],
        "residue_24hr": [{"area": 1622756}, {"area": 1437001}, {}, {}, {}, {}],
        # %Release entered %Residue values B70/B71, B76/B77, B82/B83.
        "release_1hr": [{"residue_in": 4.04}, {"residue_in": 4.14}, {}, {}, {}, {}],
        "release_4hr": [{"residue_in": 2.83}, {"residue_in": 2.83}, {}, {}, {}, {}],
        "release_24hr": [{"residue_in": 1.94}, {"residue_in": 1.84}, {}, {}, {}, {}],
    }

    @pytest.fixture()
    def result(self):
        return WorksheetEvaluator(_parsed()).evaluate({}, self.GROUPS)

    # ── Standard concentration (J19) ────────────────────────────────
    def test_standard_concentration(self, result):
        # J19 = 25.65/25 * 5/50 * 1/1 * 89.41/100 * 1000 = 91.73466
        assert result.values["standard.conc_ppm"] == pytest.approx(91.73466, abs=1e-4)

    # ── Standard area statistics (B27/B29, D27/D29) ─────────────────
    def test_standard_area_statistics(self, result):
        # B27 = AVERAGE(B22:B26)
        assert result.values["std_stats.mean_std"] == pytest.approx(3035052.8, abs=0.5)
        # B29 = STDEV(B22:B26)*100/B27
        assert result.values["std_stats.rsd_std"] == pytest.approx(
            0.20177293603399474, abs=1e-6)
        # D27 = AVERAGE(B22:B26,D22:D26) over the 7 pooled areas
        assert result.values["std_stats.mean_bkt"] == pytest.approx(
            3035369.2857142859, abs=0.5)
        # D29 = STDEV(B22:B26,D22:D26)*100/D27
        assert result.values["std_stats.rsd_bkt"] == pytest.approx(
            0.16659794279279921, abs=1e-6)

    # ── Sample-weight statistics (F/G/H 28-30) ──────────────────────
    def test_weight_statistics_1hr(self, result):
        # F28 = AVERAGE(23.59, 23.9) = 23.745
        assert result.values["weight_stats.mean_1hr"] == pytest.approx(23.745, abs=1e-4)
        # F29 = STDEV(23.59, 23.9, 23.745)  [range F22:F28 includes the mean cell]
        assert result.values["weight_stats.sd_1hr"] == pytest.approx(0.155, abs=1e-3)
        # F30 = F29*100/F28
        assert result.values["weight_stats.rsd_1hr"] == pytest.approx(
            0.6527690040008397, abs=1e-4)

    def test_weight_statistics_4hr(self, result):
        # G28 = AVERAGE(25.13, 24.84) = 24.985
        assert result.values["weight_stats.mean_4hr"] == pytest.approx(24.985, abs=1e-4)
        # G29 = STDEV(25.13, 24.84, 24.985)
        assert result.values["weight_stats.sd_4hr"] == pytest.approx(0.145, abs=1e-3)
        # G30 = G29*100/G28
        assert result.values["weight_stats.rsd_4hr"] == pytest.approx(
            0.58034820892535355, abs=1e-4)

    def test_weight_statistics_24hr(self, result):
        # H28 = AVERAGE(25.34, 23.61) = 24.475
        assert result.values["weight_stats.mean_24hr"] == pytest.approx(24.475, abs=1e-4)
        # H29 = STDEV(25.34, 23.61, 24.475)
        assert result.values["weight_stats.sd_24hr"] == pytest.approx(0.865, abs=1e-3)
        # H30 = H29*100/H28
        assert result.values["weight_stats.rsd_24hr"] == pytest.approx(
            3.5342185903983667, abs=1e-4)

    # ── %Residue — 1 hr at 37°C (K40/K41, D40/E40/F40/G40) ──────────
    def test_residue_1hr(self, result):
        # K40 = 3152088/3035052.8 * 25.65/25 * 5/50 * 1/1 * 10/23.59 * 89.41 * 1/1
        assert result.row_value("residue_1hr", 0, "residue") == pytest.approx(
            4.0386628322462599, abs=1e-4)
        # K41 (unit-2, weight 23.9)
        assert result.row_value("residue_1hr", 1, "residue") == pytest.approx(
            4.136333922855612, abs=1e-4)
        # D40 = AVERAGE(C40:C45)
        assert result.row_value("residue_1hr", 0, "mean") == pytest.approx(
            4.0874983775509364, abs=1e-4)
        # E40 = MIN; F40 = MAX
        assert result.row_value("residue_1hr", 0, "min_v") == pytest.approx(
            4.0386628322462599, abs=1e-4)
        assert result.row_value("residue_1hr", 0, "max_v") == pytest.approx(
            4.136333922855612, abs=1e-4)
        # G40 = STDEV(C40:C45)*100/D40
        assert result.row_value("residue_1hr", 0, "rsd") == pytest.approx(
            1.6896371353947515, abs=1e-4)

    # ── %Residue — 4 hr at 55°C (K46, D46/G46) ──────────────────────
    def test_residue_4hr(self, result):
        # K46 (weight 25.13)
        assert result.row_value("residue_4hr", 0, "residue") == pytest.approx(
            2.8280543211589846, abs=1e-4)
        # D46 = AVERAGE(C46:C51)
        assert result.row_value("residue_4hr", 0, "mean") == pytest.approx(
            2.8295742711996321, abs=1e-4)
        # G46 = STDEV(C46:C51)*100/D46
        assert result.row_value("residue_4hr", 0, "rsd") == pytest.approx(
            0.07596669165011731, abs=1e-4)

    # ── %Residue — 24 hr at 55°C (K52, D52/G52) ─────────────────────
    def test_residue_24hr(self, result):
        # K52 (weight 25.34)
        assert result.row_value("residue_24hr", 0, "residue") == pytest.approx(
            1.9355919975161624, abs=1e-4)
        # D52 = AVERAGE(C52:C57)
        assert result.row_value("residue_24hr", 0, "mean") == pytest.approx(
            1.8876063496116782, abs=1e-4)
        # G52 = STDEV(C52:C57)*100/D52
        assert result.row_value("residue_24hr", 0, "rsd") == pytest.approx(
            3.5951327499900718, abs=1e-4)

    # ── %Release — 1 hr at 37°C (C70/C71, D70/E70/F70/G70) ──────────
    def test_release_1hr(self, result):
        # C70 = (4.12 - 4.04)/4.12 * 100
        assert result.row_value("release_1hr", 0, "rel") == pytest.approx(
            1.9417475728155356, abs=1e-4)
        # C71 = (4.12 - 4.14)/4.12 * 100
        assert result.row_value("release_1hr", 1, "rel") == pytest.approx(
            -0.48543689320387312, abs=1e-4)
        # D70 = AVERAGE(C70:C75)
        assert result.row_value("release_1hr", 0, "mean") == pytest.approx(
            0.72815533980583125, abs=1e-4)
        # E70 = MIN; F70 = MAX
        assert result.row_value("release_1hr", 0, "min_v") == pytest.approx(
            -0.48543689320387312, abs=1e-4)
        assert result.row_value("release_1hr", 0, "max_v") == pytest.approx(
            1.9417475728155356, abs=1e-4)
        # G70 = STDEV(C70:C75)*100/D70
        assert result.row_value("release_1hr", 0, "rsd") == pytest.approx(
            235.70226039551304, abs=1e-3)

    # ── %Release — 4 hr at 55°C (C76, D76/G76) ──────────────────────
    def test_release_4hr(self, result):
        # C76 = (4.12 - 2.83)/4.12 * 100
        assert result.row_value("release_4hr", 0, "rel") == pytest.approx(
            31.310679611650489, abs=1e-4)
        # D76 = AVERAGE(C76:C81); both entered values equal, so mean == value
        assert result.row_value("release_4hr", 0, "mean") == pytest.approx(
            31.310679611650489, abs=1e-4)
        # G76 = STDEV(C76:C81)*100/D76 = 0 (both values identical)
        assert result.row_value("release_4hr", 0, "rsd") == pytest.approx(0, abs=1e-6)

    # ── %Release — 24 hr at 55°C (C82/C83, D82/G82) ─────────────────
    def test_release_24hr(self, result):
        # C82 = (4.12 - 1.94)/4.12 * 100
        assert result.row_value("release_24hr", 0, "rel") == pytest.approx(
            52.912621359223301, abs=1e-4)
        # C83 = (4.12 - 1.84)/4.12 * 100
        assert result.row_value("release_24hr", 1, "rel") == pytest.approx(
            55.339805825242728, abs=1e-4)
        # D82 = AVERAGE(C82:C87)
        assert result.row_value("release_24hr", 0, "mean") == pytest.approx(
            54.126213592233015, abs=1e-4)
        # G82 = STDEV(C82:C87)*100/D82
        assert result.row_value("release_24hr", 0, "rsd") == pytest.approx(
            3.1708824268455151, abs=1e-4)

    # ── Reportable result resolves (residue_24hr.mean) ──────────────
    def test_reportable_result(self, result):
        assert result.reportable_result == pytest.approx(
            1.8876063496116782, abs=1e-4)

    # ── Acceptance criterion: the std-replicate %RSD SST ────────────
    def test_acceptance_criterion_is_std_rsd_sst(self):
        definition = _parsed()
        assert len(definition.criteria) == 1
        crit = definition.criteria[0]
        assert crit.target == "std_stats.rsd_std"
        assert crit.operator.value == "lte"
        assert crit.limit == (pytest.approx(2.0),)

    # ── Empty worksheet is blank, never an error ────────────────────
    def test_empty_worksheet_is_blank(self):
        empty = WorksheetEvaluator(_parsed()).evaluate({}, {})
        assert empty.has_blocking_failure is False
        assert empty.reportable_result is EMPTY
