from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import LoginRequest, LoginResponse, LogoutRequest, SessionResponse
from app.auth.service import auth_service
from app.core.database import get_db

router = APIRouter(prefix='/auth', tags=['auth'])

@router.post('/login', response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await auth_service.login(
            session,
            payload.email,
            payload.password,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    return {
        'message': result['message'],
        'staff_id': result['staff_id'],
        'role': result['role'],
        'token': result['token'],
        'expires_at': result['expires_at'],
    }

@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_db),
):
    if not await auth_service.logout(session, payload.token):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found or already logged out')

@router.get('/sessions', response_model=List[SessionResponse], status_code=status.HTTP_200_OK)
async def list_sessions(session: AsyncSession = Depends(get_db)):
    return await auth_service.list_sessions(session)

@router.get('/sessions/{session_id}', response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def get_session(session_id: int, session: AsyncSession = Depends(get_db)):
    auth_session = await auth_service.get_session(session, session_id)
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')
    return auth_session
