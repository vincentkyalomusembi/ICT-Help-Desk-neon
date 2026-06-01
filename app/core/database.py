from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.core.config import settings

raw_database_url = settings.DATABASE_URL.replace("?sslmode=require", "")
parsed_url = make_url(raw_database_url)

if parsed_url.drivername == "postgresql":
    parsed_url = parsed_url.set(drivername="postgresql+asyncpg")

DATABASE_URL = str(parsed_url)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"ssl": "require"}
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def check_db_connection():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        print("Database connected successfully")
    except Exception as e:
        print(f"Connection failed: {e}")