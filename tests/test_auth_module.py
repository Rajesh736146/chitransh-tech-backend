import os

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

os.environ["debug"] = "false"
os.environ["database_url"] = "sqlite+aiosqlite:///:memory:"

from app.core.dependencies import get_db
from app.db.session import Base
from app.main import app
from app.modules.auth.auth_service import ALGORITHM
from app.core.config import get_settings
from jose import jwt


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        execution_options={"schema_translate_map": {"public": None}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    yield async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory):
    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def captured_email(monkeypatch):
    captured = {}

    def send_verification_email(email: str, token: str) -> None:
        captured["verification_email"] = email
        captured["verification_token"] = token

    def send_password_reset_email(email: str, otp: str) -> None:
        captured["reset_email"] = email
        captured["reset_otp"] = otp

    monkeypatch.setattr("app.modules.auth.auth_service.send_verification_email", send_verification_email)
    monkeypatch.setattr("app.modules.auth.auth_service.send_password_reset_email", send_password_reset_email)
    return captured


@pytest.mark.asyncio
async def test_register_verify_login_and_me(client: AsyncClient, captured_email: dict):
    email = "auth.flow@example.com"
    password = "StrongPass123"
    response = await client.post(
        "/api/v1/auth/sign-up",
        json={
            "full_name": "Auth Flow",
            "email": email,
            "password": password,
            "phone": "9999999999",
            "role_id": 1,
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == email
    assert captured_email["verification_email"] == email

    verify_response = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": captured_email["verification_token"]},
    )
    assert verify_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert token

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


@pytest.mark.asyncio
async def test_forgot_password_and_reset_with_otp(client: AsyncClient, captured_email: dict):
    email = "otp.reset@example.com"
    old_password = "OldPass123"
    new_password = "NewPass123"

    await client.post(
        "/api/v1/auth/sign-up",
        json={
            "full_name": "OTP User",
            "email": email,
            "password": old_password,
            "phone": "8888888888",
            "role_id": 1,
        },
    )

    ask_response = await client.post("/api/v1/auth/ask-reset-otp", json={"email": email})
    assert ask_response.status_code == 200
    assert ask_response.json()["message"] == "If the email is registered, a password reset code has been sent"
    otp = captured_email["reset_otp"]
    assert otp.isdigit()
    assert len(otp) == 6

    verify_otp_response = await client.post(
        "/api/v1/auth/verify-reset-otp",
        json={"email": email, "otp": otp},
    )
    assert verify_otp_response.status_code == 200
    assert verify_otp_response.json()["message"] == "Password reset code is valid"

    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": otp, "password": new_password},
    )
    assert reset_response.status_code == 200

    old_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login_response.status_code == 401

    new_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login_response.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_is_generic(client: AsyncClient):
    response = await client.post("/api/v1/auth/forgot-password", json={"email": "unknown@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "If the email is registered, a password reset code has been sent"


@pytest.mark.asyncio
async def test_reset_password_fails_with_invalid_otp(client: AsyncClient):
    email = "invalid.otp@example.com"
    await client.post(
        "/api/v1/auth/sign-up",
        json={
            "full_name": "Invalid OTP",
            "email": email,
            "password": "SomePass123",
            "phone": "7777777777",
            "role_id": 1,
        },
    )

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": email, "otp": "000000", "password": "AnotherPass123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired password reset code"


@pytest.mark.asyncio
async def test_me_rejects_invalid_token(client: AsyncClient):
    bad_token = jwt.encode({"sub": "not-a-uuid"}, get_settings().secret_key, algorithm=ALGORITHM)
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401
