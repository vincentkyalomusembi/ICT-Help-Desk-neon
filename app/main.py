from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from app.core.database import check_db_connection
from app.assets.routes import router as assets_router
from app.auth.routes import router as auth_router
from app.staff.routes import staff_router, directorate_router, department_router
from app.audit.routes import router as audit_router
from app.tickets.routes import router as tickets_router
from app.ict_personnel.routes import router as ict_personnel_router
from app.dashboard.routes import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_db_connection()
    yield


app = FastAPI(lifespan=lifespan, redirect_slashes=False)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React default
        "http://localhost:5173",    # Vite default
        "https://ict-help-desk-frontend.vercel.app",  # Production URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(staff_router)
app.include_router(directorate_router)
app.include_router(department_router)
app.include_router(audit_router)
app.include_router(tickets_router)
app.include_router(ict_personnel_router)
app.include_router(dashboard_router)


@app.get("/")
async def home():
    return {"message": "ICT Helpdesk API"}

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}