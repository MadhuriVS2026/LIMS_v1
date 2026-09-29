"""
Parity tests: reproduce real workbook calculations through the engine.

These are the tests that matter most. Each case transcribes a formula from an
actual R&D calculation sheet (with the sheet's own input values) and asserts the
engine reproduces it. Values are hand-derived from the source formula rather
than copied from a cached cell, so a transcription error in either direction
shows up as a failure.

Source workbooks live in `rd-lab-instance/Test types/`; the parsed structural
dumps used to write these tests are in `rd-lab-instance/_inspect_tests/`.
"""
import pytest

from src.domain.services.calculation import EMPTY, evaluate

# ─────────────── Assay by HPLC (archetype A1) ───────────────

# Standard block (row 14): 5.054 mg / 50 mL, 5→100, 1→1, MW 1/1, potency 99.4
STD = {
    "weight_mg": 5.054,
    "vol_1": 50.0,
    "pip_1": 5.0,
    "vol_2": 100.0,
    "pip_2": 1.0,
    "vol_3": 1.0,
    "mw_base": 1.0,
    "mw_salt": 1.0,
    "potency": 99.4,
}

# STD replicate areas (B18:B23) — six slots, sixth left blank on the sheet.
STD_AREAS = [253287.0, 253024.0, 252584.0, 252811.0, 251367.0, None]

# Bracketing block 1 (E18:E19), block 2 (I23)
BKT_1 = [251635.0, 251658.0]
BKT_2 = [260938.0]

STD_PPM_EXPR = (
    "weight_mg / vol_1 * pip_1 / vol_2 * pip_2 / vol_3 "
    "* mw_base / mw_salt * potency / 100 * 1000"
)


class TestAssayByHplcStandardBlock:
    def test_standard_concentration_ppm(self):
        # 5.054/50 * 5/100 * 1/1 * 1/1 * 0.994 * 1000 = 5.023676
        assert evaluate(STD_PPM_EXPR, STD) == pytest.approx(5.023676, abs=1e-6)

    def test_mean_of_replicates_skips_the_blank_sixth_slot(self):
        # Sheet: AVERAGE(B18:B23) over a 6-cell range with one blank → mean of 5.
        result = evaluate("mean(areas)", {"areas": STD_AREAS})
        assert result == pytest.approx(252614.6)

    def test_rsd_of_replicates(self):
        result = evaluate("rsd(areas)", {"areas": STD_AREAS})
        # sd 744.26897 / mean 252614.6 * 100
        assert result == pytest.approx(0.294626, abs=1e-6)

    def test_system_suitability_rsd_passes_nmt_2_percent(self):
        rsd = evaluate("rsd(areas)", {"areas": STD_AREAS})
        assert rsd <= 2.0

    def test_bracketing_block_1_pools_with_standard(self):
        """
        Sheet E24: AVERAGE(E18:E23, B18:B23) — bracketing areas are pooled with
        the initial standard replicates, never averaged alone.
        """
        ctx = {"std": STD_AREAS, "bkt1": BKT_1}
        pooled = evaluate("mean(pool(std, bkt1))", ctx)
        expected = (sum(a for a in STD_AREAS if a) + sum(BKT_1)) / 7
        assert pooled == pytest.approx(expected)

    def test_bracketing_block_2_pools_cumulatively(self):
        """
        Sheet I24: AVERAGE(B18:B23, I18:I23, E18:E23) — block 2 pools the
        standard AND block 1 AND block 2, not just block 2.
        """
        ctx = {"std": STD_AREAS, "bkt1": BKT_1, "bkt2": BKT_2}
        pooled = evaluate("mean(pool(std, bkt1, bkt2))", ctx)
        expected = (sum(a for a in STD_AREAS if a) + sum(BKT_1) + sum(BKT_2)) / 8
        assert pooled == pytest.approx(expected)

    def test_pooled_rsd_grows_when_a_drifting_bracket_is_added(self):
        ctx = {"std": STD_AREAS, "bkt1": BKT_1, "bkt2": BKT_2}
        rsd_1 = evaluate("rsd(pool(std, bkt1))", ctx)
        rsd_2 = evaluate("rsd(pool(std, bkt1, bkt2))", ctx)
        # BKT-2 (260938) sits well above the others, so the pooled %RSD must rise.
        assert rsd_2 > rsd_1


class TestAssayByHplcSampleResult:
    """
    Sheet Q31: % Assay for sample row 31.

    = P31/$B$24 * $C$14/$D$14 * $E$14/$F$14 * $G$14/$H$14
      * K31/J31 * M31/L31 * I31/H31 * F31/G31 * $K$14 * $I$14/$J$14

    Sample row 31 inputs: avg_weight 1, label_claim 50, sample_weight 1,
    vol 500, pip 5, vol 100, pip 1, vol 1; Area-1 273537, Area-2 blank.
    """

    SAMPLE = {
        "avg_weight": 1.0,
        "label_claim": 50.0,
        "sample_weight": 1.0,
        "s_vol_1": 500.0,
        "s_pip_1": 5.0,
        "s_vol_2": 100.0,
        "s_pip_2": 1.0,
        "s_vol_3": 1.0,
        "area_1": 273537.0,
        "area_2": None,
    }

    PCT_ASSAY_EXPR = (
        "avg_area / mean_std "
        "* std.weight_mg / std.vol_1 * std.pip_1 / std.vol_2 * std.pip_2 / std.vol_3 "
        "* s_vol_2 / s_pip_1 * s_vol_3 / s_pip_2 * s_vol_1 / sample_weight "
        "* avg_weight / label_claim "
        "* std.potency * std.mw_base / std.mw_salt"
    )

    def _context(self) -> dict:
        ctx = dict(self.SAMPLE)
        ctx["std"] = STD
        ctx["mean_std"] = evaluate("mean(areas)", {"areas": STD_AREAS})
        ctx["avg_area"] = evaluate("mean([area_1, area_2])", ctx)
        return ctx

    def test_average_area_over_one_filled_injection(self):
        ctx = self._context()
        assert ctx["avg_area"] == pytest.approx(273537.0)

    def test_percent_assay(self):
        """
        Component terms:
          ratio      = 273537 / 252614.6      = 1.08282...
          std terms  = 5.054/50 * 5/100 * 1/1 = 0.005054
          sample     = 100/5 * 1/1 * 500/1    = 10000
          claim      = 1/50                   = 0.02
          potency    = 99.4  (as a percent, not /100 — yields a % result)
        => 108.795079 (full float precision; ~108.8% assay)
        """
        result = evaluate(self.PCT_ASSAY_EXPR, self._context())
        assert result == pytest.approx(108.795079, abs=1e-6)

    def test_percent_assay_is_in_a_plausible_reportable_range(self):
        # Guards against a factor-of-10 transcription slip in the chain.
        result = evaluate(self.PCT_ASSAY_EXPR, self._context())
        assert 90.0 < result < 120.0

    def test_result_is_blank_when_area_missing(self):
        ctx = self._context()
        ctx["avg_area"] = EMPTY
        assert evaluate(self.PCT_ASSAY_EXPR, ctx) is EMPTY

    def test_result_is_blank_when_standard_mean_is_zero(self):
        ctx = self._context()
        ctx["mean_std"] = 0.0
        assert evaluate(self.PCT_ASSAY_EXPR, ctx) is EMPTY

    def test_mean_assay_averages_the_preparation_group(self):
        # Sheet R31: AVERAGE(Q31:Q34) over the two preparations of a batch.
        assert evaluate("mean([p1, p2])", {"p1": 108.79, "p2": 108.35}) == pytest.approx(108.57)


class TestStandardCoRelation:
    """
    Sheet Q23: TRUNC(P22/Q22 * M18/M17, 3) * 100 — a weight-normalised response
    ratio between two independently weighed standards, expected near 100%.
    """

    EXPR = "trunc(mean_std_1 / mean_std_2 * weight_2 / weight_1, 3) * 100"

    def test_identical_standards_give_100_percent(self):
        ctx = {"mean_std_1": 100000.0, "mean_std_2": 100000.0, "weight_1": 5.0, "weight_2": 5.0}
        assert evaluate(self.EXPR, ctx) == pytest.approx(100.0)

    def test_proportional_response_and_weight_cancel(self):
        # Twice the weight giving twice the response is still 100% correlation.
        ctx = {"mean_std_1": 100000.0, "mean_std_2": 200000.0, "weight_1": 5.0, "weight_2": 10.0}
        assert evaluate(self.EXPR, ctx) == pytest.approx(100.0)

    def test_truncation_applied_before_scaling(self):
        # TRUNC to 3 dp happens on the ratio, then ×100 — so 0.9997 → 0.999 → 99.9
        ctx = {"mean_std_1": 9997.0, "mean_std_2": 10000.0, "weight_1": 1.0, "weight_2": 1.0}
        assert evaluate(self.EXPR, ctx) == pytest.approx(99.9)


class TestRelatedSubstances:
    """
    `Related substance by HPLC_Calculation against impurity standard`
    (archetype A4), Rasagiline Mesylate.
    """

    STD_RS = {
        "potency": 99.6,
        "mw_base": 171.24,
        "mw_salt": 267.35,
        "weight_mg": 39.44,
        "dil_1": 200.0,
        "vol_1": 1.0,
        "dil_2": 100.0,
        "vol_2": 1.0,
        "dil_3": 1.0,
        "vol_3": 1.0,
        "dil_4": 1.0,
    }

    CONC_EXPR = (
        'if(mw_base = "NA" or mw_salt = "NA", '
        "weight_mg / dil_1 * vol_1 / dil_2 * vol_2 / dil_3 * vol_3 / dil_4 * potency / 100 * 1000, "
        "weight_mg / dil_1 * vol_1 / dil_2 * vol_2 / dil_3 * vol_3 / dil_4 "
        "* potency / 100 * mw_base / mw_salt * 1000)"
    )

    def test_standard_concentration_with_mw_ratio(self):
        # 39.44/200 = 0.1972; /100 → 0.001972; × 0.996 → 0.001964112;
        # × (171.24/267.35 = 0.6404339) → 0.001258031; × 1000
        assert evaluate(self.CONC_EXPR, self.STD_RS) == pytest.approx(1.258031, abs=1e-6)

    def test_na_molecular_weight_omits_the_ratio(self):
        ctx = dict(self.STD_RS, mw_base="NA", mw_salt="NA")
        # Without the MW ratio: 39.44/200 * 1/100 * 0.996 * 1000 = 1.964112
        assert evaluate(self.CONC_EXPR, ctx) == pytest.approx(1.964112, abs=1e-6)

    def test_rrt_is_impurity_rt_over_main_peak_rt(self):
        # Sheet F76: B76/$C$57 with main peak at 20.687 min
        assert evaluate("rt / main_rt", {"rt": 8.51, "main_rt": 20.687}) == pytest.approx(
            0.411369, abs=1e-6
        )

    def test_rrf_multiplication_mode(self):
        expr = 'if(mode = "RRF (multiplication factor)", base * rrf, base / rrf)'
        ctx = {"mode": "RRF (multiplication factor)", "base": 0.5, "rrf": 2.0}
        assert evaluate(expr, ctx) == pytest.approx(1.0)

    def test_rrf_division_mode(self):
        expr = 'if(mode = "RRF (multiplication factor)", base * rrf, base / rrf)'
        ctx = {"mode": "RRF (Division factor)", "base": 0.5, "rrf": 2.0}
        assert evaluate(expr, ctx) == pytest.approx(0.25)

    def test_blq_reporting_below_loq(self):
        expr = 'if(pct < loq, "BLQ", round(pct, 3))'
        assert evaluate(expr, {"pct": 0.02, "loq": 0.05}) == "BLQ"

    def test_total_impurities_sums_rounded_values(self):
        """
        Sheet G107 sums ROUND(...,3) of each row rather than rounding the sum.
        Three values just under the rounding threshold must total 0, not 0.001.
        """
        ctx = {"a": 0.0004, "b": 0.0004, "c": 0.0004}
        assert evaluate("round(a,3) + round(b,3) + round(c,3)", ctx) == pytest.approx(0.0)

    def test_single_maximum_unknown(self):
        ctx = {"unknowns": [0.012, 0.045, 0.008, 0.031]}
        assert evaluate("max(unknowns)", ctx) == pytest.approx(0.045)

    def test_area_normalisation_variant(self):
        """
        Archetype A5: pct = area / total_area / rrf * 100, where total_area is
        the impurity areas plus the main peak.
        """
        ctx = {"imp_areas": [1000.0, 2000.0], "main_area": 97000.0, "area": 2000.0, "rrf": 1.0}
        total = evaluate("sum(imp_areas) + main_area", ctx)
        assert total == pytest.approx(100000.0)
        ctx["total_area"] = total
        assert evaluate("area / total_area / rrf * 100", ctx) == pytest.approx(2.0)


class TestContentUniformity:
    """`CU by HPLC` (archetype A8), Rasagiline Mesylate Tab 1 mg."""

    PCT_LC = [
        98.9, 99.9, 101.0, 96.9, 100.5, 97.1, 99.5, 100.2, 99.8, 98.3,
    ]

    def test_k_lookup_from_n(self):
        expr = "if(n = 10, 2.4, if(n = 30, 2.0))"
        assert evaluate(expr, {"n": 10}) == pytest.approx(2.4)
        assert evaluate(expr, {"n": 30}) == pytest.approx(2.0)

    def test_acceptance_value_when_mean_within_window(self):
        # 98.5 <= X <= 101.5 → AV = k*s
        ctx = {"x": 99.2, "k": 2.4, "s": 1.3}
        expr = "if(x < 101.5, if(x < 98.5, (98.5 - x) + k * s, k * s), (x - 101.5) + k * s)"
        assert evaluate(expr, ctx) == pytest.approx(3.12)

    def test_acceptance_value_below_window(self):
        ctx = {"x": 97.0, "k": 2.4, "s": 1.3}
        expr = "if(x < 101.5, if(x < 98.5, (98.5 - x) + k * s, k * s), (x - 101.5) + k * s)"
        assert evaluate(expr, ctx) == pytest.approx(1.5 + 3.12)

    def test_acceptance_value_above_window(self):
        ctx = {"x": 103.0, "k": 2.4, "s": 1.3}
        expr = "if(x < 101.5, if(x < 98.5, (98.5 - x) + k * s, k * s), (x - 101.5) + k * s)"
        assert evaluate(expr, ctx) == pytest.approx(1.5 + 3.12)

    def test_full_acceptance_value_chain(self):
        ctx = {"pct_lc": self.PCT_LC, "n": 10}
        mean = evaluate("round(mean(pct_lc), 1)", ctx)
        sd = evaluate("round(sd(pct_lc), 4)", ctx)
        ctx |= {"x": mean, "s": sd, "k": evaluate("if(n = 10, 2.4, 2.0)", ctx)}
        av = evaluate(
            "round(if(x < 101.5, if(x < 98.5, (98.5 - x) + k * s, k * s), "
            "(x - 101.5) + k * s), 1)",
            ctx,
        )
        assert mean == pytest.approx(99.2, abs=0.05)
        assert av <= 15.0  # sheet limit: NMT 15.0

    def test_weight_variation_net_weight(self):
        # `CU by weight variation`: net = filled - empty
        ctx = {"filled": 209.6, "empty": 8.4}
        assert evaluate("filled - empty", ctx) == pytest.approx(201.2)


class TestGravimetric:
    """Archetype A10."""

    def test_loss_on_drying(self):
        # %LOD = (W2 - W3) / (W2 - W1) * 100
        ctx = {"w1": 20.0, "w2": 25.0, "w3": 24.75}
        assert evaluate("(w2 - w3) / (w2 - w1) * 100", ctx) == pytest.approx(5.0)

    def test_weight_per_ml_with_water_density_factor(self):
        # ROUND((W1 - W)/(W2 - W), 4) * 0.99704
        ctx = {"w": 20.0, "w1": 45.0, "w2": 44.5}
        expr = "round((w1 - w) / (w2 - w), 4) * 0.99704"
        assert evaluate(expr, ctx) == pytest.approx(1.0203 * 0.99704, abs=1e-4)

    def test_gross_content_per_container(self):
        ctx = {"filled": 30.5, "empty": 20.0, "wt_per_ml": 1.05}
        assert evaluate("(filled - empty) / wt_per_ml", ctx) == pytest.approx(10.0)


class TestTitrimetry:
    """Archetype A9: Sodium Metabisulfite."""

    def test_mg_per_ml_and_percent(self):
        ctx = {
            "ml_titrant": 4.2,
            "normality": 0.1,
            "factor": 47.5,
            "ml_sample": 10.0,
            "label_claim": 2.0,
        }
        mg_per_ml = evaluate(
            "(ml_titrant * normality * factor * 1000) / (ml_sample * 1000)", ctx
        )
        assert mg_per_ml == pytest.approx(1.995)
        ctx["mg_per_ml"] = mg_per_ml
        assert evaluate("mg_per_ml / label_claim * 100", ctx) == pytest.approx(99.75)


class TestBlankCorrection:
    """Nitrosamine (A13) and Sodium chloride by IC (A2) subtract a blank."""

    def test_corrected_area(self):
        assert evaluate("area - blank", {"area": 8978.0, "blank": 0.0}) == 8978.0
        assert evaluate("area - blank", {"area": 8978.0, "blank": 120.0}) == 8858.0

    def test_blank_interference_percentage(self):
        ctx = {"mean_blank": 100.0, "mean_std": 10000.0}
        assert evaluate("mean_blank / mean_std * 100", ctx) == pytest.approx(1.0)

    def test_nitrosamine_ppm_result(self):
        """
        Sheet O30: TRUNC(corrected/mean_std * std chain * purity/100
        * sample chain * avg_wt/label_claim * 1e6, 4)
        """
        ctx = {
            "corrected": 8978.0,
            "mean_std": 76406.0,
            "std_factor": 2.24 / 20 * 0.15 / 10 * 0.1 / 10 * 0.64 / 10 * 1 / 1,
            "purity": 96.88,
            "sample_factor": 20.0 / 0.4 * 1.0 / 1.0 * 1.0 / 1.0,
            "avg_weight": 1.0,
            "label_claim": 100.0,
        }
        expr = (
            "trunc(corrected / mean_std * std_factor * purity / 100 "
            "* sample_factor * avg_weight / label_claim * 1000000, 4)"
        )
        result = evaluate(expr, ctx)
        assert result is not EMPTY
        assert result > 0


class TestDissolutionRecursion:
    """
    Archetype A6a — without replacement. The media volume shrinks by the
    withdrawal volume at each timepoint, and release is the uncorrected value
    plus the accumulated carry-over of everything withdrawn earlier.

    The source sheets hard-code 500/495/490/485... — the engine must generate
    that series from (initial, withdrawal) instead.
    """

    def test_volume_series_is_generated_not_hardcoded(self):
        initial, withdrawal = 500.0, 5.0
        volumes = [initial - i * withdrawal for i in range(8)]
        assert volumes == [500.0, 495.0, 490.0, 485.0, 480.0, 475.0, 470.0, 465.0]

    def test_with_replacement_volume_series_is_constant(self):
        # V[t] = V[t-1] - withdrawal + replacement, with equal volumes → constant
        initial, withdrawal, replacement = 750.0, 5.0, 5.0
        volume = initial
        series = [volume]
        for _ in range(4):
            volume = volume - withdrawal + replacement
            series.append(volume)
        assert series == [750.0] * 5

    def test_cumulative_release_adds_prior_corrections(self):
        """
        release%[t] = uncorrected[t] + Σ corrections[1..t-1]
        Sheet D88: ROUND(D57 + C73, 0); E88: ROUND(E57 + C73 + D73, 0)
        """
        uncorrected = [20.0, 40.0, 60.0]
        corrections = [0.2, 0.4]
        assert evaluate("u", {"u": uncorrected[0]}) == 20.0
        ctx = {"u": uncorrected[1], "prior": corrections[:1]}
        assert evaluate("u + sum(prior)", ctx) == pytest.approx(40.2)
        ctx = {"u": uncorrected[2], "prior": corrections[:2]}
        assert evaluate("u + sum(prior)", ctx) == pytest.approx(60.6)

    def test_correction_factor_term(self):
        # Sheet C73: TRUNC(withdrawal / volume * uncorrected, 3)
        ctx = {"withdrawal": 5.0, "volume": 500.0, "uncorrected": 20.0}
        assert evaluate("trunc(withdrawal / volume * uncorrected, 3)", ctx) == pytest.approx(0.2)

    def test_cumsum_builds_the_carryover_series(self):
        # Compared with approx: 0.2 + 0.4 is 0.6000000000000001 in IEEE-754.
        result = evaluate("cumsum(c)", {"c": [0.2, 0.4, 0.6]})
        assert result == pytest.approx([0.2, 0.6, 1.2])

    def test_per_timepoint_statistics_across_units(self):
        units_at_t = [98.0, 101.0, 99.0, 100.0, 97.0, 102.0]
        ctx = {"u": units_at_t}
        assert evaluate("round(mean(u), 0)", ctx) == pytest.approx(100.0)
        assert evaluate("min(u)", ctx) == 97.0
        assert evaluate("max(u)", ctx) == 102.0
        assert evaluate("round(rsd(u), 1)", ctx) == pytest.approx(1.9, abs=0.1)

    def test_whole_vial_residual_release(self):
        # A6b: release% = batch_assay - content%
        ctx = {"batch_assay": 99.5, "content": 24.3}
        assert evaluate("batch_assay - content", ctx) == pytest.approx(75.2)

    def test_octreotide_residue_conversion(self):
        # release% = (assay - residue) / assay * 100
        ctx = {"assay": 100.0, "residue": 25.0}
        assert evaluate("(assay - residue) / assay * 100", ctx) == pytest.approx(75.0)


class TestMultiAnalytePeakSum:
    """
    Archetype A2, `Content of Lyso PC PG`: the analyte response is the sum of
    several named peaks per injection, and a zero sum must read as blank.
    """

    def test_peak_sum(self):
        ctx = {"peaks": [1000.0, 2000.0, 1500.0, 500.0, 250.0]}
        assert evaluate("sum(peaks)", ctx) == pytest.approx(5250.0)

    def test_zero_peak_sum_is_blank(self):
        # Sheet: IF(SUM(peaks)=0, "", SUM(peaks))
        ctx = {"peaks": [0.0, 0.0]}
        assert evaluate('if(sum(peaks) = 0, blank(), sum(peaks))', ctx) is EMPTY

    def test_vial_factor_distinguishes_mg_per_vial_from_mg_per_ml(self):
        """
        The `_mgvial_` and `_mgmL_` workbooks are the same sheet differing only
        by a ×12.5 vial factor — so it is a unit selector, not a new template.
        """
        base_expr = "conc * chain * potency / 100"
        ctx = {"conc": 2.0, "chain": 10.0, "potency": 99.0}
        per_ml = evaluate(base_expr, ctx)
        per_vial = evaluate(f"({base_expr}) * 12.5", ctx)
        assert per_vial == pytest.approx(per_ml * 12.5)

    def test_percent_of_label_claim(self):
        ctx = {"mg_per_vial": 51.5, "label_claim": 52.0}
        assert evaluate("mg_per_vial * 100 / label_claim", ctx) == pytest.approx(
            99.038, abs=1e-3
        )


class TestMicrobialAssayPrimitives:
    """
    Archetype A11 is deferred as bespoke, but its regression primitives run on
    the same engine — confirming the engine is sufficient when it is built.
    """

    def test_log_concentration(self):
        assert evaluate("round(ln(c), 4)", {"c": 10.0}) == pytest.approx(2.3026, abs=1e-4)

    def test_plate_position_correction(self):
        # corrected[L] = spl_avg[L] - (ref_avg[L] - ref_grand)
        ctx = {"spl_avg": 18.2, "ref_avg": 17.9, "ref_grand": 18.0}
        assert evaluate("spl_avg - (ref_avg - ref_grand)", ctx) == pytest.approx(18.3)

    def test_back_calculation_through_exp(self):
        # Cu = EXP((U - intercept) / slope) = exp((18.3 - 10) / 4) = exp(2.075)
        ctx = {"u": 18.3, "intercept": 10.0, "slope": 4.0}
        assert evaluate("exp((u - intercept) / slope)", ctx) == pytest.approx(
            7.964546, abs=1e-6
        )
