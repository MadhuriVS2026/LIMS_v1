"""
Shared pytest fixtures for backend-v2 tests.

Provides an in-memory SQLite async engine/session per test (mirroring
`src.infrastructure.database.session`'s engine setup, but pointed at
`sqlite+aiosqlite:///:memory:` with schema created fresh per test) and
factory helpers for constructing `User` domain entities per role.
"""
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.infrastructure.database.models  # noqa: F401  (registers all ORM models)
from src.domain.entities.user import User
from src.infrastructure.database.models.base_model import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a fresh in-memory SQLite async session per test.

    Uses a StaticPool-backed single connection so the in-memory database
    persists for the lifetime of the test (SQLite `:memory:` databases are
    otherwise per-connection), and creates all ORM tables before yielding.
    """
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


def make_user(
    role: str = "Analyst",
    *,
    id: int = 1,
    username: str | None = None,
    full_name: str | None = None,
    email: str | None = None,
    department: str | None = None,
    is_active: bool = True,
) -> User:
    """Build a `User` domain entity with sensible defaults for the given role."""
    username = username or f"{role.lower()}_user"
    full_name = full_name or f"{role} User"
    return User(
        id=id,
        username=username,
        password_hash="not-a-real-hash",
        full_name=full_name,
        role=role,
        email=email,
        department=department,
        is_active=is_active,
    )


def make_admin_user(**overrides) -> User:
    return make_user("Admin", **overrides)


def make_analyst_user(**overrides) -> User:
    return make_user("Analyst", **overrides)


def make_supervisor_user(**overrides) -> User:
    return make_user("Supervisor", **overrides)


def make_qa_user(**overrides) -> User:
    return make_user("QA", **overrides)


@pytest.fixture
def admin_user() -> User:
    return make_admin_user()


@pytest.fixture
def analyst_user() -> User:
    return make_analyst_user()


@pytest.fixture
def supervisor_user() -> User:
    return make_supervisor_user()


@pytest.fixture
def qa_user() -> User:
    return make_qa_user()
