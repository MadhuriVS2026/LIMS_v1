"""
Dilution-factor chains — the single most common structure across every
analytical calculation sheet in the lab's workbook set.

Every chromatographic quantitation encodes sample/standard preparation as an
ordered series of volumetric steps. On the standard side the chain divides the
weighed amount down to a concentration; on the sample side the *inverse* chain
multiplies the measured response back up to the original amount. The source
sheets spell this out as long products of cell pairs
(`Wt/Vol1 * Pip1/Vol2 * Pip2/Vol3`), with unused steps filled in as `1/1`.

Column headings vary across sheets (`Vol`/`Pip`, `Dilution-n`/`Volume-n`,
`Pipette (mL)`/`mL`, `Stock`/`mL of Stock`, `V.F.`/`Dil.`) but the algebra is
identical, so one representation covers all of them.
"""
from dataclasses import dataclass


class DilutionError(ValueError):
    """Raised when a dilution step is not physically meaningful."""


@dataclass(frozen=True)
class DilutionStep:
    """
    One volumetric step: `aliquot` mL taken and made up to `diluted_to` mL.

    A step of (1, 1) is the neutral step used by the source sheets to pad out
    unused dilution stages.
    """

    aliquot: float
    diluted_to: float

    def __post_init__(self) -> None:
        if self.aliquot <= 0:
            raise DilutionError(f"Dilution aliquot must be > 0 (got {self.aliquot})")
        if self.diluted_to <= 0:
            raise DilutionError(f"Dilution diluted-to volume must be > 0 (got {self.diluted_to})")

    @property
    def factor(self) -> float:
        """Concentration-reducing factor for this step: aliquot / diluted_to."""
        return self.aliquot / self.diluted_to


@dataclass(frozen=True)
class DilutionChain:
    """
    An ordered chain of dilution steps.

    `factor` is the product of the individual step factors — the amount by
    which the original concentration is reduced. `inverse_factor` is its
    reciprocal, used on the sample side of the master equation.
    """

    steps: tuple[DilutionStep, ...] = ()

    @classmethod
    def from_pairs(cls, pairs: list[tuple[float, float]] | None) -> "DilutionChain":
        """Build from a list of (aliquot, diluted_to) pairs, skipping blanks."""
        if not pairs:
            return cls()
        return cls(tuple(DilutionStep(aliquot=a, diluted_to=d) for a, d in pairs))

    @property
    def factor(self) -> float:
        result = 1.0
        for step in self.steps:
            result *= step.factor
        return result

    @property
    def inverse_factor(self) -> float:
        factor = self.factor
        if factor == 0:
            raise DilutionError("Dilution chain factor is zero; cannot invert")
        return 1.0 / factor

    def __len__(self) -> int:
        return len(self.steps)
