"""
Pydantic schemas for Certificate of Analysis endpoints.

The `snapshot` passes through as loose JSON rather than being modelled field by
field. It is an immutable historical document: a certificate issued today must
still deserialise years from now, and a strict model would start rejecting older
snapshots the first time the shape evolved.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class COASummaryResponse(BaseModel):
    """List projection — omits the snapshot, which is the bulk of the record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    coa_number: str
    product_id: int
    product_code: str | None = None
    product_name: str | None = None
    batch_number: str
    status: str
    overall_verdict: str
    test_count: int
    released_by: str
    released_at: datetime | None = None


class COAResponse(COASummaryResponse):
    """Full certificate, including the frozen snapshot the print page renders."""

    snapshot: dict[str, Any] = {}


class GenerateCOARequest(BaseModel):
    product_id: int
    batch_number: str = Field(min_length=1, max_length=100)
    remarks: str | None = None
    #  E-signature, verified by the endpoint before the service runs.
    password: str


class PreviewCOARequest(BaseModel):
    product_id: int
    batch_number: str = Field(min_length=1, max_length=100)


class COAPreviewResponse(BaseModel):
    """
    What a certificate would contain, without issuing one.

    Lets QA see any failing or unevaluated test before committing a signature.
    """

    snapshot: dict[str, Any] = {}
