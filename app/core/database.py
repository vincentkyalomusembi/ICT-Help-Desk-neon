from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
import re
import logging
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

logger = logging.getLogger(__name__)

raw = settings.DATABASE_URL

engine = None
AsyncSessionLocal = None
DATABASE_URL = None

if raw:
    normalized = re.sub(r"^postgresql:", "postgresql+asyncpg:", raw)
    p = urlparse(normalized)
    qs = dict(parse_qsl(p.query))
    qs.pop("sslmode", None)
    qs.pop("channel_binding", None)
    clean = urlunparse(
        p._replace(query=urlencode(qs))
    )
    DATABASE_URL = clean
    engine = create_async_engine(
        DATABASE_URL,
        echo=getattr(settings, "DEBUG", False),
        connect_args={"ssl": "require"},
        pool_pre_ping=True,
        pool_recycle=300,
    )
    AsyncSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


async def get_db():
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL in .env"
        )
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_connection():
    if engine is None:
        logger.warning("Database is not configured. Skipping connection check")
        return
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise