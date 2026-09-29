"""Product repository implementation (Adapter)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.product import Product
from src.domain.repositories.product_repository import IProductRepository
from src.infrastructure.database.models.product_model import ProductModel


class ProductRepositoryImpl(IProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, product_id: int) -> Product | None:
        model = await self._session.get(ProductModel, product_id)
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[Product]:
        result = await self._session.execute(select(ProductModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, product: Product) -> Product:
        model = ProductModel(
            code=product.code,
            name=product.name,
            description=product.description,
            material_type=product.material_type,
            retest_period_days=product.retest_period_days,
            storage_condition=product.storage_condition,
            status=product.status,
            created_by=product.created_by,
            modified_by=product.modified_by,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, product: Product) -> Product:
        model = await self._session.get(ProductModel, product.id)
        if model is None:
            raise ValueError(f"Product {product.id} not found")
        model.name = product.name
        model.description = product.description
        model.material_type = product.material_type
        model.retest_period_days = product.retest_period_days
        model.storage_condition = product.storage_condition
        model.status = product.status
        model.approved_by = product.approved_by
        model.approved_at = product.approved_at
        model.modified_by = product.modified_by
        model.modified_date = product.modified_date
        await self._session.flush()
        return self._to_entity(model)

    async def exists_by_code(self, code: str) -> bool:
        stmt = select(ProductModel.id).where(ProductModel.code == code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _to_entity(model: ProductModel) -> Product:
        return Product(
            id=model.id,
            code=model.code,
            name=model.name,
            description=model.description,
            material_type=model.material_type,
            retest_period_days=model.retest_period_days,
            storage_condition=model.storage_condition,
            status=model.status,
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            created_by=model.created_by,
            created_date=model.created_date,
            modified_by=model.modified_by,
            modified_date=model.modified_date,
        )
