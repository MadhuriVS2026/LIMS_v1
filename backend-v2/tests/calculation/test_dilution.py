"""Unit tests for dilution-factor chains."""
import pytest

from src.domain.services.calculation import DilutionChain, DilutionStep
from src.domain.services.calculation.dilution import DilutionError


class TestDilutionStep:
    def test_factor(self):
        assert DilutionStep(aliquot=5, diluted_to=50).factor == pytest.approx(0.1)

    def test_neutral_step(self):
        assert DilutionStep(aliquot=1, diluted_to=1).factor == 1.0

    @pytest.mark.parametrize("aliquot,diluted_to", [(0, 50), (-1, 50), (5, 0), (5, -10)])
    def test_non_physical_volumes_rejected(self, aliquot, diluted_to):
        with pytest.raises(DilutionError):
            DilutionStep(aliquot=aliquot, diluted_to=diluted_to)


class TestDilutionChain:
    def test_empty_chain_is_neutral(self):
        assert DilutionChain().factor == 1.0
        assert DilutionChain().inverse_factor == 1.0

    def test_single_step(self):
        chain = DilutionChain.from_pairs([(5, 50)])
        assert chain.factor == pytest.approx(0.1)
        assert chain.inverse_factor == pytest.approx(10.0)

    def test_multi_step_is_product_of_steps(self):
        # Assay sheet standard prep: 5/50, then 1/100, then 1/1
        chain = DilutionChain.from_pairs([(5, 50), (1, 100), (1, 1)])
        assert chain.factor == pytest.approx(0.1 * 0.01 * 1.0)
        assert chain.inverse_factor == pytest.approx(1000.0)

    def test_neutral_padding_does_not_change_factor(self):
        # Source sheets pad unused stages with 1/1 — must be a no-op.
        base = DilutionChain.from_pairs([(5, 50)])
        padded = DilutionChain.from_pairs([(5, 50), (1, 1), (1, 1), (1, 1)])
        assert padded.factor == pytest.approx(base.factor)

    def test_inverse_is_reciprocal(self):
        chain = DilutionChain.from_pairs([(2, 25), (5, 100)])
        assert chain.factor * chain.inverse_factor == pytest.approx(1.0)

    def test_from_pairs_handles_none_and_empty(self):
        assert len(DilutionChain.from_pairs(None)) == 0
        assert len(DilutionChain.from_pairs([])) == 0

    def test_length(self):
        assert len(DilutionChain.from_pairs([(1, 10), (1, 10)])) == 2

    def test_chain_is_immutable(self):
        chain = DilutionChain.from_pairs([(5, 50)])
        with pytest.raises((AttributeError, TypeError)):
            chain.steps = ()  # type: ignore[misc]


class TestRealWorkbookChains:
    def test_assay_standard_concentration(self):
        """
        `Assay by HPLC` standard block: 5.054 mg into 50 mL, 5→100, 1→1,
        potency 99.4%, MW ratio 1/1, expressed as ppm (×1000).

        Sheet formula: C14/D14*E14/F14*G14/H14*I14/J14*K14/100*1000
        """
        chain = DilutionChain.from_pairs([(5, 100), (1, 1)])
        weight_mg = 5.054
        first_volume = 50.0
        potency = 99.4
        ppm = (weight_mg / first_volume) * chain.factor * (potency / 100) * 1000
        assert ppm == pytest.approx(5.02368, abs=1e-5)

    def test_lenacapavir_rs_standard_concentration(self):
        """
        `Related substance_RS-1_Lenacapavir`: 30.71 mg into 50 mL, 1→1,
        potency 98.78%, ppm. Sheet: A18/B18*C18/D18*E18/F18*G18/100*1000
        """
        chain = DilutionChain.from_pairs([(1, 1)])
        ppm = (30.71 / 50.0) * chain.factor * (98.78 / 100) * 1000
        # 30.71/50 = 0.6142; × 0.9878 = 0.60670676; × 1000
        assert ppm == pytest.approx(606.70676, abs=1e-5)

    def test_sample_side_uses_inverse_chain(self):
        """
        The sample side multiplies by the reciprocal chain. Assay sheet sample
        prep: 1 mg into 500 mL, 5→100, 1→1 — the inverse recovers the dilution
        the response must be scaled back through.
        """
        chain = DilutionChain.from_pairs([(5, 100), (1, 1)])
        sample_weight = 1.0
        first_volume = 500.0
        factor = (first_volume / sample_weight) * chain.inverse_factor
        assert factor == pytest.approx(500.0 * 20.0)
