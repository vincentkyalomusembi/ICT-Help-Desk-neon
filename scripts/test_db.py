import os
import asyncio
import re
from sqlalchemy import text
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

load_dotenv()

async def async_main() -> None:
    raw = os.getenv('DATABASE_URL')
    if not raw:
        print('DATABASE_URL not set')
        return
    # normalize scheme to asyncpg driver
    raw = re.sub(r'^postgresql:', 'postgresql+asyncpg:', raw)
    # remove sslmode/channel_binding query params; we'll pass ssl via connect_args
    p = urlparse(raw)
    qs = dict(parse_qsl(p.query))
    qs.pop('sslmode', None)
    qs.pop('channel_binding', None)
    clean = urlunparse(p._replace(query=urlencode(qs)))

    engine = create_async_engine(clean, echo=True, connect_args={"ssl": "require"})
    async with engine.connect() as conn:
        result = await conn.execute(text("select 'hello world'"))
        print(result.all())
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(async_main())