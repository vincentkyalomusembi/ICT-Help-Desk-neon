from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import check_db_connection
from app.assets.routes import router as assets_router
from app.auth.routes import router as auth_router
from app.staff.routes import router as staff_router
from app.audit.routes import router as audit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_db_connection()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(staff_router)
app.include_router(audit_router)

@app.get("/")
async def home():
    return {"message": "ICT Helpdesk API"}

