from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from app.models.user import User
from app.core.security import get_password_hash

async def test_login_success(client: TestClient, db_session: AsyncSession):
    # Seed test user
    hashed_pw = get_password_hash("agmPassword123")
    user = User(
        email="test.agm@pothys.com",
        password_hash=hashed_pw,
        full_name="Test AGM User",
        role="AGM",
        branch_id=None
    )
    db_session.add(user)
    await db_session.commit()

    # Attempt login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test.agm@pothys.com", "password": "agmPassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

async def test_login_invalid_password(client: TestClient, db_session: AsyncSession):
    # Seed user
    hashed_pw = get_password_hash("agmPassword123")
    user = User(
        email="test.agm2@pothys.com",
        password_hash=hashed_pw,
        full_name="Test AGM User 2",
        role="AGM",
        branch_id=None
    )
    db_session.add(user)
    await db_session.commit()

    # Attempt login with invalid password
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test.agm2@pothys.com", "password": "wrongPassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

async def test_get_current_user_me(client: TestClient, db_session: AsyncSession):
    hashed_pw = get_password_hash("agmPassword123")
    user = User(
        email="test.agm3@pothys.com",
        password_hash=hashed_pw,
        full_name="Test AGM User 3",
        role="AGM",
        branch_id=None
    )
    db_session.add(user)
    await db_session.commit()

    # Authenticate
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test.agm3@pothys.com", "password": "agmPassword123"}
    )
    access_token = login_response.json()["access_token"]

    # Call endpoint with token
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["email"] == "test.agm3@pothys.com"
    assert data["full_name"] == "Test AGM User 3"
    assert data["role"] == "AGM"

async def test_get_current_user_me_unauthorized(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

async def test_setup_status_no_agm(client: TestClient):
    response = client.get("/api/v1/auth/setup-status")
    assert response.status_code == 200
    assert response.json()["has_agm"] is False

async def test_setup_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/setup",
        json={"full_name": "New AGM", "email": "new.agm@pothys.com", "password": "newAgmPassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Verify setup status is now true
    status_response = client.get("/api/v1/auth/setup-status")
    assert status_response.json()["has_agm"] is True

async def test_setup_already_exists(client: TestClient, db_session: AsyncSession):
    # Seed user first
    user = User(
        email="existing.agm@pothys.com",
        password_hash="dummy_hash",
        full_name="Existing AGM",
        role="AGM",
        branch_id=None
    )
    db_session.add(user)
    await db_session.commit()

    # Attempt setup again
    response = client.post(
        "/api/v1/auth/setup",
        json={"full_name": "New AGM", "email": "new.agm@pothys.com", "password": "newAgmPassword123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Executive account already exists."

async def test_forgot_password_smtp_unavailable(client: TestClient, db_session: AsyncSession):
    user = User(
        email="reset.agm@pothys.com",
        password_hash="dummy_hash",
        full_name="Reset AGM",
        role="AGM",
        branch_id=None
    )
    db_session.add(user)
    await db_session.commit()

    response = client.post("/api/v1/auth/forgot-password", json={"email": "reset.agm@pothys.com"})
    # Since SMTP host is empty, it returns 503 Service Unavailable
    assert response.status_code == 503
    assert "service is unavailable" in response.json()["detail"]

async def test_reset_password_success(client: TestClient, db_session: AsyncSession):
    from datetime import datetime, timedelta, timezone
    from app.core.security import get_password_hash
    
    hashed_pw = get_password_hash("oldPassword123")
    user = User(
        email="reset.success@pothys.com",
        password_hash=hashed_pw,
        full_name="Reset Success AGM",
        role="AGM",
        branch_id=None,
        reset_token="123456",
        reset_token_expires=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db_session.add(user)
    await db_session.commit()

    # Reset password
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "reset.success@pothys.com", "token": "123456", "new_password": "newPassword123"}
    )
    assert response.status_code == 200
    assert "successful" in response.json()["detail"]

    # Verify we can login with new password
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "reset.success@pothys.com", "password": "newPassword123"}
    )
    assert login_response.status_code == 200

