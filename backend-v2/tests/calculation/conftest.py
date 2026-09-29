"""
Shared fixtures/helpers for the template + worksheet service tests.

Kept alongside the calculation tests rather than in the root conftest because
nothing outside this package needs a seeded template/TRF pair.
"""
from src.domain.entities.user import User
from src.infrastructure.database.models.product_model import ProductModel
from src.infrastructure.database.models.test_model import TestModel
from src.infrastructure.database.models.trf_model import (
    TestRequestFormModel,
    TRFTestLineModel,
)


def user(username: str, role: str, user_id: int = 1) -> User:
    return User(id=user_id, username=username, full_name=username.title(), role=role)


async def seed_test(session, code: str = "TST-01", name: str = "Assay") -> TestModel:
    test = TestModel(code=code, name=name, type="Quantitative", status="Active")
    session.add(test)
    await session.flush()
    return test


async def seed_trf_with_line(
    session,
    status: str = "InProgress",
    *,
    test: TestModel | None = None,
    batch_number: str = "B-2601",
    label_claim: str = "50 mg",
) -> tuple[TestRequestFormModel, TRFTestLineModel]:
    """A product + TRF + one test line, at whichever workflow status is needed."""
    product = ProductModel(
        code="PRD-1", name="Paracetamol Tablets", material_type="FG", status="Active"
    )
    session.add(product)
    await session.flush()

    trf = TestRequestFormModel(
        trf_number="TRF-20260805-0001",
        ar_number="AR-20260805-0001",
        product_id=product.id,
        batch_number=batch_number,
        label_claim=label_claim,
        status=status,
        initiated_by="analyst",
    )
    session.add(trf)
    await session.flush()

    test = test or await seed_test(session)
    line = TRFTestLineModel(trf_id=trf.id, line_no=1, test_id=test.id)
    session.add(line)
    await session.flush()
    return trf, line


async def set_trf_status(session, trf: TestRequestFormModel, status: str) -> None:
    trf.status = status
    await session.flush()
