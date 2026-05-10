from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user
from app.models.api import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.security import create_access_token
from app.services.auth import UserAlreadyExistsError, authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> AuthResponse:
    try:
        user = await create_user(email=str(payload.email), password=payload.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    access_token, expires_in = create_access_token(
        user_id=str(user["id"]),
        email=str(user["email"]),
    )

    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    user = await authenticate_user(email=str(payload.email), password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expires_in = create_access_token(
        user_id=str(user["id"]),
        email=str(user["email"]),
    )

    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
