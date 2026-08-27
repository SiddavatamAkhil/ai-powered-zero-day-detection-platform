"""
Auth endpoints. Thin — validation and translation to HTTP only.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_service, get_current_user
from app.core.rate_limit import login_rate_limiter, register_rate_limiter
from app.models.user import User
from app.schemas.user import (
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services.auth_service import AuthError, AuthService


import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limiter)],
)
async def register(
    payload: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user = await auth_service.register(payload)
        return user
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error during registration for {payload.email}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration server error: {str(exc)}",
        )


@router.post(
    "/login",
    response_model=TokenPair,
    dependencies=[Depends(login_rate_limiter)],
)
async def login(
    payload: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Normal JSON login endpoint used by the frontend.
    """
    try:
        return await auth_service.authenticate(
            payload.email,
            payload.password,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error during login for {payload.email}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login server error: {str(exc)}",
        )


@router.post(
    "/token",
    response_model=TokenPair,
    include_in_schema=False,
)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    OAuth2-compatible login endpoint used by Swagger UI.

    Swagger sends:
        username=<email>
        password=<password>

    The username is treated as the user's email.
    """
    try:
        return await auth_service.authenticate(
            form_data.username,
            form_data.password,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post(
    "/refresh",
    response_model=TokenPair,
)
async def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.refresh(
            payload.refresh_token,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.logout(
        payload.refresh_token,
    )


@router.get(
    "/me",
    response_model=UserRead,
)
async def me(
    current_user: User = Depends(get_current_user),
):
    return current_user