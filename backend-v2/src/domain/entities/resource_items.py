"""Resource Manager value entities: Column, Reference Standard, Chemical, Volumetric Solution."""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base_entity import BaseEntity


@dataclass
class ColumnMaster(BaseEntity):
    """Chromatography column master."""

    code: str = field(default="")
    name: str = field(default="")
    type: str | None = field(default=None)
    manufacturer: str | None = field(default=None)
    dimensions: str | None = field(default=None)
    serial_number: str | None = field(default=None)
    instrument_id: int | None = field(default=None)
    max_injections: int | None = field(default=None)
    current_injections: int = field(default=0)
    status: str = field(default="Active")
    received_date: datetime | None = field(default=None)
    retirement_date: datetime | None = field(default=None)


@dataclass
class ReferenceStandard(BaseEntity):
    """Reference standard master with potency and expiry tracking."""

    code: str = field(default="")
    name: str = field(default="")
    lot_number: str | None = field(default=None)
    potency: float | None = field(default=None)
    manufacturer: str | None = field(default=None)
    category: str | None = field(default=None)  # Primary, Secondary, Working
    storage_condition: str | None = field(default=None)
    quantity_received: float | None = field(default=None)
    quantity_remaining: float | None = field(default=None)
    unit: str | None = field(default=None)
    received_date: datetime | None = field(default=None)
    expiry_date: datetime | None = field(default=None)
    status: str = field(default="Active")


@dataclass
class ChemicalReagent(BaseEntity):
    """Chemical/Reagent inventory master."""

    code: str = field(default="")
    name: str = field(default="")
    grade: str | None = field(default=None)
    manufacturer: str | None = field(default=None)
    lot_number: str | None = field(default=None)
    cas_number: str | None = field(default=None)
    quantity_received: float | None = field(default=None)
    quantity_remaining: float | None = field(default=None)
    unit: str | None = field(default=None)
    storage_condition: str | None = field(default=None)
    received_date: datetime | None = field(default=None)
    expiry_date: datetime | None = field(default=None)
    opened_date: datetime | None = field(default=None)
    status: str = field(default="Active")


@dataclass
class ProjectMaster(BaseEntity):
    """Project master for R&D / DLIMS with 17-field project tracking."""

    project_id: str = field(default="")
    product_name: str = field(default="")
    product_code: str | None = field(default=None)
    project_code: str | None = field(default=None)
    project_code_academic: str | None = field(default=None)
    bd_code_sap: str | None = field(default=None)
    group_lead: str | None = field(default=None)
    location: str | None = field(default=None)
    market: str | None = field(default=None)
    start_date: datetime | None = field(default=None)
    end_date: datetime | None = field(default=None)
    license: str | None = field(default=None)
    comments: str | None = field(default=None)
    status: str = field(default="Active")
    requested_person: str | None = field(default=None)
    remarks: str | None = field(default=None)


@dataclass
class VolumetricSolution(BaseEntity):
    """Volumetric solution preparation & standardization master."""

    code: str = field(default="")
    name: str = field(default="")
    concentration: str | None = field(default=None)
    prepared_by: str | None = field(default=None)
    prepared_date: datetime | None = field(default=None)
    expiry_date: datetime | None = field(default=None)
    standardization_factor: float | None = field(default=None)
    standardized_by: str | None = field(default=None)
    standardized_date: datetime | None = field(default=None)
    status: str = field(default="Active")
