import socket
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

from urllib.parse import urlparse

def is_postgres_available() -> bool:
    if "postgresql" not in settings.DATABASE_URL:
        return False
    try:
        parsed = urlparse(settings.DATABASE_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        s = socket.create_connection((host, port), timeout=3.0)
        s.close()
        return True
    except Exception as e:
        print(f"PostgreSQL connection check failed: {e}")
        return False

# Dynamically decide DB URL and Sync URL based on Postgres accessibility
use_postgres = is_postgres_available()

db_url = settings.DATABASE_URL if (use_postgres or "postgresql" not in settings.DATABASE_URL) else "sqlite+aiosqlite:///./pothys_agm.db"
db_sync_url = settings.DATABASE_SYNC_URL if (use_postgres or "postgresql" not in settings.DATABASE_URL) else "sqlite:///./pothys_agm.db"

print(f"[DB SESSION] Active DATABASE_URL: {db_url}")

if not use_postgres and "postgresql" in settings.DATABASE_URL:
    print("WARNING: PostgreSQL is not reachable at configured address. Falling back to SQLite.")

# Clean query parameters for asyncpg compatibility (e.g., remove pgbouncer=true parameter which asyncpg dialect rejects)
if "postgresql+asyncpg" in db_url and "?" in db_url:
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(db_url)
    query = parse_qs(parsed.query)
    query.pop("pgbouncer", None)
    clean_query = urlencode(query, doseq=True)
    db_url = urlunparse(parsed._replace(query=clean_query))

# Connection pool configurations are set only for non-sqlite connections
async_kwargs = {"future": True, "echo": True}
if "sqlite" not in db_url:
    async_kwargs["pool_size"] = 20
    async_kwargs["max_overflow"] = 10
    async_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }

async_engine = create_async_engine(db_url, **async_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

sync_kwargs = {"echo": True}
if "sqlite" not in db_sync_url:
    sync_kwargs["pool_size"] = 5
    sync_kwargs["max_overflow"] = 10

sync_engine = create_engine(db_sync_url, **sync_kwargs)

SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)

# Dependency injection for API route handlers
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
