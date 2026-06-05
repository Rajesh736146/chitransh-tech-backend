"""Auth routes — sign-up, login, email verification, and password reset."""

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.auth.auth_service import AuthService
from app.modules.auth.auth_schema import (
    SignUpRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    AskResetOtpRequest,
    VerifyOtpRequest,
    VerifyOtpResponse,
    VerifyResetOtpRequest,
    ResetPasswordRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/sign-up", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(payload: SignUpRequest, service: AuthService = Depends(get_auth_service)):
    return await service.sign_up(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return await service.login(payload)


@router.get("/me", response_model=UserResponse)
async def me(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
):
    return await service.get_current_user(credentials.credentials)


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.verify_email(payload.token)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.forgot_password(payload.email)


@router.post("/ask-reset-otp", response_model=MessageResponse)
async def ask_reset_otp(
    payload: AskResetOtpRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.forgot_password(payload.email)


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    payload: VerifyOtpRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.verify_otp(payload.email, payload.otp)


@router.post("/verify-reset-otp", response_model=MessageResponse)
async def verify_reset_otp(
    payload: VerifyResetOtpRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.verify_password_reset_otp(payload.email, payload.otp)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.reset_password(payload.email, payload.otp, payload.reset_token, payload.password)
