from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import check_db_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_db_connection()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def home():
    return {"message": "ICT Helpdesk API"}