import pytest
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector

# Map vector type to TEXT inside SQLite for unit testing compatibility
@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"

from app.db.base import Base
from app.db.session import get_db
from app.main import app

from sqlalchemy.pool import StaticPool

# Local async SQLite connection string
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    """Create test tables at beginning and drop at end of test suite."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session wrapped in an automatic rollback transaction."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client with database dependency overridden."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
