from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.auth.schemas import LoginRequest, LoginResponse, LogoutRequest
from app.auth import service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host
    result = await service.login(db, data, ip_address)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.post("/logout")
async def logout(data: LogoutRequest, db: AsyncSession = Depends(get_db)):
    success = await service.logout(db, data.token)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Logged out successfully"}
