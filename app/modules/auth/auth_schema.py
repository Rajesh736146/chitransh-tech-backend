"""Pydantic schemas for auth module."""

import uuid
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime


class SignUpRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: str | None = None
    role_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    role_id: int
    status: str
    email_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class AskResetOtpRequest(BaseModel):
    email: EmailStr


class VerifyResetOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    password: str


class MessageResponse(BaseModel):
    message: str
